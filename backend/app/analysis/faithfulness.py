"""
backend/app/analysis/faithfulness.py
Result Faithfulness and Validation Engine for Phase 4.
Cross-examines LLM-generated narrative insights against ground-truth deterministic computations,
preventing hallucinated percentages, contradicted delta directions, and fabricated numerical metrics.
"""

import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.analysis.contracts_v2 import ClaimType, FaithfulnessReport, StructuredClaim
from backend.app.core.logging import logger


class FaithfulnessValidator:
    """
    Validates narrative claims against ground-truth computed metrics and query results,
    linking individual factual statements to structured empirical evidence.
    """

    def validate_narrative(
        self,
        narrative: str,
        ground_truth_metrics: Dict[str, Any],
        ground_truth_data: Optional[List[Dict[str, Any]]] = None,
    ) -> FaithfulnessReport:
        """
        Scans narrative for quantitative, directional, driver, and causal claims,
        verifying empirical consistency and generating structured claim evidence bindings.
        """
        if not narrative or not ground_truth_metrics:
            return FaithfulnessReport(
                is_faithful=True,
                total_claims_checked=0,
                verified_claims=0,
                discrepancies=[],
                confidence_discount=0.0,
                structured_claims=[],
            )

        discrepancies: List[str] = []
        structured_claims: List[StructuredClaim] = []
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

            dir_statement = f"Directional trend claim: delta is {delta_val}%"
            if delta_val < 0 and has_increase_words and not has_decrease_words:
                disc = f"Contradiction: Narrative reported an increase, but ground truth delta is negative ({delta_val}%)."
                discrepancies.append(disc)
                structured_claims.append(StructuredClaim(
                    claim_id=f"claim_dir_{total_claims}",
                    claim_type=ClaimType.DIRECTIONAL,
                    statement=dir_statement,
                    verified=False,
                    evidence_reference=f"computed_metrics.delta={delta_val}",
                    discrepancy=disc,
                ))
            elif delta_val > 0 and has_decrease_words and not has_increase_words:
                disc = f"Contradiction: Narrative reported a decrease, but ground truth delta is positive (+{delta_val}%)."
                discrepancies.append(disc)
                structured_claims.append(StructuredClaim(
                    claim_id=f"claim_dir_{total_claims}",
                    claim_type=ClaimType.DIRECTIONAL,
                    statement=dir_statement,
                    verified=False,
                    evidence_reference=f"computed_metrics.delta={delta_val}",
                    discrepancy=disc,
                ))
            else:
                verified_count += 1
                structured_claims.append(StructuredClaim(
                    claim_id=f"claim_dir_{total_claims}",
                    claim_type=ClaimType.DIRECTIONAL,
                    statement=dir_statement,
                    verified=True,
                    evidence_reference=f"computed_metrics.delta={delta_val}",
                ))

        # 2. Percentage Claims Verification
        pct_matches = re.findall(r"([+-]?\d+(?:\.\d+)?)\s*%", narrative)
        for idx, pct_str in enumerate(pct_matches, start=1):
            total_claims += 1
            try:
                val = float(pct_str)
                abs_val = abs(val)

                matched = any(
                    math.isclose(abs_val, abs(g), rel_tol=0.05, abs_tol=0.5)
                    for g in gt_numbers
                )
                claim_stmt = f"Percentage claim: {pct_str}%"
                if matched:
                    verified_count += 1
                    structured_claims.append(StructuredClaim(
                        claim_id=f"claim_pct_{idx}",
                        claim_type=ClaimType.NUMERICAL,
                        statement=claim_stmt,
                        verified=True,
                        evidence_reference=f"Matched against computed metric: {abs_val}%",
                    ))
                else:
                    disc = f"Unverified percentage claim in narrative: {pct_str}% not found in computed metrics."
                    discrepancies.append(disc)
                    structured_claims.append(StructuredClaim(
                        claim_id=f"claim_pct_{idx}",
                        claim_type=ClaimType.NUMERICAL,
                        statement=claim_stmt,
                        verified=False,
                        evidence_reference="No matching computed metric",
                        discrepancy=disc,
                    ))
            except ValueError:
                pass

        # 3. Currency / Large Number Verification
        currency_matches = re.findall(r"\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)", narrative)
        for idx, curr_str in enumerate(currency_matches, start=1):
            total_claims += 1
            try:
                val = float(curr_str.replace(",", ""))
                matched = any(
                    math.isclose(val, abs(g), rel_tol=0.05, abs_tol=1.0)
                    for g in gt_numbers
                )
                claim_stmt = f"Monetary value claim: ${curr_str}"
                if matched:
                    verified_count += 1
                    structured_claims.append(StructuredClaim(
                        claim_id=f"claim_curr_{idx}",
                        claim_type=ClaimType.NUMERICAL,
                        statement=claim_stmt,
                        verified=True,
                        evidence_reference=f"Matched against computed metric: ${val}",
                    ))
                else:
                    disc = f"Unverified monetary claim in narrative: ${curr_str} not supported by computation."
                    discrepancies.append(disc)
                    structured_claims.append(StructuredClaim(
                        claim_id=f"claim_curr_{idx}",
                        claim_type=ClaimType.NUMERICAL,
                        statement=claim_stmt,
                        verified=False,
                        evidence_reference="No matching computed metric",
                        discrepancy=disc,
                    ))
            except ValueError:
                pass

        # 4. Driver Contribution Verification
        primary_driver = ground_truth_metrics.get("primary_driver")
        if primary_driver:
            driver_str = str(primary_driver).lower()
            if driver_str in narrative_lower:
                total_claims += 1
                verified_count += 1
                structured_claims.append(StructuredClaim(
                    claim_id=f"claim_driver_1",
                    claim_type=ClaimType.DRIVER_CONTRIBUTION,
                    statement=f"Primary driver identified as {primary_driver}",
                    verified=True,
                    evidence_reference=f"computed_metrics.primary_driver={primary_driver}",
                ))

        # 5. Causal Assertion Guardrails
        unhedged_causal_tokens = ["proven root cause", "proves that", "direct causal effect", "definitely caused", "proven to cause"]
        for c_tok in unhedged_causal_tokens:
            if c_tok in narrative_lower:
                total_claims += 1
                disc = (
                    f"Unverified Causal Assertion ('{c_tok}'): Observational analysis establishes "
                    "statistical association or driver contribution, not counterfactual causality. "
                    "Hedged language recommended: 'associated with' or 'primary contributing driver'."
                )
                discrepancies.append(disc)
                structured_claims.append(StructuredClaim(
                    claim_id=f"claim_causal_{total_claims}",
                    claim_type=ClaimType.CAUSAL,
                    statement=f"Unhedged causal claim: '{c_tok}'",
                    verified=False,
                    evidence_reference="Observational data lacks counterfactual identification",
                    discrepancy=disc,
                ))

        # Calculate faithfulness score
        is_faithful = len([d for d in discrepancies if "Contradiction" in d or "Unverified" in d]) == 0
        conf_discount = 0.0
        if not is_faithful:
            has_contradiction = any("Contradiction" in d for d in discrepancies)
            conf_discount = 0.5 if has_contradiction else 0.4
        elif discrepancies:
            conf_discount = min(0.2, len(discrepancies) * 0.05)

        return FaithfulnessReport(
            is_faithful=is_faithful,
            total_claims_checked=total_claims,
            verified_claims=verified_count,
            discrepancies=discrepancies,
            confidence_discount=round(conf_discount, 2),
            structured_claims=structured_claims,
        )


faithfulness_validator = FaithfulnessValidator()

