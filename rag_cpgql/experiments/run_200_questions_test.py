"""Runner script for 200-question test with setup verification."""
import sys
from pathlib import Path
import subprocess

def check_requirements():
    """Check if all requirements are met."""
    print("Checking requirements...")

    issues = []

    # Check data directory
    data_dir = Path(__file__).parent.parent / "data"
    train_file = data_dir / "train_split_merged.jsonl"

    if not train_file.exists():
        issues.append(f"Missing training data: {train_file}")

    # Check ChromaDB collections
    chroma_dir = Path(__file__).parent.parent / "chroma_db"
    if not chroma_dir.exists():
        issues.append(f"ChromaDB not initialized: {chroma_dir}")

    # Check model availability
    try:
        from generation.llm_interface import LLMInterface
        print("  [OK] LLM interface available")
    except ImportError as e:
        issues.append(f"Cannot import LLM interface: {e}")

    if issues:
        print("\nIssues found:")
        for issue in issues:
            print(f"  - {issue}")
        return False

    print("  [OK] All requirements met\n")
    return True


def estimate_time():
    """Estimate test duration."""
    print("Time estimates:")
    print("  Based on 30-question test (~4s per query):")
    print("  - 200 questions * 4s = ~13.3 minutes")
    print("  - With overhead: ~15-20 minutes total")
    print()
    print("  Checkpoints saved every 50 questions")
    print("  Test can be resumed if interrupted\n")


def main():
    """Run the 200-question test."""
    print("="*80)
    print("RAG-CPGQL: 200-Question Test Runner")
    print("="*80)
    print()

    if not check_requirements():
        print("\nPlease fix the issues above before running the test.")
        return 1

    estimate_time()

    # Ask for confirmation
    response = input("Start 200-question test? (y/n): ").lower()
    if response != 'y':
        print("Test cancelled.")
        return 0

    print("\nStarting test...\n")

    # Run the test
    test_script = Path(__file__).parent / "test_200_questions.py"

    try:
        result = subprocess.run(
            [sys.executable, str(test_script)],
            cwd=Path(__file__).parent.parent
        )
        return result.returncode

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        print("Progress has been saved. Run again to resume.")
        return 130

    except Exception as e:
        print(f"\nError running test: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
