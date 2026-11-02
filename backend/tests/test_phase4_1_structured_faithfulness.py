"""
backend/tests/test_phase4_1_structured_faithfulness.py
Unit tests for Structured Claim Faithfulness and Evidence Validation.
Verifies:
1. Individual factual claims are extracted into StructuredClaim objects.
2. Unhedged causal statements ("proven root cause", "proves that") are intercepted and flagged.
3. Verified claims are bound to specific ground-truth metrics.
"""

import pytest

from backend.app.analysis.contracts_v2 import ClaimType
from backend.app.analysis.faithfulness import faithfulness_validator


def test_structured_claim_extraction_and_evidence_binding():
    """Verifies numerical and directional claims are bound to evidence references."""
    narrative = "Revenue increased by 15.0% to $1,500.00 with total volume of 50 orders."
    metrics = {
        "delta_percentage": 15.0,
        "revenue": 1500.0,
        "volume": 50,
    }

    report = faithfulness_validator.validate_narrative(narrative, metrics)

    assert report.is_faithful is True
    assert report.total_claims_checked >= 3
    assert len(report.structured_claims) >= 3

    # Check claim types
    types = [c.claim_type for c in report.structured_claims]
    assert ClaimType.DIRECTIONAL in types
    assert ClaimType.NUMERICAL in types

    # Check evidence binding on all verified claims
    for c in report.structured_claims:
        assert c.verified is True
        assert c.evidence_reference is not None


def test_unhedged_causal_claim_interception():
    """
    Verifies that unhedged causal assertions (e.g. 'proven root cause')
    are flagged as unverified because observational data cannot establish counterfactual causality.
    """
    narrative = "Analysis proves that marketing spend was the proven root cause of the revenue increase."
    metrics = {"delta_percentage": 10.0, "primary_driver": "Marketing"}

    report = faithfulness_validator.validate_narrative(narrative, metrics)

    assert report.is_faithful is False
    assert len(report.discrepancies) > 0

    causal_claims = [c for c in report.structured_claims if c.claim_type == ClaimType.CAUSAL]
    assert len(causal_claims) > 0
    assert causal_claims[0].verified is False
    assert "counterfactual causality" in (causal_claims[0].discrepancy or "")


def test_driver_contribution_claim_verification():
    """Verifies that driver contribution claims match computed primary_driver metric."""
    narrative = "Cardiology was the primary driver of increased hospital treatment costs."
    metrics = {"primary_driver": "Cardiology", "cost_delta": 700.0}

    report = faithfulness_validator.validate_narrative(narrative, metrics)

    driver_claims = [c for c in report.structured_claims if c.claim_type == ClaimType.DRIVER_CONTRIBUTION]
    assert len(driver_claims) == 1
    assert driver_claims[0].verified is True
    assert "computed_metrics.primary_driver=Cardiology" in driver_claims[0].evidence_reference

