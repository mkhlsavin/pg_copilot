# RAG-CPGQL Benchmark Report

**Run ID:** 20251130_091806
**Timestamp:** 2025-11-30T09:18:06.861517

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 85 |
| Passed | 15 |
| Failed | 70 |
| Pass Rate | 17.6% |
| Scenarios Passed (≥80%) | 2/17 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 5 | 0 | 0.0% | 0.10 | 0.30 | 0.15 | 0.18 |
| Call Graph Navigation | 5 | 0 | 0.0% | 0.03 | 0.05 | 0.03 | 0.03 |
| Data Flow Tracing | 5 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Vulnerability Detection | 5 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Dead Code Detection | 5 | 4 | 80.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Complexity and Hotspots | 5 | 2 | 40.0% | 0.25 | 0.14 | 0.62 | 0.23 |
| Code Duplicates | 5 | 2 | 40.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Entry Points and Attack Surface | 5 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Concurrency Analysis | 5 | 1 | 20.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Memory Analysis | 5 | 0 | 0.0% | 0.04 | 0.04 | 0.05 | 0.03 |
| Module Dependencies | 5 | 1 | 20.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Auto-documentation | 5 | 0 | 0.0% | 0.13 | 0.60 | 0.32 | 0.39 |
| Subsystem Explanation | 5 | 0 | 0.0% | 0.20 | 0.13 | 0.20 | 0.15 |
| Debugging and Tracing | 5 | 1 | 20.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| New Vulnerability Detection | 5 | 3 | 60.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Business Logic Understanding | 5 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Test Generation | 5 | 1 | 20.0% | 0.19 | 0.60 | 0.32 | 0.39 |

## Configuration

- Language filter: None
- Difficulty filter: None
- K values: [5, 10, 20]
