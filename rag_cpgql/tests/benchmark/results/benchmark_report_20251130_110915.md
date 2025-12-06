# RAG-CPGQL Benchmark Report

**Run ID:** 20251130_110915
**Timestamp:** 2025-11-30T11:09:15.255140

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 8 |
| Passed | 3 |
| Failed | 5 |
| Pass Rate | 37.5% |
| Scenarios Passed (≥80%) | 2/4 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 2 | 0 | 0.0% | 0.12 | 0.50 | 0.25 | 0.32 |
| Vulnerability Detection | 2 | 0 | 0.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Dead Code Detection | 2 | 1 | 50.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Code Duplicates | 2 | 2 | 100.0% | 0.00 | 0.00 | 0.00 | 0.00 |

## Configuration

- Language filter: None
- Difficulty filter: None
- K values: [5, 10, 20]
