"""CLI entry point: python -m eval --config <path>."""

from __future__ import annotations

import argparse
import sys

from .aggregation import compute_aggregates
from .config import EvalConfig, load_test_cases, parse_test_cases
from .evaluation import evaluate_objective_results, evaluate_subjective_results
from .report import generate_report
from .runner import EvalRunner, save_results
from .types import AggregateMetrics


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CHAOS Evaluation & Benchmarking Framework",
        prog="python -m eval",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="eval/configs/run_configuration.yaml",
        help="Path to eval config YAML file (default: eval/configs/run_configuration.yaml)",
    )
    args = parser.parse_args()

    eval_config = EvalConfig.from_yaml(args.config)

    # Run benchmarks
    runner = EvalRunner(eval_config)
    print("Starting evaluation suite...")
    print(f"Judge model: {eval_config.judge_model}")
    print()

    results = runner.run_suite()

    if not results:
        print("No results collected. Check configuration.")
        sys.exit(1)

    # Evaluate results
    raw_cases = load_test_cases(eval_config.test_cases_path)
    cases = parse_test_cases(raw_cases)
    case_map = {c.id: c for c in cases}

    evaluate_objective_results(results, case_map, eval_config.test_cases_path, eval_config.judge_model)
    evaluate_subjective_results(results, case_map, eval_config)

    # Compute aggregates once
    rag_config_name = None
    for cfg in eval_config.models:
        if cfg.pipeline == "rag":
            rag_config_name = cfg.name
            break
    aggregates = compute_aggregates(results, cases, rag_config_name)

    # Save results
    suite_dir = save_results(results, eval_config)
    print(f"\nResults saved to: {suite_dir}")

    # Generate report
    report_path = suite_dir / "report.md"
    generate_report(aggregates, results, cases, eval_config, report_path)
    print(f"Report saved to: {report_path}")

    # Print summary
    _print_summary(aggregates)


def _print_summary(aggregates: dict[str, AggregateMetrics]) -> None:
    """Print a concise summary from pre-computed aggregates."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for name, agg in aggregates.items():
        if agg.accuracy is not None:
            print(f"  {name}: accuracy = {agg.accuracy * 100:.0f}%")
        if agg.avg_rubric_score is not None:
            print(f"  {name}: avg rubric score = {agg.avg_rubric_score:.2f}")

    print()


if __name__ == "__main__":
    main()
