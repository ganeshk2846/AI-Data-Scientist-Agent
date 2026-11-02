"""
backend/app/db/__init__.py
Database abstraction package for the Conversational Data Scientist Agent.
"""

from backend.app.db.base import BaseDatabaseAdapter, QueryResult
from backend.app.db.adapters import SQLiteAdapter, PostgresAdapter, MySQLAdapter
from backend.app.db.manager import db_manager, DatabaseConnectionManager
from backend.app.db.connection import (
    get_readonly_connection,
    get_readonly_uri,
    check_database_readiness,
    verify_database_immutability,
)

__all__ = [
    "BaseDatabaseAdapter",
    "QueryResult",
    "SQLiteAdapter",
    "PostgresAdapter",
    "MySQLAdapter",
    "db_manager",
    "DatabaseConnectionManager",
    "get_readonly_connection",
    "get_readonly_uri",
    "check_database_readiness",
    "verify_database_immutability",
]
