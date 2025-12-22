# RAG-CPGQL Benchmark Report

**Run ID:** 20251127_100303
**Timestamp:** 2025-11-27T10:03:03.511307

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 40 |
| Passed | 19 |
| Failed | 21 |
| Pass Rate | 47.5% |
| Scenarios Passed (≥80%) | 2/4 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 10 | 6 | 60.0% | 0.86 | 0.69 | 0.86 | 0.73 |
| Call Graph Navigation | 10 | 5 | 50.0% | 0.28 | 0.67 | 0.52 | 0.52 |
| Data Flow Tracing | 10 | 4 | 40.0% | 0.41 | 0.52 | 0.70 | 0.54 |
| Vulnerability Detection | 10 | 4 | 40.0% | 0.20 | 0.28 | 0.21 | 0.21 |

## Configuration

- Language filter: en
- Difficulty filter: None
- K values: [5, 10, 20]
