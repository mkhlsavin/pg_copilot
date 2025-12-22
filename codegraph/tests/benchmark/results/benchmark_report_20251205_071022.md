# RAG-CPGQL Benchmark Report

**Run ID:** 20251205_071022
**Timestamp:** 2025-12-05T07:10:22.100492

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 15 |
| Passed | 11 |
| Failed | 4 |
| Pass Rate | 73.3% |
| Scenarios Passed (≥80%) | 3/3 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 5 | 4 | 80.0% | 0.82 | 0.90 | 1.00 | 0.92 |
| Vulnerability Detection | 5 | 3 | 60.0% | 0.00 | 0.00 | 0.09 | 0.00 |
| Subsystem Explanation | 5 | 4 | 80.0% | 0.47 | 0.80 | 0.80 | 0.80 |

## Configuration

- Language filter: None
- Difficulty filter: None
- K values: [5, 10, 20]
