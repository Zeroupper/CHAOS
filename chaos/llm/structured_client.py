"""Instructor-based LLM client for structured outputs."""

from datetime import datetime, timezone
from typing import Any, TypeVar

import instructor
from openai import OpenAI
from pydantic import BaseModel

from ..core.config import LLMConfig

T = TypeVar("T", bound=BaseModel)


class StructuredLLMClient:
    """
    LLM client that returns validated Pydantic models.

    Works with ANY OpenAI-compatible endpoint: OpenRouter, Ollama, vLLM, etc.
    """

    def __init__(self, config: LLMConfig, max_retries: int = 3) -> None:
        self.config = config
        self.max_retries = max_retries
        self.transcript: list[dict[str, Any]] = []

        if not config.base_url:
            raise ValueError(
                "LLM base_url is not set. Set it in config."
            )

        if not config.is_local and not config.api_key:
            raise ValueError(
                "OpenRouter API key not found. Set OPENROUTER_API_KEY environment "
                "variable or pass api_key in LLMConfig.\n"
                "For local models, pass --base-url http://localhost:11434/v1"
            )

        self._openai_client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key or "<local-api-key>",
            timeout=20.0,
            default_headers=(
                {}
                if config.is_local
                else {
                    "HTTP-Referer": "https://github.com/chaos-agents",
                    "X-Title": "CHAOS Multi-Agent System",
                }
            ),
        )

        # Wrap with Instructor for structured outputs
        self._client = instructor.from_openai(
            self._openai_client,
            mode=instructor.Mode.JSON,
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        response_model: type[T],
        system: str | None = None,
    ) -> T:
        """
        Get a validated structured response.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            response_model: Pydantic model class for response validation.
            system: Optional system prompt to prepend.

        Returns:
            Validated Pydantic model instance.
        """
        if system:
            messages = [{"role": "system", "content": system}] + messages

        result = self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            response_model=response_model,
            max_retries=self.max_retries,
        )

        self.transcript.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": response_model.__name__,
            "system_prompt": system,
            "messages": [m for m in messages if m.get("role") != "system"],
            "response": result.model_dump(),
        })

        return result
