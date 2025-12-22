"""
JSON Formatter for Patch Review Output.

Formats review verdicts as JSON for machine consumption,
API responses, and data persistence.
"""

import json
import logging
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from ..models import (
    ReviewVerdict,
    Finding,
    Severity,
    Recommendation,
    FindingCategory,
)

logger = logging.getLogger(__name__)


class ReviewJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for review data types."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, datetime):
            return obj.isoformat()
        if is_dataclass(obj):
            return asdict(obj)
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)


class JSONFormatter:
    """
    Formats review verdicts as JSON.

    Supports multiple output modes:
    - Full: Complete review with all details
    - Summary: High-level overview only
    - Findings: Just the findings list
    - API: Structured for API responses
    """

    def __init__(self, indent: int = 2, sort_keys: bool = False):
        """
        Initialize the JSON formatter.

        Args:
            indent: JSON indentation level
            sort_keys: Whether to sort keys alphabetically
        """
        self.indent = indent
        self.sort_keys = sort_keys

    def format_full(self, verdict: ReviewVerdict) -> str:
        """
        Format complete review verdict as JSON.

        Args:
            verdict: The review verdict

        Returns:
            JSON string with full review details
        """
        data = self._verdict_to_dict(verdict)
        return json.dumps(
            data,
            cls=ReviewJSONEncoder,
            indent=self.indent,
            sort_keys=self.sort_keys
        )

    def format_summary(self, verdict: ReviewVerdict) -> str:
        """
        Format summary of review verdict.

        Args:
            verdict: The review verdict

        Returns:
            JSON string with summary only
        """
        data = {
            "patch_id": verdict.patch_id,
            "overall_score": verdict.overall_score,
            "recommendation": verdict.recommendation.value,
            "scores": {
                "security": verdict.security.score,
                "performance": verdict.performance.score,
                "error": verdict.error.score,
                "architecture": verdict.architecture.score
            },
            "finding_counts": {
                "critical": verdict.critical_count,
                "high": verdict.high_count,
                "medium": verdict.medium_count,
                "low": verdict.low_count,
                "total": len(verdict.all_findings)
            },
            "key_metrics": {
                "blast_radius_score": verdict.blast_radius_score,
                "breaking_changes": getattr(verdict.architecture, 'breaking_changes', 0),
                "new_vulnerabilities": len([f for f in verdict.security.findings if getattr(f, 'is_new', True)]),
                "hot_paths_affected": getattr(verdict.performance, 'hot_paths_affected', 0)
            },
            "review_time_seconds": verdict.review_time_seconds,
            "reviewed_at": verdict.reviewed_at.isoformat() if verdict.reviewed_at else None
        }

        return json.dumps(
            data,
            indent=self.indent,
            sort_keys=self.sort_keys
        )

    def format_findings(
        self,
        verdict: ReviewVerdict,
        min_severity: Optional[Severity] = None,
        category: Optional[FindingCategory] = None
    ) -> str:
        """
        Format findings list as JSON.

        Args:
            verdict: The review verdict
            min_severity: Minimum severity to include
            category: Filter by category

        Returns:
            JSON string with findings
        """
        findings = verdict.all_findings

        # Filter by severity
        if min_severity:
            severity_order = {
                Severity.CRITICAL: 0,
                Severity.HIGH: 1,
                Severity.MEDIUM: 2,
                Severity.LOW: 3,
                Severity.INFO: 4
            }
            min_level = severity_order.get(min_severity, 4)
            findings = [
                f for f in findings
                if severity_order.get(f.severity, 5) <= min_level
            ]

        # Filter by category
        if category:
            findings = [f for f in findings if f.category == category]

        data = {
            "patch_id": verdict.patch_id,
            "total_findings": len(findings),
            "findings": [self._finding_to_dict(f) for f in findings]
        }

        return json.dumps(
            data,
            cls=ReviewJSONEncoder,
            indent=self.indent,
            sort_keys=self.sort_keys
        )

    def format_api_response(
        self,
        verdict: ReviewVerdict,
        include_code_snippets: bool = True
    ) -> str:
        """
        Format for API response.

        Args:
            verdict: The review verdict
            include_code_snippets: Whether to include code in response

        Returns:
            JSON string structured for API
        """
        # Build findings list
        findings_data = []
        for finding in verdict.all_findings:
            finding_dict = {
                "id": hash(f"{finding.location}:{finding.title}"),
                "category": finding.category.value,
                "severity": finding.severity.value,
                "title": finding.title,
                "description": finding.description,
                "location": finding.location,
                "recommendation": finding.recommendation,
                "confidence": finding.confidence,
                "is_new": finding.is_new
            }
            if include_code_snippets and finding.code_snippet:
                finding_dict["code_snippet"] = finding.code_snippet
            if finding.cwe_id:
                finding_dict["cwe_id"] = finding.cwe_id

            findings_data.append(finding_dict)

        data = {
            "success": True,
            "data": {
                "patch_id": verdict.patch_id,
                "verdict": {
                    "overall_score": verdict.overall_score,
                    "recommendation": verdict.recommendation.value,
                    "can_merge": verdict.recommendation in [Recommendation.APPROVE, Recommendation.COMMENT]
                },
                "scores": {
                    "security": verdict.security.score,
                    "performance": verdict.performance.score,
                    "error": verdict.error.score,
                    "architecture": verdict.architecture.score
                },
                "findings": findings_data,
                "statistics": {
                    "critical_count": verdict.critical_count,
                    "high_count": verdict.high_count,
                    "medium_count": verdict.medium_count,
                    "low_count": verdict.low_count,
                    "total_findings": len(verdict.all_findings)
                },
                "metadata": {
                    "review_time_seconds": verdict.review_time_seconds,
                    "reviewed_at": verdict.reviewed_at.isoformat() if verdict.reviewed_at else None
                }
            }
        }

        return json.dumps(
            data,
            indent=self.indent,
            sort_keys=self.sort_keys
        )

    def format_webhook_payload(
        self,
        verdict: ReviewVerdict,
        event_type: str = "review.completed"
    ) -> str:
        """
        Format for webhook payload.

        Args:
            verdict: The review verdict
            event_type: Type of webhook event

        Returns:
            JSON string for webhook
        """
        data = {
            "event": event_type,
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "patch_id": verdict.patch_id,
                "recommendation": verdict.recommendation.value,
                "overall_score": verdict.overall_score,
                "blocking_issues": verdict.critical_count + verdict.high_count,
                "requires_action": verdict.recommendation in [
                    Recommendation.BLOCK,
                    Recommendation.REQUEST_CHANGES
                ],
                "summary": verdict.summary[:500] if verdict.summary else None
            }
        }

        return json.dumps(data, indent=self.indent)

    def _verdict_to_dict(self, verdict: ReviewVerdict) -> Dict[str, Any]:
        """Convert verdict to dictionary."""
        return {
            "patch_id": verdict.patch_id,
            "overall_score": verdict.overall_score,
            "recommendation": verdict.recommendation.value,
            "security": self._category_verdict_to_dict(verdict.security, "security"),
            "performance": self._category_verdict_to_dict(verdict.performance, "performance"),
            "error": self._category_verdict_to_dict(verdict.error, "error"),
            "architecture": self._category_verdict_to_dict(verdict.architecture, "architecture"),
            "all_findings": [self._finding_to_dict(f) for f in verdict.all_findings],
            "finding_counts": {
                "critical": verdict.critical_count,
                "high": verdict.high_count,
                "medium": verdict.medium_count,
                "low": verdict.low_count
            },
            "blast_radius_score": verdict.blast_radius_score,
            "review_time_seconds": verdict.review_time_seconds,
            "summary": verdict.summary,
            "reviewed_at": verdict.reviewed_at.isoformat() if verdict.reviewed_at else None
        }

    def _category_verdict_to_dict(self, verdict: Any, category: str) -> Dict[str, Any]:
        """Convert category verdict to dictionary."""
        base = {
            "score": verdict.score,
            "critical_count": getattr(verdict, 'critical_count', 0),
            "high_count": getattr(verdict, 'high_count', 0),
            "medium_count": getattr(verdict, 'medium_count', 0),
            "low_count": getattr(verdict, 'low_count', 0),
            "findings_count": len(verdict.findings)
        }

        # Add category-specific fields
        if category == "security":
            base.update({
                "new_vulnerabilities": len([f for f in verdict.findings if getattr(f, 'is_new', True)]),
                "cwe_ids": getattr(verdict, 'cwe_ids', []),
                "taint_paths_count": len(getattr(verdict, 'taint_paths', []))
            })
        elif category == "performance":
            base.update({
                "hot_paths_affected": getattr(verdict, 'hot_paths_affected', 0),
                "total_complexity_increase": getattr(verdict, 'total_complexity_increase', 0),
                "new_loops_count": len(getattr(verdict, 'new_loops', [])),
                "estimated_impact": getattr(verdict, 'estimated_impact', 'unknown')
            })
        elif category == "error":
            base.update({
                "null_safety_issues": len(getattr(verdict, 'null_safety_issues', [])),
                "error_handling_issues": len(getattr(verdict, 'error_handling_issues', [])),
                "resource_leaks": len(getattr(verdict, 'resource_leaks', [])),
                "error_probability": getattr(verdict, 'error_probability', 0.0)
            })
        elif category == "architecture":
            base.update({
                "breaking_changes": getattr(verdict, 'breaking_changes', 0),
                "circular_dependencies": getattr(verdict, 'circular_dependencies', 0),
                "layer_violations": len(getattr(verdict, 'layer_violations', [])),
                "blast_radius_score": getattr(verdict, 'blast_radius_score', 100.0),
                "new_imports_count": len(getattr(verdict, 'new_imports', []))
            })

        return base

    def _finding_to_dict(self, finding: Finding) -> Dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            "category": finding.category.value,
            "severity": finding.severity.value,
            "title": finding.title,
            "description": finding.description,
            "location": finding.location,
            "code_snippet": finding.code_snippet,
            "recommendation": finding.recommendation,
            "confidence": finding.confidence,
            "pattern_id": finding.pattern_id,
            "cwe_id": finding.cwe_id,
            "is_new": finding.is_new
        }
