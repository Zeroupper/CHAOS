# CHAOS

**C**oordinated **H**ierarchical **A**gent **O**rchestration **S**ystem

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
- **Extensible Architecture**: Easy to add new data sources and tools
- **Memory Management**: Working memory tracks execution state across iterations

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
│                    Sensemaking Loop                             │
│  ┌──────────────────┐         ┌───────────────────────────┐     │
│  │  Sensemaker      │◄───────►│  Information Seeking      │     │
│  │  Agent           │         │  Agent                    │     │
│  │  - Updates memory│         │  - Queries data sources   │     │
│  │  - Synthesizes   │         │  - Executes Python code   │     │
│  │  - Returns:      │         │  - Returns:               │     │
│  │    Complete |    │         │    QueryDecision          │     │
│  │    NeedsInfo     │         │    InfoSeekerResult       │     │
│  └──────────────────┘         └─────────────┬─────────────┘     │
│                                             │                   │
│                                             ▼                   │
│                               ┌───────────────────────────┐     │
│                               │  Data Sources & Tools     │     │
│                               │  (Registry-based)         │     │
│                               └───────────────────────────┘     │
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
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
CHAOS/
├── chaos/                    # Main package
│   ├── types.py                # Pydantic models for all data structures
│   ├── core/                   # Orchestration & config
│   │   ├── config.py             # Configuration management
│   │   ├── orchestrator.py       # Main pipeline orchestrator
│   │   └── logger.py             # Logging infrastructure
│   ├── agents/                 # Agent implementations
│   │   ├── base.py               # Base agent with _call_llm(messages, Model)
│   │   ├── planner.py            # Creates execution plans → Plan
│   │   ├── sensemaker.py         # Synthesizes information → Complete|NeedsInfo
│   │   ├── information_seeker.py # Retrieves data → InfoSeekerResult
│   │   └── verifier.py           # Validates answers → Verification
│   ├── llm/                    # LLM client
│   │   └── structured_client.py  # Instructor-wrapped OpenAI client
│   ├── tools/                  # Extensible tool system
│   │   ├── base.py               # Base tool class
│   │   └── registry.py           # Tool registry
│   ├── data/                   # Data source management
│   │   ├── base.py               # Base data source (CSVDataSource)
│   │   ├── registry.py           # Data source registry & auto-discovery
│   │   └── schema.py             # Schema generation utilities
│   └── memory/                 # Working memory
│       └── memory.py             # Memory management
├── datasets/                 # Place datasets here (auto-discovered)
├── tests/                    # Test suite
├── main.py                   # Entry point
└── pyproject.toml            # Project configuration
```

## Type System

All LLM responses are validated Pydantic models defined in `chaos/types.py`:

```python
# Plan types
Plan, PlanStep

# Information seeker types
QueryDecision, InfoSeekerResult

# Sensemaker response (discriminated union)
CompleteResponse | NeedsInfoResponse

# Verifier types
Verification

# Execution types
ExecutionResult, StepMemoryEntry
```

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/CHAOS.git
cd CHAOS

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

## Configuration

Set your OpenRouter API key:

```bash
export OPENROUTER_API_KEY=your_key_here
```

## Usage

```bash
# Interactive mode
uv run python main.py

# Single query
uv run python main.py "What is the average heart rate of test004?"

# With options
uv run python main.py "Your query" --datasets-dir ./my_data --max-iterations 5

# Verbose output
uv run python main.py "Your query" --verbose   # INFO level
uv run python main.py "Your query" --debug     # DEBUG level

# Use a different model (any OpenRouter model works)
uv run python main.py "Your query" --model "anthropic/claude-3.5-sonnet"
uv run python main.py "Your query" --model "deepseek/deepseek-chat"
uv run python main.py "Your query" --model "openai/gpt-4o"
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--datasets-dir` | Directory containing datasets | `./datasets` |
| `--max-iterations` | Maximum sensemaking loop iterations | `5` |
| `--verbose`, `-v` | Enable INFO level logging | Off |
| `--debug` | Enable DEBUG level logging | Off |
| `--log-level` | Explicit log level (DEBUG/INFO/WARNING/ERROR) | WARNING |
| `--no-color` | Disable ANSI colors in output | Off |
| `--model` | LLM model to use | `openai/chatgpt-4o-latest` |

## Adding Data Sources

### Auto-Discovery

Place CSV files in the `datasets/` directory - they will be auto-discovered:

```
datasets/
├── user_data.csv      → Becomes "user_data" source
├── heart_rate.csv     → Becomes "heart_rate" source
└── subdirectory/
    └── steps.csv      → Becomes "steps" source
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

## License

MIT
