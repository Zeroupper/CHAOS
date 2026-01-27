"""Tool registry for managing available tools."""

from typing import Any

from .base import BaseTool


class ToolRegistry:
    """
    Registry for managing and discovering tools.

    Tools can be registered manually or auto-discovered from a directory.
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """
        Register a tool.

        Args:
            tool: Tool instance to register.
        """
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools with their schemas."""
        return [tool.schema for tool in self._tools.values()]

    def execute_tool(self, name: str, **kwargs: Any) -> Any:
        """
        Execute a tool by name.

        Args:
            name: Tool name.
            **kwargs: Tool parameters.

        Returns:
            Tool execution result.

        Raises:
            KeyError: If tool not found.
        """
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Tool '{name}' not found in registry")

        if not tool.validate_params(kwargs):
            raise ValueError(f"Invalid parameters for tool '{name}'")

        return tool.execute(**kwargs)
