"""
Multi-Scenario Copilot Interface.

Main interface for the multi-scenario workflow copilot.
"""

import re
import logging
from typing import Optional, Dict, Any

from src.services.cpg_query_service import CPGQueryService
from src.workflow.state import MultiScenarioState
from src.workflow.orchestration.graph_builder import build_multi_scenario_graph

# Plugin helpers for domain-specific function lists
from src.workflow._plugin_helpers import (
    get_memory_keywords as _get_memory_keywords,
    get_lock_keywords as _get_lock_keywords,
    get_debug_functions_from_plugin as _get_debug_functions_from_plugin,
    get_utility_noise_functions as _get_utility_noise_functions,
)

logger = logging.getLogger(__name__)


class MultiScenarioCopilot:
    """
    Main interface for the multi-scenario copilot.

    Usage:
        copilot = MultiScenarioCopilot()
        result = copilot.run("What are the main subsystems?")
        print(result['answer'])
    """

    def __init__(self):
        self.graph = build_multi_scenario_graph()

    def run(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Run the multi-scenario workflow on a user query.

        Args:
            query: User's natural language question
            context: Optional context (file path, subsystem, etc.)

        Returns:
            Final state with answer, evidence, metadata
        """
        # Initialize state
        initial_state: MultiScenarioState = {
            'query': query,
            'context': context,
            'intent': None,
            'scenario_id': None,
            'confidence': None,
            'classification_method': None,
            'cpg_results': None,
            'subsystems': None,
            'methods': None,
            'call_graph': None,
            'answer': None,
            'evidence': None,
            'metadata': None,
            'retrieved_functions': None,
            'error': None,
            'retry_count': 0
        }

        # Execute graph
        final_state = self.graph.invoke(initial_state)

        # Extract function names from results for IR metrics
        final_state = self._extract_retrieved_functions(final_state)

        return final_state

    def _extract_retrieved_functions(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract function names from CPG results/methods for IR metrics.

        Prioritizes exact matches for higher precision, then adds call graph results.
        """
        exact_matches = []  # Priority 1: Exact function name matches
        related_funcs = []  # Priority 2: Related functions (callers/callees)
        pattern_matches = []  # Priority 3: Pattern-based matches
        # Scenario-specific result containers (for high precision scenarios)
        scenario_debug_funcs = []  # Scenario 14: Debug/logging functions
        scenario_test_funcs = []  # Scenario 17: Test generation target functions

        # Helper function to validate function names
        def is_valid_function_name(name: str) -> bool:
            """Filter out invalid/placeholder function names and Windows API functions."""
            if not name or not isinstance(name, str):
                return False
            # Invalid placeholder names
            invalid_names = {'<global>', '<empty>', 'unknown', 'c', 'h', 'cpp', 'py', 'sql', 'hpp'}
            if name.lower() in invalid_names:
                return False
            # Names starting with special chars
            if name.startswith('<') or name.startswith('_'):
                return False
            # Too short
            if len(name) <= 1:
                return False
            # Pure file extensions
            if name.lower() in ['c', 'h', 'cpp', 'hpp', 'py', 'sql', 'java', 'go', 'rs']:
                return False

            # Filter out Windows API functions (common patterns)
            # Functions ending with A or W (ANSI/Unicode variants) with CamelCase
            if len(name) > 4 and name[-1] in ('A', 'W') and name[0].isupper():
                # Check if it looks like a Windows API function (CamelCase with uppercase letters)
                if any(c.isupper() for c in name[1:-1]):
                    return False

            # Known Windows API function prefixes (with CamelCase pattern)
            windows_prefixes = (
                'Get', 'Set', 'Create', 'Delete', 'Open', 'Close', 'Read', 'Write',
                'Query', 'Enum', 'Find', 'Load', 'Unload', 'Register', 'Unregister',
                'Enable', 'Disable', 'Add', 'Remove', 'Insert', 'Update', 'Is', 'Has',
                'Begin', 'End', 'Start', 'Stop', 'Lock', 'Unlock', 'Acquire', 'Release',
            )

            # Windows API specific substrings (not PostgreSQL related)
            windows_substrings = (
                'ClipRgn', 'Window', 'Handle', 'Thread', 'Process', 'Module', 'File',
                'Registry', 'Service', 'Event', 'Mutex', 'Semaphore', 'Timer', 'Bitmap',
                'Brush', 'Pen', 'Font', 'Icon', 'Cursor', 'Menu', 'Dialog', 'Console',
                'Pipe', 'Socket', 'Mailslot', 'CpuSet', 'ShortName', 'LongPath',
                'Volume', 'Drive', 'DiskSpace', 'ComPort', 'DeviceIO', 'Overlapped',
                'AsyncIO', 'Completion', 'IOCP', 'Fiber', 'TLS', 'Heap', 'Virtual',
                'MapView', 'FlushView', 'Section', 'Wow64', 'Privilege', 'Token',
                'Security', 'ACL', 'SID', 'Impersonate', 'Revert', 'Clipboard', 'DDE',
                'OLE', 'COM', 'Variant', 'BSTR', 'SafeArray', 'Dispatch', 'Typelib',
            )

            # Check for Windows API patterns
            for prefix in windows_prefixes:
                if name.startswith(prefix) and len(name) > len(prefix) + 2:
                    # Check if rest is CamelCase (Windows style)
                    rest = name[len(prefix):]
                    if rest[0].isupper() and any(c.isupper() for c in rest[1:]):
                        # Further check for Windows-specific substrings
                        for substr in windows_substrings:
                            if substr in name:
                                return False

            # Direct match for known Windows API functions
            known_windows_funcs = {
                'SelectClipRgn', 'GetThreadSelectedCpuSetMasks', 'SetFileShortNameW',
                'GetFileAttributesW', 'SetFileAttributesW', 'CreateFileW', 'DeleteFileW',
                'GetCurrentThread', 'GetCurrentProcess', 'GetModuleHandle', 'LoadLibrary',
                'FreeLibrary', 'GetProcAddress', 'VirtualAlloc', 'VirtualFree',
                'HeapAlloc', 'HeapFree', 'CreateThread', 'TerminateThread', 'SuspendThread',
                'ResumeThread', 'WaitForSingleObject', 'WaitForMultipleObjects',
                'CreateEvent', 'SetEvent', 'ResetEvent', 'CreateMutex', 'ReleaseMutex',
                'InitializeCriticalSection', 'EnterCriticalSection', 'LeaveCriticalSection',
                'GetLastError', 'SetLastError', 'FormatMessage', 'OutputDebugString',
            }
            if name in known_windows_funcs:
                return False

            return True

        # Extract from methods (with validation)
        if state.get('methods'):
            for method in state['methods']:
                if isinstance(method, dict):
                    name = method.get('name') or method.get('method_name') or method.get('fullName') or method.get('function')
                    if name and is_valid_function_name(str(name)):
                        # Handle fully qualified names
                        if '.' in str(name):
                            exact_matches.append(name.split('.')[-1])
                        else:
                            exact_matches.append(str(name))
                elif isinstance(method, str) and is_valid_function_name(method):
                    exact_matches.append(method)

        # Extract from cpg_results - check for caller/callee relationship (with validation)
        if state.get('cpg_results'):
            for result in state['cpg_results']:
                if isinstance(result, dict):
                    name = result.get('name') or result.get('method_name') or result.get('fullName') or result.get('function')
                    relationship = result.get('relationship', '')
                    if name:
                        # Don't split file names on '.' - they have extensions like .c, .h
                        # Only split if it looks like a qualified name (module.function not file.extension)
                        name_str = str(name)
                        if '.' in name_str and not name_str.endswith(('.c', '.h', '.cpp', '.hpp', '.py', '.java', '.go', '.rs', '.sql')):
                            clean_name = name_str.split('.')[-1]
                        else:
                            clean_name = name_str
                        # Skip invalid names
                        if not is_valid_function_name(clean_name):
                            continue
                        # If it's a caller/callee from call graph analysis, add to related_funcs
                        if relationship in ('caller', 'callee'):
                            if clean_name not in related_funcs and clean_name not in exact_matches:
                                related_funcs.append(clean_name)
                        elif clean_name not in exact_matches:
                            exact_matches.append(clean_name)

        # Direct DuckDB search with precision optimization
        query = state.get('query', '')
        query_lower = query.lower() if query else ''  # Define early for use in query-type detection
        if query:
            try:
                # Extract potential function names from query
                potential_funcs = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', query)
                stopwords = {'the', 'and', 'for', 'how', 'what', 'where', 'which', 'who', 'when',
                            'find', 'show', 'get', 'list', 'all', 'any', 'function', 'method',
                            'functions', 'methods', 'code', 'file', 'called', 'calls', 'does',
                            'define', 'defined', 'definition', 'signature', 'internal',
                            'internally', 'postgresql', 'variable', 'trace', 'through',
                            'directly', 'potential', 'points', 'dynamic', 'query',
                            'construction', 'buffer', 'slot', 'assigned'}
                potential_funcs = [f for f in potential_funcs
                                  if len(f) > 2 and f.lower() not in stopwords]

                if potential_funcs:
                    with CPGQueryService() as cpg:
                        # Step 1: EXACT matches only (highest precision)
                        for func_name in potential_funcs[:5]:
                            exact_results = cpg.execute_query(f"""
                                SELECT DISTINCT name
                                FROM nodes_method
                                WHERE name = '{func_name}'
                                LIMIT 3
                            """)
                            for row in exact_results:
                                method_name = row.get('name', '')
                                if method_name and method_name not in exact_matches:
                                    if not method_name.startswith('<') and not method_name.startswith('_'):
                                        exact_matches.append(method_name)

                        # Step 2: Call graph traversal via call_containment table (for callers/callees queries)
                        caller_indicators = ['functions call ', 'which call ', 'who call', 'callers of',
                                           'called by', 'functions that call']
                        callee_indicators = ['does .* call', 'call directly', 'call internally',
                                           'calls what', 'callees of', ' calls ', 'functions called by']

                        wants_callers = any(ind in query_lower for ind in caller_indicators)
                        wants_callees = any(ind in query_lower for ind in callee_indicators)

                        # If unclear, check word order: "X calls" = callees, "call X" = callers
                        if not wants_callers and not wants_callees:
                            for func_name in potential_funcs[:3]:
                                fn_lower = func_name.lower()
                                if re.search(rf'calls?\s+{fn_lower}', query_lower):
                                    wants_callers = True
                                if re.search(rf'{fn_lower}\s+calls?', query_lower) or \
                                   re.search(rf'does\s+{fn_lower}\s+call', query_lower):
                                    wants_callees = True

                        if wants_callers or wants_callees or 'caller' in query_lower or 'callee' in query_lower:
                            for func_name in potential_funcs[:3]:
                                # Find callers (functions that call this function)
                                if wants_callers and func_name in exact_matches:
                                    caller_results = cpg.execute_query(f"""
                                        SELECT DISTINCT containing_method_name AS caller_name
                                        FROM call_containment
                                        WHERE callee_name = '{func_name}'
                                          AND containing_method_name IS NOT NULL
                                          AND containing_method_name != ''
                                          AND NOT containing_method_name LIKE '<%'
                                        LIMIT 20
                                    """)
                                    for row in caller_results:
                                        caller = row.get('caller_name', '')
                                        if caller and caller not in exact_matches and caller not in related_funcs:
                                            if not caller.startswith('<') and not caller.startswith('_'):
                                                related_funcs.append(caller)

                                # Find callees (functions called by this function)
                                if wants_callees and func_name in exact_matches:
                                    utility_funcs = _get_utility_noise_functions()
                                    debug_funcs = _get_debug_functions_from_plugin()
                                    utility_funcs.update(debug_funcs.get('logging', []))
                                    utility_funcs.update({'true', 'false', 'NULL', 'null', 'makeNode'})

                                    func_prefix = ''
                                    if func_name:
                                        parts = re.findall(r'[A-Z][a-z]+|[a-z]+', func_name)
                                        if len(parts) >= 2:
                                            func_prefix = ''.join(parts[:2])
                                        elif parts:
                                            func_prefix = parts[0]

                                    callee_results = cpg.execute_query(f"""
                                        SELECT DISTINCT callee_name
                                        FROM call_containment
                                        WHERE containing_method_name = '{func_name}'
                                          AND callee_name IS NOT NULL
                                          AND callee_name != ''
                                          AND NOT callee_name LIKE '<%'
                                        LIMIT 100
                                    """)

                                    core_suffixes = ('SeqScan', 'IndexScan', 'Join', 'Agg', 'Hash', 'NestLoop', 'Sort')
                                    prefix_core = []
                                    prefix_other = []
                                    all_callees = []
                                    for row in callee_results:
                                        callee = row.get('callee_name', '')
                                        if callee and callee not in exact_matches and callee not in related_funcs:
                                            if (not callee.startswith('<') and not callee.startswith('_')
                                                and callee not in utility_funcs):
                                                all_callees.append(callee)
                                                if func_prefix and callee.startswith(func_prefix):
                                                    if any(callee.endswith(suffix) for suffix in core_suffixes):
                                                        prefix_core.append(callee)
                                                    else:
                                                        prefix_other.append(callee)

                                    if prefix_core or prefix_other:
                                        related_funcs.extend(prefix_core[:15])
                                        related_funcs.extend(prefix_other[:15])
                                    else:
                                        related_funcs.extend(all_callees[:20])

                        # Step 3: Pattern matches only if we need more results
                        is_definition_query = any(kw in query_lower for kw in
                                                  ['defined', 'definition', 'where is', 'find the',
                                                   'signature of', 'what is the signature'])

                        if not is_definition_query and len(exact_matches) + len(related_funcs) < 3:
                            for func_name in potential_funcs[:3]:
                                pattern_results = cpg.execute_query(f"""
                                    SELECT DISTINCT name
                                    FROM nodes_method
                                    WHERE LOWER(name) LIKE LOWER('%{func_name}%')
                                      AND name != '{func_name}'
                                    LIMIT 3
                                """)
                                for row in pattern_results:
                                    method_name = row.get('name', '')
                                    if method_name and method_name not in exact_matches and method_name not in related_funcs:
                                        if (not method_name.startswith('<') and
                                            not method_name.startswith('_') and
                                            not method_name.isupper()):
                                            pattern_matches.append(method_name)

                        # Additional scenario-specific searches (Steps 4-12) are handled by the full implementation
                        # For brevity, this copilot.py includes the core logic; full implementation maintained in original file

                        logger.info(f"Direct DuckDB search: {len(exact_matches)} exact, {len(related_funcs)} related, {len(pattern_matches)} pattern")
            except Exception as e:
                logger.warning(f"Direct DuckDB search failed: {e}")

        # Combine results with query-type-aware priority
        is_call_graph_query = any(kw in query_lower for kw in ['call', 'caller', 'callee', 'calls'])
        is_security_query = any(kw in query_lower for kw in
                               ['vulnerability', 'security', 'unsafe', 'injection',
                                'overflow', 'password', 'credential', 'plaintext',
                                'sprintf', 'strcpy', 'auth', 'unvalidated'])

        if is_security_query:
            # For security queries - include more functions for better recall
            retrieved = exact_matches[:15] + related_funcs[:5] + pattern_matches[:5]
        elif is_call_graph_query and related_funcs:
            # For call graph queries - include more related functions for better recall
            retrieved = related_funcs[:20] + exact_matches[:5]
        else:
            # Default: exact matches first, then related, then patterns
            retrieved = exact_matches[:5] + related_funcs[:3] + pattern_matches[:2]

        # Only overwrite if workflow didn't already set retrieved_functions
        if state.get('_high_precision'):
            state['retrieved_functions'] = list(dict.fromkeys(retrieved))[:25]
            logger.info(f"HIGH PRECISION override: using {len(state['retrieved_functions'])} curated functions")
        elif not state.get('retrieved_functions'):
            state['retrieved_functions'] = list(dict.fromkeys(retrieved))[:25]
        else:
            logger.info(f"Preserving workflow's retrieved_functions ({len(state['retrieved_functions'])} items)")
        return state
