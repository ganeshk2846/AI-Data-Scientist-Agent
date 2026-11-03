"""
backend/tests/test_phase4_1_2_budget_parser.py
Targeted test suite for DEF-01: Currency and Budget Suffix Parsing.
Verifies that natural words beginning with 'k', 'm', or 'b' (e.g. 'marketing', 'month', 'maintenance')
are never incorrectly parsed as currency multipliers.
"""

import pytest
from backend.app.analysis.prescriptive_engine import prescriptive_engine


def test_mandatory_budget_parsing_cases():
    """Verifies all mandatory test cases from Phase 4.1.2 specification."""
    test_cases = [
        ("$25,000 marketing budget", 25000.0),
        ("$25k marketing budget", 25000.0),
        ("$25m marketing budget", 25000000.0),
        ("$50,000 budget", 50000.0),
        ("$1.5k allocation", 1500.0),
        ("$1.5m investment", 1500000.0),
        ("$2b budget", 2000000000.0),
        ("$25,000.50 budget", 25000.50),
    ]

    for query, expected in test_cases:
        actual = prescriptive_engine._extract_budget_from_query(query)
        assert actual == expected, f"Failed for '{query}': expected {expected}, got {actual}"


def test_natural_words_following_amount():
    """Verifies that words starting with k/m/b immediately following numbers are not multipliers."""
    cases = [
        ("Allocate $25,000 marketing budget across channels", 25000.0),
        ("How to allocate $10,000 monthly spend across departments?", 10000.0),
        ("Allocate $30,000 maintenance budget across machines", 30000.0),
        ("Allocate $5,000 borrowing budget across projects", 5000.0),
        ("What if we invest $25000 marketing budget?", 25000.0),
        ("We have a $100000 backend infrastructure plan", 100000.0),
        ("Deploy $75,000 machine learning pipeline", 75000.0),
    ]

    for query, expected in cases:
        actual = prescriptive_engine._extract_budget_from_query(query)
        assert actual == expected, f"Failed for '{query}': expected {expected}, got {actual}"


def test_uppercase_and_word_multipliers():
    """Verifies uppercase suffixes (K, M, B) and full word multipliers (thousand, million, billion)."""
    cases = [
        ("$25K marketing budget", 25000.0),
        ("$25M capital expenditure", 25000000.0),
        ("$1.5B global reserve", 1500000000.0),
        ("$50 thousand allocation", 50000.0),
        ("$10 million investment", 10000000.0),
        ("$2 billion enterprise budget", 2000000000.0),
    ]

    for query, expected in cases:
        actual = prescriptive_engine._extract_budget_from_query(query)
        assert actual == expected, f"Failed for '{query}': expected {expected}, got {actual}"


def test_non_dollar_budget_declarations():
    """Verifies secondary pattern where budget is explicitly declared without '$'."""
    cases = [
        ("allocate budget of 50000 across categories", 50000.0),
        ("capital allocation of 1.5m for expansion", 1500000.0),
        ("resource spend of 25k across channels", 25000.0),
        ("planned spend of 200000 for equipment", 200000.0),
    ]

    for query, expected in cases:
        actual = prescriptive_engine._extract_budget_from_query(query)
        assert actual == expected, f"Failed for '{query}': expected {expected}, got {actual}"


def test_missing_or_invalid_amounts():
    """Verifies safe handling of queries with no budget or invalid expressions."""
    cases = [
        "What happened to sales last month?",
        "Why did revenue drop in July?",
        "Forecast sales for next quarter",
        "How should we allocate our resources?",
        "",
        "No money mentioned here",
    ]

    for query in cases:
        actual = prescriptive_engine._extract_budget_from_query(query)
        assert actual is None, f"Expected None for '{query}', got {actual}"

