# RAG-CPGQL Benchmark Report

**Run ID:** 20251205_182125
**Timestamp:** 2025-12-05T18:21:25.851080

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 20 |
| Passed | 6 |
| Failed | 14 |
| Pass Rate | 30.0% |
| Scenarios Passed (≥80%) | 0/4 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Data Flow Tracing | 5 | 1 | 20.0% | 0.20 | 0.20 | 0.20 | 0.20 |
| Code Duplicates | 5 | 2 | 40.0% | 0.30 | 0.67 | 0.50 | 0.54 |
| Entry Points and Attack Surface | 5 | 1 | 20.0% | 0.03 | 0.12 | 0.08 | 0.07 |
| Memory Analysis | 5 | 2 | 40.0% | 0.30 | 0.67 | 0.63 | 0.58 |

## Configuration

- Language filter: None
- Difficulty filter: None
- K values: [5, 10, 20]
