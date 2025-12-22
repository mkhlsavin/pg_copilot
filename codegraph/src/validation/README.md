# Validation Module

Input and output validation utilities for ensuring data integrity.

## Overview

```
src/validation/
├── input.py             # Input validation
├── output.py            # Output validation
├── cpgql.py             # CPGQL validation
└── __init__.py
```

## Features

- Query input validation
- CPGQL syntax validation
- Response format validation
- Schema validation

## Usage

```python
from src.validation.cpgql import validate_cpgql

is_valid, errors = validate_cpgql("cpg.method.name('test').l")
```

## See Also

- `/src/execution/query_validator.py`
