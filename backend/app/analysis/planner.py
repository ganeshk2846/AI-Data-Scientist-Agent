"""

backend/app/analysis/planner.py

Domain-Independent Analytical Planning Engine for Phase 4.

Generates, grounds, and validates structured AnalyticalPlan instances against the active schema catalog.

"""



import re

import uuid

from typing import Any, Dict, List, Optional



from backend.app.analysis.contracts_v2 import (

    AnalyticalMethod,

    AnalyticalPlan,

    ComplexityLevel,

    IntentCategory,

    IntentClassificationResult,

)

from backend.app.analysis.intent_classifier import intent_classifier

from backend.app.core.logging import logger

from backend.app.retrieval.semantics import dynamic_semantic_engine

from backend.app.schema.models import DatabaseCatalog

from backend.app.schema.service import schema_service





class AnalyticalPlanner:

    """

    Transforms user questions into schema-grounded, executable analytical plans.

    """



    def create_plan(

        self,

        question: str,

        catalog: Optional[DatabaseCatalog] = None,

        fingerprint: Optional[str] = None,

        intent_override: Optional[IntentCategory] = None,

    ) -> AnalyticalPlan:

        """

        Builds a comprehensive AnalyticalPlan grounded in the provided catalog schema.

        """

        cat = catalog or schema_service.get_cached_catalog()

        fp = fingerprint or (getattr(cat, "fingerprint", None) if cat else None)



        # 1. Intent & Complexity Classification

        intent_res: IntentClassificationResult = intent_classifier.classify(question)

        final_intent = intent_override or intent_res.primary_intent

        complexity = intent_res.complexity



        plan_id = f"plan_{uuid.uuid4().hex[:10]}"

        q_lower = question.lower()



        # 2. Schema Discovery: Relevant Tables & Columns (with Fact/Dimension & Temporal Ranking)

        relevant_tables: List[str] = []

        required_cols: Dict[str, List[str]] = {}

        time_dim: Optional[str] = None

        target_var: Optional[str] = None



        DOMAIN_SYNONYMS = {

            "loans": ["borrow", "borrowing", "checkout", "checkouts", "loan", "loans"],

            "orders": ["order", "orders", "purchase", "purchases", "buy", "sale", "sales", "revenue"],

            "admissions": ["admission", "admissions", "patient", "patients", "hospital", "admitted"],

            "treatments": ["treatment", "treatments", "therapy", "procedure", "procedures"],

            "production": ["production", "manufacturing", "downtime", "defect", "machine", "workcenter"],

        }



        def _get_tbl_date_cols(tbl_m) -> List[str]:

            res = []

            for c in tbl_m.columns:

                col_lower = c.name.lower()

                if col_lower.endswith("_id") or c.is_pk:

                    continue

                if col_lower.endswith(("_hours", "_hrs", "_min", "_mins", "_minutes", "_sec", "_seconds", "_ms", "_duration")):

                    continue

                if c.is_numeric_candidate and not any(t in col_lower for t in ["year", "month", "day", "date"]):

                    continue

                type_upper = (c.sqlite_type or "").upper()

                if any(t in col_lower for t in ["date", "time", "timestamp", "created_at", "updated_at", "day", "month", "year"]):

                    res.append(c.name)

                elif any(t in type_upper for t in ["DATE", "TIME", "TIMESTAMP"]):

                    res.append(c.name)

            return res



        if cat and cat.tables:

            tables_lower = {name.lower(): (name, model) for name, model in cat.tables.items()}



            # 2a. Match candidate tables from question tokens, domain synonyms, and compound stems
            matched_tables: List[str] = []
            for tbl_l, (orig_name, tbl_model) in tables_lower.items():
                if (
                    tbl_l in q_lower
                    or orig_name.lower() in q_lower
                    or tbl_l.rstrip("s") in q_lower
                ):
                    matched_tables.append(orig_name)
                elif tbl_l in DOMAIN_SYNONYMS and any(syn in q_lower for syn in DOMAIN_SYNONYMS[tbl_l]):
                    matched_tables.append(orig_name)
                elif any(part in q_lower for part in tbl_l.split("_") if len(part) >= 4):
                    matched_tables.append(orig_name)
            # Ground single-table database

            if not matched_tables and len(cat.tables) == 1:

                orig_name, tbl_model = next(iter(cat.tables.items()))

                matched_tables.append(orig_name)



            # If still no match, inspect standard transactional entities

            if not matched_tables:

                for cand in ["orders", "admissions", "loans", "production", "sales", "billing"]:

                    if cand in tables_lower:

                        matched_tables.append(tables_lower[cand][0])

                        break



            # 2b. Temporal & Foreign-Key Relationship Resolution (DEF-02)

            # If intent is PREDICTIVE or temporal trend is requested, prioritize tables with verified dates

            # or resolve connected fact tables via foreign keys

            resolved_tables: List[str] = []



            if final_intent == IntentCategory.PREDICTIVE or any(w in q_lower for w in ["trend", "forecast", "predict", "demand"]):

                # Partition matched tables into temporal tables vs dimension tables

                temporal_matches = [t for t in matched_tables if _get_tbl_date_cols(cat.tables[t])]

                dimension_matches = [t for t in matched_tables if not _get_tbl_date_cols(cat.tables[t])]



                # If we have dimension table(s) without dates, search for FK-connected event table(s)

                if not temporal_matches and dimension_matches:

                    dim_tbl_name = dimension_matches[0]

                    dim_tbl = cat.tables[dim_tbl_name]



                    # Search catalog for event tables referencing this dimension table

                    connected_event_table = None

                    for other_name, other_model in cat.tables.items():

                        if other_name == dim_tbl_name:

                            continue

                        # Check FK from other_model pointing to dim_tbl

                        has_fk_to_dim = any(

                            fk.target_table.lower() == dim_tbl_name.lower()

                            for fk in other_model.foreign_keys

                        )

                        # Or check FK from dim_tbl pointing to other_model

                        has_fk_from_dim = any(

                            fk.target_table.lower() == other_name.lower()

                            for fk in dim_tbl.foreign_keys

                        )

                        if (has_fk_to_dim or has_fk_from_dim) and _get_tbl_date_cols(other_model):

                            connected_event_table = other_name

                            break



                    if connected_event_table:

                        # Prioritize event table as primary, dimension table as secondary

                        resolved_tables = [connected_event_table, dim_tbl_name]

                    else:

                        resolved_tables = dimension_matches

                elif temporal_matches and dimension_matches:

                    # Verified relationship ranking: place event table first, dimension table second

                    resolved_tables = temporal_matches + dimension_matches

                elif temporal_matches:

                    resolved_tables = temporal_matches

                else:

                    resolved_tables = matched_tables

            else:

                resolved_tables = matched_tables



            # Deduplicate while preserving order

            relevant_tables = list(dict.fromkeys(resolved_tables))

            for t in relevant_tables:

                if t in cat.tables:

                    required_cols[t] = [c.name for c in cat.tables[t].columns]



            # 2c. Discover Temporal Dimension

            for tbl_name in relevant_tables:

                tbl_model = cat.tables.get(tbl_name)

                if tbl_model:

                    date_cols = _get_tbl_date_cols(tbl_model)

                    if date_cols:

                        matched = [dc for dc in date_cols if any(tok in dc.lower() for tok in q_lower.split())]

                        chosen_col = matched[0] if matched else date_cols[0]

                        time_dim = f"{tbl_name}.{chosen_col}"

                        break



            # 2d. Discover Target Numeric / Metric Variable

            for tbl_name in relevant_tables:

                tbl_model = cat.tables.get(tbl_name)

                if tbl_model:

                    numeric_candidates = []

                    for c in tbl_model.columns:

                        col_lower = c.name.lower()

                        if col_lower.endswith("_id") or c.is_pk:

                            continue

                        if any(t in col_lower for t in ["amount", "total", "cost", "price", "sales", "revenue", "count", "qty", "quantity", "value", "score", "rate"]):

                            numeric_candidates.append(f"{tbl_name}.{c.name}")

                        elif c.is_numeric_candidate:

                            numeric_candidates.append(f"{tbl_name}.{c.name}")

                    if numeric_candidates:

                        matched = [nc for nc in numeric_candidates if any(tok in nc.lower() for tok in q_lower.split())]

                        target_var = matched[0] if matched else numeric_candidates[0]

                        break



        # 3. Retrieve Authoritative Metrics for Active Fingerprint

        relevant_metrics: List[str] = []

        if fp:

            auth_metrics = dynamic_semantic_engine.get_authoritative_metrics(fingerprint=fp)

            for m in auth_metrics:

                if m.metric_key in q_lower or m.display_name.lower() in q_lower:

                    relevant_metrics.append(m.metric_key)



        # 4. Method Selection

        candidate_methods = intent_res.recommended_methods

        selected_method = candidate_methods[0] if candidate_methods else AnalyticalMethod.SQL_QUERY_ONLY



        # 5. Validation Requirements based on method & intent

        val_reqs: List[str] = ["Read-only SQL safety", "Non-fabricated numerical claims"]

        if final_intent == IntentCategory.PREDICTIVE:

            val_reqs.append("Minimum 10 continuous time-series observations")

            val_reqs.append("Out-of-sample backtesting comparison with naive baseline")

        elif final_intent == IntentCategory.DIAGNOSTIC:

            val_reqs.append("Explicit non-causal disclaimer on driver ranking")

            val_reqs.append("Statistical significance or deviation quantification")

        elif final_intent == IntentCategory.PRESCRIPTIVE:

            val_reqs.append("Explicit business constraint feasibility check")

            val_reqs.append("No automated business-altering execution")



        # 6. Output format determination

        if final_intent == IntentCategory.PREDICTIVE:

            out_format = "forecast_line_chart_with_confidence_cone"

        elif final_intent == IntentCategory.DIAGNOSTIC:

            out_format = "variance_driver_decomposition_bar"

        elif final_intent == IntentCategory.PRESCRIPTIVE:

            out_format = "recommendation_table_with_tradeoff_matrix"

        elif "trend" in q_lower or time_dim:

            out_format = "trend_line_chart"

        else:

            out_format = "kpi_card_and_table"



        # 7. Executability Check & Abstention Guardrail

        is_executable = True

        abstain_reason = None



        if not cat:

            is_executable = False

            abstain_reason = "No active database schema catalog is available to ground the analytical plan."

        elif not relevant_tables and final_intent != IntentCategory.SQL_LOOKUP:

            is_executable = False

            abstain_reason = f"Could not identify relevant schema entities in the connected database for query: '{question}'."

        elif final_intent == IntentCategory.PREDICTIVE and not time_dim:

            is_executable = False

            abstain_reason = "Predictive time-series forecasting requires a detectable temporal/date column, but none was identified in the schema."



        objective_str = f"Execute {final_intent.value} analysis ({selected_method.value}) to answer: '{question}'"



        return AnalyticalPlan(

            plan_id=plan_id,

            question=question,

            intent=final_intent,

            complexity=complexity,

            analytical_objective=objective_str,

            relevant_tables=relevant_tables,

            required_columns=required_cols,

            relevant_metrics=relevant_metrics,

            filters=[],

            time_dimension=time_dim,

            target_variable=target_var,

            candidate_methods=candidate_methods,

            selected_method=selected_method,

            data_extraction_sql=None,

            validation_requirements=val_reqs,

            expected_output_format=out_format,

            is_executable=is_executable,

            abstain_reason=abstain_reason,

        )





analytical_planner = AnalyticalPlanner()



