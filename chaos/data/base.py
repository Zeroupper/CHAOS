"""Base data source class."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseDataSource(ABC):
    """
    Abstract base class for data sources.

    Data sources provide access to datasets that agents can query.
    Examples: CSV files, databases, APIs, etc.
    """

    name: str = "base_source"
    description: str = "Base data source description"

    @property
    def info(self) -> dict[str, Any]:
        """Get data source information for LLM context."""
        return {
            "name": self.name,
            "description": self.description,
            "schema": self.get_schema(),
            "example_queries": self.get_example_queries(),
        }

    @abstractmethod
    def get_schema(self) -> dict[str, Any]:
        """
        Get the schema of this data source.

        Returns:
            Dictionary describing available fields/columns.
        """
        ...

    @abstractmethod
    def get_example_queries(self) -> list[str]:
        """
        Get example queries for this data source.

        Returns:
            List of example query strings.
        """
        ...

    @abstractmethod
    def query(self, query: str, **kwargs: Any) -> Any:
        """
        Execute a query against this data source.

        Args:
            query: Query string or structured query.
            **kwargs: Additional query parameters.

        Returns:
            Query results.
        """
        ...

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the data source."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the data source."""
        ...

    def __enter__(self) -> "BaseDataSource":
        self.connect()
        return self

    def __exit__(self, *args: Any) -> None:
        self.disconnect()


class CSVDataSource(BaseDataSource):
    """Data source for CSV files."""

    def __init__(self, name: str, file_path: Path, description: str = "") -> None:
        self.name = name
        self.file_path = file_path
        self.description = description or f"CSV data from {file_path.name}"
        self._data = None

    def get_schema(self) -> dict[str, Any]:
        """Get CSV column schema."""
        # TODO: Implement schema extraction
        return {"columns": [], "types": {}}

    def get_example_queries(self) -> list[str]:
        return [
            f"Get all rows from {self.name}",
            f"Filter {self.name} where column_name = value",
        ]

    def query(self, query: str, **kwargs: Any) -> Any:
        """Execute query on CSV data."""
        # TODO: Implement query execution (e.g., using pandas)
        return None

    def connect(self) -> None:
        """Load CSV file."""
        # TODO: Load CSV using pandas
        pass

    def disconnect(self) -> None:
        """Clear loaded data."""
        self._data = None
