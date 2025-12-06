# RAG-CPGQL Benchmark Report

**Run ID:** 20251127_104431
**Timestamp:** 2025-11-27T10:44:31.634831

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 40 |
| Passed | 23 |
| Failed | 17 |
| Pass Rate | 57.5% |
| Scenarios Passed (≥80%) | 3/4 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 10 | 7 | 70.0% | 0.88 | 0.64 | 0.88 | 0.68 |
| Call Graph Navigation | 10 | 8 | 80.0% | 0.39 | 0.79 | 0.69 | 0.67 |
| Data Flow Tracing | 10 | 3 | 30.0% | 0.41 | 0.52 | 0.70 | 0.54 |
| Vulnerability Detection | 10 | 5 | 50.0% | 0.17 | 0.25 | 0.14 | 0.18 |

## Configuration

- Language filter: en
- Difficulty filter: None
- K values: [5, 10, 20]
