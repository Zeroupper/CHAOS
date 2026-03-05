# CHAOS

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/sandbox-Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-6366f1?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJ3aGl0ZSI+PGNpcmNsZSBjeD0iMTIiIGN5PSIxMiIgcj0iMTAiLz48L3N2Zz4=&logoColor=white)](https://openrouter.ai/)
[![Ollama](https://img.shields.io/badge/Ollama-000000?logo=ollama&logoColor=white)](https://ollama.com/)
[![vLLM](https://img.shields.io/badge/vLLM-FF6F00?logoColor=white)](https://docs.vllm.ai/)

**C**oordinated **H**uman-**A**gent **O**rchestrated **S**ensemaking

A multi-agent LLM system for open-ended sensemaking over datasets. Built with Instructor + Pydantic for type-safe, validated LLM responses. Works with any OpenAI-compatible endpoint: OpenRouter, Ollama, vLLM, and more.

## Why CHAOS?

**Your data. Your LLM. Your insights.**

Understanding data shouldn't require writing code or uploading sensitive information to third-party services. CHAOS lets you ask questions about your data in plain English and get verified, explainable answers.

```
You: "What's the average heart rate of user test004?"
CHAOS: Explores → Plans → Executes → Verifies → "The average heart rate is 72.5 bpm"
       (and shows you exactly how it calculated that)
```

**The problem:** Traditional data analysis requires coding skills. Cloud AI services require sending your data to external servers. Black-box answers leave you wondering "but how did it get that number?"

**The solution:** CHAOS runs locally with any OpenAI-compatible LLM endpoint (OpenRouter, Ollama, vLLM, etc.). Every answer comes with:
- **Transparency**: See the exact code executed on your data
- **Verification**: An independent agent validates the answer
- **Human guidance**: Steer the analysis when needed
- **Privacy**: Your data never leaves your machine(s)

## Features

- **Dynamic Data Exploration**: Explorer agent inspects dataset schemas (column types, nulls, sample values) before planning — no static schemas needed
- **Type-Safe LLM Responses**: All agent outputs are validated Pydantic models
- **Automatic Retries**: Instructor handles validation failures with configurable retries
- **Model Flexibility**: Works with any OpenAI-compatible endpoint — OpenRouter, Ollama, vLLM, or any local server
- **Sandboxed Execution**: Optionally run LLM-generated code in an isolated Docker container (no network, read-only data)
- **Extensible Architecture**: Easy to add new data sources
- **Memory Management**: Working memory tracks execution state across iterations
- **Evaluation Framework**: Automated benchmarking with parallel execution, LLM-as-judge scoring, and RAG baseline comparison

## Prerequisites

- [Python 3.11+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended) or pip
- An LLM backend — **one** of:
  - [OpenRouter API key](https://openrouter.ai/keys) (cloud models)
  - [Ollama](https://ollama.com/) (local models, e.g. `ollama pull qwen3.5:2b`)
  - Any OpenAI-compatible server (vLLM, llama.cpp, etc.)
- [Docker](https://docs.docker.com/get-docker/) (only if `sandbox: True` in config)

## Installation

```bash
# Clone the repository
git clone git@github.com:Zeroupper/CHAOS.git
cd CHAOS

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

### Configuration

**For OpenRouter (cloud models):**

```bash
export OPENROUTER_API_KEY=your_key_here
```

**For local models (Ollama, vLLM, etc.):**

No API key needed. The `base_url` in `chaos/core/config.py` defaults to `http://localhost:11434/v1` (Ollama). Just make sure your local server is running:

```bash
# Ollama example
ollama pull qwen3.5:2b
ollama serve
```

### Sandbox (optional)

When `sandbox: True` is set in `Config`, LLM-generated code runs in an isolated Docker container instead of the host. To set up:

```bash
# Build the sandbox image (one-time)
bash scripts/install-sandbox.sh
```

## Usage

```bash
uv run python main.py "What is the average heart rate of test004?"
```

All settings (model, base URL, sandbox, auto-approve, etc.) are configured in `chaos/core/config.py`. See the `Config` and `LLMConfig` classes.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          User Query                             │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Explorer Agent                            │
│      Inspects all dataset schemas before planning               │
│  Discovers: column types, dtypes, null counts, sample values    │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Planner Agent ◄───────────────────────┐      │
│          Creates/modifies execution plan                 │      │
│     Human: approve / modify / reject                     │      │
└─────────────────────────────┬────────────────────────────┘──────┘
                              ▼                            ▲
┌─────────────────────────────────────────────────────────────────┐
│                       Sensemaking Loop                          │
│  ┌──────────────────┐         ┌───────────────────────────┐     │
│  │  Sensemaker      │◄───────►│  Information Seeking      │     │
│  │  Agent           │         │  Agent                    │     │
│  │                  │         │  - Queries data sources   │     │
│  │  Returns:        │         │  - Executes Python code   │     │
│  │  - Complete      │         │    (host or sandbox)      │     │
│  │  - Execute       │         │                           │     │
│  │  - Review        │         │                           │     │
│  └──────────────────┘         └───────────────────────────┘     │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Verifier Agent                           │
│              Validates answer + explains on request             │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Final Review                             │
│     Human: accept / modify plan / explain answer / reject       │
│         "Modify plan" loops back to Planner ──────────────►─────┘
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Final Result                            │
│           Answer, confidence score, supporting evidence         │
│                    + Optional Run Export                        │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
CHAOS/
├── chaos/                    # Main package
│   ├── types.py                # Pydantic models for all data structures
│   ├── core/                   # Orchestration & config
│   │   ├── config.py             # Configuration management (LLMConfig, Config)
│   │   ├── orchestrator.py       # Main pipeline orchestrator (with human-in-the-loop)
│   │   ├── execution.py          # SensemakingLoop — drives the sensemaker↔info_seeker cycle
│   │   ├── code_executor.py      # Code execution (host or Docker sandbox)
│   │   ├── state.py              # ExecutionState — unified step states + memory entries
│   │   └── logger.py             # Text formatting utilities
│   ├── agents/                 # Agent implementations
│   │   ├── base.py               # Base agent with _call_llm(messages, Model)
│   │   ├── explorer.py           # Dataset schema inspector → data_context
│   │   ├── planner.py            # Creates/modifies execution plans → Plan
│   │   ├── sensemaker.py         # Synthesizes info → Complete|Execute|Review
│   │   ├── information_seeker.py # Retrieves data → InfoSeekerResult
│   │   └── verifier.py           # Validates answers + explains them → Verification
│   ├── llm/                    # LLM client
│   │   └── structured_client.py  # Instructor-wrapped OpenAI-compatible client
│   ├── data/                   # Data source management
│   │   ├── base.py               # Base data source (CSVDataSource)
│   │   └── registry.py           # Data source registry & auto-discovery
│   └── ui/                     # Interactive terminal UI
│       ├── display.py            # Rich-based display components
│       ├── prompts.py            # Questionary-based prompts
│       └── export.py             # Run export to markdown
├── eval/                    # Evaluation & benchmarking framework
│   ├── __main__.py            # CLI entry point (python -m eval)
│   ├── config.py              # EvalConfig, RunConfiguration
│   ├── runner.py              # Parallel evaluation runner with live progress
│   ├── pipelines.py           # CHAOS and RAG pipeline wrappers
│   ├── rag.py                 # RAG baseline (FAISS + sentence-transformers)
│   ├── judge.py               # LLM-as-judge for subjective evaluation
│   ├── evaluation.py          # Objective & subjective result evaluation
│   ├── metrics.py             # Metric extraction (numeric answers, etc.)
│   ├── aggregation.py         # Aggregate metrics across runs
│   ├── report.py              # Markdown report generation
│   ├── types.py               # EvalResult, AggregateMetrics, TestCase, etc.
│   ├── configs/               # Evaluation configuration files
│   │   └── run_configuration.yaml
│   └── test_cases/            # Test case definitions
│       └── test_cases.yaml
├── sandbox/                 # Docker sandbox
│   └── entrypoint.py          # In-container code executor
├── scripts/                 # Utility scripts
│   └── install-sandbox.sh     # Build sandbox Docker image
├── datasets/                # Place datasets here (auto-discovered)
├── exported_runs/           # Exported run logs (markdown)
├── tests/                   # Test suite
├── Dockerfile               # Sandbox container image
├── main.py                  # Entry point
└── pyproject.toml           # Project configuration
```

## Type System

All LLM responses are validated Pydantic models defined in `chaos/types.py`:

```python
# Plan types
Plan, PlanStep

# Information seeker types
QueryDecision, InfoSeekerResult

# Sensemaker response (discriminated union)
CompleteResponse | ExecuteResponse | ReviewResponse

# Verifier types
Verification, ExplanationResponse

# Execution types
ExecutionResult, StepState

# Schema types (from Explorer)
DatasetSchema, ColumnSchema
```

## Sandbox Mode

### Isolation guarantees

- **No network**: `--network=none` prevents any outbound connections
- **Read-only data**: Datasets mounted as `-v ...:/data:ro`
- **Ephemeral**: `--rm` removes the container after each execution
- **Timeout**: 30-second hard limit on container execution

## Human-in-the-Loop

CHAOS keeps you in control at every stage of the pipeline:

1. **Plan Review** — Before execution, approve, modify, or reject the plan
2. **Data Quality Correction** — During execution, approve or modify fixes for suspicious data (e.g., -1 placeholders)
3. **Final Review** — After verification:
   - **Accept** the answer
   - **Modify plan** — describe what to change, the planner updates the plan, and execution restarts from scratch
   - **Explain answer** — ask follow-up questions about the solution in a Q&A chat with the verifier
   - **Reject** the answer
4. **Run Export** — Export the full run (query, plan, code, results, verification) to markdown

Set `auto_approve: True` in config to skip all human prompts (used by the evaluation framework).

## Adding Data Sources

### Auto-Discovery

Place CSV files in your configured dataset directory (`datasets_dir` in config) and they are auto-discovered:

```
datasets/gloss_sample/
├── garmin_hr.csv      → Becomes "garmin_hr" source
├── garmin_steps.csv   → Becomes "garmin_steps" source
└── ios_activity.csv   → Becomes "ios_activity" source
```

### Custom Data Sources

Extend `BaseDataSource` to connect any data backend:

```python
class MongoDataSource(BaseDataSource):
    def __init__(self, name: str, uri: str, collection: str):
        self.name, self.description = name, f"MongoDB: {collection}"
        self._client = MongoClient(uri)
        self._collection = self._client.get_database()[collection]

    def connect(self) -> None:
        self._data = pd.DataFrame(list(self._collection.find()))
```

## Evaluation Framework

CHAOS includes an evaluation framework for benchmarking against a RAG baseline across multiple models. Default configuration is set to `eval/configs/run_configuration.yaml`

```bash
python -m eval
```

### What it does

1. Runs each model configuration against all test cases (with N repeats for consistency)
2. Executes CHAOS and RAG pipelines in parallel with live progress display
3. Evaluates objective answers (exact match / numeric tolerance)
4. Scores subjective answers via LLM-as-judge with rubric criteria
5. Computes aggregate metrics (accuracy, consistency, latency, token usage, Cohen's d)
6. Generates a markdown report in the output directory

### Configuration

All eval settings are in `eval/configs/run_configuration.yaml`:

```yaml
judge_model: "anthropic/claude-haiku-4.5"
n_repeats: 5
max_workers: 8
datasets_dir: "datasets/gloss_sample"
test_cases_path: "eval/test_cases/test_cases.yaml"

models:
  - name: chaos_gpt-4o
    model: openai/gpt-4o
    pipeline: chaos
    sandbox: true

  - name: rag_gpt-4o
    model: openai/gpt-4o
    pipeline: rag
```

### Test cases

Each test case has a `category` and `difficulty`:

- **Objective** — queries with a single correct numeric answer (e.g., "What is the average heart rate of test004?"). Evaluated automatically by extracting the numeric value and comparing against the expected answer within 0.5% tolerance.
- **Subjective** — open-ended analytical queries (e.g., "Describe activity trends across all users"). Evaluated by an LLM-as-judge that scores each rubric criterion and checks faithfulness against execution evidence.

```yaml
test_cases:
  - id: avg_hr_test004
    category: objective
    difficulty: simple
    query: "What is the average heart rate of test004?"

  - id: activity_trends
    category: subjective
    difficulty: complex
    query: "Describe the activity trends across all users"
    rubric:
      - criterion: "Coverage"
        weight: 0.5
        description: "Covers all users and activity types"
```

### Metrics

| Metric | Applies to | Description |
|--------|-----------|-------------|
| **Accuracy** | Objective | Fraction of runs where extracted answer matches expected value (0.5% tolerance) |
| **Relative error** | Objective | `\|predicted - expected\| / \|expected\|` — how far off the answer is |
| **Consistency** | Objective | Fraction of repeated runs that agree with each other |
| **Rubric score** | Subjective | Weighted average of per-criterion scores (0-1) from LLM-as-judge |
| **Faithfulness** | Subjective | Are all claims in the answer supported by execution evidence? (0-1) |
| **Code success rate** | Both | Fraction of code executions that completed without error |
| **Avg tokens** | Both | Average total tokens per run |
| **Avg latency** | Both | Average wall-clock seconds per run |
| **Cohen's d** | Both | Effect size comparing CHAOS vs RAG baseline accuracy |

All metrics are broken down by difficulty level (simple / medium / complex) in the generated report.

## Dependencies

- **instructor** - Structured LLM outputs with Pydantic validation
- **pydantic** - Data validation and type hints
- **openai** - OpenAI-compatible API client (works with OpenRouter, Ollama, vLLM, etc.)
- **pandas** - Data manipulation
- **numpy** - Numerical operations
- **httpx** - HTTP client
- **questionary** - Interactive terminal prompts (disabled when `auto_approve: True`)
- **rich** - Terminal formatting and tables

## License

MIT
