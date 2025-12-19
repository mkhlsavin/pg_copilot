# Hypothesis System Reference

This document describes the multi-criteria security hypothesis generation and validation system used for automated vulnerability detection in CodeGraph.

## Overview

The hypothesis system generates testable security hypotheses by combining:
- **CWE vulnerability patterns** (Common Weakness Enumeration)
- **CAPEC attack patterns** (Common Attack Pattern Enumeration)
- **Language-specific patterns** (sinks, sources, sanitizers)
- **Codebase-specific context** (from CPG analysis)

### Pipeline Architecture

```
+-----------------------------------------------------------+
|                  HYPOTHESIS PIPELINE                       |
+-----------------------------------------------------------+

1. GENERATION
   HypothesisGenerator.generate()
   +-- CWE Database (120+ patterns)
   +-- CAPEC Database (50+ attack patterns)
   +-- Language Patterns (C, Python, Java)
   +-- Cartesian Product: CWEs x CAPECs x Patterns
   +-- Template Instantiation
   +-- Output: SecurityHypothesis[]

2. SCORING
   MultiCriteriaScorer.score_batch()
   +-- CWE Frequency Score (0.40 weight)
   +-- Attack Similarity Score (0.30 weight)
   +-- Codebase Exposure Score (0.30 weight)
   +-- Bonuses: Known CVE, Critical Severity
   +-- Output: Priority scores [0.0-1.0]

3. QUERY SYNTHESIS
   QuerySynthesizer.synthesize()
   +-- Match hypothesis to SQL template
   +-- Parameter substitution
   +-- Output: DuckDB SQL/PGQ queries

4. EXECUTION
   HypothesisExecutor.execute()
   +-- Run queries against CPG
   +-- Collect evidence
   +-- Output: Evidence[]

5. VALIDATION
   HypothesisValidator.validate()
   +-- Analyze evidence
   +-- Update hypothesis status
   +-- Calculate metrics
   +-- Output: ValidationResults
```

---

## Core Data Models

### SecurityHypothesis

The central data structure for hypothesis-driven security analysis.

```python
@dataclass
class SecurityHypothesis:
    id: str                          # Unique identifier
    hypothesis_text: str             # Human-readable statement

    # Classification
    cwe_ids: List[str]              # ["CWE-120", "CWE-119"]
    capec_ids: List[str]            # ["CAPEC-100"]
    language: str                   # "C", "Python", etc.
    category: str                   # "buffer_overflow", "injection"

    # Taint patterns
    source_patterns: List[str]      # ["PQgetvalue", "getenv"]
    sink_patterns: List[str]        # ["strcpy", "memcpy"]
    sanitizer_patterns: List[str]   # ["strlcpy", "sizeof"]

    # Scoring
    priority_score: float           # 0.0-1.0, overall priority
    confidence: float               # 0.0-1.0, hypothesis confidence

    # Multi-criteria breakdown
    cwe_frequency_score: float
    attack_similarity_score: float
    codebase_exposure_score: float

    # Generated SQL query
    sql_query: Optional[str]

    # Validation
    evidence: List[Evidence]
    validation_status: ValidationStatus
```

### Evidence

Captures query results supporting or refuting a hypothesis.

```python
@dataclass
class Evidence:
    id: str
    hypothesis_id: str
    query_executed: str             # SQL query that found this
    result_count: int
    findings: List[Dict[str, Any]]  # Query results
    filename: Optional[str]
    line_number: Optional[int]
    code_snippet: Optional[str]
    confidence: float               # 0.0-1.0
```

### ValidationStatus

```python
class ValidationStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"
```

### Severity Levels

```python
class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
```

---

## Hypothesis Generation

### Template Format

Hypotheses follow the pattern:
```
"If [source] flows to [sink] without [sanitizer], then [CWE] enables [attack]"
```

### Category Templates

| Category | Template |
|----------|----------|
| `buffer_overflow` | "If untrusted data from {sources} flows to {sinks} without bounds checking via {sanitizers}, then {cwe} enables {attack} attack, potentially allowing memory corruption or code execution." |
| `sql_injection` | "If user input from {sources} is incorporated into SQL queries via {sinks} without parameterization ({sanitizers}), then {cwe} enables {attack} attack." |
| `command_injection` | "If untrusted data from {sources} flows to command execution via {sinks} without proper escaping ({sanitizers}), then {cwe} enables {attack} attack." |
| `information_disclosure` | "If sensitive data is accessed via {sinks} without authorization checks ({sanitizers}), then {cwe} enables {attack} attack." |

### Generation Algorithm

```python
from src.security.hypothesis import HypothesisGenerator

generator = HypothesisGenerator()

# Generate for specific CWE
hypotheses = generator.generate(
    language="C",
    cwe_filter=["CWE-120", "CWE-78"],
    max_hypotheses=50
)

# Generate for category
buffer_hypotheses = generator.generate_by_category("buffer_overflow")

# Full enumeration
all_hypotheses = generator.generate_all(language="C")
```

### CWE Category Mapping

| CWE | Category |
|-----|----------|
| CWE-120, CWE-119, CWE-787, CWE-125 | `buffer_overflow` |
| CWE-78, CWE-77, CWE-88 | `command_injection` |
| CWE-89 | `sql_injection` |
| CWE-94, CWE-95 | `code_injection` |
| CWE-134 | `format_string` |
| CWE-200, CWE-209, CWE-862 | `information_disclosure` |
| CWE-416 | `use_after_free` |
| CWE-190, CWE-191 | `integer_overflow` |

---

## Multi-Criteria Scoring

### Scoring Formula

```
Priority Score = (CWE_Frequency × 0.40)
               + (Attack_Similarity × 0.30)
               + (Codebase_Exposure × 0.30)
```

### Score Components

| Component | Weight | Description |
|-----------|--------|-------------|
| CWE Frequency | 0.40 | How common is this CWE in CVE database |
| Attack Similarity | 0.30 | How similar to known attack patterns |
| Codebase Exposure | 0.30 | How exposed is the codebase |

### Bonus Multipliers

| Bonus | Multiplier | Condition |
|-------|------------|-----------|
| Known CVE | 1.20 (+20%) | Matches known CVE pattern |
| Critical Severity | 1.10 (+10%) | Critical severity CWE |
| Recent Exploit | 1.15 (+15%) | Recently exploited in wild |

### Usage

```python
from src.security.hypothesis import MultiCriteriaScorer, CodebaseStats

# Gather codebase statistics
stats = CodebaseStats(
    total_methods=52000,
    total_calls=110000,
    sink_counts={"strcpy": 150, "memcpy": 800},
    source_counts={"getenv": 50, "recv": 30}
)

# Score hypotheses
scorer = MultiCriteriaScorer(weights={
    'cwe_frequency': 0.40,
    'attack_similarity': 0.30,
    'codebase_exposure': 0.30
})

scored_hypotheses = scorer.score_batch(hypotheses, stats)

# Get top priority
top_10 = sorted(scored_hypotheses, key=lambda h: h.priority_score, reverse=True)[:10]
```

---

## Query Synthesis

### SQL Templates

The system generates DuckDB SQL queries for each hypothesis category:

```python
from src.security.hypothesis import QuerySynthesizer

synthesizer = QuerySynthesizer()
query = synthesizer.synthesize_query(hypothesis)
```

### Template Examples

**Buffer Overflow Detection:**
```sql
SELECT DISTINCT nc.id, nc.name AS sink_function, nc.code,
       nc.filename, nc.line_number
FROM nodes_call nc
WHERE nc.name IN ('strcpy', 'strcat', 'sprintf', 'memcpy')
LIMIT 100;
```

**Command Injection Detection:**
```sql
SELECT DISTINCT nc.id, nc.name AS sink_function, nc.code,
       nc.filename, nc.line_number
FROM nodes_call nc
WHERE nc.name IN ('system', 'popen', 'execl', 'execv')
LIMIT 100;
```

**Data Flow with SQL/PGQ:**
```sql
FROM GRAPH_TABLE(cpg
    MATCH (src:IDENTIFIER)-[:REACHING_DEF*1..5]->(sink:CALL_NODE)
    WHERE src.name IN ('user_input', 'request')
      AND sink.name IN ('execute', 'query')
    COLUMNS (
        src.name AS source_var,
        sink.name AS sink_function,
        sink.filename,
        sink.line_number
    )
)
LIMIT 100;
```

---

## Hypothesis Execution

### Executor Usage

```python
from src.security.hypothesis import HypothesisExecutor
import duckdb

conn = duckdb.connect("cpg.duckdb")
executor = HypothesisExecutor(conn)

# Execute single hypothesis
evidence = executor.execute(hypothesis)

# Execute batch
results = executor.execute_batch(hypotheses, parallel=True)
```

### Evidence Collection

For each executed query:
1. Execute SQL against CPG
2. Capture result count and findings
3. Extract filename, line number, code snippet
4. Calculate evidence confidence
5. Associate evidence with hypothesis

---

## Validation

### Validation Process

```python
from src.security.hypothesis import HypothesisValidator

validator = HypothesisValidator()

# Validate single hypothesis
validator.validate(hypothesis)

# Validate batch
results = validator.validate_batch(hypotheses)
```

### Validation Results

```python
@dataclass
class ValidationResults:
    batch_id: str
    total_hypotheses: int
    executed_queries: int

    # CVE Detection metrics
    cves_found: List[str]
    cves_missed: List[str]

    # Precision/Recall
    true_positives: int
    false_positives: int
    false_negatives: int

    # Hypothesis quality
    confirmed_hypotheses: int
    rejected_hypotheses: int
    inconclusive_hypotheses: int

    # Computed metrics
    @property
    def detection_rate(self) -> float: ...
    @property
    def precision(self) -> float: ...
    @property
    def recall(self) -> float: ...
    @property
    def f1_score(self) -> float: ...
```

---

## Knowledge Base

### CWE Database

```python
from src.security.hypothesis import get_knowledge_base

kb = get_knowledge_base()

# Get CWE entry
cwe = kb.get_cwe("CWE-120")
print(f"Name: {cwe.name}")
print(f"Severity: {cwe.severity}")
print(f"CVSS: {cwe.cvss_base}")

# Get by category
memory_cwes = kb.get_cwes_by_category("memory")

# Get related CAPECs
capecs = kb.get_capecs_for_cwe("CWE-120")
```

### Language Patterns

```python
# Get C patterns
c_patterns = kb.get_language_patterns("C")

for pattern in c_patterns:
    print(f"Category: {pattern.category}")
    print(f"Sinks: {pattern.sinks}")
    print(f"Sources: {pattern.sources}")
    print(f"Sanitizers: {pattern.sanitizers}")
```

### Supported CWEs (Partial List)

| CWE ID | Name | Severity | CVSS |
|--------|------|----------|------|
| CWE-120 | Buffer Copy without Checking Size | HIGH | 8.0 |
| CWE-119 | Improper Restriction of Operations | HIGH | 8.0 |
| CWE-78 | OS Command Injection | CRITICAL | 9.8 |
| CWE-89 | SQL Injection | CRITICAL | 9.8 |
| CWE-200 | Exposure of Sensitive Information | MEDIUM | 5.3 |
| CWE-416 | Use After Free | HIGH | 8.1 |
| CWE-190 | Integer Overflow | HIGH | 7.5 |

---

## Python API

### Complete Example

```python
from src.security.hypothesis import (
    HypothesisGenerator,
    MultiCriteriaScorer,
    QuerySynthesizer,
    HypothesisExecutor,
    HypothesisValidator,
    CodebaseStats
)
import duckdb

# 1. Connect to CPG
conn = duckdb.connect("cpg.duckdb")

# 2. Gather codebase statistics
stats = CodebaseStats(
    total_methods=conn.execute("SELECT COUNT(*) FROM nodes_method").fetchone()[0],
    total_calls=conn.execute("SELECT COUNT(*) FROM nodes_call").fetchone()[0]
)

# 3. Generate hypotheses
generator = HypothesisGenerator()
hypotheses = generator.generate(language="C", max_hypotheses=100)

# 4. Score and prioritize
scorer = MultiCriteriaScorer()
scored = scorer.score_batch(hypotheses, stats)

# 5. Synthesize SQL queries
synthesizer = QuerySynthesizer()
for h in scored:
    h.sql_query = synthesizer.synthesize_query(h)

# 6. Execute against CPG
executor = HypothesisExecutor(conn)
for h in scored[:20]:  # Top 20
    evidence = executor.execute(h)
    h.evidence.extend(evidence)

# 7. Validate and report
validator = HypothesisValidator()
results = validator.validate_batch(scored)

print(f"Detection Rate: {results.detection_rate:.1%}")
print(f"Precision: {results.precision:.1%}")
print(f"Recall: {results.recall:.1%}")
print(f"F1 Score: {results.f1_score:.2f}")
```

---

## Performance

### Benchmark Results

| Metric | Value |
|--------|-------|
| CVE Detection Rate | 100% (3/3 target CVEs) |
| Hypothesis Confirmation Rate | 55% |
| Average Query Time | 2-3ms |
| Generation Time (100 hypotheses) | <1s |
| Execution Time (20 hypotheses) | <30s |

### Validated CVEs (PostgreSQL 17)

| CVE | Type | Detection Method |
|-----|------|------------------|
| CVE-2025-8713 | Statistics Disclosure | Hypothesis + Method |
| CVE-2025-8714 | pg_dump Injection | Method-based |
| CVE-2025-8715 | Newline Injection | Method-based |

---

## See Also

- [CPG Export Guide](../guides/CPG_EXPORT.md) - Export CPG for analysis
- [SQL Query Cookbook](./SQL_QUERY_COOKBOOK.md) - Query examples
- [CPGQL to SQL](./CPGQL_TO_SQL.md) - Query translation
- [CWE Database](https://cwe.mitre.org/)
- [CAPEC Database](https://capec.mitre.org/)
