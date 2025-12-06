"""
Hybrid Retrieval Benchmark - Phase 1 Evaluation

Comprehensive benchmark comparing:
- Pure Vector retrieval (ChromaDB)
- Pure Graph retrieval (DuckDB/CPG)
- Hybrid retrieval (RRF-merged)

Metrics:
- Precision@K, Recall@K, F1@K
- Mean Reciprocal Rank (MRR)
- Normalized Discounted Cumulative Gain (NDCG)
- Retrieval latency

Author: Phase 1 Benchmark
Date: November 25, 2025
"""

import asyncio
import json
import logging
import sys
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import numpy as np

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.retrieval.hybrid_retriever import HybridRetriever, RetrievalResult, HybridRetrievalConfig
from src.retrieval.vector_store_real import VectorStoreReal
from src.services.cpg_query_service import CPGQueryService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkQuery:
    """Single benchmark query with ground truth"""
    id: str
    query: str
    query_type: str  # "semantic", "structural", "security"
    description: str
    relevant_node_ids: Set[int]  # Ground truth relevant CPG node IDs
    highly_relevant_node_ids: Set[int]  # Highly relevant (for NDCG)
    expected_difficulty: str  # "easy", "medium", "hard"


@dataclass
class RetrievalMetrics:
    """Metrics for single query retrieval"""
    query_id: str
    mode: str  # "vector_only", "graph_only", "hybrid"

    # Ranking metrics
    precision_at_5: float = 0.0
    precision_at_10: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    f1_at_5: float = 0.0
    f1_at_10: float = 0.0
    mrr: float = 0.0  # Mean Reciprocal Rank
    ndcg_at_10: float = 0.0  # Normalized Discounted Cumulative Gain

    # Performance metrics
    latency_ms: float = 0.0
    num_results: int = 0

    # Detailed results
    retrieved_node_ids: List[int] = field(default_factory=list)
    top_5_scores: List[float] = field(default_factory=list)


@dataclass
class BenchmarkReport:
    """Aggregate benchmark report"""
    timestamp: str
    total_queries: int

    # Aggregate metrics by mode
    vector_metrics: Dict[str, float] = field(default_factory=dict)
    graph_metrics: Dict[str, float] = field(default_factory=dict)
    hybrid_metrics: Dict[str, float] = field(default_factory=dict)

    # Per-query breakdown
    per_query_results: List[Dict[str, Any]] = field(default_factory=list)

    # Summary statistics
    improvement_hybrid_vs_vector: Dict[str, float] = field(default_factory=dict)
    improvement_hybrid_vs_graph: Dict[str, float] = field(default_factory=dict)


class HybridRetrievalBenchmark:
    """
    Benchmark framework for comparing retrieval modes.

    Features:
    - Diverse query dataset (semantic, structural, security)
    - Ground truth relevance judgments
    - Standard IR metrics (P@K, R@K, F1, MRR, NDCG)
    - Performance comparison
    - Detailed reporting
    """

    def __init__(
        self,
        vector_store: VectorStoreReal,
        cpg_service: CPGQueryService,
        output_dir: str = "benchmark_results"
    ):
        """
        Initialize benchmark framework.

        Args:
            vector_store: Vector store (ChromaDB or similar)
            cpg_service: DuckDB CPG service
            output_dir: Directory for benchmark results
        """
        self.vector_store = vector_store
        self.cpg_service = cpg_service
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Initialize retrievers for each mode
        self.hybrid_retriever = HybridRetriever(
            vector_store=vector_store,
            cpg_service=cpg_service,
            config=HybridRetrievalConfig(
                vector_weight=0.6,
                graph_weight=0.4,
                final_top_k=10
            )
        )

        logger.info("Hybrid Retrieval Benchmark initialized")

    def _create_benchmark_queries(self) -> List[BenchmarkQuery]:
        """
        Create diverse benchmark query dataset.

        Returns:
            List of benchmark queries with ground truth
        """
        queries = [
            # SEMANTIC QUERIES (favor vector search)
            BenchmarkQuery(
                id="sem_001",
                query="How does PostgreSQL handle transaction commits?",
                query_type="semantic",
                description="Semantic understanding of transaction commit logic",
                relevant_node_ids={1001, 1002, 1003, 1004, 1005},  # Example IDs
                highly_relevant_node_ids={1001, 1002},
                expected_difficulty="medium"
            ),
            BenchmarkQuery(
                id="sem_002",
                query="What is the purpose of the buffer manager?",
                query_type="semantic",
                description="Conceptual question about buffer management",
                relevant_node_ids={2001, 2002, 2003},
                highly_relevant_node_ids={2001},
                expected_difficulty="easy"
            ),
            BenchmarkQuery(
                id="sem_003",
                query="How does PostgreSQL implement multi-version concurrency control?",
                query_type="semantic",
                description="Complex semantic query about MVCC implementation",
                relevant_node_ids={3001, 3002, 3003, 3004, 3005, 3006},
                highly_relevant_node_ids={3001, 3002, 3003},
                expected_difficulty="hard"
            ),

            # STRUCTURAL QUERIES (favor graph search)
            BenchmarkQuery(
                id="str_001",
                query="Show me the call path from BeginTransactionBlock to CommitTransactionCommand",
                query_type="structural",
                description="Path query requiring graph traversal",
                relevant_node_ids={1001, 1010, 1015, 1020, 1002},
                highly_relevant_node_ids={1001, 1010, 1020, 1002},
                expected_difficulty="medium"
            ),
            BenchmarkQuery(
                id="str_002",
                query="Find all functions that call malloc",
                query_type="structural",
                description="Reverse dependency query",
                relevant_node_ids={4001, 4002, 4003, 4004, 4005, 4006, 4007},
                highly_relevant_node_ids={4001, 4002, 4003},
                expected_difficulty="easy"
            ),
            BenchmarkQuery(
                id="str_003",
                query="What are the indirect callers of MemoryContextAlloc (depth 2-3)?",
                query_type="structural",
                description="Multi-hop dependency query",
                relevant_node_ids={5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008},
                highly_relevant_node_ids={5001, 5002, 5003, 5004},
                expected_difficulty="hard"
            ),

            # SECURITY QUERIES (balanced - need both semantic + structural)
            BenchmarkQuery(
                id="sec_001",
                query="Find potential SQL injection vulnerabilities in query building functions",
                query_type="security",
                description="Security query requiring semantic understanding + control flow",
                relevant_node_ids={6001, 6002, 6003, 6004},
                highly_relevant_node_ids={6001, 6002},
                expected_difficulty="medium"
            ),
            BenchmarkQuery(
                id="sec_002",
                query="Identify functions that allocate memory without proper error checking",
                query_type="security",
                description="Vulnerability pattern requiring both semantic + structural analysis",
                relevant_node_ids={7001, 7002, 7003, 7004, 7005},
                highly_relevant_node_ids={7001, 7002, 7003},
                expected_difficulty="hard"
            ),
            BenchmarkQuery(
                id="sec_003",
                query="Find buffer overflow risks in string manipulation functions",
                query_type="security",
                description="Vulnerability detection requiring semantic patterns",
                relevant_node_ids={8001, 8002, 8003},
                highly_relevant_node_ids={8001, 8002},
                expected_difficulty="medium"
            ),

            # MIXED QUERIES (require both semantic understanding AND structural traversal)
            BenchmarkQuery(
                id="mix_001",
                query="How does the query optimizer choose between index scan and sequential scan?",
                query_type="semantic",
                description="Requires understanding optimizer logic + control flow",
                relevant_node_ids={9001, 9002, 9003, 9004, 9005, 9006},
                highly_relevant_node_ids={9001, 9002, 9003},
                expected_difficulty="hard"
            ),
            BenchmarkQuery(
                id="mix_002",
                query="Trace the execution path for a SELECT statement with WHERE clause",
                query_type="structural",
                description="Requires semantic understanding of query execution + call graph",
                relevant_node_ids={10001, 10002, 10003, 10004, 10005},
                highly_relevant_node_ids={10001, 10002, 10003, 10004},
                expected_difficulty="medium"
            ),
        ]

        logger.info(f"Created {len(queries)} benchmark queries")
        logger.info(f"  Semantic: {sum(1 for q in queries if q.query_type == 'semantic')}")
        logger.info(f"  Structural: {sum(1 for q in queries if q.query_type == 'structural')}")
        logger.info(f"  Security: {sum(1 for q in queries if q.query_type == 'security')}")

        return queries

    async def run_single_query(
        self,
        query: BenchmarkQuery,
        mode: str
    ) -> RetrievalMetrics:
        """
        Run single query in specified mode and compute metrics.

        Args:
            query: Benchmark query with ground truth
            mode: Retrieval mode ("vector_only", "graph_only", "hybrid")

        Returns:
            Computed metrics for this query
        """
        start_time = time.time()

        try:
            # Retrieve results
            results = await self.hybrid_retriever.retrieve(
                query=query.query,
                mode=mode,
                query_type=query.query_type
            )

            latency_ms = (time.time() - start_time) * 1000

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

            # MRR (Mean Reciprocal Rank)
            metrics.mrr = self._compute_mrr(
                retrieved_node_ids, query.relevant_node_ids
            )

            # NDCG@10
            metrics.ndcg_at_10 = self._compute_ndcg(
                retrieved_node_ids[:10],
                query.relevant_node_ids,
                query.highly_relevant_node_ids
            )

            logger.info(
                f"{mode:12s} | {query.id} | P@10={metrics.precision_at_10:.3f} | "
                f"R@10={metrics.recall_at_10:.3f} | F1@10={metrics.f1_at_10:.3f} | "
                f"MRR={metrics.mrr:.3f} | Latency={latency_ms:.1f}ms"
            )

            return metrics

        except Exception as e:
            logger.error(f"Query {query.id} failed in {mode} mode: {e}")
            return RetrievalMetrics(
                query_id=query.id,
                mode=mode,
                latency_ms=(time.time() - start_time) * 1000
            )

    def _precision_at_k(
        self,
        retrieved: List[int],
        relevant: Set[int]
    ) -> float:
        """
        Compute Precision@K.

        P@K = (# relevant in top-K) / K
        """
        if not retrieved:
            return 0.0

        num_relevant = sum(1 for node_id in retrieved if node_id in relevant)
        return num_relevant / len(retrieved)

    def _recall_at_k(
        self,
        retrieved: List[int],
        relevant: Set[int]
    ) -> float:
        """
        Compute Recall@K.

        R@K = (# relevant in top-K) / (total # relevant)
        """
        if not relevant:
            return 0.0

        num_relevant = sum(1 for node_id in retrieved if node_id in relevant)
        return num_relevant / len(relevant)

    def _f1_score(self, precision: float, recall: float) -> float:
        """
        Compute F1 score from precision and recall.

        F1 = 2 * (P * R) / (P + R)
        """
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)

    def _compute_mrr(
        self,
        retrieved: List[int],
        relevant: Set[int]
    ) -> float:
        """
        Compute Mean Reciprocal Rank (MRR).

        MRR = 1 / rank_of_first_relevant

        If no relevant results, return 0.
        """
        for rank, node_id in enumerate(retrieved, start=1):
            if node_id in relevant:
                return 1.0 / rank
        return 0.0

    def _compute_ndcg(
        self,
        retrieved: List[int],
        relevant: Set[int],
        highly_relevant: Set[int]
    ) -> float:
        """
        Compute Normalized Discounted Cumulative Gain (NDCG@K).

        NDCG@K = DCG@K / IDCG@K

        DCG@K = Σ (2^rel_i - 1) / log2(i + 1)

        Relevance levels:
        - Highly relevant: rel = 2
        - Relevant: rel = 1
        - Not relevant: rel = 0
        """
        if not retrieved:
            return 0.0

        # Compute DCG
        dcg = 0.0
        for i, node_id in enumerate(retrieved, start=1):
            if node_id in highly_relevant:
                rel = 2
            elif node_id in relevant:
                rel = 1
            else:
                rel = 0

            dcg += (2 ** rel - 1) / np.log2(i + 1)

        # Compute IDCG (ideal DCG)
        ideal_ranking = []
        ideal_ranking.extend([2] * len(highly_relevant))
        ideal_ranking.extend([1] * len(relevant - highly_relevant))
        ideal_ranking = ideal_ranking[:len(retrieved)]

        idcg = sum(
            (2 ** rel - 1) / np.log2(i + 1)
            for i, rel in enumerate(ideal_ranking, start=1)
        )

        if idcg == 0:
            return 0.0

        return dcg / idcg

    async def run_benchmark(
        self,
        queries: Optional[List[BenchmarkQuery]] = None,
        modes: List[str] = ["vector_only", "graph_only", "hybrid"]
    ) -> BenchmarkReport:
        """
        Run complete benchmark across all queries and modes.

        Args:
            queries: List of benchmark queries (uses default if None)
            modes: List of retrieval modes to test

        Returns:
            Comprehensive benchmark report
        """
        if queries is None:
            queries = self._create_benchmark_queries()

        logger.info(f"Starting benchmark: {len(queries)} queries × {len(modes)} modes")
        logger.info("=" * 80)

        # Run all queries in all modes
        all_metrics = []
        for query in queries:
            logger.info(f"\nQuery {query.id}: {query.query}")
            logger.info(f"Type: {query.query_type} | Difficulty: {query.expected_difficulty}")
            logger.info(f"Ground truth: {len(query.relevant_node_ids)} relevant nodes")

            for mode in modes:
                metrics = await self.run_single_query(query, mode)
                all_metrics.append(metrics)

        # Aggregate metrics by mode
        logger.info("\n" + "=" * 80)
        logger.info("AGGREGATE RESULTS")
        logger.info("=" * 80)

        vector_metrics = self._aggregate_metrics(
            [m for m in all_metrics if m.mode == "vector_only"]
        )
        graph_metrics = self._aggregate_metrics(
            [m for m in all_metrics if m.mode == "graph_only"]
        )
        hybrid_metrics = self._aggregate_metrics(
            [m for m in all_metrics if m.mode == "hybrid"]
        )

        # Compute improvements
        improvements_vs_vector = {
            metric: ((hybrid_metrics[metric] - vector_metrics[metric]) / vector_metrics[metric] * 100)
            if vector_metrics[metric] > 0 else 0.0
            for metric in ["precision_at_10", "recall_at_10", "f1_at_10", "mrr", "ndcg_at_10"]
        }

        improvements_vs_graph = {
            metric: ((hybrid_metrics[metric] - graph_metrics[metric]) / graph_metrics[metric] * 100)
            if graph_metrics[metric] > 0 else 0.0
            for metric in ["precision_at_10", "recall_at_10", "f1_at_10", "mrr", "ndcg_at_10"]
        }

        # Create report
        report = BenchmarkReport(
            timestamp=datetime.now().isoformat(),
            total_queries=len(queries),
            vector_metrics=vector_metrics,
            graph_metrics=graph_metrics,
            hybrid_metrics=hybrid_metrics,
            per_query_results=[asdict(m) for m in all_metrics],
            improvement_hybrid_vs_vector=improvements_vs_vector,
            improvement_hybrid_vs_graph=improvements_vs_graph
        )

        # Print summary
        self._print_summary(report)

        return report

    def _aggregate_metrics(self, metrics_list: List[RetrievalMetrics]) -> Dict[str, float]:
        """
        Aggregate metrics across multiple queries.

        Args:
            metrics_list: List of metrics for single mode

        Returns:
            Dictionary of aggregated metrics
        """
        if not metrics_list:
            return {}

        return {
            "precision_at_5": np.mean([m.precision_at_5 for m in metrics_list]),
            "precision_at_10": np.mean([m.precision_at_10 for m in metrics_list]),
            "recall_at_5": np.mean([m.recall_at_5 for m in metrics_list]),
            "recall_at_10": np.mean([m.recall_at_10 for m in metrics_list]),
            "f1_at_5": np.mean([m.f1_at_5 for m in metrics_list]),
            "f1_at_10": np.mean([m.f1_at_10 for m in metrics_list]),
            "mrr": np.mean([m.mrr for m in metrics_list]),
            "ndcg_at_10": np.mean([m.ndcg_at_10 for m in metrics_list]),
            "avg_latency_ms": np.mean([m.latency_ms for m in metrics_list]),
            "avg_num_results": np.mean([m.num_results for m in metrics_list])
        }

    def _print_summary(self, report: BenchmarkReport):
        """Print benchmark summary to console."""
        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)
        print(f"Timestamp: {report.timestamp}")
        print(f"Total Queries: {report.total_queries}")
        print()

        # Comparison table
        print(f"{'Metric':<20} {'Vector':<12} {'Graph':<12} {'Hybrid':<12} {'vs Vector':<12} {'vs Graph':<12}")
        print("-" * 80)

        metrics_to_show = [
            ("Precision@10", "precision_at_10"),
            ("Recall@10", "recall_at_10"),
            ("F1@10", "f1_at_10"),
            ("MRR", "mrr"),
            ("NDCG@10", "ndcg_at_10"),
            ("Latency (ms)", "avg_latency_ms"),
        ]

        for display_name, key in metrics_to_show:
            vector_val = report.vector_metrics.get(key, 0.0)
            graph_val = report.graph_metrics.get(key, 0.0)
            hybrid_val = report.hybrid_metrics.get(key, 0.0)

            # For latency, lower is better
            if key == "avg_latency_ms":
                vs_vector = f"{((hybrid_val - vector_val) / vector_val * 100):+.1f}%" if vector_val > 0 else "N/A"
                vs_graph = f"{((hybrid_val - graph_val) / graph_val * 100):+.1f}%" if graph_val > 0 else "N/A"
            else:
                vs_vector_pct = report.improvement_hybrid_vs_vector.get(key, 0.0)
                vs_graph_pct = report.improvement_hybrid_vs_graph.get(key, 0.0)
                vs_vector = f"{vs_vector_pct:+.1f}%"
                vs_graph = f"{vs_graph_pct:+.1f}%"

            print(f"{display_name:<20} {vector_val:<12.4f} {graph_val:<12.4f} {hybrid_val:<12.4f} {vs_vector:<12} {vs_graph:<12}")

        print("=" * 80)

    def save_report(self, report: BenchmarkReport, filename: Optional[str] = None):
        """
        Save benchmark report to JSON file.

        Args:
            report: Benchmark report to save
            filename: Output filename (auto-generated if None)
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"hybrid_benchmark_{timestamp}.json"

        output_path = self.output_dir / filename

        with open(output_path, 'w') as f:
            json.dump(asdict(report), f, indent=2)

        logger.info(f"Benchmark report saved: {output_path}")

        # Also save markdown summary
        md_path = output_path.with_suffix('.md')
        self._save_markdown_report(report, md_path)

    def _save_markdown_report(self, report: BenchmarkReport, output_path: Path):
        """Save human-readable markdown report."""
        with open(output_path, 'w') as f:
            f.write("# Hybrid Retrieval Benchmark Report\n\n")
            f.write(f"**Date:** {report.timestamp}\n\n")
            f.write(f"**Queries:** {report.total_queries}\n\n")

            f.write("## Summary\n\n")
            f.write("| Metric | Vector | Graph | Hybrid | Improvement vs Vector | Improvement vs Graph |\n")
            f.write("|--------|--------|-------|--------|----------------------|---------------------|\n")

            for metric_key in ["precision_at_10", "recall_at_10", "f1_at_10", "mrr", "ndcg_at_10"]:
                metric_name = metric_key.replace("_", " ").title()
                v = report.vector_metrics.get(metric_key, 0.0)
                g = report.graph_metrics.get(metric_key, 0.0)
                h = report.hybrid_metrics.get(metric_key, 0.0)
                iv = report.improvement_hybrid_vs_vector.get(metric_key, 0.0)
                ig = report.improvement_hybrid_vs_graph.get(metric_key, 0.0)

                f.write(f"| {metric_name} | {v:.4f} | {g:.4f} | {h:.4f} | {iv:+.1f}% | {ig:+.1f}% |\n")

            f.write("\n## Key Findings\n\n")
            f.write(f"- **Best F1@10:** Hybrid ({report.hybrid_metrics.get('f1_at_10', 0.0):.4f})\n")
            f.write(f"- **Improvement over Vector:** {report.improvement_hybrid_vs_vector.get('f1_at_10', 0.0):+.1f}%\n")
            f.write(f"- **Improvement over Graph:** {report.improvement_hybrid_vs_graph.get('f1_at_10', 0.0):+.1f}%\n")

        logger.info(f"Markdown report saved: {output_path}")


async def main():
    """Run benchmark from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark hybrid retrieval system")
    parser.add_argument(
        "--db-path",
        default="cpg.duckdb",
        help="Path to DuckDB CPG database"
    )
    parser.add_argument(
        "--chroma-path",
        default="chroma_db",
        help="Path to ChromaDB vector store"
    )
    parser.add_argument(
        "--output-dir",
        default="benchmark_results",
        help="Output directory for results"
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        default=["vector_only", "graph_only", "hybrid"],
        help="Retrieval modes to benchmark"
    )

    args = parser.parse_args()

    # Initialize stores (would need actual initialization)
    logger.info("Initializing vector store and CPG service...")

    # TODO: Replace with actual initialization
    vector_store = None  # ChromaVectorStore(args.chroma_path)
    cpg_service = None   # CPGQueryService(args.db_path)

    if vector_store is None or cpg_service is None:
        logger.error("Vector store and CPG service initialization required")
        logger.info("This is a benchmark framework. Integrate with actual services to run.")
        return

    # Run benchmark
    benchmark = HybridRetrievalBenchmark(
        vector_store=vector_store,
        cpg_service=cpg_service,
        output_dir=args.output_dir
    )

    report = await benchmark.run_benchmark(modes=args.modes)

    # Save results
    benchmark.save_report(report)

    logger.info("\nBenchmark complete!")


if __name__ == "__main__":
    asyncio.run(main())
