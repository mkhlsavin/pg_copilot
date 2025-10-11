# API Reference - PostgreSQL Books QA Generator

**Complete module and function reference for Windows 11 + Conda environment**

---

## 📦 Core Modules

### 1. `config.py` - Configuration

Central configuration for all pipeline components.

#### Key Variables

```python
# Paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
PDF_DIR = os.path.join(PROJECT_ROOT, "pdf")
MODEL_PATH = r"C:\Users\user\.lmstudio\models\...\Qwen3-32B-Q4_K_M.gguf"
PG_SOURCE_PATH = r"C:\Users\user\postgres-REL_17_6"

# LLM Settings
N_CTX = 8192              # Context window size
N_GPU_LAYERS = -1         # GPU layers (-1 = all)
N_BATCH = 512             # Batch size
TEMPERATURE = 0.7         # Sampling temperature
MAX_TOKENS = 2048         # Max tokens per generation

# Chunking
CHUNK_SIZE = 1000         # Target tokens per chunk
CHUNK_OVERLAP = 200       # Overlap between chunks
CHUNK_METHOD = 'semantic' # 'semantic', 'fixed', or 'hierarchical'

# QA Generation
QA_PAIRS_PER_CLUSTER = 2  # Q&A pairs per cluster/chunk
MIN_CHUNK_LENGTH = 200    # Minimum tokens to use
MAX_CONTEXT_LENGTH = 4000 # Max tokens in context
```

#### Functions

```python
def verify_paths() -> bool
    """Verify critical paths exist (model, PG source)."""
    # Returns: True if all paths valid, False otherwise
```

---

### 2. `utils.py` - Utility Functions

Common helper functions used across modules.

#### JSON Operations

```python
def load_json(file_path: str) -> Any
    """Load JSON from file."""
    # Args:
    #   file_path: Path to JSON file
    # Returns:
    #   Loaded data structure

def save_json(data: Any, file_path: str) -> None
    """Save data to JSON file."""
    # Args:
    #   data: Data to save
    #   file_path: Output file path
```

#### Text Processing

```python
def clean_text(text: str) -> str
    """Clean and normalize text."""
    # Args:
    #   text: Raw text
    # Returns:
    #   Cleaned text (whitespace normalized, special chars removed)

def count_tokens(text: str, encoding: str = "cl100k_base") -> int
    """Count tokens in text using tiktoken."""
    # Args:
    #   text: Input text
    #   encoding: Tiktoken encoding name
    # Returns:
    #   Token count
```

#### Logging

```python
def setup_logging(log_file: str = None, log_level: str = "INFO") -> None
    """Setup logging configuration."""
    # Args:
    #   log_file: Path to log file (optional)
    #   log_level: Logging level (DEBUG, INFO, WARNING, ERROR)

def get_timestamp() -> str
    """Get current timestamp string."""
    # Returns:
    #   ISO format timestamp (e.g., "2025-10-03T14:30:00")
```

---

### 3. `web_book_scraper.py` - Web Content Extraction

Scrapes "The Internals of PostgreSQL" website.

#### Main Class

```python
class WebBookScraper:
    """Scraper for The Internals of PostgreSQL website."""

    def __init__(self, base_url: str = "https://www.interdb.jp/pg/"):
        """
        Initialize scraper.

        Args:
            base_url: Base URL of the website
        """

    def scrape_toc(self) -> List[Dict]:
        """
        Scrape table of contents.

        Returns:
            List of chapters with URLs
        """

    def scrape_chapter(self, chapter_url: str) -> Dict:
        """
        Scrape a single chapter.

        Args:
            chapter_url: URL of chapter

        Returns:
            Dictionary with chapter content:
            {
                'chapter': str,
                'sections': List[Dict],
                'url': str
            }
        """

    def scrape_all(self) -> List[Dict]:
        """
        Scrape all chapters.

        Returns:
            List of all content items
        """
```

#### Usage

```python
from web_book_scraper import WebBookScraper

scraper = WebBookScraper()
content = scraper.scrape_all()  # Returns list of content items
save_json(content, "data/web_content.json")
```

---

### 4. `content_chunker.py` - Content Chunking

Splits content into semantic chunks for Q&A generation.

#### Main Class

```python
class ContentChunker:
    """Chunks extracted content into semantic units."""

    def __init__(self, content_items: List[Dict]):
        """
        Initialize chunker.

        Args:
            content_items: List of content items from extractor
        """
        self.content_items = content_items
        self.chunks = []
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""

    def chunk_content(self) -> List[Dict]:
        """
        Chunk all content items.

        Returns:
            List of chunked content items
        """

    def _semantic_chunk(self, item: Dict, text: str) -> List[Dict]:
        """
        Split text using semantic boundaries.

        Args:
            item: Content item
            text: Text to chunk

        Returns:
            List of chunks (preserves paragraph boundaries)
        """

    def _sliding_window_chunk(self, item: Dict, text: str) -> List[Dict]:
        """
        Split text using sliding window with overlap.

        Args:
            item: Content item
            text: Text to chunk

        Returns:
            List of chunks (fixed size with overlap)
        """

    def get_statistics(self) -> Dict:
        """
        Get chunking statistics.

        Returns:
            Dictionary with token counts, chunk distribution
        """
```

#### Chunk Format

```python
{
    'source_type': 'web',           # or 'pdf'
    'text': '...',                  # Chunk text
    'chapter': 'Chapter 1',         # Chapter name
    'section': 'Section 1.1',       # Section name (optional)
    'chunk_index': 0,               # Index within source
    'token_count': 950,             # Actual tokens
    'source_url': 'https://...',    # Source URL (for web)
    'pdf_file': 'book.pdf',         # PDF filename (for PDF)
    'page_number': 10               # Page number (for PDF)
}
```

#### Usage

```python
from content_chunker import ContentChunker

content = load_json("data/web_content.json")
chunker = ContentChunker(content)
chunks = chunker.chunk_content()

# Get statistics
stats = chunker.get_statistics()
print(f"Total chunks: {stats['total_chunks']}")
print(f"Avg tokens: {stats['avg_tokens']:.1f}")

# Save
chunker.save_to_json("data/chunked_content.json")
```

---

### 5. `llm_interface.py` - LLM Interface

Wrapper for llama-cpp-python with GPU support.

#### Main Class

```python
class LLMInterface:
    """Interface for local LLM (llama-cpp-python)."""

    def __init__(self):
        """Initialize LLM interface (model not loaded yet)."""
        self.model = None
        self.loaded = False

    def load_model(self) -> None:
        """
        Load LLM model from config.MODEL_PATH.

        Raises:
            FileNotFoundError: If model file not found
            RuntimeError: If model loading fails
        """

    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        max_tokens: int = None,
        temperature: float = None,
        stop: List[str] = None
    ) -> str:
        """
        Generate completion from prompt.

        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            max_tokens: Max tokens to generate (default: config.MAX_TOKENS)
            temperature: Sampling temperature (default: config.TEMPERATURE)
            stop: Stop sequences (optional)

        Returns:
            Generated text

        Raises:
            RuntimeError: If model not loaded
        """

    def unload_model(self) -> None:
        """Unload model from memory."""
```

#### Chat Template

```python
# Format used internally:
<|im_start|>system
{system_prompt}<|im_end|>
<|im_start|>user
{user_prompt}<|im_end|>
<|im_start|>assistant
```

#### Usage

```python
from llm_interface import LLMInterface

# Initialize and load
llm = LLMInterface()
llm.load_model()  # Loads model from config.MODEL_PATH

# Generate
response = llm.generate(
    prompt="Explain PostgreSQL MVCC",
    system_prompt="You are a PostgreSQL expert.",
    max_tokens=500,
    temperature=0.7
)

print(response)

# Cleanup
llm.unload_model()
```

---

### 6. `qa_generator.py` - Q&A Generation

Generates question-answer pairs using LLM.

#### Main Class

```python
class QAGenerator:
    """Generates Q&A pairs from content chunks."""

    def __init__(self, llm: LLMInterface):
        """
        Initialize QA generator.

        Args:
            llm: Loaded LLM interface
        """
        self.llm = llm

    def generate_qa_pair(
        self,
        content: str,
        context: Dict,
        difficulty: str = "intermediate"
    ) -> Dict:
        """
        Generate a single Q&A pair.

        Args:
            content: Content text to generate from
            context: Context dictionary with metadata
            difficulty: Target difficulty level

        Returns:
            Q&A pair dictionary:
            {
                'question': str,
                'answer': str,
                'difficulty': str,
                'topics': List[str],
                'source_files': List[str],
                'generated_at': str
            }
        """

    def generate_multiple(
        self,
        content: str,
        context: Dict,
        n: int = 2
    ) -> List[Dict]:
        """
        Generate multiple Q&A pairs from content.

        Args:
            content: Content text
            context: Context metadata
            n: Number of Q&A pairs to generate

        Returns:
            List of Q&A pairs
        """

    def build_prompt(
        self,
        content: str,
        context: Dict,
        n: int = 1
    ) -> Tuple[str, str]:
        """
        Build system and user prompts.

        Args:
            content: Content text
            context: Context metadata
            n: Number of Q&A pairs

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
```

#### Prompt Template

```python
SYSTEM_PROMPT = """You are a PostgreSQL internals expert with deep knowledge of PostgreSQL 17.6 architecture and source code. Generate high-quality question-answer pairs based on technical book content and source code context."""

USER_PROMPT = """Generate {n} technical question-answer pairs from this PostgreSQL content:

Content:
{content}

Chapter: {chapter}
Section: {section}
Source Files: {source_files}

Requirements:
1. Questions should be specific and technical
2. Answers should be detailed (150-300 words)
3. Include difficulty level: beginner/intermediate/advanced
4. Extract relevant topics

Format: JSON array of Q&A pairs
"""
```

#### Usage

```python
from qa_generator import QAGenerator

llm = LLMInterface()
llm.load_model()

generator = QAGenerator(llm)

# Generate from chunk
chunk = {
    'text': 'PostgreSQL uses MVCC for concurrency control...',
    'chapter': 'Chapter 5: Concurrency Control',
    'source_files': ['access/heap/heapam.c', 'utils/time/tqual.c']
}

qa_pairs = generator.generate_multiple(
    content=chunk['text'],
    context=chunk,
    n=2  # Generate 2 Q&A pairs
)

for qa in qa_pairs:
    print(f"Q: {qa['question']}")
    print(f"A: {qa['answer'][:100]}...")
    print(f"Difficulty: {qa['difficulty']}\n")
```

---

### 7. `generate_qa_from_chunks.py` - Direct Q&A Generation

Generates Q&A pairs directly from chunks (bypasses clustering).

#### Main Function

```python
def main():
    """Generate QA pairs directly from chunks."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true',
                       help='Test mode with first 5 chunks')
    parser.add_argument('--max-chunks', type=int, default=None,
                       help='Maximum chunks to process')
    parser.add_argument('--qa-per-chunk', type=int, default=2,
                       help='QA pairs per chunk')
    args = parser.parse_args()

    # Load chunks
    chunks = load_json(config.CHUNKED_CONTENT_FILE)

    if args.test:
        chunks = chunks[:5]
    elif args.max_chunks:
        chunks = chunks[:args.max_chunks]

    # Initialize LLM and generator
    llm = LLMInterface()
    llm.load_model()
    generator = QAGenerator(llm)

    # Generate Q&A pairs
    qa_pairs = []
    for i, chunk in enumerate(tqdm(chunks)):
        pairs = generator.generate_multiple(
            content=chunk['text'],
            context=chunk,
            n=args.qa_per_chunk
        )
        qa_pairs.extend(pairs)

    # Save to JSONL
    with jsonlines.open(config.QA_PAIRS_FILE, 'w') as writer:
        for qa in qa_pairs:
            writer.write(qa)

    print(f"Generated {len(qa_pairs)} Q&A pairs")
```

#### Command Line

```cmd
:: Test mode (5 chunks)
python generate_qa_from_chunks.py --test --qa-per-chunk 2

:: Limited run (100 chunks)
python generate_qa_from_chunks.py --max-chunks 100 --qa-per-chunk 2

:: Full run (all chunks)
python generate_qa_from_chunks.py --qa-per-chunk 2

:: Custom pairs per chunk
python generate_qa_from_chunks.py --qa-per-chunk 3
```

---

### 8. `main.py` - Pipeline Orchestrator

Main entry point for complete pipeline.

#### Command Line Interface

```python
import argparse

parser = argparse.ArgumentParser(description="PostgreSQL Books QA Generator")

# Pipeline stages
parser.add_argument('--extract-pdf', action='store_true', help='Extract from PDFs')
parser.add_argument('--chunk', action='store_true', help='Chunk content')
parser.add_argument('--cluster', action='store_true', help='Cluster topics')
parser.add_argument('--map-source', action='store_true', help='Map to PG source')
parser.add_argument('--generate-qa', action='store_true', help='Generate Q&A')
parser.add_argument('--all', action='store_true', help='Run full pipeline')

# Parameters
parser.add_argument('--n-clusters', type=int, default=20, help='Number of clusters')
parser.add_argument('--max-clusters', type=int, help='Max clusters to process')
parser.add_argument('--qa-per-cluster', type=int, default=2, help='Q&A per cluster')
```

#### Usage

```cmd
:: Extract from PDFs
python main.py --extract-pdf

:: Chunk content
python main.py --chunk

:: Cluster into 20 topics
python main.py --cluster --n-clusters 20

:: Map to PostgreSQL source
python main.py --map-source

:: Generate Q&A (first 10 clusters, 2 pairs each)
python main.py --generate-qa --max-clusters 10 --qa-per-cluster 2

:: Run complete pipeline
python main.py --all --n-clusters 20 --qa-per-cluster 2
```

---

## 📁 Data Formats

### Chunked Content Format

```json
{
  "source_type": "web",
  "text": "PostgreSQL uses Multi-Version Concurrency Control...",
  "chapter": "Chapter 5: Concurrency Control",
  "section": "5.1 MVCC Overview",
  "chunk_index": 0,
  "token_count": 950,
  "source_url": "https://www.interdb.jp/pg/pgsql05.html",
  "extracted_at": "2025-10-03T14:30:00"
}
```

### Q&A Pair Format

```json
{
  "question": "How does PostgreSQL validate transaction IDs during visibility checks?",
  "answer": "PostgreSQL validates transaction IDs using macros and functions defined in 'transam.h' and 'xact.c'. The `TransactionIdIsValid()` macro checks if an XID is non-zero. During visibility checks in functions like `HeapTupleSatisfiesMVCC()`, PostgreSQL compares XIDs against snapshot boundaries (xmin, xmax) to determine tuple visibility. The validation process ensures that only committed transactions within the snapshot's visibility range are considered visible to the current transaction.",
  "difficulty": "intermediate",
  "topics": ["transaction_management", "mvcc", "visibility"],
  "cluster_id": 0,
  "cluster_label": "chunk_0",
  "source_files": ["access/heap/heapam.c", "utils/time/tqual.c"],
  "thread_ids": ["chunk_0"],
  "generated_at": "2025-10-03T14:35:22"
}
```

---

## 🔧 Configuration Examples

### Low VRAM Setup (16GB)

```python
# config.py
N_GPU_LAYERS = 25         # Partial GPU offload
N_CTX = 4096              # Smaller context
N_BATCH = 256             # Smaller batch
CHUNK_SIZE = 500          # Smaller chunks
MAX_TOKENS = 1024         # Shorter responses
```

### High Performance Setup (24GB+)

```python
# config.py
N_GPU_LAYERS = -1         # All on GPU
N_CTX = 8192              # Full context
N_BATCH = 512             # Large batch
CHUNK_SIZE = 1000         # Standard chunks
MAX_TOKENS = 2048         # Detailed responses
```

### Quality-Focused Setup

```python
# config.py
QA_PAIRS_PER_CLUSTER = 3  # More Q&A per topic
TEMPERATURE = 0.8         # More creative
MAX_TOKENS = 3072         # Longer answers
MIN_CHUNK_LENGTH = 500    # Only substantial chunks
```

---

## 🐍 Python API Examples

### Example 1: Custom Pipeline

```python
import sys
sys.path.insert(0, '.')

from utils import load_json, save_json
from content_chunker import ContentChunker
from llm_interface import LLMInterface
from qa_generator import QAGenerator
import config

# 1. Load content
content = load_json("data/web_content.json")

# 2. Chunk with custom settings
chunker = ContentChunker(content)
chunker.CHUNK_SIZE = 500  # Override default
chunks = chunker.chunk_content()

# 3. Initialize LLM
llm = LLMInterface()
llm.load_model()

# 4. Generate Q&A
generator = QAGenerator(llm)
qa_pairs = []

for chunk in chunks[:10]:  # First 10 chunks
    pairs = generator.generate_multiple(
        content=chunk['text'],
        context=chunk,
        n=3  # 3 pairs per chunk
    )
    qa_pairs.extend(pairs)

# 5. Save
import jsonlines
with jsonlines.open("custom_qa.jsonl", 'w') as writer:
    for qa in qa_pairs:
        writer.write(qa)

print(f"Generated {len(qa_pairs)} Q&A pairs")
```

### Example 2: Quality Filtering

```python
import jsonlines

# Load Q&A pairs
qa_pairs = list(jsonlines.open("data/qa_pairs.jsonl"))

# Filter by quality criteria
filtered = []
for qa in qa_pairs:
    answer_len = len(qa['answer'].split())

    # Keep only intermediate/advanced with 100+ words
    if (qa['difficulty'] in ['intermediate', 'advanced'] and
        answer_len >= 100):
        filtered.append(qa)

# Save filtered dataset
with jsonlines.open("data/qa_pairs_filtered.jsonl", 'w') as writer:
    for qa in filtered:
        writer.write(qa)

print(f"Filtered: {len(qa_pairs)} → {len(filtered)}")
```

---

## 📊 Performance Monitoring

### GPU Usage

```python
import subprocess

def get_gpu_usage():
    """Get current GPU memory usage."""
    result = subprocess.run(
        ['nvidia-smi', '--query-gpu=memory.used,memory.total',
         '--format=csv,noheader,nounits'],
        capture_output=True, text=True
    )
    used, total = map(int, result.stdout.strip().split(','))
    return used, total

# Monitor during generation
used, total = get_gpu_usage()
print(f"GPU Memory: {used}/{total} MB ({used/total*100:.1f}%)")
```

### Generation Speed

```python
import time

def benchmark_generation(llm, generator, chunk, n_pairs=2):
    """Benchmark Q&A generation speed."""
    start = time.time()

    pairs = generator.generate_multiple(
        content=chunk['text'],
        context=chunk,
        n=n_pairs
    )

    elapsed = time.time() - start
    speed = len(pairs) / elapsed

    print(f"Generated {len(pairs)} pairs in {elapsed:.1f}s")
    print(f"Speed: {speed:.2f} pairs/sec")

    return pairs
```

---

## 🆘 Error Handling

### Common Exceptions

```python
from llm_interface import LLMInterface

try:
    llm = LLMInterface()
    llm.load_model()
except FileNotFoundError as e:
    print(f"Model file not found: {e}")
    print("Check config.MODEL_PATH")
except RuntimeError as e:
    print(f"Model loading failed: {e}")
    print("Check CUDA/GPU availability")

try:
    response = llm.generate("Test prompt")
except RuntimeError as e:
    print("Model not loaded. Call load_model() first.")
```

### Retry Logic

```python
import time

def generate_with_retry(generator, chunk, max_retries=3):
    """Generate Q&A with retry logic."""
    for attempt in range(max_retries):
        try:
            return generator.generate_multiple(
                content=chunk['text'],
                context=chunk,
                n=2
            )
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt+1} failed: {e}")
                print("Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print(f"Failed after {max_retries} attempts")
                raise
```

---

**Last Updated:** 2025-10-03
**Platform:** Windows 11 + Conda + NVIDIA CUDA
