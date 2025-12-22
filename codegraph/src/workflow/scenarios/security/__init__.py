# ============================================================================
# DOMAIN-AGNOSTIC MODULE
# ============================================================================
# This module MUST NOT contain hardcoded domain-specific code.
# All domain-specific logic should be retrieved from:
#   - src/domains/{domain}/plugin.py via DomainRegistry
#   - src/workflow/_plugin_helpers.py helper functions
#   - src/prompts/prompt_registry.py for prompts
#
# DO NOT add:
#   - Hardcoded function names (pg_*, elog, palloc, etc.)
#   - Hardcoded SQL patterns with domain-specific terms
#   - Inline LLM prompts (use PromptRegistry)
#
# See: docs/AGENT_MIGRATION_GUIDE.md for migration patterns
# ============================================================================
"""
Security Audit Workflow Package.

Enhanced Security Audit with Graph Analysis for comprehensive vulnerability analysis:
1. SecurityScanner - Scan CPG using security patterns
2. CallGraphAnalyzer - Graph Method #2: Call chain context for vulnerabilities
3. DataFlowTracer - Graph Method #3: Real taint flow analysis (source-to-sink paths)
4. VulnerabilityReporter - Generate structured vulnerability report
5. RemediationAdvisor - Provide remediation guidance

This package provides:
- security_workflow: Main security audit workflow
- entry_points_workflow: Entry points and attack surface analysis
- security_incident_workflow: Emergency incident response workflow
- detect_security_intent: Intent detection for query filtering
- detect_hardening_intent: D3FEND hardening intent detection
"""

from src.workflow.scenarios.security.intent_detection import (
    detect_security_intent,
    detect_hardening_intent,
    SECURITY_INTENT_MAP,
)
from src.workflow.scenarios.security.main_workflow import security_workflow
from src.workflow.scenarios.security.entry_points import (
    entry_points_workflow,
    _detect_entry_point_question_type,
)
from src.workflow.scenarios.security.incident import (
    security_incident_workflow,
    _security_incident_workflow,
)


__all__ = [
    # Main workflows
    'security_workflow',
    'entry_points_workflow',
    'security_incident_workflow',
    # Intent detection
    'detect_security_intent',
    'detect_hardening_intent',
    'SECURITY_INTENT_MAP',
    # Internal functions (exported for testing)
    '_detect_entry_point_question_type',
    '_security_incident_workflow',
]
