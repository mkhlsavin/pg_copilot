"""
Synthetic Benchmark Demo - Phase 1 Evaluation

Demonstrates the benchmark framework with synthetic retrieval results.
Shows how hybrid retrieval improves over pure vector and pure graph approaches.

Author: Phase 1 Benchmark Demo
Date: November 25, 2025
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Set
import random

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from benchmark_hybrid_retrieval import (
    HybridRetrievalBenchmark,
    BenchmarkQuery,
    BenchmarkReport,
    RetrievalMetrics
)
from src.retrieval.hybrid_retriever import RetrievalResult


class SyntheticRetrievalSimulator:
    """
    Simulates retrieval results with realistic patterns:
    - Vector: Good at semantic matching, weak at structural queries
    - Graph: Good at structural traversal, weak at semantic queries
    - Hybrid: Combines both strengths
    """

    def __init__(self, seed: int = 42):
        """Initialize simulator with random seed for reproducibility"""
        random.seed(seed)

    def simulate_vector_retrieval(
        self,
        query: BenchmarkQuery,
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """
        Simulate vector retrieval results.

        Good performance on semantic queries, poor on structural queries.
        """
        results = []
        relevant_nodes = list(query.relevant_node_ids)
        highly_relevant = list(query.highly_relevant_node_ids)

        # Vector search performance depends on query type
        if query.query_type == "semantic":
            # Excellent: 80-90% of highly relevant + 60-70% of other relevant
            num_highly = int(len(highly_relevant) * 0.85)
            other_relevant_set = query.relevant_node_ids - query.highly_relevant_node_ids
            num_regular = int(len(other_relevant_set) * 0.65)
        elif query.query_type == "structural":
            # Poor: 20-30% of relevant
            num_highly = int(len(highly_relevant) * 0.25)
            other_relevant_set = query.relevant_node_ids - query.highly_relevant_node_ids
            num_regular = int(len(other_relevant_set) * 0.25)
        else:  # security or mixed
            # Moderate: 50-60% of relevant
            num_highly = int(len(highly_relevant) * 0.55)
            other_relevant_set = query.relevant_node_ids - query.highly_relevant_node_ids
            num_regular = int(len(other_relevant_set) * 0.55)

        # Add highly relevant results (high scores)
        sampled_highly = random.sample(highly_relevant, min(num_highly, len(highly_relevant)))
        for node_id in sampled_highly:
            score = random.uniform(0.75, 0.95)
            results.append(RetrievalResult(
                id=f"vec_{node_id}",
                content=f"Method {node_id}",
                score=score,
                source="vector",
                node_id=node_id
            ))

        # Add other relevant results (medium scores)
        other_relevant = list(query.relevant_node_ids - query.highly_relevant_node_ids)
        sampled_regular = random.sample(other_relevant, min(num_regular, len(other_relevant)))
        for node_id in sampled_regular:
            score = random.uniform(0.5, 0.75)
            results.append(RetrievalResult(
                id=f"vec_{node_id}",
                content=f"Method {node_id}",
                score=score,
                source="vector",
                node_id=node_id
            ))

        # Fill remaining with non-relevant (low scores)
        non_relevant_ids = list(range(10000, 10000 + top_k))
        for node_id in non_relevant_ids[:max(0, top_k - len(results))]:
            score = random.uniform(0.3, 0.5)
            results.append(RetrievalResult(
                id=f"vec_{node_id}",
                content=f"Method {node_id}",
                score=score,
                source="vector",
                node_id=node_id
            ))

        # Sort by score and return top-K
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def simulate_graph_retrieval(
        self,
        query: BenchmarkQuery,
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """
        Simulate graph retrieval results.

        Good performance on structural queries, poor on semantic queries.
        """
        results = []
        relevant_nodes = list(query.relevant_node_ids)
        highly_relevant = list(query.highly_relevant_node_ids)

        # Graph search performance depends on query type
        if query.query_type == "structural":
            # Excellent: 80-90% of relevant
            num_highly = int(len(highly_relevant) * 0.85)
            other_relevant_set = query.relevant_node_ids - query.highly_relevant_node_ids
            num_regular = int(len(other_relevant_set) * 0.80)
        elif query.query_type == "semantic":
            # Poor: 20-30% of relevant
            num_highly = int(len(highly_relevant) * 0.25)
            other_relevant_set = query.relevant_node_ids - query.highly_relevant_node_ids
            num_regular = int(len(other_relevant_set) * 0.25)
        else:  # security or mixed
            # Moderate: 50-60% of relevant
            num_highly = int(len(highly_relevant) * 0.55)
            other_relevant_set = query.relevant_node_ids - query.highly_relevant_node_ids
            num_regular = int(len(other_relevant_set) * 0.55)

        # Add highly relevant results
        sampled_highly = random.sample(highly_relevant, min(num_highly, len(highly_relevant)))
        for node_id in sampled_highly:
            score = random.uniform(0.75, 0.95)
            results.append(RetrievalResult(
                id=f"graph_{node_id}",
                content=f"Method {node_id}",
                score=score,
                source="graph",
                node_id=node_id
            ))

        # Add other relevant results
        other_relevant = list(query.relevant_node_ids - query.highly_relevant_node_ids)
        sampled_regular = random.sample(other_relevant, min(num_regular, len(other_relevant)))
        for node_id in sampled_regular:
            score = random.uniform(0.5, 0.75)
            results.append(RetrievalResult(
                id=f"graph_{node_id}",
                content=f"Method {node_id}",
                score=score,
                source="graph",
                node_id=node_id
            ))

        # Fill remaining with non-relevant
        non_relevant_ids = list(range(20000, 20000 + top_k))
        for node_id in non_relevant_ids[:max(0, top_k - len(results))]:
            score = random.uniform(0.3, 0.5)
            results.append(RetrievalResult(
                id=f"graph_{node_id}",
                content=f"Method {node_id}",
                score=score,
                source="graph",
                node_id=node_id
            ))

        # Sort by score and return top-K
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def simulate_hybrid_retrieval(
        self,
        query: BenchmarkQuery,
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """
        Simulate hybrid retrieval results using RRF merging.

        Combines strengths of both vector and graph search.
        """
        # Get results from both sources
        vector_results = self.simulate_vector_retrieval(query, top_k=20)
        graph_results = self.simulate_graph_retrieval(query, top_k=20)

        # Simulate RRF merging with adaptive weighting
        if query.query_type == "semantic":
            vector_weight, graph_weight = 0.75, 0.25
        elif query.query_type == "structural":
            vector_weight, graph_weight = 0.25, 0.75
        else:
            vector_weight, graph_weight = 0.5, 0.5

        # RRF merging: score = weight_v / (k + rank_v) + weight_g / (k + rank_g)
        k = 60
        merged_scores = {}

        for rank, result in enumerate(vector_results, start=1):
            if result.node_id not in merged_scores:
                merged_scores[result.node_id] = 0
            merged_scores[result.node_id] += vector_weight / (k + rank)

        for rank, result in enumerate(graph_results, start=1):
            if result.node_id not in merged_scores:
                merged_scores[result.node_id] = 0
            merged_scores[result.node_id] += graph_weight / (k + rank)

        # Create merged results
        merged_results = []
        for node_id, rrf_score in merged_scores.items():
            merged_results.append(RetrievalResult(
                id=f"hybrid_{node_id}",
                content=f"Method {node_id}",
                score=rrf_score,
                source="hybrid",
                node_id=node_id
            ))

        # Sort by RRF score and return top-K
        merged_results.sort(key=lambda r: r.score, reverse=True)
        return merged_results[:top_k]


class SyntheticBenchmark(HybridRetrievalBenchmark):
    """
    Benchmark using synthetic retrieval simulator.

    Overrides run_single_query to use simulated results.
    """

    def __init__(self, output_dir: str = "benchmark_results"):
        """Initialize with synthetic simulator"""
        # Don't call parent __init__ (requires actual stores)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.simulator = SyntheticRetrievalSimulator(seed=42)

    async def run_single_query(
        self,
        query: BenchmarkQuery,
        mode: str
    ) -> RetrievalMetrics:
        """
        Run single query with synthetic results.

        Simulates realistic retrieval patterns based on query type and mode.
        """
        import time
        start_time = time.time()

        # Simulate retrieval based on mode
        if mode == "vector_only":
            results = self.simulator.simulate_vector_retrieval(query, top_k=10)
        elif mode == "graph_only":
            results = self.simulator.simulate_graph_retrieval(query, top_k=10)
        elif mode == "hybrid":
            results = self.simulator.simulate_hybrid_retrieval(query, top_k=10)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        # Simulate latency
        if mode == "hybrid":
            latency_ms = random.uniform(100, 150)  # Hybrid is slower (parallel execution)
        else:
            latency_ms = random.uniform(50, 80)   # Single source is faster

        # Extract retrieved node IDs
        retrieved_node_ids = [
            r.node_id for r in results if r.node_id is not None
        ]

        # Compute metrics
        metrics = RetrievalMetrics(
            query_id=query.id,
            mode=mode,
            latency_ms=latency_ms,
            num_results=len(results),
            retrieved_node_ids=retrieved_node_ids,
            top_5_scores=[r.score for r in results[:5]]
        )

        # Precision@K and Recall@K
        metrics.precision_at_5 = self._precision_at_k(
            retrieved_node_ids[:5], query.relevant_node_ids
        )
        metrics.precision_at_10 = self._precision_at_k(
            retrieved_node_ids[:10], query.relevant_node_ids
        )
        metrics.recall_at_5 = self._recall_at_k(
            retrieved_node_ids[:5], query.relevant_node_ids
        )
        metrics.recall_at_10 = self._recall_at_k(
            retrieved_node_ids[:10], query.relevant_node_ids
        )

        # F1@K
        metrics.f1_at_5 = self._f1_score(
            metrics.precision_at_5, metrics.recall_at_5
        )
        metrics.f1_at_10 = self._f1_score(
            metrics.precision_at_10, metrics.recall_at_10
        )

        # MRR
        metrics.mrr = self._compute_mrr(
            retrieved_node_ids, query.relevant_node_ids
        )

        # NDCG@10
        metrics.ndcg_at_10 = self._compute_ndcg(
            retrieved_node_ids[:10],
            query.relevant_node_ids,
            query.highly_relevant_node_ids
        )

        print(
            f"{mode:12s} | {query.id} | P@10={metrics.precision_at_10:.3f} | "
            f"R@10={metrics.recall_at_10:.3f} | F1@10={metrics.f1_at_10:.3f} | "
            f"MRR={metrics.mrr:.3f} | NDCG={metrics.ndcg_at_10:.3f}"
        )

        return metrics


async def main():
    """Run synthetic benchmark demonstration"""
    print("=" * 80)
    print("SYNTHETIC BENCHMARK DEMONSTRATION")
    print("=" * 80)
    print()
    print("This demo simulates realistic retrieval patterns to demonstrate")
    print("how hybrid retrieval improves over pure vector and pure graph approaches.")
    print()

    # Create benchmark
    benchmark = SyntheticBenchmark(output_dir="benchmark_results")

    # Run benchmark
    report = await benchmark.run_benchmark(
        modes=["vector_only", "graph_only", "hybrid"]
    )

    # Save results
    benchmark.save_report(report, filename="synthetic_benchmark_demo.json")

    print("\n" + "=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)
    print()
    print("1. Vector search excels at semantic queries but struggles with structural queries")
    print("2. Graph search excels at structural queries but struggles with semantic queries")
    print("3. Hybrid search combines both strengths, achieving best overall performance")
    print()
    print(f"Hybrid F1@10 improvement over Vector: {report.improvement_hybrid_vs_vector.get('f1_at_10', 0):+.1f}%")
    print(f"Hybrid F1@10 improvement over Graph:  {report.improvement_hybrid_vs_graph.get('f1_at_10', 0):+.1f}%")
    print()


if __name__ == "__main__":
    asyncio.run(main())
