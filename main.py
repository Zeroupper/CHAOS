"""CHAOS - Coordinated Hierarchical Agent Orchestration System.

Entry point for the multi-agent sensemaking system.
"""

import argparse
from pathlib import Path

from chaos.core.config import Config
from chaos.core.orchestrator import Orchestrator
from chaos.data.registry import DataRegistry
from chaos.tools.registry import ToolRegistry


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="CHAOS - Multi-agent sensemaking system"
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Natural language query to process",
    )
    parser.add_argument(
        "--datasets-dir",
        type=Path,
        default=Path("datasets"),
        help="Directory containing datasets",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="Maximum sensemaking iterations",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Initialize configuration
    config = Config(
        max_iterations=args.max_iterations,
        datasets_dir=args.datasets_dir,
        verbose=args.verbose,
    )

    # Initialize registries
    tool_registry = ToolRegistry()
    data_registry = DataRegistry()

    # Auto-discover data sources
    data_registry.auto_discover(args.datasets_dir)

    # Create orchestrator
    orchestrator = Orchestrator(
        config=config,
        tool_registry=tool_registry,
        data_registry=data_registry,
    )

    # Run interactive mode or single query
    if args.query:
        result = orchestrator.run(args.query)
        print(f"\nResult: {result}")
    else:
        # Interactive mode
        print("CHAOS - Multi-agent Sensemaking System")
        print("Enter your query (or 'quit' to exit):\n")

        while True:
            try:
                query = input("> ").strip()
                if query.lower() in ("quit", "exit", "q"):
                    break
                if not query:
                    continue

                result = orchestrator.run(query)
                print(f"\nResult: {result}\n")
            except KeyboardInterrupt:
                break

    print("\nGoodbye!")


if __name__ == "__main__":
    main()
