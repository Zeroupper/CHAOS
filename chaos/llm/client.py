"""LLM client for OpenRouter API."""

import os
from typing import Any

import httpx

from ..core.config import LLMConfig


class LLMClient:
    """Client for making LLM API calls via OpenRouter."""

    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._api_key = config.api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self._api_key:
            raise ValueError(
                "OpenRouter API key not found. Set OPENROUTER_API_KEY environment "
                "variable or pass api_key in LLMConfig."
            )

    def chat(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
    ) -> str:
        """
        Send a chat completion request to the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            system: Optional system prompt to prepend.

        Returns:
            The LLM's response text.

        Raises:
            httpx.HTTPError: If the API request fails.
        """
        if system:
            messages = [{"role": "system", "content": system}] + messages

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/chaos-agents",
            "X-Title": "CHAOS Multi-Agent System",
        }

        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
        }

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                self.OPENROUTER_URL,
                headers=headers,
                json=payload,
            )
            if response.status_code >= 400:
                # Capture the actual error message from OpenRouter
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", response.text)
                except Exception:
                    error_msg = response.text
                raise httpx.HTTPStatusError(
                    f"OpenRouter API error: {error_msg}",
                    request=response.request,
                    response=response,
                )

        data = response.json()
        return data["choices"][0]["message"]["content"]
