# PostgreSQL Source Context Module Documentation

## Overview

The `pg_source_context.py` module maps mailing list discussion topics to relevant PostgreSQL 17.6 source code files, enabling LLM to generate QA pairs with concrete code context.

## Purpose

- Map topic clusters to relevant PG source files
- Identify files mentioned in email discussions
- Use heuristic matching (keywords → file paths)
- Extract relevant code snippets for context

## Architecture

```
┌──────────────────────────────────────────────────┐
│      PostgreSQL Source Context Module             │
├──────────────────────────────────────────────────┤
│                                                   │
│  Input:                                           │
│    - data/clustered_topics.json                   │
│    - C:\Users\user\postgres-REL_17_6              │
│                                                   │
│  Process:                                         │
│    1. Build PG source file index                  │
│    2. Extract file mentions from threads          │
│    3. Map keywords to source directories          │
│    4. Rank files by relevance                     │
│    5. Extract function signatures (optional)      │
│                                                   │
│  Output:                                          │
│    - data/topic_source_mapping.json               │
│                                                   │
└──────────────────────────────────────────────────┘
```

## Key Components

### 1. SourceContextMapper Class

Main class for mapping topics to source code.

```python
class SourceContextMapper:
    def __init__(self, pg_source_path: str, clustered_topics: Dict):
        """
        Initialize mapper.

        Args:
            pg_source_path: Path to PostgreSQL 17.6 source code
            clustered_topics: Output from topic_clustering
        """
        self.pg_source_path = pg_source_path
        self.topics = clustered_topics
        self.file_index = None

    def build_file_index(self):
        """Index all source files in PostgreSQL codebase."""

    def map_topics_to_source(self) -> Dict:
        """
        Map each topic cluster to relevant source files.

        Returns:
            Topic-source mapping dictionary
        """

    def save_to_json(self, output_path: str):
        """Save mapping to JSON file."""
```

### 2. Core Functions

#### `build_file_index(pg_source_path: str) -> Dict[str, Dict]`

Creates searchable index of PostgreSQL source files.

**Structure:**
```python
{
    "src/backend/optimizer/plan/planner.c": {
        "full_path": "C:/Users/user/postgres-REL_17_6/src/backend/optimizer/plan/planner.c",
        "relative_path": "src/backend/optimizer/plan/planner.c",
        "component": "optimizer",
        "subsystem": "backend",
        "language": "c",
        "size_bytes": 125643,
        "functions": ["standard_planner", "subquery_planner", ...],
        "keywords": ["planner", "optimizer", "plan", "query"]
    },
    ...
}
```

**Implementation:**
```python
import os
from pathlib import Path

def build_file_index(pg_source_path: str) -> Dict[str, Dict]:
    """
    Index all .c, .h files in PostgreSQL source.
    """
    file_index = {}

    # Walk source tree
    for root, dirs, files in os.walk(pg_source_path):
        # Skip build artifacts
        if 'build' in root or '.git' in root:
            continue

        for filename in files:
            if not filename.endswith(('.c', '.h')):
                continue

            full_path = os.path.join(root, filename)
            relative_path = os.path.relpath(full_path, pg_source_path)

            # Extract metadata
            file_info = {
                'full_path': full_path,
                'relative_path': relative_path.replace('\\', '/'),
                'component': extract_component(relative_path),
                'subsystem': extract_subsystem(relative_path),
                'language': 'c' if filename.endswith('.c') else 'h',
                'size_bytes': os.path.getsize(full_path),
                'functions': [],  # Populated later if needed
                'keywords': extract_keywords_from_path(relative_path)
            }

            file_index[relative_path.replace('\\', '/')] = file_info

    return file_index
```

#### `extract_component(file_path: str) -> str`

Identifies PostgreSQL component from file path.

**Examples:**
```python
extract_component("src/backend/optimizer/plan/planner.c")  # → "optimizer"
extract_component("src/backend/access/heap/heapam.c")      # → "heap"
extract_component("src/backend/replication/logical/worker.c")  # → "logical_replication"
extract_component("src/include/storage/bufmgr.h")          # → "buffer_manager"
```

**Implementation:**
```python
def extract_component(file_path: str) -> str:
    """
    Extract component name from path.
    """
    parts = file_path.replace('\\', '/').split('/')

    # src/backend/<component>/...
    if 'backend' in parts:
        idx = parts.index('backend')
        if idx + 1 < len(parts):
            return parts[idx + 1]

    # src/include/<component>/...
    if 'include' in parts:
        idx = parts.index('include')
        if idx + 1 < len(parts):
            return parts[idx + 1]

    return 'unknown'
```

#### `extract_file_mentions(thread_texts: List[str]) -> List[str]`

Finds explicit file path mentions in emails.

**Patterns:**
- `src/backend/optimizer/plan/planner.c`
- `heapam.c`
- `bufmgr.h`

**Implementation:**
```python
import re

def extract_file_mentions(thread_texts: List[str]) -> List[str]:
    """
    Extract file paths mentioned in discussions.
    """
    mentioned_files = []

    for text in thread_texts:
        # Match .c and .h file references
        matches = re.findall(r'[\w/]+\.(?:c|h)\b', text)
        mentioned_files.extend(matches)

        # Match src/... paths
        matches = re.findall(r'src/[\w/]+\.(?:c|h)', text)
        mentioned_files.extend(matches)

    # Deduplicate
    return list(set(mentioned_files))
```

#### `map_keywords_to_files(keywords: List[str], file_index: Dict) -> List[Tuple[str, float]]`

Maps topic keywords to relevant source files using heuristics.

**Keyword → Component Mapping:**
```python
KEYWORD_TO_COMPONENT = {
    # Query processing
    'planner': ['optimizer/plan', 'optimizer/path', 'optimizer/prep'],
    'optimizer': ['optimizer'],
    'executor': ['executor'],
    'parser': ['parser'],

    # Storage
    'heap': ['access/heap'],
    'index': ['access/index', 'access/nbtree', 'access/hash', 'access/gist'],
    'btree': ['access/nbtree'],
    'buffer': ['storage/buffer'],
    'smgr': ['storage/smgr'],

    # Transactions
    'mvcc': ['access/heap', 'access/transam'],
    'vacuum': ['commands/vacuum'],
    'transaction': ['access/transam'],
    'xact': ['access/transam'],

    # WAL & Replication
    'wal': ['access/transam', 'access/wal'],
    'replication': ['replication'],
    'logical decoding': ['replication/logical'],
    'slot': ['replication/slot'],

    # Utility
    'autovacuum': ['postmaster/autovacuum'],
    'bgwriter': ['postmaster/bgwriter'],
    'checkpoint': ['postmaster/checkpointer'],
}
```

**Implementation:**
```python
def map_keywords_to_files(keywords: List[str], file_index: Dict) -> List[Tuple[str, float]]:
    """
    Map keywords to files with relevance scores.

    Returns:
        List of (file_path, score) tuples, sorted by score
    """
    file_scores = defaultdict(float)

    for keyword in keywords:
        keyword_lower = keyword.lower()

        # Check direct component mapping
        if keyword_lower in KEYWORD_TO_COMPONENT:
            for component_path in KEYWORD_TO_COMPONENT[keyword_lower]:
                # Find all files in this component
                for file_path, file_info in file_index.items():
                    if component_path in file_path:
                        file_scores[file_path] += 1.0

        # Check file path keywords
        for file_path, file_info in file_index.items():
            if keyword_lower in ' '.join(file_info['keywords']).lower():
                file_scores[file_path] += 0.5

            # Check filename match
            if keyword_lower in os.path.basename(file_path).lower():
                file_scores[file_path] += 0.8

    # Sort by score
    ranked_files = sorted(file_scores.items(), key=lambda x: x[1], reverse=True)

    return ranked_files
```

#### `extract_function_signatures(file_path: str) -> List[str]`

Extracts function signatures from C source files (optional, for richer context).

**Pattern:**
```c
/* Function signature examples */
Plan *
standard_planner(Query *parse, int cursorOptions, ParamListInfo boundParams)

static void
create_partition_pruning_info(PlannerInfo *root)
```

**Implementation:**
```python
import re

def extract_function_signatures(file_path: str, limit: int = 10) -> List[str]:
    """
    Extract function signatures from .c file.

    Args:
        file_path: Path to .c file
        limit: Maximum signatures to extract

    Returns:
        List of function signatures
    """
    if not file_path.endswith('.c'):
        return []

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return []

    # Simple regex to find function definitions
    # Matches: <return_type> <function_name>(<params>)
    pattern = r'^[\w\s\*]+\n(\w+)\s*\([^)]*\)\s*\n?{'

    signatures = []
    for match in re.finditer(pattern, content, re.MULTILINE):
        # Extract surrounding lines for context
        start = max(0, match.start() - 100)
        end = min(len(content), match.end() + 50)
        snippet = content[start:end].strip()

        signatures.append(snippet)

        if len(signatures) >= limit:
            break

    return signatures
```

## Data Flow

```
Clustered Topics → File Index → Keyword Mapping → File Mentions → Ranked Files → Snippets
       ↓              ↓              ↓                ↓               ↓            ↓
   (keywords)    (PG source)  (heuristics)       (extracted)     (scored)   topic_source_mapping.json
```

## Output Format

### topic_source_mapping.json

```json
{
  "topic_mappings": [
    {
      "cluster_id": 0,
      "label": "query_planner_partition_pruning_optimizer",
      "keywords": ["query planner", "partition pruning", "optimizer"],
      "thread_count": 23,
      "source_files": [
        {
          "file_path": "src/backend/optimizer/plan/planner.c",
          "full_path": "C:/Users/user/postgres-REL_17_6/src/backend/optimizer/plan/planner.c",
          "relevance_score": 3.5,
          "component": "optimizer",
          "mentioned_in_threads": ["20230415-planner-optimization"],
          "functions": [
            "standard_planner",
            "subquery_planner",
            "create_partition_pruning_info"
          ]
        },
        {
          "file_path": "src/backend/optimizer/util/plancat.c",
          "full_path": "C:/Users/user/postgres-REL_17_6/src/backend/optimizer/util/plancat.c",
          "relevance_score": 2.3,
          "component": "optimizer",
          "mentioned_in_threads": [],
          "functions": ["get_relation_info", "estimate_rel_size"]
        },
        {
          "file_path": "src/backend/partitioning/partprune.c",
          "full_path": "C:/Users/user/postgres-REL_17_6/src/backend/partitioning/partprune.c",
          "relevance_score": 2.8,
          "component": "partitioning",
          "mentioned_in_threads": ["20230501-runtime-pruning"],
          "functions": ["make_partition_pruneinfo", "prune_append_rel_partitions"]
        }
      ],
      "top_components": ["optimizer", "partitioning", "executor"]
    },
    {
      "cluster_id": 1,
      "label": "wal_replication_logical_decoding",
      "keywords": ["wal", "replication", "logical decoding"],
      "thread_count": 15,
      "source_files": [
        {
          "file_path": "src/backend/replication/logical/decode.c",
          "relevance_score": 4.2,
          "component": "logical_replication",
          "mentioned_in_threads": ["20230312-logical-decoding-perf"],
          "functions": ["LogicalDecodingProcessRecord", "DecodeXLogOp"]
        },
        {
          "file_path": "src/backend/access/transam/xlog.c",
          "relevance_score": 3.1,
          "component": "wal",
          "mentioned_in_threads": [],
          "functions": ["XLogInsert", "XLogFlush"]
        }
      ],
      "top_components": ["replication", "wal", "transam"]
    }
  ],
  "metadata": {
    "total_topics": 42,
    "total_source_files_mapped": 187,
    "pg_source_path": "C:/Users/user/postgres-REL_17_6",
    "indexed_files": 1523,
    "avg_files_per_topic": 4.5
  }
}
```

## Configuration

Key settings in `config.py`:

```python
# Source context configuration
PG_SOURCE_PATH = r"C:\Users\user\postgres-REL_17_6"
EXTRACT_FUNCTIONS = True  # Extract function signatures
MAX_FILES_PER_TOPIC = 10  # Top N files to include
MIN_RELEVANCE_SCORE = 0.5  # Minimum score to include file
INCLUDE_HEADERS = True  # Include .h files or only .c
MAX_FUNCTION_SNIPPETS = 5  # Function signatures per file
```

## PostgreSQL Source Structure Reference

```
postgres-REL_17_6/
├── src/
│   ├── backend/
│   │   ├── access/          # Storage access methods
│   │   │   ├── heap/        # Heap storage
│   │   │   ├── index/       # Index access
│   │   │   ├── nbtree/      # B-tree index
│   │   │   ├── hash/        # Hash index
│   │   │   ├── gin/         # GIN index
│   │   │   ├── gist/        # GiST index
│   │   │   ├── transam/     # Transaction management
│   │   │   └── wal/         # Write-Ahead Logging
│   │   ├── optimizer/       # Query optimizer
│   │   │   ├── path/        # Path generation
│   │   │   ├── plan/        # Plan creation
│   │   │   ├── prep/        # Preprocessing
│   │   │   └── util/        # Optimizer utilities
│   │   ├── executor/        # Query executor
│   │   ├── parser/          # SQL parser
│   │   ├── commands/        # SQL commands (DDL, DML)
│   │   ├── replication/     # Replication
│   │   │   ├── logical/     # Logical replication
│   │   │   └── slot/        # Replication slots
│   │   ├── storage/         # Storage management
│   │   │   ├── buffer/      # Buffer manager
│   │   │   ├── smgr/        # Storage manager
│   │   │   └── page/        # Page operations
│   │   ├── catalog/         # System catalogs
│   │   ├── utils/           # Utilities
│   │   └── postmaster/      # Background processes
│   └── include/             # Header files
│       ├── access/
│       ├── optimizer/
│       ├── executor/
│       └── storage/
```

## Usage Examples

### Basic Usage

```python
from pg_source_context import SourceContextMapper
import json

# Load clustered topics
with open('data/clustered_topics.json', 'r') as f:
    clustered_topics = json.load(f)

# Map to source files
mapper = SourceContextMapper(
    pg_source_path=r"C:\Users\user\postgres-REL_17_6",
    clustered_topics=clustered_topics
)

# Build file index
mapper.build_file_index()

# Map topics to source
topic_mappings = mapper.map_topics_to_source()

# Save results
mapper.save_to_json('data/topic_source_mapping.json')

print(f"Mapped {len(topic_mappings['topic_mappings'])} topics to source files")
```

### Advanced: Custom Keyword Mapping

```python
from pg_source_context import SourceContextMapper

# Custom keyword mappings for specialized topics
CUSTOM_MAPPINGS = {
    'jit compilation': ['jit'],
    'parallel query': ['executor/nodeGather', 'executor/nodeGatherMerge'],
    'foreign data wrapper': ['foreign'],
    'partition': ['partitioning', 'executor/nodeAppend'],
}

mapper = SourceContextMapper(...)
mapper.keyword_component_map.update(CUSTOM_MAPPINGS)
topic_mappings = mapper.map_topics_to_source()
```

### Finding Source Files by Topic

```python
def get_source_files_for_topic(topic_label: str, mapping_data: Dict) -> List[str]:
    """
    Get source files for a specific topic.
    """
    for topic in mapping_data['topic_mappings']:
        if topic_label in topic['label']:
            return [f['file_path'] for f in topic['source_files']]
    return []

# Example
with open('data/topic_source_mapping.json', 'r') as f:
    mappings = json.load(f)

planner_files = get_source_files_for_topic('planner', mappings)
print(f"Planner-related files: {planner_files}")
```

## Performance Considerations

### Estimated Metrics

- **File indexing:** 30 seconds - 1 minute (1500+ files)
- **Keyword mapping:** 10-20 seconds
- **Function extraction:** 2-5 minutes (if enabled)
- **Total time:** ~5 minutes

### Optimization Strategies

1. **Cache File Index**
   ```python
   # Save file index to avoid rebuilding
   with open('data/file_index.json', 'w') as f:
       json.dump(file_index, f, indent=2)
   ```

2. **Parallel Function Extraction**
   ```python
   from multiprocessing import Pool

   def extract_parallel(file_paths):
       with Pool(processes=8) as pool:
           results = pool.map(extract_function_signatures, file_paths)
       return results
   ```

3. **Limit Scope**
   ```python
   # Only index relevant directories
   INCLUDE_DIRS = ['src/backend', 'src/include']
   EXCLUDE_DIRS = ['src/test', 'contrib']
   ```

## Dependencies

```
pathlib
re
json
```

## Testing

### Unit Tests

```python
import unittest
from pg_source_context import extract_component, extract_file_mentions

class TestSourceContext(unittest.TestCase):
    def test_extract_component(self):
        self.assertEqual(
            extract_component("src/backend/optimizer/plan/planner.c"),
            "optimizer"
        )

    def test_extract_file_mentions(self):
        text = "See planner.c and src/backend/executor/execMain.c"
        mentions = extract_file_mentions([text])
        self.assertIn("planner.c", mentions)
        self.assertIn("src/backend/executor/execMain.c", mentions)
```

## Troubleshooting

### No Source Files Mapped

**Issue:** Topics not mapped to any files

**Solutions:**
- Check `PG_SOURCE_PATH` is correct
- Verify file index was built
- Add custom keyword mappings
- Lower `MIN_RELEVANCE_SCORE`

### Irrelevant Files Included

**Issue:** Mapped files not related to topic

**Solutions:**
- Increase `MIN_RELEVANCE_SCORE`
- Refine keyword-to-component mapping
- Add negative filters
- Review topic keywords quality

### Function Extraction Fails

**Issue:** Can't extract function signatures

**Solutions:**
- Check file encoding (use `errors='ignore'`)
- Improve regex pattern
- Skip header files (only process .c)
- Validate file paths exist

## Next Steps

After source mapping completes:
1. Verify mappings in `data/topic_source_mapping.json`
2. Check file relevance scores
3. Proceed to `llm_interface.py` for LLM setup
