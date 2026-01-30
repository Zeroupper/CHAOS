"""Base agent class for all CHAOS agents."""

from abc import ABC
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel

from ..core.config import Config
from ..core.logger import get_logger
from ..llm.structured_client import StructuredLLMClient
from ..tools.base import BaseTool

T = TypeVar("T", bound=BaseModel)

# Type alias for tool execution callback
ToolExecutionCallback = Callable[[str, dict[str, Any], Any, bool], None]


def _default_tool_callback(
    tool_name: str, params: dict[str, Any], result: Any, success: bool
) -> None:
    """Default no-op callback for tool execution."""
    pass


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(
        self,
        config: Config,
        llm_client: StructuredLLMClient,
        tools: list[BaseTool] | None = None,
        on_tool_execute: ToolExecutionCallback | None = None,
    ) -> None:
        self.config = config
        self.llm_client = llm_client
        self._system_prompt: str = ""
        self._tools: dict[str, BaseTool] = {}
        self._logger = get_logger(self.__class__.__name__)
        self._on_tool_execute = on_tool_execute or _default_tool_callback

        # Register provided tools
        if tools:
            for tool in tools:
                self._tools[tool.name] = tool

    @property
    def system_prompt(self) -> str:
        """Get the agent's system prompt."""
        return self._system_prompt

    @system_prompt.setter
    def system_prompt(self, value: str) -> None:
        """Set the agent's system prompt."""
        self._system_prompt = value


    def get_tool(self, tool_name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(tool_name)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all tools available to this agent."""
        return [tool.schema for tool in self._tools.values()]

    def has_tool(self, tool_name: str) -> bool:
        """Check if agent has access to a specific tool."""
        return tool_name in self._tools

    def execute_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute.
            **kwargs: Tool parameters.

        Returns:
            Tool execution result.

        Raises:
            KeyError: If tool not found.
        """
        tool = self._tools.get(tool_name)
        if tool is None:
            raise KeyError(f"Tool '{tool_name}' not available to this agent")

        self._logger.info(f"Executing tool: {tool_name}")
        self._logger.debug(f"Tool params: {kwargs}")

        result = tool.execute(**kwargs)

        # Notify via callback
        success = result.get("success", True) if isinstance(result, dict) else True
        self._on_tool_execute(tool_name, kwargs, result, success)

        self._logger.debug(f"Tool result: {result}")
        return result

    def _call_llm(
        self,
        messages: list[dict[str, str]],
        response_model: type[T],
    ) -> T:
        """
        Call the LLM and get a validated Pydantic model response.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            response_model: Pydantic model class for response validation.

        Returns:
            Validated Pydantic model instance.
        """
        return self.llm_client.chat(
            messages,
            response_model,
            system=self._system_prompt,
        )
