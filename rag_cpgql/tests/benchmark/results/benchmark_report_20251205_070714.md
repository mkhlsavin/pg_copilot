# RAG-CPGQL Benchmark Report

**Run ID:** 20251205_070714
**Timestamp:** 2025-12-05T07:07:14.249117

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 15 |
| Passed | 10 |
| Failed | 5 |
| Pass Rate | 66.7% |
| Scenarios Passed (≥80%) | 3/3 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 5 | 3 | 60.0% | 0.66 | 0.90 | 0.90 | 0.85 |
| Vulnerability Detection | 5 | 3 | 60.0% | 0.05 | 0.25 | 0.10 | 0.09 |
| Subsystem Explanation | 5 | 4 | 80.0% | 0.47 | 0.80 | 0.80 | 0.80 |

## Configuration

- Language filter: None
- Difficulty filter: None
- K values: [5, 10, 20]
