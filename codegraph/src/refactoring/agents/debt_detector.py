"""Technical Debt Detector Agent.

Detects code smells and technical debt using pattern library.
"""
import logging
from typing import Dict, List, Any, Optional

from .models import CodeSmellFinding
from ..refactoring_patterns import (
    RefactoringPattern,
    REFACTORING_PATTERNS,
    CodeSmellSeverity,
    CodeSmellCategory,
    get_patterns_by_category,
)
from ...services.cpg_query_service import CPGQueryService

logger = logging.getLogger(__name__)


class TechnicalDebtDetector:
    """
    Detects code smells and technical debt using pattern library.

    Responsibilities:
    - Execute CPGQL queries from refactoring patterns
    - Identify code smells
    - Calculate debt metrics
    - Rank findings by severity and effort
    """

    def __init__(self, cpg_service: Optional[CPGQueryService] = None):
        self.cpg = cpg_service
        self._own_cpg = cpg_service is None

    def __enter__(self):
        if self._own_cpg:
            self.cpg = CPGQueryService()
            self.cpg.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._own_cpg and self.cpg:
            self.cpg.__exit__(exc_type, exc_val, exc_tb)

    def detect_all_smells(self, limit_per_pattern: int = 30) -> List[CodeSmellFinding]:
        """
        Detect all code smells using all patterns.

        Args:
            limit_per_pattern: Max findings per pattern

        Returns:
            List of code smell findings sorted by severity
        """
        logger.info("Starting comprehensive code smell detection")
        all_findings = []

        for pattern_name, pattern in REFACTORING_PATTERNS.items():
            try:
                findings = self.detect_pattern(pattern, limit_per_pattern)
                all_findings.extend(findings)
                logger.info(f"Pattern {pattern_name}: found {len(findings)} smells")
            except Exception as e:
                logger.error(f"Error detecting pattern {pattern_name}: {e}")

        # Sort by severity (critical first)
        severity_order = {
            CodeSmellSeverity.CRITICAL.value: 0,
            CodeSmellSeverity.HIGH.value: 1,
            CodeSmellSeverity.MEDIUM.value: 2,
            CodeSmellSeverity.LOW.value: 3,
            CodeSmellSeverity.INFO.value: 4,
        }
        all_findings.sort(key=lambda f: severity_order.get(f.severity, 99))

        logger.info(f"Total code smells found: {len(all_findings)}")
        return all_findings

    def detect_pattern(
        self,
        pattern: RefactoringPattern,
        limit: int = 30
    ) -> List[CodeSmellFinding]:
        """
        Detect a specific code smell pattern.

        Args:
            pattern: Refactoring pattern to detect
            limit: Max findings to return

        Returns:
            List of code smell findings
        """
        try:
            # Execute pattern's CPGQL query
            results = self.cpg.execute_query(pattern.cpgql_query)

            findings = []
            for idx, row in enumerate(results[:limit]):
                finding = CodeSmellFinding(
                    finding_id=f"{pattern.id}_{idx:03d}",
                    pattern_id=pattern.id,
                    pattern_name=pattern.name,
                    category=pattern.category.value,
                    severity=pattern.severity.value,
                    method_id=row.get('id', 0),
                    method_name=row.get('method_name', row.get('filename', 'unknown')),
                    filename=row.get('filename', 'unknown'),
                    line_number=row.get('line_number', 0),
                    code_snippet=str(row.get('code', ''))[:200],  # Truncate
                    description=pattern.description,
                    symptoms=pattern.symptoms,
                    refactoring_technique=pattern.refactoring_technique,
                    effort_hours=pattern.effort_estimate,
                    metadata=row
                )
                findings.append(finding)

            return findings

        except Exception as e:
            logger.error(f"Error executing pattern {pattern.id}: {e}")
            return []

    def detect_by_category(
        self,
        category: CodeSmellCategory,
        limit: int = 50
    ) -> List[CodeSmellFinding]:
        """Detect code smells in a specific category."""
        patterns = get_patterns_by_category(category)
        findings = []

        for pattern in patterns:
            pattern_findings = self.detect_pattern(pattern, limit)
            findings.extend(pattern_findings)

        return findings

    def calculate_debt_metrics(self, findings: List[CodeSmellFinding]) -> Dict[str, Any]:
        """
        Calculate technical debt metrics.

        Returns:
            Dictionary with debt metrics
        """
        if not findings:
            return {
                'total_smells': 0,
                'total_effort_hours': 0.0,
                'by_severity': {},
                'by_category': {},
                'debt_ratio': 0.0
            }

        total_effort = sum(f.effort_hours for f in findings)

        by_severity = {}
        for severity in CodeSmellSeverity:
            count = sum(1 for f in findings if f.severity == severity.value)
            if count > 0:
                by_severity[severity.value] = count

        by_category = {}
        for category in CodeSmellCategory:
            count = sum(1 for f in findings if f.category == category.value)
            if count > 0:
                by_category[category.value] = count

        # Simple debt ratio (total effort / estimated codebase size)
        # Assuming ~1000 methods in codebase, 1 hour maintenance per method = 1000 hours
        estimated_codebase_maintenance = 1000.0
        debt_ratio = min(total_effort / estimated_codebase_maintenance, 1.0)

        return {
            'total_smells': len(findings),
            'total_effort_hours': total_effort,
            'by_severity': by_severity,
            'by_category': by_category,
            'debt_ratio': debt_ratio,
            'avg_effort_per_smell': total_effort / len(findings) if findings else 0.0
        }
