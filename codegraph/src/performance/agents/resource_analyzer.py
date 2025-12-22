"""
Resource Analyzer Agent for Performance Analysis

Analyzes resource usage patterns:
- Method complexity and call patterns
- Memory and CPU impact estimation
- I/O operation identification
- Resource intensity scoring
"""

import logging
from typing import List, Optional
from datetime import datetime

from .models import ResourceUsage, BottleneckFinding
from ...services.cpg_query_service import CPGQueryService

logger = logging.getLogger(__name__)


class ResourceAnalyzer:
    """
    Analyzes resource usage patterns

    Responsibilities:
    - Analyze method complexity and call patterns
    - Estimate memory and CPU impact
    - Identify I/O intensive operations
    - Calculate resource intensity scores
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

    def analyze_method_resources(
        self,
        method_name: str,
        filename: Optional[str] = None
    ) -> ResourceUsage:
        """
        Analyze resource usage for a specific method

        Args:
            method_name: Method to analyze
            filename: Optional file filter

        Returns:
            Resource usage analysis
        """
        # Use correct schema: nodes_method and edges_call instead of methods/calls
        query = """
            SELECT
                m.id,
                m.name,
                m.filename,
                ANY_VALUE(COALESCE(m.hash, '')) AS cyclomatic_complexity,
                COUNT(DISTINCT ec.dst) AS call_count
            FROM nodes_method m
            LEFT JOIN nodes_call nc ON nc.containing_method_id = m.id
            LEFT JOIN edges_call ec ON ec.src = nc.id
            WHERE m.name = ?
            GROUP BY m.id, m.name, m.filename
            LIMIT 1;
        """

        try:
            results = self.cpg.execute_query(query, (method_name,))
            if not results:
                # Return default analysis if method not found
                return ResourceUsage(
                    analysis_id=f"RESOURCE_{method_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    method_name=method_name,
                    filename=filename or "unknown",
                    complexity_score=0,
                    call_count=0,
                    estimated_memory_impact="low",
                    estimated_cpu_impact="low",
                    io_operations=0,
                    resource_intensity=0.0
                )

            row = results[0]
            # cyclomatic_complexity might be a string (hash field), ensure it's numeric
            complexity_raw = row.get('cyclomatic_complexity', 0)
            try:
                complexity = int(complexity_raw) if complexity_raw else 0
            except (ValueError, TypeError):
                complexity = 0  # Default if not a valid number
            call_count = int(row.get('call_count', 0) or 0)

            # Estimate I/O operations based on called functions
            # Using call_containment table instead of calls/methods
            io_query = """
                SELECT COUNT(*) as io_count
                FROM call_containment c
                WHERE c.containing_method_name = ?
                  AND (c.callee_name LIKE '%read%'
                    OR c.callee_name LIKE '%write%'
                    OR c.callee_name LIKE '%query%'
                    OR c.callee_name LIKE '%fetch%'
                    OR c.callee_name LIKE '%execute%');
            """
            io_results = self.cpg.execute_query(io_query, (method_name,))
            io_count = io_results[0].get('io_count', 0) if io_results else 0

            # Calculate resource intensity (0.0 to 1.0)
            complexity_factor = min(complexity / 50.0, 1.0)  # Normalize to 0-1
            call_factor = min(call_count / 30.0, 1.0)
            io_factor = min(io_count / 10.0, 1.0)
            resource_intensity = (complexity_factor * 0.4 + call_factor * 0.3 + io_factor * 0.3)

            # Estimate impacts
            memory_impact = self._estimate_memory_impact(complexity, call_count)
            cpu_impact = self._estimate_cpu_impact(complexity, io_count)

            analysis = ResourceUsage(
                analysis_id=f"RESOURCE_{method_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                method_name=method_name,
                filename=row.get('filename', 'unknown'),
                complexity_score=complexity,
                call_count=call_count,
                estimated_memory_impact=memory_impact,
                estimated_cpu_impact=cpu_impact,
                io_operations=io_count,
                resource_intensity=resource_intensity
            )

            logger.info(f"Resource analysis for {method_name}: intensity={resource_intensity:.2f}, CPU={cpu_impact}, Memory={memory_impact}")
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing resources for {method_name}: {e}")
            return ResourceUsage(
                analysis_id=f"RESOURCE_{method_name}_ERROR",
                method_name=method_name,
                filename=filename or "unknown",
                complexity_score=0,
                call_count=0,
                estimated_memory_impact="unknown",
                estimated_cpu_impact="unknown",
                io_operations=0,
                resource_intensity=0.0
            )

    def _estimate_memory_impact(self, complexity: int, call_count: int) -> str:
        """Estimate memory impact based on complexity and calls"""
        score = complexity * 0.3 + call_count * 0.7
        if score > 30:
            return "high"
        elif score > 15:
            return "medium"
        else:
            return "low"

    def _estimate_cpu_impact(self, complexity: int, io_count: int) -> str:
        """Estimate CPU impact based on complexity and I/O"""
        score = complexity * 0.7 + io_count * 0.3
        if score > 25:
            return "high"
        elif score > 12:
            return "medium"
        else:
            return "low"

    def analyze_bulk_resources(
        self,
        findings: List[BottleneckFinding],
        limit: int = 20
    ) -> List[ResourceUsage]:
        """
        Analyze resources for multiple findings

        Args:
            findings: Bottleneck findings to analyze
            limit: Max analyses to perform

        Returns:
            List of resource usage analyses
        """
        analyses = []

        for finding in findings[:limit]:
            analysis = self.analyze_method_resources(
                finding.method_name,
                finding.filename
            )
            analyses.append(analysis)

        logger.info(f"Analyzed resources for {len(analyses)} methods")
        return analyses


__all__ = ['ResourceAnalyzer']
