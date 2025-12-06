# RAG-CPGQL Benchmark Report

**Run ID:** 20251127_135942
**Timestamp:** 2025-11-27T13:59:42.802557

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 40 |
| Passed | 25 |
| Failed | 15 |
| Pass Rate | 62.5% |
| Scenarios Passed (≥80%) | 3/4 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 10 | 7 | 70.0% | 0.88 | 0.64 | 0.88 | 0.68 |
| Call Graph Navigation | 10 | 8 | 80.0% | 0.39 | 0.79 | 0.69 | 0.67 |
| Data Flow Tracing | 10 | 4 | 40.0% | 0.45 | 0.45 | 0.90 | 0.51 |
| Vulnerability Detection | 10 | 6 | 60.0% | 0.27 | 0.22 | 0.33 | 0.25 |

## Configuration

- Language filter: en
- Difficulty filter: None
- K values: [5, 10, 20]
