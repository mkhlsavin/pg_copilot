# RAG-CPGQL Benchmark Report

**Run ID:** 20251127_105429
**Timestamp:** 2025-11-27T10:54:29.626548

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 40 |
| Passed | 23 |
| Failed | 17 |
| Pass Rate | 57.5% |
| Scenarios Passed (≥80%) | 2/4 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 10 | 7 | 70.0% | 0.88 | 0.64 | 0.88 | 0.68 |
| Call Graph Navigation | 10 | 8 | 80.0% | 0.40 | 0.81 | 0.71 | 0.69 |
| Data Flow Tracing | 10 | 4 | 40.0% | 0.41 | 0.44 | 0.70 | 0.48 |
| Vulnerability Detection | 10 | 4 | 40.0% | 0.13 | 0.17 | 0.09 | 0.11 |

## Configuration

- Language filter: en
- Difficulty filter: None
- K values: [5, 10, 20]
