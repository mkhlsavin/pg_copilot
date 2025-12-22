# RAG-CPGQL Benchmark Report

**Run ID:** 20251130_111509
**Timestamp:** 2025-11-30T11:15:09.939604

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 12 |
| Passed | 9 |
| Failed | 3 |
| Pass Rate | 75.0% |
| Scenarios Passed (≥80%) | 4/4 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 3 | 2 | 66.7% | 0.73 | 1.00 | 0.83 | 0.88 |
| Vulnerability Detection | 3 | 2 | 66.7% | 0.00 | 0.00 | 0.08 | 0.00 |
| Dead Code Detection | 3 | 3 | 100.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Code Duplicates | 3 | 2 | 66.7% | 0.00 | 0.00 | 0.00 | 0.00 |

## Configuration

- Language filter: None
- Difficulty filter: None
- K values: [5, 10, 20]
