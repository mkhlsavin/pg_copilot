# RAG-CPGQL Benchmark Report

**Run ID:** 20251127_090846
**Timestamp:** 2025-11-27T09:08:46.347121

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 12 |
| Passed | 10 |
| Failed | 2 |
| Pass Rate | 83.3% |
| Scenarios Passed (≥80%) | 4/4 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 3 | 2 | 66.7% | 1.00 | 1.00 | 1.00 | 1.00 |
| Call Graph Navigation | 3 | 3 | 100.0% | 0.60 | 1.00 | 0.83 | 0.83 |
| Data Flow Tracing | 3 | 2 | 66.7% | 0.22 | 0.33 | 0.67 | 0.41 |
| Vulnerability Detection | 3 | 3 | 100.0% | 0.60 | 0.50 | 1.00 | 0.64 |

## Configuration

- Language filter: en
- Difficulty filter: None
- K values: [5, 10, 20]
