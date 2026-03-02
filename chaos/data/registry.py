"""Data source registry for managing available data sources."""

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from .base import BaseDataSource, CSVDataSource

logger = logging.getLogger(__name__)


class DataRegistry:
    """
    Registry for managing and discovering data sources.

    Data sources can be registered manually or auto-discovered from
    a datasets directory.
    """

    def __init__(self) -> None:
        self._sources: dict[str, BaseDataSource] = {}

    def register(self, source: BaseDataSource) -> None:
        """Register a data source."""
        self._sources[source.name] = source

    def get(self, name: str) -> BaseDataSource | None:
        """Get a data source by name."""
        return self._sources.get(name)

    def list_sources(self) -> list[dict[str, Any]]:
        """List all registered data sources with their info."""
        return [source.info for source in self._sources.values()]

    def auto_discover(self, datasets_dir: Path) -> None:
        """
        Auto-discover data sources from a directory.

        Currently supports:
        - CSV files: Registered as CSVDataSource
        """
        if not datasets_dir.exists():
            return

        for csv_file in datasets_dir.glob("**/*.csv"):
            name = csv_file.stem
            if name not in self._sources:
                source = CSVDataSource(
                    name=name,
                    file_path=csv_file,
                    description=f"Data from {csv_file.name}",
                )
                self.register(source)

    def get_all_dataframes(self) -> dict[str, pd.DataFrame]:
        """Load and return all source DataFrames by name."""
        frames: dict[str, pd.DataFrame] = {}
        for name, source in self._sources.items():
            try:
                source.connect()
                if hasattr(source, "data") and source.data is not None:
                    frames[name] = source.data
            except Exception as e:
                logger.warning(f"Failed to load source '{name}': {e}")
        return frames

    def get_sources_prompt(self) -> str:
        """Generate a prompt describing available data sources for LLM."""
        if not self._sources:
            return "No data sources available."

        names = list(self._sources.keys())
        lines = [f"Available datasets (pre-loaded variables: {', '.join(names)}):"]
        for source in self._sources.values():
            lines.append(f"\n- `{source.name}`: {source.description}")
        return "\n".join(lines)
