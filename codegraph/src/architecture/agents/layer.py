"""Layer Validator Agent.

Agent 2: Validates architectural layering rules.
"""
from typing import List, Dict, Any, Optional

from .models import ViolationFinding, LayerRule
from ..architecture_patterns import (
    ArchitecturePattern,
    get_pattern,
    get_patterns_by_category,
)
from src.analysis.callgraph import CallGraphAnalyzer


class LayerValidator:
    """
    Agent 2: Validates architectural layering rules.

    Detects:
    - Layering violations (lower layers calling higher layers)
    - Architecture rule violations
    - Cross-layer dependencies

    Architectural Layers (PostgreSQL example):
    1. Presentation/Interface - UI, CLI, protocols
    2. Business Logic - Query processing, optimization
    3. Storage/Data - Buffer management, file I/O
    4. System/Infrastructure - OS calls, utilities

    Rules:
    - Higher layers can depend on lower layers
    - Lower layers CANNOT depend on higher layers
    - Layers should only depend on adjacent layers (skip-layer is a smell)

    Usage:
        validator = LayerValidator(cpg_service)
        findings = validator.validate_all_layers(limit=20)
        layer_violations = validator.get_layering_violations()
    """

    DEFAULT_LAYER_HIERARCHY = {
        'system': 0,
        'storage': 1,
        'data': 1,
        'business': 2,
        'logic': 2,
        'presentation': 3,
        'interface': 3,
        'frontend': 3,
        'backend': 1
    }

    def __init__(self, cpg_service, layer_hierarchy: Optional[Dict[str, int]] = None):
        """
        Initialize LayerValidator.

        Args:
            cpg_service: CPGQueryService instance
            layer_hierarchy: Custom layer hierarchy (optional, uses default if None)
        """
        self.cpg = cpg_service
        self.layer_hierarchy = layer_hierarchy or self.DEFAULT_LAYER_HIERARCHY
        self.patterns = get_patterns_by_category('layering')
        self.call_graph_analyzer = CallGraphAnalyzer(cpg_service)

    def validate_all_layers(self, limit: int = 20) -> List[ViolationFinding]:
        """
        Validate all architectural layers.

        Args:
            limit: Maximum violations to return

        Returns:
            List of ViolationFinding objects for layering violations
        """
        all_findings = []

        for pattern in self.patterns:
            try:
                findings = self._detect_layering_pattern(pattern, limit=limit)
                all_findings.extend(findings)
            except Exception as e:
                print(f"Error detecting layering pattern {pattern.pattern_id}: {e}")
                continue

        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        all_findings.sort(key=lambda f: severity_order.get(f.severity, 999))

        return all_findings

    def _detect_layering_pattern(
        self,
        pattern: ArchitecturePattern,
        limit: int = 20
    ) -> List[ViolationFinding]:
        """Detect layering violations using pattern query."""
        query = pattern.detection_query
        results = self.cpg.execute_custom_sql(query)

        findings = []
        for idx, result in enumerate(results[:limit]):
            finding = self._create_layering_finding(pattern, result, idx)
            findings.append(finding)

        return findings

    def _create_layering_finding(
        self,
        pattern: ArchitecturePattern,
        result: Dict[str, Any],
        index: int
    ) -> ViolationFinding:
        """Create a ViolationFinding from a layering query result."""
        finding_id = f"{pattern.pattern_id}_{index:03d}"

        caller_file = result.get('caller_file', 'unknown')
        caller_layer = result.get('caller_layer', 'unknown')
        callee_file = result.get('callee_file', 'unknown')
        callee_layer = result.get('callee_layer', 'unknown')

        violation_details = (
            f"{caller_layer} layer calling {callee_layer} layer: "
            f"{result.get('caller_method', 'unknown')} -> {result.get('callee_method', 'unknown')}"
        )

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
            module_a=caller_file,
            module_b=callee_file,
            violation_details=violation_details,
            impact_description=pattern.impact,
            remediation_steps=remediation_steps[:3],
            metadata=result
        )

    def get_layering_violations(self, limit: int = 50) -> List[ViolationFinding]:
        """
        Get layering violations using hierarchy rules.

        Args:
            limit: Maximum violations to return

        Returns:
            List of ViolationFinding objects
        """
        pattern = get_pattern("LAYER_VIOLATION")
        if not pattern:
            return []

        return self._detect_layering_pattern(pattern, limit=limit)

    def validate_layer_rule(self, from_layer: str, to_layer: str) -> bool:
        """
        Validate if a dependency from one layer to another is allowed.

        Args:
            from_layer: Source layer name
            to_layer: Target layer name

        Returns:
            True if dependency is allowed, False otherwise
        """
        from_level = self.layer_hierarchy.get(from_layer.lower(), -1)
        to_level = self.layer_hierarchy.get(to_layer.lower(), -1)

        if from_level == -1 or to_level == -1:
            return False

        return from_level >= to_level

    def get_layer_metrics(self, findings: List[ViolationFinding]) -> Dict[str, Any]:
        """
        Calculate layer-specific metrics.

        Args:
            findings: List of layering violation findings

        Returns:
            Dictionary with layer metrics
        """
        layer_violations = {}
        for finding in findings:
            caller_layer = finding.metadata.get('caller_layer', 'unknown')
            callee_layer = finding.metadata.get('callee_layer', 'unknown')
            pair_key = f"{caller_layer} -> {callee_layer}"
            layer_violations[pair_key] = layer_violations.get(pair_key, 0) + 1

        sorted_pairs = sorted(layer_violations.items(), key=lambda x: -x[1])

        return {
            'total_violations': len(findings),
            'violations_by_layer_pair': dict(sorted_pairs[:10]),
            'unique_layer_pairs': len(layer_violations),
            'most_violated_pair': sorted_pairs[0] if sorted_pairs else ('none', 0)
        }

    def check_layering_violations_scc(self) -> List[ViolationFinding]:
        """
        Detect architecture layer violations using SCC.

        Returns:
            List of ViolationFinding objects for layer violations detected via SCC
        """
        findings = []

        try:
            sccs = self.call_graph_analyzer.compute_strongly_connected_components()

            layer_patterns = {
                'ui': ['frontend', 'controller', 'view', 'handler', 'interface', 'presentation'],
                'service': ['service', 'business', 'manager', 'orchestrator', 'logic'],
                'data': ['repository', 'dao', 'database', 'storage', 'backend']
            }

            for idx, scc in enumerate(sccs):
                if len(scc) < 2:
                    continue

                involved_layers = set()
                for method in scc:
                    method_lower = method.lower()
                    for layer_name, patterns in layer_patterns.items():
                        if any(pattern in method_lower for pattern in patterns):
                            involved_layers.add(layer_name)
                            break

                if len(involved_layers) > 1:
                    sample_methods = list(scc)[:10]

                    finding = ViolationFinding(
                        finding_id=f"layer_violation_scc_{idx:03d}",
                        pattern_id="layering_violation_scc",
                        pattern_name="Architecture Layer Violation (SCC)",
                        category="architecture",
                        severity="critical",
                        module_a=list(involved_layers)[0],
                        module_b=list(involved_layers)[1],
                        violation_details=(
                            f"Circular dependency across architectural layers: {', '.join(involved_layers)}. "
                            f"SCC contains {len(scc)} methods that violate clean architecture layering."
                        ),
                        impact_description=(
                            f"Strongly connected component of {len(scc)} methods spans {len(involved_layers)} "
                            f"architectural layers ({', '.join(involved_layers)}). This violates the dependency "
                            f"rule that requires unidirectional flow from high to low layers."
                        ),
                        remediation_steps=[
                            "Review call chains to understand circular dependencies",
                            "Apply dependency inversion principle at layer boundaries",
                            "Introduce interfaces to break circular layer dependencies",
                            "Move shared logic to appropriate layer (usually lower)",
                            "Consider extracting cross-layer concerns to separate module"
                        ],
                        metadata={
                            'detection_algorithm': 'tarjan_scc',
                            'scc_size': len(scc),
                            'layers_involved': list(involved_layers),
                            'sample_methods': sample_methods,
                            'scc_index': idx
                        }
                    )
                    findings.append(finding)

            return findings

        except Exception:
            return []
