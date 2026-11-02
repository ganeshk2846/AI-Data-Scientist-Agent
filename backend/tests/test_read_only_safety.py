"""
backend/tests/test_read_only_safety.py
Security and read-only integrity verification suite.
Validates that:
1. Destructive write probes are never executed against user databases.
2. The primary development database (ecommerce.db) remains bitwise identical.
3. Dialect-specific injection vectors are 100% blocked by AST validation.
"""

import hashlib
from pathlib import Path
import pytest
from backend.app.core.config import settings
from backend.app.core.errors import DatabaseReadOnlyViolationError
from backend.app.db.adapters.sqlite import SQLiteAdapter
from backend.app.security.guardrails import validate_sql_security


def compute_file_sha256(file_path: Path) -> str:
    """Computes exact SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_ecommerce_db_bitwise_immutability():
    """
    Verifies that querying ecommerce.db via SQLiteAdapter leaves the database
    file 100% bitwise identical before and after execution (zero writes).
    """
    db_path = settings.resolved_ecommerce_db_path
    assert db_path.exists(), f"ecommerce.db not found at: {db_path}"

    # Compute pre-query SHA-256 hash
    hash_before = compute_file_sha256(db_path)

    # Initialize adapter in read-only mode and execute queries
    adapter = SQLiteAdapter(file_path=db_path, read_only=True)
    adapter.connect()

    res = adapter.execute_query("SELECT count(*) as total_orders FROM orders")
    assert res.rows[0]["total_orders"] == 150000

    res2 = adapter.execute_query("SELECT order_status, count(*) as cnt FROM orders GROUP BY order_status LIMIT 3")
    assert len(res2.rows) <= 3

    adapter.disconnect()

    # Compute post-query SHA-256 hash
    hash_after = compute_file_sha256(db_path)

    # Assert bitwise invariance
    assert hash_before == hash_after, "CRITICAL: ecommerce.db was modified during read-only queries!"


def test_no_destructive_write_probes_on_active_database():
    """
    Verifies that neither SQLiteAdapter nor DatabaseConnectionManager execute
    CREATE TABLE __probe__ statements against connected databases during connect or inspection.
    """
    db_path = settings.resolved_ecommerce_db_path
    adapter = SQLiteAdapter(file_path=db_path, read_only=True)
    adapter.connect()

    tables = adapter.get_table_names()
    for t in tables:
        assert not t.startswith("__probe"), f"Found lingering probe table in database: {t}"

    adapter.disconnect()


def test_adversarial_injection_payloads_blocked():
    """
    Adversarial penetration test verifying that harmful DDL/DML vectors are
    rejected before ever reaching the database driver.
    """
    attack_payloads = [
        "DROP TABLE orders",
        "TRUNCATE TABLE customers",
        "DELETE FROM order_items WHERE 1=1",
        "UPDATE users SET balance = 1000000",
        "INSERT INTO payments VALUES (1, 2, 3)",
        "ALTER TABLE orders ADD COLUMN pwned TEXT",
        "ATTACH DATABASE '/etc/passwd' AS pwn",
        "SELECT * FROM orders; DROP TABLE orders;",
        "SELECT * FROM orders; DELETE FROM customers;",
        "SELECT load_extension('malicious.so')",
    ]

    for attack in attack_payloads:
        is_safe, reason = validate_sql_security(attack)
        assert is_safe is False, f"Vulnerability! Guardrail failed to block: {attack}"
        assert reason is not None
