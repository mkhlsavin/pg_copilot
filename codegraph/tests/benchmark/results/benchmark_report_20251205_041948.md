# RAG-CPGQL Benchmark Report

**Run ID:** 20251205_041948
**Timestamp:** 2025-12-05T04:19:48.859136

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 85 |
| Passed | 65 |
| Failed | 20 |
| Pass Rate | 76.5% |
| Scenarios Passed (≥80%) | 16/17 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 5 | 3 | 60.0% | 0.66 | 0.90 | 0.90 | 0.85 |
| Call Graph Navigation | 5 | 4 | 80.0% | 0.32 | 0.66 | 0.70 | 0.65 |
| Data Flow Tracing | 5 | 4 | 80.0% | 0.70 | 0.80 | 0.80 | 0.80 |
| Vulnerability Detection | 5 | 3 | 60.0% | 0.05 | 0.25 | 0.10 | 0.09 |
| Dead Code Detection | 5 | 5 | 100.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Complexity and Hotspots | 5 | 4 | 80.0% | 0.80 | 0.73 | 1.00 | 0.83 |
| Code Duplicates | 5 | 3 | 60.0% | 0.29 | 0.67 | 0.50 | 0.56 |
| Entry Points and Attack Surface | 5 | 4 | 80.0% | 0.88 | 0.84 | 1.00 | 0.88 |
| Concurrency Analysis | 5 | 4 | 80.0% | 0.92 | 0.92 | 1.00 | 0.94 |
| Memory Analysis | 5 | 4 | 80.0% | 0.84 | 1.00 | 1.00 | 1.00 |
| Module Dependencies | 5 | 4 | 80.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Auto-documentation | 5 | 4 | 80.0% | 0.82 | 1.00 | 1.00 | 1.00 |
| Subsystem Explanation | 5 | 2 | 40.0% | 0.54 | 0.80 | 0.80 | 0.80 |
| Debugging and Tracing | 5 | 5 | 100.0% | 0.85 | 1.00 | 1.00 | 1.00 |
| New Vulnerability Detection | 5 | 3 | 60.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Business Logic Understanding | 5 | 5 | 100.0% | 1.00 | 1.00 | 1.00 | 1.00 |
| Test Generation | 5 | 4 | 80.0% | 0.80 | 0.80 | 0.80 | 0.80 |

## Configuration

- Language filter: None
- Difficulty filter: None
- K values: [5, 10, 20]
