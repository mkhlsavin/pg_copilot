# Scripts Directory

This directory contains utility scripts for system setup, maintenance, and common operations.

## Available Scripts

### 1. Joern Workspace Bootstrap (`bootstrap_joern.ps1`)

**Purpose**: Automatically initializes Joern workspace with PostgreSQL CPG and enrichment extensions.

**Language**: PowerShell

**Location**: `scripts/bootstrap_joern.ps1`

**Usage**:
```powershell
# Run from project root
cd C:\Users\user\pg_copilot\codegraph
powershell -ExecutionPolicy Bypass -File scripts/bootstrap_joern.ps1

# Or from anywhere
powershell -ExecutionPolicy Bypass -File C:\Users\user\pg_copilot\codegraph\scripts\bootstrap_joern.ps1
```

**Prerequisites**:
- Joern server running on `localhost:8080`
- PostgreSQL CPG available at `C:/Users/user/joern/workspace/pg17_full.cpg`
- Network connectivity to Joern server

**What it does**:

1. **Tests Joern Connection**
   - Pings Joern server at `http://localhost:8080`
   - Verifies server is responsive

2. **Imports Joern Libraries**
   ```scala
   import _root_.io.joern.joerncli.console.Joern
   import _root_.io.shiftleft.semanticcpg.language._
   ```

3. **Opens CPG Workspace**
   ```scala
   Joern.open("pg17_full.cpg")
   ```

4. **Initializes CPG Object**
   ```scala
   val cpg = Joern.cpg
   ```

5. **Loads Enrichment Extensions** (if available)
   - Loads custom Scala scripts from `../cpg_enrichment/`
   - Enables enrichment tags and patterns

6. **Verifies CPG State**
   - Checks method count
   - Validates tags are available
   - Confirms successful initialization

**Output**:
```
Testing Joern connection...
✓ Joern server is responsive

Importing Joern libraries...
✓ Libraries imported successfully

Opening CPG workspace...
✓ CPG workspace opened: pg17_full.cpg

Initializing CPG object...
✓ CPG object created

Loading enrichment extensions...
✓ Enrichments loaded from ../cpg_enrichment/

Verifying CPG state...
✓ CPG contains 452,847 methods
✓ Enrichment tags available

Bootstrap completed successfully!
```

**Error Handling**:

```powershell
# Connection error
if (connection fails) {
    Write-Error "Cannot connect to Joern server at localhost:8080"
    Write-Host "Start Joern with: joern -J-Xmx16G --server --server-host localhost --server-port 8080"
    exit 1
}

# CPG not found
if (cpg file missing) {
    Write-Error "CPG file not found: pg17_full.cpg"
    Write-Host "Ensure PostgreSQL CPG is located at C:/Users/user/joern/workspace/pg17_full.cpg"
    exit 1
}

# Import error
if (import fails) {
    Write-Warning "Failed to import libraries, retrying..."
    # Retry up to 3 times
}
```

**Integration**:

The bootstrap script is automatically called by:
- `src/workflow/langgraph_workflow.py` - LangGraph workflow
- `src/execution/joern_bootstrap.py` - Python bootstrap wrapper

**Manual vs. Automatic**:
- **Manual**: Run script directly when Joern workspace needs reset
- **Automatic**: LangGraph workflow calls bootstrap on connection errors

### 2. Vector Store Initialization (`init_vector_store.py`)

**Purpose**: Initializes all ChromaDB vector stores from scratch.

**Language**: Python

**Location**: `scripts/init_vector_store.py`

**Usage**:
```powershell
cd C:\Users\user\pg_copilot\codegraph
python scripts/init_vector_store.py
```

**What it does**:

1. **Clears Existing Collections** (optional)
   - Backs up current vector stores
   - Removes old collections

2. **Builds Q&A Store**
   - Loads `data/train_split_merged.jsonl`
   - Creates embeddings
   - Indexes in ChromaDB

3. **Builds Example Store**
   - Loads `data/cpgql_examples.json`
   - Creates embeddings
   - Indexes in ChromaDB

4. **Builds Pattern Stores**
   - CFG patterns from `data/cfg_patterns.json`
   - DDG patterns from `data/ddg_patterns_enriched.json`
   - Documentation from `data/cpg_documentation_complete.json`

5. **Verifies Collections**
   - Checks collection sizes
   - Tests retrieval
   - Reports statistics

**Output**:
```
Initializing vector stores...

[1/5] Q&A Store
  Loading data: 23,156 Q&A pairs
  Generating embeddings: 100% ████████████████████
  Indexed: 23,156 documents
  Collection: qa_collection
  ✓ Complete

[2/5] Example Store
  Loading data: 1,072 examples
  Generating embeddings: 100% ████████████████████
  Indexed: 1,072 documents
  Collection: examples_collection
  ✓ Complete

[3/5] CFG Pattern Store
  Loading data: 53,970 patterns
  Generating embeddings: 100% ████████████████████
  Indexed: 53,970 documents
  Collection: cfg_patterns
  ✓ Complete

[4/5] DDG Pattern Store (Enriched)
  Loading data: 169,303 patterns
  Generating embeddings: 100% ████████████████████
  Indexed: 169,303 documents
  Collection: ddg_patterns_enriched
  ✓ Complete

[5/5] Documentation Store
  Loading data: 638 methods
  Generating embeddings: 100% ████████████████████
  Indexed: 638 documents
  Collection: documentation
  ✓ Complete

Verification:
  Total collections: 5
  Total documents: 248,139
  Storage path: ./chromadb_storage
  Disk usage: 3.2 GB

Initialization complete!
```

**Options**:
```python
# Clear existing collections
python scripts/init_vector_store.py --clear

# Specific collections only
python scripts/init_vector_store.py --collections qa,examples

# Custom storage path
python scripts/init_vector_store.py --storage-path ./custom_path
```

### 3. Cache Management (`manage_cache.py`)

**Purpose**: Manages retrieval cache for performance optimization.

**Language**: Python

**Location**: `scripts/manage_cache.py`

**Usage**:
```powershell
# View cache statistics
python scripts/manage_cache.py --stats

# Clear cache
python scripts/manage_cache.py --clear

# Clear expired entries
python scripts/manage_cache.py --cleanup

# Set TTL (time-to-live)
python scripts/manage_cache.py --set-ttl 86400  # 24 hours
```

**Commands**:

**View Statistics**:
```powershell
python scripts/manage_cache.py --stats

# Output:
# Cache Statistics:
#   Total entries: 1,247
#   Cache size: 45.3 MB
#   Hit rate: 34.8%
#   Avg retrieval time: 12ms (cached) vs 487ms (uncached)
#   Expired entries: 143
```

**Clear Cache**:
```powershell
python scripts/manage_cache.py --clear

# Output:
# Clearing cache...
# Removed 1,247 entries
# Freed 45.3 MB
# Cache cleared successfully
```

**Cleanup Expired**:
```powershell
python scripts/manage_cache.py --cleanup

# Output:
# Cleaning up expired entries...
# Removed 143 expired entries
# Freed 5.2 MB
# Cleanup complete
```

## Script Organization

```
scripts/
├── README.md                  # This file
├── bootstrap_joern.ps1        # Joern workspace initialization
├── init_vector_store.py       # Vector store setup
└── manage_cache.py            # Cache management
```

## Common Use Cases

### Initial Setup

**First-time system setup**:
```powershell
# 1. Start Joern server
cd C:\Users\user\joern
joern -J-Xmx16G --server --server-host localhost --server-port 8080

# 2. Bootstrap workspace
cd C:\Users\user\pg_copilot\codegraph
powershell -ExecutionPolicy Bypass -File scripts/bootstrap_joern.ps1

# 3. Initialize vector stores
python scripts/init_vector_store.py

# 4. Verify setup
python demo_simple.py
```

### Reset After Changes

**After updating data files**:
```powershell
# Re-index vector stores
python scripts/init_vector_store.py --clear
python scripts/init_vector_store.py

# Clear retrieval cache
python scripts/manage_cache.py --clear
```

### Performance Optimization

**Optimize cache performance**:
```powershell
# Check cache stats
python scripts/manage_cache.py --stats

# If hit rate is low (<20%), consider:
# - Increasing TTL
# - Adjusting query variations
# - Pre-warming cache with common queries

# Clean up expired entries regularly
python scripts/manage_cache.py --cleanup
```

### Troubleshooting

**Joern connection issues**:
```powershell
# Test connection
curl http://localhost:8080

# Re-bootstrap workspace
powershell -ExecutionPolicy Bypass -File scripts/bootstrap_joern.ps1
```

**Vector store corruption**:
```powershell
# Rebuild from scratch
rm -r chromadb_storage
python scripts/init_vector_store.py
```

**Cache issues**:
```powershell
# Clear and rebuild
python scripts/manage_cache.py --clear
# Cache will rebuild automatically on next retrieval
```

## Script Development Guidelines

### Adding New Scripts

1. **Create script file**: `scripts/new_script.py` or `scripts/new_script.ps1`
2. **Add documentation**: Docstring and inline comments
3. **Update this README**: Add script description and usage
4. **Test thoroughly**: Ensure error handling is robust
5. **Add to workflow**: Integrate with LangGraph if needed

### Error Handling

All scripts should:
- Validate inputs and prerequisites
- Provide clear error messages
- Exit with appropriate exit codes
- Log operations for debugging

**Example**:
```python
import sys
import logging

logger = logging.getLogger(__name__)

def main():
    try:
        # Validate prerequisites
        if not check_prerequisites():
            logger.error("Prerequisites not met")
            sys.exit(1)

        # Perform operation
        result = perform_operation()

        # Report success
        logger.info(f"Operation completed: {result}")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)
```

## Dependencies

Scripts use:
- PowerShell (Windows)
- Python 3.8+
- `requests` (for Joern API)
- `chromadb` (for vector stores)
- `logging` (for operation logging)

## See Also

- `/src/execution/joern_bootstrap.py` - Python wrapper for bootstrap
- `/src/retrieval/` - Vector store implementations
- `/src/workflow/` - LangGraph workflow integration
- Root README.md - System setup instructions
