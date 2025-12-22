# Architecture Module

Architecture validation including circular dependency detection and layer violation checking.

## Overview

```
src/architecture/
├── validator.py         # Architecture validator
├── dependency.py        # Dependency analyzer
├── layers.py            # Layer violation checker
└── __init__.py
```

## Features

- Circular dependency detection
- Layer violation checking
- Module boundary validation
- Architecture drift detection

## Usage

```python
from src.architecture import ArchitectureValidator

validator = ArchitectureValidator(cpg)
violations = validator.check_circular_dependencies()
layer_issues = validator.check_layer_violations(rules)
```

## See Also

- `/src/workflow/scenarios/architecture.py`
