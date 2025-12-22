# RAG-CPGQL Benchmark Report

**Run ID:** 20251205_185555
**Timestamp:** 2025-12-05T18:55:55.190299

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 20 |
| Passed | 9 |
| Failed | 11 |
| Pass Rate | 45.0% |
| Scenarios Passed (≥80%) | 2/4 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Data Flow Tracing | 5 | 3 | 60.0% | 0.70 | 0.80 | 0.80 | 0.80 |
| Code Duplicates | 5 | 2 | 40.0% | 0.30 | 0.67 | 0.50 | 0.54 |
| Entry Points and Attack Surface | 5 | 1 | 20.0% | 0.00 | 0.00 | 0.00 | 0.00 |
| Memory Analysis | 5 | 3 | 60.0% | 0.67 | 0.87 | 0.83 | 0.78 |

## Configuration

- Language filter: None
- Difficulty filter: None
- K values: [5, 10, 20]
