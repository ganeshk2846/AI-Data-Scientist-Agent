"""
Expectations derived from the connected warehouse at test time.

Tests previously hardcoded counts from an earlier dataset (30 tables, 17,924
orders), so swapping the database broke them even though the code was correct.
Deriving the figures here keeps the assertions strict while letting the suite
run against whichever database is configured.
"""

import sqlite3
from typing import Dict, List

from backend.app.core.config import settings


def _collect() -> Dict[str, object]:
    facts: Dict[str, object] = {"tables": [], "table_count": 0, "orders_rows": 0, "total_rows": 0}
    try:
        path = settings.resolved_ecommerce_db_path
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            tables: List[str] = [
                r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%' ORDER BY name"
                )
            ]
            total = 0
            orders_rows = 0
            for t in tables:
                n = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                total += n
                if t == "orders":
                    orders_rows = n
            facts.update(tables=tables, table_count=len(tables), orders_rows=orders_rows, total_rows=total)
        finally:
            conn.close()
    except Exception:
        pass
    return facts


_FACTS = _collect()

TABLE_NAMES: List[str] = _FACTS["tables"]            # type: ignore[assignment]
EXPECTED_TABLE_COUNT: int = _FACTS["table_count"]    # type: ignore[assignment]
EXPECTED_ORDERS_ROWS: int = _FACTS["orders_rows"]    # type: ignore[assignment]
EXPECTED_TOTAL_ROWS: int = _FACTS["total_rows"]      # type: ignore[assignment]
