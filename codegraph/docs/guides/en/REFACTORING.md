# Refactoring Analysis Guide

This guide covers using the refactoring analysis module to detect code smells, analyze impact, and plan refactoring tasks.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Code Smell Detection](#code-smell-detection)
  - [Supported Pattern Categories](#supported-pattern-categories)
  - [Severity Levels](#severity-levels)
  - [Detection Methods](#detection-methods)
  - [Code Smell Finding Structure](#code-smell-finding-structure)
- [Impact Analysis](#impact-analysis)
  - [Analyzing Method Changes](#analyzing-method-changes)
  - [Impact Analysis Structure](#impact-analysis-structure)
  - [Dependency Analysis](#dependency-analysis)
- [Refactoring Planning](#refactoring-planning)
  - [Creating a Refactoring Plan](#creating-a-refactoring-plan)
  - [Task Prioritization](#task-prioritization)
  - [Refactoring Task Structure](#refactoring-task-structure)
- [Refactoring Report](#refactoring-report)
  - [Generating a Full Report](#generating-a-full-report)
  - [Report Structure](#report-structure)
- [Supported Patterns](#supported-patterns)
  - [Bloater Patterns](#bloater-patterns)
  - [Complexity Patterns](#complexity-patterns)
  - [Duplicate Patterns](#duplicate-patterns)
  - [Dead Code Patterns](#dead-code-patterns)
- [SQL Queries for Detection](#sql-queries-for-detection)
- [See Also](#see-also)

## Overview

The refactoring module provides three specialized agents:

1. **TechnicalDebtDetector** - Detects code smells using pattern library
2. **ImpactAnalyzer** - Analyzes change impact and dependencies
3. **RefactoringPlanner** - Creates prioritized refactoring plans

---

## Quick Start

```python
from src.refactoring import (
    TechnicalDebtDetector,
    ImpactAnalyzer,
    RefactoringPlanner
)
from src.services.cpg_query_service import CPGQueryService
import duckdb

# Connect to CPG
conn = duckdb.connect("cpg.duckdb")
query_service = CPGQueryService(conn)

# Initialize agents
detector = TechnicalDebtDetector(query_service)
analyzer = ImpactAnalyzer(query_service)
planner = RefactoringPlanner(query_service)

# Detect code smells
findings = detector.detect_all()

# Analyze impact for a method
impact = analyzer.analyze("heap_insert", "backend/access/heap/heapam.c")

# Create refactoring plan
plan = planner.create_plan(findings, max_tasks=10)
```

---

## Code Smell Detection

### Supported Pattern Categories

| Category | Description | Examples |
|----------|-------------|----------|
| `bloater` | Large methods, long parameter lists | God Method, Long Parameter List |
| `complexity` | High cyclomatic complexity | Complex Conditionals, Deep Nesting |
| `duplicate` | Code duplication patterns | Duplicate Code, Similar Functions |
| `dead_code` | Unused or unreachable code | Dead Code, Unused Variables |
| `documentation` | Missing or outdated docs | Missing Comments, Stale Docs |

### Severity Levels

| Severity | Description | Action |
|----------|-------------|--------|
| `CRITICAL` | Severe issue requiring immediate fix | Fix immediately |
| `HIGH` | Significant issue | Fix in current sprint |
| `MEDIUM` | Moderate issue | Plan for next sprint |
| `LOW` | Minor issue | Address when convenient |
| `INFO` | Informational | Consider for improvement |

### Detection Methods

**Detect All Patterns:**
```python
findings = detector.detect_all(
    file_filter="backend/parser/*.c",  # Optional: filter by path
    severity_filter=["CRITICAL", "HIGH"]  # Optional: filter by severity
)

for finding in findings:
    print(f"{finding.severity}: {finding.pattern_name}")
    print(f"  Location: {finding.filename}:{finding.line_number}")
    print(f"  Fix: {finding.refactoring_technique}")
```

**Detect by Category:**
```python
# Find all bloater patterns
bloaters = detector.detect_by_category("bloater")

# Find complexity issues
complexity = detector.detect_by_category("complexity")
```

**Detect Critical Only:**
```python
critical = detector.detect_critical()
```

### Code Smell Finding Structure

```python
@dataclass
class CodeSmellFinding:
    finding_id: str
    pattern_id: str
    pattern_name: str
    category: str
    severity: str
    method_id: int
    method_name: str
    filename: str
    line_number: int
    code_snippet: str
    description: str
    symptoms: List[str]
    refactoring_technique: str
    effort_hours: float
    metadata: Dict[str, Any]
```

---

## Impact Analysis

### Analyzing Method Changes

```python
impact = analyzer.analyze(
    method_name="heap_insert",
    filename="backend/access/heap/heapam.c"
)

print(f"Risk Level: {impact.risk_level}")
print(f"Impact Score: {impact.impact_score:.2f}")
print(f"Directly Affected: {len(impact.direct_dependents)} methods")
print(f"Indirectly Affected: {len(impact.indirect_dependents)} methods")
print(f"Files to Test: {len(impact.affected_files)}")
print(f"Estimated Test Effort: {impact.estimated_test_effort}h")
```

### Impact Analysis Structure

```python
@dataclass
class ImpactAnalysis:
    analysis_id: str
    target_method: str
    target_file: str
    direct_dependents: List[str]    # Methods that call target
    indirect_dependents: List[str]  # Transitive callers
    affected_files: List[str]       # Files needing review
    impact_score: float             # 0.0-1.0
    risk_level: str                 # "low", "medium", "high"
    estimated_test_effort: float    # Hours
```

### Dependency Analysis

```python
# Get all dependencies for a method
deps = analyzer.get_dependencies("heap_insert")

for dep in deps:
    print(f"{dep.from_method} -> {dep.to_method}")
    print(f"  Type: {dep.dependency_type}")
    print(f"  Strength: {dep.strength}")
```

---

## Refactoring Planning

### Creating a Refactoring Plan

```python
plan = planner.create_plan(
    findings=findings,
    max_tasks=20,
    priority_threshold=5  # Only include priority >= 5
)

print(f"Total Tasks: {len(plan.tasks)}")
print(f"Total Effort: {plan.total_effort_hours}h")
print(f"Estimated Duration: {plan.estimated_weeks} weeks")

for task in plan.tasks:
    print(f"\nTask {task.task_id}: {task.pattern_name}")
    print(f"  Target: {task.target_file}:{task.target_method}")
    print(f"  Priority: {task.priority}/10")
    print(f"  Effort: {task.effort_hours}h")
    print(f"  Steps:")
    for step in task.refactoring_steps:
        print(f"    - {step}")
```

### Task Prioritization

Tasks are prioritized based on:

1. **Severity Weight** (40%) - Higher severity = higher priority
2. **Impact Score** (30%) - Higher impact = higher priority
3. **Effort Efficiency** (30%) - Value / effort ratio

### Refactoring Task Structure

```python
@dataclass
class RefactoringTask:
    task_id: str
    finding_id: str
    pattern_name: str
    target_method: str
    target_file: str
    priority: int              # 1-10
    effort_hours: float
    impact_score: float
    refactoring_steps: List[str]
    dependencies: List[str]    # Tasks to do first
    estimated_value: float
```

---

## Refactoring Report

### Generating a Full Report

```python
report = planner.generate_report(
    findings=findings,
    include_impact=True,
    format="markdown"
)

# Save report
with open("refactoring_report.md", "w") as f:
    f.write(report.to_markdown())
```

### Report Structure

```python
@dataclass
class RefactoringReport:
    report_id: str
    generated_at: datetime
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    findings_by_category: Dict[str, int]
    tasks: List[RefactoringTask]
    total_effort_hours: float
    estimated_weeks: float
    recommendations: List[str]
```

---

## Supported Patterns

### Bloater Patterns

| Pattern | Detection | Technique |
|---------|-----------|-----------|
| God Method | Lines > 200, Complexity > 20 | Extract Method |
| Long Parameter List | Params > 5 | Introduce Parameter Object |
| Large Class | Methods > 30 | Extract Class |
| Data Clumps | Repeated param groups | Extract Class |

### Complexity Patterns

| Pattern | Detection | Technique |
|---------|-----------|-----------|
| Complex Conditionals | Nested depth > 4 | Decompose Conditional |
| Switch Statements | Switch size > 5 cases | Replace with Polymorphism |
| Feature Envy | High coupling | Move Method |

### Duplicate Patterns

| Pattern | Detection | Technique |
|---------|-----------|-----------|
| Duplicate Code | Similar code blocks | Extract Method |
| Similar Functions | Similar signatures | Extract Superclass |

### Dead Code Patterns

| Pattern | Detection | Technique |
|---------|-----------|-----------|
| Unused Methods | No callers | Remove Method |
| Unused Parameters | Unused in body | Remove Parameter |
| Speculative Generality | Unused abstractions | Remove Abstraction |

---

## SQL Queries for Detection

The module uses SQL queries against the CPG to detect patterns:

**Long Methods:**
```sql
SELECT name, full_name, filename, line_number,
       (line_number_end - line_number) as lines
FROM nodes_method
WHERE (line_number_end - line_number) > 200
  AND is_external = false
ORDER BY lines DESC;
```

**High Complexity:**
```sql
SELECT m.name, m.filename, COUNT(cs.id) as complexity
FROM nodes_method m
JOIN edges_ast a ON m.id = a.src
JOIN nodes_control_structure cs ON a.dst = cs.id
WHERE cs.control_structure_type IN ('IF', 'WHILE', 'FOR', 'SWITCH')
GROUP BY m.id, m.name, m.filename
HAVING COUNT(cs.id) > 15
ORDER BY complexity DESC;
```

**Unused Methods:**
```sql
SELECT m.name, m.full_name, m.filename
FROM nodes_method m
WHERE m.is_external = false
  AND NOT EXISTS (
      SELECT 1 FROM edges_call ec WHERE ec.dst = m.id
  )
  AND m.name NOT LIKE 'test%'
  AND m.name NOT IN ('main', 'init');
```

---

## See Also

- [SQL Query Cookbook](../reference/SQL_QUERY_COOKBOOK.md) - More detection queries
- [CPG Export Guide](./CPG_EXPORT.md) - Prepare CPG for analysis
- [Schema Reference](../reference/SCHEMA.md) - Database schema reference
