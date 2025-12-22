# RAG-CPGQL Benchmark Report

**Run ID:** 20251129_071623
**Timestamp:** 2025-11-29T07:16:23.072269

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 34 |
| Passed | 21 |
| Failed | 13 |
| Pass Rate | 61.8% |
| Scenarios Passed (≥80%) | 15/17 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 2 | 1 | 50.0% | 0.60 | 1.00 | 0.75 | 0.82 |
| Call Graph Navigation | 2 | 2 | 100.0% | 0.39 | 0.79 | 0.75 | 0.72 |
| Data Flow Tracing | 2 | 1 | 50.0% | 0.44 | 0.72 | 0.67 | 0.64 |
| Vulnerability Detection | 2 | 1 | 50.0% | 0.00 | 0.00 | 0.08 | 0.00 |
| Dead Code Detection | 2 | 2 | 100.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Complexity and Hotspots | 2 | 2 | 100.0% | 0.80 | 0.73 | 1.00 | 0.83 |
| Code Duplicates | 2 | 1 | 50.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Entry Points and Attack Surface | 2 | 2 | 100.0% | 0.50 | 0.62 | 1.00 | 0.75 |
| Concurrency Analysis | 2 | 1 | 50.0% | 0.25 | 1.00 | 1.00 | 1.00 |
| Memory Analysis | 2 | 1 | 50.0% | 0.20 | 1.00 | 1.00 | 1.00 |
| Module Dependencies | 2 | 2 | 100.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Auto-documentation | 2 | 1 | 50.0% | 0.24 | 1.00 | 0.75 | 0.82 |
| Subsystem Explanation | 2 | 2 | 100.0% | 0.60 | 1.00 | 1.00 | 1.00 |
| Debugging and Tracing | 2 | 0 | 0.0% | 0.31 | 1.00 | 1.00 | 1.00 |
| New Vulnerability Detection | 2 | 1 | 50.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Business Logic Understanding | 2 | 1 | 50.0% | 0.33 | 1.00 | 1.00 | 1.00 |
| Test Generation | 2 | 0 | 0.0% | 0.12 | 1.00 | 0.75 | 0.82 |

## Configuration

- Language filter: en
- Difficulty filter: None
- K values: [5, 10, 20]
