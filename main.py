"""CHAOS - Coordinated Hierarchical Agent Orchestration System.

Entry point for the multi-agent sensemaking system.
"""

import argparse
import sys
from pathlib import Path

from chaos.core.config import Config, LLMConfig, LogConfig
from chaos.core.logger import get_logger, setup_logging
from chaos.core.orchestrator import Orchestrator
from chaos.data.registry import DataRegistry
from chaos.llm import StructuredLLMClient

def print_result(result: dict) -> None:                                                                                                                                                       
    """Print query result."""                                                                                                                                                                 
    print(f"\n{'='*60}")                                                                                                                                                                      
    print("ANSWER:", result.get("answer", "No answer generated"))                                                                                                                             
    print(f"{'='*60}")                                                                                                                                                                        
    print(f"\nConfidence: {result.get('confidence', 0.0):.2f}\n") 

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="CHAOS - Multi-agent sensemaking system"
    )
    parser.add_argument(
        "query",
        nargs="?",
        default="This is an example query. Replace it with your own.",
        help="Natural language query to process",
    )
    parser.add_argument(
        "--datasets-dir",
        type=Path,
        default=Path("datasets"),
        help="Directory containing datasets",
    )
    parser.add_argument(
        "--max-step-attempts",
        type=int,
        default=5,
        help="Maximum attempts per step",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="WARNING",
        help="Set log level (default: WARNING)",
    )
    parser.add_argument(
        "--model",
        type=str,
        help="LLM model to use (default: moonshotai/kimi-k2.5)",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Set up logging
    setup_logging(level=args.log_level)

    # Get logger for main module
    logger = get_logger("Main")

    # Initialize configuration
    config = Config(
        llm=LLMConfig(),
        log=LogConfig(level=args.log_level),
        max_step_attempts=args.max_step_attempts,
        datasets_dir=args.datasets_dir,
    )

    # Initialize LLM client
    try:
        llm_client = StructuredLLMClient(config.llm)
    except ValueError as e:
        print(f"Error: {e}")
        print("\nPlease set your OpenRouter API key:")
        print("  export OPENROUTER_API_KEY=your_key_here")
        sys.exit(1)

    # Initialize data registry
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
        data_registry=data_registry,
    )

    # Run interactive mode 
    result = orchestrator.run(args.query)
    print_result(result)

    print("\nGoodbye!")


if __name__ == "__main__":
    main()

