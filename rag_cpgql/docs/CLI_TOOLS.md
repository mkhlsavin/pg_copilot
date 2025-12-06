# CLI Tools Reference

This document describes the command-line tools available in RAG-CPGQL for benchmarking, testing, and CPG export.

## Quick Reference

| Tool | Purpose | Typical Usage |
|------|---------|---------------|
| `demo_benchmark.py` | Synthetic benchmark demo | Quick performance testing |
| `benchmark_hybrid_retrieval.py` | Full retrieval benchmark | Evaluate vector vs graph vs hybrid |
| `demo_patch_review.py` | Patch review demo | Demonstrate security analysis |
| `comprehensive_integration_test.py` | Integration tests | Verify algorithms work correctly |
| `export_ast_edges.py` | Export AST edges | Joern → DuckDB data export |
| `tests/benchmark/run_benchmark.py` | Scenario benchmarks | Full multi-scenario evaluation |

---

## demo_benchmark.py

Demonstrates the benchmark framework with synthetic retrieval results. Shows how hybrid retrieval improves over pure vector and pure graph approaches.

### Usage

```bash
python demo_benchmark.py
```

### Features

- Simulates vector, graph, and hybrid retrieval
- Demonstrates P@K, R@K, F1@K, MRR, NDCG metrics
- Reproducible results with random seed
- No external dependencies (synthetic data)

### Output

```
Simulating retrieval for query: Find all authentication functions
Vector:  P@10=0.30, R=0.45, MRR=0.50
Graph:   P@10=0.25, R=0.38, MRR=0.33
Hybrid:  P@10=0.50, R=0.75, MRR=0.67
```

---

## benchmark_hybrid_retrieval.py

Comprehensive benchmark comparing pure vector, pure graph, and hybrid retrieval approaches on real data.

### Usage

```bash
python benchmark_hybrid_retrieval.py [--db cpg.duckdb] [--queries queries.json]
```

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--db` | `cpg.duckdb` | Path to DuckDB CPG database |
| `--queries` | Built-in | Path to benchmark queries JSON file |
| `--top-k` | `10` | Number of results to retrieve |
| `--output` | `benchmark_results/` | Output directory |

### Metrics

- **Precision@K (P@K)**: Fraction of retrieved results that are relevant
- **Recall@K (R@K)**: Fraction of relevant results retrieved
- **F1@K**: Harmonic mean of P@K and R@K
- **MRR**: Mean Reciprocal Rank (average 1/rank of first relevant result)
- **NDCG**: Normalized Discounted Cumulative Gain

### Output Files

- `benchmark_results/report.json` - Full metrics
- `benchmark_results/summary.md` - Human-readable summary

---

## demo_patch_review.py

Demonstrates the automated patch review pipeline with security analysis.

### Usage

```bash
python demo_patch_review.py [--db cpg.duckdb]
```

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--db` | `cpg.duckdb` | Path to DuckDB CPG database |

### Pipeline Steps

1. **Patch Parsing** - Parse unified diff format
2. **Delta CPG Generation** - Create CPG delta for changes
3. **Impact Analysis** - Analyze call graph impact
4. **Security Scanning** - Detect vulnerabilities in new code
5. **Verdict Generation** - Generate review verdict

### Output Files

- `demo_review_output.json` - Structured analysis results
- `demo_review_output.md` - Markdown review report

### Example Output

```markdown
## Patch Review Summary

### Security Findings
- [HIGH] SQL Injection vulnerability in `authenticate()`
  - CWE-89: Improper Neutralization of SQL Commands
  - Location: src/auth/login.py:14

### Verdict: REJECT
Changes introduce security vulnerabilities.
```

---

## comprehensive_integration_test.py

Comprehensive integration test for verifying all fixed algorithms work correctly on the real CPG.

### Usage

```bash
python comprehensive_integration_test.py
```

### Tests Performed

1. **PageRank** - Graph centrality computation
2. **SCC (Tarjan's)** - Strongly connected components
3. **Dominators** - Dominator tree computation
4. **Dead Code Detection** - Unreachable function detection
5. **Hotspot Analysis** - Performance bottleneck identification
6. **Call Graph Traversal** - Forward/backward caller analysis

### Output

```
========================================
COMPREHENSIVE INTEGRATION TEST
Testing all CallGraphAnalyzer algorithms
========================================

TEST 1: PageRank
[OK] Completed in 2.34s
     Results: 100 methods
     Top: main (score: 0.001234)

TEST 2: Strongly Connected Components
[OK] Completed in 1.56s
     Total SCCs: 45
     Largest SCC: 12 methods
...
```

---

## export_ast_edges.py

Exports missing AST edges from Joern CPG server to DuckDB for local analysis.

### Usage

```bash
python export_ast_edges.py --host localhost --port 8080 [--db cpg.duckdb]
```

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--host` | `localhost` | Joern server host |
| `--port` | `8080` | Joern server port |
| `--db` | `cpg.duckdb` | DuckDB database path |
| `--batch-size` | `10000` | Batch size for exports |

### Prerequisites

1. Joern server running with loaded CPG
2. cpgqls-client Python package installed

### Data Exported

- `edges_ast` - AST parent-child relationships
- Updates `nodes_call.filename` and `nodes_call.method_id`

---

## tests/benchmark/run_benchmark.py

Full multi-scenario benchmark runner for evaluating RAG-CPGQL across all 17 scenarios.

### Usage

```bash
python tests/benchmark/run_benchmark.py [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `--quick` | Run quick benchmark (subset of queries) |
| `--scenario N` | Run specific scenario (1-17) |
| `--all-scenarios` | Run all 17 scenarios |
| `--output DIR` | Output directory for results |
| `--verbose` | Verbose logging |

### Scenarios

| # | Scenario | Description |
|---|----------|-------------|
| 1 | Definition Search | Find function/struct definitions |
| 2 | Call Graph | Caller/callee analysis |
| 3 | Data Flow | Taint analysis, reaching definitions |
| 4 | Vulnerability | Security vulnerability detection |
| 5 | Dead Code | Unreachable code detection |
| 6 | Complexity | Cyclomatic complexity, hotspots |
| 7 | Duplicates | Code clone detection |
| 8 | Entry Points | API/CLI entry point detection |
| 9 | Concurrency | Race condition detection |
| 10 | Architecture | Layer/coupling analysis |
| 11 | Dependencies | Cross-repo analysis |
| 12 | Documentation | Comment/doc extraction |
| 13 | Subsystem | Subsystem boundary analysis |
| 14 | Debugging | Debugging-related queries |
| 15 | New Vulnerabilities | Zero-day pattern detection |
| 16 | Business Logic | Domain-specific logic analysis |
| 17 | Test Generation | Test coverage analysis |

### Output

- `tests/benchmark/results/scenario_*.json` - Per-scenario results
- `tests/benchmark/results/summary.md` - Overall summary

---

## Environment Variables

| Variable | Description | Used By |
|----------|-------------|---------|
| `DUCKDB_PATH` | Path to DuckDB database | All tools |
| `LOG_LEVEL` | Logging verbosity | All tools |
| `GIGACHAT_AUTH_KEY` | GigaChat API key | benchmark tools |
| `LLMXCPG_MODEL_PATH` | Local model path | benchmark tools |

## Common Patterns

### Running with specific database

```bash
python demo_patch_review.py --db /path/to/custom.duckdb
```

### Verbose logging

```bash
LOG_LEVEL=DEBUG python comprehensive_integration_test.py
```

### Parallel execution

```bash
# Run multiple scenarios in parallel
python tests/benchmark/run_benchmark.py --scenario 1 &
python tests/benchmark/run_benchmark.py --scenario 2 &
wait
```

## Troubleshooting

### "DuckDB database not found"

Ensure `cpg.duckdb` exists or specify path with `--db`.

### "Joern server not running"

For export tools, start Joern first:
```bash
./joern-server --port 8080
```

### "Model not found"

Set environment variables for local LLM:
```bash
export LLMXCPG_MODEL_PATH=/path/to/model.gguf
```
