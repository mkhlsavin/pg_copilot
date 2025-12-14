# Code Review Module

Automated code review system with impact analysis, best practices checking, and review report generation.

## Overview

```
src/code_review/
├── reviewer.py          # Main code reviewer
├── checkers/            # Review checkers
│   ├── style.py         # Style checker
│   ├── security.py      # Security checker
│   ├── performance.py   # Performance checker
│   └── best_practices.py
├── impact.py            # Impact analysis
└── __init__.py
```

## Usage

```python
from src.code_review.reviewer import CodeReviewer

reviewer = CodeReviewer()
review = reviewer.review_patch(patch_content)

for issue in review.issues:
    print(f"[{issue.severity}] {issue.message}")
```

## Features

- Automated style checking
- Security vulnerability detection
- Performance impact analysis
- Best practices validation
- Change impact assessment

## See Also

- `/src/patch_review/` - Patch parsing
- `/src/workflow/scenarios/code_review.py`
