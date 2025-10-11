# Windows 11 Quick Start Guide
## PostgreSQL Books QA Dataset Generator

**Environment:** Windows 11 + Conda + NVIDIA GPU

---

## ⚡ Quick Setup (5 Minutes)

### Step 1: Activate Conda Environment

```cmd
:: Open Command Prompt (cmd.exe) - NOT PowerShell or MINGW
conda activate base

:: Verify Python
python --version
:: Should show: Python 3.10+ or 3.11+
```

### Step 2: Navigate to Project

```cmd
cd C:\Users\user\pg_copilot\pg_books
```

### Step 3: Install Dependencies

```cmd
:: Install core dependencies
pip install -r requirements.txt

:: Install llama-cpp-python with CUDA support for GPU acceleration
set CMAKE_ARGS=-DLLAMA_CUBLAS=on
pip install llama-cpp-python --force-reinstall --no-cache-dir
```

### Step 4: Verify GPU Detection

```cmd
:: Check NVIDIA GPU
nvidia-smi

:: Should show your GPU (e.g., RTX 3090)
```

---

## 🚀 Generate Q&A Dataset (Recommended Method)

### Method 1: From Web Content (Fastest)

```cmd
:: 1. Scrape The Internals of PostgreSQL
python web_book_scraper.py

:: 2. Chunk the content
python content_chunker.py

:: 3. Generate Q&A pairs (2 per chunk)
python generate_qa_from_chunks.py --qa-per-chunk 2

:: DONE! Check: data\qa_pairs.jsonl
```

**Time:** ~30 minutes for 664 chunks → 1,328 Q&A pairs

---

## 📝 Alternative: From PDF Files

### Step 1: Prepare PDFs

```cmd
:: Place PDF files in pdf\ directory
:: Example: pdf\postgresql_internals.pdf
dir pdf
```

### Step 2: Extract Content

```cmd
python main.py --extract-pdf
:: Output: data\extracted_content.json
```

### Step 3: Chunk Content

```cmd
python main.py --chunk
:: Output: data\chunked_content.json
```

### Step 4: Generate Q&A

```cmd
:: Option A: Direct from chunks (recommended)
python generate_qa_from_chunks.py --qa-per-chunk 2

:: Option B: With clustering
python main.py --cluster --n-clusters 20
python main.py --generate-qa --max-clusters 20 --qa-per-cluster 2
```

---

## 🔧 Configuration (config.py)

### Update Model Path

```python
# Edit config.py with your model location
MODEL_PATH = r"C:\Users\user\.lmstudio\models\lmstudio-community\Qwen3-32B-GGUF\Qwen3-32B-Q4_K_M.gguf"
```

### GPU Settings

```python
# GPU acceleration (RTX 3090 - 24GB VRAM)
N_GPU_LAYERS = -1     # -1 = all layers on GPU
N_CTX = 8192          # Context window
N_BATCH = 512         # Batch size
N_THREADS = 8         # CPU threads
```

### Reduce VRAM Usage (if needed)

```python
# If OOM errors occur
N_GPU_LAYERS = 35     # Reduce layers on GPU
N_CTX = 4096          # Reduce context window
N_BATCH = 256         # Reduce batch size
```

---

## 📊 Check Results

### View Q&A Pairs

```cmd
:: Count Q&A pairs
python -c "import jsonlines; pairs = list(jsonlines.open('data/qa_pairs.jsonl')); print(f'Total: {len(pairs)} Q&A pairs')"

:: View first Q&A pair
python -c "import jsonlines; print(list(jsonlines.open('data/qa_pairs.jsonl'))[0])"
```

### View Statistics

```cmd
python -c "
import jsonlines
pairs = list(jsonlines.open('data/qa_pairs.jsonl'))
print(f'Total Q&A pairs: {len(pairs)}')

# Difficulty distribution
diff_counts = {}
for p in pairs:
    d = p.get('difficulty', 'unknown')
    diff_counts[d] = diff_counts.get(d, 0) + 1

print('\nDifficulty Distribution:')
for diff, count in sorted(diff_counts.items()):
    pct = count / len(pairs) * 100
    print(f'  {diff:12s}: {count:4d} ({pct:5.1f}%%)')
"
```

---

## 🐛 Troubleshooting

### Issue: "ImportError: DLL load failed"

**Cause:** CUDA libraries not found

**Solution:**
```cmd
:: Verify CUDA installation
nvcc --version

:: Add CUDA to PATH (if needed)
set PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\bin;%PATH%

:: Reinstall llama-cpp-python
pip uninstall llama-cpp-python -y
set CMAKE_ARGS=-DLLAMA_CUBLAS=on
pip install llama-cpp-python --no-cache-dir
```

### Issue: "CUDA out of memory"

**Cause:** Model too large for GPU

**Solution 1 - Reduce GPU layers:**
```python
# Edit config.py
N_GPU_LAYERS = 35  # Instead of -1
```

**Solution 2 - Use smaller model:**
```python
# Use 7B or 14B model instead of 32B
MODEL_PATH = r"C:\path\to\smaller_model.gguf"
```

### Issue: "Generation very slow (CPU mode)"

**Symptom:** ~5+ minutes per Q&A pair

**Check:**
```cmd
:: Run a test and look for:
:: "llama_model_loader: - tensor  ... | GPU"
:: If you see "CPU" instead of "GPU", GPU is not active

python -c "
import sys
sys.path.insert(0, '.')
from llm_interface import LLMInterface
llm = LLMInterface()
llm.load_model()
# Check output for GPU usage
"
```

**Solution:**
```python
# Verify config.py
N_GPU_LAYERS = -1  # Must be -1 or > 0
```

### Issue: "Clustering produces 1-2 clusters only"

**Cause:** Embeddings too similar

**Solution:** Skip clustering, use direct generation:
```cmd
python generate_qa_from_chunks.py --qa-per-chunk 2
```

### Issue: Command not found in PowerShell

**Cause:** Using PowerShell instead of cmd.exe

**Solution:** Use Command Prompt (cmd.exe):
```
1. Press Win+R
2. Type: cmd
3. Press Enter
4. cd C:\Users\user\pg_copilot\pg_books
```

---

## 📈 Performance Benchmarks

**Hardware:** RTX 3090 (24GB VRAM)
**Model:** Qwen3-32B-Q4_K_M

| Task | Time | Notes |
|------|------|-------|
| Web scraping | 5 min | 664 chunks |
| Content chunking | 1 min | Semantic splitting |
| Clustering (optional) | 2 min | 20 clusters |
| Q&A generation | ~30 sec/pair | GPU accelerated |
| **Total (1,328 pairs)** | **~11 hours** | 2 pairs × 664 chunks |

**Optimization Tips:**
```cmd
:: Test mode (5 chunks only, ~2.5 minutes)
python generate_qa_from_chunks.py --test --qa-per-chunk 2

:: Limited run (100 chunks, ~50 minutes)
python generate_qa_from_chunks.py --max-chunks 100 --qa-per-chunk 2

:: Single pair per chunk (664 pairs, ~5.5 hours)
python generate_qa_from_chunks.py --qa-per-chunk 1
```

---

## 🎯 Common Workflows

### Workflow 1: Quick Test (2 minutes)

```cmd
:: Test with 5 chunks
python generate_qa_from_chunks.py --test --qa-per-chunk 2

:: Check results
type data\qa_pairs.jsonl
```

### Workflow 2: Production Run (11 hours)

```cmd
:: Full dataset generation
python web_book_scraper.py
python content_chunker.py
python generate_qa_from_chunks.py --qa-per-chunk 2

:: Monitor progress
type pipeline.log
```

### Workflow 3: Custom Configuration

```cmd
:: Edit config.py with custom settings
notepad config.py

:: Change:
:: - CHUNK_SIZE = 500 (smaller chunks)
:: - QA_PAIRS_PER_CLUSTER = 3 (more Q&A)
:: - TEMPERATURE = 0.8 (more creative)

:: Run pipeline
python content_chunker.py
python generate_qa_from_chunks.py --qa-per-chunk 3
```

---

## 📂 File Locations (Windows Paths)

### Input Files
```
C:\Users\user\pg_copilot\pg_books\pdf\        ← Place PDFs here
C:\Users\user\postgres-REL_17_6\              ← PostgreSQL source
```

### Output Files
```
C:\Users\user\pg_copilot\pg_books\data\qa_pairs.jsonl          ← Main dataset
C:\Users\user\pg_copilot\pg_books\data\chunked_content.json    ← Processed chunks
C:\Users\user\pg_copilot\pg_books\pipeline.log                 ← Execution log
```

### Model Files
```
C:\Users\user\.lmstudio\models\lmstudio-community\Qwen3-32B-GGUF\Qwen3-32B-Q4_K_M.gguf
```

---

## 🔗 Integration with RAG-CPGQL

Once Q&A dataset is generated, use it for RAG experiments:

```cmd
:: Navigate to RAG project
cd C:\Users\user\pg_copilot\rag_cpgql

:: Prepare data (uses pg_books\data\qa_pairs.jsonl)
python prepare_data.py

:: Run experiments
cd experiments
python run_experiment.py --model finetuned --limit 5
```

---

## 📝 Environment Variables (Optional)

```cmd
:: Set CUDA device (if multiple GPUs)
set CUDA_VISIBLE_DEVICES=0

:: Increase CUDA memory
set CUDA_LAUNCH_BLOCKING=1

:: Verify
echo %CUDA_VISIBLE_DEVICES%
```

---

## 🆘 Support Commands

### Check System Info

```cmd
:: Python version
python --version

:: CUDA version
nvcc --version

:: GPU status
nvidia-smi

:: Conda environment
conda info --envs

:: Installed packages
pip list | findstr llama
pip list | findstr torch
```

### Clean Restart

```cmd
:: Remove cached files
del /Q data\embeddings_cache.npy
del /Q data\qa_pairs.jsonl

:: Remove logs
del /Q *.log

:: Regenerate
python web_book_scraper.py
python content_chunker.py
python generate_qa_from_chunks.py --qa-per-chunk 2
```

---

## 📚 Next Steps

1. ✅ **Generate dataset** (current guide)
2. 📊 **Analyze quality** - Review `data\qa_pairs.jsonl`
3. 🔬 **Run RAG experiments** - Use dataset in RAG-CPGQL system
4. 📈 **Optimize prompts** - Adjust templates in `qa_generator.py`
5. 🚀 **Scale up** - Process more sources (PDFs, docs)

---

## 💡 Pro Tips

1. **Monitor GPU usage** while running:
   ```cmd
   :: In another terminal
   nvidia-smi -l 1
   ```

2. **Run overnight** for full dataset:
   ```cmd
   python generate_qa_from_chunks.py --qa-per-chunk 2 > output.log 2>&1
   ```

3. **Backup important files**:
   ```cmd
   copy data\qa_pairs.jsonl data\qa_pairs_backup.jsonl
   ```

4. **Check logs** for errors:
   ```cmd
   findstr /i "error" pipeline.log
   findstr /i "failed" pipeline.log
   ```

---

**Last Updated:** 2025-10-03
**Platform:** Windows 11 + Conda + NVIDIA CUDA
**Python:** 3.10+
**GPU:** NVIDIA RTX 3090 (24GB VRAM)
