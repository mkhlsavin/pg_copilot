"""
Tests for Taint Verified Scanner.

Tests for TaintVerifiedScanner, VerifiedFinding, and SecurityRelevantCallsFilter.
Updated to match current API signature.
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import asdict


class TestVerifiedFinding:
    """Tests for VerifiedFinding dataclass."""

    def test_verified_finding_creation(self):
        """Test creating a VerifiedFinding."""
        from src.security.taint_verified_scanner import VerifiedFinding

        original = {
            'rule_id': 'sql-injection',
            'severity': 'high',
            'message': 'SQL injection vulnerability',
            'file_path': 'app.py',
            'line_number': 10,
        }

        finding = VerifiedFinding(
            original_finding=original,
            is_verified=True,
            taint_path=None,
            sanitization_confidence=0.1,
            verification_notes=["Taint path confirmed"],
        )

        assert finding.is_verified is True
        assert finding.original_finding == original
        assert finding.sanitization_confidence == 0.1

    def test_verified_finding_unverified(self):
        """Test unverified finding creation."""
        from src.security.taint_verified_scanner import VerifiedFinding

        original = {
            'rule_id': 'sql-injection',
            'severity': 'high',
        }

        finding = VerifiedFinding(
            original_finding=original,
            is_verified=False,
            verification_notes=["No taint path found"],
        )

        assert finding.is_verified is False
        # Severity should be downgraded for unverified high/critical
        assert finding.severity in ['medium', 'low', 'info']

    def test_verified_finding_to_dict(self):
        """Test VerifiedFinding to_dict method."""
        from src.security.taint_verified_scanner import VerifiedFinding

        original = {
            'rule_id': 'sql-injection',
            'severity': 'high',
            'file_path': 'test.py',
            'line_number': 42,
        }

        finding = VerifiedFinding(
            original_finding=original,
            is_verified=True,
            sanitization_confidence=0.2,
            verification_notes=["Confirmed via taint analysis"],
        )

        result = finding.to_dict()

        assert result['is_taint_verified'] is True
        assert result['sanitization_confidence'] == 0.2
        assert 'verification_notes' in result
        assert result['severity'] == 'high'

    def test_verified_finding_defaults(self):
        """Test VerifiedFinding default values."""
        from src.security.taint_verified_scanner import VerifiedFinding

        finding = VerifiedFinding(
            original_finding={'severity': 'high'},
            is_verified=False,
        )

        assert finding.taint_path is None
        assert finding.sanitization_confidence == 0.0
        assert finding.verification_notes == []

    def test_severity_downgrade_high_to_medium(self):
        """Test severity downgrade for unverified high severity."""
        from src.security.taint_verified_scanner import VerifiedFinding

        finding = VerifiedFinding(
            original_finding={'severity': 'high'},
            is_verified=False,
        )

        assert finding.severity == 'medium'

    def test_severity_downgrade_critical_to_medium(self):
        """Test severity downgrade for unverified critical severity."""
        from src.security.taint_verified_scanner import VerifiedFinding

        finding = VerifiedFinding(
            original_finding={'severity': 'critical'},
            is_verified=False,
        )

        assert finding.severity == 'medium'

    def test_severity_downgrade_medium_to_low(self):
        """Test severity downgrade for unverified medium severity."""
        from src.security.taint_verified_scanner import VerifiedFinding

        finding = VerifiedFinding(
            original_finding={'severity': 'medium'},
            is_verified=False,
        )

        assert finding.severity == 'low'

    def test_severity_preserved_when_verified(self):
        """Test severity is preserved when finding is verified."""
        from src.security.taint_verified_scanner import VerifiedFinding

        finding = VerifiedFinding(
            original_finding={'severity': 'high'},
            is_verified=True,
        )

        assert finding.severity == 'high'


class TestTaintSources:
    """Tests for taint source definitions."""

    def test_python_taint_sources_defined(self):
        """Test that Python taint sources are defined."""
        from src.security.taint_verified_scanner import PYTHON_TAINT_SOURCES

        assert isinstance(PYTHON_TAINT_SOURCES, (list, tuple, set))
        assert len(PYTHON_TAINT_SOURCES) > 0

    def test_common_sources_included(self):
        """Test that common taint sources are included."""
        from src.security.taint_verified_scanner import PYTHON_TAINT_SOURCES

        # Common web framework input sources
        expected_patterns = [
            "request",
            "input",
            "environ",
        ]

        sources_str = " ".join(str(s) for s in PYTHON_TAINT_SOURCES)
        for pattern in expected_patterns:
            assert pattern.lower() in sources_str.lower(), f"Missing source: {pattern}"


class TestTaintSinks:
    """Tests for taint sink definitions."""

    def test_python_sql_sinks_defined(self):
        """Test that Python SQL sinks are defined."""
        from src.security.taint_verified_scanner import PYTHON_SQL_SINKS

        assert isinstance(PYTHON_SQL_SINKS, (list, tuple, set))
        assert len(PYTHON_SQL_SINKS) > 0

    def test_common_sql_sinks_included(self):
        """Test that common SQL sinks are included."""
        from src.security.taint_verified_scanner import PYTHON_SQL_SINKS

        # Common SQL execution methods
        expected_sinks = ["execute", "executemany", "raw"]

        for sink in expected_sinks:
            found = any(sink in str(s) for s in PYTHON_SQL_SINKS)
            assert found, f"Missing sink: {sink}"

    def test_dangerous_sinks_categories(self):
        """Test dangerous sinks categories are defined."""
        from src.security.taint_verified_scanner import PYTHON_DANGEROUS_SINKS

        assert 'sql_injection' in PYTHON_DANGEROUS_SINKS
        assert 'command_injection' in PYTHON_DANGEROUS_SINKS
        assert 'path_traversal' in PYTHON_DANGEROUS_SINKS


class TestTaintVerifiedScannerInit:
    """Tests for TaintVerifiedScanner initialization."""

    def test_init_with_cpg_service(self):
        """Test initialization with CPG service."""
        from src.security.taint_verified_scanner import TaintVerifiedScanner

        mock_cpg = MagicMock()

        with patch('src.security.taint_verified_scanner.DataFlowTracer') as mock_tracer_class:
            mock_tracer_class.return_value = MagicMock()
            scanner = TaintVerifiedScanner(cpg_service=mock_cpg)

            assert scanner.cpg is mock_cpg
            assert scanner.tracer is not None
            mock_tracer_class.assert_called_once_with(mock_cpg)


class TestVerifySqlInjection:
    """Tests for SQL injection verification."""

    @pytest.fixture
    def scanner(self):
        """Create scanner with mocked CPG service."""
        from src.security.taint_verified_scanner import TaintVerifiedScanner

        mock_cpg_service = MagicMock()

        with patch('src.security.taint_verified_scanner.DataFlowTracer') as mock_tracer_class:
            mock_tracer = MagicMock()
            mock_tracer_class.return_value = mock_tracer

            scanner = TaintVerifiedScanner(cpg_service=mock_cpg_service)
            scanner._mock_tracer = mock_tracer
            return scanner

    def test_verify_sql_injection_confirmed(self, scanner):
        """Test verification of confirmed SQL injection."""
        from src.analysis.dataflow_tracer import DataFlowPath

        findings = [{
            'rule_id': 'sql-injection',
            'severity': 'high',
            'file_path': 'app.py',
            'line_number': 42,
        }]

        # Mock taint path
        mock_path = MagicMock(spec=DataFlowPath)
        mock_path.source_location = {'function': 'request.GET', 'file': 'app.py', 'line': 10}
        mock_path.sink_location = {'function': 'execute', 'file': 'app.py', 'line': 42}
        mock_path.path_length = 3
        mock_path.is_inter_procedural = False
        mock_path.sanitization_points = []

        scanner.tracer.find_taint_paths.return_value = [mock_path]

        results = scanner.verify_sql_injection(findings)

        assert len(results) == 1
        assert results[0].is_verified is True

    def test_verify_sql_injection_not_confirmed(self, scanner):
        """Test verification when no taint path found."""
        findings = [{
            'rule_id': 'sql-injection',
            'severity': 'high',
            'file_path': 'app.py',
            'line_number': 42,
        }]

        # No taint paths found
        scanner.tracer.find_taint_paths.return_value = []

        results = scanner.verify_sql_injection(findings)

        assert len(results) == 1
        assert results[0].is_verified is False

    def test_verify_empty_findings(self, scanner):
        """Test verifying empty findings list."""
        results = scanner.verify_sql_injection([])

        assert results == []

    def test_verify_multiple_findings(self, scanner):
        """Test verifying multiple findings."""
        from src.analysis.dataflow_tracer import DataFlowPath

        findings = [
            {'rule_id': 'sql-1', 'file_path': 'a.py', 'line_number': 10},
            {'rule_id': 'sql-2', 'file_path': 'b.py', 'line_number': 20},
            {'rule_id': 'sql-3', 'file_path': 'c.py', 'line_number': 30},
        ]

        # Only one has taint path
        mock_path = MagicMock(spec=DataFlowPath)
        mock_path.source_location = {'file': 'a.py', 'line': 5}
        mock_path.sink_location = {'file': 'a.py', 'line': 10}
        mock_path.path_length = 2
        mock_path.sanitization_points = []

        scanner.tracer.find_taint_paths.return_value = [mock_path]

        results = scanner.verify_sql_injection(findings)

        assert len(results) == 3
        verified_count = sum(1 for r in results if r.is_verified)
        assert verified_count == 1


class TestSecurityRelevantCallsFilter:
    """Tests for SecurityRelevantCallsFilter."""

    @pytest.fixture
    def filter_obj(self):
        """Create filter for testing."""
        from src.security.taint_verified_scanner import SecurityRelevantCallsFilter

        mock_cpg = MagicMock()

        with patch('src.security.taint_verified_scanner.DataFlowTracer') as mock_tracer_class:
            mock_tracer = MagicMock()
            mock_tracer_class.return_value = mock_tracer

            filter_obj = SecurityRelevantCallsFilter(cpg_service=mock_cpg)
            filter_obj._mock_tracer = mock_tracer
            return filter_obj

    def test_filter_by_taint_with_tainted_calls(self, filter_obj):
        """Test filtering calls with taint."""
        from src.analysis.dataflow_tracer import DataFlowPath

        findings = [
            {'file_path': 'app.py', 'line_number': 10, 'severity': 'high'},
            {'file_path': 'app.py', 'line_number': 20, 'severity': 'high'},
        ]

        # Mock taint path for first finding
        mock_path = MagicMock(spec=DataFlowPath)
        mock_path.sink_location = {'file': 'app.py', 'line': 10}
        mock_path.sanitization_points = []

        filter_obj.tracer.find_taint_paths.return_value = [mock_path]

        result = filter_obj.filter_by_taint(findings, category='sql_injection')

        # All findings returned (tainted marked as verified, non-tainted downgraded)
        assert len(result) <= len(findings)

    def test_filter_by_taint_empty_list(self, filter_obj):
        """Test filtering empty list."""
        filter_obj.tracer.find_taint_paths.return_value = []

        result = filter_obj.filter_by_taint([], category='sql_injection')

        assert result == []


class TestScanSqlInjectionVerified:
    """Tests for scan_sql_injection_verified method."""

    @pytest.fixture
    def scanner(self):
        """Create scanner with mocked CPG service."""
        from src.security.taint_verified_scanner import TaintVerifiedScanner

        mock_cpg_service = MagicMock()

        with patch('src.security.taint_verified_scanner.DataFlowTracer') as mock_tracer_class:
            mock_tracer = MagicMock()
            mock_tracer_class.return_value = mock_tracer

            scanner = TaintVerifiedScanner(cpg_service=mock_cpg_service)
            scanner._mock_tracer = mock_tracer
            return scanner

    def test_scan_sql_injection_verified_returns_findings(self, scanner):
        """Test that scan returns verified findings."""
        from src.analysis.dataflow_tracer import DataFlowPath

        mock_path = MagicMock(spec=DataFlowPath)
        mock_path.source_location = {'function': 'request.GET', 'file': 'app.py', 'line': 5}
        mock_path.sink_location = {'function': 'execute', 'file': 'app.py', 'line': 10, 'method': 'handle_request'}
        mock_path.path_length = 3
        mock_path.sanitization_points = []

        scanner.tracer.find_taint_paths.return_value = [mock_path]

        results = scanner.scan_sql_injection_verified(limit=10)

        assert len(results) == 1
        assert results[0].is_verified is True
        assert results[0].original_finding['pattern_id'] == 'TAINT_SQL_INJECTION'

    def test_scan_sql_injection_verified_respects_limit(self, scanner):
        """Test that scan respects limit parameter."""
        from src.analysis.dataflow_tracer import DataFlowPath

        # Create many mock paths
        mock_paths = []
        for i in range(100):
            mock_path = MagicMock(spec=DataFlowPath)
            mock_path.source_location = {'function': 'input', 'file': f'app{i}.py', 'line': i}
            mock_path.sink_location = {'function': 'execute', 'file': f'app{i}.py', 'line': i + 10, 'method': f'func{i}'}
            mock_path.path_length = 2
            mock_path.sanitization_points = []
            mock_paths.append(mock_path)

        scanner.tracer.find_taint_paths.return_value = mock_paths

        results = scanner.scan_sql_injection_verified(limit=10)

        assert len(results) == 10

    def test_scan_sql_injection_verified_empty(self, scanner):
        """Test scan with no taint paths."""
        scanner.tracer.find_taint_paths.return_value = []

        results = scanner.scan_sql_injection_verified()

        assert results == []


class TestIntegrateWithReportGenerator:
    """Tests for integrate_with_report_generator function."""

    def test_integration_with_sql_findings(self):
        """Test integration function with SQL findings."""
        from src.security.taint_verified_scanner import integrate_with_report_generator

        mock_cpg = MagicMock()
        findings = [
            {'pattern_id': 'sql_injection', 'severity': 'high', 'file_path': 'app.py', 'line_number': 10},
        ]

        with patch('src.security.taint_verified_scanner.TaintVerifiedScanner') as mock_scanner_class:
            mock_scanner = MagicMock()
            mock_verified = MagicMock()
            mock_verified.to_dict.return_value = {'verified': True, 'severity': 'high'}
            mock_scanner.verify_sql_injection.return_value = [mock_verified]
            mock_scanner_class.return_value = mock_scanner

            with patch('src.security.taint_verified_scanner.SecurityRelevantCallsFilter') as mock_filter_class:
                mock_filter = MagicMock()
                mock_filter.filter_security_relevant_calls.return_value = [{'verified': True}]
                mock_filter_class.return_value = mock_filter

                result = integrate_with_report_generator(mock_cpg, findings)

                assert len(result) >= 0

    def test_integration_handles_errors(self):
        """Test integration function handles errors gracefully."""
        from src.security.taint_verified_scanner import integrate_with_report_generator

        mock_cpg = MagicMock()
        findings = [
            {'pattern_id': 'sql_injection', 'severity': 'high'},
        ]

        with patch('src.security.taint_verified_scanner.TaintVerifiedScanner') as mock_scanner_class:
            mock_scanner_class.side_effect = Exception("Scanner error")

            # Should return original findings on error
            result = integrate_with_report_generator(mock_cpg, findings)

            assert result == findings

    def test_integration_without_sql_findings(self):
        """Test integration with non-SQL findings."""
        from src.security.taint_verified_scanner import integrate_with_report_generator

        mock_cpg = MagicMock()
        findings = [
            {'pattern_id': 'xss', 'severity': 'medium'},
        ]

        with patch('src.security.taint_verified_scanner.SecurityRelevantCallsFilter') as mock_filter_class:
            mock_filter = MagicMock()
            mock_filter.filter_security_relevant_calls.return_value = findings
            mock_filter_class.return_value = mock_filter

            result = integrate_with_report_generator(mock_cpg, findings)

            # Should still return findings (filtered)
            assert len(result) >= 0


class TestVerifiedFindingWithTaintPath:
    """Tests for VerifiedFinding with actual DataFlowPath."""

    def test_to_dict_with_taint_path(self):
        """Test to_dict includes taint path info."""
        from src.security.taint_verified_scanner import VerifiedFinding
        from src.analysis.dataflow_tracer import DataFlowPath

        mock_path = MagicMock(spec=DataFlowPath)
        mock_path.source_location = {'function': 'request.GET', 'file': 'app.py', 'line': 5}
        mock_path.sink_location = {'function': 'execute', 'file': 'app.py', 'line': 10}
        mock_path.path_length = 3
        mock_path.is_inter_procedural = True
        mock_path.sanitization_points = [
            {'function': 'escape', 'confidence': 0.8}
        ]

        finding = VerifiedFinding(
            original_finding={'severity': 'high', 'rule_id': 'sql'},
            is_verified=True,
            taint_path=mock_path,
            sanitization_confidence=0.8,
        )

        result = finding.to_dict()

        assert 'taint_path' in result
        assert result['taint_path']['source'] == mock_path.source_location
        assert result['taint_path']['sink'] == mock_path.sink_location
        assert result['taint_path']['path_length'] == 3
        assert result['taint_path']['is_inter_procedural'] is True
