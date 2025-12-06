# RAG-CPGQL Benchmark Report

**Run ID:** 20251128_171100
**Timestamp:** 2025-11-28T17:11:00.838944

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 34 |
| Passed | 16 |
| Failed | 18 |
| Pass Rate | 47.1% |
| Scenarios Passed (≥80%) | 9/17 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 2 | 2 | 100.0% | 1.00 | 1.00 | 1.00 | 1.00 |
| Call Graph Navigation | 2 | 2 | 100.0% | 0.50 | 0.79 | 0.75 | 0.72 |
| Data Flow Tracing | 2 | 2 | 100.0% | 0.56 | 0.80 | 1.00 | 0.83 |
| Vulnerability Detection | 2 | 1 | 50.0% | 0.00 | 0.00 | 0.09 | 0.00 |
| Dead Code Detection | 2 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Complexity and Hotspots | 2 | 2 | 100.0% | 0.80 | 0.73 | 1.00 | 0.87 |
| Code Duplicates | 2 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Entry Points and Attack Surface | 2 | 2 | 100.0% | 0.50 | 0.62 | 1.00 | 0.75 |
| Concurrency Analysis | 2 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Memory Analysis | 2 | 0 | 0.0% | 0.12 | 0.17 | 0.12 | 0.10 |
| Module Dependencies | 2 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Auto-documentation | 2 | 2 | 100.0% | 0.33 | 1.00 | 1.00 | 1.00 |
| Subsystem Explanation | 2 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Debugging and Tracing | 2 | 0 | 0.0% | 0.12 | 0.50 | 0.50 | 0.50 |
| New Vulnerability Detection | 2 | 1 | 50.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Business Logic Understanding | 2 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Test Generation | 2 | 2 | 100.0% | 0.33 | 1.00 | 1.00 | 1.00 |

## Configuration

- Language filter: en
- Difficulty filter: None
- K values: [5, 10, 20]
