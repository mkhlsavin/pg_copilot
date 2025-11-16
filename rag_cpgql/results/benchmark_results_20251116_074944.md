# SQL Query Performance Benchmark Report

**Date:** 2025-11-16 07:49:44

**Database:** sample_cpg_v2.duckdb

**Total Queries:** 8


## Performance Summary

| Query | Mean Time (ms) | Median (ms) | Min (ms) | Max (ms) | Results | Memory (MB) |
|-------|----------------|-------------|----------|----------|---------|-------------|
| find_method (find_method) | 2.576 | 2.596 | 2.122 | 3.206 | 1 | 0.20 |
| methods_in_file (methods_in_file) | 1.701 | 1.634 | 1.416 | 2.240 | 3 | 0.13 |
| top_callers (top_callers) | 6.378 | 6.409 | 5.685 | 6.788 | 5 | 0.14 |
| top_callees (top_callees) | 4.196 | 4.075 | 3.102 | 5.771 | 5 | 0.14 |
| get_all_methods | 3.917 | 3.857 | 3.516 | 4.902 | 5 | 0.43 |
| count_call_edges | 0.897 | 0.866 | 0.701 | 1.251 | 1 | 0.04 |
| methods_with_calls_join | 2.450 | 2.265 | 2.016 | 3.653 | 5 | 0.07 |
| cpg_statistics | 1.550 | 1.524 | 1.235 | 1.991 | 1 | 0.11 |

## Detailed Results


### 1. find_method (find_method)

- **Mean execution time:** 2.576 ms
- **Median execution time:** 2.596 ms
- **Min/Max:** 2.122 / 3.206 ms
- **Std deviation:** 0.315 ms
- **Memory peak:** 0.20 MB
- **Result count:** 1
- **Successful runs:** 20/20
- **Generation time:** 0.259 ms
- **Template:** find_method

### 2. methods_in_file (methods_in_file)

- **Mean execution time:** 1.701 ms
- **Median execution time:** 1.634 ms
- **Min/Max:** 1.416 / 2.240 ms
- **Std deviation:** 0.256 ms
- **Memory peak:** 0.13 MB
- **Result count:** 3
- **Successful runs:** 20/20
- **Generation time:** 0.228 ms
- **Template:** methods_in_file

### 3. top_callers (top_callers)

- **Mean execution time:** 6.378 ms
- **Median execution time:** 6.409 ms
- **Min/Max:** 5.685 / 6.788 ms
- **Std deviation:** 0.315 ms
- **Memory peak:** 0.14 MB
- **Result count:** 5
- **Successful runs:** 20/20
- **Generation time:** 0.087 ms
- **Template:** top_callers

### 4. top_callees (top_callees)

- **Mean execution time:** 4.196 ms
- **Median execution time:** 4.075 ms
- **Min/Max:** 3.102 / 5.771 ms
- **Std deviation:** 0.625 ms
- **Memory peak:** 0.14 MB
- **Result count:** 5
- **Successful runs:** 20/20
- **Generation time:** 0.096 ms
- **Template:** top_callees

### 5. get_all_methods

- **Mean execution time:** 3.917 ms
- **Median execution time:** 3.857 ms
- **Min/Max:** 3.516 / 4.902 ms
- **Std deviation:** 0.366 ms
- **Memory peak:** 0.43 MB
- **Result count:** 5
- **Successful runs:** 20/20

### 6. count_call_edges

- **Mean execution time:** 0.897 ms
- **Median execution time:** 0.866 ms
- **Min/Max:** 0.701 / 1.251 ms
- **Std deviation:** 0.160 ms
- **Memory peak:** 0.04 MB
- **Result count:** 1
- **Successful runs:** 20/20

### 7. methods_with_calls_join

- **Mean execution time:** 2.450 ms
- **Median execution time:** 2.265 ms
- **Min/Max:** 2.016 / 3.653 ms
- **Std deviation:** 0.481 ms
- **Memory peak:** 0.07 MB
- **Result count:** 5
- **Successful runs:** 20/20

### 8. cpg_statistics

- **Mean execution time:** 1.550 ms
- **Median execution time:** 1.524 ms
- **Min/Max:** 1.235 / 1.991 ms
- **Std deviation:** 0.213 ms
- **Memory peak:** 0.11 MB
- **Result count:** 1
- **Successful runs:** 20/20