"""Data source registry for managing available data sources."""

from pathlib import Path
from typing import Any

from .base import BaseDataSource, CSVDataSource
from .schema import SchemaLoader


class DataRegistry:
    """
    Registry for managing and discovering data sources.

    Data sources can be registered manually or auto-discovered from
    a datasets directory.
    """

    def __init__(self) -> None:
        self._sources: dict[str, BaseDataSource] = {}
        self._schema_loader = SchemaLoader()

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
        - schema.yaml: Loads rich metadata for datasets

        Args:
            datasets_dir: Directory containing data files.
        """
        if not datasets_dir.exists():
            return

        # Try to load schema.yaml first
        schema_path = datasets_dir / "data_schema.yaml"
        self._schema_loader.load(schema_path)

        # Discover CSV files
        for csv_file in datasets_dir.glob("**/*.csv"):
            name = csv_file.stem
            if name not in self._sources:
                # Get description from schema if available
                description = self._schema_loader.get_dataset_description(name)
                if not description:
                    description = f"Data from {csv_file.name}"

                source = CSVDataSource(
                    name=name,
                    file_path=csv_file,
                    description=description,
                )

                # Enrich with column descriptions from schema
                col_descriptions = self._schema_loader.get_column_descriptions(name)
                if col_descriptions:
                    source.column_descriptions = col_descriptions

                # Store full column metadata for richer prompts
                col_metadata = self._schema_loader.get_column_metadata(name)
                if col_metadata:
                    source.column_metadata = col_metadata

                self.register(source)

    @property
    def schema_loader(self) -> SchemaLoader:
        """Get the schema loader for rich schema access."""
        return self._schema_loader

    def get_sources_prompt(self, detailed: bool = True) -> str:
        """
        Generate a prompt describing available data sources for LLM.

        Args:
            detailed: If True and schema is loaded, use rich schema info.

        Returns:
            Formatted string describing available data sources.
        """
        if not self._sources:
            return "No data sources available."

        # Use rich schema information if available
        if detailed and self._schema_loader.is_loaded:
            return self._schema_loader.format_all_datasets_for_prompt()

        # Fallback to basic info
        lines = ["Available data sources:"]
        for source in self._sources.values():
            lines.append(f"\n- {source.name}: {source.description}")
            schema = source.get_schema()
            if schema.get("columns"):
                lines.append(f"  Columns: {', '.join(schema['columns'])}")
        return "\n".join(lines)

    def get_compact_sources_prompt(self) -> str:
        """
        Generate a compact prompt for space-constrained contexts.

        Returns:
            Compact formatted string.
        """
        if self._schema_loader.is_loaded:
            return self._schema_loader.format_compact_for_prompt()

        # Fallback
        if not self._sources:
            return "No data sources available."

        lines = []
        for source in self._sources.values():
            schema = source.get_schema()
            cols = schema.get("columns", [])
            lines.append(f"- {source.name}: {', '.join(cols[:10])}")
        return "\n".join(lines)
