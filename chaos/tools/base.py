"""Base tool class for extensible tool system."""

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """
    Abstract base class for all tools.

    Tools can be used by agents (primarily InformationSeekingAgent)
    to perform specific operations like calculations, API calls, etc.
    """

    name: str = "base_tool"
    description: str = "Base tool description"

    @property
    def schema(self) -> dict[str, Any]:
        """
        JSON schema for the tool's parameters.

        Returns:
            Dictionary describing the tool's input parameters.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self._get_parameters_schema(),
        }

    @abstractmethod
    def _get_parameters_schema(self) -> dict[str, Any]:
        """Define the parameters schema for this tool."""
        ...

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """
        Execute the tool with given parameters.

        Args:
            **kwargs: Tool-specific parameters.

        Returns:
            Tool execution result.
        """
        ...

    def validate_params(self, params: dict[str, Any]) -> bool:
        """Validate parameters before execution."""
        # TODO: Implement JSON schema validation
        return True
