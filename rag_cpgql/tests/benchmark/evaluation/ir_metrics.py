"""
Information Retrieval Metrics for CodeGraph Benchmark

Implements standard IR evaluation metrics:
- Precision@K: What fraction of retrieved items are relevant?
- Recall@K: What fraction of relevant items were retrieved?
- F1@K: Harmonic mean of precision and recall
- MRR: Mean Reciprocal Rank - position of first relevant result
- NDCG@K: Normalized Discounted Cumulative Gain - ranking quality

Author: CodeGraph Test Suite
Date: November 2025
"""

import math
from typing import List, Set, Dict, Any, Optional, Union
from dataclasses import dataclass, field


@dataclass
class IRMetricsResult:
    """Container for IR metrics computation results"""
    precision_at_k: Dict[int, float] = field(default_factory=dict)
    recall_at_k: Dict[int, float] = field(default_factory=dict)
    f1_at_k: Dict[int, float] = field(default_factory=dict)
    mrr: float = 0.0
    ndcg_at_k: Dict[int, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            'precision_at_k': self.precision_at_k,
            'recall_at_k': self.recall_at_k,
            'f1_at_k': self.f1_at_k,
            'mrr': self.mrr,
            'ndcg_at_k': self.ndcg_at_k,
        }


class IRMetrics:
    """
    Information Retrieval metrics for evaluating RAG system retrieval quality.

    Usage:
        ir = IRMetrics()

        # Single metric
        p10 = ir.precision_at_k(retrieved_ids, relevant_ids, k=10)

        # All metrics at once
        result = ir.compute_all(retrieved_ids, relevant_ids, k_values=[5, 10, 20])
    """

    @staticmethod
    def precision_at_k(
        retrieved: List[Any],
        relevant: Set[Any],
        k: Optional[int] = None
    ) -> float:
        """
        Precision@K: What fraction of top-K retrieved items are relevant?

        Modified formula for sparse retrieval (RAG systems):
        P@K = |retrieved[:k] ∩ relevant| / min(k, len(retrieved[:k]))

        This modification handles cases where fewer than k items are retrieved,
        which is common in focused retrieval like definition search.
        If we retrieve 1 item and it's correct, that should be 100% precision,
        not 10% just because k=10.

        Args:
            retrieved: Ordered list of retrieved item IDs
            relevant: Set of relevant item IDs (ground truth)
            k: Number of top items to consider. If None, uses len(retrieved)

        Returns:
            Precision score between 0.0 and 1.0
        """
        if k is None:
            k = len(retrieved)
        if k == 0:
            return 0.0

        retrieved_k = set(retrieved[:k])
        hits = len(retrieved_k & relevant)
        # Use actual count of retrieved items (up to k) as denominator
        # This is more meaningful for sparse retrieval scenarios
        denominator = min(k, len(retrieved))
        if denominator == 0:
            return 0.0
        return hits / denominator

    @staticmethod
    def recall_at_k(
        retrieved: List[Any],
        relevant: Set[Any],
        k: Optional[int] = None
    ) -> float:
        """
        Recall@K: What fraction of relevant items were retrieved in top-K?

        R@K = |retrieved[:k] ∩ relevant| / |relevant|

        Args:
            retrieved: Ordered list of retrieved item IDs
            relevant: Set of relevant item IDs (ground truth)
            k: Number of top items to consider. If None, uses len(retrieved)

        Returns:
            Recall score between 0.0 and 1.0
        """
        if len(relevant) == 0:
            return 1.0 if len(retrieved) == 0 else 0.0
        if k is None:
            k = len(retrieved)

        retrieved_k = set(retrieved[:k])
        hits = len(retrieved_k & relevant)
        return hits / len(relevant)

    @staticmethod
    def f1_at_k(
        retrieved: List[Any],
        relevant: Set[Any],
        k: Optional[int] = None
    ) -> float:
        """
        F1@K: Harmonic mean of precision and recall at K.

        F1@K = 2 * P@K * R@K / (P@K + R@K)

        Args:
            retrieved: Ordered list of retrieved item IDs
            relevant: Set of relevant item IDs
            k: Number of top items to consider

        Returns:
            F1 score between 0.0 and 1.0
        """
        precision = IRMetrics.precision_at_k(retrieved, relevant, k)
        recall = IRMetrics.recall_at_k(retrieved, relevant, k)

        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)

    @staticmethod
    def mrr(
        retrieved: List[Any],
        relevant: Set[Any]
    ) -> float:
        """
        Mean Reciprocal Rank: 1 / (position of first relevant result)

        MRR = 1 / rank(first_relevant)

        Args:
            retrieved: Ordered list of retrieved item IDs
            relevant: Set of relevant item IDs

        Returns:
            MRR score between 0.0 and 1.0
        """
        for i, item in enumerate(retrieved, start=1):
            if item in relevant:
                return 1.0 / i
        return 0.0

    @staticmethod
    def dcg_at_k(
        retrieved: List[Any],
        relevant: Set[Any],
        highly_relevant: Optional[Set[Any]] = None,
        k: Optional[int] = None
    ) -> float:
        """
        Discounted Cumulative Gain at K.

        DCG@K = Σ (2^relevance - 1) / log2(position + 1)

        Args:
            retrieved: Ordered list of retrieved item IDs
            relevant: Set of relevant item IDs (relevance = 1)
            highly_relevant: Set of highly relevant items (relevance = 2)
            k: Number of top items to consider

        Returns:
            DCG score (not normalized)
        """
        if highly_relevant is None:
            highly_relevant = set()

        if k is None:
            k = len(retrieved)

        def relevance_score(item):
            if item in highly_relevant:
                return 2
            elif item in relevant:
                return 1
            return 0

        dcg = 0.0
        for i, item in enumerate(retrieved[:k]):
            rel = relevance_score(item)
            # Using log2(i + 2) because i starts at 0, so position = i + 1
            dcg += (2**rel - 1) / math.log2(i + 2)

        return dcg

    @staticmethod
    def ndcg_at_k(
        retrieved: List[Any],
        relevant: Set[Any],
        highly_relevant: Optional[Set[Any]] = None,
        k: Optional[int] = None
    ) -> float:
        """
        Normalized Discounted Cumulative Gain at K.

        NDCG@K = DCG@K / IDCG@K

        where IDCG@K is the DCG of the ideal ranking.

        Args:
            retrieved: Ordered list of retrieved item IDs
            relevant: Set of relevant item IDs (relevance = 1)
            highly_relevant: Set of highly relevant items (relevance = 2)
            k: Number of top items to consider

        Returns:
            NDCG score between 0.0 and 1.0
        """
        if highly_relevant is None:
            highly_relevant = set()

        if k is None:
            k = len(retrieved)

        # Compute DCG
        dcg = IRMetrics.dcg_at_k(retrieved, relevant, highly_relevant, k)

        # Compute IDCG (ideal ranking: all highly_relevant first, then relevant)
        def relevance_score(item):
            if item in highly_relevant:
                return 2
            elif item in relevant:
                return 1
            return 0

        # Build ideal ranking
        all_relevant = relevant | highly_relevant
        ideal_scores = sorted(
            [relevance_score(item) for item in all_relevant],
            reverse=True
        )[:k]

        idcg = sum(
            (2**rel - 1) / math.log2(i + 2)
            for i, rel in enumerate(ideal_scores)
        )

        if idcg == 0:
            return 0.0
        return dcg / idcg

    @staticmethod
    def average_precision(
        retrieved: List[Any],
        relevant: Set[Any]
    ) -> float:
        """
        Average Precision: Area under precision-recall curve.

        AP = Σ P(k) * rel(k) / |relevant|

        where rel(k) = 1 if item at position k is relevant, 0 otherwise

        Args:
            retrieved: Ordered list of retrieved item IDs
            relevant: Set of relevant item IDs

        Returns:
            Average precision score between 0.0 and 1.0
        """
        if len(relevant) == 0:
            return 1.0 if len(retrieved) == 0 else 0.0

        score = 0.0
        hits = 0

        for i, item in enumerate(retrieved, start=1):
            if item in relevant:
                hits += 1
                score += hits / i  # P@i when item is relevant

        return score / len(relevant)

    def compute_all(
        self,
        retrieved: List[Any],
        relevant: Set[Any],
        highly_relevant: Optional[Set[Any]] = None,
        k_values: List[int] = None
    ) -> IRMetricsResult:
        """
        Compute all IR metrics at once.

        Args:
            retrieved: Ordered list of retrieved item IDs
            relevant: Set of relevant item IDs
            highly_relevant: Set of highly relevant items (optional)
            k_values: List of K values to compute. Default: [5, 10, 20]

        Returns:
            IRMetricsResult with all computed metrics
        """
        if k_values is None:
            k_values = [5, 10, 20]

        if highly_relevant is None:
            highly_relevant = set()

        result = IRMetricsResult()

        # Compute metrics at each K
        for k in k_values:
            result.precision_at_k[k] = self.precision_at_k(retrieved, relevant, k)
            result.recall_at_k[k] = self.recall_at_k(retrieved, relevant, k)
            result.f1_at_k[k] = self.f1_at_k(retrieved, relevant, k)
            result.ndcg_at_k[k] = self.ndcg_at_k(retrieved, relevant, highly_relevant, k)

        # MRR is independent of K
        result.mrr = self.mrr(retrieved, relevant)

        return result

    @staticmethod
    def hit_rate_at_k(
        retrieved: List[Any],
        relevant: Set[Any],
        k: Optional[int] = None
    ) -> float:
        """
        Hit Rate@K: 1 if any relevant item in top-K, 0 otherwise.

        Useful for "at least one correct" scenarios.

        Args:
            retrieved: Ordered list of retrieved item IDs
            relevant: Set of relevant item IDs
            k: Number of top items to consider

        Returns:
            1.0 if hit, 0.0 otherwise
        """
        if k is None:
            k = len(retrieved)

        retrieved_k = set(retrieved[:k])
        return 1.0 if retrieved_k & relevant else 0.0


# Convenience functions for direct usage
def precision_at_k(retrieved: List[Any], relevant: Set[Any], k: int = 10) -> float:
    """Compute Precision@K"""
    return IRMetrics.precision_at_k(retrieved, relevant, k)

def recall_at_k(retrieved: List[Any], relevant: Set[Any], k: int = 10) -> float:
    """Compute Recall@K"""
    return IRMetrics.recall_at_k(retrieved, relevant, k)

def mrr(retrieved: List[Any], relevant: Set[Any]) -> float:
    """Compute Mean Reciprocal Rank"""
    return IRMetrics.mrr(retrieved, relevant)

def ndcg_at_k(retrieved: List[Any], relevant: Set[Any], k: int = 10) -> float:
    """Compute NDCG@K"""
    return IRMetrics.ndcg_at_k(retrieved, relevant, k=k)
