"""
Simple interactive demo for CodeGraph.

Usage:
    python examples/demo_simple.py

Commands:
    help     - Show available commands and example queries
    examples - Show example queries for different scenarios
    quit     - Exit the demo
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.workflow import MultiScenarioCopilot


EXAMPLE_QUERIES = {
    "Security": [
        "Find potential SQL injection vulnerabilities",
        "Show unsanitized user input paths",
        "Find buffer overflow risks",
    ],
    "Architecture": [
        "Give me an overview of the executor module",
        "What is the call hierarchy of CommitTransaction?",
        "Show the data flow from parser to executor",
    ],
    "Performance": [
        "Find functions with high cyclomatic complexity",
        "Identify N+1 query patterns",
        "Show memory allocation hotspots",
    ],
}


def print_banner():
    """Print welcome banner."""
    print("=" * 60)
    print("  CodeGraph Interactive Demo")
    print("  Type 'help' for commands, 'examples' for sample queries")
    print("=" * 60)
    print()


def print_help():
    """Print help message with available commands."""
    print("\nCommands:")
    print("  help     - Show this help message")
    print("  examples - Show example queries for different scenarios")
    print("  quit     - Exit the demo")
    print("\nJust type your question to analyze the codebase.\n")


def print_examples():
    """Print example queries organized by category."""
    print("\nExample Queries:\n")
    for category, queries in EXAMPLE_QUERIES.items():
        print(f"  [{category}]")
        for q in queries:
            print(f"    > {q}")
        print()


def format_result(result: dict) -> str:
    """Format result for display.

    Args:
        result: Dictionary containing query result with keys:
            - answer: The generated answer
            - intent: Detected intent category
            - confidence: Confidence score (0-1)
            - sources: List of source references

    Returns:
        Formatted string for terminal display.
    """
    output = []
    output.append("\n" + "-" * 60)

    if result.get('intent'):
        output.append(f"Intent: {result['intent']}")
    if result.get('confidence'):
        output.append(f"Confidence: {result['confidence']:.2f}")

    output.append("-" * 60)
    output.append(f"\n{result.get('answer', 'No answer available')}\n")

    if result.get('sources'):
        output.append("Sources:")
        for src in result['sources'][:5]:
            output.append(f"  - {src}")

    output.append("-" * 60 + "\n")
    return "\n".join(output)


def main():
    """Main entry point for interactive demo."""
    print_banner()

    try:
        copilot = MultiScenarioCopilot()
    except Exception as e:
        print(f"Error initializing CodeGraph: {e}")
        print("Make sure you have a CPG database (cpg.duckdb) available.")
        return 1

    while True:
        try:
            question = input("> ").strip()

            if not question:
                continue
            elif question.lower() in ('quit', 'exit', 'q'):
                break
            elif question.lower() == 'help':
                print_help()
                continue
            elif question.lower() == 'examples':
                print_examples()
                continue

            print("\nAnalyzing...")
            result = copilot.run(question)
            print(format_result(result))

        except KeyboardInterrupt:
            print()
            break
        except Exception as e:
            print(f"\nError: {e}\n")

    print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
