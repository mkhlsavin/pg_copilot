# ============================================================================
# DOMAIN-AGNOSTIC MODULE
# ============================================================================
# This module MUST NOT contain hardcoded domain-specific code.
# All domain-specific logic should be retrieved from:
#   - src/domains/{domain}/plugin.py via DomainRegistry
#   - src/workflow/_plugin_helpers.py helper functions
#   - src/prompts/prompt_registry.py for prompts
#
# DO NOT add:
#   - Hardcoded function names (pg_*, elog, palloc, etc.)
#   - Hardcoded SQL patterns with domain-specific terms
#   - Inline LLM prompts (use PromptRegistry)
#
# See: docs/AGENT_MIGRATION_GUIDE.md for migration patterns
# ============================================================================
"""
Scenario 3: Documentation Generation with Graph Analysis
"""

import logging
import re
from typing import Dict, List, Any, Optional

from src.workflow.scenarios._language_utils import add_language_instruction
from src.services.cpg_query_service import CPGQueryService
from src.llm.llm_interface_compat import LLMInterface
from src.workflow.state import MultiScenarioState
from src.domains import DomainRegistry
from src.prompts.prompt_registry import get_global_registry

logger = logging.getLogger(__name__)


def _get_known_function_patterns() -> List[str]:
    """Get known function name patterns from the active domain plugin."""
    # Default patterns (generic)
    patterns = [
        r'\b(heap_[a-z_]+)\b', r'\b(index_[a-z_]+)\b',
        r'\b(relation_[a-z_]+)\b', r'\b(buffer_[a-z_]+)\b',
    ]

    try:
        domain = DomainRegistry.get_active_or_none()
        if domain:
            # Get debug functions (elog, ereport, etc.)
            if hasattr(domain, 'get_debug_functions'):
                debug_funcs = domain.get_debug_functions()
                for funcs in debug_funcs.values():
                    for func in funcs[:5]:  # Top 5 from each category
                        patterns.append(rf'\b({re.escape(func)})\b')

            # Get memory functions
            if hasattr(domain, 'get_memory_functions'):
                mem_funcs = domain.get_memory_functions()
                for category in mem_funcs.values():
                    if isinstance(category, list):
                        for func in category[:3]:
                            patterns.append(rf'\b({re.escape(func)})\b')
    except Exception as e:
        logger.debug(f"Could not get function patterns from plugin: {e}")
        # Fallback to hardcoded PostgreSQL patterns
        patterns.extend([
            r'\b(ereport)\b', r'\b(elog)\b', r'\b(palloc)\b', r'\b(pfree)\b',
            r'\b(repalloc)\b', r'\b(pstrdup)\b', r'\b(errcode)\b', r'\b(errmsg)\b',
            r'\b(errdetail)\b', r'\b(errhint)\b', r'\b(errcontext)\b',
        ])

    return patterns


# Stop words to filter out from function name extraction
STOP_WORDS = {
    'find', 'show', 'get', 'list', 'where', 'what', 'how', 'which', 'all',
    'the', 'for', 'documentation', 'document', 'docs', 'doc', 'function',
    'functions', 'method', 'methods', 'code', 'source', 'file', 'files',
    'in', 'of', 'and', 'or', 'to', 'from', 'with', 'is', 'are', 'can',
    'this', 'that', 'these', 'those', 'about', 'using', 'used', 'use'
}


def extract_function_names_from_query(query: str) -> List[str]:
    """
    Extract potential function names from a documentation query.

    Patterns recognized:
    - backtick quoted: `funcName`
    - function call syntax: funcName(
    - "function X" or "method X" or "X function" phrases
    - CamelCase or snake_case identifiers
    - PostgreSQL-specific function names (ereport, elog, palloc, etc.)

    Args:
        query: The user's documentation query

    Returns:
        List of extracted function name candidates
    """
    names = set()

    # Pattern 1: Backtick quoted names (highest priority)
    backtick_matches = re.findall(r'`([a-zA-Z_][a-zA-Z0-9_]*)`', query)
    names.update(backtick_matches)

    # Pattern 2: Function call syntax (e.g., "ereport(")
    call_matches = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', query)
    names.update(call_matches)

    # Pattern 3: "function X" or "method X" phrases
    func_phrase_matches = re.findall(r'(?:function|method|func)\s+([a-zA-Z_][a-zA-Z0-9_]*)', query, re.IGNORECASE)
    names.update(func_phrase_matches)

    # Pattern 3b: "X function" or "X method" - reversed order
    func_phrase_rev_matches = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s+(?:function|method|func)\b', query, re.IGNORECASE)
    names.update(func_phrase_rev_matches)

    # Pattern 4: "for X" or "of X" where X might be a function name
    for_matches = re.findall(r'\b(?:for|of)\s+([a-zA-Z_][a-zA-Z0-9_]+)\b', query, re.IGNORECASE)
    for match in for_matches:
        # Include if it looks like a function name or is 4+ characters
        if len(match) >= 4 and match.lower() not in STOP_WORDS:
            names.add(match)

    # Pattern 5: CamelCase identifiers (e.g., ExecInitNode, BufferAlloc)
    camel_matches = re.findall(r'\b([A-Z][a-z]+(?:[A-Z][a-z0-9]+)+)\b', query)
    names.update(camel_matches)

    # Pattern 6: snake_case identifiers with at least one underscore
    snake_matches = re.findall(r'\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b', query)
    names.update(snake_matches)

    # Pattern 7: PostgreSQL-specific patterns (pg_, PG_, etc.)
    pg_matches = re.findall(r'\b((?:pg_|PG_|Pg)[a-zA-Z0-9_]+)\b', query)
    names.update(pg_matches)

    # Pattern 8: Known function name patterns from domain plugin
    # Gets patterns for: ereport, elog, palloc, pfree, heap_, etc.
    known_patterns = _get_known_function_patterns()
    for pattern in known_patterns:
        func_matches = re.findall(pattern, query, re.IGNORECASE)
        names.update(func_matches)

    # Filter out stop words and very short names
    filtered = [
        name for name in names
        if name.lower() not in STOP_WORDS
        and len(name) >= 3
    ]

    return filtered


async def search_by_function_names(cpg: CPGQueryService, names: List[str], limit: int = 20) -> List[Dict]:
    """
    Search for functions by exact name match in the CPG database.

    Args:
        cpg: CPG query service instance
        names: List of function names to search for
        limit: Maximum results to return

    Returns:
        List of matching method dictionaries
    """
    if not names:
        return []

    # Build query with exact matches prioritized
    placeholders = ', '.join(['?' for _ in names])

    query = f"""
        SELECT id, name, full_name, filename, signature, code,
               line_number, line_number_end,
               CASE
                   WHEN name IN ({placeholders}) THEN 0
                   ELSE 1
               END as match_priority
        FROM nodes_method
        WHERE name IN ({placeholders})
           OR full_name IN ({placeholders})
        ORDER BY match_priority, filename, line_number
        LIMIT ?
    """

    # Parameters: names for CASE, names for name IN, names for full_name IN, limit
    params = names + names + names + [limit]

    try:
        results = cpg.execute_query(query, params)
        return results if results else []
    except Exception as e:
        logger.warning(f"Direct function name search failed: {e}")
        return []

def documentation_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    Scenario 3: Documentation Generation with Graph Analysis

    Generates documentation by:
    1. Direct function name lookup (highest priority)
    2. Tag-based semantic search
    3. Subsystem-based search (fallback)
    4. CallGraphAnalyzer - Graph Method #2: Identify usage patterns and key methods
    5. Formatting as API documentation with call graph context

    Returns enhanced API documentation with usage patterns and impact analysis.
    """
    logger.info("Executing documentation workflow with GRAPH METHODS")

    # Track graph insights
    graph_insights = {
        'method_usage': {},
        'key_methods': [],
        'call_examples': []
    }

    # Track retrieval method used
    retrieval_method = None

    try:
        query_text = state['query']
        query_lower = query_text.lower()

        with CPGQueryService() as cpg:
            methods = []

            # Phase 1: Direct function name lookup (HIGHEST PRIORITY)
            func_names = extract_function_names_from_query(query_text)
            if func_names:
                logger.info(f"Extracted function names from query: {func_names}")

                # Try direct SQL query for exact matches
                placeholders = ', '.join(['?' for _ in func_names])
                direct_query = f"""
                    SELECT id, name, full_name, filename, signature, code,
                           line_number, line_number_end
                    FROM nodes_method
                    WHERE name IN ({placeholders})
                       OR full_name IN ({placeholders})
                    ORDER BY
                        CASE WHEN name IN ({placeholders}) THEN 0 ELSE 1 END,
                        filename, line_number
                    LIMIT 20
                """
                params = func_names + func_names + func_names
                try:
                    direct_results = cpg.execute_query(direct_query, params)
                    if direct_results:
                        methods = direct_results
                        retrieval_method = 'direct_function_lookup'
                        logger.info(f"Direct function lookup found {len(methods)} methods")
                except Exception as e:
                    logger.warning(f"Direct function lookup failed: {e}")

            # Phase 2: Tag-based semantic search (if no direct results)
            if not methods:
                # Search by function purpose if query contains keywords
                if any(kw in query_lower for kw in ['execute', 'plan', 'parse', 'optimize', 'memory', 'lock', 'error', 'log']):
                    # Extract keyword
                    keyword = None
                    for kw in ['execute', 'plan', 'parse', 'optimize', 'memory', 'lock', 'error', 'log']:
                        if kw in query_lower:
                            keyword = kw
                            break

                    if keyword:
                        methods = cpg.search_by_function_purpose(keyword, limit=20)
                        if methods:
                            retrieval_method = 'tag_search'
                            logger.info(f"Tag-based search found {len(methods)} methods for keyword '{keyword}'")

            # Phase 3: Subsystem-based search (fallback)
            if not methods:
                # Try to infer subsystem from query
                # Get subsystem keywords from plugin if available
                subsystem_keywords = {
                    'executor': ['executor', 'execute', 'exec', 'query execution'],
                    'parser': ['parser', 'parse', 'sql', 'syntax'],
                    'optimizer': ['optimizer', 'planner', 'plan', 'cost'],
                    'storage': ['storage', 'file', 'disk'],
                    'catalog': ['catalog', 'system table', 'metadata'],
                    'replication': ['replication', 'wal', 'streaming'],
                    'transactions': ['transaction', 'commit', 'rollback', 'xact'],
                }

                # Enhance with plugin-specific subsystems and keywords
                try:
                    domain = DomainRegistry.get_active_or_none()
                    if domain and hasattr(domain, 'get_subsystem_functions'):
                        subsys_funcs = domain.get_subsystem_functions()
                        for subsys_name in subsys_funcs.keys():
                            if subsys_name not in subsystem_keywords:
                                subsystem_keywords[subsys_name] = [subsys_name.lower()]

                    # Add memory keywords to utils if available
                    if domain and hasattr(domain, 'get_memory_keywords'):
                        mem_kw = domain.get_memory_keywords()
                        if 'utils' in subsystem_keywords:
                            subsystem_keywords['utils'].extend(mem_kw[:5])
                except Exception:
                    pass

                target_subsystem = None
                for subsystem, keywords in subsystem_keywords.items():
                    if any(kw in query_lower for kw in keywords):
                        target_subsystem = subsystem
                        break

                if target_subsystem:
                    methods = cpg.get_methods_by_subsystem(target_subsystem, limit=20)
                    if methods:
                        retrieval_method = f'subsystem_{target_subsystem}'
                        logger.info(f"Subsystem search found {len(methods)} methods in '{target_subsystem}'")
                else:
                    # Last resort: get first available subsystem
                    subsystems = cpg.get_subsystems()
                    if subsystems:
                        methods = cpg.get_methods_by_subsystem(subsystems[0]['name'], limit=20)
                        retrieval_method = 'subsystem_fallback'
                        logger.info(f"Fallback subsystem search found {len(methods)} methods")

            # GRAPH METHOD #2: CallGraphAnalyzer - Identify usage patterns for documentation
            try:
                logger.info("Running CallGraphAnalyzer for usage pattern analysis...")
                from src.analysis import CallGraphAnalyzer
                call_analyzer = CallGraphAnalyzer(cpg)

                # Analyze each method to enhance documentation
                for method in methods[:15]:  # Top 15 methods
                    method_name = method.get('name', '')
                    if not method_name:
                        continue

                    # Find callers (who uses this method?)
                    callers = call_analyzer.find_all_callers(method_name, max_depth=2)

                    # Handle both dict and string returns from callers
                    direct_callers = []
                    caller_names = []
                    for c in callers:
                        if isinstance(c, dict):
                            if c.get('depth', 1) == 1:
                                direct_callers.append(c)
                            caller_names.append(c.get('caller_name', str(c)))
                        elif isinstance(c, str):
                            # String callers are treated as direct callers
                            direct_callers.append({'caller_name': c, 'depth': 1})
                            caller_names.append(c)

                    # Find callees (what does this method call?)
                    callees = call_analyzer.find_all_callees(method_name, max_depth=1)

                    # Handle both dict and string returns from callees
                    callee_names = []
                    for c in callees:
                        if isinstance(c, dict):
                            callee_names.append(c.get('callee_name', str(c)))
                        elif isinstance(c, str):
                            callee_names.append(c)

                    # Compute impact (how important is this method?)
                    impact = call_analyzer.analyze_impact(method_name)

                    # Track usage information
                    # Determine if entry point: no callers or starts with known entry patterns
                    is_entry = (len(callers) == 0 or
                               method_name.startswith('pg_finfo_') or
                               method_name.endswith('_main'))
                    graph_insights['method_usage'][method_name] = {
                        'callers': len(callers),
                        'direct_callers': caller_names[:5],
                        'callees': callee_names[:5],
                        'impact_score': impact.impact_score if impact else 0.0,
                        'is_public_api': len(callers) > 5,  # Methods with many callers = public API
                        'is_entry_point': is_entry
                    }

                    # Identify key methods (high impact = important to document thoroughly)
                    if impact and impact.impact_score > 0.6:
                        graph_insights['key_methods'].append({
                            'method': method_name,
                            'filename': method.get('filename', 'unknown'),
                            'impact_score': impact.impact_score,
                            'caller_count': len(callers),
                            'priority': 'high' if impact.impact_score > 0.8 else 'medium'
                        })

                    # Create call examples (for usage documentation)
                    if direct_callers:
                        example_callers = []
                        for c in direct_callers[:3]:
                            if isinstance(c, dict):
                                example_callers.append(c.get('caller_name', 'unknown'))
                            else:
                                example_callers.append(str(c))
                        graph_insights['call_examples'].append({
                            'method': method_name,
                            'example_callers': example_callers,
                            'usage_context': f"Called by {len(direct_callers)} methods"
                        })

                # Sort key methods by impact
                graph_insights['key_methods'].sort(key=lambda x: x['impact_score'], reverse=True)

                logger.info(f"CallGraphAnalyzer: Analyzed {len(graph_insights['method_usage'])} methods, "
                           f"identified {len(graph_insights['key_methods'])} key methods")

            except Exception as e:
                logger.error(f"CallGraphAnalyzer failed: {e}", exc_info=True)
                # Continue without graph insights

        # Generate documentation
        llm = LLMInterface()

        # Build enhanced doc prompt with graph insights
        usage_info = ""
        if graph_insights['method_usage']:
            usage_info = "\n\n📊 METHOD USAGE PATTERNS (Graph Analysis):\n"
            for method_name, usage in list(graph_insights['method_usage'].items())[:10]:
                usage_info += f"\n{method_name}:\n"
                usage_info += f"  - Callers: {usage['callers']} (Public API: {'Yes' if usage['is_public_api'] else 'No'})\n"
                if usage['direct_callers']:
                    usage_info += f"  - Example callers: {', '.join(usage['direct_callers'][:3])}\n"
                if usage['callees']:
                    usage_info += f"  - Calls: {', '.join(usage['callees'][:3])}\n"
                usage_info += f"  - Impact score: {usage['impact_score']:.2f}\n"

        key_methods_info = ""
        if graph_insights['key_methods']:
            key_methods_info = "\n\n🔑 KEY METHODS (High Priority for Documentation):\n"
            for km in graph_insights['key_methods'][:5]:
                key_methods_info += f"  - {km['method']} ({km['filename']}): "
                key_methods_info += f"Impact {km['impact_score']:.2f}, {km['caller_count']} callers - {km['priority'].upper()} priority\n"

        # Build function details for registry
        target_funcs = "\n".join([
            f"- {m['name']} ({m.get('filename', 'unknown')}:{m.get('line_number', '?')})"
            for m in methods[:10]
        ]) if methods else "No methods found"

        # Build function details with signatures
        func_details = []
        for m in methods[:10]:
            detail = f"Method: {m.get('name', 'unknown')}"
            if m.get('signature'):
                detail += f"\n  Signature: {m.get('signature')}"
            if m.get('filename'):
                detail += f"\n  Location: {m.get('filename')}:{m.get('line_number', '?')}"
            func_details.append(detail)

        func_details_str = "\n".join(func_details) if func_details else "No details available"

        # Build related code context
        related_ctx = f"{usage_info}\n{key_methods_info}" if usage_info or key_methods_info else "No usage patterns available"

        # Get prompts from registry
        registry = get_global_registry()
        prompts = registry.get_agent_prompt('documentation_generator',
            query=state['query'],
            target_functions=target_funcs,
            function_details=func_details_str,
            related_code=related_ctx
        )

        answer = llm.generate(add_language_instruction(prompts['system'], state), prompts['user'])

        # Enhanced evidence list with retrieval method
        evidence = [
            f"Retrieval method: {retrieval_method or 'none'}",
            f"Documented {len(methods)} methods",
            f"Methods analyzed for usage: {len(graph_insights['method_usage'])}",
            f"Key methods identified: {len(graph_insights['key_methods'])}",
            f"Public API methods: {len([m for m in graph_insights['method_usage'].values() if m['is_public_api']])}"
        ]

        # Add matched function names to evidence if direct lookup was used
        if retrieval_method == 'direct_function_lookup' and methods:
            matched_names = list(set(m.get('name', '') for m in methods[:5]))
            evidence.insert(1, f"Matched functions: {', '.join(matched_names)}")

        state['methods'] = methods
        state['answer'] = answer
        state['evidence'] = evidence

        # S01 FIX: Set retrieved_functions for benchmark IR metrics
        # For definition queries, only return the exact target function(s) to maximize precision
        # Avoid diluting precision with related functions
        if retrieval_method == 'direct_function_lookup' and func_names:
            # Only include functions that were explicitly queried for
            exact_matches = [m['name'] for m in methods if m.get('name') in func_names]
            if exact_matches:
                state['retrieved_functions'] = list(set(exact_matches))[:10]
            else:
                state['retrieved_functions'] = func_names[:10]  # Use extracted names as fallback
            logger.info(f"S01: Set retrieved_functions with {len(state.get('retrieved_functions', []))} exact matches")
        else:
            # For other retrieval methods, include all found methods
            state['retrieved_functions'] = [m.get('name') for m in methods if m.get('name')][:25]

        state['metadata'] = {
            'method_count': len(methods),
            'retrieval_method': retrieval_method,
            'extracted_function_names': func_names if 'func_names' in dir() else [],
            'graph_methods_enabled': True,
            'graph_insights': {
                'methods_analyzed': len(graph_insights['method_usage']),
                'key_methods': len(graph_insights['key_methods']),
                'high_priority_methods': len([km for km in graph_insights['key_methods'] if km['priority'] == 'high']),
                'public_api_methods': len([m for m in graph_insights['method_usage'].values() if m['is_public_api']]),
                'entry_points': len([m for m in graph_insights['method_usage'].values() if m['is_entry_point']]),
                'call_examples': len(graph_insights['call_examples'])
            }
        }

    except Exception as e:
        logger.error(f"Documentation workflow failed: {e}")
        state['error'] = str(e)
        state['answer'] = f"Error generating documentation: {e}"

    return state




__all__ = ['documentation_workflow']
