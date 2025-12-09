"""
D3FEND Source Code Hardening - Base Types

Provides base types for implementing MITRE D3FEND Source Code Hardening techniques:
- HardeningCategory: Categories aligned with D3FEND taxonomy
- HardeningSeverity: Severity levels for hardening violations
- HardeningCheck: Definition of a hardening check
- HardeningFinding: Result from running a hardening check
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid


class HardeningCategory(Enum):
    """
    D3FEND-aligned hardening categories.

    Maps to MITRE D3FEND Source Code Hardening sub-techniques.
    """
    INITIALIZATION = "initialization"           # D3-VI: Variable Initialization
    CREDENTIAL_MANAGEMENT = "credential_mgmt"   # D3-CS: Credential Scrubbing
    INTEGER_SAFETY = "integer_safety"           # D3-IRV: Integer Range Validation
    POINTER_SAFETY = "pointer_safety"           # D3-PV, D3-NPC, D3-MBSV
    MEMORY_SAFETY = "memory_safety"             # D3-RN: Reference Nullification
    LIBRARY_SAFETY = "library_safety"           # D3-TL: Trusted Library
    TYPE_SAFETY = "type_safety"                 # D3-VTV: Variable Type Validation
    DOMAIN_VALIDATION = "domain_validation"     # D3-DLV: Domain Logic Validation
    OPERATIONAL_VALIDATION = "operational"      # D3-OLV: Operational Logic Validation


class HardeningSeverity(Enum):
    """
    Severity levels for hardening violations.

    Indicates the security impact if the hardening practice is not followed.
    """
    CRITICAL = "critical"  # Directly exploitable, immediate fix required
    HIGH = "high"          # Significant security risk
    MEDIUM = "medium"      # Moderate security risk
    LOW = "low"            # Minor security concern
    INFO = "info"          # Informational, best practice recommendation


# D3FEND technique ID to category mapping
D3FEND_CATEGORY_MAP: Dict[str, HardeningCategory] = {
    "D3-VI": HardeningCategory.INITIALIZATION,
    "D3-CS": HardeningCategory.CREDENTIAL_MANAGEMENT,
    "D3-IRV": HardeningCategory.INTEGER_SAFETY,
    "D3-PV": HardeningCategory.POINTER_SAFETY,
    "D3-RN": HardeningCategory.MEMORY_SAFETY,
    "D3-TL": HardeningCategory.LIBRARY_SAFETY,
    "D3-VTV": HardeningCategory.TYPE_SAFETY,
    "D3-MBSV": HardeningCategory.POINTER_SAFETY,
    "D3-NPC": HardeningCategory.POINTER_SAFETY,
    "D3-DLV": HardeningCategory.DOMAIN_VALIDATION,
    "D3-OLV": HardeningCategory.OPERATIONAL_VALIDATION,
}


# D3FEND technique metadata
D3FEND_TECHNIQUES: Dict[str, Dict[str, str]] = {
    "D3-VI": {
        "name": "Variable Initialization",
        "description": "Setting variables to a known value before use",
        "url": "https://next.d3fend.mitre.org/technique/d3f:VariableInitialization",
    },
    "D3-CS": {
        "name": "Credential Scrubbing",
        "description": "Systematic removal of hard-coded credentials from source code",
        "url": "https://next.d3fend.mitre.org/technique/d3f:CredentialScrubbing",
    },
    "D3-IRV": {
        "name": "Integer Range Validation",
        "description": "Ensuring that an integer is within a valid range",
        "url": "https://next.d3fend.mitre.org/technique/d3f:IntegerRangeValidation",
    },
    "D3-PV": {
        "name": "Pointer Validation",
        "description": "Ensuring that a pointer variable has the required properties for use",
        "url": "https://next.d3fend.mitre.org/technique/d3f:PointerValidation",
    },
    "D3-RN": {
        "name": "Reference Nullification",
        "description": "Invalidating all pointers that reference a specific memory block",
        "url": "https://next.d3fend.mitre.org/technique/d3f:ReferenceNullification",
    },
    "D3-TL": {
        "name": "Trusted Library",
        "description": "Using pre-verified, secure code modules",
        "url": "https://next.d3fend.mitre.org/technique/d3f:TrustedLibrary",
    },
    "D3-VTV": {
        "name": "Variable Type Validation",
        "description": "Ensuring that a variable has the correct type",
        "url": "https://next.d3fend.mitre.org/technique/d3f:VariableTypeValidation",
    },
    "D3-MBSV": {
        "name": "Memory Block Start Validation",
        "description": "Ensuring a pointer accurately references the beginning of a memory block",
        "url": "https://next.d3fend.mitre.org/technique/d3f:MemoryBlockStartValidation",
    },
    "D3-NPC": {
        "name": "Null Pointer Checking",
        "description": "Checking if a pointer is NULL before use",
        "url": "https://next.d3fend.mitre.org/technique/d3f:NullPointerChecking",
    },
    "D3-DLV": {
        "name": "Domain Logic Validation",
        "description": "Validation of variable state in the context of the domain application",
        "url": "https://next.d3fend.mitre.org/technique/d3f:DomainLogicValidation",
    },
    "D3-OLV": {
        "name": "Operational Logic Validation",
        "description": "Validation of variable state in the context of operational control logic",
        "url": "https://next.d3fend.mitre.org/technique/d3f:OperationalLogicValidation",
    },
}


@dataclass
class HardeningCheck:
    """
    Represents a D3FEND hardening check definition.

    A hardening check verifies that defensive coding practices are followed.
    Unlike SecurityPattern which finds vulnerabilities, HardeningCheck verifies
    that protective measures are in place.

    Attributes:
        id: Unique identifier for this check (e.g., "D3-VI-001")
        d3fend_id: D3FEND technique ID (e.g., "D3-VI")
        d3fend_name: D3FEND technique name (e.g., "Variable Initialization")
        category: Hardening category from HardeningCategory enum
        severity: Severity level if the check fails
        description: Human-readable description of what this check detects
        cpgql_query: SQL query to execute against CPG database
        cwe_ids: List of related CWE identifiers
        language_scope: Languages this check applies to (["c", "cpp"] or ["*"] for all)
        indicators: Code patterns that indicate a violation
        good_patterns: Code patterns that indicate compliance
        remediation: Guidance on how to fix violations
        example_code: Example showing good vs bad code
        confidence_weight: Weight for confidence scoring (0.0-1.0)
    """
    id: str
    d3fend_id: str
    d3fend_name: str
    category: HardeningCategory
    severity: HardeningSeverity
    description: str
    cpgql_query: str
    cwe_ids: List[str] = field(default_factory=list)
    language_scope: List[str] = field(default_factory=lambda: ["*"])
    indicators: List[str] = field(default_factory=list)
    good_patterns: List[str] = field(default_factory=list)
    remediation: str = ""
    example_code: str = ""
    confidence_weight: float = 1.0

    def applies_to_language(self, language: str) -> bool:
        """Check if this check applies to the given language."""
        if "*" in self.language_scope:
            return True
        return language.lower() in [l.lower() for l in self.language_scope]

    def get_d3fend_url(self) -> str:
        """Get the D3FEND technique URL."""
        if self.d3fend_id in D3FEND_TECHNIQUES:
            return D3FEND_TECHNIQUES[self.d3fend_id].get("url", "")
        return ""


@dataclass
class HardeningFinding:
    """
    Result from running a hardening check.

    Represents a single location where a hardening practice is not followed.

    Attributes:
        finding_id: Unique identifier for this finding
        check_id: ID of the HardeningCheck that produced this finding
        d3fend_id: D3FEND technique ID
        category: Hardening category
        severity: Severity level
        method_name: Name of the method containing the issue
        filename: Source file path
        line_number: Line number in source file
        code_snippet: Relevant code snippet
        description: Description of the specific issue
        cwe_ids: Related CWE identifiers
        remediation: How to fix this specific issue
        confidence: Confidence score (0.0-1.0)
        metadata: Additional context data
    """
    finding_id: str
    check_id: str
    d3fend_id: str
    category: str
    severity: str
    method_name: str
    filename: str
    line_number: int
    code_snippet: str
    description: str
    cwe_ids: List[str] = field(default_factory=list)
    remediation: str = ""
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_check_and_row(
        cls,
        check: HardeningCheck,
        row: Dict[str, Any],
        confidence: float = 1.0
    ) -> "HardeningFinding":
        """
        Create a HardeningFinding from a check definition and query result row.

        Args:
            check: The HardeningCheck that produced this finding
            row: Query result row with method_name, filename, line_number, etc.
            confidence: Confidence score for this finding

        Returns:
            New HardeningFinding instance
        """
        return cls(
            finding_id=str(uuid.uuid4())[:8],
            check_id=check.id,
            d3fend_id=check.d3fend_id,
            category=check.category.value,
            severity=check.severity.value,
            method_name=row.get("method_name", row.get("method", "unknown")),
            filename=row.get("filename", "unknown"),
            line_number=row.get("line_number", 0),
            code_snippet=row.get("code", row.get("code_snippet", "")),
            description=check.description,
            cwe_ids=check.cwe_ids,
            remediation=check.remediation,
            confidence=confidence * check.confidence_weight,
            metadata=row,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary for serialization."""
        return {
            "finding_id": self.finding_id,
            "check_id": self.check_id,
            "d3fend_id": self.d3fend_id,
            "d3fend_url": D3FEND_TECHNIQUES.get(self.d3fend_id, {}).get("url", ""),
            "category": self.category,
            "severity": self.severity,
            "method_name": self.method_name,
            "filename": self.filename,
            "line_number": self.line_number,
            "code_snippet": self.code_snippet,
            "description": self.description,
            "cwe_ids": self.cwe_ids,
            "remediation": self.remediation,
            "confidence": self.confidence,
        }


def get_category_for_d3fend(d3fend_id: str) -> Optional[HardeningCategory]:
    """Get the hardening category for a D3FEND technique ID."""
    return D3FEND_CATEGORY_MAP.get(d3fend_id)


def get_d3fend_info(d3fend_id: str) -> Optional[Dict[str, str]]:
    """Get D3FEND technique metadata."""
    return D3FEND_TECHNIQUES.get(d3fend_id)
