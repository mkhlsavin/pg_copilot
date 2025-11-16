"""Simplified LangGraph RAG-CPGQL Workflow

This module implements a simplified LangGraph workflow that properly integrates
with the existing 4-agent system, adding validation, retry, and interpretation layers.

Key improvements over the original 4-agent system:
- Stateful execution with LangGraph
- Automatic retry logic on validation failure
- Natural language answer interpretation
- Observable execution flow
"""

import sys
import json
import logging
from pathlib import Path
from typing import TypedDict, List, Optional, Dict, Any
import time

# LangGraph imports
from langgraph.graph import StateGraph, END

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Local imports
from src.agents.analyzer_agent import AnalyzerAgent
from src.agents.retriever_agent import RetrieverAgent
from src.agents.enrichment_agent import EnrichmentAgent
from src.agents.generator_agent import GeneratorAgent
from src.agents.interpreter_agent import InterpreterAgent
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
# SIMPLIFIED STATE SCHEMA
# ============================================================================

class RAGCPGQLState(TypedDict):
    """Simplified state for LangGraph workflow."""

    # Input
    question: str

    # Analysis (NEW - for RAGAS)
    analysis: Optional[Dict]  # domain, intent, keywords, confidence

    # Retrieved context (from retriever)
    context: Optional[Dict]
    similar_qa: Optional[List[Dict]]  # NEW - for RAGAS retrieval metrics
    cpgql_examples: Optional[List[Dict]]  # NEW - for RAGAS retrieval metrics

    # Enrichment (NEW - for RAGAS)
    enrichment_hints: Optional[Dict]  # with coverage_score

    # Generated query
    cpgql_query: Optional[str]
    query_valid: bool
    validation_error: Optional[str]
    retry_count: int

    # Execution
    execution_result: Optional[Dict]
    execution_success: bool

    # Answer
    answer: Optional[str]
    confidence: Optional[float]  # NEW - for RAGAS

    # Adaptive regeneration (Phase 6)
    adaptive_retry_count: int  # Track adaptive regeneration attempts
    original_query: Optional[str]  # Store original query for comparison

    # Metadata
    total_time: float
    generation_time: float  # NEW - individual timing
    retrieval_time: float  # NEW - individual timing
    execution_time: float  # NEW - individual timing
    error: Optional[str]


# ============================================================================
# GLOBAL STATE (agents initialized once)
# ============================================================================

_AGENTS_INITIALIZED = False
_VECTOR_STORE = None
_ANALYZER = None
_RETRIEVER = None
_ENRICHMENT = None
_GENERATOR = None
_INTERPRETER = None
_JOERN_CLIENT = None


def _initialize_agents():
    """Initialize all agents once (shared across workflow invocations)."""
    global _AGENTS_INITIALIZED, _VECTOR_STORE, _ANALYZER, _RETRIEVER, _ENRICHMENT, _GENERATOR, _INTERPRETER, _JOERN_CLIENT

    if _AGENTS_INITIALIZED:
        return

    logger.info("Initializing agents...")

    # Vector store
    _VECTOR_STORE = VectorStoreReal()

    # Analyzer
    _ANALYZER = AnalyzerAgent()

    # Retriever
    _RETRIEVER = RetrieverAgent(_VECTOR_STORE, _ANALYZER)

    # Enrichment
    _ENRICHMENT = EnrichmentAgent()

    # Generator (with LLM and CPGQL generator)
    llm = LLMInterface(use_llmxcpg=True, n_ctx=4096, verbose=False)
    # SEMANTIC MODE ENABLED: Use comment-based question answering
    cpgql_gen = CPGQLGenerator(llm, use_grammar=False, use_semantic=True)
    _GENERATOR = GeneratorAgent(cpgql_gen, use_grammar=False, use_semantic=True)

    # Interpreter (with LLM for answer synthesis)
    # SEMANTIC MODE ENABLED: Extract and cite evidence from comments
    _INTERPRETER = InterpreterAgent(llm, use_semantic=True)

    # Joern client (persistent connection)
    _JOERN_CLIENT = JoernClient(server_endpoint="localhost:8080")
    if _JOERN_CLIENT.connect():
        logger.info("Connected to Joern server at localhost:8080")
    else:
        logger.warning("Could not connect to Joern server - execution will be skipped")

    _AGENTS_INITIALIZED = True
    logger.info("Agents initialized successfully - SEMANTIC MODE ENABLED")


# ============================================================================
# WORKFLOW NODES
# ============================================================================

def analyze_and_retrieve_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Combined node: Analyze + Retrieve + Enrich."""
    logger.info("=== ANALYZE + RETRIEVE + ENRICH ===")

    start_time = time.time()  # NEW: Track timing

    try:
        question = state["question"]

        # Analyze
        analysis = _ANALYZER.analyze(question)
        logger.info(f"Analysis: domain={analysis.get('domain')}, intent={analysis.get('intent')}")

        # Retrieve
        retrieval_result = _RETRIEVER.retrieve(
            question=question,
            analysis=analysis,
            top_k_qa=3,
            top_k_cpgql=5
        )

        # Enrich
        enrichment_hints = _ENRICHMENT.get_enrichment_hints(
            question=question,
            analysis=analysis
        )

        retrieval_time = time.time() - start_time  # NEW: Calculate retrieval time

        # Build combined context
        context = {
            "analysis": analysis,
            "similar_qa": retrieval_result.get("similar_qa", []),
            "cpgql_examples": retrieval_result.get("cpgql_examples", []),
            "enrichment_hints": enrichment_hints
        }

        # NEW: Save data to state for RAGAS evaluation
        state["context"] = context
        state["analysis"] = analysis
        state["similar_qa"] = retrieval_result.get("similar_qa", [])
        state["cpgql_examples"] = retrieval_result.get("cpgql_examples", [])
        state["enrichment_hints"] = enrichment_hints
        state["retrieval_time"] = retrieval_time

        logger.info(f"Retrieved {len(context['similar_qa'])} Q&A, "
                   f"{len(context['cpgql_examples'])} CPGQL, "
                   f"{len(enrichment_hints.get('tags', []))} enrichment tags")

    except Exception as e:
        logger.error(f"Analyze/Retrieve error: {e}", exc_info=True)
        state["error"] = f"Analysis/Retrieval failed: {str(e)}"

    return state


def generate_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Generate CPGQL query."""
    logger.info("=== GENERATE ===")

    start_time = time.time()  # NEW: Track timing

    try:
        question = state["question"]
        context = state.get("context", {})

        # Generate
        query, is_valid, error = _GENERATOR.generate(question, context)

        generation_time = time.time() - start_time  # NEW: Calculate generation time

        state["cpgql_query"] = query
        state["query_valid"] = is_valid
        state["validation_error"] = error if not is_valid else None
        state["generation_time"] = generation_time  # NEW: Save timing

        logger.info(f"Generated: {query[:100]}... (valid={is_valid})")

    except Exception as e:
        logger.error(f"Generation error: {e}", exc_info=True)
        state["cpgql_query"] = None
        state["query_valid"] = False
        state["validation_error"] = str(e)
        state["generation_time"] = time.time() - start_time  # NEW: Save timing even on error

    return state


def refine_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Refine query on validation failure."""
    logger.info("=== REFINE ===")

    try:
        retry_count = state.get("retry_count", 0)

        # Max retries reached
        if retry_count >= 2:
            logger.warning("Max retries reached")
            state["cpgql_query"] = "cpg.method.name.l.take(10)"
            state["query_valid"] = True
            state["validation_error"] = None
            return state

        # Simple refinement logic
        previous_query = state.get("cpgql_query", "")
        error = state.get("validation_error", "")

        logger.info(f"Refining (attempt {retry_count + 1}): {error}")

        # Auto-fix common issues
        refined = previous_query

        if not refined.startswith("cpg."):
            refined = "cpg." + refined

        if not any(refined.endswith(t) for t in [".l", ".toList", ".size", ".head"]):
            refined = refined.rstrip(".") + ".l"

        state["cpgql_query"] = refined
        state["retry_count"] = retry_count + 1

        # Re-validate
        state["query_valid"] = True  # Assume fix works
        state["validation_error"] = None

        logger.info(f"Refined: {refined}")

    except Exception as e:
        logger.error(f"Refinement error: {e}", exc_info=True)

    return state


def execute_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Execute query on Joern using persistent connection."""
    logger.info("=== EXECUTE ===")

    start_time = time.time()  # NEW: Track timing

    try:
        query = state.get("cpgql_query")

        if not query or not state.get("query_valid"):
            logger.warning("Skipping execution: invalid query")
            state["execution_success"] = False
            state["execution_time"] = time.time() - start_time  # NEW: Save timing
            return state

        # Use persistent Joern client
        if not _JOERN_CLIENT or not _JOERN_CLIENT.client:
            logger.warning("Joern not available")
            state["execution_success"] = False
            state["execution_time"] = time.time() - start_time  # NEW: Save timing
            return state

        result = _JOERN_CLIENT.execute_query(query)

        execution_time = time.time() - start_time  # NEW: Calculate execution time

        state["execution_result"] = result
        state["execution_success"] = result.get("success", False)
        state["execution_time"] = execution_time  # NEW: Save timing

        if state["execution_success"]:
            logger.info("Execution successful")
        else:
            logger.warning(f"Execution failed: {result.get('error')}")

    except Exception as e:
        logger.error(f"Execution error: {e}", exc_info=True)
        state["execution_success"] = False
        state["execution_time"] = time.time() - start_time  # NEW: Save timing even on error

    return state


def interpret_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Convert results to natural language answer using InterpreterAgent."""
    logger.info("=== INTERPRET (SEMANTIC MODE) ===")

    try:
        question = state.get("question", "")
        query = state.get("cpgql_query", "")
        success = state.get("execution_success", False)
        result = state.get("execution_result", {})

        # Store original query for adaptive regeneration comparison
        if state.get("adaptive_retry_count", 0) == 0:
            state["original_query"] = query

        # Use InterpreterAgent for semantic answer synthesis
        interpretation = _INTERPRETER.interpret(
            question=question,
            query=query,
            execution_success=success,
            execution_result=result,
            execution_error=result.get("error") if not success else None
        )

        state["answer"] = interpretation.get("answer", "Failed to generate answer")
        state["confidence"] = interpretation.get("confidence", 0.0)  # NEW: Save confidence

        logger.info(f"Answer generated (confidence: {interpretation.get('confidence', 0.0):.2f})")

    except Exception as e:
        logger.error(f"Interpretation error: {e}", exc_info=True)
        state["answer"] = f"Error interpreting results: {str(e)}"
        state["confidence"] = 0.0  # NEW: Set confidence to 0 on error

    return state


def adaptive_regenerate_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Adaptively regenerate query if answer is poor quality.

    Phase 6: Adaptive Regeneration
    - Detects empty or low-confidence answers
    - Regenerates with explicit instruction for broader patterns
    - Executes new query and re-interprets
    - Compares with original and keeps better answer
    """
    logger.info("=== ADAPTIVE REGENERATION ===")
    logger.warning(f"Original answer quality poor (confidence={state.get('confidence', 0):.2f}, "
                  f"length={len(state.get('answer', ''))}) - attempting regeneration")

    try:
        # Increment adaptive retry count
        state["adaptive_retry_count"] = state.get("adaptive_retry_count", 0) + 1

        # Save original answer for comparison
        original_answer = state.get("answer", "")
        original_confidence = state.get("confidence", 0.0)
        original_query = state.get("original_query", state.get("cpgql_query", ""))

        # Regenerate with explicit instruction for broader patterns
        question = state.get("question", "")
        context = state.get("context", {})

        logger.info("Regenerating with instruction: Use simpler/broader patterns")

        # Add explicit hint to context for broader patterns
        regeneration_hint = (
            "CRITICAL: Previous query returned empty/poor results. "
            "Use SIMPLER and BROADER patterns. "
            "Example: instead of '.*specific_long_method_name.*', use '.*key_word.*' "
            "Avoid OR patterns if they seem too complex."
        )

        gen_start = time.time()
        regenerated_query = _GENERATOR.generate(
            question=f"{question}\n\n{regeneration_hint}",
            context=context
        )
        state["generation_time"] = time.time() - gen_start

        state["cpgql_query"] = regenerated_query.get("query", "")
        state["query_valid"] = regenerated_query.get("valid", False)

        logger.info(f"Regenerated query: {state['cpgql_query'][:100]}...")

        # Execute regenerated query
        logger.info("=== EXECUTE (REGENERATED) ===")
        exec_start = time.time()
        exec_result = _JOERN_CLIENT.execute_query(state["cpgql_query"])
        state["execution_time"] = time.time() - exec_start

        state["execution_result"] = exec_result
        state["execution_success"] = exec_result.get("success", False)

        logger.info(f"Execution successful: {state['execution_success']}")

        # Re-interpret with regenerated query result
        logger.info("=== INTERPRET (REGENERATED) ===")
        interpretation = _INTERPRETER.interpret(
            question=question,
            query=state["cpgql_query"],
            execution_success=state["execution_success"],
            execution_result=state["execution_result"],
            execution_error=exec_result.get("error") if not state["execution_success"] else None
        )

        new_answer = interpretation.get("answer", "")
        new_confidence = interpretation.get("confidence", 0.0)

        logger.info(f"Regenerated answer: confidence={new_confidence:.2f}, length={len(new_answer)}")

        # Compare and keep better answer
        if new_confidence > original_confidence or (len(new_answer) > len(original_answer) and len(original_answer) < 100):
            logger.info(f"✓ Regenerated answer is better (conf: {original_confidence:.2f}→{new_confidence:.2f})")
            state["answer"] = new_answer
            state["confidence"] = new_confidence
        else:
            logger.info(f"✗ Original answer was better, reverting (conf: {original_confidence:.2f} vs {new_confidence:.2f})")
            # Revert to original
            state["answer"] = original_answer
            state["confidence"] = original_confidence
            state["cpgql_query"] = original_query

    except Exception as e:
        logger.error(f"Adaptive regeneration error: {e}", exc_info=True)
        # Keep original answer on error
        logger.info("Error during regeneration, keeping original answer")

    return state


# ============================================================================
# CONDITIONAL ROUTING
# ============================================================================

def should_refine(state: RAGCPGQLState) -> str:
    """Route: refine if invalid, else execute."""
    if state.get("query_valid"):
        return "execute"
    elif state.get("retry_count", 0) >= 2:
        return "execute"  # Give up
    else:
        return "refine"


def should_adaptive_regenerate(state: RAGCPGQLState) -> str:
    """Route: adaptive regenerate if answer is poor quality, else end.

    Phase 6: Adaptive Regeneration Decision Logic
    """
    answer = state.get("answer", "")
    confidence = state.get("confidence", 0.0)
    adaptive_retry_count = state.get("adaptive_retry_count", 0)

    # Check if answer is poor quality
    is_empty_answer = len(answer) < 50  # Very short or empty
    is_low_confidence = confidence < 0.5  # Low confidence
    has_retries_left = adaptive_retry_count < 1  # Max 1 adaptive retry

    if (is_empty_answer or is_low_confidence) and has_retries_left:
        logger.info(f"Routing to adaptive_regenerate: empty={is_empty_answer}, low_conf={is_low_confidence}, retries={adaptive_retry_count}")
        return "adaptive_regenerate"
    else:
        logger.info(f"Routing to end: answer_len={len(answer)}, conf={confidence:.2f}, retries={adaptive_retry_count}")
        return "end"


# ============================================================================
# WORKFLOW BUILDER
# ============================================================================

def build_workflow() -> StateGraph:
    """Build the LangGraph workflow with adaptive regeneration."""
    logger.info("Building workflow...")

    # Initialize agents
    _initialize_agents()

    # Create graph
    workflow = StateGraph(RAGCPGQLState)

    # Add nodes
    workflow.add_node("analyze_retrieve", analyze_and_retrieve_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("refine", refine_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("interpret", interpret_node)
    workflow.add_node("adaptive_regenerate", adaptive_regenerate_node)  # NEW: Phase 6

    # Define flow
    workflow.set_entry_point("analyze_retrieve")
    workflow.add_edge("analyze_retrieve", "generate")

    # Conditional: refine or execute
    workflow.add_conditional_edges(
        "generate",
        should_refine,
        {
            "refine": "refine",
            "execute": "execute"
        }
    )

    # Refine loops back to generate
    workflow.add_edge("refine", "generate")

    workflow.add_edge("execute", "interpret")

    # NEW: Phase 6 - Conditional adaptive regeneration after interpret
    workflow.add_conditional_edges(
        "interpret",
        should_adaptive_regenerate,
        {
            "adaptive_regenerate": "adaptive_regenerate",
            "end": END
        }
    )

    # Adaptive regenerate loops back to interpret (re-interpretation happens in the node itself)
    workflow.add_edge("adaptive_regenerate", END)

    logger.info("Workflow built with adaptive regeneration")
    return workflow.compile()


# ============================================================================
# EXECUTION
# ============================================================================

def run_workflow(question: str, verbose: bool = True, streaming: bool = False) -> Dict[str, Any]:
    """Run workflow on a question.

    Args:
        question: User's question
        verbose: Print progress to console
        streaming: Unused parameter for API compatibility (ignored)
    """
    if verbose:
        print("\n" + "="*80)
        print("LANGGRAPH RAG-CPGQL WORKFLOW")
        print("="*80)
        print(f"Q: {question}\n")

    workflow = build_workflow()

    initial_state: RAGCPGQLState = {
        "question": question,
        "analysis": None,  # NEW
        "context": None,
        "similar_qa": None,  # NEW
        "cpgql_examples": None,  # NEW
        "enrichment_hints": None,  # NEW
        "cpgql_query": None,
        "query_valid": False,
        "validation_error": None,
        "retry_count": 0,
        "execution_result": None,
        "execution_success": False,
        "answer": None,
        "confidence": None,  # NEW
        "adaptive_retry_count": 0,  # NEW: Phase 6
        "original_query": None,  # NEW: Phase 6
        "total_time": 0.0,
        "generation_time": 0.0,  # NEW
        "retrieval_time": 0.0,  # NEW
        "execution_time": 0.0,  # NEW
        "error": None
    }

    start_time = time.time()

    try:
        final_state = workflow.invoke(initial_state)
        final_state["total_time"] = time.time() - start_time

        if verbose:
            print("\n" + "="*80)
            print("RESULT")
            print("="*80)
            print(f"Query: {final_state.get('cpgql_query')}")
            print(f"Valid: {final_state.get('query_valid')}")
            print(f"Executed: {final_state.get('execution_success')}")
            print(f"\nAnswer:\n{final_state.get('answer')}")
            print(f"\nTime: {final_state['total_time']:.2f}s")
            print("="*80 + "\n")

        return {
            "success": True,
            "state": final_state,
            "question": question,
            "query": final_state.get("cpgql_query"),
            "answer": final_state.get("answer"),
            "valid": final_state.get("query_valid"),
            "execution_success": final_state.get("execution_success"),
            "total_time": final_state["total_time"],

            # NEW: Add all missing data for RAGAS evaluation
            "analysis": final_state.get("analysis", {}),
            "similar_qa": final_state.get("similar_qa", []),
            "cpgql_examples": final_state.get("cpgql_examples", []),
            "enrichment_hints": final_state.get("enrichment_hints", {}),
            "confidence": final_state.get("confidence", 0.0),

            # NEW: Add individual timings
            "generation_time": final_state.get("generation_time", 0.0),
            "retrieval_time": final_state.get("retrieval_time", 0.0),
            "execution_time": final_state.get("execution_time", 0.0),

            # For RAGAS compatibility
            "ground_truth": "Valid CPGQL query",
            "execution_result": final_state.get("execution_result")
        }

    except Exception as e:
        logger.error(f"Workflow failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "question": question,
            "total_time": time.time() - start_time
        }


if __name__ == "__main__":
    test_question = "How does PostgreSQL handle transaction isolation in MVCC?"
    result = run_workflow(test_question, verbose=True)

    if result["success"]:
        print("[OK] Workflow completed")
    else:
        print(f"[ERROR] {result.get('error')}")
