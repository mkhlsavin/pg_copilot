"""
Unit Tests for DuckDB CPG Client

Tests the DuckDBCPGClient class with mocked database connections.
Covers connection, queries, statistics, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os


class TestDuckDBCPGClientConnection:
    """Tests for DuckDB connection management."""

    def test_connect_with_nonexistent_file(self):
        """Test that connect returns False for nonexistent database."""
        from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

        client = DuckDBCPGClient(db_path="/nonexistent/database.duckdb")
        result = client.connect()

        assert result is False
        assert client.conn is None

    def test_connect_with_valid_file(self):
        """Test successful connection to existing database."""
        with patch('src.cpg_export.duckdb_cpg_client_v2.duckdb') as mock_duckdb:
            with patch('src.cpg_export.duckdb_cpg_client_v2.Path') as mock_path:
                mock_path.return_value.exists.return_value = True
                mock_conn = MagicMock()
                mock_duckdb.connect.return_value = mock_conn

                from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

                client = DuckDBCPGClient(db_path="test.duckdb")
                result = client.connect()

                assert result is True
                assert client.conn is not None
                mock_duckdb.connect.assert_called_once_with("test.duckdb")

    def test_connect_loads_duckpgq_extension(self):
        """Test that DuckPGQ extension is loaded on connect."""
        with patch('src.cpg_export.duckdb_cpg_client_v2.duckdb') as mock_duckdb:
            with patch('src.cpg_export.duckdb_cpg_client_v2.Path') as mock_path:
                mock_path.return_value.exists.return_value = True
                mock_conn = MagicMock()
                mock_duckdb.connect.return_value = mock_conn

                from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

                client = DuckDBCPGClient(db_path="test.duckdb")
                client.connect()

                mock_conn.execute.assert_called_with("LOAD duckpgq;")

    def test_connect_handles_duckpgq_missing(self):
        """Test graceful handling when DuckPGQ extension is not available."""
        with patch('src.cpg_export.duckdb_cpg_client_v2.duckdb') as mock_duckdb:
            with patch('src.cpg_export.duckdb_cpg_client_v2.Path') as mock_path:
                mock_path.return_value.exists.return_value = True
                mock_conn = MagicMock()
                mock_conn.execute.side_effect = Exception("Extension not found")
                mock_duckdb.connect.return_value = mock_conn

                from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

                client = DuckDBCPGClient(db_path="test.duckdb")
                result = client.connect()

                # Should still succeed even if extension loading fails
                assert result is True

    def test_disconnect_closes_connection(self):
        """Test that disconnect properly closes the connection."""
        mock_conn = MagicMock()

        from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

        client = DuckDBCPGClient(db_path="test.duckdb")
        client.conn = mock_conn

        client.disconnect()

        mock_conn.close.assert_called_once()

    def test_context_manager_connect_disconnect(self):
        """Test context manager connects on enter and disconnects on exit."""
        with patch('src.cpg_export.duckdb_cpg_client_v2.duckdb') as mock_duckdb:
            with patch('src.cpg_export.duckdb_cpg_client_v2.Path') as mock_path:
                mock_path.return_value.exists.return_value = True
                mock_conn = MagicMock()
                mock_duckdb.connect.return_value = mock_conn

                from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

                with DuckDBCPGClient(db_path="test.duckdb") as client:
                    assert client.conn is not None

                mock_conn.close.assert_called_once()


class TestDuckDBCPGClientExecuteSQL:
    """Tests for SQL execution methods."""

    @pytest.fixture
    def connected_client(self):
        """Create a connected client with mock connection."""
        from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

        client = DuckDBCPGClient(db_path="test.duckdb")
        client.conn = MagicMock()
        return client

    def test_execute_sql_without_connection_raises_error(self):
        """Test that execute_sql raises error without connection."""
        from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

        client = DuckDBCPGClient(db_path="test.duckdb")

        with pytest.raises(RuntimeError, match="Not connected"):
            client.execute_sql("SELECT 1")

    def test_execute_sql_returns_results(self, connected_client):
        """Test successful SQL execution returns results."""
        connected_client.conn.execute.return_value.fetchall.return_value = [
            (1, 'method1'),
            (2, 'method2'),
        ]

        result = connected_client.execute_sql("SELECT id, name FROM nodes_method")

        assert result == [(1, 'method1'), (2, 'method2')]

    def test_execute_sql_raises_on_error(self, connected_client):
        """Test that SQL errors are propagated."""
        connected_client.conn.execute.side_effect = Exception("SQL syntax error")

        with pytest.raises(Exception, match="SQL syntax error"):
            connected_client.execute_sql("INVALID SQL")

    def test_execute_sql_dict_returns_dictionaries(self, connected_client):
        """Test execute_sql_dict returns list of dictionaries."""
        mock_relation = MagicMock()
        mock_relation.columns = ['id', 'name', 'filename']
        mock_relation.fetchall.return_value = [
            (1, 'method1', 'file1.c'),
            (2, 'method2', 'file2.c'),
        ]
        connected_client.conn.sql.return_value = mock_relation

        result = connected_client.execute_sql_dict("SELECT id, name, filename FROM nodes_method")

        assert len(result) == 2
        assert result[0] == {'id': 1, 'name': 'method1', 'filename': 'file1.c'}
        assert result[1] == {'id': 2, 'name': 'method2', 'filename': 'file2.c'}


class TestDuckDBCPGClientStatistics:
    """Tests for CPG statistics."""

    @pytest.fixture
    def client_with_stats(self):
        """Create a client with mocked statistics queries."""
        from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

        client = DuckDBCPGClient(db_path="test.duckdb")
        mock_conn = MagicMock()

        # Set up node count responses
        def execute_side_effect(query):
            mock_result = MagicMock()
            if "nodes_method" in query:
                mock_result.fetchone.return_value = (100,)
            elif "nodes_call" in query:
                mock_result.fetchone.return_value = (500,)
            elif "nodes_identifier" in query:
                mock_result.fetchone.return_value = (1000,)
            elif "edges_ast" in query:
                mock_result.fetchone.return_value = (2000,)
            elif "edges_cfg" in query:
                mock_result.fetchone.return_value = (800,)
            elif "edges_call" in query:
                mock_result.fetchone.return_value = (300,)
            else:
                mock_result.fetchone.return_value = (0,)
            return mock_result

        mock_conn.execute.side_effect = execute_side_effect
        client.conn = mock_conn
        return client

    def test_get_statistics_returns_cpg_statistics(self, client_with_stats):
        """Test that get_statistics returns CPGStatistics object."""
        from src.cpg_export.duckdb_cpg_client_v2 import CPGStatistics

        stats = client_with_stats.get_statistics()

        assert isinstance(stats, CPGStatistics)
        assert stats.method_count == 100
        assert stats.call_node_count == 500
        assert stats.identifier_count == 1000
        assert stats.ast_edge_count == 2000
        assert stats.cfg_edge_count == 800
        assert stats.call_edge_count == 300

    def test_get_statistics_handles_missing_tables(self):
        """Test that statistics handles missing tables gracefully."""
        from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

        client = DuckDBCPGClient(db_path="test.duckdb")
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("Table not found")
        client.conn = mock_conn

        stats = client.get_statistics()

        # All counts should be 0 if queries fail
        assert stats.method_count == 0
        assert stats.call_node_count == 0


class TestDuckDBCPGClientMethodQueries:
    """Tests for method-related queries."""

    @pytest.fixture
    def client(self):
        """Create a connected client with mock."""
        from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

        client = DuckDBCPGClient(db_path="test.duckdb")
        client.conn = MagicMock()
        return client

    def test_find_method_by_name_exact(self, client):
        """Test finding method by exact name."""
        mock_relation = MagicMock()
        mock_relation.columns = ['id', 'name', 'full_name', 'filename', 'line_number', 'signature', 'code']
        mock_relation.fetchall.return_value = [
            (1, 'main', 'MyClass.main:void()', 'main.c', 10, 'void main()', 'void main() {}'),
        ]
        client.conn.sql.return_value = mock_relation

        result = client.find_method_by_name('main', exact=True)

        assert len(result) == 1
        assert result[0]['name'] == 'main'
        # Verify exact match query was used
        call_args = client.conn.sql.call_args[0][0]
        assert "name = 'main'" in call_args

    def test_find_method_by_name_pattern(self, client):
        """Test finding method by name pattern."""
        mock_relation = MagicMock()
        mock_relation.columns = ['id', 'name', 'full_name', 'filename', 'line_number', 'signature', 'code']
        mock_relation.fetchall.return_value = [
            (1, 'getUser', 'UserService.getUser', 'user.c', 20, '', ''),
            (2, 'getUserById', 'UserService.getUserById', 'user.c', 30, '', ''),
        ]
        client.conn.sql.return_value = mock_relation

        result = client.find_method_by_name('User', exact=False)

        assert len(result) == 2
        # Verify LIKE pattern was used
        call_args = client.conn.sql.call_args[0][0]
        assert "LIKE '%User%'" in call_args

    def test_find_method_by_full_name(self, client):
        """Test finding method by full qualified name."""
        mock_relation = MagicMock()
        mock_relation.columns = ['id', 'name', 'full_name', 'filename', 'line_number',
                                  'signature', 'code', 'is_external', 'ast_parent_type',
                                  'ast_parent_full_name']
        mock_relation.fetchall.return_value = [
            (1, 'main', 'MyClass.main:void()', 'main.c', 10, 'void main()',
             'void main() {}', False, 'TYPE_DECL', 'MyClass'),
        ]
        client.conn.sql.return_value = mock_relation

        result = client.find_method_by_full_name('MyClass.main:void()')

        assert result is not None
        assert result['full_name'] == 'MyClass.main:void()'

    def test_find_method_by_full_name_not_found(self, client):
        """Test finding method that doesn't exist returns None."""
        mock_relation = MagicMock()
        mock_relation.columns = []
        mock_relation.fetchall.return_value = []
        client.conn.sql.return_value = mock_relation

        result = client.find_method_by_full_name('NonExistent.method')

        assert result is None

    def test_find_methods_in_file(self, client):
        """Test finding all methods in a file."""
        mock_relation = MagicMock()
        mock_relation.columns = ['id', 'name', 'full_name', 'filename', 'line_number', 'signature']
        mock_relation.fetchall.return_value = [
            (1, 'func1', 'file.func1', 'src/myfile.c', 10, ''),
            (2, 'func2', 'file.func2', 'src/myfile.c', 50, ''),
        ]
        client.conn.sql.return_value = mock_relation

        result = client.find_methods_in_file('myfile.c')

        assert len(result) == 2
        call_args = client.conn.sql.call_args[0][0]
        assert "LIKE '%myfile.c%'" in call_args


class TestDuckDBCPGClientCallGraph:
    """Tests for call graph queries."""

    @pytest.fixture
    def client(self):
        """Create a connected client with mock."""
        from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

        client = DuckDBCPGClient(db_path="test.duckdb")
        client.conn = MagicMock()
        return client

    def test_get_direct_callees(self, client):
        """Test getting methods called by a method."""
        mock_relation = MagicMock()
        mock_relation.columns = ['caller_name', 'caller_full_name', 'callee_id',
                                  'callee_name', 'callee_full_name', 'callee_filename', 'callee_line']
        mock_relation.fetchall.return_value = [
            ('main', 'MyClass.main', 2, 'helper', 'MyClass.helper', 'main.c', 20),
            ('main', 'MyClass.main', 3, 'process', 'MyClass.process', 'main.c', 30),
        ]
        client.conn.sql.return_value = mock_relation

        result = client.get_direct_callees('main')

        assert len(result) == 2
        assert result[0]['callee_name'] == 'helper'
        assert result[1]['callee_name'] == 'process'

    def test_get_direct_callers(self, client):
        """Test getting methods that call a method."""
        mock_relation = MagicMock()
        mock_relation.columns = ['caller_id', 'caller_name', 'caller_full_name',
                                  'caller_filename', 'caller_line']
        mock_relation.fetchall.return_value = [
            (1, 'main', 'MyClass.main', 'main.c', 10),
            (5, 'test', 'Test.test', 'test.c', 100),
        ]
        client.conn.sql.return_value = mock_relation

        result = client.get_direct_callers('helper')

        assert len(result) == 2
        assert result[0]['caller_name'] == 'main'
        assert result[1]['caller_name'] == 'test'

    def test_get_call_chain(self, client):
        """Test getting transitive call chain."""
        mock_relation = MagicMock()
        mock_relation.columns = ['id', 'name', 'full_name', 'filename', 'line_number', 'depth']
        mock_relation.fetchall.return_value = [
            (2, 'helper', 'MyClass.helper', 'main.c', 20, 1),
            (3, 'process', 'MyClass.process', 'main.c', 30, 1),
            (4, 'deepHelper', 'MyClass.deepHelper', 'main.c', 40, 2),
        ]
        client.conn.sql.return_value = mock_relation

        result = client.get_call_chain('main', max_depth=3)

        assert len(result) == 3
        assert result[0]['depth'] == 1
        assert result[2]['depth'] == 2

    def test_get_methods_with_most_calls(self, client):
        """Test getting methods with most outgoing calls."""
        mock_relation = MagicMock()
        mock_relation.columns = ['id', 'name', 'full_name', 'filename', 'line_number', 'call_count']
        mock_relation.fetchall.return_value = [
            (1, 'main', 'MyClass.main', 'main.c', 10, 50),
            (2, 'process', 'MyClass.process', 'main.c', 100, 30),
        ]
        client.conn.sql.return_value = mock_relation

        result = client.get_methods_with_most_calls(limit=5)

        assert len(result) == 2
        assert result[0]['call_count'] == 50

    def test_get_most_called_methods(self, client):
        """Test getting most frequently called methods."""
        mock_relation = MagicMock()
        mock_relation.columns = ['id', 'name', 'full_name', 'filename', 'line_number', 'called_count']
        mock_relation.fetchall.return_value = [
            (10, 'log', 'Logger.log', 'logger.c', 5, 100),
            (11, 'validate', 'Validator.validate', 'validator.c', 10, 75),
        ]
        client.conn.sql.return_value = mock_relation

        result = client.get_most_called_methods(limit=5)

        assert len(result) == 2
        assert result[0]['called_count'] == 100


class TestDuckDBCPGClientDataFlow:
    """Tests for data flow queries."""

    @pytest.fixture
    def client(self):
        """Create a connected client with mock."""
        from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

        client = DuckDBCPGClient(db_path="test.duckdb")
        client.conn = MagicMock()
        return client

    def test_find_data_flow_paths(self, client):
        """Test finding data flow paths for a variable."""
        mock_relation = MagicMock()
        mock_relation.columns = ['src_id', 'dst_id', 'variable', 'hops']
        mock_relation.fetchall.return_value = [
            (1, 2, 'userInput', 1),
            (2, 3, 'userInput', 2),
            (3, 4, 'userInput', 3),
        ]
        client.conn.sql.return_value = mock_relation

        result = client.find_data_flow_paths('userInput', max_hops=5)

        assert len(result) == 3
        assert all(r['variable'] == 'userInput' for r in result)

    def test_find_references_to_declaration(self, client):
        """Test finding references to a declaration."""
        mock_relation = MagicMock()
        mock_relation.columns = ['id', 'name', 'type_full_name', 'code', 'line_number']
        mock_relation.fetchall.return_value = [
            (10, 'config', 'Config', 'config.getValue()', 25),
            (11, 'config', 'Config', 'config.set()', 30),
        ]
        client.conn.sql.return_value = mock_relation

        result = client.find_references_to_declaration('config')

        assert len(result) == 2


class TestDuckDBCPGClientAST:
    """Tests for AST traversal queries."""

    @pytest.fixture
    def client(self):
        """Create a connected client with mock."""
        from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

        client = DuckDBCPGClient(db_path="test.duckdb")
        client.conn = MagicMock()
        return client

    def test_get_ast_children_single_level(self, client):
        """Test getting direct AST children."""
        mock_relation = MagicMock()
        mock_relation.columns = ['child_id']
        mock_relation.fetchall.return_value = [(2,), (3,), (4,)]
        client.conn.sql.return_value = mock_relation

        result = client.get_ast_children(1, max_depth=1)

        assert len(result) == 3

    def test_get_ast_children_multi_level(self, client):
        """Test getting AST descendants with depth."""
        mock_relation = MagicMock()
        mock_relation.columns = ['child_id', 'depth']
        mock_relation.fetchall.return_value = [
            (2, 1), (3, 1), (4, 2), (5, 2), (6, 3)
        ]
        client.conn.sql.return_value = mock_relation

        result = client.get_ast_children(1, max_depth=3)

        assert len(result) == 5


class TestDuckDBCPGClientCFG:
    """Tests for CFG traversal queries."""

    @pytest.fixture
    def client(self):
        """Create a connected client with mock."""
        from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

        client = DuckDBCPGClient(db_path="test.duckdb")
        client.conn = MagicMock()
        return client

    def test_get_cfg_successors(self, client):
        """Test getting CFG successors."""
        client.conn.execute.return_value.fetchall.return_value = [(2,), (3,)]

        result = client.get_cfg_successors(1)

        assert result == [2, 3]

    def test_get_cfg_predecessors(self, client):
        """Test getting CFG predecessors."""
        client.conn.execute.return_value.fetchall.return_value = [(5,), (6,), (7,)]

        result = client.get_cfg_predecessors(10)

        assert result == [5, 6, 7]


class TestDuckDBCPGClientPatternMatching:
    """Tests for pattern matching queries."""

    @pytest.fixture
    def client(self):
        """Create a connected client with mock."""
        from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

        client = DuckDBCPGClient(db_path="test.duckdb")
        client.conn = MagicMock()
        return client

    def test_find_call_pattern(self, client):
        """Test finding call relationships by pattern."""
        mock_relation = MagicMock()
        mock_relation.columns = ['caller_name', 'caller_full_name', 'caller_file',
                                  'callee_name', 'callee_full_name', 'callee_file']
        mock_relation.fetchall.return_value = [
            ('processUser', 'UserService.processUser', 'user.c',
             'validateUser', 'Validator.validateUser', 'validator.c'),
        ]
        client.conn.sql.return_value = mock_relation

        result = client.find_call_pattern('process%', 'validate%')

        assert len(result) == 1
        call_args = client.conn.sql.call_args[0][0]
        assert "LIKE 'process%'" in call_args
        assert "LIKE 'validate%'" in call_args

    def test_find_methods_calling_pattern(self, client):
        """Test finding methods that call matching pattern."""
        mock_relation = MagicMock()
        mock_relation.columns = ['id', 'name', 'full_name', 'filename', 'line_number']
        mock_relation.fetchall.return_value = [
            (1, 'main', 'MyClass.main', 'main.c', 10),
            (2, 'helper', 'MyClass.helper', 'main.c', 50),
        ]
        client.conn.sql.return_value = mock_relation

        result = client.find_methods_calling_pattern('log%')

        assert len(result) == 2


class TestDuckDBCPGClientOtherQueries:
    """Tests for other query methods."""

    @pytest.fixture
    def client(self):
        """Create a connected client with mock."""
        from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

        client = DuckDBCPGClient(db_path="test.duckdb")
        client.conn = MagicMock()
        return client

    def test_find_calls_by_name_exact(self, client):
        """Test finding call nodes by exact name."""
        mock_relation = MagicMock()
        mock_relation.columns = ['id', 'name', 'method_full_name', 'signature',
                                  'type_full_name', 'dispatch_type', 'code', 'line_number']
        mock_relation.fetchall.return_value = [
            (10, 'printf', 'stdio.printf', 'void printf(char*)', 'void', 'STATIC', 'printf("hello")', 5),
        ]
        client.conn.sql.return_value = mock_relation

        result = client.find_calls_by_name('printf', exact=True)

        assert len(result) == 1
        assert result[0]['name'] == 'printf'

    def test_find_identifiers_by_name(self, client):
        """Test finding identifiers by name."""
        mock_relation = MagicMock()
        mock_relation.columns = ['id', 'name', 'type_full_name', 'code', 'line_number']
        mock_relation.fetchall.return_value = [
            (100, 'counter', 'int', 'counter++', 50),
        ]
        client.conn.sql.return_value = mock_relation

        result = client.find_identifiers_by_name('counter')

        assert len(result) == 1
        assert result[0]['type_full_name'] == 'int'

    def test_find_locals_by_name(self, client):
        """Test finding local variables by name."""
        mock_relation = MagicMock()
        mock_relation.columns = ['id', 'name', 'type_full_name', 'code', 'line_number']
        mock_relation.fetchall.return_value = [
            (200, 'buffer', 'char*', 'char* buffer', 10),
        ]
        client.conn.sql.return_value = mock_relation

        result = client.find_locals_by_name('buffer')

        assert len(result) == 1

    def test_find_params_by_name(self, client):
        """Test finding parameters by name."""
        mock_relation = MagicMock()
        mock_relation.columns = ['id', 'name', 'type_full_name', 'code', 'line_number',
                                  'index', 'is_variadic', 'evaluation_strategy']
        mock_relation.fetchall.return_value = [
            (300, 'argc', 'int', 'int argc', 1, 0, False, 'BY_VALUE'),
        ]
        client.conn.sql.return_value = mock_relation

        result = client.find_params_by_name('argc')

        assert len(result) == 1

    def test_find_type_by_name(self, client):
        """Test finding type declarations by name."""
        mock_relation = MagicMock()
        mock_relation.columns = ['id', 'name', 'full_name', 'is_external', 'filename',
                                  'inherits_from_type_full_name', 'alias_type_full_name']
        mock_relation.fetchall.return_value = [
            (400, 'UserService', 'com.example.UserService', False, 'user_service.c', None, None),
        ]
        client.conn.sql.return_value = mock_relation

        result = client.find_type_by_name('UserService')

        assert len(result) == 1

    def test_find_control_structures_by_type(self, client):
        """Test finding control structures by type."""
        mock_relation = MagicMock()
        mock_relation.columns = ['id', 'control_structure_type', 'code', 'line_number']
        mock_relation.fetchall.return_value = [
            (500, 'IF', 'if (x > 0)', 10),
            (501, 'IF', 'if (y < 0)', 20),
        ]
        client.conn.sql.return_value = mock_relation

        result = client.find_control_structures_by_type('IF')

        assert len(result) == 2

    def test_get_method_by_id(self, client):
        """Test getting method by ID."""
        mock_relation = MagicMock()
        mock_relation.columns = ['id', 'name', 'full_name', 'filename', 'line_number',
                                  'signature', 'code', 'is_external', 'ast_parent_type',
                                  'ast_parent_full_name']
        mock_relation.fetchall.return_value = [
            (1, 'main', 'MyClass.main', 'main.c', 10, 'void main()', 'void main(){}',
             False, 'TYPE_DECL', 'MyClass'),
        ]
        client.conn.sql.return_value = mock_relation

        result = client.get_method_by_id(1)

        assert result is not None
        assert result['id'] == 1
        assert result['name'] == 'main'

    def test_get_method_by_id_not_found(self, client):
        """Test getting method by ID when not found."""
        mock_relation = MagicMock()
        mock_relation.columns = []
        mock_relation.fetchall.return_value = []
        client.conn.sql.return_value = mock_relation

        result = client.get_method_by_id(99999)

        assert result is None


class TestCPGStatistics:
    """Tests for CPGStatistics dataclass."""

    def test_default_values(self):
        """Test CPGStatistics default values."""
        from src.cpg_export.duckdb_cpg_client_v2 import CPGStatistics

        stats = CPGStatistics()

        assert stats.method_count == 0
        assert stats.call_node_count == 0
        assert stats.identifier_count == 0
        assert stats.ast_edge_count == 0
        assert stats.cfg_edge_count == 0

    def test_custom_values(self):
        """Test CPGStatistics with custom values."""
        from src.cpg_export.duckdb_cpg_client_v2 import CPGStatistics

        stats = CPGStatistics(
            method_count=100,
            call_node_count=500,
            ast_edge_count=2000,
        )

        assert stats.method_count == 100
        assert stats.call_node_count == 500
        assert stats.ast_edge_count == 2000
        # Unset values should still be 0
        assert stats.literal_count == 0
