# User Guide

Complete guide to using RAG-CPGQL for code analysis.

## Overview

RAG-CPGQL answers natural language questions about codebases by combining:
- **Semantic search** - Find code by meaning and intent
- **Structural search** - Traverse call graphs and data flow
- **LLM synthesis** - Generate human-readable answers

## Basic Usage

### Interactive Mode

```bash
python demo_simple.py
```

Enter questions at the prompt:
```
> What does CommitTransaction do?
> Find methods that handle memory allocation
> Show the call chain from executor to storage
```

### Programmatic Usage

```python
from src.workflow.langgraph_workflow_simple import run_workflow

question = "What methods handle transaction commits?"
result = run_workflow(question)

print(f"Answer: {result['answer']}")
print(f"Confidence: {result['confidence']}")
```

## Question Types

### Definition Queries

Find where code is defined:
```
Find method 'heap_insert'
Where is AbortTransaction defined?
Show me the RelationGetBufferForTuple function
```

### Relationship Queries

Understand code relationships:
```
What methods call LWLockAcquire?
Find callers of MemoryContextCreate
What does heap_insert call?
```

### Semantic Queries

Ask about behavior and purpose:
```
How does PostgreSQL handle MVCC?
Explain the transaction commit process
What mechanism ensures durability?
```

### Security Queries

Find vulnerabilities:
```
Find potential SQL injection points
Show unsanitized user input paths
Find buffer overflow risks
```

## Understanding Results

### Result Structure

```python
{
    "answer": "CommitTransaction finalizes a transaction by...",
    "confidence": 0.85,
    "sources": [
        {"method": "CommitTransaction", "file": "xact.c", "line": 1234},
        {"method": "CommitTransactionCommand", "file": "xact.c", "line": 1456}
    ],
    "query_used": "cpg.method.name('CommitTransaction')...",
    "execution_time_ms": 150
}
```

### Confidence Levels

| Level | Meaning |
|-------|---------|
| > 0.9 | High confidence - direct match |
| 0.7-0.9 | Good confidence - semantic match |
| 0.5-0.7 | Moderate - inference required |
| < 0.5 | Low - best effort answer |

## Advanced Features

### Hybrid Search Mode

Combine semantic and structural search:

```python
from src.agents.retriever_agent import RetrieverAgent

retriever = RetrieverAgent(
    enable_hybrid=True,
    vector_weight=0.6,
    graph_weight=0.4
)

results = retriever.retrieve_hybrid(
    question="Find memory allocation patterns",
    mode="hybrid",
    query_type="structural"
)
```

### Multi-Domain Analysis

Switch between codebases:

```python
from src.config import CPGConfig

# Analyze PostgreSQL
pg_config = CPGConfig()
pg_config.set_cpg_type("postgresql")

# Analyze Linux Kernel
lk_config = CPGConfig()
lk_config.set_cpg_type("linux_kernel")
```

### Scenario-Based Analysis

Use specialized workflows:

```python
from src.workflow.multi_scenario_workflow import create_workflow

# Security analysis
workflow = create_workflow(scenario="vulnerability_detection")
result = workflow.run("Find SQL injection vulnerabilities")

# Performance analysis
workflow = create_workflow(scenario="performance_analysis")
result = workflow.run("Find functions with high complexity")
```

## Best Practices

### Writing Effective Questions

**Good questions:**
- "What functions handle memory allocation in the buffer manager?"
- "Show the call path from parser to executor"
- "Find unsanitized inputs that reach database queries"

**Less effective:**
- "Tell me about the code" (too vague)
- "Fix this bug" (action request, not analysis)
- "Everything about transactions" (too broad)

### Optimizing Performance

1. **Be specific** - Narrow questions get faster answers
2. **Use structural queries** - When you know the pattern
3. **Enable caching** - For repeated similar queries
4. **Limit scope** - Add file or subsystem constraints

### Interpreting Answers

1. **Check sources** - Verify the code references
2. **Consider confidence** - Lower confidence = verify manually
3. **Follow up** - Ask clarifying questions
4. **Cross-reference** - Compare with actual code

## Workflow Integration

### CI/CD Integration

```yaml
# .github/workflows/code-analysis.yml
- name: Run Code Analysis
  run: |
    python -c "
    from src.workflow import run_workflow
    result = run_workflow('Find potential security issues')
    if result['issues']:
        exit(1)
    "
```

### Code Review

```bash
# Analyze a patch
python demo_patch_review.py --patch changes.diff

# Output: Security, performance, and architecture findings
```

### Documentation Generation

```python
from src.workflow import create_workflow

workflow = create_workflow(scenario="documentation")
result = workflow.run("Document the transaction subsystem")

# result['documentation'] contains generated docs
```

## Next Steps

- [Scenarios](SCENARIOS.md) - All 16 use cases
- [CLI Usage](CLI_USAGE.md) - Command-line interface
- [API Reference](../reference/API.md) - Programmatic access
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues
