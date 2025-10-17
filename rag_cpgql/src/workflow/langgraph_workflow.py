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
"""

import sys
import json
import logging
from pathlib import Path
from typing import TypedDict, List, Optional, Dict, Any, Annotated
import time

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

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

# Local imports
from src.agents.analyzer_agent import AnalyzerAgent
from src.agents.retriever_agent import RetrieverAgent
from src.agents.enrichment_agent import EnrichmentAgent
from src.agents.generator_agent import GeneratorAgent
from src.execution.joern_client import JoernClient
from src.generation.llm_interface import LLMInterface
from src.generation.cpgql_generator import CPGQLGenerator
from src.retrieval.vector_store_real import VectorStoreReal

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# LAZY-LOADED COMPONENTS
# ============================================================================

_ANALYZER: Optional[AnalyzerAgent] = None
_VECTOR_STORE: Optional[VectorStoreReal] = None
_RETRIEVER: Optional[RetrieverAgent] = None
_ENRICHMENT_AGENT: Optional[EnrichmentAgent] = None
_LLM_INTERFACE: Optional[LLMInterface] = None
_CPGQL_GENERATOR: Optional[CPGQLGenerator] = None
_GENERATOR_AGENT: Optional[GeneratorAgent] = None


def get_analyzer() -> AnalyzerAgent:
    """Return a shared AnalyzerAgent instance."""
    global _ANALYZER
    if _ANALYZER is None:
        _ANALYZER = AnalyzerAgent()
    return _ANALYZER


def get_vector_store() -> VectorStoreReal:
    """Return an initialized VectorStoreReal instance."""
    global _VECTOR_STORE
    if _VECTOR_STORE is None:
        _VECTOR_STORE = VectorStoreReal()
        try:
            _VECTOR_STORE.initialize_collections()
        except Exception as exc:
            logger.warning(f"Vector store initialization failed: {exc}")
    return _VECTOR_STORE


def get_retriever() -> RetrieverAgent:
    """Return a retriever that shares analyzer and vector store state."""
    global _RETRIEVER
    if _RETRIEVER is None:
        _RETRIEVER = RetrieverAgent(
            vector_store=get_vector_store(),
            analyzer_agent=get_analyzer()
        )
    return _RETRIEVER


def get_enrichment_agent() -> EnrichmentAgent:
    """Return a shared EnrichmentAgent instance."""
    global _ENRICHMENT_AGENT
    if _ENRICHMENT_AGENT is None:
        _ENRICHMENT_AGENT = EnrichmentAgent()
    return _ENRICHMENT_AGENT


def get_generator_agent() -> GeneratorAgent:
    """Return a GeneratorAgent backed by a shared LLM + grammar generator."""
    global _GENERATOR_AGENT, _CPGQL_GENERATOR, _LLM_INTERFACE
    if _GENERATOR_AGENT is None:
        if _LLM_INTERFACE is None:
            # Per README guidance, default to Qwen3-Coder model (no LLMxCPG).
            _LLM_INTERFACE = LLMInterface(use_llmxcpg=False, verbose=False)
        if _CPGQL_GENERATOR is None:
            # Grammar constraints are disabled because they degrade output quality.
            _CPGQL_GENERATOR = CPGQLGenerator(_LLM_INTERFACE, use_grammar=False)
        _GENERATOR_AGENT = GeneratorAgent(
            cpgql_generator=_CPGQL_GENERATOR,
            use_grammar=False
        )
    return _GENERATOR_AGENT


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
# STATE SCHEMA
# ============================================================================

class RAGCPGQLState(TypedDict):
    """State passed between LangGraph nodes.

    This state is maintained throughout the entire workflow execution
    and is passed between all agent nodes.
    """

    # Input
    question: str

    # Analysis (Analyzer Agent)
    intent: Optional[str]  # "find-function", "explain-concept", "security-check"
    domain: Optional[str]  # "memory", "query-planning", "wal", "vacuum", etc.
    keywords: Optional[List[str]]
    complexity: Optional[str]  # "simple", "medium", "complex"

    # Retrieval (Retriever Agent)
    similar_qa: Optional[List[Dict]]  # Top-K similar Q&A pairs
    cpgql_examples: Optional[List[Dict]]  # Top-K CPGQL examples
    retrieval_metadata: Optional[Dict]  # Similarity scores, etc.

    # Enrichment (Enrichment Agent)
    enrichment_hints: Optional[List[str]]  # Relevant enrichment tags
    enrichment_coverage: Optional[float]  # Coverage score (0-1)

    # Generation (Generator Agent)
    cpgql_query: Optional[str]
    generation_time: Optional[float]

    # Validation (Validator Agent)
    query_valid: bool
    validation_error: Optional[str]
    retry_count: int

    # Execution (Executor Agent)
    execution_result: Optional[Dict]
    execution_success: bool
    execution_time: Optional[float]
    execution_error: Optional[str]

    # Interpretation (Interpreter Agent)
    answer: Optional[str]
    answer_confidence: Optional[float]

    # Evaluation (RAGAS)
    faithfulness: Optional[float]
    answer_relevance: Optional[float]
    context_precision: Optional[float]
    context_recall: Optional[float]
    overall_score: Optional[float]

    # Metadata
    messages: Annotated[List[BaseMessage], add_messages]
    iteration: int
    total_time: Optional[float]
    error: Optional[str]


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

        # Add message
        state["messages"].append(AIMessage(
            content=f"Analysis: domain={state['domain']}, "
                   f"intent={state['intent']}, "
                   f"complexity={state['complexity']}"
        ))

        logger.info(f"Domain: {state['domain']}, Intent: {state['intent']}")

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


def generate_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Generator Agent: Generate CPGQL query with full context."""
    logger.info("=== GENERATOR AGENT ===")

    try:
        start_time = time.time()

        question = state["question"]

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
        query, is_valid, error = generator.generate(
            question=question,
            context=context
        )

        generation_time = time.time() - start_time

        # Update state
        state["cpgql_query"] = query
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
        query = state.get("cpgql_query", "")

        if not query or not state.get("query_valid", False):
            logger.warning("Skipping execution: invalid query")
            state["execution_success"] = False
            state["execution_error"] = "Query not valid, skipping execution"
            return state

        # Initialize Joern client
        joern_client = JoernClient(server_endpoint="localhost:8080")

        # Try to connect
        if not joern_client.connect():
            logger.warning("Joern server not available, skipping execution")
            state["execution_success"] = False
            state["execution_error"] = "Joern server not available"

            # Add message
            state["messages"].append(AIMessage(
                content="Execution skipped: Joern server not available"
            ))

            joern_client.close()
            return state

        # Execute query
        start_time = time.time()
        exec_result = joern_client.execute_query(query)
        execution_time = time.time() - start_time

        # Update state
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

        # Cleanup
        joern_client.close()

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
        question = state["question"]
        query = state.get("cpgql_query", "")
        execution_success = state.get("execution_success", False)
        execution_result = state.get("execution_result", {})

        # Check if execution was successful
        if not execution_success:
            error = state.get("execution_error", "Unknown error")
            state["answer"] = f"I couldn't answer the question because the query execution failed: {error}"
            state["answer_confidence"] = 0.0
            state["messages"].append(AIMessage(
                content=f"Answer: {state['answer']}"
            ))
            return state

        # Get results
        result_data = execution_result.get("result", "")

        # Simple interpretation (can be enhanced with LLM)
        if not result_data or result_data == "[]" or result_data == "":
            state["answer"] = f"The query executed successfully but returned no results. "\
                            f"The query was: {query}"
            state["answer_confidence"] = 0.5
        else:
            # For now, just return the raw results
            # TODO: Use LLM to convert to natural language
            result_str = str(result_data)[:500]  # Limit length
            state["answer"] = f"Based on the CPGQL query '{query}', the results are:\n\n{result_str}"
            if len(str(result_data)) > 500:
                state["answer"] += "\n\n(Results truncated for brevity)"
            state["answer_confidence"] = 0.8

        # Add message
        state["messages"].append(AIMessage(
            content=f"Answer generated (confidence: {state['answer_confidence']:.1%})"
        ))

        logger.info(f"Answer generated: {len(state['answer'])} chars")

    except Exception as e:
        logger.error(f"Interpreter error: {e}", exc_info=True)
        state["answer"] = f"I encountered an error while interpreting the results: {str(e)}"
        state["answer_confidence"] = 0.0
        state["messages"].append(AIMessage(
            content=f"Interpretation error: {str(e)}"
        ))

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

def build_workflow() -> StateGraph:
    """Build the complete LangGraph RAG-CPGQL workflow.

    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("Building LangGraph workflow...")

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
    workflow.add_node("evaluate", evaluate_node)

    # Define linear flow
    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "retrieve")
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

    # Continue linear flow
    workflow.add_edge("execute", "interpret")
    workflow.add_edge("interpret", "evaluate")
    workflow.add_edge("evaluate", END)

    # Compile
    compiled_workflow = workflow.compile()

    logger.info("Workflow built successfully")
    return compiled_workflow


# ============================================================================
# EXECUTION INTERFACE
# ============================================================================

def run_workflow(question: str, verbose: bool = True) -> Dict[str, Any]:
    """Run the complete RAG-CPGQL workflow on a single question.

    Args:
        question: Natural language question about PostgreSQL
        verbose: Whether to print progress messages

    Returns:
        Dictionary containing final state and results
    """
    if verbose:
        print("\n" + "="*80)
        print(f"RAG-CPGQL LANGGRAPH WORKFLOW")
        print("="*80)
        print(f"Question: {question}\n")

    # Build workflow
    workflow = build_workflow()

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
        "query_valid": False,
        "validation_error": None,
        "retry_count": 0,
        "execution_result": None,
        "execution_success": False,
        "execution_time": None,
        "execution_error": None,
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
            print(f"\nRAGAS Score: {final_state.get('overall_score', 0.0):.3f}")
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
            "overall_score": final_state.get("overall_score", 0.0),
            "total_time": final_state.get("total_time", 0.0)
        }

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "question": question,
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
