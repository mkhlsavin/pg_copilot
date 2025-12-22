"""
Control Flow Mode Nodes - Phase 7 (Migrated to SQL/DuckDB)

Nodes for the control flow analysis path of the LangGraph workflow.
Handles explain-logic type questions that require call chain analysis.

Migrated from Joern/CPGQL to DuckDB/SQL execution.
"""

import logging
from typing import Optional
from langchain_core.messages import AIMessage

from src.workflow._state import RAGCPGQLState
from src.workflow._components import (
    get_control_flow_generator,
    get_call_chain_analyzer,
    get_logic_synthesizer,
)

logger = logging.getLogger(__name__)


def _get_cpg_db_path() -> Optional[str]:
    """Get the path to the CPG DuckDB database."""
    try:
        from src.config import get_config
        config = get_config()
        return config.get('cpg_db_path', 'cpg.duckdb')
    except Exception:
        return 'cpg.duckdb'


def _execute_sql_query(query: str, db_path: Optional[str] = None) -> list:
    """
    Execute SQL query on DuckDB CPG database.

    Args:
        query: SQL query to execute
        db_path: Path to DuckDB database

    Returns:
        List of result dictionaries
    """
    if not query or not query.strip():
        return []

    try:
        import duckdb

        db_path = db_path or _get_cpg_db_path()
        conn = duckdb.connect(db_path, read_only=True)

        result = conn.execute(query).fetchdf()
        conn.close()

        # Convert DataFrame to list of dicts
        return result.to_dict('records')

    except Exception as e:
        logger.warning(f"SQL execution failed: {e}")
        return []


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
    """Phase 7: Generate control flow SQL queries."""
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
            content=f"Generated 3 control flow SQL queries: entry_point, keyword_methods, call_graph"
        ))

        logger.info(f"Control flow SQL queries generated")

    except Exception as e:
        logger.error(f"Control flow generation error: {e}", exc_info=True)
        state["error"] = f"Control flow generation failed: {str(e)}"

    return state


def control_flow_execute_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Phase 7: Execute control flow SQL queries on DuckDB CPG."""
    logger.info("=== CONTROL FLOW EXECUTOR (SQL) ===")

    try:
        queries = state.get("control_flow_queries", {})
        if not queries:
            logger.warning("No control flow queries to execute")
            state["error"] = "No control flow queries generated"
            return state

        # Get database path from state or config
        db_path = state.get('cpg_db_path') or _get_cpg_db_path()

        # Execute entry point query
        logger.info("Executing entry point SQL query...")
        entry_query = queries.get('entry_point_query', '')
        entry_result = _execute_sql_query(entry_query, db_path)
        if entry_result:
            entry_result = entry_result[0] if len(entry_result) == 1 else entry_result
        logger.info(f"Entry point result: {type(entry_result)}, found: {bool(entry_result)}")

        # Execute keyword methods query
        logger.info("Executing keyword methods SQL query...")
        keyword_query = queries.get('keyword_methods_query', '')
        keyword_result = _execute_sql_query(keyword_query, db_path)
        if not isinstance(keyword_result, list):
            keyword_result = [keyword_result] if keyword_result else []
        logger.info(f"Keyword methods result: {len(keyword_result)} methods found")

        # Execute call graph query
        logger.info("Executing call graph SQL query...")
        graph_query = queries.get('call_graph_query', '')
        graph_result = _execute_sql_query(graph_query, db_path)
        if not isinstance(graph_result, list):
            graph_result = [graph_result] if graph_result else []
        logger.info(f"Call graph result: {len(graph_result)} entries found")

        state["entry_point_result"] = entry_result
        state["keyword_methods_result"] = keyword_result
        state["call_graph_result"] = graph_result

        state["messages"].append(AIMessage(
            content=f"Executed 3 SQL queries on DuckDB CPG"
        ))

        logger.info(f"Control flow SQL queries executed successfully")

    except Exception as e:
        logger.error(f"Control flow execution error: {e}", exc_info=True)
        state["error"] = f"Control flow execution failed: {str(e)}"

    return state


def control_flow_analyze_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Phase 7: Analyze call chain from SQL results."""
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
