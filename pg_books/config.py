"""
Configuration settings for PostgreSQL Books QA Dataset Generator
"""
import os

# ============================================================================
# PATHS
# ============================================================================

# Project directories
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(PROJECT_ROOT, "pdf")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

# LLM paths (reuse from hackers)
LLAMA_CPP_PATH = r"C:\Users\user\llama.cpp"
MODEL_PATH = r"C:\Users\user\.lmstudio\models\lmstudio-community\Qwen3-32B-GGUF\Qwen3-32B-Q4_K_M.gguf"

# PostgreSQL source
PG_SOURCE_PATH = r"C:\Users\user\postgres-REL_17_6"
PG_VERSION = "17.6"

# ============================================================================
# PDF EXTRACTION
# ============================================================================

# PDF processing
EXTRACT_IMAGES = False  # Don't extract images (focus on text)
EXTRACT_TABLES = True   # Extract tables as structured data
PRESERVE_LAYOUT = False  # Use simple text extraction
MIN_TEXT_LENGTH = 50     # Minimum characters per extraction unit

# Output files
EXTRACTED_CONTENT_FILE = os.path.join(DATA_DIR, "extracted_content.json")

# ============================================================================
# CONTENT CHUNKING
# ============================================================================

# Chunking strategy
CHUNK_SIZE = 1000           # Target tokens per chunk
CHUNK_OVERLAP = 200         # Overlap between chunks (tokens)
CHUNK_METHOD = 'semantic'   # 'semantic', 'fixed', or 'hierarchical'

# Hierarchical chunking (if CHUNK_METHOD='hierarchical')
RESPECT_CHAPTERS = True     # Don't split across chapters
RESPECT_SECTIONS = True     # Don't split across sections
MIN_CHUNK_SIZE = 500        # Minimum tokens per chunk
MAX_CHUNK_SIZE = 1500       # Maximum tokens per chunk

# Output files
CHUNKED_CONTENT_FILE = os.path.join(DATA_DIR, "chunked_content.json")
PROCESSED_THREADS_FILE = os.path.join(DATA_DIR, "processed_threads.json")  # For compatibility with topic_clustering

# ============================================================================
# TOPIC CLUSTERING
# ============================================================================

# Embedding model
EMBEDDING_MODEL = 'all-MiniLM-L6-v2'  # Fast and good quality

# Clustering settings
CLUSTERING_METHOD = 'kmeans'  # 'hdbscan' or 'kmeans'
MIN_CLUSTER_SIZE = 1          # Minimum chunks per cluster
N_CLUSTERS = 300              # For KMeans (None = auto-determine)

# Keyword extraction
KEYWORD_EXTRACTION = 'tfidf'  # 'tfidf' or 'keybert'
N_KEYWORDS = 5                # Keywords per cluster

# Dimensionality reduction
REDUCE_DIMENSIONS = False     # Use UMAP before clustering
UMAP_N_COMPONENTS = 50        # If REDUCE_DIMENSIONS=True

# Processing
SHOW_PROGRESS = True          # Show progress bars
RANDOM_SEED = 42              # For reproducibility

# Output files
CLUSTERED_TOPICS_FILE = os.path.join(DATA_DIR, "clustered_topics.json")
CHUNK_EMBEDDINGS_FILE = os.path.join(DATA_DIR, "chunk_embeddings.npy")
EMBEDDINGS_CACHE_FILE = os.path.join(DATA_DIR, "embeddings_cache.npy")

# ============================================================================
# SOURCE CODE MAPPING
# ============================================================================

# Mapping strategy
MAPPING_METHOD = 'keyword'  # 'keyword' or 'embedding'
EXTRACT_FUNCTIONS = True    # Extract function signatures
MAX_FILES_PER_TOPIC = 10    # Top N files to include
MIN_RELEVANCE_SCORE = 0.5   # Minimum score to include file
INCLUDE_HEADERS = True      # Include .h files or only .c
MAX_FUNCTION_SNIPPETS = 5   # Function signatures per file

# Keyword to component mapping (reuse from hackers - 120+ keywords)
KEYWORD_TO_COMPONENT = {
    # 1. Planner / Optimizer
    'planner': ['optimizer/plan', 'optimizer/path', 'optimizer/prep'],
    'optimizer': ['optimizer/plan', 'optimizer/path', 'optimizer/prep', 'optimizer'],
    'plan': ['optimizer/plan'],
    'path': ['optimizer/path'],
    'cost': ['optimizer/path', 'optimizer/cost'],
    'geqo': ['optimizer/geqo'],

    # 2. Executor
    'executor': ['executor', 'nodeAppend', 'nodeModifyTable', 'nodeHashjoin', 'nodeNestloop'],
    'modifytable': ['executor/nodeModifyTable'],
    'seqscan': ['executor/nodeSeqscan'],
    'indexscan': ['executor/nodeIndexscan'],
    'hashjoin': ['executor/nodeHashjoin'],
    'sort': ['executor/nodeSort'],
    'parallel': ['executor', 'access/parallel'],

    # 3. Parser
    'parser': ['parser'],
    'parse': ['parser'],
    'lexer': ['parser/scan'],
    'analyze': ['parser/analyze'],
    'rewrite': ['rewrite'],

    # 4. Storage
    'heap': ['access/heap'],
    'storage': ['storage', 'storage/buffer', 'storage/smgr', 'storage/file'],
    'buffer': ['storage/buffer'],
    'shared_buffers': ['storage/buffer'],
    'smgr': ['storage/smgr'],
    'page': ['storage/page'],
    'freespace': ['storage/freespace'],
    'fsm': ['storage/freespace'],
    'visibility map': ['access/heap', 'storage/freespace'],
    'toast': ['access/toast'],
    'xmin': ['access/heap'],
    'xmax': ['access/heap'],
    't_ctid': ['access/heap'],
    'tuple': ['access/heap'],

    # 5. Index Access Methods
    'index': ['access/index', 'access/nbtree', 'access/hash', 'access/gist', 'access/gin', 'access/brin'],
    'btree': ['access/nbtree'],
    'nbtree': ['access/nbtree'],
    'hash': ['access/hash'],
    'gist': ['access/gist'],
    'gin': ['access/gin'],
    'brin': ['access/brin'],
    'spgist': ['access/spgist'],

    # 6. Transaction & MVCC
    'mvcc': ['access/heap', 'access/transam', 'utils/time'],
    'transaction': ['access/transam'],
    'xact': ['access/transam'],
    'xid': ['access/transam'],
    'clog': ['access/transam/clog'],
    'subtrans': ['access/transam/subtrans'],
    'visibility': ['access/heap', 'utils/time', 'access/transam'],
    'snapshot': ['utils/time', 'access/transam'],
    'frozen': ['access/heap', 'commands/vacuumlazy'],
    'wraparound': ['access/heap', 'commands/vacuum'],

    # 7. WAL & Replication
    'wal': ['access/transam/xlog', 'access/transam', 'access/wal'],
    'xlog': ['access/transam/xlog'],
    'pg_wal': ['access/transam/xlog'],
    'write-ahead log': ['access/transam/xlog'],
    'replication': ['replication'],
    'logical replication': ['replication/logical'],
    'physical replication': ['replication'],
    'logical decoding': ['replication/logical'],
    'output plugin': ['replication/logical'],
    'pgoutput': ['replication/pgoutput'],
    'slot': ['replication/slot'],
    'replication slot': ['replication/slot'],
    'walsender': ['replication/walsender'],
    'walreceiver': ['replication/walreceiver'],
    'decode': ['replication/logical'],
    'wal_level': ['access/transam/xlog'],

    # 8. Vacuum & Cleanup
    'vacuum': ['commands/vacuum', 'commands/vacuumlazy', 'access/heap'],
    'autovacuum': ['postmaster/autovacuum'],
    'analyze': ['commands/analyze'],

    # 9. Partitioning
    'partition': ['partitioning', 'executor/nodeAppend', 'optimizer/path'],
    'partitioning': ['partitioning', 'executor/nodeAppend'],
    'pruning': ['partitioning/partprune', 'executor/execPartition'],
    'partition pruning': ['partitioning/partprune', 'executor/execPartition'],
    'runtime pruning': ['executor/execPartition'],
    'partition key': ['partitioning'],
    'constraint exclusion': ['optimizer/util/plancat'],
    'range partition': ['partitioning'],
    'list partition': ['partitioning'],
    'hash partition': ['partitioning'],

    # 10. Locking & Concurrency
    'lock': ['storage/lmgr'],
    'locking': ['storage/lmgr'],
    'deadlock': ['storage/lmgr/deadlock'],
    'lwlock': ['storage/lmgr/lwlock'],
    'spinlock': ['storage/lmgr/spin'],

    # 11. Background Processes
    'bgwriter': ['postmaster/bgwriter'],
    'background writer': ['postmaster/bgwriter'],
    'checkpointer': ['postmaster/checkpointer'],
    'checkpoint': ['access/transam/xlog', 'postmaster/checkpointer'],
    'walwriter': ['postmaster/walwriter'],
    'wal writer': ['postmaster/walwriter'],
    'archiver': ['postmaster/pgarch'],
    'stats collector': ['postmaster/pgstat'],
    'syslogger': ['postmaster/syslogger'],
    'logging collector': ['postmaster/syslogger'],
    'bgworker': ['postmaster/bgworker'],
    'background worker': ['postmaster/bgworker'],

    # 12. Query Processing
    'query': ['optimizer', 'executor', 'parser'],
    'join': ['executor/nodeHashjoin', 'executor/nodeNestloop', 'executor/nodeMergejoin', 'optimizer/path'],
    'aggregate': ['executor/nodeAgg'],
    'subquery': ['optimizer/subselect'],

    # 13. Types & Functions
    'type': ['utils/adt'],
    'function': ['utils/fmgr'],
    'cast': ['parser/parse_coerce'],

    # 14. Statistics
    'statistics': ['commands/analyze', 'optimizer/util/plancat'],
    'stats': ['commands/analyze', 'postmaster/pgstat'],
    'extended statistics': ['statistics'],
    'pg_stat': ['postmaster/pgstat'],
    'bloat': ['commands/vacuum', 'access/heap'],

    # 15. Utilities
    'utility': ['tcop/utility'],
    'ddl': ['commands'],
    'create': ['commands'],
    'alter': ['commands'],
    'drop': ['commands'],

    # 16. Extensions & Contrib
    'extension': ['commands/extension'],
    'contrib': ['contrib'],

    # 17. Additional Storage Features
    'tid': ['access/heap'],
    'ctid': ['access/heap'],
    'hot': ['access/heap'],
    'heap only tuple': ['access/heap'],

    # 18. Performance & Optimization
    'seq_page_cost': ['optimizer/path'],
    'random_page_cost': ['optimizer/path'],
    'cost model': ['optimizer/path'],
    'selectivity': ['optimizer/util'],

    # 19. System Catalog
    'catalog': ['catalog'],
    'pg_class': ['catalog'],
    'pg_attribute': ['catalog'],
    'syscache': ['utils/cache'],
}

# Output files
SOURCE_MAPPING_FILE = os.path.join(DATA_DIR, "source_mapping.json")
FILE_INDEX_CACHE_FILE = os.path.join(DATA_DIR, "file_index.json")

# ============================================================================
# LLM INTERFACE
# ============================================================================

# Model parameters (RTX 3090 - 24GB VRAM)
N_CTX = 8192  # Context window
N_GPU_LAYERS = -1  # All layers on GPU (-1 = all)
N_BATCH = 512  # Batch size for processing
N_THREADS = 8  # CPU threads for non-GPU operations

# Generation parameters
TEMPERATURE = 0.7  # Sampling temperature (0.0-2.0)
TOP_P = 0.9  # Nucleus sampling
TOP_K = 40  # Top-k sampling
REPEAT_PENALTY = 1.1  # Repetition penalty
MAX_TOKENS = 2048  # Max tokens per generation
STOP_SEQUENCES = ["<|im_end|>", "<|endoftext|>"]

# System prompt
SYSTEM_PROMPT = """You are a PostgreSQL internals expert with deep knowledge of the PostgreSQL 17 architecture and source code. Generate high-quality question-answer pairs based on technical book content and source code context."""

# ============================================================================
# QA GENERATOR
# ============================================================================

# QA generation settings
QA_PAIRS_PER_CLUSTER = 2  # Target QA pairs per topic
MIN_CHUNK_LENGTH = 200  # Minimum tokens to use chunk
MAX_CHUNKS_PER_CLUSTER = 5  # Top N chunks to include in context
MAX_THREADS_PER_CLUSTER = 5  # Top N threads/chunks to include
MAX_SOURCE_FILES_PER_CLUSTER = 10  # Top N files to include
MAX_CONTEXT_LENGTH = 4000  # Maximum tokens in context
MAX_RETRIES = 3  # Retries for LLM generation
GENERATION_TEMPERATURE = 0.7  # Temperature for QA generation
GENERATION_MAX_TOKENS = 2048  # Max tokens for QA generation

# Difficulty distribution
DIFFICULTY_LEVELS = ['beginner', 'intermediate', 'advanced']
TARGET_DIFFICULTY_DISTRIBUTION = {
    'beginner': 0.2,      # 20%
    'intermediate': 0.5,  # 50%
    'advanced': 0.3       # 30%
}

# Output files
QA_PAIRS_FILE = os.path.join(DATA_DIR, "qa_pairs.jsonl")
QA_CHECKPOINT_FILE = os.path.join(DATA_DIR, "qa_pairs_checkpoint.jsonl")

# ============================================================================
# DATASET BUILDER
# ============================================================================

# Dataset metadata
DATASET_NAME = "pg_copilot_books_qa_dataset"
DATASET_VERSION = "1.0"
DATASET_DESCRIPTION = "PostgreSQL technical books QA dataset for RAG evaluation"

# Validation
VALIDATE_JSON = True
VALIDATE_SCHEMA = True
REMOVE_DUPLICATES = True
DEDUP_SIMILARITY_THRESHOLD = 0.85  # Similarity threshold for deduplication
MIN_ANSWER_LENGTH = 20  # Minimum characters for answer

# Output files
FINAL_DATASET_FILE = os.path.join(OUTPUT_DIR, "pg_copilot_books_dataset.jsonl")
DATASET_REPORT_FILE = os.path.join(OUTPUT_DIR, "dataset_report.json")
DATASET_README_FILE = os.path.join(OUTPUT_DIR, "README.md")

# ============================================================================
# LOGGING
# ============================================================================

# Logging configuration
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = os.path.join(PROJECT_ROOT, "pipeline.log")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
