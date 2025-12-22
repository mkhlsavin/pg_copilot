# Intent Module

Intent classification system for understanding user queries and routing them to appropriate analysis scenarios.

## Overview

```
src/intent/
├── classifier.py        # Main intent classifier
├── patterns.py          # Intent patterns and keywords
├── entity_extractor.py  # Named entity extraction
└── __init__.py          # Module exports
```

## Intent Types

| Intent | Description | Example |
|--------|-------------|---------|
| `definition` | Find where something is defined | "Where is X defined?" |
| `call_graph` | Analyze call relationships | "What calls X?" |
| `dataflow` | Trace data flow | "How does data flow through X?" |
| `security` | Security analysis | "Find vulnerabilities" |
| `performance` | Performance analysis | "Find bottlenecks" |
| `documentation` | Generate documentation | "Document function X" |
| `explanation` | Explain code/concept | "Explain how X works" |
| `refactoring` | Refactoring suggestions | "Find code smells" |

## Usage

```python
from src.intent.classifier import IntentClassifier

classifier = IntentClassifier()

# Classify query
result = classifier.classify("Where is heap_insert defined?")
# {
#     'intent': 'definition',
#     'confidence': 0.95,
#     'entities': {'function': 'heap_insert'},
#     'scenario': 'onboarding'
# }
```

## Entity Extraction

```python
from src.intent.entity_extractor import EntityExtractor

extractor = EntityExtractor()

entities = extractor.extract("What functions call heap_insert in heapam.c?")
# {
#     'function': 'heap_insert',
#     'file': 'heapam.c',
#     'relationship': 'callers'
# }
```

## Pattern Matching

```python
from src.intent.patterns import INTENT_PATTERNS

# Intent detection patterns
INTENT_PATTERNS = {
    'definition': [
        r'where is .* defined',
        r'find .* definition',
        r'locate .* function',
    ],
    'call_graph': [
        r'what calls .*',
        r'what does .* call',
        r'callers of .*',
    ],
    # ...
}
```

## Configuration

```yaml
intent:
  confidence_threshold: 0.7
  fallback_intent: explanation
  use_llm_fallback: true
```

## See Also

- `/src/agents/analyzer_agent.py` - Query analysis
- `/src/workflow/scenarios/` - Scenario routing
