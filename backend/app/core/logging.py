"""
Structured logging configuration with secret redaction.
"""

import logging
import re
import sys
from typing import Any, Dict
from backend.app.core.config import settings

# Sensitive keyword patterns to redact from logs
SENSITIVE_PATTERNS = [
    re.compile(r"(key|token|secret|password|authorization|bearer)\s*[:=]\s*([^\s,;]+)", re.IGNORECASE),
    re.compile(r"(sk-[a-zA-Z0-9_-]{20,})"),
    re.compile(r"(AIza[0-9A-Za-z-_]{35})"),
]


class SafeFormatter(logging.Formatter):
    """Log formatter that automatically masks API keys and sensitive tokens."""

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        for pattern in SENSITIVE_PATTERNS:
            msg = pattern.sub(r"\1: [REDACTED]", msg)
        return msg


def setup_logging():
    """Initializes root application logger."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = SafeFormatter(
        fmt="%(asctime)s | %(levelname)-7s | [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    # Clear existing handlers to prevent duplicate output
    root_logger.handlers = [handler]

    # Silence verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)


setup_logging()
logger = logging.getLogger("ai_bi")

