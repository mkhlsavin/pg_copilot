# Troubleshooting Guide

Common issues and solutions for CodeGraph.

## Table of Contents

- [Installation Issues](#installation-issues)
  - [CUDA Not Found](#cuda-not-found)
  - [DuckDB Connection Failed](#duckdb-connection-failed)
  - [ChromaDB Initialization Failed](#chromadb-initialization-failed)
  - [Import Errors](#import-errors)
- [LLM Provider Issues](#llm-provider-issues)
  - [GigaChat Authentication Failed](#gigachat-authentication-failed)
  - [Local LLM Out of Memory](#local-llm-out-of-memory)
  - [LLM Response Timeout](#llm-response-timeout)
- [Query Issues](#query-issues)
  - [No Results Found](#no-results-found)
  - [Slow Query Performance](#slow-query-performance)
  - [Incorrect Results](#incorrect-results)
- [Joern Server Issues](#joern-server-issues)
  - [Server Won't Start](#server-wont-start)
  - [CPGQL Query Timeout](#cpgql-query-timeout)
- [Memory Issues](#memory-issues)
  - [Out of Memory During Processing](#out-of-memory-during-processing)
  - [High Memory Usage](#high-memory-usage)
- [Debugging](#debugging)
  - [Enable Debug Logging](#enable-debug-logging)
  - [Check Component Status](#check-component-status)
  - [Generate Debug Report](#generate-debug-report)
- [Getting Help](#getting-help)
- [Next Steps](#next-steps)

## Installation Issues

### CUDA Not Found

**Symptom:**
```
RuntimeError: CUDA not available
```

**Solution:**
```bash
# Check CUDA installation
nvidia-smi
nvcc --version

# Reinstall PyTorch with CUDA
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### DuckDB Connection Failed

**Symptom:**
```
duckdb.IOException: Could not open file 'cpg.duckdb'
```

**Solution:**
```bash
# Check file exists
ls -la cpg.duckdb

# Check permissions
chmod 644 cpg.duckdb

# Check not locked by another process
lsof cpg.duckdb  # Linux/Mac
```

### ChromaDB Initialization Failed

**Symptom:**
```
chromadb.errors.ChromaDBError: Collection not found
```

**Solution:**
```bash
# Verify chromadb_storage exists
ls -la chromadb_storage/

# Reinitialize if needed
python scripts/init_vector_store.py
```

### Import Errors

**Symptom:**
```
ModuleNotFoundError: No module named 'src'
```

**Solution:**
```bash
# Ensure you're in the project root
cd /path/to/codegraph

# Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or use pip install in development mode
pip install -e .
```

## LLM Provider Issues

### GigaChat Authentication Failed

**Symptom:**
```
401 Unauthorized: Invalid credentials
```

**Solution:**
```bash
# Check environment variable
echo $GIGACHAT_AUTH_KEY

# Set if missing
export GIGACHAT_AUTH_KEY="your_key"

# Verify in Python
python -c "import os; print(os.environ.get('GIGACHAT_AUTH_KEY', 'NOT SET'))"
```

### Local LLM Out of Memory

**Symptom:**
```
CUDA out of memory
```

**Solution:**
```yaml
# Reduce model layers in config.yaml
llm:
  n_gpu_layers: 20  # Reduce from -1
  n_ctx: 4096       # Reduce context window
```

Or use a smaller quantization:
```bash
# Use Q4_K_M instead of Q5_K_M
```

### LLM Response Timeout

**Symptom:**
```
TimeoutError: LLM did not respond within timeout
```

**Solution:**
```yaml
# Increase timeout in config.yaml
llm:
  timeout: 120  # seconds
  max_retries: 3
```

## Query Issues

### No Results Found

**Symptom:**
```
No methods found matching query
```

**Solutions:**
1. **Check spelling** - Method names are case-sensitive
2. **Use partial match** - Try `*Transaction*` instead of `CommitTransaction`
3. **Check database** - Verify data exists:
   ```sql
   SELECT COUNT(*) FROM nodes_method WHERE full_name LIKE '%Transaction%';
   ```

### Slow Query Performance

**Symptom:**
Query takes more than 10 seconds

**Solutions:**
```yaml
# Reduce search scope in config.yaml
retrieval:
  top_k_qa: 3      # Reduce from 10
  top_k_cpgql: 3   # Reduce from 10

# Disable hybrid mode for speed
retrieval:
  hybrid:
    enabled: false
```

### Incorrect Results

**Symptom:**
Answers don't match expected results

**Solutions:**
1. **Refine question** - Be more specific
2. **Check domain** - Ensure correct domain is set
3. **Verify embeddings** - Re-generate if corrupted:
   ```bash
   python src/cpg_export/add_vector_embeddings.py --force
   ```

## Joern Server Issues

### Server Won't Start

**Symptom:**
```
Connection refused on port 8080
```

**Solution:**
```powershell
# Check if port is in use
netstat -ano | findstr :8080

# Kill existing process if needed
taskkill /F /PID <pid>

# Restart Joern
powershell -ExecutionPolicy Bypass -File scripts/bootstrap_joern.ps1
```

### CPGQL Query Timeout

**Symptom:**
```
Joern query timed out
```

**Solution:**
```yaml
# Increase timeout in config.yaml
joern:
  timeout: 60  # seconds

# Or use SQL path instead
cpg:
  prefer_sql: true
```

## Memory Issues

### Out of Memory During Processing

**Symptom:**
```
MemoryError: Unable to allocate
```

**Solutions:**
```yaml
# Reduce batch sizes
retrieval:
  batch_size: 25  # Reduce from 100

# Enable incremental processing
processing:
  streaming: true
  chunk_size: 1000
```

### High Memory Usage

**Symptom:**
System becomes unresponsive

**Solutions:**
```bash
# Monitor memory usage
watch -n 1 'free -h'

# Clear caches
python -c "from src.optimization.query_cache import QueryCache; QueryCache().clear()"

# Reduce vector store in memory
# Use disk-backed ChromaDB instead
```

## Debugging

### Enable Debug Logging

```yaml
# In config.yaml
logging:
  level: DEBUG
```

Or via environment:
```bash
export LOG_LEVEL=DEBUG
python examples/demo_simple.py
```

### Check Component Status

```python
# Diagnostic script
from src.services.cpg_query_service import CPGQueryService
from src.retrieval.vector_store_real import VectorStoreReal

# Check DuckDB
cpg = CPGQueryService()
print(f"Methods: {cpg.count_methods()}")

# Check Vector Store
vs = VectorStoreReal()
print(f"QA docs: {vs.qa_collection.count()}")

# Check LLM
from src.llm.llm_interface_compat import get_llm
llm = get_llm()
print(f"LLM: {type(llm).__name__}")
```

### Generate Debug Report

```bash
python -c "
import sys
import platform

print('=== System Info ===')
print(f'Python: {sys.version}')
print(f'Platform: {platform.platform()}')

print('\n=== CUDA ===')
try:
    import torch
    print(f'PyTorch: {torch.__version__}')
    print(f'CUDA available: {torch.cuda.is_available()}')
    if torch.cuda.is_available():
        print(f'CUDA version: {torch.version.cuda}')
        print(f'GPU: {torch.cuda.get_device_name(0)}')
except ImportError:
    print('PyTorch not installed')

print('\n=== Dependencies ===')
import duckdb
print(f'DuckDB: {duckdb.__version__}')

import chromadb
print(f'ChromaDB: {chromadb.__version__}')
"
```

## Getting Help

If issues persist:

1. **Check logs** in `logs/codegraph.log`
2. **Search existing issues** in the repository
3. **Create a new issue** with:
   - Error message
   - Steps to reproduce
   - Debug report output
   - config.yaml (sensitive values removed)

## Next Steps

- [Installation](../getting-started/INSTALLATION.md) - Setup guide
- [Configuration](../getting-started/CONFIGURATION.md) - Config options
- [TUI User Guide](TUI_USER_GUIDE.md) - Usage instructions
