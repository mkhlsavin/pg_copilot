"""
Graph Search Module

Provides graph-based (DuckDB/CPG) search functionality.
"""

import logging
import asyncio
from typing import List, Dict

from .models import RetrievalResult

logger = logging.getLogger(__name__)


async def graph_search_async(
    cpg_service,
    query: str,
    top_k: int,
    **kwargs
) -> List[RetrievalResult]:
    """
    Graph search in DuckDB CPG (async wrapper).

    Args:
        cpg_service: CPGQueryService instance
        query: Search query (keywords or patterns)
        top_k: Number of results to return
        **kwargs: Additional parameters (domain, method_pattern, etc.)

    Returns:
        List of RetrievalResult objects from graph search
    """
    try:
        # Run in thread pool (DuckDB might block)
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            graph_search_sync,
            cpg_service,
            query,
            top_k,
            kwargs
        )
        return results

    except Exception as e:
        logger.error(f"Graph search failed: {e}", exc_info=True)
        return []


def graph_search_sync(
    cpg_service,
    query: str,
    top_k: int,
    kwargs: Dict
) -> List[RetrievalResult]:
    """Synchronous graph search implementation."""
    # Extract search parameters
    keywords = kwargs.get('keywords', [])

    # Build keyword list from query
    if not keywords:
        # Simple keyword extraction (can be improved with NLP)
        keywords = [w.lower() for w in query.split() if len(w) > 3]

    if not keywords:
        logger.warning("No keywords extracted from query for graph search")
        return []

    # Build SQL query for method search
    keyword_conditions = ' OR '.join([
        f"LOWER(m.name) LIKE '%{kw}%'" for kw in keywords[:5]
    ])

    sql_query = f"""
        SELECT
            m.id,
            m.name,
            m.fullName,
            m.signature,
            m.filename,
            m.lineNumber,
            COUNT(DISTINCT c.id) AS caller_count
        FROM nodes_method m
        LEFT JOIN edges_call ec ON ec.dst = m.id
        LEFT JOIN nodes_call c ON c.id = ec.src
        WHERE {keyword_conditions}
        GROUP BY m.id, m.name, m.fullName, m.signature, m.filename, m.lineNumber
        ORDER BY caller_count DESC, m.name
        LIMIT ?
    """

    try:
        # Execute query
        results_raw = cpg_service.execute_query(sql_query, (top_k,))

        # Convert to RetrievalResult
        results = []
        for i, row in enumerate(results_raw):
            # Score based on rank (higher rank = higher score)
            score = 1.0 - (i / max(len(results_raw), 1))

            # Build content string
            content = f"{row.get('name', 'unknown')} - {row.get('filename', 'unknown')}:{row.get('lineNumber', 0)}"
            if row.get('signature'):
                content += f"\nSignature: {row['signature']}"

            results.append(RetrievalResult(
                id=f"method_{row.get('id', i)}",
                content=content,
                score=score,
                source="graph",
                node_id=row.get('id'),
                metadata={
                    'name': row.get('name'),
                    'fullName': row.get('fullName'),
                    'filename': row.get('filename'),
                    'lineNumber': row.get('lineNumber'),
                    'caller_count': row.get('caller_count', 0)
                }
            ))

        return results

    except Exception as e:
        logger.error(f"Graph query execution failed: {e}", exc_info=True)
        return []


__all__ = ['graph_search_async', 'graph_search_sync']
