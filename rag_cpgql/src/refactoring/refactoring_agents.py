"""
Refactoring Analysis Agents for Enhanced Refactoring Workflow

Week 6, Task 2: Specialized Refactoring Agents
Phase 2: Quality & Security Enhancement

Implements 3 specialized agents:
1. TechnicalDebtDetector - Detect code smells using pattern library
2. ImpactAnalyzer - Analyze change impact and dependencies
3. RefactoringPlanner - Create prioritized refactoring plans
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .refactoring_patterns import (
    RefactoringPattern,
    REFACTORING_PATTERNS,
    CodeSmellSeverity,
    CodeSmellCategory,
    get_critical_patterns,
    get_patterns_by_category,
)
from ..services.cpg_query_service import CPGQueryService

logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class CodeSmellFinding:
    """Represents a detected code smell"""
    finding_id: str
    pattern_id: str
    pattern_name: str
    category: str
    severity: str
    method_id: int
    method_name: str
    filename: str
    line_number: int
    code_snippet: str
    description: str
    symptoms: List[str]
    refactoring_technique: str
    effort_hours: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyInfo:
    """Represents dependency relationships"""
    dependency_id: str
    from_method: str
    from_file: str
    to_method: str
    to_file: str
    dependency_type: str  # "calls", "includes", "data"
    strength: str  # "strong", "medium", "weak"


@dataclass
class ImpactAnalysis:
    """Change impact analysis results"""
    analysis_id: str
    target_method: str
    target_file: str
    direct_dependents: List[str]
    indirect_dependents: List[str]
    affected_files: List[str]
    impact_score: float  # 0.0 to 1.0
    risk_level: str  # "low", "medium", "high"
    estimated_test_effort: float  # hours


@dataclass
class RefactoringTask:
    """A prioritized refactoring task"""
    task_id: str
    finding_id: str
    pattern_name: str
    target_method: str
    target_file: str
    priority: int  # 1-10, higher = more urgent
    effort_hours: float
    impact_score: float
    refactoring_steps: List[str]
    dependencies: List[str]  # Other tasks that should be done first
    estimated_value: float  # Benefit of completing this task


@dataclass
class RefactoringReport:
    """Comprehensive refactoring report"""
    report_id: str
    timestamp: str
    total_smells: int
    by_severity: Dict[str, int]
    by_category: Dict[str, int]
    findings: List[CodeSmellFinding]
    impact_analyses: List[ImpactAnalysis]
    tasks: List[RefactoringTask]
    total_effort_hours: float
    estimated_value: float
    summary: str
    recommendations: List[str]


# ============================================================================
# AGENT 1: TECHNICAL DEBT DETECTOR
# ============================================================================

class TechnicalDebtDetector:
    """
    Detects code smells and technical debt using pattern library

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
        Detect all code smells using all patterns

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

    def detect_pattern(self, pattern: RefactoringPattern, limit: int = 30) -> List[CodeSmellFinding]:
        """
        Detect a specific code smell pattern

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
        """Detect code smells in a specific category"""
        patterns = get_patterns_by_category(category)
        findings = []

        for pattern in patterns:
            pattern_findings = self.detect_pattern(pattern, limit)
            findings.extend(pattern_findings)

        return findings

    def calculate_debt_metrics(self, findings: List[CodeSmellFinding]) -> Dict[str, Any]:
        """
        Calculate technical debt metrics

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


# ============================================================================
# AGENT 1.5: DEAD CODE DETECTOR (Sprint 1 - Scenario 5 Enhancement)
# ============================================================================

@dataclass
class DeadCodeFinding:
    """Represents a detected dead code instance"""
    finding_id: str
    pattern_id: str
    pattern_name: str
    detection_type: str  # 'uncalled', 'deprecated', 'disabled', 'orphan', etc.
    severity: str
    method_id: int
    method_name: str
    filename: str
    line_number: int
    line_count: int
    code_snippet: str
    reason: str
    confidence: float  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class DeadCodeDetector:
    """
    Specialized agent for dead code detection using 13 patterns + WCC analysis.

    Implements comprehensive dead code detection for Scenario 5:
    - Uncalled functions (original DEAD_CODE_001)
    - Deprecated markers (DEAD_CODE_002)
    - Disabled code blocks (#if 0) (DEAD_CODE_003)
    - Unused variables (DEAD_CODE_004)
    - Empty stubs (DEAD_CODE_005)
    - Error-only functions (DEAD_CODE_006)
    - Unreachable code after return (DEAD_CODE_007)
    - Dead assignments (DEAD_CODE_008)
    - Invariant dead code (DEAD_CODE_009)
    - Dead callbacks (DEAD_CODE_010)
    - Single-caller functions (DEAD_CODE_011)
    - Test-only functions (DEAD_CODE_012)
    - Orphan components via WCC analysis (DEAD_CODE_013)

    This is a specialized detector focused solely on dead code, providing
    more thorough detection than the generic TechnicalDebtDetector.
    """

    # Dead code pattern IDs to detect
    DEAD_CODE_PATTERNS = [
        'DEAD_CODE',
        'DEPRECATED_MARKER',
        'DISABLED_CODE_BLOCK',
        'EMPTY_STUB',
        'ERROR_ONLY_FUNCTION',
        'UNREACHABLE_AFTER_RETURN',
        'ORPHAN_COMPONENT',
        # Sprint 2 - 6 new patterns
        'UNUSED_VARIABLE',
        'DEAD_ASSIGNMENT',
        'INVARIANT_DEAD_CODE',
        'DEAD_CALLBACK',
        'SINGLE_CALLER_FUNCTION',
        'TEST_ONLY_FUNCTION',
    ]

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

    def detect_all(self, limit_per_pattern: int = 50) -> List[DeadCodeFinding]:
        """
        Run all dead code detection patterns.

        Returns:
            List of dead code findings sorted by severity and confidence
        """
        logger.info("Starting comprehensive dead code detection")
        all_findings = []

        # Run all dead code patterns from the pattern library
        for pattern_name in self.DEAD_CODE_PATTERNS:
            if pattern_name in REFACTORING_PATTERNS:
                pattern = REFACTORING_PATTERNS[pattern_name]
                try:
                    findings = self._run_pattern(pattern, limit_per_pattern)
                    all_findings.extend(findings)
                    logger.info(f"Pattern {pattern_name}: found {len(findings)} dead code instances")
                except Exception as e:
                    logger.error(f"Error detecting pattern {pattern_name}: {e}")

        # Run WCC-based orphan detection
        try:
            orphan_findings = self._detect_orphan_components()
            all_findings.extend(orphan_findings)
            logger.info(f"WCC analysis: found {len(orphan_findings)} orphan components")
        except Exception as e:
            logger.error(f"Error detecting orphan components: {e}")

        # Sort by severity and confidence
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}
        all_findings.sort(
            key=lambda f: (severity_order.get(f.severity, 99), -f.confidence)
        )

        logger.info(f"Total dead code findings: {len(all_findings)}")
        return all_findings

    def detect_patterns(
        self,
        pattern_names: List[str],
        limit_per_pattern: int = 30
    ) -> List[DeadCodeFinding]:
        """
        Run specific dead code detection patterns by name.

        Phase 3 Enhancement: Intent-based pattern filtering.

        Args:
            pattern_names: List of pattern IDs/names to detect (e.g., ['DEAD_CODE', 'DEPRECATED_MARKER'])
            limit_per_pattern: Max findings per pattern

        Returns:
            List of dead code findings from matched patterns
        """
        logger.info(f"Running targeted dead code detection for patterns: {pattern_names}")
        all_findings = []

        # Run only specified patterns
        for pattern_name in pattern_names:
            if pattern_name in REFACTORING_PATTERNS:
                pattern = REFACTORING_PATTERNS[pattern_name]
                try:
                    findings = self._run_pattern(pattern, limit_per_pattern)
                    all_findings.extend(findings)
                    logger.info(f"Pattern {pattern_name}: found {len(findings)} dead code instances")
                except Exception as e:
                    logger.error(f"Error detecting pattern {pattern_name}: {e}")

        # Add orphan detection if requested
        if 'ORPHAN_COMPONENT' in pattern_names:
            try:
                orphan_findings = self._detect_orphan_components()
                all_findings.extend(orphan_findings)
                logger.info(f"WCC analysis: found {len(orphan_findings)} orphan components")
            except Exception as e:
                logger.error(f"Error detecting orphan components: {e}")

        # Sort by severity and confidence
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}
        all_findings.sort(
            key=lambda f: (severity_order.get(f.severity, 99), -f.confidence)
        )

        logger.info(f"Intent-filtered dead code findings: {len(all_findings)} from {len(pattern_names)} patterns")
        return all_findings

    def _run_pattern(
        self,
        pattern: RefactoringPattern,
        limit: int
    ) -> List[DeadCodeFinding]:
        """Run a single dead code pattern query."""
        try:
            results = self.cpg.execute_query(pattern.cpgql_query)

            findings = []
            for idx, row in enumerate(results[:limit]):
                finding = DeadCodeFinding(
                    finding_id=f"{pattern.id}_{idx:03d}",
                    pattern_id=pattern.id,
                    pattern_name=pattern.name,
                    detection_type=self._pattern_to_detection_type(pattern.id),
                    severity=pattern.severity.value,
                    method_id=row.get('id', 0),
                    method_name=row.get('method_name', row.get('name', 'unknown')),
                    filename=row.get('filename', 'unknown'),
                    line_number=row.get('line_number', 0),
                    line_count=row.get('line_count', 0),
                    code_snippet=str(row.get('code', ''))[:200],
                    reason=self._get_detection_reason(pattern.id, row),
                    confidence=self._calculate_confidence(pattern.id, row),
                    metadata=row
                )
                findings.append(finding)

            return findings
        except Exception as e:
            logger.error(f"Error running pattern {pattern.id}: {e}")
            return []

    def _detect_orphan_components(self) -> List[DeadCodeFinding]:
        """
        Use Weakly Connected Components analysis to find isolated code.

        This uses the call_containment graph to find methods that are not
        reachable from any entry point.
        """
        # WCC-based query to find methods in small isolated components
        wcc_query = """
            WITH RECURSIVE reachable AS (
                -- Base case: entry point functions
                SELECT DISTINCT m.name, m.id, m.filename, m.line_number,
                       (m.line_number_end - m.line_number) AS line_count
                FROM nodes_method m
                WHERE m.name IN ('main', 'PG_init', 'InitPostgres', '_PG_init')
                   OR m.name LIKE '%_handler'
                   OR m.name LIKE '%_hook'
                   OR m.name LIKE '%_startup'
                   OR m.name LIKE '%_init'

                UNION

                -- Recursive case: functions called by reachable functions
                SELECT DISTINCT m.name, m.id, m.filename, m.line_number,
                       (m.line_number_end - m.line_number) AS line_count
                FROM nodes_method m
                JOIN call_containment c ON c.callee_name = m.name
                JOIN reachable r ON c.containing_method_name = r.name
                WHERE m.name NOT LIKE 'test_%'
            )
            SELECT DISTINCT
                m.id,
                m.name AS method_name,
                m.filename,
                m.line_number,
                (m.line_number_end - m.line_number) AS line_count,
                'ORPHAN_WCC' AS detection_type
            FROM nodes_method m
            WHERE m.name NOT IN (SELECT name FROM reachable)
              AND m.name NOT LIKE 'test_%'
              AND m.name NOT LIKE '%_fini'
              AND m.name NOT LIKE '%_cleanup'
              AND (m.line_number_end - m.line_number) > 5
              AND m.line_number_end > 0
            ORDER BY m.filename, m.line_number
            LIMIT 100;
        """

        try:
            results = self.cpg.execute_query(wcc_query)
            findings = []

            for idx, row in enumerate(results):
                finding = DeadCodeFinding(
                    finding_id=f"ORPHAN_WCC_{idx:03d}",
                    pattern_id="DEAD_CODE_WCC",
                    pattern_name="Orphan Component (WCC Analysis)",
                    detection_type="orphan",
                    severity="high",
                    method_id=row.get('id', 0),
                    method_name=row.get('method_name', 'unknown'),
                    filename=row.get('filename', 'unknown'),
                    line_number=row.get('line_number', 0),
                    line_count=row.get('line_count', 0),
                    code_snippet="",
                    reason="Not reachable from any entry point (WCC analysis)",
                    confidence=0.8,  # High confidence for WCC analysis
                    metadata=row
                )
                findings.append(finding)

            return findings
        except Exception as e:
            logger.error(f"Error in WCC orphan detection: {e}")
            return []

    def _pattern_to_detection_type(self, pattern_id: str) -> str:
        """Map pattern ID to detection type."""
        mapping = {
            'DEAD_CODE_001': 'uncalled',
            'DEAD_CODE_002': 'deprecated',
            'DEAD_CODE_003': 'disabled',
            'DEAD_CODE_005': 'stub',
            'DEAD_CODE_006': 'error_only',
            'DEAD_CODE_007': 'unreachable',
            'DEAD_CODE_013': 'orphan',
        }
        return mapping.get(pattern_id, 'unknown')

    def _get_detection_reason(self, pattern_id: str, row: Dict) -> str:
        """Generate human-readable reason for detection."""
        reasons = {
            'DEAD_CODE_001': "Function is never called in the codebase",
            'DEAD_CODE_002': f"Marked as deprecated: {row.get('code', '')[:50]}",
            'DEAD_CODE_003': "Code block disabled via preprocessor (#if 0)",
            'DEAD_CODE_005': "Function has empty body or trivial return",
            'DEAD_CODE_006': "Function only reports errors without logic",
            'DEAD_CODE_007': "Code after return/exit is unreachable",
            'DEAD_CODE_013': "Isolated component with no entry point paths",
        }
        return reasons.get(pattern_id, "Detected as dead code")

    def _calculate_confidence(self, pattern_id: str, row: Dict) -> float:
        """Calculate confidence score for detection."""
        # Base confidence by pattern type
        base_confidence = {
            'DEAD_CODE_001': 0.7,  # Uncalled might be exported/used externally
            'DEAD_CODE_002': 0.95, # Explicit deprecation marker
            'DEAD_CODE_003': 0.99, # #if 0 is definite
            'DEAD_CODE_005': 0.6,  # Empty stubs might be intentional
            'DEAD_CODE_006': 0.5,  # Error handlers might be needed
            'DEAD_CODE_007': 0.9,  # Unreachable is definite
            'DEAD_CODE_013': 0.8,  # Orphan via WCC
        }
        return base_confidence.get(pattern_id, 0.5)

    def detect_by_type(
        self,
        detection_type: str,
        limit: int = 50
    ) -> List[DeadCodeFinding]:
        """Detect specific type of dead code."""
        type_to_pattern = {
            'uncalled': 'DEAD_CODE',
            'deprecated': 'DEPRECATED_MARKER',
            'disabled': 'DISABLED_CODE_BLOCK',
            'stub': 'EMPTY_STUB',
            'error_only': 'ERROR_ONLY_FUNCTION',
            'unreachable': 'UNREACHABLE_AFTER_RETURN',
            'orphan': 'ORPHAN_COMPONENT',
        }

        pattern_name = type_to_pattern.get(detection_type)
        if pattern_name and pattern_name in REFACTORING_PATTERNS:
            pattern = REFACTORING_PATTERNS[pattern_name]
            return self._run_pattern(pattern, limit)

        return []

    def get_summary(self, findings: List[DeadCodeFinding]) -> Dict[str, Any]:
        """Generate summary statistics for dead code findings."""
        if not findings:
            return {
                'total_findings': 0,
                'total_lines': 0,
                'by_type': {},
                'by_severity': {},
                'by_file': {}
            }

        by_type = {}
        by_severity = {}
        by_file = {}

        for finding in findings:
            # By detection type
            by_type[finding.detection_type] = by_type.get(finding.detection_type, 0) + 1

            # By severity
            by_severity[finding.severity] = by_severity.get(finding.severity, 0) + 1

            # By file
            by_file[finding.filename] = by_file.get(finding.filename, 0) + 1

        total_lines = sum(f.line_count for f in findings if f.line_count > 0)

        return {
            'total_findings': len(findings),
            'total_lines': total_lines,
            'by_type': by_type,
            'by_severity': by_severity,
            'by_file': by_file,
            'avg_confidence': sum(f.confidence for f in findings) / len(findings)
        }


# ============================================================================
# AGENT 2: IMPACT ANALYZER
# ============================================================================

class ImpactAnalyzer:
    """
    Analyzes change impact and dependencies

    Responsibilities:
    - Find method dependencies (callers and callees)
    - Calculate impact scores for changes
    - Identify affected files and modules
    - Assess refactoring risk
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

    def analyze_method_impact(
        self,
        method_name: str,
        filename: Optional[str] = None
    ) -> ImpactAnalysis:
        """
        Analyze the impact of changing a specific method

        Args:
            method_name: Method to analyze
            filename: Optional file filter

        Returns:
            Impact analysis results
        """
        # Find direct callers using call_containment table
        direct_query = """
            SELECT DISTINCT
                c.containing_method_id AS id,
                c.containing_method_name AS caller_name,
                c.filename AS caller_file
            FROM call_containment c
            WHERE c.callee_name = ?
            LIMIT 50;
        """

        try:
            direct_results = self.cpg.execute_query(direct_query, (method_name,))
            direct_dependents = [r['caller_name'] for r in direct_results]
            affected_files = list(set(r['caller_file'] for r in direct_results))

            # Estimate indirect dependents (callers of callers)
            indirect_dependents = []
            for caller in direct_dependents[:5]:  # Limit to avoid explosion
                indirect_query = """
                    SELECT DISTINCT c.containing_method_name AS name
                    FROM call_containment c
                    WHERE c.callee_name = ?
                    LIMIT 10;
                """
                indirect_results = self.cpg.execute_query(indirect_query, (caller,))
                indirect_dependents.extend([r['name'] for r in indirect_results])

            # Calculate impact score based on dependency count
            impact_score = min(
                (len(direct_dependents) * 0.1 + len(indirect_dependents) * 0.05),
                1.0
            )

            # Determine risk level
            if impact_score > 0.7 or len(direct_dependents) > 20:
                risk_level = "high"
            elif impact_score > 0.4 or len(direct_dependents) > 10:
                risk_level = "medium"
            else:
                risk_level = "low"

            # Estimate test effort (proportional to dependents)
            estimated_test_effort = len(direct_dependents) * 0.25 + len(indirect_dependents) * 0.1

            analysis = ImpactAnalysis(
                analysis_id=f"IMPACT_{method_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                target_method=method_name,
                target_file=filename or "unknown",
                direct_dependents=direct_dependents,
                indirect_dependents=list(set(indirect_dependents)),
                affected_files=affected_files,
                impact_score=impact_score,
                risk_level=risk_level,
                estimated_test_effort=estimated_test_effort
            )

            logger.info(f"Impact analysis for {method_name}: {len(direct_dependents)} direct dependents, risk={risk_level}")
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing impact for {method_name}: {e}")
            return ImpactAnalysis(
                analysis_id=f"IMPACT_{method_name}_ERROR",
                target_method=method_name,
                target_file=filename or "unknown",
                direct_dependents=[],
                indirect_dependents=[],
                affected_files=[],
                impact_score=0.0,
                risk_level="unknown",
                estimated_test_effort=0.0
            )

    def analyze_bulk_impact(
        self,
        findings: List[CodeSmellFinding],
        limit: int = 20
    ) -> List[ImpactAnalysis]:
        """
        Analyze impact for multiple findings

        Args:
            findings: Code smell findings to analyze
            limit: Max analyses to perform

        Returns:
            List of impact analyses
        """
        analyses = []

        for finding in findings[:limit]:
            analysis = self.analyze_method_impact(
                finding.method_name,
                finding.filename
            )
            analyses.append(analysis)

        logger.info(f"Analyzed impact for {len(analyses)} findings")
        return analyses

    def find_dependencies(
        self,
        method_name: str,
        depth: int = 2
    ) -> List[DependencyInfo]:
        """
        Find dependencies for a method (both callers and callees)

        Args:
            method_name: Method to analyze
            depth: Dependency depth (1=direct, 2=include indirect)

        Returns:
            List of dependency relationships
        """
        dependencies = []

        # Find what this method calls using call_containment
        callees_query = """
            SELECT DISTINCT
                c.containing_method_name AS from_method,
                c.filename AS from_file,
                c.callee_name AS to_method,
                'calls' AS dep_type
            FROM call_containment c
            WHERE c.containing_method_name = ?
            LIMIT 30;
        """

        try:
            callees = self.cpg.execute_query(callees_query, (method_name,))

            for idx, callee in enumerate(callees):
                dep = DependencyInfo(
                    dependency_id=f"DEP_{idx:03d}",
                    from_method=callee['from_method'],
                    from_file=callee['from_file'],
                    to_method=callee['to_method'],
                    to_file="unknown",
                    dependency_type="calls",
                    strength="medium"
                )
                dependencies.append(dep)

            logger.info(f"Found {len(dependencies)} dependencies for {method_name}")
            return dependencies

        except Exception as e:
            logger.error(f"Error finding dependencies for {method_name}: {e}")
            return []


# ============================================================================
# AGENT 3: REFACTORING PLANNER
# ============================================================================

class RefactoringPlanner:
    """
    Creates prioritized refactoring plans

    Responsibilities:
    - Prioritize code smells by value and effort
    - Consider change impact and risk
    - Generate actionable refactoring tasks
    - Estimate ROI for refactorings
    """

    def create_refactoring_plan(
        self,
        findings: List[CodeSmellFinding],
        impact_analyses: List[ImpactAnalysis]
    ) -> List[RefactoringTask]:
        """
        Create prioritized refactoring plan

        Args:
            findings: Code smell findings
            impact_analyses: Impact analyses for findings

        Returns:
            Prioritized list of refactoring tasks
        """
        tasks = []

        # Create impact map for quick lookup
        impact_map = {ia.target_method: ia for ia in impact_analyses}

        for finding in findings:
            impact = impact_map.get(finding.method_name)

            # Calculate priority (1-10, higher = more urgent)
            priority = self._calculate_priority(finding, impact)

            # Calculate estimated value
            value = self._calculate_value(finding, impact)

            # Parse refactoring steps
            steps = self._parse_refactoring_steps(finding.refactoring_technique)

            task = RefactoringTask(
                task_id=finding.finding_id.replace('_', '_TASK_'),
                finding_id=finding.finding_id,
                pattern_name=finding.pattern_name,
                target_method=finding.method_name,
                target_file=finding.filename,
                priority=priority,
                effort_hours=finding.effort_hours,
                impact_score=impact.impact_score if impact else 0.0,
                refactoring_steps=steps,
                dependencies=[],
                estimated_value=value
            )
            tasks.append(task)

        # Sort by priority (highest first), then by ROI (value/effort)
        tasks.sort(
            key=lambda t: (t.priority, t.estimated_value / max(t.effort_hours, 0.1)),
            reverse=True
        )

        logger.info(f"Created refactoring plan with {len(tasks)} tasks")
        return tasks

    def _calculate_priority(
        self,
        finding: CodeSmellFinding,
        impact: Optional[ImpactAnalysis]
    ) -> int:
        """Calculate refactoring priority (1-10)"""
        # Base priority on severity
        severity_scores = {
            'critical': 10,
            'high': 7,
            'medium': 4,
            'low': 2,
            'info': 1
        }

        base_priority = severity_scores.get(finding.severity, 5)

        # Adjust based on impact
        if impact:
            if impact.risk_level == 'low':
                # Low risk = easier to fix = higher priority
                base_priority = min(base_priority + 1, 10)
            elif impact.risk_level == 'high':
                # High risk = more careful = slightly lower priority
                base_priority = max(base_priority - 1, 1)

        # Boost bloaters (they affect many other smells)
        if finding.category == 'bloaters':
            base_priority = min(base_priority + 2, 10)

        return base_priority

    def _calculate_value(
        self,
        finding: CodeSmellFinding,
        impact: Optional[ImpactAnalysis]
    ) -> float:
        """
        Calculate estimated value of fixing this smell

        Value considers:
        - Severity (higher = more value)
        - Impact (affects more code = more value)
        - Effort (lower effort = better ROI)
        """
        severity_values = {
            'critical': 10.0,
            'high': 7.0,
            'medium': 4.0,
            'low': 2.0,
            'info': 1.0
        }

        base_value = severity_values.get(finding.severity, 5.0)

        # Multiply by impact (affects more code = more valuable to fix)
        if impact:
            impact_multiplier = 1.0 + impact.impact_score
            base_value *= impact_multiplier

        # Category bonuses
        if finding.category in ['bloaters', 'complexity']:
            base_value *= 1.5  # High-value categories

        return base_value

    def _parse_refactoring_steps(self, technique_text: str) -> List[str]:
        """Parse refactoring technique into discrete steps"""
        steps = []
        for line in technique_text.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                # Remove numbering/bullets
                clean = line.lstrip('0123456789.-) ')
                if clean:
                    steps.append(clean)
        return steps

    def generate_report(
        self,
        findings: List[CodeSmellFinding],
        impact_analyses: List[ImpactAnalysis],
        tasks: List[RefactoringTask]
    ) -> RefactoringReport:
        """
        Generate comprehensive refactoring report

        Args:
            findings: Code smell findings
            impact_analyses: Impact analyses
            tasks: Refactoring tasks

        Returns:
            Comprehensive refactoring report
        """
        # Calculate statistics
        by_severity = {}
        for sev in CodeSmellSeverity:
            count = sum(1 for f in findings if f.severity == sev.value)
            if count > 0:
                by_severity[sev.value] = count

        by_category = {}
        for cat in CodeSmellCategory:
            count = sum(1 for f in findings if f.category == cat.value)
            if count > 0:
                by_category[cat.value] = count

        total_effort = sum(t.effort_hours for t in tasks)
        total_value = sum(t.estimated_value for t in tasks)

        # Generate summary
        summary = self._generate_summary(findings, tasks, by_severity)

        # Generate recommendations
        recommendations = self._generate_recommendations(findings, tasks)

        report = RefactoringReport(
            report_id=f"REFACTOR_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            total_smells=len(findings),
            by_severity=by_severity,
            by_category=by_category,
            findings=findings,
            impact_analyses=impact_analyses,
            tasks=tasks,
            total_effort_hours=total_effort,
            estimated_value=total_value,
            summary=summary,
            recommendations=recommendations
        )

        logger.info(f"Generated refactoring report {report.report_id}")
        return report

    def _generate_summary(
        self,
        findings: List[CodeSmellFinding],
        tasks: List[RefactoringTask],
        by_severity: Dict[str, int]
    ) -> str:
        """Generate executive summary"""
        critical = by_severity.get('critical', 0)
        high = by_severity.get('high', 0)
        total = len(findings)

        summary_parts = [
            f"Code quality analysis identified {total} code smells."
        ]

        if critical > 0:
            summary_parts.append(
                f"⚠️ {critical} CRITICAL issues severely impact maintainability."
            )

        if high > 0:
            summary_parts.append(
                f"{high} HIGH severity issues should be addressed soon."
            )

        if tasks:
            total_effort = sum(t.effort_hours for t in tasks)
            summary_parts.append(
                f"Estimated {total_effort:.1f} hours to address all issues."
            )

        return " ".join(summary_parts)

    def _generate_recommendations(
        self,
        findings: List[CodeSmellFinding],
        tasks: List[RefactoringTask]
    ) -> List[str]:
        """Generate prioritized recommendations"""
        recommendations = []

        # Identify most common categories
        category_counts = {}
        for finding in findings:
            category_counts[finding.category] = category_counts.get(finding.category, 0) + 1

        # Priority 1: Top priority tasks
        if tasks:
            high_priority = [t for t in tasks if t.priority >= 7]
            if high_priority:
                recommendations.append(
                    f"Start with {len(high_priority)} high-priority refactorings "
                    f"(estimated {sum(t.effort_hours for t in high_priority):.1f} hours)"
                )

        # Priority 2: Most common category
        if category_counts:
            top_category = max(category_counts.items(), key=lambda x: x[1])
            recommendations.append(
                f"Focus on {top_category[0]} ({top_category[1]} instances) "
                f"for systematic improvement"
            )

        # Priority 3: Low-hanging fruit
        quick_wins = [t for t in tasks if t.effort_hours <= 1.0]
        if quick_wins:
            recommendations.append(
                f"Quick wins: {len(quick_wins)} refactorings can be done in <1 hour each"
            )

        # Priority 4: General advice
        recommendations.append(
            "Refactor incrementally: tackle 1-2 smells per sprint"
        )
        recommendations.append(
            "Add tests before refactoring to ensure behavior preservation"
        )

        return recommendations


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def run_complete_refactoring_analysis(
    limit_per_pattern: int = 30
) -> Tuple[RefactoringReport, List[RefactoringTask]]:
    """
    Run complete refactoring analysis using all agents

    Returns:
        (RefactoringReport, List[RefactoringTask])
    """
    logger.info("Starting complete refactoring analysis")

    with CPGQueryService() as cpg:
        # Agent 1: Detect code smells
        detector = TechnicalDebtDetector(cpg)
        findings = detector.detect_all_smells(limit_per_pattern)

        # Agent 2: Analyze impact
        analyzer = ImpactAnalyzer(cpg)
        impact_analyses = analyzer.analyze_bulk_impact(findings, limit=20)

        # Agent 3: Create refactoring plan
        planner = RefactoringPlanner()
        tasks = planner.create_refactoring_plan(findings, impact_analyses)
        report = planner.generate_report(findings, impact_analyses, tasks)

    logger.info("Complete refactoring analysis finished")
    return report, tasks


if __name__ == "__main__":
    # Test the agents
    print("Testing Refactoring Agents...")
    print("=" * 60)

    try:
        report, tasks = run_complete_refactoring_analysis(limit_per_pattern=5)

        print(f"\n📊 Refactoring Report: {report.report_id}")
        print(f"Total Code Smells: {report.total_smells}")
        print(f"  Critical: {report.by_severity.get('critical', 0)}")
        print(f"  High: {report.by_severity.get('high', 0)}")
        print(f"  Medium: {report.by_severity.get('medium', 0)}")
        print(f"  Low: {report.by_severity.get('low', 0)}")

        print(f"\n🎯 Refactoring Tasks: {len(tasks)}")
        print(f"Total Effort: {report.total_effort_hours:.1f} hours")
        print(f"Estimated Value: {report.estimated_value:.1f}")

        if tasks:
            print(f"\n📝 Top 3 Priority Tasks:")
            for task in tasks[:3]:
                print(f"  - {task.pattern_name} in {task.target_file}")
                print(f"    Priority: {task.priority}, Effort: {task.effort_hours}h")

        print(f"\n✅ Recommendations:")
        for idx, rec in enumerate(report.recommendations[:3], 1):
            print(f"  {idx}. {rec}")

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
