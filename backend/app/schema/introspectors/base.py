"""
backend/app/schema/introspectors/base.py
Abstract base class for engine-specific database schema introspectors.
"""

from abc import ABC, abstractmethod
from typing import List
from backend.app.schema.models import ColumnModel, ForeignKeyModel, IndexModel


class BaseIntrospector(ABC):
    """Abstract interface for database introspection."""

    @abstractmethod
    def introspect_tables(self) -> List[str]:
        """Returns all table names in the active database schema."""
        pass

    @abstractmethod
    def introspect_views(self) -> List[str]:
        """Returns all view names in the active database schema."""
        pass

    @abstractmethod
    def introspect_columns(self, table_name: str) -> List[ColumnModel]:
        """Discovers column definitions, data types, and primary key flags."""
        pass

    @abstractmethod
    def introspect_primary_keys(self, table_name: str) -> List[str]:
        """Returns primary key column names for specified table."""
        pass

    @abstractmethod
    def introspect_foreign_keys(self, table_name: str) -> List[ForeignKeyModel]:
        """Discovers foreign key relationships for specified table."""
        pass

    @abstractmethod
    def introspect_indexes(self, table_name: str) -> List[IndexModel]:
        """Discovers index metadata for specified table."""
        pass

    @abstractmethod
    def get_table_row_count(self, table_name: str) -> int:
        """Returns row count for specified table."""
        pass
