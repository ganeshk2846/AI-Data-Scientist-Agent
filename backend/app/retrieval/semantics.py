"""
backend/app/retrieval/semantics.py
Dynamic Semantic Layer and Metric Provenance Engine.
Provides dynamic derivation, AST validation, and strict 3-tier lifecycle management
for business definitions and SQL calculation formulas:
  1. AUTO_INFERRED: Derived by Ollama LLM analyzing active schema and column statistics.
  2. VALIDATED_CANDIDATE: AST-verified and syntactically sound.
  3. USER_APPROVED: Human-verified authoritative ground truth.
Unapproved metrics are strictly excluded from query generation prompt contexts.
"""

from datetime import datetime, timezone
import asyncio
import concurrent.futures
import json
from pathlib import Path
import re
import sqlite3
import threading
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
import sqlglot
from backend.app.core.config import settings
from backend.app.core.contracts import MetricStatus, SemanticMetricDefinition
from backend.app.core.logging import logger
from backend.app.llm.client import BaseLLMProvider, get_llm_provider
from backend.app.llm.models import LLMMessage, LLMRequest
from backend.app.schema.models import DatabaseCatalog


# Backward-compatible model for Version 1 callers
class BusinessMetric(BaseModel):
    name: str
    display_name: str
    formula: str
    description: str
    target_tables: List[str]
    is_verified: bool = True
    synonyms: List[str] = Field(default_factory=list)


CANONICAL_METRICS: Dict[str, BusinessMetric] = {
    "gross_revenue": BusinessMetric(
        name="gross_revenue",
        display_name="Gross Revenue",
        formula="ROUND(SUM(total_amount), 2)",
        description="Total monetary value of all placed orders including cancelled orders.",
        target_tables=["orders"],
        synonyms=["gross sales", "total bookings", "headline revenue"],
    ),
    "net_revenue": BusinessMetric(
        name="net_revenue",
        display_name="Net Delivered Revenue",
        formula="ROUND(SUM(total_amount), 2) WHERE LOWER(order_status) = 'delivered'",
        description="Total monetary value of successfully delivered orders.",
        target_tables=["orders"],
        synonyms=["delivered revenue", "net sales", "realized revenue"],
    ),
    "average_order_value": BusinessMetric(
        name="average_order_value",
        display_name="Average Order Value (AOV)",
        formula="ROUND(AVG(total_amount), 2) WHERE LOWER(order_status) = 'delivered'",
        description="Average ticket size per delivered transaction.",
        target_tables=["orders"],
        synonyms=["aov", "average basket size", "avg ticket"],
    ),
    "return_rate": BusinessMetric(
        name="return_rate",
        display_name="Return Rate",
        formula="ROUND(COUNT(returns.return_id) * 100.0 / COUNT(orders.order_id), 2)",
        description="Percentage of delivered orders that resulted in a customer return.",
        target_tables=["orders", "returns"],
        synonyms=["returns percentage", "order return rate"],
    ),
    "customer_csat": BusinessMetric(
        name="customer_csat",
        display_name="Customer Satisfaction Score (CSAT)",
        formula="ROUND(AVG(satisfaction_score), 2)",
        description="Average CSAT score on resolved support tickets (scale 1 to 5).",
        target_tables=["support_tickets"],
        synonyms=["csat", "satisfaction rating"],
    ),
    "marketing_roas": BusinessMetric(
        name="marketing_roas",
        display_name="Return on Ad Spend (ROAS)",
        formula="revenue / SUM(marketing_spend.spend_amount)",
        description="Revenue generated per dollar of marketing advertising spend.",
        target_tables=["orders", "marketing_spend", "marketing_channels"],
        synonyms=["roas", "marketing efficiency ratio"],
    ),
}


class DynamicSemanticEngine:
    """
    Manages dynamic semantic metric discovery, AST validation,
    and 3-tier provenance lifecycle backed by agent_app.sqlite.
    """

    def __init__(self, app_db_path: Optional[Path] = None):
        self._lock = threading.RLock()
        self.app_db_path = app_db_path or settings.resolved_app_db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.app_db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def seed_baseline_canonical_metrics(self, fingerprint: str = "default") -> int:
        """Seeds canonical baseline metrics into semantic_metrics table as USER_APPROVED."""
        with self._lock:
            conn = self._get_connection()
            seeded_count = 0
            try:
                with conn:
                    for key, metric in CANONICAL_METRICS.items():
                        cur = conn.cursor()
                        cur.execute(
                            "SELECT metric_key FROM semantic_metrics WHERE metric_key = ?;",
                            (key,),
                        )
                        if not cur.fetchone():
                            now_str = datetime.now(timezone.utc).isoformat()
                            cur.execute(
                                """
                                INSERT INTO semantic_metrics (
                                    id, metric_key, display_name, formula_sql,
                                    status, derivation_type, verified_by, description,
                                    confidence_score, fingerprint, created_at, updated_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                                """,
                                (
                                    f"metric_{key}",
                                    key,
                                    metric.display_name,
                                    metric.formula,
                                    MetricStatus.USER_APPROVED.value,
                                    "CANONICAL",
                                    "system_baseline",
                                    metric.description,
                                    1.0,
                                    fingerprint,
                                    now_str,
                                    now_str,
                                ),
                            )
                            seeded_count += 1
                logger.info(f"Seeded {seeded_count} canonical metrics into store (fp: {fingerprint})")
                return seeded_count
            finally:
                conn.close()

    def _call_llm(self, provider: BaseLLMProvider, prompt: str) -> str:
        """Synchronously calls provider.generate() safely across sync/async contexts."""
        async def _run():
            request = LLMRequest(
                messages=[LLMMessage(role="user", content=prompt)],
                temperature=0.1,
            )
            res = await provider.generate(request)
            return res.content

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(lambda: asyncio.run(_run()))
                return future.result()
        else:
            return asyncio.run(_run())

    def infer_metrics_from_schema(
        self,
        catalog: DatabaseCatalog,
        llm_provider: Optional[BaseLLMProvider] = None,
    ) -> List[SemanticMetricDefinition]:
        """
        Analyzes active schema tables, numeric columns, and foreign keys to dynamically
        infer candidate business metrics using Ollama qwen3:4b.
        Metrics are AST-checked and stored with status AUTO_INFERRED or VALIDATED_CANDIDATE.
        """
        with self._lock:
            fp = getattr(catalog, "fingerprint", None) or getattr(catalog, "source_fingerprint", None) or "default"
            active_llm = llm_provider or get_llm_provider()

            # Compile schema summary for LLM prompt
            schema_summary = []
            for name, tbl in list(catalog.tables.items())[:15]:
                num_cols = [c.name for c in tbl.columns if c.is_numeric_candidate]
                date_cols = [c.name for c in tbl.columns if c.is_date_candidate]
                if num_cols:
                    schema_summary.append(
                        f"Table '{name}': numeric columns [{', '.join(num_cols)}], date columns [{', '.join(date_cols)}]"
                    )

            if not schema_summary:
                return []

            prompt = f"""You are a Lead Data Architect. Analyze the following database schema summary and propose 3 to 5 standard analytical business metrics for this database:

Schema:
{chr(10).join(schema_summary)}

Return ONLY a JSON array of objects. Do not include markdown commentary.
Each object must have exactly these keys:
- "metric_key": snake_case identifier (e.g. "total_sales_volume", "avg_item_price")
- "display_name": human-readable title (e.g. "Total Sales Volume")
- "formula_sql": SQL aggregation expression (e.g. "SUM(quantity)", "AVG(unit_price)")
- "description": 1-sentence business explanation

Example format:
[
  {{
    "metric_key": "total_order_spend",
    "display_name": "Total Order Spend",
    "formula_sql": "SUM(total_amount)",
    "description": "Total monetary spend across orders."
  }}
]
"""
            inferred_results: List[SemanticMetricDefinition] = []
            try:
                raw_text = self._call_llm(active_llm, prompt)
                text = raw_text.strip()
                # Strip thinking tags
                text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
                # Extract JSON array
                match = re.search(r"\[.*\]", text, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    raw_metrics = json.loads(json_str)
                    conn = self._get_connection()
                    try:
                        with conn:
                            for raw in raw_metrics:
                                key = re.sub(r"[^a-z0-9_]", "", str(raw.get("metric_key", "")).lower())
                                if not key:
                                    continue
                                formula = str(raw.get("formula_sql", "")).strip()
                                display = str(raw.get("display_name", key.replace("_", " ").title()))
                                desc = str(raw.get("description", ""))

                                # AST Validation on formula
                                is_valid = False
                                try:
                                    # Test parsing formula inside a SELECT
                                    sqlglot.parse_one(f"SELECT {formula}")
                                    is_valid = True
                                except Exception:
                                    is_valid = False

                                status = (
                                    MetricStatus.VALIDATED_CANDIDATE
                                    if is_valid
                                    else MetricStatus.AUTO_INFERRED
                                )
                                now_str = datetime.now(timezone.utc).isoformat()
                                metric_id = f"inferred_{key}"

                                cur = conn.cursor()
                                cur.execute(
                                    """
                                    INSERT INTO semantic_metrics (
                                        id, metric_key, display_name, formula_sql,
                                        status, derivation_type, verified_by, description,
                                        confidence_score, fingerprint, created_at, updated_at
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ON CONFLICT(metric_key) DO UPDATE SET
                                        display_name = excluded.display_name,
                                        formula_sql = excluded.formula_sql,
                                        status = excluded.status,
                                        description = excluded.description,
                                        updated_at = CURRENT_TIMESTAMP;
                                    """,
                                    (
                                        metric_id,
                                        key,
                                        display,
                                        formula,
                                        status.value,
                                        "INFERRED",
                                        None,
                                        desc,
                                        0.8 if is_valid else 0.5,
                                        fp,
                                        now_str,
                                        now_str,
                                    ),
                                )

                                inferred_results.append(
                                    SemanticMetricDefinition(
                                        metric_key=key,
                                        display_name=display,
                                        formula_sql=formula,
                                        status=status,
                                        derivation_type="INFERRED",
                                        description=desc,
                                        confidence_score=0.8 if is_valid else 0.5,
                                    )
                                )
                    finally:
                        conn.close()
            except Exception as e:
                logger.warning(f"Semantic metric inference error: {e}")

            return inferred_results

    def approve_metric(self, metric_key: str, approved_by: str = "user") -> Optional[SemanticMetricDefinition]:
        """
        Transitions candidate metric from AUTO_INFERRED / VALIDATED_CANDIDATE
        to authoritative USER_APPROVED status.
        """
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    cur = conn.cursor()
                    cur.execute(
                        """
                        UPDATE semantic_metrics
                        SET status = ?, verified_by = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE metric_key = ?;
                        """,
                        (MetricStatus.USER_APPROVED.value, approved_by, metric_key),
                    )
                    if cur.rowcount == 0:
                        return None

                    cur.execute("SELECT * FROM semantic_metrics WHERE metric_key = ?;", (metric_key,))
                    row = cur.fetchone()
                    if row:
                        return SemanticMetricDefinition(
                            metric_key=row["metric_key"],
                            display_name=row["display_name"],
                            formula_sql=row["formula_sql"],
                            status=MetricStatus(row["status"]),
                            derivation_type=row["derivation_type"],
                            verified_by=row["verified_by"],
                            description=row["description"],
                            confidence_score=row["confidence_score"] or 1.0,
                        )
                    return None
            finally:
                conn.close()

    def get_authoritative_metrics(self, fingerprint: Optional[str] = None) -> List[SemanticMetricDefinition]:
        """
        Returns ONLY metrics with USER_APPROVED provenance.
        Unapproved metrics (AUTO_INFERRED, VALIDATED_CANDIDATE) are strictly excluded.
        """
        with self._lock:
            conn = self._get_connection()
            results = []
            try:
                cur = conn.cursor()
                if fingerprint:
                    cur.execute(
                        """
                        SELECT * FROM semantic_metrics
                        WHERE status = ? AND (fingerprint = ? OR fingerprint = 'default')
                        ORDER BY metric_key ASC;
                        """,
                        (MetricStatus.USER_APPROVED.value, fingerprint),
                    )
                else:
                    cur.execute(
                        """
                        SELECT * FROM semantic_metrics
                        WHERE status = ?
                        ORDER BY metric_key ASC;
                        """,
                        (MetricStatus.USER_APPROVED.value,),
                    )
                rows = cur.fetchall()
                for r in rows:
                    results.append(
                        SemanticMetricDefinition(
                            metric_key=r["metric_key"],
                            display_name=r["display_name"],
                            formula_sql=r["formula_sql"],
                            status=MetricStatus(r["status"]),
                            derivation_type=r["derivation_type"],
                            verified_by=r["verified_by"],
                            description=r["description"],
                            confidence_score=r["confidence_score"] or 1.0,
                        )
                    )
                return results
            finally:
                conn.close()

    def list_metrics(
        self,
        fingerprint: Optional[str] = None,
        status: Optional[MetricStatus] = None,
    ) -> List[SemanticMetricDefinition]:
        """Lists metrics with optional filtering by status and database fingerprint."""
        with self._lock:
            conn = self._get_connection()
            results = []
            try:
                cur = conn.cursor()
                query = "SELECT * FROM semantic_metrics WHERE 1=1"
                params = []
                if status:
                    query += " AND status = ?"
                    params.append(status.value)
                if fingerprint:
                    query += " AND (fingerprint = ? OR fingerprint = 'default')"
                    params.append(fingerprint)
                query += " ORDER BY metric_key ASC;"

                cur.execute(query, tuple(params))
                for r in cur.fetchall():
                    results.append(
                        SemanticMetricDefinition(
                            metric_key=r["metric_key"],
                            display_name=r["display_name"],
                            formula_sql=r["formula_sql"],
                            status=MetricStatus(r["status"]),
                            derivation_type=r["derivation_type"],
                            verified_by=r["verified_by"],
                            description=r["description"],
                            confidence_score=r["confidence_score"] or 0.5,
                        )
                    )
                return results
            finally:
                conn.close()

    def format_authoritative_prompt_context(
        self,
        fingerprint: Optional[str] = None,
        query: Optional[str] = None,
    ) -> str:
        """
        Formats authoritative business metric calculation formulas for LLM Text-to-SQL context.
        Guarantees that only USER_APPROVED metrics are injected.
        """
        metrics = self.get_authoritative_metrics(fingerprint)
        if not metrics:
            return ""

        # Filter by query if query provided, else include top metrics
        selected = metrics
        if query:
            q_lower = query.lower()
            matched = [
                m for m in metrics
                if m.metric_key in q_lower
                or m.display_name.lower() in q_lower
                or (m.description and any(w in q_lower for w in m.description.lower().split() if len(w) > 4))
            ]
            if matched:
                selected = matched

        lines = ["Authoritative Business Metrics & Verified Calculation Rules:"]
        for m in selected[:6]:
            lines.append(f"- {m.display_name} (`{m.metric_key}`): {m.formula_sql}")
            if m.description:
                lines.append(f"  Note: {m.description}")
        return "\n".join(lines)


# Singleton instances
dynamic_semantic_engine = DynamicSemanticEngine()


# Version 1 Backward-Compatible SemanticRegistry interface
class SemanticRegistry:
    """Manages verified business metrics and synonym mappings with V1 compatibility."""

    def __init__(self, engine: DynamicSemanticEngine = dynamic_semantic_engine):
        self.engine = engine

    def get_metric(self, name: str) -> Optional[BusinessMetric]:
        name_clean = name.lower().strip()
        if name_clean in CANONICAL_METRICS:
            return CANONICAL_METRICS[name_clean]
        # Check active store
        metrics = self.engine.get_authoritative_metrics()
        for m in metrics:
            if m.metric_key == name_clean:
                return BusinessMetric(
                    name=m.metric_key,
                    display_name=m.display_name,
                    formula=m.formula_sql,
                    description=m.description or "",
                    target_tables=[],
                    is_verified=True,
                )
        return None

    def list_metrics(self) -> List[BusinessMetric]:
        return list(CANONICAL_METRICS.values())

    def find_relevant_metrics(self, query: str) -> List[BusinessMetric]:
        q_lower = query.lower()
        matched = []
        for m in CANONICAL_METRICS.values():
            if m.name in q_lower or m.display_name.lower() in q_lower or any(s in q_lower for s in m.synonyms):
                matched.append(m)
        return matched


semantic_registry = SemanticRegistry()
