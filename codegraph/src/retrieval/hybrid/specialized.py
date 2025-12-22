"""
Specialized Retriever for Code Quality Analysis

Provides specialized retrievers for dead code, complexity, duplicates,
entry points, and other code quality scenarios.
"""

import logging
from typing import List, Dict

from .models import RetrievalResult

logger = logging.getLogger(__name__)


class SpecializedRetriever:
    """
    Specialized retriever for code quality scenarios (dead code, complexity, duplicates).

    These scenarios require specific graph queries that target particular patterns
    rather than semantic or keyword-based search.
    """

    def __init__(self, cpg_service):
        """
        Initialize specialized retriever.

        Args:
            cpg_service: CPGQueryService instance for DuckDB queries
        """
        self.cpg = cpg_service
        logger.info("Specialized Retriever initialized for code quality analysis")

    def retrieve_dead_code(self, limit: int = 50) -> List[RetrievalResult]:
        """
        Find potentially dead (uncalled) functions.

        Uses call graph analysis to find methods that are never called.

        Returns:
            List of RetrievalResult with dead code candidates
        """
        query = """
            SELECT DISTINCT
                m.id,
                m.name,
                m.full_name,
                m.filename,
                m.line_number,
                (m.line_number_end - m.line_number) AS line_count,
                'dead_code' AS category
            FROM nodes_method m
            LEFT JOIN call_containment c ON c.callee_name = m.name
            WHERE c.callee_name IS NULL
            AND m.name NOT LIKE 'test_%'
            AND m.name NOT LIKE 'main'
            AND m.name NOT LIKE '%_init'
            AND m.name NOT LIKE '%_fini'
            AND m.name NOT LIKE '__attribute__%'
            AND (m.line_number_end - m.line_number) > 5
            AND m.line_number_end > 0
            ORDER BY line_count DESC
            LIMIT ?;
        """

        try:
            results = self.cpg.execute_query(query, (limit,))
            return self._convert_to_results(results, "dead_code")
        except Exception as e:
            logger.error(f"Dead code retrieval failed: {e}")
            return []

    def retrieve_high_complexity(self, limit: int = 50) -> List[RetrievalResult]:
        """
        Find methods with high complexity (based on line count as proxy).

        Since cyclomatic complexity isn't stored, uses line count as heuristic.

        Returns:
            List of RetrievalResult with high-complexity methods
        """
        query = """
            SELECT DISTINCT
                m.id,
                m.name,
                m.full_name,
                m.filename,
                m.line_number,
                (m.line_number_end - m.line_number) AS line_count,
                CASE
                    WHEN (m.line_number_end - m.line_number) > 200 THEN 'CRITICAL'
                    WHEN (m.line_number_end - m.line_number) > 100 THEN 'HIGH'
                    ELSE 'MEDIUM'
                END AS severity,
                'high_complexity' AS category
            FROM nodes_method m
            WHERE (m.line_number_end - m.line_number) > 50
            AND m.line_number_end > 0
            AND m.name NOT LIKE 'test_%'
            ORDER BY line_count DESC
            LIMIT ?;
        """

        try:
            results = self.cpg.execute_query(query, (limit,))
            return self._convert_to_results(results, "complexity")
        except Exception as e:
            logger.error(f"Complexity retrieval failed: {e}")
            return []

    def retrieve_long_methods(self, threshold: int = 50, limit: int = 50) -> List[RetrievalResult]:
        """
        Find methods exceeding line count threshold.

        Args:
            threshold: Minimum line count to include
            limit: Maximum results to return

        Returns:
            List of RetrievalResult with long methods
        """
        query = """
            SELECT DISTINCT
                m.id,
                m.name,
                m.full_name,
                m.filename,
                m.line_number,
                (m.line_number_end - m.line_number) AS line_count,
                'long_method' AS category
            FROM nodes_method m
            WHERE (m.line_number_end - m.line_number) > ?
            AND m.line_number_end > 0
            AND m.name NOT LIKE 'test_%'
            ORDER BY line_count DESC
            LIMIT ?;
        """

        try:
            results = self.cpg.execute_query(query, (threshold, limit))
            return self._convert_to_results(results, "long_method")
        except Exception as e:
            logger.error(f"Long method retrieval failed: {e}")
            return []

    def retrieve_duplicates(self, limit: int = 50) -> List[RetrievalResult]:
        """
        Find potential code duplicates based on similar method names.

        Note: True clone detection requires more sophisticated analysis.
        This is a heuristic approach based on naming patterns.

        Returns:
            List of RetrievalResult with duplicate candidates
        """
        query = """
            SELECT DISTINCT
                m1.id AS id,
                m1.name AS name,
                m1.full_name,
                m1.filename,
                m1.line_number,
                m2.name AS similar_to,
                m2.filename AS similar_file,
                'duplicate' AS category
            FROM nodes_method m1
            JOIN nodes_method m2 ON (
                m1.name LIKE m2.name || '%' OR m2.name LIKE m1.name || '%'
            )
            WHERE m1.id < m2.id
            AND m1.filename != m2.filename
            AND (m1.line_number_end - m1.line_number) > 10
            AND m1.line_number_end > 0
            AND m1.name NOT LIKE 'test_%'
            AND LENGTH(m1.name) > 5
            LIMIT ?;
        """

        try:
            results = self.cpg.execute_query(query, (limit,))
            return self._convert_to_results(results, "duplicate")
        except Exception as e:
            logger.error(f"Duplicate retrieval failed: {e}")
            return []

    def retrieve_entry_points(self, limit: int = 50) -> List[RetrievalResult]:
        """
        Find entry points and attack surface (methods called but calling nothing).

        Returns:
            List of RetrievalResult with entry point candidates
        """
        query = """
            SELECT DISTINCT
                m.id,
                m.name,
                m.full_name,
                m.filename,
                m.line_number,
                (m.line_number_end - m.line_number) AS line_count,
                COUNT(DISTINCT c.call_id) AS caller_count,
                'entry_point' AS category
            FROM nodes_method m
            JOIN call_containment c ON c.callee_name = m.name
            LEFT JOIN call_containment c2 ON c2.containing_method_name = m.name
            WHERE c2.call_id IS NULL
            AND m.name NOT LIKE 'test_%'
            GROUP BY m.id, m.name, m.full_name, m.filename, m.line_number, m.line_number_end
            HAVING COUNT(DISTINCT c.call_id) > 3
            ORDER BY caller_count DESC
            LIMIT ?;
        """

        try:
            results = self.cpg.execute_query(query, (limit,))
            return self._convert_to_results(results, "entry_point")
        except Exception as e:
            logger.error(f"Entry point retrieval failed: {e}")
            return []

    def retrieve_god_classes(self, limit: int = 50) -> List[RetrievalResult]:
        """
        Find potential god classes (files with many methods).

        Returns:
            List of RetrievalResult with god class candidates
        """
        query = """
            SELECT DISTINCT
                m.filename AS id,
                m.filename AS name,
                m.filename AS full_name,
                m.filename AS filename,
                MIN(m.line_number) AS line_number,
                COUNT(DISTINCT m.id) AS method_count,
                SUM(m.line_number_end - m.line_number) AS total_lines,
                'god_class' AS category
            FROM nodes_method m
            WHERE m.name NOT LIKE 'test_%'
            AND m.line_number_end > 0
            GROUP BY m.filename
            HAVING COUNT(DISTINCT m.id) > 30
               OR SUM(m.line_number_end - m.line_number) > 1000
            ORDER BY total_lines DESC
            LIMIT ?;
        """

        try:
            results = self.cpg.execute_query(query, (limit,))
            return self._convert_to_results(results, "god_class")
        except Exception as e:
            logger.error(f"God class retrieval failed: {e}")
            return []

    def _convert_to_results(
        self,
        raw_results: List[Dict],
        category: str
    ) -> List[RetrievalResult]:
        """Convert raw query results to RetrievalResult objects."""
        results = []
        for i, row in enumerate(raw_results):
            # Score based on position (first = best)
            score = 1.0 - (i / max(len(raw_results), 1))

            # Build content string
            name = row.get('name', 'unknown')
            filename = row.get('filename', 'unknown')
            line = row.get('line_number', 0)
            content = f"{name} - {filename}:{line}"

            if row.get('line_count'):
                content += f" ({row['line_count']} lines)"
            if row.get('similar_to'):
                content += f" [similar to {row['similar_to']}]"
            if row.get('method_count'):
                content += f" [{row['method_count']} methods]"

            results.append(RetrievalResult(
                id=f"{category}_{row.get('id', i)}",
                content=content,
                score=score,
                source="graph",
                node_id=row.get('id'),
                metadata={
                    'category': category,
                    'name': name,
                    'full_name': row.get('full_name'),
                    'filename': filename,
                    'line_number': line,
                    **{k: v for k, v in row.items() if k not in ['id', 'name', 'full_name', 'filename', 'line_number']}
                }
            ))

        return results


def create_specialized_retriever(cpg_service) -> SpecializedRetriever:
    """Factory function to create a SpecializedRetriever."""
    return SpecializedRetriever(cpg_service)


__all__ = ['SpecializedRetriever', 'create_specialized_retriever']
