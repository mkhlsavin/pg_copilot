"""Test script for streaming progress output.

This script tests the new Rich-based streaming progress tracker
with sample questions to demonstrate real-time agent progress.

Usage:
    conda activate llama.cpp
    python test_streaming_progress.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.workflow.langgraph_workflow import run_workflow


def test_streaming_mode():
    """Test streaming progress with a sample question."""
    print("\n" + "="*80)
    print("TESTING STREAMING PROGRESS MODE")
    print("="*80 + "\n")

    test_questions = [
        "How does PostgreSQL handle MVCC?",
        "What is the purpose of the vacuum process?",
        "How are indexes stored in PostgreSQL?"
    ]

    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*80}")
        print(f"Test {i}/{len(test_questions)}")
        print(f"{'='*80}\n")

        # Run with streaming mode enabled
        result = run_workflow(
            question=question,
            verbose=False,  # Disable legacy verbose mode
            streaming=True  # Enable Rich streaming
        )

        if result["success"]:
            print(f"\n✓ Test {i} completed successfully")
        else:
            print(f"\n✗ Test {i} failed: {result.get('error', 'Unknown error')}")

        # Add separator between tests
        if i < len(test_questions):
            input("\nPress Enter to continue to next test...")


def test_legacy_mode():
    """Test legacy verbose mode (backward compatibility)."""
    print("\n" + "="*80)
    print("TESTING LEGACY VERBOSE MODE (Backward Compatibility)")
    print("="*80 + "\n")

    question = "How does PostgreSQL handle transaction isolation?"

    # Run with legacy verbose mode
    result = run_workflow(
        question=question,
        verbose=True,   # Legacy mode
        streaming=False  # No streaming
    )

    if result["success"]:
        print("\n✓ Legacy mode works correctly")
    else:
        print(f"\n✗ Legacy mode failed: {result.get('error', 'Unknown error')}")


def main():
    """Main test runner."""
    print("\nRAG-CPGQL Streaming Progress Test Suite")
    print("="*80)
    print("\nThis test suite demonstrates:")
    print("  1. Rich-based streaming progress with real-time agent updates")
    print("  2. Backward compatibility with legacy verbose mode")
    print("  3. Colorized status indicators and metrics display")
    print("\n" + "="*80)

    choice = input("\nChoose test mode:\n  1. Streaming mode (Rich console)\n  2. Legacy mode\n  3. Both\n\nEnter choice (1-3): ").strip()

    if choice == "1":
        test_streaming_mode()
    elif choice == "2":
        test_legacy_mode()
    elif choice == "3":
        test_streaming_mode()
        print("\n" + "="*80 + "\n")
        input("Press Enter to test legacy mode...")
        test_legacy_mode()
    else:
        print("Invalid choice. Exiting.")
        return

    print("\n" + "="*80)
    print("Test suite completed!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
