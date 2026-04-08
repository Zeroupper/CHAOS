"""Configuration for the evaluation framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .types import RubricCriterion, TestCase


@dataclass
class RunConfiguration:
    """Configuration for a single evaluation run."""

    name: str  # e.g. "gpt4o_with_schema"
    model: str  # e.g. "openai/gpt-4o"
    pipeline: str = "chaos"  # "chaos" | "rag" | "direct"
    base_url: str | None = None  # override for local models (e.g. "http://localhost:11434/v1")
    system_prompt_overrides: dict[str, str] = field(default_factory=dict)
    sandbox: bool = False


@dataclass
class EvalConfig:
    """Top-level evaluation configuration."""

    judge_model: str = "anthropic/claude-sonnet-4-20250514"
    n_repeats: int = 5
    output_dir: str = "eval_results"
    datasets_dir: str = "datasets/gloss_sample"
    test_cases_path: str = "eval/test_cases/gloss/test_cases.yaml"
    max_workers: int = 3
    use_hints: bool = True
    models: list[RunConfiguration] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> EvalConfig:
        """Load evaluation config from a YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)

        models = []
        for cfg in data.get("models", []):
            models.append(RunConfiguration(
                name=cfg["name"],
                model=cfg["model"],
                pipeline=cfg.get("pipeline", "chaos"),
                base_url=cfg.get("base_url"),
                system_prompt_overrides=cfg.get("system_prompt_overrides", {}),
                sandbox=cfg.get("sandbox", False),
            ))

        return cls(
            judge_model=data.get("judge_model", cls.judge_model),
            n_repeats=data.get("n_repeats", cls.n_repeats),
            output_dir=data.get("output_dir", cls.output_dir),
            datasets_dir=data.get("datasets_dir", cls.datasets_dir),
            test_cases_path=data.get("test_cases_path", cls.test_cases_path),
            max_workers=data.get("max_workers", cls.max_workers),
            use_hints=data.get("use_hints", cls.use_hints),
            models=models,
        )


def load_test_cases(path: str | Path) -> list[dict[str, Any]]:
    """Load test cases from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("test_cases", [])


def parse_test_cases(raw_cases: list[dict[str, Any]]) -> list[TestCase]:
    """Parse raw YAML entries into TestCase objects."""
    cases = []
    for entry in raw_cases:
        rubric = []
        for r in entry.get("rubric", []):
            rubric.append(RubricCriterion(
                criterion=r["criterion"],
                weight=r["weight"],
                description=r["description"],
            ))
        cases.append(TestCase(
            id=entry["id"],
            category=entry["category"],
            difficulty=entry["difficulty"],
            query=entry["query"],
            hint=entry.get("hint", ""),
            rubric=rubric,
        ))
    return cases
