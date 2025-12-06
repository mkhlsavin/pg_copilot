"""
Evaluation Node - RAGAS Metrics

Node for evaluating answer quality using RAGAS metrics.
"""

import logging
from typing import List, Dict

from langchain_core.messages import AIMessage

from src.workflow._state import RAGCPGQLState

logger = logging.getLogger(__name__)

# Optional RAGAS imports
try:
    from datasets import Dataset
    from ragas import evaluate as ragas_evaluate
    from ragas.metrics import (
        context_precision as ragas_context_precision,
        context_recall as ragas_context_recall,
        answer_relevancy as ragas_answer_relevancy,
        faithfulness as ragas_faithfulness,
    )
    _RAGAS_AVAILABLE = True
    _RAGAS_METRICS = [
        ragas_context_precision,
        ragas_context_recall,
        ragas_answer_relevancy,
        ragas_faithfulness,
    ]
except Exception:
    _RAGAS_AVAILABLE = False
    _RAGAS_METRICS = []


def _build_context_strings(state: RAGCPGQLState) -> List[str]:
    """Construct textual contexts for RAGAS evaluation."""
    contexts: List[str] = []

    similar_qa = state.get("similar_qa") or []
    for qa in similar_qa:
        question = qa.get("question", "").strip()
        answer = qa.get("answer", "").strip()
        if question or answer:
            segment = "Q: " + question if question else ""
            if answer:
                segment += ("\nA: " if question else "A: ") + answer
            contexts.append(segment.strip())

    cpgql_examples = state.get("cpgql_examples") or []
    for example in cpgql_examples:
        sample_q = example.get("question", "").strip()
        query = example.get("query", "").strip()
        if sample_q or query:
            contexts.append(
                f"Example Question: {sample_q}\nExample Query: {query}".strip()
            )

    enrichment_hints = state.get("enrichment_hints") or {}
    if enrichment_hints:
        formatted_hints: List[str] = []
        for key in [
            "features",
            "subsystems",
            "function_purposes",
            "data_structures",
            "domain_concepts",
            "architectural_roles",
        ]:
            values = enrichment_hints.get(key)
            if values:
                formatted_hints.append(f"{key}: {', '.join(values)}")
        if formatted_hints:
            contexts.append("Enrichment hints: " + " | ".join(formatted_hints))

    if not contexts:
        contexts.append("No retrieved context")

    return contexts


def _compute_ragas_scores(state: RAGCPGQLState) -> Dict[str, float]:
    """Compute RAGAS metrics for the current workflow state."""
    if not _RAGAS_AVAILABLE:
        raise RuntimeError("RAGAS dependencies are not available")

    contexts = _build_context_strings(state)
    answer_text = state.get("answer") or state.get("cpgql_query") or ""
    ground_truth = state.get("cpgql_query") or answer_text or "N/A"

    dataset = Dataset.from_dict(
        {
            "question": [state.get("question", "")],
            "contexts": [contexts],
            "answer": [answer_text],
            "ground_truth": [ground_truth],
        }
    )

    ragas_result = ragas_evaluate(dataset, metrics=_RAGAS_METRICS)
    scores_row = ragas_result.to_pandas().iloc[0].to_dict()

    return {
        "context_precision": float(scores_row.get("context_precision", 0.0)),
        "context_recall": float(scores_row.get("context_recall", 0.0)),
        "answer_relevancy": float(scores_row.get("answer_relevancy", 0.0)),
        "faithfulness": float(scores_row.get("faithfulness", 0.0)),
    }


def evaluate_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Evaluator Agent: Evaluate answer quality using RAGAS metrics."""
    logger.info("=== EVALUATOR AGENT (RAGAS) ===")

    try:
        ragas_scores = _compute_ragas_scores(state)

        state["faithfulness"] = ragas_scores.get("faithfulness", 0.0)
        state["answer_relevance"] = ragas_scores.get("answer_relevancy", 0.0)
        state["context_precision"] = ragas_scores.get("context_precision", 0.0)
        state["context_recall"] = ragas_scores.get("context_recall", 0.0)

        available_scores = [
            value
            for value in [
                state.get("faithfulness"),
                state.get("answer_relevance"),
                state.get("context_precision"),
            ]
            if value is not None
        ]
        state["overall_score"] = (
            sum(available_scores) / len(available_scores)
            if available_scores
            else 0.0
        )

        state["messages"].append(
            AIMessage(
                content=(
                    "RAGAS metrics — "
                    f"Faithfulness: {state['faithfulness']:.2f}, "
                    f"Answer Relevance: {state['answer_relevance']:.2f}, "
                    f"Context Precision: {state['context_precision']:.2f}, "
                    f"Context Recall: {state.get('context_recall', 0.0):.2f}, "
                    f"Overall: {state['overall_score']:.3f}"
                )
            )
        )

        logger.info(
            "RAGAS scores — Faithfulness: %.3f | Answer Relevance: %.3f | "
            "Context Precision: %.3f | Context Recall: %.3f | Overall: %.3f",
            state["faithfulness"],
            state["answer_relevance"],
            state["context_precision"],
            state.get("context_recall", 0.0),
            state["overall_score"],
        )

    except Exception as exc:
        logger.error(f"Evaluator error: {exc}", exc_info=True)

        # Fallback heuristic if RAGAS is unavailable or fails
        if state.get("execution_success", False):
            state["faithfulness"] = 0.9
        else:
            state["faithfulness"] = 0.3

        answer_conf = state.get("answer_confidence", 0.5)
        answer_len = len(state.get("answer", ""))
        state["answer_relevance"] = (
            answer_conf * 0.9 if answer_len > 50 else answer_conf * 0.5
        )

        retrieval_meta = state.get("retrieval_metadata", {}) or {}
        state["context_precision"] = retrieval_meta.get("avg_qa_similarity", 0.5)
        state["context_recall"] = retrieval_meta.get("avg_cpgql_similarity", 0.0)

        state["overall_score"] = (
            state["faithfulness"] + state["answer_relevance"] + state["context_precision"]
        ) / 3.0

        state["messages"].append(
            AIMessage(
                content=(
                    "RAGAS fallback metrics — "
                    f"Faithfulness: {state['faithfulness']:.2f}, "
                    f"Answer Relevance: {state['answer_relevance']:.2f}, "
                    f"Context Precision: {state['context_precision']:.2f}, "
                    f"Context Recall: {state.get('context_recall', 0.0):.2f}, "
                    f"Overall: {state['overall_score']:.3f}"
                )
            )
        )

    return state
