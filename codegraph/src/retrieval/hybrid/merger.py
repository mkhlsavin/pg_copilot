"""
Result Merging with Reciprocal Rank Fusion (RRF)

Merges vector and graph search results using weighted RRF scoring.
"""

import logging
from typing import List

from .models import RetrievalResult, HybridRetrievalConfig

logger = logging.getLogger(__name__)


def merge_results_rrf(
    vector_results: List[RetrievalResult],
    graph_results: List[RetrievalResult],
    config: HybridRetrievalConfig
) -> List[RetrievalResult]:
    """
    Merge results using Reciprocal Rank Fusion (RRF) with weighted scoring.

    RRF Formula: score(d) = Σ 1/(k + rank(d))
    where k is a constant (typically 60)

    Args:
        vector_results: Results from vector search
        graph_results: Results from graph search
        config: Configuration with weights

    Returns:
        Merged and sorted results
    """
    k = 60  # RRF constant

    # Build lookup tables for RRF scores
    rrf_scores = {}

    # Process vector results
    for rank, result in enumerate(vector_results, start=1):
        result_id = result.id
        rrf_score = config.vector_weight / (k + rank)

        if result_id not in rrf_scores:
            rrf_scores[result_id] = {
                'rrf_score': 0.0,
                'result': result,
                'sources': []
            }

        rrf_scores[result_id]['rrf_score'] += rrf_score
        rrf_scores[result_id]['sources'].append('vector')

    # Process graph results
    for rank, result in enumerate(graph_results, start=1):
        result_id = result.id
        rrf_score = config.graph_weight / (k + rank)

        if result_id not in rrf_scores:
            rrf_scores[result_id] = {
                'rrf_score': 0.0,
                'result': result,
                'sources': []
            }

        rrf_scores[result_id]['rrf_score'] += rrf_score
        rrf_scores[result_id]['sources'].append('graph')

    # Create merged results
    merged_results = []
    for result_id, data in rrf_scores.items():
        result = data['result']
        rrf_score = data['rrf_score']
        sources = data['sources']

        # Determine source label
        if len(sources) == 2:
            source = "hybrid"  # Found in both
        else:
            source = sources[0]

        # Create new result with RRF score
        merged_result = RetrievalResult(
            id=result.id,
            content=result.content,
            score=rrf_score,
            source=source,
            metadata=result.metadata,
            node_id=result.node_id
        )

        merged_results.append(merged_result)

    # Sort by RRF score
    merged_results.sort(key=lambda r: r.score, reverse=True)

    logger.debug(
        f"RRF merging: {len(vector_results)} vector + {len(graph_results)} graph "
        f"→ {len(merged_results)} merged results"
    )

    return merged_results


__all__ = ['merge_results_rrf']
