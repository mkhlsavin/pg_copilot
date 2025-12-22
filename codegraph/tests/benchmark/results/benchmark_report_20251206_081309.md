# RAG-CPGQL Benchmark Report

**Run ID:** 20251206_081309
**Timestamp:** 2025-12-06T08:13:09.957314

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 85 |
| Passed | 59 |
| Failed | 26 |
| Pass Rate | 69.4% |
| Scenarios Passed (≥80%) | 17/17 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 5 | 3 | 60.0% | 0.69 | 1.00 | 0.90 | 0.90 |
| Call Graph Navigation | 5 | 3 | 60.0% | 0.24 | 0.46 | 0.50 | 0.47 |
| Data Flow Tracing | 5 | 3 | 60.0% | 0.70 | 0.80 | 0.80 | 0.80 |
| Vulnerability Detection | 5 | 3 | 60.0% | 0.15 | 0.25 | 0.55 | 0.29 |
| Dead Code Detection | 5 | 3 | 60.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Complexity and Hotspots | 5 | 4 | 80.0% | 0.80 | 0.73 | 1.00 | 0.83 |
| Code Duplicates | 5 | 3 | 60.0% | 0.21 | 0.67 | 0.67 | 0.64 |
| Entry Points and Attack Surface | 5 | 4 | 80.0% | 0.88 | 0.84 | 1.00 | 0.88 |
| Concurrency Analysis | 5 | 3 | 60.0% | 0.75 | 0.75 | 0.75 | 0.75 |
| Memory Analysis | 5 | 3 | 60.0% | 0.84 | 1.00 | 0.83 | 0.88 |
| Module Dependencies | 5 | 4 | 80.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Auto-documentation | 5 | 3 | 60.0% | 0.82 | 1.00 | 1.00 | 1.00 |
| Subsystem Explanation | 5 | 5 | 100.0% | 0.52 | 1.00 | 1.00 | 1.00 |
| Debugging and Tracing | 5 | 5 | 100.0% | 0.85 | 1.00 | 1.00 | 1.00 |
| New Vulnerability Detection | 5 | 3 | 60.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Business Logic Understanding | 5 | 3 | 60.0% | 0.80 | 0.90 | 1.00 | 0.92 |
| Test Generation | 5 | 4 | 80.0% | 0.80 | 0.80 | 0.80 | 0.80 |

## Configuration

- Language filter: None
- Difficulty filter: None
- K values: [5, 10, 20]
