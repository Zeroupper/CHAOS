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
        - schema.yaml: Loads rich metadata for datasets
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

                col_metadata = self._schema_loader.get_column_metadata(name)
                if col_metadata:
                    source.column_metadata = col_metadata

                self.register(source)

    @property
    def schema_loader(self) -> SchemaLoader:
        """Get the schema loader for rich schema access."""
        return self._schema_loader

    def get_sources_prompt(self, detailed: bool = True) -> str:
        """Generate a prompt describing available data sources for LLM."""
        if not self._sources:
            return "No data sources available."

        if detailed and self._schema_loader.is_loaded:
            return self._schema_loader.format_for_prompt(verbose=True)

        # Fallback to basic info
        lines = ["Available data sources:"]
        for source in self._sources.values():
            lines.append(f"\n- {source.name}: {source.description}")
            schema = source.get_schema()
            if schema.get("columns"):
                lines.append(f"  Columns: {', '.join(schema['columns'])}")
        return "\n".join(lines)
