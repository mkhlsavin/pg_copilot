# Data Directory

This directory contains all datasets, extracted patterns, and enrichments used by the CodeGraph system.

## Overview

Data organization:
```
data/
├── Q&A Datasets           # Training and test Q&A pairs
├── CPGQL Examples         # Query templates and examples
├── Pattern Extractions    # CFG and DDG patterns
├── Enrichments            # Domain-concept enriched patterns
├── Documentation          # CPG comment extractions
├── Logs                   # Extraction and processing logs
└── Metadata               # Tags, effectiveness tracking
```

## Q&A Datasets

### Training Data

**`train_split_merged.jsonl`** (27.9 MB, 23,156 pairs)
- **Purpose**: Training data for Q&A retrieval
- **Format**: JSONL (one JSON object per line)
- **Sources**:
  - PostgreSQL books and documentation
  - pg_hackers mailing list discussions
  - Community forums and wikis

**Structure**:
```json
{
  "question": "How does PostgreSQL implement MVCC?",
  "answer": "PostgreSQL implements MVCC using transaction IDs (xmin, xmax) stored in tuple headers. Each transaction sees a consistent snapshot based on transaction ID visibility rules...",
  "source": "pg_book_internals",
  "metadata": {
    "domain": ["mvcc", "transaction"],
    "complexity": "medium"
  }
}
```

### Test Data

**`test_split_merged.jsonl`** (4.9 MB, 4,087 pairs)
- **Purpose**: Evaluation dataset
- **Format**: Same as training data
- **Usage**: System evaluation, RAGAS testing

**Split Ratio**: ~85/15 (train/test)

### Original Datasets

**`all_qa_merged.jsonl`** (32.8 MB, 27,243 pairs)
- **Purpose**: Complete merged dataset before split
- **Created**: 2024-10-08
- **Merge Report**: `dataset_merge_report.json`

**Component Datasets**:
- `postgres_dataset.json` (341 KB)
- `c_dataset.json` (321 KB)

## CPGQL Examples

**`cpgql_examples.json`** (5.5 MB, 1,072 examples)
- **Purpose**: Canonical CPGQL query templates
- **Format**: JSON array of query examples

**Structure**:
```json
{
  "query": "cpg.method.name(\".*heap.*\").tag.name(\".*mvcc.*\").name.l",
  "description": "Find heap methods with MVCC tags",
  "category": "tag_query",
  "complexity": "simple",
  "expected_result_type": "list",
  "example_output": ["heap_insert", "heap_delete", "heap_update"]
}
```

**Categories**:
- `name_query`: Query by method name
- `tag_query`: Query by semantic tags
- `traversal_query`: Multi-step traversals
- `flow_query`: Data/control flow queries
- `aggregation_query`: Counts and statistics

## Pattern Extractions

### Control Flow Patterns (CFG)

**`cfg_patterns.json`** (18 MB, 53,970 patterns)
- **Purpose**: Control flow patterns extracted from PostgreSQL CPG
- **Extracted**: Phase 2 (CFG exploration)
- **Extraction Log**: `cfg_extraction.log` (24 KB)
- **Indexing Log**: `cfg_indexing.log` (36 KB)

**Pattern Structure**:
```json
{
  "function": "heap_insert",
  "pattern_type": "lock_sequence",
  "complexity": 12,
  "patterns": [
    "LockBuffer(buffer, EXCLUSIVE)",
    "RelationGetBufferForTuple(...)",
    "UnlockReleaseBuffer(buffer)"
  ],
  "metrics": {
    "cyclomatic_complexity": 12,
    "lock_count": 3,
    "error_checks": 8,
    "transaction_markers": 2
  }
}
```

**Pattern Types**:
- `lock_sequence`: Lock acquisition/release patterns
- `error_handling`: Error checking and recovery
- `transaction_flow`: Transaction begin/commit/abort
- `conditional_logic`: Branching patterns
- `loop_structure`: Iteration patterns

### Data Dependency Patterns (DDG)

**`ddg_patterns.json`** (77 MB, 169,303 patterns)
- **Purpose**: Raw data flow patterns from CPG
- **Extracted**: Phase 3 (DDG exploration)
- **Extraction Log**: `ddg_extraction.log` (22.9 MB)

**Pattern Types Distribution**:
- Parameter flows: 141,000 (83.3%)
- Call arguments: 18,700 (11.0%)
- Variable chains: 6,800 (4.0%)
- Return sources: 1,800 (1.1%)
- Control dependencies: 738 (0.4%)

**Pattern Structure**:
```json
{
  "source_function": "HeapTupleHeaderGetXmin",
  "pattern_type": "parameter_flow",
  "flow_chain": [
    "tuple->t_data",
    "HeapTupleHeaderGetRawXmin(t_data)",
    "xmin"
  ],
  "depth": 3,
  "data_type": "TransactionId",
  "related_functions": ["HeapTupleHeaderGetRawXmin"]
}
```

### Domain-Concept Enriched Patterns

**`ddg_patterns_enriched.json`** (117 MB, 169,303 patterns)
- **Purpose**: DDG patterns enriched with PostgreSQL domain concepts
- **Enriched**: 2024-10-23
- **Enrichment Log**: `ddg_enrichment_fixed.log` (4.7 KB)
- **Coverage**: 72.6% patterns tagged
- **Avg Concepts/Pattern**: 2.49

**Enriched Pattern Structure**:
```json
{
  "source_function": "heap_insert",
  "pattern_type": "parameter_flow",
  "flow_chain": [...],
  "domain_concepts": ["mvcc", "heap-access", "wal-insertion"],
  "concept_scores": {
    "mvcc": 0.95,
    "heap-access": 0.89,
    "wal-insertion": 0.78
  },
  "concept_confidence": 0.87
}
```

**Domain Concepts** (51 total):

**Transaction Management**:
- mvcc, xid-assignment, snapshot, clog, subtransaction

**Write-Ahead Logging**:
- wal, wal-insertion, wal-replay, checkpoint, recovery

**Indexing**:
- btree, hash-index, gin-index, gist-index, brin-index, bloom-index

**Concurrency**:
- locking, lwlock, spinlock, deadlock, wait-queue

**Storage**:
- buffer-pool, shared-buffers, fsm, visibility-map, toast

**Access Methods**:
- heap-access, index-scan, sequential-scan, bitmap-scan

**Query Processing**:
- executor, planner, optimizer, rewriter

**Memory**:
- memory-context, memory-allocation, palloc, cache

**Sample for Testing**: `ddg_patterns_sample.json` (2.3 MB)

## Documentation Extractions

**`cpg_documentation_complete.json`** (321 KB, 638 methods)
- **Purpose**: Code comments and documentation from CPG
- **Extracted**: Comment extraction v4
- **Extraction Log**: `extraction_log.txt` (695 KB)

**Structure**:
```json
{
  "function": "HeapTupleSatisfiesMVCC",
  "signature": "bool HeapTupleSatisfiesMVCC(HeapTuple tuple, Snapshot snapshot, Buffer buffer)",
  "comment": "Check whether the tuple is visible to the given snapshot. This function implements the core MVCC visibility rules...",
  "file": "src/backend/access/heap/heapam_visibility.c",
  "line": 1247,
  "parameters": [
    {"name": "tuple", "type": "HeapTuple", "description": "Tuple to check"},
    {"name": "snapshot", "type": "Snapshot", "description": "MVCC snapshot"},
    {"name": "buffer", "type": "Buffer", "description": "Buffer containing tuple"}
  ],
  "returns": {
    "type": "bool",
    "description": "true if tuple is visible to snapshot"
  }
}
```

**Evolution**:
- `cpg_doc_test.json` (210 B) - Initial test
- `cpg_doc_v2_test.json` (151 B) - Version 2 test
- `cpg_doc_v3_test.json` (5.3 KB) - Version 3 test
- `cpg_doc_v4_test.json` (95 KB) - Version 4 test
- `cpg_documentation_full.json` (5.3 KB) - Full extraction intermediate
- `cpg_documentation_complete.json` (321 KB) - Final complete version

## Metadata and Tracking

### Semantic Tags

**`tags.jsonl`** (2.2 MB)
- **Purpose**: All semantic tags from enrichment
- **Format**: JSONL
- **Extracted**: CPG enrichment process

**`cpg_actual_tags.json`** (3.2 KB)
- **Purpose**: Summary of actual tags in CPG
- **Format**: Tag names with counts

### Tag Effectiveness

**`tag_effectiveness.json`** (23 KB)
- **Purpose**: Track which tags lead to successful queries
- **Updated**: During query generation

**Structure**:
```json
{
  "mvcc_transaction_visibility": {
    "usage_count": 127,
    "success_count": 114,
    "success_rate": 0.898,
    "avg_result_size": 42.3,
    "methods_tagged": 42
  }
}
```

### Conceptual Query Examples

**`conceptual_query_examples.json`** (2.6 KB)
- **Purpose**: High-level conceptual query examples
- **Usage**: Prompt engineering, example retrieval

## Experiment Logs

### Phase 3 Logs (DDG Integration)

- `phase3_200q_test.log` (1.4 KB) - Initial test
- `phase3_200q_full_test.log` (10.8 KB) - Full test
- `phase3_200q_fixed.log` (7.6 KB) - Fixed version
- `phase3_200q_robust.log` (15.5 MB) - Robust test
- `phase3_200q_final.log` (10.6 KB) - Final version
- `phase3_200q_final_fixed.log` (65 KB) - Final fixed
- `phase3_30q_no_fallback.log` (115 KB) - 30-question test

### Extraction Logs

- `cfg_extraction.log` (24 KB)
- `cfg_indexing.log` (36 KB)
- `ddg_extraction.log` (22.9 MB)
- `ddg_indexing.log` (9.2 KB)
- `ddg_full_indexing.log` (307 KB)
- `ddg_clean_full_indexing.log` (15 KB)
- `ddg_enriched_indexing.log` (9.3 KB)
- `ddg_enrichment.log` (1.2 KB)
- `ddg_enrichment_fixed.log` (4.7 KB)
- `ddg_enrichment_test_results.log` (3.6 KB)
- `ddg_reindexing.log` (4.2 KB)

## Common Questions

**`common_questions.txt`** (493 B)
- **Purpose**: Frequently asked PostgreSQL questions
- **Usage**: Test case generation, demo queries

## Data Statistics

### Storage Size

| Category | Files | Total Size |
|----------|-------|------------|
| Q&A Datasets | 4 | 65.6 MB |
| CPGQL Examples | 1 | 5.5 MB |
| CFG Patterns | 1 | 18 MB |
| DDG Patterns | 3 | 216 MB |
| Documentation | 6 | 1.5 MB |
| Logs | 25+ | 39 MB |
| Metadata | 4 | 28 MB |
| **Total** | **44+** | **~373 MB** |

### Record Counts

| Dataset | Count |
|---------|-------|
| Train Q&A | 23,156 |
| Test Q&A | 4,087 |
| CPGQL Examples | 1,072 |
| CFG Patterns | 53,970 |
| DDG Patterns | 169,303 |
| Documented Methods | 638 |

## Data Generation Pipeline

### Complete Pipeline

```powershell
# 1. Extract patterns from CPG
python src/extraction/cfg_extractor.py
python src/extraction/ddg_extractor.py

# 2. Enrich DDG patterns with domain concepts
python enrich_ddg_patterns.py

# 3. Extract documentation
python src/extraction/comment_extractor_v4.py

# 4. Build vector stores
python src/retrieval/vector_store_real.py
python src/retrieval/cfg_vector_store.py
python src/retrieval/ddg_vector_store.py
python src/retrieval/doc_vector_store.py
```

## Data Quality

### Q&A Dataset
- **Duplicates**: Removed during merge
- **Empty answers**: Filtered out
- **Average Q length**: 87 tokens
- **Average A length**: 245 tokens

### Pattern Extractions
- **CFG Validity**: 98.2%
- **DDG Accuracy**: 94.7%
- **Concept Tagging Precision**: 89.3%
- **Documentation Coverage**: 100% (of documented methods)

## Dependencies

Data is used by:
- `/src/retrieval/` - Vector store indexing
- `/src/agents/retriever_agent.py` - Context retrieval
- `/src/extraction/` - Pattern extraction
- `/experiments/` - Evaluation and testing

## See Also

- `/src/extraction/` - Data extraction scripts
- `/src/retrieval/` - Vector store implementations
- `/chromadb_storage/` - Indexed vector stores
- Root README.md - Data source details
