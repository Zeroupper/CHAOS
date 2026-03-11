"""Generate markdown comparison reports from evaluation results."""

from __future__ import annotations

from pathlib import Path

from .config import EvalConfig
from .test_cases import load_ground_truth
from .types import AggregateMetrics, EvalResult, TestCase


def generate_report(
    aggregates: dict[str, AggregateMetrics],
    results: list[EvalResult],
    cases: list[TestCase],
    eval_config: EvalConfig,
    output_path: Path | None = None,
) -> str:
    """Generate a markdown comparison report.

    Args:
        aggregates: Pre-computed per-config aggregate metrics.
        results: All evaluation results (for per-case detail tables).
        cases: All test cases.
        eval_config: Eval configuration (for header metadata).
        output_path: Optional path to write the report to.

    Returns:
        The full markdown report as a string.
    """
    ground_truth = load_ground_truth(eval_config.test_cases_path)
    config_names = [c.name for c in eval_config.models]
    lines: list[str] = []

    # Header
    lines.append("# CHAOS Evaluation Report")
    lines.append("")
    lines.append(f"**Judge model**: {eval_config.judge_model}")
    lines.append(f"**Repeats per query**: {eval_config.n_repeats}")
    lines.append(f"**Datasets**: {eval_config.datasets_dir}")
    lines.append("")

    # Configuration summary
    lines.append("## Configurations")
    lines.append("")
    lines.append("| Name | Model | Pipeline | Sandbox |")
    lines.append("|------|-------|----------|---------|")
    for cfg in eval_config.models:
        sandbox = "Yes" if cfg.sandbox else "No"
        lines.append(f"| {cfg.name} | {cfg.model} | {cfg.pipeline} | {sandbox} |")
    lines.append("")

    # Test Cases / Queries
    lines.append("## Test Cases")
    lines.append("")
    lines.append("| ID | Category | Difficulty | Query |")
    lines.append("|----|----------|------------|-------|")
    for case in cases:
        query_display = case.query.replace("|", "\\|")
        lines.append(f"| {case.id} | {case.category} | {case.difficulty} | {query_display} |")
    lines.append("")

    # Overall Metrics comparison table
    lines.append("## Overall Metrics")
    lines.append("")
    overall_rows = [
        ("Accuracy (obj)", lambda a: _fmt_pct(a.accuracy)),
        ("Avg Relative Error (obj)", lambda a: _fmt_pct(a.avg_relative_error)),
        ("Consistency (obj)", lambda a: _fmt_pct(a.consistency)),
        ("Rubric Score (subj)", lambda a: _fmt(a.avg_rubric_score)),
        ("Faithfulness (subj)", lambda a: _fmt(a.avg_faithfulness)),
        ("Code Success Rate", lambda a: _fmt_pct(a.code_success_rate)),
        ("Avg Tokens", lambda a: _fmt_int(a.avg_tokens)),
        ("Avg Latency", lambda a: _fmt_seconds(a.avg_latency)),
        ("Cohen's d (vs RAG)", lambda a: _fmt(a.cohens_d)),
    ]
    lines.extend(_md_table("Metric", config_names, aggregates, overall_rows))
    lines.append("")

    # Accuracy by difficulty
    difficulties = ["simple", "medium", "complex"]
    lines.append("## Accuracy by Difficulty")
    lines.append("")
    diff_rows = [
        (diff, lambda a, d=diff: _fmt_pct(a.accuracy_by_difficulty.get(d)))
        for diff in difficulties
    ]
    lines.extend(_md_table("Difficulty", config_names, aggregates, diff_rows))
    lines.append("")

    # Rubric by difficulty
    has_rubric = any(agg.rubric_by_difficulty for agg in aggregates.values())
    if has_rubric:
        lines.append("## Rubric Score by Difficulty")
        lines.append("")
        rubric_rows = [
            (diff, lambda a, d=diff: _fmt(a.rubric_by_difficulty.get(d)))
            for diff in difficulties
        ]
        lines.extend(_md_table("Difficulty", config_names, aggregates, rubric_rows))
        lines.append("")

    # Per-case detail table
    lines.append("## Per-Case Results")
    lines.append("")

    # Resolve report path for relative links
    report_dir = output_path.parent if output_path else None

    for case in cases:
        lines.append(f"### {case.id}: {case.query}")
        if case.category == "objective" and case.id in ground_truth:
            lines.append(f"Expected: {ground_truth[case.id][1]}")
        lines.append("")

        for cfg in eval_config.models:
            cfg_results = sorted(
                [r for r in results if r.case_id == case.id and r.config_name == cfg.name],
                key=lambda r: r.repeat_index,
            )
            if not cfg_results:
                continue

            lines.append(f"**{cfg.name}**:")
            for r in cfg_results:
                _render_run_line(lines, r, case, report_dir, ground_truth)

            lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*Judge model: {eval_config.judge_model} (fixed across all evaluations)*")
    lines.append("")

    report = "\n".join(lines)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report)

    return report


# --- Table helper ---


def _md_table(
    row_label: str,
    config_names: list[str],
    aggregates: dict[str, AggregateMetrics],
    rows: list[tuple[str, object]],
) -> list[str]:
    """Build a markdown comparison table.

    Args:
        row_label: Header for the first column (e.g. "Metric", "Difficulty").
        config_names: Ordered config names for the column headers.
        aggregates: Per-config aggregate metrics.
        rows: List of (row_name, getter) where getter(AggregateMetrics) -> str.

    Returns:
        List of markdown lines (header + separator + data rows).
    """
    header = f"| {row_label} |"
    separator = f"|{'---' * len(row_label)}|"
    for name in config_names:
        header += f" {name} |"
        separator += "------|"

    lines = [header, separator]
    for row_name, getter in rows:
        row = f"| {row_name} |"
        for name in config_names:
            agg = aggregates.get(name, AggregateMetrics())
            row += f" {getter(agg)} |"
        lines.append(row)

    return lines


# --- Run detail rendering ---


def _make_export_link(export_path: str | None, report_dir: Path | None) -> str:
    """Build a markdown link to the exported run file, relative to the report."""
    if not export_path:
        return ""
    export = Path(export_path)
    if not export.exists():
        return ""
    if report_dir:
        try:
            rel = export.resolve().relative_to(report_dir.resolve())
            return f" ([run log]({rel}))"
        except ValueError:
            # Fall back to a relative path from report_dir
            try:
                from os.path import relpath
                rel = relpath(export.resolve(), report_dir.resolve())
                return f" ([run log]({rel}))"
            except ValueError:
                pass
    return f" ([run log]({export_path}))"


def _render_run_line(
    lines: list[str],
    r: EvalResult,
    case: TestCase,
    report_dir: Path | None,
    ground_truth: dict[str, tuple],
) -> None:
    """Render a single run with format depending on objective/subjective."""
    export_link = _make_export_link(r.export_path, report_dir)

    if r.error:
        short = r.error[:120]
        lines.append(f"\n- Run {r.repeat_index + 1}: **ERROR**: {short}{export_link}")
        if len(r.error) > 120:
            lines.append("<details><summary>Full error</summary>")
            lines.append("")
            lines.append(f"```\n{r.error}\n```")
            lines.append("")
            lines.append("</details>")
        lines.append("")
        return

    if case.category == "objective":
        _render_objective_run(lines, r, case, export_link, ground_truth)
    else:
        _render_subjective_run(lines, r, case, export_link)


def _render_objective_run(
    lines: list[str],
    r: EvalResult,
    case: TestCase,
    export_link: str,
    ground_truth: dict[str, tuple],
) -> None:
    """Render an objective run: one-line verdict comparing extracted vs expected."""
    expected = ground_truth.get(case.id, (None, None))[1]
    extracted = r.extracted_value

    rel_err_str = ""
    if r.relative_error is not None:
        rel_err_str = f" (relative error: {r.relative_error * 100:.2f}%)"

    if r.is_correct:
        verdict = f"Correct, extracted value ({_fmt_num(extracted)}) matches expected value ({_fmt_num(expected)}).{rel_err_str}"
    else:
        verdict = f"Wrong, extracted value ({_fmt_num(extracted)}) doesn't match expected value ({_fmt_num(expected)}).{rel_err_str}"

    lines.append(f"\n- Run {r.repeat_index + 1}: **{verdict}**{export_link}")


def _render_subjective_run(
    lines: list[str],
    r: EvalResult,
    case: TestCase,
    export_link: str,
) -> None:
    """Render a subjective run: answer, rubric with weighted formula, faithfulness."""
    lines.append(f"\n- Run {r.repeat_index + 1}{export_link}")

    # Answer
    answer_text = r.answer or "(no answer)"
    lines.append(f"- **Answer:** {answer_text}")

    se = r.subjective_eval
    if not se:
        return

    # --- Rubric score with weighted formula ---
    weight_map = {rc.criterion: rc.weight for rc in case.rubric}
    formula_parts: list[str] = []
    for cs in se.criteria_scores:
        w = weight_map.get(cs["criterion"])
        if w is not None:
            formula_parts.append(f"{cs['score']:.2f} x {w:.1f}")
        else:
            formula_parts.append(f"{cs['score']:.2f}")
    formula_str = " + ".join(formula_parts)

    lines.append(f"- **Rubric:** {_fmt(se.overall_score)} ({formula_str})")

    # Criteria scores in collapsible detail
    

    # --- Faithfulness score with detail ---
    lines.append(f"- **Faithfulness:** {_fmt(se.faithfulness_score)}")
    if se.criteria_scores:
        lines.append("<details><summary>Rubric details</summary>")
        lines.append("")
        for cs in se.criteria_scores:
            w = weight_map.get(cs["criterion"])
            weight_label = f", weight {w:.1f}" if w is not None else ""
            lines.append(f"- **{cs['criterion']}** ({cs['score']:.2f}{weight_label}): {cs['reasoning']}")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    if se.faithfulness_reasoning or se.unsupported_claims:
        lines.append("<details><summary>Faithfulness details</summary>")
        lines.append("")
        if se.faithfulness_reasoning:
            lines.append(se.faithfulness_reasoning)
            lines.append("")
        if se.unsupported_claims:
            lines.append("**Unsupported claims:**")
            for claim in se.unsupported_claims:
                lines.append(f"- {claim}")
            lines.append("")
        lines.append("</details>")
        lines.append("")


# --- Formatters ---


def _fmt(val: float | None) -> str:
    if val is None:
        return "N/A"
    return f"{val:.2f}"


def _fmt_pct(val: float | None) -> str:
    if val is None:
        return "N/A"
    return f"{val * 100:.0f}%"


def _fmt_int(val: float | None) -> str:
    if val is None:
        return "N/A"
    return f"{int(val)}"


def _fmt_seconds(val: float | None) -> str:
    if val is None:
        return "N/A"
    return f"{val:.1f}s"


def _fmt_num(val: float | None) -> str:
    """Format a numeric value, dropping .0 for whole numbers."""
    if val is None:
        return "N/A"
    if val == int(val):
        return str(int(val))
    return f"{val}"
