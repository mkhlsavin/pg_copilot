# RAG-CPGQL Benchmark Report

**Run ID:** 20251205_203908
**Timestamp:** 2025-12-05T20:39:08.028544

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 8 |
| Passed | 6 |
| Failed | 2 |
| Pass Rate | 75.0% |
| Scenarios Passed (≥80%) | 4/4 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Dead Code Detection | 2 | 2 | 100.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Code Duplicates | 2 | 1 | 50.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Concurrency Analysis | 2 | 1 | 50.0% | 1.00 | 1.00 | 1.00 | 1.00 |
| Module Dependencies | 2 | 2 | 100.0% | 0.00 | 0.00 | 0.00 | 0.00 |

## Configuration

- Language filter: None
- Difficulty filter: None
- K values: [5, 10, 20]
