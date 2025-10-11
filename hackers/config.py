"""
Configuration settings for PostgreSQL Hackers Mailing List QA Dataset Generator
"""
import os

# ============================================================================
# PATHS
# ============================================================================

# Project directories
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

# LLM paths
LLAMA_CPP_PATH = r"C:\Users\user\llama.cpp"
MODEL_PATH = r"C:\Users\user\.lmstudio\models\lmstudio-community\Qwen3-32B-GGUF\Qwen3-32B-Q4_K_M.gguf"

# PostgreSQL source
PG_SOURCE_PATH = r"C:\Users\user\postgres-REL_17_6"
PG_VERSION = "17.6"

# ============================================================================
# MAILING LIST SCRAPER
# ============================================================================

MAILING_LIST_URL = "https://www.postgresql.org/list/pgsql-hackers"
START_YEAR = 2022
END_YEAR = 2025

# Scraper settings
RATE_LIMIT_DELAY = 0.1  # Seconds between requests (10 req/sec)
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30  # Seconds
CONCURRENT_REQUESTS = 5  # Number of parallel message fetches
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

# Output files
RAW_THREADS_FILE = os.path.join(DATA_DIR, "raw_threads.json")
SCRAPER_CHECKPOINT_FILE = os.path.join(DATA_DIR, "scraper_checkpoint.json")

# ============================================================================
# THREAD PARSER
# ============================================================================

# Thread parsing settings
MIN_THREAD_SIZE = 1  # Minimum messages to form a thread (set to 1 because scraper doesn't extract in_reply_to)
MAX_THREAD_DEPTH = 20  # Prevent infinite recursion
CLEAN_QUOTED_TEXT = True
REMOVE_SIGNATURES = True
PRESERVE_URLS = False
NORMALIZE_SUBJECTS = True  # "Re: Re: Subject" → "Subject"

# Output files
PROCESSED_THREADS_FILE = os.path.join(DATA_DIR, "processed_threads.json")

# ============================================================================
# TOPIC CLUSTERING
# ============================================================================

# Embedding model
EMBEDDING_MODEL = 'all-MiniLM-L6-v2'  # Fast and good quality

# Clustering settings
CLUSTERING_METHOD = 'hdbscan'  # 'hdbscan' or 'kmeans'
MIN_CLUSTER_SIZE = 5  # Minimum threads per cluster (for HDBSCAN)
N_CLUSTERS = None  # For KMeans (None = auto-determine)

# Keyword extraction
KEYWORD_EXTRACTION = 'tfidf'  # 'tfidf' or 'keybert'
N_KEYWORDS = 5  # Keywords per cluster

# Dimensionality reduction
REDUCE_DIMENSIONS = False  # Use UMAP before clustering
UMAP_N_COMPONENTS = 50  # If REDUCE_DIMENSIONS=True

# Output files
CLUSTERED_TOPICS_FILE = os.path.join(DATA_DIR, "clustered_topics.json")
EMBEDDINGS_CACHE_FILE = os.path.join(DATA_DIR, "thread_embeddings.npy")

# ============================================================================
# POSTGRESQL SOURCE CONTEXT
# ============================================================================

# Source mapping settings
EXTRACT_FUNCTIONS = True  # Extract function signatures
MAX_FILES_PER_TOPIC = 10  # Top N files to include
MIN_RELEVANCE_SCORE = 0.5  # Minimum score to include file
INCLUDE_HEADERS = True  # Include .h files or only .c
MAX_FUNCTION_SNIPPETS = 5  # Function signatures per file

# Keyword to component mapping (based on PostgreSQL 17 subsystems)
KEYWORD_TO_COMPONENT = {
    # 1. Planner / Optimizer (Планировщик и оптимизатор)
    'planner': ['optimizer/plan', 'optimizer/path', 'optimizer/prep'],
    'optimizer': ['optimizer/plan', 'optimizer/path', 'optimizer/prep', 'optimizer'],
    'plan': ['optimizer/plan'],
    'path': ['optimizer/path'],
    'cost': ['optimizer/path', 'optimizer/cost'],
    'geqo': ['optimizer/geqo'],

    # 2. Executor (Исполнитель)
    'executor': ['executor', 'nodeAppend', 'nodeModifyTable', 'nodeHashjoin', 'nodeNestloop'],
    'modifytable': ['executor/nodeModifyTable'],
    'seqscan': ['executor/nodeSeqscan'],
    'indexscan': ['executor/nodeIndexscan'],
    'hashjoin': ['executor/nodeHashjoin'],
    'sort': ['executor/nodeSort'],
    'parallel': ['executor', 'access/parallel'],

    # 3. Parser (Парсер)
    'parser': ['parser'],
    'parse': ['parser'],
    'lexer': ['parser/scan'],
    'analyze': ['parser/analyze'],
    'rewrite': ['rewrite'],
    'raw parse tree': ['parser'],

    # 4. Storage (Хранилище данных)
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
    'lru': ['storage/buffer'],

    # 5. Index Access Methods (Индексы)
    'index': ['access/index', 'access/nbtree', 'access/hash', 'access/gist', 'access/gin', 'access/brin'],
    'btree': ['access/nbtree'],
    'nbtree': ['access/nbtree'],
    'hash': ['access/hash'],
    'gist': ['access/gist'],
    'gin': ['access/gin'],
    'brin': ['access/brin'],
    'spgist': ['access/spgist'],

    # 6. Transaction & MVCC (Управление транзакциями и MVCC)
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

    # 7. WAL & Replication (WAL и репликация)
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

    # 8. Vacuum & Cleanup (Вакуум и очистка)
    'vacuum': ['commands/vacuum', 'commands/vacuumlazy', 'access/heap'],
    'autovacuum': ['postmaster/autovacuum'],
    'analyze': ['commands/analyze'],

    # 9. Partitioning (Партиционирование)
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

    # 10. Locking & Concurrency (Блокировки и конкурентность)
    'lock': ['storage/lmgr'],
    'locking': ['storage/lmgr'],
    'deadlock': ['storage/lmgr/deadlock'],
    'lwlock': ['storage/lmgr/lwlock'],
    'spinlock': ['storage/lmgr/spin'],

    # 11. Background Processes (Фоновые процессы)
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

    # 12. Query Processing (Обработка запросов)
    'query': ['optimizer', 'executor', 'parser'],
    'join': ['executor/nodeHashjoin', 'executor/nodeNestloop', 'executor/nodeMergejoin', 'optimizer/path'],
    'aggregate': ['executor/nodeAgg'],
    'subquery': ['optimizer/subselect'],

    # 13. Types & Functions (Типы данных и функции)
    'type': ['utils/adt'],
    'function': ['utils/fmgr'],
    'cast': ['parser/parse_coerce'],

    # 14. Statistics (Статистика)
    'statistics': ['commands/analyze', 'optimizer/util/plancat'],
    'stats': ['commands/analyze', 'postmaster/pgstat'],
    'extended statistics': ['statistics'],
    'pg_stat': ['postmaster/pgstat'],
    'bloat': ['commands/vacuum', 'access/heap'],

    # 15. Utilities (Утилиты)
    'utility': ['tcop/utility'],
    'ddl': ['commands'],
    'create': ['commands'],
    'alter': ['commands'],
    'drop': ['commands'],

    # 16. Extensions & Contrib (Расширения)
    'extension': ['commands/extension'],
    'contrib': ['contrib'],
    'pg_stat_statements': ['contrib/pg_stat_statements'],

    # 17. Additional Storage Features (Дополнительные возможности хранения)
    'tid': ['access/heap'],
    'ctid': ['access/heap'],
    'hot': ['access/heap'],
    'heap only tuple': ['access/heap'],

    # 18. Performance & Optimization (Производительность и оптимизация)
    'seq_page_cost': ['optimizer/path'],
    'random_page_cost': ['optimizer/path'],
    'cost model': ['optimizer/path'],
    'selectivity': ['optimizer/util'],

    # 19. System Catalog (Системный каталог)
    'catalog': ['catalog'],
    'pg_class': ['catalog'],
    'pg_attribute': ['catalog'],
    'syscache': ['utils/cache'],
}

# Output files
SOURCE_MAPPING_FILE = os.path.join(DATA_DIR, "topic_source_mapping.json")
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
SYSTEM_PROMPT = """You are a PostgreSQL internals expert with deep knowledge of the PostgreSQL 17 architecture and source code. Generate high-quality question-answer pairs based on developer discussions and source code context."""

# ============================================================================
# QA GENERATOR
# ============================================================================

# QA generation settings
QA_PAIRS_PER_CLUSTER = 5  # Target QA pairs per topic
MIN_THREAD_LENGTH = 5  # Minimum messages to use thread
MAX_THREADS_PER_CLUSTER = 5  # Top N threads to include in context
MAX_SOURCE_FILES_PER_CLUSTER = 10  # Top N files to include
INCLUDE_CODE_SNIPPETS = False  # Include actual code (increases prompt size)
MAX_CONTEXT_LENGTH = 6000  # Max characters in context
MAX_RETRIES = 3  # Retry attempts per cluster

# Generation parameters (override defaults if needed)
GENERATION_TEMPERATURE = 0.7
GENERATION_MAX_TOKENS = 3072

# Difficulty levels
DIFFICULTY_LEVELS = ['beginner', 'intermediate', 'advanced']

# Output files
QA_PAIRS_FILE = os.path.join(DATA_DIR, "qa_pairs.jsonl")
QA_CHECKPOINT_FILE = os.path.join(DATA_DIR, "qa_pairs_checkpoint.jsonl")

# ============================================================================
# DATASET BUILDER
# ============================================================================

# Dataset settings
DATASET_FILENAME = "pg_copilot_qa_dataset.jsonl"
REPORT_FILENAME = "dataset_report.json"
README_FILENAME = "README.md"

# Quality control
DEDUP_SIMILARITY_THRESHOLD = 0.85  # Similarity threshold for deduplication
MIN_ANSWER_LENGTH = 50  # Minimum answer length in characters
REQUIRE_SOURCE_FILES = False  # Require source file references
VALIDATE_FILE_PATHS = False  # Check if source files exist

# Output files
FINAL_DATASET_FILE = os.path.join(OUTPUT_DIR, DATASET_FILENAME)
DATASET_REPORT_FILE = os.path.join(OUTPUT_DIR, REPORT_FILENAME)
DATASET_README_FILE = os.path.join(OUTPUT_DIR, README_FILENAME)

# ============================================================================
# LOGGING
# ============================================================================

# Logging settings
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = os.path.join(PROJECT_ROOT, "pipeline.log")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ============================================================================
# MISC
# ============================================================================

# Random seed for reproducibility
RANDOM_SEED = 42

# Progress bars
SHOW_PROGRESS = True

# Verify paths exist
def verify_paths():
    """Verify critical paths exist."""
    errors = []

    if not os.path.exists(MODEL_PATH):
        errors.append(f"Model not found: {MODEL_PATH}")

    if not os.path.exists(PG_SOURCE_PATH):
        errors.append(f"PostgreSQL source not found: {PG_SOURCE_PATH}")

    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        return False

    return True
