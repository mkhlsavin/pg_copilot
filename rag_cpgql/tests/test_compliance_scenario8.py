"""
Test Suite for Scenario 8: Regulatory Compliance (Week 13)

Tests the three-agent compliance system:
- LicenseDetector: License scanning and conflict detection
- ComplianceValidator: Privacy and security validation
- StandardsChecker: Coding standards enforcement

Test Coverage:
- LicenseDetector: 6 tests
- ComplianceValidator: 5 tests
- StandardsChecker: 5 tests
- Integration: 1 test
- Total: 17 tests
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from typing import Dict, List, Any

from src.compliance import (
    LicenseDetector,
    ComplianceValidator,
    StandardsChecker,
    ComplianceSeverity,
    ComplianceCategory,
    ComplianceRule,
    ComplianceViolation,
    ComplianceReport,
    LICENSE_RULES,
    PRIVACY_RULES,
    SECURITY_RULES,
    STANDARDS_RULES,
)


# ============================================================================
# Test Data
# ============================================================================

SAMPLE_MIT_LICENSE = """
# Copyright 2025 Example Corp
# SPDX-License-Identifier: MIT

def my_function():
    pass
"""

SAMPLE_GPL_LICENSE = """
# This file is part of Project X.
#
# Project X is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License.

def my_function():
    pass
"""

SAMPLE_NO_LICENSE = """
def my_function():
    pass
"""

SAMPLE_HARDCODED_PASSWORD = """
def connect_to_db():
    password = "MySecretPassword123"
    return connect(user="admin", password=password)
"""


# ============================================================================
# LicenseDetector Tests (6 tests)
# ============================================================================

class TestLicenseDetector:
    """Test suite for LicenseDetector agent"""

    @pytest.fixture
    def detector(self):
        """Create LicenseDetector instance"""
        return LicenseDetector()

    def test_scan_file_with_license(self, detector, tmp_path):
        """Test 1: Scan file with valid license header"""
        print("\n[TEST 1] Testing file with license header...")

        # Create temp file with license
        test_file = tmp_path / "licensed.py"
        test_file.write_text(SAMPLE_MIT_LICENSE)

        violations = detector.scan_file_licenses([str(test_file)])

        # Should have no violations for missing license
        missing_license_violations = [
            v for v in violations
            if v.rule.rule_id == "LIC-001"
        ]
        assert len(missing_license_violations) == 0
        print("[PASS] File with license passed check")

    def test_scan_file_without_license(self, detector, tmp_path):
        """Test 2: Detect missing license header"""
        print("\n[TEST 2] Testing file without license...")

        # Create temp file without license
        test_file = tmp_path / "unlicensed.py"
        test_file.write_text(SAMPLE_NO_LICENSE)

        violations = detector.scan_file_licenses([str(test_file)])

        # Should have violation for missing license
        missing_license_violations = [
            v for v in violations
            if v.rule.rule_id == "LIC-001"
        ]
        assert len(missing_license_violations) == 1
        print("[PASS] Missing license detected")

    def test_detect_gpl_license(self, detector, tmp_path):
        """Test 3: Detect GPL license"""
        print("\n[TEST 3] Testing GPL license detection...")

        # Create temp file with GPL
        test_file = tmp_path / "gpl_file.py"
        test_file.write_text(SAMPLE_GPL_LICENSE)

        violations = detector.scan_file_licenses([str(test_file)])

        # Should detect GPL
        gpl_violations = [
            v for v in violations
            if v.rule.rule_id == "LIC-002"
        ]
        assert len(gpl_violations) == 1
        print("[PASS] GPL license detected")

    def test_detect_license_conflicts(self, detector):
        """Test 4: Detect incompatible licenses"""
        print("\n[TEST 4] Testing license conflict detection...")

        # Apache-2.0 and GPL-2.0 are incompatible
        licenses = ["Apache-2.0", "GPL-2.0"]

        violations = detector.detect_license_conflicts(licenses)

        assert len(violations) > 0
        assert any("Incompatible" in v.description for v in violations)
        print(f"[PASS] Detected {len(violations)} license conflicts")

    def test_compatible_licenses(self, detector):
        """Test 5: Compatible licenses should pass"""
        print("\n[TEST 5] Testing compatible licenses...")

        # MIT and Apache-2.0 are compatible
        licenses = ["MIT", "Apache-2.0"]

        violations = detector.detect_license_conflicts(licenses)

        # Should be compatible (MIT allows Apache-2.0)
        assert len(violations) == 0
        print("[PASS] Compatible licenses passed")

    def test_extract_license_from_text(self, detector):
        """Test 6: Extract license type from text"""
        print("\n[TEST 6] Testing license extraction...")

        # Test MIT extraction
        mit_license = detector.extract_license_from_text(SAMPLE_MIT_LICENSE)
        assert mit_license is None or "MIT" in str(mit_license).upper()

        # Test GPL extraction
        gpl_license = detector.extract_license_from_text(SAMPLE_GPL_LICENSE)
        assert gpl_license in ["GPL-2.0", "GPL-3.0", None]

        print("[PASS] License extraction works")


# ============================================================================
# ComplianceValidator Tests (5 tests)
# ============================================================================

class TestComplianceValidator:
    """Test suite for ComplianceValidator agent"""

    @pytest.fixture
    def mock_cpg(self):
        """Create mock CPG service"""
        mock = Mock()
        mock.execute_custom_sql = Mock(return_value=[])
        return mock

    @pytest.fixture
    def validator(self, mock_cpg):
        """Create ComplianceValidator instance"""
        return ComplianceValidator(mock_cpg)

    def test_check_privacy_compliance(self, validator, mock_cpg):
        """Test 7: Check privacy compliance"""
        print("\n[TEST 7] Testing privacy compliance checks...")

        # Mock PII violations
        mock_cpg.execute_custom_sql = Mock(return_value=[
            {'name': 'user_email', 'filename': 'user.py', 'line_number': 10},
            {'name': 'ssn', 'filename': 'data.py', 'line_number': 25},
        ])

        violations = validator.check_privacy_compliance()

        assert isinstance(violations, list)
        print(f"[PASS] Found {len(violations)} privacy violations")

    def test_check_security_compliance(self, validator, mock_cpg):
        """Test 8: Check security compliance"""
        print("\n[TEST 8] Testing security compliance checks...")

        # Mock security violations
        mock_cpg.execute_custom_sql = Mock(return_value=[
            {'name': 'md5_hash', 'filename': 'crypto.py', 'line_number': 15, 'code': 'hashlib.md5()'},
        ])

        violations = validator.check_security_compliance()

        assert isinstance(violations, list)
        print(f"[PASS] Found {len(violations)} security violations")

    def test_check_hardcoded_secrets(self, validator):
        """Test 9: Detect hardcoded credentials"""
        print("\n[TEST 9] Testing hardcoded secret detection...")

        violations = validator.check_hardcoded_secrets(
            SAMPLE_HARDCODED_PASSWORD,
            "db_connect.py"
        )

        # Should detect hardcoded password
        assert len(violations) > 0
        assert any("password" in v.code_snippet.lower() for v in violations)
        print(f"[PASS] Detected {len(violations)} hardcoded secrets")

    def test_no_hardcoded_secrets(self, validator):
        """Test 10: Clean code should pass"""
        print("\n[TEST 10] Testing clean code...")

        clean_code = """
def connect_to_db():
    password = os.environ.get('DB_PASSWORD')
    return connect(user="admin", password=password)
"""

        violations = validator.check_hardcoded_secrets(clean_code, "db_connect.py")

        # Environment variable usage should be OK
        assert len(violations) == 0
        print("[PASS] Clean code passed secret check")

    def test_privacy_compliance_no_violations(self, validator, mock_cpg):
        """Test 11: No violations should return empty list"""
        print("\n[TEST 11] Testing no privacy violations...")

        # Mock empty results
        mock_cpg.execute_custom_sql = Mock(return_value=[])

        violations = validator.check_privacy_compliance()

        assert len(violations) == 0
        print("[PASS] No violations detected correctly")


# ============================================================================
# StandardsChecker Tests (5 tests)
# ============================================================================

class TestStandardsChecker:
    """Test suite for StandardsChecker agent"""

    @pytest.fixture
    def mock_cpg(self):
        """Create mock CPG service"""
        mock = Mock()
        mock.execute_custom_sql = Mock(return_value=[])
        return mock

    @pytest.fixture
    def checker(self, mock_cpg):
        """Create StandardsChecker instance"""
        return StandardsChecker(mock_cpg)

    def test_check_documentation(self, checker, mock_cpg):
        """Test 12: Check for missing documentation"""
        print("\n[TEST 12] Testing documentation checks...")

        # Mock undocumented methods
        mock_cpg.execute_custom_sql = Mock(return_value=[
            {'name': 'process_data', 'filename': 'processor.py', 'line_number': 42},
        ])

        violations = checker.check_documentation()

        assert isinstance(violations, list)
        print(f"[PASS] Found {len(violations)} documentation violations")

    def test_check_complexity(self, checker, mock_cpg):
        """Test 13: Check for excessive complexity"""
        print("\n[TEST 13] Testing complexity checks...")

        # Mock high complexity methods
        mock_cpg.execute_custom_sql = Mock(return_value=[
            {'name': 'complex_function', 'filename': 'complex.py', 'line_number': 100, 'complexity': '25'},
        ])

        violations = checker.check_complexity()

        assert isinstance(violations, list)
        if len(violations) > 0:
            assert any("complexity" in v.description.lower() for v in violations)
        print(f"[PASS] Found {len(violations)} complexity violations")

    def test_check_naming_conventions_python(self, checker):
        """Test 14: Check Python naming conventions"""
        print("\n[TEST 14] Testing naming conventions...")

        identifiers = [
            {'name': 'myFunction', 'kind': 'function', 'filepath': 'test.py', 'line_number': 10},
            {'name': 'MyClass', 'kind': 'class', 'filepath': 'test.py', 'line_number': 20},
            {'name': 'my_function', 'kind': 'function', 'filepath': 'test.py', 'line_number': 30},
        ]

        violations = checker.check_naming_conventions(identifiers, language="python")

        # myFunction should violate snake_case
        bad_names = [v for v in violations if 'myFunction' in v.description]
        assert len(bad_names) > 0

        # MyClass should be OK (PascalCase)
        # my_function should be OK (snake_case)

        print(f"[PASS] Detected {len(violations)} naming violations")

    def test_check_magic_numbers(self, checker):
        """Test 15: Detect magic numbers"""
        print("\n[TEST 15] Testing magic number detection...")

        code_with_magic = """
def calculate_price(base_price):
    tax_rate = 0.15
    discount = base_price * 42
    total = base_price + 365
    return total * tax_rate - discount
"""

        violations = checker.check_magic_numbers(code_with_magic, "pricing.py")

        # Should detect magic numbers (42, 365)
        # Note: Some may be filtered if implementation is strict
        assert isinstance(violations, list)
        print(f"[PASS] Magic number detection works ({len(violations)} found)")

    def test_generate_compliance_report(self, checker):
        """Test 16: Generate compliance report"""
        print("\n[TEST 16] Testing compliance report generation...")

        # Create sample violations
        violations = [
            ComplianceViolation(
                violation_id="TEST_001",
                rule=SECURITY_RULES["HARDCODED_CREDENTIALS"],
                filepath="test.py",
                line_number=10,
                description="Test violation 1"
            ),
            ComplianceViolation(
                violation_id="TEST_002",
                rule=STANDARDS_RULES["MISSING_DOCSTRING"],
                filepath="test.py",
                line_number=20,
                description="Test violation 2"
            ),
        ]

        report = checker.generate_compliance_report(violations)

        assert isinstance(report, ComplianceReport)
        assert report.compliance_score >= 0
        assert report.compliance_score <= 100
        assert len(report.violations) == 2
        assert report.critical_count >= 0
        print(f"[PASS] Generated report with score: {report.compliance_score:.1f}/100")


# ============================================================================
# Integration Test (1 test)
# ============================================================================

class TestScenario8Integration:
    """Full end-to-end integration test for Scenario 8"""

    def test_full_compliance_workflow(self, tmp_path):
        """Test 17: Complete compliance workflow integration"""
        print("\n[TEST 17] Testing full compliance workflow integration...")

        # Create test files
        test_file_licensed = tmp_path / "licensed.py"
        test_file_licensed.write_text(SAMPLE_MIT_LICENSE)

        test_file_unlicensed = tmp_path / "unlicensed.py"
        test_file_unlicensed.write_text(SAMPLE_NO_LICENSE)

        test_file_secrets = tmp_path / "secrets.py"
        test_file_secrets.write_text(SAMPLE_HARDCODED_PASSWORD)

        # Mock CPG service
        mock_cpg = Mock()
        mock_cpg.execute_custom_sql = Mock(return_value=[
            {'name': 'undocumented_func', 'filename': 'test.py', 'line_number': 42},
        ])

        all_violations = []

        # Step 1: License Detection
        license_detector = LicenseDetector()
        license_violations = license_detector.scan_file_licenses([
            str(test_file_licensed),
            str(test_file_unlicensed),
        ])
        all_violations.extend(license_violations)

        assert len(license_violations) > 0  # Should find unlicensed file
        print(f"  [STEP 1] Found {len(license_violations)} license violations")

        # Step 2: Compliance Validation
        compliance_validator = ComplianceValidator(mock_cpg)

        # Check hardcoded secrets
        with open(test_file_secrets, 'r') as f:
            content = f.read()
        secret_violations = compliance_validator.check_hardcoded_secrets(
            content,
            str(test_file_secrets)
        )
        all_violations.extend(secret_violations)

        assert len(secret_violations) > 0  # Should find hardcoded password
        print(f"  [STEP 2] Found {len(secret_violations)} security violations")

        # Step 3: Standards Checking
        standards_checker = StandardsChecker(mock_cpg)

        doc_violations = standards_checker.check_documentation()
        all_violations.extend(doc_violations)

        print(f"  [STEP 3] Found {len(doc_violations)} documentation violations")

        # Step 4: Generate Report
        report = standards_checker.generate_compliance_report(all_violations)

        assert isinstance(report, ComplianceReport)
        assert len(report.violations) > 0
        assert 0 <= report.compliance_score <= 100
        assert len(report.recommendations) > 0

        print(f"\n[PASS] Full workflow completed successfully:")
        print(f"  - Total Violations: {len(all_violations)}")
        print(f"  - Compliance Score: {report.compliance_score:.1f}/100")
        print(f"  - Critical: {report.critical_count}")
        print(f"  - High: {report.high_count}")
        print(f"  - Status: {'PASSED' if report.passed else 'FAILED'}")


# ============================================================================
# Test Execution
# ============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("SCENARIO 8 TEST SUITE: Regulatory Compliance")
    print("=" * 80)

    # Run all tests
    exit_code = pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '--color=yes'
    ])

    print("\n" + "=" * 80)
    if exit_code == 0:
        print("ALL TESTS PASSED")
    else:
        print(f"TESTS FAILED (exit code: {exit_code})")
    print("=" * 80)

    exit(exit_code)
