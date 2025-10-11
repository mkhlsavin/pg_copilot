# PostgreSQL Copilot - Code Property Graph Analysis Suite

**Research Platform for PostgreSQL Source Code Analysis using Code Property Graphs (Joern) and RAG**

Comprehensive toolkit for analyzing PostgreSQL internals through Code Property Graphs (CPG), enrichment automation, RAG-based query generation, and dataset creation for AI-assisted development.

---

## 🏆 Key Achievement: RAG-CPGQL System

**✅ Production Ready - 100% Query Validity**

The **rag_cpgql** system successfully achieved 100% valid CPGQL query generation on a 30-question validation set using a 4-agent RAG architecture with semantic enrichment.

### Highlights
- **100% Query Validity** on 30-question validation set
- **4-Agent Architecture**: Analyzer → Retriever → Enrichment → Generator
- **24k Indexed Items**: 23,156 Q&A pairs + 1,072 CPGQL examples
- **12-Layer Semantic Enrichment**: transaction, lock, memory, io, network, security, optimization, parallel, replication, vacuum, partition, extension
- **RAGAS Metrics**: 79.1% Q&A similarity, 44.2% enrichment coverage
- **Real Joern Integration**: Connected to PostgreSQL 17.6 CPG (~450k vertices)
- **200-Question Test Suite**: Statistical validation with 95% confidence intervals

[→ See rag_cpgql README for details](rag_cpgql/README.md)

---

## 📦 Project Structure

```
pg_copilot/
├── rag_cpgql/              ✅ PRODUCTION: RAG-based CPGQL query generation (100% validity)
├── cpg_enrichment/         ✅ COMPLETE: CPG metadata enrichment suite (96/100 quality score)
├── feature_mapping/        ✅ COMPLETE: PostgreSQL feature → CPG node mapping toolkit
├── cpgql_gbnf/            ✅ COMPLETE: CPGQL grammar (GBNF format) for validation
├── hackers/               ✅ COMPLETE: QA dataset from pgsql-hackers (2022-2025)
├── pg_books/              ✅ COMPLETE: 1,328 QA pairs from technical books
└── xgrammar_tests/        🚧 PROTOTYPE: Grammar-guided CPGQL generation experiments
```

---

## 🚀 Quick Start

### Prerequisites
- **Joern 2.x** installed locally (Code Property Graph platform)
- **PostgreSQL 17.6** source code
- **Python 3.10+** with conda/venv
- **GPU recommended** for LLM inference (RTX 3090 or similar)

### 1. Initialize PostgreSQL CPG

```bash
# Generate CPG from PostgreSQL source
cd C:/Users/user/joern
./joern-parse C:/Users/user/postgres-REL_17_6 -o workspace/pg17_full.cpg
```

### 2. Enrich CPG with Metadata

```bash
cd C:/Users/user/pg_copilot/cpg_enrichment

# Run full enrichment suite (~90 minutes)
./enrich_cpg.sh full

# Quality check
./joern --script test_cpg_quality.sc
# Target: 96/100 quality score
```

### 3. Run RAG-CPGQL System

```bash
cd C:/Users/user/pg_copilot/rag_cpgql

# Install dependencies
pip install -r requirements.txt

# Initialize vector store (23k Q&A + 1k CPGQL examples)
python src/retrieval/vector_store_real.py

# Run 30-question validation test
python experiments/test_30_questions.py
# Expected: 100% validity rate

# Run 200-question statistical test (~15-20 minutes)
python experiments/run_200_questions_test.py

# Evaluate with RAGAS metrics
python experiments/test_with_ragas.py
```

### 4. Test Joern Client Integration

```bash
# Start Joern server
cd C:/Users/user/joern
./joern.bat --server --server-host localhost --server-port 8080

# In new terminal, test connection
cd C:/Users/user/pg_copilot
python experiments/test_joern_client.py
```

---

## 📂 Subproject Documentation

### 1. RAG-CPGQL: Query Generation System ✅ **PRODUCTION**

**Status:** 100% query validity achieved

Advanced Retrieval-Augmented Generation system that translates natural language questions about PostgreSQL internals into valid CPGQL queries.

**Architecture:**
```
Question → Analyzer → Retriever → Enrichment → Generator → CPGQL Query
               ↓                                    ↓
          Domain Analysis              12-Layer Semantic Tags
               ↓                                    ↓
         ChromaDB (24k items)           Query Validation
```

**Performance:**
- **Validity Rate:** 100% (30/30 questions)
- **Generation Time:** 4.1s average
- **Enrichment Coverage:** 0.44
- **Retrieval Quality:** 0.791 Q&A similarity

**Dataset:**
- 23,156 Q&A pairs from pgsql-hackers + technical books
- 1,072 curated CPGQL examples
- 200-question test suite with statistical analysis

**Quick Test:**
```bash
cd rag_cpgql
python experiments/test_30_questions.py
```

[→ Full Documentation](rag_cpgql/README.md)

---

### 2. CPG Enrichment Suite ✅ **COMPLETE**

**Status:** 96/100 quality score, 82% architectural coverage

Scala scripts and automation wrappers that enrich PostgreSQL CPG with domain-specific metadata for downstream RAG and analytics.

**Enrichment Layers:**
- **AST Comments:** 2.4M comment associations
- **Subsystem Tags:** 712 files → 83 subsystems
- **API Catalog:** 14,380 APIs classified
- **Security Patterns:** 4,508 risky call sites tagged
- **Code Metrics:** 52,303 methods scored (complexity, coupling, smells)
- **Test Coverage:** 51,908 methods linked to tests
- **Performance Hotspots:** 10,798 routines flagged
- **Architectural Layers:** 82% files classified (fixed Oct 2025)
- **Semantic Classification:** 100% methods labeled (30+ taxonomies)

**Execution Profiles:**
- **Minimal:** ~10 min (baseline comments + subsystems)
- **Standard:** ~50-60 min (production default, most metadata)
- **Full:** ~90 min (adds coverage, performance, semantic layers)

**Quick Run:**
```bash
cd cpg_enrichment
./enrich_cpg.sh standard  # or: minimal, full
```

**Quality Gate:**
```bash
./joern --script test_cpg_quality.sc
# Target: 96/100
```

[→ Full Documentation](cpg_enrichment/README.md)

---

### 3. Feature Mapping Toolkit ✅ **COMPLETE**

**Status:** 394 PostgreSQL features mapped to CPG nodes

Maps official PostgreSQL 17 feature matrix to concrete code locations in the CPG for traceability, documentation, and impact analysis.

**Workflow:**
```
Feature Matrix → Heuristic Expansion → Joern Query → Score & Filter → Tag CPG
```

**Features:**
- Automatic feature name → search heuristic expansion
- Multi-node-type candidate search (files, methods, types, calls)
- Heuristic scoring (token matching + directory hints)
- Batch tag application to CPG
- Resume capability for interrupted runs
- Per-feature summary reports for audit trails

**Usage Scenarios:**
- Developer onboarding (feature X → code)
- Security audits (filter security features)
- Impact analysis (enumerate tagged nodes before changes)
- Documentation generation (auto-link features to code)

**Quick Run:**
```bash
cd feature_mapping

# Review-first (no mutations, summaries only)
python -m feature_mapping.cli --dry-run --skip-tagging --summary-dir summaries

# Persist feature tags to CPG
python -m feature_mapping.cli --output mappings.json --summary-dir summaries

# Verify coverage
python verify_tag_coverage.py --output coverage.json
```

[→ Full Documentation](feature_mapping/README.md)

---

### 4. CPGQL Grammar (GBNF) ✅ **COMPLETE**

**Status:** Formal grammar for CPGQL in GBNF format

Defines Code Property Graph Query Language syntax in **GBNF** (Extended BNF) for grammar-guided tooling, validation, and constrained LLM decoding.

**Grammar Components:**
- Root object (`cpg`)
- Node-type steps (`.method`, `.call`, `.file`)
- Filter/map/repeat steps (Scala-style lambdas)
- Property directives (`.name`, `.codeExact`)
- Execution directives (`.l`, `.head`, `.toList`)
- Augmentation directives (`newTagNode`, `store`, `run.commit`)

**Use Cases:**
- Query generation (enforce syntactic correctness)
- Static validation (parse before Joern execution)
- RAG integration (constrain LLM decoding)
- llama.cpp integration (`LlamaGrammar`)

**Example Usage:**
```python
from llama_cpp import Llama, LlamaGrammar
from pathlib import Path

gbnf = Path("cpgql_clean.gbnf").read_text(encoding="utf-8")
llm = Llama(model_path="path/to/model.gguf", n_ctx=32768)
grammar = LlamaGrammar.from_string(gbnf)
response = llm.create_completion(prompt="...", grammar=grammar, max_tokens=512)
```

[→ Full Documentation](cpgql_gbnf/README.md)

---

### 5. PostgreSQL Hackers QA Dataset ✅ **COMPLETE**

**Status:** Production-ready scraper, tested on 2,665 emails

Scrapes and parses pgsql-hackers mailing list (2022-2025) to generate high-quality QA pairs using local LLM inference.

**Pipeline:**
```
Web Scraping → Thread Parsing → Topic Clustering → Source Mapping → QA Generation
     ↓              ↓                  ↓                  ↓               ↓
raw_threads → processed_threads → clustered_topics → source_mapping → qa_pairs
```

**Performance:**
- **Scraping Speed:** 10.8 emails/second (10x improvement)
- **Concurrent Requests:** 5 parallel connections
- **Checkpoint Resume:** Automatic recovery from interruptions
- **Expected Output:** ~4,000-7,000 QA pairs (2022-2025)

**Testing Results:**
- ✅ Sample: 54 emails → 10 threads → 1 cluster → 5 QA pairs
- ✅ Real data: 2,665 emails from Jan-Feb 2022
- ✅ QA generation validated with Qwen3-32B

**Quick Run:**
```bash
cd hackers

# Full pipeline (2022-2025, ~7-8 hours scraping)
python main.py --all

# Or step-by-step
python main.py --scrape      # ~8 hours for 2022-2025
python main.py --parse       # ~10 minutes
python main.py --cluster     # ~1 hour
python main.py --map-source  # ~30 minutes
python main.py --generate-qa # ~4-8 hours
```

[→ Full Documentation](hackers/README.md)

---

### 6. PostgreSQL Books QA Dataset ✅ **COMPLETE**

**Status:** 1,328 QA pairs from technical books

Generates QA pairs from PostgreSQL technical books and online documentation (notably "The Internals of PostgreSQL").

**Dataset:**
- **1,328 Q&A pairs** from PostgreSQL technical content
- **664 content chunks** semantically split
- **3 difficulty levels:** beginner, intermediate, advanced
- **Topics:** MVCC, transactions, indexing, storage, executor, partitioning, etc.

**Pipeline:**
```
PDF/Web → Extraction → Chunking → Source Mapping → QA Generation → JSONL
```

**Generation Strategy (Dynamic):**
- Long chunks (≥400 tokens): 2 QA pairs
- Medium chunks (150-400 tokens): 1 QA pair
- Short chunks (50-150 tokens): 1 QA pair
- Very short (<50 tokens): Skipped

**Quick Run:**
```bash
cd pg_books

# Recommended: Direct chunk → Q&A (bypasses clustering)
python web_book_scraper.py         # Scrape content (~5 min)
python content_chunker.py          # Chunk content (~1 min)
python generate_qa_from_chunks.py  # Generate QA (~8-12 hours)

# Resume if interrupted
python generate_qa_from_chunks.py --resume
```

**Output Format:**
```json
{
  "question": "How does PostgreSQL validate transaction IDs?",
  "answer": "PostgreSQL uses TransactionIdIsValid() macro...",
  "difficulty": "intermediate",
  "topics": ["transaction_management", "mvcc"],
  "source_files": ["src/backend/access/transam/xact.c"]
}
```

[→ Full Documentation](pg_books/README.md)

---

### 7. XGrammar Tests 🚧 **PROTOTYPE**

**Status:** Experimental grammar-guided CPGQL generation

Prototype playground for generating CPGQL queries using formal grammar (`cpgql_clean.gbnf`) and the [XGrammar](https://xgrammar.mlc.ai/) library.

**Goal:** Grammar-constrained LLM decoding for guaranteed-valid CPGQL generation.

**Current Status:**
- Grammar compilation working
- Tokenizer integration in progress
- Joern end-to-end tests available

**Quick Test:**
```bash
cd xgrammar_tests
conda activate llama.cpp

# Generate queries (requires tokenizer metadata)
xgrammar-generate --count 3 \
  --tokenizer-gguf path/to/model.gguf

# Joern end-to-end smoke test
python tools/run_joern_e2e.py \
  --tokenizer-gguf path/to/model.gguf \
  --count 5 --connect --joern-load
```

[→ Full Documentation](xgrammar_tests/README.md)

---

## 🎯 System Requirements

### Hardware
- **CPU:** Multi-core recommended (8+ cores for parallel enrichment)
- **RAM:** 32GB+ recommended (Joern CPG operations, LLM inference)
- **GPU:** NVIDIA RTX 3090 or similar (24GB VRAM for 32B models)
- **Storage:** ~50GB for CPG, datasets, and models

### Software
- **Joern 2.x** - Code Property Graph platform
- **PostgreSQL 17.6** source code
- **Python 3.10+** with conda/venv
- **CUDA 12.4** (for GPU acceleration)
- **Java 11+** (for Joern, recommend `-Xmx24G`)

### Python Dependencies
```bash
# Core
pip install chromadb sentence-transformers ragas datasets
pip install llama-cpp-python[server]  # GPU: CMAKE_ARGS=-DLLAMA_CUBLAS=on
pip install cpgqls-client  # Joern client library

# Optional
pip install xgrammar  # For grammar-guided generation experiments
```

---

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 1: PostgreSQL Source Code (17.6)                              │
│ - C source files (~450k vertices after CPG generation)               │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 2: Code Property Graph (Joern)                                │
│ - CPG: pg17_full.cpg (~450k vertices)                                │
│ - Enrichment: 9 scripts, 96/100 quality score                        │
│ - Feature Tags: 394 PostgreSQL features mapped                       │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 3: Knowledge Base                                              │
│ - Q&A Pairs: 23,156 (hackers + books)                                │
│ - CPGQL Examples: 1,072 curated queries                              │
│ - ChromaDB: 24,228 indexed items                                     │
│ - Embeddings: sentence-transformers                                   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 4: RAG-CPGQL System (4-Agent Pipeline)                         │
│ - Analyzer: Domain + keyword extraction                              │
│ - Retriever: RAG retrieval (top-k Q&A + CPGQL)                       │
│ - Enrichment: 12-layer semantic tagging                              │
│ - Generator: CPGQL generation (100% validity)                        │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 5: Execution & Evaluation                                      │
│ - Joern Server: WebSocket client (cpgqls-client)                     │
│ - RAGAS Metrics: context precision/recall, answer relevancy          │
│ - Statistical Tests: 200 questions, 95% confidence intervals         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📈 Performance Benchmarks

### CPG Enrichment
- **Minimal Profile:** ~10 minutes
- **Standard Profile:** ~50-60 minutes (production default)
- **Full Profile:** ~90 minutes
- **Quality Score:** 96/100
- **Coverage:** 82% architectural classification (1,748/2,111 files)

### RAG-CPGQL System
- **Query Validity:** 100% (30/30 questions)
- **Generation Time:** 4.1s average per query
- **Retrieval Quality:** 0.791 Q&A similarity
- **Enrichment Coverage:** 0.44 (12 semantic layers)
- **Throughput:** 0.24 queries/second

### Dataset Generation
- **Hackers Scraping:** 10.8 emails/second (2,665 emails in ~4 min)
- **Books QA Generation:** ~30s per Q&A pair (1,328 pairs total)
- **Expected Full Dataset:** 4,000-7,000 Q&A pairs (2022-2025)

### Joern Client
- **Connection:** WebSocket to localhost:8080
- **Query Execution:** <1s for simple queries on 450k vertex CPG
- **CPG Load Time:** ~10-30s for pg17_full.cpg

---

## 🧪 Testing & Validation

### RAG-CPGQL Tests
```bash
cd rag_cpgql/experiments

# 30-question validation (~2-3 minutes)
python test_30_questions.py
# Expected: 100% validity

# 200-question statistical test (~15-20 minutes)
python run_200_questions_test.py
# Expected: >95% validity (95% CI)

# RAGAS evaluation
python test_with_ragas.py
# Metrics: context precision/recall, answer relevancy, faithfulness
```

### CPG Quality Tests
```bash
cd cpg_enrichment

# Quality score (target: 96/100)
./joern --script test_cpg_quality.sc

# Architectural layers coverage
./joern --script run_layers_final.sc
# Expected: 82% classification
```

### Joern Integration Tests
```bash
# Start Joern server
cd C:/Users/user/joern
./joern.bat --server --server-host localhost --server-port 8080

# Test connection and queries
cd C:/Users/user/pg_copilot
python experiments/test_joern_client.py
python experiments/test_cpg_loaded.py
```

---

## 🔧 Troubleshooting

### ChromaDB Issues
```bash
# Reinitialize if corrupted
rm -rf rag_cpgql/chroma_db/
cd rag_cpgql
python src/retrieval/vector_store_real.py
```

### LLM Model Loading
```python
# Reduce context if OOM
# In config: N_CTX = 4096 (instead of 8192)
# Or reduce GPU layers: N_GPU_LAYERS = 35 (instead of -1)
```

### Joern Server Issues
```bash
# Check server status
netstat -ano | findstr :8080

# Increase heap if needed
export JOERN_MAX_HEAP=24G

# Restart server
cd C:/Users/user/joern
./joern.bat --server --server-host localhost --server-port 8080
```

### GPU Not Detected
```bash
# Verify CUDA
nvidia-smi
nvcc --version

# Reinstall llama-cpp-python with CUDA
pip uninstall llama-cpp-python -y
set CMAKE_ARGS=-DLLAMA_CUBLAS=on
pip install llama-cpp-python --no-cache-dir
```

---

## 🚀 Next Steps

### Immediate (Week 1-2)
1. ✅ ~~Run 200-question statistical validation~~
2. ✅ ~~RAGAS evaluation on test results~~
3. ✅ ~~Joern client integration and testing~~
4. ⬜ Fine-tune enrichment hint generation
5. ⬜ Optimize retrieval quality (improve CPGQL example embeddings)

### Short-term (Month 1-2)
1. ⬜ Full LangGraph integration (9-agent workflow)
2. ⬜ Production deployment with FastAPI
3. ⬜ Real-time query execution on PostgreSQL CPG
4. ⬜ Expand test suite to 500 questions
5. ⬜ Implement query caching and optimization

### Long-term (Quarter 1-2)
1. ⬜ Multi-model ensemble (combine multiple LLMs)
2. ⬜ Interactive query refinement UI
3. ⬜ Integration with PostgreSQL documentation portal
4. ⬜ Automated CPG re-enrichment on PG version updates
5. ⬜ Community dataset contributions and validation

---

## 📚 Documentation Map

```
pg_copilot/
├── README.MD                           # This file (project overview)
├── rag_cpgql/
│   ├── README.md                       # RAG-CPGQL system documentation
│   ├── experiments/README.md           # Experiment scripts guide
│   └── LANGGRAPH_ARCHITECTURE.md       # Future 9-agent architecture
├── cpg_enrichment/
│   ├── README.MD                       # Enrichment suite overview
│   ├── ARCHITECTURAL_LAYERS_SUCCESS.md # Oct 2025 layer fix postmortem
│   ├── SESSION_SUMMARY_2025-10-07.md   # Enrichment session log
│   └── QUICK_START.md                  # Platform-specific commands
├── feature_mapping/
│   └── README.md                       # Feature mapping toolkit
├── cpgql_gbnf/
│   ├── README.md                       # CPGQL grammar documentation
│   └── docs/GBNF grammar for the CPGQL.md  # Grammar manuscript
├── hackers/
│   ├── README.md                       # Hackers dataset generator
│   ├── TESTING.md                      # Test results and bug fixes
│   ├── STATUS.md                       # Project status checklist
│   └── QUICKSTART.md                   # Quick start examples
├── pg_books/
│   └── README.md                       # Books dataset generator
└── xgrammar_tests/
    └── README.md                       # XGrammar experiments
```

---

## 🔗 External Resources

- **Joern Documentation:** https://docs.joern.io/
- **PostgreSQL Source:** https://github.com/postgres/postgres
- **XGrammar:** https://xgrammar.mlc.ai/
- **ChromaDB:** https://docs.trychroma.com/
- **RAGAS:** https://docs.ragas.io/
- **llama.cpp:** https://github.com/ggerganov/llama.cpp
- **PostgreSQL Mailing Lists:** https://www.postgresql.org/list/

---

## 📄 License

Research project - see individual component licenses.

---

## 📞 Contact

Research project for PostgreSQL copilot evaluation using Code Property Graphs and RAG.

**Core Components:**
- Code Property Graph generation (Joern)
- CPG enrichment automation (Scala scripts)
- RAG-based query generation (100% validity)
- Dataset creation (hackers + books, 23k+ Q&A pairs)

**Last Updated:** 2025-10-11
