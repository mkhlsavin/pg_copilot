# Configuration Guide

Configure RAG-CPGQL for your environment.

## Configuration Files

| File | Purpose |
|------|---------|
| `config.yaml` | Main configuration |
| `.env` | Environment variables |
| `config/prompts/*.yaml` | Prompt templates |

## Main Configuration (config.yaml)

```yaml
# Domain Configuration
domain:
  name: postgresql      # postgresql, linux_kernel, llvm, generic
  auto_activate: true   # Automatically activate domain plugin

# CPG Database
cpg:
  type: postgresql
  db_path: cpg.duckdb

# LLM Provider
llm:
  provider: gigachat    # gigachat, local, openai
  model: GigaChat-2-Pro
  temperature: 0.1
  max_tokens: 4096

# Retrieval Settings
retrieval:
  embedding_model: all-MiniLM-L6-v2
  embedding_dimension: 384   # Embedding vector dimension
  top_k_qa: 3
  top_k_cpgql: 5
  max_results: 50            # Maximum search results
  chunk_size: 512            # Text chunk size for embeddings

  # Hybrid retrieval (Phase 1)
  hybrid:
    enabled: true
    vector_weight: 0.6
    graph_weight: 0.4
    rrf_k: 60

# Query limits for database operations
query:
  default_limit: 100         # Default LIMIT for SQL queries
  max_limit: 1000            # Maximum allowed LIMIT

# Analysis thresholds
analysis:
  sanitization_confidence_threshold: 0.7  # Threshold for sanitization detection
  similarity_threshold: 0.8               # Threshold for semantic similarity
  complexity_threshold: 10                # Cyclomatic complexity threshold

# Paths
paths:
  chromadb_storage: chromadb_storage
  data: data
  logs: logs
```

## Domain Configuration

Switch between codebases by changing the domain:

```yaml
domain:
  name: postgresql  # Analyze PostgreSQL
```

Available domains:
- `postgresql` - PostgreSQL 17.6
- `linux_kernel` - Linux Kernel 6.x
- `llvm` - LLVM 18.x
- `generic` - Generic C/C++ codebase

## LLM Provider Configuration

### GigaChat

```yaml
llm:
  provider: gigachat
  model: GigaChat-2-Pro
  scope: GIGACHAT_API_PERS
```

Environment variable:
```bash
export GIGACHAT_AUTH_KEY="your_key"
```

### Local LLM

```yaml
llm:
  provider: local
  model_path: /path/to/model.gguf
  n_gpu_layers: -1   # Use all GPU layers
  n_ctx: 8192        # Context window
  n_threads: 8       # CPU threads
```

### OpenAI

```yaml
llm:
  provider: openai
  model: gpt-4
  api_base: https://api.openai.com/v1
```

Environment variable:
```bash
export OPENAI_API_KEY="your_key"
```

## Hybrid Retrieval Configuration

```yaml
retrieval:
  hybrid:
    enabled: true

    # Weight distribution (should sum to 1.0)
    vector_weight: 0.6  # Semantic search weight
    graph_weight: 0.4   # Structural search weight

    # RRF parameters
    rrf_k: 60           # RRF constant (default: 60)

    # Adaptive weights by query type
    adaptive_weights:
      semantic:
        vector: 0.75
        graph: 0.25
      structural:
        vector: 0.25
        graph: 0.75
      security:
        vector: 0.5
        graph: 0.5
```

## Performance Tuning

### For Large Codebases

```yaml
retrieval:
  batch_size: 50
  top_k_qa: 3
  top_k_cpgql: 3

llm:
  max_tokens: 2048

cache:
  enabled: true
  ttl: 3600  # 1 hour
```

### For Fast Response

```yaml
retrieval:
  hybrid:
    enabled: false  # Vector-only mode
  top_k_qa: 1

llm:
  temperature: 0.0
  max_tokens: 1024
```

### For High Accuracy

```yaml
retrieval:
  hybrid:
    enabled: true
  top_k_qa: 10
  top_k_cpgql: 10

llm:
  temperature: 0.3
  max_tokens: 8192
```

## Environment Variables

Create `.env` file (copy from `.env.example`):

```bash
# =============================================================================
# LLM API Providers
# =============================================================================
GIGACHAT_AUTH_KEY=your_gigachat_key      # Required for GigaChat provider
OPENAI_API_KEY=your_openai_key           # Required for OpenAI provider

# =============================================================================
# Local Model Paths (REQUIRED for local LLM provider)
# =============================================================================
# Path to fine-tuned LLMxCPG model (recommended for CPGQL generation)
LLMXCPG_MODEL_PATH=/path/to/llmxcpg/qwen2.5-coder-32B-instruct.gguf

# Path to base Qwen3 model (alternative general-purpose model)
QWEN3_MODEL_PATH=/path/to/qwen3/Qwen3-Coder-30B-A3B-Instruct.gguf

# =============================================================================
# Database Paths
# =============================================================================
DUCKDB_PATH=cpg.duckdb                   # Path to DuckDB CPG database
CHROMADB_PATH=chroma_db                  # Path to ChromaDB vector storage

# =============================================================================
# Joern Server
# =============================================================================
JOERN_HOST=localhost
JOERN_PORT=8080
JOERN_QUERY_TIMEOUT=60

# =============================================================================
# Logging
# =============================================================================
LOG_LEVEL=INFO                           # DEBUG, INFO, WARNING, ERROR
LLM_VERBOSE=false                        # Verbose LLM provider logging

# =============================================================================
# Performance
# =============================================================================
CUDA_VISIBLE_DEVICES=0                   # GPU selection for llama-cpp
OMP_NUM_THREADS=8                        # CPU threads
```

### Required Variables by Provider

| Provider | Required Variables |
|----------|-------------------|
| `local` | `LLMXCPG_MODEL_PATH` or `QWEN3_MODEL_PATH` |
| `gigachat` | `GIGACHAT_AUTH_KEY` |
| `openai` | `OPENAI_API_KEY` |

## Prompt Configuration

Prompts are stored in `config/prompts/`:

```yaml
# config/prompts/prompts.yaml
prompts:
  analyzer:
    question_analysis: |
      Analyze the following question about code:
      {question}

      Extract:
      - Intent (what user wants)
      - Domain (which subsystem)
      - Keywords (important terms)
```

### Domain-Specific Prompts

```yaml
# config/prompts/cpg_domains.yaml
domains:
  postgresql:
    code_analyst_title: PostgreSQL 17.6 expert
    subsystems:
      - access-method
      - storage-engine
      - transaction-manager

  linux_kernel:
    code_analyst_title: Linux Kernel 6.x expert
    subsystems:
      - scheduler
      - memory-management
      - filesystem
```

## Logging Configuration

```yaml
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: logs/rag_cpgql.log
  max_size: 10MB
  backup_count: 5
```

## Validation

Validate your configuration:

```bash
python -c "
from src.config import CPGConfig
config = CPGConfig()
print(f'Domain: {config.cpg_type}')
print(f'LLM: {config.llm_provider}')
print(f'Valid: OK')
"
```

## Next Steps

- [User Guide](../guides/USER_GUIDE.md) - Start using the system
- [Troubleshooting](../guides/TROUBLESHOOTING.md) - Common issues
