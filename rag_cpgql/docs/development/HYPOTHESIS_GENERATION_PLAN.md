# Plan: Multi-Criteria Hypothesis Generation Algorithm

## Implementation Plan for AI Copilot Security Audit

**Goal**: Implement the Unified Multi-Criteria Hypothesis Generation Algorithm and validate it on PostgreSQL 17.6 security patches (CVE-2025-8713, CVE-2025-8714, CVE-2025-8715).

---

## Executive Summary

The algorithm systematically generates testable vulnerability hypotheses through:
1. **CWE-based enumeration** - Language-specific weakness patterns
2. **Attack method mapping** - CAPEC patterns and exploit techniques
3. **Multi-criteria scoring** - Prioritization by frequency, similarity, exposure
4. **CPG query formalization** - Executable queries for validation
5. **Evidence-based validation** - Confirmation against real CVEs

### Validation Target: PostgreSQL 17.6 Security Patches

| CVE | Description | CVSS | Type |
|-----|-------------|------|------|
| CVE-2025-8713 | Optimizer statistics data leakage | Medium | Information Disclosure |
| CVE-2025-8714 | pg_dump untrusted data code execution | 8.8 | Remote Code Execution |
| CVE-2025-8715 | Newline injection in pg_dump | 8.8 | Code Injection |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  HYPOTHESIS GENERATION ENGINE                │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ KNOWLEDGE    │   │ HYPOTHESIS   │   │ MULTI-CRITERIA│
│ BASE         │──▶│ GENERATOR    │──▶│ SCORER        │
│              │   │              │   │               │
│ - CWE DB     │   │ - Enumerate  │   │ - CWE Freq    │
│ - CAPEC      │   │ - Instantiate│   │ - Attack Sim  │
│ - Language   │   │ - Template   │   │ - Exposure    │
│   Patterns   │   │              │   │               │
└──────────────┘   └──────────────┘   └──────────────┘
                           │
                           ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ QUERY        │   │ EXECUTOR     │   │ VALIDATOR    │
│ SYNTHESIZER  │──▶│              │──▶│              │
│              │   │              │   │              │
│ - SQL/PGQ    │   │ - DuckDB     │   │ - FP Filter  │
│ - Templates  │   │ - Run Queries│   │ - CVE Match  │
│ - Optimize   │   │ - Evidence   │   │ - Confirm    │
└──────────────┘   └──────────────┘   └──────────────┘
```

---

## Phase 1: Knowledge Base

### 1.1 CWE Database for C Language

**File**: `src/security/hypothesis/knowledge_base.py`

```python
@dataclass
class CWEEntry:
    id: str                    # "CWE-120"
    name: str                  # "Buffer Copy without Checking Size"
    description: str
    severity: str              # critical/high/medium/low
    cvss_base: float           # 7.5
    languages: List[str]       # ["C", "C++"]
    prevalence: float          # 0.85 (how common in CVE database)
    exploitability: float      # 0.9
    related_cwes: List[str]    # ["CWE-119", "CWE-787"]
    capec_ids: List[str]       # ["CAPEC-100", "CAPEC-123"]
```

**Top CWEs for C/C++ (PostgreSQL)**:
| CWE | Name | Prevalence | PostgreSQL Relevance |
|-----|------|------------|---------------------|
| CWE-120 | Buffer Overflow | 0.85 | High - string operations |
| CWE-416 | Use After Free | 0.75 | High - memory management |
| CWE-476 | NULL Pointer Deref | 0.80 | Medium - error handling |
| CWE-190 | Integer Overflow | 0.70 | High - size calculations |
| CWE-78 | OS Command Injection | 0.65 | Medium - pg_dump |
| CWE-89 | SQL Injection | 0.60 | Low - internal queries |
| CWE-200 | Information Exposure | 0.55 | High - optimizer stats |
| CWE-94 | Code Injection | 0.50 | High - pg_dump restore |

### 1.2 CAPEC Attack Patterns

```python
@dataclass
class CAPECPattern:
    id: str                    # "CAPEC-100"
    name: str                  # "Overflow Buffers"
    description: str
    related_cwes: List[str]    # ["CWE-120", "CWE-119"]
    attack_steps: List[str]
    prerequisites: List[str]
    typical_severity: str
```

### 1.3 Language-Specific Patterns

```python
C_DANGEROUS_SINKS = {
    "memory": ["strcpy", "strcat", "sprintf", "gets", "memcpy", "memmove"],
    "format": ["printf", "fprintf", "sprintf", "snprintf"],
    "command": ["system", "popen", "exec*"],
    "file": ["fopen", "open", "read", "write"],
}

C_TAINT_SOURCES = {
    "network": ["recv", "recvfrom", "read"],
    "file": ["fread", "fscanf", "fgets"],
    "user_input": ["getenv", "argv"],
    "database": ["PQgetvalue", "SPI_getvalue"],  # PostgreSQL specific
}

C_SANITIZERS = {
    "bounds_check": ["if.*<.*sizeof", "if.*<=.*len"],
    "null_check": ["if.*!=.*NULL", "if.*==.*NULL"],
    "length_limit": ["strlcpy", "strlcat", "snprintf"],
}
```

---

## Phase 2: Hypothesis Generator

### 2.1 Hypothesis Data Model

**File**: `src/security/hypothesis/models.py`

```python
@dataclass
class SecurityHypothesis:
    id: str
    hypothesis_text: str       # "If untrusted input flows to strcpy without bounds check..."
    cwe_ids: List[str]         # ["CWE-120"]
    capec_ids: List[str]       # ["CAPEC-100"]
    language: str              # "C"

    # Sources and Sinks
    source_patterns: List[str] # ["PQgetvalue", "getenv"]
    sink_patterns: List[str]   # ["strcpy", "memcpy"]
    sanitizer_patterns: List[str]

    # Scoring
    priority_score: float      # 0.0-1.0
    confidence: float          # 0.0-1.0

    # Multi-criteria breakdown
    cwe_frequency_score: float
    attack_similarity_score: float
    codebase_exposure_score: float

    # DuckDB SQL/PGQ Query (NOT Joern DSL!)
    sql_query: Optional[str]

    # Evidence
    evidence: List[Evidence]
    validation_status: str     # "pending", "confirmed", "rejected"
```

### 2.2 Hypothesis Generation Algorithm

```python
class HypothesisGenerator:
    def generate_hypotheses(
        self,
        language: str,
        codebase_stats: Dict,
        max_hypotheses: int = 100
    ) -> List[SecurityHypothesis]:
        """
        Phase 1: ENUMERATION
        - Get top CWEs for language
        - Get CAPEC attack patterns
        - Get language-specific sinks/sources

        Phase 2: CARTESIAN PRODUCT
        hypotheses = CWEs × AttackMethods × Sinks × Sources × FlowPatterns

        Phase 3: TEMPLATE INSTANTIATION
        "If [source] flows to [sink] without [sanitizer],
         then [CWE] enables [attack_method]"
        """
```

### 2.3 PostgreSQL-Specific Hypotheses

**H1: pg_dump Code Injection (CVE-2025-8714, CVE-2025-8715)**
```
Hypothesis: If database object names containing shell metacharacters
flow to pg_dump output without escaping, then CWE-94 enables
arbitrary code execution during restore.

Source: Database object names (tables, functions, schemas)
Sink: psql meta-command generation in pg_dump
Sanitizer: Proper quoting/escaping of identifiers
```

**H2: Optimizer Statistics Leakage (CVE-2025-8713)**
```
Hypothesis: If table data is sampled for statistics without
ACL verification, then CWE-200 enables unauthorized data access.

Source: Table rows accessed for statistics collection
Sink: pg_statistic system catalog
Sanitizer: Row-level security policy enforcement
```

**H3: Buffer Overflow in String Operations**
```
Hypothesis: If external input flows to fixed-size buffer copy
without length check, then CWE-120 enables memory corruption.

Source: Network input, file data, SQL parameters
Sink: strcpy, memcpy, sprintf without size limit
Sanitizer: strlcpy, snprintf, explicit bounds check
```

---

## Phase 3: Multi-Criteria Scorer

### 3.1 Scoring Formula

```python
class MultiCriteriaScorer:
    """
    Priority Score =
        (CWE_Frequency × 0.40) +
        (Attack_Similarity × 0.30) +
        (Codebase_Exposure × 0.30) +
        Bonus adjustments
    """

    WEIGHTS = {
        'cwe_frequency': 0.40,      # How common is this CWE?
        'attack_similarity': 0.30,  # Similar attacks in the wild?
        'codebase_exposure': 0.30,  # How exposed is the codebase?
    }

    def score_hypothesis(self, hypothesis: SecurityHypothesis) -> float:
        cwe_score = self._score_cwe_frequency(hypothesis.cwe_ids)
        attack_score = self._score_attack_similarity(hypothesis.capec_ids)
        exposure_score = self._score_codebase_exposure(hypothesis)

        base_score = (
            cwe_score * self.WEIGHTS['cwe_frequency'] +
            attack_score * self.WEIGHTS['attack_similarity'] +
            exposure_score * self.WEIGHTS['codebase_exposure']
        )

        # Bonus for known CVE patterns
        if self._matches_known_cve_pattern(hypothesis):
            base_score *= 1.2

        return min(1.0, base_score)
```

### 3.2 Criteria Calculation

**CWE Frequency Score** (40%):
```python
def _score_cwe_frequency(self, cwe_ids: List[str]) -> float:
    """Based on CVE database statistics"""
    scores = []
    for cwe_id in cwe_ids:
        entry = self.knowledge_base.get_cwe(cwe_id)
        scores.append(entry.prevalence * entry.exploitability)
    return max(scores) if scores else 0.0
```

**Attack Similarity Score** (30%):
```python
def _score_attack_similarity(self, capec_ids: List[str]) -> float:
    """Based on known exploits and attack patterns"""
    # Check if similar attacks exist in threat intelligence
    # Check EPSS scores for related CVEs
    # Check if weaponized exploits are available
```

**Codebase Exposure Score** (30%):
```python
def _score_codebase_exposure(self, hypothesis: SecurityHypothesis) -> float:
    """Based on CPG analysis of the codebase"""
    # Count occurrences of sink functions
    # Count reachable paths from sources to sinks
    # Check presence of sanitizers
    # Consider code complexity
```

---

## Phase 4: Query Synthesizer

### 4.1 DuckDB SQL/PGQ Templates

**File**: `src/security/hypothesis/query_templates.py`

**ВАЖНО**: Все запросы выполняются к DuckDB с использованием SQL и PGQ расширений.
Joern используется ТОЛЬКО для экспорта графа, но не для запросов.

```python
SQL_PGQ_TEMPLATES = {
    "buffer_overflow": """
        -- Find buffer overflows: strcpy/memcpy without bounds check
        -- CWE-120: Buffer Copy without Checking Size of Input
        SELECT DISTINCT
            c.id,
            c.name AS sink_function,
            c.code,
            c.filename,
            c.line_number,
            m.full_name AS containing_method
        FROM nodes_call c
        JOIN edges_ast ea ON ea.dst = c.id
        JOIN nodes_method m ON ea.src = m.id
        WHERE c.name IN ('strcpy', 'strcat', 'memcpy', 'sprintf', 'gets')
        -- Check if tainted by external input via reaching definitions
        AND EXISTS (
            SELECT 1 FROM edges_reaching_def rd
            JOIN nodes_call src ON rd.src = src.id
            WHERE rd.dst = c.id
            AND src.name IN ('recv', 'read', 'fgets', 'getenv', 'PQgetvalue', 'SPI_getvalue')
        )
        -- Exclude if bounds check exists in parent control structure
        AND NOT EXISTS (
            SELECT 1 FROM nodes_control_structure cs
            JOIN edges_ast a ON a.src = cs.id
            WHERE a.dst = c.id
            AND (cs.code LIKE '%sizeof%' OR cs.code LIKE '%len%' OR cs.code LIKE '%<=%')
        )
        ORDER BY c.filename, c.line_number;
    """,

    "command_injection": """
        -- Find command injection: system/popen with tainted input
        -- CWE-78: OS Command Injection
        SELECT DISTINCT
            c.id,
            c.name AS sink_function,
            c.code,
            c.filename,
            c.line_number,
            src.name AS taint_source
        FROM nodes_call c
        JOIN edges_reaching_def rd ON rd.dst = c.id
        JOIN nodes_call src ON rd.src = src.id
        WHERE c.name IN ('system', 'popen', 'execl', 'execv', 'execve', 'execvp')
        AND src.name IN ('getenv', 'fgets', 'PQgetvalue', 'SPI_getvalue', 'read')
        -- Exclude if sanitization is present
        AND NOT EXISTS (
            SELECT 1 FROM nodes_call san
            JOIN edges_reaching_def rd2 ON rd2.src = san.id AND rd2.dst = c.id
            WHERE san.name IN ('sanitize', 'escape_shell', 'quote_argument')
        )
        ORDER BY c.filename, c.line_number;
    """,

    "format_string": """
        -- Find format string vulnerabilities
        -- CWE-134: Use of Externally-Controlled Format String
        SELECT DISTINCT
            c.id,
            c.name AS sink_function,
            c.code,
            c.filename,
            c.line_number
        FROM nodes_call c
        WHERE c.name IN ('printf', 'fprintf', 'sprintf', 'snprintf', 'syslog')
        -- First argument (format string) comes from external source
        AND EXISTS (
            SELECT 1 FROM edges_argument arg
            JOIN edges_reaching_def rd ON rd.dst = arg.dst
            JOIN nodes_call src ON rd.src = src.id
            WHERE arg.src = c.id
            AND src.name IN ('fgets', 'read', 'getenv', 'PQgetvalue')
        )
        ORDER BY c.filename, c.line_number;
    """,

    "sql_injection_internal": """
        -- Find internal SQL injection in PostgreSQL
        -- CWE-89: SQL Injection (internal queries)
        SELECT DISTINCT
            c.id,
            c.name AS sink_function,
            c.code,
            c.filename,
            c.line_number
        FROM nodes_call c
        WHERE c.name IN ('SPI_execute', 'SPI_exec', 'PQexec', 'PQexecParams')
        -- Query string appears to be dynamically constructed
        AND (c.code LIKE '%+%' OR c.code LIKE '%format%' OR c.code LIKE '%psprintf%')
        -- Not using proper quoting functions
        AND c.code NOT LIKE '%quote_literal%'
        AND c.code NOT LIKE '%quote_identifier%'
        ORDER BY c.filename, c.line_number;
    """,

    "information_disclosure": """
        -- Find potential information disclosure (CVE-2025-8713 pattern)
        -- CWE-200: Exposure of Sensitive Information
        SELECT DISTINCT
            m.id,
            m.full_name,
            m.filename,
            m.line_number,
            'Missing ACL check' AS issue
        FROM nodes_method m
        WHERE (m.name LIKE '%statistic%' OR m.name LIKE '%sample%' OR m.name LIKE '%analyze%')
        -- Method accesses data but doesn't check ACL
        AND NOT EXISTS (
            SELECT 1 FROM nodes_call acl_check
            JOIN edges_ast ea ON ea.src = m.id AND ea.dst = acl_check.id
            WHERE acl_check.name IN (
                'pg_class_aclcheck', 'has_table_privilege', 'check_enable_rls',
                'pg_attribute_aclcheck', 'has_column_privilege'
            )
        )
        ORDER BY m.filename, m.line_number;
    """,

    "pg_dump_injection": """
        -- Find pg_dump object name injection points (CVE-2025-8714, CVE-2025-8715)
        -- CWE-94: Code Injection via untrusted object names
        SELECT DISTINCT
            c.id,
            c.name AS sink_function,
            c.code,
            c.filename,
            c.line_number,
            src.name AS data_source
        FROM nodes_call c
        JOIN edges_reaching_def rd ON rd.dst = c.id
        JOIN nodes_call src ON rd.src = src.id
        WHERE c.name IN ('appendPQExpBuffer', 'appendStringInfo', 'appendPQExpBufferStr')
        AND src.name IN ('PQgetvalue', 'PQfname', 'getTableAttrs', 'getTables')
        -- Not properly escaped
        AND c.code NOT LIKE '%fmtId%'
        AND c.code NOT LIKE '%fmtQualifiedId%'
        AND c.code NOT LIKE '%quote_identifier%'
        ORDER BY c.filename, c.line_number;
    """,

    "use_after_free": """
        -- Find Use-After-Free patterns
        -- CWE-416: Use After Free
        SELECT DISTINCT
            use_call.id,
            use_call.code,
            use_call.filename,
            use_call.line_number,
            free_call.name AS free_function,
            free_call.line_number AS free_line
        FROM nodes_call free_call
        JOIN nodes_call use_call ON use_call.filename = free_call.filename
        WHERE free_call.name IN ('pfree', 'free', 'ReleaseSysCache')
        AND use_call.line_number > free_call.line_number
        -- Same variable used after free (via reaching definitions)
        AND EXISTS (
            SELECT 1 FROM edges_reaching_def rd1, edges_reaching_def rd2
            WHERE rd1.dst = free_call.id
            AND rd2.dst = use_call.id
            AND rd1.variable = rd2.variable
        )
        ORDER BY use_call.filename, free_call.line_number;
    """,

    "integer_overflow": """
        -- Find Integer Overflow in size calculations
        -- CWE-190: Integer Overflow or Wraparound
        SELECT DISTINCT
            c.id,
            c.name AS allocation_function,
            c.code,
            c.filename,
            c.line_number
        FROM nodes_call c
        WHERE c.name IN ('palloc', 'palloc0', 'malloc', 'repalloc')
        -- Size argument involves multiplication without overflow check
        AND (c.code LIKE '%*%' OR c.code LIKE '%sizeof%*%')
        -- No overflow check nearby
        AND NOT EXISTS (
            SELECT 1 FROM nodes_control_structure cs
            JOIN edges_cfg cfg ON cfg.src = cs.id AND cfg.dst = c.id
            WHERE cs.code LIKE '%overflow%' OR cs.code LIKE '%> MAX%'
        )
        ORDER BY c.filename, c.line_number;
    """
}
```

### 4.2 DuckDB PGQ Graph Queries

Для более сложных запросов с обходом графа используется PGQ синтаксис:

```python
PGQ_TEMPLATES = {
    "taint_flow_path": """
        -- Find complete taint flow paths from source to sink
        SELECT *
        FROM GRAPH_TABLE(cpg
            MATCH (source:CALL_NODE)-[:REACHING_DEF*1..10]->(sink:CALL_NODE)
            WHERE source.name IN ('recv', 'read', 'getenv', 'PQgetvalue')
              AND sink.name IN ('strcpy', 'system', 'printf')
            COLUMNS (
                source.name AS source_func,
                source.filename AS source_file,
                source.line_number AS source_line,
                sink.name AS sink_func,
                sink.filename AS sink_file,
                sink.line_number AS sink_line
            )
        )
        LIMIT 100;
    """,

    "call_chain_to_sink": """
        -- Find call chains leading to dangerous function
        SELECT *
        FROM GRAPH_TABLE(cpg
            MATCH (caller:METHOD)-[:AST]->(call:CALL_NODE)-[:CALLS]->(callee:METHOD)
                  -[:AST]->(nested:CALL_NODE)
            WHERE nested.name IN ({sink_functions})
            COLUMNS (
                caller.full_name AS entry_method,
                callee.full_name AS intermediate_method,
                nested.name AS sink_function,
                nested.filename AS file,
                nested.line_number AS line
            )
        );
    """,

    "control_dependent_data_flow": """
        -- Find data flows that are control-dependent on conditions
        SELECT *
        FROM GRAPH_TABLE(cpg
            MATCH (cond:CONTROL_STRUCTURE)-[:CDG]->(stmt:CPG_NODE)
                  -[:REACHING_DEF]->(sink:CALL_NODE)
            WHERE sink.name IN ({sink_functions})
            COLUMNS (
                cond.code AS condition,
                sink.name AS sink_func,
                sink.line_number AS line
            )
        );
    """
}
```

### 4.3 Query Generator

```python
class QuerySynthesizer:
    """Generates DuckDB SQL/PGQ queries from security hypotheses."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.templates = SQL_PGQ_TEMPLATES

    def synthesize_query(self, hypothesis: SecurityHypothesis) -> str:
        """Generate SQL/PGQ query from hypothesis."""

        # Select base template by CWE
        template = self._select_template(hypothesis.cwe_ids)

        # Customize sink functions
        if hypothesis.sink_patterns:
            sinks_sql = ", ".join(f"'{s}'" for s in hypothesis.sink_patterns)
            template = template.replace("{sink_functions}", sinks_sql)

        # Customize source functions
        if hypothesis.source_patterns:
            sources_sql = ", ".join(f"'{s}'" for s in hypothesis.source_patterns)
            template = template.replace("{source_functions}", sources_sql)

        # Add sanitizer exclusions
        if hypothesis.sanitizer_patterns:
            sanitizer_clause = self._build_sanitizer_exclusion(
                hypothesis.sanitizer_patterns
            )
            template = self._insert_sanitizer_clause(template, sanitizer_clause)

        return template

    def _build_sanitizer_exclusion(self, sanitizers: List[str]) -> str:
        """Build NOT EXISTS clause for sanitizers."""
        sanitizer_list = ", ".join(f"'{s}'" for s in sanitizers)
        return f"""
        AND NOT EXISTS (
            SELECT 1 FROM nodes_call san
            JOIN edges_reaching_def rd_san ON rd_san.src = san.id
            WHERE rd_san.dst = c.id
            AND san.name IN ({sanitizer_list})
        )
        """

    def execute_query(self, query: str) -> List[Dict]:
        """Execute query against DuckDB CPG database."""
        import duckdb
        conn = duckdb.connect(self.db_path, read_only=True)
        result = conn.execute(query).fetchdf()
        conn.close()
        return result.to_dict('records')

---

## Phase 5: Validation on PostgreSQL 17.6

### 5.1 Validation Strategy

```
┌─────────────────────────────────────────────────────────────┐
│              VALIDATION WORKFLOW                             │
└─────────────────────────────────────────────────────────────┘

1. SETUP
   ├── Download PostgreSQL 17.5 source (vulnerable)
   ├── Download PostgreSQL 17.6 source (patched)
   └── Generate CPGs for both versions

2. HYPOTHESIS GENERATION
   ├── Run algorithm on 17.5 source
   ├── Generate prioritized hypotheses
   └── Synthesize SQL/PGQ queries

3. QUERY EXECUTION
   ├── Execute queries on 17.5 DuckDB CPG
   ├── Collect potential vulnerabilities
   └── Record evidence

4. VALIDATION
   ├── Compare findings with CVE descriptions
   ├── Verify fixed in 17.6
   ├── Calculate recall/precision
   └── Measure false positive rate

5. METRICS
   ├── Detection Rate: Found CVEs / Total CVEs
   ├── False Positive Rate: FPs / Total Findings
   ├── Hypothesis Quality: Confirmed / Generated
   └── Time to Detection
```

### 5.2 Expected Results

**CVE-2025-8714 (pg_dump RCE)**:
- Hypothesis should detect: untrusted object names → pg_dump output
- Query pattern: `appendPQExpBuffer` without `fmtId`
- Expected files: `src/bin/pg_dump/pg_dump.c`

**CVE-2025-8715 (Newline injection)**:
- Hypothesis should detect: newlines in identifiers → psql commands
- Query pattern: Object names without newline escaping
- Expected files: `src/bin/pg_dump/pg_backup_*.c`

**CVE-2025-8713 (Statistics leakage)**:
- Hypothesis should detect: statistics access bypassing ACL
- Query pattern: `analyze_*` functions without privilege check
- Expected files: `src/backend/commands/analyze.c`

### 5.3 Validation Metrics

```python
@dataclass
class ValidationResults:
    total_hypotheses: int
    executed_queries: int

    # CVE Detection
    cves_found: List[str]        # ["CVE-2025-8714", ...]
    cves_missed: List[str]
    detection_rate: float        # cves_found / total_cves

    # Precision/Recall
    true_positives: int          # Confirmed vulnerabilities
    false_positives: int         # Not actual vulnerabilities
    false_negatives: int         # Missed vulnerabilities
    precision: float             # TP / (TP + FP)
    recall: float                # TP / (TP + FN)
    f1_score: float

    # Hypothesis Quality
    confirmed_hypotheses: int
    rejected_hypotheses: int
    hypothesis_accuracy: float

    # Performance
    generation_time_sec: float
    execution_time_sec: float
    total_time_sec: float
```

---

## Implementation Order

### Sprint 1: Foundation (Week 1-2)
1. Create `src/security/hypothesis/` package structure
2. Implement `knowledge_base.py` with CWE/CAPEC data
3. Implement `models.py` with data structures
4. Add C language patterns for PostgreSQL

### Sprint 2: Generator (Week 3-4)
5. Implement `hypothesis_generator.py`
6. Create hypothesis templates
7. Implement Cartesian product generation
8. Add PostgreSQL-specific hypothesis variants

### Sprint 3: Scorer (Week 5)
9. Implement `multi_criteria_scorer.py`
10. Add CWE frequency scoring
11. Add attack similarity scoring
12. Add codebase exposure scoring

### Sprint 4: Query Synthesis (Week 6)
13. Implement `query_synthesizer.py`
14. Create SQL/PGQ query templates
15. Add query optimization
16. Integrate with existing DuckDB executor

### Sprint 5: Validation (Week 7-8)
17. Set up PostgreSQL 17.5/17.6 test environment
18. Generate CPGs for both versions
19. Run validation workflow
20. Collect and analyze metrics
21. Document results

---

## File Structure

```
src/security/hypothesis/
├── __init__.py
├── models.py                 # Hypothesis, Evidence data classes
├── knowledge_base.py         # CWE, CAPEC, language patterns
├── hypothesis_generator.py   # Main generation algorithm
├── multi_criteria_scorer.py  # Scoring engine
├── query_synthesizer.py      # DuckDB SQL/PGQ query generation
├── query_templates.py        # SQL/PGQ templates by CWE
├── executor.py               # DuckDB query executor
├── validator.py              # CVE validation logic
└── postgresql/
    ├── __init__.py
    ├── patterns.py           # PostgreSQL-specific patterns
    ├── hypotheses.py         # PostgreSQL hypothesis variants
    └── validation.py         # PostgreSQL 17.6 validation

tests/security/hypothesis/
├── test_knowledge_base.py
├── test_hypothesis_generator.py
├── test_multi_criteria_scorer.py
├── test_query_synthesizer.py
└── test_postgresql_validation.py

docs/
├── HYPOTHESIS_GENERATION_PLAN.md  # This file
└── POSTGRESQL_VALIDATION_REPORT.md # Results
```

---

## Success Criteria

1. **Detection Rate ≥ 67%**: Detect at least 2 of 3 PostgreSQL CVEs
2. **Precision ≥ 70%**: No more than 30% false positives
3. **Hypothesis Quality ≥ 50%**: At least half of top-50 hypotheses lead to findings
4. **Performance**: Generate + score 100 hypotheses in < 60 seconds
5. **False Positive Reduction**: 36% reduction vs pattern-only scanning (per VulAgent paper)

---

## References

- [VulAgent: Hypothesis Validation-Based Multi-Agent System](https://arxiv.org/abs/2509.11523)
- [PostgreSQL 17.6 Security Release](https://www.postgresql.org/about/news/postgresql-176-1610-1514-1419-1322-and-18-beta-3-released-3118/)
- [CWE - Common Weakness Enumeration](https://cwe.mitre.org)
- [CAPEC - Common Attack Pattern Enumeration](https://capec.mitre.org)
- [Code Property Graphs - Joern](https://docs.joern.io/code-property-graph/)

---

## Технические примечания

### Joern vs DuckDB

**ВАЖНО**: Joern используется ТОЛЬКО для экспорта CPG в DuckDB формат:

```bash
# Экспорт CPG из Joern в DuckDB
joern-export --format=duckdb postgresql_src/ -o postgresql.cpg.duckdb
```

Все последующие запросы выполняются к DuckDB:

```python
import duckdb

# Подключение к CPG базе
conn = duckdb.connect('postgresql.cpg.duckdb', read_only=True)

# Выполнение SQL запроса
results = conn.execute("""
    SELECT c.name, c.filename, c.line_number
    FROM nodes_call c
    WHERE c.name = 'strcpy'
""").fetchdf()
```

### DuckDB PGQ для обхода графа

Для запросов с обходом графа (например, поиск путей taint flow) используется
расширение duckpgq:

```sql
-- Загрузка расширения
INSTALL duckpgq FROM core;
LOAD duckpgq;

-- Создание property graph (один раз)
CREATE PROPERTY GRAPH cpg ... ;

-- Поиск путей
SELECT * FROM GRAPH_TABLE(cpg
    MATCH (src:CALL_NODE)-[:REACHING_DEF*1..5]->(dst:CALL_NODE)
    WHERE src.name = 'getenv' AND dst.name = 'strcpy'
    COLUMNS (src.filename, src.line_number, dst.line_number)
);
```

---

**Version**: 1.1.0
**Created**: 2025-12-12
**Updated**: 2025-12-12
**Status**: Planning

### Changelog

**v1.1.0** (2025-12-12):
- Заменены все шаблоны запросов Joern DSL на DuckDB SQL/PGQ
- Добавлены дополнительные шаблоны: use_after_free, integer_overflow
- Добавлены PGQ шаблоны для обхода графа
- Уточнено: Joern используется только для экспорта, запросы к DuckDB

**v1.0.0** (2025-12-12):
- Начальная версия плана
