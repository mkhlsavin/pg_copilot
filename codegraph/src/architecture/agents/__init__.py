"""Architecture Agents Package.

Three specialized agents for detecting and analyzing architectural violations:

1. DependencyAnalyzer - Detects dependency-related violations
   - Circular dependencies
   - Unstable dependencies
   - God modules
   - Feature envy
   - Inappropriate intimacy

2. LayerValidator - Validates architectural layering
   - Layering violations (lower calling higher)
   - Architecture rule enforcement
   - Layer dependency validation

3. ArchitectureReporter - Generates violation reports
   - Structured violation reports
   - Remediation recommendations
   - Priority-based action items

Example usage:
    from src.architecture.agents import DependencyAnalyzer, LayerValidator, ArchitectureReporter

    analyzer = DependencyAnalyzer(cpg_service)
    findings = analyzer.detect_all_violations()

    validator = LayerValidator(cpg_service)
    layer_findings = validator.validate_all_layers()

    reporter = ArchitectureReporter()
    report = reporter.generate_report(findings)
"""

from .models import (
    ViolationFinding,
    DependencyMetrics,
    DependencyAnalysis,
    LayerRule,
    RemediationAction,
    ArchitectureReport,
)
from .dependency import DependencyAnalyzer
from .layer import LayerValidator
from .reporter import ArchitectureReporter

__all__ = [
    # Agents
    "DependencyAnalyzer",
    "LayerValidator",
    "ArchitectureReporter",
    # Models
    "ViolationFinding",
    "DependencyMetrics",
    "DependencyAnalysis",
    "LayerRule",
    "RemediationAction",
    "ArchitectureReport",
]
