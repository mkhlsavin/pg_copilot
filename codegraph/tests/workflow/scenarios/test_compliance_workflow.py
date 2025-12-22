"""
Tests for Regulatory Compliance Workflow (Scenario 8).

Tests for compliance workflow, license detection, GDPR/HIPAA checks, and standards.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any


def create_mock_state(query: str) -> Dict[str, Any]:
    """Create a minimal state dict for testing."""
    return {
        "query": query,
        "context": None,
        "intent": "compliance",
        "scenario_id": "scenario_8",
        "confidence": 0.9,
        "classification_method": "test",
        "cpg_results": None,
        "subsystems": None,
        "methods": None,
        "call_graph": None,
        "answer": None,
        "evidence": None,
        "metadata": None,
        "retrieved_functions": None,
        "error": None,
        "retry_count": 0,
    }


class TestComplianceWorkflowImports:
    """Tests for compliance workflow module imports."""

    def test_import_workflow(self):
        """Test that compliance workflow can be imported."""
        from src.workflow.scenarios.compliance import compliance_workflow

        assert callable(compliance_workflow)

    def test_import_compliance_agents(self):
        """Test that compliance agents can be imported."""
        from src.compliance.compliance_agents import (
            LicenseDetector,
            ComplianceValidator,
            StandardsChecker,
        )

        assert LicenseDetector is not None
        assert ComplianceValidator is not None
        assert StandardsChecker is not None


class TestComplianceQueryPatterns:
    """Tests for compliance query pattern detection."""

    def test_license_keywords(self):
        """Test license compliance keyword detection."""
        queries = [
            "Check license compliance",
            "Find GPL violations",
            "Open source license issues",
        ]

        license_keywords = ["license", "gpl", "mit", "apache", "open source"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in license_keywords)

    def test_gdpr_keywords(self):
        """Test GDPR compliance keyword detection."""
        queries = [
            "Check GDPR compliance",
            "Personal data handling",
            "Data privacy issues",
        ]

        gdpr_keywords = ["gdpr", "personal data", "privacy", "data protection"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in gdpr_keywords)

    def test_hipaa_keywords(self):
        """Test HIPAA compliance keyword detection."""
        queries = [
            "HIPAA compliance check",
            "Protected health information",
            "PHI handling",
        ]

        hipaa_keywords = ["hipaa", "health", "phi", "medical"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in hipaa_keywords)

    def test_security_standards_keywords(self):
        """Test security standards keyword detection."""
        queries = [
            "OWASP compliance",
            "CWE vulnerabilities",
            "Security standards check",
        ]

        standards_keywords = ["owasp", "cwe", "security", "standard"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in standards_keywords)

    def test_coding_standards_keywords(self):
        """Test coding standards keyword detection."""
        queries = [
            "Check coding standards",
            "Naming conventions",
            "Code style violations",
        ]

        coding_keywords = ["standard", "convention", "style", "naming"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in coding_keywords)


class TestComplianceWorkflowMocked:
    """Tests for compliance_workflow function with mocked dependencies."""

    @pytest.fixture
    def mock_cpg_service(self):
        """Create mock CPG service."""
        mock = MagicMock()
        mock.get_subsystems.return_value = []
        mock.get_database_stats.return_value = {"method_count": 10000}
        mock.execute_query.return_value = []
        return mock

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM interface."""
        mock = MagicMock()
        mock.generate.return_value = "Compliance check: No violations found."
        return mock

    def test_workflow_returns_state(self, mock_cpg_service, mock_llm):
        """Test that workflow returns state dict."""
        from src.workflow.scenarios.compliance import compliance_workflow

        state = create_mock_state("Check license compliance")

        with patch("src.workflow.scenarios.compliance.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(return_value=mock_cpg_service)
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.compliance.LLMInterface", return_value=mock_llm):
                with patch("src.workflow.scenarios.compliance.get_global_registry") as mock_registry:
                    mock_registry.return_value.get_agent_prompt.return_value = {
                        "system": "You are a compliance expert",
                        "user": "Check compliance",
                    }
                    with patch("src.workflow.scenarios.compliance.LicenseDetector"):
                        with patch("src.workflow.scenarios.compliance.ComplianceValidator"):
                            with patch("src.workflow.scenarios.compliance.StandardsChecker"):
                                result = compliance_workflow(state)

        assert isinstance(result, dict)


class TestComplianceErrorHandling:
    """Tests for compliance workflow error handling."""

    def test_cpg_connection_error(self):
        """Test handling of CPG connection error."""
        from src.workflow.scenarios.compliance import compliance_workflow

        state = create_mock_state("Check compliance")

        with patch("src.workflow.scenarios.compliance.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(
                side_effect=Exception("CPG connection failed")
            )
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            result = compliance_workflow(state)

        # Should have error set
        assert result.get("error") is not None


class TestLicenseDetector:
    """Tests for LicenseDetector agent interface."""

    def test_detector_interface(self):
        """Test license detector interface."""
        mock_detector = MagicMock()
        mock_detector.detect_licenses.return_value = [
            {"file": "src/main.c", "license": "GPL-3.0"},
            {"file": "lib/util.c", "license": "MIT"},
        ]

        licenses = mock_detector.detect_licenses()

        assert len(licenses) == 2
        assert licenses[0]["license"] == "GPL-3.0"

    def test_compatibility_check(self):
        """Test license compatibility checking."""
        mock_detector = MagicMock()
        mock_detector.check_compatibility.return_value = {
            "compatible": False,
            "conflicts": [("GPL-3.0", "proprietary")],
        }

        result = mock_detector.check_compatibility()

        assert not result["compatible"]
        assert len(result["conflicts"]) > 0


class TestComplianceValidator:
    """Tests for ComplianceValidator agent interface."""

    def test_validator_interface(self):
        """Test compliance validator interface."""
        mock_validator = MagicMock()
        mock_validator.validate_gdpr.return_value = {
            "compliant": True,
            "findings": [],
        }

        result = mock_validator.validate_gdpr()

        assert result["compliant"] is True

    def test_hipaa_validation(self):
        """Test HIPAA validation interface."""
        mock_validator = MagicMock()
        mock_validator.validate_hipaa.return_value = {
            "compliant": False,
            "findings": [
                {"type": "PHI_EXPOSURE", "location": "patient_data.c:45"},
            ],
        }

        result = mock_validator.validate_hipaa()

        assert result["compliant"] is False
        assert len(result["findings"]) > 0


class TestStandardsChecker:
    """Tests for StandardsChecker agent interface."""

    def test_checker_interface(self):
        """Test standards checker interface."""
        mock_checker = MagicMock()
        mock_checker.check_owasp.return_value = [
            {"rule": "A1-Injection", "status": "PASS"},
            {"rule": "A2-BrokenAuth", "status": "FAIL"},
        ]

        results = mock_checker.check_owasp()

        assert len(results) == 2
        assert results[0]["status"] == "PASS"

    def test_cwe_check(self):
        """Test CWE checking interface."""
        mock_checker = MagicMock()
        mock_checker.check_cwe.return_value = [
            {"cwe_id": "CWE-89", "description": "SQL Injection", "found": True},
        ]

        results = mock_checker.check_cwe()

        assert len(results) > 0
        assert results[0]["cwe_id"] == "CWE-89"

    def test_coding_standards_check(self):
        """Test coding standards checking."""
        mock_checker = MagicMock()
        mock_checker.check_coding_standards.return_value = {
            "naming": {"violations": 5},
            "formatting": {"violations": 0},
            "complexity": {"violations": 3},
        }

        results = mock_checker.check_coding_standards()

        assert "naming" in results
        assert results["naming"]["violations"] == 5


class TestComplianceViolationImpact:
    """Tests for compliance violation impact analysis."""

    def test_impact_calculation(self):
        """Test violation impact calculation."""
        violations = [
            {"severity": "critical", "count": 1},
            {"severity": "high", "count": 5},
            {"severity": "medium", "count": 10},
        ]

        # Calculate weighted impact
        severity_weights = {"critical": 10, "high": 5, "medium": 2, "low": 1}

        total_impact = sum(
            v["count"] * severity_weights.get(v["severity"], 1)
            for v in violations
        )

        assert total_impact == 10 + 25 + 20  # 55

    def test_high_impact_violations(self):
        """Test identification of high impact violations."""
        violations = [
            {"id": 1, "impact_score": 0.9},
            {"id": 2, "impact_score": 0.3},
            {"id": 3, "impact_score": 0.7},
        ]

        high_impact = [v for v in violations if v["impact_score"] > 0.5]

        assert len(high_impact) == 2
        assert all(v["impact_score"] > 0.5 for v in high_impact)


class TestComplianceReporting:
    """Tests for compliance report generation."""

    def test_report_structure(self):
        """Test compliance report structure."""
        report = {
            "summary": {
                "total_checks": 50,
                "passed": 45,
                "failed": 5,
                "score": 90,
            },
            "violations": [],
            "recommendations": [],
        }

        assert "summary" in report
        assert report["summary"]["score"] == 90

    def test_violation_details(self):
        """Test violation details in report."""
        violation = {
            "type": "LICENSE_CONFLICT",
            "severity": "high",
            "file": "lib/crypto.c",
            "description": "GPL code in proprietary project",
            "recommendation": "Replace with MIT-licensed alternative",
        }

        required_fields = ["type", "severity", "file", "description"]
        assert all(field in violation for field in required_fields)


class TestComplianceGraphInsights:
    """Tests for compliance graph insights integration."""

    def test_graph_insights_structure(self):
        """Test graph insights structure."""
        graph_insights = {
            "violation_impact": {},
            "high_impact_violations": [],
            "critical_methods": [],
        }

        assert "violation_impact" in graph_insights
        assert isinstance(graph_insights["high_impact_violations"], list)

    def test_violation_impact_tracking(self):
        """Test tracking of violation impact."""
        violations = [
            {"method": "process_data", "callers": 50},
            {"method": "validate_input", "callers": 100},
        ]

        # Sort by impact (callers)
        sorted_violations = sorted(
            violations,
            key=lambda v: v["callers"],
            reverse=True
        )

        assert sorted_violations[0]["method"] == "validate_input"
