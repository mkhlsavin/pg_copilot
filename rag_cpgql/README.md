# RAG-CPGQL: Hybrid Graph-Vector Code Analysis System

A production-ready code analysis system combining **semantic vector search** with **structural graph queries** to understand large codebases through natural language.

**Target Publication:** Tier-1 Software Engineering Venue (ICSE/FSE/ASE)

## Key Features

- **Hybrid Retrieval** - Parallel async vector (ChromaDB) + graph (DuckDB) search with RRF merging
- **Multi-Domain Support** - PostgreSQL, Linux Kernel, LLVM, or any codebase - switch with one config line
- **13 Specialized Agents** - Question analysis, retrieval, enrichment, generation, interpretation
- **16 Workflow Scenarios** - From codebase onboarding to security incident response
- **100x Faster Queries** - Sub-3ms average with 90%+ memory reduction vs traditional approaches

## Quick Start

```bash
# 1. Clone and setup environment
git clone <repository-url>
cd rag_cpgql
conda create -n llama.cpp python=3.11
conda activate llama.cpp
pip install -r requirements.txt

# 2. Run interactive demo
python demo_simple.py

# Example queries:
# - "Find method 'CommitTransaction'"
# - "What methods call 'AbortTransaction'?"
# - "Find SQL injection vulnerabilities"
```

See [Installation Guide](docs/getting-started/INSTALLATION.md) for detailed setup.

## Use Cases (16 Scenarios)

### 1. Codebase Onboarding
> "Where is heap_insert defined?", "What functions call LWLockAcquire?", "Explain the executor subsystem"

Navigate code definitions, call graphs, data flow, subsystem architecture, and debugging paths.

### 2. Security Audit
> "Find SQL injection vulnerabilities", "List network-facing entry points"

Detect vulnerabilities, analyze attack surface, and identify security risks.

### 3. Documentation Generation
> "Document the transaction subsystem"

Generate API documentation from code structure and comments.

### 4. Feature Development
> "Where should I add a new join algorithm?"

Find extension points, hooks, and integration locations for new features.

### 5. Refactoring Assistance
> "Find dead code", "Show similar code patterns"

Identify unused code, duplicates, and refactoring opportunities.

### 6. Performance Optimization
> "Find functions with high complexity", "Analyze memory allocation patterns"

Locate hotspots, complexity issues, memory patterns, and concurrency bottlenecks.

### 7. Test Coverage Analysis
> "Generate unit tests for heap_insert"

Generate test cases and identify untested code paths.

### 8. Compliance Checking
> "Check coding style violations"

Verify naming conventions, license headers, and coding standards.

### 9. Code Review Assistance
> "Review this patch for breaking changes"

Automated code review and change impact analysis.

### 10. Cross-Repository Impact
> "Which extensions depend on this function?"

Analyze API changes and cross-repository dependencies.

### 11. Architecture Violation Detection
> "Find circular dependencies"

Detect layering violations and architectural issues.

### 12. Technical Debt Quantification
> "Find all TODO comments"

Quantify and track technical debt across the codebase.

### 13. Mass Refactoring Automation
> "Rename all instances of ExecProcNode"

Bulk code changes and signature modifications.

### 14. Security Incident Response
> "Trace data flow from this vulnerability"

Emergency investigation and impact analysis.

### 15. Debugging Support
> "Where should I set breakpoints for query execution?", "Trace execution through the executor"

Find debug points, trace execution paths, and locate logging points.

### 16. Entry Points and Attack Surface
> "Find all external entry points", "List network-facing functions"

Identify attack surface, network handlers, and trust boundaries.

See [Scenarios Guide](docs/guides/SCENARIOS.md) for detailed examples.

## Domain Plugin System

The system uses a **pluggable domain architecture** that separates codebase-specific knowledge from core analysis logic. This allows easy adaptation to new codebases.

### Supported Domains

| Domain | Description | Key Functions |
|--------|-------------|---------------|
| **PostgreSQL** | Database server analysis | `palloc`, `LWLockAcquire`, `ereport`, `SPI_execute` |
| **Linux Kernel** | Kernel code analysis | `kmalloc`, `spin_lock`, `printk` |
| **LLVM** | Compiler infrastructure | `CreateAlloca`, `IRBuilder` |
| **Generic C/C++** | Any C/C++ codebase | Standard library patterns |

### Plugin Capabilities

Each domain plugin provides:

```python
# Memory management functions
plugin.get_memory_functions()      # {'allocation': [...], 'deallocation': [...]}

# Synchronization primitives
plugin.get_concurrency_functions() # {'lwlock': [...], 'spinlock': [...], 'atomic': [...]}

# Security analysis
plugin.get_vulnerability_function_mappings()  # {'sql_injection': [...], 'buffer_overflow': [...]}
plugin.get_taint_sources()         # User input functions
plugin.get_taint_sinks()           # Dangerous operations

# Code patterns
plugin.get_duplicate_pattern_functions()  # {'error_handling': [...], 'locking': [...]}
```

### Switching Domains

```yaml
# config.yaml
domain: postgresql  # or: linux_kernel, llvm, generic_cpp
```

See [Domain Plugin Guide](docs/development/DOMAIN_PLUGINS.md) for creating custom plugins.

## Architecture

```
User Question
    |
    v
+------------------+     +------------------+     +------------------+
|  Analyzer Agent  | --> | Retriever Agent  | --> | Enrichment Agent |
|  (Intent/Domain) |     | (Hybrid Search)  |     | (Semantic Tags)  |
+------------------+     +------------------+     +------------------+
                               |
              +----------------+----------------+
              |                                 |
              v                                 v
     +----------------+                +----------------+
     | Vector Search  |   PARALLEL     | Graph Search   |
     | (ChromaDB)     |   ========     | (DuckDB)       |
     | 250K documents |                | 52K methods    |
     +----------------+                +----------------+
              |                                 |
              +----------------+----------------+
                               |
                               v
                    +--------------------+
                    | RRF Merging        |
                    | Cross-Source Rank  |
                    +--------------------+
                               |
    +------------------+       |       +------------------+
    | Generator Agent  | <-----+-----> | Interpreter Agent|
    | (Query Gen)      |               | (Answer Synth)   |
    +------------------+               +------------------+
                               |
                               v
                    +--------------------+
                    |   Final Answer     |
                    | (with confidence)  |
                    +--------------------+
```

## Documentation

### Getting Started
- [Quick Start](docs/getting-started/README.md) - 5-minute setup
- [Installation](docs/getting-started/INSTALLATION.md) - Detailed setup guide
- [Configuration](docs/getting-started/CONFIGURATION.md) - Config options

### User Guides
- [User Guide](docs/guides/USER_GUIDE.md) - End-to-end tutorial
- [Scenarios](docs/guides/SCENARIOS.md) - All 14 use cases with examples
- [Troubleshooting](docs/guides/TROUBLESHOOTING.md) - Common issues
- [CLI Usage](docs/guides/CLI_USAGE.md) - Command-line interface

### Reference
- [API Reference](docs/reference/API.md) - Complete API documentation
- [Agents](docs/reference/AGENTS.md) - Agent architecture
- [Workflows](docs/reference/WORKFLOWS.md) - Workflow system
- [CPG Schema](docs/reference/SCHEMA.md) - Database schema
- [SQL Cookbook](docs/reference/SQL_COOKBOOK.md) - Query examples

### Development
- [Architecture](docs/development/ARCHITECTURE.md) - System design
- [Domain Plugins](docs/development/DOMAIN_PLUGINS.md) - Creating custom domain plugins
- [Contributing](docs/development/CONTRIBUTING.md) - How to contribute
- [Patterns](docs/development/PATTERNS.md) - Code patterns

### Integrations
- [GigaChat](docs/integrations/GIGACHAT.md) - Russian LLM integration
- [Joern](docs/integrations/JOERN.md) - CPG parser setup

## Project Statistics

| Metric | Value |
|--------|-------|
| Production Code | ~69,000 lines |
| Test Coverage | 54+ unit tests (100% pass) |
| Methods Indexed | 52,303 |
| Call Nodes | 111,208 |
| Vector Documents | 250,000+ |
| Domains Supported | 4 (PostgreSQL, Linux, LLVM, Generic) |
| Workflow Scenarios | 16 |
| Agents | 13 specialized |

## License

[License information]

## Citation

```bibtex
@inproceedings{rag-cpgql2026,
  title={RAG-CPGQL: Hybrid Graph-Vector Retrieval for Code Understanding},
  author={...},
  booktitle={Proceedings of ...},
  year={2026}
}
```

---

**Last Updated:** December 2025
