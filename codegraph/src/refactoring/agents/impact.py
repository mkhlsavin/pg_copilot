"""Impact Analyzer Agent.

Analyzes change impact and dependencies for refactoring planning.
"""
import logging
from datetime import datetime
from typing import List, Optional

from .models import CodeSmellFinding, DependencyInfo, ImpactAnalysis
from ...services.cpg_query_service import CPGQueryService

logger = logging.getLogger(__name__)


class ImpactAnalyzer:
    """
    Analyzes change impact and dependencies.

    Responsibilities:
    - Find method dependencies (callers and callees)
    - Calculate impact scores for changes
    - Identify affected files and modules
    - Assess refactoring risk
    """

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

    def analyze_method_impact(
        self,
        method_name: str,
        filename: Optional[str] = None
    ) -> ImpactAnalysis:
        """
        Analyze the impact of changing a specific method.

        Args:
            method_name: Method to analyze
            filename: Optional file filter

        Returns:
            Impact analysis results
        """
        # Find direct callers using call_containment table
        direct_query = """
            SELECT DISTINCT
                c.containing_method_id AS id,
                c.containing_method_name AS caller_name,
                c.filename AS caller_file
            FROM call_containment c
            WHERE c.callee_name = ?
            LIMIT 50;
        """

        try:
            direct_results = self.cpg.execute_query(direct_query, (method_name,))
            direct_dependents = [r['caller_name'] for r in direct_results]
            affected_files = list(set(r['caller_file'] for r in direct_results))

            # Estimate indirect dependents (callers of callers)
            indirect_dependents = []
            for caller in direct_dependents[:5]:  # Limit to avoid explosion
                indirect_query = """
                    SELECT DISTINCT c.containing_method_name AS name
                    FROM call_containment c
                    WHERE c.callee_name = ?
                    LIMIT 10;
                """
                indirect_results = self.cpg.execute_query(indirect_query, (caller,))
                indirect_dependents.extend([r['name'] for r in indirect_results])

            # Calculate impact score based on dependency count
            impact_score = min(
                (len(direct_dependents) * 0.1 + len(indirect_dependents) * 0.05),
                1.0
            )

            # Determine risk level
            if impact_score > 0.7 or len(direct_dependents) > 20:
                risk_level = "high"
            elif impact_score > 0.4 or len(direct_dependents) > 10:
                risk_level = "medium"
            else:
                risk_level = "low"

            # Estimate test effort (proportional to dependents)
            estimated_test_effort = (
                len(direct_dependents) * 0.25 + len(indirect_dependents) * 0.1
            )

            analysis = ImpactAnalysis(
                analysis_id=f"IMPACT_{method_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                target_method=method_name,
                target_file=filename or "unknown",
                direct_dependents=direct_dependents,
                indirect_dependents=list(set(indirect_dependents)),
                affected_files=affected_files,
                impact_score=impact_score,
                risk_level=risk_level,
                estimated_test_effort=estimated_test_effort
            )

            logger.info(
                f"Impact analysis for {method_name}: "
                f"{len(direct_dependents)} direct dependents, risk={risk_level}"
            )
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing impact for {method_name}: {e}")
            return ImpactAnalysis(
                analysis_id=f"IMPACT_{method_name}_ERROR",
                target_method=method_name,
                target_file=filename or "unknown",
                direct_dependents=[],
                indirect_dependents=[],
                affected_files=[],
                impact_score=0.0,
                risk_level="unknown",
                estimated_test_effort=0.0
            )

    def analyze_bulk_impact(
        self,
        findings: List[CodeSmellFinding],
        limit: int = 20
    ) -> List[ImpactAnalysis]:
        """
        Analyze impact for multiple findings.

        Args:
            findings: Code smell findings to analyze
            limit: Max analyses to perform

        Returns:
            List of impact analyses
        """
        analyses = []

        for finding in findings[:limit]:
            analysis = self.analyze_method_impact(
                finding.method_name,
                finding.filename
            )
            analyses.append(analysis)

        logger.info(f"Analyzed impact for {len(analyses)} findings")
        return analyses

    def find_dependencies(
        self,
        method_name: str,
        depth: int = 2
    ) -> List[DependencyInfo]:
        """
        Find dependencies for a method (both callers and callees).

        Args:
            method_name: Method to analyze
            depth: Dependency depth (1=direct, 2=include indirect)

        Returns:
            List of dependency relationships
        """
        dependencies = []

        # Find what this method calls using call_containment
        callees_query = """
            SELECT DISTINCT
                c.containing_method_name AS from_method,
                c.filename AS from_file,
                c.callee_name AS to_method,
                'calls' AS dep_type
            FROM call_containment c
            WHERE c.containing_method_name = ?
            LIMIT 30;
        """

        try:
            callees = self.cpg.execute_query(callees_query, (method_name,))

            for idx, callee in enumerate(callees):
                dep = DependencyInfo(
                    dependency_id=f"DEP_{idx:03d}",
                    from_method=callee['from_method'],
                    from_file=callee['from_file'],
                    to_method=callee['to_method'],
                    to_file="unknown",
                    dependency_type="calls",
                    strength="medium"
                )
                dependencies.append(dep)

            logger.info(f"Found {len(dependencies)} dependencies for {method_name}")
            return dependencies

        except Exception as e:
            logger.error(f"Error finding dependencies for {method_name}: {e}")
            return []
