"""Base agent class for all CHAOS agents."""

import json
import re
from abc import ABC, abstractmethod
from typing import Any

from ..core.config import Config
from ..llm import LLMClient


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, config: Config, llm_client: LLMClient) -> None:
        self.config = config
        self.llm_client = llm_client
        self._system_prompt: str = ""

    @property
    def system_prompt(self) -> str:
        """Get the agent's system prompt."""
        return self._system_prompt

    @system_prompt.setter
    def system_prompt(self, value: str) -> None:
        """Set the agent's system prompt."""
        self._system_prompt = value

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the agent's main task."""
        ...

    def _call_llm(self, messages: list[dict[str, str]]) -> str:
        """
        Call the LLM with the given messages.

        Args:
            messages: List of message dicts with 'role' and 'content'.

        Returns:
            The LLM response text.
        """
        return self.llm_client.chat(messages, system=self._system_prompt)

    def _parse_response(self, response: str) -> dict[str, Any]:
        """
        Parse LLM response into structured format.

        Handles responses that may contain JSON in markdown code blocks.

        Args:
            response: Raw LLM response text.

        Returns:
            Parsed dictionary from JSON content.
        """
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", response)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # Try to find raw JSON object
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                json_str = json_match.group(0)
            else:
                # Return response as plain text in a dict
                return {"raw_response": response}

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {"raw_response": response, "parse_error": True}
