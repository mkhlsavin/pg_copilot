"""
Scenario 14: Debugging Support with Graph Analysis

Provides debugging-related code analysis including:
- Finding elog/ereport logging calls
- Locating assertion macros
- Tracing instrumentation points
- Explain/query plan analysis
- Stack trace and backtrace functions
"""

import logging
import re
from typing import Dict, List, Any, Optional

from src.services.cpg_query_service import CPGQueryService
from src.llm.llm_interface_compat import LLMInterface
from src.workflow.state import MultiScenarioState
from src.domains import DomainRegistry
from src.prompts.prompt_registry import get_global_registry

logger = logging.getLogger(__name__)


def _get_debug_patterns_from_plugin() -> Dict[str, Dict[str, List[str]]]:
    """Get debug function patterns from the active domain plugin."""
    # Default patterns if plugin not available
    default = {
        'logging': {
            'functions': ['elog', 'ereport', 'errcode', 'errmsg', 'errdetail', 'errhint', 'errcontext'],
            'keywords': ['elog', 'ereport', 'log', 'error message', 'warning', 'notice', 'info'],
        },
        'assertion': {
            'functions': ['Assert', 'AssertMacro', 'AssertArg', 'AssertState', 'Insist'],
            'keywords': ['assert', 'assertion', 'invariant', 'check'],
        },
        'trace': {
            'functions': ['trace_', 'TRACE_', 'pg_trace', 'TraceFlags', 'MemoryContextStats'],
            'keywords': ['trace', 'tracing', 'instrument', 'profil'],
        },
        'explain': {
            'functions': ['ExplainQuery', 'ExplainState', 'ExplainPrintPlan', 'ExplainProperty'],
            'keywords': ['explain', 'query plan', 'execution plan', 'plan tree'],
        },
        'debug_output': {
            'functions': ['DEBUG1', 'DEBUG2', 'DEBUG3', 'DEBUG4', 'DEBUG5', 'LOG', 'WARNING'],
            'keywords': ['debug level', 'debug output', 'verbose'],
        },
        'stack_trace': {
            'functions': ['errbacktrace', 'pg_backtrace', 'stack_', 'gdb', 'core_dump'],
            'keywords': ['stack trace', 'backtrace', 'call stack', 'stack dump'],
        },
        'breakpoint': {
            'functions': ['BreakpointCreate', 'pg_breakpoint', 'SetBreakpoint'],
            'keywords': ['breakpoint', 'debug point', 'stop point'],
        },
    }

    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_debug_functions'):
            plugin_funcs = domain.get_debug_functions()
            # Merge plugin functions with default keywords
            for category, funcs in plugin_funcs.items():
                if category in default:
                    default[category]['functions'] = funcs
                else:
                    # New category from plugin - create entry with functions as keywords
                    default[category] = {
                        'functions': funcs,
                        'keywords': [f.lower() for f in funcs[:3]],
                    }
    except Exception as e:
        logger.debug(f"Could not get debug patterns from plugin: {e}")

    return default


def _get_error_levels_from_plugin() -> List[str]:
    """Get error levels from the active domain plugin."""
    default = ['ERROR', 'WARNING', 'NOTICE', 'INFO', 'LOG',
               'DEBUG1', 'DEBUG2', 'DEBUG3', 'DEBUG4', 'DEBUG5', 'FATAL', 'PANIC']
    try:
        domain = DomainRegistry.get_active_or_none()
        if domain and hasattr(domain, 'get_error_levels'):
            return domain.get_error_levels()
    except Exception:
        pass
    return default


# Get patterns from plugin (cached at module load time for performance)
DEBUG_FUNCTION_PATTERNS = _get_debug_patterns_from_plugin()
ERROR_LEVELS = _get_error_levels_from_plugin()


def detect_debug_intent(query: str) -> str:
    """
    Detect what type of debugging query this is.

    Args:
        query: User's debugging-related query

    Returns:
        Debug intent category (logging, assertion, trace, explain, etc.)
    """
    query_lower = query.lower()

    scores = {}
    for intent, patterns in DEBUG_FUNCTION_PATTERNS.items():
        score = sum(1 for kw in patterns['keywords'] if kw in query_lower)
        # Also check for function names directly mentioned
        for func in patterns['functions']:
            if func.lower() in query_lower:
                score += 2  # Function name mentions are weighted higher
        if score > 0:
            scores[intent] = score

    if scores:
        return max(scores, key=scores.get)
    return 'generic'


def extract_error_level(query: str) -> Optional[str]:
    """Extract specific error level from query if mentioned."""
    query_upper = query.upper()
    for level in ERROR_LEVELS:
        if level in query_upper:
            return level
    return None


def debugging_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    Scenario 14: Debugging Support with Graph Analysis

    Provides debugging code analysis by:
    1. Detecting debug query intent (logging, assertion, trace, etc.)
    2. Querying CPG for relevant debugging constructs
    3. Analyzing debug function usage patterns
    4. Generating helpful debugging information with LLM

    Returns debugging information with code locations and usage patterns.
    """
    logger.info("Executing debugging workflow with intent detection")

    # Track debugging insights
    debug_insights = {
        'intent': None,
        'functions_found': [],
        'error_level': None,
        'call_sites': [],
        'patterns': []
    }

    try:
        query_text = state['query']
        query_lower = query_text.lower()

        # Detect debug intent
        intent = detect_debug_intent(query_text)
        debug_insights['intent'] = intent
        logger.info(f"Detected debug intent: {intent}")

        # Extract error level if specified
        error_level = extract_error_level(query_text)
        debug_insights['error_level'] = error_level

        with CPGQueryService() as cpg:
            results = []

            if intent == 'logging':
                results = _find_logging_calls(cpg, query_text, error_level)
            elif intent == 'assertion':
                results = _find_assertions(cpg, query_text)
            elif intent == 'trace':
                results = _find_trace_points(cpg, query_text)
            elif intent == 'explain':
                results = _find_explain_code(cpg, query_text)
            elif intent == 'stack_trace':
                results = _find_stack_trace_functions(cpg, query_text)
            elif intent == 'debug_output':
                results = _find_debug_output(cpg, query_text)
            else:
                # Generic debug search
                results = _generic_debug_search(cpg, query_text)

            debug_insights['functions_found'] = results

        # Generate answer with LLM using registry
        llm = LLMInterface()
        registry = get_global_registry()

        # Build context from results
        results_context = ""
        if results:
            results_context = "\n\nFound debugging functions:\n"
            for r in results[:20]:
                name = r.get('name', r.get('function_name', 'unknown'))
                filename = r.get('filename', 'unknown')
                line = r.get('line_number', '?')
                code = r.get('code', '')[:100] if r.get('code') else ''
                results_context += f"- {name} ({filename}:{line})"
                if code:
                    results_context += f"\n  Code: {code}..."
                results_context += "\n"

        # Get prompts from registry
        prompt_vars = {
            'domain': 'PostgreSQL',
            'query': state['query'],
            'debug_intent': intent,
            'error_level': error_level if error_level else 'Not specified',
            'functions_found': results_context if results_context else 'No functions found',
            'call_sites': chr(10).join([f"- {r.get('name', 'unknown')} at {r.get('filename', '?')}:{r.get('line_number', '?')}" for r in results[:10]]) if results else 'None',
            'patterns_detected': intent
        }

        prompts = registry.get_agent_prompt('debugging_expert', **prompt_vars)

        debug_prompt = f"""{prompts['system']}

{prompts['user']}

{results_context}

Provide:
1. Explanation of the debugging pattern/function requested
2. Key code locations found (with file:line references)
3. How to use these debugging facilities
4. Related debugging techniques

Be specific about PostgreSQL debugging patterns like elog(), ereport(), Assert macros, etc.
"""

        answer = llm.generate(prompts['system'], debug_prompt)

        # Build evidence list
        evidence = [
            f"Debug intent: {intent}",
            f"Functions found: {len(results)}",
        ]
        if error_level:
            evidence.append(f"Error level: {error_level}")

        if results:
            sample_funcs = list(set(r.get('name', r.get('function_name', ''))[:30] for r in results[:5]))
            evidence.append(f"Sample functions: {', '.join(sample_funcs)}")

        state['methods'] = results
        state['answer'] = answer
        state['evidence'] = evidence
        state['metadata'] = {
            'method_count': len(results),
            'debug_intent': intent,
            'error_level': error_level,
            'graph_methods_enabled': True,
            'debug_insights': debug_insights
        }

    except Exception as e:
        logger.error(f"Debugging workflow failed: {e}")
        state['error'] = str(e)
        state['answer'] = f"Error in debugging analysis: {e}"

    return state


def _find_logging_calls(cpg: CPGQueryService, query: str, error_level: Optional[str] = None) -> List[Dict]:
    """Find elog/ereport logging calls."""
    query_sql = """
        SELECT DISTINCT
            nc.id,
            nc.name AS function_name,
            nc.code,
            nc.line_number,
            m.name AS caller_name,
            m.filename
        FROM nodes_call nc
        LEFT JOIN nodes_method m ON nc.method_full_name = m.full_name
        WHERE (nc.name LIKE '%elog%' OR nc.name LIKE '%ereport%'
               OR nc.name = 'errcode' OR nc.name = 'errmsg'
               OR nc.name = 'errdetail' OR nc.name = 'errhint')
    """

    if error_level:
        query_sql += f" AND (nc.code LIKE '%{error_level}%' OR nc.name LIKE '%{error_level}%')"

    query_sql += " ORDER BY m.filename, nc.line_number LIMIT 50"

    try:
        results = cpg.execute_query(query_sql)
        logger.info(f"Found {len(results) if results else 0} logging calls")
        return results if results else []
    except Exception as e:
        logger.warning(f"Error finding logging calls: {e}")
        return []


def _find_assertions(cpg: CPGQueryService, query: str) -> List[Dict]:
    """Find assertion macros in the codebase."""
    query_sql = """
        SELECT DISTINCT
            nc.id,
            nc.name AS function_name,
            nc.code,
            nc.line_number,
            m.name AS caller_name,
            m.filename
        FROM nodes_call nc
        LEFT JOIN nodes_method m ON nc.method_full_name = m.full_name
        WHERE (nc.name LIKE 'Assert%'
               OR nc.name IN ('Assert', 'AssertMacro', 'AssertArg', 'AssertState', 'Insist')
               OR nc.name LIKE '%assert%')
        ORDER BY m.filename, nc.line_number
        LIMIT 50
    """

    try:
        results = cpg.execute_query(query_sql)
        logger.info(f"Found {len(results) if results else 0} assertions")
        return results if results else []
    except Exception as e:
        logger.warning(f"Error finding assertions: {e}")
        return []


def _find_trace_points(cpg: CPGQueryService, query: str) -> List[Dict]:
    """Find trace instrumentation points."""
    query_sql = """
        SELECT DISTINCT
            nc.id,
            nc.name AS function_name,
            nc.code,
            nc.line_number,
            m.name AS caller_name,
            m.filename
        FROM nodes_call nc
        LEFT JOIN nodes_method m ON nc.method_full_name = m.full_name
        WHERE (nc.name LIKE '%trace%'
               OR nc.name LIKE 'TRACE%'
               OR nc.name LIKE '%Trace%'
               OR nc.name LIKE '%MemoryContextStats%'
               OR nc.name LIKE '%pg_trace%')
        ORDER BY m.filename, nc.line_number
        LIMIT 50
    """

    try:
        results = cpg.execute_query(query_sql)
        logger.info(f"Found {len(results) if results else 0} trace points")
        return results if results else []
    except Exception as e:
        logger.warning(f"Error finding trace points: {e}")
        return []


def _find_explain_code(cpg: CPGQueryService, query: str) -> List[Dict]:
    """Find EXPLAIN and query plan related code."""
    query_sql = """
        SELECT DISTINCT
            m.id,
            m.name,
            m.full_name,
            m.filename,
            m.signature,
            m.line_number,
            m.line_number_end
        FROM nodes_method m
        WHERE (m.name LIKE '%Explain%'
               OR m.name LIKE '%explain%'
               OR m.name LIKE '%Plan%'
               OR m.full_name LIKE '%explain%')
        ORDER BY
            CASE WHEN m.name LIKE 'Explain%' THEN 0 ELSE 1 END,
            m.filename, m.line_number
        LIMIT 50
    """

    try:
        results = cpg.execute_query(query_sql)
        logger.info(f"Found {len(results) if results else 0} explain-related functions")
        return results if results else []
    except Exception as e:
        logger.warning(f"Error finding explain code: {e}")
        return []


def _find_stack_trace_functions(cpg: CPGQueryService, query: str) -> List[Dict]:
    """Find stack trace and backtrace related functions."""
    query_sql = """
        SELECT DISTINCT
            m.id,
            m.name,
            m.full_name,
            m.filename,
            m.signature,
            m.line_number
        FROM nodes_method m
        WHERE (m.name LIKE '%backtrace%'
               OR m.name LIKE '%stack%'
               OR m.name LIKE '%errbacktrace%'
               OR m.name LIKE '%core_dump%'
               OR m.name LIKE '%gdb%')
        ORDER BY m.filename, m.line_number
        LIMIT 50
    """

    try:
        results = cpg.execute_query(query_sql)
        logger.info(f"Found {len(results) if results else 0} stack trace functions")
        return results if results else []
    except Exception as e:
        logger.warning(f"Error finding stack trace functions: {e}")
        return []


def _find_debug_output(cpg: CPGQueryService, query: str) -> List[Dict]:
    """Find debug output level usage."""
    query_sql = """
        SELECT DISTINCT
            nc.id,
            nc.name AS function_name,
            nc.code,
            nc.line_number,
            m.name AS caller_name,
            m.filename
        FROM nodes_call nc
        LEFT JOIN nodes_method m ON nc.method_full_name = m.full_name
        WHERE (nc.code LIKE '%DEBUG1%'
               OR nc.code LIKE '%DEBUG2%'
               OR nc.code LIKE '%DEBUG3%'
               OR nc.code LIKE '%DEBUG4%'
               OR nc.code LIKE '%DEBUG5%'
               OR nc.name = 'elog')
        ORDER BY m.filename, nc.line_number
        LIMIT 50
    """

    try:
        results = cpg.execute_query(query_sql)
        logger.info(f"Found {len(results) if results else 0} debug output calls")
        return results if results else []
    except Exception as e:
        logger.warning(f"Error finding debug output: {e}")
        return []


def _generic_debug_search(cpg: CPGQueryService, query: str) -> List[Dict]:
    """Generic search for debugging-related code."""
    # Extract potential function names from query
    words = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]+)\b', query)
    debug_terms = [w for w in words if len(w) >= 3 and w.lower() not in
                   {'find', 'show', 'list', 'all', 'the', 'for', 'how', 'where', 'what', 'functions'}]

    if debug_terms:
        # Search for specific terms
        term_conditions = ' OR '.join([f"m.name LIKE '%{t}%'" for t in debug_terms[:3]])
        query_sql = f"""
            SELECT DISTINCT
                m.id,
                m.name,
                m.full_name,
                m.filename,
                m.signature,
                m.line_number
            FROM nodes_method m
            WHERE ({term_conditions})
            ORDER BY m.filename, m.line_number
            LIMIT 50
        """
    else:
        # Default: search common debug functions
        query_sql = """
            SELECT DISTINCT
                m.id,
                m.name,
                m.full_name,
                m.filename,
                m.signature,
                m.line_number
            FROM nodes_method m
            WHERE (m.name LIKE '%debug%'
                   OR m.name LIKE '%Debug%'
                   OR m.name LIKE '%elog%'
                   OR m.name LIKE '%Assert%')
            ORDER BY m.filename, m.line_number
            LIMIT 50
        """

    try:
        results = cpg.execute_query(query_sql)
        logger.info(f"Generic debug search found {len(results) if results else 0} functions")
        return results if results else []
    except Exception as e:
        logger.warning(f"Error in generic debug search: {e}")
        return []


__all__ = ['debugging_workflow', 'detect_debug_intent']
