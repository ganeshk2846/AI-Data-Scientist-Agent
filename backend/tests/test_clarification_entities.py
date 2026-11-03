"""
Tests for Structured Entity Extraction and Multi-Round Clarification.
"""

import pytest
from backend.app.agents.entity_extractor import entity_extractor
from backend.app.orchestration.supervisor import agentic_supervisor


def test_structured_entity_extraction_slots():
    q = "What was our total revenue in the North region for Electronics in 2024?"
    rep = entity_extractor.extract(q)
    assert "revenue" in rep.metrics
    assert rep.region == "North"
    assert rep.product == "Electronics"
    assert rep.date_range is not None
    assert rep.date_range["start_date"] == "2024-01-01"
    assert rep.clarification_required is False


def test_clarification_single_question_generation():
    rep = entity_extractor.extract("compare revenue")
    assert rep.clarification_required is True
    assert rep.clarification_question is not None
    assert "How would you like to compare revenue?" in rep.clarification_question
    assert len(rep.clarification_options) >= 2


def test_contextual_followup_resolution():
    rep1 = entity_extractor.extract("compare revenue")
    assert rep1.clarification_required is True

    # User answers "by region"
    rep2 = entity_extractor.resolve_followup(rep1, "by region")
    assert rep2.clarification_required is False
    assert "region" in rep2.dimensions
    assert "geographic regions" in rep2.resolved_query or "region" in rep2.resolved_query
    assert rep2.turn_count == 1


def test_clarification_two_round_cap():
    # When turn_count >= 2, clarification must stop and default transparent assumptions applied
    rep_capped = entity_extractor.extract("compare revenue", turn_count=2)
    assert rep_capped.clarification_required is False
    assert len(rep_capped.assumptions) > 0
    assert any("default" in a.lower() for a in rep_capped.assumptions)


def test_supervisor_interactive_clarification_and_followup():
    sid = "test_clarif_round_session"
    agentic_supervisor.clear_session(sid)

    # Turn 1: ambiguous inquiry
    res1 = agentic_supervisor.supervise("compare revenue", session_id=sid)
    assert res1.clarification_needed is True
    assert len(res1.clarification_options) > 0

    # Turn 2: user specifies resolution
    res2 = agentic_supervisor.supervise("by geographic region", session_id=sid)
    assert res2.clarification_needed is False
    assert res2.success is True
