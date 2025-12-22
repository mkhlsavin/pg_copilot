# RAG-CPGQL Benchmark Report

**Run ID:** 20251127_134244
**Timestamp:** 2025-11-27T13:42:44.535463

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 40 |
| Passed | 22 |
| Failed | 18 |
| Pass Rate | 55.0% |
| Scenarios Passed (≥80%) | 2/4 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 10 | 7 | 70.0% | 0.88 | 0.64 | 0.88 | 0.68 |
| Call Graph Navigation | 10 | 8 | 80.0% | 0.39 | 0.79 | 0.69 | 0.67 |
| Data Flow Tracing | 10 | 3 | 30.0% | 0.45 | 0.52 | 0.90 | 0.57 |
| Vulnerability Detection | 10 | 4 | 40.0% | 0.10 | 0.08 | 0.08 | 0.08 |

## Configuration

- Language filter: en
- Difficulty filter: None
- K values: [5, 10, 20]
