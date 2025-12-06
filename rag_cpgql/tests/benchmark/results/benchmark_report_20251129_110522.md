# RAG-CPGQL Benchmark Report

**Run ID:** 20251129_110522
**Timestamp:** 2025-11-29T11:05:22.338608

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 34 |
| Passed | 24 |
| Failed | 10 |
| Pass Rate | 70.6% |
| Scenarios Passed (≥80%) | 17/17 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 2 | 1 | 50.0% | 0.60 | 1.00 | 0.75 | 0.82 |
| Call Graph Navigation | 2 | 2 | 100.0% | 0.37 | 0.79 | 0.75 | 0.72 |
| Data Flow Tracing | 2 | 1 | 50.0% | 0.19 | 0.30 | 0.50 | 0.34 |
| Vulnerability Detection | 2 | 1 | 50.0% | 0.00 | 0.00 | 0.09 | 0.00 |
| Dead Code Detection | 2 | 1 | 50.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Complexity and Hotspots | 2 | 2 | 100.0% | 0.80 | 0.73 | 1.00 | 0.83 |
| Code Duplicates | 2 | 2 | 100.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Entry Points and Attack Surface | 2 | 2 | 100.0% | 0.50 | 0.62 | 1.00 | 0.75 |
| Concurrency Analysis | 2 | 1 | 50.0% | 0.25 | 1.00 | 1.00 | 1.00 |
| Memory Analysis | 2 | 1 | 50.0% | 0.20 | 1.00 | 1.00 | 1.00 |
| Module Dependencies | 2 | 2 | 100.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Auto-documentation | 2 | 1 | 50.0% | 0.32 | 1.00 | 0.75 | 0.82 |
| Subsystem Explanation | 2 | 2 | 100.0% | 0.60 | 1.00 | 1.00 | 1.00 |
| Debugging and Tracing | 2 | 1 | 50.0% | 1.00 | 1.00 | 1.00 | 1.00 |
| New Vulnerability Detection | 2 | 1 | 50.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Business Logic Understanding | 2 | 1 | 50.0% | 0.70 | 1.00 | 1.00 | 1.00 |
| Test Generation | 2 | 2 | 100.0% | 1.00 | 1.00 | 1.00 | 1.00 |

## Configuration

- Language filter: en
- Difficulty filter: None
- K values: [5, 10, 20]
