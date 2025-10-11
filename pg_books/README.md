# PostgreSQL Books QA Dataset Generator

**Windows 11 | Conda Environment | GPU-Accelerated**

Automated pipeline for generating high-quality question-answer pairs from PostgreSQL technical books and online documentation. This system extracts content, chunks it semantically, and generates technical Q&A pairs using local LLMs.

## 📊 Current Dataset

- **1,328 Q&A pairs** generated from PostgreSQL technical books
- **664 content chunks** from "The Internals of PostgreSQL" and other sources
- **3 difficulty levels:** beginner, intermediate, advanced
- **Topics covered:** MVCC, transactions, indexing, storage, executor, partitioning, and more

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 1: Content Extraction                                     │
│ PDF/Web → Raw Text + Metadata                                   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 2: Semantic Chunking                                      │
│ Raw Text → Chunked Content (1000 tokens/chunk, 200 overlap)    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 3: Topic Clustering (Optional)                            │
│ Chunks → Semantic Clusters via Embeddings                       │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 4: Source Code Mapping                                    │
│ Topics → PostgreSQL Source Files (via keyword matching)         │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 5: QA Generation                                          │
│ LLM generates Q&A pairs with source code context               │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ OUTPUT: qa_pairs.jsonl (1,328 pairs)                           │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start (Windows 11 + Conda)

### Prerequisites

1. **Conda environment** with Python 3.10+
2. **NVIDIA GPU** with CUDA support (for llama-cpp-python)
3. **24GB+ VRAM** (for 32B model)
4. **PostgreSQL source code** at `C:\Users\user\postgres-REL_17_6`

### Installation

```cmd
:: 1. Activate conda environment
conda activate your_env_name

:: 2. Navigate to project directory
cd C:\Users\user\pg_copilot\pg_books

:: 3. Install dependencies
pip install -r requirements.txt

:: 4. Install llama-cpp-python with CUDA support (Windows)
set CMAKE_ARGS=-DLLAMA_CUBLAS=on
pip install llama-cpp-python --force-reinstall --no-cache-dir
```

### Configuration

Edit `config.py` to set:

```python
# LLM Model Path (32B Qwen model recommended)
MODEL_PATH = r"C:\Users\user\.lmstudio\models\lmstudio-community\Qwen3-32B-GGUF\Qwen3-32B-Q4_K_M.gguf"

# PostgreSQL Source
PG_SOURCE_PATH = r"C:\Users\user\postgres-REL_17_6"
PG_VERSION = "17.6"

# Generation settings
QA_PAIRS_PER_CLUSTER = 2  # Q&A pairs per chunk/cluster
```

## 📖 Usage

### Method 1: Extract from Web (Recommended)

```cmd
:: 1. Scrape "The Internals of PostgreSQL" website
python web_book_scraper.py

:: 2. Chunk the content
python content_chunker.py

:: 3. Generate Q&A pairs directly from chunks (no clustering)
::    Dynamic QA pairs: 2 for long chunks, 1 for medium/short
python generate_qa_from_chunks.py

:: Result: data/qa_pairs.jsonl
```

### Method 2: Extract from PDF

```cmd
:: 1. Place PDFs in pdf/ directory

:: 2. Extract content from PDFs
python main.py --extract-pdf

:: 3. Chunk the content
python main.py --chunk

:: 4. Cluster into topics
python main.py --cluster --n-clusters 20

:: 5. Map to PostgreSQL source code
python main.py --map-source

:: 6. Generate Q&A pairs
python main.py --generate-qa --max-clusters 20 --qa-per-cluster 2
```

### Method 3: Full Pipeline (All-in-One)

```cmd
:: Run complete pipeline
python main.py --all --n-clusters 20 --qa-per-cluster 2
```

## 📁 Project Structure

```
pg_books/
├── config.py                      # Configuration (paths, LLM settings)
├── main.py                        # Main pipeline orchestrator
├── requirements.txt               # Python dependencies
│
├── Content Extraction/
│   ├── pdf_extractor.py          # PDF text extraction
│   └── web_book_scraper.py       # Web scraping (The Internals of PostgreSQL)
│
├── Processing/
│   ├── content_chunker.py        # Semantic text chunking
│   ├── topic_clustering.py       # HDBSCAN/KMeans clustering
│   └── pg_source_context.py      # Map topics to PG source files
│
├── Generation/
│   ├── llm_interface.py          # llama-cpp-python wrapper (GPU)
│   ├── qa_generator.py           # Q&A generation with prompts
│   └── generate_qa_from_chunks.py # Direct chunk→Q&A (bypass clustering)
│
├── Utilities/
│   ├── utils.py                  # Helper functions
│   └── dataset_builder.py        # Final dataset assembly
│
├── data/                         # Generated data
│   ├── extracted_content.json    # Raw extracted text
│   ├── chunked_content.json      # Chunked content (664 chunks)
│   ├── clustered_topics.json     # Topic clusters (optional)
│   ├── source_mapping.json       # Topic→PG source mapping
│   ├── qa_pairs.jsonl           # Final Q&A dataset (1,328 pairs)
│   └── embeddings_cache.npy      # Cached embeddings
│
├── pdf/                          # Input PDFs (place here)
└── output/                       # Final dataset + reports
```

## 🔧 Key Components

### 1. Web Scraper (`web_book_scraper.py`)

Extracts content from "The Internals of PostgreSQL" website:

```cmd
python web_book_scraper.py
```

**Output:** `data/web_the_internals_of_postgresql.json`
- Chapters, sections, paragraphs
- Code blocks preserved
- Hierarchical structure maintained

### 2. Content Chunker (`content_chunker.py`)

Splits text into semantic chunks:

```python
# Chunking strategy
CHUNK_SIZE = 1000           # Target tokens per chunk
CHUNK_OVERLAP = 200         # Overlap between chunks
CHUNK_METHOD = 'semantic'   # Respects paragraph boundaries
```

**Usage:**
```cmd
python content_chunker.py
```

**Output:** `data/chunked_content.json` (664 chunks)

### 3. Topic Clustering (`topic_clustering.py`)

Groups similar chunks (optional step):

```cmd
python main.py --cluster --n-clusters 20
```

**Methods:**
- `HDBSCAN` - Auto-detects number of clusters
- `KMeans` - Fixed number of clusters

**Output:** `data/clustered_topics.json`

### 4. Source Code Mapper (`pg_source_context.py`)

Maps topics to PostgreSQL source files using keyword matching:

```python
KEYWORD_TO_COMPONENT = {
    'mvcc': ['access/heap', 'access/transam', 'utils/time'],
    'btree': ['access/nbtree'],
    'executor': ['executor', 'nodeAppend', 'nodeModifyTable'],
    # ... 120+ keyword mappings
}
```

**Output:** `data/source_mapping.json`

### 5. Q&A Generator (`qa_generator.py`)

Generates Q&A pairs using local LLM:

**Direct from Chunks (Recommended):**
```cmd
:: Dynamic QA pairs based on chunk length
python generate_qa_from_chunks.py

:: Resume if interrupted (uses checkpoint)
python generate_qa_from_chunks.py --resume
```

**QA Pairs Strategy (Dynamic):**
- **Long chunks (≥400 tokens):** 2 QA pairs
- **Medium chunks (150-400 tokens):** 1 QA pair
- **Short chunks (50-150 tokens):** 1 QA pair
- **Very short (<50 tokens):** Skipped

**From Clusters:**
```cmd
python main.py --generate-qa --max-clusters 20 --qa-per-cluster 2
```

**Prompt Template:**
```
You are a PostgreSQL internals expert. Generate {n} technical Q&A pairs.

Content: {chunk_text}
Source Files: {source_files}
Chapter: {chapter_name}

Generate questions covering:
1. Technical details
2. Implementation specifics
3. Use cases and best practices

Format: JSON with question, answer, difficulty, topics
```

**Checkpoint System:**
- Progress saved to `data/qa_checkpoint.jsonl` after each chunk
- Use `--resume` to continue from last checkpoint
- Safe for long-running processes (days)

## 📊 Generated Q&A Format

```json
{
  "question": "How does PostgreSQL validate the validity of a transaction ID (XID) during visibility checks?",
  "answer": "PostgreSQL validates transaction IDs using macros and functions defined in 'transam.h' and 'xact.c'. The `TransactionIdIsValid()` macro checks if an XID is non-zero. During visibility checks in functions like `HeapTupleSatisfiesMVCC()`, PostgreSQL compares XIDs against snapshot boundaries...",
  "difficulty": "intermediate",
  "topics": ["transaction_management", "mvcc"],
  "cluster_id": 0,
  "cluster_label": "chunk_0",
  "source_files": [],
  "thread_ids": ["chunk_0"],
  "generated_at": "2025-10-02T19:05:20.618829"
}
```

## 🎯 Command Reference

### Web Scraping
```cmd
:: Scrape The Internals of PostgreSQL
python web_book_scraper.py

:: Output: data/web_the_internals_of_postgresql.json
```

### Content Processing
```cmd
:: Chunk content
python content_chunker.py

:: Cluster topics (optional)
python main.py --cluster --n-clusters 20

:: Map to PostgreSQL source
python main.py --map-source
```

### Q&A Generation
```cmd
:: Generate directly from chunks (RECOMMENDED - bypasses clustering issues)
:: Uses dynamic QA pairs count based on chunk length
python generate_qa_from_chunks.py

:: Resume from checkpoint if interrupted
python generate_qa_from_chunks.py --resume

:: Generate from clusters
python main.py --generate-qa --max-clusters 20 --qa-per-cluster 2

:: Test mode (5 chunks only)
python generate_qa_from_chunks.py --test

:: Limit processing
python generate_qa_from_chunks.py --max-chunks 100
```

### Full Pipeline
```cmd
:: Complete pipeline
python main.py --all --n-clusters 20 --qa-per-cluster 2
```

## 🔍 Troubleshooting

### Issue: Model OOM (Out of Memory)

**Solution:** Reduce context size or GPU layers in `config.py`:
```python
N_CTX = 4096  # Reduce from 8192
N_GPU_LAYERS = 35  # Reduce from -1 (all layers)
```

### Issue: Clustering produces too few clusters

**Symptom:** All chunks collapse into 1-2 clusters

**Solution:** Use direct chunk→Q&A generation:
```cmd
python generate_qa_from_chunks.py --qa-per-chunk 2
```

This bypasses clustering entirely.

### Issue: llama-cpp-python import error

**Solution:** Reinstall with CUDA support:
```cmd
pip uninstall llama-cpp-python -y
set CMAKE_ARGS=-DLLAMA_CUBLAS=on
pip install llama-cpp-python --no-cache-dir
```

### Issue: GPU not detected

**Solution:** Verify CUDA installation:
```cmd
nvidia-smi
nvcc --version

:: Set environment variable
set CUDA_VISIBLE_DEVICES=0
```

### Issue: Slow generation (CPU mode)

**Check:** Verify GPU is being used:
```python
# In config.py
N_GPU_LAYERS = -1  # -1 = all layers on GPU
```

Should see: `llama_model_loader: - kv   0: general.architecture str = qwen2`
with GPU device info.

## 📈 Performance

**Hardware:** RTX 3090 (24GB VRAM)
**Model:** Qwen3-32B-Q4_K_M

- **Extraction:** ~5 minutes for full website
- **Chunking:** ~1 minute for 664 chunks
- **Clustering:** ~2 minutes (optional)
- **Q&A Generation:** ~30 seconds per Q&A pair
  - **Dynamic generation:** Varies by chunk length
  - **Estimated total:** ~8-12 hours for full dataset
  - **Checkpoint saves:** Every chunk (resume-safe)

**Optimization:**
- Use `--max-chunks` to limit processing
- Use `--resume` to continue interrupted runs
- Use test mode: `--test` flag

## 📊 Dataset Statistics

```cmd
:: View Q&A dataset stats
python -c "
import jsonlines
import json

with jsonlines.open('data/qa_pairs.jsonl') as f:
    qa_pairs = list(f)

print(f'Total Q&A pairs: {len(qa_pairs)}')

difficulties = {}
topics_set = set()

for qa in qa_pairs:
    diff = qa.get('difficulty', 'unknown')
    difficulties[diff] = difficulties.get(diff, 0) + 1
    for topic in qa.get('topics', []):
        topics_set.add(topic)

print(f'\nDifficulty distribution:')
for diff, count in sorted(difficulties.items()):
    print(f'  {diff}: {count}')

print(f'\nUnique topics: {len(topics_set)}')
print(f'Topics: {sorted(topics_set)[:10]}...')
"
```

## 🔗 Integration with RAG-CPGQL

The generated Q&A dataset is used by the RAG-CPGQL system:

```cmd
cd C:\Users\user\pg_copilot\rag_cpgql

:: Prepare data (uses pg_books/data/qa_pairs.jsonl)
python prepare_data.py

:: Run experiments
cd experiments
python run_experiment.py --model both --limit 5
```

## 📝 Configuration Reference

### Key Settings in `config.py`

```python
# ============================================================================
# PATHS
# ============================================================================
MODEL_PATH = r"C:\Users\user\.lmstudio\models\...\Qwen3-32B-Q4_K_M.gguf"
PG_SOURCE_PATH = r"C:\Users\user\postgres-REL_17_6"

# ============================================================================
# LLM SETTINGS (RTX 3090 - 24GB VRAM)
# ============================================================================
N_CTX = 8192          # Context window
N_GPU_LAYERS = -1     # All layers on GPU
N_BATCH = 512         # Batch size
TEMPERATURE = 0.7     # Sampling temperature
MAX_TOKENS = 2048     # Max tokens per generation

# ============================================================================
# CHUNKING
# ============================================================================
CHUNK_SIZE = 1000           # Target tokens per chunk
CHUNK_OVERLAP = 200         # Overlap between chunks
CHUNK_METHOD = 'semantic'   # Preserve paragraph boundaries

# ============================================================================
# CLUSTERING (Optional)
# ============================================================================
CLUSTERING_METHOD = 'kmeans'  # or 'hdbscan'
N_CLUSTERS = 300              # For KMeans
MIN_CLUSTER_SIZE = 1          # For HDBSCAN

# ============================================================================
# QA GENERATION
# ============================================================================
QA_PAIRS_PER_CLUSTER = 2      # Q&A pairs per chunk/cluster
MIN_CHUNK_LENGTH = 200        # Minimum tokens to use
MAX_CONTEXT_LENGTH = 4000     # Maximum tokens in context
GENERATION_TEMPERATURE = 0.7  # Temperature for generation
```

## 📄 Output Files

### Primary Outputs
- `data/qa_pairs.jsonl` - **Main Q&A dataset (1,328 pairs)**
- `data/chunked_content.json` - Processed chunks (664)
- `data/source_mapping.json` - Topic→source file mappings

### Intermediate Files
- `data/extracted_content.json` - Raw extracted text
- `data/clustered_topics.json` - Topic clusters (if clustering used)
- `data/embeddings_cache.npy` - Cached embeddings (speeds up re-runs)
- `data/file_index.json` - PostgreSQL source file index

### Logs
- `pipeline.log` - Complete pipeline execution log
- `qa_generation.log` - Q&A generation details
- `full_qa_generation.log` - Chunk→Q&A generation log

## 🎓 Example: Generate Custom Dataset

```cmd
:: 1. Scrape custom source (modify web_book_scraper.py)
python web_book_scraper.py

:: 2. Chunk with custom settings
:: Edit config.py: CHUNK_SIZE = 500, CHUNK_OVERLAP = 100
python content_chunker.py

:: 3. Generate 3 Q&A pairs per chunk
python generate_qa_from_chunks.py --qa-per-chunk 3

:: Result: Higher quantity, possibly lower quality per chunk
```

## 📚 Resources

- **PostgreSQL Source:** https://github.com/postgres/postgres
- **The Internals of PostgreSQL:** https://www.interdb.jp/pg/
- **llama-cpp-python:** https://github.com/abetlen/llama-cpp-python
- **Qwen Models:** https://huggingface.co/Qwen

## 🐛 Known Issues

1. **Clustering Collapse:** Embeddings too similar → Use `generate_qa_from_chunks.py` instead
2. **GPU Memory Spikes:** Reduce `N_CTX` or `N_BATCH` if OOM occurs
3. **Slow Generation:** Normal for 32B models (~30s per Q&A pair)

## 🚀 Future Improvements

- [ ] Support for multiple PDF sources
- [ ] Parallel Q&A generation (multi-GPU)
- [ ] Fine-tuning prompt templates per difficulty level
- [ ] Automatic quality scoring and filtering
- [ ] Integration with more PostgreSQL documentation sources

## 📊 Citation

If you use this dataset in research, please cite:

```bibtex
@dataset{pg_books_qa_2025,
  title={PostgreSQL Books QA Dataset},
  author={[Your Name]},
  year={2025},
  publisher={GitHub},
  howpublished={\url{https://github.com/yourusername/pg_copilot}}
}
```

---

**Generated Q&A Pairs:** 1,328
**Source Content:** The Internals of PostgreSQL + Technical Books
**PostgreSQL Version:** 17.6
**Last Updated:** 2025-10-03
