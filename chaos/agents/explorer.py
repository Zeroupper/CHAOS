"""Explorer agent - inspects datasets to discover schema for the planner."""

from collections import defaultdict

from ..data.registry import DataRegistry
from ..types import ColumnSchema, DatasetSchema

# Datasets with more columns than this get a grouped summary.
_MAX_COLUMNS_FULL = 50
# Number of example columns shown per prefix group in wide-dataset summaries.
_EXAMPLES_PER_GROUP = 3


class ExplorerAgent:
    """Inspects all registered datasets and returns their schemas."""

    def __init__(self, data_registry: DataRegistry) -> None:
        self._registry = data_registry

    def explore(self) -> list[DatasetSchema]:
        """Inspect all datasets and return structured schemas.

        Returns:
            List of DatasetSchema, one per registered dataset.
        """
        schemas = []
        for name, df in self._registry.get_all_dataframes().items():
            if len(df.columns) <= _MAX_COLUMNS_FULL:
                columns = self._full_columns(df)
            else:
                columns = self._summarized_columns(df)
            schemas.append(DatasetSchema(
                name=name,
                shape=[int(df.shape[0]), int(df.shape[1])],
                columns=columns,
            ))
        return schemas

    @staticmethod
    def _full_columns(df) -> list[ColumnSchema]:
        """Return a ColumnSchema for every column (small datasets)."""
        columns = []
        for col in df.columns:
            columns.append(ColumnSchema(
                name=col,
                dtype=str(df[col].dtype),
                nulls=int(df[col].isna().sum()),
                sample=[str(v) for v in df[col].dropna().head(3).tolist()],
            ))
        return columns

    @staticmethod
    def _summarized_columns(df) -> list[ColumnSchema]:
        """Return a compact summary for wide datasets.

        Groups columns by the prefix before the first ':' and shows a few
        examples per group with full detail plus a count of remaining columns.
        This prevents prompt bloat for datasets with thousands of columns
        (e.g. GLOBEM feature files with 5,000+ columns).
        """
        groups: dict[str, list[str]] = defaultdict(list)
        for col in df.columns:
            prefix = col.split(":")[0] if ":" in col else col
            groups[prefix].append(col)

        columns: list[ColumnSchema] = []
        for prefix, cols in sorted(groups.items()):
            examples = cols[:_EXAMPLES_PER_GROUP]
            for ex in examples:
                columns.append(ColumnSchema(
                    name=ex,
                    dtype=str(df[ex].dtype),
                    nulls=int(df[ex].isna().sum()),
                    sample=[str(v) for v in df[ex].dropna().head(3).tolist()],
                ))
            remaining = len(cols) - len(examples)
            if remaining > 0:
                extra_names = cols[len(examples):len(examples) + 5]
                columns.append(ColumnSchema(
                    name=f"... +{remaining} more '{prefix}:*' columns",
                    dtype="see examples above",
                    nulls=0,
                    sample=extra_names,
                ))

        return columns
