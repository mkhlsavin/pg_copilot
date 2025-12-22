"""Batch Processor for CPG Export.

Handles batched export of nodes and edges from Joern to DuckDB.
"""
import logging
from typing import List, Dict, Any, Optional, Callable
import duckdb

from .progress import ProgressTracker
from src.execution.scala_parser import parse_scala_output

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Handles batched export of CPG nodes and edges.

    Provides generic batch processing with progress tracking,
    error handling, and resumable exports.
    """

    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        joern_client,
        progress: ProgressTracker,
        batch_size: int = 10000
    ):
        """
        Initialize batch processor.

        Args:
            conn: DuckDB connection
            joern_client: JoernClient instance
            progress: ProgressTracker instance
            batch_size: Rows per batch
        """
        self.conn = conn
        self.joern = joern_client
        self.progress = progress
        self.batch_size = batch_size

    def export_nodes(
        self,
        entity_type: str,
        cpg_type: str,
        query_template: str,
        insert_sql: str,
        field_count: int,
        row_parser: Callable[[List], tuple],
        limit: Optional[int] = None,
        start_offset: int = 0
    ) -> int:
        """
        Export nodes of a specific type in batches.

        Args:
            entity_type: Entity type name (e.g., 'methods', 'calls')
            cpg_type: CPG node type (e.g., 'Method', 'Call')
            query_template: CPGQL query template with {offset} and {batch_size}
            insert_sql: SQL INSERT statement
            field_count: Number of fields in INSERT
            row_parser: Function to parse row from Joern output
            limit: Optional limit on total rows
            start_offset: Offset to start from (for resumption)

        Returns:
            Total count of exported rows
        """
        # Check if already completed
        if self.progress.is_completed(entity_type):
            count = self.progress.get_existing_count(f"nodes_{entity_type}")
            logger.info(f"[SKIP] {entity_type}: already completed ({count} records)")
            return count

        logger.info(f"Starting batched export of {cpg_type} nodes...")

        # Get total count
        count_query = f"cpg.{cpg_type.lower()}.size"
        try:
            count_result = self.joern.run_query(count_query)
            total_count = int(count_result.strip()) if count_result.strip().isdigit() else 0
        except Exception as e:
            logger.warning(f"Could not get count for {cpg_type}: {e}")
            total_count = 0

        if limit:
            total_count = min(total_count, limit)

        logger.info(f"Total {cpg_type} count: {total_count}")

        offset = start_offset
        total_exported = 0
        consecutive_empty = 0
        max_consecutive_empty = 3

        while True:
            # Check limit
            if limit and offset >= limit:
                break

            current_batch_size = min(self.batch_size, (limit - offset) if limit else self.batch_size)

            # Build query
            query = query_template.format(offset=offset, batch_size=current_batch_size)

            try:
                result = self.joern.run_query(query)
                rows = parse_scala_output(result)

                if not rows:
                    consecutive_empty += 1
                    if consecutive_empty >= max_consecutive_empty:
                        logger.info(f"{cpg_type}: No more data after {total_exported} rows")
                        break
                    offset += current_batch_size
                    continue

                consecutive_empty = 0

                # Parse and insert rows
                batch_data = []
                for row in rows:
                    try:
                        parsed = row_parser(row)
                        if parsed and len(parsed) == field_count:
                            batch_data.append(parsed)
                    except Exception as e:
                        logger.debug(f"Parse error for {cpg_type} row: {e}")
                        continue

                if batch_data:
                    placeholders = ','.join(['?' for _ in range(field_count)])
                    self.conn.executemany(insert_sql, batch_data)
                    total_exported += len(batch_data)

                    if total_exported % 10000 == 0:
                        logger.info(f"{cpg_type}: Exported {total_exported} rows...")

                    # Update progress
                    self.progress.mark_in_progress(
                        entity_type, total_count, total_exported, offset
                    )

                offset += current_batch_size

            except Exception as e:
                logger.error(f"Batch export error for {cpg_type} at offset {offset}: {e}")
                self.progress.mark_failed(entity_type, str(e), offset)
                raise

        # Mark completed
        self.progress.mark_completed(entity_type, total_exported)
        return total_exported

    def export_edges(
        self,
        entity_type: str,
        edge_query_template: str,
        insert_sql: str,
        limit: Optional[int] = None,
        start_offset: int = 0
    ) -> int:
        """
        Export edges via node traversal in batches.

        Args:
            entity_type: Entity type name (e.g., 'ast_edges', 'cfg_edges')
            edge_query_template: CPGQL query template for edges
            insert_sql: SQL INSERT statement
            limit: Optional limit on total edges
            start_offset: Offset to start from

        Returns:
            Total count of exported edges
        """
        # Check if already completed
        if self.progress.is_completed(entity_type):
            count = self.progress.get_existing_count(f"edges_{entity_type.replace('_edges', '')}")
            logger.info(f"[SKIP] {entity_type}: already completed ({count} records)")
            return count

        logger.info(f"Starting batched export of {entity_type}...")

        offset = start_offset
        total_exported = 0
        consecutive_empty = 0

        while True:
            if limit and offset >= limit:
                break

            current_batch_size = self.batch_size

            # Build query
            query = edge_query_template.format(offset=offset, batch_size=current_batch_size)

            try:
                result = self.joern.run_query(query)
                rows = parse_scala_output(result)

                if not rows:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        break
                    offset += current_batch_size
                    continue

                consecutive_empty = 0

                # Parse and insert edges
                batch_data = []
                for row in rows:
                    try:
                        if len(row) >= 2:
                            src_id = int(row[0]) if row[0] else None
                            dst_id = int(row[1]) if row[1] else None
                            if src_id is not None and dst_id is not None:
                                batch_data.append((src_id, dst_id))
                    except (ValueError, TypeError) as e:
                        continue

                if batch_data:
                    self.conn.executemany(insert_sql, batch_data)
                    total_exported += len(batch_data)

                    if total_exported % 50000 == 0:
                        logger.info(f"{entity_type}: Exported {total_exported} edges...")

                    self.progress.mark_in_progress(
                        entity_type, 0, total_exported, offset
                    )

                offset += current_batch_size

            except Exception as e:
                logger.error(f"Batch edge export error for {entity_type} at offset {offset}: {e}")
                self.progress.mark_failed(entity_type, str(e), offset)
                raise

        self.progress.mark_completed(entity_type, total_exported)
        return total_exported

    def export_simple_nodes(
        self,
        entity_type: str,
        cpg_type: str,
        query_template: str,
        insert_sql: str,
        field_parsers: List[Callable],
        limit: Optional[int] = None,
        start_offset: int = 0
    ) -> int:
        """
        Export simple nodes using field parser list.

        Args:
            entity_type: Entity type name
            cpg_type: CPG node type
            query_template: CPGQL query template
            insert_sql: SQL INSERT statement
            field_parsers: List of functions to parse each field
            limit: Optional limit
            start_offset: Starting offset

        Returns:
            Total exported count
        """

        def row_parser(row):
            result = []
            for i, parser in enumerate(field_parsers):
                if i < len(row):
                    try:
                        result.append(parser(row[i]))
                    except Exception:
                        result.append(None)
                else:
                    result.append(None)
            return tuple(result)

        return self.export_nodes(
            entity_type=entity_type,
            cpg_type=cpg_type,
            query_template=query_template,
            insert_sql=insert_sql,
            field_count=len(field_parsers),
            row_parser=row_parser,
            limit=limit,
            start_offset=start_offset
        )

    def export_call_edges(
        self,
        limit: Optional[int] = None,
        start_offset: int = 0
    ) -> int:
        """
        Export CALL edges (call sites to target methods).

        Returns:
            Total exported count
        """
        entity_type = "call_edges"

        if self.progress.is_completed(entity_type):
            count = self.progress.get_existing_count("edges_call")
            logger.info(f"[SKIP] {entity_type}: already completed ({count} records)")
            return count

        logger.info("Starting batched export of CALL edges...")

        # Query call -> callee edges via method resolution
        query_template = """
            cpg.call.drop({offset}).take({batch_size}).map {{ c =>
                val calleeOpt = c.callee.headOption
                (c.id, calleeOpt.map(_.id).getOrElse(-1L))
            }}.filter(_._2 != -1L).l
        """

        insert_sql = """
            INSERT INTO edges_call (src, dst)
            VALUES (?, ?)
            ON CONFLICT DO NOTHING
        """

        return self.export_edges(
            entity_type=entity_type,
            edge_query_template=query_template,
            insert_sql=insert_sql,
            limit=limit,
            start_offset=start_offset
        )

    def export_reaching_def_edges(
        self,
        limit: Optional[int] = None,
        start_offset: int = 0
    ) -> int:
        """
        Export REACHING_DEF edges (data flow).

        Returns:
            Total exported count
        """
        entity_type = "reaching_def_edges"

        if self.progress.is_completed(entity_type):
            count = self.progress.get_existing_count("edges_reaching_def")
            logger.info(f"[SKIP] {entity_type}: already completed ({count} records)")
            return count

        logger.info("Starting batched export of REACHING_DEF edges...")

        offset = start_offset
        total_exported = 0
        consecutive_empty = 0

        while True:
            if limit and offset >= limit:
                break

            query = f"""
                cpg.method.drop({offset}).take({self.batch_size}).flatMap {{ m =>
                    m.ast.isIdentifier.flatMap {{ ident =>
                        ident.reachingDefIn.map {{ rd =>
                            val varName = rd match {{
                                case i: io.shiftleft.codepropertygraph.generated.nodes.Identifier => i.name
                                case l: io.shiftleft.codepropertygraph.generated.nodes.Local => l.name
                                case p: io.shiftleft.codepropertygraph.generated.nodes.MethodParameterIn => p.name
                                case _ => ""
                            }}
                            (rd.id, ident.id, varName)
                        }}
                    }}
                }}.l
            """

            try:
                result = self.joern.run_query(query)
                rows = parse_scala_output(result)

                if not rows:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        break
                    offset += self.batch_size
                    continue

                consecutive_empty = 0

                batch_data = []
                for row in rows:
                    try:
                        if len(row) >= 3:
                            src_id = int(row[0]) if row[0] else None
                            dst_id = int(row[1]) if row[1] else None
                            variable = str(row[2]) if row[2] else ''
                            if src_id is not None and dst_id is not None:
                                batch_data.append((src_id, dst_id, variable))
                    except (ValueError, TypeError):
                        continue

                if batch_data:
                    self.conn.executemany("""
                        INSERT INTO edges_reaching_def (src, dst, variable)
                        VALUES (?, ?, ?)
                        ON CONFLICT DO NOTHING
                    """, batch_data)
                    total_exported += len(batch_data)

                    if total_exported % 50000 == 0:
                        logger.info(f"REACHING_DEF: Exported {total_exported} edges...")

                    self.progress.mark_in_progress(
                        entity_type, 0, total_exported, offset
                    )

                offset += self.batch_size

            except Exception as e:
                logger.error(f"REACHING_DEF export error at offset {offset}: {e}")
                self.progress.mark_failed(entity_type, str(e), offset)
                raise

        self.progress.mark_completed(entity_type, total_exported)
        return total_exported
