"""
Architecture Verdict Generator for Patch Review System.

Analyzes patch changes for architectural impact, design patterns,
and structural quality.
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
    ArchitectureVerdict,
    FindingCategory,
)
from ..analyzers import (
    PatchCallGraphAnalyzer,
    CallGraphAnalysisResult
)
from ..analyzers import (
    PatchDependencyAnalyzer,
    DependencyAnalysisResult
)

logger = logging.getLogger(__name__)


class ArchitectureIssueType(Enum):
    """Types of architecture issues."""
    COUPLING = "coupling"
    COHESION = "cohesion"
    ABSTRACTION = "abstraction"
    LAYERING = "layering"
    DEPENDENCY = "dependency"
    DESIGN_PATTERN = "design_pattern"
    API_DESIGN = "api_design"
    MODULARITY = "modularity"


@dataclass
class ArchitecturePattern:
    """An architecture pattern/anti-pattern to check for."""
    name: str
    description: str
    issue_type: ArchitectureIssueType
    severity: Severity
    pattern: str  # Regex pattern
    recommendation: str
    is_antipattern: bool = True
    confidence: float = 0.8


class ArchitectureVerdictGenerator:
    """
    Generates architecture verdicts for patch changes.

    Analyzes:
    - Module coupling and cohesion
    - Layer violations
    - Design pattern adherence
    - API design quality
    - Breaking changes
    - Blast radius
    """

    ARCHITECTURE_PATTERNS: List[ArchitecturePattern] = [
        # Coupling Issues
        ArchitecturePattern(
            name="God Class",
            description="Class with too many responsibilities (many methods/imports)",
            issue_type=ArchitectureIssueType.COUPLING,
            severity=Severity.MEDIUM,
            pattern=r'class\s+\w+.*:\s*\n(?:.*\n){50,}',
            recommendation="Split into smaller, focused classes",
            confidence=0.60
        ),
        ArchitecturePattern(
            name="Feature Envy",
            description="Method accessing many fields from another class",
            issue_type=ArchitectureIssueType.COUPLING,
            severity=Severity.LOW,
            pattern=r'def\s+\w+\([^)]*\):\s*\n(?:.*(?:self\.\w+\.\w+\.){2,}.*\n){2,}',
            recommendation="Consider moving method to the class it envies",
            confidence=0.55
        ),
        ArchitecturePattern(
            name="Circular Import",
            description="Potential circular import pattern",
            issue_type=ArchitectureIssueType.DEPENDENCY,
            severity=Severity.HIGH,
            pattern=r'from\s+\.\w+\s+import.*\n(?:.*\n)*?.*from\s+\.\w+\s+import',
            recommendation="Restructure to break circular dependency",
            confidence=0.50
        ),

        # Abstraction Issues
        ArchitecturePattern(
            name="Missing Abstraction",
            description="Direct instantiation of concrete class that should be injected",
            issue_type=ArchitectureIssueType.ABSTRACTION,
            severity=Severity.LOW,
            pattern=r'def\s+__init__\([^)]*\):\s*\n\s*self\.\w+\s*=\s*\w+\(',
            recommendation="Consider dependency injection for better testability",
            confidence=0.50
        ),
        ArchitecturePattern(
            name="Leaky Abstraction",
            description="Implementation details exposed in interface",
            issue_type=ArchitectureIssueType.ABSTRACTION,
            severity=Severity.MEDIUM,
            pattern=r'def\s+\w+\([^)]*(?:sql|query|connection|cursor)',
            recommendation="Abstract away implementation details from public API",
            confidence=0.60
        ),

        # API Design Issues
        ArchitecturePattern(
            name="Long Parameter List",
            description="Function with too many parameters",
            issue_type=ArchitectureIssueType.API_DESIGN,
            severity=Severity.MEDIUM,
            pattern=r'def\s+\w+\s*\([^)]{100,}\)',
            recommendation="Use parameter objects or builder pattern",
            confidence=0.80
        ),
        ArchitecturePattern(
            name="Boolean Parameter",
            description="Boolean parameter that changes function behavior",
            issue_type=ArchitectureIssueType.API_DESIGN,
            severity=Severity.LOW,
            pattern=r'def\s+\w+\s*\([^)]*:\s*bool\s*(?:=|,|\))',
            recommendation="Consider splitting into separate functions",
            confidence=0.50
        ),
        ArchitecturePattern(
            name="Inconsistent Return Type",
            description="Function returning different types",
            issue_type=ArchitectureIssueType.API_DESIGN,
            severity=Severity.MEDIUM,
            pattern=r'def\s+\w+[^:]+:\s*\n(?:.*\n)*?.*return\s+None.*\n(?:.*\n)*?.*return\s+(?!None)',
            recommendation="Use Optional type or raise exception instead of returning None",
            confidence=0.65
        ),

        # Design Pattern Violations
        ArchitecturePattern(
            name="Singleton Abuse",
            description="Using singleton pattern where not appropriate",
            issue_type=ArchitectureIssueType.DESIGN_PATTERN,
            severity=Severity.LOW,
            pattern=r'_instance\s*=\s*None.*\n.*@classmethod.*\n.*get_instance',
            recommendation="Consider dependency injection instead of singleton",
            confidence=0.60
        ),
        ArchitecturePattern(
            name="Hardcoded Configuration",
            description="Configuration values hardcoded in code",
            issue_type=ArchitectureIssueType.DESIGN_PATTERN,
            severity=Severity.MEDIUM,
            pattern=r'(?:host|port|url|endpoint)\s*=\s*["\'][^"\']+["\']',
            recommendation="Move configuration to config file or environment variables",
            confidence=0.70
        ),

        # Modularity Issues
        ArchitecturePattern(
            name="Mixed Concerns",
            description="Business logic mixed with infrastructure code",
            issue_type=ArchitectureIssueType.MODULARITY,
            severity=Severity.MEDIUM,
            pattern=r'def\s+\w+.*:\s*\n(?:.*\n)*?.*(?:cursor|execute|query)(?:.*\n)*?.*(?:if|for|while)',
            recommendation="Separate data access from business logic",
            confidence=0.55
        ),
        ArchitecturePattern(
            name="Utility Class",
            description="Class with only static methods (should be module)",
            issue_type=ArchitectureIssueType.MODULARITY,
            severity=Severity.LOW,
            pattern=r'class\s+\w+(?:Utils?|Helper|Manager).*:\s*\n(?:\s*@staticmethod\s*\n\s*def\s+\w+.*\n)+',
            recommendation="Consider using module functions instead of static class",
            confidence=0.70
        ),
    ]

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        """
        Initialize the architecture verdict generator.

        Args:
            conn: DuckDB connection with CPG loaded
        """
        self.conn = conn
        self.call_graph_analyzer = PatchCallGraphAnalyzer(conn)
        self.dependency_analyzer = PatchDependencyAnalyzer(conn)

    def generate_verdict(
        self,
        patch: PatchContext,
        delta_cpg: DeltaCPG,
        call_graph_result: Optional[CallGraphAnalysisResult] = None,
        dependency_result: Optional[DependencyAnalysisResult] = None
    ) -> ArchitectureVerdict:
        """
        Generate comprehensive architecture verdict for the patch.

        Args:
            patch: The patch context
            delta_cpg: Delta CPG with changes
            call_graph_result: Optional pre-computed call graph analysis
            dependency_result: Optional pre-computed dependency analysis

        Returns:
            Complete architecture verdict
        """
        logger.info(f"Generating architecture verdict for patch {patch.patch_id}")

        findings: List[Finding] = []

        # 1. Pattern-based architecture analysis
        pattern_findings = self._check_architecture_patterns(patch, delta_cpg)
        findings.extend(pattern_findings)

        # 2. Call graph analysis (blast radius, breaking changes)
        if call_graph_result is None:
            call_graph_result = self.call_graph_analyzer.analyze_call_graph_impact(
                patch, delta_cpg
            )

        # Add blast radius findings
        blast_radius_findings = self._analyze_blast_radius(call_graph_result)
        findings.extend(blast_radius_findings)

        # Add breaking change findings
        for breaking_change in call_graph_result.breaking_changes:
            findings.append(Finding(
                category=FindingCategory.ARCHITECTURE,
                severity=breaking_change.severity,
                title=f"Breaking Change: {breaking_change.change_type}",
                description=breaking_change.description,
                location=breaking_change.location,
                recommendation=breaking_change.recommendation,
                confidence=0.85
            ))

        # 3. Dependency analysis
        if dependency_result is None:
            dependency_result = self.dependency_analyzer.analyze_dependency_changes(
                patch, delta_cpg
            )

        # Add dependency findings
        findings.extend(dependency_result.findings)

        # 4. Module cohesion analysis
        cohesion_findings = self._analyze_cohesion(patch, delta_cpg)
        findings.extend(cohesion_findings)

        # 5. API consistency analysis
        api_findings = self._analyze_api_consistency(patch, delta_cpg)
        findings.extend(api_findings)

        # 6. Design principle violations
        principle_findings = self._check_design_principles(patch, delta_cpg)
        findings.extend(principle_findings)

        # Calculate architecture score
        score = self._calculate_architecture_score(
            findings, call_graph_result, dependency_result
        )

        # Get metrics
        blast_radius_score = self._calculate_blast_radius_score(call_graph_result)

        verdict = ArchitectureVerdict(
            findings=findings,
            score=score,
            layer_violations=dependency_result.layer_violations if dependency_result else [],
            circular_deps=dependency_result.circular_dependencies if dependency_result else [],
            new_imports=[{"module": m} for m in dependency_result.affected_modules] if dependency_result else [],
            api_changes=call_graph_result.breaking_changes if call_graph_result else [],
            blast_radius_score=blast_radius_score
        )

        logger.info(
            f"Architecture verdict: score={score:.2f}, "
            f"breaking_changes={verdict.breaking_changes}, "
            f"blast_radius={blast_radius_score:.2f}"
        )

        return verdict

    def _check_architecture_patterns(
        self,
        patch: PatchContext,
        delta_cpg: DeltaCPG
    ) -> List[Finding]:
        """Check for architecture patterns/anti-patterns."""
        findings: List[Finding] = []

        # Collect added code
        added_code_blocks: List[Tuple[str, int, str]] = []

        for file_diff in patch.files:
            full_code = '\n'.join(
                line
                for hunk in file_diff.hunks
                for line in hunk.added_lines
            )
            if full_code:
                added_code_blocks.append((file_diff.path, 1, full_code))

        # Check patterns
        for pattern in self.ARCHITECTURE_PATTERNS:
            compiled = re.compile(pattern.pattern, re.IGNORECASE | re.MULTILINE)

            for filepath, line_num, code in added_code_blocks:
                if compiled.search(code):
                    findings.append(Finding(
                        category=FindingCategory.ARCHITECTURE,
                        severity=pattern.severity,
                        title=f"{'Anti-Pattern' if pattern.is_antipattern else 'Pattern'}: {pattern.name}",
                        description=pattern.description,
                        location=filepath,
                        recommendation=pattern.recommendation,
                        confidence=pattern.confidence,
                        is_new=True
                    ))

        return findings

    def _analyze_blast_radius(
        self,
        call_graph_result: CallGraphAnalysisResult
    ) -> List[Finding]:
        """Analyze blast radius and generate findings."""
        findings: List[Finding] = []

        for method, blast_radius in call_graph_result.blast_radius.items():
            if blast_radius.direct_callers > 10:
                findings.append(Finding(
                    category=FindingCategory.ARCHITECTURE,
                    severity=Severity.HIGH,
                    title="High Blast Radius",
                    description=f"Method has {blast_radius.direct_callers} direct callers and {blast_radius.transitive_callers} transitive callers",
                    location=method,
                    recommendation="Test changes thoroughly; consider feature flag for gradual rollout",
                    confidence=0.85
                ))
            elif blast_radius.direct_callers > 5:
                findings.append(Finding(
                    category=FindingCategory.ARCHITECTURE,
                    severity=Severity.MEDIUM,
                    title="Moderate Blast Radius",
                    description=f"Method has {blast_radius.direct_callers} direct callers",
                    location=method,
                    recommendation="Ensure adequate test coverage for affected callers",
                    confidence=0.80
                ))

        return findings

    def _analyze_cohesion(
        self,
        patch: PatchContext,
        delta_cpg: DeltaCPG
    ) -> List[Finding]:
        """Analyze module cohesion."""
        findings: List[Finding] = []

        # Check for methods that seem unrelated to the class
        for method in patch.changed_methods:
            if method.change_type.value == 'added':
                # Check method name against class name (basic heuristic)
                class_name = self._extract_class_name(method.full_name)
                method_name = method.name

                if class_name:
                    # Basic cohesion check: method should relate to class
                    class_words = set(self._split_camel_case(class_name).lower().split())
                    method_words = set(self._split_camel_case(method_name).lower().split())

                    # If method name shares no words with class, might be low cohesion
                    common = class_words & method_words
                    if not common and len(method_words) > 1:
                        findings.append(Finding(
                            category=FindingCategory.ARCHITECTURE,
                            severity=Severity.LOW,
                            title="Potential Low Cohesion",
                            description=f"Method '{method_name}' may not belong to class '{class_name}'",
                            location=f"{method.filepath}:{method.line_start}",
                            recommendation="Verify method belongs in this class or consider moving it",
                            confidence=0.40
                        ))

        return findings

    def _analyze_api_consistency(
        self,
        patch: PatchContext,
        delta_cpg: DeltaCPG
    ) -> List[Finding]:
        """Analyze API design consistency."""
        findings: List[Finding] = []

        # Check for inconsistent naming conventions
        method_names: List[Tuple[str, str]] = []

        for method in patch.changed_methods:
            if method.change_type.value == 'added':
                method_names.append((method.name, method.filepath))

        # Check naming conventions
        snake_case = 0
        camel_case = 0
        other = 0

        for name, filepath in method_names:
            if '_' in name and name.islower():
                snake_case += 1
            elif name[0].islower() and any(c.isupper() for c in name):
                camel_case += 1
            else:
                other += 1

        total = snake_case + camel_case + other
        if total >= 3:  # Need enough samples
            if snake_case > 0 and camel_case > 0:
                findings.append(Finding(
                    category=FindingCategory.ARCHITECTURE,
                    severity=Severity.LOW,
                    title="Inconsistent Naming Convention",
                    description=f"Mixed naming styles: {snake_case} snake_case, {camel_case} camelCase",
                    location="Multiple files",
                    recommendation="Adopt consistent naming convention (snake_case for Python)",
                    confidence=0.70
                ))

        return findings

    def _check_design_principles(
        self,
        patch: PatchContext,
        delta_cpg: DeltaCPG
    ) -> List[Finding]:
        """Check for SOLID and other design principle violations."""
        findings: List[Finding] = []

        for node in delta_cpg.nodes:
            if node.change_type.value == 'added' and node.node_type == 'TYPE_DECL':
                code = node.code or ''

                # Single Responsibility: Check for many public methods
                public_methods = len(re.findall(r'def\s+(?!_)\w+', code))
                if public_methods > 10:
                    findings.append(Finding(
                        category=FindingCategory.ARCHITECTURE,
                        severity=Severity.MEDIUM,
                        title="Potential SRP Violation",
                        description=f"Class has {public_methods} public methods - may have too many responsibilities",
                        location=f"{node.filename}:{node.line_number}",
                        recommendation="Consider splitting into smaller, focused classes",
                        confidence=0.60
                    ))

                # Interface Segregation: Check for many abstract methods
                abstract_methods = len(re.findall(r'@abstractmethod|def\s+\w+\([^)]*\):\s*\.\.\.|pass', code))
                if abstract_methods > 8:
                    findings.append(Finding(
                        category=FindingCategory.ARCHITECTURE,
                        severity=Severity.LOW,
                        title="Potential ISP Violation",
                        description=f"Interface has {abstract_methods} abstract methods - may be too broad",
                        location=f"{node.filename}:{node.line_number}",
                        recommendation="Consider splitting into smaller, focused interfaces",
                        confidence=0.55
                    ))

        return findings

    def _calculate_architecture_score(
        self,
        findings: List[Finding],
        call_graph_result: CallGraphAnalysisResult,
        dependency_result: DependencyAnalysisResult
    ) -> float:
        """Calculate architecture score (0-100)."""
        severity_weights = {
            Severity.CRITICAL: 20,
            Severity.HIGH: 12,
            Severity.MEDIUM: 6,
            Severity.LOW: 2,
            Severity.INFO: 0.5,
        }

        total_penalty = 0

        # Penalty from findings
        for finding in findings:
            weight = severity_weights.get(finding.severity, 1)
            total_penalty += weight * finding.confidence

        # Penalty for breaking changes
        total_penalty += len(call_graph_result.breaking_changes) * 10

        # Penalty for circular dependencies
        total_penalty += len(dependency_result.circular_dependencies) * 15

        # Penalty for layer violations
        total_penalty += len(dependency_result.layer_violations) * 8

        score = max(0, 100 - total_penalty)
        return round(score, 2)

    def _calculate_blast_radius_score(
        self,
        call_graph_result: CallGraphAnalysisResult
    ) -> float:
        """Calculate blast radius score (0-100, lower is higher risk)."""
        if not call_graph_result.blast_radius:
            return 100.0

        max_direct = max(
            br.direct_callers
            for br in call_graph_result.blast_radius.values()
        )
        max_transitive = max(
            br.transitive_callers
            for br in call_graph_result.blast_radius.values()
        )

        # Score decreases with higher blast radius
        direct_penalty = min(max_direct * 5, 50)
        transitive_penalty = min(max_transitive * 2, 30)

        score = max(0, 100 - direct_penalty - transitive_penalty)
        return round(score, 2)

    def _extract_class_name(self, full_name: str) -> Optional[str]:
        """Extract class name from fully qualified method name."""
        if '.' in full_name:
            parts = full_name.rsplit('.', 2)
            if len(parts) >= 2:
                return parts[-2]
        return None

    def _split_camel_case(self, name: str) -> str:
        """Split camelCase or PascalCase into words."""
        return re.sub(r'([a-z])([A-Z])', r'\1 \2', name)

    def _get_recommendation(self, score: float, findings: List[Finding]) -> str:
        """Get overall recommendation."""
        critical_count = sum(1 for f in findings if f.severity == Severity.CRITICAL)
        high_count = sum(1 for f in findings if f.severity == Severity.HIGH)

        if critical_count > 0:
            return "BLOCK - Critical architecture issues detected. Requires architectural review."
        elif high_count >= 3:
            return "REQUEST_CHANGES - Multiple high-impact architecture issues. Needs refactoring."
        elif score < 60:
            return "REQUEST_CHANGES - Architecture score below threshold. Address major issues."
        elif score < 80:
            return "COMMENT - Some architecture concerns. Consider addressing before merge."
        else:
            return "APPROVE - Architecture looks good. Minor improvements possible."
