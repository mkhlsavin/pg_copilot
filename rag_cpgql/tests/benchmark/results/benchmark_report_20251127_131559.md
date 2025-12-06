# RAG-CPGQL Benchmark Report

**Run ID:** 20251127_131559
**Timestamp:** 2025-11-27T13:15:59.481850

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 20 |
| Passed | 15 |
| Failed | 5 |
| Pass Rate | 75.0% |
| Scenarios Passed (≥80%) | 4/4 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 5 | 5 | 100.0% | 1.00 | 0.90 | 1.00 | 0.92 |
| Call Graph Navigation | 5 | 4 | 80.0% | 0.38 | 0.71 | 0.60 | 0.62 |
| Data Flow Tracing | 5 | 3 | 60.0% | 0.36 | 0.56 | 1.00 | 0.63 |
| Vulnerability Detection | 5 | 3 | 60.0% | 0.20 | 0.17 | 0.33 | 0.18 |

## Configuration

- Language filter: en
- Difficulty filter: None
- K values: [5, 10, 20]
