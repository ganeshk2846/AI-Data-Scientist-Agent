"""
backend/tests/test_phase3_2_hardening.py
Phase 3.2 Architectural Hardening & Regression Test Suite:
1. Multi-Entity Topology Validation & Zero False Positives (Scenario D: Manufacturing Work Orders).
2. Per-Metric Identifier & Predicate Validation (Scenario E: Partial E-commerce).
3. Value Linker Domain Isolation Gating.
4. Database-Scoped Approval API Security (Server-derived verification, tamper rejection, HTTP 400).
5. Specialized Churn Pre-Execution Schema Validation (Tables, columns, controlled exception boundaries).
6. Provenance & Lifecycle Separation (SYSTEM_APPROVED vs USER_APPROVED vs Candidate exclusion).
7. Non-Destructive Invariance verification of ecommerce.db.
"""

import hashlib
import sqlite3
from pathlib import Path
from typing import Tuple
import pytest
from fastapi.testclient import TestClient

from backend.app.analysis.churn import analyze_customer_churn_risk
from backend.app.analysis.contracts import AnalysisType
from backend.app.core.config import settings
from backend.app.core.contracts import MetricStatus, SemanticMetricDefinition
from backend.app.db.adapters import SQLiteAdapter
from backend.app.db.migration import run_agent_store_migration
from backend.app.main import app
from backend.app.retrieval.semantics import (
    DynamicSemanticEngine,
    dynamic_semantic_engine,
    is_ecommerce_compatible,
)
from backend.app.retrieval.value_linker import ValueLinker
from backend.app.schema.models import DatabaseCatalog
from backend.app.schema.service import SchemaService, schema_service


def compute_file_sha256(path: Path) -> str:
    """Computes SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


# =====================================================================
# Fixture Helpers for Synthetic Databases
# =====================================================================

def _create_manufacturing_db(path: Path) -> Tuple[SQLiteAdapter, DatabaseCatalog]:
    """
    Creates Scenario D: Manufacturing Work Orders database.
    Contains 'orders' table with total_amount and order_status, but lacks e-commerce
    entities (customers, order_items, products, payments).
    """
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute("""
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                machine_id INTEGER NOT NULL,
                shop_floor_section TEXT NOT NULL,
                order_status TEXT NOT NULL,
                total_amount REAL NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE workshops (
                workshop_id INTEGER PRIMARY KEY,
                supervisor_name TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE maintenance_logs (
                log_id INTEGER PRIMARY KEY,
                machine_id INTEGER NOT NULL,
                maintenance_cost REAL NOT NULL
            );
        """)
        conn.execute("INSERT INTO orders VALUES (101, 5, 'Section A', 'delivered', 12500.0);")
        conn.execute("INSERT INTO orders VALUES (102, 6, 'Section B', 'in_progress', 8500.0);")
        conn.execute("INSERT INTO workshops VALUES (1, 'Hans Gruber');")
        conn.execute("INSERT INTO maintenance_logs VALUES (1, 5, 450.0);")
    conn.close()

    adapter = SQLiteAdapter(file_path=str(path), name="manufacturing_db", read_only=True)
    adapter.connect()
    svc = SchemaService(db_path=str(path))
    catalog = svc.profile_database(force_refresh=True)
    return adapter, catalog


def _create_partial_ecommerce_db(path: Path, include_delivered_sample: bool = True) -> Tuple[SQLiteAdapter, DatabaseCatalog]:
    """
    Creates Scenario E: Partial E-commerce database.
    Has customers, orders, products. Lacks returns, support_tickets, marketing_spend.
    """
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute("""
            CREATE TABLE customers (
                customer_id INTEGER PRIMARY KEY,
                customer_name TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE products (
                product_id INTEGER PRIMARY KEY,
                product_name TEXT NOT NULL,
                unit_price REAL NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                order_date TEXT NOT NULL,
                order_status TEXT NOT NULL,
                total_amount REAL NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
            );
        """)
        conn.execute("INSERT INTO customers VALUES (1, 'Alice');")
        conn.execute("INSERT INTO products VALUES (10, 'Industrial Gear', 200.0);")

        if include_delivered_sample:
            conn.execute("INSERT INTO orders VALUES (1001, 1, '2026-01-01', 'delivered', 200.0);")
            conn.execute("INSERT INTO orders VALUES (1002, 1, '2026-01-02', 'cancelled', 50.0);")
        else:
            conn.execute("INSERT INTO orders VALUES (1001, 1, '2026-01-01', 'pending', 200.0);")
            conn.execute("INSERT INTO orders VALUES (1002, 1, '2026-01-02', 'shipped', 50.0);")
    conn.close()

    adapter = SQLiteAdapter(file_path=str(path), name="partial_ecom_db", read_only=True)
    adapter.connect()
    svc = SchemaService(db_path=str(path))
    catalog = svc.profile_database(force_refresh=True)
    return adapter, catalog


# =====================================================================
# Objective 1 & 4 Tests: E-commerce Topology & Per-Metric Validation
# =====================================================================

def test_scenario_d_manufacturing_work_orders_rejected(tmp_path: Path):
    """
    Verifies Scenario D (Manufacturing Work Orders):
    - Has 'orders' with 'total_amount' and 'order_status', but no 'customers' or supporting entities.
    - is_ecommerce_compatible() MUST return False.
    - seed_baseline_canonical_metrics() MUST return 0.
    - Zero metrics seeded into storage.
    """
    app_db = tmp_path / "test_agent_app.sqlite"
    run_agent_store_migration(app_db)
    engine = DynamicSemanticEngine(app_db_path=app_db)

    mfg_db = tmp_path / "manufacturing.sqlite"
    adapter, catalog = _create_manufacturing_db(mfg_db)
    fp = adapter.compute_fingerprint()

    # 1. Compatibility check must reject manufacturing topology
    assert is_ecommerce_compatible(catalog) is False

    # 2. Seeding must abstain
    seeded = engine.seed_baseline_canonical_metrics(fingerprint=fp, catalog=catalog)
    assert seeded == 0

    # 3. Authoritative metrics must be empty
    auth_metrics = engine.get_authoritative_metrics(fingerprint=fp)
    assert len(auth_metrics) == 0

    adapter.disconnect()


def test_scenario_e_partial_ecommerce_selective_seeding(tmp_path: Path):
    """
    Verifies Scenario E (Partial E-commerce):
    - Has 'orders', 'customers', 'products', with 'delivered' sample values.
    - is_ecommerce_compatible() returns True.
    - Seeds ONLY metrics whose required tables and columns exist (gross_revenue, net_revenue, average_order_value).
    - Correctly abstains from seeding missing-table metrics (return_rate, customer_csat, marketing_roas).
    - Verified metrics are marked SYSTEM_APPROVED.
    """
    app_db = tmp_path / "test_agent_app.sqlite"
    run_agent_store_migration(app_db)
    engine = DynamicSemanticEngine(app_db_path=app_db)

    partial_db = tmp_path / "partial_ecom.sqlite"
    adapter, catalog = _create_partial_ecommerce_db(partial_db, include_delivered_sample=True)
    fp = adapter.compute_fingerprint()

    assert is_ecommerce_compatible(catalog) is True

    seeded = engine.seed_baseline_canonical_metrics(fingerprint=fp, catalog=catalog)
    # Exactly 3 metrics have all required tables and columns
    assert seeded == 3

    auth_metrics = engine.get_authoritative_metrics(fingerprint=fp)
    seeded_keys = {m.metric_key for m in auth_metrics}

    # Present metrics
    assert "gross_revenue" in seeded_keys
    assert "net_revenue" in seeded_keys
    assert "average_order_value" in seeded_keys

    # Abstaining metrics (tables missing)
    assert "return_rate" not in seeded_keys
    assert "customer_csat" not in seeded_keys
    assert "marketing_roas" not in seeded_keys

    # Check status is SYSTEM_APPROVED
    for m in auth_metrics:
        assert m.status == MetricStatus.SYSTEM_APPROVED
        assert m.verified_by == "system_baseline"

    adapter.disconnect()


def test_predicate_validation_abstains_when_delivered_status_absent(tmp_path: Path):
    """
    Verifies value predicate validation:
    If 'order_status' sample values do NOT contain 'delivered',
    net_revenue and average_order_value MUST NOT be seeded!
    Only gross_revenue (which requires no predicate) can be seeded.
    """
    app_db = tmp_path / "test_agent_app.sqlite"
    run_agent_store_migration(app_db)
    engine = DynamicSemanticEngine(app_db_path=app_db)

    partial_db = tmp_path / "no_delivered_sample.sqlite"
    adapter, catalog = _create_partial_ecommerce_db(partial_db, include_delivered_sample=False)
    fp = adapter.compute_fingerprint()

    assert is_ecommerce_compatible(catalog) is True

    seeded = engine.seed_baseline_canonical_metrics(fingerprint=fp, catalog=catalog)
    auth_metrics = engine.get_authoritative_metrics(fingerprint=fp)
    seeded_keys = {m.metric_key for m in auth_metrics}

    # gross_revenue passes (has total_amount, no predicate)
    assert "gross_revenue" in seeded_keys
    # net_revenue and average_order_value must be skipped because 'delivered' is not in sample values
    assert "net_revenue" not in seeded_keys
    assert "average_order_value" not in seeded_keys

    adapter.disconnect()


def test_value_linker_domain_isolation_with_manufacturing(tmp_path: Path):
    """
    Verifies ValueLinker does NOT fire e-commerce literal rules on non-e-commerce databases.
    """
    linker = ValueLinker()
    mfg_db = tmp_path / "mfg_linker.sqlite"
    adapter, catalog = _create_manufacturing_db(mfg_db)

    # Manufacturing schema has 'delivered' in order_status, but is NOT e-commerce compatible
    assert is_ecommerce_compatible(catalog) is False

    # Dynamic value discovery: should match 'delivered' only as a generic dynamic column value,
    # but NOT trigger e-commerce specific mappings (like customer_segments, promotions, etc.)
    results = linker.link_values("Show me VIP delivered orders", catalog=catalog)
    target_tables = {r.target_table for r in results}

    # customer_segments VIP mapping MUST NOT trigger because table doesn't exist and domain is invalid
    assert "customer_segments" not in target_tables
    adapter.disconnect()


# =====================================================================
# Objective 2 Tests: Database-Scoped Approval API Security
# =====================================================================

def test_approve_api_rejects_fingerprint_mismatch():
    """
    Verifies that POST /api/v1/retrieval/metrics/approve rejects a client-supplied
    fingerprint that mismatches the active connected database (HTTP 400).
    """
    with TestClient(app) as client:
        res = client.post(
            "/api/v1/retrieval/metrics/approve",
            json={
                "metric_key": "gross_revenue",
                "fingerprint": "attacker_fake_fingerprint_12345",
                "approved_by": "attacker",
            },
        )
        assert res.status_code == 400
        error_msg = res.json().get("error", {}).get("message", "") or res.json().get("detail", "")
        assert "does not match active connected database" in error_msg


def test_approve_api_succeeds_with_active_database():
    """
    Verifies that POST /api/v1/retrieval/metrics/approve succeeds when approving
    an existing metric under the active database fingerprint, upgrading status to USER_APPROVED.
    """
    cat = schema_service.get_cached_catalog() or schema_service.profile_database(force_refresh=False)
    fp = cat.fingerprint
    dynamic_semantic_engine.seed_baseline_canonical_metrics(fingerprint=fp, catalog=cat)

    with TestClient(app) as client:
        # 1. Approve without supplying fingerprint (server derives active fingerprint)
        res = client.post(
            "/api/v1/retrieval/metrics/approve",
            json={"metric_key": "gross_revenue", "approved_by": "lead_data_scientist"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["metric_key"] == "gross_revenue"
        assert data["status"] == MetricStatus.USER_APPROVED.value
        assert data["verified_by"] == "lead_data_scientist"

        # 2. Approve supplying matching fingerprint
        res2 = client.post(
            "/api/v1/retrieval/metrics/approve",
            json={"metric_key": "gross_revenue", "fingerprint": fp, "approved_by": "director_bi"},
        )
        assert res2.status_code == 200
        assert res2.json()["data"]["verified_by"] == "director_bi"


def test_engine_approve_metric_refuses_empty_fingerprint(tmp_path: Path):
    """
    Verifies DynamicSemanticEngine.approve_metric refuses empty or 'default' fingerprints.
    """
    app_db = tmp_path / "test_app.sqlite"
    run_agent_store_migration(app_db)
    engine = DynamicSemanticEngine(app_db_path=app_db)

    # Empty fingerprint
    assert engine.approve_metric("some_metric", fingerprint="") is None
    # None fingerprint
    assert engine.approve_metric("some_metric", fingerprint=None) is None
    # 'default' fingerprint
    assert engine.approve_metric("some_metric", fingerprint="default") is None


# =====================================================================
# Objective 3 Tests: Specialized Churn Schema Pre-Execution Validation
# =====================================================================

def test_churn_analysis_abstains_on_missing_tables(tmp_path: Path):
    """
    Verifies analyze_customer_churn_risk cleanly abstains if required tables are missing.
    """
    db_path = tmp_path / "incomplete_db.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE orders (order_id INTEGER PRIMARY KEY);")
    conn.close()

    result = analyze_customer_churn_risk(db_path=str(db_path))
    assert result.success is False
    assert result.analysis_type == AnalysisType.CHURN_RISK
    assert "missing required tables" in result.abstain_reason


def test_churn_analysis_abstains_on_missing_columns(tmp_path: Path):
    """
    Verifies analyze_customer_churn_risk checks required columns:
    customer_segments: segment_id, segment_name
    customer_segment_history: customer_id, segment_id, valid_to
    orders: customer_id, total_amount, order_id
    """
    db_path = tmp_path / "missing_col_db.sqlite"
    conn = sqlite3.connect(str(db_path))
    with conn:
        # customer_segments missing segment_name
        conn.execute("CREATE TABLE customer_segments (segment_id INTEGER PRIMARY KEY);")
        # customer_segment_history missing valid_to
        conn.execute("CREATE TABLE customer_segment_history (customer_id INTEGER, segment_id INTEGER);")
        # orders missing total_amount
        conn.execute("CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER);")
    conn.close()

    result = analyze_customer_churn_risk(db_path=str(db_path))
    assert result.success is False
    assert "missing columns" in result.abstain_reason
    assert "valid_to" in result.abstain_reason


def test_churn_analysis_succeeds_on_valid_schema(tmp_path: Path):
    """
    Verifies analyze_customer_churn_risk succeeds when all required tables and columns are present.
    """
    db_path = tmp_path / "valid_churn_db.sqlite"
    conn = sqlite3.connect(str(db_path))
    with conn:
        conn.execute("""
            CREATE TABLE customer_segments (
                segment_id INTEGER PRIMARY KEY,
                segment_name TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE customer_segment_history (
                customer_id INTEGER NOT NULL,
                segment_id INTEGER NOT NULL,
                valid_to TEXT
            );
        """)
        conn.execute("""
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                total_amount REAL NOT NULL
            );
        """)
        conn.execute("INSERT INTO customer_segments VALUES (1, 'At Risk');")
        conn.execute("INSERT INTO customer_segment_history VALUES (101, 1, NULL);")
        conn.execute("INSERT INTO orders VALUES (1, 101, 500.0);")
    conn.close()

    result = analyze_customer_churn_risk(db_path=str(db_path))
    assert result.success is True
    assert result.churn_risk is not None
    assert result.churn_risk.total_customers_analyzed == 1
    assert result.churn_risk.total_revenue_at_risk > 0


# =====================================================================
# Objective 4 Tests: SYSTEM_APPROVED vs USER_APPROVED Model
# =====================================================================

def test_system_vs_user_approval_provenance_lifecycle(tmp_path: Path):
    """
    Verifies clean separation:
    - Candidate inserted as VALIDATED_CANDIDATE: NOT in authoritative metrics.
    - Baseline canonical seeded as SYSTEM_APPROVED: IN authoritative metrics.
    - Explicit human approval upgrades to USER_APPROVED: IN authoritative metrics.
    - Candidate unapproved is STILL excluded.
    """
    app_db = tmp_path / "agent_store.sqlite"
    run_agent_store_migration(app_db)
    engine = DynamicSemanticEngine(app_db_path=app_db)

    fp = "test_lifecycle_fp"

    # 1. Insert unapproved candidate metric
    conn = sqlite3.connect(str(app_db))
    with conn:
        conn.execute("""
            INSERT INTO semantic_metrics (
                id, metric_key, display_name, formula_sql, status, derivation_type,
                confidence_score, fingerprint
            ) VALUES ('m_cand', 'churn_rate', 'Churn Rate', 'count(churned)/count(*)',
                      'VALIDATED_CANDIDATE', 'INFERRED', 0.8, ?);
        """, (fp,))
    conn.close()

    # Verify unapproved candidate NOT returned
    auth = engine.get_authoritative_metrics(fingerprint=fp)
    assert len(auth) == 0

    # 2. Seed baseline metric (SYSTEM_APPROVED)
    partial_db = tmp_path / "ecom.sqlite"
    adapter, catalog = _create_partial_ecommerce_db(partial_db, include_delivered_sample=True)
    engine.seed_baseline_canonical_metrics(fingerprint=fp, catalog=catalog)

    auth = engine.get_authoritative_metrics(fingerprint=fp)
    assert len(auth) == 3
    # All are SYSTEM_APPROVED
    for m in auth:
        assert m.status == MetricStatus.SYSTEM_APPROVED

    # Candidate still excluded
    assert "churn_rate" not in {m.metric_key for m in auth}

    # 3. Human user explicitly approves the candidate metric
    approved = engine.approve_metric("churn_rate", fingerprint=fp, approved_by="head_of_analytics")
    assert approved is not None
    assert approved.status == MetricStatus.USER_APPROVED
    assert approved.verified_by == "head_of_analytics"

    # 4. Authoritative list now includes both SYSTEM_APPROVED and USER_APPROVED
    auth_final = engine.get_authoritative_metrics(fingerprint=fp)
    assert len(auth_final) == 4
    status_map = {m.metric_key: m.status for m in auth_final}
    assert status_map["churn_rate"] == MetricStatus.USER_APPROVED
    assert status_map["gross_revenue"] == MetricStatus.SYSTEM_APPROVED

    adapter.disconnect()


# =====================================================================
# Objective 6: Bitwise Invariance of ecommerce.db
# =====================================================================

def test_phase3_2_ecommerce_db_bitwise_invariance():
    """Confirms ecommerce.db SHA-256 remains 100% bitwise invariant."""
    expected_hash = "366080C92E8DC7024A15B95730A35E63AC16765F748142F51CC40F92B63F3D9E"
    actual_hash = compute_file_sha256(settings.resolved_ecommerce_db_path)
    assert actual_hash == expected_hash, f"CRITICAL: Hash mismatch! {actual_hash} != {expected_hash}"
