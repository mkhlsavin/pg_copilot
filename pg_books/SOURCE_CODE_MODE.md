# Source Code Extraction Mode

**NEW: Generate Q&A pairs from PostgreSQL source code documentation**

This mode extracts README files and multi-line comments from PostgreSQL C source code and generates Q&A pairs from them.

---

## Quick Start

### Extract from PostgreSQL Source Code

```cmd
:: 1. Extract READMEs and C comments (test with 10 files)
python pg_source_code_extractor.py --max-c-files 10

:: 2. Chunk the content
python content_chunker.py data\pg_source_content.json

:: 3. Generate Q&A pairs (dynamic: 1-2 per chunk based on length)
python generate_qa_from_chunks.py
```

**Time:** ~2 minutes for test (10 C files), ~30 minutes for full extraction

---

## What Gets Extracted

### README Files
All README files in the PostgreSQL source tree:
- `src\backend\access\brin\README` - BRIN index documentation
- `src\backend\replication\README` - Replication system docs
- `src\backend\optimizer\README` - Query optimizer design
- And 90+ more...

### C Multi-Line Comments
Documentation comments from `.c` source files:
```c
/*
 * brin.c
 *     Implementation of BRIN indexes for Postgres
 *
 * See src/backend/access/brin/README for details.
 *
 * Portions Copyright (c) 1996-2024, PostgreSQL Global Development Group
 */
```

Only comments **longer than 50 characters** are extracted (filters out trivial comments).

---

## Usage

### Basic Usage (All Files)

```cmd
:: Extract all README files + all C comments
python pg_source_code_extractor.py

:: Output:
::   data\pg_source_extracted.json       - Raw extraction data
::   data\pg_source_content.json         - Content items for chunking
```

### Limited Extraction (Testing)

```cmd
:: Extract README files + comments from first 10 C files only
python pg_source_code_extractor.py --max-c-files 10

:: Output:
::   data\pg_source_extracted.json       - 94 READMEs + ~500-600 comments
::   data\pg_source_content.json         - Ready for chunking
```

### Custom Paths

```cmd
:: Use different PostgreSQL source location
python pg_source_code_extractor.py ^
    --source-root C:\custom\path\to\postgres\src ^
    --output data\custom_extract.json ^
    --output-content data\custom_content.json
```

---

## Command-Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--source-root` | `C:\Users\user\postgres-REL_17_6\src` | PostgreSQL source root directory |
| `--max-c-files` | None (all files) | Limit number of C files to process |
| `--output` | `data/pg_source_extracted.json` | Output file for raw extraction |
| `--output-content` | `data/pg_source_content.json` | Output file for content items |

---

## Complete Pipeline

### Step 1: Extract Source Code Documentation

```cmd
:: Option A: Full extraction (all C files - takes ~5-10 minutes)
python pg_source_code_extractor.py

:: Option B: Limited extraction (10 files - takes ~1 minute)
python pg_source_code_extractor.py --max-c-files 10
```

**Output:**
```
EXTRACTION STATISTICS
============================================================
Source root:        C:\Users\user\postgres-REL_17_6\src
README files:       94
C comments:         562 (from 10 files) or ~15,000+ (from all files)
Total items:        656 (10 files) or ~15,000+ (all files)
```

### Step 2: Chunk Content

```cmd
python content_chunker.py data\pg_source_content.json
```

**Output:**
```
Chunking Statistics:
============================================================
total_chunks: 796 (for 10 files)
avg_tokens: 241
min_tokens: 8
max_tokens: 1008
```

### Step 3: Generate Q&A Pairs

```cmd
:: Generate Q&A pairs (dynamic: 1-2 per chunk based on token count)
python generate_qa_from_chunks.py

:: Resume if interrupted (uses checkpoint system)
python generate_qa_from_chunks.py --resume

:: Or test with just 5 chunks
python generate_qa_from_chunks.py --test
```

**QA Pairs Strategy:**
- Long chunks (≥400 tokens): 2 QA pairs
- Medium chunks (150-400 tokens): 1 QA pair
- Short chunks (50-150 tokens): 1 QA pair
- Very short (<50 tokens): Skipped

**Output:**
```
data\qa_pairs.jsonl - Generated Q&A pairs from source code
data\qa_checkpoint.jsonl - Checkpoint file (for resume)
```

---

## Data Format

### Extracted Content Items

```json
{
  "title": "README: backend\\access\\brin",
  "url": "backend\\access\\brin\\README",
  "content": "Block Range Indexes (BRIN)\n==========================\n...",
  "source_type": "README",
  "metadata": {
    "file_path": "C:\\Users\\user\\postgres-REL_17_6\\src\\backend\\access\\brin\\README",
    "directory": "backend\\access\\brin"
  }
}
```

```json
{
  "title": "Comment from brin.c:53",
  "url": "backend\\access\\brin\\brin.c:53",
  "content": "brinbuild() -- build a new BRIN index.\n\nWe use three BulkWriteState...",
  "source_type": "C_COMMENT",
  "metadata": {
    "file_path": "C:\\Users\\user\\postgres-REL_17_6\\src\\backend\\access\\brin\\brin.c",
    "relative_path": "backend\\access\\brin\\brin.c",
    "line_start": 53
  }
}
```

### Chunked Content

```json
{
  "source_type": "README",
  "text": "Block Range Indexes (BRIN)\n==========================\n...",
  "chunk_index": 0,
  "token_count": 973,
  "metadata": {
    "file_path": "C:\\Users\\user\\postgres-REL_17_6\\src\\backend\\access\\brin\\README",
    "directory": "backend\\access\\brin"
  }
}
```

### Generated Q&A Pairs

```json
{
  "question": "What is the purpose of BRIN indexes in PostgreSQL?",
  "answer": "BRIN indexes enable very fast scanning of extremely large tables by keeping track of summarizing values...",
  "difficulty": "intermediate",
  "topics": ["indexes", "brin", "performance"],
  "source_files": ["backend/access/brin"],
  "source_type": "README"
}
```

---

## Performance Benchmarks

**Hardware:** RTX 3090 (24GB VRAM)
**Model:** Qwen3-32B-Q4_K_M

| Task | Time (10 files) | Time (all ~3000 files) |
|------|-----------------|------------------------|
| Extract READMEs | <1 sec | ~5 sec |
| Extract C comments | ~1 sec | ~10 min |
| Chunk content | <1 sec | ~5 sec |
| Generate Q&A (2/chunk) | ~5 min | ~8-10 hours |
| **Total** | **~6 min** | **~10-12 hours** |

---

## Combining with Web Content

You can combine source code Q&A pairs with web-scraped content:

```cmd
:: 1. Generate from web content (existing workflow)
python web_book_scraper.py
python content_chunker.py
python generate_qa_from_chunks.py

:: 2. Generate from source code
python pg_source_code_extractor.py --max-c-files 50
python content_chunker.py data\pg_source_content.json
python generate_qa_from_chunks.py

:: 3. Combine datasets
python -c "
import jsonlines

qa_pairs = list(jsonlines.open('data/qa_pairs.jsonl'))

print(f'Total Q&A pairs: {len(qa_pairs)}')

# Separate by source type if needed
web_qa = [qa for qa in qa_pairs if qa.get('source_type') == 'web']
code_qa = [qa for qa in qa_pairs if qa.get('source_type') in ('README', 'C_COMMENT')]

print(f'Web content: {len(web_qa)}')
print(f'Source code: {len(code_qa)}')
"
```

---

## What Makes Good Q&A Pairs?

### From README Files
- **Design documentation** - Architecture, algorithms, data structures
- **Implementation notes** - How features work internally
- **Technical specifications** - File formats, protocols, interfaces

Example README topics:
- BRIN index structure and algorithms
- WAL (Write-Ahead Logging) design
- Vacuum and autovacuum mechanics
- Query optimizer strategies

### From C Comments
- **Function documentation** - Purpose, parameters, return values
- **Algorithm explanations** - Step-by-step implementation details
- **Edge cases and caveats** - Special handling, limitations
- **Historical context** - Why code was written a certain way

---

## Filtering and Quality

### Built-in Filtering
The extractor automatically filters out:
- Comments shorter than 50 characters (trivial comments)
- Copyright headers (detected and skipped)
- License text (standard boilerplate)
- Simple variable declarations

### Manual Quality Improvement

If you want higher quality Q&A pairs:

1. **Increase comment length threshold:**
   ```python
   # In pg_source_code_extractor.py, line ~110
   if len(comment_text) < 100:  # Increase from 50 to 100
       continue
   ```

2. **Filter by file type:**
   ```python
   # Only process core backend files
   c_files = [f for f in self.source_root.rglob('*.c')
              if 'backend' in str(f)]
   ```

3. **Filter by directory:**
   ```cmd
   :: Extract only from specific directories
   python pg_source_code_extractor.py --source-root C:\Users\user\postgres-REL_17_6\src\backend\access
   ```

---

## Troubleshooting

### Issue: "Source root does not exist"

**Cause:** PostgreSQL source path is incorrect

**Solution:**
```cmd
:: Check your PostgreSQL source location
dir C:\Users\user\postgres-REL_17_6\src

:: Use correct path
python pg_source_code_extractor.py --source-root C:\path\to\your\postgres\src
```

### Issue: Too many comments extracted

**Cause:** Extracting from all C files generates thousands of comments

**Solution:**
```cmd
:: Limit to specific number of files for testing
python pg_source_code_extractor.py --max-c-files 20

:: Or extract only from specific subdirectory
python pg_source_code_extractor.py --source-root C:\Users\user\postgres-REL_17_6\src\backend\optimizer
```

### Issue: Low quality Q&A pairs

**Cause:** Some C comments are too technical or context-dependent

**Solution:**
1. Use higher comment length threshold (edit `pg_source_code_extractor.py`)
2. Focus on README files only:
   ```cmd
   python pg_source_code_extractor.py --max-c-files 0  # No C files, READMEs only
   ```
3. Manually review and filter `data/qa_pairs.jsonl`

---

## Advanced: Custom Extraction

### Extract Only READMEs (No C Comments)

```python
from pg_source_code_extractor import PgSourceCodeExtractor

extractor = PgSourceCodeExtractor(r'C:\Users\user\postgres-REL_17_6\src')
readme_files = extractor.extract_readme_files()

# Convert to content items
content_items = extractor.convert_to_content_items({
    'readme_files': readme_files,
    'c_comments': []
})

import json
with open('data/readme_only.json', 'w') as f:
    json.dump(content_items, f, indent=2)
```

### Extract from Specific Files

```python
import re
from pathlib import Path

# Custom filter: only extract from files matching pattern
c_files = list(Path(r'C:\Users\user\postgres-REL_17_6\src').rglob('*.c'))
filtered_files = [f for f in c_files if re.search(r'(vacuum|autovacuum|heap)', str(f))]

print(f'Filtered to {len(filtered_files)} files')
# ... extract from filtered_files
```

---

## Integration with Existing Workflows

This mode integrates seamlessly with existing pg_books workflows:

| Workflow | Command | Output |
|----------|---------|--------|
| **Web content** | `python web_book_scraper.py` | Web documentation Q&A |
| **PDF content** | `python main.py --extract-pdf` | PDF book Q&A |
| **Source code** | `python pg_source_code_extractor.py` | Source code docs Q&A |

All three produce compatible `qa_pairs.jsonl` format for use with:
- RAG-CPGQL system
- Fine-tuning datasets
- Question-answering systems

---

## Next Steps

1. ✅ **Extract source code docs** (this guide)
2. 📊 **Analyze quality** - Review generated Q&A pairs
3. 🔬 **Use in RAG experiments** - Test with RAG-CPGQL system
4. 📈 **Combine datasets** - Merge with web/PDF content
5. 🚀 **Fine-tune models** - Use as training data

---

**Last Updated:** 2025-10-03
**Platform:** Windows 11 + Conda + NVIDIA CUDA
**Python:** 3.10+
**PostgreSQL Version:** 17.6
