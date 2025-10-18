"""Execute the LangGraph workflow on 200 questions with Joern execution enabled."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.execution.joern_bootstrap import ensure_joern_ready, reset_bootstrap_state
from src.workflow.langgraph_workflow import run_workflow
from langchain_core.messages import BaseMessage


def load_questions(dataset_path: Path, limit: int = 200, seed: int = 42) -> List[str]:
    """Load up to `limit` questions from the merged training split."""
    with dataset_path.open("r", encoding="utf-8") as f:
        data = [json.loads(line) for line in f]

    questions = [item["question"] for item in data if "question" in item]

    if not questions:
        raise ValueError(f"No questions found in {dataset_path}")

    random.seed(seed)
    if len(questions) > limit:
        questions = random.sample(questions, limit)
    else:
        questions = questions[:limit]

    return questions


def _to_jsonable(value: Any) -> Any:
    """Recursively convert LangChain message objects and other non-JSON types."""
    if isinstance(value, BaseMessage):
        return {"type": value.type, "content": value.content}
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _sanitize_outcome(outcome: Dict[str, Any]) -> Dict[str, Any]:
    """Strip non-serializable fields from a workflow outcome."""
    sanitized = {
        "question": outcome.get("question"),
        "question_index": outcome.get("question_index"),
        "query": outcome.get("query"),
        "answer": outcome.get("answer"),
        "valid": outcome.get("valid"),
        "overall_score": outcome.get("overall_score"),
        "total_time": outcome.get("total_time"),
        "execution_success": outcome.get("execution_success"),
        "execution_error": outcome.get("execution_error"),
        "success": outcome.get("success"),
        "elapsed": outcome.get("elapsed"),
    }

    state = outcome.get("state") or {}
    sanitized["state"] = _to_jsonable(state)

    return sanitized


def summarize_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute aggregate statistics for the run."""
    executed = [r for r in results if r.get("execution_success")]
    successful = [r for r in results if r.get("success")]
    valid = [r for r in results if r.get("valid")]

    overall_score = sum(r.get("overall_score", 0.0) for r in successful)
    total_time = sum(r.get("total_time", 0.0) for r in successful)

    return {
        "questions_total": len(results),
        "successful_workflows": len(successful),
        "valid_queries": len(valid),
        "execution_successes": len(executed),
        "avg_ragas_score": (overall_score / len(successful)) if successful else 0.0,
        "avg_time_per_question": (total_time / len(successful)) if successful else 0.0,
        "total_time": total_time,
    }


def run_questions(
    questions: List[str],
    force_restart: bool = False,
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """Run the workflow for each question."""
    if force_restart:
        reset_bootstrap_state()

    if not ensure_joern_ready(force_restart=force_restart):
        raise RuntimeError("Failed to bootstrap Joern server.")

    results: List[Dict[str, Any]] = []

    for idx, question in enumerate(questions, 1):
        print(f"[{idx}/{len(questions)}] {question[:80]}...")
        start = time.time()
        outcome = run_workflow(question, verbose=verbose)
        outcome["elapsed"] = time.time() - start
        outcome["question_index"] = idx

        sanitized = _sanitize_outcome(outcome)
        results.append(sanitized)

        status = "OK" if sanitized.get("execution_success") else "FAIL"
        ragas = sanitized.get("overall_score", 0.0)
        print(
            f"    -> {status}, valid={sanitized.get('valid')}, "
            f"ragas={ragas:.3f}, time={sanitized.get('total_time', 0.0):.2f}s"
        )

        if not sanitized.get("execution_success"):
            exec_error = sanitized.get("execution_error")
            state_exec_error = sanitized.get("state", {}).get("execution_error")
            if not exec_error:
                exec_error = state_exec_error
            if exec_error and "joern" in exec_error.lower():
                raise RuntimeError(
                    f"Joern execution unavailable at question {idx}: {exec_error}"
                )

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the 9-agent LangGraph workflow on 200 questions with Joern execution and RAGAS evaluation."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "data" / "train_split_merged.jsonl",
        help="Path to the dataset containing questions.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Maximum number of questions to run.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sampling questions.",
    )
    parser.add_argument(
        "--force-restart",
        action="store_true",
        help="Force restart the Joern server before running.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose workflow output per question.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "results" / "langgraph_200_questions_execution.json",
        help="Where to store the aggregated results.",
    )

    args = parser.parse_args()

    if not args.dataset.exists():
        raise FileNotFoundError(f"Dataset file not found: {args.dataset}")

    questions = load_questions(args.dataset, limit=args.limit, seed=args.seed)
    print(f"Loaded {len(questions)} questions.")

    start_time = time.time()
    try:
        results = run_questions(
            questions,
            force_restart=args.force_restart,
            verbose=args.verbose,
        )
    except RuntimeError as exc:
        print(f"\n[ERROR] {exc}")
        return 1
    total_elapsed = time.time() - start_time

    summary = summarize_results(results)
    summary["total_elapsed"] = total_elapsed
    summary["timestamp"] = datetime.now().isoformat()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "metadata": {
                    "workflow": "LangGraph 9-agent",
                    "execution_enabled": True,
                    "ragas_enabled": True,
                    "limit": args.limit,
                    "seed": args.seed,
                },
                "summary": summary,
                "results": results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("\nRun complete.")
    print(f"  Successful workflows: {summary['successful_workflows']}/{summary['questions_total']}")
    print(f"  Valid queries:        {summary['valid_queries']}/{summary['questions_total']}")
    print(f"  Execution success:    {summary['execution_successes']}/{summary['questions_total']}")
    print(f"  Avg RAGAS score:      {summary['avg_ragas_score']:.3f}")
    print(f"  Avg time/question:    {summary['avg_time_per_question']:.2f}s")
    print(f"  Total elapsed time:   {summary['total_elapsed'] / 60:.2f} minutes")
    print(f"Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
