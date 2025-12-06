"""
Performance Verdict Generator for Patch Review System.

Analyzes patch changes for performance implications and generates
a comprehensive performance verdict.
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
    PerformanceVerdict,
    FindingCategory,
)
from ..analyzers import (
    PatchControlFlowAnalyzer,
    ControlFlowAnalysisResult
)
from ..analyzers import (
    PatchCallGraphAnalyzer,
    CallGraphAnalysisResult
)

logger = logging.getLogger(__name__)


class PerformanceIssueType(Enum):
    """Types of performance issues."""
    ALGORITHMIC = "algorithmic"
    MEMORY = "memory"
    IO = "io"
    NETWORK = "network"
    DATABASE = "database"
    CONCURRENCY = "concurrency"
    RESOURCE_LEAK = "resource_leak"


@dataclass
class PerformancePattern:
    """A performance anti-pattern to check for."""
    name: str
    description: str
    issue_type: PerformanceIssueType
    severity: Severity
    pattern: str  # Regex pattern
    recommendation: str
    estimated_impact: str  # e.g., "O(n²) complexity"
    confidence: float = 0.8


class PerformanceVerdictGenerator:
    """
    Generates performance verdicts for patch changes.

    Analyzes:
    - Algorithmic complexity (nested loops, recursion)
    - Memory usage patterns
    - I/O operations (file, network, database)
    - Resource management
    - Caching opportunities
    """

    PERFORMANCE_PATTERNS: List[PerformancePattern] = [
        # Algorithmic Issues
        PerformancePattern(
            name="Nested Loop O(n²)",
            description="Nested loop detected - potential O(n²) complexity",
            issue_type=PerformanceIssueType.ALGORITHMIC,
            severity=Severity.MEDIUM,
            pattern=r'for\s+\w+\s+in\s+.*:\s*\n\s*for\s+\w+\s+in',
            recommendation="Consider using dict/set for O(1) lookup or optimize algorithm",
            estimated_impact="O(n²) time complexity",
            confidence=0.85
        ),
        PerformancePattern(
            name="Triple Nested Loop",
            description="Triple nested loop - O(n³) complexity",
            issue_type=PerformanceIssueType.ALGORITHMIC,
            severity=Severity.HIGH,
            pattern=r'for\s+\w+\s+in\s+.*:\s*\n\s*for\s+\w+\s+in\s+.*:\s*\n\s*for\s+\w+\s+in',
            recommendation="Restructure algorithm to reduce nesting depth",
            estimated_impact="O(n³) time complexity",
            confidence=0.90
        ),
        PerformancePattern(
            name="List Comprehension in Loop",
            description="Creating new list in each iteration",
            issue_type=PerformanceIssueType.MEMORY,
            severity=Severity.LOW,
            pattern=r'for\s+\w+\s+in\s+.*:\s*\n.*\[.+\s+for\s+',
            recommendation="Move list creation outside loop or use generator",
            estimated_impact="O(n) extra memory allocations",
            confidence=0.70
        ),

        # Database Issues
        PerformancePattern(
            name="N+1 Query Pattern",
            description="Potential N+1 query problem - query in loop",
            issue_type=PerformanceIssueType.DATABASE,
            severity=Severity.HIGH,
            pattern=r'for\s+\w+\s+in\s+.*:\s*\n.*(?:execute|query|find|get|select|fetch)',
            recommendation="Use batch queries or eager loading (JOIN, prefetch_related)",
            estimated_impact="N additional database round trips",
            confidence=0.80
        ),
        PerformancePattern(
            name="SELECT * Query",
            description="SELECT * fetches all columns unnecessarily",
            issue_type=PerformanceIssueType.DATABASE,
            severity=Severity.LOW,
            pattern=r'SELECT\s+\*\s+FROM',
            recommendation="Select only required columns",
            estimated_impact="Unnecessary data transfer",
            confidence=0.75
        ),
        PerformancePattern(
            name="Missing Index Hint",
            description="Query on large table without index consideration",
            issue_type=PerformanceIssueType.DATABASE,
            severity=Severity.MEDIUM,
            pattern=r'WHERE\s+\w+\s*(?:=|LIKE|IN)\s*.*(?:AND|OR)\s+\w+\s*(?:=|LIKE|IN)',
            recommendation="Ensure proper indexes exist for query predicates",
            estimated_impact="Full table scan possible",
            confidence=0.50
        ),

        # I/O Issues
        PerformancePattern(
            name="File Open in Loop",
            description="Opening file in each loop iteration",
            issue_type=PerformanceIssueType.IO,
            severity=Severity.MEDIUM,
            pattern=r'for\s+\w+\s+in\s+.*:\s*\n.*(?:open\(|with\s+open)',
            recommendation="Open file once outside loop or batch operations",
            estimated_impact="N file handle operations",
            confidence=0.85
        ),
        PerformancePattern(
            name="Synchronous File I/O",
            description="Blocking file I/O in async context",
            issue_type=PerformanceIssueType.IO,
            severity=Severity.MEDIUM,
            pattern=r'async\s+def\s+.*:\s*\n.*(?:open\(|\.read\(|\.write\()',
            recommendation="Use aiofiles or run in executor",
            estimated_impact="Blocks event loop",
            confidence=0.75
        ),

        # Network Issues
        PerformancePattern(
            name="HTTP Request in Loop",
            description="Making HTTP request in each iteration",
            issue_type=PerformanceIssueType.NETWORK,
            severity=Severity.HIGH,
            pattern=r'for\s+\w+\s+in\s+.*:\s*\n.*(?:requests\.|urllib|fetch|http)',
            recommendation="Use batch API calls or async requests",
            estimated_impact="N network round trips",
            confidence=0.85
        ),
        PerformancePattern(
            name="Missing Connection Pooling",
            description="Creating new connection for each request",
            issue_type=PerformanceIssueType.NETWORK,
            severity=Severity.MEDIUM,
            pattern=r'(?:requests\.get|requests\.post|urllib\.request\.urlopen)\s*\(',
            recommendation="Use session with connection pooling",
            estimated_impact="Connection overhead per request",
            confidence=0.60
        ),

        # Memory Issues
        PerformancePattern(
            name="Large List in Memory",
            description="Loading potentially large data into list",
            issue_type=PerformanceIssueType.MEMORY,
            severity=Severity.MEDIUM,
            pattern=r'list\(.*(?:readlines|fetchall|find_all)\(\)\)',
            recommendation="Use iterator/generator for large datasets",
            estimated_impact="O(n) memory usage",
            confidence=0.70
        ),
        PerformancePattern(
            name="String Concatenation in Loop",
            description="Inefficient string concatenation in loop",
            issue_type=PerformanceIssueType.MEMORY,
            severity=Severity.LOW,
            pattern=r'for\s+\w+\s+in\s+.*:\s*\n.*\w+\s*\+=\s*["\']|.*\w+\s*=\s*\w+\s*\+\s*["\']',
            recommendation="Use list.join() or io.StringIO",
            estimated_impact="O(n²) string operations",
            confidence=0.80
        ),

        # Resource Leaks
        PerformancePattern(
            name="Resource Not Closed",
            description="Resource opened but not closed with context manager",
            issue_type=PerformanceIssueType.RESOURCE_LEAK,
            severity=Severity.MEDIUM,
            pattern=r'(?<!with\s)open\s*\(.*\)(?!\s*as)',
            recommendation="Use 'with' statement for automatic cleanup",
            estimated_impact="Resource leak potential",
            confidence=0.75
        ),
        PerformancePattern(
            name="Connection Not Closed",
            description="Database connection not properly managed",
            issue_type=PerformanceIssueType.RESOURCE_LEAK,
            severity=Severity.HIGH,
            pattern=r'(?:connect|Connection)\s*\(.*\)(?!\s*as)',
            recommendation="Use context manager or try-finally for connections",
            estimated_impact="Connection pool exhaustion",
            confidence=0.70
        ),

        # Concurrency Issues
        PerformancePattern(
            name="GIL Blocking",
            description="CPU-bound operation in async code",
            issue_type=PerformanceIssueType.CONCURRENCY,
            severity=Severity.MEDIUM,
            pattern=r'async\s+def\s+.*:\s*\n(?:.*\n)*?.*(?:json\.loads|pickle|compress|encrypt)',
            recommendation="Run CPU-bound operations in thread/process pool",
            estimated_impact="Blocks other async tasks",
            confidence=0.65
        ),
        PerformancePattern(
            name="Unbounded Queue",
            description="Queue without size limit",
            issue_type=PerformanceIssueType.MEMORY,
            severity=Severity.LOW,
            pattern=r'Queue\s*\(\s*\)|queue\.Queue\s*\(\s*\)',
            recommendation="Set maxsize to prevent unbounded growth",
            estimated_impact="Potential memory exhaustion",
            confidence=0.60
        ),
    ]

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        """
        Initialize the performance verdict generator.

        Args:
            conn: DuckDB connection with CPG loaded
        """
        self.conn = conn
        self.control_flow_analyzer = PatchControlFlowAnalyzer(conn)
        self.call_graph_analyzer = PatchCallGraphAnalyzer(conn)

    def generate_verdict(
        self,
        patch: PatchContext,
        delta_cpg: DeltaCPG,
        control_flow_result: Optional[ControlFlowAnalysisResult] = None,
        call_graph_result: Optional[CallGraphAnalysisResult] = None
    ) -> PerformanceVerdict:
        """
        Generate comprehensive performance verdict for the patch.

        Args:
            patch: The patch context
            delta_cpg: Delta CPG with changes
            control_flow_result: Optional pre-computed control flow analysis
            call_graph_result: Optional pre-computed call graph analysis

        Returns:
            Complete performance verdict
        """
        logger.info(f"Generating performance verdict for patch {patch.patch_id}")

        findings: List[Finding] = []

        # 1. Pattern-based anti-pattern detection
        pattern_findings = self._check_performance_patterns(patch, delta_cpg)
        findings.extend(pattern_findings)

        # 2. Complexity analysis
        if control_flow_result is None:
            control_flow_result = self.control_flow_analyzer.analyze_control_flow_changes(
                patch, delta_cpg
            )

        # Add complexity findings
        complexity_findings = self._analyze_complexity_changes(control_flow_result)
        findings.extend(complexity_findings)

        # Add loop findings
        for loop in control_flow_result.new_loops:
            severity = Severity.HIGH if loop.is_potentially_infinite else (
                Severity.MEDIUM if loop.has_expensive_body else Severity.LOW
            )
            findings.append(Finding(
                category=FindingCategory.PERFORMANCE,
                severity=severity,
                title=f"New {loop.loop_type.value} Loop",
                description=f"New loop with estimated {loop.estimated_iterations or 'unknown'} iterations",
                location=f"{loop.location}",
                code_snippet=loop.condition[:100] if loop.condition else '',
                recommendation="Ensure loop has proper bounds and efficient body",
                confidence=0.75
            ))

        # 3. Hot path analysis
        if call_graph_result is None:
            call_graph_result = self.call_graph_analyzer.analyze_call_graph_impact(
                patch, delta_cpg
            )

        hot_path_findings = self._analyze_hot_paths(patch, delta_cpg, call_graph_result)
        findings.extend(hot_path_findings)

        # 4. Resource usage analysis
        resource_findings = self._analyze_resource_usage(patch, delta_cpg)
        findings.extend(resource_findings)

        # 5. Caching opportunity analysis
        caching_findings = self._identify_caching_opportunities(patch, delta_cpg)
        findings.extend(caching_findings)

        # Calculate performance score
        score = self._calculate_performance_score(findings, control_flow_result)

        # Get impact summary
        impact_summary = self._get_impact_summary(findings)

        # Calculate complexity delta
        complexity_delta = self._calculate_complexity_delta(control_flow_result)

        verdict = PerformanceVerdict(
            findings=findings,
            score=score,
            complexity_deltas=control_flow_result.complexity_changes if control_flow_result else [],
            hotspot_impacts=[{"method": f.location, "impact": f.title} for f in hot_path_findings],
            new_loops=control_flow_result.new_loops if control_flow_result else [],
            estimated_impact=impact_summary
        )

        logger.info(
            f"Performance verdict: score={score:.2f}, "
            f"complexity_delta={complexity_delta:+d}, hot_paths={verdict.hot_paths_affected}"
        )

        return verdict

    def _check_performance_patterns(
        self,
        patch: PatchContext,
        delta_cpg: DeltaCPG
    ) -> List[Finding]:
        """Check for performance anti-patterns in added code."""
        findings: List[Finding] = []

        # Collect added code blocks
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
        for pattern in self.PERFORMANCE_PATTERNS:
            compiled = re.compile(pattern.pattern, re.IGNORECASE | re.MULTILINE)

            for filepath, line_num, code in added_code_blocks:
                if compiled.search(code):
                    findings.append(Finding(
                        category=FindingCategory.PERFORMANCE,
                        severity=pattern.severity,
                        title=pattern.name,
                        description=f"{pattern.description}. Impact: {pattern.estimated_impact}",
                        location=f"{filepath}:{line_num}",
                        code_snippet=code[:200],
                        recommendation=pattern.recommendation,
                        confidence=pattern.confidence,
                        is_new=True
                    ))

        return findings

    def _analyze_complexity_changes(
        self,
        control_flow_result: ControlFlowAnalysisResult
    ) -> List[Finding]:
        """Analyze complexity changes and generate findings."""
        findings: List[Finding] = []

        for method_id, change in control_flow_result.complexity_changes.items():
            delta = change.get('delta', 0)
            after = change.get('after', 0)

            if delta > 10:
                findings.append(Finding(
                    category=FindingCategory.PERFORMANCE,
                    severity=Severity.HIGH,
                    title="Significant Complexity Increase",
                    description=f"Cyclomatic complexity increased by {delta} (now {after})",
                    location=change.get('method_name', str(method_id)),
                    recommendation="Consider refactoring into smaller functions",
                    confidence=0.85
                ))
            elif delta > 5:
                findings.append(Finding(
                    category=FindingCategory.PERFORMANCE,
                    severity=Severity.MEDIUM,
                    title="Moderate Complexity Increase",
                    description=f"Cyclomatic complexity increased by {delta} (now {after})",
                    location=change.get('method_name', str(method_id)),
                    recommendation="Review for refactoring opportunities",
                    confidence=0.80
                ))

            # Check for methods exceeding threshold
            if after > 20:
                findings.append(Finding(
                    category=FindingCategory.PERFORMANCE,
                    severity=Severity.MEDIUM,
                    title="High Cyclomatic Complexity",
                    description=f"Method complexity {after} exceeds recommended threshold of 20",
                    location=change.get('method_name', str(method_id)),
                    recommendation="Refactor to reduce complexity",
                    confidence=0.90
                ))

        return findings

    def _analyze_hot_paths(
        self,
        patch: PatchContext,
        delta_cpg: DeltaCPG,
        call_graph_result: CallGraphAnalysisResult
    ) -> List[Finding]:
        """Analyze impact on hot execution paths."""
        findings: List[Finding] = []

        # Check if changed methods are on hot paths
        for method in patch.changed_methods:
            # Get method's callers
            centrality = call_graph_result.affected_centrality.get(method.full_name, 0)

            # High centrality methods are likely on hot paths
            if centrality > 0.5:
                findings.append(Finding(
                    category=FindingCategory.PERFORMANCE,
                    severity=Severity.HIGH,
                    title="Hot Path Modified",
                    description=f"High-centrality method modified (centrality: {centrality:.2f})",
                    location=f"{method.filepath}:{method.line_start}",
                    recommendation="Profile changes in production-like environment",
                    confidence=0.75
                ))
            elif centrality > 0.2:
                findings.append(Finding(
                    category=FindingCategory.PERFORMANCE,
                    severity=Severity.MEDIUM,
                    title="Frequently Called Method Modified",
                    description=f"Moderately central method modified (centrality: {centrality:.2f})",
                    location=f"{method.filepath}:{method.line_start}",
                    recommendation="Consider performance implications",
                    confidence=0.65
                ))

        return findings

    def _analyze_resource_usage(
        self,
        patch: PatchContext,
        delta_cpg: DeltaCPG
    ) -> List[Finding]:
        """Analyze resource usage patterns in the patch."""
        findings: List[Finding] = []

        resource_patterns = [
            (r'new\s+\w+\[\d{6,}\]', 'Large array allocation', Severity.HIGH),
            (r'cache\s*=\s*\{\}|dict\(\)', 'Unbounded cache', Severity.LOW),
            (r'global\s+\w+|GlobalScope', 'Global state', Severity.LOW),
            (r'(?:Thread|Process)\.start', 'New thread/process', Severity.MEDIUM),
        ]

        for node in delta_cpg.nodes:
            if node.change_type.value == 'added' and node.code:
                for pattern, issue_name, severity in resource_patterns:
                    if re.search(pattern, node.code, re.IGNORECASE):
                        findings.append(Finding(
                            category=FindingCategory.PERFORMANCE,
                            severity=severity,
                            title=f"Resource Pattern: {issue_name}",
                            description=f"Detected {issue_name.lower()} pattern",
                            location=f"{node.filename}:{node.line_number}",
                            code_snippet=node.code[:150],
                            recommendation="Review resource management",
                            confidence=0.65
                        ))

        return findings

    def _identify_caching_opportunities(
        self,
        patch: PatchContext,
        delta_cpg: DeltaCPG
    ) -> List[Finding]:
        """Identify potential caching opportunities."""
        findings: List[Finding] = []

        # Patterns that suggest caching might help
        caching_opportunities = [
            (r'def\s+\w+\s*\([^)]*\)\s*:\s*\n(?:.*\n)*?.*(?:requests\.|query\(|execute\()', 'Consider memoization for expensive operations'),
            (r'for\s+\w+\s+in\s+.*:\s*\n.*\.\w+\([^)]*\)\s*(?:#.*)?$', 'Consider caching repeated method calls'),
        ]

        for file_diff in patch.files:
            full_code = '\n'.join(
                line
                for hunk in file_diff.hunks
                for line in hunk.added_lines
            )

            for pattern, suggestion in caching_opportunities:
                if re.search(pattern, full_code, re.MULTILINE):
                    findings.append(Finding(
                        id=f"perf_cache_{hash(file_diff.path)}",
                        category=FindingCategory.PERFORMANCE,
                        severity=Severity.INFO,
                        title="Caching Opportunity",
                        description=suggestion,
                        location=file_diff.path,
                        code_snippet=None,
                        recommendation="Consider adding @lru_cache or explicit caching",
                        confidence=0.50
                    ))
                    break  # One finding per file

        return findings

    def _calculate_performance_score(
        self,
        findings: List[Finding],
        control_flow_result: ControlFlowAnalysisResult
    ) -> float:
        """Calculate performance score (0-100)."""
        if not findings and not control_flow_result.new_loops:
            return 100.0

        severity_weights = {
            Severity.CRITICAL: 20,
            Severity.HIGH: 12,
            Severity.MEDIUM: 6,
            Severity.LOW: 2,
            Severity.INFO: 0.5,
        }

        total_penalty = 0
        for finding in findings:
            weight = severity_weights.get(finding.severity, 1)
            total_penalty += weight * finding.confidence

        # Additional penalty for complexity
        complexity_delta = self._calculate_complexity_delta(control_flow_result)
        if complexity_delta > 0:
            total_penalty += complexity_delta * 0.5

        score = max(0, 100 - total_penalty)
        return round(score, 2)

    def _calculate_complexity_delta(
        self,
        control_flow_result: ControlFlowAnalysisResult
    ) -> int:
        """Calculate total complexity delta."""
        return sum(
            change.get('delta', 0)
            for change in control_flow_result.complexity_changes.values()
        )

    def _get_impact_summary(self, findings: List[Finding]) -> str:
        """Get summary of performance impact."""
        if not findings:
            return "No significant performance impact detected"

        issue_types = set()
        for finding in findings:
            title_lower = finding.title.lower()
            if 'loop' in title_lower or 'n+1' in title_lower:
                issue_types.add('algorithmic')
            elif 'memory' in title_lower or 'list' in title_lower:
                issue_types.add('memory')
            elif 'http' in title_lower or 'network' in title_lower:
                issue_types.add('network')
            elif 'database' in title_lower or 'query' in title_lower:
                issue_types.add('database')

        if issue_types:
            return f"Potential {', '.join(issue_types)} performance issues"
        return "Various performance patterns detected"

    def _get_recommendation(self, score: float, findings: List[Finding]) -> str:
        """Get overall recommendation."""
        critical_count = sum(1 for f in findings if f.severity == Severity.CRITICAL)
        high_count = sum(1 for f in findings if f.severity == Severity.HIGH)

        if critical_count > 0:
            return "BLOCK - Critical performance issues detected. Profile and optimize before merge."
        elif high_count >= 3:
            return "REQUEST_CHANGES - Multiple high-impact performance issues. Requires optimization."
        elif score < 60:
            return "REQUEST_CHANGES - Performance score below threshold. Address major issues."
        elif score < 80:
            return "COMMENT - Some performance concerns. Consider addressing before merge."
        else:
            return "APPROVE - No significant performance issues detected."
