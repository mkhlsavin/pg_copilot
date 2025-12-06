# RAG-CPGQL Benchmark Report

**Run ID:** 20251128_192426
**Timestamp:** 2025-11-28T19:24:26.664527

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 85 |
| Passed | 32 |
| Failed | 53 |
| Pass Rate | 37.6% |
| Scenarios Passed (≥80%) | 8/17 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 5 | 4 | 80.0% | 0.80 | 0.80 | 0.80 | 0.80 |
| Call Graph Navigation | 5 | 3 | 60.0% | 0.35 | 0.71 | 0.61 | 0.63 |
| Data Flow Tracing | 5 | 3 | 60.0% | 0.36 | 0.56 | 1.00 | 0.63 |
| Vulnerability Detection | 5 | 3 | 60.0% | 0.05 | 0.25 | 0.29 | 0.19 |
| Dead Code Detection | 5 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Complexity and Hotspots | 5 | 5 | 100.0% | 0.80 | 0.73 | 1.00 | 0.87 |
| Code Duplicates | 5 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Entry Points and Attack Surface | 5 | 2 | 40.0% | 0.12 | 0.16 | 0.25 | 0.19 |
| Concurrency Analysis | 5 | 1 | 20.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Memory Analysis | 5 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Module Dependencies | 5 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Auto-documentation | 5 | 4 | 80.0% | 0.27 | 0.80 | 0.80 | 0.80 |
| Subsystem Explanation | 5 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Debugging and Tracing | 5 | 0 | 0.0% | 0.06 | 0.25 | 0.25 | 0.25 |
| New Vulnerability Detection | 5 | 4 | 80.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Business Logic Understanding | 5 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Test Generation | 5 | 3 | 60.0% | 0.25 | 0.80 | 0.70 | 0.73 |

## Configuration

- Language filter: en
- Difficulty filter: None
- K values: [5, 10, 20]
