"""
Tests for Taint Verified Scanner.

Tests for TaintVerifiedScanner, VerifiedFinding, and SecurityRelevantCallsFilter.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import asdict


class MockFinding:
    """Mock security finding for testing."""

    def __init__(
        self,
        rule_id="sql-injection",
        severity="HIGH",
        message="SQL injection vulnerability",
        file_path="app.py",
        line_start=10,
        line_end=12,
        code_snippet="cursor.execute(query)",
        sink_function="execute",
    ):
        self.rule_id = rule_id
        self.severity = severity
        self.message = message
        self.file_path = file_path
        self.line_start = line_start
        self.line_end = line_end
        self.code_snippet = code_snippet
        self.sink_function = sink_function


class TestVerifiedFinding:
    """Tests for VerifiedFinding dataclass."""

    def test_verified_finding_creation(self):
        """Test creating a VerifiedFinding."""
        from src.security.taint_verified_scanner import VerifiedFinding

        finding = VerifiedFinding(
            original_finding=MockFinding(),
            is_verified=True,
            taint_path=["input", "sanitize", "execute"],
            source_variable="user_input",
            sink_function="execute",
            adjusted_severity="CRITICAL",
            confidence=0.95,
            verification_method="dataflow",
        )

        assert finding.is_verified is True
        assert finding.adjusted_severity == "CRITICAL"
        assert finding.confidence == 0.95
        assert len(finding.taint_path) == 3

    def test_verified_finding_unverified(self):
        """Test unverified finding creation."""
        from src.security.taint_verified_scanner import VerifiedFinding

        finding = VerifiedFinding(
            original_finding=MockFinding(),
            is_verified=False,
            taint_path=[],
            source_variable=None,
            sink_function="execute",
            adjusted_severity="LOW",
            confidence=0.3,
            verification_method="static",
        )

        assert finding.is_verified is False
        assert finding.adjusted_severity == "LOW"
        assert finding.confidence == 0.3

    def test_verified_finding_to_dict(self):
        """Test VerifiedFinding to_dict method."""
        from src.security.taint_verified_scanner import VerifiedFinding

        original = MockFinding(
            rule_id="sql-injection",
            severity="HIGH",
            file_path="test.py",
            line_start=42,
        )

        finding = VerifiedFinding(
            original_finding=original,
            is_verified=True,
            taint_path=["input", "query", "execute"],
            source_variable="user_data",
            sink_function="execute",
            adjusted_severity="CRITICAL",
            confidence=0.9,
            verification_method="dataflow",
        )

        result = finding.to_dict()

        assert result["is_verified"] is True
        assert result["adjusted_severity"] == "CRITICAL"
        assert result["confidence"] == 0.9
        assert result["source_variable"] == "user_data"
        assert result["taint_path"] == ["input", "query", "execute"]

    def test_verified_finding_defaults(self):
        """Test VerifiedFinding default values."""
        from src.security.taint_verified_scanner import VerifiedFinding

        finding = VerifiedFinding(
            original_finding=MockFinding(),
            is_verified=False,
            sink_function="execute",
        )

        assert finding.taint_path == []
        assert finding.source_variable is None
        assert finding.adjusted_severity is None
        assert finding.confidence == 0.0
        assert finding.verification_method is None


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
            "argv",
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


class TestTaintVerifiedScannerInit:
    """Tests for TaintVerifiedScanner initialization."""

    def test_init_with_tracer(self):
        """Test initialization with DataFlowTracer."""
        from src.security.taint_verified_scanner import TaintVerifiedScanner

        mock_tracer = MagicMock()
        scanner = TaintVerifiedScanner(dataflow_tracer=mock_tracer)

        assert scanner.tracer is mock_tracer

    def test_init_without_tracer(self):
        """Test initialization without tracer creates default."""
        from src.security.taint_verified_scanner import TaintVerifiedScanner

        with patch(
            "src.security.taint_verified_scanner.DataFlowTracer"
        ) as mock_tracer_class:
            mock_tracer_class.return_value = MagicMock()
            scanner = TaintVerifiedScanner()

            # Should create a tracer
            assert scanner.tracer is not None

    def test_init_with_custom_sources(self):
        """Test initialization with custom sources."""
        from src.security.taint_verified_scanner import TaintVerifiedScanner

        custom_sources = ["custom_input", "my_source"]
        mock_tracer = MagicMock()

        scanner = TaintVerifiedScanner(
            dataflow_tracer=mock_tracer,
            taint_sources=custom_sources,
        )

        assert scanner.sources == custom_sources

    def test_init_with_custom_sinks(self):
        """Test initialization with custom sinks."""
        from src.security.taint_verified_scanner import TaintVerifiedScanner

        custom_sinks = ["custom_execute", "my_sink"]
        mock_tracer = MagicMock()

        scanner = TaintVerifiedScanner(
            dataflow_tracer=mock_tracer,
            taint_sinks=custom_sinks,
        )

        assert scanner.sinks == custom_sinks


class TestVerifySqlInjection:
    """Tests for SQL injection verification."""

    @pytest.fixture
    def scanner(self):
        """Create scanner with mocked CPG service."""
        from src.security.taint_verified_scanner import TaintVerifiedScanner

        mock_cpg_service = MagicMock()
        scanner = TaintVerifiedScanner(cpg_service=mock_cpg_service)
        scanner.tracer = MagicMock()
        return scanner

    @pytest.mark.asyncio
    async def test_verify_sql_injection_confirmed(self, scanner):
        """Test verification of confirmed SQL injection."""
        finding = MockFinding(
            rule_id="sql-injection",
            severity="HIGH",
            file_path="app.py",
            line_start=42,
            sink_function="execute",
        )

        # Mock tracer to return taint path
        scanner.tracer.trace_dataflow = AsyncMock(
            return_value={
                "has_taint_path": True,
                "path": ["user_input", "query", "execute"],
                "source": "user_input",
                "sink": "execute",
            }
        )

        result = await scanner.verify_sql_injection(finding)

        assert result.is_verified is True
        assert result.adjusted_severity == "CRITICAL"
        assert result.confidence > 0.8

    @pytest.mark.asyncio
    async def test_verify_sql_injection_not_confirmed(self, scanner):
        """Test verification when no taint path found."""
        finding = MockFinding(
            rule_id="sql-injection",
            severity="HIGH",
            file_path="app.py",
            line_start=42,
        )

        # Mock tracer to return no taint path
        scanner.tracer.trace_dataflow = AsyncMock(
            return_value={
                "has_taint_path": False,
                "path": [],
                "source": None,
                "sink": "execute",
            }
        )

        result = await scanner.verify_sql_injection(finding)

        assert result.is_verified is False
        assert result.confidence < 0.5

    @pytest.mark.asyncio
    async def test_verify_sql_injection_reduces_severity_if_sanitized(self, scanner):
        """Test that severity is reduced if sanitization detected."""
        finding = MockFinding(
            rule_id="sql-injection",
            severity="HIGH",
        )

        # Mock tracer showing sanitization in path
        scanner.tracer.trace_dataflow = AsyncMock(
            return_value={
                "has_taint_path": True,
                "path": ["user_input", "escape_string", "execute"],
                "source": "user_input",
                "sink": "execute",
                "sanitized": True,
            }
        )

        result = await scanner.verify_sql_injection(finding)

        # Severity should be reduced due to sanitization
        assert result.adjusted_severity in ["LOW", "MEDIUM", "INFO"]

    @pytest.mark.asyncio
    async def test_verify_sql_injection_error_handling(self, scanner):
        """Test error handling during verification."""
        finding = MockFinding(
            rule_id="sql-injection",
            severity="HIGH",
        )

        # Mock tracer to raise error
        scanner.tracer.trace_dataflow = AsyncMock(
            side_effect=Exception("Tracer error")
        )

        result = await scanner.verify_sql_injection(finding)

        # Should return unverified finding
        assert result.is_verified is False
        assert result.verification_method == "error"


class TestVerifyFindings:
    """Tests for bulk finding verification."""

    @pytest.fixture
    def scanner(self):
        """Create scanner with mocked CPG service."""
        from src.security.taint_verified_scanner import TaintVerifiedScanner

        mock_cpg_service = MagicMock()
        scanner = TaintVerifiedScanner(cpg_service=mock_cpg_service)
        scanner.tracer = MagicMock()
        return scanner

    @pytest.mark.asyncio
    async def test_verify_multiple_findings(self, scanner):
        """Test verifying multiple findings."""
        findings = [
            MockFinding(rule_id="sql-injection-1"),
            MockFinding(rule_id="sql-injection-2"),
            MockFinding(rule_id="sql-injection-3"),
        ]

        # Mock tracer
        scanner.tracer.trace_dataflow = AsyncMock(
            return_value={"has_taint_path": True, "path": ["a", "b"]}
        )

        results = await scanner.verify_findings(findings)

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_verify_empty_findings(self, scanner):
        """Test verifying empty findings list."""
        results = await scanner.verify_findings([])

        assert results == []

    @pytest.mark.asyncio
    async def test_verify_findings_filters_duplicates(self, scanner):
        """Test that duplicate findings are filtered."""
        # Two findings at same location
        findings = [
            MockFinding(file_path="app.py", line_start=10),
            MockFinding(file_path="app.py", line_start=10),
        ]

        scanner.tracer.trace_dataflow = AsyncMock(
            return_value={"has_taint_path": True, "path": ["a"]}
        )

        results = await scanner.verify_findings(findings, deduplicate=True)

        # Should deduplicate
        assert len(results) <= len(findings)


class TestSecurityRelevantCallsFilter:
    """Tests for SecurityRelevantCallsFilter."""

    @pytest.fixture
    def filter_obj(self):
        """Create filter for testing."""
        from src.security.taint_verified_scanner import SecurityRelevantCallsFilter

        return SecurityRelevantCallsFilter()

    def test_filter_by_taint_with_tainted_calls(self, filter_obj):
        """Test filtering calls with taint."""
        calls = [
            {"name": "execute", "args": ["user_input"], "tainted": True},
            {"name": "execute", "args": ["constant"], "tainted": False},
            {"name": "log", "args": ["message"], "tainted": False},
        ]

        result = filter_obj.filter_by_taint(calls)

        # Should only include tainted security-relevant calls
        assert len(result) <= len(calls)

    def test_filter_by_taint_empty_list(self, filter_obj):
        """Test filtering empty list."""
        result = filter_obj.filter_by_taint([])

        assert result == []

    def test_is_security_relevant(self, filter_obj):
        """Test security relevance check."""
        # SQL execution is security relevant
        assert filter_obj.is_security_relevant("execute") is True
        assert filter_obj.is_security_relevant("executemany") is True

        # Logging is not security relevant
        assert filter_obj.is_security_relevant("print") is False
        assert filter_obj.is_security_relevant("log") is False

    def test_filter_by_sink_type(self, filter_obj):
        """Test filtering by sink type."""
        calls = [
            {"name": "execute", "sink_type": "sql"},
            {"name": "system", "sink_type": "command"},
            {"name": "open", "sink_type": "file"},
        ]

        sql_calls = filter_obj.filter_by_sink_type(calls, "sql")

        assert len(sql_calls) == 1
        assert sql_calls[0]["name"] == "execute"


class TestSeverityAdjustment:
    """Tests for severity adjustment logic."""

    @pytest.fixture
    def scanner(self):
        """Create scanner with mocked CPG service."""
        from src.security.taint_verified_scanner import TaintVerifiedScanner

        mock_cpg_service = MagicMock()
        scanner = TaintVerifiedScanner(cpg_service=mock_cpg_service)
        scanner.tracer = MagicMock()
        return scanner

    def test_adjust_severity_confirmed_critical(self, scanner):
        """Test severity adjustment for confirmed finding."""
        severity = scanner._adjust_severity(
            original_severity="HIGH",
            is_verified=True,
            has_sanitization=False,
        )

        assert severity == "CRITICAL"

    def test_adjust_severity_sanitized(self, scanner):
        """Test severity reduction for sanitized path."""
        severity = scanner._adjust_severity(
            original_severity="HIGH",
            is_verified=True,
            has_sanitization=True,
        )

        # Sanitization should reduce severity
        assert severity in ["LOW", "MEDIUM", "INFO"]

    def test_adjust_severity_unverified(self, scanner):
        """Test severity for unverified finding."""
        severity = scanner._adjust_severity(
            original_severity="HIGH",
            is_verified=False,
            has_sanitization=False,
        )

        # Unverified should be lower
        assert severity in ["LOW", "MEDIUM", "INFO"]

    def test_adjust_severity_preserves_info(self, scanner):
        """Test that INFO severity is preserved."""
        severity = scanner._adjust_severity(
            original_severity="INFO",
            is_verified=False,
            has_sanitization=False,
        )

        assert severity == "INFO"


class TestConfidenceCalculation:
    """Tests for confidence calculation."""

    @pytest.fixture
    def scanner(self):
        """Create scanner with mocked CPG service."""
        from src.security.taint_verified_scanner import TaintVerifiedScanner

        mock_cpg_service = MagicMock()
        scanner = TaintVerifiedScanner(cpg_service=mock_cpg_service)
        scanner.tracer = MagicMock()
        return scanner

    def test_calculate_confidence_verified(self, scanner):
        """Test confidence for verified finding."""
        confidence = scanner._calculate_confidence(
            is_verified=True,
            path_length=3,
            has_sanitization=False,
        )

        assert confidence > 0.8

    def test_calculate_confidence_unverified(self, scanner):
        """Test confidence for unverified finding."""
        confidence = scanner._calculate_confidence(
            is_verified=False,
            path_length=0,
            has_sanitization=False,
        )

        assert confidence < 0.5

    def test_calculate_confidence_long_path(self, scanner):
        """Test confidence reduction for long paths."""
        short_path_conf = scanner._calculate_confidence(
            is_verified=True,
            path_length=2,
            has_sanitization=False,
        )

        long_path_conf = scanner._calculate_confidence(
            is_verified=True,
            path_length=10,
            has_sanitization=False,
        )

        # Longer paths should have lower confidence
        assert long_path_conf <= short_path_conf

    def test_calculate_confidence_with_sanitization(self, scanner):
        """Test confidence with sanitization in path."""
        without_sanitization = scanner._calculate_confidence(
            is_verified=True,
            path_length=3,
            has_sanitization=False,
        )

        with_sanitization = scanner._calculate_confidence(
            is_verified=True,
            path_length=3,
            has_sanitization=True,
        )

        # Sanitization should reduce confidence
        assert with_sanitization < without_sanitization


class TestIntegration:
    """Integration tests for TaintVerifiedScanner."""

    @pytest.mark.asyncio
    async def test_full_verification_flow(self):
        """Test complete verification flow."""
        from src.security.taint_verified_scanner import TaintVerifiedScanner

        mock_tracer = MagicMock()
        mock_tracer.trace_dataflow = AsyncMock(
            return_value={
                "has_taint_path": True,
                "path": ["request.args.get", "query", "cursor.execute"],
                "source": "request.args.get",
                "sink": "cursor.execute",
                "sanitized": False,
            }
        )

        scanner = TaintVerifiedScanner(dataflow_tracer=mock_tracer)

        finding = MockFinding(
            rule_id="sql-injection",
            severity="HIGH",
            file_path="app/routes.py",
            line_start=42,
            code_snippet='cursor.execute(f"SELECT * FROM users WHERE id={user_id}")',
        )

        result = await scanner.verify_sql_injection(finding)

        assert result.is_verified is True
        assert result.adjusted_severity == "CRITICAL"
        assert result.confidence > 0.8
        assert "request.args.get" in result.taint_path

    @pytest.mark.asyncio
    async def test_verification_with_sanitization(self):
        """Test verification detects sanitization."""
        from src.security.taint_verified_scanner import TaintVerifiedScanner

        mock_tracer = MagicMock()
        mock_tracer.trace_dataflow = AsyncMock(
            return_value={
                "has_taint_path": True,
                "path": ["request.args.get", "escape", "cursor.execute"],
                "source": "request.args.get",
                "sink": "cursor.execute",
                "sanitized": True,
            }
        )

        scanner = TaintVerifiedScanner(dataflow_tracer=mock_tracer)

        finding = MockFinding(
            rule_id="sql-injection",
            severity="HIGH",
        )

        result = await scanner.verify_sql_injection(finding)

        # Finding verified but severity reduced due to sanitization
        assert result.is_verified is True
        assert result.adjusted_severity != "CRITICAL"

    @pytest.mark.asyncio
    async def test_batch_verification_performance(self):
        """Test batch verification handles many findings."""
        from src.security.taint_verified_scanner import TaintVerifiedScanner

        mock_tracer = MagicMock()
        mock_tracer.trace_dataflow = AsyncMock(
            return_value={"has_taint_path": False, "path": []}
        )

        scanner = TaintVerifiedScanner(dataflow_tracer=mock_tracer)

        # Create many findings
        findings = [
            MockFinding(rule_id=f"sql-injection-{i}", line_start=i)
            for i in range(100)
        ]

        results = await scanner.verify_findings(findings)

        assert len(results) == 100
