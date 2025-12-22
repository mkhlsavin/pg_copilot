# Compliance Module

Compliance and coding standards checking including naming conventions, license headers, and style guides.

## Overview

```
src/compliance/
├── checker.py           # Main compliance checker
├── rules/               # Compliance rules
│   ├── naming.py        # Naming conventions
│   ├── licensing.py     # License headers
│   └── style.py         # Style guide rules
└── __init__.py
```

## Features

- Naming convention validation
- License header checking
- Coding standard compliance
- Custom rule support

## Usage

```python
from src.compliance.checker import ComplianceChecker

checker = ComplianceChecker(rules=['naming', 'licensing'])
violations = checker.check_codebase()
```

## See Also

- `/src/workflow/scenarios/compliance.py`
