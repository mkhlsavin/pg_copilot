"""
Patch Data Flow Impact Analyzer

Extends the base DataFlowTracer to analyze patch-specific data flow impact:
- New taint paths introduced by the patch
- Sanitization bypass detection
- Sensitive data flow tracking

Phase: Impact Analyzers (Phase 2)
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from src.patch_review.models import (
    ChangedMethod,
    ChangeType,
    DeltaCPG,
    SanitizationBypass,
    Severity,
    TaintPathFinding,
)

logger = logging.getLogger(__name__)


# Common taint sources (user input, external data)
DEFAULT_TAINT_SOURCES = [
    'recv', 'read', 'fread', 'fgets', 'gets', 'scanf', 'fscanf',
    'getenv', 'getchar', 'fgetc', 'getline',
    'PQgetvalue', 'PQescapeString',  # PostgreSQL
    'socket', 'accept', 'recvfrom', 'recvmsg',
    'input', 'raw_input',  # Python
    'request.GET', 'request.POST', 'request.params',  # Web frameworks
]

# Common taint sinks (dangerous operations)
DEFAULT_TAINT_SINKS = [
    'system', 'popen', 'exec', 'execl', 'execlp', 'execv', 'execvp',
    'strcpy', 'strcat', 'sprintf', 'vsprintf',
    'SPI_execute', 'SPI_exec', 'exec_simple_query',  # PostgreSQL SQL
    'free', 'pfree',  # Memory operations
    'open', 'fopen', 'unlink', 'remove',  # File operations
    'eval', 'exec',  # Dynamic code execution
    'query', 'execute', 'raw_query',  # Database operations
]

# Sanitization function patterns with confidence scores
SANITIZATION_PATTERNS = {
    # High confidence (1.0) - Strong sanitization
    'parameterize': 1.0,
    'prepare': 1.0,
    'bind_param': 1.0,
    'escape_string': 0.9,
    'pg_escape': 0.9,
    'htmlspecialchars': 0.9,

    # Medium-high confidence (0.8)
    'validate': 0.8,
    'sanitize': 0.8,
    'verify': 0.8,
    'check': 0.7,
    'escape': 0.7,

    # Medium confidence (0.6)
    'filter': 0.6,
    'clean': 0.6,
    'encode': 0.6,

    # Lower confidence (0.4)
    'trim': 0.4,
    'strip': 0.4,
    'intval': 0.5,
    'floatval': 0.5,
}

# Minimum confidence threshold for adequate sanitization
SANITIZATION_THRESHOLD = 0.7


@dataclass
class DataFlowChange:
    """Represents a change in data flow"""
    change_type: str  # "new_path", "removed_sanitization", "new_source", "new_sink"
    description: str
    source: Optional[str] = None
    sink: Optional[str] = None
    path: List[str] = None
    severity: Severity = Severity.MEDIUM


class PatchDataFlowAnalyzer:
    """
    Analyzes data flow impact of patch changes.

    Computes:
    - New taint paths (source to sink without sanitization)
    - Sanitization bypass (removed or bypassed sanitization)
    - Sensitive data flow tracking
    """

    def __init__(
        self,
        conn: Any,
        delta_cpg: Optional[DeltaCPG] = None,
        taint_sources: Optional[List[str]] = None,
        taint_sinks: Optional[List[str]] = None
    ):
        """
        Initialize the analyzer.

        Args:
            conn: DuckDB connection or CPGQueryService
            delta_cpg: Optional DeltaCPG for patch-specific analysis
            taint_sources: Custom taint source functions
            taint_sinks: Custom taint sink functions
        """
        self.conn = conn
        self.delta = delta_cpg
        self.taint_sources = taint_sources or DEFAULT_TAINT_SOURCES
        self.taint_sinks = taint_sinks or DEFAULT_TAINT_SINKS

        # Support multiple interfaces
        if hasattr(conn, 'execute'):
            self._execute = self._execute_duckdb
        elif hasattr(conn, 'execute_query'):
            self._execute = conn.execute_query
        elif hasattr(conn, 'execute_sql_dict'):
            self._execute = conn.execute_sql_dict
        else:
            self._execute = lambda q, p=None: []

        logger.info("PatchDataFlowAnalyzer initialized")

    def _execute_duckdb(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute query on DuckDB and return list of dicts."""
        try:
            if params:
                result = self.conn.execute(query, params)
            else:
                result = self.conn.execute(query)
            columns = [desc[0] for desc in result.description] if result.description else []
            rows = result.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.debug(f"Query failed: {e}")
            return []

    def analyze_dataflow_changes(
        self,
        patch: Any,  # PatchContext
        delta_cpg: DeltaCPG
    ) -> 'DataFlowAnalysisResult':
        """
        Analyze complete data flow impact of a patch.

        Args:
            patch: The patch context
            delta_cpg: Delta CPG with changes

        Returns:
            DataFlowAnalysisResult with all data flow findings
        """
        from . import DataFlowAnalysisResult
        from ..models import Finding, FindingCategory

        self.delta = delta_cpg

        # Find new taint paths
        new_taint_paths = self.analyze_new_taint_paths(patch.changed_methods)

        # Check for sanitization bypass
        bypasses = self.check_sanitization_bypass(patch.changed_methods)

        # Track sensitive data flow
        sensitive_findings = self.track_sensitive_data_flow(patch.changed_methods)

        # Convert to findings
        findings = []
        for path in new_taint_paths:
            findings.append(Finding(
                category=FindingCategory.SECURITY,
                severity=path.severity,
                title=f"Taint Path: {path.source_type} → {path.sink_type}",
                description=path.description,
                location=f"{path.source_file}:{path.source_line}",
                recommendation=path.recommendation,
                confidence=path.confidence,
                cwe_id=path.cwe_id
            ))

        return DataFlowAnalysisResult(
            new_taint_paths=new_taint_paths,
            sanitization_bypasses=bypasses,
            sensitive_data_findings=sensitive_findings,
            findings=findings
        )

    def set_delta(self, delta_cpg: DeltaCPG):
        """Set or update the delta CPG"""
        self.delta = delta_cpg

    def analyze_new_taint_paths(
        self,
        changed_methods: List[ChangedMethod],
        max_depth: int = 10
    ) -> List[TaintPathFinding]:
        """
        Check if patch introduces new taint paths.

        A taint path is dangerous when:
        1. Data flows from a taint source to a taint sink
        2. There's no adequate sanitization on the path

        Args:
            changed_methods: List of changed methods
            max_depth: Maximum dataflow traversal depth

        Returns:
            List of new taint paths found
        """
        findings: List[TaintPathFinding] = []

        if not changed_methods:
            return findings

        logger.info(f"Analyzing taint paths for {len(changed_methods)} changed methods")

        # Get methods by change type
        added_methods = [m for m in changed_methods if m.change_type == ChangeType.ADDED]
        modified_methods = [m for m in changed_methods if m.change_type == ChangeType.MODIFIED]

        # Check for new taint sources in added/modified code
        new_sources = self._find_taint_sources_in_methods(
            [m.method_name for m in added_methods + modified_methods]
        )

        # Check for new taint sinks in added/modified code
        new_sinks = self._find_taint_sinks_in_methods(
            [m.method_name for m in added_methods + modified_methods]
        )

        # Find paths from sources to sinks
        for source_info in new_sources:
            for sink_info in new_sinks:
                path_finding = self._trace_taint_path(
                    source_info,
                    sink_info,
                    max_depth
                )

                if path_finding:
                    findings.append(path_finding)

        # Also check if changes create new paths to existing sinks
        for method in modified_methods:
            existing_paths = self._check_paths_through_method(
                method.method_name,
                max_depth
            )
            findings.extend(existing_paths)

        logger.info(f"Found {len(findings)} potential taint paths")
        return findings

    def check_sanitization_bypass(
        self,
        changed_methods: List[ChangedMethod]
    ) -> List[SanitizationBypass]:
        """
        Check if patch bypasses existing sanitization.

        Bypass scenarios:
        1. Sanitization function removed
        2. New path that skips sanitization
        3. Weakened validation logic

        Args:
            changed_methods: List of changed methods

        Returns:
            List of sanitization bypass findings
        """
        bypasses: List[SanitizationBypass] = []

        # Check for removed sanitization functions
        deleted_methods = [m for m in changed_methods if m.change_type == ChangeType.DELETED]

        for method in deleted_methods:
            # Check if this was a sanitization function
            confidence = self._get_sanitization_confidence(method.method_name)
            if confidence >= 0.5:  # Was likely a sanitization function
                # Find what sinks this protected
                protected_sinks = self._find_sinks_protected_by(method.method_name)

                if protected_sinks:
                    bypasses.append(SanitizationBypass(
                        bypass_id=f"BYPASS_{method.method_name}",
                        bypass_type="removed_sanitization",
                        affected_sink=', '.join(protected_sinks[:3]),
                        original_sanitization=method.method_name,
                        details=(
                            f"Sanitization function '{method.method_name}' was removed. "
                            f"This may expose {len(protected_sinks)} sink(s) to untrusted input."
                        ),
                        severity=Severity.HIGH if confidence >= 0.8 else Severity.MEDIUM
                    ))

        # Check for new bypass paths in modified methods
        modified_methods = [m for m in changed_methods if m.change_type == ChangeType.MODIFIED]

        for method in modified_methods:
            bypass = self._check_method_for_bypass(method)
            if bypass:
                bypasses.append(bypass)

        logger.info(f"Found {len(bypasses)} potential sanitization bypasses")
        return bypasses

    def track_sensitive_data_flow(
        self,
        changed_methods: List[ChangedMethod],
        sensitive_patterns: Optional[List[str]] = None
    ) -> List[DataFlowChange]:
        """
        Track how patch affects sensitive data flow.

        Sensitive data includes:
        - User credentials
        - Authentication tokens
        - PII (personally identifiable information)
        - Database credentials

        Args:
            changed_methods: List of changed methods
            sensitive_patterns: Patterns to identify sensitive data

        Returns:
            List of sensitive data flow changes
        """
        if sensitive_patterns is None:
            sensitive_patterns = [
                'password', 'passwd', 'secret', 'token', 'key', 'credential',
                'auth', 'session', 'cookie', 'ssn', 'credit_card', 'cvv',
                'private_key', 'api_key', 'access_token', 'refresh_token'
            ]

        changes: List[DataFlowChange] = []

        for method in changed_methods:
            # Check if method handles sensitive data
            sensitive_vars = self._find_sensitive_variables(
                method.method_name,
                sensitive_patterns
            )

            for var_info in sensitive_vars:
                # Check if this variable flows to unsafe locations
                unsafe_flows = self._trace_sensitive_data(
                    method.method_name,
                    var_info['name']
                )

                for flow in unsafe_flows:
                    changes.append(DataFlowChange(
                        change_type="sensitive_data_exposure",
                        description=(
                            f"Sensitive variable '{var_info['name']}' in method "
                            f"'{method.method_name}' may flow to {flow['destination']}"
                        ),
                        source=method.method_name,
                        sink=flow['destination'],
                        path=flow.get('path', []),
                        severity=Severity.HIGH
                    ))

        logger.info(f"Found {len(changes)} sensitive data flow changes")
        return changes

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _find_taint_sources_in_methods(
        self,
        method_names: List[str]
    ) -> List[Dict[str, Any]]:
        """Find taint source calls within given methods"""
        if not method_names:
            return []

        source_list = ','.join([f"'{s}'" for s in self.taint_sources])
        method_list = ','.join([f"'{m}'" for m in method_names])

        query = f"""
            SELECT DISTINCT
                nc.id AS call_id,
                nc.name AS source_function,
                nc.line_number,
                nc.filename,
                nm.name AS containing_method
            FROM nodes_call nc
            JOIN nodes_method nm ON nc.containing_method_id = nm.id
            WHERE nc.name IN ({source_list})
              AND nm.name IN ({method_list})
            LIMIT 50;
        """

        try:
            results = self._execute(query)
            return [
                {
                    'call_id': r.get('call_id'),
                    'function': r.get('source_function'),
                    'line': r.get('line_number'),
                    'file': r.get('filename'),
                    'method': r.get('containing_method')
                }
                for r in results
            ]
        except Exception as e:
            logger.warning(f"Error finding taint sources: {e}")
            return []

    def _find_taint_sinks_in_methods(
        self,
        method_names: List[str]
    ) -> List[Dict[str, Any]]:
        """Find taint sink calls within given methods"""
        if not method_names:
            return []

        sink_list = ','.join([f"'{s}'" for s in self.taint_sinks])
        method_list = ','.join([f"'{m}'" for m in method_names])

        query = f"""
            SELECT DISTINCT
                nc.id AS call_id,
                nc.name AS sink_function,
                nc.line_number,
                nc.filename,
                nm.name AS containing_method
            FROM nodes_call nc
            JOIN nodes_method nm ON nc.containing_method_id = nm.id
            WHERE nc.name IN ({sink_list})
              AND nm.name IN ({method_list})
            LIMIT 50;
        """

        try:
            results = self._execute(query)
            return [
                {
                    'call_id': r.get('call_id'),
                    'function': r.get('sink_function'),
                    'line': r.get('line_number'),
                    'file': r.get('filename'),
                    'method': r.get('containing_method')
                }
                for r in results
            ]
        except Exception as e:
            logger.warning(f"Error finding taint sinks: {e}")
            return []

    def _trace_taint_path(
        self,
        source_info: Dict[str, Any],
        sink_info: Dict[str, Any],
        max_depth: int
    ) -> Optional[TaintPathFinding]:
        """
        Trace if there's a data flow path from source to sink.

        Uses REACHING_DEF edges for intra-procedural flow
        and CALL edges for inter-procedural flow.
        """
        source_call_id = source_info.get('call_id')
        sink_call_id = sink_info.get('call_id')

        if not source_call_id or not sink_call_id:
            return None

        # Check if source and sink are in the same method (simplest case)
        if source_info.get('method') == sink_info.get('method'):
            # Try to find REACHING_DEF path
            path_query = f"""
                WITH RECURSIVE dataflow AS (
                    SELECT DISTINCT
                        i.id AS node_id,
                        1 AS depth,
                        CAST(i.id AS VARCHAR) AS path
                    FROM nodes_identifier i
                    JOIN edges_argument ea ON ea.dst = i.id
                    WHERE ea.src = {source_call_id}

                    UNION ALL

                    SELECT DISTINCT
                        i2.id,
                        df.depth + 1,
                        df.path || '->' || CAST(i2.id AS VARCHAR)
                    FROM dataflow df
                    JOIN edges_reaching_def rd ON rd.src = df.node_id
                    JOIN nodes_identifier i2 ON i2.id = rd.dst
                    WHERE df.depth < {max_depth}
                )
                SELECT DISTINCT df.path, df.depth
                FROM dataflow df
                JOIN edges_argument ea ON ea.dst = df.node_id
                WHERE ea.src = {sink_call_id}
                ORDER BY df.depth
                LIMIT 1;
            """

            try:
                results = self._execute(path_query)
                if results:
                    # Path found - check for sanitization
                    sanitization_points, max_confidence = self._check_sanitization_on_path(
                        source_call_id,
                        sink_call_id,
                        max_depth
                    )

                    # Only report if not adequately sanitized
                    if max_confidence < SANITIZATION_THRESHOLD:
                        return TaintPathFinding(
                            path_id=f"TAINT_{source_call_id}_{sink_call_id}",
                            source_function=source_info.get('function', ''),
                            source_location={
                                'method': source_info.get('method'),
                                'line': source_info.get('line'),
                                'file': source_info.get('file')
                            },
                            sink_function=sink_info.get('function', ''),
                            sink_location={
                                'method': sink_info.get('method'),
                                'line': sink_info.get('line'),
                                'file': sink_info.get('file')
                            },
                            path_length=results[0].get('depth', 0),
                            intermediate_nodes=[],
                            sanitization_points=sanitization_points,
                            max_sanitization_confidence=max_confidence,
                            is_new=True
                        )
            except Exception as e:
                logger.debug(f"Error tracing taint path: {e}")

        return None

    def _check_paths_through_method(
        self,
        method_name: str,
        max_depth: int
    ) -> List[TaintPathFinding]:
        """Check if modified method creates new paths to existing sinks"""
        findings: List[TaintPathFinding] = []

        # Find sources that flow into this method
        source_list = ','.join([f"'{s}'" for s in self.taint_sources])

        sources_query = f"""
            SELECT DISTINCT nc.name AS source_func, nc.id AS source_id
            FROM nodes_call nc
            JOIN nodes_method nm ON nc.containing_method_id = nm.id
            WHERE nc.name IN ({source_list})
              AND nm.name = ?
            LIMIT 10;
        """

        try:
            sources = self._execute(sources_query, (method_name,))

            # Find sinks called by this method
            sink_list = ','.join([f"'{s}'" for s in self.taint_sinks])

            sinks_query = f"""
                SELECT DISTINCT nc.name AS sink_func, nc.id AS sink_id
                FROM nodes_call nc
                JOIN nodes_method nm ON nc.containing_method_id = nm.id
                WHERE nc.name IN ({sink_list})
                  AND nm.name = ?
                LIMIT 10;
            """

            sinks = self._execute(sinks_query, (method_name,))

            # Check each source-sink pair
            for source in sources:
                for sink in sinks:
                    sanitization, confidence = self._check_sanitization_on_path(
                        source.get('source_id'),
                        sink.get('sink_id'),
                        max_depth
                    )

                    if confidence < SANITIZATION_THRESHOLD:
                        findings.append(TaintPathFinding(
                            path_id=f"TAINT_{source.get('source_id')}_{sink.get('sink_id')}",
                            source_function=source.get('source_func', ''),
                            source_location={'method': method_name},
                            sink_function=sink.get('sink_func', ''),
                            sink_location={'method': method_name},
                            path_length=1,
                            intermediate_nodes=[],
                            sanitization_points=sanitization,
                            max_sanitization_confidence=confidence,
                            is_new=True
                        ))

        except Exception as e:
            logger.debug(f"Error checking paths through method: {e}")

        return findings

    def _check_sanitization_on_path(
        self,
        source_id: int,
        sink_id: int,
        max_depth: int
    ) -> Tuple[List[Dict[str, Any]], float]:
        """Check for sanitization functions between source and sink"""
        # Build pattern conditions for sanitization functions
        pattern_conditions = []
        for pattern in SANITIZATION_PATTERNS.keys():
            pattern_conditions.append(f"nc.name LIKE '%{pattern}%'")

        conditions_sql = ' OR '.join(pattern_conditions)

        query = f"""
            WITH RECURSIVE path_trace AS (
                SELECT i.id AS node_id, 0 AS depth
                FROM nodes_identifier i
                JOIN edges_argument ea ON ea.dst = i.id
                WHERE ea.src = ?

                UNION ALL

                SELECT i2.id, pt.depth + 1
                FROM path_trace pt
                JOIN edges_reaching_def rd ON rd.src = pt.node_id
                JOIN nodes_identifier i2 ON i2.id = rd.dst
                WHERE pt.depth < ?
            )
            SELECT DISTINCT nc.name AS sanitizer, nc.line_number
            FROM path_trace pt
            JOIN edges_argument ea ON ea.dst = pt.node_id
            JOIN nodes_call nc ON nc.id = ea.src
            WHERE ({conditions_sql})
              AND nc.id != ?
              AND nc.id != ?
            LIMIT 10;
        """

        sanitization_points: List[Dict[str, Any]] = []
        max_confidence = 0.0

        try:
            results = self._execute(query, (source_id, max_depth, source_id, sink_id))

            for row in results:
                sanitizer = row.get('sanitizer', '').lower()
                confidence = self._get_sanitization_confidence(sanitizer)

                sanitization_points.append({
                    'function': row.get('sanitizer'),
                    'line': row.get('line_number'),
                    'confidence': confidence
                })

                max_confidence = max(max_confidence, confidence)

        except Exception as e:
            logger.debug(f"Error checking sanitization: {e}")

        return sanitization_points, max_confidence

    def _get_sanitization_confidence(self, function_name: str) -> float:
        """Get sanitization confidence for a function name"""
        function_lower = function_name.lower()

        for pattern, confidence in SANITIZATION_PATTERNS.items():
            if pattern in function_lower:
                return confidence

        return 0.0

    def _find_sinks_protected_by(self, sanitization_func: str) -> List[str]:
        """Find sinks that were protected by a sanitization function"""
        sink_list = ','.join([f"'{s}'" for s in self.taint_sinks])

        query = f"""
            SELECT DISTINCT nc.name AS sink_name
            FROM nodes_call nc
            JOIN nodes_method nm ON nc.containing_method_id = nm.id
            WHERE nc.name IN ({sink_list})
              AND nm.name IN (
                  SELECT DISTINCT nm2.name
                  FROM nodes_call nc2
                  JOIN nodes_method nm2 ON nc2.containing_method_id = nm2.id
                  WHERE nc2.name = ?
              )
            LIMIT 20;
        """

        try:
            results = self._execute(query, (sanitization_func,))
            return [r.get('sink_name', '') for r in results if r.get('sink_name')]
        except Exception:
            return []

    def _check_method_for_bypass(
        self,
        method: ChangedMethod
    ) -> Optional[SanitizationBypass]:
        """Check if modified method introduces a sanitization bypass"""
        # This is a simplified check - look for removed sanitization calls
        # A full implementation would compare old vs new code

        # Check if method previously called sanitization and now doesn't
        # This requires diffing the method's code, which we don't have here
        # For now, return None - this would be enhanced with actual code diff analysis

        return None

    def _find_sensitive_variables(
        self,
        method_name: str,
        patterns: List[str]
    ) -> List[Dict[str, Any]]:
        """Find variables matching sensitive patterns in a method"""
        sensitive_vars: List[Dict[str, Any]] = []

        for pattern in patterns:
            query = f"""
                SELECT DISTINCT i.name, i.line_number
                FROM nodes_identifier i
                JOIN nodes_method nm ON i.filename = nm.filename
                WHERE nm.name = ?
                  AND LOWER(i.name) LIKE '%{pattern.lower()}%'
                LIMIT 10;
            """

            try:
                results = self._execute(query, (method_name,))
                for r in results:
                    sensitive_vars.append({
                        'name': r.get('name'),
                        'line': r.get('line_number'),
                        'pattern': pattern
                    })
            except Exception:
                pass

        return sensitive_vars

    def _trace_sensitive_data(
        self,
        method_name: str,
        variable_name: str
    ) -> List[Dict[str, Any]]:
        """Trace where sensitive data flows"""
        unsafe_flows: List[Dict[str, Any]] = []

        # Check if variable flows to logging, network, or file operations
        unsafe_destinations = [
            'printf', 'fprintf', 'sprintf', 'log', 'elog', 'print',
            'send', 'write', 'fwrite', 'socket',
            'store', 'save', 'persist'
        ]

        dest_list = ','.join([f"'{d}'" for d in unsafe_destinations])

        query = f"""
            SELECT DISTINCT nc.name AS destination, nc.line_number
            FROM nodes_call nc
            JOIN nodes_method nm ON nc.containing_method_id = nm.id
            WHERE nm.name = ?
              AND nc.name IN ({dest_list})
              AND nc.code LIKE '%{variable_name}%'
            LIMIT 10;
        """

        try:
            results = self._execute(query, (method_name,))
            for r in results:
                unsafe_flows.append({
                    'destination': r.get('destination'),
                    'line': r.get('line_number'),
                    'path': [method_name, r.get('destination')]
                })
        except Exception:
            pass

        return unsafe_flows
