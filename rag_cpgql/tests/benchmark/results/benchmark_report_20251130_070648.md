# RAG-CPGQL Benchmark Report

**Run ID:** 20251130_070648
**Timestamp:** 2025-11-30T07:06:48.341915

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 85 |
| Passed | 14 |
| Failed | 71 |
| Pass Rate | 16.5% |
| Scenarios Passed (≥80%) | 2/17 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 5 | 0 | 0.0% | 0.16 | 0.50 | 0.22 | 0.28 |
| Call Graph Navigation | 5 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Data Flow Tracing | 5 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Vulnerability Detection | 5 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Dead Code Detection | 5 | 4 | 80.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Complexity and Hotspots | 5 | 2 | 40.0% | 0.28 | 0.14 | 0.62 | 0.23 |
| Code Duplicates | 5 | 2 | 40.0% | 0.06 | 0.17 | 0.07 | 0.08 |
| Entry Points and Attack Surface | 5 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Concurrency Analysis | 5 | 1 | 20.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Memory Analysis | 5 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Module Dependencies | 5 | 1 | 20.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Auto-documentation | 5 | 0 | 0.0% | 0.13 | 0.40 | 0.25 | 0.29 |
| Subsystem Explanation | 5 | 0 | 0.0% | 0.07 | 0.13 | 0.20 | 0.15 |
| Debugging and Tracing | 5 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| New Vulnerability Detection | 5 | 4 | 80.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Business Logic Understanding | 5 | 0 | 0.0% | 0.05 | 0.10 | 0.07 | 0.06 |
| Test Generation | 5 | 0 | 0.0% | 0.05 | 0.20 | 0.20 | 0.20 |

## Configuration

- Language filter: None
- Difficulty filter: None
- K values: [5, 10, 20]
