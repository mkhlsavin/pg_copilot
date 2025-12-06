"""DuckDB CPG Client v2 for querying Code Property Graphs (CPG Spec v1.1)

This module provides a comprehensive Python interface for querying CPG data
stored in DuckDB using SQL and SQL/PGQ (SQL Property Graph Queries).

Supports all CPG spec v1.1 node and edge types:
- Nodes: METHOD, CALL, IDENTIFIER, LITERAL, LOCAL, PARAM, RETURN, BLOCK,
         CONTROL_STRUCTURE, TYPE_DECL, METADATA
- Edges: AST, CFG, CALL, REF, REACHING_DEF, ARGUMENT, RECEIVER, CONDITION,
         DOMINATE, POST_DOMINATE
"""

import duckdb
import logging
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CPGStatistics:
    """Statistics about the CPG"""
    method_count: int = 0
    call_node_count: int = 0
    identifier_count: int = 0
    literal_count: int = 0
    local_count: int = 0
    param_count: int = 0
    return_count: int = 0
    block_count: int = 0
    control_structure_count: int = 0
    type_decl_count: int = 0

    ast_edge_count: int = 0
    cfg_edge_count: int = 0
    call_edge_count: int = 0
    ref_edge_count: int = 0
    reaching_def_edge_count: int = 0
    argument_edge_count: int = 0
    receiver_edge_count: int = 0
    condition_edge_count: int = 0


class DuckDBCPGClient:
    """Client for querying Code Property Graphs in DuckDB (CPG Spec v1.1)"""

    def __init__(self, db_path: str = "cpg.duckdb"):
        """
        Initialize DuckDB CPG client

        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = db_path
        self.conn = None

    def connect(self) -> bool:
        """
        Connect to DuckDB and load duckpgq extension

        Returns:
            True if connection successful, False otherwise
        """
        try:
            if not Path(self.db_path).exists():
                logger.error(f"Database file not found: {self.db_path}")
                return False

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
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

    # === Basic Query Methods ===

    def execute_sql(self, query: str) -> List[tuple]:
        """
        Execute raw SQL query

        Args:
            query: SQL query string

        Returns:
            List of result tuples
        """
        if not self.conn:
            raise RuntimeError("Not connected to database. Call connect() first.")

        try:
            result = self.conn.execute(query).fetchall()
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def execute_sql_dict(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results as dictionaries

        Args:
            query: SQL query string

        Returns:
            List of result dictionaries
        """
        if not self.conn:
            raise RuntimeError("Not connected to database. Call connect() first.")

        try:
            # Use sql() method and fetchnumpy() which has better GIL handling
            # Then immediately convert to dict to avoid holding numpy arrays
            import gc

            # Execute query
            relation = self.conn.sql(query)

            # Get column names first
            columns = relation.columns

            # Fetch as native Python objects (not pandas/numpy)
            # Use pl() to get polars dataframe which has better GIL handling
            try:
                # Try using native Python list conversion
                rows_list = relation.fetchall()

                # Immediately convert to dict while GIL is held
                result = []
                for row in rows_list:
                    result.append(dict(zip(columns, row)))

                # Force cleanup
                del rows_list
                gc.collect()

                return result

            except:
                # Fallback: use basic execute and fetch
                cursor = self.conn.execute(query)
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

    def get_statistics(self) -> CPGStatistics:
        """
        Get comprehensive CPG statistics

        Returns:
            CPGStatistics object with node and edge counts
        """
        stats = CPGStatistics()

        # Node counts
        try:
            stats.method_count = self.conn.execute("SELECT COUNT(*) FROM nodes_method").fetchone()[0]
        except: pass

        try:
            stats.call_node_count = self.conn.execute("SELECT COUNT(*) FROM nodes_call").fetchone()[0]
        except: pass

        try:
            stats.identifier_count = self.conn.execute("SELECT COUNT(*) FROM nodes_identifier").fetchone()[0]
        except: pass

        try:
            stats.literal_count = self.conn.execute("SELECT COUNT(*) FROM nodes_literal").fetchone()[0]
        except: pass

        try:
            stats.local_count = self.conn.execute("SELECT COUNT(*) FROM nodes_local").fetchone()[0]
        except: pass

        try:
            stats.param_count = self.conn.execute("SELECT COUNT(*) FROM nodes_param").fetchone()[0]
        except: pass

        try:
            stats.return_count = self.conn.execute("SELECT COUNT(*) FROM nodes_return").fetchone()[0]
        except: pass

        try:
            stats.block_count = self.conn.execute("SELECT COUNT(*) FROM nodes_block").fetchone()[0]
        except: pass

        try:
            stats.control_structure_count = self.conn.execute("SELECT COUNT(*) FROM nodes_control_structure").fetchone()[0]
        except: pass

        try:
            stats.type_decl_count = self.conn.execute("SELECT COUNT(*) FROM nodes_type_decl").fetchone()[0]
        except: pass

        # Edge counts
        try:
            stats.ast_edge_count = self.conn.execute("SELECT COUNT(*) FROM edges_ast").fetchone()[0]
        except: pass

        try:
            stats.cfg_edge_count = self.conn.execute("SELECT COUNT(*) FROM edges_cfg").fetchone()[0]
        except: pass

        try:
            stats.call_edge_count = self.conn.execute("SELECT COUNT(*) FROM edges_call").fetchone()[0]
        except: pass

        try:
            stats.ref_edge_count = self.conn.execute("SELECT COUNT(*) FROM edges_ref").fetchone()[0]
        except: pass

        try:
            stats.reaching_def_edge_count = self.conn.execute("SELECT COUNT(*) FROM edges_reaching_def").fetchone()[0]
        except: pass

        try:
            stats.argument_edge_count = self.conn.execute("SELECT COUNT(*) FROM edges_argument").fetchone()[0]
        except: pass

        try:
            stats.receiver_edge_count = self.conn.execute("SELECT COUNT(*) FROM edges_receiver").fetchone()[0]
        except: pass

        try:
            stats.condition_edge_count = self.conn.execute("SELECT COUNT(*) FROM edges_condition").fetchone()[0]
        except: pass

        return stats

    # === Method Queries ===

    def find_method_by_name(self, name: str, exact: bool = True) -> List[Dict[str, Any]]:
        """
        Find methods by name

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
        Find method by full qualified name

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
        Find all methods in a specific file

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
        Get method details by ID

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
        Find call nodes by name

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
        Find identifier nodes by name

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
        Find local variable declarations by name

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
        Find parameter declarations by name

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
        Find type declarations by name

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
        Find control structures by type

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
        Get all methods directly called by a given method

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
        Get all methods that directly call a given method

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
        Get transitive call chain starting from a method

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
        Get methods with the most outgoing calls

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
        Get most frequently called methods

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
        Find all references to a declaration (variable, parameter, method, type)

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
        Find data flow paths for a variable using REACHING_DEF edges

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
        Get AST children of a node

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
        Get control flow successors of a node

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
        Get control flow predecessors of a node

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
        Find call relationships matching name patterns

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
        Find all methods that call methods matching a pattern

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


def main():
    """Example usage and testing"""
    import argparse

    parser = argparse.ArgumentParser(description="Query DuckDB CPG v2")
    parser.add_argument('--db', type=str, default='cpg.duckdb',
                        help='Path to DuckDB database file')
    parser.add_argument('--stats', action='store_true',
                        help='Show CPG statistics')
    parser.add_argument('--method', type=str,
                        help='Find method by name')
    parser.add_argument('--callees', type=str,
                        help='Get callees of method')
    parser.add_argument('--callers', type=str,
                        help='Get callers of method')
    parser.add_argument('--chain', type=str,
                        help='Get call chain from method')
    parser.add_argument('--type', type=str,
                        help='Find type declaration by name')
    parser.add_argument('--identifier', type=str,
                        help='Find identifiers by name')

    args = parser.parse_args()

    with DuckDBCPGClient(db_path=args.db) as client:
        if args.stats:
            stats = client.get_statistics()
            print("\nCPG Statistics (CPG Spec v1.1):")
            print("=" * 80)
            print(f"  Methods: {stats.method_count}")
            print(f"  Call Nodes: {stats.call_node_count}")
            print(f"  Identifiers: {stats.identifier_count}")
            print(f"  Literals: {stats.literal_count}")
            print(f"  Local Variables: {stats.local_count}")
            print(f"  Parameters: {stats.param_count}")
            print(f"  Returns: {stats.return_count}")
            print(f"  Blocks: {stats.block_count}")
            print(f"  Control Structures: {stats.control_structure_count}")
            print(f"  Type Declarations: {stats.type_decl_count}")
            print(f"\n  AST Edges: {stats.ast_edge_count}")
            print(f"  CFG Edges: {stats.cfg_edge_count}")
            print(f"  Call Edges: {stats.call_edge_count}")
            print(f"  Reference Edges: {stats.ref_edge_count}")
            print(f"  Reaching Def Edges: {stats.reaching_def_edge_count}")
            print(f"  Argument Edges: {stats.argument_edge_count}")

        if args.method:
            results = client.find_method_by_name(args.method)
            print(f"\nMethods matching '{args.method}':")
            print("=" * 80)
            for method in results:
                print(f"  {method['name']} ({method['filename']}:{method['line_number']})")
                print(f"    Full name: {method['full_name']}")

        if args.callees:
            results = client.get_direct_callees(args.callees)
            print(f"\nMethods called by '{args.callees}':")
            print("=" * 80)
            for callee in results:
                print(f"  → {callee['callee_name']} ({callee['callee_filename']}:{callee['callee_line']})")

        if args.callers:
            results = client.get_direct_callers(args.callers)
            print(f"\nMethods calling '{args.callers}':")
            print("=" * 80)
            for caller in results:
                print(f"  ← {caller['caller_name']} ({caller['caller_filename']}:{caller['caller_line']})")

        if args.chain:
            results = client.get_call_chain(args.chain)
            print(f"\nCall chain from '{args.chain}':")
            print("=" * 80)
            current_depth = 0
            for method in results:
                if method['depth'] != current_depth:
                    current_depth = method['depth']
                    print(f"\nDepth {current_depth}:")
                print(f"  → {method['name']} ({method['filename']}:{method['line_number']})")

        if args.type:
            results = client.find_type_by_name(args.type)
            print(f"\nType declarations matching '{args.type}':")
            print("=" * 80)
            for type_decl in results:
                print(f"  {type_decl['name']} ({type_decl['filename']})")
                print(f"    Full name: {type_decl['full_name']}")
                if type_decl['inherits_from_type_full_name']:
                    print(f"    Inherits: {type_decl['inherits_from_type_full_name']}")

        if args.identifier:
            results = client.find_identifiers_by_name(args.identifier)
            print(f"\nIdentifiers named '{args.identifier}':")
            print("=" * 80)
            for ident in results:
                print(f"  {ident['name']} : {ident['type_full_name']} (line {ident['line_number']})")


if __name__ == "__main__":
    main()
