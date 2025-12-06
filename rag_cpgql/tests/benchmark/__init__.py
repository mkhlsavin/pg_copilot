"""
Comprehensive Benchmark Suite for RAG-CPGQL Copilot

This module provides a complete benchmarking framework for evaluating
17 user scenarios across the Code Property Graph analysis system.

Features:
- 500+ test questions (EN + RU)
- IR metrics (P@K, R@K, MRR, NDCG)
- Accuracy metrics (semantic similarity, keyword coverage)
- Full traceability for debugging

Author: RAG-CPGQL Test Suite
Date: November 2025
"""

from tests.benchmark.evaluation.ir_metrics import IRMetrics
from tests.benchmark.evaluation.accuracy_metrics import AccuracyMetrics
from tests.benchmark.runners.benchmark_runner import BenchmarkRunner
from tests.benchmark.runners.traceability_logger import TraceabilityLogger

__all__ = [
    'IRMetrics',
    'AccuracyMetrics',
    'BenchmarkRunner',
    'TraceabilityLogger',
]
