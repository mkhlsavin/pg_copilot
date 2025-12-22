"""
Data models for Multi-Criteria Hypothesis Generation.

This module defines the core data structures used throughout the hypothesis
generation and validation pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class Severity(str, Enum):
    """Vulnerability severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ValidationStatus(str, Enum):
    """Hypothesis validation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"


class EvaluationStrategy(str, Enum):
    """Parameter evaluation strategy (from CPG spec)."""
    BY_VALUE = "BY_VALUE"
    BY_REFERENCE = "BY_REFERENCE"
    BY_SHARING = "BY_SHARING"


@dataclass
class CWEEntry:
    """Common Weakness Enumeration entry.

    Represents a vulnerability pattern from the CWE database with
    language-specific metadata and scoring information.
    """
    id: str                         # "CWE-120"
    name: str                       # "Buffer Copy without Checking Size"
    description: str
    severity: Severity
    cvss_base: float                # Base CVSS score (0.0-10.0)
    languages: List[str]            # ["C", "C++"]
    prevalence: float               # How common (0.0-1.0)
    exploitability: float           # Ease of exploitation (0.0-1.0)
    related_cwes: List[str] = field(default_factory=list)  # ["CWE-119", "CWE-787"]
    capec_ids: List[str] = field(default_factory=list)     # ["CAPEC-100"]
    mitigations: List[str] = field(default_factory=list)
    detection_methods: List[str] = field(default_factory=list)

    @property
    def numeric_id(self) -> int:
        """Extract numeric ID from CWE identifier."""
        return int(self.id.replace("CWE-", ""))

    @property
    def risk_score(self) -> float:
        """Calculate combined risk score."""
        return self.prevalence * self.exploitability * (self.cvss_base / 10.0)


@dataclass
class CAPECPattern:
    """Common Attack Pattern Enumeration and Classification entry.

    Represents an attack pattern that can exploit one or more CWEs.
    """
    id: str                         # "CAPEC-100"
    name: str                       # "Overflow Buffers"
    description: str
    related_cwes: List[str]         # ["CWE-120", "CWE-119"]
    attack_steps: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    typical_severity: Severity = Severity.HIGH
    likelihood: float = 0.5         # Attack likelihood (0.0-1.0)
    skill_level: str = "Medium"     # Low, Medium, High, Expert

    @property
    def numeric_id(self) -> int:
        """Extract numeric ID from CAPEC identifier."""
        return int(self.id.replace("CAPEC-", ""))


@dataclass
class LanguagePattern:
    """Language-specific vulnerability pattern.

    Defines sinks (dangerous functions), sources (taint origins),
    and sanitizers for a specific programming language.
    """
    language: str                   # "C", "Python", "Java"
    category: str                   # "memory", "injection", "crypto"
    sinks: List[str]                # ["strcpy", "memcpy"]
    sources: List[str]              # ["recv", "getenv"]
    sanitizers: List[str]           # ["strlcpy", "snprintf"]
    related_cwes: List[str]         # ["CWE-120"]
    description: str = ""
    examples: List[str] = field(default_factory=list)


@dataclass
class Evidence:
    """Evidence supporting or refuting a hypothesis.

    Captures query results and analysis that validates a security finding.
    """
    id: str
    hypothesis_id: str
    query_executed: str             # The SQL/PGQ query that found this
    result_count: int
    findings: List[Dict[str, Any]]  # Query results
    filename: Optional[str] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    confidence: float = 0.5         # How confident in this evidence (0.0-1.0)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    notes: str = ""

    @property
    def is_positive(self) -> bool:
        """Check if evidence supports the hypothesis."""
        return self.result_count > 0 and self.confidence > 0.5


@dataclass
class SecurityHypothesis:
    """A testable security vulnerability hypothesis.

    Core data structure for hypothesis-driven security analysis.
    Generated from CWE/CAPEC combinations and validated against CPG.
    """
    id: str
    hypothesis_text: str            # Human-readable hypothesis statement

    # Classification
    cwe_ids: List[str]              # ["CWE-120"]
    capec_ids: List[str]            # ["CAPEC-100"]
    language: str                   # "C"
    category: str                   # "memory", "injection", etc.

    # Taint analysis patterns
    source_patterns: List[str]      # ["PQgetvalue", "getenv"]
    sink_patterns: List[str]        # ["strcpy", "memcpy"]
    sanitizer_patterns: List[str]   # ["strlcpy", "sizeof"]

    # Scoring
    priority_score: float = 0.0     # Overall priority (0.0-1.0)
    confidence: float = 0.0         # Confidence in hypothesis (0.0-1.0)

    # Multi-criteria breakdown
    cwe_frequency_score: float = 0.0
    attack_similarity_score: float = 0.0
    codebase_exposure_score: float = 0.0

    # DuckDB SQL/PGQ Query (NOT Joern DSL)
    sql_query: Optional[str] = None

    # Evidence and validation
    evidence: List[Evidence] = field(default_factory=list)
    validation_status: ValidationStatus = ValidationStatus.PENDING
    validated_at: Optional[datetime] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)
    notes: str = ""

    @property
    def is_confirmed(self) -> bool:
        """Check if hypothesis has been confirmed."""
        return self.validation_status == ValidationStatus.CONFIRMED

    @property
    def has_evidence(self) -> bool:
        """Check if hypothesis has supporting evidence."""
        return len(self.evidence) > 0 and any(e.is_positive for e in self.evidence)

    def add_evidence(self, evidence: Evidence) -> None:
        """Add evidence to hypothesis."""
        self.evidence.append(evidence)
        # Update confidence based on evidence
        if evidence.is_positive:
            self.confidence = min(1.0, self.confidence + 0.1 * evidence.confidence)


@dataclass
class HypothesisBatch:
    """A batch of related hypotheses for processing.

    Used for efficient batch processing and reporting.
    """
    id: str
    name: str
    description: str
    hypotheses: List[SecurityHypothesis]
    target_project: str             # e.g., "postgresql-17.5"
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def total_count(self) -> int:
        return len(self.hypotheses)

    @property
    def confirmed_count(self) -> int:
        return sum(1 for h in self.hypotheses if h.is_confirmed)

    @property
    def pending_count(self) -> int:
        return sum(1 for h in self.hypotheses
                   if h.validation_status == ValidationStatus.PENDING)

    def get_by_cwe(self, cwe_id: str) -> List[SecurityHypothesis]:
        """Get hypotheses for a specific CWE."""
        return [h for h in self.hypotheses if cwe_id in h.cwe_ids]

    def get_top_priority(self, n: int = 10) -> List[SecurityHypothesis]:
        """Get top N hypotheses by priority score."""
        return sorted(self.hypotheses, key=lambda h: h.priority_score, reverse=True)[:n]


@dataclass
class ValidationResults:
    """Results from hypothesis validation run.

    Comprehensive metrics for evaluating hypothesis generation quality.
    """
    batch_id: str
    total_hypotheses: int
    executed_queries: int

    # CVE Detection (for known vulnerability testing)
    cves_found: List[str] = field(default_factory=list)
    cves_missed: List[str] = field(default_factory=list)

    # Precision/Recall metrics
    true_positives: int = 0         # Confirmed vulnerabilities
    false_positives: int = 0        # Not actual vulnerabilities
    false_negatives: int = 0        # Missed vulnerabilities

    # Hypothesis quality
    confirmed_hypotheses: int = 0
    rejected_hypotheses: int = 0
    inconclusive_hypotheses: int = 0

    # Performance
    generation_time_sec: float = 0.0
    execution_time_sec: float = 0.0

    # Timestamps
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    @property
    def detection_rate(self) -> float:
        """Calculate CVE detection rate."""
        total_cves = len(self.cves_found) + len(self.cves_missed)
        if total_cves == 0:
            return 0.0
        return len(self.cves_found) / total_cves

    @property
    def precision(self) -> float:
        """Calculate precision: TP / (TP + FP)."""
        denominator = self.true_positives + self.false_positives
        if denominator == 0:
            return 0.0
        return self.true_positives / denominator

    @property
    def recall(self) -> float:
        """Calculate recall: TP / (TP + FN)."""
        denominator = self.true_positives + self.false_negatives
        if denominator == 0:
            return 0.0
        return self.true_positives / denominator

    @property
    def f1_score(self) -> float:
        """Calculate F1 score: 2 * (precision * recall) / (precision + recall)."""
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)

    @property
    def hypothesis_accuracy(self) -> float:
        """Calculate hypothesis confirmation rate."""
        total = self.confirmed_hypotheses + self.rejected_hypotheses
        if total == 0:
            return 0.0
        return self.confirmed_hypotheses / total

    @property
    def total_time_sec(self) -> float:
        """Total time for generation + execution."""
        return self.generation_time_sec + self.execution_time_sec
