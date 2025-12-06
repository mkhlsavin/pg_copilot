# RAG-CPGQL Benchmark Report

**Run ID:** 20251205_195628
**Timestamp:** 2025-12-05T19:56:28.001514

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
| Code Duplicates | 5 | 3 | 60.0% | 0.21 | 0.67 | 0.67 | 0.64 |
| Entry Points and Attack Surface | 5 | 4 | 80.0% | 0.88 | 0.84 | 1.00 | 0.88 |
| Memory Analysis | 5 | 3 | 60.0% | 0.84 | 1.00 | 0.83 | 0.88 |

## Configuration

- Language filter: None
- Difficulty filter: None
- K values: [5, 10, 20]
