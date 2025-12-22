"""
Subsystem Mapper for Architecture Queries

Maps queries to subsystems for architecture analysis.
Helps with dependency and subsystem explanation scenarios.
"""

import logging
from typing import List, Dict

from .models import RetrievalResult
from .domain_plugin import get_subsystems

logger = logging.getLogger(__name__)


class SubsystemMapper:
    """
    Maps queries to PostgreSQL subsystems for architecture analysis.

    Helps with scenarios 11 (Dependencies) and 13 (Subsystem Explanation)
    by identifying which subsystem(s) a query relates to.
    """

    def __init__(self, cpg_service):
        self.cpg = cpg_service

    def identify_subsystem(self, query_text: str) -> List[Dict]:
        """
        Identify which subsystem(s) a query relates to.

        Args:
            query_text: User's query text

        Returns:
            List of matching subsystems with confidence scores
        """
        query_lower = query_text.lower()
        matches = []

        subsystems = get_subsystems()
        for subsystem, info in subsystems.items():
            score = 0
            matched_keywords = []

            # Check keywords
            for kw in info.get('keywords', []):
                if kw.lower() in query_lower:
                    score += 10
                    matched_keywords.append(kw)

            # Check patterns
            for pattern in info['patterns']:
                if pattern.lower() in query_lower:
                    score += 20
                    matched_keywords.append(pattern)

            if score > 0:
                matches.append({
                    'subsystem': subsystem,
                    'score': score,
                    'description': info['description'],
                    'matched_keywords': matched_keywords
                })

        # Sort by score
        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches

    def retrieve_subsystem_methods(
        self,
        subsystem: str,
        limit: int = 50
    ) -> List[RetrievalResult]:
        """
        Retrieve methods belonging to a specific subsystem.

        Args:
            subsystem: Subsystem name (e.g., 'executor', 'parser')
            limit: Maximum results

        Returns:
            List of RetrievalResult with methods from that subsystem
        """
        subsystems = get_subsystems()
        if subsystem not in subsystems:
            logger.warning(f"Unknown subsystem: {subsystem}")
            return []

        info = subsystems[subsystem]

        # Build pattern matching conditions
        pattern_conditions = []
        for pattern in info['patterns']:
            pattern_conditions.append(f"m.filename LIKE '%{pattern}%'")

        if not pattern_conditions:
            return []

        pattern_where = ' OR '.join(pattern_conditions)

        query = f"""
            SELECT DISTINCT
                m.id,
                m.name,
                m.full_name,
                m.filename,
                m.line_number,
                (m.line_number_end - m.line_number) AS line_count,
                '{subsystem}' AS subsystem
            FROM nodes_method m
            WHERE ({pattern_where})
            AND m.name NOT LIKE 'test_%'
            AND m.line_number_end > 0
            ORDER BY line_count DESC
            LIMIT ?;
        """

        try:
            results = self.cpg.execute_query(query, (limit,))

            retrieval_results = []
            for i, row in enumerate(results):
                score = 1.0 - (i / max(len(results), 1))

                content = f"{row.get('name', 'unknown')} - {row.get('filename', 'unknown')}:{row.get('line_number', 0)}"
                if row.get('line_count'):
                    content += f" ({row['line_count']} lines)"

                retrieval_results.append(RetrievalResult(
                    id=f"subsystem_{subsystem}_{row.get('id', i)}",
                    content=content,
                    score=score,
                    source="graph",
                    node_id=row.get('id'),
                    metadata={
                        'subsystem': subsystem,
                        'name': row.get('name'),
                        'full_name': row.get('full_name'),
                        'filename': row.get('filename'),
                        'line_number': row.get('line_number'),
                        'line_count': row.get('line_count')
                    }
                ))

            return retrieval_results

        except Exception as e:
            logger.error(f"Subsystem retrieval failed for {subsystem}: {e}")
            return []

    def retrieve_subsystem_dependencies(
        self,
        subsystem: str,
        limit: int = 50
    ) -> List[RetrievalResult]:
        """
        Find dependencies between a subsystem and other subsystems.

        Args:
            subsystem: Subsystem name
            limit: Maximum results

        Returns:
            List of RetrievalResult showing cross-subsystem dependencies
        """
        subsystems = get_subsystems()
        if subsystem not in subsystems:
            return []

        info = subsystems[subsystem]

        # Build pattern for this subsystem
        patterns = info['patterns']
        if not patterns:
            return []

        pattern_conditions = ' OR '.join([f"c.filename LIKE '%{p}%'" for p in patterns])

        query = f"""
            SELECT
                c.filename AS caller_file,
                c.containing_method_name AS caller_method,
                m.filename AS callee_file,
                c.callee_name AS callee_method,
                '{subsystem}' AS from_subsystem
            FROM call_containment c
            JOIN nodes_method m ON c.callee_name = m.name
            WHERE ({pattern_conditions})
            AND NOT ({' OR '.join([f"m.filename LIKE '%{p}%'" for p in patterns])})
            AND m.filename IS NOT NULL
            AND c.filename != m.filename
            GROUP BY c.filename, c.containing_method_name, m.filename, c.callee_name
            LIMIT ?;
        """

        try:
            results = self.cpg.execute_query(query, (limit,))

            retrieval_results = []
            for i, row in enumerate(results):
                score = 1.0 - (i / max(len(results), 1))

                content = f"{row.get('caller_method', 'unknown')} ({row.get('caller_file', '')}) -> {row.get('callee_method', 'unknown')} ({row.get('callee_file', '')})"

                retrieval_results.append(RetrievalResult(
                    id=f"dep_{subsystem}_{i}",
                    content=content,
                    score=score,
                    source="graph",
                    metadata={
                        'from_subsystem': subsystem,
                        'caller_file': row.get('caller_file'),
                        'caller_method': row.get('caller_method'),
                        'callee_file': row.get('callee_file'),
                        'callee_method': row.get('callee_method')
                    }
                ))

            return retrieval_results

        except Exception as e:
            logger.error(f"Subsystem dependency retrieval failed: {e}")
            return []


def create_subsystem_mapper(cpg_service) -> SubsystemMapper:
    """Factory function to create a SubsystemMapper."""
    return SubsystemMapper(cpg_service)


__all__ = ['SubsystemMapper', 'create_subsystem_mapper']
