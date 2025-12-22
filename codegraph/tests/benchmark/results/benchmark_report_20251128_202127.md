# RAG-CPGQL Benchmark Report

**Run ID:** 20251128_202127
**Timestamp:** 2025-11-28T20:21:27.036315

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 8 |
| Passed | 4 |
| Failed | 4 |
| Pass Rate | 50.0% |
| Scenarios Passed (≥80%) | 3/4 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Dead Code Detection | 2 | 1 | 50.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Code Duplicates | 2 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Module Dependencies | 2 | 1 | 50.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Subsystem Explanation | 2 | 2 | 100.0% | 0.60 | 1.00 | 1.00 | 1.00 |

## Configuration

- Language filter: en
- Difficulty filter: None
- K values: [5, 10, 20]
