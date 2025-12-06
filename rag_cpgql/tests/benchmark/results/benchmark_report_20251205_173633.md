# RAG-CPGQL Benchmark Report

**Run ID:** 20251205_173633
**Timestamp:** 2025-12-05T17:36:33.226668

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 85 |
| Passed | 51 |
| Failed | 34 |
| Pass Rate | 60.0% |
| Scenarios Passed (≥80%) | 13/17 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 5 | 3 | 60.0% | 0.69 | 1.00 | 0.90 | 0.90 |
| Call Graph Navigation | 5 | 3 | 60.0% | 0.26 | 0.51 | 0.50 | 0.50 |
| Data Flow Tracing | 5 | 1 | 20.0% | 0.20 | 0.20 | 0.20 | 0.20 |
| Vulnerability Detection | 5 | 4 | 80.0% | 0.38 | 0.50 | 0.55 | 0.50 |
| Dead Code Detection | 5 | 4 | 80.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Complexity and Hotspots | 5 | 3 | 60.0% | 0.80 | 0.73 | 1.00 | 0.83 |
| Code Duplicates | 5 | 2 | 40.0% | 0.30 | 0.67 | 0.50 | 0.54 |
| Entry Points and Attack Surface | 5 | 1 | 20.0% | 0.03 | 0.12 | 0.04 | 0.05 |
| Concurrency Analysis | 5 | 3 | 60.0% | 0.75 | 0.75 | 0.75 | 0.75 |
| Memory Analysis | 5 | 1 | 20.0% | 0.30 | 0.67 | 0.63 | 0.58 |
| Module Dependencies | 5 | 4 | 80.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Auto-documentation | 5 | 4 | 80.0% | 0.82 | 1.00 | 1.00 | 1.00 |
| Subsystem Explanation | 5 | 5 | 100.0% | 0.52 | 1.00 | 1.00 | 1.00 |
| Debugging and Tracing | 5 | 3 | 60.0% | 0.45 | 0.75 | 0.75 | 0.75 |
| New Vulnerability Detection | 5 | 3 | 60.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Business Logic Understanding | 5 | 3 | 60.0% | 0.80 | 0.90 | 1.00 | 0.92 |
| Test Generation | 5 | 4 | 80.0% | 0.80 | 0.80 | 0.80 | 0.80 |

## Configuration

- Language filter: None
- Difficulty filter: None
- K values: [5, 10, 20]
