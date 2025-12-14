# Examples

Demonstration scripts and usage examples for the RAG-CPGQL system.

## Overview

```
examples/
├── agent_migration_example.py    # Agent system migration patterns
├── demo_benchmark.py             # Performance benchmarking demo
├── demo_patch_review.py          # Patch review demonstration
├── prompt_registry_examples.py   # Prompt template usage
├── ragas_evaluation_examples.py  # RAGAS evaluation integration
└── week5_analyzer_test.py        # Analyzer testing examples
```

## Scripts

### agent_migration_example.py

Demonstrates migration patterns for the agent system:

```python
from examples.agent_migration_example import run_migration_demo

# Run migration demonstration
run_migration_demo()
```

### demo_benchmark.py

Performance benchmarking demonstration for retrieval and generation:

```python
from examples.demo_benchmark import run_benchmark

# Execute benchmark suite
results = run_benchmark()
```

### demo_patch_review.py

Interactive patch review demonstration:

```python
from examples.demo_patch_review import review_patch

# Review a git patch
result = review_patch("path/to/patch.diff")
```

Output formats:
- `demo_review_output.json` - Structured review results
- `demo_review_output.md` - Human-readable review report

### prompt_registry_examples.py

Examples of using the prompt template registry:

```python
from examples.prompt_registry_examples import (
    demonstrate_prompt_loading,
    demonstrate_variable_injection
)

# Load and use prompt templates
demonstrate_prompt_loading()
demonstrate_variable_injection()
```

### ragas_evaluation_examples.py

Integration with RAGAS for RAG evaluation:

```python
from examples.ragas_evaluation_examples import (
    evaluate_retrieval_quality,
    evaluate_generation_quality
)

# Evaluate retrieval component
retrieval_scores = evaluate_retrieval_quality(dataset)

# Evaluate generation component
generation_scores = evaluate_generation_quality(dataset)
```

### week5_analyzer_test.py

Test script for analyzer functionality:

```python
from examples.week5_analyzer_test import run_analyzer_tests

# Execute analyzer test suite
run_analyzer_tests()
```

## Running Examples

```bash
# Run individual example
python -m examples.demo_benchmark

# Run with specific configuration
python -m examples.demo_patch_review --input patch.diff

# Run RAGAS evaluation
python -m examples.ragas_evaluation_examples
```

## Configuration

Examples use the project's unified configuration:

```yaml
# config.yaml
examples:
  output_dir: "./examples/output"
  verbose: true
```

## Output Files

- `demo_review_output.json` - Structured patch review results
- `demo_review_output.md` - Markdown-formatted review report

## See Also

- `/docs/getting-started/` - Getting started guide
- `/scripts/` - Utility scripts
- `/tests/benchmark/` - Benchmark test suite
