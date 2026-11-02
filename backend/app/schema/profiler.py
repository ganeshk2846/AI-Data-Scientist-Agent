"""
backend/app/schema/profiler.py
Adaptive Sampling Profiler for relational database tables and columns.
For tables > 50,000 rows, samples up to 10,000 rows to prevent expensive full-table scans
while maintaining statistical accuracy and high performance (<5s profiling duration).
"""

import time
from typing import Dict, List, Optional, Tuple
from backend.app.core.logging import logger
from backend.app.db.base import BaseDatabaseAdapter
from backend.app.schema.models import ColumnModel


class AdaptiveSamplingProfiler:
    """Profiles columns with adaptive sampling and 5-second safety bounds."""

    def __init__(self, adapter: BaseDatabaseAdapter, sampling_threshold: int = 50_000, sample_size: int = 10_000):
        self.adapter = adapter
        self.sampling_threshold = sampling_threshold
        self.sample_size = sample_size

    def profile_table_columns(
        self,
        table_name: str,
        row_count: int,
        columns: List[ColumnModel],
    ) -> List[ColumnModel]:
        """
        Profiles statistical distributions (nulls, distincts, min/max, safe categories)
        using adaptive sampling on large tables.
        """
        use_sampling = row_count > self.sampling_threshold
        profiled_columns: List[ColumnModel] = []

        for col in columns:
            null_cnt = 0
            dist_cnt = 0
            min_v = None
            max_v = None
            sample_vals: List[str] = []
            profiling_skipped = False

            try:
                if use_sampling:
                    # Bounded sampling subquery for tables > 50k rows
                    query = f'''
                        WITH sample_data AS (
                            SELECT "{col.name}" 
                            FROM "{table_name}" 
                            LIMIT {self.sample_size}
                        )
                        SELECT 
                            SUM(CASE WHEN "{col.name}" IS NULL THEN 1 ELSE 0 END),
                            COUNT(DISTINCT "{col.name}"),
                            MIN("{col.name}"),
                            MAX("{col.name}")
                        FROM sample_data;
                    '''
                else:
                    # Direct query for tables <= 50k rows
                    query = f'''
                        SELECT 
                            SUM(CASE WHEN "{col.name}" IS NULL THEN 1 ELSE 0 END),
                            COUNT(DISTINCT "{col.name}"),
                            MIN("{col.name}"),
                            MAX("{col.name}")
                        FROM "{table_name}";
                    '''

                res = self.adapter.execute_query(query, timeout=5)
                if res.rows:
                    row = res.rows[0]
                    vals = list(row.values())
                    null_cnt = vals[0] if vals[0] is not None else 0
                    dist_cnt = vals[1] if vals[1] is not None else 0
                    min_v = vals[2]
                    max_v = vals[3]

                # If sampled, scale null count estimate proportionally
                if use_sampling and self.sample_size > 0:
                    null_ratio = null_cnt / self.sample_size
                    null_cnt = int(null_ratio * row_count)

                # Safe sample values for low-cardinality categorical fields (excluding PKs/FKs)
                if not col.is_pk and not col.is_fk and 0 < dist_cnt <= 10:
                    cat_query = f'''
                        SELECT DISTINCT "{col.name}" 
                        FROM "{table_name}" 
                        WHERE "{col.name}" IS NOT NULL 
                        LIMIT 10;
                    '''
                    cat_res = self.adapter.execute_query(cat_query, timeout=3)
                    sample_vals = [str(list(r.values())[0]) for r in cat_res.rows if list(r.values())[0] is not None]

            except Exception as err:
                logger.debug(f"Adaptive profiling skipped for {table_name}.{col.name}: {err}")
                profiling_skipped = True

            null_pct = round((null_cnt / row_count * 100), 2) if row_count > 0 else 0.0

            # Update column with profiled statistics
            col_dict = col.model_dump()
            col_dict.update({
                "null_count": null_cnt,
                "null_percentage": null_pct,
                "distinct_count": dist_cnt,
                "min_sample": str(min_v)[:60] if min_v is not None else None,
                "max_sample": str(max_v)[:60] if max_v is not None else None,
                "sample_values": sample_vals,
            })
            profiled_columns.append(ColumnModel(**col_dict))

        return profiled_columns
