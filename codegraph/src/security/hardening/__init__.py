"""
D3FEND Source Code Hardening Module

Provides checks based on MITRE D3FEND Source Code Hardening techniques:
- D3-VI: Variable Initialization
- D3-CS: Credential Scrubbing
- D3-IRV: Integer Range Validation
- D3-PV: Pointer Validation
- D3-RN: Reference Nullification
- D3-TL: Trusted Library
- D3-VTV: Variable Type Validation
- D3-MBSV: Memory Block Start Validation
- D3-NPC: Null Pointer Checking
- D3-DLV: Domain Logic Validation
- D3-OLV: Operational Logic Validation

Usage:
    from src.security.hardening import HardeningScanner, HardeningCategory

    # Initialize scanner with CPG service
    scanner = HardeningScanner(cpg_service, language="c")

    # Run all applicable checks
    findings = scanner.scan_all()

    # Run specific D3FEND techniques
    findings = scanner.scan_by_d3fend_id(["D3-VI", "D3-NPC", "D3-TL"])

    # Get compliance scores
    scores = scanner.get_compliance_score(findings)
"""

from .base import (
    HardeningCheck,
    HardeningCategory,
    HardeningSeverity,
    HardeningFinding,
    D3FEND_CATEGORY_MAP,
    D3FEND_TECHNIQUES,
    get_category_for_d3fend,
    get_d3fend_info,
)

from .hardening_scanner import HardeningScanner

from .d3fend_checks import (
    # Registry and lookup functions
    HARDENING_CHECKS,
    D3FEND_TECHNIQUE_IDS,
    get_check_by_id,
    get_checks_by_category,
    get_checks_by_d3fend_id,
    get_all_checks,
    get_checks_for_language,

    # Individual check definitions (for reference)
    VARIABLE_INITIALIZATION_CHECK,
    CREDENTIAL_SCRUBBING_CHECK,
    INTEGER_RANGE_VALIDATION_CHECK,
    REFERENCE_NULLIFICATION_CHECK,
    TRUSTED_LIBRARY_CHECK,
    VARIABLE_TYPE_VALIDATION_CHECK,
    MEMORY_BLOCK_START_VALIDATION_CHECK,
    NULL_POINTER_CHECKING,
    DOMAIN_LOGIC_VALIDATION_CHECK,
    OPERATIONAL_LOGIC_VALIDATION_CHECK,
    POINTER_VALIDATION_CHECK,
)


__all__ = [
    # Base types
    "HardeningCheck",
    "HardeningCategory",
    "HardeningSeverity",
    "HardeningFinding",

    # D3FEND metadata
    "D3FEND_CATEGORY_MAP",
    "D3FEND_TECHNIQUES",
    "D3FEND_TECHNIQUE_IDS",
    "get_category_for_d3fend",
    "get_d3fend_info",

    # Scanner
    "HardeningScanner",

    # Registry
    "HARDENING_CHECKS",
    "get_check_by_id",
    "get_checks_by_category",
    "get_checks_by_d3fend_id",
    "get_all_checks",
    "get_checks_for_language",

    # Individual checks
    "VARIABLE_INITIALIZATION_CHECK",
    "CREDENTIAL_SCRUBBING_CHECK",
    "INTEGER_RANGE_VALIDATION_CHECK",
    "REFERENCE_NULLIFICATION_CHECK",
    "TRUSTED_LIBRARY_CHECK",
    "VARIABLE_TYPE_VALIDATION_CHECK",
    "MEMORY_BLOCK_START_VALIDATION_CHECK",
    "NULL_POINTER_CHECKING",
    "DOMAIN_LOGIC_VALIDATION_CHECK",
    "OPERATIONAL_LOGIC_VALIDATION_CHECK",
    "POINTER_VALIDATION_CHECK",
]
