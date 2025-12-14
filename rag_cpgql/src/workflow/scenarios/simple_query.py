# ============================================================================
# DOMAIN-AGNOSTIC MODULE
# ============================================================================
# This module MUST NOT contain hardcoded domain-specific code.
# All domain-specific logic should be retrieved from:
#   - src/domains/{domain}/plugin.py via DomainRegistry
#   - src/workflow/_plugin_helpers.py helper functions
#   - src/prompts/prompt_registry.py for prompts
#
# See: docs/AGENT_MIGRATION_GUIDE.md for migration patterns
# ============================================================================
"""
Scenario: Simple Query - Basic CPGQL question answering.

Provides a simplified workflow for basic code questions:
- Direct CPGQL query generation
- Single-pass execution
- Natural language answer synthesis

This is a lightweight alternative to full multi-scenario routing
for simple, direct questions about the codebase.
"""

import logging
import time
from typing import Dict, List, Any, Optional

from src.workflow.state import MultiScenarioState
from src.workflow.scenarios._language_utils import add_language_instruction
from src.services.cpg_query_service import CPGQueryService
from src.llm.llm_interface_compat import LLMInterface
from src.prompts.prompt_registry import get_global_registry

logger = logging.getLogger(__name__)


# ============================================================================
# INTENT DETECTION
# ============================================================================

SIMPLE_QUERY_KEYWORDS = [
    # Basic questions
    'what', 'where', 'how many', 'list', 'show', 'find', 'get',
    # Simple code queries
    'function', 'method', 'class', 'variable', 'parameter',
    'return type', 'signature', 'definition',
    # Direct queries
    'all functions', 'all methods', 'all classes',
    'count', 'number of',
]


def is_simple_query(query: str) -> bool:
    """
    Detect if query is a simple, direct question.

    Simple queries are:
    - Short (< 100 chars typically)
    - Ask for basic code facts
    - Don't require complex analysis

    Args:
        query: User's question

    Returns:
        True if query is simple and direct
    """
    query_lower = query.lower()

    # Check for simple query patterns
    for keyword in SIMPLE_QUERY_KEYWORDS:
        if keyword in query_lower:
            return True

    # Very short queries are likely simple
    if len(query) < 80 and '?' in query:
        return True

    return False


# ============================================================================
# QUERY GENERATION
# ============================================================================

def _generate_simple_cpgql(query: str) -> Optional[str]:
    """
    Generate a simple CPGQL query from natural language.

    Uses pattern matching for common query types.
    Falls back to LLM generation for complex queries.
    """
    query_lower = query.lower()

    # Pattern-based generation for common queries
    if 'all function' in query_lower or 'list function' in query_lower:
        return "SELECT name, filename, line_number FROM nodes_method LIMIT 50"

    if 'all method' in query_lower or 'list method' in query_lower:
        return "SELECT name, filename, line_number FROM nodes_method LIMIT 50"

    if 'how many function' in query_lower or 'count function' in query_lower:
        return "SELECT COUNT(*) as count FROM nodes_method"

    if 'how many method' in query_lower or 'count method' in query_lower:
        return "SELECT COUNT(*) as count FROM nodes_method"

    # Extract function name if mentioned
    import re
    func_match = re.search(r"function\s+['\"]?(\w+)['\"]?", query_lower)
    if func_match:
        func_name = func_match.group(1)
        return f"SELECT name, filename, signature, line_number FROM nodes_method WHERE name = '{func_name}' LIMIT 10"

    # Find function by pattern
    if 'find' in query_lower and ('function' in query_lower or 'method' in query_lower):
        # Extract pattern from query
        pattern_match = re.search(r"(?:named?|called?|like)\s+['\"]?(\w+)['\"]?", query_lower)
        if pattern_match:
            pattern = pattern_match.group(1)
            return f"SELECT name, filename, signature, line_number FROM nodes_method WHERE name LIKE '%{pattern}%' LIMIT 20"

    # Default: search for relevant methods
    return None


def _generate_cpgql_with_llm(query: str, llm: LLMInterface) -> str:
    """Generate CPGQL using LLM when pattern matching fails."""
    registry = get_global_registry()

    prompt_vars = {
        'query': query,
        'schema_info': '''
Available tables:
- nodes_method (id, name, full_name, filename, signature, line_number, line_number_end, code)
- nodes_call (id, name, code, line_number, method_full_name)
- edges_call (src_id, dst_id, src_name, dst_name)
''',
    }

    try:
        prompts = registry.get_agent_prompt('cpgql_generator', **prompt_vars)
        sql = llm.generate(prompts['system'], prompts['user'])

        # Clean up response
        sql = sql.strip()
        if sql.startswith('```'):
            sql = sql.split('```')[1]
            if sql.startswith('sql'):
                sql = sql[3:]
        sql = sql.strip()

        return sql
    except Exception as e:
        logger.warning(f"LLM generation failed: {e}")
        return "SELECT name, filename, line_number FROM nodes_method LIMIT 20"


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

def simple_query_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    Simple Query Workflow - Basic CPGQL question answering.

    Provides fast, direct answers for simple code questions:
    1. Generate CPGQL query from natural language
    2. Execute query on CPG
    3. Synthesize natural language answer

    Returns state with answer and evidence.
    """
    logger.info("Executing simple query workflow")
    start_time = time.time()

    try:
        query_text = state['query']

        # Step 1: Generate CPGQL query
        cpgql_query = _generate_simple_cpgql(query_text)

        if not cpgql_query:
            # Fall back to LLM generation
            llm = LLMInterface()
            cpgql_query = _generate_cpgql_with_llm(query_text, llm)

        logger.info(f"Generated SQL: {cpgql_query[:100]}...")

        # Step 2: Execute query
        results = []
        with CPGQueryService() as cpg:
            try:
                results = cpg.execute_query(cpgql_query)
                logger.info(f"Query returned {len(results) if results else 0} results")
            except Exception as e:
                logger.warning(f"Query execution failed: {e}")
                state['error'] = f"Query execution failed: {e}"

        # Step 3: Build evidence list
        evidence = []
        retrieved_functions = []

        if results:
            for r in results[:20]:
                name = r.get('name', r.get('function_name', ''))
                filename = r.get('filename', '')
                line = r.get('line_number', '')

                if name:
                    retrieved_functions.append(name)
                    evidence.append(f"{name} ({filename}:{line})")

        state['retrieved_functions'] = retrieved_functions
        state['evidence'] = evidence
        state['methods'] = results if results else []

        # Step 4: Generate answer
        if results:
            try:
                llm = LLMInterface()
                registry = get_global_registry()

                # Build results context
                results_text = "\n".join([
                    f"- {r.get('name', 'unknown')} in {r.get('filename', 'unknown')}:{r.get('line_number', '?')}"
                    for r in results[:15]
                ])

                prompt_vars = {
                    'query': query_text,
                    'results': results_text,
                    'count': len(results),
                }

                prompts = registry.get_agent_prompt('interpreter', **prompt_vars)
                answer = llm.generate(
                    add_language_instruction(prompts['system'], state),
                    prompts['user']
                )

            except Exception as e:
                logger.warning(f"LLM answer generation failed: {e}")
                # Fallback answer
                answer = f"Found {len(results)} results:\n" + "\n".join(evidence[:10])
        else:
            answer = "No results found for your query. Try rephrasing or asking a more specific question."

        state['answer'] = answer
        state['metadata'] = {
            'cpgql_query': cpgql_query,
            'result_count': len(results) if results else 0,
            'execution_time': time.time() - start_time,
            'scenario': 'simple_query',
        }

    except Exception as e:
        logger.error(f"Simple query workflow failed: {e}")
        state['error'] = str(e)
        state['answer'] = f"Error processing query: {e}"
        if 'retrieved_functions' not in state:
            state['retrieved_functions'] = []

    return state


__all__ = ['simple_query_workflow', 'is_simple_query']
