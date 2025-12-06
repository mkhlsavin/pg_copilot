# RAG-CPGQL Benchmark Report

**Run ID:** 20251127_133228
**Timestamp:** 2025-11-27T13:32:28.016771

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
| Call Graph Navigation | 5 | 4 | 80.0% | 0.40 | 0.72 | 0.62 | 0.63 |
| Data Flow Tracing | 5 | 3 | 60.0% | 0.41 | 0.55 | 1.00 | 0.60 |
| Vulnerability Detection | 5 | 3 | 60.0% | 0.20 | 0.17 | 0.17 | 0.16 |

## Configuration

- Language filter: en
- Difficulty filter: None
- K values: [5, 10, 20]
