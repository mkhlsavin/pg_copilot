# Installation Guide

Complete installation instructions for RAG-CPGQL.

## System Requirements

### Hardware
- **CPU**: 8+ cores recommended
- **RAM**: 32GB minimum (64GB for large codebases)
- **GPU**: NVIDIA RTX 3090 or better (for local LLM)
- **Storage**: 100GB free space

### Software
- Windows 10/11 or Linux
- Anaconda/Miniconda
- CUDA Toolkit 11.8+ (for GPU acceleration)
- Git

## Step 1: Environment Setup

```bash
# Clone repository
git clone <repository-url>
cd rag_cpgql

# Create conda environment
conda create -n llama.cpp python=3.11
conda activate llama.cpp

# Install PyTorch with CUDA (for GPU)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install requirements
pip install -r requirements.txt
```

## Step 2: DuckDB Setup

The CPG database is pre-built in `cpg.duckdb`. To verify:

```bash
python -c "
import duckdb
conn = duckdb.connect('cpg.duckdb')
print('Methods:', conn.execute('SELECT COUNT(*) FROM nodes_method').fetchone()[0])
print('Calls:', conn.execute('SELECT COUNT(*) FROM nodes_call').fetchone()[0])
"
```

Expected output:
```
Methods: 52303
Calls: 111208
```

## Step 3: Vector Store Setup

ChromaDB storage is in `chromadb_storage/` (3.1GB). Verify:

```python
from src.retrieval.vector_store_real import VectorStoreReal

vs = VectorStoreReal()
print(f"QA documents: {vs.qa_collection.count()}")
print(f"Examples: {vs.examples_collection.count()}")
```

## Step 4: LLM Provider Setup

### Option A: GigaChat (Recommended for Russia)

```bash
# Set environment variable
export GIGACHAT_AUTH_KEY="your_auth_key"

# Update config.yaml
# llm:
#   provider: gigachat
```

See [GigaChat Integration](../integrations/GIGACHAT.md) for details.

### Option B: Local LLM (llama-cpp-python)

```bash
# Install llama-cpp-python with CUDA
CMAKE_ARGS="-DLLAMA_CUDA=on" pip install llama-cpp-python

# Download model (Qwen3-Coder-30B recommended)
# Place in: ~/.lmstudio/models/

# Update config.yaml
# llm:
#   provider: local
#   model_path: path/to/model.gguf
```

### Option C: OpenAI API

```bash
export OPENAI_API_KEY="your_api_key"

# Update config.yaml
# llm:
#   provider: openai
#   model: gpt-4
```

## Step 5: Joern Setup (Optional)

For CPGQL query support:

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File scripts/bootstrap_joern.ps1

# Verify server
netstat -ano | findstr :8080
```

## Step 6: Verify Installation

```bash
# Run test suite
python -m pytest tests/unit/ -v --tb=short

# Expected: 54+ tests passing

# Run demo
python demo_simple.py
```

## Troubleshooting

### CUDA Not Found

```bash
# Check CUDA installation
nvcc --version
nvidia-smi

# Reinstall PyTorch with CUDA
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### DuckDB Connection Error

```bash
# Check file exists
ls -la cpg.duckdb

# Check permissions
chmod 644 cpg.duckdb
```

### ChromaDB Initialization Failed

```bash
# Reinitialize vector store
python scripts/init_vector_store.py
```

### Out of Memory

```yaml
# Reduce batch sizes in config.yaml
retrieval:
  batch_size: 50  # Lower from 100
  top_k: 5        # Lower from 10
```

## Next Steps

- [Configuration](CONFIGURATION.md) - Customize settings
- [User Guide](../guides/USER_GUIDE.md) - Learn to use the system
- [Troubleshooting](../guides/TROUBLESHOOTING.md) - Common issues
