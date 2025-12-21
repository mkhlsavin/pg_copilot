"""
Field-Sensitive Dataflow Tracer

Extends DataFlowTracer with field-path tracking for precise taint analysis.

Key Features:
- Track obj.field1.field2 access chains
- Field-aware taint propagation
- Struct field type resolution
- Distinguish between obj.password and obj.name in taint analysis

This module provides field-sensitive analysis capabilities that are
missing from the base DataFlowTracer.

FUTURE ENHANCEMENTS mentioned in dataflow_tracer.py (lines 27-29):
- Field-sensitive analysis to track struct fields (requires type hierarchy)

Based on: "Graph methods for RAG copilot.md" - Method #3 enhancement
Used in scenarios: 2, 8, 14 (security, compliance, incident response)
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class FieldPath:
    """
    Represents a field access path like obj.field1.field2

    Examples:
        - "user.password" -> base_variable="user", field_chain=["password"]
        - "req->data->buf" -> base_variable="req", field_chain=["data", "buf"]
    """
    base_variable: str
    field_chain: List[str]
    full_path: str
    node_ids: List[int] = field(default_factory=list)
    type_full_name: Optional[str] = None

    @classmethod
    def from_code(cls, code: str) -> 'FieldPath':
        """
        Parse field access from code string.

        Handles both -> and . notation:
        - obj.field1.field2
        - obj->field1->field2
        - mixed: obj->field1.field2
        """
        # Normalize -> to .
        normalized = code.replace('->', '.').strip()
        # Remove whitespace around dots
        normalized = re.sub(r'\s*\.\s*', '.', normalized)
        # Remove array indexing for path comparison
        normalized = re.sub(r'\[[^\]]*\]', '', normalized)

        parts = [p.strip() for p in normalized.split('.') if p.strip()]

        if not parts:
            return cls(
                base_variable='',
                field_chain=[],
                full_path=code,
            )

        return cls(
            base_variable=parts[0],
            field_chain=parts[1:] if len(parts) > 1 else [],
            full_path=normalized,
        )

    def matches(self, other: 'FieldPath') -> Tuple[bool, str]:
        """
        Check if this path matches another path.

        Returns:
            (matches, relationship)
            relationship: 'exact', 'prefix', 'suffix', 'same_base', 'unrelated'
        """
        # Exact match
        if self.full_path == other.full_path:
            return True, 'exact'

        # Same base, different fields
        if self.base_variable == other.base_variable:
            # Check if one is prefix of other
            if len(self.field_chain) < len(other.field_chain):
                if other.field_chain[:len(self.field_chain)] == self.field_chain:
                    return True, 'prefix'  # self is prefix of other
            elif len(self.field_chain) > len(other.field_chain):
                if self.field_chain[:len(other.field_chain)] == other.field_chain:
                    return True, 'suffix'  # other is prefix of self
            return False, 'same_base'

        return False, 'unrelated'

    def __str__(self) -> str:
        return self.full_path


@dataclass
class FieldAccess:
    """Represents a single field access in code"""
    node_id: int
    base_variable: str
    field_name: str
    access_code: str
    line_number: int
    filename: str
    access_type: str = 'read'  # 'read', 'write', 'call'
    containing_method: Optional[str] = None


@dataclass
class FieldSensitiveFlow:
    """A dataflow path with field sensitivity"""
    source_path: FieldPath
    sink_path: FieldPath
    intermediate_fields: List[FieldPath]
    is_tainted: bool
    relationship: str  # 'exact', 'prefix', 'suffix', 'propagated'
    confidence: float = 1.0


class FieldSensitiveTracer:
    """
    Field-sensitive dataflow analysis.

    Tracks taint through field access patterns:
    - obj.field reads/writes
    - obj->field pointer access
    - Nested field access (obj.a.b.c)

    Example usage:
        tracer = FieldSensitiveTracer(cpg_service)

        # Parse field access
        path = tracer.parse_field_path("user->password")
        # path.base_variable = "user"
        # path.field_chain = ["password"]

        # Find all accesses to a field
        accesses = tracer.find_field_accesses("user", "password")

        # Trace taint through fields
        flows = tracer.trace_field_taint("user_input", "data")
    """

    def __init__(self, cpg_service):
        """
        Initialize field-sensitive tracer.

        Args:
            cpg_service: CPGQueryService instance for database access
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

        # Cache for struct field definitions
        self._type_cache: Dict[str, List[Dict]] = {}

        logger.info("FieldSensitiveTracer initialized")

    def _execute(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute a SQL query with parameters."""
        try:
            if self._use_inline_params and params:
                query_with_params = query
                for param in params:
                    if isinstance(param, str):
                        query_with_params = query_with_params.replace('?', f"'{param}'", 1)
                    else:
                        query_with_params = query_with_params.replace('?', str(param), 1)
                return self._execute_base(query_with_params)
            else:
                return self._execute_base(query, params) if params else self._execute_base(query)
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []

    def parse_field_path(self, code: str) -> FieldPath:
        """
        Parse field access from code string.

        Args:
            code: Code like "obj->field1->field2" or "obj.field1.field2"

        Returns:
            FieldPath with parsed components
        """
        return FieldPath.from_code(code)

    def get_struct_fields(self, type_name: str) -> List[Dict[str, Any]]:
        """
        Get field definitions for a struct/class type.

        Args:
            type_name: Name of the struct/class type

        Returns:
            List of field definitions with name, type, line_number
        """
        if type_name in self._type_cache:
            return self._type_cache[type_name]

        query = """
            SELECT
                m.name AS field_name,
                m.type_full_name AS field_type,
                m.line_number,
                m.order_index,
                td.name AS struct_name,
                td.full_name AS struct_full_name
            FROM nodes_type_decl td
            JOIN edges_ast ast ON ast.src = td.id
            JOIN nodes_member m ON m.id = ast.dst
            WHERE td.full_name LIKE ?
               OR td.name = ?
            ORDER BY m.order_index
        """

        results = self._execute(query, (f'%{type_name}%', type_name))
        self._type_cache[type_name] = results
        return results

    def find_field_accesses(
        self,
        base_variable: str,
        field_name: Optional[str] = None
    ) -> List[FieldAccess]:
        """
        Find all accesses to a specific field of a variable.

        Args:
            base_variable: The base variable name (e.g., "user")
            field_name: Optional specific field name (e.g., "password")

        Returns:
            List of FieldAccess objects
        """
        if field_name:
            query = """
                SELECT
                    i.id AS base_id,
                    i.name AS base_name,
                    i.line_number AS base_line,
                    fi.id AS field_id,
                    fi.canonical_name AS field_name,
                    fi.code AS access_code,
                    fi.line_number AS access_line,
                    COALESCE(nm.name, '') AS containing_method,
                    COALESCE(nm.filename, i.argument_name) AS filename
                FROM nodes_identifier i
                JOIN edges_ast ast ON ast.src = i.id
                JOIN nodes_field_identifier fi ON fi.id = ast.dst
                LEFT JOIN edges_contains ec ON ec.dst = i.id
                LEFT JOIN nodes_method nm ON nm.id = ec.src
                WHERE i.name = ?
                  AND fi.canonical_name = ?
                ORDER BY fi.line_number
            """
            results = self._execute(query, (base_variable, field_name))
        else:
            query = """
                SELECT
                    i.id AS base_id,
                    i.name AS base_name,
                    i.line_number AS base_line,
                    fi.id AS field_id,
                    fi.canonical_name AS field_name,
                    fi.code AS access_code,
                    fi.line_number AS access_line,
                    COALESCE(nm.name, '') AS containing_method,
                    COALESCE(nm.filename, i.argument_name) AS filename
                FROM nodes_identifier i
                JOIN edges_ast ast ON ast.src = i.id
                JOIN nodes_field_identifier fi ON fi.id = ast.dst
                LEFT JOIN edges_contains ec ON ec.dst = i.id
                LEFT JOIN nodes_method nm ON nm.id = ec.src
                WHERE i.name = ?
                ORDER BY fi.line_number
            """
            results = self._execute(query, (base_variable,))

        return [
            FieldAccess(
                node_id=r.get('field_id', 0),
                base_variable=r.get('base_name', ''),
                field_name=r.get('field_name', ''),
                access_code=r.get('access_code', ''),
                line_number=r.get('access_line', 0),
                filename=r.get('filename', ''),
                containing_method=r.get('containing_method', ''),
            )
            for r in results
        ]

    def find_all_field_identifiers(
        self,
        field_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find all field identifiers, optionally filtered by field name.

        Args:
            field_name: Optional field name filter
            limit: Maximum results to return

        Returns:
            List of field identifier records
        """
        if field_name:
            query = """
                SELECT
                    fi.id,
                    fi.canonical_name AS field_name,
                    fi.code,
                    fi.line_number,
                    fi.column_number,
                    fi.order_index,
                    nm.name AS containing_method,
                    nm.filename
                FROM nodes_field_identifier fi
                LEFT JOIN edges_contains ec ON ec.dst = fi.id
                LEFT JOIN nodes_method nm ON nm.id = ec.src
                WHERE fi.canonical_name = ?
                ORDER BY fi.line_number
                LIMIT ?
            """
            return self._execute(query, (field_name, limit))
        else:
            query = """
                SELECT
                    fi.id,
                    fi.canonical_name AS field_name,
                    fi.code,
                    fi.line_number,
                    fi.column_number,
                    fi.order_index,
                    nm.name AS containing_method,
                    nm.filename
                FROM nodes_field_identifier fi
                LEFT JOIN edges_contains ec ON ec.dst = fi.id
                LEFT JOIN nodes_method nm ON nm.id = ec.src
                ORDER BY fi.line_number
                LIMIT ?
            """
            return self._execute(query, (limit,))

    def trace_field_taint(
        self,
        source_variable: str,
        source_field: Optional[str] = None,
        sink_patterns: Optional[List[str]] = None,
        max_depth: int = 10
    ) -> List[FieldSensitiveFlow]:
        """
        Trace taint through field accesses.

        If source_field is specified, only track taint from that specific field.
        Otherwise, track all fields of the source variable.

        Args:
            source_variable: Source variable name
            source_field: Optional specific field to track
            sink_patterns: Optional list of sink function patterns
            max_depth: Maximum traversal depth

        Returns:
            List of FieldSensitiveFlow objects
        """
        flows: List[FieldSensitiveFlow] = []

        # Get all field accesses for the source variable
        source_accesses = self.find_field_accesses(source_variable, source_field)

        if not source_accesses:
            logger.debug(f"No field accesses found for {source_variable}.{source_field or '*'}")
            return flows

        # Build source field path
        source_path = FieldPath(
            base_variable=source_variable,
            field_chain=[source_field] if source_field else [],
            full_path=f"{source_variable}.{source_field}" if source_field else source_variable,
        )

        # For each source access, trace forward via REACHING_DEF edges
        for access in source_accesses:
            # Query for reaching definitions from this field access
            query = """
                WITH RECURSIVE taint_propagation AS (
                    -- Base: start from the field identifier
                    SELECT
                        ? AS node_id,
                        ? AS var_name,
                        ? AS field_name,
                        1 AS depth

                    UNION ALL

                    -- Recursive: follow REACHING_DEF edges
                    SELECT
                        rd.dst AS node_id,
                        COALESCE(i.name, tp.var_name) AS var_name,
                        COALESCE(fi.canonical_name, tp.field_name) AS field_name,
                        tp.depth + 1 AS depth
                    FROM taint_propagation tp
                    JOIN edges_reaching_def rd ON rd.src = tp.node_id
                    LEFT JOIN nodes_identifier i ON i.id = rd.dst
                    LEFT JOIN edges_ast ast ON ast.src = rd.dst
                    LEFT JOIN nodes_field_identifier fi ON fi.id = ast.dst
                    WHERE tp.depth < ?
                )
                SELECT DISTINCT node_id, var_name, field_name, depth
                FROM taint_propagation
                ORDER BY depth
                LIMIT 100
            """

            results = self._execute(
                query,
                (access.node_id, access.base_variable, access.field_name, max_depth)
            )

            for r in results:
                sink_field = r.get('field_name', '')
                sink_var = r.get('var_name', '')

                if sink_var and sink_var != source_variable:
                    sink_path = FieldPath(
                        base_variable=sink_var,
                        field_chain=[sink_field] if sink_field else [],
                        full_path=f"{sink_var}.{sink_field}" if sink_field else sink_var,
                    )

                    matches, relationship = source_path.matches(sink_path)

                    flows.append(FieldSensitiveFlow(
                        source_path=source_path,
                        sink_path=sink_path,
                        intermediate_fields=[],
                        is_tainted=True,
                        relationship=relationship if matches else 'propagated',
                        confidence=0.8 if matches else 0.6,
                    ))

        return flows

    def check_field_propagation(
        self,
        source_path: FieldPath,
        sink_path: FieldPath
    ) -> Tuple[bool, str]:
        """
        Check if taint can propagate between two field paths.

        Returns:
            (can_propagate, relationship)
        """
        return source_path.matches(sink_path)

    def find_sensitive_field_flows(
        self,
        sensitive_fields: List[str] = None,
        sink_functions: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find flows from sensitive fields to sink functions.

        Args:
            sensitive_fields: List of field names considered sensitive
                (default: password, token, secret, key, credential, auth)
            sink_functions: List of sink function patterns
                (default: printf, sprintf, log, send, write)

        Returns:
            List of potential sensitive data flows
        """
        if sensitive_fields is None:
            sensitive_fields = [
                'password', 'passwd', 'pwd',
                'token', 'access_token', 'api_key',
                'secret', 'private_key',
                'credential', 'cred',
                'auth', 'authentication',
            ]

        if sink_functions is None:
            sink_functions = [
                'printf', 'sprintf', 'fprintf',
                'log', 'elog', 'ereport',
                'send', 'write', 'fwrite',
                'strcpy', 'strcat',
            ]

        findings = []

        for field in sensitive_fields:
            # Find all accesses to this sensitive field
            accesses = self.find_all_field_identifiers(field)

            for access in accesses:
                # Check if this access is in the context of a sink function
                query = """
                    SELECT
                        nc.id,
                        nc.name AS sink_function,
                        nc.line_number,
                        nc.code,
                        nm.name AS containing_method,
                        nm.filename
                    FROM nodes_call nc
                    JOIN edges_contains ec ON ec.dst = nc.id
                    JOIN nodes_method nm ON nm.id = ec.src
                    WHERE nc.name IN ({})
                      AND nm.name = ?
                      AND ABS(nc.line_number - ?) <= 5
                    LIMIT 10
                """.format(','.join(['?' for _ in sink_functions]))

                params = tuple(sink_functions) + (
                    access.get('containing_method', ''),
                    access.get('line_number', 0),
                )

                nearby_sinks = self._execute(query, params)

                for sink in nearby_sinks:
                    findings.append({
                        'sensitive_field': field,
                        'field_access': access,
                        'sink_function': sink.get('sink_function'),
                        'sink_line': sink.get('line_number'),
                        'containing_method': sink.get('containing_method'),
                        'filename': sink.get('filename'),
                        'risk': 'HIGH' if field in ['password', 'secret', 'private_key'] else 'MEDIUM',
                    })

        return findings
