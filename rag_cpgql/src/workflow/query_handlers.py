"""
Query Handler Functions for Workflow Scenarios.

Contains specialized query detection and handling functions for:
- Definition queries (find function definitions)
- Call graph queries (who calls X, what does X call)
- Dataflow queries (variable tracing)
"""

import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def detect_onboarding_query_type(query: str) -> Dict[str, Any]:
    """
    Detect specific query type within onboarding intent.

    Returns:
        dict with 'type' (definition|call_graph|dataflow|general), 'target' (method name if found),
        and 'variable' (variable name for dataflow queries)
    """
    query_lower = query.lower()

    # Extract potential method/function name from query
    # NOTE: Order matters! More specific patterns first
    method_patterns = [
        # Specific call graph patterns with function name at start
        r'what\s+(?:functions?\s+)?does\s+(\w+)\s+call',  # "What does X call" / "What functions does X call"
        r'(\w+)\s+call(?:s|ing)?\s+(?:what|which|directly)',  # "X calls what" / "X calling directly"
        # Definition patterns
        r'(?:function|method|procedure)\s+(\w+)',
        r'where\s+is\s+(?:the\s+)?(?:function\s+)?(\w+)',
        r'(?:defined?|definition\s+of)\s+(\w+)',
        r'signature\s+of\s+(\w+)',
        # Call graph patterns
        r'(?:who|what|which)\s+(?:functions?\s+)?call(?:s)?\s+(\w+)',  # "who calls X"
        r'(?:callers?|callees?)\s+(?:of\s+)?(\w+)',
        r'call(?:s|ed)?\s+(?:to\s+|by\s+)?(\w+)',  # "calls to X" / "called by X"
        # General patterns (lower priority)
        r'(\w+)\s+(?:defined?|function|method)',
        r'trace\s+(?:the\s+)?(?:variable\s+)?(\w+)',
        r'(\w+)\s+(?:variable|flows?)',
    ]

    target_method = None
    for pattern in method_patterns:
        # Search in lowercase for pattern matching
        match = re.search(pattern, query_lower, re.IGNORECASE)
        if match:
            # Extract position and get original case from original query
            start, end = match.span(1)
            target_method = query[start:end]  # Preserve original case
            # Skip common words
            if target_method.lower() not in ['the', 'a', 'an', 'is', 'are', 'function', 'method', 'variable']:
                break
            target_method = None

    # Detect query type
    # 1. Definition queries: "where is X defined", "signature of X", "find function X"
    definition_keywords = ['where is', 'defined', 'definition', 'signature', 'find function',
                          'locate', 'which file', 'find the function']

    # 2. Call graph queries: "who calls X", "what does X call", "callers of X"
    call_graph_keywords = ['who calls', 'what calls', 'callers', 'callees', 'calls to',
                          'functions call', 'called by', 'call directly']
    # Regex patterns for call graph (for patterns that need wildcard matching)
    call_graph_patterns = [r'what\s+does\s+\w+\s+call', r'\w+\s+call\??$']

    # 3. Dataflow queries: "trace variable X", "where does X flow", "data flow"
    dataflow_keywords = ['trace', 'dataflow', 'data flow', 'flows to', 'assigned',
                        'variable', 'flows from', 'taint']

    # Check for definition query
    if any(kw in query_lower for kw in definition_keywords):
        return {'type': 'definition', 'target': target_method, 'variable': None}

    # Check for call graph query (keywords + regex patterns)
    if any(kw in query_lower for kw in call_graph_keywords):
        return {'type': 'call_graph', 'target': target_method, 'variable': None}
    if any(re.search(p, query_lower) for p in call_graph_patterns):
        return {'type': 'call_graph', 'target': target_method, 'variable': None}

    # Check for dataflow query - extract both function and variable
    if any(kw in query_lower for kw in dataflow_keywords):
        # Dataflow-specific patterns to extract both function and variable
        # NOTE: Order matters! More specific patterns should come first
        df_patterns = [
            # Pattern: "What is the data flow of 'X' in Y" - extracts quoted variable and function
            r"(?:data\s+flow|dataflow)\s+of\s+['\"]?(\w+)['\"]?\s+(?:in|through)\s+(\w+)",
            # Pattern: "Trace how 'X' flows in Y" - the word "how" should NOT be captured
            r"trace\s+how\s+['\"]?(\w+)['\"]?\s+(?:flows?|is\s+used)\s+(?:in|through)\s+(\w+)",
            # Pattern: "Trace the variable 'X' in Y function" or "Trace variable X in Y"
            r"trace\s+(?:the\s+)?(?:variable\s+)?['\"]?(\w+)['\"]?\s+(?:in|through|within)\s+(\w+)",
            # Pattern: "Where does the 'X' variable get assigned in Y"
            r"where\s+(?:does|is)\s+(?:the\s+)?['\"](\w+)['\"](?:\s+variable)?\s+(?:get\s+)?assigned\s+in\s+(\w+)",
            # Pattern: "trace X through Y function" or "Trace the buffer variable through ReadBuffer"
            r"trace\s+(?:the\s+)?(\w+)\s+(?:variable\s+)?through\s+(\w+)",
            r"['\"]?(\w+)['\"]?\s+(?:variable|var)\s+(?:in|through)\s+(\w+)",
            # Pattern: "'X' flows in Y" - quoted variable with flow keyword
            r"['\"](\w+)['\"]?\s+(?:flow|flows)\s+(?:in|through)\s+(\w+)",
        ]

        # Also try to extract quoted variable name separately for fallback
        quoted_var_match = re.search(r"['\"](\w+)['\"]", query)

        variable_name = None
        function_name = None

        for df_pattern in df_patterns:
            match = re.search(df_pattern, query_lower, re.IGNORECASE)
            if match:
                # Extract and preserve original case
                var_start, var_end = match.span(1)
                func_start, func_end = match.span(2)
                variable_name = query[var_start:var_end]
                function_name = query[func_start:func_end]
                break

        # If no explicit function found, target_method might be the function from general patterns
        if not function_name and target_method:
            # Check if we can extract variable from quoted strings
            quoted_match = re.search(r"['\"](\w+)['\"]", query)
            if quoted_match:
                variable_name = quoted_match.group(1)
                function_name = target_method
            else:
                # Default: target_method is likely the variable, look for function name elsewhere
                func_match = re.search(r'(?:in|through|within)\s+(\w+)(?:\s+function)?', query_lower)
                if func_match:
                    func_start, func_end = func_match.span(1)
                    function_name = query[func_start:func_end]
                    variable_name = target_method
                else:
                    function_name = target_method

        return {'type': 'dataflow', 'target': function_name, 'variable': variable_name}

    # 4. Subsystem explain queries: "explain executor", "buffer manager", "how does the parser work"
    # Map keywords to subsystem names and their key methods for retrieval
    subsystem_mapping = {
        'executor': {
            'subsystem': 'executor',
            'key_methods': ['ExecInitNode', 'ExecProcNode', 'ExecEndNode', 'ExecutePlan', 'ExecScan'],
            'patterns': ['executor', 'execut']
        },
        'buffer': {
            'subsystem': 'storage/buffer',
            'key_methods': ['ReadBuffer', 'ReleaseBuffer', 'BufferAlloc', 'PinBuffer', 'UnpinBuffer'],
            'patterns': ['buffer manager', 'buffer pool', 'buffer cache', 'storage.*buffer']
        },
        'parser': {
            'subsystem': 'parser',
            'key_methods': ['raw_parser', 'pg_parse_query', 'base_yyparse', 'make_parsestate'],
            'patterns': ['parser', 'parsing', 'sql syntax']
        },
        'optimizer': {
            'subsystem': 'optimizer',
            'key_methods': ['standard_planner', 'create_plan', 'set_plan_references', 'cost_qual_eval'],
            'patterns': ['optimizer', 'planner', 'query planning', 'cost estimation']
        },
        'wal': {
            'subsystem': 'access/transam',
            'key_methods': ['XLogInsert', 'XLogFlush', 'XLogRecovery', 'CheckPointGuts'],
            'patterns': ['wal', 'write-ahead log', 'transaction log', 'xlog']
        },
        'lock': {
            'subsystem': 'storage/lmgr',
            'key_methods': ['LockAcquire', 'LockRelease', 'LWLockAcquire', 'LWLockRelease'],
            'patterns': ['lock manager', 'locking', 'concurrency control', 'lwlock']
        },
        'catalog': {
            'subsystem': 'catalog',
            'key_methods': ['SearchSysCache', 'RelationGetDescr', 'heap_open', 'systable_beginscan'],
            'patterns': ['catalog', 'system table', 'metadata', 'syscache']
        },
        'postmaster': {
            'subsystem': 'postmaster',
            'key_methods': ['PostmasterMain', 'ServerLoop', 'BackendStartup', 'fork_process'],
            'patterns': ['postmaster', 'server loop', 'backend process']
        }
    }

    subsystem_keywords = ['subsystem', 'explain', 'how does', 'how do', 'what is', 'what does', 'work']
    if any(kw in query_lower for kw in subsystem_keywords):
        for subsys_name, subsys_info in subsystem_mapping.items():
            for pattern in subsys_info['patterns']:
                if re.search(pattern, query_lower):
                    return {
                        'type': 'subsystem_explain',
                        'target': subsys_name,
                        'subsystem': subsys_info['subsystem'],
                        'key_methods': subsys_info['key_methods'],
                        'variable': None
                    }

    # Default to general overview
    return {'type': 'general', 'target': target_method, 'variable': None}


def _filter_by_relevance(results: List[Dict], target: str) -> List[Dict]:
    """
    Filter and score results by relevance to target.

    Scoring: exact match (1.0) > prefix match (0.8) > suffix match (0.6) > contains (0.4)
    """
    scored = []
    target_lower = target.lower()

    for r in results:
        name = r.get('name', '')
        name_lower = name.lower()

        if name_lower == target_lower:
            score = 1.0
        elif name_lower.startswith(target_lower):
            score = 0.8
        elif name_lower.endswith(target_lower):
            score = 0.6
        elif target_lower in name_lower:
            score = 0.4
        else:
            score = 0.2

        r['relevance_score'] = score
        scored.append((score, r))

    # Sort by score descending, then by name length (prefer shorter names)
    scored.sort(key=lambda x: (-x[0], len(x[1].get('name', ''))))
    return [r for _, r in scored]


def handle_definition_query(cpg, query: str, target: str) -> Dict[str, Any]:
    """
    Handle definition/location queries with exact match priority.

    Phase 1 Improvement: Two-phase retrieval with relevance filtering.
    1. First try exact match only
    2. If no exact match, use pattern match with relevance scoring
    3. Include graph context (callers/callees) for better benchmark precision
    """
    results = {
        'methods': [],
        'exact_matches': [],
        'evidence': [],
        'graph_context': {}  # NEW: Graph context for related functions
    }

    if target:
        # PHASE 1: Exact match search (highest priority)
        exact_query = f"""
            SELECT id, name, full_name, filename, line_number, signature
            FROM nodes_method
            WHERE name = '{target}'
            ORDER BY line_number
            LIMIT 10
        """
        exact_results = cpg.execute_query(exact_query)

        if exact_results:
            # Apply relevance filtering even to exact matches (for ordering)
            exact_results = _filter_by_relevance(exact_results, target)
            results['exact_matches'] = exact_results[:5]  # Return top 5 exact matches
            results['evidence'].append(f"Found {len(exact_results)} exact match(es) for '{target}'")

            for m in exact_results[:3]:
                # Include signature in evidence for signature queries
                sig_info = m.get('signature', '')
                if sig_info:
                    results['evidence'].append(
                        f"  - {m['name']} in {m.get('filename', 'unknown')}:{m.get('line_number', '?')}"
                    )
                    results['evidence'].append(
                        f"    Signature: {sig_info}"
                    )
                    if '(' in sig_info:
                        return_type = sig_info.split('(')[0]
                        params = sig_info[sig_info.find('(')+1:sig_info.rfind(')')]
                        results['evidence'].append(
                            f"    Returns: {return_type}, Parameters: {params}"
                        )
                else:
                    results['evidence'].append(
                        f"  - {m['name']} in {m.get('filename', 'unknown')}:{m.get('line_number', '?')}"
                    )

            # NEW: Add graph context (callers/callees) for benchmark questions expecting related functions
            try:
                if exact_results and exact_results[0].get('id'):
                    method_id = exact_results[0]['id']

                    # Find top 3 callers
                    caller_query = f"""
                        SELECT DISTINCT m.name AS caller_name
                        FROM call_containment cc
                        JOIN nodes_method m ON cc.containing_method_id = m.id
                        JOIN nodes_call c ON cc.call_id = c.id
                        WHERE c.name = '{target}'
                        LIMIT 3
                    """
                    caller_results = cpg.execute_query(caller_query)
                    if caller_results:
                        results['graph_context']['callers'] = [r['caller_name'] for r in caller_results]

                    # Find top 3 callees
                    callee_query = f"""
                        SELECT DISTINCT c.name AS callee_name
                        FROM call_containment cc
                        JOIN nodes_call c ON cc.call_id = c.id
                        WHERE cc.containing_method_id = {method_id}
                        AND c.name NOT IN ('true', 'false', 'NULL', 'null', '')
                        LIMIT 3
                    """
                    callee_results = cpg.execute_query(callee_query)
                    if callee_results:
                        results['graph_context']['callees'] = [r['callee_name'] for r in callee_results]

                    if results['graph_context']:
                        results['evidence'].append(f"Graph context: {len(results['graph_context'].get('callers', []))} callers, {len(results['graph_context'].get('callees', []))} callees")
            except Exception as e:
                logger.debug(f"Graph context lookup failed: {e}")
        else:
            # PHASE 2: Pattern match with relevance filtering
            pattern_query = f"""
                SELECT id, name, full_name, filename, line_number, signature
                FROM nodes_method
                WHERE name LIKE '%{target}%'
                ORDER BY line_number
                LIMIT 30
            """
            pattern_results = cpg.execute_query(pattern_query)

            # Apply relevance filtering to pattern matches
            if pattern_results:
                pattern_results = _filter_by_relevance(pattern_results, target)
                results['methods'] = pattern_results[:10]  # Return top 10 after filtering
                results['evidence'].append(f"Found {len(pattern_results)} methods matching '{target}' (top 10 by relevance)")

    return results


def handle_call_graph_query(cpg, call_analyzer, query: str, target: str) -> Dict[str, Any]:
    """Handle call graph queries using CallGraphAnalyzer."""
    results = {
        'callers': [],
        'callees': [],
        'target': target,
        'evidence': []
    }

    if not target:
        results['evidence'].append("No target method identified in query")
        return results

    query_lower = query.lower()

    # Determine if asking for callers or callees using both keywords and regex
    caller_keywords = ['who calls', 'callers', 'called by', 'functions call']
    caller_patterns = [r'which\s+\w*\s*call\s+', r'what\s+calls\s+']

    callee_keywords = ['callees', 'call directly', 'does .* call']
    callee_patterns = [r'what\s+does\s+\w+\s+call', r'functions?\s+does\s+\w+\s+call']

    # Check for callers query
    is_caller_query = (
        any(kw in query_lower for kw in caller_keywords) or
        any(re.search(p, query_lower) for p in caller_patterns)
    )

    # Check for callees query
    is_callee_query = (
        any(kw in query_lower for kw in callee_keywords) or
        any(re.search(p, query_lower) for p in callee_patterns)
    )

    if is_caller_query:
        # Find callers
        callers = call_analyzer.find_all_callers(target, max_depth=2, direct_only=False)
        direct_callers = call_analyzer.find_all_callers(target, max_depth=1, direct_only=True)

        results['callers'] = callers
        results['direct_callers'] = direct_callers
        results['evidence'].append(f"Found {len(direct_callers)} direct callers of '{target}'")
        results['evidence'].append(f"Total callers (depth 2): {len(callers)}")

        if direct_callers:
            results['evidence'].append(f"Direct callers: {', '.join(direct_callers[:10])}")

    if is_callee_query:
        # Find callees
        callees = call_analyzer.find_all_callees(target, max_depth=2)
        direct_callees = call_analyzer.find_all_callees(target, max_depth=1)

        results['callees'] = callees
        results['direct_callees'] = direct_callees
        results['evidence'].append(f"Found {len(direct_callees)} direct callees of '{target}'")
        results['evidence'].append(f"Total callees (depth 2): {len(callees)}")

        if direct_callees:
            # Filter out noise
            clean_callees = [c for c in direct_callees if c not in ['true', 'false', 'NULL', 'null']]
            results['evidence'].append(f"Direct callees: {', '.join(clean_callees[:10])}")

    # FALLBACK: If no results from call graph, try direct SQL query
    if not results.get('callers') and not results.get('callees'):
        logger.info(f"Call graph empty for '{target}', using direct SQL fallback")
        try:
            # Find callers via nodes_call.name and containing_method_id
            caller_query = f"""
                SELECT DISTINCT m.name AS caller_name
                FROM nodes_call c
                JOIN nodes_method m ON c.containing_method_id = m.id
                WHERE c.name = '{target}'
                ORDER BY caller_name
                LIMIT 20
            """
            caller_results = cpg.execute_sql_dict(caller_query)
            if caller_results:
                callers = [r['caller_name'] for r in caller_results]
                results['callers'] = callers
                results['direct_callers'] = callers
                results['evidence'].append(f"[Fallback] Found {len(callers)} callers of '{target}'")

            # Find callees via nodes_call within the target method
            method_query = f"SELECT id FROM nodes_method WHERE name = '{target}' LIMIT 1"
            method_result = cpg.execute_query(method_query)
            if method_result:
                method_id = method_result[0]['id']
                callee_query = f"""
                    SELECT DISTINCT c.name AS callee_name
                    FROM nodes_call c
                    WHERE c.containing_method_id = {method_id}
                    AND c.name NOT IN ('true', 'false', 'NULL', 'null', '', '<operator>')
                    ORDER BY callee_name
                    LIMIT 30
                """
                callee_results = cpg.execute_sql_dict(callee_query)
                if callee_results:
                    callees = [r['callee_name'] for r in callee_results]
                    results['callees'] = callees
                    results['direct_callees'] = callees
                    results['evidence'].append(f"[Fallback] Found {len(callees)} callees of '{target}'")

        except Exception as e:
            logger.warning(f"Fallback query failed: {e}")

    return results


def handle_dataflow_query(cpg, query: str, target: str, variable: str = None) -> Dict[str, Any]:
    """Handle dataflow/variable tracing queries.

    Args:
        cpg: CPG query service
        query: Original query string
        target: Target function name (e.g., 'heap_open')
        variable: Variable name to trace (e.g., 'relid')
    """
    results = {
        'methods': [],  # Methods relevant to the dataflow query
        'variables': [],
        'flows': [],
        'evidence': []
    }

    if not target and not variable:
        results['evidence'].append("No target function/variable identified")
        return results

    found_method_ids = []
    seen_methods = set()

    # Strategy 1: Find the target function with flexible matching
    if target:
        # Try exact match first, then fuzzy
        func_query = f"""
            SELECT DISTINCT
                m.id,
                m.name AS method_name,
                m.full_name,
                m.filename,
                m.line_number,
                m.signature
            FROM nodes_method m
            WHERE m.name = '{target}'
               OR m.name ILIKE '%{target}%'
               OR m.full_name ILIKE '%{target}%'
            ORDER BY
                CASE WHEN m.name = '{target}' THEN 0
                     WHEN m.name ILIKE '{target}%' THEN 1
                     ELSE 2 END,
                m.name
            LIMIT 15
        """

        try:
            func_results = cpg.execute_query(func_query)
            if func_results:
                results['methods'].extend(func_results)
                found_method_ids = [r.get('id') for r in func_results if r.get('id')]
                seen_methods = {r.get('method_name') for r in func_results if r.get('method_name')}
                results['evidence'].append(f"Found {len(func_results)} methods matching '{target}'")
        except Exception as e:
            results['evidence'].append(f"Function search error: {str(e)[:50]}")

    # Strategy 2: Search for methods containing the variable name in their name/code
    # (nodes_local is empty, so search in method names and code instead)
    if variable:
        var_method_query = f"""
            SELECT DISTINCT
                m.id,
                m.name AS method_name,
                m.full_name,
                m.filename,
                m.line_number
            FROM nodes_method m
            WHERE m.name ILIKE '%{variable}%'
               OR m.code ILIKE '%{variable}%'
            ORDER BY
                CASE WHEN m.name ILIKE '%{variable}%' THEN 0 ELSE 1 END,
                m.name
            LIMIT 10
        """

        try:
            var_results = cpg.execute_query(var_method_query)
            if var_results:
                # Add unique methods from variable search
                for vr in var_results:
                    if vr.get('method_name') and vr.get('method_name') not in seen_methods:
                        results['methods'].append(vr)
                        seen_methods.add(vr.get('method_name'))
                        if vr.get('id'):
                            found_method_ids.append(vr.get('id'))
                results['evidence'].append(f"Found {len(var_results)} methods related to variable '{variable}'")
        except Exception as e:
            results['evidence'].append(f"Variable method search error: {str(e)[:50]}")

    # Strategy 3: Find related functions via CallGraphAnalyzer (more reliable)
    if target:
        try:
            from src.analysis import CallGraphAnalyzer
            call_analyzer = CallGraphAnalyzer(cpg)

            # Find callees (functions called by target) using CallGraphAnalyzer
            callees = call_analyzer.find_all_callees(target, max_depth=1)
            if callees:
                # Filter out operators, builtins, and noise
                clean_callees = [
                    c for c in callees
                    if c and not c.startswith('<') and c not in ['true', 'false', 'NULL', 'null', '']
                ]
                for callee_name in clean_callees[:20]:  # Increased limit to get more relevant callees
                    if callee_name not in seen_methods:
                        results['methods'].append({
                            'method_name': callee_name,
                            'relationship': 'callee'
                        })
                        seen_methods.add(callee_name)
                results['evidence'].append(f"CallGraphAnalyzer found {len(clean_callees)} callees for '{target}'")

            # Find callers (functions that call target)
            callers = call_analyzer.find_all_callers(target, max_depth=1)
            if callers:
                for caller_name in callers[:10]:
                    if caller_name not in seen_methods:
                        results['methods'].append({
                            'method_name': caller_name,
                            'relationship': 'caller'
                        })
                        seen_methods.add(caller_name)
                results['evidence'].append(f"CallGraphAnalyzer found {len(callers)} callers for '{target}'")
        except Exception as e:
            results['evidence'].append(f"CallGraphAnalyzer error: {str(e)[:50]}")

    # Strategy 3b: Fallback to SQL query for call graph if CallGraphAnalyzer didn't find much
    if found_method_ids and len(results['methods']) < 5:
        try:
            method_ids_str = ','.join(str(mid) for mid in found_method_ids[:5])
            # Find callees (functions called by target)
            callee_query = f"""
                SELECT DISTINCT
                    m.id,
                    m.name AS method_name,
                    m.full_name,
                    m.filename,
                    'callee' AS relationship
                FROM edges_call ec
                JOIN nodes_method m ON m.id = ec.dst
                WHERE ec.src IN ({method_ids_str})
                LIMIT 10
            """
            callee_results = cpg.execute_query(callee_query)

            # Find callers (functions that call target)
            caller_query = f"""
                SELECT DISTINCT
                    m.id,
                    m.name AS method_name,
                    m.full_name,
                    m.filename,
                    'caller' AS relationship
                FROM edges_call ec
                JOIN nodes_method m ON m.id = ec.src
                WHERE ec.dst IN ({method_ids_str})
                LIMIT 10
            """
            caller_results = cpg.execute_query(caller_query)

            # Combine results
            related_results = (callee_results or []) + (caller_results or [])
            if related_results:
                for rel in related_results:
                    if rel.get('method_name') and rel.get('method_name') not in seen_methods:
                        results['methods'].append(rel)
                        seen_methods.add(rel.get('method_name'))
                results['evidence'].append(f"SQL fallback found {len(related_results)} related functions")
        except Exception as e:
            results['evidence'].append(f"Call graph SQL error: {str(e)[:50]}")

    # Strategy 4: If still no results, try broader semantic search
    if not results['methods'] and (target or variable):
        search_term = target or variable
        # Try searching in method names with word boundaries
        broad_query = f"""
            SELECT DISTINCT
                m.id,
                m.name AS method_name,
                m.full_name,
                m.filename,
                m.line_number
            FROM nodes_method m
            WHERE m.name ILIKE '%{search_term[:4]}%'
            ORDER BY m.name
            LIMIT 10
        """
        try:
            broad_results = cpg.execute_query(broad_query)
            if broad_results:
                results['methods'].extend(broad_results)
                results['evidence'].append(f"Broad search found {len(broad_results)} methods")
        except Exception as e:
            results['evidence'].append(f"Broad search error: {str(e)[:50]}")

    return results


def detect_architecture_query_type(query: str) -> Dict[str, Any]:
    """
    Detect specific query type within architecture/dependency intent.

    Returns:
        dict with 'type' (dependency|circular|coupling|layer|general),
        'target_module' (module name if found),
        and expected patterns.
    """
    query_lower = query.lower()

    # 1. Module dependency queries: "modules that depend on X", "what depends on X"
    dependency_patterns = [
        r'(?:modules?|files?)\s+(?:that\s+)?depend(?:s)?\s+on\s+(\S+)',
        r'depend(?:s|encies)?\s+(?:of|on)\s+(\S+)',
        r'what\s+(?:depends|includes?)\s+(\S+)',
        r'(?:files?|modules?)\s+(?:that\s+)?include\s+(\S+)',
    ]

    for pattern in dependency_patterns:
        match = re.search(pattern, query_lower)
        if match:
            target = match.group(1).strip()
            # Clean up target (remove quotes, trailing punctuation)
            target = target.strip('\'",.?!')
            return {
                'type': 'dependency',
                'target_module': target,
                'direction': 'dependents'  # modules that depend ON target
            }

    # 2. Include queries: "list files that include X", "show files including X"
    include_patterns = [
        r'(?:list|show|find|get)\s+(?:all\s+)?(?:files?|modules?)\s+(?:that\s+)?include\s+(\S+)',
        r'(?:files?|modules?)\s+(?:that\s+)?include\s+(\S+)',
        r'include\s+(\S+\.h)',  # "include postgres.h"
        r'(\S+\.h)\s+include',  # "postgres.h include"
    ]

    for pattern in include_patterns:
        match = re.search(pattern, query_lower)
        if match:
            target = match.group(1).strip()
            target = target.strip('\'",.?!')
            return {
                'type': 'include',
                'target_module': target,
                'direction': 'includers'  # files that include target
            }

    # 2. Circular dependency queries
    if any(kw in query_lower for kw in ['circular', 'cycle', 'mutual depend']):
        return {'type': 'circular', 'target_module': None}

    # 3. Coupling queries
    if any(kw in query_lower for kw in ['coupling', 'god module', 'fan-in', 'fan-out']):
        return {'type': 'coupling', 'target_module': None}

    # 4. Layering queries
    if any(kw in query_lower for kw in ['layer', 'layering', 'boundary', 'violation']):
        return {'type': 'layer', 'target_module': None}

    # 5. General architecture queries
    return {'type': 'general', 'target_module': None}


def detect_refactoring_query_type(query: str) -> Dict[str, Any]:
    """
    Detect specific query type within refactoring intent.

    Returns:
        dict with 'type' (duplicates|dead_code|complexity|general),
        'category' (for duplicates: exact_duplicates|pattern_clone|semantic_clone|etc),
        and expected function patterns.
    """
    query_lower = query.lower()

    # 1. Duplicate/Clone detection queries
    duplicate_keywords = [
        'duplicate', 'duplicated', 'clone', 'cloned', 'copy-paste', 'copy paste',
        'copied', 'similar function', 'similar implementation', 'same implementation',
        'repeated', 'identical', 'merge candidates', 'extract', 'cloned code'
    ]

    if any(kw in query_lower for kw in duplicate_keywords):
        # Detect category based on specific keywords
        category = 'exact_duplicates'
        expected_patterns = []

        if any(kw in query_lower for kw in ['semantic', 'similar function', 'different name']):
            category = 'semantic_clone'
        elif any(kw in query_lower for kw in ['pattern', 'error handling', 'memory', 'lock', 'switch']):
            category = 'pattern_clone'
            if 'error' in query_lower:
                expected_patterns = ['ereport', 'elog']
            elif 'memory' in query_lower or 'alloc' in query_lower:
                expected_patterns = ['palloc', 'palloc0']
            elif 'lock' in query_lower:
                expected_patterns = ['LWLockAcquire', 'LockAcquire']
        elif any(kw in query_lower for kw in ['cross', 'different module', 'across']):
            category = 'cross_file_clone'
        elif any(kw in query_lower for kw in ['copy-paste', 'copy paste', 'copied']):
            category = 'copy_paste'
        elif any(kw in query_lower for kw in ['merge', 'extract', 'refactor']):
            category = 'merge_candidates'

        return {
            'type': 'duplicates',
            'category': category,
            'expected_patterns': expected_patterns
        }

    # 2. Dead code detection queries
    dead_code_keywords = ['dead code', 'unused', 'unreachable', 'deprecated', 'never called', 'obsolete']
    if any(kw in query_lower for kw in dead_code_keywords):
        return {'type': 'dead_code', 'category': 'general'}

    # 3. Complexity queries
    complexity_keywords = ['complexity', 'cyclomatic', 'nesting', 'god class', 'bloater', 'long method']
    if any(kw in query_lower for kw in complexity_keywords):
        return {'type': 'complexity', 'category': 'general'}

    # 4. General refactoring queries
    return {'type': 'general', 'category': None}


__all__ = [
    'detect_onboarding_query_type',
    'detect_architecture_query_type',
    'detect_refactoring_query_type',
    'handle_definition_query',
    'handle_call_graph_query',
    'handle_dataflow_query',
]
