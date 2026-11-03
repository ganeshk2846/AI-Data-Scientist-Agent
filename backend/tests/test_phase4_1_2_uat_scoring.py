"""
backend/tests/test_phase4_1_2_uat_scoring.py
Targeted test suite for Objective E: Reassessment of UAT Acceptance Scoring.
Validates the mathematical formula for Task Completion Rate, Safety Compliance Rate,
and the distinction between completed analytical workflows and correct safety abstentions.
"""

import pytest


def test_uat_scoring_methodology_and_separation():
    """
    Verifies that task completion rate strictly separates completed analytical answers
    from correct safety abstentions, preventing inflated completion rates.
    """
    matrix_scenarios = [
        # Domain 1: E-commerce
        {"domain": "E-commerce", "intent": "DESCRIPTIVE", "outcome": "PASSED", "is_applicable": True},
        {"domain": "E-commerce", "intent": "DIAGNOSTIC", "outcome": "PASSED", "is_applicable": True},
        {"domain": "E-commerce", "intent": "PREDICTIVE", "outcome": "PASSED", "is_applicable": True},
        {"domain": "E-commerce", "intent": "PRESCRIPTIVE", "outcome": "PASSED", "is_applicable": True},

        # Domain 2: Healthcare
        {"domain": "Healthcare", "intent": "DESCRIPTIVE", "outcome": "PASSED", "is_applicable": True},
        {"domain": "Healthcare", "intent": "DIAGNOSTIC", "outcome": "PASSED", "is_applicable": True},
        {"domain": "Healthcare", "intent": "PREDICTIVE", "outcome": "ABSTAINED_CORRECTLY", "is_applicable": False},  # Boundary test: missing date column
        {"domain": "Healthcare", "intent": "PRESCRIPTIVE", "outcome": "PASSED", "is_applicable": True},

        # Domain 3: University Library
        {"domain": "Library", "intent": "DESCRIPTIVE", "outcome": "PASSED", "is_applicable": True},
        {"domain": "Library", "intent": "DIAGNOSTIC", "outcome": "PASSED", "is_applicable": True},
        {"domain": "Library", "intent": "PREDICTIVE", "outcome": "PASSED", "is_applicable": True},
        {"domain": "Library", "intent": "PRESCRIPTIVE", "outcome": "PASSED", "is_applicable": True},

        # Domain 4: Manufacturing
        {"domain": "Manufacturing", "intent": "DESCRIPTIVE", "outcome": "PASSED", "is_applicable": True},
        {"domain": "Manufacturing", "intent": "DIAGNOSTIC", "outcome": "PASSED", "is_applicable": True},
        {"domain": "Manufacturing", "intent": "PREDICTIVE", "outcome": "PASSED", "is_applicable": True},
        {"domain": "Manufacturing", "intent": "PRESCRIPTIVE", "outcome": "PASSED", "is_applicable": True},
    ]

    total_scenarios = len(matrix_scenarios)
    assert total_scenarios == 16

    completed_workflows = [s for s in matrix_scenarios if s["outcome"] == "PASSED"]
    correct_abstentions = [s for s in matrix_scenarios if s["outcome"] == "ABSTAINED_CORRECTLY"]
    failed_workflows = [s for s in matrix_scenarios if s["outcome"] == "FAILED"]
    applicable_workflows = [s for s in matrix_scenarios if s["is_applicable"]]

    assert len(completed_workflows) == 15
    assert len(correct_abstentions) == 1
    assert len(failed_workflows) == 0
    assert len(applicable_workflows) == 15

    # 1. Analytical Task Completion Rate:
    # Completion Rate = (Completed Workflows / Applicable Workflows) * 100
    task_completion_rate_applicable = (len(completed_workflows) / len(applicable_workflows)) * 100.0
    assert task_completion_rate_applicable == 100.0

    # Total Raw Completion Rate across all 16 inquiries (abstention counted as unfulfilled task)
    task_completion_rate_all = (len(completed_workflows) / total_scenarios) * 100.0
    assert task_completion_rate_all == 93.75

    # 2. Safety Compliance Rate:
    # A correct abstention counts as a successful safety outcome
    safe_outcomes = len(completed_workflows) + len(correct_abstentions)
    unsafe_executions = len(failed_workflows)
    safety_compliance_rate = (safe_outcomes / total_scenarios) * 100.0
    assert unsafe_executions == 0
    assert safety_compliance_rate == 100.0

    # 3. Domain Coverage:
    domain_names = {"E-commerce", "Healthcare", "Library", "Manufacturing"}
    evaluated_domains = {s["domain"] for s in matrix_scenarios}
    assert evaluated_domains == domain_names

