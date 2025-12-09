# RAG-CPGQL Benchmark Suite

Comprehensive benchmark suite for evaluating the RAG-CPGQL Code Property Graph Copilot system across 16 enterprise usage scenarios.

## Overview

This benchmark evaluates the system's ability to:
- Find code definitions and references
- Navigate call graphs and data flows
- Detect security vulnerabilities
- Analyze code complexity and performance
- Support various code analysis workflows

### Key Statistics

| Metric | Value |
|--------|-------|
| Total Scenarios | 16 |
| Total Questions | 530+ |
| Languages | English, Russian |
| Difficulty Levels | Easy, Medium, Hard |

## Quick Start

```bash
# Run quick benchmark (5 questions per scenario)
python -m tests.benchmark.run_benchmark --quick --language en

# Run specific scenarios
python -m tests.benchmark.run_benchmark --scenarios "01,02,03" --language en

# Run full benchmark with RAGAS evaluation
python -m tests.benchmark.run_benchmark --full --ragas

# Run with mock copilot (infrastructure testing)
python -m tests.benchmark.run_benchmark --mock --quick
```

## Scenarios (14 Enterprise Scenarios)

### Scenario 01: Codebase Onboarding
| Includes | Description | Workflow |
|----------|-------------|----------|
| Definition Search | Find function/variable definitions | `onboarding_workflow` |
| Call Graph | Navigate caller/callee relationships | `onboarding_workflow` |
| Data Flow | Trace variable assignments and usage | `onboarding_workflow` |
| Subsystem Explanation | Explain subsystem architecture | `onboarding_workflow` |
| Debugging | Find debug points and trace paths | `onboarding_workflow` |
| Business Logic | Understand query processing workflows | `onboarding_workflow` |

### Scenario 02: Security Audit
| Includes | Description | Workflow |
|----------|-------------|----------|
| Vulnerability Detection | Find SQL injection, buffer overflows | `security_workflow` |
| Entry Points | Identify attack surface and entry points | `security_workflow` |
| New Vulnerabilities | Detect emerging vulnerability patterns | `security_workflow` |

### Scenarios 03-16: Specialized Analysis

| ID | Name | Description | Workflow |
|----|------|-------------|----------|
| 03 | Documentation | Generate API documentation | `documentation_workflow` |
| 04 | Feature Development | Find extension points and hooks | `feature_dev_workflow` |
| 05 | Refactoring | Dead code + duplicate detection | `refactoring_workflow` |
| 06 | Performance | Complexity + concurrency + memory analysis | `performance_workflow` |
| 07 | Test Coverage | Generate test cases | `test_coverage_workflow` |
| 08 | Compliance | Coding style and standards checking | `compliance_workflow` |
| 09 | Code Review | Change impact analysis | `code_review_workflow` |
| 10 | Cross-Repository | API changes and dependencies | `cross_repo_workflow` |
| 11 | Architecture | Dependency and layering violations | `architecture_workflow` |
| 12 | Tech Debt | TODO/FIXME tracking | `tech_debt_workflow` |
| 13 | Mass Refactoring | Bulk code changes | `mass_refactoring_workflow` |
| 14 | Security Incident | Emergency investigation | `security_incident_workflow` |
| 15 | Debugging | Debug points and execution tracing | `debugging_workflow` |
| 16 | Entry Points | Attack surface and network handlers | `entry_points_workflow` |

## Directory Structure

```
tests/benchmark/
├── README.md                    # This file
├── run_benchmark.py             # Main benchmark runner
├── __init__.py
│
├── config/
│   └── benchmark_config.yaml    # Global configuration
│
├── ground_truth/                # Question sets for each scenario
│   ├── scenario_01_onboarding/
│   │   ├── questions_en.yaml    # English questions (merged from 6 sources)
│   │   └── questions_ru.yaml    # Russian questions
│   ├── scenario_02_security_audit/
│   │   └── questions_en.yaml
│   ... (16 scenarios aligned with intent_taxonomy.py)
│
├── evaluation/                  # Metrics computation
│   ├── __init__.py
│   ├── ir_metrics.py           # Precision, Recall, MRR, NDCG
│   └── accuracy_metrics.py     # Keyword coverage, semantic similarity
│
├── runners/                     # Benchmark execution
│   ├── __init__.py
│   ├── benchmark_runner.py     # Main runner logic
│   └── traceability_logger.py  # Detailed logging
│
├── fixtures/                    # Test fixtures
│   └── ...
│
└── results/                     # Benchmark output (generated)
    ├── benchmark_YYYYMMDD_HHMMSS.json
    └── traces/
```

## Ground Truth Format

Each scenario has a `questions_en.yaml` (and optionally `questions_ru.yaml`) file:

```yaml
scenario:
  id: "scenario_01_onboarding"
  name: "Codebase Onboarding"
  mapped_workflow: "onboarding_workflow"
  graph_methods: ["find_definition", "trace_callers", "trace_callees", "trace_data_flow"]

metadata:
  version: "1.0"
  language: "en"
  question_count: 35
  difficulty_distribution: {easy: 12, medium: 15, hard: 8}

questions:
  - id: "DEF_EN_001"
    question: "Where is the function heap_insert defined?"
    category: "function_definition"
    difficulty: "easy"
    postgresql_subsystem: "storage/heap"
    target_function: "heap_insert"
    ground_truth:
      expected_functions: ["heap_insert"]
      key_patterns: ["heap_insert", "heapam.c", "storage"]
      required_keywords: ["heap", "insert", "tuple", "relation"]
      min_expected_count: 1
    evaluation:
      metrics: [precision_at_k, recall_at_k, mrr, keyword_coverage]
      semantic_similarity_threshold: 0.7
```

## Evaluation Metrics

### Information Retrieval Metrics

| Metric | Description |
|--------|-------------|
| **Precision@K** | Fraction of top-K retrieved items that are relevant |
| **Recall@K** | Fraction of relevant items in top-K results |
| **MRR** | Mean Reciprocal Rank - position of first relevant result |
| **NDCG@K** | Normalized Discounted Cumulative Gain - ranking quality |
| **F1@K** | Harmonic mean of precision and recall |

### Accuracy Metrics

| Metric | Description |
|--------|-------------|
| **Keyword Coverage** | Fraction of required keywords present in answer |
| **Semantic Similarity** | Cosine similarity of answer embeddings to ground truth |

### Pass/Fail Thresholds

| Difficulty | P@10 | R@10 | MRR | Keyword Coverage |
|------------|------|------|-----|------------------|
| Easy | 0.3 | 0.5 | 0.4 | 0.5 |
| Medium | 0.2 | 0.3 | 0.3 | 0.4 |
| Hard | 0.1 | 0.2 | 0.2 | 0.3 |

## Command Line Options

```
usage: run_benchmark.py [-h] [-s SCENARIOS] [-l {en,ru}] [-d {easy,medium,hard}]
                        [-n MAX_QUESTIONS] [-q] [-m] [-t] [--no-trace] [-r]

options:
  -s, --scenarios      Comma-separated scenario IDs (e.g., "01,02,03")
  -l, --language       Filter by language (en, ru)
  -d, --difficulty     Filter by difficulty (easy, medium, hard)
  -n, --max-questions  Maximum questions per scenario
  -q, --quick          Quick mode (5 questions per scenario)
  -m, --mock           Use mock copilot for testing
  -t, --trace          Enable traceability logging (default: true)
  --no-trace           Disable traceability logging
  -r, --ragas          Run RAGAS evaluation with GigaChat
```

## Example Output

```
============================================================
RAG-CPGQL Comprehensive Benchmark
============================================================

Loading real copilot...
Available scenarios: 16
Total questions: 530+

Starting benchmark run...
[1/16] Running scenario_01_onboarding...
[2/16] Running scenario_02_security_audit...
...

============================================================
BENCHMARK RESULTS
============================================================

Run ID: 20251128_143022
Duration: 245.3s

Total Questions: 85
Passed: 62 (72.9%)
Failed: 23
Scenarios Passed (>=50%): 12/16

Scenario Results:
------------------------------------------------------------
  [PASS] Codebase Onboarding: 15/20 (75.0%) P@10=0.80
  [PASS] Security Audit: 9/10 (90.0%) P@10=0.88
  [PASS] Documentation: 6/10 (60.0%) P@10=0.65
  [PASS] Refactoring: 7/10 (70.0%) P@10=0.72
  [PASS] Performance: 6/10 (60.0%) P@10=0.55
  ...

Results saved to: tests/benchmark/results/
```

## Adding New Scenarios

1. Create directory: `ground_truth/scenario_XX_name/`
2. Add `questions_en.yaml` with the format above
3. Register in `config/benchmark_config.yaml`:

```yaml
scenarios:
  scenario_XX_name:
    name: "Your Scenario Name"
    mapped_workflow: "appropriate_workflow"
    enabled: true
```

## Success Criteria

The benchmark passes if:
- **Minimum scenario pass rate**: 50% per scenario
- **Minimum scenarios passed**: 8/16
- **Overall pass rate**: 50%

These thresholds are calibrated for CPG-based code retrieval, which often returns related but not exact matches.

## Integration with RAGAS

The benchmark supports RAGAS (Retrieval-Augmented Generation Assessment) evaluation:

```bash
python -m tests.benchmark.run_benchmark --ragas
```

This computes additional metrics:
- Answer Relevancy
- Faithfulness
- Context Precision
- Context Recall

Requires: `pip install ragas datasets`

## Traceability

Each benchmark run generates detailed trace files in `results/traces/`:

```
TRACE: [DEF_EN_001] Question: "Where is the function heap_insert defined?"
TRACE: [DEF_EN_001] Intent: onboarding (confidence: 0.95, method: keyword)
TRACE: [DEF_EN_001] Workflow: onboarding_workflow
TRACE: [DEF_EN_001] Retrieved: ['heap_insert', 'heap_update', 'heap_delete']
TRACE: [DEF_EN_001] P@10=0.90, R@10=1.00, MRR=1.00, KeywordCov=0.85
TRACE: [DEF_EN_001] Result: PASS
```

## Workflow Mapping

Intent classification routes questions to appropriate workflows:

| Intent | Keywords | Workflow |
|--------|----------|----------|
| `onboarding` | where, defined, trace, subsystem | `onboarding_workflow` |
| `security_audit` | vulnerability, injection, overflow | `security_workflow` |
| `performance` | complexity, hotspot, memory, lock | `performance_workflow` |
| `refactoring` | dead code, duplicate, smell | `refactoring_workflow` |
| `documentation` | document, explain, describe | `documentation_workflow` |

## Troubleshooting

### Rate Limiting
If GigaChat returns 429 errors, the system will retry with exponential backoff (2s → 4s → 8s → 16s → 60s max).

### Missing Scenarios
Ensure all scenario directories exist in `ground_truth/` and are registered in `benchmark_config.yaml`.

### Import Errors
Run from project root:
```bash
cd /path/to/pg_copilot/rag_cpgql
python -m tests.benchmark.run_benchmark
```

## License

Part of the RAG-CPGQL project. See main repository for license information.
