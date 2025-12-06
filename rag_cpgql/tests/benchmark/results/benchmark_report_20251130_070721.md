# RAG-CPGQL Benchmark Report

**Run ID:** 20251130_070721
**Timestamp:** 2025-11-30T07:07:21.562133

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 85 |
| Passed | 3 |
| Failed | 82 |
| Pass Rate | 3.5% |
| Scenarios Passed (≥80%) | 1/17 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 5 | 0 | 0.0% | 0.66 | 0.90 | 0.90 | 0.85 |
| Call Graph Navigation | 5 | 0 | 0.0% | 0.31 | 0.66 | 0.70 | 0.65 |
| Data Flow Tracing | 5 | 0 | 0.0% | 0.90 | 1.00 | 1.00 | 1.00 |
| Vulnerability Detection | 5 | 3 | 60.0% | 0.20 | 0.50 | 0.31 | 0.32 |
| Dead Code Detection | 5 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Complexity and Hotspots | 5 | 0 | 0.0% | 0.80 | 0.73 | 1.00 | 0.83 |
| Code Duplicates | 5 | 0 | 0.0% | 0.07 | 0.33 | 0.33 | 0.33 |
| Entry Points and Attack Surface | 5 | 0 | 0.0% | 0.88 | 0.84 | 1.00 | 0.88 |
| Concurrency Analysis | 5 | 0 | 0.0% | 0.47 | 0.67 | 0.75 | 0.69 |
| Memory Analysis | 5 | 0 | 0.0% | 0.84 | 1.00 | 1.00 | 1.00 |
| Module Dependencies | 5 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Auto-documentation | 5 | 0 | 0.0% | 0.14 | 0.80 | 0.70 | 0.73 |
| Subsystem Explanation | 5 | 0 | 0.0% | 0.54 | 0.80 | 0.80 | 0.80 |
| Debugging and Tracing | 5 | 0 | 0.0% | 0.50 | 0.50 | 0.50 | 0.50 |
| New Vulnerability Detection | 5 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Business Logic Understanding | 5 | 0 | 0.0% | 1.00 | 1.00 | 1.00 | 1.00 |
| Test Generation | 5 | 0 | 0.0% | 0.80 | 0.80 | 0.80 | 0.80 |

## Configuration

- Language filter: None
- Difficulty filter: None
- K values: [5, 10, 20]
