"""
Unit Tests for Benchmark Metrics Computation

Tests IR metrics (Precision@K, Recall@K, F1, MRR, NDCG) used in
hybrid retrieval benchmarking.

Author: Phase 1 Benchmark Tests
Date: November 25, 2025
"""

import pytest
import sys
import os
from pathlib import Path

# Add project root and scripts to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "scripts"))

from benchmark_hybrid_retrieval import (
    HybridRetrievalBenchmark,
    BenchmarkQuery,
    RetrievalMetrics
)


class TestPrecisionAtK:
    """Test Precision@K computation"""

    def test_perfect_precision(self):
        """Test precision when all retrieved are relevant"""
        benchmark = HybridRetrievalBenchmark(None, None)

        retrieved = [1, 2, 3, 4, 5]
        relevant = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}

        precision = benchmark._precision_at_k(retrieved, relevant)

        assert precision == 1.0
        print("\n  OK Perfect precision: 5/5 relevant")

    def test_half_precision(self):
        """Test precision when half retrieved are relevant"""
        benchmark = HybridRetrievalBenchmark(None, None)

        retrieved = [1, 2, 99, 100, 101]  # 2 relevant, 3 not
        relevant = {1, 2, 3, 4, 5}

        precision = benchmark._precision_at_k(retrieved, relevant)

        assert precision == 0.4  # 2/5
        print(f"\n  OK Half precision: 2/5 = {precision:.2f}")

    def test_zero_precision(self):
        """Test precision when no retrieved are relevant"""
        benchmark = HybridRetrievalBenchmark(None, None)

        retrieved = [99, 100, 101, 102, 103]
        relevant = {1, 2, 3, 4, 5}

        precision = benchmark._precision_at_k(retrieved, relevant)

        assert precision == 0.0
        print("\n  OK Zero precision: 0/5 relevant")

    def test_empty_retrieved(self):
        """Test precision with empty retrieved list"""
        benchmark = HybridRetrievalBenchmark(None, None)

        retrieved = []
        relevant = {1, 2, 3}

        precision = benchmark._precision_at_k(retrieved, relevant)

        assert precision == 0.0
        print("\n  OK Empty retrieved: precision = 0.0")

    def test_different_k_values(self):
        """Test precision at different K values"""
        benchmark = HybridRetrievalBenchmark(None, None)

        retrieved = [1, 2, 99, 100, 3, 101, 102, 4, 5, 103]
        relevant = {1, 2, 3, 4, 5}

        # Precision@5: [1, 2, 99, 100, 3] -> 3/5 = 0.6
        p_at_5 = benchmark._precision_at_k(retrieved[:5], relevant)
        assert p_at_5 == 0.6

        # Precision@10: all 10 -> 5/10 = 0.5
        p_at_10 = benchmark._precision_at_k(retrieved[:10], relevant)
        assert p_at_10 == 0.5

        print(f"\n  OK P@5 = {p_at_5:.2f}, P@10 = {p_at_10:.2f}")


class TestRecallAtK:
    """Test Recall@K computation"""

    def test_perfect_recall(self):
        """Test recall when all relevant are retrieved"""
        benchmark = HybridRetrievalBenchmark(None, None)

        retrieved = [1, 2, 3, 4, 5, 99, 100, 101]
        relevant = {1, 2, 3, 4, 5}

        recall = benchmark._recall_at_k(retrieved, relevant)

        assert recall == 1.0  # All 5 relevant retrieved
        print("\n  OK Perfect recall: 5/5 relevant retrieved")

    def test_partial_recall(self):
        """Test recall when some relevant are retrieved"""
        benchmark = HybridRetrievalBenchmark(None, None)

        retrieved = [1, 2, 99, 100, 101]
        relevant = {1, 2, 3, 4, 5}  # 5 total relevant

        recall = benchmark._recall_at_k(retrieved, relevant)

        assert recall == 0.4  # 2 out of 5 relevant retrieved
        print(f"\n  OK Partial recall: 2/5 = {recall:.2f}")

    def test_zero_recall(self):
        """Test recall when no relevant are retrieved"""
        benchmark = HybridRetrievalBenchmark(None, None)

        retrieved = [99, 100, 101, 102, 103]
        relevant = {1, 2, 3, 4, 5}

        recall = benchmark._recall_at_k(retrieved, relevant)

        assert recall == 0.0
        print("\n  OK Zero recall: 0/5 relevant retrieved")

    def test_recall_increases_with_k(self):
        """Test that recall increases (or stays same) as K increases"""
        benchmark = HybridRetrievalBenchmark(None, None)

        retrieved = [99, 100, 1, 2, 101, 102, 3, 4, 103, 5]
        relevant = {1, 2, 3, 4, 5}  # 5 total relevant

        # Recall@5: [99, 100, 1, 2, 101] -> 2/5 = 0.4
        r_at_5 = benchmark._recall_at_k(retrieved[:5], relevant)

        # Recall@10: [99, 100, 1, 2, 101, 102, 3, 4, 103, 5] -> 5/5 = 1.0
        r_at_10 = benchmark._recall_at_k(retrieved[:10], relevant)

        assert r_at_5 == 0.4
        assert r_at_10 == 1.0
        assert r_at_10 >= r_at_5  # Recall monotonically increases

        print(f"\n  OK R@5 = {r_at_5:.2f}, R@10 = {r_at_10:.2f}")


class TestF1Score:
    """Test F1 score computation"""

    def test_perfect_f1(self):
        """Test F1 when both precision and recall are 1.0"""
        benchmark = HybridRetrievalBenchmark(None, None)

        f1 = benchmark._f1_score(precision=1.0, recall=1.0)

        assert f1 == 1.0
        print("\n  OK Perfect F1: P=1.0, R=1.0 -> F1=1.0")

    def test_balanced_f1(self):
        """Test F1 with balanced precision and recall"""
        benchmark = HybridRetrievalBenchmark(None, None)

        # P=0.6, R=0.6 -> F1 = 2*(0.6*0.6)/(0.6+0.6) = 0.72/1.2 = 0.6
        f1 = benchmark._f1_score(precision=0.6, recall=0.6)

        assert f1 == pytest.approx(0.6, abs=0.01)
        print(f"\n  OK Balanced F1: P=0.6, R=0.6 -> F1={f1:.3f}")

    def test_unbalanced_f1(self):
        """Test F1 with unbalanced precision and recall"""
        benchmark = HybridRetrievalBenchmark(None, None)

        # P=0.8, R=0.4 -> F1 = 2*(0.8*0.4)/(0.8+0.4) = 0.64/1.2 = 0.533
        f1 = benchmark._f1_score(precision=0.8, recall=0.4)

        expected_f1 = 2 * (0.8 * 0.4) / (0.8 + 0.4)
        assert f1 == pytest.approx(expected_f1, abs=0.01)
        print(f"\n  OK Unbalanced F1: P=0.8, R=0.4 -> F1={f1:.3f}")

    def test_zero_f1(self):
        """Test F1 when precision or recall is zero"""
        benchmark = HybridRetrievalBenchmark(None, None)

        f1_zero_p = benchmark._f1_score(precision=0.0, recall=0.5)
        f1_zero_r = benchmark._f1_score(precision=0.5, recall=0.0)
        f1_both_zero = benchmark._f1_score(precision=0.0, recall=0.0)

        assert f1_zero_p == 0.0
        assert f1_zero_r == 0.0
        assert f1_both_zero == 0.0

        print("\n  OK Zero cases: F1=0 when P or R is 0")


class TestMRR:
    """Test Mean Reciprocal Rank computation"""

    def test_mrr_first_position(self):
        """Test MRR when first result is relevant"""
        benchmark = HybridRetrievalBenchmark(None, None)

        retrieved = [1, 2, 3, 4, 5]
        relevant = {1}

        mrr = benchmark._compute_mrr(retrieved, relevant)

        assert mrr == 1.0  # 1 / 1
        print("\n  OK MRR=1.0: First result relevant")

    def test_mrr_second_position(self):
        """Test MRR when second result is relevant"""
        benchmark = HybridRetrievalBenchmark(None, None)

        retrieved = [99, 1, 3, 4, 5]
        relevant = {1}

        mrr = benchmark._compute_mrr(retrieved, relevant)

        assert mrr == 0.5  # 1 / 2
        print("\n  OK MRR=0.5: Second result relevant")

    def test_mrr_fifth_position(self):
        """Test MRR when fifth result is relevant"""
        benchmark = HybridRetrievalBenchmark(None, None)

        retrieved = [99, 98, 97, 96, 1]
        relevant = {1}

        mrr = benchmark._compute_mrr(retrieved, relevant)

        assert mrr == 0.2  # 1 / 5
        print("\n  OK MRR=0.2: Fifth result relevant")

    def test_mrr_no_relevant(self):
        """Test MRR when no relevant results"""
        benchmark = HybridRetrievalBenchmark(None, None)

        retrieved = [99, 98, 97, 96, 95]
        relevant = {1, 2, 3}

        mrr = benchmark._compute_mrr(retrieved, relevant)

        assert mrr == 0.0
        print("\n  OK MRR=0.0: No relevant results")

    def test_mrr_first_relevant_wins(self):
        """Test MRR uses first relevant result (not best)"""
        benchmark = HybridRetrievalBenchmark(None, None)

        retrieved = [99, 98, 1, 2, 3]  # Multiple relevant at positions 3, 4, 5
        relevant = {1, 2, 3}

        mrr = benchmark._compute_mrr(retrieved, relevant)

        assert mrr == pytest.approx(1.0 / 3, abs=0.01)  # First relevant at position 3
        print(f"\n  OK MRR={mrr:.3f}: First relevant at position 3")


class TestNDCG:
    """Test Normalized Discounted Cumulative Gain computation"""

    def test_ndcg_perfect_ranking(self):
        """Test NDCG when ranking is perfect (highly relevant first)"""
        benchmark = HybridRetrievalBenchmark(None, None)

        # Perfect ranking: highly relevant first, then relevant, then not
        retrieved = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        relevant = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}
        highly_relevant = {1, 2, 3}

        ndcg = benchmark._compute_ndcg(retrieved, relevant, highly_relevant)

        assert ndcg == 1.0  # Perfect ranking
        print("\n  OK NDCG=1.0: Perfect ranking")

    def test_ndcg_worst_ranking(self):
        """Test NDCG when ranking is worst (highly relevant last)"""
        benchmark = HybridRetrievalBenchmark(None, None)

        # Worst ranking: not relevant first, then relevant, then highly relevant last
        retrieved = [99, 98, 97, 4, 5, 1, 2]
        relevant = {1, 2, 4, 5}
        highly_relevant = {1, 2}

        ndcg = benchmark._compute_ndcg(retrieved, relevant, highly_relevant)

        assert 0 < ndcg < 1.0  # Poor ranking, but not zero
        print(f"\n  OK NDCG={ndcg:.3f}: Poor ranking (highly relevant last)")

    def test_ndcg_partial_relevant(self):
        """Test NDCG with mix of relevant and not relevant"""
        benchmark = HybridRetrievalBenchmark(None, None)

        # Mixed ranking
        retrieved = [1, 99, 2, 98, 3]  # Highly: 1,2  Relevant: 3  Not: 99,98
        relevant = {1, 2, 3}
        highly_relevant = {1, 2}

        ndcg = benchmark._compute_ndcg(retrieved, relevant, highly_relevant)

        assert 0 < ndcg < 1.0
        print(f"\n  OK NDCG={ndcg:.3f}: Mixed ranking")

    def test_ndcg_empty_retrieved(self):
        """Test NDCG with empty retrieved list"""
        benchmark = HybridRetrievalBenchmark(None, None)

        retrieved = []
        relevant = {1, 2, 3}
        highly_relevant = {1}

        ndcg = benchmark._compute_ndcg(retrieved, relevant, highly_relevant)

        assert ndcg == 0.0
        print("\n  OK NDCG=0.0: Empty retrieved")

    def test_ndcg_no_relevant_retrieved(self):
        """Test NDCG when no relevant documents retrieved"""
        benchmark = HybridRetrievalBenchmark(None, None)

        retrieved = [99, 98, 97, 96, 95]
        relevant = {1, 2, 3}
        highly_relevant = {1}

        ndcg = benchmark._compute_ndcg(retrieved, relevant, highly_relevant)

        assert ndcg == 0.0
        print("\n  OK NDCG=0.0: No relevant retrieved")


class TestBenchmarkQuery:
    """Test BenchmarkQuery dataclass"""

    def test_query_creation(self):
        """Test creating a benchmark query"""
        query = BenchmarkQuery(
            id="test_001",
            query="What does this function do?",
            query_type="semantic",
            description="Test semantic query",
            relevant_node_ids={1, 2, 3},
            highly_relevant_node_ids={1},
            expected_difficulty="easy"
        )

        assert query.id == "test_001"
        assert query.query_type == "semantic"
        assert len(query.relevant_node_ids) == 3
        assert len(query.highly_relevant_node_ids) == 1
        assert 1 in query.highly_relevant_node_ids

        print("\n  OK BenchmarkQuery created correctly")

    def test_highly_relevant_subset(self):
        """Test that highly_relevant is subset of relevant"""
        query = BenchmarkQuery(
            id="test_002",
            query="Test",
            query_type="structural",
            description="Test",
            relevant_node_ids={1, 2, 3, 4, 5},
            highly_relevant_node_ids={1, 2},
            expected_difficulty="medium"
        )

        assert query.highly_relevant_node_ids.issubset(query.relevant_node_ids)

        print("\n  OK Highly relevant is subset of relevant")


class TestRetrievalMetrics:
    """Test RetrievalMetrics dataclass"""

    def test_metrics_creation(self):
        """Test creating retrieval metrics"""
        metrics = RetrievalMetrics(
            query_id="test_001",
            mode="hybrid",
            precision_at_10=0.8,
            recall_at_10=0.6,
            f1_at_10=0.686,
            mrr=0.5,
            ndcg_at_10=0.75,
            latency_ms=150.0,
            num_results=10
        )

        assert metrics.query_id == "test_001"
        assert metrics.mode == "hybrid"
        assert metrics.precision_at_10 == 0.8
        assert metrics.recall_at_10 == 0.6
        assert metrics.f1_at_10 == pytest.approx(0.686, abs=0.01)

        print("\n  OK RetrievalMetrics created correctly")

    def test_metrics_defaults(self):
        """Test metrics with default values"""
        metrics = RetrievalMetrics(
            query_id="test_002",
            mode="vector_only"
        )

        assert metrics.precision_at_10 == 0.0
        assert metrics.recall_at_10 == 0.0
        assert metrics.latency_ms == 0.0
        assert metrics.retrieved_node_ids == []

        print("\n  OK Default metrics values correct")


class TestBenchmarkDataset:
    """Test benchmark query dataset creation"""

    def test_dataset_creation(self):
        """Test that benchmark dataset is created correctly"""
        benchmark = HybridRetrievalBenchmark(None, None)

        queries = benchmark._create_benchmark_queries()

        assert len(queries) > 0
        assert all(isinstance(q, BenchmarkQuery) for q in queries)

        # Check diversity
        query_types = {q.query_type for q in queries}
        assert "semantic" in query_types
        assert "structural" in query_types
        assert "security" in query_types

        print(f"\n  OK Dataset: {len(queries)} queries with {len(query_types)} types")

    def test_dataset_has_ground_truth(self):
        """Test that all queries have ground truth"""
        benchmark = HybridRetrievalBenchmark(None, None)

        queries = benchmark._create_benchmark_queries()

        for query in queries:
            assert len(query.relevant_node_ids) > 0, f"Query {query.id} has no relevant nodes"
            assert len(query.highly_relevant_node_ids) > 0, f"Query {query.id} has no highly relevant nodes"
            assert query.highly_relevant_node_ids.issubset(query.relevant_node_ids)

        print("\n  OK All queries have valid ground truth")

    def test_dataset_difficulty_distribution(self):
        """Test that dataset has mix of difficulties"""
        benchmark = HybridRetrievalBenchmark(None, None)

        queries = benchmark._create_benchmark_queries()

        difficulties = {q.expected_difficulty for q in queries}

        assert "easy" in difficulties
        assert "medium" in difficulties
        assert "hard" in difficulties

        print(f"\n  OK Difficulty distribution: {difficulties}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
