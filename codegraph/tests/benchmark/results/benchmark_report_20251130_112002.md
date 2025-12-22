# RAG-CPGQL Benchmark Report

**Run ID:** 20251130_112002
**Timestamp:** 2025-11-30T11:20:02.108380

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 20 |
| Passed | 10 |
| Failed | 10 |
| Pass Rate | 50.0% |
| Scenarios Passed (≥80%) | 3/4 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 5 | 3 | 60.0% | 0.66 | 0.90 | 0.90 | 0.85 |
| Vulnerability Detection | 5 | 3 | 60.0% | 0.00 | 0.00 | 0.09 | 0.00 |
| Dead Code Detection | 5 | 3 | 60.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Code Duplicates | 5 | 1 | 20.0% | 0.07 | 0.33 | 0.33 | 0.33 |

## Configuration

- Language filter: None
- Difficulty filter: None
- K values: [5, 10, 20]
