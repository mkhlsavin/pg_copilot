# RAG-CPGQL: Hybrid Graph-Vector Code Analysis System

A production-ready code analysis system combining **semantic vector search** with **structural graph queries** to understand large codebases through natural language.

**Target Publication:** Tier-1 Software Engineering Venue (ICSE/FSE/ASE)

## Key Features

- **Hybrid Retrieval** - Parallel async vector (ChromaDB) + graph (DuckDB) search with RRF merging
- **Multi-Domain Support** - PostgreSQL, Linux Kernel, LLVM, or any codebase - switch with one config line
- **13 Specialized Agents** - Question analysis, retrieval, enrichment, generation, interpretation
- **16 Workflow Scenarios** - From definition search to security incident response
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

## Use Cases

### 1. Definition Search
> "Where is the function `heap_insert` defined?"

Find function/class definitions across the codebase.

### 2. Call Graph Analysis
> "What functions call `LWLockAcquire`?"

Trace call relationships and dependencies.

### 3. Data Flow Tracing
> "How does user input flow to SQL execution?"

Track data propagation through the system.

### 4. Vulnerability Detection
> "Find potential SQL injection points"

Identify security vulnerabilities with CWE mappings.

### 5. Dead Code Detection
> "Find unreachable functions"

Locate unused code for cleanup.

### 6. Performance Analysis
> "Find functions with high cyclomatic complexity"

Identify performance bottlenecks.

### 7. Code Duplication
> "Find similar code patterns"

Detect clone candidates for refactoring.

### 8. Entry Point Discovery
> "What are the public API entry points?"

Map system boundaries and interfaces.

### 9. Concurrency Analysis
> "Find race conditions in shared data access"

Analyze thread safety patterns.

### 10. Dependency Analysis
> "What modules depend on the storage layer?"

Understand module dependencies.

### 11. Documentation Generation
> "Document the transaction subsystem"

Generate documentation from code structure.

### 12. Tech Debt Assessment
> "Find code with excessive coupling"

Identify technical debt hot spots.

### 13. Security Incident Response
> "Trace the impact of this vulnerability"

Investigate security incidents.

### 14. Refactoring Orchestration
> "Plan refactoring of the buffer manager"

Generate refactoring plans.

### 15. Code Review Automation
> "Review this patch for security issues"

Automated code review assistance.

### 16. Architecture Analysis
> "Map the subsystem architecture"

Understand architectural patterns.

See [Scenarios Guide](docs/guides/SCENARIOS.md) for detailed examples.

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
- [Scenarios](docs/guides/SCENARIOS.md) - All 16 use cases with examples
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
