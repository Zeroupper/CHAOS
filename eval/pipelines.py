"""Pipeline functions for evaluation: CHAOS and RAG."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from chaos.core.config import Config, LLMConfig
from chaos.core.orchestrator import Orchestrator
from chaos.data.registry import DataRegistry
from chaos.llm.structured_client import StructuredLLMClient

from .config import EvalConfig, RunConfiguration
from .types import EvalResult, RunMetrics, TestCase

T_co = type[BaseModel]


class InstrumentedLLMClient(StructuredLLMClient):
    """StructuredLLMClient that tracks token usage from instructor responses."""

    def __init__(self, config: LLMConfig, max_retries: int = 3) -> None:
        super().__init__(config, max_retries)
        self._total_tokens = 0
        self._input_tokens = 0
        self._output_tokens = 0

    def chat(
        self,
        messages: list[dict[str, str]],
        response_model: type[T_co],
        system: str | None = None,
    ) -> T_co:
        result = super().chat(messages, response_model, system)
        raw = getattr(result, "_raw_response", None)
        if raw and raw.usage:
            self._total_tokens += raw.usage.total_tokens
            self._input_tokens += raw.usage.prompt_tokens
            self._output_tokens += raw.usage.completion_tokens
        return result

    def get_metrics(self) -> dict[str, int]:
        return {
            "total_tokens": self._total_tokens,
            "input_tokens": self._input_tokens,
            "output_tokens": self._output_tokens,
        }


def run_chaos(
    eval_config: EvalConfig,
    run_config: RunConfiguration,
    case: TestCase,
    repeat: int,
    data_registry: DataRegistry | None = None,
) -> EvalResult:
    """Run a single test case through the CHAOS orchestrator."""
    llm_config = LLMConfig(model=run_config.model, base_url=run_config.base_url)
    llm_client = InstrumentedLLMClient(llm_config)

    config = Config(
        llm=llm_config,
        datasets_dir=Path(eval_config.datasets_dir),
        sandbox=run_config.sandbox,
        auto_approve=True,
    )

    if data_registry is None:
        data_registry = DataRegistry()
        data_registry.auto_discover(config.datasets_dir)

    orchestrator = Orchestrator(
        config=config,
        llm_client=llm_client,
        data_registry=data_registry,
    )

    # Apply system prompt overrides
    for agent_name, prompt in run_config.system_prompt_overrides.items():
        agent = getattr(orchestrator, agent_name, None)
        if agent and hasattr(agent, "system_prompt"):
            agent.system_prompt = prompt

    query = case.query
    if eval_config.use_hints and case.hint:
        query = f"{query}\n\nHint: {case.hint}"

    start = time.time()

    try:
        raw_result = orchestrator.run(query)
        duration = time.time() - start
        token_metrics = llm_client.get_metrics()

        state_export = orchestrator.state.export()
        entries = state_export.get("entries", [])
        code_execs = [e for e in entries if e.get("code") and not e.get("is_internal_context")]
        code_successes = sum(1 for e in code_execs if e.get("success"))

        run_log_entries: list[dict[str, Any]] = []
        if orchestrator.run_log:
            for rle in orchestrator.run_log.entries:
                run_log_entries.append({
                    "source": rle.source,
                    "action": rle.action,
                    "content": rle.content,
                })

        answer = raw_result.get("answer") if raw_result else None
        export_path = None
        if orchestrator.run_log and orchestrator.run_log.export_path:
            export_path = orchestrator.run_log.export_path

        return EvalResult(
            case_id=case.id,
            config_name=run_config.name,
            repeat_index=repeat,
            answer=str(answer) if answer else None,
            metrics=RunMetrics(
                total_tokens=token_metrics["total_tokens"],
                input_tokens=token_metrics["input_tokens"],
                output_tokens=token_metrics["output_tokens"],
                duration_seconds=duration,
                code_executions=len(code_execs),
                code_successes=code_successes,
            ),
            execution_evidence=entries,
            run_log_entries=run_log_entries,
            raw_result=raw_result or {},
            export_path=export_path,
        )

    except Exception as e:
        duration = time.time() - start
        return EvalResult(
            case_id=case.id,
            config_name=run_config.name,
            repeat_index=repeat,
            error=str(e),
            metrics=RunMetrics(duration_seconds=duration),
        )


def _export_rag_run(
    case: TestCase,
    query: str,
    raw_result: dict[str, Any],
    duration: float,
    token_metrics: dict[str, int],
    output_dir: str = "exported_runs",
) -> str:
    """Export a RAG run to markdown and return the file path."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_id = case.id.replace(" ", "_")
    path = out / f"{ts}_rag_{safe_id}.md"

    chunks = raw_result.get("retrieved_chunks", [])
    lines = [
        "# RAG Run Export",
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Case:** {case.id} ({case.difficulty})",
        f"**Duration:** {duration:.2f}s",
        f"**Tokens:** {token_metrics.get('total_tokens', 0)} "
        f"(in: {token_metrics.get('input_tokens', 0)}, out: {token_metrics.get('output_tokens', 0)})",
        "",
        "## Query",
        "",
        f"> {query}",
        "",
        f"## Retrieved Chunks ({len(chunks)})",
        "",
    ]
    for i, chunk in enumerate(chunks, 1):
        preview = chunk[:500] + ("..." if len(chunk) > 500 else "")
        lines += [f"### Chunk {i}", "", "```", preview, "```", ""]

    lines += [
        "## LLM Prompt",
        "",
        "```",
        raw_result.get("prompt", "(not captured)"),
        "```",
        "",
        "## Answer",
        "",
        f"```",
        raw_result.get("answer", "(no answer)"),
        "```",
        "",
    ]

    path.write_text("\n".join(lines))
    return str(path)


def run_rag(
    run_config: RunConfiguration,
    case: TestCase,
    repeat: int,
    rag_index: Any,
    use_hints: bool = True,
) -> EvalResult:
    """Run a single test case through the RAG baseline."""
    llm_client = InstrumentedLLMClient(LLMConfig(model=run_config.model, base_url=run_config.base_url))

    query = case.query
    if use_hints and case.hint:
        query = f"{query}\n\nHint: {case.hint}"

    start = time.time()

    try:
        raw_result = rag_index.run(query, llm_client)
        duration = time.time() - start
        token_metrics = llm_client.get_metrics()

        answer = raw_result.get("answer")
        chunks = raw_result.get("retrieved_chunks", [])
        evidence = [
            {"step": i + 1, "result": chunk, "success": True, "is_internal_context": True}
            for i, chunk in enumerate(chunks)
        ]

        export_path = _export_rag_run(case, query, raw_result, duration, token_metrics)

        return EvalResult(
            case_id=case.id,
            config_name=run_config.name,
            repeat_index=repeat,
            answer=str(answer) if answer else None,
            metrics=RunMetrics(
                total_tokens=token_metrics["total_tokens"],
                input_tokens=token_metrics["input_tokens"],
                output_tokens=token_metrics["output_tokens"],
                duration_seconds=duration,
            ),
            execution_evidence=evidence,
            raw_result=raw_result,
            export_path=export_path,
        )

    except Exception as e:
        duration = time.time() - start
        return EvalResult(
            case_id=case.id,
            config_name=run_config.name,
            repeat_index=repeat,
            error=str(e),
            metrics=RunMetrics(duration_seconds=duration),
        )
