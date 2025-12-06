# RAG-CPGQL Benchmark Report

**Run ID:** 20251130_110932
**Timestamp:** 2025-11-30T11:09:32.076346

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 12 |
| Passed | 10 |
| Failed | 2 |
| Pass Rate | 83.3% |
| Scenarios Passed (≥80%) | 4/4 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 3 | 2 | 66.7% | 0.73 | 1.00 | 0.83 | 0.88 |
| Vulnerability Detection | 3 | 3 | 100.0% | 0.30 | 0.50 | 0.50 | 0.47 |
| Dead Code Detection | 3 | 3 | 100.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Code Duplicates | 3 | 2 | 66.7% | 0.00 | 0.00 | 0.00 | 0.00 |

## Configuration

- Language filter: None
- Difficulty filter: None
- K values: [5, 10, 20]
