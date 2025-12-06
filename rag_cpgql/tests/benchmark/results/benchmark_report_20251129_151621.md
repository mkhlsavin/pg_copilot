# RAG-CPGQL Benchmark Report

**Run ID:** 20251129_151621
**Timestamp:** 2025-11-29T15:16:21.157172

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 50 |
| Passed | 20 |
| Failed | 30 |
| Pass Rate | 40.0% |
| Scenarios Passed (≥80%) | 3/5 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Data Flow Tracing | 10 | 5 | 50.0% | 0.45 | 0.44 | 0.70 | 0.48 |
| Entry Points and Attack Surface | 10 | 5 | 50.0% | 0.61 | 0.60 | 0.67 | 0.62 |
| Concurrency Analysis | 10 | 3 | 30.0% | 0.37 | 0.52 | 0.63 | 0.55 |
| Memory Analysis | 10 | 1 | 10.0% | 0.57 | 0.75 | 0.75 | 0.72 |
| Business Logic Understanding | 10 | 6 | 60.0% | 1.00 | 1.00 | 1.00 | 1.00 |

## Configuration

- Language filter: en
- Difficulty filter: None
- K values: [5, 10, 20]
