# QA Generator Module Documentation

## Overview

The `qa_generator.py` module orchestrates the generation of question-answer pairs by combining mailing list discussions, topic clusters, PostgreSQL source code context, and LLM inference.

## Purpose

- Construct prompts with discussion + source context
- Generate 3-5 QA pairs per topic cluster using Qwen3-32B
- Parse and validate LLM JSON responses
- Handle generation errors and retries
- Track generation progress

## Architecture

```
┌──────────────────────────────────────────────────┐
│           QA Generator Module                     │
├──────────────────────────────────────────────────┤
│                                                   │
│  Input:                                           │
│    - data/clustered_topics.json                   │
│    - data/topic_source_mapping.json               │
│    - data/processed_threads.json                  │
│                                                   │
│  Process:                                         │
│    1. Load all input data                         │
│    2. Initialize LLM interface                    │
│    3. For each topic cluster:                     │
│       a. Build context (threads + source files)   │
│       b. Construct prompt                         │
│       c. Generate QA pairs via LLM                │
│       d. Parse and validate JSON response         │
│       e. Save QA pairs                            │
│    4. Aggregate all QA pairs                      │
│                                                   │
│  Output:                                          │
│    - data/qa_pairs.jsonl                          │
│                                                   │
└──────────────────────────────────────────────────┘
```

## Key Components

### 1. QAGenerator Class

Main class for QA pair generation.

```python
class QAGenerator:
    def __init__(
        self,
        llm_interface: LLMInterface,
        clustered_topics: Dict,
        source_mappings: Dict,
        processed_threads: Dict
    ):
        """
        Initialize QA generator.

        Args:
            llm_interface: Initialized LLM interface
            clustered_topics: Output from topic_clustering
            source_mappings: Output from pg_source_context
            processed_threads: Output from thread_parser
        """
        self.llm = llm_interface
        self.topics = clustered_topics
        self.source_mappings = source_mappings
        self.threads = processed_threads
        self.qa_pairs = []

    def generate_all(self, max_topics: int = None) -> List[Dict]:
        """
        Generate QA pairs for all topics.

        Args:
            max_topics: Limit number of topics (for testing)

        Returns:
            List of QA pair dictionaries
        """

    def generate_for_topic(self, cluster_id: int) -> List[Dict]:
        """Generate QA pairs for a single topic cluster."""

    def save_to_jsonl(self, output_path: str):
        """Save QA pairs to JSONL file."""
```

### 2. Core Functions

#### `build_topic_context(cluster: Dict, source_mapping: Dict, threads: Dict) -> str`

Constructs context string for prompt.

**Structure:**
```
TOPIC: {cluster_label}
KEYWORDS: {keywords}

DISCUSSION THREADS ({n} threads):

Thread 1: {subject}
Date: {start_date} to {end_date}
Messages: {message_count}

{aggregated_content}

---

Thread 2: ...

RELEVANT SOURCE FILES ({n} files):

File: src/backend/optimizer/plan/planner.c
Component: optimizer
Functions: standard_planner, subquery_planner

File: src/backend/partitioning/partprune.c
Component: partitioning
Functions: make_partition_pruneinfo, prune_append_rel_partitions
```

**Implementation:**
```python
def build_topic_context(
    cluster: Dict,
    source_mapping: Dict,
    threads_data: Dict
) -> str:
    """
    Build comprehensive context for QA generation.

    Args:
        cluster: Topic cluster from clustered_topics
        source_mapping: Source mapping for this cluster
        threads_data: All processed threads

    Returns:
        Formatted context string
    """
    context_parts = []

    # Topic header
    context_parts.append(f"TOPIC: {cluster['label']}")
    context_parts.append(f"KEYWORDS: {', '.join(cluster['keywords'])}")
    context_parts.append("")

    # Discussion threads
    context_parts.append(f"DISCUSSION THREADS ({cluster['thread_count']} threads):")
    context_parts.append("")

    for i, thread_ref in enumerate(cluster['threads'][:5], 1):  # Limit to top 5
        thread_id = thread_ref['thread_id']
        thread = threads_data[thread_id]

        context_parts.append(f"Thread {i}: {thread['subject']}")
        context_parts.append(f"Date: {thread['start_date']} to {thread['end_date']}")
        context_parts.append(f"Messages: {thread['message_count']}")
        context_parts.append("")

        # Truncate content if too long
        content = thread['aggregated_content']
        if len(content) > 2000:
            content = content[:2000] + "... [truncated]"

        context_parts.append(content)
        context_parts.append("")
        context_parts.append("---")
        context_parts.append("")

    # Source files
    if source_mapping and 'source_files' in source_mapping:
        context_parts.append(f"RELEVANT SOURCE FILES ({len(source_mapping['source_files'])} files):")
        context_parts.append("")

        for file_info in source_mapping['source_files'][:10]:  # Limit to top 10
            context_parts.append(f"File: {file_info['file_path']}")
            context_parts.append(f"Component: {file_info['component']}")

            if 'functions' in file_info and file_info['functions']:
                context_parts.append(f"Functions: {', '.join(file_info['functions'][:5])}")

            context_parts.append("")

    return '\n'.join(context_parts)
```

#### `build_qa_prompt(context: str, n_pairs: int = 5) -> str`

Constructs full prompt for LLM.

**Template:**
```python
def build_qa_prompt(context: str, n_pairs: int = 5) -> str:
    """
    Build prompt for QA generation.

    Args:
        context: Topic context from build_topic_context
        n_pairs: Number of QA pairs to generate

    Returns:
        Formatted prompt
    """
    prompt = f"""You are a PostgreSQL internals expert with deep knowledge of PostgreSQL 17 architecture and source code.

Based on the developer discussion threads and related source code context below, generate {n_pairs} high-quality question-answer pairs that test deep understanding of PostgreSQL internals.

Requirements:
- Questions should be specific and technical, focusing on architecture, algorithms, and implementation details
- Answers should be comprehensive, accurate, and reference specific source code components when relevant
- Cover different aspects of the topic (design decisions, performance implications, edge cases, etc.)
- Questions should be at the level of an experienced PostgreSQL developer or contributor
- Include code examples or file references in answers when appropriate

{context}

Generate exactly {n_pairs} question-answer pairs in the following JSON format:

[
  {{
    "question": "How does PostgreSQL's partition pruning work during query planning?",
    "answer": "PostgreSQL's partition pruning in the query planner is implemented in src/backend/partitioning/partprune.c. During planning, the function make_partition_pruneinfo() analyzes partition key constraints and query predicates to determine which partitions can be safely excluded. The planner builds a pruning structure that encodes partition bounds and generates pruning steps that test query clauses against these bounds. This happens in standard_planner() before the executor runs, allowing the executor to skip entire partition scans. Runtime pruning can also occur in the executor when predicates contain parameter values not known at plan time.",
    "difficulty": "advanced",
    "topics": ["query_planner", "partitioning", "optimization"]
  }},
  {{
    "question": "...",
    "answer": "...",
    "difficulty": "intermediate",
    "topics": [...]
  }}
]

Output ONLY the JSON array, no additional text.
"""

    return prompt
```

#### `parse_qa_response(response: str) -> List[Dict]`

Parses JSON response from LLM.

**Implementation:**
```python
import json
import re

def parse_qa_response(response: str) -> List[Dict]:
    """
    Parse QA pairs from LLM response.

    Handles:
    - Markdown code blocks
    - Extra whitespace
    - Malformed JSON

    Returns:
        List of QA pair dictionaries
    """
    # Remove markdown code blocks if present
    response = response.strip()
    if response.startswith('```'):
        # Extract content between ```json and ```
        match = re.search(r'```(?:json)?\n(.*?)\n```', response, re.DOTALL)
        if match:
            response = match.group(1)
        else:
            # Remove first and last lines
            lines = response.split('\n')
            response = '\n'.join(lines[1:-1])

    # Try to parse JSON
    try:
        qa_pairs = json.loads(response)

        # Validate structure
        if not isinstance(qa_pairs, list):
            raise ValueError("Response is not a list")

        for qa in qa_pairs:
            if 'question' not in qa or 'answer' not in qa:
                raise ValueError("Missing question or answer field")

        return qa_pairs

    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Response: {response[:500]}...")
        return []
    except ValueError as e:
        print(f"Validation error: {e}")
        return []
```

#### `generate_for_topic(cluster: Dict, llm: LLMInterface, ...) -> List[Dict]`

Generates QA pairs for a single topic.

**Implementation:**
```python
def generate_for_topic(
    cluster: Dict,
    source_mapping: Dict,
    threads_data: Dict,
    llm: LLMInterface,
    n_pairs: int = 5,
    max_retries: int = 3
) -> List[Dict]:
    """
    Generate QA pairs for one topic cluster.

    Args:
        cluster: Topic cluster
        source_mapping: Source mapping for cluster
        threads_data: All threads
        llm: LLM interface
        n_pairs: Number of QA pairs to generate
        max_retries: Retry attempts on failure

    Returns:
        List of QA pairs with metadata
    """
    # Build context
    context = build_topic_context(cluster, source_mapping, threads_data)

    # Build prompt
    prompt = build_qa_prompt(context, n_pairs)

    # Generate with retries
    qa_pairs = []
    for attempt in range(max_retries):
        try:
            # Generate
            response = llm.generate(
                prompt=prompt,
                max_tokens=3072,
                temperature=0.7,
                top_p=0.9
            )

            # Parse
            qa_pairs = parse_qa_response(response)

            if qa_pairs:
                break  # Success
            else:
                print(f"Attempt {attempt + 1}: Failed to parse response")

        except Exception as e:
            print(f"Attempt {attempt + 1}: Error during generation: {e}")

        if attempt < max_retries - 1:
            time.sleep(2)

    # Add metadata
    for qa in qa_pairs:
        qa['cluster_id'] = cluster.get('cluster_id')
        qa['cluster_label'] = cluster['label']
        qa['source_files'] = [f['file_path'] for f in source_mapping.get('source_files', [])[:5]]
        qa['thread_ids'] = [t['thread_id'] for t in cluster['threads'][:5]]
        qa['generated_at'] = datetime.now().isoformat()

    return qa_pairs
```

## Data Flow

```
Topics + Threads + Source → Context Building → Prompt → LLM → JSON Response → Parsed QA Pairs
        ↓                         ↓              ↓       ↓          ↓              ↓
   (loaded data)          (combined context)  (prompt) (gen)   (validated)   qa_pairs.jsonl
```

## Output Format

### qa_pairs.jsonl

**Format:** One JSON object per line

```json
{"question": "How does PostgreSQL's MVCC system determine tuple visibility?", "answer": "PostgreSQL's MVCC implementation uses transaction IDs (xmin/xmax) stored in each tuple header to determine visibility. The function HeapTupleSatisfiesMVCC() in src/backend/access/heap/heapam.c implements the core visibility rules. It checks if the tuple's xmin (creating transaction) is committed and visible to the current snapshot, and if xmax (deleting transaction) is either invalid or not yet committed/visible. The snapshot structure contains xmin/xmax thresholds and a list of in-progress transactions, allowing each transaction to see a consistent view of the database without blocking writers.", "difficulty": "advanced", "topics": ["mvcc", "transaction", "visibility"], "cluster_id": 2, "cluster_label": "mvcc_visibility_vacuum_bloat", "source_files": ["src/backend/access/heap/heapam.c", "src/include/access/htup_details.h", "src/backend/utils/time/tqual.c"], "thread_ids": ["20230520-mvcc-performance", "20230603-vacuum-bloat"], "generated_at": "2025-10-02T15:30:45"}
{"question": "What is the purpose of the visibility map in PostgreSQL?", "answer": "The visibility map (VM) is a bitmap structure in PostgreSQL that tracks which heap pages contain only tuples visible to all transactions. Implemented in src/backend/access/heap/visibilitymap.c, each bit represents one heap page. When all tuples on a page are visible to all transactions and have no dead tuples, the page is marked in the VM. This optimization allows VACUUM to skip pages that don't need processing and enables index-only scans by indicating which heap pages don't need to be checked for tuple visibility. The VM is stored in files with the '_vm' suffix.", "difficulty": "intermediate", "topics": ["vacuum", "visibility_map", "storage"], "cluster_id": 2, "cluster_label": "mvcc_visibility_vacuum_bloat", "source_files": ["src/backend/access/heap/visibilitymap.c", "src/backend/access/heap/vacuumlazy.c"], "thread_ids": ["20230520-mvcc-performance"], "generated_at": "2025-10-02T15:30:45"}
```

## Configuration

Key settings in `config.py`:

```python
# QA generation configuration
QA_PAIRS_PER_CLUSTER = 5  # Target QA pairs per topic
MIN_THREAD_LENGTH = 5  # Minimum messages to use thread
MAX_THREADS_PER_CLUSTER = 5  # Top N threads to include in context
MAX_SOURCE_FILES_PER_CLUSTER = 10  # Top N files to include
INCLUDE_CODE_SNIPPETS = False  # Include actual code (increases prompt size)
MAX_CONTEXT_LENGTH = 6000  # Max characters in context
MAX_RETRIES = 3  # Retry attempts per cluster
GENERATION_TEMPERATURE = 0.7
GENERATION_MAX_TOKENS = 3072

# Difficulty levels
DIFFICULTY_LEVELS = ['beginner', 'intermediate', 'advanced']
```

## Usage Examples

### Basic Usage

```python
from qa_generator import QAGenerator
from llm_interface import LLMInterface
import json

# Load data
with open('data/clustered_topics.json', 'r') as f:
    clustered_topics = json.load(f)

with open('data/topic_source_mapping.json', 'r') as f:
    source_mappings = json.load(f)

with open('data/processed_threads.json', 'r') as f:
    processed_threads = json.load(f)

# Initialize LLM
llm = LLMInterface(
    model_path=MODEL_PATH,
    n_ctx=8192,
    n_gpu_layers=-1
)
llm.load_model()

# Create generator
generator = QAGenerator(
    llm_interface=llm,
    clustered_topics=clustered_topics,
    source_mappings=source_mappings,
    processed_threads=processed_threads
)

# Generate all QA pairs
qa_pairs = generator.generate_all()

# Save to JSONL
generator.save_to_jsonl('data/qa_pairs.jsonl')

print(f"Generated {len(qa_pairs)} QA pairs")

# Unload model
llm.unload_model()
```

### Incremental Generation with Checkpoints

```python
from qa_generator import QAGenerator
import json
from tqdm import tqdm

# Load data
...

# Initialize
llm = LLMInterface(...)
llm.load_model()

generator = QAGenerator(...)

# Load existing QA pairs if resuming
existing_qa = []
checkpoint_file = 'data/qa_pairs_checkpoint.jsonl'
if os.path.exists(checkpoint_file):
    with open(checkpoint_file, 'r') as f:
        existing_qa = [json.loads(line) for line in f]

processed_clusters = {qa['cluster_id'] for qa in existing_qa}

# Generate for remaining clusters
for cluster in tqdm(clustered_topics['clusters']):
    if cluster['cluster_id'] in processed_clusters:
        continue  # Skip already processed

    # Find source mapping
    source_mapping = next(
        (m for m in source_mappings['topic_mappings'] if m['cluster_id'] == cluster['cluster_id']),
        {}
    )

    # Generate
    qa_pairs = generator.generate_for_topic(cluster['cluster_id'])

    # Append to checkpoint
    with open(checkpoint_file, 'a') as f:
        for qa in qa_pairs:
            f.write(json.dumps(qa) + '\n')

print("Generation complete")
```

### Quality Filtering

```python
def filter_qa_pairs(qa_pairs: List[Dict]) -> List[Dict]:
    """
    Filter QA pairs by quality heuristics.
    """
    filtered = []

    for qa in qa_pairs:
        # Skip if answer is too short
        if len(qa['answer']) < 100:
            continue

        # Skip if question doesn't end with '?'
        if not qa['question'].strip().endswith('?'):
            continue

        # Skip if answer contains obvious errors
        if 'I don\'t know' in qa['answer'] or 'cannot answer' in qa['answer'].lower():
            continue

        # Skip if no source files referenced
        if not qa.get('source_files'):
            continue

        filtered.append(qa)

    return filtered

# Apply filter
qa_pairs = generator.generate_all()
filtered_qa = filter_qa_pairs(qa_pairs)
print(f"Filtered: {len(qa_pairs)} → {len(filtered_qa)} QA pairs")
```

## Performance Considerations

### Estimated Metrics

- **Per-topic generation:** 1-2 minutes (5 QA pairs)
- **Total topics:** 30-50
- **Total time:** 30-100 minutes
- **Expected output:** 150-250 QA pairs (5 per topic)

### Optimization Strategies

1. **Parallel Generation (Experimental)**
   ```python
   # Use multiple LLM instances if you have multiple GPUs
   # Not applicable for single RTX 3090
   ```

2. **Batch Similar Topics**
   ```python
   # Generate multiple related topics in one prompt
   # Trade-off: less focused QA pairs
   ```

3. **Cache Contexts**
   ```python
   # Pre-build all contexts to avoid recomputation
   contexts = {}
   for cluster in clusters:
       contexts[cluster['cluster_id']] = build_topic_context(...)

   # Then generate
   for cluster_id, context in contexts.items():
       qa_pairs = generate(context)
   ```

4. **Skip Low-Value Topics**
   ```python
   # Skip clusters with too few threads or poor source mappings
   min_threads = 3
   min_source_files = 1

   clusters_to_process = [
       c for c in clusters
       if c['thread_count'] >= min_threads
       and len(get_source_mapping(c)) >= min_source_files
   ]
   ```

## Dependencies

```
json
re
datetime
time
tqdm
```

## Testing

### Unit Tests

```python
import unittest
from qa_generator import parse_qa_response, build_qa_prompt

class TestQAGenerator(unittest.TestCase):
    def test_parse_valid_json(self):
        response = '''[
            {"question": "Q1?", "answer": "A1", "difficulty": "intermediate", "topics": ["t1"]},
            {"question": "Q2?", "answer": "A2", "difficulty": "advanced", "topics": ["t2"]}
        ]'''
        qa_pairs = parse_qa_response(response)
        self.assertEqual(len(qa_pairs), 2)
        self.assertEqual(qa_pairs[0]['question'], 'Q1?')

    def test_parse_markdown_json(self):
        response = '''```json
        [{"question": "Q?", "answer": "A", "difficulty": "beginner", "topics": []}]
        ```'''
        qa_pairs = parse_qa_response(response)
        self.assertEqual(len(qa_pairs), 1)
```

## Troubleshooting

### LLM Returns Non-JSON

**Symptoms:** Parsing errors, empty QA pairs

**Solutions:**
- Check prompt clarity
- Add explicit "Output ONLY JSON" instruction
- Increase temperature slightly (0.7 → 0.8)
- Add JSON schema example

### Low Quality QA Pairs

**Symptoms:** Generic questions, short answers

**Solutions:**
- Improve context quality (better threads, more source files)
- Adjust prompt to emphasize technical depth
- Use lower temperature (0.5-0.6) for more focused output
- Add few-shot examples in prompt

### Generation Too Slow

**Symptoms:** >5 minutes per topic

**Solutions:**
- Reduce `QA_PAIRS_PER_CLUSTER` (5 → 3)
- Reduce `MAX_TOKENS` (3072 → 2048)
- Truncate context more aggressively
- Skip topics with excessive thread content

### GPU OOM During Generation

**Symptoms:** CUDA out of memory errors

**Solutions:**
- Reduce context length
- Reduce `MAX_TOKENS`
- Reduce `N_CTX` in LLM config
- Generate in smaller batches

## Next Steps

After QA generation completes:
1. Review sample QA pairs for quality
2. Check distribution across topics
3. Proceed to `dataset_builder.py` for final assembly
