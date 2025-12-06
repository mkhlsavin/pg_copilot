# RAG-CPGQL Benchmark Report

**Run ID:** 20251130_113158
**Timestamp:** 2025-11-30T11:31:58.674379

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 20 |
| Passed | 11 |
| Failed | 9 |
| Pass Rate | 55.0% |
| Scenarios Passed (≥80%) | 3/4 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 5 | 3 | 60.0% | 0.66 | 0.90 | 0.90 | 0.85 |
| Vulnerability Detection | 5 | 3 | 60.0% | 0.00 | 0.00 | 0.09 | 0.00 |
| Dead Code Detection | 5 | 2 | 40.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Code Duplicates | 5 | 3 | 60.0% | 0.29 | 0.67 | 0.50 | 0.56 |

## Configuration

- Language filter: None
- Difficulty filter: None
- K values: [5, 10, 20]
