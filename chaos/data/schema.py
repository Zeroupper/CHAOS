"""Schema loader for dataset metadata from schema.yaml files."""

from pathlib import Path
from typing import Any

import yaml


class SchemaLoader:
    """
    Loads and provides access to dataset schema metadata.

    The schema.yaml file contains rich information about datasets including:
    - Column descriptions and types
    - Value ranges and units
    - Relationships between datasets
    - Analysis hints
    """

    def __init__(self) -> None:
        self._schema: dict[str, Any] = {}
        self._loaded = False

    def load(self, schema_path: Path) -> bool:
        """
        Load schema from a YAML file.

        Args:
            schema_path: Path to schema.yaml file.

        Returns:
            True if loaded successfully, False otherwise.
        """
        if not schema_path.exists():
            return False

        try:
            with open(schema_path) as f:
                self._schema = yaml.safe_load(f) or {}
            self._loaded = True
            return True
        except Exception:
            return False

    @property
    def is_loaded(self) -> bool:
        """Check if schema has been loaded."""
        return self._loaded

    @property
    def version(self) -> str:
        """Get schema version."""
        return self._schema.get("version", "unknown")

    @property
    def description(self) -> str:
        """Get overall schema description."""
        return self._schema.get("description", "").strip()

    @property
    def common_fields(self) -> dict[str, Any]:
        """Get common fields shared across datasets."""
        return self._schema.get("common_fields", {})

    @property
    def datasets(self) -> dict[str, Any]:
        """Get all dataset definitions."""
        return self._schema.get("datasets", {})

    @property
    def relationships(self) -> dict[str, Any]:
        """Get relationship definitions between datasets."""
        return self._schema.get("relationships", {})

    @property
    def analysis_hints(self) -> dict[str, Any]:
        """Get analysis hints for common queries."""
        return self._schema.get("analysis_hints", {})

    def get_dataset_schema(self, name: str) -> dict[str, Any] | None:
        """
        Get schema for a specific dataset.

        Args:
            name: Dataset name (e.g., 'garmin_hr', 'ios_activity').

        Returns:
            Dataset schema dict or None if not found.
        """
        return self.datasets.get(name)

    def get_dataset_description(self, name: str) -> str:
        """Get description for a dataset."""
        schema = self.get_dataset_schema(name)
        if schema:
            return schema.get("description", "").strip()
        return ""

    def get_dataset_columns(self, name: str) -> dict[str, Any]:
        """
        Get column definitions for a dataset.

        Args:
            name: Dataset name.

        Returns:
            Dict mapping column names to their definitions.
        """
        schema = self.get_dataset_schema(name)
        if schema:
            return schema.get("columns", {})
        return {}

    def get_column_descriptions(self, name: str) -> dict[str, str]:
        """
        Get column descriptions for a dataset.

        Args:
            name: Dataset name.

        Returns:
            Dict mapping column names to description strings.
        """
        columns = self.get_dataset_columns(name)
        return {
            col: info.get("description", "")
            for col, info in columns.items()
        }

    def get_column_metadata(self, name: str) -> dict[str, dict[str, Any]]:
        """
        Get full column metadata for a dataset.

        Args:
            name: Dataset name.

        Returns:
            Dict mapping column names to metadata dicts with type, unit, etc.
        """
        return self.get_dataset_columns(name)

    def format_dataset_for_prompt(self, name: str) -> str:
        """
        Format dataset schema for inclusion in LLM prompts.

        Args:
            name: Dataset name.

        Returns:
            Formatted string with rich schema information.
        """
        schema = self.get_dataset_schema(name)
        if not schema:
            return f"- {name}: No schema information available"

        lines = []

        # Dataset description
        desc = schema.get("description", "").strip().replace("\n", " ")
        source = schema.get("source", "")
        category = schema.get("category", "")

        header = f"- {name}"
        if source:
            header += f" ({source})"
        lines.append(header)

        if desc:
            lines.append(f"  Description: {desc}")
        if category:
            lines.append(f"  Category: {category}")

        # Row count
        row_count = schema.get("row_count", "")
        if row_count:
            lines.append(f"  Approximate rows: {row_count}")

        # Columns with details
        columns = schema.get("columns", {})
        if columns:
            lines.append("  Columns:")
            for col_name, col_info in columns.items():
                col_type = col_info.get("type", "unknown")
                col_desc = col_info.get("description", "")
                unit = col_info.get("unit", "")
                typical_range = col_info.get("typical_range", [])

                col_line = f"    - {col_name} ({col_type})"
                if unit:
                    col_line += f" [{unit}]"
                if col_desc:
                    col_line += f": {col_desc}"
                if typical_range:
                    col_line += f" (range: {typical_range[0]}-{typical_range[1]})"

                lines.append(col_line)

                # Add enum values if present
                values = col_info.get("values", [])
                if values:
                    lines.append(f"      Values: {', '.join(values)}")

        return "\n".join(lines)

    def format_all_datasets_for_prompt(self) -> str:
        """
        Format all datasets for inclusion in LLM prompts.

        Returns:
            Formatted string with all dataset schemas.
        """
        if not self._loaded:
            return "No schema information available."

        lines = ["Available datasets with schema information:"]
        lines.append("")

        for name in self.datasets:
            lines.append(self.format_dataset_for_prompt(name))
            lines.append("")

        # Add relationships if present
        if self.relationships:
            lines.append("Dataset relationships:")
            for rel_name, rel_info in self.relationships.items():
                desc = rel_info.get("description", "").strip().replace("\n", " ")
                join_key = rel_info.get("join_key", "")
                lines.append(f"  - {rel_name}: {desc}")
                if join_key:
                    lines.append(f"    Join key: {join_key}")

        # Add analysis hints if present
        if self.analysis_hints:
            lines.append("")
            lines.append("Analysis hints:")
            for hint_name, hint_info in self.analysis_hints.items():
                desc = hint_info.get("description", "")
                datasets = hint_info.get("relevant_datasets", [])
                lines.append(f"  - {hint_name}: {desc}")
                if datasets:
                    if datasets == "all":
                        lines.append("    Relevant datasets: all")
                    else:
                        lines.append(f"    Relevant datasets: {', '.join(datasets)}")

        return "\n".join(lines)

    def format_compact_for_prompt(self) -> str:
        """
        Format a compact version of schema for space-constrained prompts.

        Returns:
            Compact formatted string.
        """
        if not self._loaded:
            return "No schema information available."

        lines = ["Datasets:"]

        for name, schema in self.datasets.items():
            source = schema.get("source", "")
            desc = schema.get("description", "").strip().split("\n")[0]  # First line
            columns = schema.get("columns", {})

            header = f"- {name}"
            if source:
                header += f" ({source})"
            header += f": {desc}"
            lines.append(header)

            # List key columns with types
            col_strs = []
            for col_name, col_info in columns.items():
                col_type = col_info.get("type", "?")
                unit = col_info.get("unit", "")
                if unit:
                    col_strs.append(f"{col_name}:{col_type}[{unit}]")
                else:
                    col_strs.append(f"{col_name}:{col_type}")

            if col_strs:
                lines.append(f"  Columns: {', '.join(col_strs)}")

        return "\n".join(lines)
