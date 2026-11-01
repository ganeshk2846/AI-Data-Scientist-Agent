"""
Security guardrails, AST SQL injection defense, and prompt injection filters.
Enforces read-only database isolation, blocks adversarial bypasses, and redacts sensitive PII/secrets.
"""

import re
from typing import Optional, Set, Tuple
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

DANGEROUS_KEYWORDS: Set[str] = {
    "ATTACH",
    "DETACH",
    "DROP",
    "DELETE",
    "UPDATE",
    "INSERT",
    "ALTER",
    "CREATE",
    "REPLACE",
    "TRUNCATE",
    "PRAGMA",
    "VACUUM",
    "REINDEX",
}

DANGEROUS_FUNCTIONS: Set[str] = {
    "LOAD_EXTENSION",
    "WRITEFILE",
    "READFILE",
    "EDIT",
    "SHELL",
}

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions"),
    re.compile(r"(?i)system\s*:\s*(you\s+are|override|new\s+role)"),
    re.compile(r"(?i)disregard\s+(all\s+)?(rules|safety|guidelines)"),
    re.compile(r"(?i)reveal\s+(the\s+)?(system\s+prompt|instructions|secret|api\s*key|password|env)"),
    re.compile(r"(?i)print\s+(environment\s+variables|env\b|secrets)"),
    re.compile(r"(?i)bypass\s+(guardrail|filter|security)"),
]

# PII and Secret Redaction Patterns
CREDIT_CARD_REGEX = re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
API_KEY_REGEX = re.compile(r"(sk-[a-zA-Z0-9_-]{20,}|AIzaSy[a-zA-Z0-9_-]{33}|bearer\s+[a-zA-Z0-9_\-\.]{20,})", re.IGNORECASE)


def validate_sql_security(sql: str) -> Tuple[bool, Optional[str]]:
    """
    Validates that a SQL string is strictly a safe read-only SELECT query,
    free from DDL/DML, ATTACH bypasses, pragma abuse, and dangerous SQLite extensions.
    """
    cleaned = sql.strip().rstrip(";")
    if not cleaned:
        return False, "Query string is empty."

    # Pre-parse token checks for immediate block
    tokens_upper = set(re.findall(r"\b[A-Za-z_]+\b", cleaned.upper()))
    intersection = tokens_upper.intersection(DANGEROUS_KEYWORDS)
    if intersection:
        return False, f"Prohibited SQL keyword detected: {', '.join(sorted(intersection))}."

    # Parse AST
    try:
        parsed_expressions = sqlglot.parse(cleaned, read="sqlite")
    except ParseError as e:
        return False, f"SQL syntax error: {str(e)}"

    if not parsed_expressions:
        return False, "Failed to parse SQL statement."

    if len(parsed_expressions) > 1:
        return False, "Multi-statement execution (statement chaining via semicolon) is strictly prohibited."

    expression = parsed_expressions[0]

    # Must be SELECT expression
    if not isinstance(expression, (exp.Select, exp.Union)):
        return False, f"Only SELECT statements are permitted. Received: {expression.key.upper()}."

    # Check for any nested DML/DDL or prohibited AST nodes
    for node in expression.walk():
        if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter)):
            return False, f"Prohibited write statement node detected: {node.key.upper()}."

        # Check function calls
        if isinstance(node, exp.Anonymous):
            func_name = node.name.upper()
            if func_name in DANGEROUS_FUNCTIONS:
                return False, f"Prohibited SQLite function invocation: {func_name}."

        # Cost guard: check for Cartesian cross joins without conditions
        if isinstance(node, exp.Join):
            if node.kind and "CROSS" in node.kind.upper() and not node.args.get("on"):
                return False, "Unconstrained Cartesian cross join without ON condition rejected by cost guard."

    return True, None


def detect_prompt_injection(text: str) -> Tuple[bool, Optional[str]]:
    """
    Scans natural language user text for jailbreak or prompt override attempts.
    """
    for pattern in PROMPT_INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            return True, f"Prompt injection attempt detected: '{match.group(0)}'."
    return False, None


def redact_sensitive_data(text: str) -> str:
    """
    Redacts credit cards, emails, and API secret keys from logs and traces.
    """
    if not text:
        return text
    redacted = CREDIT_CARD_REGEX.sub("[REDACTED_CC]", text)
    redacted = EMAIL_REGEX.sub("[REDACTED_EMAIL]", redacted)
    redacted = API_KEY_REGEX.sub("[REDACTED_SECRET]", redacted)
    return redacted
