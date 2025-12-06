# RAG-CPGQL Benchmark Report

**Run ID:** 20251127_141000
**Timestamp:** 2025-11-27T14:10:00.767170

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 40 |
| Passed | 26 |
| Failed | 14 |
| Pass Rate | 65.0% |
| Scenarios Passed (≥80%) | 3/4 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 10 | 7 | 70.0% | 0.88 | 0.64 | 0.88 | 0.68 |
| Call Graph Navigation | 10 | 8 | 80.0% | 0.39 | 0.79 | 0.69 | 0.67 |
| Data Flow Tracing | 10 | 4 | 40.0% | 0.50 | 0.40 | 0.95 | 0.47 |
| Vulnerability Detection | 10 | 7 | 70.0% | 0.27 | 0.22 | 0.17 | 0.20 |

## Configuration

- Language filter: en
- Difficulty filter: None
- K values: [5, 10, 20]
