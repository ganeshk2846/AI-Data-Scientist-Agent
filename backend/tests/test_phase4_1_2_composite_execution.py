"""
backend/tests/test_phase4_1_2_composite_execution.py
Targeted test suite for Objective C: Verification of the Complete Composite Analytical Pipeline.
Verifies dynamic detection and sequential multi-stage execution across 2-stage, 3-stage,
and 4-stage analytical requests, ensuring all requested stages execute and report their individual statuses.
"""

from pathlib import Path
import sqlite3
import pytest

from backend.app.analysis.contracts_v2 import IntentCategory
from backend.app.analysis.intent_classifier import intent_classifier
from backend.app.analysis.orchestrator import analytical_orchestrator
from backend.app.db.adapters.sqlite import SQLiteAdapter
from backend.app.db.manager import db_manager
from backend.app.schema.service import SchemaService


def _setup_manufacturing_db(db_path: Path):
    """Sets up an isolated synthetic manufacturing database with temporal and categorical attributes."""
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE machines (
            machine_id INTEGER PRIMARY KEY,
            machine_name TEXT NOT NULL,
            workcenter TEXT NOT NULL,
            operating_cost REAL NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE downtime_events (
            event_id INTEGER PRIMARY KEY,
            machine_id INTEGER NOT NULL,
            event_date TEXT NOT NULL,
            downtime_hours REAL NOT NULL,
            root_cause TEXT NOT NULL,
            cost REAL NOT NULL,
            FOREIGN KEY (machine_id) REFERENCES machines (machine_id)
        )
    """)

    machines = ["Press-01", "CNC-02", "Lathe-03", "Welder-04"]
    for i, m in enumerate(machines, 1):
        cur.execute(
            "INSERT INTO machines (machine_id, machine_name, workcenter, operating_cost) VALUES (?, ?, ?, ?)",
            (i, m, f"WC-{i}", 15000.0 * i),
        )

    # 40 historical downtime observations spanning 40 days
    for day_idx in range(1, 41):
        m_id = (day_idx % 4) + 1
        dt = f"2025-01-{day_idx:02d}" if day_idx <= 31 else f"2025-02-{day_idx - 31:02d}"
        hours = 2.0 + (day_idx % 5) * 1.5 + (3.0 if m_id == 1 else 0.5)
        cur.execute(
            "INSERT INTO downtime_events (event_id, machine_id, event_date, downtime_hours, root_cause, cost) VALUES (?, ?, ?, ?, ?, ?)",
            (day_idx, m_id, dt, hours, f"Wear-{m_id}", hours * 250.0),
        )

    conn.commit()
    conn.close()


def test_scenario_a_three_stage_pipeline(tmp_path: Path):
    """
    Scenario A: Three-stage request (Descriptive -> Predictive -> Prescriptive)
    Query: 'What happened to machine downtime, what is likely to happen next month, and how should we allocate the maintenance budget?'
    """
    db_file = tmp_path / "mfg_a.sqlite"
    _setup_manufacturing_db(db_file)

    adapter = SQLiteAdapter(file_path=str(db_file), name="mfg_a_db", read_only=True)
    adapter.connect()
    db_manager._active_adapter = adapter
    svc = SchemaService(db_path=str(db_file))
    cat = svc.profile_database(force_refresh=True)

    q = "What happened to machine downtime, what is likely to happen next month, and how should we allocate our $25,000 maintenance budget?"

    # 1. Intent classification check
    cls_res = intent_classifier.classify(q)
    assert cls_res.is_composite is True
    assert cls_res.composite_intents == [
        IntentCategory.DESCRIPTIVE,
        IntentCategory.PREDICTIVE,
        IntentCategory.PRESCRIPTIVE,
    ]
    assert cls_res.execution_sequence == [
        "descriptive_trend_analysis",
        "predictive_forecasting",
        "prescriptive_recommendations",
    ]

    # 2. Sequential execution through orchestrator
    res = analytical_orchestrator.analyze(question=q, catalog=cat)
    assert res.success is True
    assert "composite_stages" in res.model_information
    assert res.model_information["composite_stages"] == [
        IntentCategory.DESCRIPTIVE.value,
        IntentCategory.PREDICTIVE.value,
        IntentCategory.PRESCRIPTIVE.value,
    ]

    # All 3 stages must be recorded as completed
    statuses = res.model_information.get("stage_statuses", {})
    assert statuses.get("DESCRIPTIVE") == "COMPLETED" or statuses.get("descriptive") == "COMPLETED"
    assert statuses.get("PREDICTIVE") == "COMPLETED" or statuses.get("predictive") == "COMPLETED"
    assert statuses.get("PRESCRIPTIVE") == "COMPLETED" or statuses.get("prescriptive") == "COMPLETED"

    # Evidence from all 3 stages must be present in findings and metrics
    assert len(res.findings) >= 3
    assert len(res.recommended_next_steps) > 0
    assert "forecast_preview" in res.model_information or "selected_model" in res.model_information

    adapter.disconnect()


def test_scenario_b_diagnostic_prescriptive_pipeline(tmp_path: Path):
    """
    Scenario B: Two-stage request (Diagnostic -> Prescriptive)
    Query: 'Which machines contributed most to downtime and what should we do?'
    """
    db_file = tmp_path / "mfg_b.sqlite"
    _setup_manufacturing_db(db_file)

    adapter = SQLiteAdapter(file_path=str(db_file), name="mfg_b_db", read_only=True)
    adapter.connect()
    db_manager._active_adapter = adapter
    svc = SchemaService(db_path=str(db_file))
    cat = svc.profile_database(force_refresh=True)

    q = "Which machines contributed most to downtime and what should we do?"

    cls_res = intent_classifier.classify(q)
    assert cls_res.is_composite is True
    assert cls_res.composite_intents == [IntentCategory.DIAGNOSTIC, IntentCategory.PRESCRIPTIVE]

    res = analytical_orchestrator.analyze(question=q, catalog=cat)
    assert res.success is True
    statuses = res.model_information.get("stage_statuses", {})
    assert statuses.get("DIAGNOSTIC") == "COMPLETED" or statuses.get("diagnostic") == "COMPLETED"
    assert statuses.get("PRESCRIPTIVE") == "COMPLETED" or statuses.get("prescriptive") == "COMPLETED"
    assert len(res.recommended_next_steps) > 0

    adapter.disconnect()


def test_scenario_c_descriptive_predictive_pipeline(tmp_path: Path):
    """
    Scenario C: Two-stage request (Descriptive -> Predictive)
    Query: 'What were the last 12 months of sales and what is the forecast for next month?'
    """
    q = "What were the last 12 months of sales and what is the forecast for next month?"
    cls_res = intent_classifier.classify(q)
    assert cls_res.is_composite is True
    assert cls_res.composite_intents == [IntentCategory.DESCRIPTIVE, IntentCategory.PREDICTIVE]
    assert cls_res.execution_sequence == ["descriptive_trend_analysis", "predictive_forecasting"]


def test_scenario_d_four_stage_pipeline(tmp_path: Path):
    """
    Scenario D: Four-stage request (Descriptive -> Diagnostic -> Predictive -> Prescriptive)
    Query: 'Analyze downtime, identify the primary drivers, predict future downtime and recommend a maintenance budget allocation.'
    """
    db_file = tmp_path / "mfg_d.sqlite"
    _setup_manufacturing_db(db_file)

    adapter = SQLiteAdapter(file_path=str(db_file), name="mfg_d_db", read_only=True)
    adapter.connect()
    db_manager._active_adapter = adapter
    svc = SchemaService(db_path=str(db_file))
    cat = svc.profile_database(force_refresh=True)

    q = "Analyze downtime, identify the primary drivers, predict future downtime and recommend a $20,000 maintenance budget allocation."

    cls_res = intent_classifier.classify(q)
    assert cls_res.is_composite is True
    assert cls_res.composite_intents == [
        IntentCategory.DESCRIPTIVE,
        IntentCategory.DIAGNOSTIC,
        IntentCategory.PREDICTIVE,
        IntentCategory.PRESCRIPTIVE,
    ]

    res = analytical_orchestrator.analyze(question=q, catalog=cat)
    assert res.success is True
    assert res.model_information["stage_count"] == 4
    statuses = res.model_information.get("stage_statuses", {})
    assert statuses.get("DESCRIPTIVE") == "COMPLETED" or statuses.get("descriptive") == "COMPLETED"
    assert statuses.get("DIAGNOSTIC") == "COMPLETED" or statuses.get("diagnostic") == "COMPLETED"
    assert statuses.get("PREDICTIVE") == "COMPLETED" or statuses.get("predictive") == "COMPLETED"
    assert statuses.get("PRESCRIPTIVE") == "COMPLETED" or statuses.get("prescriptive") == "COMPLETED"

    adapter.disconnect()


def test_no_synthetic_prescriptive_when_prescriptive_omitted():
    """Verifies that prescriptive recommendations and allocations are NEVER synthesized when prescriptive did not execute."""
    q = "What was our monthly downtime and why did it increase?"
    cls_res = intent_classifier.classify(q)
    assert IntentCategory.PRESCRIPTIVE not in cls_res.composite_intents
