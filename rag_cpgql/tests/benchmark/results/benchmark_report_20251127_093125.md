# RAG-CPGQL Benchmark Report

**Run ID:** 20251127_093125
**Timestamp:** 2025-11-27T09:31:25.317277

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 12 |
| Passed | 8 |
| Failed | 4 |
| Pass Rate | 66.7% |
| Scenarios Passed (≥80%) | 3/4 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 3 | 1 | 33.3% | 1.00 | 1.00 | 1.00 | 1.00 |
| Call Graph Navigation | 3 | 2 | 66.7% | 0.37 | 0.71 | 0.67 | 0.58 |
| Data Flow Tracing | 3 | 2 | 66.7% | 0.33 | 0.50 | 0.67 | 0.51 |
| Vulnerability Detection | 3 | 3 | 100.0% | 0.60 | 0.50 | 0.50 | 0.47 |

## Configuration

- Language filter: en
- Difficulty filter: None
- K values: [5, 10, 20]
