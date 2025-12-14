# Prompts Module

Prompt management and templates for LLM interactions across all analysis scenarios.

## Overview

```
src/prompts/
├── prompt_registry.py   # Central prompt registry
├── templates/           # Prompt templates
│   ├── analysis.py      # Analysis prompts
│   ├── generation.py    # Query generation prompts
│   ├── interpretation.py # Result interpretation
│   └── scenarios/       # Scenario-specific prompts
└── __init__.py
```

## Usage

```python
from src.prompts.prompt_registry import get_global_registry

registry = get_global_registry()

# Get prompt template
prompt = registry.get_prompt('security_analysis', {
    'query': 'Find SQL injection vulnerabilities',
    'context': {...}
})
```

## Template Structure

```python
SECURITY_ANALYSIS_PROMPT = """
You are analyzing code for security vulnerabilities.

Query: {query}
Context: {context}

Identify potential security issues and explain their impact.
"""
```

## See Also

- `/src/generation/prompts.py` - Generation prompts
- `/src/agents/` - Agent-specific prompts
