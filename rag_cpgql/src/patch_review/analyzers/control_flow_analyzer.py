"""
Patch Control Flow Impact Analyzer

Analyzes control flow changes introduced by the patch:
- Cyclomatic complexity changes
- New loops (nested, unbounded, with I/O)
- Error handling changes
- Branch coverage impact

Phase: Impact Analyzers (Phase 2)
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.patch_review.models import (
    ChangedMethod,
    ChangeType,
    ComplexityDelta,
    DeltaCPG,
    Severity,
)

logger = logging.getLogger(__name__)


@dataclass
class NewLoopFinding:
    """Represents a new loop introduced by the patch"""
    method_name: str
    loop_type: str          # "for", "while", "do_while", "recursion"
    line_number: int
    is_nested: bool
    has_io: bool            # Loop contains I/O operations
    is_unbounded: bool      # No clear termination condition
    severity: Severity
    details: str


@dataclass
class ErrorHandlingChange:
    """Represents a change to error handling"""
    method_name: str
    change_type: str        # "added", "removed", "modified"
    error_type: str         # "try_catch", "error_check", "null_check"
    line_number: int
    details: str


@dataclass
class BranchCoverageImpact:
    """Impact on branch coverage from the patch"""
    new_branches: int
    removed_branches: int
    net_change: int
    methods_with_new_branches: List[str]
    uncovered_paths: List[Dict[str, Any]]


class PatchControlFlowAnalyzer:
    """
    Analyzes control flow impact of patch changes.

    Computes:
    - Cyclomatic complexity changes
    - New loop detection
    - Error handling changes
    - Branch coverage impact
    """

    def __init__(self, conn: Any, delta_cpg: Optional[DeltaCPG] = None):
        """
        Initialize the analyzer.

        Args:
            conn: DuckDB connection or CPGQueryService
            delta_cpg: Optional DeltaCPG for patch-specific analysis
        """
        self.conn = conn
        self.delta = delta_cpg

        # Support multiple interfaces
        if hasattr(conn, 'execute'):
            self._execute = self._execute_duckdb
        elif hasattr(conn, 'execute_query'):
            self._execute = conn.execute_query
        elif hasattr(conn, 'execute_sql_dict'):
            self._execute = conn.execute_sql_dict
        else:
            self._execute = lambda q, p=None: []

        logger.info("PatchControlFlowAnalyzer initialized")

    def _execute_duckdb(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute query on DuckDB and return list of dicts."""
        try:
            if params:
                result = self.conn.execute(query, params)
            else:
                result = self.conn.execute(query)
            columns = [desc[0] for desc in result.description] if result.description else []
            rows = result.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.debug(f"Query failed: {e}")
            return []

    def analyze_control_flow_changes(
        self,
        patch: Any,  # PatchContext
        delta_cpg: DeltaCPG
    ) -> 'ControlFlowAnalysisResult':
        """
        Analyze complete control flow impact of a patch.

        Args:
            patch: The patch context
            delta_cpg: Delta CPG with changes

        Returns:
            ControlFlowAnalysisResult with all control flow findings
        """
        from . import ControlFlowAnalysisResult
        from ..models import Finding, FindingCategory

        self.delta = delta_cpg

        # Analyze complexity changes
        complexity_deltas = self.analyze_complexity_change(patch.changed_methods)
        complexity_changes = {}
        for cd in complexity_deltas:
            complexity_changes[cd.method_id] = {
                'method_name': cd.method_name,
                'before': cd.before,
                'after': cd.after,
                'delta': cd.after - cd.before
            }

        # Detect new loops
        new_loops = self.detect_new_loops(patch.changed_methods)

        # Analyze error handling changes
        error_changes = self.analyze_error_handling_changes(patch.changed_methods)

        # Analyze branch coverage impact
        branch_impact = self.analyze_branch_coverage_impact(patch.changed_methods)

        # Convert to findings
        findings = []
        for loop in new_loops:
            if loop.is_unbounded or loop.is_nested:
                findings.append(Finding(
                    category=FindingCategory.PERFORMANCE,
                    severity=loop.severity,
                    title=f"New {loop.loop_type} Loop",
                    description=loop.details,
                    location=f"{loop.method_name}:{loop.line_number}",
                    recommendation="Review loop bounds and performance implications"
                ))

        return ControlFlowAnalysisResult(
            complexity_changes=complexity_changes,
            new_loops=new_loops,
            error_handling_changes=error_changes,
            branch_coverage_impacts=[branch_impact] if branch_impact else [],
            findings=findings
        )

    def set_delta(self, delta_cpg: DeltaCPG):
        """Set or update the delta CPG"""
        self.delta = delta_cpg

    def analyze_complexity_change(
        self,
        changed_methods: List[ChangedMethod]
    ) -> List[ComplexityDelta]:
        """
        Calculate cyclomatic complexity change for modified methods.

        Cyclomatic complexity: M = E - N + 2
        Where E = edges, N = nodes in CFG

        Args:
            changed_methods: List of changed methods

        Returns:
            List of complexity deltas
        """
        deltas: List[ComplexityDelta] = []

        for method in changed_methods:
            if method.change_type == ChangeType.DELETED:
                # Deleted method - complexity goes to 0
                old_complexity = method.complexity_before or self._get_method_complexity(method.method_name)
                if old_complexity > 0:
                    deltas.append(ComplexityDelta(
                        method_name=method.method_name,
                        complexity_before=old_complexity,
                        complexity_after=0,
                        delta=-old_complexity,
                        risk_level="low"  # Removing code reduces complexity
                    ))

            elif method.change_type == ChangeType.ADDED:
                # New method - estimate complexity from code patterns
                new_complexity = self._estimate_complexity_from_delta(method)
                if new_complexity > 0:
                    risk_level = self._classify_complexity_risk(0, new_complexity)
                    deltas.append(ComplexityDelta(
                        method_name=method.method_name,
                        complexity_before=0,
                        complexity_after=new_complexity,
                        delta=new_complexity,
                        risk_level=risk_level
                    ))

            elif method.change_type == ChangeType.MODIFIED:
                # Modified method - compare before/after
                old_complexity = method.complexity_before or self._get_method_complexity(method.method_name)
                new_complexity = method.complexity_after or self._estimate_complexity_change(method)

                if new_complexity is None:
                    new_complexity = old_complexity  # Assume no change if we can't estimate

                delta = new_complexity - old_complexity
                if delta != 0:
                    risk_level = self._classify_complexity_risk(old_complexity, new_complexity)
                    deltas.append(ComplexityDelta(
                        method_name=method.method_name,
                        complexity_before=old_complexity,
                        complexity_after=new_complexity,
                        delta=delta,
                        risk_level=risk_level
                    ))

        # Sort by delta (largest increases first)
        deltas.sort(key=lambda d: d.delta, reverse=True)

        logger.info(f"Analyzed complexity for {len(changed_methods)} methods, found {len(deltas)} changes")
        return deltas

    def detect_new_loops(
        self,
        changed_methods: List[ChangedMethod]
    ) -> List[NewLoopFinding]:
        """
        Detect new loops introduced by the patch.

        Flags potentially problematic loops:
        - Nested loops (O(n^2) risk)
        - Loops with I/O operations
        - Unbounded loops (no clear termination)

        Args:
            changed_methods: List of changed methods

        Returns:
            List of new loop findings
        """
        findings: List[NewLoopFinding] = []

        # Get methods that were added or modified
        relevant_methods = [
            m for m in changed_methods
            if m.change_type in [ChangeType.ADDED, ChangeType.MODIFIED]
        ]

        for method in relevant_methods:
            loops = self._find_loops_in_method(method)
            findings.extend(loops)

        # Sort by severity
        findings.sort(key=lambda f: f.severity.value)

        logger.info(f"Found {len(findings)} new loops in changed methods")
        return findings

    def analyze_error_handling_changes(
        self,
        changed_methods: List[ChangedMethod]
    ) -> List[ErrorHandlingChange]:
        """
        Detect changes to error handling in the patch.

        Looks for:
        - Added/removed try-catch blocks
        - Added/removed error checks
        - Changes to null checks

        Args:
            changed_methods: List of changed methods

        Returns:
            List of error handling changes
        """
        changes: List[ErrorHandlingChange] = []

        for method in changed_methods:
            if method.change_type == ChangeType.DELETED:
                # Check if deleted method had error handling
                error_handling = self._get_error_handling_in_method(method.method_name)
                for eh in error_handling:
                    changes.append(ErrorHandlingChange(
                        method_name=method.method_name,
                        change_type="removed",
                        error_type=eh['type'],
                        line_number=eh['line'],
                        details=f"Error handling removed with deleted method"
                    ))

            elif method.change_type == ChangeType.ADDED:
                # Estimate error handling in new method
                # This would require parsing the actual code
                pass

            elif method.change_type == ChangeType.MODIFIED:
                # Compare error handling before and after
                # This requires code diffing
                pass

        logger.info(f"Found {len(changes)} error handling changes")
        return changes

    def analyze_branch_coverage_impact(
        self,
        changed_methods: List[ChangedMethod]
    ) -> BranchCoverageImpact:
        """
        Estimate how patch affects branch coverage.

        New branches that need testing are identified.

        Args:
            changed_methods: List of changed methods

        Returns:
            BranchCoverageImpact summary
        """
        new_branches = 0
        removed_branches = 0
        methods_with_new_branches: List[str] = []
        uncovered_paths: List[Dict[str, Any]] = []

        for method in changed_methods:
            if method.change_type == ChangeType.ADDED:
                # New method - all branches are new
                branch_count = self._count_branches_in_method(method)
                if branch_count > 0:
                    new_branches += branch_count
                    methods_with_new_branches.append(method.method_name)

            elif method.change_type == ChangeType.DELETED:
                # Deleted method - branches removed
                branch_count = self._get_branch_count(method.method_name)
                removed_branches += branch_count

            elif method.change_type == ChangeType.MODIFIED:
                # Modified - estimate net change
                old_branches = self._get_branch_count(method.method_name)
                new_branch_estimate = self._estimate_new_branches(method)

                if new_branch_estimate > old_branches:
                    new_branches += (new_branch_estimate - old_branches)
                    methods_with_new_branches.append(method.method_name)
                elif new_branch_estimate < old_branches:
                    removed_branches += (old_branches - new_branch_estimate)

        return BranchCoverageImpact(
            new_branches=new_branches,
            removed_branches=removed_branches,
            net_change=new_branches - removed_branches,
            methods_with_new_branches=methods_with_new_branches,
            uncovered_paths=uncovered_paths
        )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _get_method_complexity(self, method_name: str) -> int:
        """
        Get cyclomatic complexity for a method from base CPG.

        Uses CFG edges: M = E - N + 2
        """
        query = """
            WITH method_cfg AS (
                SELECT COUNT(DISTINCT cfg.src) + COUNT(DISTINCT cfg.dst) AS nodes,
                       COUNT(*) AS edges
                FROM nodes_method m
                JOIN cpg_nodes n ON n.method_full_name LIKE '%' || m.name || '%'
                JOIN edges_cfg cfg ON cfg.src = n.id OR cfg.dst = n.id
                WHERE m.name = ?
            )
            SELECT
                CASE
                    WHEN nodes = 0 THEN 1
                    ELSE edges - nodes + 2
                END AS complexity
            FROM method_cfg;
        """

        try:
            results = self._execute(query, (method_name,))
            if results:
                return max(1, results[0].get('complexity', 1))
        except Exception as e:
            logger.debug(f"Error getting complexity for {method_name}: {e}")

        # Fallback: estimate from control structures
        return self._estimate_complexity_from_controls(method_name)

    def _estimate_complexity_from_controls(self, method_name: str) -> int:
        """Estimate complexity by counting control structures"""
        query = """
            SELECT COUNT(*) as control_count
            FROM nodes_control_structure ncs
            JOIN nodes_method nm ON ncs.filename = nm.filename
            WHERE nm.name = ?
              AND ncs.line_number >= nm.line_number
              AND (nm.line_number_end IS NULL OR ncs.line_number <= nm.line_number_end);
        """

        try:
            results = self._execute(query, (method_name,))
            if results:
                # Complexity ~= control structures + 1
                return results[0].get('control_count', 0) + 1
        except Exception:
            pass

        return 1

    def _estimate_complexity_from_delta(self, method: ChangedMethod) -> int:
        """Estimate complexity for a new method from delta info"""
        # Without the actual code, use heuristics based on line count
        line_count = method.line_end - method.line_start + 1

        # Rough estimate: 1 decision point per 5-10 lines
        estimated_decisions = max(0, line_count // 7)
        return estimated_decisions + 1

    def _estimate_complexity_change(self, method: ChangedMethod) -> Optional[int]:
        """Estimate complexity change for a modified method"""
        # Get current complexity
        current = self._get_method_complexity(method.method_name)

        # If we have delta info, adjust based on added lines
        if self.delta:
            # Look for added control structures in delta
            added_controls = 0
            for node in self.delta.nodes:
                if node.name == method.method_name and node.change_type == ChangeType.ADDED:
                    # Rough estimate based on code patterns
                    code = node.code or ''
                    added_controls += code.count('if ')
                    added_controls += code.count('while ')
                    added_controls += code.count('for ')
                    added_controls += code.count('switch ')

            return current + added_controls

        return None

    def _classify_complexity_risk(self, old: int, new: int) -> str:
        """Classify complexity risk level"""
        delta = new - old

        if new <= 10:
            return "low"
        elif new <= 20:
            return "moderate" if delta > 5 else "low"
        elif new <= 50:
            return "high" if delta > 10 else "moderate"
        else:
            return "very_high"

    def _find_loops_in_method(self, method: ChangedMethod) -> List[NewLoopFinding]:
        """Find loops in a method"""
        findings: List[NewLoopFinding] = []

        query = """
            SELECT
                ncs.control_structure_type AS loop_type,
                ncs.line_number,
                ncs.code
            FROM nodes_control_structure ncs
            JOIN nodes_method nm ON ncs.filename = nm.filename
            WHERE nm.name = ?
              AND ncs.control_structure_type IN ('FOR', 'WHILE', 'DO')
              AND ncs.line_number >= nm.line_number
              AND (nm.line_number_end IS NULL OR ncs.line_number <= nm.line_number_end)
            ORDER BY ncs.line_number;
        """

        try:
            results = self._execute(query, (method.method_name,))

            # Track line numbers to detect nesting
            loop_lines = [r.get('line_number', 0) for r in results]

            for i, row in enumerate(results):
                loop_type = row.get('loop_type', 'UNKNOWN').lower()
                line = row.get('line_number', 0)
                code = row.get('code', '')

                # Check if nested (another loop nearby)
                is_nested = len([l for l in loop_lines if abs(l - line) < 10 and l != line]) > 0

                # Check for I/O in loop (simplified)
                io_patterns = ['read', 'write', 'fopen', 'query', 'execute', 'send', 'recv']
                has_io = any(p in code.lower() for p in io_patterns)

                # Check for unbounded (no clear limit)
                is_unbounded = 'true' in code.lower() or ('while' in loop_type and '(' not in code)

                # Determine severity
                if is_nested and has_io:
                    severity = Severity.HIGH
                elif is_nested or has_io:
                    severity = Severity.MEDIUM
                elif is_unbounded:
                    severity = Severity.MEDIUM
                else:
                    severity = Severity.LOW

                findings.append(NewLoopFinding(
                    method_name=method.method_name,
                    loop_type=loop_type,
                    line_number=line,
                    is_nested=is_nested,
                    has_io=has_io,
                    is_unbounded=is_unbounded,
                    severity=severity,
                    details=self._generate_loop_details(loop_type, is_nested, has_io, is_unbounded)
                ))

        except Exception as e:
            logger.debug(f"Error finding loops in {method.method_name}: {e}")

        return findings

    def _generate_loop_details(
        self,
        loop_type: str,
        is_nested: bool,
        has_io: bool,
        is_unbounded: bool
    ) -> str:
        """Generate human-readable details for a loop finding"""
        issues = []

        if is_nested:
            issues.append("nested loop (potential O(n^2) complexity)")
        if has_io:
            issues.append("contains I/O operations (N+1 query risk)")
        if is_unbounded:
            issues.append("potentially unbounded (no clear termination)")

        if not issues:
            return f"{loop_type} loop - no significant issues detected"

        return f"{loop_type} loop: {'; '.join(issues)}"

    def _get_error_handling_in_method(self, method_name: str) -> List[Dict[str, Any]]:
        """Get error handling constructs in a method"""
        error_handling: List[Dict[str, Any]] = []

        # Check for try-catch (control structures)
        query = """
            SELECT ncs.line_number, 'try_catch' AS type
            FROM nodes_control_structure ncs
            JOIN nodes_method nm ON ncs.filename = nm.filename
            WHERE nm.name = ?
              AND ncs.control_structure_type = 'TRY'
              AND ncs.line_number >= nm.line_number;
        """

        try:
            results = self._execute(query, (method_name,))
            for r in results:
                error_handling.append({
                    'type': r.get('type'),
                    'line': r.get('line_number')
                })
        except Exception:
            pass

        return error_handling

    def _count_branches_in_method(self, method: ChangedMethod) -> int:
        """Count branches in a new method"""
        # Estimate based on line range
        line_count = method.line_end - method.line_start + 1

        # Rough estimate: 1 branch per 8-10 lines
        return max(0, line_count // 9)

    def _get_branch_count(self, method_name: str) -> int:
        """Get branch count for existing method"""
        query = """
            SELECT COUNT(*) as branch_count
            FROM nodes_control_structure ncs
            JOIN nodes_method nm ON ncs.filename = nm.filename
            WHERE nm.name = ?
              AND ncs.control_structure_type IN ('IF', 'SWITCH', 'FOR', 'WHILE', 'DO')
              AND ncs.line_number >= nm.line_number;
        """

        try:
            results = self._execute(query, (method_name,))
            if results:
                return results[0].get('branch_count', 0)
        except Exception:
            pass

        return 0

    def _estimate_new_branches(self, method: ChangedMethod) -> int:
        """Estimate branches after modification"""
        # Start with current count and estimate additions
        current = self._get_branch_count(method.method_name)

        # Estimate based on changed lines
        line_delta = (method.line_end - method.line_start) - (method.complexity_before or 0)
        added_branches = max(0, line_delta // 10)

        return current + added_branches
