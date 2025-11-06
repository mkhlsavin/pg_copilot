# RAG-CPGQL: Enrichment-Aware Code Query Generation

**Research Objective:** Demonstrate that semantic enrichments, retrieval-augmented generation, and LangGraph orchestration significantly improve natural language to CPGQL query translation for large-scale code analysis.

**Target Publication:** Tier-1 Software Engineering Venue (ICSE/FSE/ASE)

## Overview

RAG-CPGQL converts natural-language questions about PostgreSQL internals into executable Code Property Graph Query Language (CPGQL) programs. The system combines:

- **Multi-layer semantic enrichments** extracted from PostgreSQL 17 CPG
- **Three-dimensional code context** (Documentation + Control Flow + Data Flow)
- **RAG-based retrieval** from 23K Q&A pairs and 1K exemplar queries
- **LangGraph orchestration** with validation, retry, and execution

## Core Research Contributions

1. **Semantic Enrichment Framework**: 12-layer metadata extraction (tags, metrics, patterns) improving query generation accuracy
2. **Three-Dimensional Context**: Novel integration of documentation (WHAT), CFG (HOW), and DDG (WHERE) patterns
3. **Domain-Concept Tagging**: Automated mapping of low-level code patterns to high-level PostgreSQL concepts (51 concepts, 72.6% coverage)
4. **Retrieval-Orchestrated Generation**: LangGraph workflow with retry logic and execution feedback

## System Architecture

```
Natural Language Question
          ↓
    Analyzer Agent (domain/intent/entities)
          ↓
    Retriever Agent (Q&A + exemplars from ChromaDB)
          ↓
    Enrichment Agent (12 semantic layers + 3D context)
          ↓
    Generator Agent (Qwen3-Coder-30B)
          ↓
    LangGraph Workflow (validate → retry → execute → interpret)
          ↓
    CPGQL Query + Execution Result + Answer
```

## Data Resources

### Training & Evaluation Datasets
- `data/train_split_merged.jsonl` – 23,156 Q&A pairs (pg_hackers + pg_books)
- `data/test_split_merged.jsonl` – 4,087 evaluation pairs
- `data/cpgql_examples.json` – 1,072 canonical query templates

### Code Property Graph
- **Location**: `C:/Users/user/joern/workspace/pg17_full.cpg`
- **Source**: PostgreSQL 17.6 codebase (~450K vertices)
- **Enrichments**: 12 semantic layers (quality score 100/100)
  - Architectural layers, ACID patterns, access methods
  - Complexity metrics, concurrency patterns, error handling
  - Performance indicators, security attributes, transaction markers
  - Memory management, storage engine patterns, system call annotations

### Three-Dimensional Context (Phase 3 Integration)
- **Documentation Context** (WHAT functions do):
  - 638 documented methods with comments
  - Extracted via CPG comment traversal

- **Control Flow Patterns** (HOW functions execute):
  - `data/cfg_patterns.json` – 53,970 patterns
  - Error handling, locks, transactions, complexity metrics
  - Indexed in `chromadb_storage/cfg_patterns`

- **Data Flow Patterns** (WHERE data flows):
  - `data/ddg_patterns.json` – 169,303 patterns
    - 141K parameter flows
    - 18.7K call arguments
    - 6.8K variable chains
    - 1.8K return sources
    - 738 control dependencies
  - `data/ddg_patterns_enriched.json` – Domain-concept enriched version (117MB)
    - 51 PostgreSQL concepts (mvcc, wal, brin-index, etc.)
    - 72.6% patterns tagged, avg 2.49 concepts/pattern
  - Indexed in `chromadb_storage/ddg_patterns_enriched`

## Quick Start

### Environment Setup

```powershell
# Activate Conda environment
conda activate llama.cpp

# Install dependencies (if needed)
pip install -r requirements.txt

# Build vector stores
python src/retrieval/vector_store_real.py
python src/retrieval/ddg_vector_store.py  # Index enriched DDG patterns
```

### Model Configuration

- **Model**: Qwen3-Coder-30B-A3B-Instruct (Q4_K_M quantized)
- **Path**: `C:/Users/user/.lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/`
- **Configuration**: Update `config.yaml` with model path

### Running Experiments

```powershell
# Interactive demo
python demo_simple.py

# Benchmark evaluation (200 questions)
python experiments/run_langgraph_200_questions.py --limit 200

# Statistical validation
python experiments/analyze_results.py results/phase3_200q_final.json
```

### Joern Execution (Optional)

For query execution on actual CPG:

```powershell
# Start Joern server
cd C:/Users/user/joern
joern -J-Xmx16G --server --server-host localhost --server-port 8080

# Bootstrap workspace (from C:/Users/user/joern)
python pg17_client.py --query "import _root_.io.joern.joerncli.console.Joern"
python pg17_client.py --query "import _root_.io.shiftleft.semanticcpg.language._"
python pg17_client.py --query "Joern.open(\"pg17_full.cpg\")"
python pg17_client.py --query "val cpg = Joern.cpg"
```

Or use auto-bootstrapping via `scripts/bootstrap_joern.ps1` (integrated in LangGraph).

## Current Metrics (Research Evaluation)

### Query Generation Performance
- **Validity**: 97.5% on 200-question statistical run
- **Execution Success**: 86.7% on 30-question enrichment suite
- **Enrichment Coverage**: 62.2% (improved from 44%)

### Semantic Mode Performance (November 2025 - Latest)
- **Semantic Query Generation**: 100% (22/22 scale validation questions)
- **Comment Access Rate**: 100% (cpg.comment accessed in all semantic queries)
- **Execution Success**: 100% (all generated queries execute successfully)
- **Answer Confidence**: 0.90 average (high quality semantic answers)
- **Average Query Time**: 202-343s per semantic question (scales with query complexity)

**Validation Results**:
- ✅ 3-question initial test: 100% success (12.6s avg)
- ✅ 5-question extended test: 100% success (355.6s avg)
- ✅ 22-question scale test: 100% success (202-343s avg)

**Key Improvements (10x increase)**:
- Simplified semantic prompts (13KB → 2KB, 85% reduction)
- Multiline query extraction for `.map {}` structures
- Smart fallback with method name extraction
- Scala syntax fix with explicit statement termination

### Retrieval Quality (RAGAS on 50 samples)
- **Q&A Similarity**: 0.524-0.839
- **Tag Usage**: 100% in generated queries
- **Context Precision**: High semantic alignment

### Three-Dimensional Context Impact
- **DDG Retrieval Rate**: Expected 20% → 80% (after domain-concept enrichment)
- **CFG Retrieval Rate**: Expected 15% → 70%
- **Comment Usage**: Achieved 100% in semantic mode (0% → 100%)
- **Query Diversity**: Shift from 100% tags-only to mixed context (DDG 40%, CFG 40%, Comments 100% in semantic mode)

## Repository Structure

```
rag_cpgql/
├── config.yaml                      # System configuration (model path, server endpoints)
├── demo_simple.py                   # Quick demo script for testing the system
├── enrich_ddg_patterns.py           # DDG domain-concept enrichment tool
├── test_enriched_ddg.py             # Semantic similarity validation for enriched patterns
├── requirements.txt                 # Python dependencies
│
├── src/                             # Source code [detailed READMEs in each subdirectory]
│   ├── agents/                      # Core agents (analyze, retrieve, enrich, generate)
│   │   └── README.md                # Agent architecture and pipeline documentation
│   ├── retrieval/                   # ChromaDB vector stores and retrievers
│   │   └── README.md                # Vector store setup and retrieval mechanisms
│   ├── extraction/                  # CPG pattern extractors + domain concept tagger
│   │   └── README.md                # Extraction pipeline and enrichment layers
│   ├── generation/                  # LLM interface + prompt templates
│   │   └── README.md                # Query generation and prompt engineering
│   ├── workflow/                    # LangGraph orchestration with retry logic
│   │   └── README.md                # Workflow graph and state management
│   ├── execution/                   # Joern client and workspace management
│   │   └── README.md                # Query execution and Joern integration
│   ├── ranking/                     # Multi-query result ranking
│   │   └── README.md                # RRF and diversity-aware ranking
│   ├── evaluation/                  # Metrics computation and RAGAS integration
│   │   └── README.md                # Evaluation framework and RAGAS metrics
│   └── utils/                       # Configuration and data loading utilities
│       └── README.md                # Configuration management and data loaders
│
├── experiments/                     # Benchmark scripts and evaluation
│   ├── run_langgraph_200_questions.py  # Primary 200-question benchmark
│   ├── test_comprehensive_ragas.py     # RAGAS evaluation framework
│   └── README.md                       # Complete experiment documentation and workflow
│
├── data/                            # Datasets, patterns, enrichments
│   ├── train_split_merged.jsonl     # 23,156 Q&A training pairs
│   ├── test_split_merged.jsonl      # 4,087 Q&A test pairs
│   ├── cpgql_examples.json          # 1,072 canonical query templates
│   ├── cfg_patterns.json            # 53,970 control flow patterns
│   ├── ddg_patterns.json            # 169,303 raw data flow patterns
│   ├── ddg_patterns_enriched.json   # Domain-concept enriched DDG (117MB)
│   ├── cpg_documentation_complete.json  # 638 documented methods
│   └── README.md                    # Complete data catalog and statistics
│
├── results/                         # Benchmark outputs and RAGAS evaluations
│   ├── comprehensive_ragas_results_*.json  # RAGAS evaluation results
│   ├── ragas_summary_*.txt          # Statistical summaries
│   └── README.md                    # Results interpretation and metrics guide
│
├── scripts/                         # Utility scripts for setup and maintenance
│   ├── bootstrap_joern.ps1          # Joern workspace initialization
│   ├── init_vector_store.py         # Vector store setup
│   ├── manage_cache.py              # Retrieval cache management
│   └── README.md                    # Script usage and troubleshooting
│
├── cpgql_gbnf/                      # CPGQL grammar for constrained generation
│   ├── cpgql_llama_cpp_v2.gbnf      # GBNF grammar file for llama.cpp
│   └── README.md                    # Grammar syntax and usage documentation
│
└── chromadb_storage/                # Persistent vector store data (3.1GB)
    ├── qa_collection/               # Q&A pairs (23,156 documents)
    ├── examples_collection/         # CPGQL examples (1,072 documents)
    ├── cfg_patterns/                # Control flow patterns (53,970 documents)
    ├── ddg_patterns_enriched/       # Enriched data flow patterns (169,303 documents)
    └── documentation/               # Code documentation (638 documents)
```

**📚 Documentation**: Each major directory contains a comprehensive README.md with detailed information about:
- Purpose and architecture
- Component descriptions and usage
- Configuration options
- Performance metrics
- Integration points and dependencies
- Examples and troubleshooting guides

## Key Implementation Components

### Enrichment Pipeline
- **Tag Extraction**: `src/extraction/tag_extractor.py`
- **CFG Patterns**: `src/extraction/cfg_extractor.py`
- **DDG Patterns**: `src/extraction/ddg_extractor.py`
- **Domain Concepts**: `src/extraction/domain_concept_tagger.py`
- **Enrichment Script**: `enrich_ddg_patterns.py`

### Agents
- **Analyzer**: `src/agents/analyzer_agent.py`
- **Retriever**: `src/agents/retriever_agent.py`
- **Enrichment**: `src/agents/enrichment_agent.py` (with `enrichment_prompt_builder.py`)
- **Generator**: `src/agents/generator_agent.py` (with semantic mode improvements)
- **Interpreter**: `src/agents/interpreter_agent.py` (semantic answer synthesis)

### Semantic Query Generation (November 2025 Update)
- **Simplified Prompts**: `src/generation/prompts_semantic_simple.py` (2KB template-based)
- **Query Extraction**: Multiline `.map {}` support in `generator_agent.py`
- **Smart Fallback**: Method name extraction for targeted queries
- **Validation Tests**:
  - `test_semantic_improvements.py` (3-question validation, 100% success)
  - `test_semantic_5q_validation.py` (5-question extended test)
- **Documentation**: `SEMANTIC_IMPROVEMENTS_SUMMARY.md` (complete technical details)

### Workflow Orchestration
- **LangGraph**: `src/workflow/langgraph_workflow_simple.py`
- **State Management**: Validation, retry (≤2), execution, answer interpretation
- **Semantic Mode**: Comment-based question answering with 12.6M code comments

## Research Workflow (ANALYSIS_AND_PAPER_PLAN.md)

See `ANALYSIS_AND_PAPER_PLAN.md` for detailed 11-day research plan:

### Phase 1 - Data Collection (Days 1-2)
- Run 200-question benchmarks for all configurations
- Execute ablation studies (enrichment layers)
- Capture LangGraph execution traces

### Phase 2 - Statistical Analysis (Days 3-4)
- Compute descriptive statistics and significance tests
- Generate violin/box plots for metrics
- Create master evaluation table

### Phase 3 - Enrichment Impact Study (Days 5-6)
- Build contribution matrix (question categories → enrichment layers)
- Cumulative ablation analysis
- Error taxonomy and qualitative examples

### Phase 4 - Paper Drafting (Days 7-10)
- 8-12 page draft (ICSE/FSE template)
- 8 figures, 6 tables
- Introduction, approach, evaluation, discussion

### Phase 5 - Artifact Packaging (Day 11)
- Docker/Conda reproducibility package
- Curated shareable dataset
- Zenodo archive for DOI

## Known Limitations & Future Work

### Current Status
- **Production Ready**: Generation pipeline with 3D context
- **Automated Execution**: Joern workspace auto-loading via LangGraph
- **Enrichment Quality**: 100/100 score, but architectural tags use filename fallbacks

### Research Questions for Paper
1. **RQ1**: How much do semantic enrichments improve query validity and execution success?
2. **RQ2**: What is the marginal contribution of each enrichment layer?
3. **RQ3**: How does three-dimensional context (Doc+CFG+DDG) impact retrieval and generation quality?
4. **RQ4**: What are the runtime trade-offs of enrichment-aware RAG vs. baseline approaches?

### Threats to Validity
- **External**: Single codebase (PostgreSQL 17), may not generalize to other domains
- **Internal**: Manual enrichment validation, potential bias in Q&A dataset
- **Construct**: RAGAS metrics may not fully capture semantic correctness
- **Conclusion**: Limited to Qwen3-Coder model, may vary with other LLMs

## Citation & Publication

This work is in preparation for submission to ICSE/FSE/ASE 2025. Reproducibility artifacts will be published upon acceptance.

## Contact & Collaboration

For research collaboration, dataset access, or reproducibility questions, please open an issue in the repository.

---

**Last Updated**: 2025-11-04
**Implementation Status**: Phase 3 Complete + Semantic Mode Optimizations + Scale Validation (22Q @ 100%)
**Next Milestone**: Phase 1 Data Collection (200-question baseline and ablation studies)

**Recent Updates (November 2025)**:
- ✅ Semantic query generation: 10% → 100% (10x improvement)
- ✅ Simplified semantic prompts: 13KB → 2KB (85% reduction)
- ✅ Multiline query extraction for `.map {}` structures
- ✅ Smart fallback with method name extraction
- ✅ Scala syntax fix with explicit statement termination
- ✅ Scale validation: 22-question test at 100% success rate
- ✅ Documentation: `SEMANTIC_IMPROVEMENTS_SUMMARY.md` with complete technical details
