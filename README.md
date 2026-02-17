# CHAOS

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/sandbox-Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

**C**oordinated **H**uman-**A**gent **O**rchestrated **S**ensemaking

A multi-agent LLM system for open-ended sensemaking over datasets. Built with Instructor + Pydantic for type-safe, validated LLM responses.

## Why CHAOS?

**Your data. Your LLM. Your insights.**

Understanding data shouldn't require writing code or uploading sensitive information to third-party services. CHAOS lets you ask questions about your data in plain English and get verified, explainable answers.

```
You: "What's the average heart rate of user test004?"
CHAOS: Plans → Executes → Verifies → "The average heart rate is 72.5 bpm"
       (and shows you exactly how it calculated that)
```

**The problem:** Traditional data analysis requires coding skills. Cloud AI services require sending your data to external servers. Black-box answers leave you wondering "but how did it get that number?"

**The solution:** CHAOS runs locally with any OpenRouter-compatible LLM (including self-hosted models). Every answer comes with:
- **Transparency**: See the exact code executed on your data
- **Verification**: An independent agent validates the answer
- **Human guidance**: Steer the analysis when needed
- **Privacy**: Your data never leaves your machine(s)

## Features

- **Type-Safe LLM Responses**: All agent outputs are validated Pydantic models
- **Automatic Retries**: Instructor handles validation failures with configurable retries
- **Model Flexibility**: Works with any OpenRouter model (GPT-4o, Claude, DeepSeek, Kimi K2, etc.)
- **Sandboxed Execution**: Optionally run LLM-generated code in an isolated Docker container (no network, read-only data)
- **Extensible Architecture**: Easy to add new data sources and tools
- **Memory Management**: Working memory tracks execution state across iterations

## Prerequisites

- [Python 3.11+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended) or pip
- An [OpenRouter API key](https://openrouter.ai/keys)
- [Docker](https://docs.docker.com/get-docker/) (only if using `--sandbox` mode)

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

Set your OpenRouter API key:

```bash
export OPENROUTER_API_KEY=your_key_here
```

### Sandbox (optional)

By default, LLM-generated Python code runs on the host via `exec()`. To run it in an isolated Docker container instead:

```bash
# Build the sandbox image (one-time)
bash scripts/install-sandbox.sh
```

## Usage

```bash
# Single query
uv run python main.py "What is the average heart rate of test004?"

# With options
uv run python main.py "Your query" --log-level DEBUG

# Use a different model (any OpenRouter model works)
uv run python main.py "Your query" --model "anthropic/claude-3.5-sonnet"
uv run python main.py "Your query" --model "deepseek/deepseek-chat"
uv run python main.py "Your query" --model "openai/gpt-4o"
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--max-step-attempts` | Maximum attempts per step | `5` |
| `--log-level` | Log level (DEBUG/INFO/WARNING/ERROR) | WARNING |
| `--model` | LLM model to use | from config |
| `--sandbox` | Run LLM-generated code in Docker sandbox | off |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          User Query                             │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Planner Agent                            │
│                 Creates execution plan from query               │
│              Returns: Plan (validated Pydantic model)           │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Sensemaking Loop                          │
│  ┌──────────────────┐         ┌───────────────────────────┐     │
│  │  Sensemaker      │◄───────►│  Information Seeking      │     │
│  │  Agent           │         │  Agent                    │     │
│  │                  │         │  - Queries data sources   │     │
│  │  Returns:        │         │  - Executes Python code   │     │
│  │                  │         │    (host or sandbox)      │     │
│  │  - Complete      │         │  - Returns:               │     │
│  │  - Execute       │         │    InfoSeekerResult       │     │
│  │  - Review        │         │                           │     │
│  └────────┬─────────┘         └─────────────┬─────────────┘     │
│           │                                 │                   │
│           │ Review?                         ▼                   │
│           │                   ┌───────────────────────────┐     │
│           ▼                   │  Data Sources & Tools     │     │
│  ┌──────────────────┐         │  (Registry-based)         │     │
│  │  Human Approval  │         └───────────────────────────┘     │
│  │  for Correction  │                                           │
│  └──────────────────┘                                           │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Verifier Agent                           │
│                Validates answer, creates report                 │
│             Returns: Verification (validated model)             │
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
│   │   ├── config.py             # Configuration management
│   │   ├── orchestrator.py       # Main pipeline orchestrator (with human-in-the-loop)
│   │   ├── execution.py          # SensemakingLoop — drives the sensemaker↔info_seeker cycle
│   │   ├── interaction.py        # InteractionHandler — revision, replan, add-step flows
│   │   ├── context.py            # Context builders for LLM prompts (step history, replan)
│   │   ├── state.py              # ExecutionState — unified step states + memory entries
│   │   └── logger.py             # Logging infrastructure (loguru)
│   ├── agents/                 # Agent implementations
│   │   ├── base.py               # Base agent with _call_llm(messages, Model)
│   │   ├── planner.py            # Creates execution plans → Plan
│   │   ├── sensemaker.py         # Synthesizes info → Complete|Execute|Review
│   │   ├── information_seeker.py # Retrieves data → InfoSeekerResult
│   │   └── verifier.py           # Validates answers → Verification
│   ├── llm/                    # LLM client
│   │   └── structured_client.py  # Instructor-wrapped OpenAI client
│   ├── tools/                  # Extensible tool system
│   │   ├── base.py               # Base tool class
│   │   └── registry.py           # Tool registry
│   ├── data/                   # Data source management
│   │   ├── base.py               # Base data source (CSVDataSource)
│   │   ├── sandbox.py            # Docker sandbox bridge for isolated execution
│   │   ├── registry.py           # Data source registry & auto-discovery
│   │   └── schema.py             # Schema loader for YAML dataset metadata
│   └── ui/                     # Interactive terminal UI
│       ├── display.py            # Rich-based display components
│       ├── prompts.py            # Questionary-based prompts
│       └── export.py             # Run export to markdown
├── sandbox/                 # Docker sandbox
│   └── executor.py            # In-container code executor
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
Verification

# Execution types
ExecutionResult, StepState
```

### Sensemaker Response Types

| Response | When Used |
|----------|-----------|
| `CompleteResponse` | All steps completed, final answer ready |
| `ExecuteResponse` | Need to execute a step or request clarification |
| `ReviewResponse` | Data quality issue detected, proposes a fix |

## Sandbox Mode

### How it works

```
Host (CHAOS)                          Docker container (chaos-sandbox)
────────────                          ──────────────────────────────
InformationSeeker._execute_query()
  ├─ --sandbox:
  │   → docker run --rm -i            → /sandbox/executor.py
  │     --network=none                   reads JSON from stdin
  │     -v datasets:/data:ro             loads CSVs, exec(code)
  │     stdin: JSON payload              writes JSON to stdout
  │   ← parse stdout → ExecutionResult
  │
  └─ default:
      → exec() on host (current behavior, unchanged)
```

### Isolation guarantees

- **No network**: `--network=none` prevents any outbound connections
- **Read-only data**: Datasets mounted as `-v ...:/data:ro`
- **Ephemeral**: `--rm` removes the container after each execution
- **Timeout**: 30-second hard limit on container execution

### Testing the sandbox directly

```bash
echo '{"code": "result = df[\"heart_rate\"].mean()", "primary_source": "garmin_hr"}' | \
  docker run --rm -i --network=none -v "$(pwd)/datasets/gloss_sample:/data:ro" chaos-sandbox
```

## Human-in-the-Loop Mode

CHAOS includes a human-in-the-loop workflow where you can guide the analysis:

```
uv run python main.py "What is the average heart rate of test004?"
```

### Interaction Flow

```
User Query
    │
    ▼
┌───────────────────────────┐
│      PLAN CREATION        │
│   Planner creates plan    │
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│   HUMAN: Plan Review      │
│  > Approve and execute    │◄──┐
│    Modify plan steps      │   │
│    Reject                 │   │
└───────────┬───────────────┘   │
            │                   │
            ▼                   │
┌───────────────────────────┐   │
│   AUTOMATIC EXECUTION     │   │
│  Sensemaking loop runs    │   │
│  (progress displayed)     │   │
└───────────┬───────────────┘   │
            │                   │
            ▼                   │
┌───────────────────────────┐   │
│  DATA QUALITY ISSUE?      │   │
│  (e.g., -1 placeholder)   │   │
│                           │   │
│  > Approve correction     │   │
│    Modify correction      │   │
│    Skip                   │   │
└───────────┬───────────────┘   │
            │                   │
            ▼                   │
┌───────────────────────────┐   │
│      VERIFICATION         │   │
│  Verifier checks answer   │   │
└───────────┬───────────────┘   │
            │                   │
            ▼                   │
┌───────────────────────────┐   │
│   HUMAN: Final Review     │   │
│  > Accept answer          │   │
│    Reject                 │   │
│    Revise (fix a step)  ──┼───┤
│    Replan (fresh start) ──┼───┘
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│      RUN EXPORT           │
│  Export to markdown?      │
│  (saved to exported_runs/)│
└───────────────────────────┘
```

### Features

1. **Plan Review** (before execution)
   - **Approve**: Execute the plan as-is
   - **Modify**: Edit individual plan steps (changes are tracked and emphasized during execution)
   - **Reject**: Cancel and start over

2. **Automatic Execution**
   - Sensemaking runs without per-step approval
   - Real-time progress display with code and results

3. **Data Quality Correction** (during execution)
   - When suspicious data is detected (e.g., -1 as placeholder for missing values)
   - Sensemaker proposes a fix (e.g., "exclude -1 values")
   - Human can **Approve**, **Modify**, or **Skip** the correction
   - Corrected query is re-executed automatically

4. **Final Review** (after verification)
   - **Accept**: Finalize the answer
   - **Revise**: Go back and fix a specific step that went wrong
   - **Replan**: Start fresh with learnings from the failed attempt
   - **Reject**: Discard and start over

5. **Run Export**
   - After accepting or rejecting, export the full run to markdown
   - Includes: query, plan, all agent exchanges, corrections, final answer, verification
   - Saved to `exported_runs/` directory by default

## Adding Data Sources

### Dataset Directory

The dataset directory is configured in `chaos/core/config.py`:

```python
datasets_dir: Path = Path("datasets/gloss_sample")
```

Change this path to point to your dataset folder. Only CSV files within the configured directory (and its subdirectories) will be auto-discovered. This prevents accidentally loading unrelated datasets that may exceed LLM context limits.

### Auto-Discovery

Place CSV files in your configured dataset directory and they will be auto-discovered:

```
datasets/gloss_sample/
├── data_schema.yaml   → Optional: rich column metadata for the LLM
├── garmin_hr.csv      → Becomes "garmin_hr" source
├── garmin_steps.csv   → Becomes "garmin_steps" source
└── ios_activity.csv   → Becomes "ios_activity" source
```

### Custom Data Sources

Implement `BaseDataSource` for custom data sources:

```python
from chaos.data.base import BaseDataSource
from chaos.types import ExecutionResult

class MyDataSource(BaseDataSource):
    name = "my_source"
    description = "My custom data source"

    def get_schema(self):
        return {
            "columns": ["col1", "col2"],
            "types": {"col1": "int64", "col2": "string"},
            "row_count": 1000
        }

    def query(self, query_type: str, **kwargs) -> ExecutionResult:
        if query_type == "exec":
            code = kwargs.get("code", "")
            # Execute code and return result
            return ExecutionResult(result="computed value")
        return ExecutionResult(error="Unknown query type")
```

## Adding Tools

Implement `BaseTool` and register with `ToolRegistry`:

```python
from chaos.tools.base import BaseTool

class MyTool(BaseTool):
    name = "my_tool"
    description = "Does something useful"

    def _get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string"}
            }
        }

    def execute(self, **kwargs):
        # Implement tool logic
        return {"result": "success"}
```

## Dependencies

- **instructor** - Structured LLM outputs with Pydantic validation
- **pydantic** - Data validation and type hints
- **openai** - OpenAI-compatible API client (used with OpenRouter)
- **pandas** - Data manipulation
- **numpy** - Numerical operations
- **httpx** - HTTP client
- **questionary** - Interactive terminal prompts (for `--interactive` mode)
- **rich** - Terminal formatting and tables (for `--interactive` mode)

## License

MIT
