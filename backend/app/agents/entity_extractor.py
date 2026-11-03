"""
backend/app/agents/entity_extractor.py
Structured Entity Extraction and Multi-Round Clarification Resolver.

Extracts structured query representations (intent, metrics, dimensions, filters, time bounds,
scenario params), grounds them in the active database catalog, generates single targeted
clarification questions when ambiguous, limits clarification to a strict 2-round cap,
and contextually resolves user follow-ups without losing context.
"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

from backend.app.agents.contracts import ClarificationOption
from backend.app.analysis.contracts_v2 import IntentCategory
from backend.app.schema.models import DatabaseCatalog
from backend.app.core.logging import logger


class StructuredQuestionRepresentation(BaseModel):
    """
    Pydantic contract representing an extracted, schema-grounded business query.
    """
    model_config = ConfigDict(extra="ignore")

    raw_question: str
    intent_category: IntentCategory = IntentCategory.DESCRIPTIVE
    secondary_intents: List[str] = Field(default_factory=list)
    metrics: List[str] = Field(default_factory=list)
    dimensions: List[str] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)
    region: Optional[str] = None
    product: Optional[str] = None
    customer_segment: Optional[str] = None
    date_range: Optional[Dict[str, str]] = None
    comparison_period: Optional[str] = None
    aggregation: Optional[str] = None
    ranking_requirement: Optional[Dict[str, Any]] = None
    forecast_horizon: Optional[int] = None
    scenario_parameters: Optional[Dict[str, Any]] = None
    ambiguity_flags: List[str] = Field(default_factory=list)
    clarification_required: bool = False
    clarification_question: Optional[str] = None
    clarification_options: List[ClarificationOption] = Field(default_factory=list)
    missing_slots: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    turn_count: int = 0
    resolved_query: Optional[str] = None


class EntityExtractor:
    """
    Extracts structured slots from user questions, checks ambiguities, and resolves follow-ups.
    """

    MAX_CLARIFICATION_TURNS: int = 2

    COMMON_METRICS = {
        "revenue": ["revenue", "sales", "gross sales", "total amount", "turnover"],
        "orders": ["orders", "order count", "number of orders", "transactions"],
        "profit": ["profit", "margin", "net margin", "gross profit"],
        "quantity": ["quantity", "units", "items sold", "volume"],
        "spend": ["spend", "expenditure", "customer spend"],
        "churn": ["churn", "attrition", "lost customers", "inactive customers"],
    }

    COMMON_DIMENSIONS = {
        "category": ["category", "product category", "department"],
        "region": ["region", "state", "city", "country", "territory", "location"],
        "customer_segment": ["segment", "customer segment", "tier", "loyalty"],
        "time": ["month", "quarter", "year", "date", "day", "weekly", "monthly", "annual"],
        "channel": ["channel", "sales channel", "marketing channel", "acquisition channel"],
    }

    def extract(
        self,
        question: str,
        catalog: Optional[DatabaseCatalog] = None,
        turn_count: int = 0,
        prior_state: Optional[StructuredQuestionRepresentation] = None,
    ) -> StructuredQuestionRepresentation:
        """
        Parses the question into StructuredQuestionRepresentation,
        validates entities against schema, and flags ambiguities if slots are missing.
        """
        q_low = question.lower().strip()

        # If this is a follow-up turn to a prior state requiring clarification:
        if prior_state and prior_state.clarification_required:
            return self.resolve_followup(prior_state, question, catalog=catalog)

        # 1. Intent Detection
        intent = IntentCategory.DESCRIPTIVE
        if any(w in q_low for w in ["what if", "simulate", "suppose", "shock", "increase price by", "decrease demand"]):
            intent = IntentCategory.PRESCRIPTIVE
        elif any(w in q_low for w in ["why did", "why are", "driver", "variance", "anomaly", "spike", "drop in"]):
            intent = IntentCategory.DIAGNOSTIC
        elif any(w in q_low for w in ["forecast", "predict", "project", "future sales", "next quarter"]):
            intent = IntentCategory.PREDICTIVE
        elif any(w in q_low for w in ["optimize", "recommend", "allocation", "allocate budget"]):
            intent = IntentCategory.PRESCRIPTIVE

        # 2. Extract Metrics
        extracted_metrics: List[str] = []
        for std_metric, aliases in self.COMMON_METRICS.items():
            if any(a in q_low for a in aliases):
                extracted_metrics.append(std_metric)

        # 3. Extract Dimensions
        extracted_dimensions: List[str] = []
        for std_dim, aliases in self.COMMON_DIMENSIONS.items():
            if any(a in q_low for a in aliases):
                extracted_dimensions.append(std_dim)

        # 4. Extract Filters
        extracted_filters: Dict[str, Any] = {}
        region_val = None
        for r in ["north", "south", "east", "west", "central", "northeast", "northwest", "southeast", "southwest"]:
            if re.search(rf"\b{r}\b", q_low):
                region_val = r.capitalize()
                extracted_filters["region"] = region_val
                break

        product_val = None
        for p in ["electronics", "apparel", "clothing", "home & kitchen", "beauty", "books", "sports"]:
            if p in q_low:
                product_val = p.title()
                extracted_filters["category"] = product_val
                break

        segment_val = None
        for s in ["at risk", "inactive", "high value", "premium", "budget shoppers", "regular", "dormant"]:
            if s in q_low:
                segment_val = s.title()
                extracted_filters["customer_segment"] = segment_val
                break

        # 5. Extract Time Range & Comparison
        date_range = None
        comp_period = None
        year_matches = re.findall(r"\b(20[2-3][0-9])\b", question)
        if year_matches:
            if len(year_matches) == 1:
                y = year_matches[0]
                date_range = {"start_date": f"{y}-01-01", "end_date": f"{y}-12-31"}
            elif len(year_matches) >= 2:
                date_range = {"start_date": f"{year_matches[0]}-01-01", "end_date": f"{year_matches[1]}-12-31"}
                comp_period = f"{year_matches[0]} vs {year_matches[1]}"

        if any(w in q_low for w in ["yoy", "year over year", "compared to last year"]):
            comp_period = "YoY"
        elif any(w in q_low for w in ["mom", "month over month"]):
            comp_period = "MoM"

        # 6. Extract Ranking / Limit
        ranking_req = None
        top_match = re.search(r"\b(top|bottom)\s+(\d+)\b", q_low)
        if top_match:
            ranking_req = {
                "direction": "desc" if top_match.group(1) == "top" else "asc",
                "limit": int(top_match.group(2)),
            }
        elif any(w in q_low for w in ["top customers", "best customers", "top products"]):
            ranking_req = {"direction": "desc", "limit": 10}

        # 7. Extract Scenario Params
        scenario_params = None
        if intent == IntentCategory.PRESCRIPTIVE or "what if" in q_low:
            pct_m = re.findall(r"([+-]?\s*\d+(?:\.\d+)?)\s*%", question)
            shock = float(pct_m[0].replace(" ", "")) if pct_m else 5.0
            param = "price" if "price" in q_low else ("marketing" if "marketing" in q_low else "demand")
            scenario_params = {"parameter": param, "shock_pct": shock}

        # 8. Check Schema Grounding
        missing_slots: List[str] = []
        ambiguity_flags: List[str] = []
        assumptions: List[str] = []

        if catalog:
            if isinstance(catalog.tables, dict):
                catalog_tables = {k.lower() for k in catalog.tables.keys()}
                catalog_columns = {
                    col.name.lower()
                    for t in catalog.tables.values()
                    for col in getattr(t, "columns", [])
                }
            else:
                catalog_tables = {t.name.lower() for t in catalog.tables}
                catalog_columns = {
                    col.name.lower()
                    for t in catalog.tables
                    for col in getattr(t, "columns", [])
                }

            # Check if extracted entities exist
            for m in extracted_metrics:
                if m not in catalog_columns and not any(m in c for c in catalog_columns):
                    assumptions.append(f"Mapped colloquial metric '{m}' to schema column total_amount/quantity.")

        # 9. Evaluate Ambiguity & Clarification Need
        clarification_needed = False
        clarif_question = None
        clarif_options: List[ClarificationOption] = []

        # Case A: Bare comparison query ("compare revenue", "compare sales", "comparison")
        if q_low in ["compare revenue", "compare sales", "comparison", "compare performance"]:
            if turn_count < self.MAX_CLARIFICATION_TURNS:
                clarification_needed = True
                clarif_question = "How would you like to compare revenue?"
                ambiguity_flags.append("missing_comparison_dimension_or_period")
                missing_slots.append("dimension_or_period")
                clarif_options = [
                    ClarificationOption(
                        option_id="opt_time",
                        label="Year-over-Year (2024 vs 2025)",
                        description="Compare annual gross revenue between 2024 and 2025",
                        inferred_query="Compare annual revenue between 2024 and 2025",
                    ),
                    ClarificationOption(
                        option_id="opt_cat",
                        label="By Product Category",
                        description="Compare revenue across product categories",
                        inferred_query="Compare revenue across product categories",
                    ),
                    ClarificationOption(
                        option_id="opt_reg",
                        label="By Geographic Region",
                        description="Compare revenue across delivery regions",
                        inferred_query="Compare revenue across geographic regions",
                    ),
                    ClarificationOption(
                        option_id="opt_seg",
                        label="By Customer Segment",
                        description="Compare revenue across customer loyalty tiers",
                        inferred_query="Compare revenue across customer segments",
                    ),
                ]
            else:
                # Max turns reached: apply transparent default
                assumptions.append("Applied default comparison: Year-over-Year (2024 vs 2025) across product categories.")
                extracted_dimensions.append("category")
                comp_period = "YoY"

        # Case B: Bare ranking query ("top customers", "best customers")
        elif q_low in ["top customers", "best customers", "who are our best customers"]:
            if turn_count < self.MAX_CLARIFICATION_TURNS:
                clarification_needed = True
                clarif_question = "Which ranking metric would you like to use for top customers?"
                ambiguity_flags.append("ambiguous_ranking_metric")
                missing_slots.append("ranking_metric")
                clarif_options = [
                    ClarificationOption(
                        option_id="opt_spend",
                        label="Total Lifetime Spend ($)",
                        description="Rank customers by total gross order value",
                        inferred_query="List top 10 customers by total spend",
                    ),
                    ClarificationOption(
                        option_id="opt_freq",
                        label="Order Frequency",
                        description="Rank customers by total order count",
                        inferred_query="List top 10 customers by order frequency",
                    ),
                ]
            else:
                assumptions.append("Applied default ranking metric: Total Lifetime Spend ($) descending for top 10 customers.")
                ranking_req = {"direction": "desc", "limit": 10, "metric": "total_spend"}
                extracted_metrics.append("spend")

        # Case C: Vague performance inquiry with no metric or timeframe ("how are we doing", "show performance")
        elif q_low in ["how are we doing", "show performance", "business status", "overview"]:
            if turn_count < self.MAX_CLARIFICATION_TURNS:
                clarification_needed = True
                clarif_question = "Which business area would you like to focus on for this performance review?"
                ambiguity_flags.append("broad_unspecified_domain")
                missing_slots.append("domain_focus")
                clarif_options = [
                    ClarificationOption(
                        option_id="opt_rev",
                        label="Monthly Revenue & Sales Trend",
                        description="Review gross revenue trends and monthly order volumes",
                        inferred_query="Show monthly revenue trend for the past year",
                    ),
                    ClarificationOption(
                        option_id="opt_cust",
                        label="Customer Segments & Churn Risk",
                        description="Analyze customer activity, retention, and revenue at risk",
                        inferred_query="Analyze customer segments and churn risk",
                    ),
                    ClarificationOption(
                        option_id="opt_prod",
                        label="Product Catalog Performance",
                        description="Review top-selling product categories and stock reorder alerts",
                        inferred_query="Show top-selling product categories",
                    ),
                ]
            else:
                assumptions.append("Applied default performance overview: Total gross revenue and order count for 2025.")
                extracted_metrics.append("revenue")
                extracted_dimensions.append("month")

        return StructuredQuestionRepresentation(
            raw_question=question,
            intent_category=intent,
            secondary_intents=[],
            metrics=extracted_metrics or ["revenue"],
            dimensions=extracted_dimensions,
            filters=extracted_filters,
            region=region_val,
            product=product_val,
            customer_segment=segment_val,
            date_range=date_range,
            comparison_period=comp_period,
            aggregation="sum" if "avg" not in q_low else "avg",
            ranking_requirement=ranking_req,
            scenario_parameters=scenario_params,
            ambiguity_flags=ambiguity_flags,
            clarification_required=clarification_needed,
            clarification_question=clarif_question,
            clarification_options=clarif_options,
            missing_slots=missing_slots,
            assumptions=assumptions,
            turn_count=turn_count,
            resolved_query=question if not clarification_needed else None,
        )

    def resolve_followup(
        self,
        prior_state: StructuredQuestionRepresentation,
        user_reply: str,
        catalog: Optional[DatabaseCatalog] = None,
    ) -> StructuredQuestionRepresentation:
        """
        Merges user follow-up answer into the existing structured representation,
        resolves ambiguity, and advances turn count without re-asking questions.
        """
        reply_low = user_reply.lower().strip()
        updated = prior_state.model_copy(deep=True)
        updated.turn_count += 1
        updated.clarification_required = False
        updated.clarification_question = None
        updated.clarification_options = []

        # 1. Match selected option ID if provided
        matched_option = None
        for opt in prior_state.clarification_options:
            if opt.option_id.lower() == reply_low or opt.label.lower() in reply_low:
                matched_option = opt
                break

        if matched_option:
            updated.resolved_query = matched_option.inferred_query
            # Re-extract slots from inferred query
            fresh = self.extract(matched_option.inferred_query, catalog=catalog, turn_count=updated.turn_count)
            fresh.turn_count = updated.turn_count
            return fresh

        # 2. Contextual keyword resolution
        # Check if user specified a dimension
        if any(w in reply_low for w in ["category", "product category", "product", "products"]):
            updated.dimensions.append("category")
            updated.resolved_query = f"{prior_state.raw_question} across product categories"
        elif any(w in reply_low for w in ["region", "regions", "geography", "territory"]):
            updated.dimensions.append("region")
            updated.resolved_query = f"{prior_state.raw_question} across geographic regions"
        elif any(w in reply_low for w in ["segment", "customer segment", "loyalty"]):
            updated.dimensions.append("customer_segment")
            updated.resolved_query = f"{prior_state.raw_question} across customer segments"
        elif any(w in reply_low for w in ["spend", "total spend", "highest spend", "money", "dollars"]):
            updated.ranking_requirement = {"direction": "desc", "limit": 10, "metric": "total_spend"}
            updated.metrics.append("spend")
            updated.resolved_query = "List top 10 customers by total lifetime spend"
        elif any(w in reply_low for w in ["order", "orders", "frequency", "most orders"]):
            updated.ranking_requirement = {"direction": "desc", "limit": 10, "metric": "order_count"}
            updated.metrics.append("orders")
            updated.resolved_query = "List top 10 customers by order frequency"
        elif any(w in reply_low for w in ["year", "yoy", "annual", "2024", "2025"]):
            updated.comparison_period = "YoY"
            updated.dimensions.append("year")
            updated.resolved_query = f"{prior_state.raw_question} Year-over-Year (2024 vs 2025)"
        else:
            # Append reply directly as a contextual filter or query refinement
            updated.resolved_query = f"{prior_state.raw_question} ({user_reply})"
            updated.assumptions.append(f"Applied contextual clarification response: '{user_reply}'")

        # Deduplicate dimensions & metrics
        updated.dimensions = list(dict.fromkeys(updated.dimensions))
        updated.metrics = list(dict.fromkeys(updated.metrics))
        return updated


entity_extractor = EntityExtractor()
