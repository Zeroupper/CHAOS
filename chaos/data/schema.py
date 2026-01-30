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
        """Load schema from a YAML file."""
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
        return self._loaded

    @property
    def datasets(self) -> dict[str, Any]:
        return self._schema.get("datasets", {})

    @property
    def relationships(self) -> dict[str, Any]:
        return self._schema.get("relationships", {})

    @property
    def analysis_hints(self) -> dict[str, Any]:
        return self._schema.get("analysis_hints", {})

    def get_dataset_description(self, name: str) -> str:
        """Get description for a dataset."""
        schema = self.datasets.get(name)
        if schema:
            return schema.get("description", "").strip()
        return ""

    def get_column_descriptions(self, name: str) -> dict[str, str]:
        """Get column descriptions for a dataset."""
        schema = self.datasets.get(name)
        if not schema:
            return {}
        columns = schema.get("columns", {})
        return {col: info.get("description", "") for col, info in columns.items()}

    def get_column_metadata(self, name: str) -> dict[str, dict[str, Any]]:
        """Get full column metadata for a dataset."""
        schema = self.datasets.get(name)
        if schema:
            return schema.get("columns", {})
        return {}

    def format_for_prompt(self, verbose: bool = True) -> str:
        """
        Format schema for inclusion in LLM prompts.

        Args:
            verbose: If True, include full column details. If False, compact format.

        Returns:
            Formatted string with schema information.
        """
        if not self._loaded:
            return "No schema information available."

        lines = ["Available datasets with schema information:"]
        lines.append("")

        for name, schema in self.datasets.items():
            lines.append(self._format_dataset(name, schema, verbose))
            lines.append("")

        # Add relationships
        if self.relationships:
            lines.append("Dataset relationships:")
            for rel_name, rel_info in self.relationships.items():
                desc = rel_info.get("description", "").strip().replace("\n", " ")
                join_key = rel_info.get("join_key", "")
                lines.append(f"  - {rel_name}: {desc}")
                if join_key and verbose:
                    lines.append(f"    Join key: {join_key}")

        # Add analysis hints
        if self.analysis_hints and verbose:
            lines.append("")
            lines.append("Analysis hints:")
            for hint_name, hint_info in self.analysis_hints.items():
                desc = hint_info.get("description", "")
                datasets = hint_info.get("relevant_datasets", [])
                lines.append(f"  - {hint_name}: {desc}")
                if datasets:
                    ds_str = "all" if datasets == "all" else ", ".join(datasets)
                    lines.append(f"    Relevant datasets: {ds_str}")

        return "\n".join(lines)

    def _format_dataset(self, name: str, schema: dict, verbose: bool) -> str:
        """Format a single dataset schema."""
        lines = []
        desc = schema.get("description", "").strip()
        source = schema.get("source", "")
        columns = schema.get("columns", {})

        # Header
        header = f"- {name}"
        if source:
            header += f" ({source})"
        lines.append(header)

        if verbose:
            if desc:
                lines.append(f"  Description: {desc.replace(chr(10), ' ')}")
            category = schema.get("category", "")
            if category:
                lines.append(f"  Category: {category}")
            row_count = schema.get("row_count", "")
            if row_count:
                lines.append(f"  Approximate rows: {row_count}")

            # Detailed columns
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

                    values = col_info.get("values", [])
                    if values:
                        lines.append(f"      Values: {', '.join(values)}")
        else:
            # Compact: first line of desc + column list
            if desc:
                first_line = desc.split("\n")[0]
                lines[0] += f": {first_line}"
            if columns:
                col_strs = []
                for col_name, col_info in columns.items():
                    col_type = col_info.get("type", "?")
                    unit = col_info.get("unit", "")
                    if unit:
                        col_strs.append(f"{col_name}:{col_type}[{unit}]")
                    else:
                        col_strs.append(f"{col_name}:{col_type}")
                lines.append(f"  Columns: {', '.join(col_strs)}")

        return "\n".join(lines)
