# Quick Start Guide

Get RAG-CPGQL running in 5 minutes.

## Prerequisites

- Python 3.10+
- 32GB RAM (recommended)
- NVIDIA GPU with CUDA (for local LLM)
- 100GB free disk space

## Installation

```bash
# Clone repository
git clone <repository-url>
cd rag_cpgql

# Create conda environment
conda create -n llama.cpp python=3.11
conda activate llama.cpp

# Install dependencies
pip install -r requirements.txt
```

## Verify Installation

```bash
# Check DuckDB CPG
python -c "import duckdb; conn = duckdb.connect('cpg.duckdb'); print(conn.execute('SELECT COUNT(*) FROM nodes_method').fetchone())"
# Expected: (52303,)

# Check vector store
python -c "from src.retrieval.vector_store_real import VectorStoreReal; vs = VectorStoreReal(); print('OK')"
```

## Run Demo

```bash
python demo_simple.py
```

### Example Queries

```
> Find method 'CommitTransaction'
> What methods call 'AbortTransaction'?
> Find methods in file 'xact.c'
```

## Next Steps

- [Detailed Installation](INSTALLATION.md) - Full setup with all dependencies
- [Configuration](CONFIGURATION.md) - Customize settings
- [User Guide](../guides/USER_GUIDE.md) - Complete tutorial
