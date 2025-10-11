# PostgreSQL Books QA Dataset Generator

A Python-based system for parsing PostgreSQL technical books (PDF) and generating high-quality question-answer pairs using local LLM inference. This dataset is designed to evaluate a RAG-based copilot for PostgreSQL developers built on Code Property Graphs (Joern).

**Status:** 🚧 **In Development** (October 2025)

## Overview

This tool automates the creation of evaluation datasets for PostgreSQL development assistants by:
1. Extracting chapters and sections from PostgreSQL technical books (PDF)
2. Clustering content by topic
3. Mapping content to relevant PostgreSQL 17.6 source code
4. Generating contextual QA pairs using Qwen3-32B via llama.cpp

## System Requirements

- **Python:** 3.11
- **GPU:** NVIDIA RTX 3090 (24GB VRAM) with CUDA 12.4
- **Conda Environment:** `llama.cpp` (pre-configured)
- **Local LLM:** Qwen3-32B-Q4_K_M.gguf
- **PostgreSQL Source:** PostgreSQL 17.6 source code
- **PDF Books:** Technical books in `pdf/` directory

## Architecture

```
PDF Extraction → Content Chunking → Topic Clustering → Source Mapping → QA Generation → Dataset Export
     ↓                 ↓                    ↓                  ↓               ↓              ↓
  chapters      chunked_content    clustered_topics    source_mapping    qa_pairs    final_dataset.jsonl
```

## Key Differences from Hackers Pipeline

| Aspect | Hackers Pipeline | Books Pipeline |
|--------|------------------|----------------|
| **Input** | Mailing list emails | PDF books |
| **Extraction** | Email scraping + threading | PDF parsing + chunking |
| **Structure** | Thread conversations | Chapters → Sections → Paragraphs |
| **Metadata** | From, Date, Message-ID | Book title, Chapter, Page number |
| **Volume** | ~300k emails (2022-2025) | ~500-2000 pages per book |

## Pipeline Stages

### 1. **PDF Extractor** (New)
   - Extracts text from PDF books
   - Preserves chapter/section structure
   - Handles tables, code snippets
   - Tracks page numbers and metadata

### 2. **Content Chunker** (New)
   - Splits content into semantic chunks
   - Respects chapter/section boundaries
   - Creates overlapping windows for context
   - Maintains references to source

### 3. **Topic Clustering** (Reused from hackers)
   - Embeds content using sentence transformers
   - Clusters similar topics (HDBSCAN/KMeans)
   - Extracts topic keywords

### 4. **Source Context** (Reused from hackers)
   - Maps content to PG17.6 source files
   - Uses 120+ subsystem keywords
   - Identifies relevant code locations

### 5. **QA Generator** (Reused from hackers)
   - Uses Qwen3-32B for generation
   - Generates 3-5 QA pairs per cluster
   - Includes difficulty levels

### 6. **Dataset Builder** (Reused from hackers)
   - Aggregates QA pairs
   - Adds metadata and statistics
   - Exports JSONL for RAG evaluation

## Installation

```bash
# Activate environment
conda activate llama.cpp

# Install dependencies
cd C:\Users\user\pg_copilot\pg_books
pip install -r requirements.txt
```

## Usage

```bash
# Full pipeline
python main.py --all

# Step-by-step
python main.py --extract              # Extract from PDFs
python main.py --cluster              # Cluster topics
python main.py --map-source           # Map to PostgreSQL source
python main.py --generate-qa          # Generate QA pairs
python main.py --build-dataset        # Build final dataset
```

## Configuration

Key parameters in `config.py`:

### PDF Extraction
- `PDF_DIR`: Directory containing PDF books
- `CHUNK_SIZE`: Target chunk size (tokens)
- `CHUNK_OVERLAP`: Overlap between chunks
- `PRESERVE_STRUCTURE`: Keep chapter/section hierarchy

### Content Processing
- Same clustering and LLM settings as hackers pipeline
- Reuses PostgreSQL source mapping (120+ keywords)

## Output Format

Same JSONL format as hackers pipeline:

```json
{
  "question": "How does PostgreSQL implement MVCC visibility rules?",
  "answer": "PostgreSQL uses tuple versioning where each row version contains...",
  "difficulty": "advanced",
  "topics": ["mvcc", "visibility"],
  "source_files": ["src/backend/access/heap/heapam.c"],
  "source_book": "postgresql_internals-17.pdf",
  "chapter": "Chapter 5: MVCC and Vacuuming",
  "page": 127,
  "metadata": {
    "chunk_id": "ch5_s2_p3",
    "context_window": 512
  }
}
```

## Expected Output

- **Per book (500 pages)**: ~200-400 QA pairs
- **Total dataset**: Depends on number of books
- **Quality**: High-quality technical Q&A from authoritative sources

## Integration with PG Copilot

This dataset complements the hackers dataset:
- **Hackers**: Real-world developer discussions
- **Books**: Structured technical knowledge
- **Combined**: Comprehensive evaluation dataset

## Project Structure

```
pg_copilot/pg_books/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── config.py                    # Configuration
├── main.py                      # Orchestration
├── utils.py                     # Shared utilities
│
├── pdf_extractor.py             # PDF extraction
├── content_chunker.py           # Content chunking
│
├── topic_clustering.py          # Reused from hackers
├── pg_source_context.py         # Reused from hackers
├── qa_generator.py              # Reused from hackers
├── dataset_builder.py           # Reused from hackers
│
├── pdf/                         # Input PDFs
│   └── postgresql_internals-17.pdf
│
├── data/                        # Intermediate files
│   ├── extracted_content.json
│   ├── chunked_content.json
│   ├── clustered_topics.json
│   └── source_mapping.json
│
└── output/                      # Final dataset
    └── pg_copilot_books_dataset.jsonl
```

## Status

- [x] Project structure designed
- [ ] PDF extractor implementation
- [ ] Content chunker implementation
- [ ] Integration with existing modules
- [ ] Testing with postgresql_internals-17.pdf
- [ ] Full pipeline testing
