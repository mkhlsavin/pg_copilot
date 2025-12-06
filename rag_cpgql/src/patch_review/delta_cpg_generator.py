"""
Delta CPG Generator

Generates a delta CPG (virtual graph overlay) from a patch.
The delta CPG represents the changes introduced by the patch without
modifying the base CPG.

Workflow:
1. Extract changed files from patch
2. Parse changed files with Joern (selective parsing)
3. Match new nodes to existing base CPG nodes
4. Compute node changes (added/modified/deleted)
5. Compute edge changes (new call edges, removed edges)
6. Store in delta tables

Phase: Core Infrastructure (Phase 1)
"""

import json
import logging
import os
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.patch_review.models import (
    ChangeType,
    ChangedMethod,
    DeltaCPG,
    DeltaEdge,
    DeltaNode,
    FileDiff,
    PatchContext,
    ReviewSession,
    ReviewStatus,
)

logger = logging.getLogger(__name__)


class DeltaCPGGenerator:
    """
    Generates delta CPG from patch changes.

    Uses Joern to parse only the changed files and computes
    the difference between the new parse and the base CPG.
    """

    def __init__(
        self,
        conn: Any,
        joern_client: Optional[Any] = None,
        joern_path: Optional[str] = None,
        work_dir: Optional[str] = None
    ):
        """
        Initialize the delta CPG generator.

        Args:
            conn: DuckDB connection or CPGQueryService
            joern_client: Optional JoernClient for CPGQL queries
            joern_path: Path to Joern installation (for parsing)
            work_dir: Working directory for temporary files
        """
        self.conn = conn
        self.joern = joern_client
        self.joern_path = joern_path or self._find_joern()
        self.work_dir = work_dir or tempfile.gettempdir()

        # Support multiple interfaces
        if hasattr(conn, 'execute'):
            # DuckDB connection
            self._execute = self._execute_duckdb
        elif hasattr(conn, 'execute_query'):
            self._execute = conn.execute_query
        elif hasattr(conn, 'execute_sql_dict'):
            self._execute = conn.execute_sql_dict
        else:
            # Fallback - create a no-op execute
            self._execute = lambda q, p=None: []

        logger.info(f"DeltaCPGGenerator initialized (work_dir: {self.work_dir})")

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

    def _find_joern(self) -> Optional[str]:
        """Attempt to find Joern installation"""
        # Check common locations
        locations = [
            os.path.expanduser('~/joern'),
            '/opt/joern',
            'C:/joern',
            os.environ.get('JOERN_HOME', ''),
        ]

        for loc in locations:
            if loc and os.path.isdir(loc):
                return loc

        logger.warning("Joern installation not found. Set JOERN_HOME or pass joern_path")
        return None

    def generate_delta(
        self,
        patch: PatchContext,
        session_id: Optional[str] = None,
        source_root: Optional[str] = None
    ) -> DeltaCPG:
        """
        Generate delta CPG for a patch.

        Args:
            patch: Parsed patch context
            session_id: Optional session ID (generated if not provided)
            source_root: Root directory of the source code

        Returns:
            DeltaCPG with all changed nodes and edges
        """
        session_id = session_id or f"SESSION_{uuid.uuid4().hex[:12].upper()}"

        logger.info(f"Generating delta CPG for patch {patch.patch_id} (session: {session_id})")

        delta = DeltaCPG(
            session_id=session_id,
            patch_id=patch.patch_id
        )

        try:
            # Step 1: Create review session in database
            self._create_session(session_id, patch)

            # Step 2: Process each changed file
            for file_diff in patch.files:
                self._process_file_diff(file_diff, delta, source_root)

            # Step 3: Compute edge changes
            self._compute_edge_changes(delta, patch)

            # Step 4: Store delta in database
            self._store_delta(delta)

            # Step 5: Update statistics
            delta.nodes_added = len([n for n in delta.nodes if n.change_type == ChangeType.ADDED])
            delta.nodes_modified = len([n for n in delta.nodes if n.change_type == ChangeType.MODIFIED])
            delta.nodes_deleted = len([n for n in delta.nodes if n.change_type == ChangeType.DELETED])
            delta.edges_added = len([e for e in delta.edges if e.change_type == ChangeType.ADDED])
            delta.edges_deleted = len([e for e in delta.edges if e.change_type == ChangeType.DELETED])

            logger.info(
                f"Delta CPG generated: {delta.nodes_added} added, "
                f"{delta.nodes_modified} modified, {delta.nodes_deleted} deleted nodes; "
                f"{delta.edges_added} added, {delta.edges_deleted} deleted edges"
            )

            return delta

        except Exception as e:
            logger.error(f"Failed to generate delta CPG: {e}", exc_info=True)
            self._update_session_status(session_id, ReviewStatus.FAILED, error=str(e))
            raise

    def _create_session(self, session_id: str, patch: PatchContext):
        """Create review session record in database"""
        query = """
            INSERT INTO review_sessions (
                session_id, patch_id, base_commit, head_commit,
                status, created_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        try:
            self._execute(query, (
                session_id,
                patch.patch_id,
                patch.base_commit,
                patch.head_commit,
                'analyzing',
                datetime.utcnow().isoformat(),
                json.dumps(patch.metadata)
            ))
        except Exception as e:
            # Table might not exist yet - log and continue
            logger.warning(f"Could not create session record: {e}")

    def _update_session_status(
        self,
        session_id: str,
        status: ReviewStatus,
        error: Optional[str] = None
    ):
        """Update session status"""
        query = """
            UPDATE review_sessions
            SET status = ?, completed_at = ?
            WHERE session_id = ?
        """
        try:
            self._execute(query, (
                status.value,
                datetime.utcnow().isoformat() if status in [ReviewStatus.COMPLETED, ReviewStatus.FAILED] else None,
                session_id
            ))
        except Exception as e:
            logger.warning(f"Could not update session status: {e}")

    def _process_file_diff(
        self,
        file_diff: FileDiff,
        delta: DeltaCPG,
        source_root: Optional[str]
    ):
        """
        Process a single file diff and add to delta CPG.

        For each file:
        1. If deleted: Mark all methods in file as deleted
        2. If added: Parse new file and mark all as added
        3. If modified: Compare old and new, identify changes
        """
        filepath = file_diff.path
        logger.debug(f"Processing file diff: {filepath} ({file_diff.change_type.value})")

        if file_diff.change_type == ChangeType.DELETED:
            self._process_deleted_file(filepath, delta)
        elif file_diff.change_type == ChangeType.ADDED:
            self._process_added_file(file_diff, delta, source_root)
        elif file_diff.change_type == ChangeType.MODIFIED:
            self._process_modified_file(file_diff, delta, source_root)
        elif file_diff.change_type == ChangeType.RENAMED:
            self._process_renamed_file(file_diff, delta, source_root)

    def _process_deleted_file(self, filepath: str, delta: DeltaCPG):
        """Mark all methods in deleted file as deleted"""
        # Find all methods in this file from base CPG
        query = """
            SELECT id, name, full_name, line_number, line_number_end, code
            FROM nodes_method
            WHERE filename LIKE ?
        """

        results = self._execute(query, (f'%{filepath}',))

        for row in results:
            node = DeltaNode(
                id=self._next_delta_id(delta),
                session_id=delta.session_id,
                node_type='METHOD',
                change_type=ChangeType.DELETED,
                name=row.get('name', ''),
                full_name=row.get('full_name', ''),
                filename=filepath,
                line_number=row.get('line_number', 0),
                line_number_end=row.get('line_number_end'),
                code=row.get('code'),
                original_node_id=row.get('id')
            )
            delta.nodes.append(node)

            # Track as changed method
            delta.changed_methods.append(ChangedMethod(
                method_name=row.get('name', ''),
                full_name=row.get('full_name', ''),
                filepath=filepath,
                change_type=ChangeType.DELETED,
                line_start=row.get('line_number', 0),
                line_end=row.get('line_number_end', 0),
                method_id=row.get('id'),
                delta_node_id=node.id
            ))

        logger.debug(f"Marked {len(results)} methods as deleted in {filepath}")

    def _process_added_file(
        self,
        file_diff: FileDiff,
        delta: DeltaCPG,
        source_root: Optional[str]
    ):
        """Parse and add all methods from new file"""
        # For added files, we need to parse the new content
        # This is a simplified approach - in production, use Joern

        # Extract method signatures from added lines
        for hunk in file_diff.hunks:
            for i, line in enumerate(hunk.added_lines):
                method_info = self._extract_method_from_line(
                    line,
                    file_diff.path,
                    hunk.new_start + i,
                    file_diff.language
                )

                if method_info:
                    node = DeltaNode(
                        id=self._next_delta_id(delta),
                        session_id=delta.session_id,
                        node_type='METHOD',
                        change_type=ChangeType.ADDED,
                        name=method_info['name'],
                        full_name=f"{file_diff.path}:{method_info['name']}",
                        filename=file_diff.path,
                        line_number=method_info['line'],
                        code=line.strip()
                    )
                    delta.nodes.append(node)

                    delta.changed_methods.append(ChangedMethod(
                        method_name=method_info['name'],
                        full_name=node.full_name,
                        filepath=file_diff.path,
                        change_type=ChangeType.ADDED,
                        line_start=method_info['line'],
                        line_end=method_info['line'],
                        delta_node_id=node.id,
                        new_signature=method_info.get('signature')
                    ))

    def _process_modified_file(
        self,
        file_diff: FileDiff,
        delta: DeltaCPG,
        source_root: Optional[str]
    ):
        """
        Process modified file by comparing changed regions.

        Strategy:
        1. Find all methods in base CPG for this file
        2. For each hunk, check which methods are affected
        3. Mark affected methods as modified
        """
        filepath = file_diff.path

        # Get all methods in this file from base CPG
        query = """
            SELECT id, name, full_name, line_number, line_number_end, code, signature
            FROM nodes_method
            WHERE filename LIKE ?
        """

        base_methods = self._execute(query, (f'%{filepath}',))

        # Track which methods are affected by changes
        affected_methods = set()

        for hunk in file_diff.hunks:
            hunk_start = hunk.old_start
            hunk_end = hunk.old_start + hunk.old_lines

            for method in base_methods:
                method_start = method.get('line_number', 0)
                method_end = method.get('line_number_end', method_start + 100)

                # Check if hunk overlaps with method
                if self._ranges_overlap(hunk_start, hunk_end, method_start, method_end):
                    affected_methods.add(method.get('id'))

        # Process affected methods
        for method in base_methods:
            if method.get('id') in affected_methods:
                node = DeltaNode(
                    id=self._next_delta_id(delta),
                    session_id=delta.session_id,
                    node_type='METHOD',
                    change_type=ChangeType.MODIFIED,
                    name=method.get('name', ''),
                    full_name=method.get('full_name', ''),
                    filename=filepath,
                    line_number=method.get('line_number', 0),
                    line_number_end=method.get('line_number_end'),
                    code=method.get('code'),
                    original_node_id=method.get('id'),
                    old_values={'signature': method.get('signature')}
                )
                delta.nodes.append(node)

                delta.changed_methods.append(ChangedMethod(
                    method_name=method.get('name', ''),
                    full_name=method.get('full_name', ''),
                    filepath=filepath,
                    change_type=ChangeType.MODIFIED,
                    line_start=method.get('line_number', 0),
                    line_end=method.get('line_number_end', 0),
                    method_id=method.get('id'),
                    delta_node_id=node.id,
                    old_signature=method.get('signature')
                ))

        # Check for new methods in added lines
        for hunk in file_diff.hunks:
            for i, line in enumerate(hunk.added_lines):
                method_info = self._extract_method_from_line(
                    line,
                    filepath,
                    hunk.new_start + i,
                    file_diff.language
                )

                if method_info:
                    # Check if this is truly new (not modifying existing)
                    existing = [m for m in base_methods if m.get('name') == method_info['name']]
                    if not existing:
                        node = DeltaNode(
                            id=self._next_delta_id(delta),
                            session_id=delta.session_id,
                            node_type='METHOD',
                            change_type=ChangeType.ADDED,
                            name=method_info['name'],
                            full_name=f"{filepath}:{method_info['name']}",
                            filename=filepath,
                            line_number=method_info['line']
                        )
                        delta.nodes.append(node)

                        delta.changed_methods.append(ChangedMethod(
                            method_name=method_info['name'],
                            full_name=node.full_name,
                            filepath=filepath,
                            change_type=ChangeType.ADDED,
                            line_start=method_info['line'],
                            line_end=method_info['line'],
                            delta_node_id=node.id
                        ))

        logger.debug(f"Found {len(affected_methods)} modified methods in {filepath}")

    def _process_renamed_file(
        self,
        file_diff: FileDiff,
        delta: DeltaCPG,
        source_root: Optional[str]
    ):
        """
        Process renamed file.

        For renames, we need to update file references but the methods
        themselves may or may not have changed.
        """
        old_path = file_diff.old_path
        new_path = file_diff.path

        # Find all methods in old file location
        query = """
            SELECT id, name, full_name, line_number, line_number_end, code
            FROM nodes_method
            WHERE filename LIKE ?
        """

        results = self._execute(query, (f'%{old_path}',))

        for row in results:
            # Create modified node with updated filename
            node = DeltaNode(
                id=self._next_delta_id(delta),
                session_id=delta.session_id,
                node_type='METHOD',
                change_type=ChangeType.MODIFIED,
                name=row.get('name', ''),
                full_name=row.get('full_name', '').replace(old_path, new_path),
                filename=new_path,
                line_number=row.get('line_number', 0),
                line_number_end=row.get('line_number_end'),
                original_node_id=row.get('id'),
                old_values={'filename': old_path},
                new_values={'filename': new_path}
            )
            delta.nodes.append(node)

        # Also process any content changes in the renamed file
        if file_diff.hunks:
            # Create a temporary modified file_diff for processing
            temp_diff = FileDiff(
                path=new_path,
                change_type=ChangeType.MODIFIED,
                hunks=file_diff.hunks,
                language=file_diff.language
            )
            self._process_modified_file(temp_diff, delta, source_root)

    def _compute_edge_changes(self, delta: DeltaCPG, patch: PatchContext):
        """
        Compute edge changes based on node changes.

        For modified/deleted nodes, find affected edges in base CPG.
        For added nodes, new edges will be detected when the delta
        CPG is queried.
        """
        # Get IDs of changed methods
        changed_method_ids = [
            n.original_node_id for n in delta.nodes
            if n.original_node_id is not None and n.node_type == 'METHOD'
        ]

        if not changed_method_ids:
            return

        # Find call edges to/from changed methods
        id_list = ','.join(str(id) for id in changed_method_ids)

        # Edges where changed method is the target (callers)
        query = f"""
            SELECT ec.id, ec.src, ec.dst, 'CALL' as edge_type
            FROM edges_call ec
            WHERE ec.dst IN ({id_list})
        """

        try:
            results = self._execute(query)

            for row in results:
                # Check if source method is also deleted
                dst_node = next(
                    (n for n in delta.nodes if n.original_node_id == row.get('dst')),
                    None
                )

                if dst_node and dst_node.change_type == ChangeType.DELETED:
                    # Edge to deleted method - mark as deleted
                    edge = DeltaEdge(
                        id=self._next_delta_edge_id(delta),
                        session_id=delta.session_id,
                        edge_type='CALL',
                        src=row.get('src'),
                        dst=row.get('dst'),
                        change_type=ChangeType.DELETED,
                        dst_is_delta=True
                    )
                    delta.edges.append(edge)

        except Exception as e:
            logger.warning(f"Could not compute edge changes: {e}")

    def _store_delta(self, delta: DeltaCPG):
        """Store delta nodes and edges in database"""
        # Store delta nodes
        for node in delta.nodes:
            try:
                query = """
                    INSERT INTO delta_nodes (
                        id, session_id, node_type, change_type, original_node_id,
                        name, full_name, filename, line_number, line_number_end,
                        code, old_values, new_values
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                self._execute(query, (
                    node.id,
                    node.session_id,
                    node.node_type,
                    node.change_type.value,
                    node.original_node_id,
                    node.name,
                    node.full_name,
                    node.filename,
                    node.line_number,
                    node.line_number_end,
                    node.code,
                    json.dumps(node.old_values) if node.old_values else None,
                    json.dumps(node.new_values) if node.new_values else None
                ))
            except Exception as e:
                logger.warning(f"Could not store delta node: {e}")

        # Store delta edges
        for edge in delta.edges:
            try:
                query = """
                    INSERT INTO delta_edges (
                        id, session_id, edge_type, src, dst, change_type,
                        src_is_delta, dst_is_delta, properties
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                self._execute(query, (
                    edge.id,
                    edge.session_id,
                    edge.edge_type,
                    edge.src,
                    edge.dst,
                    edge.change_type.value,
                    edge.src_is_delta,
                    edge.dst_is_delta,
                    json.dumps(edge.properties) if edge.properties else None
                ))
            except Exception as e:
                logger.warning(f"Could not store delta edge: {e}")

        # Store changed methods
        for i, method in enumerate(delta.changed_methods):
            try:
                query = """
                    INSERT INTO delta_changed_methods (
                        id, session_id, method_name, full_name, filepath,
                        change_type, line_start, line_end, base_method_id,
                        delta_node_id, old_signature, new_signature,
                        complexity_before, complexity_after
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                self._execute(query, (
                    i + 1,
                    delta.session_id,
                    method.method_name,
                    method.full_name,
                    method.filepath,
                    method.change_type.value,
                    method.line_start,
                    method.line_end,
                    method.method_id,
                    method.delta_node_id,
                    method.old_signature,
                    method.new_signature,
                    method.complexity_before,
                    method.complexity_after
                ))
            except Exception as e:
                logger.warning(f"Could not store changed method: {e}")

    def persist_delta(self, session_id: str):
        """
        Mark delta as persistent (don't clean up).

        Use for merged patches where we want to keep history.
        """
        query = """
            UPDATE review_sessions
            SET persist_delta = TRUE
            WHERE session_id = ?
        """
        try:
            self._execute(query, (session_id,))
            logger.info(f"Marked session {session_id} for persistence")
        except Exception as e:
            logger.warning(f"Could not mark session for persistence: {e}")

    def cleanup_delta(self, session_id: str):
        """
        Remove delta data for a session.

        Called after review is complete for non-persistent sessions.
        """
        try:
            # Delete in correct order (foreign key constraints)
            self._execute("DELETE FROM review_findings WHERE session_id = ?", (session_id,))
            self._execute("DELETE FROM delta_changed_methods WHERE session_id = ?", (session_id,))
            self._execute("DELETE FROM delta_edges WHERE session_id = ?", (session_id,))
            self._execute("DELETE FROM delta_nodes WHERE session_id = ?", (session_id,))
            self._execute("DELETE FROM review_sessions WHERE session_id = ?", (session_id,))

            logger.info(f"Cleaned up delta for session {session_id}")
        except Exception as e:
            logger.warning(f"Could not clean up delta: {e}")

    def get_delta(self, session_id: str) -> Optional[DeltaCPG]:
        """
        Retrieve delta CPG for a session.

        Args:
            session_id: Session ID to retrieve

        Returns:
            DeltaCPG if found, None otherwise
        """
        try:
            # Get session info
            session_query = """
                SELECT patch_id, status FROM review_sessions WHERE session_id = ?
            """
            session_result = self._execute(session_query, (session_id,))
            if not session_result:
                return None

            patch_id = session_result[0].get('patch_id', '')

            delta = DeltaCPG(session_id=session_id, patch_id=patch_id)

            # Load nodes
            nodes_query = """
                SELECT * FROM delta_nodes WHERE session_id = ?
            """
            nodes_result = self._execute(nodes_query, (session_id,))

            for row in nodes_result:
                delta.nodes.append(DeltaNode(
                    id=row.get('id'),
                    session_id=session_id,
                    node_type=row.get('node_type', ''),
                    change_type=ChangeType(row.get('change_type', 'modified')),
                    name=row.get('name', ''),
                    full_name=row.get('full_name', ''),
                    filename=row.get('filename', ''),
                    line_number=row.get('line_number', 0),
                    line_number_end=row.get('line_number_end'),
                    code=row.get('code'),
                    original_node_id=row.get('original_node_id'),
                    old_values=json.loads(row.get('old_values') or '{}'),
                    new_values=json.loads(row.get('new_values') or '{}')
                ))

            # Load edges
            edges_query = """
                SELECT * FROM delta_edges WHERE session_id = ?
            """
            edges_result = self._execute(edges_query, (session_id,))

            for row in edges_result:
                delta.edges.append(DeltaEdge(
                    id=row.get('id'),
                    session_id=session_id,
                    edge_type=row.get('edge_type', ''),
                    src=row.get('src'),
                    dst=row.get('dst'),
                    change_type=ChangeType(row.get('change_type', 'added')),
                    src_is_delta=row.get('src_is_delta', False),
                    dst_is_delta=row.get('dst_is_delta', False),
                    properties=json.loads(row.get('properties') or '{}')
                ))

            # Compute statistics
            delta.nodes_added = len([n for n in delta.nodes if n.change_type == ChangeType.ADDED])
            delta.nodes_modified = len([n for n in delta.nodes if n.change_type == ChangeType.MODIFIED])
            delta.nodes_deleted = len([n for n in delta.nodes if n.change_type == ChangeType.DELETED])
            delta.edges_added = len([e for e in delta.edges if e.change_type == ChangeType.ADDED])
            delta.edges_deleted = len([e for e in delta.edges if e.change_type == ChangeType.DELETED])

            return delta

        except Exception as e:
            logger.error(f"Could not retrieve delta: {e}")
            return None

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _next_delta_id(self, delta: DeltaCPG) -> int:
        """Generate next unique delta node ID"""
        if not delta.nodes:
            return 1
        return max(n.id for n in delta.nodes) + 1

    def _next_delta_edge_id(self, delta: DeltaCPG) -> int:
        """Generate next unique delta edge ID"""
        if not delta.edges:
            return 1
        return max(e.id for e in delta.edges) + 1

    def _ranges_overlap(
        self,
        start1: int,
        end1: int,
        start2: int,
        end2: int
    ) -> bool:
        """Check if two line ranges overlap"""
        return start1 <= end2 and start2 <= end1

    def _extract_method_from_line(
        self,
        line: str,
        filepath: str,
        line_number: int,
        language: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract method signature from a line of code.

        Simple heuristic approach - for production use, integrate
        with tree-sitter or language-specific parsers.
        """
        import re

        # Language-specific patterns
        patterns = {
            'c': [
                # C function: return_type function_name(params) {
                re.compile(r'^\s*(?:static\s+)?(?:\w+\s+\*?\s*)+(\w+)\s*\([^)]*\)\s*\{?\s*$'),
            ],
            'python': [
                # Python def
                re.compile(r'^\s*def\s+(\w+)\s*\('),
            ],
            'java': [
                # Java method
                re.compile(r'^\s*(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\('),
            ],
            'javascript': [
                # JS function
                re.compile(r'^\s*(?:async\s+)?function\s+(\w+)'),
                # JS arrow/method
                re.compile(r'^\s*(\w+)\s*[=:]\s*(?:async\s*)?\(?'),
            ],
        }

        lang_patterns = patterns.get(language, patterns.get('c', []))

        for pattern in lang_patterns:
            match = pattern.search(line)
            if match:
                method_name = match.group(1)
                # Filter out common keywords that aren't method names
                if method_name not in ('if', 'while', 'for', 'switch', 'return', 'else'):
                    return {
                        'name': method_name,
                        'line': line_number,
                        'signature': line.strip()
                    }

        return None
