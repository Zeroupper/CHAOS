# CHAOS Evaluation Framework

Automated benchmarking framework for comparing CHAOS against a RAG baseline across multiple models.

## Quick Start

```bash
python -m eval
```

By default, this uses `eval/configs/run_configuration.yaml`. To use a custom config:

```bash
python -m eval --config eval/configs/my_config.yaml
```

## What It Does

1. Runs each model configuration against all test cases (with N repeats for consistency)
2. Executes CHAOS and RAG pipelines in parallel with live progress display
3. Evaluates objective answers (exact match / numeric tolerance)
4. Scores subjective answers via LLM-as-judge with rubric criteria
5. Computes aggregate metrics (accuracy, consistency, latency, token usage, Cohen's d)
6. Generates a markdown report in the output directory

## Configuration

All settings are defined in a YAML config file. See [`configs/run_configuration.yaml`](configs/run_configuration.yaml) for a full example.

### Global Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `judge_model` | `anthropic/claude-haiku-4.5` | LLM used as judge for subjective rubric scoring |
| `n_repeats` | `2` | How many times to repeat each (configuration x query) pair |
| `max_workers` | `50` | Max concurrent workers for the parallel runner |
| `datasets_dir` | `datasets/gloss_sample` | Path to datasets used by CHAOS and RAG pipelines |
| `test_cases_path` | `eval/test_cases/test_cases_small.yaml` | Path to test cases file |
| `output_dir` | `eval_results` | Directory where results and reports are written |
| `use_hints` | `true` | Append dataset/column hints to queries (set `false` to benchmark without hints) |

### Model Configuration

Each model entry runs as an independent pipeline. The runner executes all models x all test cases x `n_repeats` in parallel.

```yaml
models:
  - name: chaos_gpt-4o          # Unique label (required)
    model: openai/gpt-4o        # OpenRouter model ID (required)
    pipeline: chaos              # "chaos" or "rag" (default: "chaos")
    sandbox: true                # Sandboxed code execution (default: false)

  - name: rag_gpt-4o
    model: openai/gpt-4o
    pipeline: rag

  # Local model (Ollama)
  - name: chaos_qwen3.5-2b_local
    model: qwen3.5:2b
    base_url: "http://localhost:11434/v1"
    pipeline: chaos
    sandbox: true

  # Custom system prompt overrides
  - name: chaos_gpt-4o_strict
    model: openai/gpt-4o
    pipeline: chaos
    system_prompt_overrides:
      planner: "You are a strict data analyst. Only use exact computations, never estimate."
```

## Test Cases

Test cases are defined in YAML files under [`test_cases/`](test_cases/). Each test case has a `category` and `difficulty`.

### Objective

Queries with a single correct numeric answer. Evaluated automatically by extracting the numeric value and comparing against the expected answer within 0.5% tolerance.

```yaml
- id: obj_001
  category: objective
  difficulty: simple
  query: "What was the highest heart rate recorded for user test004?"
```

### Subjective

Open-ended analytical queries. Evaluated by an LLM-as-judge that scores each rubric criterion and checks faithfulness against execution evidence.

```yaml
- id: sub_001
  category: subjective
  difficulty: medium
  query: "Based on the data, is user test004 physically active or sedentary?"
  rubric:
    - criterion: "Uses step data"
      weight: 0.3
      description: "References actual step count values from garmin_steps or ios_steps"
    - criterion: "Sound reasoning"
      weight: 0.2
      description: "Logical chain from step data to activity level conclusion"
```

### Difficulty Levels

- **Simple** — single dataset, straightforward aggregation (e.g., max, count)
- **Medium** — requires filtering, handling invalid data, or domain knowledge
- **Complex** — cross-dataset joins, temporal alignment, statistical computation

## Metrics

| Metric | Applies to | Description |
|--------|-----------|-------------|
| **Accuracy** | Objective | Fraction of runs where extracted answer matches expected value (0.5% tolerance) |
| **Relative error** | Objective | `|predicted - expected| / |expected|` — how far off the answer is |
| **Consistency** | Objective | Fraction of repeated runs that agree with each other |
| **Rubric score** | Subjective | Weighted average of per-criterion scores (0-1) from LLM-as-judge |
| **Faithfulness** | Subjective | Are all claims in the answer supported by execution evidence? (0-1) |
| **Code success rate** | Both | Fraction of code executions that completed without error |
| **Avg tokens** | Both | Average total tokens per run |
| **Avg latency** | Both | Average wall-clock seconds per run |
| **Cohen's d** | Both | Effect size comparing CHAOS vs RAG baseline accuracy |

All metrics are broken down by difficulty level (simple / medium / complex) in the generated report.

## Package Structure

```
eval/
├── __main__.py           # CLI entry point (python -m eval)
├── config.py             # EvalConfig, RunConfiguration
├── runner.py             # Parallel evaluation runner with live progress
├── pipelines.py          # CHAOS and RAG pipeline wrappers
├── rag.py                # RAG baseline (FAISS + sentence-transformers)
├── judge.py              # LLM-as-judge for subjective evaluation
├── evaluation.py         # Objective & subjective result evaluation
├── metrics.py            # Metric extraction (numeric answers, etc.)
├── aggregation.py        # Aggregate metrics across runs
├── report.py             # Markdown report generation
├── types.py              # EvalResult, AggregateMetrics, TestCase, etc.
├── configs/              # Evaluation configuration files
│   └── run_configuration.yaml
└── test_cases/           # Test case definitions
    └── test_cases.yaml
```
