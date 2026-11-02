"""
backend/app/analysis/faithfulness.py
Result Faithfulness and Validation Engine for Phase 4.
Cross-examines LLM-generated narrative insights against ground-truth deterministic computations,
preventing hallucinated percentages, contradicted delta directions, and fabricated numerical metrics.
"""

import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.analysis.contracts_v2 import FaithfulnessReport
from backend.app.core.logging import logger


class FaithfulnessValidator:
    """
    Validates narrative claims against ground-truth computed metrics and query results.
    """

    def validate_narrative(
        self,
        narrative: str,
        ground_truth_metrics: Dict[str, Any],
        ground_truth_data: Optional[List[Dict[str, Any]]] = None,
    ) -> FaithfulnessReport:
        """
        Scans narrative for quantitative claims (percentages, dollar amounts, direction verbs)
        and verifies consistency with computed facts.
        """
        if not narrative or not ground_truth_metrics:
            return FaithfulnessReport(
                is_faithful=True,
                total_claims_checked=0,
                verified_claims=0,
                discrepancies=[],
                confidence_discount=0.0,
            )

        discrepancies: List[str] = []
        verified_count = 0
        total_claims = 0

        # Extract numerical values from ground truth
        gt_numbers: Set[float] = set()
        for k, v in ground_truth_metrics.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and not math.isnan(v):
                gt_numbers.add(round(float(v), 2))
                gt_numbers.add(round(float(v), 1))
                gt_numbers.add(round(float(v), 0))
                # Also check percentage variations (e.g., 0.15 vs 15.0%)
                gt_numbers.add(round(float(v) * 100.0, 1))

        # 1. Direction Consistency Check
        # Check if ground truth has an overall delta or growth rate
        delta_val = None
        for key in ["delta_percentage", "delta_pct", "growth_rate_pct", "delta_absolute", "delta"]:
            if key in ground_truth_metrics and isinstance(ground_truth_metrics[key], (int, float)):
                delta_val = float(ground_truth_metrics[key])
                break

        narrative_lower = narrative.lower()

        if delta_val is not None:
            total_claims += 1
            has_increase_words = any(w in narrative_lower for w in ["increased by", "increase of", "growth of", "rose by", "up by", "grew by"])
            has_decrease_words = any(w in narrative_lower for w in ["decreased by", "decrease of", "decline of", "fell by", "down by", "dropped by"])

            if delta_val < 0 and has_increase_words and not has_decrease_words:
                discrepancies.append(
                    f"Contradiction: Narrative reported an increase, but ground truth delta is negative ({delta_val}%)."
                )
            elif delta_val > 0 and has_decrease_words and not has_increase_words:
                discrepancies.append(
                    f"Contradiction: Narrative reported a decrease, but ground truth delta is positive (+{delta_val}%)."
                )
            else:
                verified_count += 1

        # 2. Percentage Claims Verification
        # Extract patterns like "15%", "15.4%", "-20.0%"
        pct_matches = re.findall(r"([+-]?\d+(?:\.\d+)?)\s*%", narrative)
        for pct_str in pct_matches:
            total_claims += 1
            try:
                val = float(pct_str)
                abs_val = abs(val)

                # Match against ground truth numbers or percentages
                matched = any(
                    math.isclose(abs_val, abs(g), rel_tol=0.05, abs_tol=0.5)
                    for g in gt_numbers
                )
                if matched:
                    verified_count += 1
                else:
                    # Minor rounding or unmapped claim
                    discrepancies.append(f"Unverified percentage claim in narrative: {pct_str}% not found in computed metrics.")
            except ValueError:
                pass

        # 3. Currency / Large Number Verification
        currency_matches = re.findall(r"\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)", narrative)
        for curr_str in currency_matches:
            total_claims += 1
            try:
                val = float(curr_str.replace(",", ""))
                matched = any(
                    math.isclose(val, abs(g), rel_tol=0.05, abs_tol=1.0)
                    for g in gt_numbers
                )
                if matched:
                    verified_count += 1
                else:
                    discrepancies.append(f"Unverified monetary claim in narrative: ${curr_str} not supported by computation.")
            except ValueError:
                pass

        # Calculate faithfulness score
        is_faithful = len([d for d in discrepancies if "Contradiction" in d]) == 0
        conf_discount = 0.0
        if not is_faithful:
            conf_discount = 0.5
        elif discrepancies:
            conf_discount = min(0.3, len(discrepancies) * 0.1)

        return FaithfulnessReport(
            is_faithful=is_faithful,
            total_claims_checked=total_claims,
            verified_claims=verified_count,
            discrepancies=discrepancies,
            confidence_discount=round(conf_discount, 2),
        )


faithfulness_validator = FaithfulnessValidator()

