"""Configuration management for CHAOS."""

from dataclasses import dataclass, field
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """LLM provider configuration with automatic env loading."""

    model_config = SettingsConfigDict(env_prefix="OPENROUTER_")

    provider: str = "openrouter"
    model: str = "openai/chatgpt-4o-latest"
    api_key: str | None = None
    max_tokens: int = 4096  # Safe default that works with most API key limits


@dataclass
class LogConfig:
    """Logging configuration."""

    level: str = "WARNING"
    use_colors: bool = True


@dataclass
class Config:
    """Main configuration for CHAOS."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    log: LogConfig = field(default_factory=LogConfig)
    max_step_attempts: int = 5  # Max different approaches for a step
    max_code_retries: int = 3  # Max retries for failed code execution
    datasets_dir: Path = field(default_factory=lambda: Path("datasets"))
