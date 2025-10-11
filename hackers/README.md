# PostgreSQL Hackers Mailing List QA Dataset Generator

A Python-based system for parsing the PostgreSQL pgsql-hackers mailing list (2022-2025) and generating high-quality question-answer pairs using local LLM inference. This dataset is designed to evaluate a RAG-based copilot for PostgreSQL developers built on Code Property Graphs (Joern).

**Status:** ✅ **Fully Tested and Production Ready** (January 2025)

## Overview

This tool automates the creation of evaluation datasets for PostgreSQL development assistants by:
1. Scraping and parsing threaded email discussions from pgsql-hackers
2. Clustering discussions by topic
3. Mapping discussions to relevant PostgreSQL 17.6 source code
4. Generating contextual QA pairs using Qwen3-32B via llama.cpp

### Testing Results

- ✅ **Sample Data Pipeline**: 54 emails → 10 threads → 1 cluster → 5 QA pairs
- ✅ **Real Data Validation**: Successfully scraped 2,665 emails from January-February 2022
- ✅ **Bug Fixes**: 5 critical bugs identified and fixed during testing
- ✅ **QA Generation**: Validated with Qwen3-32B producing high-quality technical QA pairs
- ✅ **Performance**: **10.8 emails/second** (10x improvement from 1 email/sec)
- ✅ **Checkpoint Resume**: Automatically resumes from last scraped archive

See [TESTING.md](TESTING.md) for detailed test results.

## System Requirements

- **Python:** 3.11
- **GPU:** NVIDIA RTX 3090 (24GB VRAM) with CUDA 12.4
- **Conda Environment:** `llama.cpp` (pre-configured)
- **Local LLM:** Qwen3-32B-Q4_K_M.gguf
- **PostgreSQL Source:** PostgreSQL 17.6 source code

## Architecture

```
Web Scraping → Thread Parsing → Topic Clustering → Source Mapping → QA Generation → Dataset Export
     ↓              ↓                  ↓                  ↓               ↓              ↓
raw_threads → processed_threads → clustered_topics → source_mapping → qa_pairs → final_dataset.jsonl
```

## Project Structure

```
pg_copilot/hackers/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── config.py                    # Configuration settings
├── main.py                      # Orchestration pipeline
├── utils.py                     # Shared utilities
│
├── scraper.py                   # Web scraper for mailing lists
├── thread_parser.py             # Email thread reconstruction
├── topic_clustering.py          # Discussion clustering
├── pg_source_context.py         # Source code context mapping
├── llm_interface.py             # llama.cpp integration
├── qa_generator.py              # QA pair generation
├── dataset_builder.py           # Final dataset assembly
│
├── docs/                        # Module documentation
│   ├── scraper.md
│   ├── thread_parser.md
│   ├── topic_clustering.md
│   ├── pg_source_context.md
│   ├── llm_interface.md
│   ├── qa_generator.md
│   └── dataset_builder.md
│
├── data/                        # Intermediate artifacts
│   ├── raw_threads.json
│   ├── processed_threads.json
│   ├── clustered_topics.json
│   └── topic_source_mapping.json
│
└── output/                      # Final output
    └── pg_copilot_qa_dataset.jsonl
```

## Installation

### 1. Activate Conda Environment

```bash
conda activate llama.cpp
```

### 2. Install Dependencies

```bash
cd C:\Users\user\pg_copilot\hackers
pip install -r requirements.txt
```

### 3. Verify Configuration

Edit `config.py` to ensure paths are correct:

```python
# Model paths
LLAMA_CPP_PATH = r"C:\Users\user\llama.cpp"
MODEL_PATH = r"C:\Users\user\.lmstudio\models\lmstudio-community\Qwen3-32B-GGUF\Qwen3-32B-Q4_K_M.gguf"

# PostgreSQL source
PG_SOURCE_PATH = r"C:\Users\user\postgres-REL_17_6"

# Mailing list configuration
MAILING_LIST_URL = "https://www.postgresql.org/list/pgsql-hackers"
START_YEAR = 2022
END_YEAR = 2025
```

## Usage

### Quick Start: Full Pipeline

```bash
python main.py --all
```

### Step-by-Step Execution

```bash
# Step 1: Scrape mailing list
python main.py --scrape

# Step 2: Parse threads
python main.py --parse

# Step 3: Cluster topics
python main.py --cluster

# Step 4: Map source code
python main.py --map-source

# Step 5: Generate QA pairs
python main.py --generate-qa

# Step 6: Build final dataset
python main.py --build-dataset
```

### Advanced Options

```bash
# Limit number of threads to process
python main.py --all --max-threads 100

# Adjust clustering parameters
python main.py --cluster --n-clusters 50 --min-cluster-size 5

# Configure LLM generation
python main.py --generate-qa --batch-size 4 --temperature 0.7 --max-tokens 2048
```

## Configuration

Key parameters in `config.py`:

### Scraper Settings
- `RATE_LIMIT_DELAY`: Delay between requests (default: 0.1 seconds = 10 req/sec)
- `CONCURRENT_REQUESTS`: Number of parallel message fetches (default: 5)
- `MAX_RETRIES`: Maximum retry attempts for failed requests (default: 3)
- `REQUEST_TIMEOUT`: Request timeout (default: 30 seconds)

**Performance**: ~10.8 emails/second with concurrent requests enabled

### Clustering Settings
- `EMBEDDING_MODEL`: Sentence transformer model
- `N_CLUSTERS`: Target number of topic clusters
- `MIN_CLUSTER_SIZE`: Minimum messages per cluster

### LLM Settings
- `N_GPU_LAYERS`: GPU layers to offload (-1 = all)
- `N_CTX`: Context window size (8192)
- `N_BATCH`: Batch size for processing (512)
- `TEMPERATURE`: Generation temperature (0.7)
- `TOP_P`: Nucleus sampling parameter (0.9)
- `MAX_TOKENS`: Maximum tokens per generation (2048)

### QA Generation Settings
- `QA_PAIRS_PER_THREAD`: Target QA pairs per discussion (3-5)
- `MIN_THREAD_LENGTH`: Minimum messages to consider (5)
- `INCLUDE_CODE_SNIPPETS`: Include source code in context (True)

## Output Format

### QA Dataset Schema (JSONL)

```json
{
  "question": "How does PostgreSQL's MVCC implementation handle transaction visibility?",
  "answer": "PostgreSQL uses tuple versioning where each row version contains xmin/xmax...",
  "topic": "mvcc_internals",
  "source_files": [
    "src/backend/access/heap/heapam.c",
    "src/include/access/htup_details.h"
  ],
  "thread_id": "20230415-planner-optimization",
  "relevance_score": 0.92,
  "metadata": {
    "cluster_id": 12,
    "message_count": 18,
    "date_range": "2023-04-15 to 2023-04-22"
  }
}
```

## Pipeline Stages

### 1. **Scraper** ([docs/scraper.md](docs/scraper.md))
   - Fetches mailing list archives from postgresql.org (2022-2025)
   - Concurrent request handling (5 parallel connections)
   - Automatic checkpoint/resume functionality
   - Pagination support for all day pages
   - Rate limiting: 10 requests/second
   - Performance: ~10.8 emails/second

### 2. **Thread Parser** ([docs/thread_parser.md](docs/thread_parser.md))
   - Reconstructs conversation trees
   - Cleans quoted text and signatures
   - Extracts message content and metadata

### 3. **Topic Clustering** ([docs/topic_clustering.md](docs/topic_clustering.md))
   - Embeds discussions using sentence transformers
   - Clusters similar topics (HDBSCAN/KMeans)
   - Extracts topic keywords

### 4. **Source Context** ([docs/pg_source_context.md](docs/pg_source_context.md))
   - Maps discussions to PG17.6 source files
   - Identifies relevant code locations
   - Extracts function signatures and snippets

### 5. **LLM Interface** ([docs/llm_interface.md](docs/llm_interface.md))
   - Loads Qwen3-32B via llama-cpp-python
   - Manages GPU memory (24GB RTX 3090)
   - Implements batched inference

### 6. **QA Generator** ([docs/qa_generator.md](docs/qa_generator.md))
   - Constructs prompts with discussion + source context
   - Generates 3-5 QA pairs per topic cluster
   - Validates and parses JSON responses

### 7. **Dataset Builder** ([docs/dataset_builder.md](docs/dataset_builder.md))
   - Aggregates QA pairs
   - Adds metadata and statistics
   - Exports JSONL for RAG evaluation

## Performance Estimates

### Scraping Performance (2022-2025 archives)
- **Rate**: 10.8 emails/second with concurrent requests
- **January 2022**: ~10 minutes (~2,500 messages)
- **Full year**: ~2 hours (~80,000 messages)
- **2022-2025 (4 years)**: ~7-8 hours (~300,000 messages)

### Pipeline Processing
- **Thread Parsing**: 5-10 minutes (per year)
- **Topic Clustering**: 30-60 minutes (per year)
- **Source Mapping**: 15-30 minutes (per year)
- **QA Generation**: 4-8 hours (per year, ~500-2000 QA pairs)

### Expected Output
- **Per Month**: ~80-150 QA pairs
- **Per Year**: ~1,000-1,800 QA pairs
- **Full Dataset (2022-2025)**: ~4,000-7,000 QA pairs

## Integration with PG Copilot

This dataset evaluates your RAG system built on:
- **Code Property Graph:** Generated via Joern (https://docs.joern.io/code-property-graph/)
- **Source Code:** PostgreSQL 17.6
- **Evaluation Method:** Compare copilot answers against LLM-generated ground truth

## Troubleshooting

### GPU Memory Issues
```python
# Reduce context window or batch size in config.py
N_CTX = 4096  # Instead of 8192
N_BATCH = 256  # Instead of 512
```

### Scraping Errors
```python
# Adjust rate limiting in config.py if getting 429 errors
RATE_LIMIT_DELAY = 0.2  # Slow down from 0.1 (default)
CONCURRENT_REQUESTS = 3  # Reduce from 5 (default)
```

### Resume from Checkpoint
```bash
# Scraper automatically resumes from last completed archive
python main.py --scrape  # Continues where it left off

# Start fresh (ignore checkpoint)
python main.py --scrape --no-checkpoint
```

### Clustering Quality
```bash
# Adjust cluster parameters
python main.py --cluster --min-cluster-size 10 --embedding-model all-mpnet-base-v2
```

## Contributing

This is a research project. Suggestions for improvements:
- Better thread deduplication
- Multi-language code snippet extraction
- Fine-grained source code linking (function-level)
- Quality filtering for QA pairs

## License

Research project - no formal license

## Testing & Validation

Complete testing documentation available in:
- **[TESTING.md](TESTING.md)** - Comprehensive test results and bug fixes
- **[STATUS.md](STATUS.md)** - Current project status and testing checklist
- **[QUICKSTART.md](QUICKSTART.md)** - Quick start guide with examples

### Known Issues
- **HDBSCAN on Windows**: Falls back to KMeans automatically (no action needed)
- **In-Reply-To/References**: Not always available in HTML, reconstructed from thread structure

## References

- **PostgreSQL Mailing Lists:** https://www.postgresql.org/list/pgsql-hackers/
- **Joern CPG:** https://docs.joern.io/code-property-graph/
- **llama.cpp:** https://github.com/ggerganov/llama.cpp
- **PostgreSQL 17.6:** https://www.postgresql.org/docs/17/

## Contact

Research project for PostgreSQL copilot evaluation using Code Property Graphs.
