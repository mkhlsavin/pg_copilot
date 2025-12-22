"""DuckDB CPG Client for querying Code Property Graphs.

Main client class for CPG queries (CPG Spec v1.1).
Supports both direct and pooled connection modes.
"""
import duckdb
import gc
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
from contextlib import contextmanager

from .connection import DuckDBConnectionPool
from .models import CPGStatistics

logger = logging.getLogger(__name__)


class DuckDBCPGClient:
    """Client for querying Code Property Graphs in DuckDB (CPG Spec v1.1).

    Supports two modes of operation:
    1. Direct connection (default): Single connection, not thread-safe
    2. Pooled connection: Uses DuckDBConnectionPool for thread-safe access

    Example (direct):
        client = DuckDBCPGClient("cpg.duckdb")
        client.connect()
        results = client.find_methods_by_name("exec%")
        client.disconnect()

    Example (pooled):
        client = DuckDBCPGClient("cpg.duckdb", use_pool=True, pool_size=4)
        client.connect()  # Initializes pool
        results = client.find_methods_by_name("exec%")  # Thread-safe
        client.disconnect()  # Closes pool
    """

    def __init__(
        self,
        db_path: str = "cpg.duckdb",
        use_pool: bool = False,
        pool_size: int = 4,
        pool_max_idle_time: float = 300.0
    ):
        """
        Initialize DuckDB CPG client.

        Args:
            db_path: Path to DuckDB database file
            use_pool: Whether to use connection pooling (thread-safe mode)
            pool_size: Number of connections in pool (only if use_pool=True)
            pool_max_idle_time: Max idle time before recycling (only if use_pool=True)
        """
        self.db_path = db_path
        self.use_pool = use_pool
        self.pool_size = pool_size
        self.pool_max_idle_time = pool_max_idle_time

        self.conn = None  # Direct connection (if not using pool)
        self._pool: Optional[DuckDBConnectionPool] = None  # Connection pool

    def connect(self) -> bool:
        """
        Connect to DuckDB and load duckpgq extension.

        If use_pool=True, initializes the connection pool.
        Otherwise, creates a single direct connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            if not Path(self.db_path).exists():
                logger.error(f"Database file not found: {self.db_path}")
                return False

            if self.use_pool:
                # Initialize connection pool
                self._pool = DuckDBConnectionPool(
                    self.db_path,
                    pool_size=self.pool_size,
                    max_idle_time=self.pool_max_idle_time
                )
                success = self._pool.initialize()
                if success:
                    logger.info(f"Connection pool initialized: {self.db_path}")
                return success
            else:
                # Direct connection
                logger.info(f"Connecting to DuckDB: {self.db_path}")
                self.conn = duckdb.connect(self.db_path)

                # Load duckpgq extension
                try:
                    self.conn.execute("LOAD duckpgq;")
                    logger.info("DuckPGQ extension loaded")
                except Exception as e:
                    logger.warning(f"DuckPGQ extension not available: {e}")

                return True
        except Exception as e:
            logger.error(f"Failed to connect to DuckDB: {e}")
            return False

    def disconnect(self):
        """Close database connection(s)."""
        if self.use_pool and self._pool:
            self._pool.close_all()
            logger.info("Connection pool closed")
        elif self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def _get_connection(self):
        """
        Get a connection for query execution.

        For pooled mode, this should be used with a context manager.
        For direct mode, returns the single connection.
        """
        if self.use_pool:
            if not self._pool:
                raise RuntimeError("Connection pool not initialized. Call connect() first.")
            return self._pool.get_connection()
        else:
            if not self.conn:
                raise RuntimeError("Not connected to database. Call connect() first.")
            return self._direct_connection_context()

    @contextmanager
    def _direct_connection_context(self):
        """Context manager wrapper for direct connection (for API consistency)."""
        yield self.conn

    def get_pool_stats(self) -> Optional[Dict[str, Any]]:
        """Get connection pool statistics (only available in pooled mode)."""
        if self.use_pool and self._pool:
            return self._pool.get_stats()
        return None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    # === Basic Query Methods ===

    def execute_sql(self, query: str) -> List[tuple]:
        """
        Execute raw SQL query.

        Thread-safe when using pooled connections.

        Args:
            query: SQL query string

        Returns:
            List of result tuples
        """
        try:
            with self._get_connection() as conn:
                result = conn.execute(query).fetchall()
                return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def execute_sql_dict(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results as dictionaries.

        Thread-safe when using pooled connections.

        Args:
            query: SQL query string

        Returns:
            List of result dictionaries
        """
        try:
            with self._get_connection() as conn:
                # Execute query
                relation = conn.sql(query)

                # Get column names first
                columns = relation.columns

                # Fetch as native Python objects
                try:
                    rows_list = relation.fetchall()

                    # Immediately convert to dict
                    result = []
                    for row in rows_list:
                        result.append(dict(zip(columns, row)))

                    # Force cleanup
                    del rows_list
                    gc.collect()

                    return result

                except duckdb.Error as e:
                    # Fallback: use basic execute and fetch
                    logger.debug(f"Relation fetchall failed, using cursor fallback: {e}")
                    cursor = conn.execute(query)
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()

                    result = []
                    for row in rows:
                        result.append(dict(zip(columns, row)))

                    return result

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    # === CPG Statistics ===

    def _safe_count_table(self, conn: duckdb.DuckDBPyConnection, table_name: str) -> int:
        """
        Safely count rows in a table, returning 0 if table doesn't exist.

        Args:
            conn: DuckDB connection
            table_name: Name of table to count

        Returns:
            Row count, or 0 if table doesn't exist or error occurs
        """
        try:
            result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            return result[0] if result else 0
        except duckdb.CatalogException:
            # Table doesn't exist - this is expected for optional tables
            logger.debug(f"Table {table_name} not found in CPG")
            return 0
        except duckdb.Error as e:
            logger.debug(f"Error counting table {table_name}: {e}")
            return 0

    def get_statistics(self) -> CPGStatistics:
        """
        Get comprehensive CPG statistics.

        Thread-safe when using pooled connections.

        Returns:
            CPGStatistics object with node and edge counts
        """
        stats = CPGStatistics()

        with self._get_connection() as conn:
            # Node counts
            stats.method_count = self._safe_count_table(conn, "nodes_method")
            stats.call_node_count = self._safe_count_table(conn, "nodes_call")
            stats.identifier_count = self._safe_count_table(conn, "nodes_identifier")
            stats.literal_count = self._safe_count_table(conn, "nodes_literal")
            stats.local_count = self._safe_count_table(conn, "nodes_local")
            stats.param_count = self._safe_count_table(conn, "nodes_param")
            stats.return_count = self._safe_count_table(conn, "nodes_return")
            stats.block_count = self._safe_count_table(conn, "nodes_block")
            stats.control_structure_count = self._safe_count_table(conn, "nodes_control_structure")
            stats.type_decl_count = self._safe_count_table(conn, "nodes_type_decl")

            # Edge counts
            stats.ast_edge_count = self._safe_count_table(conn, "edges_ast")
            stats.cfg_edge_count = self._safe_count_table(conn, "edges_cfg")
            stats.call_edge_count = self._safe_count_table(conn, "edges_call")
            stats.ref_edge_count = self._safe_count_table(conn, "edges_ref")
            stats.reaching_def_edge_count = self._safe_count_table(conn, "edges_reaching_def")
            stats.argument_edge_count = self._safe_count_table(conn, "edges_argument")
            stats.receiver_edge_count = self._safe_count_table(conn, "edges_receiver")
            stats.condition_edge_count = self._safe_count_table(conn, "edges_condition")

        return stats

    # === Method Queries ===

    def find_method_by_name(self, name: str, exact: bool = True) -> List[Dict[str, Any]]:
        """
        Find methods by name.

        Args:
            name: Method name to search for
            exact: If True, exact match; if False, LIKE pattern match

        Returns:
            List of matching methods
        """
        if exact:
            query = f"""
                SELECT id, name, full_name, filename, line_number, signature, code
                FROM nodes_method
                WHERE name = '{name}'
            """
        else:
            query = f"""
                SELECT id, name, full_name, filename, line_number, signature, code
                FROM nodes_method
                WHERE name LIKE '%{name}%'
            """

        return self.execute_sql_dict(query)

    def find_method_by_full_name(self, full_name: str) -> Optional[Dict[str, Any]]:
        """
        Find method by full qualified name.

        Args:
            full_name: Full method name (e.g., "com.example.MyClass.myMethod:void()")

        Returns:
            Method details or None if not found
        """
        query = f"""
            SELECT id, name, full_name, filename, line_number, signature, code,
                   is_external, ast_parent_type, ast_parent_full_name
            FROM nodes_method
            WHERE full_name = '{full_name}'
        """

        results = self.execute_sql_dict(query)
        return results[0] if results else None

    def find_methods_in_file(self, filename: str) -> List[Dict[str, Any]]:
        """
        Find all methods in a specific file.

        Args:
            filename: Source file path (can be partial)

        Returns:
            List of methods in the file
        """
        query = f"""
            SELECT id, name, full_name, filename, line_number, signature
            FROM nodes_method
            WHERE filename LIKE '%{filename}%'
            ORDER BY line_number
        """

        return self.execute_sql_dict(query)

    def get_method_by_id(self, method_id: int) -> Optional[Dict[str, Any]]:
        """
        Get method details by ID.

        Args:
            method_id: Method ID

        Returns:
            Method details or None if not found
        """
        query = f"""
            SELECT id, name, full_name, filename, line_number, signature, code,
                   is_external, ast_parent_type, ast_parent_full_name
            FROM nodes_method
            WHERE id = {method_id}
        """

        results = self.execute_sql_dict(query)
        return results[0] if results else None

    # === Call Node Queries ===

    def find_calls_by_name(self, name: str, exact: bool = True) -> List[Dict[str, Any]]:
        """
        Find call nodes by name.

        Args:
            name: Call name to search for
            exact: If True, exact match; if False, LIKE pattern match

        Returns:
            List of matching call nodes
        """
        if exact:
            query = f"""
                SELECT id, name, method_full_name, signature, type_full_name,
                       dispatch_type, code, line_number
                FROM nodes_call
                WHERE name = '{name}'
            """
        else:
            query = f"""
                SELECT id, name, method_full_name, signature, type_full_name,
                       dispatch_type, code, line_number
                FROM nodes_call
                WHERE name LIKE '%{name}%'
            """

        return self.execute_sql_dict(query)

    # === Identifier Queries ===

    def find_identifiers_by_name(self, name: str) -> List[Dict[str, Any]]:
        """
        Find identifier nodes by name.

        Args:
            name: Identifier name

        Returns:
            List of matching identifiers
        """
        query = f"""
            SELECT id, name, type_full_name, code, line_number
            FROM nodes_identifier
            WHERE name = '{name}'
        """

        return self.execute_sql_dict(query)

    # === Local Variable Queries ===

    def find_locals_by_name(self, name: str) -> List[Dict[str, Any]]:
        """
        Find local variable declarations by name.

        Args:
            name: Local variable name

        Returns:
            List of matching local variables
        """
        query = f"""
            SELECT id, name, type_full_name, code, line_number
            FROM nodes_local
            WHERE name = '{name}'
        """

        return self.execute_sql_dict(query)

    # === Parameter Queries ===

    def find_params_by_name(self, name: str) -> List[Dict[str, Any]]:
        """
        Find parameter declarations by name.

        Args:
            name: Parameter name

        Returns:
            List of matching parameters
        """
        query = f"""
            SELECT id, name, type_full_name, code, line_number, index,
                   is_variadic, evaluation_strategy
            FROM nodes_param
            WHERE name = '{name}'
        """

        return self.execute_sql_dict(query)

    # === Type Declaration Queries ===

    def find_type_by_name(self, name: str, exact: bool = True) -> List[Dict[str, Any]]:
        """
        Find type declarations by name.

        Args:
            name: Type name to search for
            exact: If True, exact match; if False, LIKE pattern match

        Returns:
            List of matching type declarations
        """
        if exact:
            query = f"""
                SELECT id, name, full_name, is_external, filename,
                       inherits_from_type_full_name, alias_type_full_name
                FROM nodes_type_decl
                WHERE name = '{name}'
            """
        else:
            query = f"""
                SELECT id, name, full_name, is_external, filename,
                       inherits_from_type_full_name, alias_type_full_name
                FROM nodes_type_decl
                WHERE name LIKE '%{name}%'
            """

        return self.execute_sql_dict(query)

    # === Control Structure Queries ===

    def find_control_structures_by_type(self, control_type: str) -> List[Dict[str, Any]]:
        """
        Find control structures by type.

        Args:
            control_type: Type (IF, WHILE, FOR, SWITCH, TRY, etc.)

        Returns:
            List of matching control structures
        """
        query = f"""
            SELECT id, control_structure_type, code, line_number
            FROM nodes_control_structure
            WHERE control_structure_type = '{control_type}'
        """

        return self.execute_sql_dict(query)

    # === Call Graph Queries (Using CALL edges) ===

    def get_direct_callees(self, method_name: str) -> List[Dict[str, Any]]:
        """
        Get all methods directly called by a given method.

        Args:
            method_name: Name of the calling method

        Returns:
            List of called methods with their details
        """
        query = f"""
            SELECT
                caller.name AS caller_name,
                caller.full_name AS caller_full_name,
                callee.id AS callee_id,
                callee.name AS callee_name,
                callee.full_name AS callee_full_name,
                callee.filename AS callee_filename,
                callee.line_number AS callee_line
            FROM edges_call ec
            JOIN nodes_call c ON ec.src = c.id
            JOIN nodes_method caller ON c.containing_method_id = caller.id
            JOIN nodes_method callee ON ec.dst = callee.id
            WHERE caller.name = '{method_name}'
        """

        return self.execute_sql_dict(query)

    def get_direct_callers(self, method_name: str) -> List[Dict[str, Any]]:
        """
        Get all methods that directly call a given method.

        Args:
            method_name: Name of the called method

        Returns:
            List of calling methods with their details
        """
        query = f"""
            SELECT DISTINCT
                caller.id AS caller_id,
                caller.name AS caller_name,
                caller.full_name AS caller_full_name,
                caller.filename AS caller_filename,
                caller.line_number AS caller_line
            FROM edges_call ec
            JOIN nodes_call c ON ec.src = c.id
            JOIN nodes_method callee ON ec.dst = callee.id
            JOIN nodes_method caller ON c.containing_method_id = caller.id
            WHERE callee.name = '{method_name}'
        """

        return self.execute_sql_dict(query)

    def get_call_chain(self, method_name: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        """
        Get transitive call chain starting from a method.

        Args:
            method_name: Starting method name
            max_depth: Maximum depth to traverse (default 5)

        Returns:
            List of methods in the call chain with depth information
        """
        query = f"""
            WITH RECURSIVE call_chain AS (
                -- Base case: find starting method and its direct calls
                SELECT
                    ec.src as call_id,
                    ec.dst as method_id,
                    1 as depth
                FROM edges_call ec
                JOIN nodes_call c ON ec.src = c.id
                JOIN nodes_method m_start ON c.containing_method_id = m_start.id
                WHERE m_start.name = '{method_name}'

                UNION ALL

                -- Recursive case: follow the chain
                SELECT
                    ec2.src,
                    ec2.dst,
                    cc.depth + 1
                FROM edges_call ec2
                JOIN call_chain cc ON ec2.src IN (
                    SELECT c2.id FROM nodes_call c2
                    WHERE c2.method_full_name IN (
                        SELECT m2.full_name FROM nodes_method m2 WHERE m2.id = cc.method_id
                    )
                )
                WHERE cc.depth < {max_depth}
            )
            SELECT DISTINCT
                m.id,
                m.name,
                m.full_name,
                m.filename,
                m.line_number,
                MIN(cc.depth) as depth
            FROM call_chain cc
            JOIN nodes_method m ON cc.method_id = m.id
            GROUP BY m.id, m.name, m.full_name, m.filename, m.line_number
            ORDER BY depth, m.name
        """

        return self.execute_sql_dict(query)

    def get_methods_with_most_calls(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get methods with the most outgoing calls.

        Args:
            limit: Number of results to return

        Returns:
            List of methods sorted by call count
        """
        query = f"""
            SELECT
                m.id,
                m.name,
                m.full_name,
                m.filename,
                m.line_number,
                COUNT(DISTINCT c.id) as call_count
            FROM nodes_method m
            LEFT JOIN nodes_call c ON c.containing_method_id = m.id
            GROUP BY m.id, m.name, m.full_name, m.filename, m.line_number
            ORDER BY call_count DESC
            LIMIT {limit}
        """

        return self.execute_sql_dict(query)

    def get_most_called_methods(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most frequently called methods.

        Args:
            limit: Number of results to return

        Returns:
            List of methods sorted by incoming call count
        """
        query = f"""
            SELECT
                m.id,
                m.name,
                m.full_name,
                m.filename,
                m.line_number,
                COUNT(ec.src) as called_count
            FROM nodes_method m
            LEFT JOIN edges_call ec ON m.id = ec.dst
            GROUP BY m.id, m.name, m.full_name, m.filename, m.line_number
            ORDER BY called_count DESC
            LIMIT {limit}
        """

        return self.execute_sql_dict(query)

    # === Reference (REF) Edge Queries ===

    def find_references_to_declaration(self, declaration_name: str) -> List[Dict[str, Any]]:
        """
        Find all references to a declaration (variable, parameter, method, type).

        Args:
            declaration_name: Name of the declaration

        Returns:
            List of identifiers that reference this declaration
        """
        query = f"""
            SELECT DISTINCT
                i.id, i.name, i.type_full_name, i.code, i.line_number
            FROM edges_ref er
            JOIN nodes_identifier i ON er.src = i.id
            JOIN (
                SELECT id, name FROM nodes_local
                UNION ALL
                SELECT id, name FROM nodes_param
                UNION ALL
                SELECT id, name FROM nodes_method
                UNION ALL
                SELECT id, name FROM nodes_type_decl
            ) decl ON er.dst = decl.id
            WHERE decl.name = '{declaration_name}'
        """

        return self.execute_sql_dict(query)

    # === Data Flow (REACHING_DEF) Queries ===

    def find_data_flow_paths(self, variable_name: str, max_hops: int = 5) -> List[Dict[str, Any]]:
        """
        Find data flow paths for a variable using REACHING_DEF edges.

        Args:
            variable_name: Variable name to track
            max_hops: Maximum number of hops to traverse

        Returns:
            List of nodes in the data flow path
        """
        query = f"""
            WITH RECURSIVE data_flow AS (
                -- Base case: find initial definitions
                SELECT
                    erd.src as src_id,
                    erd.dst as dst_id,
                    erd.variable,
                    1 as hops
                FROM edges_reaching_def erd
                WHERE erd.variable = '{variable_name}'

                UNION ALL

                -- Recursive case: follow the flow
                SELECT
                    erd2.src,
                    erd2.dst,
                    erd2.variable,
                    df.hops + 1
                FROM edges_reaching_def erd2
                JOIN data_flow df ON erd2.src = df.dst_id
                WHERE df.hops < {max_hops}
                  AND erd2.variable = '{variable_name}'
            )
            SELECT DISTINCT
                df.src_id,
                df.dst_id,
                df.variable,
                df.hops
            FROM data_flow df
            ORDER BY hops
        """

        return self.execute_sql_dict(query)

    # === AST Traversal Queries ===

    def get_ast_children(self, node_id: int, max_depth: int = 1) -> List[Dict[str, Any]]:
        """
        Get AST children of a node.

        Args:
            node_id: Parent node ID
            max_depth: Maximum depth to traverse (1 = direct children only)

        Returns:
            List of child nodes
        """
        if max_depth == 1:
            query = f"""
                SELECT DISTINCT ea.dst as child_id
                FROM edges_ast ea
                WHERE ea.src = {node_id}
            """
        else:
            query = f"""
                WITH RECURSIVE ast_descendants AS (
                    -- Base case
                    SELECT dst as child_id, 1 as depth
                    FROM edges_ast
                    WHERE src = {node_id}

                    UNION ALL

                    -- Recursive case
                    SELECT ea.dst, ad.depth + 1
                    FROM edges_ast ea
                    JOIN ast_descendants ad ON ea.src = ad.child_id
                    WHERE ad.depth < {max_depth}
                )
                SELECT DISTINCT child_id, depth
                FROM ast_descendants
                ORDER BY depth
            """

        return self.execute_sql_dict(query)

    # === CFG Traversal Queries ===

    def get_cfg_successors(self, node_id: int) -> List[int]:
        """
        Get control flow successors of a node.

        Args:
            node_id: Node ID

        Returns:
            List of successor node IDs
        """
        query = f"""
            SELECT dst
            FROM edges_cfg
            WHERE src = {node_id}
        """

        results = self.execute_sql(query)
        return [r[0] for r in results]

    def get_cfg_predecessors(self, node_id: int) -> List[int]:
        """
        Get control flow predecessors of a node.

        Args:
            node_id: Node ID

        Returns:
            List of predecessor node IDs
        """
        query = f"""
            SELECT src
            FROM edges_cfg
            WHERE dst = {node_id}
        """

        results = self.execute_sql(query)
        return [r[0] for r in results]

    # === Pattern Matching Queries ===

    def find_call_pattern(self, caller_pattern: str, callee_pattern: str) -> List[Dict[str, Any]]:
        """
        Find call relationships matching name patterns.

        Args:
            caller_pattern: Pattern for caller method name (SQL LIKE syntax)
            callee_pattern: Pattern for callee method name (SQL LIKE syntax)

        Returns:
            List of matching call relationships
        """
        query = f"""
            SELECT DISTINCT
                caller.name AS caller_name,
                caller.full_name AS caller_full_name,
                caller.filename AS caller_file,
                callee.name AS callee_name,
                callee.full_name AS callee_full_name,
                callee.filename AS callee_file
            FROM edges_call ec
            JOIN nodes_call c ON ec.src = c.id
            JOIN nodes_method caller ON c.containing_method_id = caller.id
            JOIN nodes_method callee ON ec.dst = callee.id
            WHERE caller.name LIKE '{caller_pattern}'
              AND callee.name LIKE '{callee_pattern}'
        """

        return self.execute_sql_dict(query)

    def find_methods_calling_pattern(self, callee_pattern: str) -> List[Dict[str, Any]]:
        """
        Find all methods that call methods matching a pattern.

        Args:
            callee_pattern: Pattern for callee method name (SQL LIKE syntax)

        Returns:
            List of caller methods
        """
        query = f"""
            SELECT DISTINCT
                caller.id,
                caller.name,
                caller.full_name,
                caller.filename,
                caller.line_number
            FROM edges_call ec
            JOIN nodes_call c ON ec.src = c.id
            JOIN nodes_method caller ON c.containing_method_id = caller.id
            JOIN nodes_method callee ON ec.dst = callee.id
            WHERE callee.name LIKE '{callee_pattern}'
        """

        return self.execute_sql_dict(query)
