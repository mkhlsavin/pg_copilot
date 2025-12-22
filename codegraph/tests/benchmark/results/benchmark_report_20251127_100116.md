# RAG-CPGQL Benchmark Report

**Run ID:** 20251127_100116
**Timestamp:** 2025-11-27T10:01:16.933715

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 12 |
| Passed | 11 |
| Failed | 1 |
| Pass Rate | 91.7% |
| Scenarios Passed (≥80%) | 4/4 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 3 | 3 | 100.0% | 1.00 | 1.00 | 1.00 | 1.00 |
| Call Graph Navigation | 3 | 3 | 100.0% | 0.47 | 0.86 | 0.67 | 0.70 |
| Data Flow Tracing | 3 | 3 | 100.0% | 0.50 | 0.78 | 1.00 | 0.80 |
| Vulnerability Detection | 3 | 2 | 66.7% | 0.60 | 0.50 | 0.33 | 0.40 |

## Configuration

- Language filter: en
- Difficulty filter: None
- K values: [5, 10, 20]
