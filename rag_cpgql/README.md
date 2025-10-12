# RAG-CPGQL

RAG-CPGQL converts natural-language questions about PostgreSQL internals into executable Code Property Graph Query Language (CPGQL) programs. The system couples retrieval, semantic enrichment, and a grammar-free Qwen3-Coder generation stack with optional Joern execution.

## Project Snapshot

- **Pipeline:** Four agents (analyze -> retrieve -> enrich -> generate) orchestrated by a LangGraph state machine that adds retries, execution, and answer interpretation.
- **Knowledge Base:** 23,156 Q&A pairs and 1,072 curated CPGQL exemplars indexed in ChromaDB; PostgreSQL 17.6 CPG (~450k vertices) enriched with 12 semantic layers.
- **Model:** Qwen3-Coder-30B-A3B-Instruct (quantized `Q4_K_M`) hosted at `C:/Users/user/.lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`.
- **Latest Metrics:** 100% validity on a 30-question validation set, 97.5% validity on a 200-question statistical run, 86.7% success across a 30-question enrichment suite.
- **Status:** Generation pipeline production ready; Joern execution requires automated workspace loading; architectural-layer tags currently rely on filename fallbacks.

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
- **EnrichmentAgent:** Supplies 12-layer semantic hints (feature tags, security risks, metrics, and more).
- **GeneratorAgent:** Uses hints to emit valid CPGQL; LangGraph handles validation, retries, execution, and answer synthesis.

## Data and Resources

- `data/train_split_merged.jsonl` – 23,156 training pairs (pg_hackers + pg_books).
- `data/test_split_merged.jsonl` – 4,087 evaluation pairs.
- `data/cpgql_examples.json` – 1,072 canonical query templates.
- `C:/Users/user/joern/workspace/pg17_full.cpg` – enriched PostgreSQL 17.6 CPG (12 layers, quality score 100/100 after feature tagging).
- `cpgql_gbnf/cpgql_llama_cpp_v2.gbnf` – test GBNF-grammar for llama.cpp compatible runtimes. We don't use it because it breaks model generation.

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
  python -c "from src.workflow.langgraph_workflow_simple import run_workflow; \
             print(run_workflow('How does PostgreSQL handle MVCC?', verbose=True)['answer'])"
  ```

- **30-question validation:** `python experiments/test_30_questions.py`
- **200-question statistical run:** `python experiments/run_200_questions_test.py`
- **LangGraph smoke test:** `python experiments/test_langgraph_workflow.py --samples 10`
- **Grammar-only regression:** `python test_grammar_integration.py`

## Evaluation Summary

| Test | Scope | Key Results |
| --- | --- | --- |
| 30-question validation | Production pipeline | 100% validity, 4.1 s avg generation, enrichment coverage 0.44 |
| 200-question statistical | Generation-only | 97.5% validity, 3.35 s avg generation, 52% tag usage |
| 30-question enrichment suite | Feature and semantic tags | 86.7% end-to-end success across 8/8 enrichment categories |

## Current Limitations

- **Query specificity:** Further prompt tuning and enrichment-weighting are required.
- **Joern workspace loading:** Server mode currently fails to auto-load the enriched CPG; manual startup or batch mode works as an interim workaround.
- **Architectural-layer tags:** Windows path issues mark 93% of files as `unknown`; rely on filename patterns until re-enrichment completes.

## Roadmap Highlights

1. Automate Joern workspace loading and resume full end-to-end execution tests.
2. Enhance enrichment-aware prompting to raise average query quality to >=80/100 (see `IMPLEMENTATION_PLAN.md`).
3. Run the 200-question suite with execution enabled to collect semantic accuracy metrics.
4. Execute the 11-day analysis plan and draft the research paper (see `ANALYSIS_AND_PAPER_PLAN.md`).

## Documentation

- Implementation decisions, completed work, and outstanding engineering tasks: `IMPLEMENTATION_PLAN.md`
- Evaluation and publication strategy: `ANALYSIS_AND_PAPER_PLAN.md`
