"""
backend/tests/test_phase4_intent_classifier.py
Unit & Evaluation Tests for Phase 4 Intent and Analytical Complexity Classifier.
"""

import pytest
from backend.app.analysis.contracts_v2 import ComplexityLevel, IntentCategory
from backend.app.analysis.intent_classifier import intent_classifier


def test_intent_classification_cross_domain():
    """Verifies that queries across 4 distinct domains are mapped to the correct analytical intent."""
    test_cases = [
        # Descriptive
        ("What was our monthly gross revenue for 2025?", IntentCategory.DESCRIPTIVE),
        ("Show total hospital admissions by department", IntentCategory.DESCRIPTIVE),
        ("List the top 5 most borrowed books this semester", IntentCategory.DESCRIPTIVE),
        ("What was average machine downtime yesterday?", IntentCategory.DESCRIPTIVE),

        # Diagnostic
        ("Why did customer returns increase sharply in Q3?", IntentCategory.DIAGNOSTIC),
        ("What caused the sudden spike in ICU treatment costs?", IntentCategory.DIAGNOSTIC),
        ("Why are overdue book loans higher among seniors?", IntentCategory.DIAGNOSTIC),
        ("Detect anomalies in machine operating temperatures", IntentCategory.DIAGNOSTIC),

        # Predictive
        ("Forecast sales for the next two quarters", IntentCategory.PREDICTIVE),
        ("What will hospital bed occupancy likely be next week?", IntentCategory.PREDICTIVE),
        ("Predict book borrowing demand for next semester", IntentCategory.PREDICTIVE),
        ("Project factory energy consumption for next month", IntentCategory.PREDICTIVE),

        # Prescriptive
        ("How should we allocate our $50k marketing budget across channels?", IntentCategory.PRESCRIPTIVE),
        ("What if we increase retail price by 10%, how does revenue change?", IntentCategory.PRESCRIPTIVE),
        ("Recommend optimal reorder quantities for library books", IntentCategory.PRESCRIPTIVE),
        ("Optimize preventive maintenance schedule to minimize downtime", IntentCategory.PRESCRIPTIVE),

        # SQL Lookup
        ("Find customer with email test@example.com", IntentCategory.SQL_LOOKUP),
        ("What is the phone number for patient ID 1042?", IntentCategory.SQL_LOOKUP),
        ("Look up ISBN of 'Clean Code'", IntentCategory.SQL_LOOKUP),
    ]

    for question, expected_intent in test_cases:
        res = intent_classifier.classify(question)
        assert res.primary_intent == expected_intent, f"Failed for '{question}': expected {expected_intent}, got {res.primary_intent}"
        assert res.confidence_score > 0.30


def test_complexity_grading():
    """Verifies that complexity levels correspond to question analytical depth."""
    simple_q = "List the top 10 customers by spend"
    advanced_q = "Forecast patient admissions for the upcoming winter season"

    res_simple = intent_classifier.classify(simple_q)
    res_advanced = intent_classifier.classify(advanced_q)

    assert res_simple.complexity in [ComplexityLevel.SIMPLE, ComplexityLevel.MODERATE]
    assert res_advanced.complexity == ComplexityLevel.ADVANCED


def test_ambiguity_detection_and_clarification():
    """Verifies multi-intent conflict triggers clarification request."""
    ambiguous_q = "What was our total revenue last year and what will our sales forecast be for next year?"
    res = intent_classifier.classify(ambiguous_q)

    assert res.is_ambiguous is True
    assert res.requires_clarification is True
    assert res.suggested_clarification is not None
    assert "historical" in res.suggested_clarification.lower()


def test_evaluation_benchmark_metrics():
    """Evaluates classifier on a stratified test split and benchmarks accuracy & macro F1."""
    metrics = intent_classifier.evaluate(test_size=0.2, random_state=42)

    assert metrics["test_sample_count"] > 15
    assert metrics["accuracy"] >= 0.70, f"Accuracy {metrics['accuracy']} below 0.70 threshold"
    assert metrics["macro_f1"] >= 0.70, f"Macro F1 {metrics['macro_f1']} below 0.70 threshold"
    assert "DESCRIPTIVE" in metrics["classification_report"]
    assert "DIAGNOSTIC" in metrics["classification_report"]

