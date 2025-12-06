"""
Scenario-specific workflow implementations.

Each scenario has its own module containing the LangGraph workflow
and node implementations for that specific use case.

Available Scenarios:
- security: Security vulnerability analysis
- performance: Performance and complexity analysis
- documentation: Documentation generation
- architecture: Architecture and dependency analysis
- onboarding: Codebase onboarding and navigation
- refactoring: Refactoring assistance and dead code detection
- compliance: Compliance and standards checking
- code_review: Code review assistance
- tech_debt: Technical debt quantification
- cross_repo: Cross-repository impact analysis
- debugging: Debugging support (elog, ereport, assertions, traces)
"""

# Import all scenario workflows
from .security import security_workflow
from .performance import performance_workflow
# Unified refactoring workflow with mode parameter + backward-compatible aliases
from .refactoring import (
    refactoring_workflow,
    large_scale_refactoring_workflow,  # Alias: refactoring_workflow(mode='large_scale')
    mass_refactoring_workflow,          # Alias: refactoring_workflow(mode='mass_migration')
)
from .onboarding import onboarding_workflow
from .documentation import documentation_workflow
from .feature_dev import feature_dev_workflow
from .test_coverage import test_coverage_workflow
from .code_review import code_review_workflow
from .compliance import compliance_workflow
# security_incident_workflow is now an alias in security.py
from .security import security_incident_workflow
from .cross_repo import cross_repo_workflow
from .architecture import architecture_workflow
from .tech_debt import tech_debt_workflow
from .debugging import debugging_workflow

__all__ = [
    'security_workflow',
    'performance_workflow',
    'refactoring_workflow',
    'onboarding_workflow',
    'documentation_workflow',
    'feature_dev_workflow',
    'test_coverage_workflow',
    'code_review_workflow',
    'compliance_workflow',
    'security_incident_workflow',
    'cross_repo_workflow',
    'large_scale_refactoring_workflow',
    'architecture_workflow',
    'tech_debt_workflow',
    'mass_refactoring_workflow',
    'debugging_workflow',
]
