# RAG Pipeline Prompt Improvements

**Date:** 2025-10-09
**Status:** ✅ Implemented

---

## Problems Identified

### Problem 1: LLM Generated Invalid JSON Instead of CPGQL

**Symptom:**
```
Generated Query: {"query": "cpg.method.where(_.tag.nameExact('function-purpose')..."}
Joern Error: Type Mismatch Error - Found: ("query" : String)
```

**Root Cause:**
- System prompt instructed LLM to return JSON: `{"query": "..."}`
- Joern expects pure Scala CPGQL code, not JSON
- LLM faithfully followed instructions and wrapped query in JSON

### Problem 2: LLM Used Non-Existent Enrichment Tags

**Symptom:**
```
Generated: cpg.method.where(_.tag.nameExact('function-purpose').valueExact('wal-recovery'))
Generated: cpg.method.where(_.tag.nameExact('security-block').valueExact('true'))
```

**Root Cause:**
- Prompts contained generic enrichment layer descriptions
- No concrete examples of REAL tag values from CPG
- LLM invented plausible-sounding but non-existent tags

**Real Tags in PostgreSQL CPG:**
```scala
// Semantic Classification Tags:
function-purpose: memory-management, parsing, utilities, statistics, general
data-structure: linked-list, relation, array, hash-table
algorithm-class: searching, sorting, hashing
domain-concept: replication, parallelism, extension

// Code Metrics Tags:
cyclomatic-complexity: (integer values)
lines-of-code: (integer values)
code-smell: (specific patterns)
refactor-priority: (high/medium/low)

// Performance Tags:
perf-hotspot: hot/warm/cold
allocation-heavy: true/false
loop-depth: (integer)

// Security Tags:
security-risk: sql-injection, buffer-overflow, etc.
sanitization-point: (locations)

// Test Coverage Tags:
test-coverage: tested/untested
test-count: (integer)

// Architectural Tags:
arch-layer: storage, query-executor, query-optimizer, etc.
subsystem-name: executor, planner, parser, etc.
```

---

## Solutions Implemented

### Solution 1: Updated CPGQL_SYSTEM_PROMPT

**File:** `src/generation/prompts.py`

**Changes:**

1. **Replaced generic patterns with REAL CPGQL examples** from PostgreSQL docs:
   ```scala
   // BEFORE (generic):
   "Use tags like cyclomatic-complexity, security-risk..."

   // AFTER (concrete):
   1. Find WAL functions:
      cpg.method.name("XLog.*").filename(".*transam.*").map(m => (m.name, m.filename)).l

   2. Find buffer management API:
      cpg.method.name(".*Buffer.*").filename(".*storage/buffer.*").map(m => (m.name, m.signature)).l

   3. Find functions by semantic purpose:
      cpg.method.where(_.tag.nameExact("function-purpose").valueExact("memory-management")).name.l.take(10)
   ```

2. **Changed output format instructions**:
   ```
   // BEFORE:
   Return ONLY a JSON object with a "query" field.
   Example: {"query": "cpg.method..."}

   // AFTER:
   Return ONLY the CPGQL query as plain Scala code - NO JSON, NO explanations, NO markdown.
   CORRECT: cpg.method.name("PostgresMain").map(m => (m.name, m.filename)).l
   WRONG: {"query": "cpg.method..."} or ```scala ... ```
   ```

3. **Added 10 real-world query examples** covering:
   - WAL/transaction logging
   - Security-critical authentication
   - Buffer management
   - Query planning
   - Performance analysis
   - Semantic classification
   - Refactoring candidates
   - Untested code detection
   - Performance hotspots
   - Architectural layers

### Solution 2: Added Query Parsing Logic

**File:** `run_rag_pipeline.py` (lines 128-149)

**Implementation:**

```python
# Parse LLM response - handle JSON or plain text
generated_query = raw_response.strip()

# Try to extract from JSON if LLM returned {"query": "..."}
if generated_query.startswith('{'):
    try:
        import json
        parsed = json.loads(generated_query)
        if 'query' in parsed:
            generated_query = parsed['query']
            logger.info("  Extracted query from JSON wrapper")
    except:
        pass

# Remove markdown code blocks if present
if generated_query.startswith('```'):
    lines = generated_query.split('\n')
    # Remove first and last lines (code fence)
    generated_query = '\n'.join(lines[1:-1]) if len(lines) > 2 else generated_query
    logger.info("  Extracted query from markdown code block")

generated_query = generated_query.strip()
```

**Handles:**
- ✅ Pure CPGQL: `cpg.method...` → passes through
- ✅ JSON wrapper: `{"query": "cpg.method..."}` → extracts query
- ✅ Markdown: ` ```scala\ncpg.method...\n``` ` → extracts query
- ✅ Extra whitespace → stripped

---

## Testing Plan

### Test 1: Verify Prompt Updates

```bash
cd C:/Users/user/pg_copilot/rag_cpgql
python -c "
from src.generation.prompts import CPGQL_SYSTEM_PROMPT
print('Prompt length:', len(CPGQL_SYSTEM_PROMPT))
print('Contains real examples:', 'XLog.*' in CPGQL_SYSTEM_PROMPT)
print('No JSON wrapper:', 'Return ONLY a JSON' not in CPGQL_SYSTEM_PROMPT)
print('Has Scala code examples:', 'cpg.method.name' in CPGQL_SYSTEM_PROMPT)
"
```

**Expected:**
```
Prompt length: ~4500
Contains real examples: True
No JSON wrapper: True
Has Scala code examples: True
```

### Test 2: Run RAG Pipeline

```bash
cd C:/Users/user/pg_copilot/rag_cpgql
python run_rag_pipeline.py
```

**Expected improvements:**
- LLM generates queries without JSON wrappers
- Queries use real tag names like `function-purpose`, `arch-layer`
- Queries use real tag values like `memory-management`, `storage`
- Higher query execution success rate (target: >50%)

### Test 3: Manual Query Verification

After pipeline run, check `rag_pipeline_results_3q.json`:

```python
import json
with open('rag_pipeline_results_3q.json') as f:
    results = json.load(f)

for i, result in enumerate(results['results'], 1):
    print(f"\n=== Question {i} ===")
    print(f"Query: {result.get('generated_query', 'N/A')[:100]}...")
    print(f"Success: {result.get('execution_success', False)}")
    if not result.get('execution_success'):
        print(f"Error: {result.get('raw_result', '')[:200]}")
```

---

## Expected Improvements

### Before (Previous Run):
```
Successful executions: 0/3 (0.0%)

Issues:
1. All queries wrapped in JSON: {"query": "..."}
2. Non-existent tags: function-purpose='wal-recovery', security-block='true'
3. Type mismatch errors in Joern
```

### After (Expected with CUDA LLM):
```
Successful executions: 2-3/3 (66-100%)

Improvements:
1. ✅ Pure CPGQL queries (with fallback JSON parser)
2. ✅ Real tag names from enriched CPG
3. ✅ Real tag values from semantic classification
4. ✅ Working query syntax based on real examples
```

---

## Documentation References

### Source Documents Used:

1. **CPGQL examples for PostgreSQL.md** (731 lines)
   - 80 practical CPGQL queries
   - 8 real-world scenarios
   - Real PostgreSQL function names
   - Actual enrichment tag usage

2. **SESSION_SUMMARY_2025-10-07.md** (496 lines)
   - CPG enrichment status (Quality Score: 96/100)
   - 11 enrichment layers with real tags
   - Semantic classification results (52K methods, 4 dimensions)
   - Architectural layers (16 layers, 99% coverage)

### Key Insights from Docs:

**Semantic Classification Tags (Script 10):**
```
function-purpose:
  - statistics: 15,085 methods
  - utilities: 14,170 methods
  - memory-management: 5,252 methods
  - parsing: 3,844 methods

data-structure:
  - linked-list: 4,572 methods
  - relation: 2,893 methods
  - array: 1,665 methods
  - hash-table: 1,638 methods

algorithm-class:
  - searching: 3,712 methods
  - sorting: 2,330 methods
  - hashing: 1,598 methods

domain-concept:
  - replication: 2,766 methods
  - parallelism: 1,276 methods
  - extension: 1,184 methods
```

**Architectural Layers (Script 11):**
```
arch-layer values:
  - query-executor
  - storage
  - query-optimizer
  - utils
  - access
  - replication
  - ... (16 total layers)
```

---

## Files Modified

1. **src/generation/prompts.py**
   - Lines 68-106: Replaced generic patterns with 10 real CPGQL examples
   - Line 100-104: Changed output format from JSON to plain Scala

2. **run_rag_pipeline.py**
   - Lines 118-156: Added LLM response parsing logic
   - Handles JSON wrappers, markdown code blocks, whitespace

3. **PROMPT_IMPROVEMENTS.md** (this file)
   - Complete documentation of changes
   - Testing plan
   - Expected improvements

---

## Next Steps

1. ✅ Wait for user to finish updating llama-cpp-python with CUDA
2. ⏳ Run updated RAG pipeline with improved prompts
3. ⏳ Analyze results and measure improvement
4. ⏳ Iterate on prompt engineering based on results
5. ⏳ Add more real query examples if needed

---

**Status:** ✅ Ready for testing with CUDA-enabled LLM