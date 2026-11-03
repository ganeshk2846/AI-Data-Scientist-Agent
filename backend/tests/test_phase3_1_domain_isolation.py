"""
backend/tests/test_phase3_1_domain_isolation.py
Phase 3.1 Cross-Domain Isolation and Semantic Integrity Test Suite.

Verifies:
Test A: E-commerce compatibility (e-commerce database accesses compatible canonical metrics with exact fingerprint).
Test B: Healthcare isolation (synthetic Healthcare DB with patients/billing never receives e-commerce canonical metrics).
Test C: Database switching (connect e-commerce -> switch Healthcare -> reconnect e-commerce with strict isolation).
Test D: No static fallback (unfamiliar database with no approved metrics gets empty semantic metric context in orchestrator).
Test E: Approval lifecycle (AUTO_INFERRED and VALIDATED_CANDIDATE do not enter authoritative context; only USER_APPROVED enters).
Test F: Schema changes (changing table or column invalidates/changes fingerprint).
Test G: Retriever fallback (question without matching keywords does not force 'orders' table into retrieval results).
Test H: Specialized analytics safety (churn analysis safely abstains on incompatible schema without crashing).
Test I: Value linker isolation (e-commerce literal mappings are not applied to unfamiliar schemas; dynamic values linked from catalog).
Test J: Reconnection persistence (compatible approved definitions survive disconnect/reconnect to same database).
Test K: Real Ollama semantic inference on unfamiliar domain (live local Ollama qwen3:4b verification).
"""

from pathlib import Path
import sqlite3
from typing import Tuple
import pytest
from backend.app.analysis.churn import analyze_customer_churn_risk
from backend.app.core.config import settings
from backend.app.core.contracts import MetricStatus, SemanticMetricDefinition
from backend.app.db.adapters import SQLiteAdapter
from backend.app.db.migration import run_agent_store_migration
from backend.app.retrieval.retriever import schema_grounder
from backend.app.retrieval.semantics import (
    CANONICAL_METRICS,
    DynamicSemanticEngine,
    is_ecommerce_compatible,
    semantic_registry,
)
from backend.app.retrieval.value_linker import value_linker
from backend.app.schema.models import DatabaseCatalog
from backend.app.schema.service import SchemaService


def _create_synthetic_healthcare_db(path: Path) -> Tuple[SQLiteAdapter, DatabaseCatalog]:
    """Creates a temporary synthetic Healthcare SQLite database and returns adapter and catalog."""
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute("""
            CREATE TABLE patients (
                patient_id INTEGER PRIMARY KEY,
                admission_date TEXT NOT NULL,
                discharge_date TEXT,
                length_of_stay_days INTEGER,
                readmitted_30d INTEGER DEFAULT 0
            );
        """)
        conn.execute("""
            CREATE TABLE billing (
                bill_id INTEGER PRIMARY KEY,
                patient_id INTEGER NOT NULL,
                treatment_cost REAL NOT NULL,
                patient_copay REAL NOT NULL,
                billing_status TEXT DEFAULT 'copay_pending',
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
            );
        """)
        conn.execute("INSERT INTO patients VALUES (1, '2026-01-01', '2026-01-05', 4, 0);")
        conn.execute("INSERT INTO patients VALUES (2, '2026-01-02', '2026-01-10', 8, 1);")
        conn.execute("INSERT INTO billing VALUES (101, 1, 1500.0, 50.0, 'copay_paid');")
        conn.execute("INSERT INTO billing VALUES (102, 2, 8500.0, 200.0, 'copay_pending');")
    conn.close()
    adapter = SQLiteAdapter(file_path=str(path), name="healthcare_db", read_only=True)
    adapter.connect()
    svc = SchemaService(db_path=str(path))
    catalog = svc.profile_database(force_refresh=True)
    return adapter, catalog


def _create_synthetic_ecommerce_db(path: Path) -> Tuple[SQLiteAdapter, DatabaseCatalog]:
    """Creates a temporary synthetic minimal E-Commerce SQLite database and returns adapter and catalog."""
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute("""
            CREATE TABLE customers (
                customer_id INTEGER PRIMARY KEY,
                customer_name TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                order_date TEXT NOT NULL,
                order_status TEXT NOT NULL,
                total_amount REAL NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE order_items (
                item_id INTEGER PRIMARY KEY,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(order_id)
            );
        """)
        conn.execute("""
            CREATE TABLE returns (
                return_id INTEGER PRIMARY KEY,
                order_id INTEGER NOT NULL,
                return_reason TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(order_id)
            );
        """)
        conn.execute("INSERT INTO customers VALUES (10, 'Alice');")
        conn.execute("INSERT INTO customers VALUES (11, 'Bob');")
        conn.execute("INSERT INTO orders VALUES (1, 10, '2026-01-01', 'delivered', 150.0);")
        conn.execute("INSERT INTO orders VALUES (2, 11, '2026-01-02', 'cancelled', 80.0);")
        conn.execute("INSERT INTO order_items VALUES (1, 1, 1001, 2, 75.0);")
        conn.execute("INSERT INTO returns VALUES (1, 2, 'defective');")
    conn.close()
    adapter = SQLiteAdapter(file_path=str(path), name="synthetic_ecom_db", read_only=True)
    adapter.connect()
    svc = SchemaService(db_path=str(path))
    catalog = svc.profile_database(force_refresh=True)
    return adapter, catalog


# =====================================================================
# Test A: E-Commerce Compatibility
# =====================================================================
def test_a_ecommerce_compatibility(tmp_path: Path):
    """Verifies that an e-commerce database accesses compatible canonical metrics with its exact fingerprint."""
    app_db = tmp_path / "agent_store.sqlite"
    run_agent_store_migration(app_db)
    engine = DynamicSemanticEngine(app_db_path=app_db)

    ecom_db = tmp_path / "ecom.sqlite"
    adapter, catalog = _create_synthetic_ecommerce_db(ecom_db)
    fp = adapter.compute_fingerprint()

    assert is_ecommerce_compatible(catalog) is True

    # Seed canonical metrics for ecom
    seeded = engine.seed_baseline_canonical_metrics(fingerprint=fp, catalog=catalog)
    assert seeded > 0

    # Retrieve authoritative metrics
    authoritative = engine.get_authoritative_metrics(fingerprint=fp)
    metric_keys = {m.metric_key for m in authoritative}
    assert "gross_revenue" in metric_keys
    assert "net_revenue" in metric_keys
    assert "return_rate" in metric_keys
    adapter.disconnect()


# =====================================================================
# Test B: Healthcare Isolation
# =====================================================================
def test_b_healthcare_isolation(tmp_path: Path):
    """Verifies a synthetic Healthcare DB containing patients/billing NEVER receives e-commerce canonical metrics."""
    app_db = tmp_path / "agent_store.sqlite"
    run_agent_store_migration(app_db)
    engine = DynamicSemanticEngine(app_db_path=app_db)

    health_db = tmp_path / "healthcare.sqlite"
    adapter, catalog = _create_synthetic_healthcare_db(health_db)
    fp = adapter.compute_fingerprint()

    assert is_ecommerce_compatible(catalog) is False

    # Attempt to seed canonical e-commerce metrics into healthcare
    seeded = engine.seed_baseline_canonical_metrics(fingerprint=fp, catalog=catalog)
    assert seeded == 0, "Canonical e-commerce metrics must not be seeded into Healthcare schema."

    # Verify no authoritative metrics exist for healthcare
    authoritative = engine.get_authoritative_metrics(fingerprint=fp)
    assert len(authoritative) == 0, "Healthcare database must not receive e-commerce metrics."

    # Verify formatted prompt context is empty
    prompt_ctx = engine.format_authoritative_prompt_context(fingerprint=fp, query="What is net revenue?")
    assert prompt_ctx == ""
    adapter.disconnect()


# =====================================================================
# Test C: Database Switching Isolation
# =====================================================================
def test_c_database_switching(tmp_path: Path):
    """Connect to e-commerce, switch to Healthcare, reconnect to e-commerce: verify strict isolation."""
    app_db = tmp_path / "agent_store.sqlite"
    run_agent_store_migration(app_db)
    engine = DynamicSemanticEngine(app_db_path=app_db)

    ecom_db = tmp_path / "ecom.sqlite"
    health_db = tmp_path / "healthcare.sqlite"

    ecom_adapter, ecom_cat = _create_synthetic_ecommerce_db(ecom_db)
    health_adapter, health_cat = _create_synthetic_healthcare_db(health_db)

    ecom_fp = ecom_adapter.compute_fingerprint()
    health_fp = health_adapter.compute_fingerprint()
    assert ecom_fp != health_fp

    # 1. Active: E-commerce
    engine.seed_baseline_canonical_metrics(fingerprint=ecom_fp, catalog=ecom_cat)
    ecom_metrics = engine.get_authoritative_metrics(fingerprint=ecom_fp)
    assert len(ecom_metrics) > 0

    # 2. Switch: Healthcare
    engine.seed_baseline_canonical_metrics(fingerprint=health_fp, catalog=health_cat)
    health_metrics = engine.get_authoritative_metrics(fingerprint=health_fp)
    assert len(health_metrics) == 0, "Healthcare must see 0 e-commerce metrics upon switch."

    # 3. Reconnect: E-commerce
    reconnect_metrics = engine.get_authoritative_metrics(fingerprint=ecom_fp)
    assert len(reconnect_metrics) == len(ecom_metrics)
    assert {m.metric_key for m in reconnect_metrics} == {m.metric_key for m in ecom_metrics}

    ecom_adapter.disconnect()
    health_adapter.disconnect()


# =====================================================================
# Test D: No Static Fallback
# =====================================================================
def test_d_no_static_fallback(tmp_path: Path):
    """An unfamiliar database with no approved metrics must not receive metrics from static registry."""
    app_db = tmp_path / "agent_store.sqlite"
    run_agent_store_migration(app_db)
    engine = DynamicSemanticEngine(app_db_path=app_db)

    health_db = tmp_path / "healthcare.sqlite"
    adapter, catalog = _create_synthetic_healthcare_db(health_db)
    fp = adapter.compute_fingerprint()

    # format_authoritative_prompt_context must return empty
    context = engine.format_authoritative_prompt_context(fingerprint=fp, query="Calculate our gross revenue and return rate")
    assert context == "", "Authoritative prompt context must be empty when no approved metrics exist for database."

    # Static registry find_relevant_metrics with catalog gating must return empty
    relevant = semantic_registry.find_relevant_metrics("gross revenue and return rate", catalog=catalog)
    assert len(relevant) == 0, "Static registry must not return e-commerce metrics for non-ecommerce catalog."
    adapter.disconnect()


# =====================================================================
# Test E: Approval Lifecycle
# =====================================================================
def test_e_approval_lifecycle(tmp_path: Path):
    """AUTO_INFERRED and VALIDATED_CANDIDATE definitions do not enter authoritative context; only USER_APPROVED enters."""
    app_db = tmp_path / "agent_store.sqlite"
    run_agent_store_migration(app_db)
    engine = DynamicSemanticEngine(app_db_path=app_db)

    health_db = tmp_path / "healthcare.sqlite"
    adapter, _ = _create_synthetic_healthcare_db(health_db)
    fp = adapter.compute_fingerprint()

    # Insert candidate metric with VALIDATED_CANDIDATE
    conn = sqlite3.connect(str(app_db))
    with conn:
        conn.execute("""
            INSERT INTO semantic_metrics (
                id, metric_key, display_name, formula_sql, status, derivation_type, fingerprint
            ) VALUES ('inferred_1', 'avg_length_of_stay', 'Avg Length of Stay', 'AVG(length_of_stay_days)', 'VALIDATED_CANDIDATE', 'INFERRED', ?);
        """, (fp,))
    conn.close()

    # Candidate metric must NOT be authoritative
    authoritative = engine.get_authoritative_metrics(fingerprint=fp)
    assert len(authoritative) == 0

    # Attempt to approve with wrong fingerprint: must FAIL
    failed_approval = engine.approve_metric("avg_length_of_stay", fingerprint="wrong_fingerprint_xyz")
    assert failed_approval is None

    # Still unapproved
    assert len(engine.get_authoritative_metrics(fingerprint=fp)) == 0

    # Approve with correct fingerprint
    approved = engine.approve_metric("avg_length_of_stay", fingerprint=fp, approved_by="admin_user")
    assert approved is not None
    assert approved.status == MetricStatus.USER_APPROVED
    assert approved.verified_by == "admin_user"

    # Now appears in authoritative metrics
    authoritative_after = engine.get_authoritative_metrics(fingerprint=fp)
    assert len(authoritative_after) == 1
    assert authoritative_after[0].metric_key == "avg_length_of_stay"
    adapter.disconnect()


# =====================================================================
# Test F: Schema Changes Invalidation
# =====================================================================
def test_f_schema_changes_invalidation(tmp_path: Path):
    """Changing a relevant table or column changes the fingerprint and isolates old definitions."""
    app_db = tmp_path / "agent_store.sqlite"
    run_agent_store_migration(app_db)
    engine = DynamicSemanticEngine(app_db_path=app_db)

    db_path = tmp_path / "evolving.sqlite"
    conn = sqlite3.connect(str(db_path))
    with conn:
        conn.execute("CREATE TABLE inventory (item_id INTEGER PRIMARY KEY, stock_qty INTEGER);")
    conn.close()

    adapter_v1 = SQLiteAdapter(file_path=str(db_path), name="evolving_db")
    adapter_v1.connect()
    fp_v1 = adapter_v1.compute_fingerprint()

    # Insert approved metric under fp_v1
    conn = sqlite3.connect(str(app_db))
    with conn:
        conn.execute("""
            INSERT INTO semantic_metrics (
                id, metric_key, display_name, formula_sql, status, derivation_type, fingerprint
            ) VALUES ('met_v1', 'total_stock', 'Total Stock', 'SUM(stock_qty)', 'USER_APPROVED', 'CANONICAL', ?);
        """, (fp_v1,))
    conn.close()

    assert len(engine.get_authoritative_metrics(fingerprint=fp_v1)) == 1
    adapter_v1.disconnect()

    # Schema change: restructure schema topology
    conn = sqlite3.connect(str(db_path))
    with conn:
        conn.execute("CREATE TABLE suppliers (supplier_id INTEGER PRIMARY KEY, name TEXT);")
    conn.close()

    adapter_v2 = SQLiteAdapter(file_path=str(db_path), name="evolving_db")
    adapter_v2.connect()
    fp_v2 = adapter_v2.compute_fingerprint()

    assert fp_v1 != fp_v2, "Schema alteration must change computed fingerprint."
    # fp_v2 must not see stale definitions from fp_v1
    assert len(engine.get_authoritative_metrics(fingerprint=fp_v2)) == 0
    adapter_v2.disconnect()


# =====================================================================
# Test G: Retriever Fallback
# =====================================================================
def test_g_retriever_no_orders_fallback(tmp_path: Path):
    """A question that does not match existing keywords must not force 'orders' table."""
    health_db = tmp_path / "healthcare.sqlite"
    adapter, catalog = _create_synthetic_healthcare_db(health_db)

    # Query with no keywords matching ecom synonyms
    tables = schema_grounder.retrieve_tables("What is the average treatment cost?", catalog)
    assert "orders" not in tables, "Unrelated query on Healthcare DB must never force 'orders' table."
    # If anything is retrieved, it must be from catalog.tables
    for t in tables:
        assert t in catalog.tables
    adapter.disconnect()


# =====================================================================
# Test H: Specialized Analytics Safety (Churn Risk)
# =====================================================================
def test_h_specialized_analytics_churn_safety(tmp_path: Path):
    """Customer churn analysis must not execute against a database lacking required schema."""
    health_db = tmp_path / "healthcare.sqlite"
    adapter, _ = _create_synthetic_healthcare_db(health_db)

    # Run churn analysis directly against healthcare db
    result = analyze_customer_churn_risk(db_path=str(health_db))
    assert result.success is False
    assert result.abstain_reason is not None
    assert "missing required tables" in result.abstain_reason.lower()
    assert "customer_segments" in result.abstain_reason
    adapter.disconnect()


# =====================================================================
# Test I: Value Linker Isolation
# =====================================================================
def test_i_value_linker_isolation(tmp_path: Path):
    """E-commerce literal mappings must not be applied as global assumptions to unfamiliar schemas."""
    health_db = tmp_path / "healthcare.sqlite"
    adapter, catalog = _create_synthetic_healthcare_db(health_db)

    # 1. E-commerce query on Healthcare catalog: no e-commerce literal mappings produced
    linked_health = value_linker.link_values("Show all delivered orders from VIP customers", catalog=catalog)
    ecom_targets = {lv.target_table for lv in linked_health}
    assert "orders" not in ecom_targets
    assert "customer_segments" not in ecom_targets

    # 2. Dynamic linking: query mentioning actual sample value in billing table
    # billing_status has sample 'copay_pending'
    linked_dynamic = value_linker.link_values("Which patients have copay_pending status?", catalog=catalog)
    assert any(lv.target_table == "billing" and lv.target_column == "billing_status" for lv in linked_dynamic)
    adapter.disconnect()


# =====================================================================
# Test J: Reconnection Persistence
# =====================================================================
def test_j_reconnection_persistence(tmp_path: Path):
    """Compatible approved semantic definitions must survive disconnect/reconnect to the same database."""
    app_db = tmp_path / "agent_store.sqlite"
    run_agent_store_migration(app_db)
    engine = DynamicSemanticEngine(app_db_path=app_db)

    health_db = tmp_path / "healthcare.sqlite"
    adapter, _ = _create_synthetic_healthcare_db(health_db)
    fp = adapter.compute_fingerprint()

    # Add and approve metric
    conn = sqlite3.connect(str(app_db))
    with conn:
        conn.execute("""
            INSERT INTO semantic_metrics (
                id, metric_key, display_name, formula_sql, status, derivation_type, fingerprint
            ) VALUES ('m_readmit', 'readmission_rate', '30-Day Readmission Rate', 'AVG(readmitted_30d) * 100', 'USER_APPROVED', 'MANUAL', ?);
        """, (fp,))
    conn.close()

    # Disconnect
    adapter.disconnect()

    # Reconnect
    adapter_reconnect = SQLiteAdapter(file_path=str(health_db), name="healthcare_db", read_only=True)
    adapter_reconnect.connect()
    fp_reconnect = adapter_reconnect.compute_fingerprint()

    assert fp == fp_reconnect

    reconnected_metrics = engine.get_authoritative_metrics(fingerprint=fp_reconnect)
    assert len(reconnected_metrics) == 1
    assert reconnected_metrics[0].metric_key == "readmission_rate"
    assert reconnected_metrics[0].status == MetricStatus.USER_APPROVED
    adapter_reconnect.disconnect()


# =====================================================================
# Test K: Real Groq Inference on Unfamiliar Domain (Live Groq verification)
# =====================================================================
def is_groq_configured() -> bool:
    """Checks if Groq API key is configured."""
    return settings.is_llm_configured()


@pytest.mark.skipif(not is_groq_configured(), reason="Groq API key is not configured")
def test_k_live_groq_unfamiliar_domain_inference(tmp_path: Path):
    """
    Verifies actual Groq model inference on a synthetic unfamiliar University Library domain.
    Verifies structured response, schema validation, candidate persistence, and explicit approval.
    """
    app_db = tmp_path / "agent_store.sqlite"
    run_agent_store_migration(app_db)
    engine = DynamicSemanticEngine(app_db_path=app_db)

    lib_db = tmp_path / "university_library.sqlite"
    conn = sqlite3.connect(str(lib_db))
    with conn:
        conn.execute("""
            CREATE TABLE books (
                book_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                total_pages INTEGER NOT NULL,
                replacement_cost_usd REAL NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE loans (
                loan_id INTEGER PRIMARY KEY,
                book_id INTEGER NOT NULL,
                borrower_id INTEGER NOT NULL,
                loan_duration_days INTEGER NOT NULL,
                overdue_fine_usd REAL DEFAULT 0.0,
                FOREIGN KEY (book_id) REFERENCES books(book_id)
            );
        """)
        conn.execute("INSERT INTO books VALUES (1, 'Algorithms 4th Ed', 950, 85.0);")
        conn.execute("INSERT INTO books VALUES (2, 'Operating Systems', 780, 95.0);")
        conn.execute("INSERT INTO loans VALUES (101, 1, 501, 14, 0.0);")
        conn.execute("INSERT INTO loans VALUES (102, 2, 502, 21, 5.0);")
    conn.close()

    adapter = SQLiteAdapter(file_path=str(lib_db), name="library_db", read_only=True)
    adapter.connect()
    svc = SchemaService(db_path=str(lib_db))
    catalog = svc.profile_database(force_refresh=True)
    fp = adapter.compute_fingerprint()

    # Run genuine Groq inference using real GroqLLMProvider
    from backend.app.llm.client import GroqLLMProvider
    groq_provider = GroqLLMProvider()

    inferred = engine.infer_metrics_from_schema(catalog, llm_provider=groq_provider)
    assert len(inferred) >= 2, f"Groq should infer at least 2 metrics, got {len(inferred)}"

    for m in inferred:
        assert m.metric_key
        assert m.formula_sql
        # Provenance must be INFERRED
        assert m.derivation_type == "INFERRED"
        # Status must be VALIDATED_CANDIDATE if columns exist, or AUTO_INFERRED
        assert m.status in [MetricStatus.VALIDATED_CANDIDATE, MetricStatus.AUTO_INFERRED]

    # Verify they are stored in DB with fp
    stored = engine.list_metrics(fingerprint=fp)
    assert len(stored) == len(inferred)

    # Must NOT be authoritative before approval
    auth_before = engine.get_authoritative_metrics(fingerprint=fp)
    assert len(auth_before) == 0

    # Explicitly approve the first candidate
    first_key = inferred[0].metric_key
    approved = engine.approve_metric(first_key, fingerprint=fp, approved_by="library_admin")
    assert approved is not None
    assert approved.status == MetricStatus.USER_APPROVED

    # Now authoritative
    auth_after = engine.get_authoritative_metrics(fingerprint=fp)
    assert len(auth_after) == 1
    assert auth_after[0].metric_key == first_key

    adapter.disconnect()
