"""LangGraph-based RAG-CPGQL Workflow

This module implements the full 9-agent workflow using LangGraph for
orchestration and state management. It provides:

1. Analyzer Agent - Question analysis and domain classification
2. Retriever Agent - Context retrieval from vector store
3. Enrichment Agent - CPG metadata enrichment
4. Generator Agent - CPGQL query generation
5. Validator Agent - Query syntax and safety validation
6. Refiner Agent - Query refinement on validation failure
7. Executor Agent - Query execution on Joern CPG
8. Interpreter Agent - Natural language answer generation
9. Evaluator Agent - RAGAS evaluation metrics

Architecture Benefits:
- Stateful workflow with automatic retry logic
- Observable and debuggable execution
- Modular and testable components
- Self-improving through RAGAS feedback

The workflow core components are organized in the core/ package:
- core/helpers.py - RAGAS and query processing utilities
- core/routing.py - Conditional routing functions

For new code, import directly from src.workflow.core.
"""

import sys
import json
import logging
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
import time

# LangGraph imports
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

# Phase 2: Result Ranking
from src.ranking.result_ranker import ResultRanker

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
    _RAGAS_METRIC_NAMES = {
        "context_precision": "context_precision",
        "context_recall": "context_recall",
        "answer_relevancy": "answer_relevancy",
        "faithfulness": "faithfulness",
    }
except Exception as ragas_import_error:  # pragma: no cover
    _RAGAS_AVAILABLE = False
    _RAGAS_METRICS = []
    _RAGAS_METRIC_NAMES = {}


# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Local imports - State and Components from split modules
from src.workflow._state import RAGCPGQLState
from src.workflow._components import (
    get_analyzer,
    get_vector_store,
    get_retriever,
    get_enrichment_agent,
    get_llm_interface,
    get_generator_agent,
    get_interpreter_agent,
    get_joern_client,
    get_adaptive_refiner,
    get_control_flow_generator,
    get_call_chain_analyzer,
    get_logic_synthesizer,
)

# Agent imports still needed for type hints
from src.agents.executor_agent_with_fallback import ExecutorAgentWithFallback
from src.agents.adaptive_refiner import classify_question_type

# Phase 7: Control Flow Analysis imports
from src.execution.scala_parser import parse_scala_output

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# RAGAS HELPER FUNCTIONS
# ============================================================================

def _build_context_strings(state: "RAGCPGQLState") -> List[str]:
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


def _compute_ragas_scores(state: "RAGCPGQLState") -> Dict[str, float]:
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

# ============================================================================
# AGENT NODE FUNCTIONS
# ============================================================================

def analyze_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Analyzer Agent: Extract intent, domain, and keywords from question."""
    logger.info("=== ANALYZER AGENT ===")

    try:
        question = state["question"]

        # Analyze question (shared analyzer ensures consistent heuristics)
        analysis = get_analyzer().analyze(question)

        # Update state
        state["intent"] = analysis.get("intent", "unknown")
        state["domain"] = analysis.get("domain", "general")
        state["keywords"] = analysis.get("keywords", [])
        state["complexity"] = analysis.get("complexity", "medium")

        # Phase 7: Capture query mode
        state["query_mode"] = analysis.get("query_mode", "find-method")
        state["query_mode_confidence"] = analysis.get("query_mode_confidence", 0.5)

        # Add message
        state["messages"].append(AIMessage(
            content=f"Analysis: domain={state['domain']}, intent={state['intent']}, "
                   f"complexity={state['complexity']}, query_mode={state['query_mode']} "
                   f"(conf: {state['query_mode_confidence']:.2f})"
        ))

        logger.info(f"Domain: {state['domain']}, Intent: {state['intent']}, "
                   f"QueryMode: {state['query_mode']} ({state['query_mode_confidence']:.2f})")

    except Exception as e:
        logger.error(f"Analyzer error: {e}", exc_info=True)
        state["error"] = f"Analyzer failed: {str(e)}"

    return state


def retrieve_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Retriever Agent: Retrieve relevant context from vector store."""
    logger.info("=== RETRIEVER AGENT ===")

    try:
        question = state["question"]

        # Get analysis context
        analysis = {
            "domain": state.get("domain"),
            "keywords": state.get("keywords", []),
            "intent": state.get("intent")
        }

        # Retrieve context using shared retriever
        retrieval_result = get_retriever().retrieve(
            question=question,
            analysis=analysis,
            top_k_qa=3,
            top_k_cpgql=5
        )

        # Update state
        state["similar_qa"] = retrieval_result.get("similar_qa", [])
        state["cpgql_examples"] = retrieval_result.get("cpgql_examples", [])
        state["retrieval_metadata"] = retrieval_result.get("retrieval_stats", {})

        # Add message
        qa_count = len(state["similar_qa"])
        cpgql_count = len(state["cpgql_examples"])
        avg_sim = state["retrieval_metadata"].get("avg_qa_similarity")
        sim_text = f"{avg_sim:.3f}" if isinstance(avg_sim, (int, float)) else "n/a"

        state["messages"].append(AIMessage(
            content=f"Retrieved: {qa_count} Q&A pairs, {cpgql_count} CPGQL examples "
                   f"(avg similarity: {sim_text})"
        ))

        logger.info(f"Retrieved {qa_count} Q&A, {cpgql_count} CPGQL examples")

    except Exception as e:
        logger.error(f"Retriever error: {e}", exc_info=True)
        state["error"] = f"Retriever failed: {str(e)}"

    return state


def enrich_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Enrichment Agent: Get relevant enrichment hints from CPG metadata."""
    logger.info("=== ENRICHMENT AGENT ===")

    try:
        question = state["question"]

        # Get analysis context
        analysis = {
            "domain": state.get("domain"),
            "keywords": state.get("keywords", [])
        }

        # Get enrichment hints
        hints = get_enrichment_agent().get_enrichment_hints(
            question=question,
            analysis=analysis
        )

        # Calculate coverage from agent output
        coverage = hints.get("coverage_score", 0.0)
        tag_count = len(hints.get("tags", []))

        # Update state
        state["enrichment_hints"] = hints
        state["enrichment_coverage"] = coverage

        # Add message
        state["messages"].append(AIMessage(
            content=f"Enrichment: {tag_count} tag hints ({coverage:.0%} coverage)"
        ))

        logger.info(f"Enrichment: {tag_count} tag hints, {coverage:.0%} coverage")

    except Exception as e:
        logger.error(f"Enrichment error: {e}", exc_info=True)
        state["error"] = f"Enrichment failed: {str(e)}"

    return state


def _count_scala_results(result_str: str) -> int:
    """Count results in Scala output using proper parsing.

    Supports multiple Scala output formats:
    - List("item1", "item2", ...) - Count quoted strings
    - Newline-separated items - Count non-empty lines
    - Empty or error messages - Return 0

    Args:
        result_str: Raw Scala output string

    Returns:
        Number of results found
    """
    import re

    if not result_str or result_str == "No results found for the specified criteria":
        return 0

    # Pattern 1: Scala List with quoted strings
    # Example: val res1: List[String] = List("item1", "item2", ...)
    if "List(" in result_str:
        # Extract all quoted strings within List(...)
        # Match the List(...) portion
        list_match = re.search(r'List\s*\((.*)\)', result_str, re.DOTALL)
        if list_match:
            list_content = list_match.group(1)
            # Count quoted strings (handles escaped quotes)
            quoted_items = re.findall(r'"(?:[^"\\]|\\.)*"', list_content)
            count = len(quoted_items)
            if count > 0:
                return count

    # Pattern 2: Newline-separated output (fallback)
    # Count non-empty lines that look like method names or values
    lines = [line.strip() for line in result_str.split('\n') if line.strip()]
    # Filter out Scala REPL output lines (val res, type definitions, etc.)
    data_lines = [
        line for line in lines
        if not line.startswith('val res')
        and not line.startswith('[')  # ANSI color codes
        and not line.startswith('defined')
        and not line.endswith('=')
    ]

    if data_lines:
        return len(data_lines)

    # Pattern 3: If we have substantial content but couldn't parse it, estimate
    # This prevents false negatives when format is unexpected
    if len(result_str) > 100:
        # Rough estimate: 50 chars per result on average
        estimated_count = max(1, len(result_str) // 50)
        logger.warning(f"Could not parse Scala output format, estimating {estimated_count} results from {len(result_str)} chars")
        return estimated_count

    return 0


def post_process_query(query: str) -> tuple[str, bool]:
    """Post-process generated query to fix common issues that cause empty results.

    This function:
    1. Replaces exact matching with pattern matching for flexibility
    2. Validates and fixes invalid tag values (catches LLM hallucinations)
    3. Detects and fixes impossible AND combinations (same tag name, different values)

    Args:
        query: The generated CPGQL query

    Returns:
        Tuple of (processed_query, was_modified)
    """
    if not query:
        return query, False

    original_query = query
    modifications = []

    # 1. Replace exact matching with pattern matching
    query = query.replace(".nameExact(", ".name(")
    query = query.replace(".valueExact(", ".value(")

    if query != original_query:
        modifications.append("exact→pattern matching")

    # 2. Validate and fix invalid tag values (catches LLM hallucinations)
    try:
        from src.validation.query_validator import get_query_validator
        query_validator = get_query_validator()
        validation_result = query_validator.validate_query(query)

        if validation_result["corrections"]:
            query = validation_result["corrected_query"]
            for correction in validation_result["corrections"]:
                modifications.append(f"tag: {correction}")
                logger.info(f"Post-processing tag fix: {correction}")

        if validation_result["warnings"]:
            for warning in validation_result["warnings"]:
                logger.warning(f"Post-processing tag warning: {warning}")
    except Exception as e:
        logger.warning(f"Tag validation failed: {e}", exc_info=True)

    # 3. Detect and fix impossible AND combinations
    # Pattern: .where(_.tag.name("X").value("Y"))...where(_.tag.name("X").value("Z"))
    # This is impossible - a method can't have tag X with both values Y and Z
    import re

    # Find all .where clauses with tag filters
    tag_where_pattern = r'\.where\(_\.tag\.name\(["\']([^"\']+)["\']\)\.value\(["\']([^"\']+)["\']\)\)'
    matches = list(re.finditer(tag_where_pattern, query))

    if len(matches) > 1:
        # Track which tag names we've seen
        seen_tags = {}
        indices_to_remove = []

        for i, match in enumerate(matches):
            tag_name = match.group(1)
            tag_value = match.group(2)

            if tag_name in seen_tags:
                # Duplicate tag name found! This creates an impossible AND condition
                first_value = seen_tags[tag_name]['value']
                logger.warning(
                    f"Detected impossible AND combination: "
                    f"tag '{tag_name}' with values '{first_value}' AND '{tag_value}'. "
                    f"Keeping first value '{first_value}', removing second."
                )
                indices_to_remove.append(i)
                modifications.append(f"removed duplicate tag '{tag_name}'")
            else:
                seen_tags[tag_name] = {'value': tag_value, 'index': i}

        # Remove duplicate tag filters (in reverse order to preserve indices)
        if indices_to_remove:
            # Build new query by removing duplicate .where() clauses
            parts = []
            last_end = 0

            for i, match in enumerate(matches):
                if i not in indices_to_remove:
                    # Keep this match - add everything up to it
                    parts.append(query[last_end:match.end()])
                    last_end = match.end()
                else:
                    # Remove this match - skip to after it
                    parts.append(query[last_end:match.start()])
                    last_end = match.end()

            # Add remainder
            parts.append(query[last_end:])
            query = ''.join(parts)

    was_modified = (query != original_query)

    if was_modified:
        logger.info(f"Post-processing: Applied {', '.join(modifications)}")
        logger.debug(f"Original: {original_query[:150]}...")
        logger.debug(f"Modified: {query[:150]}...")

    return query, was_modified


def generate_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Generator Agent: Generate CPGQL query with full context."""
    logger.info("=== GENERATOR AGENT ===")

    try:
        start_time = time.time()

        question = state["question"]
        use_multi_query = state.get("use_multi_query", False)

        # Get context
        analysis = {
            "domain": state.get("domain"),
            "keywords": state.get("keywords", []),
            "intent": state.get("intent"),
            "complexity": state.get("complexity")
        }

        context = {
            "analysis": analysis,
            "similar_qa": state.get("similar_qa", []),
            "cpgql_examples": state.get("cpgql_examples", []),
            "enrichment_hints": state.get("enrichment_hints", {}),
            "retrieval_metadata": state.get("retrieval_metadata", {})
        }

        generator = get_generator_agent()

        if use_multi_query:
            # Multi-query approach: generate 3 variants
            logger.info("Using multi-query approach (Query Funnel)")
            variants = generator.generate_query_variants(
                question=question,
                context=context,
                num_variants=3
            )

            state["query_variants"] = variants

            # Set the first (PRECISE) variant as the primary query for validation
            if variants:
                raw_query = variants[0].get("query", "")
                # Apply post-processing to convert exact matching to pattern matching
                processed_query, was_modified = post_process_query(raw_query)
                state["cpgql_query"] = processed_query
                state["query_valid"] = True  # Will be validated later
                state["validation_error"] = None
            else:
                state["cpgql_query"] = ""
                state["query_valid"] = False
                state["validation_error"] = "No query variants generated"

            generation_time = time.time() - start_time
            state["generation_time"] = generation_time

            # Add message
            variant_count = len(variants)
            state["messages"].append(AIMessage(
                content=f"Generated {variant_count} query variants ({generation_time:.2f}s) - Query Funnel approach"
            ))

            logger.info(f"Generated {variant_count} query variants in {generation_time:.2f}s")

        else:
            # Original single-query approach
            query, is_valid, error = generator.generate(
                question=question,
                context=context
            )

            # Apply post-processing to convert exact matching to pattern matching
            processed_query, was_modified = post_process_query(query)

            generation_time = time.time() - start_time

            # Update state
            state["cpgql_query"] = processed_query
            state["generation_time"] = generation_time
            state["query_valid"] = is_valid
            state["validation_error"] = error if error else None

            # Add message
            preview = (query or "")[:100]
            state["messages"].append(AIMessage(
                content=f"Generated query ({generation_time:.2f}s | valid={'yes' if is_valid else 'no'}): {preview}"
            ))

            logger.info(f"Generated query (valid={is_valid}) in {generation_time:.2f}s")

    except Exception as e:
        logger.error(f"Generator error: {e}", exc_info=True)
        state["error"] = f"Generator failed: {str(e)}"
        state["query_valid"] = False
        state["validation_error"] = str(e)

    return state


def validate_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Validator Agent: Validate query syntax and safety."""
    logger.info("=== VALIDATOR AGENT ===")

    try:
        query = state.get("cpgql_query", "")

        if not query:
            state["query_valid"] = False
            state["validation_error"] = "Empty query"
            return state

        # Basic validation checks
        errors = []

        # 1. Check for required CPGQL components
        if "cpg." not in query.lower():
            errors.append("Query must start with 'cpg.'")

        # 2. Check for .l terminator (list results)
        if not (query.endswith(".l") or query.endswith(".toList") or
                query.endswith(".size") or query.endswith(".head")):
            errors.append("Query should end with .l, .toList, .size, or .head")

        # 3. Check for dangerous operations
        dangerous_ops = ["delete", "drop", "remove", "clear"]
        query_lower = query.lower()
        for op in dangerous_ops:
            if op in query_lower:
                errors.append(f"Dangerous operation detected: {op}")

        # 4. Check balanced parentheses
        if query.count("(") != query.count(")"):
            errors.append("Unbalanced parentheses")

        # 5. Check balanced quotes
        if query.count('"') % 2 != 0:
            errors.append("Unbalanced quotes")

        # Set validation result
        if errors:
            state["query_valid"] = False
            state["validation_error"] = "; ".join(errors)
            logger.warning(f"Validation failed: {state['validation_error']}")
        else:
            state["query_valid"] = True
            state["validation_error"] = None
            logger.info("Query validation passed")

        # Add message
        status = "VALID" if state["query_valid"] else "INVALID"
        state["messages"].append(AIMessage(
            content=f"Validation: {status}" +
                   (f" - {state['validation_error']}" if not state["query_valid"] else "")
        ))

    except Exception as e:
        logger.error(f"Validator error: {e}", exc_info=True)
        state["query_valid"] = False
        state["validation_error"] = f"Validation error: {str(e)}"

    return state


def refine_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Refiner Agent: Refine query based on validation error."""
    logger.info("=== REFINER AGENT ===")

    try:
        retry_count = state.get("retry_count", 0)

        # Check retry limit
        if retry_count >= 2:
            logger.warning("Max retries reached, using fallback query")
            state["cpgql_query"] = "cpg.method.name.l.take(10)"
            state["query_valid"] = True
            state["validation_error"] = None
            state["messages"].append(AIMessage(
                content="Max retries reached, using fallback query"
            ))
            return state

        # Get previous query and error
        previous_query = state.get("cpgql_query") or ""
        error = state.get("validation_error", "") or ""

        logger.info(f"Refining query (attempt {retry_count + 1}/2)")
        logger.info(f"Error: {error}")

        # Simple refinement logic
        refined_query = previous_query.strip()

        if not refined_query:
            # If we have nothing to refine, fall back to a safe default
            refined_query = "cpg.method.name.l"

        # Fix common issues
        if "Query must start with 'cpg.'" in error:
            if not refined_query.startswith("cpg."):
                refined_query = "cpg." + refined_query

        if "Query should end with" in error:
            if not any(refined_query.endswith(t) for t in [".l", ".toList", ".size", ".head"]):
                refined_query = refined_query.rstrip(".") + ".l"

        if "Unbalanced parentheses" in error:
            open_count = refined_query.count("(")
            close_count = refined_query.count(")")
            if open_count > close_count:
                refined_query += ")" * (open_count - close_count)

        # Update state
        state["cpgql_query"] = refined_query
        state["retry_count"] = retry_count + 1

        # Add message
        preview = refined_query[:100] if refined_query else "[empty]"
        state["messages"].append(AIMessage(
            content=f"Refined query (attempt {retry_count + 1}): {preview}"
        ))

        logger.info(f"Refined query: {refined_query}")

    except Exception as e:
        logger.error(f"Refiner error: {e}", exc_info=True)
        state["error"] = f"Refiner failed: {str(e)}"

    return state


def execute_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Executor Agent: Execute query on Joern CPG server."""
    logger.info("=== EXECUTOR AGENT ===")

    try:
        use_multi_query = state.get("use_multi_query", False)
        query_variants = state.get("query_variants", [])

        # Get persistent Joern client (reuses connection across queries)
        joern_client = get_joern_client()

        if not joern_client:
            logger.warning("Joern client not available, skipping execution")
            state["execution_success"] = False
            state["execution_error"] = "Joern server not available"
            state["messages"].append(AIMessage(
                content="Execution skipped: Joern server not available"
            ))
            return state

        if use_multi_query and query_variants:
            # Use ExecutorAgentWithFallback for multi-query approach
            logger.info("Using ExecutorAgentWithFallback for multi-query execution")

            executor = ExecutorAgentWithFallback(
                joern_client=joern_client,
                min_results_threshold=5
            )

            exec_result = executor.execute_with_fallback(
                query_variants=query_variants,
                question=state["question"]
            )

            # Update state with fallback execution results
            state["cpgql_query"] = exec_result.get("query_used", "")
            state["execution_result"] = {"result": exec_result.get("raw_result", ""), "success": exec_result.get("success", False)}
            state["execution_success"] = exec_result.get("success", False)
            state["execution_time"] = state.get("generation_time", 0.0)  # Approximate
            state["execution_error"] = None if exec_result.get("success") else "All query variants failed"
            state["fallback_count"] = exec_result.get("fallback_count", 0)
            state["specificity_used"] = exec_result.get("specificity", "unknown")

            # Add message with fallback info
            num_results = len(exec_result.get("results", []))
            specificity = exec_result.get("specificity", "unknown")
            fallback_count = exec_result.get("fallback_count", 0)

            state["messages"].append(AIMessage(
                content=f"Execution: {specificity.upper()} query succeeded (fallbacks: {fallback_count}, results: {num_results})"
            ))

            logger.info(f"Multi-query execution: {specificity.upper()} succeeded with {num_results} results after {fallback_count} fallbacks")

            # Phase 2: Rank results by relevance (if we have results)
            results = exec_result.get("results", [])
            if results and num_results > 0:
                logger.info(f"Ranking {num_results} results by relevance")

                ranker = ResultRanker()

                # Build context for ranking
                ranking_context = {
                    'enrichment_hints': state.get('enrichment_hints', {}),
                    'analysis': {
                        'domain': state.get('domain', 'unknown'),
                        'intent': state.get('intent', ''),
                        'keywords': state.get('keywords', [])
                    }
                }

                # Rank results
                ranked = ranker.rank_results(
                    results=results,
                    question=state["question"],
                    context=ranking_context,
                    top_k=10
                )

                # Store ranked results in state
                state["ranked_results"] = ranked
                state["ranking_metadata"] = {
                    "top_score": ranked[0]["score"] if ranked else 0.0,
                    "num_ranked": len(ranked),
                    "avg_score": sum(r["score"] for r in ranked) / len(ranked) if ranked else 0.0
                }

                logger.info(f"Ranked {len(ranked)} results - Top score: {ranked[0]['score']:.3f}, Avg: {state['ranking_metadata']['avg_score']:.3f}")
            else:
                logger.info("No results to rank")
                state["ranked_results"] = []
                state["ranking_metadata"] = {"top_score": 0.0, "num_ranked": 0, "avg_score": 0.0}

        else:
            # Original single-query execution
            query = state.get("cpgql_query", "")

            if not query or not state.get("query_valid", False):
                logger.warning("Skipping execution: invalid query")
                state["execution_success"] = False
                state["execution_error"] = "Query not valid, skipping execution"
                return state

            def _attempt_execution(current_query: str) -> Dict[str, Any]:
                start = time.time()
                result_payload = joern_client.execute_query(current_query)
                elapsed = time.time() - start
                return result_payload, elapsed

            exec_result, execution_time = _attempt_execution(query)

            if exec_result.get("success") and is_empty_result(exec_result.get("result")):
                # FALLBACK MECHANISM DISABLED FOR ACCURACY
                # Root cause analysis revealed fallbacks generate garbage data:
                # - Syntax errors from bare .valueExact() without .tag.nameExact()
                # - Empty .where(_) returns ALL 52,303 methods
                # - Overly broad queries return 10,000+ irrelevant methods
                # Better to return honest "No results found" than pollute answers with garbage
                logger.warning(
                    "Primary query returned no rows. Fallback mechanism disabled to prevent "
                    "garbage results. Query was: %s", query
                )
                exec_result = {
                    "success": True,
                    "result": "No results found for the specified criteria",
                    "error": None
                }

            # Update state
            state["cpgql_query"] = query
            state["execution_result"] = exec_result
            state["execution_success"] = exec_result.get("success", False)
            state["execution_time"] = execution_time
            state["execution_error"] = exec_result.get("error") if not exec_result.get("success") else None

            # Add message
            if state["execution_success"]:
                result_length = len(str(exec_result.get("result", "")))
                state["messages"].append(AIMessage(
                    content=f"Execution successful ({execution_time:.2f}s): {result_length} chars"
                ))
                logger.info(f"Execution successful: {result_length} chars in {execution_time:.2f}s")
            else:
                state["messages"].append(AIMessage(
                    content=f"Execution failed: {state['execution_error']}"
                ))
                logger.warning(f"Execution failed: {state['execution_error']}")

        # NOTE: Don't close joern_client - we're using a persistent connection!

    except Exception as e:
        logger.error(f"Executor error: {e}", exc_info=True)
        state["execution_success"] = False
        state["execution_error"] = str(e)
        state["messages"].append(AIMessage(
            content=f"Execution error: {str(e)}"
        ))

    return state


def interpret_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Interpreter Agent: Convert query results to natural language answer."""
    logger.info("=== INTERPRETER AGENT ===")

    try:
        # Get interpreter agent
        interpreter = get_interpreter_agent()

        # Extract relevant state
        question = state["question"]
        query = state.get("cpgql_query", "")
        execution_success = state.get("execution_success", False)
        execution_result = state.get("execution_result", {})
        execution_error = state.get("execution_error")
        enrichment_hints = state.get("enrichment_hints", {})

        # Check if fallback was used (query changed during execution)
        # We detect this by checking if execution_result has a different query
        used_fallback = False
        fallback_query = None
        # Look for fallback message in state messages
        for msg in state.get("messages", []):
            if hasattr(msg, "content") and "Fallback query executed:" in str(msg.content):
                used_fallback = True
                # Extract the fallback query from the message
                import re
                match = re.search(r"Fallback query executed: (.+)", str(msg.content))
                if match:
                    fallback_query = match.group(1).strip()
                break

        # Call the interpreter agent
        interpretation = interpreter.interpret(
            question=question,
            query=query,
            execution_success=execution_success,
            execution_result=execution_result,
            execution_error=execution_error,
            enrichment_hints=enrichment_hints,
            used_fallback=used_fallback,
            fallback_query=fallback_query
        )

        # Update state with interpretation results
        state["answer"] = interpretation["answer"]
        state["answer_confidence"] = interpretation["confidence"]

        # Add message
        summary_type = interpretation.get("summary_type", "unknown")
        state["messages"].append(AIMessage(
            content=f"Answer generated ({summary_type} synthesis, confidence: {state['answer_confidence']:.1%})"
        ))

        logger.info(
            f"Answer generated: {len(state['answer'])} chars, "
            f"confidence={state['answer_confidence']:.2f}, "
            f"type={summary_type}"
        )

    except Exception as e:
        logger.error(f"Interpreter error: {e}", exc_info=True)
        state["answer"] = f"I encountered an error while interpreting the results: {str(e)}"
        state["answer_confidence"] = 0.0
        state["messages"].append(AIMessage(
            content=f"Interpretation error: {str(e)}"
        ))

    return state


def adaptive_refine_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Adaptive Refinement Agent: Learn from results and apply refinements if needed."""
    logger.info("=== ADAPTIVE REFINEMENT AGENT ===")

    try:
        refiner = get_adaptive_refiner()

        # Classify question type
        analysis = {
            "intent": state.get("intent"),
            "domain": state.get("domain"),
            "keywords": state.get("keywords", [])
        }
        question_type = classify_question_type(state["question"], analysis)
        state["question_type"] = question_type

        # Count results using proper Scala List parsing
        execution_result = state.get("execution_result", {})
        result_count = 0

        if execution_result and execution_result.get("success"):
            result_str = str(execution_result.get("result", ""))
            result_count = _count_scala_results(result_str)
            logger.debug(f"Counted {result_count} results from {len(result_str)} chars of output")

        state["result_count"] = result_count

        # Record outcome for learning
        query = state.get("cpgql_query", "")
        success = result_count >= 5  # Consider success if >= 5 results

        refiner.record_query_outcome(
            question=state["question"],
            question_type=question_type,
            query=query,
            success=success,
            result_count=result_count,
            execution_time=state.get("execution_time", 0.0)
        )

        logger.info(f"Recorded query outcome: {result_count} results, success={success}, type={question_type}")

        # Apply refinements if results are insufficient
        if result_count < 5 and query:
            logger.info(f"Insufficient results ({result_count} < 5), generating refinement suggestions")

            suggestions = refiner.suggest_refinements(
                question=state["question"],
                question_type=question_type,
                failed_query=query,
                max_suggestions=3
            )

            state["refinement_suggestions"] = suggestions

            if suggestions:
                logger.info(f"Generated {len(suggestions)} refinement suggestions")

                # Try the best suggestion
                best_suggestion = suggestions[0]
                refined_query = best_suggestion["query"]
                strategy = best_suggestion["strategy"]

                logger.info(f"Applying refinement: {strategy}")
                logger.info(f"Refined query: {refined_query[:100]}...")

                # Try executing refined query
                joern_client = get_joern_client()
                if joern_client:
                    try:
                        start = time.time()
                        refined_result = joern_client.execute_query(refined_query)
                        elapsed = time.time() - start

                        if refined_result.get("success"):
                            refined_result_str = str(refined_result.get("result", ""))
                            refined_count = _count_scala_results(refined_result_str)
                            logger.debug(f"Refinement counted {refined_count} results from {len(refined_result_str)} chars")

                            if refined_count > result_count:
                                logger.info(f"Refinement successful: {refined_count} results (improvement: +{refined_count - result_count})")

                                # Update state with refined results
                                state["cpgql_query"] = refined_query
                                state["execution_result"] = refined_result
                                state["execution_success"] = True
                                state["execution_time"] = elapsed
                                state["result_count"] = refined_count
                                state["refinement_applied"] = True
                                state["refinement_strategy"] = strategy

                                # Re-interpret with refined results
                                interpreter = get_interpreter_agent()
                                interpretation = interpreter.interpret(
                                    question=state["question"],
                                    query=refined_query,
                                    execution_success=True,
                                    execution_result=refined_result,
                                    execution_error=None,
                                    enrichment_hints=state.get("enrichment_hints", {}),
                                    used_fallback=False,
                                    fallback_query=None
                                )

                                state["answer"] = interpretation["answer"]
                                state["answer_confidence"] = interpretation["confidence"]

                                state["messages"].append(AIMessage(
                                    content=f"Refinement applied: {strategy} -> {refined_count} results (+{refined_count - result_count} improvement)"
                                ))
                            else:
                                logger.info(f"Refinement did not improve results: {refined_count} <= {result_count}")
                                state["refinement_applied"] = False
                        else:
                            logger.warning(f"Refined query failed: {refined_result.get('error')}")
                            state["refinement_applied"] = False
                    except Exception as e:
                        logger.error(f"Refinement execution error: {e}")
                        state["refinement_applied"] = False
                else:
                    logger.warning("Joern client not available for refinement")
                    state["refinement_applied"] = False
            else:
                logger.info("No refinement suggestions generated")
                state["refinement_applied"] = False
        else:
            logger.info(f"Results adequate ({result_count} >= 5), no refinement needed")
            state["refinement_applied"] = False

        # Save patterns periodically
        refiner.save_patterns()

    except Exception as e:
        logger.error(f"Adaptive refinement error: {e}", exc_info=True)
        state["refinement_applied"] = False

    return state


# ============================================================================
# PHASE 7: CONTROL FLOW NODE FUNCTIONS
# ============================================================================

def route_by_mode(state: RAGCPGQLState) -> str:
    """Route to semantic or control flow mode based on query_mode.

    Returns:
        "control_flow_generate" for explain-logic mode
        "retrieve" for find-method mode (semantic)
    """
    query_mode = state.get("query_mode", "find-method")
    logger.info(f"Routing: query_mode={query_mode}")

    if query_mode == "explain-logic":
        return "control_flow_generate"
    else:
        return "retrieve"  # Continue to semantic mode


def control_flow_generate_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Phase 7: Generate control flow CPGQL queries."""
    logger.info("=== CONTROL FLOW GENERATOR ===")

    try:
        question = state["question"]
        context = {
            'keywords': state.get('keywords', []),
            'domain': state.get('domain', 'general')
        }

        generator = get_control_flow_generator()
        result = generator.generate(question, context)

        state["control_flow_queries"] = result
        state["control_flow_metadata"] = result.get('metadata', {})

        state["messages"].append(AIMessage(
            content=f"Generated 3 control flow queries: entry_point, keyword_methods, call_graph"
        ))

        logger.info(f"Control flow queries generated")

    except Exception as e:
        logger.error(f"Control flow generation error: {e}", exc_info=True)
        state["error"] = f"Control flow generation failed: {str(e)}"

    return state


def control_flow_execute_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Phase 7: Execute control flow CPGQL queries on Joern."""
    logger.info("=== CONTROL FLOW EXECUTOR ===")

    try:
        queries = state.get("control_flow_queries", {})
        if not queries:
            logger.warning("No control flow queries to execute")
            state["error"] = "No control flow queries generated"
            return state

        joern = get_joern_client()

        # Execute entry point query
        logger.info("Executing entry point query...")
        entry_response = joern.execute_query(queries.get('entry_point_query', ''))
        entry_raw = entry_response.get('result') if entry_response.get('success') else None
        entry_result = parse_scala_output(entry_raw) if isinstance(entry_raw, str) else entry_raw
        logger.info(f"Entry point result type: {type(entry_result)}, parsed: {entry_result is not None}")

        # Execute keyword methods query
        logger.info("Executing keyword methods query...")
        keyword_response = joern.execute_query(queries.get('keyword_methods_query', ''))
        keyword_raw = keyword_response.get('result', []) if keyword_response.get('success') else []
        keyword_result = parse_scala_output(keyword_raw) if isinstance(keyword_raw, str) else keyword_raw
        # Ensure it's a list
        if keyword_result and not isinstance(keyword_result, list):
            keyword_result = [keyword_result]
        elif not keyword_result:
            keyword_result = []
        logger.info(f"Keyword methods result type: {type(keyword_result)}, count: {len(keyword_result)}")

        # Execute call graph query
        logger.info("Executing call graph query...")
        graph_response = joern.execute_query(queries.get('call_graph_query', ''))
        graph_raw = graph_response.get('result', []) if graph_response.get('success') else []
        graph_result = parse_scala_output(graph_raw) if isinstance(graph_raw, str) else graph_raw
        # Ensure it's a list
        if graph_result and not isinstance(graph_result, list):
            graph_result = [graph_result]
        elif not graph_result:
            graph_result = []
        logger.info(f"Call graph result type: {type(graph_result)}, count: {len(graph_result)}")

        state["entry_point_result"] = entry_result
        state["keyword_methods_result"] = keyword_result if isinstance(keyword_result, list) else []
        state["call_graph_result"] = graph_result if isinstance(graph_result, list) else []

        state["messages"].append(AIMessage(
            content=f"Executed 3 CPGQL queries on Joern CPG"
        ))

        logger.info(f"Control flow queries executed")

    except Exception as e:
        logger.error(f"Control flow execution error: {e}", exc_info=True)
        state["error"] = f"Control flow execution failed: {str(e)}"

    return state


def control_flow_analyze_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Phase 7: Analyze call chain from CPGQL results."""
    logger.info("=== CALL CHAIN ANALYZER ===")

    try:
        analyzer = get_call_chain_analyzer()

        analysis = analyzer.analyze(
            entry_point_result=state.get("entry_point_result"),
            keyword_methods_result=state.get("keyword_methods_result", []),
            call_graph_result=state.get("call_graph_result", []),
            question_keywords=state.get("keywords", [])
        )

        state["call_chain_analysis"] = analysis

        entry_point = analysis.get('entry_point', 'Unknown')
        key_function_count = analysis.get('metadata', {}).get('key_function_count', 0)
        chain_count = analysis.get('metadata', {}).get('chain_count', 0)

        state["messages"].append(AIMessage(
            content=f"Call chain analysis complete: entry={entry_point}, "
                   f"key_functions={key_function_count}, chains={chain_count}"
        ))

        logger.info(f"Call chain analyzed: {key_function_count} key functions, {chain_count} chains")

    except Exception as e:
        logger.error(f"Call chain analysis error: {e}", exc_info=True)
        state["error"] = f"Call chain analysis failed: {str(e)}"

    return state


def control_flow_synthesize_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Phase 7: Synthesize logic explanation from call chain analysis."""
    logger.info("=== LOGIC SYNTHESIZER ===")

    try:
        synthesizer = get_logic_synthesizer()

        result = synthesizer.synthesize(
            question=state["question"],
            call_chain_analysis=state.get("call_chain_analysis", {})
        )

        state["logic_explanation"] = result['explanation']
        state["answer"] = result['explanation']  # Set as final answer

        explanation_length = len(result['explanation'])
        generation_method = result.get('metadata', {}).get('generation_method', 'unknown')

        state["messages"].append(AIMessage(
            content=f"Logic explanation synthesized: {explanation_length} chars ({generation_method} mode)"
        ))

        logger.info(f"Logic explanation generated: {explanation_length} chars")

    except Exception as e:
        logger.error(f"Logic synthesis error: {e}", exc_info=True)
        state["error"] = f"Logic synthesis failed: {str(e)}"

    return state


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


# ============================================================================
# CONDITIONAL ROUTING
# ============================================================================

def should_refine(state: RAGCPGQLState) -> str:
    """Determine if query needs refinement or can proceed to execution."""
    if state.get("query_valid", False):
        return "execute"
    else:
        retry_count = state.get("retry_count", 0)
        if retry_count >= 2:
            return "execute"  # Give up, try to execute anyway
        return "refine"


# ============================================================================
# WORKFLOW CONSTRUCTION
# ============================================================================

def build_workflow(enable_ragas: bool = False) -> StateGraph:
    """Build the complete LangGraph RAG-CPGQL workflow.

    Args:
        enable_ragas: Whether to enable RAGAS evaluation (default: False).
                     RAGAS evaluation adds 50-70s overhead per query and is recommended
                     only for single-question debugging, not batch processing.

    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info(f"Building LangGraph workflow (RAGAS: {'enabled' if enable_ragas else 'disabled'})...")

    # Create graph
    workflow = StateGraph(RAGCPGQLState)

    # Add nodes
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("enrich", enrich_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("refine", refine_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("interpret", interpret_node)
    workflow.add_node("adaptive_refine", adaptive_refine_node)  # Adaptive refinement

    # Phase 7: Control Flow nodes
    workflow.add_node("control_flow_generate", control_flow_generate_node)
    workflow.add_node("control_flow_execute", control_flow_execute_node)
    workflow.add_node("control_flow_analyze", control_flow_analyze_node)
    workflow.add_node("control_flow_synthesize", control_flow_synthesize_node)

    # Conditionally add RAGAS evaluation node
    if enable_ragas:
        workflow.add_node("evaluate", evaluate_node)

    # Define entry point
    workflow.set_entry_point("analyze")

    # Phase 7: Conditional routing after analyze
    workflow.add_conditional_edges(
        "analyze",
        route_by_mode,
        {
            "retrieve": "retrieve",  # Semantic mode (existing path)
            "control_flow_generate": "control_flow_generate"  # Control flow mode (Phase 7)
        }
    )

    # Semantic mode path (existing)
    workflow.add_edge("retrieve", "enrich")
    workflow.add_edge("enrich", "generate")
    workflow.add_edge("generate", "validate")

    # Conditional: refine if invalid, otherwise execute
    workflow.add_conditional_edges(
        "validate",
        should_refine,
        {
            "refine": "refine",
            "execute": "execute"
        }
    )

    # Refine loops back to validate
    workflow.add_edge("refine", "validate")

    # Execute -> Interpret -> Adaptive Refinement
    workflow.add_edge("execute", "interpret")
    workflow.add_edge("interpret", "adaptive_refine")  # Apply refinements after interpretation

    # Phase 7: Control flow mode path
    workflow.add_edge("control_flow_generate", "control_flow_execute")
    workflow.add_edge("control_flow_execute", "control_flow_analyze")
    workflow.add_edge("control_flow_analyze", "control_flow_synthesize")
    workflow.add_edge("control_flow_synthesize", END)  # Control flow mode ends here

    # Semantic mode: Continue to RAGAS or END
    if enable_ragas:
        workflow.add_edge("adaptive_refine", "evaluate")
        workflow.add_edge("evaluate", END)
    else:
        workflow.add_edge("adaptive_refine", END)

    # Compile
    compiled_workflow = workflow.compile()

    logger.info("Workflow built successfully (Phase 7 control flow mode integrated)")
    return compiled_workflow


# ============================================================================
# EXECUTION INTERFACE
# ============================================================================

def run_workflow(question: str, verbose: bool = True, enable_ragas: bool = False, streaming: bool = False, use_multi_query: bool = False) -> Dict[str, Any]:
    """Run the complete RAG-CPGQL workflow on a single question.

    Args:
        question: Natural language question about PostgreSQL
        verbose: Whether to print progress messages
        enable_ragas: Whether to enable RAGAS evaluation (default: False).
                     Adds 50-70s overhead per query. Recommended only for debugging,
                     not for batch processing.
        streaming: Unused parameter for API compatibility (ignored)
        use_multi_query: Whether to use multi-query approach (Query Funnel) with automatic fallback (default: False).
                        When enabled, generates 3 query variants (PRECISE, BALANCED, BROAD) and uses the first
                        that returns sufficient results (≥5). Recommended for reducing empty result rate.

    Returns:
        Dictionary containing final state and results
    """
    if verbose:
        print("\n" + "="*80)
        print(f"RAG-CPGQL LANGGRAPH WORKFLOW")
        if use_multi_query:
            print("(Multi-Query Approach ENABLED)")
        print("="*80)
        print(f"Question: {question}\n")

    # Build workflow
    workflow = build_workflow(enable_ragas=enable_ragas)

    # Initialize state
    initial_state: RAGCPGQLState = {
        "question": question,
        "intent": None,
        "domain": None,
        "keywords": None,
        "complexity": None,
        "similar_qa": None,
        "cpgql_examples": None,
        "retrieval_metadata": None,
        "enrichment_hints": None,
        "enrichment_coverage": None,
        "cpgql_query": None,
        "generation_time": None,
        "query_variants": None,
        "use_multi_query": use_multi_query,
        "query_valid": False,
        "validation_error": None,
        "retry_count": 0,
        "execution_result": None,
        "execution_success": False,
        "execution_time": None,
        "execution_error": None,
        "fallback_count": None,
        "specificity_used": None,
        "ranked_results": None,
        "ranking_metadata": None,
        "question_type": None,
        "result_count": None,
        "refinement_applied": None,
        "refinement_strategy": None,
        "refinement_suggestions": None,
        "answer": None,
        "answer_confidence": None,
        "faithfulness": None,
        "answer_relevance": None,
        "context_precision": None,
        "context_recall": None,
        "overall_score": None,
        "messages": [HumanMessage(content=question)],
        "iteration": 0,
        "total_time": None,
        "error": None
    }

    # Execute workflow
    start_time = time.time()

    try:
        final_state = workflow.invoke(initial_state)
        final_state["total_time"] = time.time() - start_time

        if verbose:
            print("\n" + "="*80)
            print("WORKFLOW COMPLETED")
            print("="*80)
            print(f"\nQuery: {final_state.get('cpgql_query', 'N/A')}")
            print(f"Valid: {final_state.get('query_valid', False)}")
            print(f"Execution: {'SUCCESS' if final_state.get('execution_success') else 'FAILED'}")
            print(f"\nAnswer:\n{final_state.get('answer', 'N/A')}")

            # Handle RAGAS score (may be None if RAGAS disabled)
            overall_score = final_state.get('overall_score')
            if overall_score is not None:
                print(f"\nRAGAS Score: {overall_score:.3f}")
            else:
                print(f"\nRAGAS Score: N/A (disabled)")

            print(f"Total Time: {final_state.get('total_time', 0):.2f}s")
            print("="*80 + "\n")

        return {
            "success": True,
            "state": final_state,
            "question": question,
            "query": final_state.get("cpgql_query"),
            "answer": final_state.get("answer"),
            "valid": final_state.get("query_valid", False),
            "execution_success": final_state.get("execution_success", False),
            "execution_error": final_state.get("execution_error"),
            "overall_score": final_state.get("overall_score", 0.0),
            "total_time": final_state.get("total_time", 0.0)
        }

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "question": question,
            "execution_success": False,
            "execution_error": str(e),
            "total_time": time.time() - start_time
        }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Test the workflow with a sample question
    test_question = "How does PostgreSQL handle transaction isolation in MVCC?"

    result = run_workflow(test_question, verbose=True)

    if result["success"]:
        print("\n[OK] Workflow executed successfully")
    else:
        print(f"\n[ERROR] Workflow failed: {result.get('error')}")
EMPTY_RESULT_PATTERNS = [
    r"^\s*\[\s*\]\s*$",
    r"List\(\)\s*$",
    r"Vector\(\)\s*$",
    r"ArrayBuffer\(\)\s*$",
    r"=\s*List\(\)\s*$",
    r"=\s*Vector\(\)\s*$",
    r"=\s*None\s*$",
    r"No CPG loaded",
    r"No results",
]


def is_empty_result(raw_result: Optional[str]) -> bool:
    if raw_result is None:
        return True
    stripped = raw_result.strip()
    if not stripped:
        return True
    for pattern in EMPTY_RESULT_PATTERNS:
        if re.search(pattern, stripped):
            # Ensure we do not misclassify non-empty lists like List(Call(...))
            if "List(" in stripped and not re.search(r"List\(\)", stripped):
                continue
            return True
    return False


def generate_query_fallbacks(query: str) -> List[str]:
    fallbacks: List[str] = []

    def _normalize(candidate: str) -> Optional[str]:
        candidate = candidate.strip().rstrip(";")
        candidate = re.sub(r"\.\.", ".", candidate)
        candidate = re.sub(r"\.l\.l", ".l", candidate)
        candidate = re.sub(r"\.l\.(take|head|size)", r".l.\1", candidate)
        if not candidate:
            return None
        return candidate

    # Removed: Fallback that deletes .valueExact() alone creates invalid syntax
    # Only delete .valueExact() when it's part of .tag.nameExact().valueExact() pattern
    # This is handled by the broader pattern below at line 1150-1152

    if ".tag." in query:
        fallbacks.append(re.sub(r"\.tag\.[^\.]+\(\".*?\"\)", "", query))

    loosened = re.sub(r"\.valueExact\(\".*?\"\)", "", query)
    loosened = re.sub(r"\.tag\.[^\.]+\(\".*?\"\)", "", loosened)
    fallbacks.append(loosened)

    if ".argument." in query:
        fallbacks.append(re.sub(r"\.argument[^\.]*", "", query))

    if "cpg.call" in query:
        fallbacks.append(query.replace("cpg.call", "cpg.method"))

    for match in re.findall(r'\.name\("([^"]+)"\)', query):
        if not match:
            continue
        base = match.replace("*", "")
        if match and "*" not in match and len(match) >= 3:
            fallbacks.append(query.replace(f'.name("{match}")', f'.name("{match}*")'))
        if base and len(base) >= 3:
            regex_variant = f'.name(".*{re.escape(base)}.*")'
            fallbacks.append(query.replace(f'.name("{match}")', regex_variant))

    for match in re.findall(r'\.nameExact\("([^"]+)"\)', query):
        if not match:
            continue
        base = match.replace("*", "")
        if match and "*" not in match and len(match) >= 3:
            fallbacks.append(query.replace(f'.nameExact("{match}")', f'.name("{match}*")'))
        if base and len(base) >= 3:
            regex_variant = f'.name(".*{re.escape(base)}.*")'
            fallbacks.append(query.replace(f'.nameExact("{match}")', regex_variant))

    normalized = _normalize(query)
    if normalized and normalized.endswith(".l"):
        fallbacks.append(f"{normalized}.take(20)")

    cleaned: List[str] = []
    seen = set()
    for candidate in fallbacks:
        candidate = _normalize(candidate)
        if not candidate:
            continue
        if not candidate.endswith(".l") and not candidate.endswith(".take(20)"):
            candidate = re.sub(r"\.l$", "", candidate)
            candidate += ".l"
        candidate = candidate.replace("..", ".")
        if candidate not in seen and candidate != query:
            seen.add(candidate)
            cleaned.append(candidate)

    expanded: List[str] = []
    for candidate in cleaned:
        expanded.append(candidate)
        if "cpg.call" in candidate:
            expanded.append(candidate.replace("cpg.call", "cpg.method", 1))

    final: List[str] = []
    final_seen = set()
    for candidate in expanded:
        candidate = _normalize(candidate)
        if not candidate:
            continue
        if not candidate.endswith(".l") and not candidate.endswith(".take(20)"):
            candidate = re.sub(r"\.l$", "", candidate)
            candidate += ".l"
        candidate = candidate.replace("..", ".")
        if candidate not in final_seen and candidate != query:
            final_seen.add(candidate)
            final.append(candidate)

    return final


def build_keyword_fallback_query(state: RAGCPGQLState) -> Optional[str]:
    keywords = state.get("keywords") or []
    for keyword in keywords:
        token = re.sub(r"[^A-Za-z0-9_]", "", keyword)
        if token and len(token) >= 3:
            pattern = re.escape(token)
            return f'cpg.method.name(".*{pattern}.*").l.take(20)'
    return None
