# RAG-CPGQL Benchmark Report

**Run ID:** 20251129_061115
**Timestamp:** 2025-11-29T06:11:15.561793

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 16 |
| Passed | 10 |
| Failed | 6 |
| Pass Rate | 62.5% |
| Scenarios Passed (≥80%) | 7/8 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Dead Code Detection | 2 | 2 | 100.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Code Duplicates | 2 | 1 | 50.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Concurrency Analysis | 2 | 1 | 50.0% | 0.25 | 1.00 | 1.00 | 1.00 |
| Memory Analysis | 2 | 1 | 50.0% | 0.20 | 1.00 | 1.00 | 1.00 |
| Module Dependencies | 2 | 2 | 100.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Subsystem Explanation | 2 | 2 | 100.0% | 0.60 | 1.00 | 1.00 | 1.00 |
| Debugging and Tracing | 2 | 0 | 0.0% | 0.19 | 1.00 | 1.00 | 1.00 |
| Business Logic Understanding | 2 | 1 | 50.0% | 0.33 | 1.00 | 1.00 | 1.00 |

## Configuration

- Language filter: en
- Difficulty filter: None
- K values: [5, 10, 20]
