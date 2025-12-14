"""Tests for CPG export validation module."""
import pytest
from io import StringIO
from unittest.mock import MagicMock, patch


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_is_valid(self):
        """Test is_valid property when counts match."""
        from src.cpg_export.validation import ValidationResult

        result = ValidationResult(
            entity="nodes_method",
            joern_count=1000,
            duckdb_count=1000,
            is_valid=True,
            missing=0
        )
        assert result.is_valid is True
        assert result.missing == 0

    def test_validation_result_missing(self):
        """Test is_valid property when counts don't match."""
        from src.cpg_export.validation import ValidationResult

        result = ValidationResult(
            entity="nodes_method",
            joern_count=1000,
            duckdb_count=900,
            is_valid=False,
            missing=100
        )
        assert result.is_valid is False
        assert result.missing == 100

    def test_validation_result_percentage(self):
        """Test percentage property."""
        from src.cpg_export.validation import ValidationResult

        result = ValidationResult(
            entity="nodes_method",
            joern_count=1000,
            duckdb_count=750,
            is_valid=False,
            missing=250
        )
        assert result.percentage == 75.0

    def test_validation_result_percentage_zero_total(self):
        """Test percentage when joern_count is zero."""
        from src.cpg_export.validation import ValidationResult

        result = ValidationResult(
            entity="nodes_method",
            joern_count=0,
            duckdb_count=0,
            is_valid=True,
            missing=0
        )
        assert result.percentage == 100.0


class TestNodeTypeMapping:
    """Tests for NODE_TYPE_MAPPING."""

    def test_node_type_mapping_completeness(self):
        """Test that all node types are mapped."""
        from src.cpg_export.validation import NODE_TYPE_MAPPING

        # Check core mappings
        assert NODE_TYPE_MAPPING['nodes_method'] == 'method'
        assert NODE_TYPE_MAPPING['nodes_call'] == 'call'
        assert NODE_TYPE_MAPPING['nodes_identifier'] == 'identifier'
        assert NODE_TYPE_MAPPING['nodes_file'] == 'file'
        assert NODE_TYPE_MAPPING['nodes_type'] == 'typ'


class TestExportValidator:
    """Tests for ExportValidator class."""

    @pytest.fixture
    def mock_joern_client(self):
        """Create a mock JoernClient."""
        client = MagicMock()
        return client

    @pytest.fixture
    def mock_conn(self):
        """Create a mock DuckDB connection."""
        conn = MagicMock()
        return conn

    def test_validator_creation(self, mock_joern_client, mock_conn):
        """Test ExportValidator instantiation."""
        from src.cpg_export.validation import ExportValidator

        validator = ExportValidator(mock_joern_client, mock_conn)
        assert validator.joern_client is mock_joern_client
        assert validator.conn is mock_conn

    def test_validate_all_returns_dict(self, mock_joern_client, mock_conn):
        """Test that validate_all returns a dict."""
        from src.cpg_export.validation import ExportValidator

        # Mock Joern response
        mock_joern_client.execute_query.return_value = {
            'success': True,
            'result': 'val res: Int = 100'
        }

        # Mock DuckDB response
        mock_conn.execute.return_value.fetchone.return_value = (100,)

        validator = ExportValidator(mock_joern_client, mock_conn)
        results = validator.validate_all(['nodes_method'])

        assert isinstance(results, dict)
        assert 'nodes_method' in results

    def test_get_summary(self, mock_joern_client, mock_conn):
        """Test get_summary method."""
        from src.cpg_export.validation import ExportValidator, ValidationResult

        validator = ExportValidator(mock_joern_client, mock_conn)

        results = {
            'nodes_method': ValidationResult(
                entity='nodes_method',
                joern_count=1000,
                duckdb_count=1000,
                is_valid=True,
                missing=0
            ),
            'nodes_call': ValidationResult(
                entity='nodes_call',
                joern_count=500,
                duckdb_count=450,
                is_valid=False,
                missing=50
            )
        }

        summary = validator.get_summary(results)

        assert summary['total_joern'] == 1500
        assert summary['total_duckdb'] == 1450
        assert summary['total_missing'] == 50
        assert summary['all_valid'] is False
        assert summary['valid_entities'] == 1
        assert summary['total_entities'] == 2

    def test_print_report(self, mock_joern_client, mock_conn, capsys):
        """Test print_report output."""
        from src.cpg_export.validation import ExportValidator, ValidationResult

        validator = ExportValidator(mock_joern_client, mock_conn)

        results = {
            'nodes_method': ValidationResult(
                entity='nodes_method',
                joern_count=100,
                duckdb_count=100,
                is_valid=True,
                missing=0
            )
        }

        is_valid = validator.print_report(results)

        captured = capsys.readouterr()
        assert 'VALIDATION REPORT' in captured.out
        assert 'nodes_method' in captured.out
        assert is_valid is True


class TestValidateExportFunction:
    """Tests for validate_export convenience function."""

    def test_validate_export_returns_results(self):
        """Test validate_export function."""
        from src.cpg_export.validation import validate_export

        mock_joern = MagicMock()
        mock_joern.execute_query.return_value = {
            'success': True,
            'result': 'val res: Int = 10'
        }

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = (10,)

        results = validate_export(mock_joern, mock_conn, print_report=False)

        assert isinstance(results, dict)
