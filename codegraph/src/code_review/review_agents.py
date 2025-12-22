"""
Code Review Automation Agents (Scenario 9)

Implements three specialized agents for automated code review:

1. PRAnalyzer - Parses pull request diffs and extracts changes
2. ContextAggregator - Gathers CPG context for changed code
3. ReviewReporter - Generates review comments and recommendations

Author: Code Review Team
Date: 2025-11-22
"""

import re
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from enum import Enum

from ..analysis.call_graph_analyzer import CallGraphAnalyzer


# ============================================================================
# ENUMS
# ============================================================================

class ChangeType(Enum):
    """Type of code change"""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class ReviewSeverity(Enum):
    """Severity of review finding"""
    CRITICAL = "critical"    # Must fix before merge
    HIGH = "high"            # Should fix before merge
    MEDIUM = "medium"        # Consider fixing
    LOW = "low"              # Optional improvement
    INFO = "info"            # Informational only


class ReviewAction(Enum):
    """Recommended review action"""
    APPROVE = "approve"                    # Ready to merge
    REQUEST_CHANGES = "request_changes"    # Changes required
    COMMENT = "comment"                    # Feedback only


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ChangedFile:
    """
    Represents a file changed in a PR.

    Attributes:
        filepath: Path to the file
        change_type: Type of change (added, modified, deleted)
        additions: Number of lines added
        deletions: Number of lines deleted
        diff: Unified diff content
        language: Programming language
    """
    filepath: str
    change_type: ChangeType
    additions: int
    deletions: int
    diff: str
    language: str = "unknown"


@dataclass
class ChangedMethod:
    """
    Represents a method changed in a PR.

    Attributes:
        method_name: Name of the method
        filepath: File containing the method
        line_number: Line number in file
        change_type: Type of change
        code_snippet: Changed code
        method_id: CPG method ID (if found)
    """
    method_name: str
    filepath: str
    line_number: int
    change_type: ChangeType
    code_snippet: str
    method_id: Optional[int] = None


@dataclass
class MethodContext:
    """
    CPG context for a method.

    Attributes:
        method_id: CPG method ID
        method_name: Method name
        callers: List of methods that call this
        callees: List of methods this calls
        test_count: Number of tests covering this
        complexity: Cyclomatic complexity
        security_tags: Security-related tags
        performance_tags: Performance-related tags
        subsystem: Subsystem this belongs to
    """
    method_id: int
    method_name: str
    callers: List[Dict[str, Any]] = field(default_factory=list)
    callees: List[Dict[str, Any]] = field(default_factory=list)
    test_count: int = 0
    complexity: int = 0
    security_tags: List[str] = field(default_factory=list)
    performance_tags: List[str] = field(default_factory=list)
    subsystem: Optional[str] = None


@dataclass
class ReviewFinding:
    """
    A review finding/issue.

    Attributes:
        finding_id: Unique identifier
        severity: Finding severity
        category: Finding category (security, performance, etc.)
        title: Short title
        description: Detailed description
        filepath: File location
        line_number: Line number
        suggestion: Suggested fix
        references: Related documentation/links
    """
    finding_id: str
    severity: ReviewSeverity
    category: str
    title: str
    description: str
    filepath: str
    line_number: int
    suggestion: Optional[str] = None
    references: List[str] = field(default_factory=list)


@dataclass
class ReviewComment:
    """
    A review comment to post.

    Attributes:
        filepath: File to comment on
        line_number: Line to comment on
        body: Comment text
        severity: Comment severity
    """
    filepath: str
    line_number: int
    body: str
    severity: ReviewSeverity


@dataclass
class ReviewReport:
    """
    Complete code review report.

    Attributes:
        report_id: Unique identifier
        timestamp: When review was performed
        pr_info: PR metadata
        files_changed: Number of files changed
        methods_changed: Number of methods changed
        findings: All review findings
        comments: Generated review comments
        review_score: Overall score (0-100)
        review_action: Recommended action
        summary: Executive summary
        recommendations: Key recommendations
    """
    report_id: str
    timestamp: str
    pr_info: Dict[str, Any]
    files_changed: int
    methods_changed: int
    findings: List[ReviewFinding]
    comments: List[ReviewComment]
    review_score: float
    review_action: ReviewAction
    summary: str
    recommendations: List[str]


# ============================================================================
# AGENT 1: PR ANALYZER
# ============================================================================

class PRAnalyzer:
    """
    Agent 1: Parses pull request diffs and extracts changes.

    Analyzes:
    - PR metadata (author, description, etc.)
    - Changed files and line counts
    - Changed methods and functions
    - Affected subsystems

    Usage:
        analyzer = PRAnalyzer()
        pr_data = analyzer.parse_pr_diff(diff_text)
        changed_methods = analyzer.extract_changed_methods(pr_data)
    """

    def __init__(self):
        """Initialize PRAnalyzer"""
        self.function_patterns = {
            'c': r'^\s*(?:static\s+)?(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*\{?',
            'python': r'^\s*def\s+(\w+)\s*\(',
            'java': r'^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:\w+\s+)+(\w+)\s*\(',
        }

    def parse_pr_diff(self, diff_text: str, pr_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Parse unified diff format.

        Args:
            diff_text: Unified diff content
            pr_metadata: PR metadata (title, author, etc.)

        Returns:
            Parsed PR data with changed files
        """
        files = []
        current_file = None

        for line in diff_text.split('\n'):
            # File header: diff --git a/file b/file
            if line.startswith('diff --git'):
                if current_file:
                    files.append(current_file)
                current_file = {'diff_lines': []}

            # File path: --- a/file, +++ b/file
            elif line.startswith('---'):
                if current_file:
                    current_file['old_path'] = line[6:].strip()
            elif line.startswith('+++'):
                if current_file:
                    current_file['new_path'] = line[6:].strip()
                    current_file['filepath'] = current_file['new_path']
                    # Detect language from extension
                    if current_file['filepath'].endswith('.c'):
                        current_file['language'] = 'c'
                    elif current_file['filepath'].endswith('.py'):
                        current_file['language'] = 'python'
                    elif current_file['filepath'].endswith('.java'):
                        current_file['language'] = 'java'
                    else:
                        current_file['language'] = 'unknown'

            # Diff content
            elif current_file:
                current_file['diff_lines'].append(line)

        # Add last file
        if current_file:
            files.append(current_file)

        # Process files to ChangedFile objects
        changed_files = []
        for f in files:
            additions = len([l for l in f['diff_lines'] if l.startswith('+')])
            deletions = len([l for l in f['diff_lines'] if l.startswith('-')])

            # Determine change type
            if f.get('old_path') == '/dev/null':
                change_type = ChangeType.ADDED
            elif f.get('new_path') == '/dev/null':
                change_type = ChangeType.DELETED
            else:
                change_type = ChangeType.MODIFIED

            changed_files.append(ChangedFile(
                filepath=f.get('filepath', ''),
                change_type=change_type,
                additions=additions,
                deletions=deletions,
                diff='\n'.join(f['diff_lines']),
                language=f.get('language', 'unknown')
            ))

        return {
            'pr_metadata': pr_metadata or {},
            'files_changed': len(changed_files),
            'changed_files': changed_files,
            'total_additions': sum(f.additions for f in changed_files),
            'total_deletions': sum(f.deletions for f in changed_files),
        }

    def extract_changed_methods(self, pr_data: Dict[str, Any]) -> List[ChangedMethod]:
        """
        Extract changed methods from PR data.

        Args:
            pr_data: Parsed PR data

        Returns:
            List of ChangedMethod objects
        """
        changed_methods = []

        for file in pr_data['changed_files']:
            if file.change_type == ChangeType.DELETED:
                continue

            # Get function pattern for this language
            pattern = self.function_patterns.get(file.language)
            if not pattern:
                continue

            # Parse diff to find changed methods
            in_function = False
            current_function = None
            line_num = 0

            for line in file.diff.split('\n'):
                # Track line numbers from diff hunks
                if line.startswith('@@'):
                    # Parse hunk header: @@ -old_start,old_lines +new_start,new_lines @@
                    match = re.search(r'\+(\d+)', line)
                    if match:
                        line_num = int(match.group(1))
                    continue

                # Check if this is an added/modified line
                if line.startswith('+') and not line.startswith('+++'):
                    # Check if this line defines a function
                    match = re.match(pattern, line[1:])  # Remove '+' prefix
                    if match:
                        function_name = match.group(1)
                        changed_methods.append(ChangedMethod(
                            method_name=function_name,
                            filepath=file.filepath,
                            line_number=line_num,
                            change_type=ChangeType.MODIFIED if file.change_type == ChangeType.MODIFIED else ChangeType.ADDED,
                            code_snippet=line[1:].strip()
                        ))

                # Increment line number for added/unchanged lines
                if not line.startswith('-'):
                    line_num += 1

        return changed_methods

    def identify_affected_subsystems(self, changed_files: List[ChangedFile]) -> List[str]:
        """
        Identify affected subsystems from changed files.

        Args:
            changed_files: List of changed files

        Returns:
            List of affected subsystem names
        """
        subsystems = set()

        for file in changed_files:
            # Simple heuristic: top-level directory is subsystem
            parts = file.filepath.split('/')
            if len(parts) > 1:
                subsystems.add(parts[0])

        return sorted(list(subsystems))


# ============================================================================
# AGENT 2: CONTEXT AGGREGATOR
# ============================================================================

class ContextAggregator:
    """
    Agent 2: Gathers CPG context for changed code.

    Gathers:
    - Call graph information (callers, callees)
    - Test coverage data
    - Security and performance tags
    - Complexity metrics
    - Related issues from other scenarios

    Usage:
        aggregator = ContextAggregator(cpg_service)
        context = aggregator.gather_method_context(method_id)
        impacted = aggregator.find_impacted_methods(changed_methods)
    """

    def __init__(self, cpg_service):
        """
        Initialize ContextAggregator.

        Args:
            cpg_service: CPGQueryService instance
        """
        self.cpg = cpg_service
        self.call_graph_analyzer = CallGraphAnalyzer(cpg_service)
        self._complexity_cache = None  # Cache cyclomatic complexity results

    def gather_method_context(self, method_id: int) -> MethodContext:
        """
        Gather complete CPG context for a method.

        Args:
            method_id: CPG method ID

        Returns:
            MethodContext object
        """
        # Get method details
        method_query = f"""
        SELECT
            m.id,
            m.name,
            m.filename,
            m.line_number
        FROM nodes_method m
        WHERE m.id = {method_id}
        """
        method_result = self.cpg.execute_custom_sql(method_query)
        if not method_result:
            return None

        method = method_result[0]

        # Get callers
        callers_query = f"""
        SELECT DISTINCT
            caller.name AS caller_name,
            caller.filename AS caller_file,
            caller.line_number AS caller_line
        FROM edges_call ec
        JOIN nodes_call nc ON ec.src = nc.id
        JOIN nodes_method caller ON nc.method_full_name = caller.full_name
        WHERE ec.dst = {method_id}
        LIMIT 20
        """
        callers = self.cpg.execute_custom_sql(callers_query)

        # Get callees
        callees_query = f"""
        SELECT DISTINCT
            callee.name AS callee_name,
            callee.filename AS callee_file,
            callee.line_number AS callee_line
        FROM nodes_method m
        JOIN nodes_call nc ON nc.method_full_name = m.full_name
        JOIN edges_call ec ON ec.src = nc.id
        JOIN nodes_method callee ON ec.dst = callee.id
        WHERE m.id = {method_id}
        LIMIT 20
        """
        callees = self.cpg.execute_custom_sql(callees_query)

        # Get tags (complexity, security, etc.)
        tags_query = f"""
        SELECT
            tag.name AS tag_name,
            tag.value AS tag_value
        FROM edges_tagged_by e
        JOIN nodes_tag tag ON e.dst = tag.id
        WHERE e.src = {method_id}
        """
        tags = self.cpg.execute_custom_sql(tags_query)

        # Process tags
        complexity = 0
        security_tags = []
        performance_tags = []
        subsystem = None
        test_count = 0

        for tag in tags:
            tag_name = tag.get('tag_name', '')
            tag_value = tag.get('tag_value', '')

            if tag_name == 'cyclomatic-complexity':
                complexity = int(tag_value) if tag_value else 0
            elif tag_name == 'subsystem':
                subsystem = tag_value
            elif tag_name == 'test-count':
                test_count = int(tag_value) if tag_value else 0
            elif 'security' in tag_name.lower():
                security_tags.append(f"{tag_name}:{tag_value}")
            elif 'performance' in tag_name.lower() or 'hotspot' in tag_name.lower():
                performance_tags.append(f"{tag_name}:{tag_value}")

        # Phase 2 Enhancement: Compute cyclomatic complexity if not in tags
        if complexity == 0:
            complexity = self._compute_complexity_for_method(method['name'])

        return MethodContext(
            method_id=method_id,
            method_name=method['name'],
            callers=callers,
            callees=callees,
            test_count=test_count,
            complexity=complexity,
            security_tags=security_tags,
            performance_tags=performance_tags,
            subsystem=subsystem
        )

    def find_impacted_methods(self, changed_methods: List[ChangedMethod]) -> List[Dict[str, Any]]:
        """
        Find methods impacted by changes.

        Args:
            changed_methods: List of changed methods

        Returns:
            List of impacted methods with impact details
        """
        impacted = []

        for method in changed_methods:
            if not method.method_id:
                continue

            # Get all callers (directly impacted)
            context = self.gather_method_context(method.method_id)
            if not context:
                continue

            for caller in context.callers:
                impacted.append({
                    'impacted_method': caller['caller_name'],
                    'impacted_file': caller['caller_file'],
                    'reason': f"Calls modified method {method.method_name}",
                    'impact_level': 'direct'
                })

        return impacted

    def check_test_coverage(self, changed_methods: List[ChangedMethod]) -> Dict[str, Any]:
        """
        Check test coverage for changed methods.

        Args:
            changed_methods: List of changed methods

        Returns:
            Test coverage report
        """
        total_methods = len(changed_methods)
        tested_methods = 0
        untested_methods = []

        for method in changed_methods:
            if not method.method_id:
                continue

            context = self.gather_method_context(method.method_id)
            if context and context.test_count > 0:
                tested_methods += 1
            else:
                untested_methods.append(method.method_name)

        coverage_percent = (tested_methods / total_methods * 100) if total_methods > 0 else 0

        return {
            'total_methods': total_methods,
            'tested_methods': tested_methods,
            'untested_methods': untested_methods,
            'coverage_percent': coverage_percent
        }

    def _compute_complexity_for_method(self, method_name: str) -> int:
        """
        Compute cyclomatic complexity for a method using CallGraphAnalyzer.

        Phase 2 Enhancement: Uses CallGraphAnalyzer.compute_cyclomatic_complexity()
        to calculate CFG-based cyclomatic complexity (M = E - N + 2).

        Args:
            method_name: Name of the method

        Returns:
            Cyclomatic complexity score (1-100+)
        """
        try:
            # Compute complexity for all methods (cached)
            if self._complexity_cache is None:
                self._complexity_cache = self.call_graph_analyzer.compute_cyclomatic_complexity(
                    top_n=1000  # Cache top 1000
                )

            # Find this method's complexity
            for result in self._complexity_cache:
                if result.get('method_name') == method_name:
                    return result.get('complexity', 0)

            # Method not found in top N, likely low complexity
            return 1  # Default to 1 (simplest possible)

        except Exception as e:
            # Gracefully degrade if complexity computation fails
            return 0  # Unknown


# ============================================================================
# AGENT 3: REVIEW REPORTER
# ============================================================================

class ReviewReporter:
    """
    Agent 3: Generates review comments and recommendations.

    Generates:
    - Review findings (security, performance, architecture, debt issues)
    - Review comments for each file/line
    - Overall review score
    - Recommendation (APPROVE, REQUEST_CHANGES, COMMENT)

    Usage:
        reporter = ReviewReporter()
        findings = reporter.analyze_changes(pr_data, contexts)
        report = reporter.generate_review_report(pr_data, findings)
    """

    def __init__(self):
        """Initialize ReviewReporter"""
        pass

    def analyze_changes(
        self,
        pr_data: Dict[str, Any],
        method_contexts: List[MethodContext],
        test_coverage: Dict[str, Any]
    ) -> List[ReviewFinding]:
        """
        Analyze changes and generate findings.

        Args:
            pr_data: Parsed PR data
            method_contexts: CPG contexts for changed methods
            test_coverage: Test coverage report

        Returns:
            List of ReviewFinding objects
        """
        findings = []

        # Check 1: Large PR size
        if pr_data['total_additions'] + pr_data['total_deletions'] > 500:
            findings.append(ReviewFinding(
                finding_id=f"LARGE_PR_{uuid.uuid4().hex[:8]}",
                severity=ReviewSeverity.MEDIUM,
                category="code_quality",
                title="Large Pull Request",
                description=f"PR has {pr_data['total_additions']} additions and {pr_data['total_deletions']} deletions. Consider breaking into smaller PRs.",
                filepath="<overall>",
                line_number=0,
                suggestion="Split into smaller, focused PRs for easier review",
                references=["https://google.github.io/eng-practices/review/developer/small-cls.html"]
            ))

        # Check 2: Test coverage
        if test_coverage['coverage_percent'] < 50:
            findings.append(ReviewFinding(
                finding_id=f"LOW_COVERAGE_{uuid.uuid4().hex[:8]}",
                severity=ReviewSeverity.HIGH,
                category="testing",
                title="Low Test Coverage",
                description=f"Only {test_coverage['coverage_percent']:.1f}% of changed methods have tests. Untested: {', '.join(test_coverage['untested_methods'][:5])}",
                filepath="<overall>",
                line_number=0,
                suggestion="Add tests for changed methods",
                references=[]
            ))

        # Check 3: High complexity
        for context in method_contexts:
            if context.complexity > 15:
                findings.append(ReviewFinding(
                    finding_id=f"HIGH_COMPLEXITY_{context.method_id}",
                    severity=ReviewSeverity.MEDIUM,
                    category="code_quality",
                    title="High Cyclomatic Complexity",
                    description=f"Method {context.method_name} has complexity {context.complexity}. Consider refactoring.",
                    filepath="<needs_lookup>",
                    line_number=0,
                    suggestion="Break down into smaller methods",
                    references=[]
                ))

        # Check 4: Security tags
        for context in method_contexts:
            if context.security_tags:
                findings.append(ReviewFinding(
                    finding_id=f"SECURITY_{context.method_id}",
                    severity=ReviewSeverity.HIGH,
                    category="security",
                    title="Security Concern",
                    description=f"Method {context.method_name} has security tags: {', '.join(context.security_tags)}",
                    filepath="<needs_lookup>",
                    line_number=0,
                    suggestion="Review security implications carefully",
                    references=[]
                ))

        return findings

    def generate_review_comments(self, findings: List[ReviewFinding]) -> List[ReviewComment]:
        """
        Convert findings to review comments.

        Args:
            findings: List of review findings

        Returns:
            List of ReviewComment objects
        """
        comments = []

        for finding in findings:
            if finding.filepath == "<overall>":
                continue  # Skip overall findings

            comment_body = f"**{finding.title}** [{finding.severity.value}]\n\n"
            comment_body += f"{finding.description}\n\n"
            if finding.suggestion:
                comment_body += f"💡 Suggestion: {finding.suggestion}\n\n"
            if finding.references:
                comment_body += f"📚 References: {', '.join(finding.references)}"

            comments.append(ReviewComment(
                filepath=finding.filepath,
                line_number=finding.line_number,
                body=comment_body,
                severity=finding.severity
            ))

        return comments

    def calculate_review_score(self, findings: List[ReviewFinding]) -> float:
        """
        Calculate overall review score (0-100).

        Args:
            findings: List of review findings

        Returns:
            Review score (higher = better)
        """
        # Start with perfect score
        score = 100.0

        # Deduct points based on severity
        severity_penalties = {
            ReviewSeverity.CRITICAL: 25,
            ReviewSeverity.HIGH: 15,
            ReviewSeverity.MEDIUM: 5,
            ReviewSeverity.LOW: 1,
            ReviewSeverity.INFO: 0
        }

        for finding in findings:
            score -= severity_penalties.get(finding.severity, 0)

        # Floor at 0
        return max(0.0, score)

    def recommend_action(self, score: float, findings: List[ReviewFinding]) -> ReviewAction:
        """
        Recommend review action based on score and findings.

        Args:
            score: Review score
            findings: List of review findings

        Returns:
            Recommended ReviewAction
        """
        # Any critical findings = request changes
        if any(f.severity == ReviewSeverity.CRITICAL for f in findings):
            return ReviewAction.REQUEST_CHANGES

        # Score < 70 or high severity findings = request changes
        if score < 70 or any(f.severity == ReviewSeverity.HIGH for f in findings):
            return ReviewAction.REQUEST_CHANGES

        # Score >= 90 and no medium+ findings = approve
        if score >= 90 and not any(f.severity in [ReviewSeverity.MEDIUM, ReviewSeverity.HIGH] for f in findings):
            return ReviewAction.APPROVE

        # Otherwise = comment only
        return ReviewAction.COMMENT

    def generate_review_report(
        self,
        pr_data: Dict[str, Any],
        findings: List[ReviewFinding],
        method_contexts: List[MethodContext]
    ) -> ReviewReport:
        """
        Generate complete review report.

        Args:
            pr_data: Parsed PR data
            findings: Review findings
            method_contexts: Method contexts

        Returns:
            ReviewReport object
        """
        # Generate comments
        comments = self.generate_review_comments(findings)

        # Calculate score
        score = self.calculate_review_score(findings)

        # Recommend action
        action = self.recommend_action(score, findings)

        # Generate summary
        summary = self._generate_summary(pr_data, findings, score, action)

        # Generate recommendations
        recommendations = self._generate_recommendations(findings)

        return ReviewReport(
            report_id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().isoformat(),
            pr_info=pr_data.get('pr_metadata', {}),
            files_changed=pr_data['files_changed'],
            methods_changed=len(method_contexts),
            findings=findings,
            comments=comments,
            review_score=score,
            review_action=action,
            summary=summary,
            recommendations=recommendations
        )

    def _generate_summary(
        self,
        pr_data: Dict[str, Any],
        findings: List[ReviewFinding],
        score: float,
        action: ReviewAction
    ) -> str:
        """Generate executive summary"""
        files_changed = pr_data['files_changed']
        additions = pr_data['total_additions']
        deletions = pr_data['total_deletions']

        # Count by severity
        critical = len([f for f in findings if f.severity == ReviewSeverity.CRITICAL])
        high = len([f for f in findings if f.severity == ReviewSeverity.HIGH])
        medium = len([f for f in findings if f.severity == ReviewSeverity.MEDIUM])

        parts = [
            f"Reviewed PR with {files_changed} files changed (+{additions}/-{deletions} lines).",
            f"Found {len(findings)} issues: {critical} critical, {high} high, {medium} medium.",
            f"Review score: {score:.1f}/100."
        ]

        if action == ReviewAction.APPROVE:
            parts.append("✅ Recommended action: APPROVE")
        elif action == ReviewAction.REQUEST_CHANGES:
            parts.append("⚠️ Recommended action: REQUEST CHANGES")
        else:
            parts.append("💬 Recommended action: COMMENT")

        return " ".join(parts)

    def _generate_recommendations(self, findings: List[ReviewFinding]) -> List[str]:
        """Generate top recommendations"""
        recommendations = []

        # Group by category
        by_category = {}
        for finding in findings:
            cat = finding.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(finding)

        # Recommend based on most common categories
        sorted_categories = sorted(by_category.items(), key=lambda x: -len(x[1]))

        for category, category_findings in sorted_categories[:3]:
            count = len(category_findings)
            if category_findings[0].suggestion:
                recommendations.append(f"[{category}] {count} issues: {category_findings[0].suggestion}")

        return recommendations[:5]


if __name__ == "__main__":
    print("Code Review Automation Agents (Scenario 9)")
    print("=" * 60)
    print("[OK] Agent 1: PRAnalyzer - COMPLETE")
    print("[OK] Agent 2: ContextAggregator - COMPLETE")
    print("[OK] Agent 3: ReviewReporter - COMPLETE")
    print()
    print("Data Structures:")
    print("  - ChangedFile (file changes)")
    print("  - ChangedMethod (method changes)")
    print("  - MethodContext (CPG context)")
    print("  - ReviewFinding (issues found)")
    print("  - ReviewComment (comments to post)")
    print("  - ReviewReport (complete report)")
