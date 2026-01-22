# CHAOS

**C**oordinated **H**ierarchical **A**gent **O**rchestration **S**ystem

A multi-agent LLM system for open-ended sensemaking over datasets.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          User Query                             │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Planner Agent                            │
│                 Creates execution plan from query               │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Sensemaking Loop                             │
│  ┌──────────────────┐         ┌───────────────────────────┐     │
│  │  Sensemaker      │◄───────►│  Information Seeking      │     │
│  │  Agent           │         │  Agent                    │     │
│  │  - Updates memory│         │  - Queries data sources   │     │
│  │  - Synthesizes   │         │  - Uses tools             │     │
│  │  - Sends COMPLETE│         │                           │     │
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
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Human Review                            │
│                 Approve / Reject / Add Info                     │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
CHAOS/
├── chaos/                 # Main package
│   ├── core/                # Orchestration & config
│   │   ├── config.py          # Configuration management
│   │   └── orchestrator.py    # Main pipeline orchestrator
│   ├── agents/             # Agent implementations
│   │   ├── base.py          # Base agent class
│   │   ├── planner.py       # Creates execution plans
│   │   ├── sensemaker.py    # Synthesizes information
│   │   ├── information_seeker.py  # Retrieves data
│   │   └── verifier.py      # Validates answers
│   ├── tools/              # Extensible tool system
│   │   ├── base.py          # Base tool class
│   │   └── registry.py      # Tool registry
│   ├── data/               # Data source management
│   │   ├── base.py          # Base data source class
│   │   └── registry.py      # Data source registry
│   └── memory/             # Working memory
│       └── memory.py         # Memory management
├── datasets/             # Place datasets here
├── tests/                # Test suite
├── main.py               # Entry point
└── pyproject.toml        # Project configuration
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

## Usage

```bash
# Interactive mode
python main.py

# Single query
python main.py "What patterns do you see in the data?"

# With options
python main.py --datasets-dir ./my_data --max-iterations 3 --verbose
```

## Adding Data Sources

Place CSV files in the `datasets/` directory - they will be auto-discovered.

For custom data sources, implement `BaseDataSource`:

```python
from chaos.data.base import BaseDataSource

class MyDataSource(BaseDataSource):
    name = "my_source"
    description = "My custom data source"

    def get_schema(self):
        return {"columns": ["col1", "col2"]}

    def query(self, query, **kwargs):
        # Implement query logic
        pass
```

## Adding Tools

Implement `BaseTool` and register with `ToolRegistry`:

```python
from chaos.tools.base import BaseTool

class MyTool(BaseTool):
    name = "my_tool"
    description = "Does something useful"

    def _get_parameters_schema(self):
        return {"type": "object", "properties": {...}}

    def execute(self, **kwargs):
        # Implement tool logic
        pass
```

## License

MIT
