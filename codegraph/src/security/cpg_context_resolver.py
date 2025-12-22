"""
CPG Context Resolver.

Resolves context (containing file/method) for CPG nodes with unknown method references.
Uses recursive AST traversal to find parent method nodes.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

try:
    import duckdb
except ImportError:
    duckdb = None

logger = logging.getLogger(__name__)


@dataclass
class CallContext:
    """
    Context information for a function call.

    Attributes:
        call_id: Unique ID of the call node
        call_name: Name of the called function
        line_number: Line number in source file
        containing_file: Path to the file containing this call
        containing_method: Name of the method containing this call
        code: Source code of the call
    """
    call_id: int
    call_name: str
    line_number: int
    containing_file: str
    containing_method: str
    code: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'call_id': self.call_id,
            'call_name': self.call_name,
            'line_number': self.line_number,
            'containing_file': self.containing_file,
            'containing_method': self.containing_method,
            'code': self.code,
        }


def resolve_unknown_calls(
    conn: 'duckdb.DuckDBPyConnection',
    call_ids: Optional[List[int]] = None
) -> Dict[int, CallContext]:
    """
    Resolve containing method/file for calls with unknown target method.

    Uses recursive CTE to traverse AST edges upward until a method node is found.

    Args:
        conn: DuckDB connection
        call_ids: Optional list of specific call IDs to resolve.
                  If None, resolves all unknown calls.

    Returns:
        Dictionary mapping call_id to CallContext
    """
    if duckdb is None:
        logger.error("DuckDB not available")
        return {}

    # Build WHERE clause for filtering
    where_clause = "c.method_full_name = '<unknownFullName>'"
    if call_ids:
        ids_str = ', '.join(str(i) for i in call_ids)
        where_clause += f" AND c.id IN ({ids_str})"

    query = f'''
    WITH RECURSIVE ast_ancestry AS (
        -- Base case: unknown calls + first parent from edges_ast
        SELECT
            c.id as call_id,
            c.name as call_name,
            c.code,
            c.line_number,
            e.src_id as parent_id,
            1 as depth
        FROM nodes_call c
        LEFT JOIN edges_ast e ON e.dst_id = c.id
        WHERE {where_clause}

        UNION ALL

        -- Recursive case: traverse up the AST tree
        SELECT
            a.call_id,
            a.call_name,
            a.code,
            a.line_number,
            e.src_id,
            a.depth + 1
        FROM ast_ancestry a
        INNER JOIN edges_ast e ON e.dst_id = a.parent_id
        WHERE a.depth < 50 AND a.parent_id IS NOT NULL
    ),

    -- Find the first method in the chain (minimum depth)
    method_depth AS (
        SELECT
            call_id,
            MIN(depth) as min_depth
        FROM ast_ancestry
        WHERE parent_id IN (SELECT id FROM nodes_method)
        GROUP BY call_id
    )

    -- Final result with context
    SELECT
        a.call_id,
        a.call_name,
        a.code,
        a.line_number,
        m.filename as containing_file,
        m.name as containing_method
    FROM ast_ancestry a
    INNER JOIN method_depth md ON a.call_id = md.call_id AND a.depth = md.min_depth
    LEFT JOIN nodes_method m ON m.id = a.parent_id
    ORDER BY a.line_number, a.call_id
    '''

    result = {}
    try:
        for row in conn.execute(query).fetchall():
            result[row[0]] = CallContext(
                call_id=row[0],
                call_name=row[1] or 'unknown',
                code=row[2] or '',
                line_number=row[3] or 0,
                containing_file=row[4] or 'unknown',
                containing_method=row[5] or 'unknown',
            )
        logger.info(f"Resolved context for {len(result)} unknown calls")
    except Exception as e:
        logger.error(f"Error resolving unknown calls: {e}")

    return result


def resolve_all_calls(
    conn: 'duckdb.DuckDBPyConnection',
    include_known: bool = True
) -> Dict[int, CallContext]:
    """
    Resolve context for all function calls.

    Args:
        conn: DuckDB connection
        include_known: If True, also include calls with known targets

    Returns:
        Dictionary mapping call_id to CallContext
    """
    if duckdb is None:
        logger.error("DuckDB not available")
        return {}

    # Build WHERE clause
    where_clause = "1=1" if include_known else "c.method_full_name = '<unknownFullName>'"

    query = f'''
    WITH RECURSIVE ast_ancestry AS (
        SELECT
            c.id as call_id,
            c.name as call_name,
            c.code,
            c.line_number,
            e.src_id as parent_id,
            1 as depth
        FROM nodes_call c
        LEFT JOIN edges_ast e ON e.dst_id = c.id
        WHERE {where_clause}

        UNION ALL

        SELECT
            a.call_id,
            a.call_name,
            a.code,
            a.line_number,
            e.src_id,
            a.depth + 1
        FROM ast_ancestry a
        INNER JOIN edges_ast e ON e.dst_id = a.parent_id
        WHERE a.depth < 50 AND a.parent_id IS NOT NULL
    ),

    method_depth AS (
        SELECT
            call_id,
            MIN(depth) as min_depth
        FROM ast_ancestry
        WHERE parent_id IN (SELECT id FROM nodes_method)
        GROUP BY call_id
    )

    SELECT
        a.call_id,
        a.call_name,
        a.code,
        a.line_number,
        m.filename as containing_file,
        m.name as containing_method
    FROM ast_ancestry a
    INNER JOIN method_depth md ON a.call_id = md.call_id AND a.depth = md.min_depth
    LEFT JOIN nodes_method m ON m.id = a.parent_id
    ORDER BY a.line_number, a.call_id
    '''

    result = {}
    try:
        for row in conn.execute(query).fetchall():
            result[row[0]] = CallContext(
                call_id=row[0],
                call_name=row[1] or 'unknown',
                code=row[2] or '',
                line_number=row[3] or 0,
                containing_file=row[4] or 'unknown',
                containing_method=row[5] or 'unknown',
            )
        logger.info(f"Resolved context for {len(result)} calls")
    except Exception as e:
        logger.error(f"Error resolving calls: {e}")

    return result


def get_security_calls_with_context(
    conn: 'duckdb.DuckDBPyConnection',
    dangerous_patterns: Optional[List[str]] = None
) -> List[CallContext]:
    """
    Get security-relevant function calls with their context.

    Args:
        conn: DuckDB connection
        dangerous_patterns: List of function name patterns to search for.
                            Defaults to common dangerous functions.

    Returns:
        List of CallContext for matching calls
    """
    if duckdb is None:
        logger.error("DuckDB not available")
        return []

    if dangerous_patterns is None:
        dangerous_patterns = [
            'execute', 'raw', 'cursor',  # SQL
            'eval', 'exec',  # Code execution
            'subprocess', 'system', 'popen',  # Command injection
            'pickle', 'yaml.load',  # Deserialization
            'open', 'read', 'write',  # File operations
            'mark_safe',  # XSS
        ]

    # Build LIKE conditions
    like_conditions = ' OR '.join(
        f"c.name LIKE '%{pat}%' OR c.method_full_name LIKE '%{pat}%'"
        for pat in dangerous_patterns
    )

    query = f'''
    WITH RECURSIVE ast_ancestry AS (
        SELECT
            c.id as call_id,
            c.name as call_name,
            c.code,
            c.line_number,
            e.src_id as parent_id,
            1 as depth
        FROM nodes_call c
        LEFT JOIN edges_ast e ON e.dst_id = c.id
        WHERE {like_conditions}

        UNION ALL

        SELECT
            a.call_id,
            a.call_name,
            a.code,
            a.line_number,
            e.src_id,
            a.depth + 1
        FROM ast_ancestry a
        INNER JOIN edges_ast e ON e.dst_id = a.parent_id
        WHERE a.depth < 50 AND a.parent_id IS NOT NULL
    ),

    method_depth AS (
        SELECT
            call_id,
            MIN(depth) as min_depth
        FROM ast_ancestry
        WHERE parent_id IN (SELECT id FROM nodes_method)
        GROUP BY call_id
    )

    SELECT DISTINCT
        a.call_id,
        a.call_name,
        a.code,
        a.line_number,
        m.filename as containing_file,
        m.name as containing_method
    FROM ast_ancestry a
    INNER JOIN method_depth md ON a.call_id = md.call_id AND a.depth = md.min_depth
    LEFT JOIN nodes_method m ON m.id = a.parent_id
    ORDER BY m.filename, a.line_number
    '''

    result = []
    try:
        for row in conn.execute(query).fetchall():
            result.append(CallContext(
                call_id=row[0],
                call_name=row[1] or 'unknown',
                code=row[2] or '',
                line_number=row[3] or 0,
                containing_file=row[4] or 'unknown',
                containing_method=row[5] or 'unknown',
            ))
        logger.info(f"Found {len(result)} security-relevant calls")
    except Exception as e:
        logger.error(f"Error finding security calls: {e}")

    return result


def enrich_findings_with_context(
    conn: 'duckdb.DuckDBPyConnection',
    findings: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Enrich security findings with resolved context.

    Replaces 'unknown' file/method references with actual values
    from AST traversal.

    Args:
        conn: DuckDB connection
        findings: List of finding dictionaries

    Returns:
        Enriched findings list
    """
    # Collect call IDs that need resolution
    call_ids = []
    for finding in findings:
        if finding.get('file_path') == 'unknown' or finding.get('containing_method') == 'unknown':
            call_id = finding.get('call_id') or finding.get('node_id')
            if call_id:
                call_ids.append(call_id)

    if not call_ids:
        return findings

    # Resolve contexts
    contexts = resolve_unknown_calls(conn, call_ids)

    # Enrich findings
    enriched = []
    for finding in findings:
        call_id = finding.get('call_id') or finding.get('node_id')
        if call_id and call_id in contexts:
            ctx = contexts[call_id]
            finding = finding.copy()
            finding['file_path'] = ctx.containing_file
            finding['containing_method'] = ctx.containing_method
            if not finding.get('line_number'):
                finding['line_number'] = ctx.line_number
        enriched.append(finding)

    return enriched


__all__ = [
    'CallContext',
    'resolve_unknown_calls',
    'resolve_all_calls',
    'get_security_calls_with_context',
    'enrich_findings_with_context',
]
