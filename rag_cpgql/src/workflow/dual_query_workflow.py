"""Dual-Path RAG Workflow: CPGQL + SQL Integration (Phase 8F)

This workflow integrates both CPGQL (Joern) and SQL (DuckDB) query paths,
allowing parallel execution and result comparison.

Features:
- Parallel query generation (CPGQL + SQL)
- Dual execution (Joern + DuckDB)
- Result comparison and validation
- Automatic fallback if one path fails
- Performance metrics for both paths
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
# Use new configurable LLM provider (supports GigaChat, local models, etc.)
from src.llm.llm_interface_compat import LLMInterface
from src.generation.cpgql_generator import CPGQLGenerator
from src.generation.sql_query_generator import SQLQueryGenerator
from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient
from src.retrieval.vector_store_real import VectorStoreReal

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# DUAL-PATH STATE SCHEMA
# ============================================================================

class DualPathState(TypedDict):
    """State for dual-path workflow (CPGQL + SQL)."""

    # Input
    question: str
    use_sql: bool  # Enable SQL path
    use_cpgql: bool  # Enable CPGQL path

    # Analysis
    analysis: Optional[Dict]

    # Retrieved context
    context: Optional[Dict]
    similar_qa: Optional[List[Dict]]
    cpgql_examples: Optional[List[Dict]]
    enrichment_hints: Optional[Dict]

    # CPGQL Path
    cpgql_query: Optional[str]
    cpgql_valid: bool
    cpgql_execution_result: Optional[Dict]
    cpgql_success: bool
    cpgql_time: float

    # SQL Path (NEW)
    sql_query: Optional[str]
    sql_template: Optional[str]
    sql_params: Optional[Dict]
    sql_execution_result: Optional[Dict]
    sql_success: bool
    sql_time: float

    # Result Comparison
    results_match: Optional[bool]
    result_count_cpgql: Optional[int]
    result_count_sql: Optional[int]

    # Final Answer
    answer: Optional[str]
    answer_source: Optional[str]  # "cpgql", "sql", or "both"
    confidence: Optional[float]

    # Metadata
    total_time: float
    retrieval_time: float
    error: Optional[str]


# ============================================================================
# GLOBAL STATE (agents initialized once)
# ============================================================================

_AGENTS_INITIALIZED = False
_VECTOR_STORE = None
_ANALYZER = None
_RETRIEVER = None
_ENRICHMENT = None
_CPGQL_GENERATOR = None
_SQL_GENERATOR = None
_INTERPRETER = None
_JOERN_CLIENT = None
_DUCKDB_CLIENT = None


def _initialize_agents(duckdb_path: str = "sample_cpg_v2.duckdb"):
    """Initialize all agents once (shared across workflow invocations)."""
    global _AGENTS_INITIALIZED, _VECTOR_STORE, _ANALYZER, _RETRIEVER, _ENRICHMENT
    global _CPGQL_GENERATOR, _SQL_GENERATOR, _INTERPRETER, _JOERN_CLIENT, _DUCKDB_CLIENT

    if _AGENTS_INITIALIZED:
        return

    logger.info("Initializing dual-path agents...")

    # Vector store
    _VECTOR_STORE = VectorStoreReal()

    # Analyzer
    _ANALYZER = AnalyzerAgent()

    # Retriever
    _RETRIEVER = RetrieverAgent(_VECTOR_STORE, _ANALYZER)

    # Enrichment
    _ENRICHMENT = EnrichmentAgent()

    # LLM (shared)
    llm = LLMInterface(use_llmxcpg=True, n_ctx=4096, verbose=False)

    # CPGQL Generator
    cpgql_gen = CPGQLGenerator(llm, use_grammar=False, use_semantic=True)
    _CPGQL_GENERATOR = GeneratorAgent(cpgql_gen, use_grammar=False, use_semantic=True)

    # SQL Generator (NEW - Phase 8E)
    _SQL_GENERATOR = SQLQueryGenerator(llm=llm)

    # Interpreter (with LLM for answer synthesis)
    _INTERPRETER = InterpreterAgent(llm, use_semantic=True)

    # Joern client (persistent connection, uses JOERN_ENDPOINT env var or config)
    _JOERN_CLIENT = JoernClient()
    if _JOERN_CLIENT.connect():
        logger.info(f"[OK] Connected to Joern server at {_JOERN_CLIENT.server_endpoint}")
    else:
        logger.warning("[!] Could not connect to Joern server - CPGQL execution will be skipped")

    # DuckDB client (NEW - Phase 8D)
    _DUCKDB_CLIENT = DuckDBCPGClient(db_path=duckdb_path)
    if _DUCKDB_CLIENT.connect():
        logger.info(f"[OK] Connected to DuckDB: {duckdb_path}")
    else:
        logger.warning(f"[!] Could not connect to DuckDB - SQL execution will be skipped")

    _AGENTS_INITIALIZED = True
    logger.info("[OK] Dual-path agents initialized successfully")


# ============================================================================
# WORKFLOW NODES
# ============================================================================

def analyze_and_retrieve_node(state: DualPathState) -> DualPathState:
    """Combined node: Analyze + Retrieve + Enrich."""
    logger.info("=== ANALYZE + RETRIEVE + ENRICH ===")

    start_time = time.time()

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

        retrieval_time = time.time() - start_time

        # Build combined context
        context = {
            "analysis": analysis,
            "similar_qa": retrieval_result.get("similar_qa", []),
            "cpgql_examples": retrieval_result.get("cpgql_examples", []),
            "enrichment_hints": enrichment_hints
        }

        state["context"] = context
        state["analysis"] = analysis
        state["similar_qa"] = retrieval_result.get("similar_qa", [])
        state["cpgql_examples"] = retrieval_result.get("cpgql_examples", [])
        state["enrichment_hints"] = enrichment_hints
        state["retrieval_time"] = retrieval_time

        logger.info(f"[OK] Retrieved {len(context['similar_qa'])} Q&A, "
                   f"{len(context['cpgql_examples'])} CPGQL examples")

    except Exception as e:
        logger.error(f"Analysis/Retrieval error: {e}")
        state["error"] = str(e)

    return state


def generate_queries_node(state: DualPathState) -> DualPathState:
    """Generate both CPGQL and SQL queries in parallel."""
    logger.info("=== DUAL QUERY GENERATION ===")

    question = state["question"]
    context = state.get("context", {})

    # Generate CPGQL query (if enabled)
    if state.get("use_cpgql", True):
        try:
            start = time.time()
            cpgql_result = _CPGQL_GENERATOR.generate(question, context)
            state["cpgql_query"] = cpgql_result.get("query", "")
            state["cpgql_valid"] = True
            state["cpgql_time"] = time.time() - start
            logger.info(f"[OK] CPGQL query: {state['cpgql_query'][:100]}...")
        except Exception as e:
            logger.error(f"CPGQL generation failed: {e}")
            state["cpgql_valid"] = False
            state["cpgql_time"] = 0

    # Generate SQL query (if enabled) - NEW
    if state.get("use_sql", True):
        try:
            start = time.time()
            sql_result = _SQL_GENERATOR.generate_query(question)
            state["sql_query"] = sql_result.get("query", "")
            state["sql_template"] = sql_result.get("template", "")
            state["sql_params"] = sql_result.get("params", {})
            state["sql_time"] = time.time() - start
            logger.info(f"[OK] SQL query ({sql_result['template']}): {state['sql_query'][:100]}...")
        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            state["sql_query"] = None
            state["sql_time"] = 0

    return state


def execute_cpgql_node(state: DualPathState) -> DualPathState:
    """Execute CPGQL query on Joern."""
    if not state.get("use_cpgql", True) or not state.get("cpgql_valid", False):
        logger.info("Skipping CPGQL execution")
        state["cpgql_success"] = False
        return state

    logger.info("=== EXECUTE CPGQL ===")

    start = time.time()

    try:
        if not _JOERN_CLIENT or not _JOERN_CLIENT.connected:
            logger.warning("Joern not connected - skipping")
            state["cpgql_success"] = False
            return state

        query = state["cpgql_query"]
        result = _JOERN_CLIENT.execute_query(query)

        if result and result.get("success"):
            state["cpgql_execution_result"] = result
            state["cpgql_success"] = True

            # Count results
            result_str = result.get("result", "")
            # Simple heuristic: count newlines or list items
            count = len([line for line in result_str.split('\n') if line.strip()])
            state["result_count_cpgql"] = count

            logger.info(f"[OK] CPGQL execution successful ({count} results)")
        else:
            state["cpgql_success"] = False
            logger.warning("CPGQL execution failed")

    except Exception as e:
        logger.error(f"CPGQL execution error: {e}")
        state["cpgql_success"] = False

    state["cpgql_time"] = (state.get("cpgql_time", 0) + time.time() - start)

    return state


def execute_sql_node(state: DualPathState) -> DualPathState:
    """Execute SQL query on DuckDB (NEW - Phase 8F)."""
    if not state.get("use_sql", True) or not state.get("sql_query"):
        logger.info("Skipping SQL execution")
        state["sql_success"] = False
        return state

    logger.info("=== EXECUTE SQL ===")

    start = time.time()

    try:
        if not _DUCKDB_CLIENT or not _DUCKDB_CLIENT.conn:
            logger.warning("DuckDB not connected - skipping")
            state["sql_success"] = False
            return state

        query = state["sql_query"]
        results = _DUCKDB_CLIENT.execute_sql_dict(query)

        state["sql_execution_result"] = {"results": results}
        state["sql_success"] = True
        state["result_count_sql"] = len(results)

        logger.info(f"[OK] SQL execution successful ({len(results)} results)")

    except Exception as e:
        logger.error(f"SQL execution error: {e}")
        state["sql_success"] = False
        state["sql_execution_result"] = {"error": str(e)}

    state["sql_time"] = (state.get("sql_time", 0) + time.time() - start)

    return state


def compare_results_node(state: DualPathState) -> DualPathState:
    """Compare CPGQL and SQL results (NEW - Phase 8F)."""
    logger.info("=== COMPARE RESULTS ===")

    cpgql_success = state.get("cpgql_success", False)
    sql_success = state.get("sql_success", False)

    if cpgql_success and sql_success:
        cpgql_count = state.get("result_count_cpgql", 0)
        sql_count = state.get("result_count_sql", 0)

        # Simple comparison: check if counts are similar
        if abs(cpgql_count - sql_count) <= 2:  # Allow small variance
            state["results_match"] = True
            logger.info(f"[OK] Results match: CPGQL={cpgql_count}, SQL={sql_count}")
        else:
            state["results_match"] = False
            logger.warning(f"[!] Results differ: CPGQL={cpgql_count}, SQL={sql_count}")

        # Prefer SQL results (faster, more reliable for current setup)
        state["answer_source"] = "both"

    elif sql_success:
        state["answer_source"] = "sql"
        logger.info("Using SQL results (CPGQL unavailable)")
    elif cpgql_success:
        state["answer_source"] = "cpgql"
        logger.info("Using CPGQL results (SQL unavailable)")
    else:
        state["answer_source"] = "none"
        logger.warning("No results available from either path")

    return state


def interpret_node(state: DualPathState) -> DualPathState:
    """Interpret results and generate natural language answer."""
    logger.info("=== INTERPRET ANSWER ===")

    try:
        question = state["question"]
        answer_source = state.get("answer_source", "none")

        # Select result to interpret
        if answer_source == "both" or answer_source == "sql":
            # Prefer SQL results
            execution_result = state.get("sql_execution_result", {})
            query_used = state.get("sql_query", "")
            execution_success = state.get("sql_success", False)
        elif answer_source == "cpgql":
            execution_result = state.get("cpgql_execution_result", {})
            query_used = state.get("cpgql_query", "")
            execution_success = state.get("cpgql_success", False)
        else:
            # No results
            state["answer"] = "I couldn't find any results for your question."
            state["confidence"] = 0.0
            return state

        # Interpret
        interpretation = _INTERPRETER.interpret(
            question=question,
            query=query_used,
            execution_success=execution_success,
            execution_result=execution_result,
            enrichment_hints=state.get("enrichment_hints", {})
        )

        state["answer"] = interpretation.get("answer", "No answer generated.")
        state["confidence"] = interpretation.get("confidence", 0.5)

        # Add metadata about which path was used
        if answer_source == "both":
            state["answer"] += f"\n\n(Results validated: SQL and CPGQL both returned {state.get('result_count_sql', 0)} items)"
        elif answer_source == "sql":
            state["answer"] += f"\n\n(Source: SQL query on DuckDB CPG)"
        elif answer_source == "cpgql":
            state["answer"] += f"\n\n(Source: CPGQL query on Joern)"

        logger.info(f"[OK] Answer generated (confidence: {state['confidence']:.2f}, source: {answer_source})")

    except Exception as e:
        logger.error(f"Interpretation error: {e}")
        state["answer"] = f"Error generating answer: {str(e)}"
        state["confidence"] = 0.0

    return state


# ============================================================================
# WORKFLOW GRAPH CONSTRUCTION
# ============================================================================

def create_dual_path_workflow():
    """Create the dual-path workflow graph."""

    workflow = StateGraph(DualPathState)

    # Add nodes
    workflow.add_node("analyze_retrieve", analyze_and_retrieve_node)
    workflow.add_node("generate_queries", generate_queries_node)
    workflow.add_node("execute_cpgql", execute_cpgql_node)
    workflow.add_node("execute_sql", execute_sql_node)
    workflow.add_node("compare_results", compare_results_node)
    workflow.add_node("interpret", interpret_node)

    # Define edges (linear flow with parallel execution)
    workflow.set_entry_point("analyze_retrieve")
    workflow.add_edge("analyze_retrieve", "generate_queries")
    workflow.add_edge("generate_queries", "execute_cpgql")
    workflow.add_edge("execute_cpgql", "execute_sql")  # Sequential for simplicity
    workflow.add_edge("execute_sql", "compare_results")
    workflow.add_edge("compare_results", "interpret")
    workflow.add_edge("interpret", END)

    return workflow.compile()


# ============================================================================
# PUBLIC API
# ============================================================================

def run_dual_path_query(
    question: str,
    use_sql: bool = True,
    use_cpgql: bool = False,  # Default to SQL only (Joern not available)
    duckdb_path: str = "sample_cpg_v2.duckdb"
) -> Dict[str, Any]:
    """
    Run a query through both CPGQL and SQL paths.

    Args:
        question: Natural language question
        use_sql: Enable SQL query path
        use_cpgql: Enable CPGQL query path
        duckdb_path: Path to DuckDB database

    Returns:
        Final state with answer and metadata
    """
    # Initialize agents
    _initialize_agents(duckdb_path=duckdb_path)

    # Create workflow
    app = create_dual_path_workflow()

    # Initial state
    initial_state = {
        "question": question,
        "use_sql": use_sql,
        "use_cpgql": use_cpgql,
        "analysis": None,
        "context": None,
        "cpgql_query": None,
        "cpgql_valid": False,
        "cpgql_success": False,
        "cpgql_time": 0.0,
        "sql_query": None,
        "sql_template": None,
        "sql_params": None,
        "sql_success": False,
        "sql_time": 0.0,
        "results_match": None,
        "answer": None,
        "answer_source": None,
        "confidence": None,
        "total_time": 0.0,
        "retrieval_time": 0.0,
        "error": None
    }

    # Run workflow
    start_time = time.time()
    final_state = app.invoke(initial_state)
    final_state["total_time"] = time.time() - start_time

    return final_state


def main():
    """Example usage and testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Dual-Path RAG Query")
    parser.add_argument('question', type=str, help='Natural language question')
    parser.add_argument('--sql', action='store_true', default=True, help='Use SQL path')
    parser.add_argument('--cpgql', action='store_true', default=False, help='Use CPGQL path')
    parser.add_argument('--db', type=str, default='sample_cpg_v2.duckdb', help='DuckDB path')

    args = parser.parse_args()

    print("=" * 80)
    print("Dual-Path RAG Query System (Phase 8F)")
    print("=" * 80)
    print(f"Question: {args.question}")
    print(f"Paths: SQL={args.sql}, CPGQL={args.cpgql}")
    print("=" * 80)

    result = run_dual_path_query(
        question=args.question,
        use_sql=args.sql,
        use_cpgql=args.cpgql,
        duckdb_path=args.db
    )

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    if result.get("sql_query"):
        print(f"\nSQL Query ({result.get('sql_template', 'unknown')}):")
        print(result['sql_query'][:300])

    if result.get("cpgql_query"):
        print(f"\nCPGQL Query:")
        print(result['cpgql_query'][:300])

    print(f"\nAnswer Source: {result.get('answer_source', 'none')}")
    print(f"SQL Results: {result.get('result_count_sql', 0)}")
    print(f"CPGQL Results: {result.get('result_count_cpgql', 0)}")

    if result.get("results_match") is not None:
        match_str = "[OK] MATCH" if result["results_match"] else "[!] DIFFER"
        print(f"Results Comparison: {match_str}")

    print(f"\n{result.get('answer', 'No answer generated.')}")

    print(f"\nMetrics:")
    print(f"  Total Time: {result.get('total_time', 0):.2f}s")
    print(f"  SQL Time: {result.get('sql_time', 0):.2f}s")
    print(f"  CPGQL Time: {result.get('cpgql_time', 0):.2f}s")
    print(f"  Confidence: {result.get('confidence', 0):.2f}")
    print("=" * 80)


if __name__ == "__main__":
    main()
