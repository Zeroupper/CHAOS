"""Configuration management for CHAOS."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """LLM provider configuration with automatic env loading."""

    model_config = SettingsConfigDict(env_prefix="OPENROUTER_")

    model: str = "qwen/qwen3.5-35b-a3b"
    base_url: str = "https://openrouter.ai/api/v1"
    # model: str = "qwen3.5:9b"
    # base_url: str | None = "http://localhost:11434/v1"
    api_key: str | None = None
    max_tokens: int = 16000

    @property
    def is_local(self) -> bool:
        """True when pointing at a local inference server."""
        return self.base_url is not None and ("localhost" in self.base_url or "127.0.0.1" in self.base_url)


@dataclass
class Config:
    """Main configuration for CHAOS."""

    llm: LLMConfig
    max_step_attempts: int = 5  # Max different approaches for a step
    max_research_turns: int = 10  # Max exploration turns for ExplorerAgent
    datasets_dir: Path = Path("datasets/gloss_sample")
    sandbox: bool = True  # Run LLM-generated code in Docker sandbox
    auto_approve: bool = True  # Auto-approve planner and sensemaker without human guidance
    verbose_export: bool = True  # Export full LLM transcripts alongside normal export
