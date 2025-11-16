"""Export Joern CPG to DuckDB for Phase 8B

This module exports the Code Property Graph from Joern to DuckDB tables
and creates a SQL/PGQ property graph for querying.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import duckdb
import logging
from typing import List, Dict, Optional
from src.execution.joern_client import JoernClient
from src.execution.scala_parser import parse_scala_output

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JoernCPGExporter:
    """Export Joern CPG to DuckDB"""

    def __init__(self, db_path: str = "cpg.duckdb"):
        """
        Initialize exporter

        Args:
            db_path: Path to DuckDB database file (default: cpg.duckdb)
        """
        self.db_path = db_path
        self.joern = JoernClient()
        self.conn = None
        self.joern_id_map = {}  # Maps Joern IDs to sequential IDs

    def connect_joern(self) -> bool:
        """Connect to Joern server"""
        logger.info("Connecting to Joern server...")
        connected = self.joern.connect()
        if connected:
            logger.info("Connected to Joern successfully")
        else:
            logger.error("Failed to connect to Joern")
        return connected

    def setup_duckdb(self):
        """Setup DuckDB database and install duckpgq"""
        logger.info(f"Setting up DuckDB at {self.db_path}")

        self.conn = duckdb.connect(self.db_path)

        # Install and load duckpgq
        logger.info("Installing duckpgq extension...")
        self.conn.execute("INSTALL duckpgq FROM community;")
        self.conn.execute("LOAD duckpgq;")
        logger.info("DuckPGQ extension loaded")

    def create_schema(self):
        """Create DuckDB schema for CPG"""
        logger.info("Creating CPG schema in DuckDB...")

        # Drop existing tables if they exist
        self.conn.execute("DROP TABLE IF EXISTS calls;")
        self.conn.execute("DROP TABLE IF EXISTS methods;")

        # Create methods table
        self.conn.execute("""
            CREATE TABLE methods (
                id INTEGER PRIMARY KEY,
                name VARCHAR,
                filename VARCHAR,
                line_number INTEGER,
                signature VARCHAR,
                code TEXT
            );
        """)
        logger.info("Created methods table")

        # Create calls table
        self.conn.execute("""
            CREATE TABLE calls (
                caller_id INTEGER,
                callee_id INTEGER,
                call_line INTEGER
            );
        """)
        logger.info("Created calls table")

    def extract_methods(self, batch_size: int = 1000) -> List[Dict]:
        """
        Extract all methods from Joern CPG in batches

        Args:
            batch_size: Number of methods to extract per batch

        Returns:
            List of method dictionaries with id, name, filename, line, signature, code
        """
        logger.info("Extracting methods from Joern CPG...")

        # First, get total count
        count_query = "cpg.method.size"
        count_result = self.joern.execute_query(count_query)

        if not count_result or not count_result.get('success'):
            logger.error("Failed to get method count")
            return []

        # Parse count from result - look for the actual number after "= "
        count_str = count_result.get('result', '0')
        import re
        # Match pattern like "val res578: Int = 52303"
        count_match = re.search(r'=\s*(\d+)', count_str)
        total_methods = int(count_match.group(1)) if count_match else 0
        logger.info(f"Total methods in CPG: {total_methods}")

        # Extract methods in batches
        all_methods = []
        offset = 0

        while offset < total_methods:
            logger.info(f"Extracting batch {offset//batch_size + 1} (methods {offset}-{min(offset+batch_size, total_methods)})")

            # CPGQL query to get methods with their properties
            query = f"""
                cpg.method.drop({offset}).take({batch_size}).map {{ m =>
                    Map(
                        "id" -> m.id.toString,
                        "name" -> m.name,
                        "filename" -> m.filename,
                        "line" -> m.lineNumber.getOrElse(0),
                        "signature" -> m.signature
                    )
                }}.l
            """

            result = self.joern.execute_query(query)

            if not result or not result.get('success'):
                logger.warning(f"Failed to extract batch at offset {offset}: {result.get('error')}")
                break

            # Parse Scala output to Python list of dicts
            methods = parse_scala_output(result.get('result', ''))

            if not methods:
                logger.warning(f"No methods found in batch at offset {offset}")
                break

            all_methods.extend(methods)
            offset += batch_size

        logger.info(f"Extracted {len(all_methods)} methods total")
        return all_methods

    def extract_calls(self, batch_size: int = 5000) -> List[Dict]:
        """
        Extract all call edges from Joern CPG in batches

        Args:
            batch_size: Number of methods to process per batch

        Returns:
            List of call dictionaries with caller_id, callee_id, call_line
        """
        logger.info("Extracting calls from Joern CPG...")

        # Get total method count first
        count_query = "cpg.method.size"
        count_result = self.joern.execute_query(count_query)

        if not count_result or not count_result.get('success'):
            logger.error("Failed to get method count for calls extraction")
            return []

        import re
        count_str = count_result.get('result', '0')
        # Match pattern like "val res578: Int = 52303"
        count_match = re.search(r'=\s*(\d+)', count_str)
        total_methods = int(count_match.group(1)) if count_match else 0
        logger.info(f"Processing calls for {total_methods} methods...")

        # Extract call relationships in batches
        all_calls = []
        offset = 0

        while offset < total_methods:
            logger.info(f"Extracting calls batch {offset//batch_size + 1} (methods {offset}-{min(offset+batch_size, total_methods)})")

            # CPGQL query: For each method, get all its outgoing calls
            query = f"""
                cpg.method.drop({offset}).take({batch_size}).flatMap {{ m =>
                    m.callOut.map {{ callee =>
                        Map(
                            "caller_id" -> m.id.toString,
                            "callee_id" -> callee.id.toString,
                            "call_line" -> m.lineNumber.getOrElse(0)
                        )
                    }}
                }}.l
            """

            result = self.joern.execute_query(query)

            if not result or not result.get('success'):
                logger.warning(f"Failed to extract calls batch at offset {offset}: {result.get('error')}")
                break

            # Parse Scala output
            calls = parse_scala_output(result.get('result', ''))

            if calls:
                all_calls.extend(calls)
                logger.info(f"  Found {len(calls)} calls in this batch")
            else:
                logger.info(f"  No calls found in this batch")

            offset += batch_size

        logger.info(f"Extracted {len(all_calls)} total call relationships")
        return all_calls

    def load_methods(self, methods: List[Dict]):
        """Load methods into DuckDB and build ID mapping"""
        logger.info(f"Loading {len(methods)} methods into DuckDB...")

        # Build mapping from Joern ID to sequential ID
        self.joern_id_map = {}

        # Prepare data for insertion
        for idx, method in enumerate(methods):
            # Clean filename - remove triple quotes if present
            filename = method.get('filename', '')
            filename = filename.replace('"""', '').replace('""', '')

            sequential_id = idx + 1
            joern_id = method.get('id', '')

            # Store mapping
            if joern_id:
                self.joern_id_map[joern_id] = sequential_id

            self.conn.execute("""
                INSERT INTO methods (id, name, filename, line_number, signature, code)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                sequential_id,  # Use sequential ID since Joern IDs might be too large
                method.get('name', ''),
                filename,
                method.get('line', 0),
                method.get('signature', ''),
                ''  # No code for now to keep things simple
            ])

        # Verify count
        count = self.conn.execute("SELECT COUNT(*) FROM methods").fetchone()[0]
        logger.info(f"Loaded {count} methods into DuckDB")

    def load_calls(self, calls: List[Dict]):
        """Load call edges into DuckDB using ID mapping"""
        logger.info(f"Loading {len(calls)} calls into DuckDB...")

        loaded_count = 0
        skipped_count = 0

        for call in calls:
            joern_caller_id = str(call.get('caller_id', ''))
            joern_callee_id = str(call.get('callee_id', ''))

            # Map Joern IDs to sequential IDs
            caller_id = self.joern_id_map.get(joern_caller_id)
            callee_id = self.joern_id_map.get(joern_callee_id)

            # Only insert if both IDs exist in our mapping
            if caller_id and callee_id:
                self.conn.execute("""
                    INSERT INTO calls (caller_id, callee_id, call_line)
                    VALUES (?, ?, ?)
                """, [
                    caller_id,
                    callee_id,
                    call.get('call_line', 0)
                ])
                loaded_count += 1
            else:
                skipped_count += 1

        # Verify count
        count = self.conn.execute("SELECT COUNT(*) FROM calls").fetchone()[0]
        logger.info(f"Loaded {count} calls into DuckDB ({skipped_count} skipped due to missing method IDs)")

    def create_property_graph(self):
        """Create SQL/PGQ property graph"""
        logger.info("Creating SQL/PGQ property graph...")

        # Drop existing graph if exists
        self.conn.execute("DROP PROPERTY GRAPH IF EXISTS cpg;")

        # Create property graph
        self.conn.execute("""
            CREATE PROPERTY GRAPH cpg
            VERTEX TABLES (
                methods LABEL method
            )
            EDGE TABLES (
                calls
                    SOURCE KEY (caller_id) REFERENCES methods (id)
                    DESTINATION KEY (callee_id) REFERENCES methods (id)
                    LABEL calls
            );
        """)

        logger.info("Property graph 'cpg' created successfully")

    def export(self):
        """Main export workflow"""
        try:
            # Step 1: Connect to Joern
            if not self.connect_joern():
                logger.error("Cannot proceed without Joern connection")
                return False

            # Step 2: Setup DuckDB
            self.setup_duckdb()

            # Step 3: Create schema
            self.create_schema()

            # Step 4: Extract methods from Joern
            methods = self.extract_methods()
            if not methods:
                logger.error("Failed to extract methods")
                return False

            # Step 5: Load methods into DuckDB
            self.load_methods(methods)

            # Step 6: Extract calls from Joern
            calls = self.extract_calls()
            if not calls:
                logger.warning("No calls extracted, but continuing...")

            # Step 7: Load calls into DuckDB
            if calls:
                self.load_calls(calls)

            # Step 8: Create property graph
            self.create_property_graph()

            logger.info("=" * 80)
            logger.info("CPG Export Summary")
            logger.info("=" * 80)
            logger.info(f"Database: {self.db_path}")
            logger.info(f"Methods: {len(methods)}")
            logger.info(f"Calls: {len(calls)}")
            logger.info(f"Property graph: cpg")
            logger.info("=" * 80)

            return True

        except Exception as e:
            logger.error(f"Export failed: {e}", exc_info=True)
            return False

        finally:
            if self.conn:
                self.conn.close()
                logger.info("Database connection closed")

    def test_query(self):
        """Test a simple SQL/PGQ query on exported data"""
        logger.info("\nTesting SQL/PGQ query on exported data...")

        conn = duckdb.connect(self.db_path)
        conn.execute("LOAD duckpgq;")

        # Find all methods with their call counts
        result = conn.execute("""
            SELECT
                m.name,
                m.filename,
                m.line_number,
                COUNT(c.callee_id) as call_count
            FROM methods m
            LEFT JOIN calls c ON m.id = c.caller_id
            GROUP BY m.id, m.name, m.filename, m.line_number
            ORDER BY call_count DESC
            LIMIT 10
        """).fetchall()

        logger.info("Top 10 methods by call count:")
        for row in result:
            logger.info(f"  {row[0]} ({row[1]}:{row[2]}) - {row[3]} calls")

        conn.close()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Export Joern CPG to DuckDB")
    parser.add_argument('--db', type=str, default='cpg.duckdb',
                        help='Path to DuckDB database file')
    parser.add_argument('--test', action='store_true',
                        help='Run test query after export')

    args = parser.parse_args()

    exporter = JoernCPGExporter(db_path=args.db)
    success = exporter.export()

    if success and args.test:
        exporter.test_query()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
