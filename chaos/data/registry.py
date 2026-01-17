"""Data source registry for managing available data sources."""

from pathlib import Path
from typing import Any

from .base import BaseDataSource, CSVDataSource


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

    def unregister(self, name: str) -> None:
        """Remove a data source from the registry."""
        self._sources.pop(name, None)

    def get(self, name: str) -> BaseDataSource | None:
        """Get a data source by name."""
        return self._sources.get(name)

    def list_sources(self) -> list[dict[str, Any]]:
        """List all registered data sources with their info."""
        return [source.info for source in self._sources.values()]

    def query_source(self, name: str, query: str, **kwargs: Any) -> Any:
        """
        Query a data source by name.

        Args:
            name: Data source name.
            query: Query string.
            **kwargs: Additional query parameters.

        Returns:
            Query results.

        Raises:
            KeyError: If data source not found.
        """
        source = self._sources.get(name)
        if source is None:
            raise KeyError(f"Data source '{name}' not found in registry")
        return source.query(query, **kwargs)

    def auto_discover(self, datasets_dir: Path) -> None:
        """
        Auto-discover data sources from a directory.

        Currently supports:
        - CSV files: Registered as CSVDataSource

        Args:
            datasets_dir: Directory containing data files.
        """
        if not datasets_dir.exists():
            return

        # Discover CSV files
        for csv_file in datasets_dir.glob("**/*.csv"):
            name = csv_file.stem
            if name not in self._sources:
                source = CSVDataSource(
                    name=name,
                    file_path=csv_file,
                    description=f"Data from {csv_file.name}",
                )
                self.register(source)

    def get_sources_prompt(self) -> str:
        """Generate a prompt describing available data sources for LLM."""
        if not self._sources:
            return "No data sources available."

        lines = ["Available data sources:"]
        for source in self._sources.values():
            lines.append(f"\n- {source.name}: {source.description}")
            schema = source.get_schema()
            if schema.get("columns"):
                lines.append(f"  Columns: {', '.join(schema['columns'])}")
        return "\n".join(lines)
