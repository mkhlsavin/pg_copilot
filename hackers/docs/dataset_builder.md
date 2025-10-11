# Dataset Builder Module Documentation

## Overview

The `dataset_builder.py` module aggregates, validates, and formats QA pairs into a final dataset suitable for evaluating the PostgreSQL copilot RAG system.

## Purpose

- Load and validate QA pairs from JSONL
- Add metadata and enrichment
- Generate statistics and quality reports
- Export final dataset in standardized format
- Create dataset documentation

## Architecture

```
┌──────────────────────────────────────────────────┐
│          Dataset Builder Module                   │
├──────────────────────────────────────────────────┤
│                                                   │
│  Input:                                           │
│    - data/qa_pairs.jsonl                          │
│                                                   │
│  Process:                                         │
│    1. Load all QA pairs                           │
│    2. Validate structure and quality              │
│    3. Deduplicate similar questions               │
│    4. Add metadata (IDs, timestamps, versions)    │
│    5. Calculate statistics                        │
│    6. Generate dataset report                     │
│    7. Export in final format                      │
│                                                   │
│  Output:                                          │
│    - output/pg_copilot_qa_dataset.jsonl           │
│    - output/dataset_report.json                   │
│    - output/README.md                             │
│                                                   │
└──────────────────────────────────────────────────┘
```

## Key Components

### 1. DatasetBuilder Class

Main class for dataset assembly.

```python
class DatasetBuilder:
    def __init__(self, qa_pairs_file: str):
        """
        Initialize dataset builder.

        Args:
            qa_pairs_file: Path to qa_pairs.jsonl
        """
        self.qa_pairs_file = qa_pairs_file
        self.qa_pairs = []
        self.stats = {}

    def load_qa_pairs(self):
        """Load QA pairs from JSONL."""

    def validate_qa_pairs(self) -> Dict:
        """
        Validate QA pair structure and quality.

        Returns:
            Validation report
        """

    def deduplicate(self, similarity_threshold: float = 0.85):
        """Remove duplicate or highly similar questions."""

    def add_metadata(self):
        """Add unique IDs and metadata to each QA pair."""

    def generate_statistics(self) -> Dict:
        """Generate dataset statistics."""

    def export_dataset(self, output_path: str):
        """Export final dataset."""

    def create_report(self, output_path: str):
        """Create dataset report."""
```

### 2. Core Functions

#### `load_qa_pairs(file_path: str) -> List[Dict]`

Loads QA pairs from JSONL file.

**Implementation:**
```python
import json

def load_qa_pairs(file_path: str) -> List[Dict]:
    """
    Load QA pairs from JSONL file.

    Args:
        file_path: Path to qa_pairs.jsonl

    Returns:
        List of QA pair dictionaries
    """
    qa_pairs = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                qa = json.loads(line.strip())
                qa['_line_number'] = line_num
                qa_pairs.append(qa)
            except json.JSONDecodeError as e:
                print(f"Error parsing line {line_num}: {e}")
                continue

    return qa_pairs
```

#### `validate_qa_pairs(qa_pairs: List[Dict]) -> Dict`

Validates QA pair quality and structure.

**Validation Rules:**
1. Required fields present
2. Non-empty question and answer
3. Question ends with '?'
4. Answer length > 50 characters
5. Topics list is valid
6. Source files exist (optional)

**Implementation:**
```python
def validate_qa_pairs(qa_pairs: List[Dict]) -> Dict:
    """
    Validate QA pairs and generate report.

    Returns:
        Validation report with errors and warnings
    """
    report = {
        'total': len(qa_pairs),
        'valid': 0,
        'errors': [],
        'warnings': []
    }

    required_fields = ['question', 'answer', 'cluster_id', 'cluster_label']

    for i, qa in enumerate(qa_pairs):
        errors = []
        warnings = []

        # Check required fields
        for field in required_fields:
            if field not in qa:
                errors.append(f"Missing field: {field}")

        # Validate question
        if 'question' in qa:
            if not qa['question'].strip():
                errors.append("Empty question")
            elif not qa['question'].strip().endswith('?'):
                warnings.append("Question doesn't end with '?'")

        # Validate answer
        if 'answer' in qa:
            if not qa['answer'].strip():
                errors.append("Empty answer")
            elif len(qa['answer']) < 50:
                warnings.append(f"Short answer ({len(qa['answer'])} chars)")

        # Validate topics
        if 'topics' in qa and not isinstance(qa['topics'], list):
            errors.append("Topics must be a list")

        # Record issues
        if errors:
            report['errors'].append({
                'index': i,
                'line': qa.get('_line_number'),
                'errors': errors,
                'warnings': warnings
            })
        else:
            report['valid'] += 1

        if warnings and not errors:
            report['warnings'].append({
                'index': i,
                'line': qa.get('_line_number'),
                'warnings': warnings
            })

    return report
```

#### `deduplicate_questions(qa_pairs: List[Dict], threshold: float = 0.85) -> List[Dict]`

Removes duplicate or highly similar questions.

**Method:** Use sentence embeddings + cosine similarity

**Implementation:**
```python
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def deduplicate_questions(
    qa_pairs: List[Dict],
    threshold: float = 0.85
) -> List[Dict]:
    """
    Remove duplicate questions using semantic similarity.

    Args:
        qa_pairs: List of QA pairs
        threshold: Similarity threshold (0-1)

    Returns:
        Deduplicated QA pairs
    """
    if not qa_pairs:
        return []

    # Extract questions
    questions = [qa['question'] for qa in qa_pairs]

    # Generate embeddings
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(questions, show_progress_bar=True)

    # Calculate pairwise similarities
    similarities = cosine_similarity(embeddings)

    # Find duplicates
    keep_indices = set(range(len(qa_pairs)))

    for i in range(len(qa_pairs)):
        if i not in keep_indices:
            continue

        for j in range(i + 1, len(qa_pairs)):
            if j not in keep_indices:
                continue

            if similarities[i, j] >= threshold:
                # Keep the one with longer answer
                if len(qa_pairs[i]['answer']) >= len(qa_pairs[j]['answer']):
                    keep_indices.discard(j)
                else:
                    keep_indices.discard(i)
                    break

    # Filter
    deduplicated = [qa_pairs[i] for i in sorted(keep_indices)]

    print(f"Deduplicated: {len(qa_pairs)} → {len(deduplicated)} QA pairs")

    return deduplicated
```

#### `add_metadata(qa_pairs: List[Dict]) -> List[Dict]`

Adds unique IDs and enrichment metadata.

**Implementation:**
```python
import uuid
from datetime import datetime

def add_metadata(qa_pairs: List[Dict]) -> List[Dict]:
    """
    Add unique IDs and metadata to QA pairs.

    Metadata added:
    - qa_id: Unique identifier
    - dataset_version: Version string
    - created_at: Timestamp
    - postgres_version: PostgreSQL version (17.6)
    """
    for i, qa in enumerate(qa_pairs):
        # Unique ID
        qa['qa_id'] = f"pg17_{i:04d}_{uuid.uuid4().hex[:8]}"

        # Dataset metadata
        qa['dataset_version'] = "1.0"
        qa['postgres_version'] = "17.6"

        if 'generated_at' not in qa:
            qa['created_at'] = datetime.now().isoformat()

        # Quality metadata (placeholders for future scoring)
        qa['quality_score'] = None
        qa['reviewed'] = False

    return qa_pairs
```

#### `generate_statistics(qa_pairs: List[Dict]) -> Dict`

Generates comprehensive dataset statistics.

**Implementation:**
```python
from collections import Counter

def generate_statistics(qa_pairs: List[Dict]) -> Dict:
    """
    Generate dataset statistics.

    Returns:
        Statistics dictionary
    """
    stats = {
        'total_qa_pairs': len(qa_pairs),
        'total_questions': len(qa_pairs),
        'total_answers': len(qa_pairs)
    }

    # Difficulty distribution
    difficulty_counts = Counter(qa.get('difficulty', 'unknown') for qa in qa_pairs)
    stats['difficulty_distribution'] = dict(difficulty_counts)

    # Topic distribution
    all_topics = [topic for qa in qa_pairs for topic in qa.get('topics', [])]
    topic_counts = Counter(all_topics)
    stats['topic_distribution'] = dict(topic_counts.most_common(20))

    # Cluster distribution
    cluster_counts = Counter(qa.get('cluster_label', 'unknown') for qa in qa_pairs)
    stats['cluster_distribution'] = dict(cluster_counts.most_common(10))

    # Length statistics
    question_lengths = [len(qa['question']) for qa in qa_pairs]
    answer_lengths = [len(qa['answer']) for qa in qa_pairs]

    stats['question_length'] = {
        'min': min(question_lengths),
        'max': max(question_lengths),
        'mean': sum(question_lengths) / len(question_lengths),
        'median': sorted(question_lengths)[len(question_lengths) // 2]
    }

    stats['answer_length'] = {
        'min': min(answer_lengths),
        'max': max(answer_lengths),
        'mean': sum(answer_lengths) / len(answer_lengths),
        'median': sorted(answer_lengths)[len(answer_lengths) // 2]
    }

    # Source file coverage
    all_source_files = [f for qa in qa_pairs for f in qa.get('source_files', [])]
    stats['unique_source_files'] = len(set(all_source_files))
    stats['total_source_file_references'] = len(all_source_files)

    # Component coverage
    components = set()
    for qa in qa_pairs:
        for file_path in qa.get('source_files', []):
            # Extract component from path
            parts = file_path.split('/')
            if len(parts) > 2:
                components.add(parts[2])  # e.g., src/backend/<component>

    stats['components_covered'] = sorted(components)

    return stats
```

#### `create_dataset_readme(qa_pairs: List[Dict], stats: Dict) -> str`

Creates README for dataset.

**Implementation:**
```python
def create_dataset_readme(qa_pairs: List[Dict], stats: Dict) -> str:
    """
    Generate README.md for dataset.

    Returns:
        README content
    """
    readme = f"""# PostgreSQL 17.6 Developer Copilot QA Dataset

## Overview

This dataset contains {stats['total_qa_pairs']} question-answer pairs about PostgreSQL 17.6 internals, generated from pgsql-hackers mailing list discussions (2022-2025) and mapped to source code.

## Purpose

Evaluate RAG-based copilot systems for PostgreSQL development built on Code Property Graphs (Joern).

## Dataset Statistics

- **Total QA Pairs:** {stats['total_qa_pairs']}
- **Unique Source Files:** {stats['unique_source_files']}
- **PostgreSQL Version:** 17.6
- **Generated:** {datetime.now().strftime('%Y-%m-%d')}

### Difficulty Distribution

"""

    for difficulty, count in stats['difficulty_distribution'].items():
        percentage = (count / stats['total_qa_pairs']) * 100
        readme += f"- **{difficulty.capitalize()}:** {count} ({percentage:.1f}%)\n"

    readme += f"""
### Topic Distribution (Top 10)

"""

    for topic, count in list(stats['topic_distribution'].items())[:10]:
        readme += f"- **{topic}:** {count}\n"

    readme += f"""
### Component Coverage

Components from PostgreSQL source code covered in this dataset:

"""

    for component in stats['components_covered'][:15]:
        readme += f"- {component}\n"

    readme += f"""
### Answer Length Statistics

- **Mean:** {stats['answer_length']['mean']:.0f} characters
- **Median:** {stats['answer_length']['median']:.0f} characters
- **Range:** {stats['answer_length']['min']}-{stats['answer_length']['max']} characters

## Dataset Format

Each line is a JSON object with the following structure:

```json
{{
  "qa_id": "pg17_0001_abc123de",
  "question": "Question text?",
  "answer": "Detailed answer...",
  "difficulty": "intermediate",
  "topics": ["topic1", "topic2"],
  "cluster_id": 0,
  "cluster_label": "topic_cluster_name",
  "source_files": ["src/backend/optimizer/plan/planner.c"],
  "thread_ids": ["20230415-thread-id"],
  "generated_at": "2025-10-02T15:30:45",
  "dataset_version": "1.0",
  "postgres_version": "17.6"
}}
```

## Fields

- **qa_id:** Unique identifier
- **question:** Technical question about PostgreSQL internals
- **answer:** Comprehensive answer with source code references
- **difficulty:** beginner | intermediate | advanced
- **topics:** List of topic tags
- **cluster_id:** Topic cluster ID from mailing list analysis
- **cluster_label:** Human-readable cluster name
- **source_files:** Relevant PostgreSQL 17.6 source files
- **thread_ids:** Original mailing list thread IDs
- **generated_at:** Generation timestamp
- **dataset_version:** Dataset version
- **postgres_version:** PostgreSQL version (17.6)

## Usage

### Python

```python
import json

qa_pairs = []
with open('pg_copilot_qa_dataset.jsonl', 'r') as f:
    for line in f:
        qa_pairs.append(json.loads(line))

# Filter by difficulty
advanced_qa = [qa for qa in qa_pairs if qa['difficulty'] == 'advanced']

# Filter by topic
planner_qa = [qa for qa in qa_pairs if 'planner' in qa['topics']]
```

### Evaluation

Use this dataset to evaluate copilot responses:

1. Query copilot with question
2. Compare response to ground truth answer
3. Metrics: semantic similarity, source file coverage, factual accuracy

## Source

Generated from:
- **Mailing List:** pgsql-hackers (2022-2025)
- **PostgreSQL Source:** 17.6 (REL_17_6)
- **LLM:** Qwen3-32B-Q4_K_M
- **Method:** Topic clustering + source code mapping

## License

Research dataset - use for PostgreSQL copilot evaluation

## Citation

If you use this dataset, please reference the PostgreSQL project and pgsql-hackers mailing list.
"""

    return readme
```

## Data Flow

```
qa_pairs.jsonl → Load → Validate → Deduplicate → Add Metadata → Statistics → Export
       ↓          ↓        ↓           ↓              ↓             ↓          ↓
   (raw QA)   (parsed) (checked) (unique) (enriched)      (analyzed)  final_dataset.jsonl
```

## Output Format

### Final Dataset Structure

**Directory:**
```
output/
├── pg_copilot_qa_dataset.jsonl    # Main dataset
├── dataset_report.json             # Statistics and validation
└── README.md                       # Dataset documentation
```

### pg_copilot_qa_dataset.jsonl

```json
{"qa_id": "pg17_0000_a1b2c3d4", "question": "How does PostgreSQL implement MVCC for tuple visibility?", "answer": "PostgreSQL's MVCC uses transaction IDs in tuple headers...", "difficulty": "advanced", "topics": ["mvcc", "visibility"], "cluster_id": 2, "cluster_label": "mvcc_visibility", "source_files": ["src/backend/access/heap/heapam.c"], "thread_ids": ["20230520-mvcc"], "generated_at": "2025-10-02T15:30:45", "dataset_version": "1.0", "postgres_version": "17.6", "quality_score": null, "reviewed": false}
```

### dataset_report.json

```json
{
  "metadata": {
    "created_at": "2025-10-02T16:00:00",
    "postgres_version": "17.6",
    "dataset_version": "1.0",
    "source_mailing_list": "pgsql-hackers",
    "date_range": "2022-2025"
  },
  "statistics": {
    "total_qa_pairs": 187,
    "difficulty_distribution": {
      "beginner": 23,
      "intermediate": 98,
      "advanced": 66
    },
    "topic_distribution": {
      "planner": 34,
      "mvcc": 28,
      "wal": 22,
      "index": 19
    },
    "answer_length": {
      "mean": 487.3,
      "median": 456,
      "min": 112,
      "max": 1243
    },
    "unique_source_files": 145,
    "components_covered": ["optimizer", "executor", "access", "storage", "replication"]
  },
  "validation": {
    "total": 187,
    "valid": 187,
    "errors": [],
    "warnings": []
  }
}
```

## Configuration

Key settings in `config.py`:

```python
# Dataset builder configuration
OUTPUT_DIR = "output"
DATASET_FILENAME = "pg_copilot_qa_dataset.jsonl"
REPORT_FILENAME = "dataset_report.json"
README_FILENAME = "README.md"

# Quality control
DEDUP_SIMILARITY_THRESHOLD = 0.85
MIN_ANSWER_LENGTH = 50
REQUIRE_SOURCE_FILES = False
VALIDATE_FILE_PATHS = False
```

## Usage Examples

### Basic Usage

```python
from dataset_builder import DatasetBuilder

# Initialize builder
builder = DatasetBuilder('data/qa_pairs.jsonl')

# Load QA pairs
builder.load_qa_pairs()
print(f"Loaded {len(builder.qa_pairs)} QA pairs")

# Validate
validation_report = builder.validate_qa_pairs()
print(f"Valid: {validation_report['valid']}/{validation_report['total']}")

# Deduplicate
builder.deduplicate(similarity_threshold=0.85)

# Add metadata
builder.add_metadata()

# Generate statistics
stats = builder.generate_statistics()

# Export
builder.export_dataset('output/pg_copilot_qa_dataset.jsonl')
builder.create_report('output/dataset_report.json')

print("Dataset build complete!")
```

### Custom Validation Rules

```python
from dataset_builder import DatasetBuilder

builder = DatasetBuilder('data/qa_pairs.jsonl')
builder.load_qa_pairs()

# Custom validation
def custom_validate(qa):
    errors = []

    # Require specific topics
    if not qa.get('topics') or len(qa['topics']) == 0:
        errors.append("Missing topics")

    # Require source file references
    if not qa.get('source_files'):
        errors.append("Missing source files")

    # Check answer mentions source code
    if 'src/' not in qa['answer']:
        errors.append("Answer doesn't reference source code")

    return errors

# Apply custom validation
for qa in builder.qa_pairs:
    errors = custom_validate(qa)
    if errors:
        print(f"QA {qa.get('qa_id')}: {errors}")
```

## Performance Considerations

### Estimated Metrics

- **Load time:** 1-2 seconds
- **Validation time:** 2-5 seconds
- **Deduplication time:** 30-60 seconds (depends on count)
- **Export time:** 1-2 seconds
- **Total time:** ~1-2 minutes

## Dependencies

```
json
sentence-transformers>=2.2.0
scikit-learn>=1.3.0
numpy>=1.24.0
```

## Testing

### Unit Tests

```python
import unittest
from dataset_builder import validate_qa_pairs, deduplicate_questions

class TestDatasetBuilder(unittest.TestCase):
    def test_validation(self):
        qa_pairs = [
            {'question': 'Q1?', 'answer': 'A1' * 30, 'cluster_id': 1, 'cluster_label': 'test'},
            {'question': 'Q2', 'answer': 'A2', 'cluster_id': 2, 'cluster_label': 'test2'}  # Missing '?'
        ]
        report = validate_qa_pairs(qa_pairs)
        self.assertEqual(report['valid'], 1)
        self.assertEqual(len(report['warnings']), 1)
```

## Troubleshooting

### Deduplication Too Aggressive

**Symptoms:** Too many QA pairs removed

**Solutions:**
- Increase `DEDUP_SIMILARITY_THRESHOLD` (0.85 → 0.90)
- Use stricter matching (exact question match only)
- Manually review duplicates

### Validation Fails

**Symptoms:** Many validation errors

**Solutions:**
- Review QA generation quality
- Adjust validation rules
- Fix malformed QA pairs manually

### Statistics Incomplete

**Symptoms:** Missing statistics

**Solutions:**
- Ensure all QA pairs have required fields
- Add default values for missing fields
- Update statistics calculation

## Next Steps

After dataset is built:
1. Review `output/README.md`
2. Check `dataset_report.json` statistics
3. Use dataset to evaluate PostgreSQL copilot RAG system
4. Share with research team
