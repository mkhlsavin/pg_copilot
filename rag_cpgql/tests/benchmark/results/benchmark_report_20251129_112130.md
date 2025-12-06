# RAG-CPGQL Benchmark Report

**Run ID:** 20251129_112130
**Timestamp:** 2025-11-29T11:21:30.918723

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 170 |
| Passed | 84 |
| Failed | 86 |
| Pass Rate | 49.4% |
| Scenarios Passed (≥80%) | 12/17 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 10 | 5 | 50.0% | 0.54 | 0.60 | 0.70 | 0.59 |
| Call Graph Navigation | 10 | 8 | 80.0% | 0.34 | 0.76 | 0.74 | 0.69 |
| Data Flow Tracing | 10 | 2 | 20.0% | 0.29 | 0.18 | 0.51 | 0.23 |
| Vulnerability Detection | 10 | 7 | 70.0% | 0.00 | 0.00 | 0.06 | 0.00 |
| Dead Code Detection | 10 | 6 | 60.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Complexity and Hotspots | 10 | 7 | 70.0% | 0.32 | 0.29 | 0.40 | 0.33 |
| Code Duplicates | 10 | 6 | 60.0% | 0.07 | 0.33 | 0.33 | 0.33 |
| Entry Points and Attack Surface | 10 | 2 | 20.0% | 0.06 | 0.07 | 0.12 | 0.08 |
| Concurrency Analysis | 10 | 4 | 40.0% | 0.14 | 0.56 | 0.63 | 0.58 |
| Memory Analysis | 10 | 3 | 30.0% | 0.14 | 0.65 | 0.65 | 0.62 |
| Module Dependencies | 10 | 6 | 60.0% | 0.33 | 0.50 | 1.00 | 0.61 |
| Auto-documentation | 10 | 5 | 50.0% | 0.24 | 0.82 | 0.80 | 0.79 |
| Subsystem Explanation | 10 | 5 | 50.0% | 0.49 | 0.80 | 0.80 | 0.80 |
| Debugging and Tracing | 10 | 5 | 50.0% | 0.43 | 0.43 | 0.43 | 0.43 |
| New Vulnerability Detection | 10 | 5 | 50.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Business Logic Understanding | 10 | 3 | 30.0% | 0.42 | 0.80 | 0.80 | 0.80 |
| Test Generation | 10 | 5 | 50.0% | 0.50 | 0.50 | 0.50 | 0.50 |

## Configuration

- Language filter: en
- Difficulty filter: None
- K values: [5, 10, 20]
