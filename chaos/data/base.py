"""Base data source class."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd


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
            Dictionary describing available fields/columns, including:
            - columns: list of column names
            - types: dict mapping column names to their types
            - column_descriptions: dict mapping column names to descriptions
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

    def __init__(
        self,
        name: str,
        file_path: Path,
        description: str = "",
    ) -> None:
        self.name = name
        self.file_path = file_path
        self.description = description or f"CSV data from {file_path.name}"
        self.column_descriptions: dict[str, str] = {}
        self.column_metadata: dict[str, dict[str, Any]] = {}
        self._data: pd.DataFrame | None = None

    def connect(self) -> None:
        """Load CSV file into memory."""
        if self._data is None:
            self._data = pd.read_csv(self.file_path)

    def disconnect(self) -> None:
        """Clear loaded data."""
        self._data = None

    def get_schema(self) -> dict[str, Any]:
        """Get CSV column schema with rich metadata if available."""
        self.connect()
        if self._data is None:
            return {"columns": [], "types": {}, "row_count": 0}

        schema = {
            "columns": list(self._data.columns),
            "types": {col: str(dtype) for col, dtype in self._data.dtypes.items()},
            "row_count": len(self._data),
            "column_descriptions": self.column_descriptions,
        }

        # Include rich column metadata if available
        if self.column_metadata:
            schema["column_metadata"] = self.column_metadata

        return schema

    def get_example_queries(self) -> list[str]:
        return [
            f"exec(code=\"result = df['column'].mean()\") - Compute average of a column in {self.name}",
            f"exec(code=\"result = len(df)\") - Count rows in {self.name}",
            f"exec(code=\"result = df.groupby('col')['val'].sum().to_dict()\") - Group and aggregate",
            f"exec(code=\"result = df.describe().to_dict()\") - Get statistical summary",
        ]

    def query(self, query: str, **kwargs: Any) -> Any:
        """
        Execute query on CSV data.

        Args:
            query: Query type to execute. Use "exec" to run Python code.
            **kwargs: Query parameters. For "exec", pass code="<python code>".

        Returns:
            Query results as dict.
        """
        self.connect()
        if self._data is None:
            return {"error": "Data not loaded"}

        try:
            if query == "exec":
                import json as _json

                import numpy as np

                code = kwargs.get("code", "")
                if not code:
                    return {"error": "No code provided"}

                # Create restricted namespace with DataFrame and common libraries
                namespace = {
                    "df": self._data.copy(),
                    "pd": pd,
                    "np": np,
                    "result": None,
                }

                try:
                    # Execute code with restricted builtins
                    exec(code, {"__builtins__": {}}, namespace)

                    # Get the result
                    result = namespace.get("result")

                    # Serialize result to string for size control
                    try:
                        if hasattr(result, "to_dict"):
                            result_str = _json.dumps(result.to_dict())
                        elif hasattr(result, "tolist"):
                            result_str = _json.dumps(result.tolist())
                        else:
                            result_str = _json.dumps(result, default=str)
                    except (TypeError, ValueError):
                        result_str = str(result)

                    # Truncate if too large
                    max_chars = 5000
                    truncated = False
                    if len(result_str) > max_chars:
                        result_str = result_str[:max_chars]
                        truncated = True

                    return {
                        "result": result_str,
                        "truncated": truncated,
                    }

                except Exception as e:
                    return {"error": f"Code execution failed: {e}"}

            else:
                return {"error": f"Unknown query type '{query}'. Use 'exec' with code parameter."}

        except Exception as e:
            return {"error": str(e)}

