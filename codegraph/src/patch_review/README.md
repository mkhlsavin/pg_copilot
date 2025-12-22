# Patch Review Module

Multi-source patch parsing and analysis for code review automation.

## Overview

```
src/patch_review/
├── patch_parser.py      # Main patch parser
├── models.py            # Data models
├── analyzers/           # Patch analyzers
└── __init__.py
```

## Supported Sources

- Git diff (unified format)
- GitHub Pull Request API
- GitLab Merge Request API

## Features

- Language detection
- Method extraction (with tree-sitter support)
- Change type classification
- Impact analysis

## Usage

```python
from src.patch_review.patch_parser import PatchParser

parser = PatchParser()
patch = parser.parse_git_diff(diff_content)

for file in patch.files:
    print(f"{file.path}: {len(file.changes)} changes")
```

## See Also

- `/src/code_review/` - Code review system
- `/src/workflow/scenarios/code_review.py`
