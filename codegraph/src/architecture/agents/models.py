"""Architecture Agents Data Models.

Data structures for architecture violation detection and reporting.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional


@dataclass
class ViolationFinding:
    """
    A detected instance of an architecture violation.

    Attributes:
        finding_id: Unique identifier for this finding
        pattern_id: ID of the pattern that was violated
        pattern_name: Human-readable pattern name
        category: Violation category (dependency, layering, coupling, cohesion)
        severity: Violation severity (critical, high, medium, low)
        module_a: First module involved in violation
        module_b: Second module involved (if applicable)
        violation_details: Specific details about this violation
        impact_description: Description of impact
        remediation_steps: How to fix this violation
        metadata: Additional CPG data
    """
    finding_id: str
    pattern_id: str
    pattern_name: str
    category: str
    severity: str
    module_a: str
    module_b: Optional[str] = None
    violation_details: str = ""
    impact_description: str = ""
    remediation_steps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyMetrics:
    """
    Metrics for a module's dependencies.

    Attributes:
        module_name: Module file path
        fan_in: Number of modules that depend on this module
        fan_out: Number of modules this module depends on
        instability: Instability metric (0.0-1.0, higher = more unstable)
        coupling_score: Overall coupling score
        is_god_module: Whether this is a god module
        violation_count: Number of violations for this module
    """
    module_name: str
    fan_in: int
    fan_out: int
    instability: float
    coupling_score: int
    is_god_module: bool
    violation_count: int = 0


@dataclass
class DependencyAnalysis:
    """
    Complete dependency analysis result.

    Attributes:
        analysis_id: Unique identifier
        timestamp: When analysis was performed
        total_modules: Total number of modules analyzed
        total_violations: Total violations found
        violations_by_severity: Count by severity level
        violations_by_category: Count by category
        circular_dependency_count: Number of circular dependency chains
        god_module_count: Number of god modules
        module_metrics: Dependency metrics per module
        high_coupling_modules: List of highly coupled modules
    """
    analysis_id: str
    timestamp: str
    total_modules: int
    total_violations: int
    violations_by_severity: Dict[str, int]
    violations_by_category: Dict[str, int]
    circular_dependency_count: int
    god_module_count: int
    module_metrics: List[DependencyMetrics]
    high_coupling_modules: List[str]


@dataclass
class LayerRule:
    """
    Architectural layer dependency rule.

    Attributes:
        from_layer: Source layer name
        to_layer: Target layer name
        allowed: Whether this dependency is allowed
        description: Rule description
    """
    from_layer: str
    to_layer: str
    allowed: bool
    description: str


@dataclass
class RemediationAction:
    """
    Prioritized remediation action for a violation.

    Attributes:
        action_id: Unique identifier
        finding_id: Associated finding ID
        priority: Priority score (1-10, 10 = highest)
        violation_type: Type of violation
        action_description: What to do
        estimated_effort: Effort estimate (low, medium, high)
        risk_level: Risk of fixing (low, medium, high)
        modules_affected: List of affected modules
    """
    action_id: str
    finding_id: str
    priority: int
    violation_type: str
    action_description: str
    estimated_effort: str
    risk_level: str
    modules_affected: List[str]


@dataclass
class ArchitectureReport:
    """
    Complete architecture violation report.

    Attributes:
        report_id: Unique identifier
        timestamp: When report was generated
        total_violations: Total violations found
        by_severity: Violations grouped by severity
        by_category: Violations grouped by category
        findings: All violation findings
        dependency_analysis: Dependency metrics and analysis
        layer_metrics: Layer-specific metrics (if available)
        remediation_actions: Prioritized remediation actions
        summary: Executive summary
        recommendations: Top recommendations
        action_items: High-priority action items
    """
    report_id: str
    timestamp: str
    total_violations: int
    by_severity: Dict[str, int]
    by_category: Dict[str, int]
    findings: List[ViolationFinding]
    dependency_analysis: Optional[DependencyAnalysis]
    layer_metrics: Optional[Dict[str, Any]]
    remediation_actions: List[RemediationAction]
    summary: str
    recommendations: List[str]
    action_items: List[str]
