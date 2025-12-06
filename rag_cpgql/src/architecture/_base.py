"""
Architecture Pattern Library - Base Types

Contains core types, enums, and data structures for architecture patterns.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class ViolationSeverity(Enum):
    """Severity levels for architecture violations"""
    CRITICAL = "critical"  # System-wide architectural breakdown
    HIGH = "high"          # Major architectural issues
    MEDIUM = "medium"      # Moderate architectural concerns
    LOW = "low"            # Minor architectural improvements


class ViolationCategory(Enum):
    """Categories of architecture violations"""
    DEPENDENCY = "dependency"       # Circular deps, unstable deps
    LAYERING = "layering"          # Layer violations
    COUPLING = "coupling"          # God modules, inappropriate intimacy
    COHESION = "cohesion"          # Feature envy, low cohesion


@dataclass
class ArchitecturePattern:
    """
    Definition of an architecture violation pattern.

    Attributes:
        pattern_id: Unique identifier (e.g., "CIRCULAR_DEPS")
        name: Human-readable name
        description: What this violation means
        category: ViolationCategory enum
        severity: ViolationSeverity enum
        symptoms: Observable signs of this violation
        remediation: How to fix this violation
        impact: Consequences of this violation
        detection_query: SQL/CPGQL query to find instances
        example_before: Code example showing violation
        example_after: Code example after fix
    """
    pattern_id: str
    name: str
    description: str
    category: ViolationCategory
    severity: ViolationSeverity
    symptoms: List[str]
    remediation: str
    impact: str
    detection_query: str
    example_before: str = ""
    example_after: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'pattern_id': self.pattern_id,
            'name': self.name,
            'description': self.description,
            'category': self.category.value,
            'severity': self.severity.value,
            'symptoms': self.symptoms,
            'remediation': self.remediation,
            'impact': self.impact,
            'detection_query': self.detection_query,
            'example_before': self.example_before,
            'example_after': self.example_after
        }


def validate_pattern(pattern: ArchitecturePattern) -> bool:
    """
    Validate that a pattern has all required fields.

    Args:
        pattern: Pattern to validate

    Returns:
        True if valid, False otherwise
    """
    required_fields = [
        'pattern_id', 'name', 'description', 'category',
        'severity', 'symptoms', 'remediation', 'impact', 'detection_query'
    ]

    for field_name in required_fields:
        if not getattr(pattern, field_name):
            return False

    return True


__all__ = [
    'ViolationSeverity',
    'ViolationCategory',
    'ArchitecturePattern',
    'validate_pattern',
]
