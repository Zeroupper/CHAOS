# Limitations

Known limitations of the CHAOS system.

## Data Sources

- **CSV only** — auto-discovery only supports CSV files. Other formats (Parquet, JSON, databases) require a custom `BaseDataSource` subclass.
- **Single directory** — all datasets must live under a single configured directory. Nested subdirectory structures are not auto-discovered.
- **In-memory processing** — datasets are loaded entirely into memory via pandas. Very large datasets (> available RAM) will fail.

## LLM Dependency

- **Code quality depends on the model** — the quality of generated Python code varies significantly across models. Smaller or less capable models produce more errors and require more retry iterations.
- **Non-deterministic** — identical queries can produce different plans and answers across runs, even with the same model.
- **Structured output support required** — the LLM must reliably follow JSON schemas. Models that struggle with structured output will cause frequent validation failures.

## Execution

- **Sequential step execution** — plan steps execute one at a time. Steps that could run in parallel (independent computations) are still serialized.
- **No persistent state across queries** — each query starts from scratch. There is no session memory or conversation history between runs.
- **Sandbox overhead** — Docker sandbox mode adds latency per code execution due to container startup. Disabling the sandbox removes isolation guarantees.
- **Fixed retry budget** — each step has a fixed number of retry attempts (`max_step_attempts`). Complex errors that require more iterations will result in partial answers.

## Analysis Capabilities

- **No visualization** — CHAOS computes answers but does not generate charts or plots.
- **Single-user queries** — queries are designed around single-user datasets. Cross-user analysis (e.g., "compare all users") is not well supported.
- **No streaming results** — the full pipeline must complete before the user sees any answer. There is no incremental output.

## Evaluation Framework

- **Objective answer tolerance** — numeric answers are compared with 0.5% relative tolerance. Edge cases near the tolerance boundary may be inconsistently scored.
- **Subjective scoring variability** — LLM-as-judge scores vary across runs and judge models. Results should be interpreted as approximate.
- **No ground truth for subjective queries** — subjective evaluation relies entirely on rubric criteria and faithfulness checks, not verified correct answers.
