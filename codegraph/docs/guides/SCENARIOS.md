# Workflow Scenarios Guide

CodeGraph supports 16 specialized analysis scenarios.

## Table of Contents

- [Scenario Overview](#scenario-overview)
- [1. Definition Search](#1-definition-search)
  - [Example Questions](#example-questions)
  - [Usage](#usage)
- [2. Call Graph Analysis](#2-call-graph-analysis)
  - [Example Questions](#example-questions)
  - [Usage](#usage)
- [3. Data Flow Tracing](#3-data-flow-tracing)
  - [Example Questions](#example-questions)
  - [Usage](#usage)
- [4. Vulnerability Detection](#4-vulnerability-detection)
  - [Example Questions](#example-questions)
  - [Security Patterns Detected](#security-patterns-detected)
  - [Usage](#usage)
- [5. Dead Code Detection](#5-dead-code-detection)
  - [Example Questions](#example-questions)
  - [Dead Code Patterns](#dead-code-patterns)
  - [Usage](#usage)
- [6. Performance Analysis](#6-performance-analysis)
  - [Example Questions](#example-questions)
  - [Metrics Analyzed](#metrics-analyzed)
  - [Usage](#usage)
- [7. Code Duplication](#7-code-duplication)
  - [Example Questions](#example-questions)
  - [Usage](#usage)
- [8. Entry Point Discovery](#8-entry-point-discovery)
  - [Example Questions](#example-questions)
  - [PostgreSQL Entry Patterns](#postgresql-entry-patterns)
  - [Usage](#usage)
- [9. Concurrency Analysis](#9-concurrency-analysis)
  - [Example Questions](#example-questions)
  - [Patterns Analyzed](#patterns-analyzed)
  - [Usage](#usage)
- [10. Dependency Analysis](#10-dependency-analysis)
  - [Example Questions](#example-questions)
  - [Usage](#usage)
- [11. Documentation Generation](#11-documentation-generation)
  - [Example Questions](#example-questions)
  - [Usage](#usage)
- [12. Tech Debt Assessment](#12-tech-debt-assessment)
  - [Example Questions](#example-questions)
  - [Debt Indicators](#debt-indicators)
  - [Usage](#usage)
- [13. Security Incident Response](#13-security-incident-response)
  - [Example Questions](#example-questions)
  - [Usage](#usage)
- [14. Refactoring Orchestration](#14-refactoring-orchestration)
  - [Example Questions](#example-questions)
  - [Usage](#usage)
- [15. Code Review Automation](#15-code-review-automation)
  - [Example Questions](#example-questions)
  - [Usage](#usage)
- [16. Architecture Analysis](#16-architecture-analysis)
  - [Example Questions](#example-questions)
  - [Usage](#usage)
- [Combining Scenarios](#combining-scenarios)
- [Next Steps](#next-steps)

## Scenario Overview

| # | Scenario | Use Case |
|---|----------|----------|
| 1 | Definition Search | Find function/class definitions |
| 2 | Call Graph Analysis | Trace call relationships |
| 3 | Data Flow Tracing | Track data propagation |
| 4 | Vulnerability Detection | Find security issues |
| 5 | Dead Code Detection | Find unused code |
| 6 | Performance Analysis | Identify bottlenecks |
| 7 | Code Duplication | Detect clones |
| 8 | Entry Point Discovery | Map API boundaries |
| 9 | Concurrency Analysis | Thread safety |
| 10 | Dependency Analysis | Module dependencies |
| 11 | Documentation Generation | Auto-generate docs |
| 12 | Tech Debt Assessment | Find debt hotspots |
| 13 | Security Incident Response | Incident investigation |
| 14 | Refactoring Orchestration | Plan refactoring |
| 15 | Code Review Automation | Automated reviews |
| 16 | Architecture Analysis | Architectural patterns |

---

## 1. Definition Search

Find where functions, classes, or variables are defined.

### Example Questions
```
Find method 'heap_insert'
Where is AbortTransaction defined?
Show the definition of RelFileNode struct
Find all methods in file 'xact.c'
```

### Usage
```python
from src.workflow import MultiScenarioCopilot

copilot = MultiScenarioCopilot()
result = copilot.run("Find method 'CommitTransaction'", scenario="definition_search")

print(result['definitions'])
# [{'name': 'CommitTransaction', 'file': 'xact.c', 'line': 2156}]
```

---

## 2. Call Graph Analysis

Trace function call relationships.

### Example Questions
```
What functions call LWLockAcquire?
Show callers of heap_insert
Find the call chain from executor_start to heap_insert
What does ProcessQuery call?
```

### Usage
```python
copilot = MultiScenarioCopilot()
result = copilot.run("Find all callers of MemoryContextCreate", scenario="call_graph")

for caller in result['callers']:
    print(f"{caller['name']} calls MemoryContextCreate at line {caller['line']}")
```

---

## 3. Data Flow Tracing

Track how data flows through the system.

### Example Questions
```
How does user input reach SQL execution?
Trace the flow of query string from parser to executor
Where does the result of heap_fetch go?
Find all paths from input to database write
```

### Usage
```python
copilot = MultiScenarioCopilot()
result = copilot.run("Trace user input to query execution", scenario="data_flow")

for path in result['data_flows']:
    print(f"Flow: {' -> '.join(path['nodes'])}")
```

---

## 4. Vulnerability Detection

Find potential security issues with CWE mappings.

### Example Questions
```
Find SQL injection vulnerabilities
Show potential buffer overflows
Find unsanitized user input
Detect format string vulnerabilities
```

### Security Patterns Detected
- SQL Injection (CWE-89)
- Buffer Overflow (CWE-120)
- Command Injection (CWE-78)
- Format String (CWE-134)
- Integer Overflow (CWE-190)

### Usage
```python
workflow = create_workflow(scenario="vulnerability_detection")
result = workflow.run("Find SQL injection vulnerabilities")

for vuln in result['vulnerabilities']:
    print(f"CWE-{vuln['cwe']}: {vuln['description']}")
    print(f"  File: {vuln['file']}:{vuln['line']}")
    print(f"  Severity: {vuln['severity']}")
```

---

## 5. Dead Code Detection

Find unreachable or unused code.

### Example Questions
```
Find unreachable functions
Show unused static functions
Find code after return statements
Detect functions with no callers
```

### Dead Code Patterns
- Functions with no callers
- Unreachable code blocks
- Unused static functions
- Dead stores
- Commented-out code

### Usage
```python
workflow = create_workflow(scenario="dead_code")
result = workflow.run("Find unused functions")

for dead in result['dead_code']:
    print(f"Unused: {dead['name']} in {dead['file']}")
```

---

## 6. Performance Analysis

Identify performance bottlenecks.

### Example Questions
```
Find functions with high cyclomatic complexity
Show expensive loops
Find O(n^2) patterns
Identify hot paths in query execution
```

### Metrics Analyzed
- Cyclomatic complexity
- Loop nesting depth
- Function length
- Call frequency
- Memory allocation patterns

### Usage
```python
workflow = create_workflow(scenario="performance")
result = workflow.run("Find functions with complexity > 20")

for func in result['complex_functions']:
    print(f"{func['name']}: complexity={func['complexity']}")
```

---

## 7. Code Duplication

Detect similar code patterns.

### Example Questions
```
Find duplicate code blocks
Show similar functions
Detect copy-paste patterns
Find refactoring opportunities for duplicates
```

### Usage
```python
workflow = create_workflow(scenario="duplication")
result = workflow.run("Find similar code patterns")

for clone in result['clones']:
    print(f"Clone pair: {clone['location1']} <-> {clone['location2']}")
    print(f"Similarity: {clone['similarity']:.0%}")
```

---

## 8. Entry Point Discovery

Map API boundaries and entry points.

### Example Questions
```
What are the public API entry points?
Find all exported functions
Show main entry points
Find hook functions
```

### PostgreSQL Entry Patterns
- `PG_FUNCTION_INFO_V1` macros
- `PostgresMain` and command handlers
- Hook registration functions

### Usage
```python
workflow = create_workflow(scenario="entry_points")
result = workflow.run("Find API entry points")

for entry in result['entry_points']:
    print(f"Entry: {entry['name']} ({entry['type']})")
```

---

## 9. Concurrency Analysis

Analyze thread safety and synchronization.

### Example Questions
```
Find race conditions
Show lock ordering issues
Find missing lock acquisitions
Detect deadlock potential
```

### Patterns Analyzed
- Lock acquire/release pairs
- Shared variable access
- Critical section coverage
- Lock hierarchy violations

### Usage
```python
workflow = create_workflow(scenario="concurrency")
result = workflow.run("Find potential race conditions")

for issue in result['concurrency_issues']:
    print(f"Issue: {issue['type']} at {issue['location']}")
```

---

## 10. Dependency Analysis

Understand module dependencies.

### Example Questions
```
What modules depend on storage?
Show the dependency graph
Find circular dependencies
Which modules use the buffer manager?
```

### Usage
```python
workflow = create_workflow(scenario="dependencies")
result = workflow.run("Show dependencies of transaction module")

for dep in result['dependencies']:
    print(f"{dep['from']} -> {dep['to']}")
```

---

## 11. Documentation Generation

Generate documentation from code.

### Example Questions
```
Document the transaction subsystem
Generate API documentation for executor
Summarize the buffer manager
Create documentation for heap functions
```

### Usage
```python
workflow = create_workflow(scenario="documentation")
result = workflow.run("Document the transaction subsystem")

print(result['documentation'])
# Markdown-formatted documentation
```

---

## 12. Tech Debt Assessment

Identify technical debt hotspots.

### Example Questions
```
Find code with excessive coupling
Show modules needing refactoring
Find code smells
Identify maintenance hotspots
```

### Debt Indicators
- High complexity
- Deep nesting
- Long functions
- High coupling
- Missing error handling

### Usage
```python
workflow = create_workflow(scenario="tech_debt")
result = workflow.run("Find technical debt hotspots")

for debt in result['debt_items']:
    print(f"{debt['location']}: {debt['type']} (severity: {debt['severity']})")
```

---

## 13. Security Incident Response

Investigate security incidents.

### Example Questions
```
Trace the impact of CVE-XXXX
Find all code paths affected by this vulnerability
Show exploitation paths
Identify affected functions
```

### Usage
```python
workflow = create_workflow(scenario="security_incident")
result = workflow.run("Trace impact of vulnerability in parse_query")

for path in result['impact_paths']:
    print(f"Impact: {path['description']}")
```

---

## 14. Refactoring Orchestration

Plan and execute refactoring.

### Example Questions
```
Plan refactoring of the buffer manager
Extract method opportunities in executor
Find functions to split
Suggest interface improvements
```

### Usage
```python
workflow = create_workflow(scenario="refactoring")
result = workflow.run("Plan buffer manager refactoring")

for step in result['refactoring_plan']:
    print(f"Step {step['order']}: {step['action']}")
```

---

## 15. Code Review Automation

Automated code review assistance.

### Example Questions
```
Review this patch for security issues
Find potential bugs in this change
Check for style violations
Analyze test coverage for changes
```

### Usage
```bash
python demo_patch_review.py --patch changes.diff
```

Or programmatically:
```python
workflow = create_workflow(scenario="code_review")
result = workflow.run_on_patch("path/to/changes.diff")

for finding in result['findings']:
    print(f"{finding['severity']}: {finding['description']}")
```

---

## 16. Architecture Analysis

Understand architectural patterns.

### Example Questions
```
Map the subsystem architecture
Show layer boundaries
Find architectural violations
Identify design patterns used
```

### Usage
```python
workflow = create_workflow(scenario="architecture")
result = workflow.run("Map the PostgreSQL architecture")

for subsystem in result['subsystems']:
    print(f"{subsystem['name']}: {subsystem['description']}")
```

---

## Combining Scenarios

Run multiple scenarios together:

```python
from src.workflow import MultiScenarioWorkflow

workflow = MultiScenarioWorkflow()
workflow.add_scenario("vulnerability_detection")
workflow.add_scenario("performance")
workflow.add_scenario("tech_debt")

result = workflow.run("Analyze the executor module")

print(f"Security issues: {len(result['vulnerabilities'])}")
print(f"Performance issues: {len(result['performance_issues'])}")
print(f"Tech debt items: {len(result['debt_items'])}")
```

## Next Steps

- [TUI User Guide](TUI_USER_GUIDE.md) - General usage
- [API Reference](../reference/API.md) - Programmatic access
- [Patterns Reference](../development/PATTERNS.md) - Detection patterns
