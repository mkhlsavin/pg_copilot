"""DuckDB CPG Client for querying exported Code Property Graphs

This module provides a high-level Python interface for querying CPG data
stored in DuckDB using SQL/PGQ (SQL Property Graph Queries).
"""
import duckdb
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DuckDBCPGClient:
    """Client for querying Code Property Graphs in DuckDB using SQL/PGQ"""

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
            self.conn.execute("LOAD duckpgq;")
            logger.info("DuckPGQ extension loaded")

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
            result = self.conn.execute(query).fetchdf().to_dict('records')
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    # === CPG Statistics ===

    def get_statistics(self) -> Dict[str, int]:
        """
        Get CPG statistics

        Returns:
            Dictionary with method count, call count, etc.
        """
        stats = {}

        # Method count
        result = self.conn.execute("SELECT COUNT(*) FROM methods").fetchone()
        stats['method_count'] = result[0]

        # Call count
        result = self.conn.execute("SELECT COUNT(*) FROM calls").fetchone()
        stats['call_count'] = result[0]

        # Methods with calls
        result = self.conn.execute("""
            SELECT COUNT(DISTINCT caller_id) FROM calls
        """).fetchone()
        stats['methods_with_outgoing_calls'] = result[0]

        # Average calls per method
        if stats['method_count'] > 0:
            stats['avg_calls_per_method'] = stats['call_count'] / stats['method_count']
        else:
            stats['avg_calls_per_method'] = 0

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
                SELECT id, name, filename, line_number, signature
                FROM methods
                WHERE name = '{name}'
            """
        else:
            query = f"""
                SELECT id, name, filename, line_number, signature
                FROM methods
                WHERE name LIKE '%{name}%'
            """

        return self.execute_sql_dict(query)

    def find_methods_in_file(self, filename: str) -> List[Dict[str, Any]]:
        """
        Find all methods in a specific file

        Args:
            filename: Source file path (can be partial)

        Returns:
            List of methods in the file
        """
        query = f"""
            SELECT id, name, filename, line_number, signature
            FROM methods
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
            SELECT id, name, filename, line_number, signature, code
            FROM methods
            WHERE id = {method_id}
        """

        results = self.execute_sql_dict(query)
        return results[0] if results else None

    # === Call Graph Queries ===

    def get_direct_callees(self, method_name: str) -> List[Dict[str, Any]]:
        """
        Get all methods directly called by a given method (SQL/PGQ)

        Args:
            method_name: Name of the calling method

        Returns:
            List of called methods with their details
        """
        query = f"""
            SELECT *
            FROM GRAPH_TABLE (cpg
                MATCH (caller:method)-[e:calls]->(callee:method)
                WHERE caller.name = '{method_name}'
                COLUMNS (
                    caller.name AS caller_name,
                    callee.id AS callee_id,
                    callee.name AS callee_name,
                    callee.filename AS callee_filename,
                    callee.line_number AS callee_line
                )
            )
        """

        return self.execute_sql_dict(query)

    def get_direct_callers(self, method_name: str) -> List[Dict[str, Any]]:
        """
        Get all methods that directly call a given method (SQL/PGQ)

        Args:
            method_name: Name of the called method

        Returns:
            List of calling methods with their details
        """
        query = f"""
            SELECT *
            FROM GRAPH_TABLE (cpg
                MATCH (caller:method)-[e:calls]->(callee:method)
                WHERE callee.name = '{method_name}'
                COLUMNS (
                    caller.id AS caller_id,
                    caller.name AS caller_name,
                    caller.filename AS caller_filename,
                    caller.line_number AS caller_line,
                    callee.name AS callee_name
                )
            )
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
                -- Base case: direct calls from method
                SELECT
                    c.caller_id,
                    c.callee_id,
                    1 as depth,
                    m.name as method_name
                FROM calls c
                JOIN methods m ON c.callee_id = m.id
                WHERE c.caller_id = (SELECT id FROM methods WHERE name = '{method_name}')

                UNION ALL

                -- Recursive case: follow the chain
                SELECT
                    c.caller_id,
                    c.callee_id,
                    cc.depth + 1,
                    m.name as method_name
                FROM calls c
                JOIN call_chain cc ON c.caller_id = cc.callee_id
                JOIN methods m ON c.callee_id = m.id
                WHERE cc.depth < {max_depth}
            )
            SELECT DISTINCT
                m.id,
                m.name,
                m.filename,
                m.line_number,
                cc.depth
            FROM call_chain cc
            JOIN methods m ON cc.callee_id = m.id
            ORDER BY cc.depth, m.name
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
                m.filename,
                m.line_number,
                COUNT(c.callee_id) as call_count
            FROM methods m
            LEFT JOIN calls c ON m.id = c.caller_id
            GROUP BY m.id, m.name, m.filename, m.line_number
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
                m.filename,
                m.line_number,
                COUNT(c.caller_id) as called_count
            FROM methods m
            LEFT JOIN calls c ON m.id = c.callee_id
            GROUP BY m.id, m.name, m.filename, m.line_number
            ORDER BY called_count DESC
            LIMIT {limit}
        """

        return self.execute_sql_dict(query)

    # === Pattern Matching Queries ===

    def find_call_pattern(self, caller_pattern: str, callee_pattern: str) -> List[Dict[str, Any]]:
        """
        Find call relationships matching name patterns (SQL/PGQ)

        Args:
            caller_pattern: Pattern for caller method name (SQL LIKE syntax)
            callee_pattern: Pattern for callee method name (SQL LIKE syntax)

        Returns:
            List of matching call relationships
        """
        query = f"""
            SELECT *
            FROM GRAPH_TABLE (cpg
                MATCH (caller:method)-[e:calls]->(callee:method)
                WHERE caller.name LIKE '{caller_pattern}'
                  AND callee.name LIKE '{callee_pattern}'
                COLUMNS (
                    caller.name AS caller_name,
                    caller.filename AS caller_file,
                    callee.name AS callee_name,
                    callee.filename AS callee_file
                )
            )
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
                caller.filename,
                caller.line_number
            FROM GRAPH_TABLE (cpg
                MATCH (caller:method)-[e:calls]->(callee:method)
                WHERE callee.name LIKE '{callee_pattern}'
                COLUMNS (
                    caller.id,
                    caller.name,
                    caller.filename,
                    caller.line_number
                )
            )
        """

        return self.execute_sql_dict(query)


def main():
    """Example usage"""
    import argparse

    parser = argparse.ArgumentParser(description="Query DuckDB CPG")
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

    args = parser.parse_args()

    with DuckDBCPGClient(db_path=args.db) as client:
        if args.stats:
            stats = client.get_statistics()
            print("\nCPG Statistics:")
            print("=" * 80)
            for key, value in stats.items():
                print(f"  {key}: {value}")

        if args.method:
            results = client.find_method_by_name(args.method)
            print(f"\nMethods matching '{args.method}':")
            print("=" * 80)
            for method in results:
                print(f"  {method['name']} ({method['filename']}:{method['line_number']})")

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


if __name__ == "__main__":
    main()
