# RAG-CPGQL Benchmark Report

**Run ID:** 20251205_071947
**Timestamp:** 2025-12-05T07:19:47.708249

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 15 |
| Passed | 12 |
| Failed | 3 |
| Pass Rate | 80.0% |
| Scenarios Passed (≥80%) | 3/3 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 5 | 3 | 60.0% | 0.69 | 1.00 | 0.90 | 0.90 |
| Vulnerability Detection | 5 | 4 | 80.0% | 0.42 | 0.75 | 0.55 | 0.59 |
| Subsystem Explanation | 5 | 5 | 100.0% | 0.52 | 1.00 | 1.00 | 1.00 |

## Configuration

- Language filter: None
- Difficulty filter: None
- K values: [5, 10, 20]
