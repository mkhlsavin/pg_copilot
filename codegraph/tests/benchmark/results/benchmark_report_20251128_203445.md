# RAG-CPGQL Benchmark Report

**Run ID:** 20251128_203445
**Timestamp:** 2025-11-28T20:34:45.459688

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 8 |
| Passed | 7 |
| Failed | 1 |
| Pass Rate | 87.5% |
| Scenarios Passed (≥80%) | 4/4 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Dead Code Detection | 2 | 2 | 100.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Code Duplicates | 2 | 2 | 100.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Module Dependencies | 2 | 1 | 50.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Subsystem Explanation | 2 | 2 | 100.0% | 0.60 | 1.00 | 1.00 | 1.00 |

## Configuration

- Language filter: en
- Difficulty filter: None
- K values: [5, 10, 20]
