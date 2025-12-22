"""Data Flow Tracer - Main tracer class.

Data flow analysis using REACHING_DEF edges.
"""
import logging
from typing import Dict, List, Any, Optional, Tuple

from .base import BaseTracer
from .models import DataFlowPath, VariableFlow
from .sanitization import (
    get_sanitization_patterns,
    SANITIZATION_CONFIDENCE_THRESHOLD,
)

logger = logging.getLogger(__name__)


class DataFlowTracer(BaseTracer):
    """
    Data flow analysis using REACHING_DEF edges.

    Methods:
    - trace_variable: Trace a variable from definition to uses
    - find_reaching_definitions: Find all definitions reaching a use
    - find_variable_uses: Find all uses of a definition
    - trace_inter_procedural: Trace across function calls
    - find_taint_paths: Find paths from sources to sinks (for taint analysis)
    """

    def __init__(self, cpg_service):
        """Initialize tracer with CPG service."""
        super().__init__(cpg_service)
        logger.info("DataFlowTracer initialized")

    def trace_variable(
        self,
        variable_name: str,
        method_name: Optional[str] = None,
        max_depth: int = 10
    ) -> VariableFlow:
        """
        Trace all flows of a variable using actual REACHING_DEF edges.

        Args:
            variable_name: Name of variable to trace
            method_name: Optional method scope (None = all methods)
            max_depth: Maximum flow depth

        Returns:
            VariableFlow with all definition and use points
        """
        try:
            flow_query = """
                WITH RECURSIVE dataflow AS (
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
                      AND i2.id != df.node_id
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

            definition_points = []
            use_points = []
            flows = []

            flow_map = {}
            for row in results:
                node_id = row.get('node_id')
                source_id = row.get('source_id')
                depth = row.get('depth', 0)

                if depth == 0:
                    definition_points.append({
                        'node_id': node_id,
                        'variable_name': variable_name,
                        'line_number': row.get('line_number'),
                        'code': row.get('code'),
                        'type': 'definition'
                    })
                else:
                    use_points.append({
                        'node_id': node_id,
                        'variable_name': variable_name,
                        'line_number': row.get('line_number'),
                        'code': row.get('code'),
                        'type': 'use'
                    })

                    if source_id not in flow_map:
                        flow_map[source_id] = []
                    flow_map[source_id].append({
                        'node_id': node_id,
                        'depth': depth,
                        'path': row.get('path', '')
                    })

            all_node_ids = set()
            for d in definition_points:
                if d.get('node_id'):
                    all_node_ids.add(d['node_id'])
            for u in use_points:
                if u.get('node_id'):
                    all_node_ids.add(u['node_id'])

            method_map = self._get_containing_methods(list(all_node_ids))

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
                        intermediate_nodes=[],
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
        Find all definitions that reach a specific use point.

        Args:
            use_location: Use point {node_id OR (method_name, variable_name, line_number)}
            max_depth: Maximum backward flow depth

        Returns:
            List of definition points that can reach this use
        """
        node_id = use_location.get('node_id')
        var_name = use_location.get('variable_name')

        if not node_id:
            line_number = use_location.get('line_number')

            if not var_name:
                logger.warning("Invalid use_location: missing variable_name")
                return []

            find_node_query = "SELECT i.id FROM nodes_identifier i WHERE i.name = ?"
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

        query = """
            WITH RECURSIVE reaching_defs AS (
                SELECT
                    i.id AS node_id,
                    i.name AS var_name,
                    i.line_number,
                    i.code,
                    0 AS depth
                FROM nodes_identifier i
                WHERE i.id = ?

                UNION ALL

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
            WHERE depth > 0
            ORDER BY depth, line_number;
        """

        try:
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
        Find all uses reachable from a definition.

        Args:
            definition_location: Definition point {node_id OR (method_name, variable_name, line_number)}
            max_depth: Maximum forward flow depth

        Returns:
            List of use points reachable from this definition
        """
        node_id = definition_location.get('node_id')
        var_name = definition_location.get('variable_name')

        if not node_id:
            line_number = definition_location.get('line_number')

            if not var_name:
                logger.warning("Invalid definition_location: missing variable_name")
                return []

            find_node_query = "SELECT i.id FROM nodes_identifier i WHERE i.name = ?"
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

        query = """
            WITH RECURSIVE reachable_uses AS (
                SELECT
                    i.id AS node_id,
                    i.name AS var_name,
                    i.line_number,
                    i.code,
                    0 AS depth
                FROM nodes_identifier i
                WHERE i.id = ?

                UNION ALL

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
            WHERE depth > 0
            ORDER BY depth, line_number;
        """

        try:
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
        Trace data flow across function boundaries.

        Args:
            source_method: Starting method
            source_variable: Variable to trace
            target_method: Target method
            max_depth: Maximum call depth

        Returns:
            DataFlowPath if flow exists, None otherwise
        """
        query = """
            WITH RECURSIVE inter_procedural_flow AS (
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
                  AND m2.id != ipf.current_method_id
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
            path_str = result.get('path', '')
            intermediate = path_str.split(' -> ')[1:-1] if ' -> ' in path_str else []

            return DataFlowPath(
                path_id=f"INTER_FLOW_{source_method}_{target_method}",
                variable_name=source_variable,
                source_location={'method': source_method, 'type': 'definition'},
                sink_location={'method': target_method, 'type': 'use'},
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
        Find taint flow paths from sources to sinks using REACHING_DEF edges.

        Args:
            source_functions: Taint sources (e.g., ['readLine', 'recv', 'getenv'])
            sink_functions: Dangerous sinks (e.g., ['system', 'strcpy', 'executeSQL'])
            max_depth: Maximum flow depth
            check_sanitization: If True, filter out paths with adequate sanitization

        Returns:
            List of taint paths found with actual REACHING_DEF edge traversal
        """
        if not source_functions or not sink_functions:
            logger.warning("Empty source or sink functions list")
            return []

        source_placeholders = ','.join(['?'] * len(source_functions))
        sink_placeholders = ','.join(['?'] * len(sink_functions))

        query = f"""
            WITH RECURSIVE taint_flow AS (
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

                intermediate = []
                if ' -> ' in path_str:
                    parts = path_str.split(' -> ')[1:-1]
                    for part in parts:
                        intermediate.append({'code': part})

                sanitization_points, max_confidence = self._detect_sanitization_on_path(
                    result.get('source_call_id'),
                    result.get('sink_call_id'),
                    result.get('tainted_var', ''),
                    max_depth
                )

                if check_sanitization and max_confidence >= SANITIZATION_CONFIDENCE_THRESHOLD:
                    logger.debug(
                        f"Filtering out sanitized path: {result.get('source_func')} -> "
                        f"{result.get('sink_func')} (confidence: {max_confidence:.2f})"
                    )
                    continue

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
                    is_inter_procedural=True,
                    sanitization_points=sanitization_points
                ))

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

    def _detect_sanitization_on_path(
        self,
        source_call_id: int,
        sink_call_id: int,
        variable_name: str,
        max_depth: int = 10
    ) -> Tuple[List[Dict[str, Any]], float]:
        """
        Detect sanitization/validation functions on a taint path.

        Args:
            source_call_id: Source call node ID
            sink_call_id: Sink call node ID
            variable_name: Variable being tracked
            max_depth: Maximum depth to search

        Returns:
            Tuple of (sanitization_points, max_confidence_score)
        """
        sanitization_dict = get_sanitization_patterns()
        sanitize_patterns = list(sanitization_dict.keys())

        pattern_conditions = ' OR '.join([f"nc.name LIKE ?" for _ in sanitize_patterns])

        query = f"""
            WITH RECURSIVE path_trace AS (
                SELECT
                    i.id AS node_id,
                    0 AS depth
                FROM nodes_identifier i
                JOIN edges_argument ea ON ea.dst = i.id
                WHERE ea.src = ?

                UNION ALL

                SELECT
                    i2.id,
                    pt.depth + 1
                FROM path_trace pt
                JOIN edges_reaching_def rd ON rd.src = pt.node_id
                JOIN nodes_identifier i2 ON i2.id = rd.dst
                WHERE pt.depth < ?
            )
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
              AND nc.id != ?
              AND nc.id != ?
            ORDER BY pt.depth;
        """

        params = [source_call_id, max_depth] + sanitize_patterns + [source_call_id, sink_call_id]

        try:
            results = self._execute(query, tuple(params))

            sanitization_points = []
            max_confidence = 0.0

            for result in results:
                function_name = result.get('function_name', '').lower()
                confidence = 0.0
                matched_pattern = None

                for pattern, score in sanitization_dict.items():
                    if pattern.endswith('%'):
                        prefix = pattern[:-1]
                        if function_name.startswith(prefix):
                            confidence = max(confidence, score)
                            matched_pattern = pattern
                    else:
                        if pattern in function_name:
                            confidence = max(confidence, score)
                            matched_pattern = pattern

                max_confidence = max(max_confidence, confidence)

                sanitization_points.append({
                    'call_id': result.get('call_id'),
                    'function': result.get('function_name'),
                    'line': result.get('line_number'),
                    'file': result.get('filename'),
                    'position': result.get('position_in_path'),
                    'type': 'sanitization',
                    'confidence': confidence,
                    'pattern': matched_pattern
                })

            if sanitization_points:
                logger.info(
                    f"Found {len(sanitization_points)} sanitization points "
                    f"(max confidence: {max_confidence:.2f})"
                )

            return sanitization_points, max_confidence

        except Exception as e:
            logger.error(f"Error detecting sanitization: {e}", exc_info=True)
            return [], 0.0

    def get_dataflow_statistics(self) -> Dict[str, Any]:
        """Get data flow statistics."""
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

        Args:
            source_functions: Taint sources
            sink_functions: Dangerous sinks
            track_fields: If True, track field accesses
            max_depth: Maximum flow depth
            check_sanitization: If True, filter out sanitized paths

        Returns:
            List of taint paths with field information
        """
        base_paths = self.find_taint_paths(
            source_functions,
            sink_functions,
            max_depth,
            check_sanitization
        )

        if not track_fields or not base_paths:
            return base_paths

        try:
            from .field_sensitive_tracer import FieldSensitiveTracer

            field_tracer = FieldSensitiveTracer(self.cpg)

            enhanced_paths = []
            for path in base_paths:
                var_name = path.variable_name
                field_accesses = field_tracer.find_field_accesses(var_name)

                if field_accesses:
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
        Find flows from sensitive fields to sink functions.

        Args:
            sensitive_fields: Field names considered sensitive
            sink_functions: Sink function patterns

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
