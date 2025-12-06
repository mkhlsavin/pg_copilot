"""
Control Flow Mode Nodes - Phase 7

Nodes for the control flow analysis path of the LangGraph workflow.
Handles explain-logic type questions that require call chain analysis.
"""

import logging
from langchain_core.messages import AIMessage

from src.workflow._state import RAGCPGQLState
from src.workflow._components import (
    get_control_flow_generator,
    get_call_chain_analyzer,
    get_logic_synthesizer,
    get_joern_client,
)
from src.execution.scala_parser import parse_scala_output

logger = logging.getLogger(__name__)


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
