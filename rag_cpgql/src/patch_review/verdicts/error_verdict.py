"""
Error Verdict Generator for Patch Review System.

Analyzes patch changes for potential runtime errors, exceptions,
and reliability issues.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum

import duckdb

from ..models import (
    PatchContext,
    DeltaCPG,
    Finding,
    Severity,
    ErrorVerdict,
    FindingCategory,
)
from ..analyzers import (
    PatchControlFlowAnalyzer,
    ControlFlowAnalysisResult
)

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Types of potential errors."""
    NULL_POINTER = "null_pointer"
    TYPE_ERROR = "type_error"
    BOUNDS_ERROR = "bounds_error"
    RESOURCE_ERROR = "resource_error"
    CONCURRENCY_ERROR = "concurrency_error"
    LOGIC_ERROR = "logic_error"
    EXCEPTION_HANDLING = "exception_handling"
    ASSERTION = "assertion"


@dataclass
class ErrorPattern:
    """An error pattern to check for."""
    name: str
    description: str
    error_type: ErrorType
    severity: Severity
    pattern: str  # Regex pattern
    recommendation: str
    confidence: float = 0.8


class ErrorVerdictGenerator:
    """
    Generates error verdicts for patch changes.

    Analyzes:
    - Null/undefined reference risks
    - Type safety issues
    - Exception handling gaps
    - Resource management errors
    - Concurrency issues
    - Logic errors
    """

    ERROR_PATTERNS: List[ErrorPattern] = [
        # Null/Undefined Reference
        ErrorPattern(
            name="Unchecked Optional Access",
            description="Accessing optional/nullable value without null check",
            error_type=ErrorType.NULL_POINTER,
            severity=Severity.HIGH,
            pattern=r'(?:\.get\([^)]+\)|Optional\[[^]]+\])\.(?!is_none|is_some|unwrap_or)',
            recommendation="Add null check or use safe accessor (get_or, unwrap_or)",
            confidence=0.70
        ),
        ErrorPattern(
            name="Dict Access Without Check",
            description="Accessing dict key that may not exist",
            error_type=ErrorType.NULL_POINTER,
            severity=Severity.MEDIUM,
            pattern=r'\[\s*["\'][^"\']+["\']\s*\](?!\s*(?:if|=))',
            recommendation="Use .get() with default or check key existence first",
            confidence=0.60
        ),
        ErrorPattern(
            name="Attribute Access on None",
            description="Potential attribute access on None return value",
            error_type=ErrorType.NULL_POINTER,
            severity=Severity.HIGH,
            pattern=r'(?:find|search|match|get)\([^)]*\)\.(?:group|text|value)',
            recommendation="Check for None before accessing attributes",
            confidence=0.75
        ),

        # Type Errors
        ErrorPattern(
            name="Implicit Type Coercion",
            description="Potentially unsafe type coercion",
            error_type=ErrorType.TYPE_ERROR,
            severity=Severity.MEDIUM,
            pattern=r'(?:int|float|str)\s*\([^)]*(?:input|request|params)',
            recommendation="Add try-except for type conversion or validate first",
            confidence=0.70
        ),
        ErrorPattern(
            name="Mixed Type Operations",
            description="Operations between potentially incompatible types",
            error_type=ErrorType.TYPE_ERROR,
            severity=Severity.LOW,
            pattern=r'\+\s*(?:str\(|["\'])|["\'].*?\+',
            recommendation="Explicitly convert types before concatenation",
            confidence=0.50
        ),

        # Bounds Errors
        ErrorPattern(
            name="Array Index Out of Bounds",
            description="Accessing array with potentially invalid index",
            error_type=ErrorType.BOUNDS_ERROR,
            severity=Severity.HIGH,
            pattern=r'\[\s*(?:-1|\w+\s*[-+]\s*\d+|\w+\s*\*\s*\d+)\s*\]',
            recommendation="Validate index bounds before access",
            confidence=0.65
        ),
        ErrorPattern(
            name="Substring Out of Range",
            description="String slicing with potentially invalid range",
            error_type=ErrorType.BOUNDS_ERROR,
            severity=Severity.MEDIUM,
            pattern=r'\[\s*\d+\s*:\s*(?:\d+|len\([^)]+\)\s*[-+])?\s*\]',
            recommendation="Check string length before slicing",
            confidence=0.55
        ),

        # Resource Errors
        ErrorPattern(
            name="Missing Close",
            description="Resource opened but may not be closed on all paths",
            error_type=ErrorType.RESOURCE_ERROR,
            severity=Severity.MEDIUM,
            pattern=r'=\s*open\([^)]+\)(?!\s*$)',
            recommendation="Use context manager (with statement) for automatic cleanup",
            confidence=0.75
        ),
        ErrorPattern(
            name="Partial Resource Cleanup",
            description="Resource cleanup in try but not in except/finally",
            error_type=ErrorType.RESOURCE_ERROR,
            severity=Severity.HIGH,
            pattern=r'try:\s*\n(?:.*\n)*?.*\.close\(\)(?:.*\n)*?except.*:(?:(?!close).)*$',
            recommendation="Move close() to finally block",
            confidence=0.70
        ),

        # Exception Handling Issues
        ErrorPattern(
            name="Bare Except",
            description="Catching all exceptions without specificity",
            error_type=ErrorType.EXCEPTION_HANDLING,
            severity=Severity.MEDIUM,
            pattern=r'except\s*:(?!\s*#)',
            recommendation="Catch specific exception types",
            confidence=0.90
        ),
        ErrorPattern(
            name="Silent Exception Swallowing",
            description="Exception caught but ignored (pass/...)",
            error_type=ErrorType.EXCEPTION_HANDLING,
            severity=Severity.HIGH,
            pattern=r'except\s+\w+.*:\s*\n\s*(?:pass|\.\.\.)\s*$',
            recommendation="Log the exception or handle it properly",
            confidence=0.85
        ),
        ErrorPattern(
            name="Exception in Exception Handler",
            description="Risky operation in exception handler",
            error_type=ErrorType.EXCEPTION_HANDLING,
            severity=Severity.MEDIUM,
            pattern=r'except\s+\w+.*:\s*\n(?:.*\n)*?.*(?:open|connect|request)',
            recommendation="Wrap handler operations in their own try-except",
            confidence=0.65
        ),
        ErrorPattern(
            name="Catch and Re-raise Without Context",
            description="Raising new exception without chaining",
            error_type=ErrorType.EXCEPTION_HANDLING,
            severity=Severity.LOW,
            pattern=r'except\s+\w+.*:\s*\n(?:.*\n)*?.*raise\s+\w+\([^)]*\)(?!\s+from)',
            recommendation="Use 'raise NewException() from e' to preserve context",
            confidence=0.70
        ),

        # Concurrency Errors
        ErrorPattern(
            name="Race Condition Pattern",
            description="Check-then-act without synchronization",
            error_type=ErrorType.CONCURRENCY_ERROR,
            severity=Severity.HIGH,
            pattern=r'if\s+(?:\w+\.exists|os\.path\.exists|len\(\w+\)).*:\s*\n\s*(?:.*\.(?:delete|remove|write|append))',
            recommendation="Use atomic operations or proper synchronization",
            confidence=0.70
        ),
        ErrorPattern(
            name="Shared State Modification",
            description="Modifying shared state without lock",
            error_type=ErrorType.CONCURRENCY_ERROR,
            severity=Severity.MEDIUM,
            pattern=r'self\.\w+\s*(?:\+=|-=|\*=|=\s*\w+\s*\+)',
            recommendation="Use threading.Lock or thread-safe data structures",
            confidence=0.50
        ),

        # Logic Errors
        ErrorPattern(
            name="Off-by-One Error",
            description="Potential off-by-one in range/index",
            error_type=ErrorType.LOGIC_ERROR,
            severity=Severity.MEDIUM,
            pattern=r'range\s*\(\s*\d+\s*,\s*len\([^)]+\)\s*\)|for\s+\w+\s+in\s+range\s*\(\s*1\s*,',
            recommendation="Verify range bounds carefully",
            confidence=0.55
        ),
        ErrorPattern(
            name="Assignment in Condition",
            description="Assignment used where comparison intended",
            error_type=ErrorType.LOGIC_ERROR,
            severity=Severity.MEDIUM,
            pattern=r'(?:if|while)\s*\([^)]*[^=!<>]=[^=][^)]*\)',
            recommendation="Use == for comparison, not =",
            confidence=0.80
        ),
        ErrorPattern(
            name="Inverted Condition",
            description="Potentially inverted boolean condition",
            error_type=ErrorType.LOGIC_ERROR,
            severity=Severity.LOW,
            pattern=r'if\s+not\s+\w+\s*(?:is\s+not|!=)',
            recommendation="Review double negation logic",
            confidence=0.50
        ),

        # Assertion Issues
        ErrorPattern(
            name="Assert in Production Code",
            description="Using assert for validation (can be disabled)",
            error_type=ErrorType.ASSERTION,
            severity=Severity.MEDIUM,
            pattern=r'assert\s+\w+(?:\s*[!=<>]=|\s+is|\s+in)',
            recommendation="Use explicit if-raise for production validation",
            confidence=0.70
        ),
    ]

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        """
        Initialize the error verdict generator.

        Args:
            conn: DuckDB connection with CPG loaded
        """
        self.conn = conn
        self.control_flow_analyzer = PatchControlFlowAnalyzer(conn)

    def generate_verdict(
        self,
        patch: PatchContext,
        delta_cpg: DeltaCPG,
        control_flow_result: Optional[ControlFlowAnalysisResult] = None
    ) -> ErrorVerdict:
        """
        Generate comprehensive error verdict for the patch.

        Args:
            patch: The patch context
            delta_cpg: Delta CPG with changes
            control_flow_result: Optional pre-computed control flow analysis

        Returns:
            Complete error verdict
        """
        logger.info(f"Generating error verdict for patch {patch.patch_id}")

        findings: List[Finding] = []

        # 1. Pattern-based error detection
        pattern_findings = self._check_error_patterns(patch, delta_cpg)
        findings.extend(pattern_findings)

        # 2. Exception handling analysis
        if control_flow_result is None:
            control_flow_result = self.control_flow_analyzer.analyze_control_flow_changes(
                patch, delta_cpg
            )

        # Add error handling findings
        for change in control_flow_result.error_handling_changes:
            severity = Severity.HIGH if change.coverage_reduction else Severity.MEDIUM
            findings.append(Finding(
                category=FindingCategory.ERROR,
                severity=severity,
                title=f"Error Handling {change.change_type}",
                description=change.description,
                location=change.location,
                recommendation=change.recommendation,
                confidence=0.80
            ))

        # 3. Null safety analysis
        null_findings = self._analyze_null_safety(patch, delta_cpg)
        findings.extend(null_findings)

        # 4. Unreachable code detection
        unreachable_findings = self._detect_unreachable_code(delta_cpg)
        findings.extend(unreachable_findings)

        # 5. Dead code after exceptions
        dead_code_findings = self._detect_dead_exception_code(patch, delta_cpg)
        findings.extend(dead_code_findings)

        # 6. Type safety analysis (basic)
        type_findings = self._analyze_type_safety(patch, delta_cpg)
        findings.extend(type_findings)

        # Calculate error score
        score = self._calculate_error_score(findings)

        # Count by error type
        error_type_counts = self._count_by_error_type(findings)

        # Build issue lists from findings
        null_safety_list = [{"finding": f.title, "location": f.location}
                            for f in findings if 'null' in f.title.lower()]
        resource_leak_list = [{"finding": f.title, "location": f.location}
                              for f in findings if 'resource' in f.title.lower() or 'leak' in f.title.lower()]
        error_handling_list = [{"finding": f.title, "location": f.location}
                               for f in findings if 'exception' in f.title.lower() or 'error' in f.title.lower()]

        verdict = ErrorVerdict(
            findings=findings,
            score=score,
            null_safety_issues=null_safety_list,
            resource_leaks=resource_leak_list,
            error_handling_issues=error_handling_list
        )

        logger.info(
            f"Error verdict: score={score:.2f}, "
            f"null_safety={len(verdict.null_safety_issues)}, "
            f"resource_leaks={len(verdict.resource_leaks)}"
        )

        return verdict

    def _check_error_patterns(
        self,
        patch: PatchContext,
        delta_cpg: DeltaCPG
    ) -> List[Finding]:
        """Check for error patterns in added code."""
        findings: List[Finding] = []

        # Collect added code
        added_code_blocks: List[Tuple[str, int, str]] = []

        for file_diff in patch.files:
            for hunk in file_diff.hunks:
                # Added lines are already contiguous in the hunk
                if hunk.added_lines:
                    added_code_blocks.append((
                        file_diff.path,
                        hunk.new_start,
                        '\n'.join(hunk.added_lines)
                    ))

        # Check patterns
        for pattern in self.ERROR_PATTERNS:
            compiled = re.compile(pattern.pattern, re.IGNORECASE | re.MULTILINE)

            for filepath, line_num, code in added_code_blocks:
                if compiled.search(code):
                    findings.append(Finding(
                        category=FindingCategory.ERROR,
                        severity=pattern.severity,
                        title=pattern.name,
                        description=pattern.description,
                        location=f"{filepath}:{line_num}",
                        code_snippet=code[:200],
                        recommendation=pattern.recommendation,
                        confidence=pattern.confidence,
                        is_new=True
                    ))

        return findings

    def _analyze_null_safety(
        self,
        patch: PatchContext,
        delta_cpg: DeltaCPG
    ) -> List[Finding]:
        """Analyze null/undefined safety issues."""
        findings: List[Finding] = []

        # Look for patterns that indicate null risk
        null_risk_patterns = [
            # Function that may return None followed by attribute access
            (r'(\w+)\s*=\s*\w+\.(?:find|get|search|match)\([^)]*\)\s*\n(?:(?!if\s+\1).)*\1\.',
             "Possible null dereference", Severity.HIGH),
            # List/dict access without existence check
            (r'(\w+)\[([^\]]+)\](?!\s*(?:=|if))',
             "Unguarded collection access", Severity.MEDIUM),
        ]

        for file_diff in patch.files:
            full_added_code = '\n'.join(
                line
                for hunk in file_diff.hunks
                for line in hunk.added_lines
            )

            for pattern, description, severity in null_risk_patterns:
                for match in re.finditer(pattern, full_added_code, re.MULTILINE):
                    findings.append(Finding(
                        id=f"null_{hash(match.group(0))}",
                        category=FindingCategory.ERROR,
                        severity=severity,
                        title="Null Safety Issue",
                        description=description,
                        location=file_diff.path,
                        code_snippet=match.group(0)[:100],
                        recommendation="Add null check before access",
                        confidence=0.65
                    ))

        return findings

    def _detect_unreachable_code(self, delta_cpg: DeltaCPG) -> List[Finding]:
        """Detect unreachable code in added methods."""
        findings: List[Finding] = []

        # Look for code after return/raise/break/continue
        for node in delta_cpg.nodes:
            if node.change_type.value == 'added' and node.code:
                # Check for statements after control flow terminators
                lines = node.code.split('\n')
                in_unreachable = False

                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if in_unreachable and stripped and not stripped.startswith('#'):
                        # Found code after terminator
                        if not stripped.startswith(('except', 'finally', 'else', 'elif')):
                            findings.append(Finding(
                                category=FindingCategory.ERROR,
                                severity=Severity.MEDIUM,
                                title="Unreachable Code",
                                description="Code detected after return/raise statement",
                                location=f"{node.filename}:{(node.line_number or 0) + i}",
                                code_snippet=stripped[:100],
                                recommendation="Remove unreachable code",
                                confidence=0.80
                            ))
                            break

                    if re.match(r'^(return|raise|break|continue)\s', stripped):
                        in_unreachable = True
                    elif stripped.endswith(':'):  # New block resets
                        in_unreachable = False

        return findings

    def _detect_dead_exception_code(
        self,
        patch: PatchContext,
        delta_cpg: DeltaCPG
    ) -> List[Finding]:
        """Detect code after exception-raising calls that never returns."""
        findings: List[Finding] = []

        # Known functions that never return
        never_return = ['sys.exit', 'os._exit', 'exit', 'quit', 'abort']

        for node in delta_cpg.nodes:
            if node.change_type.value == 'added' and node.code:
                for func in never_return:
                    pattern = rf'{func}\s*\([^)]*\)\s*\n(\s*.+)'
                    match = re.search(pattern, node.code)
                    if match:
                        next_line = match.group(1).strip()
                        if next_line and not next_line.startswith('#'):
                            findings.append(Finding(
                                category=FindingCategory.ERROR,
                                severity=Severity.LOW,
                                title="Dead Code After Exit",
                                description=f"Code after {func}() will never execute",
                                location=f"{node.filename}:{node.line_number}",
                                code_snippet=match.group(0)[:150],
                                recommendation="Remove dead code after exit call",
                                confidence=0.90
                            ))

        return findings

    def _analyze_type_safety(
        self,
        patch: PatchContext,
        delta_cpg: DeltaCPG
    ) -> List[Finding]:
        """Analyze type safety issues."""
        findings: List[Finding] = []

        # Patterns indicating type safety issues
        type_patterns = [
            # Comparing different types
            (r'if\s+\w+\s*==\s*["\']|if\s+["\'].*==\s*\w+',
             "String comparison with potential non-string", Severity.LOW),
            # Using + with mixed types
            (r'["\'].*\+\s*\w+|\w+\s*\+\s*["\']',
             "String concatenation with potential type mismatch", Severity.LOW),
        ]

        for node in delta_cpg.nodes:
            if node.change_type.value == 'added' and node.code:
                for pattern, description, severity in type_patterns:
                    if re.search(pattern, node.code):
                        findings.append(Finding(
                            category=FindingCategory.ERROR,
                            severity=severity,
                            title="Type Safety Concern",
                            description=description,
                            location=f"{node.filename}:{node.line_number}",
                            code_snippet=node.code[:100],
                            recommendation="Ensure type consistency",
                            confidence=0.50
                        ))

        return findings

    def _calculate_error_score(self, findings: List[Finding]) -> float:
        """Calculate error score (0-100)."""
        if not findings:
            return 100.0

        severity_weights = {
            Severity.CRITICAL: 25,
            Severity.HIGH: 15,
            Severity.MEDIUM: 7,
            Severity.LOW: 2,
            Severity.INFO: 0.5,
        }

        total_penalty = 0
        for finding in findings:
            weight = severity_weights.get(finding.severity, 1)
            total_penalty += weight * finding.confidence

        score = max(0, 100 - total_penalty)
        return round(score, 2)

    def _count_by_error_type(self, findings: List[Finding]) -> Dict[str, int]:
        """Count findings by error type."""
        counts: Dict[str, int] = {}

        for finding in findings:
            # Infer error type from title
            title_lower = finding.title.lower()

            if 'null' in title_lower or 'undefined' in title_lower:
                error_type = 'null_pointer'
            elif 'exception' in title_lower or 'error handling' in title_lower:
                error_type = 'exception_handling'
            elif 'type' in title_lower:
                error_type = 'type_error'
            elif 'resource' in title_lower or 'close' in title_lower:
                error_type = 'resource_error'
            elif 'race' in title_lower or 'concurrent' in title_lower:
                error_type = 'concurrency_error'
            else:
                error_type = 'logic_error'

            counts[error_type] = counts.get(error_type, 0) + 1

        return counts

    def _get_recommendation(self, score: float, findings: List[Finding]) -> str:
        """Get overall recommendation."""
        critical_count = sum(1 for f in findings if f.severity == Severity.CRITICAL)
        high_count = sum(1 for f in findings if f.severity == Severity.HIGH)

        if critical_count > 0:
            return "BLOCK - Critical error risks detected. Fix before merge."
        elif high_count >= 3:
            return "REQUEST_CHANGES - Multiple high-severity error risks. Requires fixes."
        elif score < 60:
            return "REQUEST_CHANGES - Error score below threshold. Address issues."
        elif score < 80:
            return "COMMENT - Some error risks detected. Consider addressing."
        else:
            return "APPROVE - No significant error risks detected."
