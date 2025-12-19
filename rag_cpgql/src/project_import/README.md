# Project Import Module

Universal project import pipeline for ingesting codebases into CodeGraph with CPG generation.

## Overview

```
src/project_import/
├── pipeline.py          # Import pipeline
├── registry.py          # Frontend registry
├── config.py            # Import configuration
├── steps/               # Pipeline steps
│   ├── detect_language.py
│   ├── joern_import.py
│   └── cpg_export.py
├── frontends/           # Language frontends
│   ├── c_frontend.py
│   ├── python_frontend.py
│   └── java_frontend.py
└── __init__.py
```

## Supported Languages

- C/C++
- Python
- Java
- JavaScript/TypeScript
- Go

## Usage

```python
from src.project_import.pipeline import ImportPipeline

pipeline = ImportPipeline()
result = pipeline.import_project(
    path="/path/to/source",
    language="c"
)
```

## CLI

```bash
codegraph import /path/to/source --language c --name my-project
```

## See Also

- `/src/api/routers/import_project.py` - Import API
- `/docs/guides/PROJECT_IMPORT.md`
