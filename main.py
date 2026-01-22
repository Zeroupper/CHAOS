"""CHAOS - Coordinated Hierarchical Agent Orchestration System.

Entry point for the multi-agent sensemaking system.
"""

import argparse
import sys
from pathlib import Path

from chaos.core.config import Config, LogConfig
from chaos.core.logger import get_logger, setup_logging
from chaos.core.orchestrator import Orchestrator
from chaos.data.registry import DataRegistry
from chaos.llm import LLMClient
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
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output (INFO level)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output (DEBUG level, more verbose than --verbose)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="Set explicit log level (overrides --verbose and --debug)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors in output",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="openai/chatgpt-4o-latest",
        help="LLM model to use (default: openai/chatgpt-4o-latest)",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Determine log level
    if args.log_level:
        log_level = args.log_level
    elif args.debug:
        log_level = "DEBUG"
    elif args.verbose:
        log_level = "INFO"
    else:
        log_level = "WARNING"

    # Set up logging
    use_colors = not args.no_color
    setup_logging(level=log_level, use_colors=use_colors)

    # Get logger for main module
    logger = get_logger("Main")

    # Initialize configuration
    log_config = LogConfig(level=log_level, use_colors=use_colors)
    config = Config(
        max_iterations=args.max_iterations,
        datasets_dir=args.datasets_dir,
        log=log_config,
    )
    config.llm.model = args.model

    # Initialize LLM client
    try:
        llm_client = LLMClient(config.llm)
    except ValueError as e:
        print(f"Error: {e}")
        print("\nPlease set your OpenRouter API key:")
        print("  export OPENROUTER_API_KEY=your_key_here")
        sys.exit(1)

    # Initialize registries
    tool_registry = ToolRegistry()
    data_registry = DataRegistry()

    # Auto-discover data sources
    data_registry.auto_discover(args.datasets_dir)

    sources = data_registry.list_sources()
    source_names = ", ".join(s["name"] for s in sources) if sources else "none"
    logger.info(f"Discovered {len(sources)} data sources: {source_names}")

    # Create orchestrator
    orchestrator = Orchestrator(
        config=config,
        llm_client=llm_client,
        tool_registry=tool_registry,
        data_registry=data_registry,
    )

    # Run interactive mode or single query
    if args.query:
        result = orchestrator.run(args.query)
        print(f"\n{'='*60}")
        print("ANSWER:")
        print(f"{'='*60}")
        print(result.get("answer", "No answer generated"))
        print(f"\nConfidence: {result.get('confidence', 0.0):.2f}")
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
                print(f"\n{'='*60}")
                print("ANSWER:")
                print(f"{'='*60}")
                print(result.get("answer", "No answer generated"))
                print(f"\nConfidence: {result.get('confidence', 0.0):.2f}")
                print()
            except KeyboardInterrupt:
                break

    print("\nGoodbye!")


if __name__ == "__main__":
    main()
