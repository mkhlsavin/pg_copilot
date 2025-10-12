"""Test script for LangGraph RAG-CPGQL workflow.

This script tests the complete 9-agent LangGraph workflow on sample questions
and compares performance with the original 4-agent system.
"""

import sys
from pathlib import Path
import json
import time
import subprocess
from typing import List, Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.workflow.langgraph_workflow import run_workflow

SCRIPT_ROOT = Path(__file__).parent.parent
BOOTSTRAP_SCRIPT = SCRIPT_ROOT / "scripts" / "bootstrap_joern.ps1"


def bootstrap_joern(force_restart: bool = False) -> None:
    """Ensure Joern server is running and workspace is loaded."""
    if not BOOTSTRAP_SCRIPT.exists():
        print(f"[WARNING] Bootstrap script missing: {BOOTSTRAP_SCRIPT}")
        return

    command = [
        "powershell",
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(BOOTSTRAP_SCRIPT),
    ]

    if force_restart:
        command.append("-ForceRestart")

    print("\n[BOOTSTRAP] Initializing Joern server...")
    result = subprocess.run(command, cwd=str(SCRIPT_ROOT), capture_output=True, text=True)

    if result.returncode != 0:
        print("[BOOTSTRAP] Joern bootstrap failed:")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        raise RuntimeError("Joern bootstrap script failed")

    if result.stdout:
        print(result.stdout.strip())
    print("[BOOTSTRAP] Joern ready.\n")


def test_langgraph_workflow(
    test_questions: List[str] = None,
    num_samples: int = 10,
    save_results: bool = True,
    auto_bootstrap: bool = True,
    force_restart: bool = False
):
    """Test LangGraph workflow on sample questions.

    Args:
        test_questions: Optional list of custom questions
        num_samples: Number of questions to test (if no custom questions)
        save_results: Whether to save results to JSON
    """
    print("\n" + "="*80)
    print("LANGGRAPH RAG-CPGQL WORKFLOW TEST")
    print("="*80 + "\n")

    # Default test questions if none provided
    if test_questions is None:
        test_questions = [
            # MVCC
            "How does PostgreSQL handle transaction isolation in MVCC?",
            "What is the purpose of TransactionIdIsValid function?",
            "How does PostgreSQL implement snapshot isolation?",

            # WAL
            "How does PostgreSQL implement Write-Ahead Logging?",
            "What are the key functions in WAL writing?",

            # Query Planning
            "How does PostgreSQL choose between sequential and index scans?",
            "What is the role of the query planner in PostgreSQL?",

            # Memory Management
            "How does PostgreSQL manage memory contexts?",
            "What is the purpose of palloc in PostgreSQL?",

            # Security
            "How does PostgreSQL implement authentication?",
        ]

    test_questions = test_questions[:num_samples]

    if auto_bootstrap:
        bootstrap_joern(force_restart=force_restart)

    print(f"Testing {len(test_questions)} questions...\n")

    # Initialize vector store once
    print("[1/2] Initializing vector store...")
    from src.retrieval.vector_store_real import VectorStoreReal
    try:
        vector_store = VectorStoreReal()
        # Check if collections exist
        try:
            qa_count = vector_store.qa_collection.count()
            cpgql_count = vector_store.cpgql_collection.count()
            if qa_count == 0 or cpgql_count == 0:
                print("  [WARNING] Vector store empty. Run vector_store_real.py to index data.")
                print(f"  Q&A count: {qa_count}, CPGQL count: {cpgql_count}")
            else:
                print(f"  [OK] Vector store ready: {qa_count} Q&A, {cpgql_count} CPGQL examples\n")
        except Exception:
            print("  [WARNING] Could not verify vector store contents")
    except Exception as e:
        print(f"  [ERROR] Vector store initialization failed: {e}")
        return

    # Run tests
    print("[2/2] Running workflow tests...\n")

    results = []
    start_time = time.time()

    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*80}")
        print(f"Test {i}/{len(test_questions)}")
        print(f"{'='*80}")

        # Run workflow
        result = run_workflow(question, verbose=True)

        # Store result
        results.append({
            "question_num": i,
            "question": question,
            "success": result.get("success", False),
            "query": result.get("query"),
            "answer": result.get("answer"),
            "valid": result.get("valid", False),
            "execution_success": result.get("execution_success", False),
            "overall_score": result.get("overall_score", 0.0),
            "total_time": result.get("total_time", 0.0),
            "error": result.get("error")
        })

    total_time = time.time() - start_time

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80 + "\n")

    successful = sum(1 for r in results if r["success"])
    valid_queries = sum(1 for r in results if r["valid"])
    executed = sum(1 for r in results if r["execution_success"])
    avg_score = sum(r["overall_score"] for r in results) / len(results) if results else 0
    avg_time = sum(r["total_time"] for r in results) / len(results) if results else 0

    print(f"Total questions:       {len(results)}")
    print(f"Successful workflows:  {successful}/{len(results)} ({100*successful/len(results):.1f}%)")
    print(f"Valid queries:         {valid_queries}/{len(results)} ({100*valid_queries/len(results):.1f}%)")
    print(f"Successful execution:  {executed}/{valid_queries} ({100*executed/valid_queries:.1f}% of valid)" if valid_queries > 0 else "Successful execution:  0/0")
    print(f"\nAverage RAGAS score:   {avg_score:.3f}")
    print(f"Average time/question: {avg_time:.2f}s")
    print(f"Total test time:       {total_time:.2f}s")

    # Domain breakdown
    print(f"\n{'='*80}")
    print("DETAILED RESULTS")
    print(f"{'='*80}\n")

    for r in results:
        status = "✓" if r["success"] and r["valid"] else "✗"
        exec_status = "✓" if r["execution_success"] else "✗"
        print(f"{status} Q{r['question_num']}: Valid={r['valid']}, "
              f"Exec={exec_status}, "
              f"Score={r['overall_score']:.3f}, "
              f"Time={r['total_time']:.2f}s")

    # Save results
    if save_results:
        output_file = project_root / "results" / "langgraph_workflow_test_results.json"
        output_file.parent.mkdir(exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "test_name": "LangGraph RAG-CPGQL Workflow Test",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "config": {
                    "num_questions": len(results),
                    "workflow_type": "9-agent LangGraph"
                },
                "summary": {
                    "successful_workflows": successful,
                    "valid_queries": valid_queries,
                    "executed_successfully": executed,
                    "avg_ragas_score": avg_score,
                    "avg_time_per_question": avg_time,
                    "total_time": total_time
                },
                "results": results
            }, f, indent=2, ensure_ascii=False)

        print(f"\n[OK] Results saved to: {output_file}")

    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80 + "\n")

    return results


def compare_with_baseline():
    """Compare LangGraph workflow with baseline 4-agent system."""
    print("\n" + "="*80)
    print("COMPARISON: LANGGRAPH vs BASELINE")
    print("="*80 + "\n")

    # Load baseline results
    baseline_file = Path(__file__).parent.parent / "results" / "test_30_questions_results.json"

    if not baseline_file.exists():
        print("[WARNING] Baseline results not found. Run test_30_questions.py first.")
        return

    with open(baseline_file, 'r', encoding='utf-8') as f:
        baseline = json.load(f)

    # Load LangGraph results
    langgraph_file = Path(__file__).parent.parent / "results" / "langgraph_workflow_test_results.json"

    if not langgraph_file.exists():
        print("[WARNING] LangGraph results not found. Run this test first.")
        return

    with open(langgraph_file, 'r', encoding='utf-8') as f:
        langgraph = json.load(f)

    # Compare metrics
    print("Metric                    Baseline (4-agent)    LangGraph (9-agent)    Difference")
    print("-" * 90)

    baseline_validity = baseline["validity_rate"] / 100
    langgraph_validity = langgraph["summary"]["valid_queries"] / langgraph["summary"]["successful_workflows"] if langgraph["summary"]["successful_workflows"] > 0 else 0

    print(f"Validity Rate             {baseline_validity:6.1%}               {langgraph_validity:6.1%}              {(langgraph_validity - baseline_validity)*100:+.1f}%")

    baseline_time = baseline["avg_generation_time"]
    langgraph_time = langgraph["summary"]["avg_time_per_question"]

    print(f"Avg Time (s)              {baseline_time:6.2f}s              {langgraph_time:6.2f}s             {langgraph_time - baseline_time:+.2f}s")

    # RAGAS scores (only in LangGraph)
    langgraph_score = langgraph["summary"]["avg_ragas_score"]
    print(f"RAGAS Score               N/A                  {langgraph_score:6.3f}              (new)")

    print("\nKey Improvements:")
    print("- ✓ RAGAS evaluation integrated")
    print("- ✓ Retry logic with query refinement")
    print("- ✓ Natural language answer interpretation")
    print("- ✓ Stateful workflow with observability")
    print("- ✓ Modular and testable architecture")

    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test LangGraph RAG-CPGQL workflow')
    parser.add_argument('--samples', type=int, default=10,
                        help='Number of test samples (default: 10)')
    parser.add_argument('--questions', nargs='+',
                        help='Custom questions to test')
    parser.add_argument('--compare', action='store_true',
                        help='Compare with baseline after test')
    parser.add_argument('--no-bootstrap', action='store_true',
                        help='Skip automatic Joern bootstrap')
    parser.add_argument('--force-restart', action='store_true',
                        help='Force restart Joern server during bootstrap')

    args = parser.parse_args()

    # Run test
    results = test_langgraph_workflow(
        test_questions=args.questions,
        num_samples=args.samples,
        save_results=True,
        auto_bootstrap=not args.no_bootstrap,
        force_restart=args.force_restart
    )

    # Compare with baseline
    if args.compare and results:
        compare_with_baseline()
