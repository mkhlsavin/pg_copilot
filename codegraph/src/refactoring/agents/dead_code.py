"""Dead Code Detector Agent.

Specialized agent for dead code detection using patterns + WCC analysis.
"""
import logging
from typing import Dict, List, Any, Optional

from .models import DeadCodeFinding
from ..refactoring_patterns import RefactoringPattern, REFACTORING_PATTERNS
from ...services.cpg_query_service import CPGQueryService

logger = logging.getLogger(__name__)


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
                    logger.info(
                        f"Pattern {pattern_name}: found {len(findings)} dead code instances"
                    )
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
            pattern_names: List of pattern IDs/names to detect
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
                    logger.info(
                        f"Pattern {pattern_name}: found {len(findings)} dead code instances"
                    )
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

        logger.info(
            f"Intent-filtered dead code findings: {len(all_findings)} "
            f"from {len(pattern_names)} patterns"
        )
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
            'DEAD_CODE_002': 0.95,  # Explicit deprecation marker
            'DEAD_CODE_003': 0.99,  # #if 0 is definite
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
            by_type[finding.detection_type] = (
                by_type.get(finding.detection_type, 0) + 1
            )

            # By severity
            by_severity[finding.severity] = (
                by_severity.get(finding.severity, 0) + 1
            )

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
