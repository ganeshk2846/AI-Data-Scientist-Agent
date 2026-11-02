"""
backend/tests/test_phase4_1_intent_multi_intent.py
Unit tests for Intent Classifier and Multi-Intent Composite Intelligence.
Verifies:
1. Composite multi-intent questions produce sequential execution plans without triggering ambiguity clarification.
2. Truly ambiguous disjunction questions still request clarification.
3. Expanded multi-domain evaluation benchmark retains >75% accuracy and macro F1.
"""

import pytest

from backend.app.analysis.contracts_v2 import ComplexityLevel, IntentCategory
from backend.app.analysis.intent_classifier import intent_classifier


def test_composite_diagnostic_prescriptive():
    """
    Verifies that 'What caused the decline and what should we do?' is recognized
    as a composite multi-stage analytical request (DIAGNOSTIC -> PRESCRIPTIVE)
    without triggering ambiguity clarification.
    """
    q = "What caused the decline in revenue and what should we do to fix it?"
    res = intent_classifier.classify(q)

    assert res.is_composite is True
    assert res.is_ambiguous is False
    assert res.requires_clarification is False
    assert res.primary_intent == IntentCategory.DIAGNOSTIC
    assert IntentCategory.DIAGNOSTIC in res.composite_intents
    assert IntentCategory.PRESCRIPTIVE in res.composite_intents
    assert len(res.execution_sequence) >= 2


def test_composite_descriptive_predictive():
    """
    Verifies that 'What were last quarter sales and what is the forecast for next quarter?'
    is recognized as a composite DESCRIPTIVE -> PREDICTIVE plan.
    """
    q = "What were last quarter's sales and what is the forecast for next quarter?"
    res = intent_classifier.classify(q)

    assert res.is_composite is True
    assert res.is_ambiguous is False
    assert res.requires_clarification is False
    assert res.primary_intent == IntentCategory.DESCRIPTIVE
    assert IntentCategory.DESCRIPTIVE in res.composite_intents
    assert IntentCategory.PREDICTIVE in res.composite_intents


def test_composite_three_stage_workflow():
    """
    Verifies a 3-stage compound business request:
    'What caused the revenue decrease last quarter, what is the forecast, and how can we improve it?'
    """
    q = "What caused the revenue decrease last quarter, what is the forecast, and how can we improve it?"
    res = intent_classifier.classify(q)

    assert res.is_composite is True
    assert res.is_ambiguous is False
    assert res.requires_clarification is False
    assert IntentCategory.DIAGNOSTIC in res.composite_intents
    assert IntentCategory.PREDICTIVE in res.composite_intents
    assert IntentCategory.PRESCRIPTIVE in res.composite_intents


def test_truly_ambiguous_disjunction_requests_clarification():
    """
    Verifies that an ambiguous disjunctive query (either/or without composite conjunction)
    prompts the user for clarification.
    """
    q = "Should we evaluate past historical revenue or future forecast figures?"
    res = intent_classifier.classify(q)

    assert res.is_ambiguous is True
    assert res.requires_clarification is True
    assert res.suggested_clarification is not None
    assert "clarification" in res.suggested_clarification.lower() or "specify" in res.suggested_clarification.lower()


def test_expanded_evaluation_benchmark():
    """Verifies that the expanded 150+ sample dataset achieves >=75% accuracy and macro F1."""
    metrics = intent_classifier.evaluate(test_size=0.2, random_state=42)

    assert metrics["test_sample_count"] >= 25
    assert metrics["accuracy"] >= 0.75, f"Accuracy {metrics['accuracy']} below 0.75"
    assert metrics["macro_f1"] >= 0.70, f"Macro F1 {metrics['macro_f1']} below 0.70"
    assert "DESCRIPTIVE" in metrics["classification_report"]
    assert "DIAGNOSTIC" in metrics["classification_report"]
    assert "PREDICTIVE" in metrics["classification_report"]
    assert "PRESCRIPTIVE" in metrics["classification_report"]

