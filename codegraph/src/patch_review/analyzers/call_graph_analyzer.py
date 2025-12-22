"""
Patch Call Graph Impact Analyzer

Extends the base CallGraphAnalyzer to compute patch-specific impact:
- Blast radius: How many methods are affected by changes
- Breaking changes: Signature changes that break callers
- Ripple effect: Cascading impact through call graph

Phase: Impact Analyzers (Phase 2)
"""

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from src.patch_review.models import (
    BlastRadius,
    BreakingChange,
    ChangedMethod,
    ChangeType,
    DeltaCPG,
    RippleEffect,
    Severity,
)

logger = logging.getLogger(__name__)


@dataclass
class CallGraphNode:
    """Node in the call graph with metadata"""
    method_name: str
    full_name: str
    filename: str
    callers: List[str] = field(default_factory=list)
    callees: List[str] = field(default_factory=list)
    is_changed: bool = False
    change_type: Optional[ChangeType] = None


class PatchCallGraphAnalyzer:
    """
    Analyzes call graph impact of patch changes.

    Computes:
    - Blast radius (direct and transitive callers/callees)
    - Breaking changes (signature incompatibilities)
    - Ripple effect (weighted impact propagation)
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
            # DuckDB connection
            self._execute = self._execute_duckdb
        elif hasattr(conn, 'execute_query'):
            self._execute = conn.execute_query
        elif hasattr(conn, 'execute_sql_dict'):
            self._execute = conn.execute_sql_dict
        else:
            # Fallback - just store it
            self._execute = lambda q, p=None: []

        # Cache for call graph data
        self._callers_cache: Dict[str, List[str]] = {}
        self._callees_cache: Dict[str, List[str]] = {}

        logger.info("PatchCallGraphAnalyzer initialized")

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

    def analyze_call_graph_impact(
        self,
        patch: Any,  # PatchContext
        delta_cpg: DeltaCPG
    ) -> 'CallGraphAnalysisResult':
        """
        Analyze complete call graph impact of a patch.

        Args:
            patch: The patch context
            delta_cpg: Delta CPG with changes

        Returns:
            CallGraphAnalysisResult with all impact data
        """
        from . import CallGraphAnalysisResult

        self.delta = delta_cpg

        # Compute blast radius for all changed methods
        blast_radius_map = {}
        for method in patch.changed_methods:
            br = self.compute_blast_radius([method])
            blast_radius_map[method.full_name or method.name] = br

        # Identify breaking changes
        breaking_changes = self.identify_breaking_changes(patch.changed_methods)

        # Compute ripple effects
        ripple_effects = {}
        for method in patch.changed_methods[:10]:  # Limit for performance
            re = self.compute_ripple_effect(method.name)
            ripple_effects[method.name] = re

        # Get centrality
        centrality = self.get_method_centrality(patch.changed_methods)

        return CallGraphAnalysisResult(
            blast_radius=blast_radius_map,
            breaking_changes=breaking_changes,
            ripple_effects=ripple_effects,
            affected_centrality=centrality,
            findings=[]
        )

    def set_delta(self, delta_cpg: DeltaCPG):
        """Set or update the delta CPG"""
        self.delta = delta_cpg
        # Clear caches when delta changes
        self._callers_cache.clear()
        self._callees_cache.clear()

    def compute_blast_radius(
        self,
        changed_methods: List[ChangedMethod],
        max_depth: int = 5
    ) -> BlastRadius:
        """
        Compute the blast radius of changed methods.

        Blast radius includes:
        - Direct callers: Methods that directly call changed methods
        - Indirect callers: Transitive callers up to max_depth
        - Direct callees: Methods called by changed methods
        - Indirect callees: Transitive callees up to max_depth
        - Affected files/subsystems

        Args:
            changed_methods: List of methods changed in the patch
            max_depth: Maximum depth for transitive analysis

        Returns:
            BlastRadius with complete impact information
        """
        if not changed_methods:
            return BlastRadius(
                changed_methods=[],
                direct_callers=[],
                indirect_callers=[],
                direct_callees=[],
                indirect_callees=[],
                affected_files=[],
                affected_subsystems=[],
                risk_score=0.0
            )

        changed_names = [m.method_name for m in changed_methods]
        logger.info(f"Computing blast radius for {len(changed_names)} changed methods")

        # Compute direct and indirect callers
        direct_callers: Set[str] = set()
        all_callers: Set[str] = set()

        for method_name in changed_names:
            # Direct callers
            direct = self._find_callers(method_name, direct_only=True)
            direct_callers.update(direct)

            # All transitive callers
            transitive = self._find_callers(method_name, max_depth=max_depth)
            all_callers.update(transitive)

        indirect_callers = all_callers - direct_callers - set(changed_names)

        # Compute direct and indirect callees
        direct_callees: Set[str] = set()
        all_callees: Set[str] = set()

        for method_name in changed_names:
            # Direct callees
            direct = self._find_callees(method_name, direct_only=True)
            direct_callees.update(direct)

            # All transitive callees
            transitive = self._find_callees(method_name, max_depth=max_depth)
            all_callees.update(transitive)

        indirect_callees = all_callees - direct_callees - set(changed_names)

        # Get affected files
        affected_files = self._get_affected_files(
            list(direct_callers | indirect_callers | direct_callees | indirect_callees)
        )

        # Group into subsystems (directories)
        affected_subsystems = self._group_into_subsystems(affected_files)

        # Calculate risk score
        risk_score = self._calculate_risk_score(
            changed_methods,
            direct_callers,
            indirect_callers,
            direct_callees,
            indirect_callees
        )

        blast_radius = BlastRadius(
            changed_methods=changed_names,
            direct_callers=sorted(direct_callers),
            indirect_callers=sorted(indirect_callers),
            direct_callees=sorted(direct_callees),
            indirect_callees=sorted(indirect_callees),
            affected_files=sorted(affected_files),
            affected_subsystems=sorted(affected_subsystems),
            risk_score=risk_score
        )

        logger.info(
            f"Blast radius computed: {len(direct_callers)} direct callers, "
            f"{len(indirect_callers)} indirect callers, "
            f"{len(direct_callees)} direct callees, "
            f"risk score: {risk_score:.2f}"
        )

        return blast_radius

    def identify_breaking_changes(
        self,
        changed_methods: List[ChangedMethod]
    ) -> List[BreakingChange]:
        """
        Identify signature changes that break callers.

        Checks for:
        - Parameter count changes
        - Parameter type changes
        - Return type changes
        - Removed methods with existing callers

        Args:
            changed_methods: List of changed methods

        Returns:
            List of breaking changes detected
        """
        breaking_changes: List[BreakingChange] = []

        for method in changed_methods:
            # Check for deleted methods
            if method.change_type == ChangeType.DELETED:
                callers = self._find_callers(method.method_name, direct_only=True)
                if callers:
                    breaking_changes.append(BreakingChange(
                        method_name=method.method_name,
                        breaking_type="method_removed",
                        old_signature=method.old_signature or method.method_name,
                        new_signature=None,
                        affected_callers=list(callers),
                        severity=Severity.CRITICAL if len(callers) > 5 else Severity.HIGH
                    ))

            # Check for signature changes
            elif method.change_type == ChangeType.MODIFIED:
                if method.old_signature and method.new_signature:
                    if method.old_signature != method.new_signature:
                        # Analyze the signature change
                        change_type, severity = self._analyze_signature_change(
                            method.old_signature,
                            method.new_signature
                        )

                        if change_type:
                            callers = self._find_callers(method.method_name, direct_only=True)
                            if callers:
                                breaking_changes.append(BreakingChange(
                                    method_name=method.method_name,
                                    breaking_type=change_type,
                                    old_signature=method.old_signature,
                                    new_signature=method.new_signature,
                                    affected_callers=list(callers),
                                    severity=severity
                                ))

        logger.info(f"Identified {len(breaking_changes)} breaking changes")
        return breaking_changes

    def compute_ripple_effect(
        self,
        method_name: str,
        max_depth: int = 5,
        decay_factor: float = 0.5
    ) -> RippleEffect:
        """
        Compute cascading ripple effect through call graph.

        Uses BFS traversal with exponentially decaying weights per depth level.
        Higher weight = more direct impact.

        Args:
            method_name: Starting method
            max_depth: Maximum traversal depth
            decay_factor: Weight decay per level (0.5 = halve each level)

        Returns:
            RippleEffect with affected methods and weights
        """
        affected: List[Tuple[str, int, float]] = []
        visited: Set[str] = {method_name}
        queue: deque = deque([(method_name, 0, 1.0)])

        while queue:
            current, depth, weight = queue.popleft()

            if depth > 0:  # Don't include the starting method
                affected.append((current, depth, weight))

            if depth < max_depth:
                # Get callers (upstream impact)
                callers = self._find_callers(current, direct_only=True)
                next_weight = weight * decay_factor

                for caller in callers:
                    if caller not in visited:
                        visited.add(caller)
                        queue.append((caller, depth + 1, next_weight))

        # Sort by weight (highest impact first)
        affected.sort(key=lambda x: x[2], reverse=True)

        total_weight = sum(w for _, _, w in affected)

        return RippleEffect(
            source_method=method_name,
            affected_methods=affected,
            max_depth=max_depth,
            total_weight=total_weight
        )

    def get_method_centrality(
        self,
        changed_methods: List[ChangedMethod]
    ) -> Dict[str, float]:
        """
        Get centrality scores for changed methods.

        High centrality = method is a critical hub in the call graph.

        Args:
            changed_methods: List of changed methods

        Returns:
            Dict mapping method name to centrality score
        """
        centrality: Dict[str, float] = {}

        for method in changed_methods:
            # Simple centrality: in-degree + out-degree
            callers = self._find_callers(method.method_name, direct_only=True)
            callees = self._find_callees(method.method_name, direct_only=True)

            # Normalize by total methods
            total_methods = self._get_total_method_count()
            if total_methods > 0:
                centrality[method.method_name] = (len(callers) + len(callees)) / total_methods
            else:
                centrality[method.method_name] = 0.0

        return centrality

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _find_callers(
        self,
        method_name: str,
        max_depth: int = 5,
        direct_only: bool = False
    ) -> Set[str]:
        """Find all methods that call the given method"""
        cache_key = f"{method_name}_{max_depth}_{direct_only}"
        if cache_key in self._callers_cache:
            return set(self._callers_cache[cache_key])

        if direct_only:
            query = """
                SELECT DISTINCT m.name AS caller_name
                FROM nodes_method m
                JOIN nodes_call nc ON nc.containing_method_id = m.id
                JOIN edges_call ec ON ec.src = nc.id
                JOIN nodes_method target ON ec.dst = target.id
                WHERE target.name = ?
                  AND m.name != ?
                LIMIT 100;
            """
            params = (method_name, method_name)
        else:
            query = """
                WITH RECURSIVE callers AS (
                    SELECT DISTINCT m.id AS caller_id, m.name AS caller_name, 1 AS depth
                    FROM nodes_method m
                    JOIN nodes_call nc ON nc.containing_method_id = m.id
                    JOIN edges_call ec ON ec.src = nc.id
                    JOIN nodes_method target ON ec.dst = target.id
                    WHERE target.name = ?

                    UNION

                    SELECT DISTINCT m.id, m.name, c.depth + 1
                    FROM nodes_method m
                    JOIN nodes_call nc ON nc.containing_method_id = m.id
                    JOIN edges_call ec ON ec.src = nc.id
                    JOIN callers c ON ec.dst = c.caller_id
                    WHERE c.depth < ?
                )
                SELECT DISTINCT caller_name FROM callers
                WHERE caller_name != ?
                LIMIT 200;
            """
            params = (method_name, max_depth, method_name)

        try:
            results = self._execute(query, params)
            callers = {r.get('caller_name', '') for r in results if r.get('caller_name')}

            # Also check call_containment table as fallback
            if not callers:
                fallback_query = """
                    SELECT DISTINCT containing_method_name AS caller_name
                    FROM call_containment
                    WHERE callee_name = ?
                      AND containing_method_name IS NOT NULL
                      AND containing_method_name != ''
                      AND containing_method_name != ?
                    LIMIT 100;
                """
                try:
                    fallback_results = self._execute(fallback_query, (method_name, method_name))
                    callers = {r.get('caller_name', '') for r in fallback_results if r.get('caller_name')}
                except Exception:
                    pass

            self._callers_cache[cache_key] = list(callers)
            return callers

        except Exception as e:
            logger.warning(f"Error finding callers for {method_name}: {e}")
            return set()

    def _find_callees(
        self,
        method_name: str,
        max_depth: int = 5,
        direct_only: bool = False
    ) -> Set[str]:
        """Find all methods called by the given method"""
        cache_key = f"callees_{method_name}_{max_depth}_{direct_only}"
        if cache_key in self._callees_cache:
            return set(self._callees_cache[cache_key])

        if direct_only:
            query = """
                SELECT DISTINCT target.name AS callee_name
                FROM nodes_method m
                JOIN nodes_call nc ON nc.containing_method_id = m.id
                JOIN edges_call ec ON ec.src = nc.id
                JOIN nodes_method target ON ec.dst = target.id
                WHERE m.name = ?
                  AND target.name != ?
                LIMIT 100;
            """
            params = (method_name, method_name)
        else:
            query = """
                WITH RECURSIVE callees AS (
                    SELECT DISTINCT target.id AS callee_id, target.name AS callee_name, 1 AS depth
                    FROM nodes_method m
                    JOIN nodes_call nc ON nc.containing_method_id = m.id
                    JOIN edges_call ec ON ec.src = nc.id
                    JOIN nodes_method target ON ec.dst = target.id
                    WHERE m.name = ?

                    UNION

                    SELECT DISTINCT target.id, target.name, c.depth + 1
                    FROM nodes_call nc
                    JOIN edges_call ec ON ec.src = nc.id
                    JOIN nodes_method target ON ec.dst = target.id
                    JOIN callees c ON nc.containing_method_id = c.callee_id
                    WHERE c.depth < ?
                )
                SELECT DISTINCT callee_name FROM callees
                WHERE callee_name != ?
                LIMIT 200;
            """
            params = (method_name, max_depth, method_name)

        try:
            results = self._execute(query, params)
            callees = {r.get('callee_name', '') for r in results if r.get('callee_name')}

            # Filter out operators and special names
            callees = {c for c in callees if c and not c.startswith('<') and c not in ('true', 'false', 'NULL')}

            self._callees_cache[cache_key] = list(callees)
            return callees

        except Exception as e:
            logger.warning(f"Error finding callees for {method_name}: {e}")
            return set()

    def _get_affected_files(self, method_names: List[str]) -> Set[str]:
        """Get files containing the given methods"""
        if not method_names:
            return set()

        # Build query with method names
        placeholders = ','.join(['?' for _ in method_names])
        query = f"""
            SELECT DISTINCT filename
            FROM nodes_method
            WHERE name IN ({placeholders})
              AND filename IS NOT NULL
        """

        try:
            results = self._execute(query, tuple(method_names))
            return {r.get('filename', '') for r in results if r.get('filename')}
        except Exception as e:
            logger.warning(f"Error getting affected files: {e}")
            return set()

    def _group_into_subsystems(self, files: Set[str]) -> Set[str]:
        """Group files into subsystem directories"""
        subsystems: Set[str] = set()

        for filepath in files:
            if not filepath:
                continue

            # Extract directory path
            parts = filepath.replace('\\', '/').rsplit('/', 1)
            if len(parts) > 1:
                directory = parts[0]
                # Get top-level subsystem (first 2 levels)
                dir_parts = directory.split('/')
                if len(dir_parts) >= 2:
                    subsystems.add('/'.join(dir_parts[:2]))
                else:
                    subsystems.add(directory)

        return subsystems

    def _calculate_risk_score(
        self,
        changed_methods: List[ChangedMethod],
        direct_callers: Set[str],
        indirect_callers: Set[str],
        direct_callees: Set[str],
        indirect_callees: Set[str]
    ) -> float:
        """
        Calculate risk score for the blast radius.

        Factors:
        - Number of changed methods
        - Number of callers (direct weighted more)
        - Number of callees
        - Whether critical/complex methods are affected
        """
        # Base score from change count
        change_score = min(1.0, len(changed_methods) / 10)

        # Caller impact (direct callers are higher risk)
        caller_score = min(1.0, (len(direct_callers) * 2 + len(indirect_callers)) / 50)

        # Callee impact
        callee_score = min(1.0, (len(direct_callees) + len(indirect_callees)) / 30)

        # Weighted combination
        risk_score = (
            change_score * 0.3 +
            caller_score * 0.5 +
            callee_score * 0.2
        )

        return min(1.0, risk_score)

    def _analyze_signature_change(
        self,
        old_sig: str,
        new_sig: str
    ) -> Tuple[Optional[str], Severity]:
        """
        Analyze signature change to determine breaking type.

        Returns:
            Tuple of (change_type, severity) or (None, None) if not breaking
        """
        import re

        # Extract parameter lists
        old_params = re.findall(r'\((.*?)\)', old_sig)
        new_params = re.findall(r'\((.*?)\)', new_sig)

        if not old_params or not new_params:
            return None, Severity.LOW

        old_param_list = [p.strip() for p in old_params[0].split(',') if p.strip()]
        new_param_list = [p.strip() for p in new_params[0].split(',') if p.strip()]

        # Check parameter count
        if len(new_param_list) < len(old_param_list):
            return "parameter_removed", Severity.HIGH
        elif len(new_param_list) > len(old_param_list):
            # Added parameters might have defaults - less severe
            return "parameter_added", Severity.MEDIUM

        # Check for type changes (simplified)
        for old_p, new_p in zip(old_param_list, new_param_list):
            if old_p != new_p:
                return "parameter_type_changed", Severity.HIGH

        return None, Severity.LOW

    def _get_total_method_count(self) -> int:
        """Get total number of methods in base CPG"""
        try:
            query = "SELECT COUNT(*) as total FROM nodes_method"
            results = self._execute(query)
            return results[0].get('total', 1000) if results else 1000
        except Exception:
            return 1000
