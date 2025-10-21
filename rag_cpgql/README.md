# RAG-CPGQL

RAG-CPGQL converts natural-language questions about PostgreSQL internals into executable Code Property Graph Query Language (CPGQL) programs. The system couples retrieval, semantic enrichment, and a grammar-free Qwen3-Coder generation stack with optional Joern execution.

## Project Snapshot

- **Pipeline:** Four agents (analyze -> retrieve -> enrich -> generate) orchestrated by a LangGraph state machine that adds retries, execution, and answer interpretation.
- **Knowledge Base:** 23,156 Q&A pairs and 1,072 curated CPGQL exemplars indexed in ChromaDB; PostgreSQL 17.6 CPG (~450k vertices) enriched with 12 semantic layers. **NEW**: Three-dimensional code understanding with 169,303 DDG (Data Dependency Graph) patterns, 53,970 CFG (Control Flow Graph) patterns, and comprehensive documentation context.
- **Model:** Qwen3-Coder-30B-A3B-Instruct (quantized `Q4_K_M`) hosted at `C:/Users/user/.lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`.
- **Latest Metrics:** 100% validity on a 30-question validation set, 97.5% validity on a 200-question statistical run, 86.7% success across a 30-question enrichment suite. Enrichment coverage improved 41% (0.44 → 0.622) via 4-phase improvement plan. RAGAS evaluation on 50 samples confirms: Q&A retrieval excellence (0.524-0.839 similarity), 100% tag usage in generated queries.
- **Status:** Generation pipeline production ready with comprehensive three-dimensional code context (Documentation + CFG + DDG); Joern execution requires automated workspace loading; architectural-layer tags currently rely on filename fallbacks.

## System Architecture

```text
Question -> Analyzer -> Retriever -> Enrichment -> Generator
                                   |
                                   v
                          LangGraph Workflow
                            |- validate / refine (<=2 retries)
                            |- execute on Joern (optional)
                            |- interpret -> evaluate
```

- **AnalyzerAgent:** Identifies domain, intent, and key entities.
- **RetrieverAgent:** Pulls semantically similar Q&A entries and exemplar queries from ChromaDB.
- **EnrichmentAgent:** Supplies 12-layer semantic hints (feature tags, security risks, metrics, and more) with tag effectiveness tracking, complexity-aware patterns, and fallback strategies for low-coverage queries. **Phase 3 Enhancement**: Integrated three-dimensional code context retrieval:
  - **Documentation Context (WHAT)**: Code comments and function purpose from CPG documentation extraction
  - **Control Flow Context (HOW)**: 53,970 CFG patterns capturing execution flow, error handling, locks, transactions
  - **Data Flow Context (WHERE)**: 169,303 DDG patterns tracking parameter flow, variable dependencies, return sources, call arguments, and control dependencies
- **GeneratorAgent:** Uses hints and three-dimensional context to emit valid CPGQL; LangGraph handles validation, retries, execution, and answer synthesis.

## Data and Resources

- `data/train_split_merged.jsonl` – 23,156 training pairs (pg_hackers + pg_books).
- `data/test_split_merged.jsonl` – 4,087 evaluation pairs.
- `data/cpgql_examples.json` – 1,072 canonical query templates.
- `C:/Users/user/joern/workspace/pg17_full.cpg` – enriched PostgreSQL 17.6 CPG (12 layers, quality score 100/100 after feature tagging).
- `cpgql_gbnf/cpgql_llama_cpp_v2.gbnf` – test GBNF-grammar for llama.cpp compatible runtimes. We don't use it because it breaks model generation.
- **Phase 3 DDG Resources**:
  - `data/ddg_patterns.json` – 169,303 data flow patterns (141K parameter flows, 18.7K call arguments, 6.8K variable chains, 1.8K return sources, 738 control dependencies)
  - `data/cfg_patterns.json` – 53,970 control flow patterns (error handling, locks, transactions, complexity metrics)
  - `chromadb_storage/ddg_patterns` – ChromaDB collection with indexed DDG patterns for semantic search
  - `chromadb_storage/cfg_patterns` – ChromaDB collection with indexed CFG patterns

## Environment Setup

All commands, tests, and scripts must run from the `llama.cpp` Conda environment. Activate it before proceeding:

```powershell
conda activate llama.cpp
```

The required packages are preinstalled in this environment; do **not** install additional dependencies outside it.

1. Dependencies for this project are already installed in `llama.cpp`. If the environment is ever reset, reinstall them from within the activated environment:

   ```bash
   pip install -r requirements.txt
   ```

2. Build or refresh the vector store (generates embeddings for Q&A and examples):

   ```bash
   python src/retrieval/vector_store_real.py
   ```

3. Ensure the model path in `config.yaml` points to `C:/Users/user/.lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`.
4. (Optional) Start Joern with the enriched CPG if execution is required (see the next section for the full procedure).

### Starting Joern for Execution Tests

LangGraph now auto-launches Joern (imports + workspace open + `val cpg = Joern.cpg`) through `scripts/bootstrap_joern.ps1` each time execution is requested. Use the manual steps below only when you need to inspect or recover the server manually.

1. From `C:/Users/user/joern`, launch the server:

   ```powershell
   joern -J-Xmx16G --server --server-host localhost --server-port 8080
   ```

2. Confirm the listener is active:

   ```powershell
   Get-NetTCPConnection -LocalPort 8080 -State Listen
   ```

3. Bootstrap the REPL context once per server start (imports persist until restart). Run these commands from `C:/Users/user/joern` so that `pg17_client.py` is on the path, and prefer double-quoted PowerShell strings:

   ```powershell
   python pg17_client.py --query "import _root_.io.joern.joerncli.console.Joern"
   python pg17_client.py --query "import _root_.io.shiftleft.semanticcpg.language._"
   python pg17_client.py --query "Joern.open(\"pg17_full.cpg\")"
   python pg17_client.py --query "val cpg = Joern.cpg"
   ```

   or run the bundled smoke test (also from `C:/Users/user/joern`):

   ```powershell
   .\test_server_connection.ps1
   ```

4. Issue queries with the helper client (defaults to `localhost:8080`). After defining `val cpg = Joern.cpg`, either of the following will return results:

   ```powershell
   python pg17_client.py --sample-limit 5
   python pg17_client.py --query "cpg.method.name.size"
   ```

Refer to `C:/Users/user/joern/how_to_start_server_with_project.md` for the authoritative checklist.

## Running the Workflow

- **Single question (LangGraph workflow):**

  ```bash
  python -c "from src.workflow.langgraph_workflow import run_workflow; \
             print(run_workflow('How does PostgreSQL handle MVCC?', verbose=True)['answer'])"
  ```

- **Single question with RAGAS evaluation (debug mode):**

  ```bash
  python -c "from src.workflow.langgraph_workflow import run_workflow; \
             print(run_workflow('How does PostgreSQL handle MVCC?', verbose=True, enable_ragas=True)['answer'])"
  ```

- **30-question validation:** `python experiments/test_30_questions.py`
- **200-question statistical run:** `python experiments/run_200_questions_test.py`
- **200-question LangGraph execution + RAGAS:** `python experiments/run_langgraph_200_questions.py`
- **LangGraph smoke test:** `python experiments/test_langgraph_workflow.py --samples 10`
- **Grammar-only regression:** `python test_grammar_integration.py`

> **Notes**
> - Run LangGraph workflows inside the `llama.cpp` environment (e.g., `conda run -n llama.cpp python experiments/run_langgraph_200_questions.py --limit 200`). The runner aborts immediately if Joern cannot be bootstrapped and reports which fallback query (if any) succeeded.
> - Executor fallbacks automatically retry relaxed CPGQL variants (tag loosening, regex name filters, method-based lookups, keyword-driven fallbacks) whenever a query is valid but empty, and they log the winning query.
> - RAGAS metrics call the official OpenAI backend when `OPENAI_API_KEY` is set. Without the key, the workflow automatically falls back to heuristic scoring and logs the fallback.
> - **RAGAS evaluation is disabled by default** to avoid 50-70s overhead per query. Enable it with `enable_ragas=True` for single-question debugging only, not for batch processing.

## Evaluation Summary

| Test | Scope | Key Results |
| --- | --- | --- |
| 200-question statistical | Generation-only | 97.5% validity, 3.35 s avg generation, 52% tag usage |

## Documentation

- Implementation decisions, completed work, and outstanding engineering tasks: `IMPLEMENTATION_PLAN.md`
- Enrichment improvement roadmap and results: `ENRICHMENT_IMPROVEMENT_PLAN.md`
- Phase 4 fallback strategies documentation: `PHASE_4_COMPLETION.md`
- **Phase 3 DDG Integration** (NEW):
  - Three-dimensional context system overview: `PHASE3_COMPLETION.md`
  - DDG API research and findings: `PHASE3_DDG_API_FINDINGS.md`
  - Technical implementation summary: `PHASE3_SUMMARY.md`
  - Progress tracking: `PHASE3_DDG_STATUS.md`
- RAGAS evaluation findings and analysis: `RAGAS_EVALUATION_FINDINGS.md`
- RAGAS improvement plan and metrics targets: `RAGAS_IMPROVEMENT_PLAN.md`
- Evaluation and publication strategy: `ANALYSIS_AND_PAPER_PLAN.md`
