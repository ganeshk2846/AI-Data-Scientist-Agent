"""
Typed models for database schema catalog, profiling, and preparation jobs.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ColumnModel(BaseModel):
    """Profiled metadata for a single column."""
    name: str
    sqlite_type: str
    is_pk: bool = False
    not_null: bool = False
    default_value: Optional[str] = None
    is_fk: bool = False
    fk_target_table: Optional[str] = None
    fk_target_column: Optional[str] = None
    is_date_candidate: bool = False
    is_numeric_candidate: bool = False
    null_count: int = 0
    null_percentage: float = 0.0
    distinct_count: int = 0
    min_sample: Optional[str] = None
    max_sample: Optional[str] = None
    sample_values: List[str] = Field(default_factory=list, description="Low-cardinality safe samples")


class ForeignKeyModel(BaseModel):
    """Foreign key constraint link."""
    source_column: str
    target_table: str
    target_column: str
    on_update: Optional[str] = None
    on_delete: Optional[str] = None


class IndexModel(BaseModel):
    """Table index metadata."""
    name: str
    unique: bool = False
    columns: List[str] = Field(default_factory=list)


class TableModel(BaseModel):
    """Complete profiled metadata for a single table."""
    name: str
    row_count: int = 0
    columns: List[ColumnModel] = Field(default_factory=list)
    foreign_keys: List[ForeignKeyModel] = Field(default_factory=list)
    indexes: List[IndexModel] = Field(default_factory=list)
    primary_key_columns: List[str] = Field(default_factory=list)
    description: Optional[str] = None

    def get_column(self, col_name: str) -> Optional[ColumnModel]:
        col_lower = col_name.lower()
        for c in self.columns:
            if c.name.lower() == col_lower:
                return c
        return None


class DatabaseCatalog(BaseModel):
    """Full schema catalogue across all profiled tables."""
    source_fingerprint: str
    database_path: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_tables: int = 0
    total_rows: int = 0
    tables: Dict[str, TableModel] = Field(default_factory=dict)
    foreign_key_graph: List[Dict[str, str]] = Field(default_factory=list)

    def to_minimal_prompt_schema(self, table_names: Optional[List[str]] = None) -> str:
        """
        Formats a compact, schema-grounded representation of selected tables
        for LLM prompt context without leaking raw row data.
        """
        targets = table_names or list(self.tables.keys())
        lines = []
        for name in targets:
            tbl = self.tables.get(name)
            if not tbl:
                continue
            cols_desc = []
            for col in tbl.columns:
                pk_flag = " [PK]" if col.is_pk else ""
                fk_flag = f" [FK -> {col.fk_target_table}.{col.fk_target_column}]" if col.is_fk else ""
                cols_desc.append(f"  - {col.name} ({col.sqlite_type}){pk_flag}{fk_flag}")
            lines.append(f"Table: {name} (Rows: {tbl.row_count:,})")
            lines.extend(cols_desc)
            lines.append("")
        return "\n".join(lines).strip()


class JobStatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PreparationJobState(BaseModel):
    """Current state of a preparation job."""
    job_id: str
    status: JobStatusEnum = JobStatusEnum.PENDING
    progress_percent: int = 0
    current_table: Optional[str] = None
    message: str = "Job initialized"
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    tables_processed: int = 0
    total_tables: int = 0
    source_fingerprint: Optional[str] = None

