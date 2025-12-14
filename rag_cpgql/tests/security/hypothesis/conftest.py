"""
Shared fixtures for hypothesis generation tests.

Provides reusable test fixtures for:
- CWE entries
- CAPEC patterns
- Language patterns
- Security hypotheses
- Evidence items
- Hypothesis batches
- Mock DuckDB connections
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any

from src.security.hypothesis.models import (
    Severity,
    ValidationStatus,
    EvaluationStrategy,
    CWEEntry,
    CAPECPattern,
    LanguagePattern,
    Evidence,
    SecurityHypothesis,
    HypothesisBatch,
    ValidationResults,
)


# =============================================================================
# CWE Entry Fixtures
# =============================================================================

@pytest.fixture
def sample_cwe_entry() -> CWEEntry:
    """Create a sample CWE entry for buffer overflow."""
    return CWEEntry(
        id="CWE-120",
        name="Buffer Copy without Checking Size of Input",
        description="Buffer overflow vulnerability",
        severity=Severity.CRITICAL,
        cvss_base=9.8,
        languages=["C", "C++"],
        prevalence=0.85,
        exploitability=0.90,
        related_cwes=["CWE-119", "CWE-787"],
        capec_ids=["CAPEC-100", "CAPEC-123"],
        mitigations=["Use safe string functions"],
        detection_methods=["Static analysis"],
    )


@pytest.fixture
def sample_cwe_entry_medium() -> CWEEntry:
    """Create a sample CWE entry with medium severity."""
    return CWEEntry(
        id="CWE-476",
        name="NULL Pointer Dereference",
        description="NULL pointer dereference vulnerability",
        severity=Severity.MEDIUM,
        cvss_base=5.5,
        languages=["C", "C++"],
        prevalence=0.80,
        exploitability=0.60,
        related_cwes=["CWE-252"],
        capec_ids=["CAPEC-129"],
    )


@pytest.fixture
def sample_cwe_entry_low() -> CWEEntry:
    """Create a sample CWE entry with low severity."""
    return CWEEntry(
        id="CWE-200",
        name="Exposure of Sensitive Information",
        description="Information disclosure vulnerability",
        severity=Severity.LOW,
        cvss_base=3.3,
        languages=["C", "C++", "Python"],
        prevalence=0.55,
        exploitability=0.50,
    )


# =============================================================================
# CAPEC Pattern Fixtures
# =============================================================================

@pytest.fixture
def sample_capec_pattern() -> CAPECPattern:
    """Create a sample CAPEC attack pattern."""
    return CAPECPattern(
        id="CAPEC-100",
        name="Overflow Buffers",
        description="Buffer overflow attack pattern",
        related_cwes=["CWE-120", "CWE-119", "CWE-787"],
        attack_steps=[
            "Identify buffer input",
            "Craft oversized payload",
            "Trigger overflow",
            "Execute payload",
        ],
        prerequisites=["Accessible buffer input", "No bounds checking"],
        typical_severity=Severity.CRITICAL,
        likelihood=0.75,
        skill_level="Medium",
    )


@pytest.fixture
def sample_capec_pattern_low_skill() -> CAPECPattern:
    """Create a sample CAPEC pattern with low skill level."""
    return CAPECPattern(
        id="CAPEC-88",
        name="OS Command Injection",
        description="Command injection attack pattern",
        related_cwes=["CWE-78", "CWE-77"],
        attack_steps=["Identify command input", "Inject shell metacharacters"],
        prerequisites=["Shell command execution"],
        typical_severity=Severity.CRITICAL,
        likelihood=0.80,
        skill_level="Low",
    )


# =============================================================================
# Language Pattern Fixtures
# =============================================================================

@pytest.fixture
def sample_language_pattern() -> LanguagePattern:
    """Create a sample language pattern for C buffer operations."""
    return LanguagePattern(
        language="C",
        category="buffer_overflow",
        sinks=["strcpy", "strcat", "memcpy", "sprintf", "gets"],
        sources=["recv", "read", "fgets", "getenv", "PQgetvalue"],
        sanitizers=["strlcpy", "strlcat", "snprintf"],
        related_cwes=["CWE-120", "CWE-119"],
        description="Buffer overflow patterns in C",
        examples=["strcpy(buf, user_input)"],
    )


@pytest.fixture
def sample_language_pattern_injection() -> LanguagePattern:
    """Create a sample language pattern for command injection."""
    return LanguagePattern(
        language="C",
        category="command_injection",
        sinks=["system", "popen", "execl", "execve"],
        sources=["getenv", "argv", "fgets"],
        sanitizers=["sanitize_command", "quote_argument"],
        related_cwes=["CWE-78", "CWE-77"],
        description="Command injection patterns in C",
    )


# =============================================================================
# Evidence Fixtures
# =============================================================================

@pytest.fixture
def sample_evidence() -> Evidence:
    """Create a sample positive evidence item."""
    return Evidence(
        id="ev-001",
        hypothesis_id="hyp-001",
        query_executed="SELECT * FROM nodes_call WHERE name = 'strcpy'",
        result_count=5,
        findings=[
            {"filename": "utils.c", "line": 42, "code": "strcpy(buf, input)"},
            {"filename": "parser.c", "line": 100, "code": "strcpy(dest, src)"},
        ],
        filename="utils.c",
        line_number=42,
        code_snippet="strcpy(buf, input)",
        confidence=0.85,
        notes="Found multiple unsafe strcpy calls",
    )


@pytest.fixture
def sample_evidence_negative() -> Evidence:
    """Create a sample negative evidence item (no findings)."""
    return Evidence(
        id="ev-002",
        hypothesis_id="hyp-001",
        query_executed="SELECT * FROM nodes_call WHERE name = 'gets'",
        result_count=0,
        findings=[],
        confidence=0.3,
        notes="No dangerous gets() calls found",
    )


@pytest.fixture
def sample_evidence_low_confidence() -> Evidence:
    """Create evidence with low confidence."""
    return Evidence(
        id="ev-003",
        hypothesis_id="hyp-002",
        query_executed="SELECT * FROM nodes_call WHERE name LIKE '%copy%'",
        result_count=10,
        findings=[{"filename": "copy.c", "line": 1}],
        confidence=0.4,
        notes="Uncertain matches",
    )


# =============================================================================
# Security Hypothesis Fixtures
# =============================================================================

@pytest.fixture
def sample_hypothesis() -> SecurityHypothesis:
    """Create a sample security hypothesis."""
    return SecurityHypothesis(
        id="hyp-001",
        hypothesis_text="If untrusted input flows to strcpy without bounds check, then CWE-120 enables buffer overflow.",
        cwe_ids=["CWE-120"],
        capec_ids=["CAPEC-100"],
        language="C",
        category="buffer_overflow",
        source_patterns=["recv", "getenv", "PQgetvalue"],
        sink_patterns=["strcpy", "memcpy"],
        sanitizer_patterns=["strlcpy", "sizeof"],
        priority_score=0.85,
        confidence=0.0,
        cwe_frequency_score=0.9,
        attack_similarity_score=0.8,
        codebase_exposure_score=0.7,
        tags=["postgresql", "memory-safety"],
    )


@pytest.fixture
def sample_hypothesis_confirmed(sample_hypothesis, sample_evidence) -> SecurityHypothesis:
    """Create a confirmed hypothesis with evidence."""
    hyp = sample_hypothesis
    hyp.validation_status = ValidationStatus.CONFIRMED
    hyp.evidence = [sample_evidence]
    hyp.validated_at = datetime.now(timezone.utc)
    hyp.confidence = 0.9
    return hyp


@pytest.fixture
def sample_hypothesis_rejected() -> SecurityHypothesis:
    """Create a rejected hypothesis."""
    return SecurityHypothesis(
        id="hyp-002",
        hypothesis_text="If input flows to gets(), then CWE-242 enables buffer overflow.",
        cwe_ids=["CWE-242"],
        capec_ids=["CAPEC-100"],
        language="C",
        category="buffer_overflow",
        source_patterns=["fgets"],
        sink_patterns=["gets"],
        sanitizer_patterns=[],
        priority_score=0.5,
        validation_status=ValidationStatus.REJECTED,
    )


@pytest.fixture
def sample_hypothesis_pending() -> SecurityHypothesis:
    """Create a pending hypothesis."""
    return SecurityHypothesis(
        id="hyp-003",
        hypothesis_text="If database object names flow to appendPQExpBuffer without fmtId, then code injection is possible.",
        cwe_ids=["CWE-94"],
        capec_ids=["CAPEC-242"],
        language="C",
        category="code_injection",
        source_patterns=["PQgetvalue", "getTables"],
        sink_patterns=["appendPQExpBuffer"],
        sanitizer_patterns=["fmtId", "fmtQualifiedId"],
        priority_score=0.75,
        validation_status=ValidationStatus.PENDING,
    )


# =============================================================================
# Hypothesis Batch Fixtures
# =============================================================================

@pytest.fixture
def sample_batch(
    sample_hypothesis,
    sample_hypothesis_confirmed,
    sample_hypothesis_rejected,
    sample_hypothesis_pending,
) -> HypothesisBatch:
    """Create a sample hypothesis batch."""
    return HypothesisBatch(
        id="batch-001",
        name="PostgreSQL 17.5 Security Audit",
        description="Hypothesis batch for PostgreSQL security validation",
        hypotheses=[
            sample_hypothesis,
            sample_hypothesis_rejected,
            sample_hypothesis_pending,
        ],
        target_project="postgresql-17.5",
    )


@pytest.fixture
def sample_batch_with_confirmed(sample_hypothesis_confirmed) -> HypothesisBatch:
    """Create a batch with confirmed hypotheses."""
    confirmed1 = sample_hypothesis_confirmed
    confirmed2 = SecurityHypothesis(
        id="hyp-conf-2",
        hypothesis_text="Confirmed hypothesis 2",
        cwe_ids=["CWE-78"],
        capec_ids=["CAPEC-88"],
        language="C",
        category="command_injection",
        source_patterns=["getenv"],
        sink_patterns=["system"],
        sanitizer_patterns=[],
        validation_status=ValidationStatus.CONFIRMED,
    )
    return HypothesisBatch(
        id="batch-002",
        name="Confirmed Batch",
        description="Batch with confirmed hypotheses",
        hypotheses=[confirmed1, confirmed2],
        target_project="test-project",
    )


# =============================================================================
# Validation Results Fixtures
# =============================================================================

@pytest.fixture
def sample_validation_results() -> ValidationResults:
    """Create sample validation results."""
    return ValidationResults(
        batch_id="batch-001",
        total_hypotheses=100,
        executed_queries=95,
        cves_found=["CVE-2025-8713", "CVE-2025-8714"],
        cves_missed=["CVE-2025-8715"],
        true_positives=30,
        false_positives=10,
        false_negatives=5,
        confirmed_hypotheses=35,
        rejected_hypotheses=50,
        inconclusive_hypotheses=15,
        generation_time_sec=15.5,
        execution_time_sec=45.2,
    )


@pytest.fixture
def sample_validation_results_empty() -> ValidationResults:
    """Create empty validation results."""
    return ValidationResults(
        batch_id="batch-empty",
        total_hypotheses=0,
        executed_queries=0,
    )


@pytest.fixture
def sample_validation_results_perfect() -> ValidationResults:
    """Create perfect validation results."""
    return ValidationResults(
        batch_id="batch-perfect",
        total_hypotheses=50,
        executed_queries=50,
        cves_found=["CVE-2025-8713", "CVE-2025-8714", "CVE-2025-8715"],
        cves_missed=[],
        true_positives=50,
        false_positives=0,
        false_negatives=0,
        confirmed_hypotheses=50,
        rejected_hypotheses=0,
        inconclusive_hypotheses=0,
        generation_time_sec=10.0,
        execution_time_sec=30.0,
    )


# =============================================================================
# Mock DuckDB Connection Fixtures
# =============================================================================

@pytest.fixture
def mock_duckdb_connection():
    """Create a mock DuckDB connection."""
    mock_conn = MagicMock()
    mock_result = MagicMock()
    mock_result.fetchdf.return_value = MagicMock()
    mock_result.fetchall.return_value = []
    mock_conn.execute.return_value = mock_result
    return mock_conn


@pytest.fixture
def mock_duckdb_with_results():
    """Create a mock DuckDB connection with sample results."""
    mock_conn = MagicMock()
    mock_result = MagicMock()
    mock_df = MagicMock()
    mock_df.to_dict.return_value = [
        {"id": 1, "name": "strcpy", "filename": "utils.c", "line_number": 42},
        {"id": 2, "name": "strcpy", "filename": "parser.c", "line_number": 100},
    ]
    mock_result.fetchdf.return_value = mock_df
    mock_conn.execute.return_value = mock_result
    return mock_conn


# =============================================================================
# Knowledge Base Fixtures
# =============================================================================

@pytest.fixture
def mock_knowledge_base():
    """Create a mock SecurityKnowledgeBase."""
    mock_kb = MagicMock()
    mock_kb.get_cwe.return_value = CWEEntry(
        id="CWE-120",
        name="Buffer Overflow",
        description="Buffer overflow",
        severity=Severity.CRITICAL,
        cvss_base=9.8,
        languages=["C"],
        prevalence=0.85,
        exploitability=0.9,
    )
    mock_kb.get_cwes_by_language.return_value = [
        CWEEntry(
            id="CWE-120",
            name="Buffer Overflow",
            description="Buffer overflow",
            severity=Severity.CRITICAL,
            cvss_base=9.8,
            languages=["C"],
            prevalence=0.85,
            exploitability=0.9,
        )
    ]
    mock_kb.get_patterns_by_language.return_value = [
        LanguagePattern(
            language="C",
            category="buffer_overflow",
            sinks=["strcpy"],
            sources=["getenv"],
            sanitizers=["strlcpy"],
            related_cwes=["CWE-120"],
        )
    ]
    return mock_kb
