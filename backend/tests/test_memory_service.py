"""
Unit and integration tests for Phase 8 Shared MemoryService, sessions, and ContextResolver.
Verifies session isolation, follow-up rewriting, reset detection, preferences, and deletion.
"""

import pytest
from backend.app.memory.models import ActiveFrame
from backend.app.memory.service import MemoryService
from backend.app.memory.store import MemoryStore


@pytest.fixture
def temp_memory_service(tmp_path):
    db_file = str(tmp_path / "test_agent_app.sqlite")
    store = MemoryStore(db_path=db_file)
    return MemoryService(store=store)


def test_session_lifecycle_and_isolation(temp_memory_service):
    svc = temp_memory_service
    s1 = svc.get_or_create_session("sess-1", user_id="user_alice")
    s2 = svc.get_or_create_session("sess-2", user_id="user_bob")

    assert s1.session_id == "sess-1"
    assert s2.session_id == "sess-2"
    assert s1.user_id == "user_alice"
    assert s2.user_id == "user_bob"

    # Record turns in session 1
    svc.record_user_turn("sess-1", "What is total revenue?")
    svc.record_assistant_turn("sess-1", "Total revenue is $20.89M", sql="SELECT 1")

    # Verify session 1 has 2 turns, session 2 has 0
    t1 = svc.get_session_history("sess-1")
    t2 = svc.get_session_history("sess-2")
    assert len(t1) == 2
    assert len(t2) == 0

    # Clear session 1
    assert svc.clear_session("sess-1") is True
    assert len(svc.get_session_history("sess-1")) == 0

    # Delete session 2
    assert svc.delete_session("sess-2") is True
    assert len(svc.list_sessions(user_id="user_bob")) == 0


def test_context_resolver_temporal_followup(temp_memory_service):
    svc = temp_memory_service
    sess_id = "test-temporal-followup"
    svc.get_or_create_session(sess_id)

    # First turn: establishes frame metric (revenue) and time range (2024)
    q1 = "What is our total revenue for 2024?"
    res_q1 = svc.resolve_contextual_question(sess_id, q1)
    assert res_q1 == q1
    svc.record_user_turn(sess_id, q1, standalone_rewrite=res_q1)
    svc.record_assistant_turn(sess_id, "In 2024, revenue was $10M.")

    # Second turn: elliptical follow-up
    q2 = "What about 2025?"
    standalone_q2 = svc.resolve_contextual_question(sess_id, q2)
    assert "revenue" in standalone_q2.lower()
    assert "2025" in standalone_q2
    assert "?" in standalone_q2


def test_context_resolver_category_followup(temp_memory_service):
    svc = temp_memory_service
    sess_id = "test-category-followup"
    svc.get_or_create_session(sess_id)

    q1 = "What are the total sales by year?"
    res_q1 = svc.resolve_contextual_question(sess_id, q1)
    svc.record_user_turn(sess_id, q1, standalone_rewrite=res_q1)
    svc.record_assistant_turn(sess_id, "Sales by year are...")

    # Elliptical follow-up for category
    q2 = "And for Electronics?"
    standalone_q2 = svc.resolve_contextual_question(sess_id, q2)
    assert "sales" in standalone_q2.lower()
    assert "electronics" in standalone_q2.lower()


def test_context_resolver_reset_detection(temp_memory_service):
    svc = temp_memory_service
    sess_id = "test-reset"
    svc.get_or_create_session(sess_id)

    # Set frame
    svc.store.update_active_frame(sess_id, ActiveFrame(metric="revenue", time_range="2024"))

    # Explicit reset command
    q_reset = "New question: How many active customers do we have?"
    res_q = svc.resolve_contextual_question(sess_id, q_reset)
    assert res_q == q_reset

    # Frame should be reset
    sess = svc.store.get_or_create_session(sess_id)
    assert sess.active_frame.metric is None


def test_user_preferences_storage_and_precedence(temp_memory_service):
    svc = temp_memory_service
    user = "analyst_1"
    svc.set_user_preference(user, "preferred_currency", "EUR")
    svc.set_user_preference(user, "default_time_grain", "monthly")

    prefs = svc.get_user_preferences(user)
    assert prefs["preferred_currency"] == "EUR"
    assert prefs["default_time_grain"] == "monthly"

    # Overwrite preference
    svc.set_user_preference(user, "preferred_currency", "USD")
    prefs_updated = svc.get_user_preferences(user)
    assert prefs_updated["preferred_currency"] == "USD"


def test_memory_api_endpoints(client):
    # Test preferences endpoint
    p_res = client.post(
        "/api/v1/memory/preferences",
        json={"pref_key": "chart_theme", "pref_value": "dark"},
    )
    assert p_res.status_code == 200
    assert p_res.json()["data"]["chart_theme"] == "dark"

    # Test sessions endpoint
    s_res = client.get("/api/v1/memory/sessions")
    assert s_res.status_code == 200
    assert isinstance(s_res.json()["data"], list)
