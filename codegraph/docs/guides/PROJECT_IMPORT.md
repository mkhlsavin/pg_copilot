# Importing a New Codebase

Guide to importing new projects into the CodeGraph system.

## Overview

The system supports automatic import of codebases with various programming languages. The process includes:

1. **Clone** - repository cloning
2. **Detect Language** - programming language detection
3. **Create CPG** - Code Property Graph creation via Joern
4. **Export to DuckDB** - graph export to SQL database
5. **Import Source Code** - full source file content import into DuckDB
6. **Validate** - CPG integrity validation
7. **Import Docs** - documentation indexing into ChromaDB
8. **Create Plugin** - Domain Plugin generation

---

## Supported Languages

| Language | Joern Frontend | File Extensions | Description |
|----------|----------------|-----------------|-------------|
| C/C++ | c2cpg | `.c`, `.h`, `.cpp`, `.hpp`, `.cc`, `.cxx` | C/C++ source code |
| C# | csharp2cpg | `.cs` | C# source code |
| Go | gosrc2cpg | `.go` | Go source code |
| Java (source) | javasrc2cpg | `.java` | Java source code |
| Java (bytecode) | java2cpg | `.class`, `.jar`, `.war` | Java bytecode |
| JavaScript/TypeScript | jssrc2cpg | `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs` | JavaScript/TypeScript |
| Kotlin | kotlin2cpg | `.kt`, `.kts` | Kotlin source code |
| PHP | php2cpg | `.php` | PHP source code |
| Python | pysrc2cpg | `.py`, `.pyw` | Python source code |
| Ruby | rubysrc2cpg | `.rb` | Ruby source code |
| Swift | swiftsrc2cpg | `.swift` | Swift source code |
| Ghidra (binary) | ghidra2cpg | `.exe`, `.dll`, `.so`, `.dylib`, `.bin`, `.elf` | Binary file analysis |

---

## CLI Usage

### Full Pipeline (Single Command)

```bash
# Import from GitHub repository
python -m src.cli.import_commands full \
    --repo https://github.com/llvm/llvm-project \
    --branch main \
    --shallow \
    --language c

# Import local project
python -m src.cli.import_commands full \
    --path /path/to/project \
    --language java

# With selective import (only specific directories)
python -m src.cli.import_commands full \
    --repo https://github.com/llvm/llvm-project \
    --include llvm/lib llvm/include \
    --exclude test tests

# Import using Docker
python -m src.cli.import_commands full \
    --repo https://github.com/example/project \
    --docker
```

### Docker Support

The system supports running Joern in a Docker container for cross-platform operation:

```bash
# Import with Docker (no local Joern installation required)
python -m src.cli.import_commands full \
    --repo https://github.com/example/project \
    --docker

# With specific Docker image
python -m src.cli.import_commands full \
    --repo https://github.com/example/project \
    --docker \
    --docker-image ghcr.io/joernio/joern:v4.0.0
```

**Docker Advantages:**
- No local Joern installation required
- Consistent behavior across all platforms (Windows, Linux, macOS)
- Isolated execution environment
- Automatic resource management

### Joern Server Management

```bash
# Server status
python -m src.cli.import_commands server status

# Start server (local Joern)
python -m src.cli.import_commands server start

# Start server in Docker
python -m src.cli.import_commands server start --docker

# Stop server
python -m src.cli.import_commands server stop
```

### Project Management

```bash
# List all imported projects
python -m src.cli.import_commands projects list

# Project information
python -m src.cli.import_commands projects info my_project

# Activate project (set as current)
python -m src.cli.import_commands projects activate my_project

# Delete project (metadata only)
python -m src.cli.import_commands projects delete my_project

# Delete project with files (CPG, DuckDB)
python -m src.cli.import_commands projects delete my_project --delete-files
```

### Step-by-Step Import

```bash
# 1. Clone repository
python -m src.cli.import_commands clone \
    --repo https://github.com/org/repo \
    --branch main \
    --shallow \
    --depth 1

# 2. Detect language
python -m src.cli.import_commands detect --path ./workspace/repo

# 3. Create CPG
python -m src.cli.import_commands cpg \
    --path ./workspace/repo \
    --language c

# 4. Export to DuckDB
python -m src.cli.import_commands export --cpg ./workspace/repo.cpg

# 5. Validate
python -m src.cli.import_commands validate --db ./workspace/repo.duckdb

# 6. Import documentation
python -m src.cli.import_commands docs \
    --path ./workspace/repo \
    --db ./workspace/repo.duckdb

# 7. Create Domain Plugin
python -m src.cli.import_commands domain \
    --path ./workspace/repo \
    --name my_project \
    --db ./workspace/repo.duckdb
```

### List Supported Languages

```bash
python -m src.cli.import_commands languages
```

---

## REST API Usage

### Get List of Supported Languages

```http
GET /api/v1/import/languages
```

**Response:**
```json
{
  "languages": [
    {
      "id": "c",
      "name": "C",
      "extensions": [".c", ".h", ".cpp", ".hpp"],
      "joern_command": "c2cpg",
      "joern_flag": "C"
    },
    {
      "id": "java",
      "name": "JAVA",
      "extensions": [".java"],
      "joern_command": "javasrc2cpg",
      "joern_flag": "JAVASRC"
    }
  ]
}
```

### Start Import (Asynchronous)

```http
POST /api/v1/import/start
Content-Type: application/json

{
  "repo_url": "https://github.com/llvm/llvm-project",
  "branch": "main",
  "shallow_clone": true,
  "language": null,
  "mode": "full",
  "include_paths": ["llvm/lib", "llvm/include"],
  "exclude_paths": ["test", "tests"],
  "create_domain_plugin": true,
  "import_docs": true
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Import started. Use job_id to track progress."
}
```

### Check Import Status

```http
GET /api/v1/import/status/{job_id}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "project_name": "llvm-project",
  "status": "in_progress",
  "steps": [
    {"name": "Clone Repository", "status": "completed", "progress": 100},
    {"name": "Detect Language", "status": "completed", "progress": 100},
    {"name": "Create CPG", "status": "in_progress", "progress": 45, "message": "Creating CPG nodes..."},
    {"name": "Export to DuckDB", "status": "pending", "progress": 0},
    {"name": "Import Source Code", "status": "pending", "progress": 0},
    {"name": "Validate CPG", "status": "pending", "progress": 0},
    {"name": "Import Documentation", "status": "pending", "progress": 0},
    {"name": "Setup Domain Plugin", "status": "pending", "progress": 0}
  ],
  "current_step": "joern_import",
  "overall_progress": 35,
  "created_at": "2024-12-09T10:00:00Z",
  "updated_at": "2024-12-09T10:05:00Z"
}
```

### List All Import Jobs

```http
GET /api/v1/import/jobs?status_filter=in_progress&limit=10
```

### Cancel Import

```http
DELETE /api/v1/import/cancel/{job_id}
```

### Run Individual Step

```http
POST /api/v1/import/step
Content-Type: application/json

{
  "step_id": "validate",
  "context": {
    "duckdb_path": "./workspace/project.duckdb"
  }
}
```

### Import with Docker

```http
POST /api/v1/import/start
Content-Type: application/json

{
  "repo_url": "https://github.com/example/project",
  "branch": "main",
  "use_docker": true,
  "docker_image": "ghcr.io/joernio/joern:latest"
}
```

### Joern Server Management

**Get server status:**
```http
GET /api/v1/import/server/status
```

**Response:**
```json
{
  "status": "running",
  "mode": "docker",
  "container_id": "abc123",
  "port": 8080,
  "uptime_seconds": 3600
}
```

**Start server:**
```http
POST /api/v1/import/server/start
Content-Type: application/json

{
  "use_docker": true,
  "docker_image": "ghcr.io/joernio/joern:latest"
}
```

**Stop server:**
```http
POST /api/v1/import/server/stop
```

### Project Management

**List projects:**
```http
GET /api/v1/import/projects
```

**Response:**
```json
{
  "projects": [
    {
      "id": "123",
      "name": "my_project",
      "language": "python",
      "cpg_path": "./workspace/my_project.cpg",
      "duckdb_path": "./workspace/my_project.duckdb",
      "is_active": true,
      "created_at": "2024-12-10T10:00:00Z"
    }
  ]
}
```

**Activate project:**
```http
POST /api/v1/import/projects/{project_id}/activate
```

**Delete project:**
```http
DELETE /api/v1/import/projects/{project_id}?delete_files=true
```

---

## WebSocket for Progress Tracking

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/jobs/550e8400-e29b-41d4-a716-446655440000');

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);

  switch (msg.type) {
    case 'job.progress':
      console.log(`Progress: ${msg.payload.progress}% - ${msg.payload.message}`);
      break;
    case 'job.completed':
      console.log('Import completed:', msg.payload.result);
      break;
    case 'job.failed':
      console.error('Import failed:', msg.payload.error);
      break;
  }
};
```

---

## Import Parameters

### Import Modes

| Mode | Description |
|------|-------------|
| `full` | Full import of entire codebase |
| `selective` | Import only specified paths (`include_paths`) |
| `incremental` | Import only changes since last import |

### Cloning Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `shallow_clone` | `true` | Use shallow clone |
| `shallow_depth` | `1` | Shallow clone depth |
| `branch` | `"main"` | Branch to clone |

### Joern Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `joern_memory_gb` | `16` | Memory for Joern (GB) |
| `batch_size` | `10000` | Batch size for DuckDB export |
| `use_docker` | `false` | Use Docker for Joern |
| `docker_image` | `ghcr.io/joernio/joern:latest` | Joern Docker image |

### Documentation Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `import_docs` | `true` | Import documentation |
| `import_readme` | `true` | Index README files |
| `import_comments` | `true` | Import code comments |

---

## Import Result

After successful import, the following are created:

```
workspace/
├── llvm-project/           # Source code
├── llvm-project.cpg        # Joern CPG file
└── llvm-project.duckdb     # DuckDB database (graph)

chromadb_storage/
└── llvm_project_documentation/  # ChromaDB collection

src/domains/
└── llvm_project/           # Domain Plugin
    ├── __init__.py
    ├── plugin.py
    ├── subsystems.yaml
    └── prompts.yaml
```

### Result Structure (ProjectImportResult)

```json
{
  "cpg_path": "./workspace/llvm-project.cpg",
  "duckdb_path": "./workspace/llvm-project.duckdb",
  "domain_plugin_path": "./src/domains/llvm_project",
  "chromadb_collection": "llvm_project_documentation",
  "chromadb_stats": {
    "readme_indexed": 45,
    "docs_indexed": 230,
    "comments_indexed": 1500
  },
  "cpg_stats": {
    "methods": 125000,
    "calls": 450000,
    "identifiers": 890000
  },
  "source_code_stats": {
    "files_imported": 6307,
    "files_skipped_size": 12,
    "total_size_mb": 84.95
  },
  "validation_report": {
    "status": "passed",
    "quality_score": 85
  },
  "detected_language": "c",
  "import_duration_seconds": 3600.5
}
```

---

## CPG Validation

### Quality Score (0-100)

Quality assessment of the imported CPG:

| Criterion | Points |
|-----------|--------|
| Methods found | +50 |
| Files linked to methods (>50%) | +20 |
| AST edges present | +8 |
| CFG edges present | +7 |
| No validation errors | +15 |

### Checked Metrics

- `methods_exist` - number of methods
- `calls_exist` - number of calls
- `edges_ast` - AST edges
- `edges_cfg` - CFG edges
- `methods_with_files` - methods linked to files

---

## Source Code Import

The `SourceContentStep` imports full source code content into `nodes_file.content` for code navigation and analysis.

### How It Works

1. Reads files from `source_path` specified in project configuration
2. Populates `nodes_file.content` with full file contents
3. Automatically normalizes file paths for JOIN compatibility with `nodes_method`
4. Detects programming language from file extension

### Supported File Extensions

| Language | Extensions |
|----------|------------|
| C/C++ | `.c`, `.h`, `.cpp`, `.hpp`, `.cc`, `.cxx` |
| Python | `.py`, `.pyw` |
| Java | `.java` |
| JavaScript/TypeScript | `.js`, `.jsx`, `.ts`, `.tsx` |
| Go | `.go` |
| Rust | `.rs` |
| Ruby | `.rb` |
| PHP | `.php` |
| C# | `.cs` |
| Kotlin | `.kt`, `.kts` |
| Swift | `.swift` |
| Scala | `.scala` |
| SQL | `.sql` |
| Shell | `.sh`, `.bash` |
| Config | `.yaml`, `.yml`, `.json`, `.xml`, `.toml`, `.ini` |

### File Size Limit

Files larger than **500 KB** are skipped to keep database size manageable. This limit covers most source files while excluding large generated or binary files.

### Path Normalization

File paths in `nodes_file.name` are automatically normalized to match `nodes_method.filename` format. Common prefixes like `src/` are stripped to enable direct JOINs:

```sql
-- Get method source code by line number
SELECT
    m.full_name,
    m.line_number,
    m.line_number_end,
    f.content
FROM nodes_method m
JOIN nodes_file f ON REPLACE(m.filename, '/', '\') = REPLACE(f.name, '/', '\')
WHERE m.full_name = 'exec_simple_query';
```

### Import Statistics

After import, the following statistics are available:

| Metric | Description |
|--------|-------------|
| `source_files_imported` | Number of files successfully imported |
| `source_files_skipped_size` | Files skipped due to size limit |
| `source_files_skipped_not_found` | Files not found in source path |
| `source_files_total` | Total files processed |

---

## Domain Plugin

A plugin is automatically generated for working with the new project.

### Plugin Structure

```python
# src/domains/llvm_project/plugin.py

class LlvmProjectPlugin(DomainPlugin):
    @property
    def name(self) -> str:
        return "llvm_project"

    @property
    def display_name(self) -> str:
        return "Llvm Project"

    def _load_subsystems(self) -> Dict[str, SubsystemInfo]:
        # Load from subsystems.yaml
        ...

    def get_vulnerability_function_mappings(self) -> Dict[str, List[str]]:
        return {
            "buffer_overflow": ["strcpy", "memcpy", ...],
            "sql_injection": [...],
            ...
        }
```

### Configuration: subsystems.yaml

```yaml
subsystems:
  core:
    description: "Core application logic"
    key_functions:
      - main
      - init
      - start
    patterns:
      - "src"
      - "lib"
    related_files: []

  utils:
    description: "Utility functions"
    key_functions: []
    patterns:
      - "util"
      - "helper"
```

### Configuration: prompts.yaml

```yaml
prompts:
  onboarding:
    system: |
      You are a Llvm Project expert helping developers understand the codebase.
    user_template: |
      Help me understand the following aspect: {query}

  security:
    system: |
      You are a security expert analyzing Llvm Project (C) code.
    user_template: |
      Analyze the following code for security vulnerabilities:
      {code}
```

---

## Activating Domain Plugin

After creating the plugin, add it to the configuration:

```yaml
# config.yaml
domains:
  active: "llvm_project"
  available:
    - postgresql
    - llvm_project
```

Or programmatically:

```python
from src.domains import DomainRegistry

DomainRegistry.activate("llvm_project")
```

---

## Handling Large Repositories

### LLVM (Millions of Lines of Code)

```bash
# Use shallow clone
python -m src.cli.import_commands full \
    --repo https://github.com/llvm/llvm-project \
    --shallow \
    --depth 1

# Or selective import
python -m src.cli.import_commands full \
    --repo https://github.com/llvm/llvm-project \
    --include llvm/lib/Target/X86 \
    --mode selective

# Increase memory for Joern
python -m src.cli.import_commands full \
    --repo https://github.com/llvm/llvm-project \
    --memory 32
```

### Recommendations

1. **Use shallow clone** to save space and time
2. **Select needed directories** via `--include`
3. **Exclude tests** via `--exclude test tests`
4. **Increase Joern memory** for large projects (16-32GB)

---

## Python API

```python
from src.project_import import (
    ProjectImportPipeline,
    ProjectImportRequest,
    SupportedLanguage,
    ImportMode,
)

# Create request
request = ProjectImportRequest(
    repo_url="https://github.com/example/project",
    branch="main",
    shallow_clone=True,
    language=SupportedLanguage.JAVA,  # or None for auto-detection
    mode=ImportMode.FULL,
    include_paths=["src/main"],
    exclude_paths=["src/test"],
    create_domain_plugin=True,
    import_docs=True,
)

# Run pipeline
async def run_import():
    def progress_callback(status):
        print(f"Progress: {status.overall_progress}% - {status.current_step}")

    pipeline = ProjectImportPipeline(progress_callback=progress_callback)
    result = await pipeline.run(request)

    print(f"CPG: {result.cpg_path}")
    print(f"DuckDB: {result.duckdb_path}")
    print(f"Language: {result.detected_language}")
    print(f"Quality Score: {result.validation_report['quality_score']}")

import asyncio
asyncio.run(run_import())
```

### Running Individual Steps

```python
from src.project_import.pipeline import ProjectImportPipeline

pipeline = ProjectImportPipeline()

# Step context
context = {
    "request": ProjectImportRequest(),
    "source_path": Path("./workspace/project"),
    "duckdb_path": "./workspace/project.duckdb",
}

# Run validation step
result = await pipeline.run_step("validate", context)
print(result["validation_report"])
```

---

## Troubleshooting

### Joern Frontend Not Found

```
RuntimeError: Frontend not found at expected paths
```

**Solution:** Check `JOERN_HOME` or specify explicitly:
```bash
export JOERN_HOME=/path/to/joern
python -m src.cli.import_commands full --repo ...
```

### Insufficient Memory for Joern

```
java.lang.OutOfMemoryError: Java heap space
```

**Solution:** Increase memory:
```bash
python -m src.cli.import_commands full --repo ... --memory 32
```

### Language Not Detected

```
ValueError: No supported source files found
```

**Solution:** Specify language explicitly:
```bash
python -m src.cli.import_commands full --repo ... --language java
```

### CPG Validation Failed

```
Validation errors: ['methods_exist: expected >= 1, got 0']
```

**Solution:** Check:
1. Source code path is correct
2. Joern frontend matches the language
3. Files are not excluded by patterns

---

## Configuration (config.yaml)

Settings for the `project_import` module in `config.yaml`:

```yaml
project_import:
  joern:
    # Path to local Joern installation (optional if using Docker)
    home: ${JOERN_HOME}
    # Use Docker instead of local Joern
    use_docker: false
    # Docker image for Joern
    docker_image: "ghcr.io/joernio/joern:latest"
    # Server connection timeout (seconds)
    server_timeout: 30
    # JVM memory (GB)
    memory_gb: 16

  workspace:
    # Directory for cloned repositories
    clone_dir: "./workspace"
    # Directory for CPG files
    cpg_dir: "./workspace"
    # Directory for DuckDB files
    duckdb_dir: "./workspace"

  defaults:
    # Default shallow clone depth
    shallow_depth: 1
    # Default exclusion patterns
    exclude_patterns:
      - "node_modules"
      - "venv"
      - ".venv"
      - "__pycache__"
      - ".git"
      - "test"
      - "tests"
      - "vendor"
      - "third_party"
```

---

## Component Architecture

### JoernServerManager

Central component for managing the Joern server:

```python
from src.project_import import JoernServerManager

# Create manager
manager = JoernServerManager(use_docker=True)

# Start server
await manager.start()

# Get client
client = manager.get_client()

# Stop server
await manager.stop()
```

### ProjectRegistry

Project registry in PostgreSQL:

```python
from src.project_import import ProjectRegistry

async with ProjectRegistry() as registry:
    # List projects
    projects = await registry.list_projects()

    # Activate project
    await registry.set_active_project("my_project")

    # Delete project
    await registry.delete_project("old_project", delete_files=True)
```

### LocalJoernRunner / DockerJoernRunner

Runners for executing Joern commands:

```python
# Local execution
from src.project_import import LocalJoernRunner
runner = LocalJoernRunner(joern_home="/path/to/joern")

# Docker execution
from src.project_import import DockerJoernRunner
runner = DockerJoernRunner(image="ghcr.io/joernio/joern:latest")

# Run frontend
await runner.run_frontend("pysrc2cpg", source_path, output_cpg)
```

---

## See Also

- [REST API Documentation](../api/REST_API.md) - HTTP API endpoints
- [API Reference](../reference/API.md) - Python API
- [Scenarios Guide](SCENARIOS.md) - Analysis scenarios
