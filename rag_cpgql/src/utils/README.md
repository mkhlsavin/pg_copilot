# Utils Module

This module contains utility functions and helper classes used throughout the RAG-CPGQL system.

## Components

### 1. Configuration Loader (`config.py`)

**Purpose**: Centralized configuration management for the entire system.

**Configuration File**: `config.yaml` (root directory)

**Key Sections**:

```yaml
# Model configuration
model:
  path: "C:/Users/user/.lmstudio/models/..."
  n_ctx: 32768
  n_gpu_layers: 35
  temperature: 0.1

# Joern server
joern:
  host: localhost
  port: 8080
  cpg_path: "C:/Users/user/joern/workspace/pg17_full.cpg"

# Vector stores
vector_stores:
  storage_path: "./chromadb_storage"
  embedding_model: "sentence-transformers/all-MiniLM-L6-v2"

# Retrieval
retrieval:
  top_k_qa: 10
  top_k_examples: 5
  top_k_cfg: 10
  top_k_ddg: 15
  top_k_docs: 5

# Workflow
workflow:
  max_retries: 2
  execution_timeout: 300
  auto_bootstrap: true
```

**Usage**:

```python
from src.utils.config import Config

config = Config()

# Access configuration
model_path = config.get('model.path')
joern_host = config.get('joern.host')
top_k = config.get('retrieval.top_k_qa')

# Check if value exists
if config.has('joern.server.custom_settings'):
    custom = config.get('joern.server.custom_settings')

# Get with default
timeout = config.get('execution.timeout', default=300)
```

**Key Functions**:

```python
class Config:
    def __init__(self, config_path='config.yaml'):
        """Load configuration from YAML file"""

    def get(self, key, default=None):
        """Get configuration value using dot notation"""

    def has(self, key):
        """Check if configuration key exists"""

    def set(self, key, value):
        """Set configuration value (runtime only)"""

    def save(self, path=None):
        """Save configuration to file"""
```

**Environment Variable Override**:

```python
# Environment variables override config file
# Format: RAG_CPGQL_<SECTION>_<KEY>

export RAG_CPGQL_JOERN_HOST=192.168.1.100
export RAG_CPGQL_MODEL_TEMPERATURE=0.2

# Accessed normally via config
config.get('joern.host')  # Returns '192.168.1.100'
```

### 2. Data Loader (`data_loader.py`)

**Purpose**: Utilities for loading and processing datasets.

**Key Functions**:

#### Load Q&A Dataset

```python
def load_qa_dataset(split='train'):
    """
    Load Q&A dataset (train or test split).

    Args:
        split: 'train' or 'test'

    Returns:
        List of {'question': str, 'answer': str} dicts
    """
    if split == 'train':
        path = 'data/train_split_merged.jsonl'
    else:
        path = 'data/test_split_merged.jsonl'

    qa_pairs = []
    with open(path, 'r') as f:
        for line in f:
            qa_pairs.append(json.loads(line))

    return qa_pairs
```

**Usage**:
```python
from src.utils.data_loader import load_qa_dataset

# Load training data
train_data = load_qa_dataset('train')
print(f"Loaded {len(train_data)} training pairs")
# Output: Loaded 23156 training pairs

# Access data
question = train_data[0]['question']
answer = train_data[0]['answer']
```

#### Load CPGQL Examples

```python
def load_cpgql_examples():
    """
    Load CPGQL example queries.

    Returns:
        List of {'query': str, 'description': str} dicts
    """
    with open('data/cpgql_examples.json', 'r') as f:
        examples = json.load(f)
    return examples
```

**Usage**:
```python
from src.utils.data_loader import load_cpgql_examples

examples = load_cpgql_examples()
print(f"Loaded {len(examples)} CPGQL examples")
# Output: Loaded 1072 CPGQL examples

# Access examples
query = examples[0]['query']
description = examples[0]['description']
```

#### Load Pattern Data

```python
def load_patterns(pattern_type):
    """
    Load extracted patterns (CFG or DDG).

    Args:
        pattern_type: 'cfg', 'ddg', or 'ddg_enriched'

    Returns:
        List of pattern dictionaries
    """
    paths = {
        'cfg': 'data/cfg_patterns.json',
        'ddg': 'data/ddg_patterns.json',
        'ddg_enriched': 'data/ddg_patterns_enriched.json'
    }

    with open(paths[pattern_type], 'r') as f:
        patterns = json.load(f)

    return patterns
```

**Usage**:
```python
from src.utils.data_loader import load_patterns

cfg_patterns = load_patterns('cfg')
ddg_enriched = load_patterns('ddg_enriched')

print(f"CFG patterns: {len(cfg_patterns)}")
print(f"DDG enriched: {len(ddg_enriched)}")
```

#### Batch Processing

```python
def batch_iterator(data, batch_size=32):
    """
    Create batches from data for efficient processing.

    Args:
        data: List of items
        batch_size: Batch size

    Yields:
        Batches of items
    """
    for i in range(0, len(data), batch_size):
        yield data[i:i + batch_size]
```

**Usage**:
```python
from src.utils.data_loader import batch_iterator

questions = [...]  # Large list of questions

for batch in batch_iterator(questions, batch_size=10):
    # Process 10 questions at a time
    results = process_batch(batch)
```

## Common Utilities

### Logging Setup

```python
import logging
from src.utils.config import Config

# Standard logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/rag_cpgql.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

### Path Utilities

```python
import os
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Data directory
DATA_DIR = PROJECT_ROOT / 'data'

# Results directory
RESULTS_DIR = PROJECT_ROOT / 'results'

# Ensure directory exists
def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)
```

### JSON Utilities

```python
import json

def save_json(data, path, indent=2):
    """Save data to JSON file with pretty printing"""
    with open(path, 'w') as f:
        json.dump(data, f, indent=indent)

def load_json(path):
    """Load data from JSON file"""
    with open(path, 'r') as f:
        return json.load(f)

def save_jsonl(data, path):
    """Save data to JSONL file (one JSON object per line)"""
    with open(path, 'w') as f:
        for item in data:
            f.write(json.dumps(item) + '\n')

def load_jsonl(path):
    """Load data from JSONL file"""
    data = []
    with open(path, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return data
```

## Usage Examples

### Example 1: Load Configuration and Data

```python
from src.utils.config import Config
from src.utils.data_loader import load_qa_dataset, load_cpgql_examples

# Load configuration
config = Config()
print(f"Model: {config.get('model.path')}")
print(f"Joern: {config.get('joern.host')}:{config.get('joern.port')}")

# Load datasets
train_qa = load_qa_dataset('train')
examples = load_cpgql_examples()

print(f"Loaded {len(train_qa)} Q&A pairs")
print(f"Loaded {len(examples)} CPGQL examples")
```

### Example 2: Batch Processing with Configuration

```python
from src.utils.config import Config
from src.utils.data_loader import load_qa_dataset, batch_iterator

config = Config()
batch_size = config.get('processing.batch_size', default=32)

questions = load_qa_dataset('test')

for batch in batch_iterator(questions, batch_size):
    # Process batch
    results = process_questions(batch)
```

### Example 3: Save Results

```python
from pathlib import Path
import json

def save_results(results, experiment_name):
    """Save experiment results with timestamp"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{experiment_name}_{timestamp}.json"

    results_dir = Path('results')
    results_dir.mkdir(exist_ok=True)

    path = results_dir / filename

    with open(path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to {path}")

# Usage
results = {'accuracy': 0.92, 'queries': [...]}
save_results(results, 'phase3_200q')
```

## Directory Structure Conventions

```
rag_cpgql/
├── config.yaml              # Main configuration
├── data/                    # Datasets and patterns
├── chromadb_storage/        # Vector store persistence
├── logs/                    # Application logs
├── results/                 # Experiment results
└── src/
    └── utils/
        ├── config.py        # Configuration management
        └── data_loader.py   # Data loading utilities
```

## Configuration Best Practices

1. **Use config.yaml**: Centralize all configuration
2. **Environment variables**: Override for different environments
3. **Default values**: Always provide sensible defaults
4. **Validation**: Validate configuration on load
5. **Documentation**: Comment configuration options

## Dependencies

- `pyyaml`: YAML parsing
- `pathlib`: Path manipulation
- `json`: JSON serialization
- `logging`: Logging utilities

## See Also

- Root `config.yaml` - Main configuration file
- `/data/` - Dataset directory
- `/results/` - Results storage
- All other modules use these utilities for configuration and data loading
