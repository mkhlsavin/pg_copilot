# Scripts Directory

This directory contains utility scripts for system setup, documentation building, deployment, and maintenance.

## Available Scripts

### Quick Reference

| Script | Purpose |
|--------|---------|
| `build_landing.py` | Build landing page from modular templates |
| `build_docs.py` | Build bilingual HTML documentation |
| `manage_cache.py` | Manage retrieval cache |
| `init_vector_store.py` | Initialize ChromaDB vector stores |
| `bootstrap_joern.ps1` | Initialize Joern workspace |
| `export_full_calls.py` | Export function calls from Joern to DuckDB |
| `install-ubuntu.sh` | Install CodeGraph on Ubuntu |
| `deploy-yandex.sh` | Deploy to Yandex Cloud |

---

## Landing & Documentation

### 1. Landing Page Builder (`build_landing.py`)

**Purpose**: Builds `index.html` and `whitepaper.html` from modular template components.

**Language**: Python

**Location**: `scripts/build_landing.py`

**Usage**:
```bash
# Legacy mode: update header/footer only in existing files
python scripts/build_landing.py

# Modular mode: build index.html from section templates (recommended)
python scripts/build_landing.py --sections
```

**Modes**:

| Mode | Command | Description |
|------|---------|-------------|
| Legacy | `python scripts/build_landing.py` | Updates header/footer in existing `index.html` and `whitepaper.html` |
| Sections | `python scripts/build_landing.py --sections` | Builds complete `index.html` from modular section templates |

**Template Structure**:
```
docs/landing/
├── templates/
│   ├── header.html          # Navigation header
│   ├── footer.html          # Page footer
│   └── sections/            # Modular content sections
│       ├── hero.html
│       ├── problems.html
│       ├── solution.html
│       ├── features.html
│       ├── metrics.html
│       ├── integrations.html
│       ├── architecture.html
│       ├── usp.html
│       ├── faq.html
│       └── cta.html
├── index.html               # Output: main landing page
└── whitepaper.html          # Output: whitepaper page
```

**Section Order** (for `--sections` mode):
1. hero
2. problems
3. solution
4. features
5. metrics
6. integrations
7. architecture
8. usp
9. faq
10. cta

**Features**:
- Shared header/footer components
- Automatic year update in footer
- UI strings for localization (currently Russian)
- Preserves existing content when updating header/footer

---

### 2. Documentation Builder (`build_docs.py`)

**Purpose**: Builds bilingual (EN/RU) HTML documentation from Markdown files with automatic translation.

**Language**: Python

**Location**: `scripts/build_docs.py`

**Detailed Documentation**: See [`scripts/docs_builder/README.md`](docs_builder/README.md) for full module documentation.

**Usage**:
```bash
# Full build with translation (default)
python scripts/build_docs.py

# Build English only (no translation)
python scripts/build_docs.py --no-translate

# Build with specific LLM provider
python scripts/build_docs.py --provider yandex
python scripts/build_docs.py --provider gigachat
python scripts/build_docs.py --provider openai

# Test build with mock translator
python scripts/build_docs.py --mock

# Validate links only (no build)
python scripts/build_docs.py --validate

# Force re-translation (ignore cache)
python scripts/build_docs.py --force-translate

# Verbose output
python scripts/build_docs.py -v
```

**CLI Options**:

| Option | Description |
|--------|-------------|
| `--translate` | Enable translation (default) |
| `--no-translate` | Build English only |
| `--provider {yandex,gigachat,openai}` | LLM provider for translation |
| `--mock` | Use mock translator for testing |
| `--validate` | Only validate links in existing output |
| `--force-translate` | Ignore translation cache |
| `-v, --verbose` | Verbose output |

**Input Folders** (from `docs/`):
- `getting-started/` - Installation, configuration
- `guides/` - User guides, scenarios
- `api/` - REST, WebSocket API documentation
- `integrations/` - LLM integrations (GigaChat, YandexGPT)
- `reference/` - Technical reference
- `enterprise/` - Enterprise features (already bilingual)

**Output Structure**:
```
docs/landing/docs/
├── en/
│   ├── index.html
│   ├── getting-started/
│   ├── guides/
│   ├── api/
│   ├── integrations/
│   ├── reference/
│   └── enterprise/
└── ru/
    └── (mirror structure)
```

**Environment Variables**:
```bash
# For YandexGPT
export YANDEX_API_KEY="your-api-key"
export YANDEX_FOLDER_ID="your-folder-id"

# For GigaChat
export GIGACHAT_CREDENTIALS="your-credentials"
```

**Translation Cache**: Translations are cached in `.doc_translation_cache/` to speed up subsequent builds.

---

## Data Management

### 3. Cache Management (`manage_cache.py`)

**Purpose**: Manages retrieval cache for performance optimization.

**Language**: Python

**Location**: `scripts/manage_cache.py`

**Commands**:
```bash
# View cache metrics and statistics
python scripts/manage_cache.py metrics

# Warm cache with common queries
python scripts/manage_cache.py warm --file queries.txt
python scripts/manage_cache.py warm --top-k-qa 3 --top-k-cpgql 5

# Invalidate entries by pattern
python scripts/manage_cache.py invalidate --pattern "security"

# Clear entire cache
python scripts/manage_cache.py clear
python scripts/manage_cache.py clear --force  # Skip confirmation

# Export cache to file
python scripts/manage_cache.py export
python scripts/manage_cache.py export --output cache_backup.json
```

**Metrics Output**:
```
Cache Statistics:
  Hits: 1,247
  Misses: 892
  Hit rate: 58.3%
  Current size: 45.3 MB
  Max size: 100 MB
  Utilization: 45.3%
  Memory: 45,312,000 bytes
  Avg get time: 12ms
  Avg set time: 45ms
  Evictions (size): 0
  Evictions (TTL): 143
  Oldest entry: 7200s
  Newest entry: 5s
```

---

### 4. Vector Store Initialization (`init_vector_store.py`)

**Purpose**: Initializes all ChromaDB vector stores from scratch.

**Language**: Python

**Location**: `scripts/init_vector_store.py`

**Usage**:
```bash
# Initialize all vector stores
python scripts/init_vector_store.py

# Clear existing and reinitialize
python scripts/init_vector_store.py --clear

# Specific collections only
python scripts/init_vector_store.py --collections qa,examples

# Custom storage path
python scripts/init_vector_store.py --storage-path ./custom_path
```

**What it indexes**:
- `data/train_split_merged.jsonl` - Q&A pairs (~23,000 entries)
- `data/sql_examples.json` - SQL/PGQ examples

**Output**:
```
Initializing vector stores...

[1/2] Q&A Store
  Loading data: 23,156 Q&A pairs
  Generating embeddings: 100%
  Indexed: 23,156 documents
  Collection: qa_collection

[2/2] SQL Examples Store
  Loading data: 1,072 examples
  Indexed: 1,072 documents
  Collection: sql_collection

Verification:
  Total collections: 2
  Total documents: 24,228
  Storage path: ./chromadb_storage
```

---

## Data Export & Processing

### 5. Joern Export (`export_full_calls.py`)

**Purpose**: Exports function call data from Joern CPG to DuckDB for analysis.

**Language**: Python

**Location**: `scripts/export_full_calls.py`

**Usage**:
```bash
python scripts/export_full_calls.py \
    --db cpg.duckdb \
    --joern localhost:8080 \
    --workspace pg17_full.cpg \
    --directories backend/commands bin/pg_dump backend/optimizer
```

**Options**:

| Option | Description |
|--------|-------------|
| `--db` | DuckDB database path |
| `--joern` | Joern server address |
| `--workspace` | CPG workspace name |
| `--directories` | Source directories to export |
| `--batch-size` | Batch size for export (default: 5000) |

**Exports to table**: `nodes_call` with columns:
- `id`, `method_full_name`, `name`, `signature`
- `type_full_name`, `dispatch_type`, `code`
- `line_number`, `column_number`, `order_index`
- `argument_index`, `filename`

---

### 6. Scenario Consolidation (`consolidate_scenarios.py`)

**Purpose**: Merges 17 benchmark scenarios into 14 consolidated scenarios.

**Language**: Python

**Location**: `scripts/consolidate_scenarios.py`

**Usage**:
```bash
python scripts/consolidate_scenarios.py
```

**Scenario Mapping**:
- `scenario_01_onboarding` ← 01_definition_search + 02_call_graph + 03_data_flow + 13_subsystem + 14_debugging + 16_business_logic
- `scenario_02_security_audit` ← 04_vulnerability + 08_entry_points + 15_new_vulnerabilities
- `scenario_03_documentation` ← 12_documentation
- (and others)

---

### 7. Hybrid Retrieval Benchmark (`benchmark_hybrid_retrieval.py`)

**Purpose**: Benchmarks hybrid retrieval performance with various metrics.

**Language**: Python

**Location**: `scripts/benchmark_hybrid_retrieval.py`

**Metrics Evaluated**:
- Precision@5, Precision@10
- Recall@5, Recall@10
- F1@5, F1@10
- MRR (Mean Reciprocal Rank)
- NDCG@10 (Normalized Discounted Cumulative Gain)
- Latency (ms)

---

## Joern & CPG

### 8. Joern Workspace Bootstrap (`bootstrap_joern.ps1`)

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
1. Tests Joern connection
2. Imports Joern libraries
3. Opens CPG workspace (`pg17_full.cpg`)
4. Initializes CPG object (`val cpg = Joern.cpg`)
5. Loads enrichment extensions (if available)
6. Verifies CPG state

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

**Integration**: Called automatically by:
- `src/workflow/langgraph_workflow.py` - LangGraph workflow
- `src/execution/joern_bootstrap.py` - Python bootstrap wrapper

---

## Deployment

### 9. Ubuntu Installation (`install-ubuntu.sh`)

**Purpose**: Installs CodeGraph and all dependencies on Ubuntu 22.04.

**Language**: Bash

**Location**: `scripts/install-ubuntu.sh`

**Usage**:
```bash
# Run as root or with sudo
sudo ./scripts/install-ubuntu.sh
```

**Installs**:
- Docker & Docker Compose
- Python 3.11+ & pip
- Joern server
- PostgreSQL (optional)
- UFW firewall configuration

**Functions**:
- `check_root()` - Verify root privileges
- `check_ubuntu()` - Verify Ubuntu OS
- `update_system()` - Update packages
- `install_dependencies()` - Base dependencies
- `install_docker()` - Docker Engine
- `install_docker_compose()` - Docker Compose
- `install_joern()` - Joern CPG tool
- `configure_firewall()` - UFW rules

---

### 10. Yandex Cloud Deployment (`deploy-yandex.sh`)

**Purpose**: Deploys CodeGraph to Yandex Cloud infrastructure.

**Language**: Bash

**Location**: `scripts/deploy-yandex.sh`

**Prerequisites**:
```bash
# Set required environment variables
export FOLDER_ID=<your-yandex-folder-id>
export SUBNET_ID=<your-subnet-id>
```

**Commands**:
```bash
# Create VM and deploy
./scripts/deploy-yandex.sh deploy

# Connect via SSH
./scripts/deploy-yandex.sh connect

# Check status
./scripts/deploy-yandex.sh status

# Stop VM
./scripts/deploy-yandex.sh stop

# Start VM
./scripts/deploy-yandex.sh start
```

**Default Configuration**:
| Parameter | Default |
|-----------|---------|
| VM_NAME | codegraph-prod |
| ZONE | ru-central1-a |
| PLATFORM | standard-v3 |
| CORES | 4 |
| MEMORY | 16 GB |
| DISK_SIZE | 100 GB |

**Override Defaults**:
```bash
export VM_NAME=my-codegraph
export CORES=8
export MEMORY=32
./scripts/deploy-yandex.sh deploy
```

---

## Documentation Utilities

### Fix Scripts

Scripts for fixing and maintaining documentation:

| Script | Purpose |
|--------|---------|
| `fix_readme_links.py` | Fix relative links in README files (`./en/` → `en/`) |
| `fix_toc_anchors.py` | Add explicit anchors to Russian headings for TOC compatibility |
| `fix_toc_by_position.py` | Fix TOC anchors by position matching |
| `fix_ru_anchors.py` | Fix Russian anchor IDs |
| `audit_toc.py` | Audit TOC entries and find broken anchors |
| `extract_ru_from_html.py` | Extract Russian content from HTML to Markdown |
| `reorganize_docs.py` | Reorganize docs/ folder structure |

**Usage Examples**:

```bash
# Audit TOC anchors
python scripts/audit_toc.py

# Fix TOC anchors in Russian docs
python scripts/fix_toc_anchors.py

# Extract Russian content from landing HTML
python scripts/extract_ru_from_html.py --section guides
python scripts/extract_ru_from_html.py --dry-run  # Preview only

# Reorganize docs structure
python scripts/reorganize_docs.py --dry-run
python scripts/reorganize_docs.py --revert  # Undo changes
```

---

## Script Organization

```
scripts/
├── README.md                      # This file
│
├── # Landing & Documentation
├── build_landing.py               # Landing page builder
├── build_docs.py                  # Documentation builder (orchestrator)
├── docs_builder/                  # Documentation builder modules
│   ├── README.md                  # Module documentation
│   ├── config.py                  # Constants and settings
│   ├── discovery.py               # MD file discovery
│   ├── translator.py              # LLM translation with cache
│   ├── converter.py               # Markdown → HTML
│   ├── template.py                # HTML template generator
│   ├── linker.py                  # Link validation
│   └── navigation.py              # Sidebar/navigation generation
│
├── # Data Management
├── init_vector_store.py           # ChromaDB initialization
├── manage_cache.py                # Retrieval cache management
│
├── # Data Export
├── export_full_calls.py           # Joern → DuckDB export
├── consolidate_scenarios.py       # Scenario consolidation
├── benchmark_hybrid_retrieval.py  # Retrieval benchmarking
│
├── # Joern & CPG
├── bootstrap_joern.ps1            # Joern workspace initialization
│
├── # Deployment
├── install-ubuntu.sh              # Ubuntu installation
├── deploy-yandex.sh               # Yandex Cloud deployment
│
├── # Documentation Fixes
├── fix_readme_links.py            # Fix README links
├── fix_toc_anchors.py             # Fix TOC anchors
├── fix_toc_by_position.py         # Fix TOC by position
├── fix_ru_anchors.py              # Fix Russian anchors
├── audit_toc.py                   # Audit TOC entries
├── extract_ru_from_html.py        # HTML → MD extraction
└── reorganize_docs.py             # Docs reorganization
```

---

## Common Use Cases

### Initial Setup

**First-time system setup**:
```bash
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

### Build Documentation

**Full documentation build**:
```bash
# Build with translation
python scripts/build_docs.py --provider yandex

# Build landing page
python scripts/build_landing.py --sections
```

### Reset After Changes

**After updating data files**:
```bash
# Re-index vector stores
python scripts/init_vector_store.py --clear

# Clear retrieval cache
python scripts/manage_cache.py clear
```

### Deploy to Cloud

**Yandex Cloud deployment**:
```bash
export FOLDER_ID=<folder-id>
export SUBNET_ID=<subnet-id>

./scripts/deploy-yandex.sh deploy
./scripts/deploy-yandex.sh status
```

---

## Troubleshooting

### Joern connection issues
```bash
# Test connection
curl http://localhost:8080

# Re-bootstrap workspace
powershell -ExecutionPolicy Bypass -File scripts/bootstrap_joern.ps1
```

### Vector store corruption
```bash
# Rebuild from scratch
rm -r chromadb_storage
python scripts/init_vector_store.py
```

### Cache issues
```bash
# Clear and rebuild
python scripts/manage_cache.py clear
# Cache will rebuild automatically on next retrieval
```

### Documentation build errors
```bash
# Install dependencies
pip install markdown pygments tqdm openai

# Clear translation cache
rm -rf .doc_translation_cache/

# Rebuild
python scripts/build_docs.py --force-translate
```

---

## Dependencies

Scripts use:
- PowerShell (Windows)
- Python 3.8+
- Bash (Linux/macOS)

Python packages:
- `requests` - HTTP client
- `chromadb` - Vector store
- `markdown` - Markdown parsing
- `pygments` - Syntax highlighting
- `tqdm` - Progress bars
- `openai` - LLM API client

---

## See Also

- [`scripts/docs_builder/README.md`](docs_builder/README.md) - Detailed documentation builder docs
- `/src/execution/joern_bootstrap.py` - Python wrapper for bootstrap
- `/src/retrieval/` - Vector store implementations
- `/src/workflow/` - LangGraph workflow integration
- Root `README.md` - System setup instructions
