"""
Unit Tests for Security Analysis Agents

Tests the SecurityScanner, DataFlowAnalyzer, VulnerabilityReporter,
and RemediationAdvisor classes with mocked CPG queries.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestSecurityDataStructures:
    """Tests for security agent data structures."""

    def test_security_finding_creation(self):
        """Test SecurityFinding dataclass creation."""
        from src.security.security_agents import SecurityFinding

        finding = SecurityFinding(
            finding_id="SQL_001_000",
            pattern_id="SQL_001",
            pattern_name="SQL Injection",
            category="INJECTION",
            severity="CRITICAL",
            method_id=123,
            method_name="executeQuery",
            filename="db.c",
            line_number=42,
            code_snippet="query = \"SELECT * FROM users WHERE id=\" + input;",
            description="Potential SQL injection vulnerability",
            cwe_ids=["CWE-89"],
            confidence=0.85,
        )

        assert finding.finding_id == "SQL_001_000"
        assert finding.severity == "CRITICAL"
        assert finding.confidence == 0.85
        assert "CWE-89" in finding.cwe_ids

    def test_security_finding_with_metadata(self):
        """Test SecurityFinding with additional metadata."""
        from src.security.security_agents import SecurityFinding

        finding = SecurityFinding(
            finding_id="BUFF_001_000",
            pattern_id="BUFF_001",
            pattern_name="Buffer Overflow",
            category="MEMORY_SAFETY",
            severity="HIGH",
            method_id=456,
            method_name="copyBuffer",
            filename="utils.c",
            line_number=100,
            code_snippet="memcpy(dst, src, len);",
            description="Potential buffer overflow",
            cwe_ids=["CWE-120"],
            confidence=0.75,
            metadata={"call_site": True, "taint_source": "user_input"},
        )

        assert finding.metadata["call_site"] is True
        assert finding.metadata["taint_source"] == "user_input"

    def test_data_flow_path_creation(self):
        """Test DataFlowPath dataclass creation."""
        from src.security.security_agents import DataFlowPath

        path = DataFlowPath(
            path_id="flow_001",
            source_method="readInput",
            source_file="input.c",
            source_line=10,
            sink_method="executeSQL",
            sink_file="db.c",
            sink_line=50,
            path_length=3,
            intermediate_nodes=[
                {"method": "processInput", "file": "process.c", "line": 25},
            ],
            taint_type="user_input",
            sanitized=False,
        )

        assert path.path_length == 3
        assert path.sanitized is False
        assert len(path.intermediate_nodes) == 1

    def test_vulnerability_report_creation(self):
        """Test VulnerabilityReport dataclass creation."""
        from src.security.security_agents import (
            VulnerabilityReport,
            SecurityFinding,
            DataFlowPath,
        )

        findings = [
            SecurityFinding(
                finding_id="SQL_001_000",
                pattern_id="SQL_001",
                pattern_name="SQL Injection",
                category="INJECTION",
                severity="CRITICAL",
                method_id=1,
                method_name="query",
                filename="db.c",
                line_number=10,
                code_snippet="",
                description="SQL injection",
                cwe_ids=["CWE-89"],
                confidence=0.9,
            ),
        ]

        report = VulnerabilityReport(
            report_id="report_001",
            timestamp=datetime.now().isoformat(),
            total_findings=1,
            critical_count=1,
            high_count=0,
            medium_count=0,
            low_count=0,
            findings_by_category={"INJECTION": 1},
            findings=findings,
            data_flows=[],
            summary="Found 1 critical vulnerability",
            recommendations=["Review SQL query construction"],
        )

        assert report.total_findings == 1
        assert report.critical_count == 1
        assert "INJECTION" in report.findings_by_category

    def test_remediation_advice_creation(self):
        """Test RemediationAdvice dataclass creation."""
        from src.security.security_agents import RemediationAdvice

        advice = RemediationAdvice(
            finding_id="SQL_001_000",
            pattern_id="SQL_001",
            remediation_steps=[
                "Use parameterized queries",
                "Validate input data",
                "Implement input sanitization",
            ],
            code_example="query.prepare('SELECT * FROM users WHERE id = ?', [userId]);",
            references=[
                "https://owasp.org/Top10/A03_2021-Injection/",
                "CWE-89",
            ],
            estimated_effort="medium",
            priority=1,
        )

        assert len(advice.remediation_steps) == 3
        assert advice.priority == 1
        assert advice.estimated_effort == "medium"


class TestSecurityScanner:
    """Tests for SecurityScanner class."""

    @pytest.fixture
    def mock_cpg_service(self):
        """Create a mock CPG query service."""
        mock_service = MagicMock()
        return mock_service

    @pytest.fixture
    def mock_pattern(self):
        """Create a mock security pattern."""
        from src.security._base import SecurityPattern, VulnerabilitySeverity, VulnerabilityCategory

        return SecurityPattern(
            id="TEST_001",
            name="Test Pattern",
            description="A test security pattern",
            category=VulnerabilityCategory.INJECTION,
            severity=VulnerabilitySeverity.HIGH,
            cwe_ids=["CWE-89"],
            cpgql_query="cpg.method.name(\"testVuln\").l",
            remediation="Use parameterized queries",
            example_code="vulnerable(input);",
            test_cases=[],
        )

    def test_scanner_initialization(self, mock_cpg_service):
        """Test SecurityScanner initialization."""
        from src.security.security_agents import SecurityScanner

        scanner = SecurityScanner(cpg_service=mock_cpg_service)

        assert scanner.cpg is mock_cpg_service
        assert scanner._own_cpg is False

    def test_scanner_context_manager(self):
        """Test SecurityScanner as context manager."""
        with patch('src.security.security_agents.CPGQueryService') as mock_cpg_class:
            mock_cpg = MagicMock()
            mock_cpg_class.return_value = mock_cpg

            from src.security.security_agents import SecurityScanner

            scanner = SecurityScanner()  # No service provided

            with scanner:
                # Should create own CPG service
                pass

            # Should exit the CPG service context
            mock_cpg.__exit__.assert_called()

    def test_scan_pattern_returns_findings(self, mock_cpg_service, mock_pattern):
        """Test scanning a pattern returns findings."""
        # Mock query results
        mock_cpg_service.execute_query.return_value = [
            {
                'id': 1,
                'method_name': 'vulnerableMethod',
                'filename': 'vuln.c',
                'line_number': 42,
                'code': 'exec(userInput);',
            },
            {
                'id': 2,
                'method_name': 'anotherVuln',
                'filename': 'vuln.c',
                'line_number': 100,
                'code': 'eval(data);',
            },
        ]

        from src.security.security_agents import SecurityScanner

        scanner = SecurityScanner(cpg_service=mock_cpg_service)
        findings = scanner.scan_pattern(mock_pattern, limit=10)

        assert len(findings) == 2
        assert findings[0].pattern_id == "TEST_001"
        assert findings[0].method_name == "vulnerableMethod"
        assert findings[1].method_name == "anotherVuln"

    def test_scan_pattern_handles_empty_results(self, mock_cpg_service, mock_pattern):
        """Test scanning when no vulnerabilities found."""
        mock_cpg_service.execute_query.return_value = []

        from src.security.security_agents import SecurityScanner

        scanner = SecurityScanner(cpg_service=mock_cpg_service)
        findings = scanner.scan_pattern(mock_pattern)

        assert len(findings) == 0

    def test_scan_pattern_handles_errors(self, mock_cpg_service, mock_pattern):
        """Test graceful error handling during scan."""
        mock_cpg_service.execute_query.side_effect = Exception("Query failed")

        from src.security.security_agents import SecurityScanner

        scanner = SecurityScanner(cpg_service=mock_cpg_service)
        findings = scanner.scan_pattern(mock_pattern)

        assert len(findings) == 0  # Should return empty list on error

    def test_scan_pattern_respects_limit(self, mock_cpg_service, mock_pattern):
        """Test that limit parameter is respected."""
        # Return 100 results from mock
        mock_cpg_service.execute_query.return_value = [
            {'id': i, 'method_name': f'method_{i}', 'filename': 'file.c',
             'line_number': i, 'code': 'code'}
            for i in range(100)
        ]

        from src.security.security_agents import SecurityScanner

        scanner = SecurityScanner(cpg_service=mock_cpg_service)
        findings = scanner.scan_pattern(mock_pattern, limit=5)

        assert len(findings) == 5

    def test_scan_patterns_filters_by_name(self, mock_cpg_service):
        """Test scanning specific patterns by name."""
        mock_cpg_service.execute_query.return_value = [
            {'id': 1, 'method_name': 'vuln', 'filename': 'f.c', 'line_number': 1, 'code': ''}
        ]

        with patch('src.security.security_agents.SECURITY_PATTERNS') as mock_patterns:
            from src.security._base import SecurityPattern, VulnerabilitySeverity, VulnerabilityCategory

            mock_patterns.items.return_value = [
                ('SQL_INJECTION', SecurityPattern(
                    id="SQL_INJECTION",
                    name="SQL Injection",
                    description="",
                    category=VulnerabilityCategory.INJECTION,
                    severity=VulnerabilitySeverity.CRITICAL,
                    cwe_ids=[],
                    cpgql_query="",
                    remediation="",
                    example_code="",
                    test_cases=[],
                )),
                ('XSS', SecurityPattern(
                    id="XSS",
                    name="Cross-Site Scripting",
                    description="",
                    category=VulnerabilityCategory.INJECTION,
                    severity=VulnerabilitySeverity.HIGH,
                    cwe_ids=[],
                    cpgql_query="",
                    remediation="",
                    example_code="",
                    test_cases=[],
                )),
            ]

            from src.security.security_agents import SecurityScanner

            scanner = SecurityScanner(cpg_service=mock_cpg_service)
            findings = scanner.scan_patterns(['SQL_INJECTION'])

            # Should only scan SQL_INJECTION pattern
            assert mock_cpg_service.execute_query.call_count == 1

    def test_calculate_confidence_lowers_for_test_files(self, mock_cpg_service, mock_pattern):
        """Test that confidence is lowered for test files."""
        from src.security.security_agents import SecurityScanner

        scanner = SecurityScanner(cpg_service=mock_cpg_service)

        # Test file result
        test_result = {'filename': 'src/test/TestClass.java'}
        confidence = scanner._calculate_confidence(test_result, mock_pattern)

        # Production file result
        prod_result = {'filename': 'src/main/MyClass.java'}
        prod_confidence = scanner._calculate_confidence(prod_result, mock_pattern)

        # Test file should have lower confidence
        assert confidence < prod_confidence

    def test_calculate_confidence_lowers_for_validation_code(self, mock_cpg_service, mock_pattern):
        """Test that confidence is lowered when validation code is present."""
        from src.security.security_agents import SecurityScanner

        scanner = SecurityScanner(cpg_service=mock_cpg_service)

        # Code with validation
        validated_result = {'code': 'if (validate(input)) { exec(input); }', 'filename': 'f.c'}
        validated_confidence = scanner._calculate_confidence(validated_result, mock_pattern)

        # Code without validation
        raw_result = {'code': 'exec(input);', 'filename': 'f.c'}
        raw_confidence = scanner._calculate_confidence(raw_result, mock_pattern)

        # Validated code should have lower confidence
        assert validated_confidence < raw_confidence

    def test_scan_all_patterns_sorts_by_severity(self, mock_cpg_service):
        """Test that findings are sorted by severity."""
        with patch('src.security.security_agents.SECURITY_PATTERNS') as mock_patterns:
            from src.security._base import SecurityPattern, VulnerabilitySeverity, VulnerabilityCategory

            # Create patterns with different severities
            mock_patterns.items.return_value = [
                ('LOW', SecurityPattern(
                    id="LOW_001",
                    name="Low Severity",
                    description="",
                    category=VulnerabilityCategory.CONFIGURATION,
                    severity=VulnerabilitySeverity.LOW,
                    cwe_ids=[],
                    cpgql_query="",
                    remediation="",
                    example_code="",
                    test_cases=[],
                )),
                ('CRITICAL', SecurityPattern(
                    id="CRIT_001",
                    name="Critical Severity",
                    description="",
                    category=VulnerabilityCategory.INJECTION,
                    severity=VulnerabilitySeverity.CRITICAL,
                    cwe_ids=[],
                    cpgql_query="",
                    remediation="",
                    example_code="",
                    test_cases=[],
                )),
            ]

            # Both patterns return one finding
            mock_cpg_service.execute_query.return_value = [
                {'id': 1, 'method_name': 'vuln', 'filename': 'f.c', 'line_number': 1, 'code': ''}
            ]

            from src.security.security_agents import SecurityScanner

            scanner = SecurityScanner(cpg_service=mock_cpg_service)
            findings = scanner.scan_all_patterns(limit_per_pattern=1)

            # First finding should be critical (lowercase enum value)
            assert findings[0].severity == "critical"
            assert findings[1].severity == "low"


class TestSecurityScannerCategoryFiltering:
    """Tests for category-based filtering in SecurityScanner."""

    @pytest.fixture
    def mock_cpg_service(self):
        """Create a mock CPG query service."""
        mock_service = MagicMock()
        mock_service.execute_query.return_value = [
            {'id': 1, 'method_name': 'vuln', 'filename': 'f.c', 'line_number': 1, 'code': ''}
        ]
        return mock_service

    def test_scan_by_category(self, mock_cpg_service):
        """Test scanning by vulnerability category."""
        with patch('src.security.security_agents.get_patterns_by_category') as mock_get:
            from src.security._base import SecurityPattern, VulnerabilitySeverity, VulnerabilityCategory

            mock_get.return_value = [
                SecurityPattern(
                    id="INJ_001",
                    name="Injection",
                    description="",
                    category=VulnerabilityCategory.INJECTION,
                    severity=VulnerabilitySeverity.HIGH,
                    cwe_ids=[],
                    cpgql_query="",
                    remediation="",
                    example_code="",
                    test_cases=[],
                ),
            ]

            from src.security.security_agents import SecurityScanner

            scanner = SecurityScanner(cpg_service=mock_cpg_service)
            findings = scanner.scan_by_category(VulnerabilityCategory.INJECTION)

            mock_get.assert_called_once_with(VulnerabilityCategory.INJECTION)
            assert len(findings) >= 0  # At least tried to scan

    def test_scan_critical_only(self, mock_cpg_service):
        """Test scanning for critical vulnerabilities only."""
        with patch('src.security.security_agents.get_critical_patterns') as mock_get:
            from src.security._base import SecurityPattern, VulnerabilitySeverity, VulnerabilityCategory

            mock_get.return_value = [
                SecurityPattern(
                    id="CRIT_001",
                    name="Critical",
                    description="",
                    category=VulnerabilityCategory.INJECTION,
                    severity=VulnerabilitySeverity.CRITICAL,
                    cwe_ids=[],
                    cpgql_query="",
                    remediation="",
                    example_code="",
                    test_cases=[],
                ),
            ]

            from src.security.security_agents import SecurityScanner

            scanner = SecurityScanner(cpg_service=mock_cpg_service)
            findings = scanner.scan_critical_only()

            mock_get.assert_called_once()


class TestFindingConfidenceCalculation:
    """Tests for confidence score calculation."""

    @pytest.fixture
    def scanner(self):
        """Create a scanner with mock service."""
        mock_service = MagicMock()
        from src.security.security_agents import SecurityScanner
        return SecurityScanner(cpg_service=mock_service)

    @pytest.fixture
    def base_pattern(self):
        """Create a base test pattern."""
        from src.security._base import SecurityPattern, VulnerabilitySeverity, VulnerabilityCategory

        return SecurityPattern(
            id="TEST",
            name="Test",
            description="",
            category=VulnerabilityCategory.INJECTION,
            severity=VulnerabilitySeverity.HIGH,
            cwe_ids=[],
            cpgql_query="",
            remediation="",
            example_code="",
            test_cases=[],
        )

    def test_base_confidence_is_reasonable(self, scanner, base_pattern):
        """Test that base confidence is within expected range."""
        result = {'filename': 'main.c', 'code': 'exec(x);'}
        confidence = scanner._calculate_confidence(result, base_pattern)

        assert 0.0 <= confidence <= 1.0
        assert confidence >= 0.5  # Should be reasonably confident

    def test_test_file_penalty(self, scanner, base_pattern):
        """Test confidence penalty for test files."""
        test_result = {'filename': 'test_main.c', 'code': 'exec(x);'}
        prod_result = {'filename': 'main.c', 'code': 'exec(x);'}

        test_conf = scanner._calculate_confidence(test_result, base_pattern)
        prod_conf = scanner._calculate_confidence(prod_result, base_pattern)

        assert test_conf < prod_conf

    def test_sanitization_keywords_reduce_confidence(self, scanner, base_pattern):
        """Test that sanitization keywords reduce confidence."""
        sanitized = {'filename': 'f.c', 'code': 'if (sanitize(input)) { exec(input); }'}
        unsanitized = {'filename': 'f.c', 'code': 'exec(input);'}

        san_conf = scanner._calculate_confidence(sanitized, base_pattern)
        unsan_conf = scanner._calculate_confidence(unsanitized, base_pattern)

        assert san_conf < unsan_conf

    def test_handles_none_values(self, scanner, base_pattern):
        """Test graceful handling of None values in results."""
        result = {'filename': None, 'code': None}

        # Should not raise exception
        confidence = scanner._calculate_confidence(result, base_pattern)

        assert 0.0 <= confidence <= 1.0


class TestSecurityFindingGeneration:
    """Tests for proper SecurityFinding generation from query results."""

    @pytest.fixture
    def mock_cpg_service(self):
        """Create a mock CPG query service."""
        mock_service = MagicMock()
        return mock_service

    def test_finding_fields_populated_from_result(self, mock_cpg_service):
        """Test that finding fields are populated from query result."""
        from src.security._base import SecurityPattern, VulnerabilitySeverity, VulnerabilityCategory
        from src.security.security_agents import SecurityScanner

        pattern = SecurityPattern(
            id="SQL_001",
            name="SQL Injection",
            description="Detects SQL injection vulnerabilities",
            category=VulnerabilityCategory.INJECTION,
            severity=VulnerabilitySeverity.CRITICAL,
            cwe_ids=["CWE-89"],
            cpgql_query="",
            remediation="Use parameterized queries",
            example_code="stmt.execute(query);",
            test_cases=[],
        )

        mock_cpg_service.execute_query.return_value = [{
            'id': 42,
            'method_name': 'executeQuery',
            'filename': '/src/db/Database.java',
            'line_number': 156,
            'code': 'stmt.execute("SELECT * FROM users WHERE id=" + userId);',
        }]

        scanner = SecurityScanner(cpg_service=mock_cpg_service)
        findings = scanner.scan_pattern(pattern, limit=1)

        assert len(findings) == 1
        finding = findings[0]

        assert finding.pattern_id == "SQL_001"
        assert finding.pattern_name == "SQL Injection"
        assert finding.category == "injection"  # lowercase enum value
        assert finding.severity == "critical"  # lowercase enum value
        assert finding.method_id == 42
        assert finding.method_name == "executeQuery"
        assert finding.filename == "/src/db/Database.java"
        assert finding.line_number == 156
        assert "CWE-89" in finding.cwe_ids
        assert finding.description == "Detects SQL injection vulnerabilities"

    def test_finding_truncates_long_code(self, mock_cpg_service):
        """Test that code snippet is truncated for long code."""
        from src.security._base import SecurityPattern, VulnerabilitySeverity, VulnerabilityCategory
        from src.security.security_agents import SecurityScanner

        pattern = SecurityPattern(
            id="TEST",
            name="Test",
            description="",
            category=VulnerabilityCategory.CONFIGURATION,
            severity=VulnerabilitySeverity.INFO,
            cwe_ids=[],
            cpgql_query="",
            remediation="",
            example_code="",
            test_cases=[],
        )

        # Very long code string
        long_code = "x" * 1000

        mock_cpg_service.execute_query.return_value = [{
            'id': 1,
            'method_name': 'method',
            'filename': 'f.c',
            'line_number': 1,
            'code': long_code,
        }]

        scanner = SecurityScanner(cpg_service=mock_cpg_service)
        findings = scanner.scan_pattern(pattern, limit=1)

        # Code should be truncated to 200 chars
        assert len(findings[0].code_snippet) <= 200

    def test_finding_handles_missing_fields(self, mock_cpg_service):
        """Test graceful handling when result fields are missing."""
        from src.security._base import SecurityPattern, VulnerabilitySeverity, VulnerabilityCategory
        from src.security.security_agents import SecurityScanner

        pattern = SecurityPattern(
            id="TEST",
            name="Test",
            description="",
            category=VulnerabilityCategory.CONFIGURATION,
            severity=VulnerabilitySeverity.INFO,
            cwe_ids=[],
            cpgql_query="",
            remediation="",
            example_code="",
            test_cases=[],
        )

        # Result missing many fields
        mock_cpg_service.execute_query.return_value = [{'extra': 'field'}]

        scanner = SecurityScanner(cpg_service=mock_cpg_service)
        findings = scanner.scan_pattern(pattern, limit=1)

        assert len(findings) == 1
        finding = findings[0]

        # Should use defaults for missing fields
        assert finding.method_id == 0
        assert finding.method_name == "unknown"
        assert finding.filename == "unknown"
        assert finding.line_number == 0
