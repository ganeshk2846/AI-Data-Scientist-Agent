"""
backend/tests/test_phase4_faithfulness.py
Unit tests for Result Faithfulness and Validation Engine.
"""

import pytest
from backend.app.analysis.faithfulness import faithfulness_validator


def test_faithfulness_passes_for_consistent_narrative():
    """Verifies faithful narrative matching computed ground truth."""
    gt_metrics = {
        "delta_percentage": -12.5,
        "delta_absolute": -500.0,
        "baseline_value": 4000.0,
        "simulated_value": 3500.0,
    }
    narrative = "Revenue decreased by 12.5% resulting in a net drop of $500.00 from baseline $4,000.00 to $3,500.00."

    report = faithfulness_validator.validate_narrative(narrative, gt_metrics)

    assert report.is_faithful is True
    assert len(report.discrepancies) == 0
    assert report.confidence_discount == 0.0


def test_faithfulness_catches_direction_contradiction():
    """Verifies that asserting an increase when ground truth is negative is caught as a contradiction."""
    gt_metrics = {
        "delta_percentage": -15.0,
        "total_sales": 10000.0,
    }
    contradictory_narrative = "Sales experienced a growth of 15.0% reached $10,000."

    report = faithfulness_validator.validate_narrative(contradictory_narrative, gt_metrics)

    assert report.is_faithful is False
    assert any("Contradiction" in d for d in report.discrepancies)
    assert report.confidence_discount >= 0.5


def test_faithfulness_catches_fabricated_numerical_claims():
    """Verifies that reporting fabricated numbers not found in ground truth is flagged."""
    gt_metrics = {
        "mean_value": 50.0,
        "total_count": 100,
    }
    hallucinated_narrative = "The average ticket size was 88.5% with a profit margin of $4,500."

    report = faithfulness_validator.validate_narrative(hallucinated_narrative, gt_metrics)

    assert len(report.discrepancies) > 0
    assert any("88.5%" in d for d in report.discrepancies)

