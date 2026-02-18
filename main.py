"""CHAOS - Coordinated Hierarchical Agent Orchestration System.

Entry point for the multi-agent sensemaking system.
"""

import argparse
import sys

from chaos.core.config import Config, LLMConfig, LogConfig
from chaos.core.logger import setup_logging
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
    parser.add_argument(
        "--sandbox",
        action="store_true",
        help="Run LLM-generated code in Docker sandbox",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve planner and sensemaker decisions without human guidance",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Set up logging
    setup_logging(level=args.log_level)

    # Initialize configuration
    config = Config(
        llm=LLMConfig(),
        log=LogConfig(level=args.log_level),
        max_step_attempts=args.max_step_attempts,
        sandbox=args.sandbox,
        auto_approve=args.auto_approve,
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
    data_registry.auto_discover(config.datasets_dir)

    sources = data_registry.list_sources()
    print(f"\nDiscovered {len(sources)} data sources from {config.datasets_dir}:")
    for s in sources:
        print(f"  - {s['name']}")
    print()

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

