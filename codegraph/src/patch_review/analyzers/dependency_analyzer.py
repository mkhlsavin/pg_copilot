"""
Dependency Analyzer for Patch Review System.

Analyzes how patches affect module dependencies, import relationships,
and overall architectural coupling.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum

import duckdb

from ..models import (
    PatchContext,
    DeltaCPG,
    ChangedMethod,
    Finding,
    Severity,
    FindingCategory,
)

logger = logging.getLogger(__name__)


class DependencyChangeType(Enum):
    """Types of dependency changes."""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    CIRCULAR_INTRODUCED = "circular_introduced"
    LAYER_VIOLATION = "layer_violation"


@dataclass
class DependencyChange:
    """Represents a change in module dependencies."""
    change_type: DependencyChangeType
    source_module: str
    target_module: str
    source_file: str
    line_number: Optional[int] = None
    old_imports: List[str] = field(default_factory=list)
    new_imports: List[str] = field(default_factory=list)
    is_circular: bool = False
    violates_layer: bool = False


@dataclass
class CircularDependency:
    """Represents a circular dependency introduced by the patch."""
    cycle_path: List[str]
    introduced_edge: Tuple[str, str]
    severity: Severity
    description: str


@dataclass
class LayerViolation:
    """Represents a violation of architectural layers."""
    source_layer: str
    target_layer: str
    source_module: str
    target_module: str
    source_file: str
    line_number: Optional[int]
    description: str


@dataclass
class CouplingMetrics:
    """Metrics for module coupling analysis."""
    afferent_coupling: int  # Number of modules that depend on this module
    efferent_coupling: int  # Number of modules this module depends on
    instability: float  # Efferent / (Afferent + Efferent)
    abstractness: float  # Abstract types / Total types
    distance_from_main: float  # |Abstractness + Instability - 1|

    @property
    def is_in_zone_of_pain(self) -> bool:
        """Zone of pain: too concrete and too stable."""
        return self.abstractness < 0.2 and self.instability < 0.2

    @property
    def is_in_zone_of_uselessness(self) -> bool:
        """Zone of uselessness: too abstract and too unstable."""
        return self.abstractness > 0.8 and self.instability > 0.8


@dataclass
class DependencyAnalysisResult:
    """Complete dependency analysis result."""
    dependency_changes: List[DependencyChange]
    circular_dependencies: List[CircularDependency]
    layer_violations: List[LayerViolation]
    coupling_before: Dict[str, CouplingMetrics]
    coupling_after: Dict[str, CouplingMetrics]
    findings: List[Finding]
    new_dependencies_count: int
    removed_dependencies_count: int
    affected_modules: Set[str]


class PatchDependencyAnalyzer:
    """
    Analyzes dependency changes introduced by a patch.

    Detects:
    - New/removed module dependencies
    - Circular dependency introduction
    - Architectural layer violations
    - Coupling metric changes
    """

    # Architectural layers (from high to low level)
    # Higher layers should not depend on lower layers
    ARCHITECTURAL_LAYERS = {
        'presentation': 4,  # UI, controllers
        'api': 3,           # API endpoints, routes
        'service': 2,       # Business logic
        'domain': 1,        # Domain models
        'infrastructure': 0  # Database, external services
    }

    # Layer detection patterns
    LAYER_PATTERNS = {
        'presentation': ['controller', 'view', 'ui', 'component', 'page'],
        'api': ['api', 'route', 'endpoint', 'handler'],
        'service': ['service', 'usecase', 'manager', 'facade'],
        'domain': ['model', 'entity', 'domain', 'aggregate'],
        'infrastructure': ['repository', 'dao', 'adapter', 'client', 'db']
    }

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        """
        Initialize the dependency analyzer.

        Args:
            conn: DuckDB connection with CPG loaded
        """
        self.conn = conn
        self._module_dependencies: Dict[str, Set[str]] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}

    def analyze_dependency_changes(
        self,
        patch: PatchContext,
        delta_cpg: DeltaCPG
    ) -> DependencyAnalysisResult:
        """
        Analyze how the patch affects module dependencies.

        Args:
            patch: The patch context
            delta_cpg: Delta CPG with changes

        Returns:
            Complete dependency analysis result
        """
        logger.info(f"Analyzing dependency changes for patch {patch.patch_id}")

        findings: List[Finding] = []
        dependency_changes: List[DependencyChange] = []
        circular_dependencies: List[CircularDependency] = []
        layer_violations: List[LayerViolation] = []
        affected_modules: Set[str] = set()

        # Build current dependency graph
        self._build_dependency_graph()

        # Get coupling metrics before
        coupling_before = self._compute_coupling_metrics()

        # Analyze each changed file for dependency changes
        for file_diff in patch.files:
            module = self._file_to_module(file_diff.path)
            affected_modules.add(module)

            # Find import changes in this file
            file_dep_changes = self._analyze_file_dependencies(
                file_diff.path,
                delta_cpg
            )
            dependency_changes.extend(file_dep_changes)

            # Check for new imports
            for change in file_dep_changes:
                if change.change_type == DependencyChangeType.ADDED:
                    target_module = change.target_module

                    # Check for circular dependency
                    cycle = self._check_circular_dependency(module, target_module)
                    if cycle:
                        circular_dep = CircularDependency(
                            cycle_path=cycle,
                            introduced_edge=(module, target_module),
                            severity=Severity.HIGH,
                            description=f"New import introduces circular dependency: {' -> '.join(cycle)}"
                        )
                        circular_dependencies.append(circular_dep)
                        change.is_circular = True

                        findings.append(Finding(
                            category=FindingCategory.ARCHITECTURE,
                            severity=Severity.HIGH,
                            title="Circular Dependency Introduced",
                            description=circular_dep.description,
                            location=f"{change.source_file}:{change.line_number or 0}",
                            recommendation="Refactor to break the circular dependency using dependency inversion or extracting shared interfaces",
                            confidence=0.95
                        ))

                    # Check for layer violation
                    violation = self._check_layer_violation(
                        module, target_module,
                        change.source_file,
                        change.line_number
                    )
                    if violation:
                        layer_violations.append(violation)
                        change.violates_layer = True

                        findings.append(Finding(
                            category=FindingCategory.ARCHITECTURE,
                            severity=Severity.MEDIUM,
                            title="Architectural Layer Violation",
                            description=violation.description,
                            location=f"{change.source_file}:{change.line_number or 0}",
                            recommendation=f"Move dependency to {violation.source_layer} layer or use dependency injection",
                            confidence=0.85
                        ))

        # Simulate dependency graph with changes
        simulated_graph = self._simulate_dependency_changes(dependency_changes)

        # Compute coupling metrics after
        coupling_after = self._compute_coupling_metrics_from_graph(simulated_graph)

        # Check for coupling degradation
        for module in affected_modules:
            if module in coupling_before and module in coupling_after:
                before = coupling_before[module]
                after = coupling_after[module]

                # Check if module moved into zone of pain
                if not before.is_in_zone_of_pain and after.is_in_zone_of_pain:
                    findings.append(Finding(
                        category=FindingCategory.ARCHITECTURE,
                        severity=Severity.MEDIUM,
                        title="Module Moving Into Zone of Pain",
                        description=f"Module '{module}' is becoming too concrete and stable. Consider adding abstractions.",
                        location=module,
                        recommendation="Add interfaces or abstract classes to increase abstractness",
                        confidence=0.75
                    ))

                # Check for significant instability increase
                instability_delta = after.instability - before.instability
                if instability_delta > 0.3:
                    findings.append(Finding(
                        category=FindingCategory.ARCHITECTURE,
                        severity=Severity.LOW,
                        title="Significant Instability Increase",
                        description=f"Module '{module}' instability increased by {instability_delta:.2f}",
                        location=module,
                        recommendation="Review new dependencies for necessity",
                        confidence=0.70
                    ))

        # Count changes
        new_deps = sum(1 for c in dependency_changes if c.change_type == DependencyChangeType.ADDED)
        removed_deps = sum(1 for c in dependency_changes if c.change_type == DependencyChangeType.REMOVED)

        logger.info(
            f"Dependency analysis complete: {new_deps} new, {removed_deps} removed, "
            f"{len(circular_dependencies)} circular, {len(layer_violations)} violations"
        )

        return DependencyAnalysisResult(
            dependency_changes=dependency_changes,
            circular_dependencies=circular_dependencies,
            layer_violations=layer_violations,
            coupling_before=coupling_before,
            coupling_after=coupling_after,
            findings=findings,
            new_dependencies_count=new_deps,
            removed_dependencies_count=removed_deps,
            affected_modules=affected_modules
        )

    def _build_dependency_graph(self) -> None:
        """Build the current dependency graph from CPG."""
        query = """
        SELECT DISTINCT
            n1.filename as source_file,
            n2.filename as target_file
        FROM cpg_nodes n1
        JOIN cpg_edges e ON n1.id = e.src
        JOIN cpg_nodes n2 ON e.dst = n2.id
        WHERE e.edge_type = 'IMPORTS'
          AND n1.filename IS NOT NULL
          AND n2.filename IS NOT NULL
          AND n1.filename != n2.filename
        """

        try:
            result = self.conn.execute(query).fetchall()

            self._dependency_graph = {}
            for source_file, target_file in result:
                source_module = self._file_to_module(source_file)
                target_module = self._file_to_module(target_file)

                if source_module not in self._dependency_graph:
                    self._dependency_graph[source_module] = set()
                self._dependency_graph[source_module].add(target_module)

        except Exception as e:
            logger.warning(f"Could not build dependency graph: {e}")
            # Try alternative query using CALL edges as proxy
            self._build_dependency_graph_from_calls()

    def _build_dependency_graph_from_calls(self) -> None:
        """Build dependency graph from call edges as fallback."""
        query = """
        SELECT DISTINCT
            caller.filename as source_file,
            callee.filename as target_file
        FROM cpg_nodes caller
        JOIN cpg_edges call_edge ON caller.id = call_edge.src
        JOIN cpg_nodes call_site ON call_edge.dst = call_site.id
        JOIN cpg_edges ref_edge ON call_site.id = ref_edge.src
        JOIN cpg_nodes callee ON ref_edge.dst = callee.id
        WHERE call_edge.edge_type = 'AST'
          AND call_site.node_type = 'CALL'
          AND callee.node_type = 'METHOD'
          AND caller.filename IS NOT NULL
          AND callee.filename IS NOT NULL
          AND caller.filename != callee.filename
        """

        try:
            result = self.conn.execute(query).fetchall()

            self._dependency_graph = {}
            for source_file, target_file in result:
                source_module = self._file_to_module(source_file)
                target_module = self._file_to_module(target_file)

                if source_module not in self._dependency_graph:
                    self._dependency_graph[source_module] = set()
                self._dependency_graph[source_module].add(target_module)

        except Exception as e:
            logger.warning(f"Could not build dependency graph from calls: {e}")
            self._dependency_graph = {}

    def _file_to_module(self, filepath: str) -> str:
        """Convert filepath to module name."""
        if not filepath:
            return "unknown"

        # Remove common prefixes
        for prefix in ['src/', 'lib/', 'app/', 'pkg/']:
            if filepath.startswith(prefix):
                filepath = filepath[len(prefix):]
                break

        # Get directory as module (or file for single-file modules)
        parts = filepath.replace('\\', '/').split('/')
        if len(parts) > 1:
            return parts[0]  # Top-level directory as module
        else:
            # Single file - use filename without extension
            return parts[0].rsplit('.', 1)[0]

    def _analyze_file_dependencies(
        self,
        filepath: str,
        delta_cpg: DeltaCPG
    ) -> List[DependencyChange]:
        """Analyze dependency changes in a single file."""
        changes: List[DependencyChange] = []
        source_module = self._file_to_module(filepath)

        # Find added import nodes
        added_imports = [
            node for node in delta_cpg.nodes
            if node.change_type.value == 'added'
            and node.filename == filepath
            and node.node_type in ('IMPORT', 'NAMESPACE_BLOCK', 'INCLUDE')
        ]

        for imp in added_imports:
            # Extract target module from import
            target = self._extract_import_target(imp.name or imp.code or '')
            if target:
                changes.append(DependencyChange(
                    change_type=DependencyChangeType.ADDED,
                    source_module=source_module,
                    target_module=target,
                    source_file=filepath,
                    line_number=imp.line_number,
                    new_imports=[imp.name or imp.code or '']
                ))

        # Find deleted import nodes
        deleted_imports = [
            node for node in delta_cpg.nodes
            if node.change_type.value == 'deleted'
            and node.filename == filepath
            and node.node_type in ('IMPORT', 'NAMESPACE_BLOCK', 'INCLUDE')
        ]

        for imp in deleted_imports:
            target = self._extract_import_target(imp.name or imp.code or '')
            if target:
                changes.append(DependencyChange(
                    change_type=DependencyChangeType.REMOVED,
                    source_module=source_module,
                    target_module=target,
                    source_file=filepath,
                    line_number=imp.line_number,
                    old_imports=[imp.name or imp.code or '']
                ))

        return changes

    def _extract_import_target(self, import_stmt: str) -> Optional[str]:
        """Extract target module from import statement."""
        import re

        # Python: from x import y, import x
        if match := re.match(r'(?:from\s+)?(\w+(?:\.\w+)*)', import_stmt):
            parts = match.group(1).split('.')
            return parts[0]  # Top-level module

        # JavaScript/TypeScript: import x from 'module'
        if match := re.search(r'from\s+[\'"]([^\'"/]+)', import_stmt):
            return match.group(1)

        # C/C++: #include <header> or #include "header"
        if match := re.search(r'#include\s*[<"]([^>"]+)', import_stmt):
            header = match.group(1)
            return header.split('/')[0] if '/' in header else header.rsplit('.', 1)[0]

        # Java: import package.Class
        if match := re.match(r'import\s+(?:static\s+)?(\w+)', import_stmt):
            return match.group(1)

        return None

    def _check_circular_dependency(
        self,
        source: str,
        target: str
    ) -> Optional[List[str]]:
        """
        Check if adding an edge from source to target creates a cycle.

        Returns the cycle path if found, None otherwise.
        """
        # Check if there's already a path from target back to source
        visited: Set[str] = set()
        path: List[str] = []

        def dfs(current: str) -> Optional[List[str]]:
            if current == source:
                return path + [current]

            if current in visited:
                return None

            visited.add(current)
            path.append(current)

            for neighbor in self._dependency_graph.get(current, set()):
                result = dfs(neighbor)
                if result:
                    return result

            path.pop()
            return None

        # Start DFS from target
        cycle = dfs(target)
        if cycle:
            return [source] + cycle

        return None

    def _check_layer_violation(
        self,
        source_module: str,
        target_module: str,
        source_file: str,
        line_number: Optional[int]
    ) -> Optional[LayerViolation]:
        """Check if dependency violates architectural layers."""
        source_layer = self._detect_layer(source_module, source_file)
        target_layer = self._detect_layer(target_module, '')

        if source_layer is None or target_layer is None:
            return None

        source_level = self.ARCHITECTURAL_LAYERS.get(source_layer, -1)
        target_level = self.ARCHITECTURAL_LAYERS.get(target_layer, -1)

        # Violation: lower layer depending on higher layer
        if source_level < target_level:
            return LayerViolation(
                source_layer=source_layer,
                target_layer=target_layer,
                source_module=source_module,
                target_module=target_module,
                source_file=source_file,
                line_number=line_number,
                description=(
                    f"'{source_layer}' layer ({source_module}) should not depend on "
                    f"'{target_layer}' layer ({target_module})"
                )
            )

        return None

    def _detect_layer(self, module: str, filepath: str) -> Optional[str]:
        """Detect which architectural layer a module belongs to."""
        module_lower = module.lower()
        filepath_lower = filepath.lower()

        for layer, patterns in self.LAYER_PATTERNS.items():
            for pattern in patterns:
                if pattern in module_lower or pattern in filepath_lower:
                    return layer

        return None

    def _simulate_dependency_changes(
        self,
        changes: List[DependencyChange]
    ) -> Dict[str, Set[str]]:
        """Simulate dependency graph after applying changes."""
        # Deep copy current graph
        simulated = {k: v.copy() for k, v in self._dependency_graph.items()}

        for change in changes:
            if change.change_type == DependencyChangeType.ADDED:
                if change.source_module not in simulated:
                    simulated[change.source_module] = set()
                simulated[change.source_module].add(change.target_module)
            elif change.change_type == DependencyChangeType.REMOVED:
                if change.source_module in simulated:
                    simulated[change.source_module].discard(change.target_module)

        return simulated

    def _compute_coupling_metrics(self) -> Dict[str, CouplingMetrics]:
        """Compute coupling metrics for all modules."""
        return self._compute_coupling_metrics_from_graph(self._dependency_graph)

    def _compute_coupling_metrics_from_graph(
        self,
        graph: Dict[str, Set[str]]
    ) -> Dict[str, CouplingMetrics]:
        """Compute coupling metrics from a dependency graph."""
        metrics: Dict[str, CouplingMetrics] = {}

        # Get all modules
        all_modules: Set[str] = set(graph.keys())
        for deps in graph.values():
            all_modules.update(deps)

        # Compute afferent coupling (who depends on me)
        afferent: Dict[str, int] = {m: 0 for m in all_modules}
        for source, targets in graph.items():
            for target in targets:
                afferent[target] = afferent.get(target, 0) + 1

        # Compute efferent coupling (who do I depend on)
        efferent: Dict[str, int] = {}
        for module in all_modules:
            efferent[module] = len(graph.get(module, set()))

        # Compute metrics for each module
        for module in all_modules:
            aff = afferent.get(module, 0)
            eff = efferent.get(module, 0)

            # Instability
            total = aff + eff
            instability = eff / total if total > 0 else 0.0

            # Abstractness (estimate based on naming - would need full analysis)
            abstractness = self._estimate_abstractness(module)

            # Distance from main sequence
            distance = abs(abstractness + instability - 1)

            metrics[module] = CouplingMetrics(
                afferent_coupling=aff,
                efferent_coupling=eff,
                instability=instability,
                abstractness=abstractness,
                distance_from_main=distance
            )

        return metrics

    def _estimate_abstractness(self, module: str) -> float:
        """
        Estimate module abstractness based on naming patterns.

        In a full implementation, this would analyze the actual
        abstract vs concrete types in the module.
        """
        abstract_patterns = ['interface', 'abstract', 'base', 'protocol', 'contract']
        module_lower = module.lower()

        for pattern in abstract_patterns:
            if pattern in module_lower:
                return 0.8

        # Query CPG for abstract types in module
        try:
            query = """
            SELECT
                COUNT(*) FILTER (WHERE n.code LIKE '%abstract%' OR n.code LIKE '%interface%') as abstract_count,
                COUNT(*) as total_count
            FROM cpg_nodes n
            WHERE n.node_type = 'TYPE_DECL'
              AND n.filename LIKE ?
            """
            result = self.conn.execute(query, [f"%{module}%"]).fetchone()
            if result and result[1] > 0:
                return result[0] / result[1]
        except Exception:
            pass

        return 0.3  # Default medium abstractness

    def get_module_dependencies(self, module: str) -> Dict[str, any]:
        """Get detailed dependency info for a specific module."""
        if not self._dependency_graph:
            self._build_dependency_graph()

        deps_out = self._dependency_graph.get(module, set())
        deps_in = {
            m for m, targets in self._dependency_graph.items()
            if module in targets
        }

        metrics = self._compute_coupling_metrics()
        module_metrics = metrics.get(module)

        return {
            'module': module,
            'depends_on': list(deps_out),
            'depended_by': list(deps_in),
            'metrics': {
                'afferent_coupling': module_metrics.afferent_coupling if module_metrics else 0,
                'efferent_coupling': module_metrics.efferent_coupling if module_metrics else 0,
                'instability': module_metrics.instability if module_metrics else 0.0,
                'abstractness': module_metrics.abstractness if module_metrics else 0.0,
                'distance_from_main': module_metrics.distance_from_main if module_metrics else 0.0
            } if module_metrics else None
        }

    def find_all_cycles(self) -> List[List[str]]:
        """Find all cycles in the dependency graph using Tarjan's algorithm."""
        if not self._dependency_graph:
            self._build_dependency_graph()

        index_counter = [0]
        stack: List[str] = []
        lowlinks: Dict[str, int] = {}
        index: Dict[str, int] = {}
        on_stack: Set[str] = set()
        sccs: List[List[str]] = []

        def strongconnect(node: str):
            index[node] = index_counter[0]
            lowlinks[node] = index_counter[0]
            index_counter[0] += 1
            stack.append(node)
            on_stack.add(node)

            for successor in self._dependency_graph.get(node, set()):
                if successor not in index:
                    strongconnect(successor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[successor])
                elif successor in on_stack:
                    lowlinks[node] = min(lowlinks[node], index[successor])

            if lowlinks[node] == index[node]:
                scc: List[str] = []
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    scc.append(w)
                    if w == node:
                        break
                if len(scc) > 1:  # Only include actual cycles
                    sccs.append(scc)

        for node in self._dependency_graph:
            if node not in index:
                strongconnect(node)

        return sccs
