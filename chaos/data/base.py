"""Data source classes."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd


class BaseDataSource(ABC):
    """Abstract base class for data sources."""

    name: str
    description: str

    @property
    def info(self) -> dict[str, Any]:
        """Get data source information for LLM context."""
        return {
            "name": self.name,
            "description": self.description
        }

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the data source."""
        ...


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
        self._data: pd.DataFrame | None = None

    def connect(self) -> None:
        """Load CSV file into memory."""
        if self._data is None:
            self._data = pd.read_csv(self.file_path)

    @property
    def data(self) -> pd.DataFrame | None:
        """Access the loaded DataFrame."""
        return self._data
