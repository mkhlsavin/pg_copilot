# Retrieval Module

This module implements vector store operations and retrieval mechanisms for the CodeGraph system. It provides three-dimensional context retrieval (Documentation + Control Flow + Data Flow).

## Architecture Overview

The retrieval system uses ChromaDB for efficient semantic search across multiple data sources:

```
Question Analysis
        ↓
┌───────┴───────┐
│  Vector Store  │
│   Retrievers   │
└───────┬───────┘
        ↓
Multi-Source Retrieval:
  - Q&A Pairs
  - SQL Query Examples
  - CFG Patterns
  - DDG Patterns
  - Documentation Comments
```

## Core Components

### 1. Q&A and Example Retrieval

#### `vector_store_real.py`
**Purpose**: Main vector store for Q&A pairs and SQL query examples.

**Data Sources**:
- `data/train_split_merged.jsonl` (23,156 Q&A pairs)
- `data/cpgql_examples.json` (1,072 SQL query templates for CPG)

**Features**:
- Dual-collection architecture (Q&A + Examples)
- Semantic similarity search
- Relevance scoring
- Persistent storage in `chromadb_storage/`

**Usage**:
```python
from src.retrieval.vector_store_real import retrieve_qa, retrieve_examples

qa_results = retrieve_qa(question, top_k=10)
examples = retrieve_examples(question, top_k=5)
```

#### `vector_store.py`
**Purpose**: Legacy/alternative vector store implementation.

### 2. Control Flow Graph (CFG) Retrieval

#### `cfg_vector_store.py`
**Purpose**: Indexes and retrieves control flow patterns.

**Data Source**: `data/cfg_patterns.json` (53,970 patterns)

**Pattern Types**:
- Error handling patterns (try/catch, error codes)
- Lock acquisition/release sequences
- Transaction begin/commit flows
- Conditional branching patterns
- Loop structures

**Storage**: `chromadb_storage/cfg_patterns/`

**Features**:
- Pattern-level indexing
- Complexity metric filtering
- Pattern type categorization

#### `cfg_retriever.py`
**Purpose**: High-level CFG retrieval interface.

**Key Functions**:
- `retrieve_cfg_patterns(question, top_k=10)`
- Pattern filtering by complexity
- Relevance ranking

**Usage**:
```python
from src.retrieval.cfg_retriever import retrieve_cfg_patterns

cfg_patterns = retrieve_cfg_patterns(
    question="How are locks acquired in PostgreSQL?",
    top_k=10
)
```

### 3. Data Dependency Graph (DDG) Retrieval

#### `ddg_vector_store.py`
**Purpose**: Indexes and retrieves data flow patterns with domain concept enrichment.

**Data Sources**:
- `data/ddg_patterns.json` (169,303 raw patterns)
- `data/ddg_patterns_enriched.json` (domain-concept enriched, 117MB)

**Pattern Types**:
- Parameter flows (141K patterns)
- Call argument propagation (18.7K patterns)
- Variable dependency chains (6.8K patterns)
- Return value sources (1.8K patterns)
- Control dependencies (738 patterns)

**Domain Concepts**: 51 PostgreSQL concepts (mvcc, wal, brin-index, etc.)
**Coverage**: 72.6% patterns tagged, avg 2.49 concepts/pattern

**Storage**: `chromadb_storage/ddg_patterns_enriched/`

**Features**:
- Concept-enriched retrieval
- Multi-pattern aggregation
- Source-sink flow tracking

#### `ddg_retriever.py`
**Purpose**: High-level DDG retrieval interface.

**Key Functions**:
- `retrieve_ddg_patterns(question, top_k=15)`
- Concept-based filtering
- Flow type categorization

**Usage**:
```python
from src.retrieval.ddg_retriever import retrieve_ddg_patterns

ddg_patterns = retrieve_ddg_patterns(
    question="Where does transaction ID flow in MVCC?",
    top_k=15
)
```

### 4. Documentation Retrieval

#### `doc_vector_store.py`
**Purpose**: Indexes and retrieves code documentation comments.

**Data Source**: `data/cpg_documentation_complete.json` (638 methods)

**Features**:
- Method-level documentation
- Comment extraction from CPG
- Function signature matching

**Storage**: `chromadb_storage/documentation/`

#### `documentation_retriever.py`
**Purpose**: High-level documentation retrieval interface.

**Key Functions**:
- `retrieve_documentation(question, top_k=5)`
- Comment filtering by relevance
- Method name matching

## Supporting Components

### Retrieval Cache (`retrieval_cache.py`)
**Purpose**: Caches retrieval results to improve performance.

**Features**:
- Query-based caching
- TTL (time-to-live) management
- Cache invalidation
- Statistics tracking

**Performance Impact**:
- First retrieval: ~500ms
- Cached retrieval: ~10ms
- Hit rate: ~35% on benchmark runs

**Storage**: `chromadb_storage/retrieval_cache/`

**Usage**:
```python
from src.retrieval.retrieval_cache import RetrievalCache

cache = RetrievalCache()
results = cache.get_or_retrieve(question, retrieval_fn)
```

## Vector Store Configuration

### ChromaDB Settings
- **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Distance Metric**: Cosine similarity
- **Persistence**: Local disk storage

### Collection Structure

```
chromadb_storage/
├── qa_collection/           # Q&A pairs
├── examples_collection/     # SQL query examples
├── cfg_patterns/            # Control flow patterns
├── ddg_patterns_enriched/   # Data flow patterns (enriched)
├── documentation/           # Code comments
└── retrieval_cache/         # Cached results
```

## Retrieval Pipeline

### Standard Retrieval Flow

```python
from src.retrieval.vector_store_real import retrieve_qa, retrieve_examples
from src.retrieval.cfg_retriever import retrieve_cfg_patterns
from src.retrieval.ddg_retriever import retrieve_ddg_patterns
from src.retrieval.documentation_retriever import retrieve_documentation

def retrieve_all_context(question):
    return {
        'qa': retrieve_qa(question, top_k=10),
        'examples': retrieve_examples(question, top_k=5),
        'cfg': retrieve_cfg_patterns(question, top_k=10),
        'ddg': retrieve_ddg_patterns(question, top_k=15),
        'docs': retrieve_documentation(question, top_k=5)
    }
```

## Building Vector Stores

### Initial Setup

```powershell
# Build Q&A and examples store
python src/retrieval/vector_store_real.py

# Build CFG pattern store
python src/extraction/cfg_extractor.py  # Extract patterns
python src/retrieval/cfg_vector_store.py  # Index patterns

# Build DDG pattern store (enriched)
python src/extraction/ddg_extractor.py  # Extract raw patterns
python enrich_ddg_patterns.py  # Add domain concepts
python src/retrieval/ddg_vector_store.py  # Index enriched patterns

# Build documentation store
python src/extraction/comment_extractor_v4.py  # Extract comments
python src/retrieval/doc_vector_store.py  # Index documentation
```

## Performance Metrics

### Retrieval Latency
- **Q&A Retrieval**: ~200ms (10 results)
- **Example Retrieval**: ~150ms (5 results)
- **CFG Retrieval**: ~180ms (10 results)
- **DDG Retrieval**: ~250ms (15 results, enriched)
- **Documentation Retrieval**: ~120ms (5 results)
- **Total (parallel)**: ~500ms (all sources)

### Storage Size
- Q&A Collection: ~450MB
- Examples Collection: ~150MB
- CFG Patterns: ~320MB
- DDG Patterns (enriched): ~2.1GB
- Documentation: ~45MB
- **Total**: ~3.1GB

### Retrieval Quality (RAGAS Metrics)
- **Context Precision**: 0.78-0.92
- **Context Recall**: 0.65-0.84
- **Semantic Similarity**: 0.524-0.839
- **Retrieval Rate**: 20-80% (varies by pattern type)

## Dependencies

- `chromadb`: Vector database
- `sentence-transformers`: Embedding generation
- `langchain`: Retrieval utilities
- `numpy`: Vector operations

## See Also

- `/src/extraction/` - Pattern extraction from CPG
- `/src/agents/retriever_agent.py` - Retrieval agent orchestration
- `/data/` - Raw data sources
- `/experiments/` - Retrieval evaluation scripts
