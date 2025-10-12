# RAG-CPGQL Experiments

This directory contains test scripts for evaluating the RAG-CPGQL system.

> **Environment requirement:** Activate the `llama.cpp` Conda environment (`conda activate llama.cpp`) before running any commands in this guide. All dependencies are preinstalled there; do not install new packages outside this environment.
>
> **Joern requirement:** When a test exercises the execution path (LangGraph workflow, Joern client scripts), start the server from `C:\Users\user\joern` with `joern -J-Xmx16G --server --server-host localhost --server-port 8080`, then bootstrap the session once per server start:
> ```powershell
> python pg17_client.py --query "import _root_.io.joern.joerncli.console.Joern"
> python pg17_client.py --query "import _root_.io.shiftleft.semanticcpg.language._"
> python pg17_client.py --query "Joern.open(\"pg17_full.cpg\")"
> python pg17_client.py --query "val cpg = Joern.cpg"
> ```
> Leaving `val cpg = Joern.cpg` defined ensures all downstream queries (including automated tests) can call into the workspace without redefining the alias.

## Available Tests

### 1. 30-Question Test (`test_30_questions.py`)

Quick validation test with 30 diverse questions.

**Usage:**
```bash
cd C:/Users/user/pg_copilot/rag_cpgql
python experiments/test_30_questions.py
```

**Expected Duration:** ~2-3 minutes

**Results:** `results/test_30_questions_results.json`

---

### 2. 200-Question Test (`test_200_questions.py`)

Comprehensive test for statistical significance with 200 questions.

**Features:**
- Automatic checkpointing every 50 questions
- Resume capability on interruption
- Statistical analysis (95% confidence intervals)
- Detailed domain-wise breakdown

**Usage:**
```bash
# Using runner (recommended)
cd C:/Users/user/pg_copilot/rag_cpgql
python experiments/run_200_questions_test.py

# Direct execution
python experiments/test_200_questions.py
```

**Expected Duration:** ~15-20 minutes

**Results:**
- Final: `results/test_200_questions_results.json`
- Checkpoint: `results/test_200_checkpoint.json` (auto-deleted on completion)
- Log: `results/test_200_run.log`

**Resume from Checkpoint:**
If the test is interrupted (Ctrl+C or error), simply run it again:
```bash
python experiments/test_200_questions.py
# You'll be prompted: "Resume from checkpoint? (y/n)"
```

---

### 3. RAGAS Evaluation (`test_with_ragas.py`)

Evaluate RAG pipeline quality using RAGAS metrics.

**Usage:**
```bash
cd C:/Users/user/pg_copilot/rag_cpgql
python experiments/test_with_ragas.py
```

**Requires:** Existing test results (30 or 200 questions)

**Results:** `results/ragas_evaluation.json`

---

### 4. Joern Client Tests

**Connection Test (`test_joern_client.py`):**
```bash
cd C:/Users/user/pg_copilot
python experiments/test_joern_client.py
```
Tests Joern server connection and query execution.

**CPG Loaded Test (`test_cpg_loaded.py`):**
```bash
python experiments/test_cpg_loaded.py
```
Tests CPGQL queries on loaded PostgreSQL CPG.

---

## Results Structure

### test_200_questions_results.json

```json
{
  "test_name": "Core Agents Test - 200 Questions",
  "timestamp": "2025-10-11T01:23:45",
  "total_questions": 200,
  "valid_queries": 195,
  "validity_rate": 97.5,
  "avg_generation_time": 4.12,
  "avg_enrichment_coverage": 0.45,
  "total_test_time": 1234.56,
  "query_patterns": {
    "has_tag_filter": 92,
    "has_name_filter": 165,
    "uses_method": 145,
    ...
  },
  "statistical_analysis": {
    "sample_size": 200,
    "validity_rate": 0.975,
    "standard_error": 0.011,
    "confidence_interval_95": [0.953, 0.997]
  },
  "domains": {
    "mvcc": {"total": 25, "valid": 24},
    "wal": {"total": 18, "valid": 18},
    ...
  },
  "results": [
    {
      "question": "How does PostgreSQL implement MVCC?",
      "analysis": {
        "domain": "mvcc",
        "keywords": ["mvcc", "transaction", "visibility"],
        ...
      },
      "query": "cpg.method.name(\".*HeapTuple.*\").tag.name(\"transaction\").l",
      "valid": true,
      "times": {
        "analysis": 0.01,
        "retrieval": 0.05,
        "enrichment": 0.02,
        "generation": 4.12
      }
    },
    ...
  ]
}
```

---

## Key Metrics

### Validity Rate
Percentage of syntactically valid CPGQL queries generated.
- **Target:** >95%
- **Current (30 questions):** 100%

### Enrichment Coverage
How many enrichment layers are utilized in queries.
- **Range:** 0.0 to 1.0
- **Current avg:** 0.44

### Generation Time
Time to generate a query (LLM inference).
- **Current avg:** ~4.1 seconds

### Query Patterns
- **Uses enrichment tags:** ~47%
- **Uses name filters:** ~80%
- **Uses cpg.method:** ~65%

---

## Statistical Significance (200-Question Test)

With 200 questions:
- **Confidence Level:** 95%
- **Margin of Error:** ±1.96 * SE

Example interpretation:
```
Validity rate: 97.5% ± 2.2%
95% CI: [95.3%, 99.7%]
```

This means we can be 95% confident that the true validity rate of the system lies between 95.3% and 99.7%.

---

## Troubleshooting

### Test hangs during initialization
**Cause:** LLM model not loaded or ChromaDB not initialized

**Solution:**
```bash
# Check ChromaDB
ls C:/Users/user/pg_copilot/rag_cpgql/chroma_db

# Reinitialize if needed
python src/retrieval/vector_store_real.py
```

### Out of memory errors
**Cause:** LLM model too large for available RAM

**Solution:** Close other applications or reduce `n_ctx` in test script

### Checkpoint corruption
**Cause:** Test interrupted during checkpoint save

**Solution:** Delete checkpoint and restart:
```bash
rm results/test_200_checkpoint.json
python experiments/test_200_questions.py
```

---

## Next Steps

After 200-question test completes:

1. **Run RAGAS evaluation:**
   ```bash
   python experiments/test_with_ragas.py
   ```

2. **Analyze results:** Review JSON files in `results/` directory

3. **Test on real CPG:**
   - Start Joern server with PostgreSQL CPG loaded
   - Run actual query execution tests

4. **Production deployment:** Integrate validated components into full LangGraph workflow

---

## Development Notes

- All tests use **Qwen3-Coder-30B** base model (no grammar constraints)
- **ChromaDB** indexed with 24,228 items (23,156 Q&A + 1,072 CPGQL examples)
- **4-Agent Pipeline:** Analyzer → Retriever → Enrichment → Generator
- **12 Enrichment Layers:** transaction, lock, memory, io, network, security, etc.

---

## File Overview

```
experiments/
├── README.md                      # This file
├── test_30_questions.py          # Quick 30-question validation
├── test_200_questions.py         # Full 200-question test
├── run_200_questions_test.py     # Runner with checks
├── test_with_ragas.py            # RAGAS evaluation
├── test_joern_client.py          # Joern connection test
└── test_cpg_loaded.py            # CPG query execution test
```

```
results/
├── test_30_questions_results.json
├── test_200_questions_results.json
├── test_200_checkpoint.json       # Auto-deleted on success
├── test_200_run.log
└── ragas_evaluation.json
```
