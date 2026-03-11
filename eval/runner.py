"""Evaluation runner: parallel execution with live progress display."""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.table import Table

from chaos.ui.display import set_quiet

from .config import EvalConfig, RunConfiguration, load_test_cases, parse_test_cases
from .pipelines import run_chaos, run_rag
from .types import EvalResult, RunMetrics, TestCase


# ---------------------------------------------------------------------------
# Work item & progress tracking for the parallel runner
# ---------------------------------------------------------------------------

@dataclass
class _WorkItem:
    """A single unit of work for the thread pool."""

    run_config: RunConfiguration
    case: TestCase
    repeat: int
    data_registry: Any = None  # shared DataRegistry for chaos pipeline
    rag_index: Any = None  # shared RAG index, only set for rag pipeline


@dataclass
class _ProgressState:
    """Thread-safe progress tracking per (config_name, case_id)."""

    lock: threading.Lock = field(default_factory=threading.Lock)
    rows: dict[tuple[str, str], dict[str, int]] = field(default_factory=dict)
    _insertion_order: list[tuple[str, str]] = field(default_factory=list)

    def init_row(self, config_name: str, case_id: str, total: int) -> None:
        with self.lock:
            key = (config_name, case_id)
            self.rows[key] = {"completed": 0, "total": total, "errors": 0}
            self._insertion_order.append(key)

    def mark_done(self, config_name: str, case_id: str, error: bool = False) -> None:
        with self.lock:
            row = self.rows[(config_name, case_id)]
            row["completed"] += 1
            if error:
                row["errors"] += 1


def _build_progress_table(progress: _ProgressState) -> Table:
    """Build a Rich Table showing current evaluation progress."""
    table = Table(title="Evaluation Progress")
    table.add_column("Query", style="cyan", min_width=10)
    table.add_column("Configuration", style="magenta", min_width=14)
    table.add_column("Progress", min_width=12)
    table.add_column("Status", min_width=10)

    with progress.lock:
        for key in progress._insertion_order:
            config_name, case_id = key
            row = progress.rows[key]
            completed = row["completed"]
            total = row["total"]
            errors = row["errors"]
            pct = int(completed / total * 100) if total > 0 else 0
            progress_str = f"{completed}/{total} ({pct}%)"

            if completed == total:
                if errors > 0:
                    status = f"[yellow]done ({errors} err)[/yellow]"
                else:
                    status = "[green]done[/green]"
            elif completed > 0:
                status = "[blue]running...[/blue]"
            else:
                status = "[dim]pending[/dim]"

            table.add_row(case_id, config_name, progress_str, status)

    return table


def _run_work_item(item: _WorkItem, eval_config: EvalConfig) -> EvalResult:
    """Dispatch a work item to the correct pipeline function."""
    if item.run_config.pipeline == "rag":
        return run_rag(item.run_config, item.case, item.repeat, item.rag_index, eval_config.use_hints)
    return run_chaos(eval_config, item.run_config, item.case, item.repeat, item.data_registry)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class EvalRunner:
    """Runs evaluations across model configurations and repeats."""

    def __init__(self, eval_config: EvalConfig) -> None:
        self.config = eval_config
        self.results: list[EvalResult] = []

    def run_suite(self) -> list[EvalResult]:
        """Run the full evaluation suite with parallel execution."""
        raw_cases = load_test_cases(self.config.test_cases_path)
        cases = parse_test_cases(raw_cases)

        progress_console = Console()
        progress_console.print(f"Loaded {len(cases)} test cases")
        progress_console.print(
            f"Running {len(self.config.models)} models "
            f"x {self.config.n_repeats} repeats "
            f"(max {self.config.max_workers} workers)\n"
        )

        # Suppress all CHAOS output: Rich display
        set_quiet(True)

        try:
            # Build shared data registry (loaded once, reused by all work items)
            from chaos.data.registry import DataRegistry

            progress_console.print("Loading datasets...")
            shared_registry = DataRegistry()
            shared_registry.auto_discover(Path(self.config.datasets_dir))
            shared_registry.get_all_dataframes()  # eagerly load all CSVs
            progress_console.print(
                f"Loaded {len(shared_registry.list_sources())} datasets"
            )

            # Build shared RAG index if any config uses it
            rag_index = None
            if any(cfg.pipeline == "rag" for cfg in self.config.models):
                from .rag import RAGBaseline

                progress_console.print("Building shared RAG index...")
                rag_index = RAGBaseline()
                rag_index.build_index(Path(self.config.datasets_dir))

            # Build flat list of work items
            work_items: list[_WorkItem] = []
            progress = _ProgressState()

            for run_config in self.config.models:
                for case in cases:
                    progress.init_row(run_config.name, case.id, self.config.n_repeats)
                    for repeat in range(self.config.n_repeats):
                        work_items.append(_WorkItem(
                            run_config=run_config,
                            case=case,
                            repeat=repeat,
                            data_registry=shared_registry,
                            rag_index=rag_index if run_config.pipeline == "rag" else None,
                        ))

            max_workers = min(self.config.max_workers, len(work_items)) or 1

            # Execute in parallel with live progress display
            with Live(
                _build_progress_table(progress),
                console=progress_console,
                refresh_per_second=4,
                redirect_stdout=True,
                redirect_stderr=True,
            ) as live:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_item = {}
                    for item in work_items:
                        future = executor.submit(_run_work_item, item, self.config)
                        future_to_item[future] = item

                    for future in as_completed(future_to_item):
                        item = future_to_item[future]
                        try:
                            result = future.result()
                        except Exception as exc:
                            result = EvalResult(
                                case_id=item.case.id,
                                config_name=item.run_config.name,
                                repeat_index=item.repeat,
                                error=str(exc),
                                metrics=RunMetrics(),
                            )
                        self.results.append(result)
                        progress.mark_done(
                            item.run_config.name,
                            item.case.id,
                            error=result.error is not None,
                        )
                        live.update(_build_progress_table(progress))

        finally:
            set_quiet(False)

        return self.results


# ---------------------------------------------------------------------------
# Results persistence (standalone)
# ---------------------------------------------------------------------------


def save_results(
    results: list[EvalResult],
    eval_config: EvalConfig,
    output_dir: str | None = None,
) -> Path:
    """Save all results to JSON."""
    out_dir = Path(output_dir or eval_config.output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suite_dir = out_dir / f"{timestamp}_suite"
    suite_dir.mkdir(parents=True, exist_ok=True)

    results_data = {
        "config": {
            "judge_model": eval_config.judge_model,
            "n_repeats": eval_config.n_repeats,
            "datasets_dir": eval_config.datasets_dir,
            "models": [
                {
                    "name": c.name,
                    "model": c.model,
                    "pipeline": c.pipeline,
                    "sandbox": c.sandbox,
                }
                for c in eval_config.models
            ],
        },
        "results": [asdict(r) for r in results],
        "timestamp": timestamp,
    }

    results_path = suite_dir / "results.json"
    results_path.write_text(json.dumps(results_data, indent=2, default=str))

    return suite_dir
