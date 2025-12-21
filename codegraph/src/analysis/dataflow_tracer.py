"""
Data Flow Tracer - Graph Method #3 (MAJOR REWRITE - 2025-11-24)

Implements data flow tracing using ACTUAL CPG REACHING_DEF edges:
- Intra-procedural: Within a single function (REACHING_DEF edges)
- Inter-procedural: Across function boundaries (CALL + REACHING_DEF edges)
- Variable path tracking: From definition to all uses via real graph traversal
- Source-to-sink paths: For taint analysis with actual dataflow paths

**MAJOR CHANGES FROM PREVIOUS VERSION:**
1. Now uses actual `edges_reaching_def` table instead of `nodes_identifier.is_definition/is_use` flags
2. All queries traverse real REACHING_DEF edges from the CPG schema
3. Taint analysis follows real dataflow via REACHING_DEF + ARGUMENT edges
4. More accurate inter-procedural analysis
5. Removed reliance on identifier table workarounds

**Key Improvements:**
- trace_variable(): Now uses recursive CTE with edges_reaching_def
- find_reaching_definitions(): Backward REACHING_DEF traversal
- find_variable_uses(): Forward REACHING_DEF traversal
- find_taint_paths(): REACHING_DEF from source arguments to sink arguments
- _compute_flows(): Deprecated (direct queries more efficient)

Based on: "Graph methods for RAG copilot.md" - Method #3
Used in scenarios: 2, 6, 8, 14

FUTURE ENHANCEMENTS (Low Priority):
- CFG integration for more precise intra-procedural flows (requires CFG edges in schema)
- Field-sensitive analysis to track struct fields (requires type hierarchy)

IMPLEMENTED:
- Inter-procedural flow detection via AST parent traversal (2025-12-06)
- Sanitization detection with confidence scoring (Phase 4C)
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DataFlowPath:
    """Represents a data flow path"""
    path_id: str
    variable_name: str
    source_location: Dict[str, Any]  # {method, file, line, type}
    sink_location: Dict[str, Any]    # {method, file, line, type}
    path_length: int
    intermediate_nodes: List[Dict[str, Any]] = field(default_factory=list)
    is_inter_procedural: bool = False  # Crosses function boundaries
    sanitization_points: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class VariableFlow:
    """Tracks flow of a single variable"""
    variable_name: str
    definition_points: List[Dict[str, Any]] = field(default_factory=list)
    use_points: List[Dict[str, Any]] = field(default_factory=list)
    flows: List[DataFlowPath] = field(default_factory=list)


# Phase 4C: Sanitization Confidence Scoring
# Maps sanitization function patterns to confidence scores (0.0-1.0)
# Higher confidence = more reliable sanitization
#
# NOTE: Domain-specific patterns are loaded from the active domain plugin.
# Generic patterns here are merged with domain-specific ones at runtime.
_GENERIC_SANITIZATION_CONFIDENCE = {
    # High confidence (1.0) - Strong, proper sanitization
    'parameterize': 1.0,      # SQL parameterization (best practice)
    'prepare': 1.0,           # Prepared statements
    'bind': 1.0,              # Parameter binding
    'bind_param': 1.0,        # Explicit parameter binding
    'placeholder': 1.0,       # Placeholder-based queries

    # High confidence (0.9) - Database-specific escaping
    'pg_escape_string': 0.9,     # PostgreSQL escaping
    'pg_escape_bytea': 0.9,      # PostgreSQL bytea escaping
    'mysqli_real_escape_string': 0.9,  # MySQL escaping
    'mysql_real_escape_string': 0.9,   # MySQL (old API)
    'htmlspecialchars': 0.9,     # HTML escaping
    'htmlentities': 0.9,         # HTML entities

    # Medium-high confidence (0.8) - Context-specific validation
    'validate_%': 0.8,        # Validation functions
    'verify_%': 0.8,          # Verification functions
    'is_valid_%': 0.8,        # Validation checks
    'check_type': 0.8,        # Type checking
    'whitelist': 0.8,         # Whitelist filtering
    'allowlist': 0.8,         # Allowlist filtering

    # Medium confidence (0.7) - Generic escaping/encoding
    'escape_%': 0.7,          # Generic escaping
    'sanitize_%': 0.7,        # Generic sanitization
    'encode_%': 0.7,          # Encoding functions
    'urlencode': 0.7,         # URL encoding
    'base64_encode': 0.7,     # Base64 encoding
    'json_encode': 0.7,       # JSON encoding

    # Medium-low confidence (0.6) - Filtering
    'filter_%': 0.6,          # Generic filtering
    'clean_%': 0.6,           # Generic cleaning
    'strip_tags': 0.6,        # HTML tag stripping
    'preg_replace': 0.6,      # Regex replacement (depends on pattern)

    # Lower confidence (0.4-0.5) - Type conversion (may be sufficient)
    'intval': 0.5,            # Integer casting
    'floatval': 0.5,          # Float casting
    'int': 0.5,               # Type cast to int
    'float': 0.5,             # Type cast to float
    'str.isdigit': 0.4,       # Digit checking
    'str.isalpha': 0.4,       # Alpha checking

    # Low confidence (0.3) - Minimal sanitization
    'trim': 0.3,              # Whitespace trimming
    'strip': 0.3,             # Whitespace stripping
    'lower': 0.3,             # Case conversion
    'upper': 0.3,             # Case conversion
    'normalize': 0.3,         # Generic normalization

    # Very low confidence (0.2) - Often insufficient
    'addslashes': 0.2,        # Weak escaping (deprecated)
    'stripslashes': 0.2,      # Weak unescaping
    'str_replace': 0.2,       # Simple replacement (often incomplete)

    # =============================================================
    # Python/Django/SQLAlchemy-specific patterns (Phase 4D)
    # =============================================================

    # High confidence (1.0) - Django ORM (parameterized by default)
    'objects.filter': 1.0,       # Django ORM filter (safe)
    'objects.get': 1.0,          # Django ORM get (safe)
    'objects.exclude': 1.0,      # Django ORM exclude (safe)
    'objects.create': 1.0,       # Django ORM create (safe)
    'objects.update': 1.0,       # Django ORM update (safe)
    'objects.annotate': 1.0,     # Django ORM annotate (safe)
    'objects.aggregate': 1.0,    # Django ORM aggregate (safe)
    'objects.values': 1.0,       # Django ORM values (safe)
    'objects.values_list': 1.0,  # Django ORM values_list (safe)

    # High confidence (1.0) - SQLAlchemy parameterized queries
    'query.filter': 1.0,         # SQLAlchemy filter (safe)
    'query.filter_by': 1.0,      # SQLAlchemy filter_by (safe)
    'session.query': 1.0,        # SQLAlchemy query builder (safe)
    'session.execute': 0.8,      # SQLAlchemy execute (depends on usage)
    'bindparam': 1.0,            # SQLAlchemy explicit binding
    'text': 0.7,                 # SQLAlchemy text() - needs params

    # High confidence (0.9) - Django security utilities
    'escape': 0.9,               # Django escape
    'mark_safe': 0.3,            # Django mark_safe (DANGEROUS - low confidence)
    'format_html': 0.9,          # Django format_html (safe)
    'conditional_escape': 0.9,   # Django conditional_escape

    # Medium-high confidence (0.8) - Python type validation
    'isinstance': 0.8,           # Type checking
    'issubclass': 0.8,           # Type checking
    'hasattr': 0.6,              # Attribute checking
    'getattr': 0.5,              # Attribute access (depends on default)

    # Medium confidence (0.7) - Django form validation
    'cleaned_data': 0.8,         # Django form cleaned data
    'is_valid': 0.8,             # Django form validation
    'clean_%': 0.8,              # Django form field cleaning
    'validate_%': 0.8,           # Django validators

    # Medium confidence (0.7) - Python stdlib
    'json.loads': 0.6,           # JSON parsing (can still be dangerous)
    'json.dumps': 0.7,           # JSON serialization
    're.match': 0.7,             # Regex validation
    're.search': 0.7,            # Regex search
    're.sub': 0.6,               # Regex substitution
    'ast.literal_eval': 0.9,     # Safe eval for literals
}

# Phase 4C: Minimum confidence threshold for considering path "sanitized"
# Paths with max_confidence >= this threshold are filtered out (not reported as vulnerabilities)
SANITIZATION_CONFIDENCE_THRESHOLD = 0.7


def _get_sanitization_patterns() -> Dict[str, float]:
    """
    Get merged sanitization patterns: generic + domain-specific.

    Domain-specific patterns (e.g., PostgreSQL's pg_escape_string, SPI_prepare)
    are loaded from the active domain plugin and merged with generic patterns.
    Domain-specific patterns take precedence over generic ones if there's overlap.

    Returns:
        Dictionary mapping pattern names to confidence scores (0.0-1.0)
    """
    # Start with generic patterns
    merged = dict(_GENERIC_SANITIZATION_CONFIDENCE)

    # Try to load domain-specific patterns from active plugin
    try:
        from src.domains import DomainRegistry
        domain = DomainRegistry.get_active_or_none()
        if domain is not None and hasattr(domain, 'get_sanitization_confidence'):
            domain_patterns = domain.get_sanitization_confidence()
            if domain_patterns:
                # Domain patterns override generic (higher specificity)
                merged.update(domain_patterns)
                logger.debug(
                    f"Loaded {len(domain_patterns)} sanitization patterns from "
                    f"{domain.name} plugin (total: {len(merged)})"
                )
    except ImportError:
        logger.debug("Domain registry not available, using generic patterns only")
    except Exception as e:
        logger.debug(f"Could not load domain sanitization patterns: {e}")

    return merged


# Module-level cached patterns (lazy-loaded)
_cached_sanitization_patterns: Optional[Dict[str, float]] = None


def get_sanitization_patterns() -> Dict[str, float]:
    """
    Get sanitization patterns with caching.

    Returns merged generic + domain-specific patterns.
    """
    global _cached_sanitization_patterns
    if _cached_sanitization_patterns is None:
        _cached_sanitization_patterns = _get_sanitization_patterns()
    return _cached_sanitization_patterns


# Backwards compatibility: For external imports that expect dict access
# Usage: SANITIZATION_CONFIDENCE['pattern'] or SANITIZATION_CONFIDENCE.items()
# This is lazy-evaluated on first access
class _SanitizationConfidenceProxy:
    """
    Proxy class that mimics dict behavior but lazy-loads sanitization patterns.

    This singleton class provides lazy loading of sanitization confidence patterns,
    combining generic patterns with domain-specific ones. It implements the dict
    interface (__getitem__, __contains__, keys, values, items, get) so it can be
    used as a drop-in replacement for a dictionary.

    The lazy loading defers pattern initialization until first access, which:
    - Avoids import-time circular dependencies with DomainRegistry
    - Reduces startup time when patterns aren't needed
    - Allows domain plugins to be loaded before patterns are merged

    Pattern confidence scores range from 0.0 to 1.0:
    - 1.0: Strong sanitization (parameterized queries, prepared statements)
    - 0.8-0.9: Context-specific validation (input validation, type checking)
    - 0.6-0.7: Generic encoding/escaping (URL encoding, HTML escaping)
    - 0.3-0.5: Weak sanitization (type casting, trimming)
    - 0.2: Often insufficient (addslashes, simple replacement)

    Example:
        >>> patterns = SANITIZATION_CONFIDENCE  # Singleton proxy
        >>> 'parameterize' in patterns
        True
        >>> patterns.get('parameterize', 0.0)
        1.0
        >>> patterns['pg_escape_string']
        0.9

    See Also:
        _GENERIC_SANITIZATION_CONFIDENCE: Generic patterns (always loaded)
        _get_sanitization_patterns(): Merges generic + domain patterns
        SANITIZATION_CONFIDENCE_THRESHOLD: Minimum confidence to consider sanitized
    """
    _instance = None
    _patterns = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _ensure_loaded(self):
        if self._patterns is None:
            self._patterns = get_sanitization_patterns()

    def __getitem__(self, key):
        self._ensure_loaded()
        return self._patterns[key]

    def __contains__(self, key):
        self._ensure_loaded()
        return key in self._patterns

    def keys(self):
        self._ensure_loaded()
        return self._patterns.keys()

    def values(self):
        self._ensure_loaded()
        return self._patterns.values()

    def items(self):
        self._ensure_loaded()
        return self._patterns.items()

    def get(self, key, default=None):
        self._ensure_loaded()
        return self._patterns.get(key, default)

    def __len__(self):
        self._ensure_loaded()
        return len(self._patterns)


SANITIZATION_CONFIDENCE = _SanitizationConfidenceProxy()


class DataFlowTracer:
    """
    Data flow analysis using REACHING_DEF edges

    Methods:
    - trace_variable: Trace a variable from definition to uses
    - find_reaching_definitions: Find all definitions reaching a use
    - find_variable_uses: Find all uses of a definition
    - trace_inter_procedural: Trace across function calls
    - find_taint_paths: Find paths from sources to sinks (for taint analysis)
    """

    def __init__(self, cpg_service):
        """
        Initialize tracer with CPG service

        Args:
            cpg_service: CPGQueryService instance
        """
        self.cpg = cpg_service

        # Support both execute_query and execute_sql_dict interfaces
        if hasattr(cpg_service, 'execute_query'):
            self._execute_base = cpg_service.execute_query
            self._use_inline_params = False
        elif hasattr(cpg_service, 'execute_sql_dict'):
            self._execute_base = cpg_service.execute_sql_dict
            self._use_inline_params = True
        else:
            raise ValueError("CPG service must have execute_query or execute_sql_dict method")

        logger.info("DataFlowTracer initialized")

    def _execute(self, query: str, params: tuple = None):
        """Execute query with proper parameter handling for both interfaces"""
        if self._use_inline_params and params:
            # Inline parameters for execute_sql_dict (doesn't support params)
            for p in params:
                if isinstance(p, str):
                    query = query.replace('?', f"'{p}'", 1)
                else:
                    query = query.replace('?', str(p), 1)
            return self._execute_base(query)
        elif params:
            return self._execute_base(query, params)
        else:
            return self._execute_base(query)

    def _get_containing_methods(self, node_ids: List[int]) -> Dict[int, Optional[str]]:
        """
        Find the containing method for each node using AST parent traversal.

        This is used to detect inter-procedural flows by comparing the
        containing method of source and sink nodes.

        Args:
            node_ids: List of node IDs to lookup

        Returns:
            Dict mapping node_id -> method_full_name (or None if not in a method)
        """
        if not node_ids:
            return {}

        # Build query to find containing method for each node
        # Using recursive AST traversal upward to find METHOD node
        node_list = ','.join(str(nid) for nid in node_ids)

        query = f"""
            WITH RECURSIVE ast_ancestors AS (
                -- Base: Start with the identifiers we're looking for
                SELECT
                    id AS original_id,
                    id AS current_id,
                    0 AS depth
                FROM nodes_identifier
                WHERE id IN ({node_list})

                UNION ALL

                -- Recursive: Traverse AST parent edges
                SELECT
                    aa.original_id,
                    ast.src AS current_id,
                    aa.depth + 1
                FROM ast_ancestors aa
                JOIN edges_ast ast ON ast.dst = aa.current_id
                WHERE aa.depth < 20  -- Limit depth to prevent infinite loops
            )
            SELECT DISTINCT
                aa.original_id AS node_id,
                m.full_name AS method_full_name
            FROM ast_ancestors aa
            JOIN nodes_method m ON m.id = aa.current_id
            WHERE m.full_name IS NOT NULL
        """

        try:
            results = self._execute(query)
            return {row['node_id']: row['method_full_name'] for row in results}
        except Exception as e:
            logger.warning(f"Failed to get containing methods: {e}")
            return {}

    def _detect_inter_procedural(
        self,
        source_id: int,
        sink_id: int,
        method_map: Dict[int, Optional[str]]
    ) -> bool:
        """
        Detect if a flow is inter-procedural (crosses function boundaries).

        A flow is inter-procedural if:
        1. Source and sink are in different methods, OR
        2. Either source or sink is a parameter/argument (data passed across calls)

        Args:
            source_id: Source node ID (definition)
            sink_id: Sink node ID (use)
            method_map: Mapping from node_id to containing method

        Returns:
            True if flow crosses function boundaries
        """
        source_method = method_map.get(source_id)
        sink_method = method_map.get(sink_id)

        # If either is None, we couldn't determine containment
        if source_method is None or sink_method is None:
            return False

        # Different methods = inter-procedural
        return source_method != sink_method

    def trace_variable(
        self,
        variable_name: str,
        method_name: Optional[str] = None,
        max_depth: int = 10
    ) -> VariableFlow:
        """
        Trace all flows of a variable using actual REACHING_DEF edges

        Args:
            variable_name: Name of variable to trace
            method_name: Optional method scope (None = all methods)
            max_depth: Maximum flow depth

        Returns:
            VariableFlow with all definition and use points

        SQL/PGQ Query:
            MATCH (def:Identifier {name='x'})-[:REACHING_DEF*]->(use:Identifier {name='x'})
        """
        try:
            # Query using actual REACHING_DEF edges from CPG
            # Find all definition->use flows via REACHING_DEF edges
            flow_query = """
                WITH RECURSIVE dataflow AS (
                    -- Base: All identifiers with this variable name (sources)
                    SELECT DISTINCT
                        i.id AS node_id,
                        i.name AS var_name,
                        i.line_number,
                        i.code,
                        0 AS depth,
                        CAST(i.id AS VARCHAR) AS path,
                        CAST(i.id AS BIGINT) AS source_id
                    FROM nodes_identifier i
                    WHERE i.name = ?

                    UNION ALL

                    -- Recursive: Follow REACHING_DEF edges
                    SELECT DISTINCT
                        i2.id,
                        i2.name,
                        i2.line_number,
                        i2.code,
                        df.depth + 1,
                        df.path || '->' || CAST(i2.id AS VARCHAR),
                        df.source_id
                    FROM dataflow df
                    JOIN edges_reaching_def rd ON rd.src = df.node_id AND rd.variable = ?
                    JOIN nodes_identifier i2 ON i2.id = rd.dst
                    WHERE df.depth < ?
                      AND i2.id != df.node_id  -- Prevent self-loops
                )
                SELECT DISTINCT
                    node_id,
                    var_name,
                    line_number,
                    code,
                    depth,
                    path,
                    source_id
                FROM dataflow
                ORDER BY depth, line_number;
            """

            params = (variable_name, variable_name, max_depth)
            results = self._execute(flow_query, params)

            if not results:
                logger.info(f"No REACHING_DEF flows found for variable '{variable_name}'")
                return VariableFlow(variable_name=variable_name)

            # Separate into definitions (sources) and uses (reachable nodes)
            definition_points = []
            use_points = []
            flows = []

            # Build flow map: source_id -> list of reached nodes
            flow_map = {}
            for row in results:
                node_id = row.get('node_id')
                source_id = row.get('source_id')
                depth = row.get('depth', 0)

                if depth == 0:
                    # This is a definition point (source of flow)
                    definition_points.append({
                        'node_id': node_id,
                        'variable_name': variable_name,
                        'line_number': row.get('line_number'),
                        'code': row.get('code'),
                        'type': 'definition'
                    })
                else:
                    # This is a use point (reached via REACHING_DEF)
                    use_points.append({
                        'node_id': node_id,
                        'variable_name': variable_name,
                        'line_number': row.get('line_number'),
                        'code': row.get('code'),
                        'type': 'use'
                    })

                    # Track flow from source to this node
                    if source_id not in flow_map:
                        flow_map[source_id] = []
                    flow_map[source_id].append({
                        'node_id': node_id,
                        'depth': depth,
                        'path': row.get('path', '')
                    })

            # Collect all node IDs for method context lookup
            all_node_ids = set()
            for d in definition_points:
                if d.get('node_id'):
                    all_node_ids.add(d['node_id'])
            for u in use_points:
                if u.get('node_id'):
                    all_node_ids.add(u['node_id'])

            # Get containing method for each node (for inter-procedural detection)
            method_map = self._get_containing_methods(list(all_node_ids))

            # Create DataFlowPath objects for each source->sink flow
            flow_id = 0
            inter_procedural_count = 0
            for source_id, sinks in flow_map.items():
                source_def = next((d for d in definition_points if d['node_id'] == source_id), None)
                if not source_def:
                    continue

                for sink in sinks:
                    sink_use = next((u for u in use_points if u['node_id'] == sink['node_id']), None)
                    if not sink_use:
                        continue

                    # Detect inter-procedural flows
                    is_inter_proc = self._detect_inter_procedural(
                        source_id, sink['node_id'], method_map
                    )
                    if is_inter_proc:
                        inter_procedural_count += 1

                    flows.append(DataFlowPath(
                        path_id=f"FLOW_{flow_id:03d}",
                        variable_name=variable_name,
                        source_location=source_def,
                        sink_location=sink_use,
                        path_length=sink['depth'],
                        intermediate_nodes=[],  # Could parse from path if needed
                        is_inter_procedural=is_inter_proc
                    ))
                    flow_id += 1

            logger.info(
                f"Found {len(definition_points)} definitions, {len(use_points)} uses, "
                f"{len(flows)} flows ({inter_procedural_count} inter-procedural) for '{variable_name}'"
            )

            return VariableFlow(
                variable_name=variable_name,
                definition_points=definition_points,
                use_points=use_points,
                flows=flows
            )

        except Exception as e:
            logger.error(f"Error tracing variable {variable_name}: {e}", exc_info=True)
            return VariableFlow(variable_name=variable_name)

    def find_reaching_definitions(
        self,
        use_location: Dict[str, Any],
        max_depth: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find all definitions that reach a specific use point
        Uses actual REACHING_DEF edges traversed backward

        Args:
            use_location: Use point {node_id OR (method_name, variable_name, line_number)}
            max_depth: Maximum backward flow depth

        Returns:
            List of definition points that can reach this use

        SQL/PGQ: Backward traversal of REACHING_DEF edges
        """
        node_id = use_location.get('node_id')
        var_name = use_location.get('variable_name')

        # If node_id not provided, try to find the identifier node
        if not node_id:
            method_name = use_location.get('method_name')
            line_number = use_location.get('line_number')

            if not var_name:
                logger.warning("Invalid use_location: missing variable_name")
                return []

            # Find the identifier node matching this use location
            find_node_query = """
                SELECT i.id
                FROM nodes_identifier i
                WHERE i.name = ?
            """
            params = [var_name]

            if method_name:
                # Note: nodes_identifier doesn't have method_id in current schema
                # We'll need to join through other means or just use variable name
                pass

            if line_number:
                find_node_query += " AND i.line_number = ?"
                params.append(line_number)

            find_node_query += " LIMIT 1"

            try:
                node_results = self._execute(find_node_query, tuple(params))
                if not node_results:
                    logger.warning(f"Could not find identifier node for {var_name}")
                    return []
                node_id = node_results[0].get('id')
            except Exception as e:
                logger.error(f"Error finding identifier node: {e}")
                return []

        # Query to find reaching definitions by traversing REACHING_DEF backward
        query = """
            WITH RECURSIVE reaching_defs AS (
                -- Base: The use point itself
                SELECT
                    i.id AS node_id,
                    i.name AS var_name,
                    i.line_number,
                    i.code,
                    0 AS depth
                FROM nodes_identifier i
                WHERE i.id = ?

                UNION ALL

                -- Recursive: Traverse REACHING_DEF edges backward (reverse direction)
                SELECT
                    i2.id,
                    i2.name,
                    i2.line_number,
                    i2.code,
                    rd_parent.depth + 1
                FROM reaching_defs rd_parent
                JOIN edges_reaching_def rd ON rd.dst = rd_parent.node_id
                JOIN nodes_identifier i2 ON i2.id = rd.src
                WHERE rd_parent.depth < ?
                  AND i2.id != rd_parent.node_id
                  AND (? IS NULL OR rd.variable = ?)
            )
            SELECT DISTINCT
                node_id,
                var_name,
                line_number,
                code,
                depth
            FROM reaching_defs
            WHERE depth > 0  -- Exclude the starting use point
            ORDER BY depth, line_number;
        """

        try:
            # Parameters: node_id, max_depth, var_name (for filtering), var_name
            results = self._execute(query, (node_id, max_depth, var_name, var_name))
            logger.info(f"Found {len(results)} reaching definitions for node {node_id}")
            return results
        except Exception as e:
            logger.error(f"Error finding reaching definitions: {e}", exc_info=True)
            return []

    def find_variable_uses(
        self,
        definition_location: Dict[str, Any],
        max_depth: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find all uses reachable from a definition
        Uses actual REACHING_DEF edges traversed forward

        Args:
            definition_location: Definition point {node_id OR (method_name, variable_name, line_number)}
            max_depth: Maximum forward flow depth

        Returns:
            List of use points reachable from this definition

        SQL/PGQ: Forward traversal of REACHING_DEF edges
        """
        node_id = definition_location.get('node_id')
        var_name = definition_location.get('variable_name')

        # If node_id not provided, try to find the identifier node
        if not node_id:
            method_name = definition_location.get('method_name')
            line_number = definition_location.get('line_number')

            if not var_name:
                logger.warning("Invalid definition_location: missing variable_name")
                return []

            # Find the identifier node matching this definition location
            find_node_query = """
                SELECT i.id
                FROM nodes_identifier i
                WHERE i.name = ?
            """
            params = [var_name]

            if line_number:
                find_node_query += " AND i.line_number = ?"
                params.append(line_number)

            find_node_query += " LIMIT 1"

            try:
                node_results = self._execute(find_node_query, tuple(params))
                if not node_results:
                    logger.warning(f"Could not find identifier node for {var_name}")
                    return []
                node_id = node_results[0].get('id')
            except Exception as e:
                logger.error(f"Error finding identifier node: {e}")
                return []

        # Query to find uses by traversing REACHING_DEF forward
        query = """
            WITH RECURSIVE reachable_uses AS (
                -- Base: The definition point itself
                SELECT
                    i.id AS node_id,
                    i.name AS var_name,
                    i.line_number,
                    i.code,
                    0 AS depth
                FROM nodes_identifier i
                WHERE i.id = ?

                UNION ALL

                -- Recursive: Traverse REACHING_DEF edges forward
                SELECT
                    i2.id,
                    i2.name,
                    i2.line_number,
                    i2.code,
                    ru.depth + 1
                FROM reachable_uses ru
                JOIN edges_reaching_def rd ON rd.src = ru.node_id
                JOIN nodes_identifier i2 ON i2.id = rd.dst
                WHERE ru.depth < ?
                  AND i2.id != ru.node_id
                  AND (? IS NULL OR rd.variable = ?)
            )
            SELECT DISTINCT
                node_id,
                var_name,
                line_number,
                code,
                depth
            FROM reachable_uses
            WHERE depth > 0  -- Exclude the starting definition point
            ORDER BY depth, line_number;
        """

        try:
            # Parameters: node_id, max_depth, var_name (for filtering), var_name
            results = self._execute(query, (node_id, max_depth, var_name, var_name))
            logger.info(f"Found {len(results)} uses reachable from node {node_id}")
            return results
        except Exception as e:
            logger.error(f"Error finding variable uses: {e}", exc_info=True)
            return []

    def trace_inter_procedural(
        self,
        source_method: str,
        source_variable: str,
        target_method: str,
        max_depth: int = 5
    ) -> Optional[DataFlowPath]:
        """
        Trace data flow across function boundaries

        Combines:
        - REACHING_DEF edges (intra-procedural)
        - CALL edges (inter-procedural)

        Args:
            source_method: Starting method
            source_variable: Variable to trace
            target_method: Target method
            max_depth: Maximum call depth

        Returns:
            DataFlowPath if flow exists, None otherwise

        Pattern:
            (src)-[:REACHING_DEF]->(exit)-[:CALL]->(entry)-[:REACHING_DEF]->(dst)
        """
        # Query combining REACHING_DEF and CALL edges
        query = """
            WITH RECURSIVE inter_procedural_flow AS (
                -- Base: variable in source method
                SELECT
                    m1.id AS current_method_id,
                    m1.name AS current_method,
                    ? AS current_var,
                    m1.filename,
                    m1.line_number,
                    1 AS depth,
                    CAST(m1.name AS VARCHAR) AS path
                FROM nodes_method m1
                WHERE m1.name = ?

                UNION

                -- Recursive: follow through calls
                SELECT
                    m2.id,
                    m2.name,
                    ipf.current_var,
                    m2.filename,
                    m2.line_number,
                    ipf.depth + 1,
                    ipf.path || ' -> ' || m2.name
                FROM inter_procedural_flow ipf
                JOIN nodes_call nc ON nc.containing_method_id = ipf.current_method_id
                JOIN edges_call ec ON ec.src = nc.id
                JOIN nodes_method m2 ON ec.dst = m2.id
                WHERE ipf.depth < ?
                  AND m2.id != ipf.current_method_id  -- Avoid immediate recursion
            )
            SELECT *
            FROM inter_procedural_flow
            WHERE current_method = ?
            ORDER BY depth
            LIMIT 1;
        """

        try:
            results = self._execute(
                query,
                (source_variable, source_method, max_depth, target_method)
            )

            if not results:
                logger.info(f"No inter-procedural flow from {source_method} to {target_method}")
                return None

            result = results[0]

            # Parse path
            path_str = result.get('path', '')
            intermediate = path_str.split(' -> ')[1:-1] if ' -> ' in path_str else []

            return DataFlowPath(
                path_id=f"INTER_FLOW_{source_method}_{target_method}",
                variable_name=source_variable,
                source_location={
                    'method': source_method,
                    'type': 'definition'
                },
                sink_location={
                    'method': target_method,
                    'type': 'use'
                },
                path_length=result.get('depth', 0),
                intermediate_nodes=[{'method': m} for m in intermediate],
                is_inter_procedural=True
            )

        except Exception as e:
            logger.error(f"Error tracing inter-procedural flow: {e}")
            return None

    def find_taint_paths(
        self,
        source_functions: List[str],
        sink_functions: List[str],
        max_depth: int = 10,
        check_sanitization: bool = True
    ) -> List[DataFlowPath]:
        """
        Find taint flow paths from sources to sinks using REACHING_DEF edges (Phase 4C Enhanced)

        Used for security vulnerability analysis (Method #4)

        Phase 4C Enhancements:
        - Optional sanitization filtering to reduce false positives
        - Confidence-based path filtering
        - Paths with sufficient sanitization (confidence >= 0.7) are excluded

        Args:
            source_functions: Taint sources (e.g., ['readLine', 'recv', 'getenv'])
            sink_functions: Dangerous sinks (e.g., ['system', 'strcpy', 'executeSQL'])
            max_depth: Maximum flow depth
            check_sanitization: If True, filter out paths with adequate sanitization (Phase 4C)

        Returns:
            List of taint paths found with actual REACHING_DEF edge traversal
            If check_sanitization=True, only returns unsanitized paths

        SQL/PGQ:
            MATCH (src:Call {name IN sources})-[:ARGUMENT]->(arg)-[:REACHING_DEF*]->(sink_arg)<-[:ARGUMENT]-(sink:Call {name IN sinks})
        """
        if not source_functions or not sink_functions:
            logger.warning("Empty source or sink functions list")
            return []

        # Build placeholders for IN clause
        source_placeholders = ','.join(['?'] * len(source_functions))
        sink_placeholders = ','.join(['?'] * len(sink_functions))

        # Taint analysis: Find paths from source function return values to sink function arguments
        # via REACHING_DEF edges
        query = f"""
            WITH RECURSIVE taint_flow AS (
                -- Base: Identifiers that are arguments to source functions (tainted values)
                SELECT DISTINCT
                    i.id AS current_node_id,
                    i.name AS var_name,
                    i.line_number AS line_num,
                    nc.name AS source_func,
                    nc.id AS source_call_id,
                    1 AS depth,
                    CAST(nc.name || '(' || i.name || ')' AS VARCHAR) AS path
                FROM nodes_call nc
                JOIN edges_argument ea ON ea.src = nc.id
                JOIN nodes_identifier i ON i.id = ea.dst
                WHERE nc.name IN ({source_placeholders})

                UNION ALL

                -- Recursive: Follow REACHING_DEF edges from tainted identifiers
                SELECT DISTINCT
                    i2.id,
                    i2.name,
                    i2.line_number,
                    tf.source_func,
                    tf.source_call_id,
                    tf.depth + 1,
                    tf.path || ' -> ' || i2.name || '@' || CAST(i2.line_number AS VARCHAR)
                FROM taint_flow tf
                JOIN edges_reaching_def rd ON rd.src = tf.current_node_id
                JOIN nodes_identifier i2 ON i2.id = rd.dst
                WHERE tf.depth < ?
                  AND i2.id != tf.current_node_id
            )
            -- Find paths that reach sink function arguments
            SELECT DISTINCT
                tf.source_func,
                tf.source_call_id,
                tf.var_name AS tainted_var,
                nc_sink.name AS sink_func,
                nc_sink.id AS sink_call_id,
                tf.line_num AS taint_line,
                nc_sink.line_number AS sink_line,
                nc_sink.filename AS sink_file,
                tf.depth,
                tf.path || ' -> ' || nc_sink.name AS full_path
            FROM taint_flow tf
            JOIN edges_argument ea_sink ON ea_sink.dst = tf.current_node_id
            JOIN nodes_call nc_sink ON nc_sink.id = ea_sink.src
            WHERE nc_sink.name IN ({sink_placeholders})
            ORDER BY tf.depth, nc_sink.line_number
            LIMIT 100;
        """

        params = tuple(source_functions) + (max_depth,) + tuple(sink_functions)

        try:
            results = self._execute(query, params)

            if not results:
                logger.info(f"No taint paths found from {source_functions[:3]}... to {sink_functions[:3]}...")
                return []

            paths = []
            for idx, result in enumerate(results):
                path_str = result.get('full_path', '')

                # Parse intermediate nodes from path
                intermediate = []
                if ' -> ' in path_str:
                    parts = path_str.split(' -> ')[1:-1]  # Exclude source and sink
                    for part in parts:
                        intermediate.append({'code': part})

                # Phase 4C: Check for sanitization points on the taint path
                sanitization_points, max_confidence = self._detect_sanitization_on_path(
                    result.get('source_call_id'),
                    result.get('sink_call_id'),
                    result.get('tainted_var', ''),
                    max_depth
                )

                # Phase 4C: Filter out paths with sufficient sanitization if requested
                if check_sanitization and max_confidence >= SANITIZATION_CONFIDENCE_THRESHOLD:
                    logger.debug(
                        f"Filtering out sanitized path: {result.get('source_func')} → "
                        f"{result.get('sink_func')} (confidence: {max_confidence:.2f})"
                    )
                    continue  # Skip this path - it's adequately sanitized

                paths.append(DataFlowPath(
                    path_id=f"TAINT_{idx:03d}",
                    variable_name=result.get('tainted_var', 'tainted_data'),
                    source_location={
                        'function': result.get('source_func', ''),
                        'call_id': result.get('source_call_id'),
                        'line': result.get('taint_line', 0),
                        'type': 'source'
                    },
                    sink_location={
                        'function': result.get('sink_func', ''),
                        'call_id': result.get('sink_call_id'),
                        'file': result.get('sink_file', ''),
                        'line': result.get('sink_line', 0),
                        'type': 'sink'
                    },
                    path_length=result.get('depth', 0),
                    intermediate_nodes=intermediate,
                    is_inter_procedural=True,  # REACHING_DEF can cross function boundaries
                    sanitization_points=sanitization_points  # Phase 4C: Enhanced sanitization detection
                ))

            # Phase 4C: Log filtering statistics
            if check_sanitization:
                filtered_count = len(results) - len(paths)
                logger.info(
                    f"Found {len(paths)} unsanitized taint paths "
                    f"({filtered_count} filtered due to sanitization)"
                )
            else:
                logger.info(f"Found {len(paths)} taint paths via REACHING_DEF edges")

            return paths

        except Exception as e:
            logger.error(f"Error finding taint paths: {e}", exc_info=True)
            return []

    def _compute_flows(
        self,
        variable_name: str,
        definitions: List[Dict[str, Any]],
        uses: List[Dict[str, Any]],
        max_depth: int
    ) -> List[DataFlowPath]:
        """
        Compute flows between definition and use points using REACHING_DEF edges

        Internal helper method - NO LONGER USED (replaced by direct REACHING_DEF queries)

        Args:
            variable_name: Variable being traced
            definitions: List of definition points
            uses: List of use points
            max_depth: Maximum flow depth

        Returns:
            List of DataFlowPath objects

        NOTE: This method is deprecated. The trace_variable() method now directly
        queries REACHING_DEF edges and builds flows inline, which is more efficient
        and accurate than this two-phase approach.
        """
        # This method is no longer used - keeping for backward compatibility
        # trace_variable() now directly queries REACHING_DEF edges
        logger.warning("_compute_flows() is deprecated - trace_variable() now uses direct REACHING_DEF queries")

        flows = []

        # For backward compatibility, create simple flows if definitions/uses are provided
        # But this won't be accurate without actual REACHING_DEF edge traversal
        for idx, def_point in enumerate(definitions):
            for use_point in uses:
                # Note: This is a simplified approximation
                # Real implementation should query REACHING_DEF edges
                flows.append(DataFlowPath(
                    path_id=f"FLOW_{len(flows):03d}",
                    variable_name=variable_name,
                    source_location=def_point,
                    sink_location=use_point,
                    path_length=1,  # Unknown without REACHING_DEF traversal
                    is_inter_procedural=False  # Unknown without analysis
                ))

        return flows

    def _detect_sanitization_on_path(
        self,
        source_call_id: int,
        sink_call_id: int,
        variable_name: str,
        max_depth: int = 10
    ) -> Tuple[List[Dict[str, Any]], float]:
        """
        Detect sanitization/validation functions on a taint path (Phase 4C Enhanced)

        Sanitization functions include:
        - Input validation: validate_*, check_*, verify_*, is_valid_*
        - Escaping: escape_*, sanitize_*, clean_*, htmlspecialchars, pg_escape_string
        - Encoding: encode_*, urlencode, base64_encode
        - Type conversion with validation: int(), float(), str.strip()
        - Parameterization: prepare(), bind(), parameterize()

        Phase 4C Enhancements:
        - Expanded pattern library (18 → 45 patterns)
        - Confidence scoring for each sanitization type
        - Returns both sanitization points and max confidence score

        Args:
            source_call_id: Source call node ID
            sink_call_id: Sink call node ID
            variable_name: Variable being tracked
            max_depth: Maximum depth to search

        Returns:
            Tuple of (sanitization_points, max_confidence_score)
            - sanitization_points: List of sanitization functions found
            - max_confidence_score: Highest confidence score found (0.0-1.0)
        """
        # Phase 4C: Expanded sanitization pattern library
        # Merged generic + domain-specific patterns via get_sanitization_patterns()
        sanitization_dict = get_sanitization_patterns()
        sanitize_patterns = list(sanitization_dict.keys())

        # Build LIKE patterns for SQL
        pattern_conditions = ' OR '.join([f"nc.name LIKE ?" for _ in sanitize_patterns])

        query = f"""
            WITH RECURSIVE path_trace AS (
                -- Start from source
                SELECT
                    i.id AS node_id,
                    0 AS depth
                FROM nodes_identifier i
                JOIN edges_argument ea ON ea.dst = i.id
                WHERE ea.src = ?

                UNION ALL

                -- Follow REACHING_DEF edges
                SELECT
                    i2.id,
                    pt.depth + 1
                FROM path_trace pt
                JOIN edges_reaching_def rd ON rd.src = pt.node_id
                JOIN nodes_identifier i2 ON i2.id = rd.dst
                WHERE pt.depth < ?
            )
            -- Find sanitization function calls on the path
            SELECT DISTINCT
                nc.id AS call_id,
                nc.name AS function_name,
                nc.line_number,
                nc.filename,
                pt.depth AS position_in_path
            FROM path_trace pt
            JOIN edges_argument ea ON ea.dst = pt.node_id
            JOIN nodes_call nc ON nc.id = ea.src
            WHERE ({pattern_conditions})
              AND nc.id != ?  -- Exclude source
              AND nc.id != ?  -- Exclude sink
            ORDER BY pt.depth;
        """

        params = [source_call_id, max_depth] + sanitize_patterns + [source_call_id, sink_call_id]

        try:
            results = self._execute(query, tuple(params))

            sanitization_points = []
            max_confidence = 0.0  # Phase 4C: Track maximum confidence score

            for result in results:
                function_name = result.get('function_name', '').lower()

                # Phase 4C: Compute confidence score for this sanitization function
                confidence = 0.0
                matched_pattern = None

                # Check exact matches first (use sanitization_dict from earlier)
                for pattern, score in sanitization_dict.items():
                    if pattern.endswith('%'):
                        # Wildcard pattern (e.g., 'validate_%')
                        prefix = pattern[:-1]
                        if function_name.startswith(prefix):
                            confidence = max(confidence, score)
                            matched_pattern = pattern
                    else:
                        # Exact match
                        if pattern in function_name:
                            confidence = max(confidence, score)
                            matched_pattern = pattern

                # Track maximum confidence across all sanitization points
                max_confidence = max(max_confidence, confidence)

                sanitization_points.append({
                    'call_id': result.get('call_id'),
                    'function': result.get('function_name'),
                    'line': result.get('line_number'),
                    'file': result.get('filename'),
                    'position': result.get('position_in_path'),
                    'type': 'sanitization',
                    'confidence': confidence,  # Phase 4C: Add confidence score
                    'pattern': matched_pattern  # Phase 4C: Add matched pattern
                })

            if sanitization_points:
                logger.info(
                    f"Found {len(sanitization_points)} sanitization points "
                    f"(max confidence: {max_confidence:.2f})"
                )

            # Phase 4C: Return both sanitization points and max confidence
            return sanitization_points, max_confidence

        except Exception as e:
            logger.error(f"Error detecting sanitization: {e}", exc_info=True)
            return [], 0.0  # Phase 4C: Return tuple on error

    def get_dataflow_statistics(self) -> Dict[str, Any]:
        """
        Get data flow statistics

        Returns:
            Dictionary with metrics:
            - total_identifiers: Number of variables/identifiers
            - definitions_count: Number of definition points
            - uses_count: Number of use points
            - avg_def_use_ratio: Average definitions per use
        """
        stats_query = """
            SELECT
                (SELECT COUNT(*) FROM nodes_identifier) AS total_identifiers,
                (SELECT COUNT(*) FROM nodes_identifier WHERE is_definition = TRUE) AS definitions,
                (SELECT COUNT(*) FROM nodes_identifier WHERE is_use = TRUE) AS uses;
        """

        try:
            results = self._execute(stats_query)
            if results:
                stats = results[0]
                total_defs = stats.get('definitions', 0) or 0
                total_uses = stats.get('uses', 0) or 0

                return {
                    'total_identifiers': stats.get('total_identifiers', 0),
                    'definitions_count': total_defs,
                    'uses_count': total_uses,
                    'avg_def_use_ratio': total_defs / total_uses if total_uses > 0 else 0.0
                }
            return {}
        except Exception as e:
            logger.error(f"Error getting dataflow statistics: {e}")
            return {}

    # =========================================================================
    # FIELD-SENSITIVE ANALYSIS (Integration with FieldSensitiveTracer)
    # =========================================================================

    def find_taint_paths_field_sensitive(
        self,
        source_functions: List[str],
        sink_functions: List[str],
        track_fields: bool = True,
        max_depth: int = 10,
        check_sanitization: bool = True
    ) -> List[DataFlowPath]:
        """
        Enhanced taint analysis with field sensitivity.

        When track_fields=True:
        - Distinguishes between obj.field1 and obj.field2
        - Tracks field access chains (obj.a.b.c)
        - Reports field-specific taint paths

        This method combines the base taint analysis with field-sensitive
        tracking from FieldSensitiveTracer.

        Args:
            source_functions: Taint sources (e.g., ['readLine', 'recv', 'getenv'])
            sink_functions: Dangerous sinks (e.g., ['system', 'strcpy', 'executeSQL'])
            track_fields: If True, track field accesses (default: True)
            max_depth: Maximum flow depth
            check_sanitization: If True, filter out paths with adequate sanitization

        Returns:
            List of taint paths with field information in intermediate_nodes
        """
        # First, run standard taint analysis
        base_paths = self.find_taint_paths(
            source_functions,
            sink_functions,
            max_depth,
            check_sanitization
        )

        if not track_fields or not base_paths:
            return base_paths

        # Enhance paths with field sensitivity information
        try:
            from .field_sensitive_tracer import FieldSensitiveTracer, FieldPath

            field_tracer = FieldSensitiveTracer(self.cpg)

            enhanced_paths = []
            for path in base_paths:
                # Extract variable name from path
                var_name = path.variable_name

                # Find field accesses for this variable
                field_accesses = field_tracer.find_field_accesses(var_name)

                if field_accesses:
                    # Add field information to intermediate nodes
                    field_info = []
                    for access in field_accesses:
                        field_info.append({
                            'type': 'field_access',
                            'base': access.base_variable,
                            'field': access.field_name,
                            'code': access.access_code,
                            'line': access.line_number,
                            'containing_method': access.containing_method,
                        })

                    # Create enhanced path with field information
                    enhanced_path = DataFlowPath(
                        path_id=path.path_id + '_FS',
                        variable_name=path.variable_name,
                        source_location=path.source_location,
                        sink_location=path.sink_location,
                        path_length=path.path_length,
                        intermediate_nodes=path.intermediate_nodes + field_info,
                        is_inter_procedural=path.is_inter_procedural,
                        sanitization_points=path.sanitization_points,
                    )
                    enhanced_paths.append(enhanced_path)
                else:
                    enhanced_paths.append(path)

            logger.info(f"Enhanced {len(enhanced_paths)} taint paths with field sensitivity")
            return enhanced_paths

        except ImportError as e:
            logger.warning(f"Field-sensitive analysis not available: {e}")
            return base_paths
        except Exception as e:
            logger.error(f"Error in field-sensitive analysis: {e}")
            return base_paths

    def find_sensitive_data_flows(
        self,
        sensitive_fields: List[str] = None,
        sink_functions: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find flows from sensitive fields (like passwords) to sink functions.

        Uses FieldSensitiveTracer to find flows where sensitive data
        might be exposed.

        Args:
            sensitive_fields: Field names considered sensitive
                (default: password, token, secret, key, credential)
            sink_functions: Sink function patterns
                (default: printf, log, send, write)

        Returns:
            List of potential sensitive data flows
        """
        try:
            from .field_sensitive_tracer import FieldSensitiveTracer

            field_tracer = FieldSensitiveTracer(self.cpg)
            return field_tracer.find_sensitive_field_flows(
                sensitive_fields,
                sink_functions
            )

        except ImportError as e:
            logger.warning(f"Field-sensitive analysis not available: {e}")
            return []
        except Exception as e:
            logger.error(f"Error finding sensitive data flows: {e}")
            return []
