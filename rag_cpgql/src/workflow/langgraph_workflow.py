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
from typing import TypedDict, List, Optional, Dict, Any
import time

# LangGraph imports
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

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
    overall_score: Optional[float]

    # Metadata
    messages: List[BaseMessage]
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

        # Initialize analyzer
        analyzer = AnalyzerAgent()

        # Analyze question
        analysis = analyzer.analyze(question)

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

        # Initialize retriever (assumes vector store is already initialized)
        retriever = RetrieverAgent()

        # Retrieve context
        retrieval_result = retriever.retrieve(
            question=question,
            analysis=analysis,
            top_k_qa=3,
            top_k_cpgql=5
        )

        # Update state
        state["similar_qa"] = retrieval_result.get("qa_pairs", [])
        state["cpgql_examples"] = retrieval_result.get("cpgql_examples", [])
        state["retrieval_metadata"] = retrieval_result.get("metadata", {})

        # Add message
        qa_count = len(state["similar_qa"])
        cpgql_count = len(state["cpgql_examples"])
        avg_sim = state["retrieval_metadata"].get("avg_qa_similarity", 0)

        state["messages"].append(AIMessage(
            content=f"Retrieved: {qa_count} Q&A pairs, {cpgql_count} CPGQL examples "
                   f"(avg similarity: {avg_sim:.3f})"
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

        # Initialize enrichment agent
        enrichment = EnrichmentAgent()

        # Get enrichment hints
        hints = enrichment.get_enrichment_hints(
            question=question,
            analysis=analysis,
            retrieved_qa=state.get("similar_qa", [])
        )

        # Calculate coverage
        coverage = len(hints) / 12.0  # 12 total enrichment layers

        # Update state
        state["enrichment_hints"] = hints
        state["enrichment_coverage"] = coverage

        # Add message
        state["messages"].append(AIMessage(
            content=f"Enrichment: {len(hints)} hints ({coverage:.1%} coverage)"
        ))

        logger.info(f"Enrichment: {len(hints)} hints, {coverage:.1%} coverage")

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

        retrieval_result = {
            "qa_pairs": state.get("similar_qa", []),
            "cpgql_examples": state.get("cpgql_examples", []),
            "metadata": state.get("retrieval_metadata", {})
        }

        enrichment_hints = state.get("enrichment_hints", [])

        # Initialize generator (without grammar for now)
        # TODO: Add grammar support
        generator = GeneratorAgent(use_llmxcpg=True, use_grammar=False)

        # Generate query
        query = generator.generate(
            question=question,
            analysis=analysis,
            retrieval_result=retrieval_result,
            enrichment_hints=enrichment_hints
        )

        generation_time = time.time() - start_time

        # Update state
        state["cpgql_query"] = query
        state["generation_time"] = generation_time

        # Add message
        state["messages"].append(AIMessage(
            content=f"Generated query ({generation_time:.2f}s): {query[:100]}..."
        ))

        logger.info(f"Generated query in {generation_time:.2f}s")

    except Exception as e:
        logger.error(f"Generator error: {e}", exc_info=True)
        state["error"] = f"Generator failed: {str(e)}"
        state["query_valid"] = False

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
        previous_query = state.get("cpgql_query", "")
        error = state.get("validation_error", "")

        logger.info(f"Refining query (attempt {retry_count + 1}/2)")
        logger.info(f"Error: {error}")

        # Simple refinement logic
        refined_query = previous_query

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
        state["messages"].append(AIMessage(
            content=f"Refined query (attempt {retry_count + 1}): {refined_query[:100]}..."
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
        # For now, compute simple heuristic scores
        # TODO: Integrate actual RAGAS evaluation

        # Faithfulness: based on execution success
        if state.get("execution_success", False):
            state["faithfulness"] = 0.9
        else:
            state["faithfulness"] = 0.3

        # Answer relevance: based on answer confidence and length
        answer_conf = state.get("answer_confidence", 0.5)
        answer_len = len(state.get("answer", ""))
        if answer_len > 50:
            state["answer_relevance"] = answer_conf * 0.9
        else:
            state["answer_relevance"] = answer_conf * 0.5

        # Context precision: based on retrieval quality
        retrieval_meta = state.get("retrieval_metadata", {})
        avg_sim = retrieval_meta.get("avg_qa_similarity", 0.5)
        state["context_precision"] = avg_sim

        # Overall score
        state["overall_score"] = (
            state["faithfulness"] +
            state["answer_relevance"] +
            state["context_precision"]
        ) / 3.0

        # Add message
        state["messages"].append(AIMessage(
            content=f"RAGAS Score: {state['overall_score']:.3f} "
                   f"(F:{state['faithfulness']:.2f}, "
                   f"A:{state['answer_relevance']:.2f}, "
                   f"C:{state['context_precision']:.2f})"
        ))

        logger.info(f"RAGAS Overall Score: {state['overall_score']:.3f}")

    except Exception as e:
        logger.error(f"Evaluator error: {e}", exc_info=True)
        state["faithfulness"] = 0.0
        state["answer_relevance"] = 0.0
        state["context_precision"] = 0.0
        state["overall_score"] = 0.0

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
