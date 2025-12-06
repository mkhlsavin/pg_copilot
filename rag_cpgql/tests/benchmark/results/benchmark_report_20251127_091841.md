# RAG-CPGQL Benchmark Report

**Run ID:** 20251127_091841
**Timestamp:** 2025-11-27T09:18:41.093565

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 12 |
| Passed | 10 |
| Failed | 2 |
| Pass Rate | 83.3% |
| Scenarios Passed (≥80%) | 3/4 |

## Scenario Results

| Scenario | Total | Passed | Pass Rate | P@10 | R@10 | MRR | NDCG@10 |
|----------|-------|--------|-----------|------|------|-----|---------|
| Definition Search | 3 | 3 | 100.0% | 1.00 | 1.00 | 1.00 | 1.00 |
| Call Graph Navigation | 3 | 3 | 100.0% | 0.57 | 0.95 | 0.83 | 0.88 |
| Data Flow Tracing | 3 | 1 | 33.3% | 0.22 | 0.33 | 0.67 | 0.41 |
| Vulnerability Detection | 3 | 3 | 100.0% | 0.60 | 0.50 | 0.50 | 0.46 |

## Configuration

- Language filter: en
- Difficulty filter: None
- K values: [5, 10, 20]
