"""Explorer agent - inspects datasets to discover schema for the planner."""

from ..data.registry import DataRegistry
from ..types import ColumnSchema, DatasetSchema


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
            columns = []
            for col in df.columns:
                columns.append(ColumnSchema(
                    name=col,
                    dtype=str(df[col].dtype),
                    nulls=int(df[col].isna().sum()),
                    sample=[str(v) for v in df[col].dropna().head(3).tolist()],
                ))
            schemas.append(DatasetSchema(
                name=name,
                shape=[int(df.shape[0]), int(df.shape[1])],
                columns=columns,
            ))
        return schemas
