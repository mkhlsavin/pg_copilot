"""Dependency Analyzer Agent.

Agent 1: Analyzes module dependencies and detects violations.
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from .models import (
    ViolationFinding,
    DependencyMetrics,
    DependencyAnalysis,
)
from ..architecture_patterns import (
    ArchitecturePattern,
    get_pattern,
    get_patterns_by_category,
)
from src.analysis.callgraph import CallGraphAnalyzer


class DependencyAnalyzer:
    """
    Agent 1: Analyzes module dependencies and detects violations.

    Detects:
    - Circular dependencies between modules
    - God modules (excessive dependencies)
    - Unstable dependencies (stable depending on unstable)
    - Feature envy (methods too interested in other modules)
    - Inappropriate intimacy (bidirectional tight coupling)

    Usage:
        analyzer = DependencyAnalyzer(cpg_service)
        findings = analyzer.detect_all_violations(limit_per_pattern=20)
        metrics = analyzer.calculate_dependency_metrics(findings)
    """

    def __init__(self, cpg_service):
        """
        Initialize DependencyAnalyzer.

        Args:
            cpg_service: CPGQueryService instance for database access
        """
        self.cpg = cpg_service
        self.patterns = (
            get_patterns_by_category('dependency') +
            get_patterns_by_category('coupling') +
            get_patterns_by_category('cohesion')
        )
        self.call_graph_analyzer = CallGraphAnalyzer(cpg_service)

    def detect_all_violations(self, limit_per_pattern: int = 20) -> List[ViolationFinding]:
        """
        Detect all dependency-related violations using all patterns.

        Args:
            limit_per_pattern: Maximum findings per pattern (default: 20)

        Returns:
            List of ViolationFinding objects, sorted by severity
        """
        all_findings = []

        for pattern in self.patterns:
            try:
                findings = self.detect_pattern(pattern, limit=limit_per_pattern)
                all_findings.extend(findings)
            except Exception as e:
                print(f"Error detecting pattern {pattern.pattern_id}: {e}")
                continue

        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        all_findings.sort(key=lambda f: severity_order.get(f.severity, 999))

        return all_findings

    def detect_pattern(self, pattern: ArchitecturePattern, limit: int = 20) -> List[ViolationFinding]:
        """
        Detect instances of a specific violation pattern.

        Args:
            pattern: ArchitecturePattern to detect
            limit: Maximum findings to return

        Returns:
            List of ViolationFinding objects for this pattern
        """
        query = pattern.detection_query
        results = self.cpg.execute_custom_sql(query)

        findings = []
        for idx, result in enumerate(results[:limit]):
            finding = self._create_finding_from_result(pattern, result, idx)
            findings.append(finding)

        return findings

    def _create_finding_from_result(
        self,
        pattern: ArchitecturePattern,
        result: Dict[str, Any],
        index: int
    ) -> ViolationFinding:
        """Create a ViolationFinding from a query result."""
        finding_id = f"{pattern.pattern_id}_{index:03d}"

        module_a = self._extract_module_name(result, pattern.pattern_id)
        module_b = self._extract_module_b_name(result, pattern.pattern_id)
        violation_details = self._format_violation_details(pattern, result)

        remediation_steps = [
            step.strip() for step in pattern.remediation.split('\n')
            if step.strip() and not step.strip().isdigit()
        ]

        return ViolationFinding(
            finding_id=finding_id,
            pattern_id=pattern.pattern_id,
            pattern_name=pattern.name,
            category=pattern.category.value,
            severity=pattern.severity.value,
            module_a=module_a,
            module_b=module_b,
            violation_details=violation_details,
            impact_description=pattern.impact,
            remediation_steps=remediation_steps[:3],
            metadata=result
        )

    def _extract_module_name(self, result: Dict[str, Any], pattern_id: str) -> str:
        """Extract primary module name from result based on pattern type."""
        if pattern_id == "CIRCULAR_DEPS":
            return result.get('from_file', 'unknown')
        elif pattern_id == "GOD_MODULE":
            return result.get('module_file', 'unknown')
        elif pattern_id == "UNSTABLE_DEPS":
            return result.get('stable_module', 'unknown')
        elif pattern_id == "FEATURE_ENVY":
            return result.get('envious_module', 'unknown')
        elif pattern_id == "INAPPROPRIATE_INTIMACY":
            return result.get('module_a', 'unknown')
        else:
            return result.get('module', result.get('filename', result.get('module_file', 'unknown')))

    def _extract_module_b_name(self, result: Dict[str, Any], pattern_id: str) -> Optional[str]:
        """Extract secondary module name from result based on pattern type."""
        if pattern_id == "CIRCULAR_DEPS":
            return result.get('to_file')
        elif pattern_id == "UNSTABLE_DEPS":
            return result.get('unstable_module')
        elif pattern_id == "FEATURE_ENVY":
            return result.get('envied_module')
        elif pattern_id == "INAPPROPRIATE_INTIMACY":
            return result.get('module_b')
        else:
            return None

    def _format_violation_details(self, pattern: ArchitecturePattern, result: Dict[str, Any]) -> str:
        """Format violation details based on pattern type."""
        if pattern.pattern_id == "CIRCULAR_DEPS":
            return f"Circular dependency path: {result.get('path', 'N/A')} (depth: {result.get('depth', 0)})"
        elif pattern.pattern_id == "GOD_MODULE":
            return f"Fan-out: {result.get('outgoing_dependencies', 0)}, Fan-in: {result.get('incoming_dependencies', 0)}"
        elif pattern.pattern_id == "UNSTABLE_DEPS":
            return (
                f"Stable module (instability: {result.get('stable_instability', 0):.2f}) "
                f"depends on unstable module (instability: {result.get('unstable_instability', 0):.2f})"
            )
        elif pattern.pattern_id == "FEATURE_ENVY":
            return f"Method makes {result.get('call_count', 0)} calls to external module"
        elif pattern.pattern_id == "INAPPROPRIATE_INTIMACY":
            return (
                f"Bidirectional coupling: {result.get('a_to_b_calls', 0)} calls A->B, "
                f"{result.get('b_to_a_calls', 0)} calls B->A (total: {result.get('total_coupling', 0)})"
            )
        else:
            return str(result)

    def calculate_dependency_metrics(self, findings: List[ViolationFinding]) -> DependencyAnalysis:
        """
        Calculate dependency metrics from findings.

        Args:
            findings: List of violation findings

        Returns:
            DependencyAnalysis with comprehensive metrics
        """
        violations_by_severity = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        violations_by_category = {'dependency': 0, 'layering': 0, 'coupling': 0, 'cohesion': 0}

        for finding in findings:
            violations_by_severity[finding.severity] = violations_by_severity.get(finding.severity, 0) + 1
            violations_by_category[finding.category] = violations_by_category.get(finding.category, 0) + 1

        circular_deps = len([f for f in findings if f.pattern_id == "CIRCULAR_DEPS"])
        god_modules = len([f for f in findings if f.pattern_id == "GOD_MODULE"])

        module_metrics = self._calculate_module_metrics(findings)

        high_coupling = [
            m.module_name for m in module_metrics
            if m.coupling_score > 30 or m.is_god_module
        ]

        all_modules = set()
        for finding in findings:
            all_modules.add(finding.module_a)
            if finding.module_b:
                all_modules.add(finding.module_b)

        return DependencyAnalysis(
            analysis_id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().isoformat(),
            total_modules=len(all_modules),
            total_violations=len(findings),
            violations_by_severity=violations_by_severity,
            violations_by_category=violations_by_category,
            circular_dependency_count=circular_deps,
            god_module_count=god_modules,
            module_metrics=module_metrics,
            high_coupling_modules=high_coupling
        )

    def _calculate_module_metrics(self, findings: List[ViolationFinding]) -> List[DependencyMetrics]:
        """Calculate dependency metrics for each module."""
        module_data = {}

        for finding in findings:
            if finding.module_a not in module_data:
                module_data[finding.module_a] = {
                    'fan_in': 0,
                    'fan_out': 0,
                    'violation_count': 0,
                    'is_god_module': False
                }

            module_data[finding.module_a]['violation_count'] += 1

            if finding.pattern_id == "GOD_MODULE":
                module_data[finding.module_a]['fan_out'] = finding.metadata.get('outgoing_dependencies', 0)
                module_data[finding.module_a]['fan_in'] = finding.metadata.get('incoming_dependencies', 0)
                module_data[finding.module_a]['is_god_module'] = True

            if finding.module_b and finding.module_b not in module_data:
                module_data[finding.module_b] = {
                    'fan_in': 0,
                    'fan_out': 0,
                    'violation_count': 0,
                    'is_god_module': False
                }

        metrics = []
        for module_name, data in module_data.items():
            fan_in = data['fan_in']
            fan_out = data['fan_out']

            total_deps = fan_in + fan_out
            instability = fan_out / total_deps if total_deps > 0 else 0.0
            coupling_score = fan_in + fan_out

            metrics.append(DependencyMetrics(
                module_name=module_name,
                fan_in=fan_in,
                fan_out=fan_out,
                instability=instability,
                coupling_score=coupling_score,
                is_god_module=data['is_god_module'],
                violation_count=data['violation_count']
            ))

        metrics.sort(key=lambda m: m.coupling_score, reverse=True)
        return metrics

    def detect_dead_code(self) -> List[ViolationFinding]:
        """
        Detect isolated/dead code using Weakly Connected Components (WCC).

        Returns:
            List of ViolationFinding objects for isolated methods/modules
        """
        findings = []

        try:
            wccs = self.call_graph_analyzer.compute_weakly_connected_components()

            if not wccs:
                return findings

            main_component = max(wccs, key=len)
            main_size = len(main_component)

            isolated_components = [wcc for wcc in wccs if len(wcc) < main_size * 0.01]

            for idx, isolated in enumerate(isolated_components):
                if len(isolated) == 0:
                    continue

                sample_methods = list(isolated)[:5]
                method_list = ", ".join(sample_methods)
                if len(isolated) > 5:
                    method_list += f" (and {len(isolated) - 5} more)"

                finding = ViolationFinding(
                    finding_id=f"dead_code_wcc_{idx:03d}",
                    pattern_id="dead_code_detection",
                    pattern_name="Isolated Dead Code (WCC)",
                    category="cohesion",
                    severity="medium" if len(isolated) > 5 else "low",
                    module_a=sample_methods[0] if sample_methods else "unknown",
                    module_b=None,
                    violation_details=f"Isolated component with {len(isolated)} methods: {method_list}",
                    impact_description=(
                        f"Code is unreachable from main codebase ({main_size} methods). "
                        f"May represent dead code, test utilities, or orphaned features."
                    ),
                    remediation_steps=[
                        "Review if this code is still needed",
                        "Check if it's test-only code (acceptable if in test directory)",
                        "Remove if confirmed as dead code",
                        "Add entry points if it should be reachable"
                    ],
                    metadata={
                        'component_size': len(isolated),
                        'main_component_size': main_size,
                        'isolation_ratio': len(isolated) / main_size if main_size > 0 else 0,
                        'methods': list(isolated)
                    }
                )
                findings.append(finding)

            return findings

        except Exception:
            return []

    def detect_circular_dependencies(self) -> List[ViolationFinding]:
        """
        Detect circular dependencies using Strongly Connected Components (SCC).

        Returns:
            List of ViolationFinding objects for circular dependencies
        """
        findings = []

        try:
            sccs = self.call_graph_analyzer.compute_strongly_connected_components()
            significant_cycles = [scc for scc in sccs if len(scc) >= 3]

            for idx, scc in enumerate(significant_cycles):
                modules = set()
                for method in scc:
                    parts = method.split('::')
                    if len(parts) > 1:
                        modules.add(parts[0])
                    else:
                        parts = method.split('/')
                        if len(parts) > 1:
                            modules.add(parts[0])

                if len(modules) > 1:
                    if len(modules) > 5 or len(scc) > 20:
                        severity = "critical"
                    elif len(modules) > 3 or len(scc) > 10:
                        severity = "high"
                    else:
                        severity = "medium"

                    sample_methods = list(scc)[:10]
                    method_sample = ", ".join(sample_methods[:5])
                    if len(sample_methods) > 5:
                        method_sample += f" ... (and {len(sample_methods) - 5} more)"

                    finding = ViolationFinding(
                        finding_id=f"circular_dep_scc_{idx:03d}",
                        pattern_id="circular_module_dependency",
                        pattern_name="Circular Module Dependency (SCC)",
                        category="coupling",
                        severity=severity,
                        module_a=list(modules)[0] if modules else "unknown",
                        module_b=list(modules)[1] if len(modules) > 1 else None,
                        violation_details=(
                            f"Circular dependency among {len(modules)} modules "
                            f"involving {len(scc)} methods. "
                            f"Modules: {', '.join(list(modules)[:5])}"
                        ),
                        impact_description=(
                            f"Strongly connected component detected with {len(scc)} methods "
                            f"across {len(modules)} modules. This creates tight coupling that "
                            f"makes refactoring dangerous and violates dependency inversion principle."
                        ),
                        remediation_steps=[
                            "Break cycle by introducing interfaces/abstractions",
                            "Apply dependency inversion principle (depend on abstractions)",
                            "Extract shared logic to new module",
                            "Consider facade pattern to reduce coupling",
                            "Use dependency injection to invert dependencies"
                        ],
                        metadata={
                            'detection_algorithm': 'tarjan_scc',
                            'scc_size': len(scc),
                            'modules_involved': list(modules),
                            'method_count': len(scc),
                            'sample_methods': sample_methods,
                            'scc_index': idx
                        }
                    )
                    findings.append(finding)

            return findings

        except Exception:
            return []

    def identify_architectural_chokepoints(self) -> List[Dict[str, Any]]:
        """
        Identify architectural chokepoints using betweenness centrality.

        Returns:
            List of dictionaries with chokepoint information
        """
        try:
            betweenness_results = self.call_graph_analyzer.compute_betweenness_centrality(
                sample_size=1000,
                top_n=50
            )

            if not betweenness_results:
                return []

            max_betweenness = max(b['betweenness_score'] for b in betweenness_results)
            threshold = max_betweenness * 0.05

            chokepoints = []
            for result in betweenness_results:
                if result['betweenness_score'] >= threshold:
                    if result['betweenness_score'] > max_betweenness * 0.1:
                        risk_level = 'critical'
                        impact = 'Removing this method would severely disconnect the architecture'
                    else:
                        risk_level = 'high'
                        impact = 'Removing this method would disconnect multiple subsystems'

                    chokepoint = {
                        'method_name': result['method_name'],
                        'betweenness_score': result['betweenness_score'],
                        'betweenness_percentile': result.get('percentile', 0),
                        'is_bridge': True,
                        'risk_level': risk_level,
                        'impact': impact,
                        'recommendation': (
                            'Add redundancy or alternative paths. '
                            'Ensure comprehensive testing. '
                            'Consider circuit breaker pattern.'
                        ),
                        'detection_algorithm': 'brandes_betweenness'
                    }
                    chokepoints.append(chokepoint)

            return chokepoints

        except Exception:
            return []
