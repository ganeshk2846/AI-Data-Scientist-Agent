"""
Security and AST guardrail tests for sqlglot validator.
"""

from backend.app.schema.service import schema_service
from backend.app.sql.validator import sql_validator


def test_select_query_allowed():
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database()
    query = "SELECT order_id, total_amount FROM orders WHERE order_status = 'delivered';"
    is_valid, sanitized, errors = sql_validator.validate_and_format_sql(query, catalog)
    assert is_valid is True
    assert len(errors) == 0
    assert "LIMIT" in sanitized


def test_mutations_blocked():
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database()

    # INSERT
    v, _, errs = sql_validator.validate_and_format_sql("INSERT INTO orders (order_id) VALUES (1);", catalog)
    assert v is False
    assert any("SELECT" in e or "INSERT" in e for e in errs)

    # UPDATE
    v, _, errs = sql_validator.validate_and_format_sql("UPDATE orders SET total_amount = 0;", catalog)
    assert v is False

    # DELETE
    v, _, errs = sql_validator.validate_and_format_sql("DELETE FROM orders;", catalog)
    assert v is False


def test_ddl_and_pragmas_blocked():
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database()

    # DROP
    v, _, errs = sql_validator.validate_and_format_sql("DROP TABLE orders;", catalog)
    assert v is False

    # PRAGMA
    v, _, errs = sql_validator.validate_and_format_sql("PRAGMA table_info(orders);", catalog)
    assert v is False
    assert any("PRAGMA" in e or "SELECT" in e for e in errs)


def test_multiple_statements_blocked():
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database()
    query = "SELECT 1 FROM orders; DROP TABLE orders;"
    v, _, errs = sql_validator.validate_and_format_sql(query, catalog)
    assert v is False
    assert any("Multiple statement" in e for e in errs)


def test_hallucinated_table_blocked():
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database()
    query = "SELECT * FROM non_existent_financial_ledger_table;"
    v, _, errs = sql_validator.validate_and_format_sql(query, catalog)
    assert v is False
    assert any("does not exist" in e for e in errs)


def test_automatic_limit_appended():
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database()
    query = "SELECT customer_id, first_name FROM customers;"
    v, sanitized, _ = sql_validator.validate_and_format_sql(query, catalog)
    assert v is True
    assert "LIMIT 1000" in sanitized or "LIMIT" in sanitized

