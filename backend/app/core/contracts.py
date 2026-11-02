"""
backend/app/core/contracts.py
Frozen Pydantic v2 data contracts for Version 2 Architecture.
Establishes stable schema interfaces between Subsystems:
1. Connection & Discovery
2. Metadata & Semantics
3. Hybrid Retrieval
4. Safety & Execution
5. Analytics & Visualization
6. Orchestration & API
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class SupportedEngine(str, Enum):
    """Supported database engines for single active connection."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"


class ConnectionStatus(str, Enum):
    """Status lifecycle of active database connection."""
    READY = "READY"
    ONBOARDING = "ONBOARDING"
    ERROR = "ERROR"
    DISCONNECTED = "DISCONNECTED"


class MetricStatus(str, Enum):
    """Three-tier semantic metric lifecycle status."""
    AUTO_INFERRED = "AUTO_INFERRED"           # Tier 1: Draft/heuristic derivation
    VALIDATED_CANDIDATE = "VALIDATED_CANDIDATE" # Tier 2: AST-checked and execution-tested
    SYSTEM_APPROVED = "SYSTEM_APPROVED"         # Domain-validated baseline canonical metric
    USER_APPROVED = "USER_APPROVED"             # Explicit human-verified authoritative ground truth


# =====================================================================
# 1. Connection & Active Database Contracts
# =====================================================================

class ActiveDatabaseConfig(BaseModel):
    """Configuration contract for single active database connection."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(default="active_db", description="Unique identifier for active connection")
    name: str = Field(..., description="Human-readable database name or filename")
    engine: SupportedEngine = Field(..., description="Database engine type")
    file_path: Optional[str] = Field(default=None, description="SQLite database file path")
    host: Optional[str] = Field(default=None, description="PostgreSQL / MySQL host")
    port: Optional[int] = Field(default=None, description="PostgreSQL / MySQL port")
    database: Optional[str] = Field(default=None, description="PostgreSQL / MySQL database name")
    username: Optional[str] = Field(default=None, description="Database username (read-only)")
    status: ConnectionStatus = Field(default=ConnectionStatus.READY)
    fingerprint: Optional[str] = Field(default=None, description="SHA-256 schema fingerprint")
    read_only: bool = Field(default=True, description="Strict read-only enforcement")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DatabaseStatusResponse(BaseModel):
    """REST API contract for GET /api/v1/database/status."""
    model_config = ConfigDict(frozen=True)

    connected: bool
    engine: Optional[SupportedEngine] = None
    database_name: Optional[str] = None
    status: ConnectionStatus
    tables_count: int = 0
    total_rows: int = 0
    fingerprint: Optional[str] = None
    read_only: bool = True
    onboarding_progress: Optional[float] = None
    error_message: Optional[str] = None


# =====================================================================
# 2. Schema Discovery & Catalog Contracts
# =====================================================================

class ColumnProfile(BaseModel):
    """Statistical profile of a database column."""
    model_config = ConfigDict(frozen=True)

    name: str
    data_type: str
    is_primary_key: bool = False
    is_nullable: bool = True
    is_foreign_key: bool = False
    foreign_key_target: Optional[str] = None   # "target_table.target_column"
    null_count: int = 0
    null_percentage: float = 0.0
    distinct_count: int = 0
    min_sample: Optional[str] = None
    max_sample: Optional[str] = None
    top_categories: Optional[List[str]] = None
    profiling_skipped: bool = False


class ForeignKeyRelation(BaseModel):
    """Foreign key relationship edge between tables."""
    model_config = ConfigDict(frozen=True)

    source_table: str
    source_column: str
    target_table: str
    target_column: str
    is_inferred: bool = False  # True if inferred by naming heuristic, False if DDL FK


class TableMetadata(BaseModel):
    """Complete metadata and column profiles for a single table."""
    model_config = ConfigDict(frozen=True)

    name: str
    row_count: int = 0
    column_count: int = 0
    primary_keys: List[str] = Field(default_factory=list)
    foreign_keys: List[ForeignKeyRelation] = Field(default_factory=list)
    columns: Dict[str, ColumnProfile] = Field(default_factory=dict)
    indexes: List[Dict[str, Any]] = Field(default_factory=list)
    description: Optional[str] = None


class DatabaseCatalog(BaseModel):
    """Complete dynamic schema catalog of the currently connected database."""
    model_config = ConfigDict(frozen=True)

    database_name: str
    engine: SupportedEngine
    fingerprint: str
    tables_count: int
    total_rows: int
    tables: Dict[str, TableMetadata]
    relationship_graph: List[ForeignKeyRelation] = Field(default_factory=list)
    date_ranges: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# =====================================================================
# 3. Semantic Layer Contracts
# =====================================================================

class SemanticMetricDefinition(BaseModel):
    """Contract for database-specific business metrics."""
    model_config = ConfigDict(frozen=True)

    metric_key: str = Field(..., description="Unique metric key, e.g. 'net_revenue'")
    display_name: str = Field(..., description="Human readable name, e.g. 'Net Revenue'")
    formula_sql: str = Field(..., description="SQL calculation expression or snippet")
    status: MetricStatus = Field(default=MetricStatus.AUTO_INFERRED)
    derivation_type: str = Field(default="INFERRED", description="'INFERRED' or 'CUSTOM_USER'")
    verified_by: Optional[str] = None
    description: Optional[str] = None
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# =====================================================================
# 4. Orchestration & Chat API Contracts
# =====================================================================

class ChatQueryRequest(BaseModel):
    """REST API contract for natural language analytical queries."""
    question: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None


class MultiAgentWorkflowResult(BaseModel):
    """Unified result envelope produced by the multi-agent workflow."""
    question: str
    intent: str
    route: str
    is_answerable: bool
    refusal_reason: Optional[str] = None
    sql_generated: Optional[str] = None
    sql_ast_valid: bool = False
    sql_execution_success: bool = False
    row_count: int = 0
    columns: List[str] = Field(default_factory=list)
    sample_rows: List[Dict[str, Any]] = Field(default_factory=list)
    executive_narrative: Optional[str] = None
    chart_plotly_json: Optional[str] = None
    execution_time_ms: float = 0.0
    active_database: str
    engine: SupportedEngine
    session_id: str
