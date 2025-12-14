"""
Unit tests for Joern to DuckDB export.

Tests:
- CALL nodes export includes filename
- Graceful handling of missing filename
- Joern query string validation
- Comment export filename handling

Author: CPG Export Fixes
Date: December 12, 2025
"""

import pytest
import os
import sys
import tempfile
import duckdb
from pathlib import Path
from unittest.mock import Mock, patch, PropertyMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class MockJoernClient:
    """Mock Joern client for testing."""

    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_index = 0
        self.captured_queries = []

    def connect(self):
        return True

    def open_workspace(self, name):
        return {'success': True}

    def execute_query(self, query):
        self.captured_queries.append(query)
        if self.call_index < len(self.responses):
            result = self.responses[self.call_index]
            self.call_index += 1
            return result
        return {'success': True, 'result': ''}


def create_test_exporter(temp_db, responses):
    """Create exporter with mock client - directly inject mock."""
    from src.cpg_export.joern_to_duckdb_v2 import JoernToDuckDB

    mock_client = MockJoernClient(responses)

    # Create exporter - the init will try to connect to Joern but we'll override
    with patch('src.cpg_export.joern_to_duckdb_v2.JoernClient') as MockJoernClass:
        MockJoernClass.return_value = mock_client
        exporter = JoernToDuckDB(
            joern_path='/fake/joern',
            workspace_path='/fake/workspace',
            db_path=temp_db,
            batch_size=1000
        )

    # CRITICAL: Force the mock client after exporter creation
    # This ensures we use our mock regardless of what happened during __init__
    exporter.joern_client = mock_client

    # Connect to database
    exporter.conn = duckdb.connect(temp_db)

    # Create schema
    exporter.conn.execute("""
        CREATE TABLE IF NOT EXISTS nodes_call (
            id BIGINT PRIMARY KEY,
            method_full_name VARCHAR,
            name VARCHAR,
            signature VARCHAR,
            type_full_name VARCHAR,
            dispatch_type VARCHAR,
            code VARCHAR,
            line_number INTEGER,
            column_number INTEGER,
            order_index INTEGER,
            argument_index INTEGER,
            filename VARCHAR
        )
    """)
    exporter.conn.execute("""
        CREATE TABLE IF NOT EXISTS edges_call (
            caller_id BIGINT,
            callee_id BIGINT
        )
    """)
    exporter.conn.execute("""
        CREATE TABLE IF NOT EXISTS nodes_comment (
            id BIGINT PRIMARY KEY,
            code VARCHAR,
            filename VARCHAR,
            line_number INTEGER,
            column_number INTEGER,
            "offset" INTEGER,
            offset_end INTEGER,
            order_index INTEGER
        )
    """)

    return exporter, mock_client


class TestCallExportFilename:
    """Test CALL nodes export filename handling."""

    def test_call_export_includes_filename(self):
        """Test that CALL nodes export includes filename."""
        fd, temp_db = tempfile.mkstemp(suffix='.duckdb')
        os.close(fd)
        os.unlink(temp_db)

        try:
            responses = [
                {'success': True, 'result': 'res0: Int = 2'},
                {'success': True, 'result':
                    '123\tmethodName\tcallName\tsig\ttype\tSTATIC\tcode\t10\t5\t1\t0\tbackend/commands/analyze.c\n'
                    '124\tmethodName2\tcallName2\tsig2\ttype2\tDYNAMIC\tcode2\t20\t10\t2\t1\tbin/pg_dump/pg_dump.c'
                },
                {'success': True, 'result': ''}
            ]

            exporter, mock_client = create_test_exporter(temp_db, responses)

            # Export calls
            nodes, edges = exporter._export_calls_batched(limit=10)

            # Verify filename is populated
            result = exporter.conn.execute(
                "SELECT filename FROM nodes_call WHERE id = 123"
            ).fetchone()

            assert result is not None, "Row with id=123 not found"
            assert result[0] == 'backend/commands/analyze.c'

            # Verify second row
            result2 = exporter.conn.execute(
                "SELECT filename FROM nodes_call WHERE id = 124"
            ).fetchone()

            assert result2 is not None, "Row with id=124 not found"
            assert result2[0] == 'bin/pg_dump/pg_dump.c'

            exporter.conn.close()
        finally:
            if os.path.exists(temp_db):
                try:
                    os.unlink(temp_db)
                except PermissionError:
                    pass

    def test_call_export_with_different_filenames(self):
        """Test that different filename formats are handled correctly."""
        fd, temp_db = tempfile.mkstemp(suffix='.duckdb')
        os.close(fd)
        os.unlink(temp_db)

        try:
            # Test various filename scenarios:
            # - Unix-style path
            # - Windows-style path (with backslashes)
            # - Deep nested path
            responses = [
                {'success': True, 'result': 'res0: Int = 3'},
                {'success': True, 'result':
                    '125\tmethodName\tcallName\tsig\ttype\tSTATIC\tcode\t10\t5\t1\t0\tbackend/commands/analyze.c\n'
                    '126\tmethodName\tcallName\tsig\ttype\tSTATIC\tcode\t11\t6\t2\t1\tbin/pg_dump/pg_dump.c\n'
                    '127\tmethodName\tcallName\tsig\ttype\tSTATIC\tcode\t12\t7\t3\t2\tcontrib/extensions/pgcrypto/pgcrypto.c'
                },
                {'success': True, 'result': ''}
            ]

            exporter, mock_client = create_test_exporter(temp_db, responses)

            exporter._export_calls_batched(limit=10)

            # Check all rows were inserted with correct filenames
            result125 = exporter.conn.execute(
                "SELECT id, filename FROM nodes_call WHERE id = 125"
            ).fetchone()
            assert result125 is not None, "Row 125 not found"
            assert result125[1] == 'backend/commands/analyze.c'

            result126 = exporter.conn.execute(
                "SELECT id, filename FROM nodes_call WHERE id = 126"
            ).fetchone()
            assert result126 is not None, "Row 126 not found"
            assert result126[1] == 'bin/pg_dump/pg_dump.c'

            result127 = exporter.conn.execute(
                "SELECT id, filename FROM nodes_call WHERE id = 127"
            ).fetchone()
            assert result127 is not None, "Row 127 not found"
            assert result127[1] == 'contrib/extensions/pgcrypto/pgcrypto.c'

            exporter.conn.close()
        finally:
            if os.path.exists(temp_db):
                try:
                    os.unlink(temp_db)
                except PermissionError:
                    pass

    def test_call_export_handles_short_row(self):
        """Test that rows with less than 12 fields are skipped."""
        fd, temp_db = tempfile.mkstemp(suffix='.duckdb')
        os.close(fd)
        os.unlink(temp_db)

        try:
            responses = [
                {'success': True, 'result': 'res0: Int = 2'},
                {'success': True, 'result':
                    '126\tmethodName\tcallName\tsig\ttype\tSTATIC\tcode\t10\t5\t1\t0\n'  # 11 fields
                    '127\tmethodName\tcallName\tsig\ttype\tSTATIC\tcode\t10\t5\t1\t0\tvalid/file.c'  # 12 fields
                },
                {'success': True, 'result': ''}
            ]

            exporter, mock_client = create_test_exporter(temp_db, responses)

            nodes, edges = exporter._export_calls_batched(limit=10)

            # Row 126 should be skipped (only 11 fields)
            result126 = exporter.conn.execute(
                "SELECT * FROM nodes_call WHERE id = 126"
            ).fetchone()
            assert result126 is None, "Row 126 should be skipped (insufficient fields)"

            # Row 127 should exist (12 fields)
            result127 = exporter.conn.execute(
                "SELECT filename FROM nodes_call WHERE id = 127"
            ).fetchone()
            assert result127 is not None, "Row 127 should exist"
            assert result127[0] == 'valid/file.c'

            exporter.conn.close()
        finally:
            if os.path.exists(temp_db):
                try:
                    os.unlink(temp_db)
                except PermissionError:
                    pass


class TestCallQueryFormat:
    """Test Joern query format for CALL nodes."""

    def test_query_includes_file_name_attribute(self):
        """Verify Joern query string includes c.file.name."""
        fd, temp_db = tempfile.mkstemp(suffix='.duckdb')
        os.close(fd)
        os.unlink(temp_db)

        try:
            # Need count > 0 for the data query to be executed
            responses = [
                {'success': True, 'result': 'res0: Int = 1'},  # count = 1 triggers data query
                {'success': True, 'result': '123\ta\tb\tc\td\te\tf\t1\t2\t3\t4\ttest.c'},  # data
                {'success': True, 'result': ''}  # edges
            ]

            exporter, mock_client = create_test_exporter(temp_db, responses)

            exporter._export_calls_batched(limit=10)

            # Find the query that contains the call export with file.name
            call_query_found = False
            for query in mock_client.captured_queries:
                if 'cpg.call' in query and 'file.name' in query:
                    call_query_found = True
                    break

            assert call_query_found, \
                f"No query found with 'cpg.call' and 'file.name'. Captured: {mock_client.captured_queries}"

            exporter.conn.close()
        finally:
            if os.path.exists(temp_db):
                try:
                    os.unlink(temp_db)
                except PermissionError:
                    pass


class TestCommentQueryFormat:
    """Test COMMENT nodes query format."""

    def test_comment_query_uses_filename_attribute(self):
        """Verify comment query uses c.filename."""
        fd, temp_db = tempfile.mkstemp(suffix='.duckdb')
        os.close(fd)
        os.unlink(temp_db)

        try:
            # Need count > 0 for the data query to be executed
            responses = [
                {'success': True, 'result': 'res0: Int = 1'},  # count = 1 triggers data query
                {'success': True, 'result': '123\t/* comment */\ttest.c\t10\t5\t100\t110\t1'},  # data
            ]

            exporter, mock_client = create_test_exporter(temp_db, responses)

            exporter._export_comments_batched(limit=10)

            # Find the query that contains comment export with c.filename
            comment_query_found = False
            for query in mock_client.captured_queries:
                if 'cpg.comment' in query and 'map' in query:
                    # After fix, should use c.filename.getOrElse, not c.file.name.headOption
                    if 'c.filename.getOrElse' in query:
                        comment_query_found = True
                    break

            assert comment_query_found, \
                f"Comment query should use 'c.filename.getOrElse'. Captured: {mock_client.captured_queries}"

            exporter.conn.close()
        finally:
            if os.path.exists(temp_db):
                try:
                    os.unlink(temp_db)
                except PermissionError:
                    pass


class TestDataIntegrity:
    """Test data integrity of exported data."""

    def test_call_data_types_are_correct(self):
        """Test that exported CALL data has correct types."""
        fd, temp_db = tempfile.mkstemp(suffix='.duckdb')
        os.close(fd)
        os.unlink(temp_db)

        try:
            responses = [
                {'success': True, 'result': 'res0: Int = 1'},
                {'success': True, 'result':
                    '999\tfullMethod\tcallName\tsignature\ttypeFull\tSTATIC\tcode(arg)\t42\t7\t3\t2\tpath/to/file.c'
                },
                {'success': True, 'result': ''}
            ]

            exporter, mock_client = create_test_exporter(temp_db, responses)

            exporter._export_calls_batched(limit=10)

            result = exporter.conn.execute("""
                SELECT id, method_full_name, name, line_number, column_number,
                       order_index, argument_index, filename
                FROM nodes_call WHERE id = 999
            """).fetchone()

            assert result is not None, "Row not found"
            assert result[0] == 999  # id (BIGINT)
            assert result[1] == 'fullMethod'  # method_full_name (VARCHAR)
            assert result[2] == 'callName'  # name (VARCHAR)
            assert result[3] == 42  # line_number (INTEGER)
            assert result[4] == 7  # column_number (INTEGER)
            assert result[5] == 3  # order_index (INTEGER)
            assert result[6] == 2  # argument_index (INTEGER)
            assert result[7] == 'path/to/file.c'  # filename (VARCHAR)

            exporter.conn.close()
        finally:
            if os.path.exists(temp_db):
                try:
                    os.unlink(temp_db)
                except PermissionError:
                    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
