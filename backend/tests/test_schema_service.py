"""
Tests for Phase 2: Schema introspection, profiling service, caching, and API endpoints.
"""

import asyncio
from pathlib import Path
import sqlite3
import pytest
from backend.app.schema.models import DatabaseCatalog, TableModel
from backend.app.schema.service import SchemaService, schema_service


def test_compute_source_fingerprint():
    fp = schema_service.compute_source_fingerprint()
    assert isinstance(fp, str)
    assert len(fp) == 64  # SHA256 length


def test_profile_database():
    catalog = schema_service.profile_database(force_refresh=True)
    assert isinstance(catalog, DatabaseCatalog)
    assert catalog.total_tables == 30
    assert catalog.total_rows == 334503
    assert len(catalog.foreign_key_graph) == 44

    # Check key tables exist
    for tbl in ["orders", "customers", "products", "payments", "marketing_spend", "daily_targets"]:
        assert tbl in catalog.tables


def test_table_columns_and_metrics():
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database(force_refresh=False)
    orders = catalog.tables["orders"]
    assert orders.name == "orders"
    assert orders.row_count == 17924
    assert "order_id" in orders.primary_key_columns

    # Verify column naming in payments: amount (not payment_amount)
    payments = catalog.tables["payments"]
    assert payments.get_column("amount") is not None
    assert payments.get_column("payment_amount") is None

    # Check safe sample values on low-cardinality status field
    status_col = payments.get_column("payment_status")
    assert status_col is not None
    assert set(status_col.sample_values) == {"paid", "voided"}


def test_minimal_prompt_schema():
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database(force_refresh=False)
    prompt_schema = catalog.to_minimal_prompt_schema(["orders", "payments"])
    assert "Table: orders" in prompt_schema
    assert "Table: payments" in prompt_schema
    assert "amount" in prompt_schema
    assert "[PK]" in prompt_schema
    # Ensure no massive row data is dumped
    assert "20891624.33" not in prompt_schema


def test_api_schema_status(client):
    res = client.get("/api/v1/schema/status")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["is_prepared"] is True
    assert body["data"]["catalog_summary"]["total_tables"] == 30


def test_api_list_tables(client):
    res = client.get("/api/v1/schema/tables")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    tables = body["data"]
    assert len(tables) == 30
    names = [t["name"] for t in tables]
    assert "orders" in names
    assert "products" in names


def test_api_get_single_table(client):
    res = client.get("/api/v1/schema/tables/orders")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    tbl = body["data"]
    assert tbl["name"] == "orders"
    assert tbl["row_count"] == 17924
    assert len(tbl["columns"]) == 14


def test_api_get_nonexistent_table_404(client):
    res = client.get("/api/v1/schema/tables/non_existent_table_xyz")
    assert res.status_code == 404
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_api_prepare_schema_job(client):
    res = client.post("/api/v1/schema/prepare?force=false")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    job = body["data"]
    assert "job_id" in job
    assert job["status"] in ["pending", "running", "succeeded"]


def test_temporary_test_database(tmp_path):
    """Verifies schema service on a temporary SQLite database."""
    test_db = tmp_path / "test_mini.sqlite"
    conn = sqlite3.connect(str(test_db))
    cur = conn.cursor()
    cur.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, role TEXT);")
    cur.execute("INSERT INTO users (id, name, role) VALUES (1, 'Alice', 'admin'), (2, 'Bob', 'user');")
    conn.commit()
    conn.close()

    temp_service = SchemaService(db_path=test_db)
    fp = temp_service.compute_source_fingerprint()
    assert len(fp) == 64
    # Profile with a custom connection
    conn_ro = sqlite3.connect(f"file:{test_db.as_posix()}?mode=ro", uri=True)
    cur = conn_ro.cursor()
    cur.execute("SELECT COUNT(*) FROM users;")
    assert cur.fetchone()[0] == 2
    conn_ro.close()

