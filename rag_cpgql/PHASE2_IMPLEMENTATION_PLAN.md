# Phase 2 Implementation Plan: Control Flow Graph (CFG) Integration

**Status**: 🚧 IN PROGRESS
**Started**: 2025-10-18
**Estimated Duration**: 2-3 weeks
**Goal**: Extract execution flow patterns to explain "how" code works

---

## Overview

Phase 1 successfully integrated code documentation (comments) with 0.331 avg relevance. Phase 2 builds on this foundation by adding **Control Flow Graph (CFG) analysis** to understand execution paths, branching logic, and runtime behavior.

### Phase 1 Achievement
- ✅ 638 methods with documentation indexed
- ✅ 0.331 average retrieval relevance (excellent quality)
- ✅ 100% success rate on validation tests
- ✅ Documentation integrated into prompt generation

### Phase 2 Goal
Transform answers from:
- **Before**: "Functions involved: HeapTupleSatisfiesMVCC, XidInMVCCSnapshot..."
- **After**: "Visibility check follows execution path:
  1. Call HeapTupleSatisfiesMVCC with tuple and snapshot
  2. Extract tuple->t_xmin (creating transaction)
  3. Check if xmin in snapshot via XidInMVCCSnapshot
  4. Return visibility result based on MVCC rules"

---

## Background: Joern CFG Capabilities

### Available CFG Traversals
```cpgql
// Entry/Exit points
.cfgFirst  // Entry point of method
.cfgLast   // Exit points (returns, throws)

// Traversal
.cfgNext   // Next CFG node(s) in execution
.cfgPrev   // Previous CFG node(s)

// Full traversal
.repeat(_.cfgNext)(_.emit.times(N))  // Traverse N steps
.repeat(_.cfgNext)(_.until(condition))  // Traverse until condition

// Analysis
.dominates         // Control dominance
.postDominates     // Post-dominance
.controlledBy      // Control dependencies
```

### CFG Node Types
- **METHOD** - Entry/exit points
- **CALL** - Function calls
- **IDENTIFIER** - Variable references
- **LITERAL** - Constants
- **CONTROL_STRUCTURE** - if/while/for/switch
- **RETURN** - Return statements
- **JUMP_TARGET** - Labels for goto/break/continue

---

## Implementation Tasks

### Task 1: Research & Exploration ✅ IN PROGRESS

**Objective**: Understand Joern CFG API capabilities and limitations

**Activities**:
- [x] Create `test_cfg_exploration.py` test suite
- [ ] Run 8 CFG capability tests:
  1. Basic CFG access
  2. CFG traversal
  3. Call extraction in CFG order
  4. Control structure extraction
  5. Error handling pattern detection
  6. Lock pattern detection
  7. Branching path analysis
  8. Execution sequence extraction
- [ ] Analyze results and identify working patterns
- [ ] Document CFG API capabilities and limitations

**Output**: `cfg_exploration_results.json` with test results

---

### Task 2: CFG Pattern Design

**Objective**: Design extraction patterns for common execution flows

**Key Patterns to Extract**:

#### 1. Lock Acquisition Patterns
```cpgql
cpg.call.name("LockBuffer")
  .method
  .map { m =>
    val locks = m.call.name(".*Lock.*")
    val unlocks = m.call.name(".*Unlock.*")
    (m.name, locks.size, unlocks.size)
  }
```

**Use Case**: Identify lock-protected regions for concurrency explanations

#### 2. Error Handling Patterns
```cpgql
cpg.method
  .controlStructure.controlStructureType("IF")
  .where(_.condition.code(".*== NULL.*"))
  .map { ifStmt =>
    val check = ifStmt.condition.code.head
    val errorPath = ifStmt.cfgNext.isCall.name("elog|ereport").nonEmpty
    (ifStmt.method.name.head, check, errorPath)
  }
```

**Use Case**: Explain error handling and edge cases

#### 3. Transaction Boundary Patterns
```cpgql
cpg.call.name("StartTransactionCommand")
  .cfgNext
  .repeat(_.cfgNext)(_.until(_.isCall.name("CommitTransactionCommand")))
  .path
```

**Use Case**: Identify transactional regions

#### 4. Call Sequence Patterns
```cpgql
cpg.method.name("bringetbitmap")
  .cfgFirst
  .repeat(_.cfgNext)(_.emit.times(20))
  .where(_.isCall)
  .map(call => (call.order, call.name, call.argument.code.l))
```

**Use Case**: Extract execution flow for "how does X work" questions

---

### Task 3: CFG Extractor Implementation

**Objective**: Create production CFG extractor similar to `comment_extractor_v4.py`

**File**: `src/extraction/cfg_extractor.py`

**Key Classes**:

```python
class CFGExtractor:
    """Extract control flow patterns from Joern CPG."""

    def __init__(self, joern_client: JoernClient):
        self.client = joern_client

    def extract_execution_flow(self, method_name: str, max_steps: int = 20):
        """
        Extract execution flow for a method.

        Returns:
            {
                'method_name': str,
                'entry_point': str,
                'execution_steps': [
                    {'order': int, 'type': str, 'code': str, 'is_call': bool},
                    ...
                ],
                'call_sequence': [str],  # Function calls in order
                'branching_points': [str]  # Control structures
            }
        """

    def extract_error_handling(self, method_name: str):
        """Extract error handling patterns."""

    def extract_lock_patterns(self, method_name: str):
        """Extract lock acquisition/release patterns."""

    def extract_transaction_boundaries(self, method_name: str):
        """Extract transaction start/commit points."""

    def extract_batch(self, method_names: List[str]):
        """Batch extraction for multiple methods."""
```

**Output Format**: `data/cfg_patterns.json`
```json
{
  "method_name": "heap_fetch",
  "file_path": "backend/access/heap/heapam.c",
  "execution_flow": {
    "entry": "heap_fetch(relation, snapshot, tuple)",
    "steps": [
      {"order": 1, "type": "CALL", "code": "LockBuffer(buffer, BUFFER_LOCK_SHARE)"},
      {"order": 2, "type": "CALL", "code": "HeapTupleSatisfiesMVCC(tuple, snapshot)"},
      ...
    ],
    "call_sequence": ["LockBuffer", "HeapTupleSatisfiesMVCC", "UnlockBuffer"],
    "error_checks": [
      {"check": "if (buffer == InvalidBuffer)", "action": "ereport(ERROR)"}
    ],
    "lock_pattern": {
      "acquires": ["LockBuffer"],
      "releases": ["UnlockBuffer"],
      "balanced": true
    }
  }
}
```

---

### Task 4: CFG Vector Store Creation

**Objective**: Create ChromaDB collection for CFG patterns

**File**: `src/retrieval/cfg_vector_store.py`

**Collection**: `execution_patterns`

**Schema**:
```python
{
    'id': 'cfg_heap_fetch_0',
    'text': '''
        Execution flow for heap_fetch:
        1. Acquire buffer lock (LockBuffer)
        2. Check tuple visibility (HeapTupleSatisfiesMVCC)
        3. Validate snapshot consistency
        4. Release buffer lock (UnlockBuffer)
        5. Return tuple if visible

        Error handling: NULL buffer check, invalid snapshot check
        Lock pattern: LockBuffer → UnlockBuffer (balanced)
    ''',
    'metadata': {
        'method_name': 'heap_fetch',
        'file_path': 'backend/access/heap/heapam.c',
        'pattern_type': 'execution_flow',
        'call_count': 5,
        'has_locks': True,
        'has_error_handling': True
    }
}
```

---

### Task 5: CFG Retrieval Integration

**Objective**: Add CFG retrieval to `EnrichmentPromptBuilder`

**File**: `src/agents/enrichment_prompt_builder.py` (enhance existing)

**New Methods**:

```python
def build_cfg_context(self, question: str, analysis: Dict, top_k: int = 3) -> str:
    """
    Retrieve and format CFG execution patterns.

    Args:
        question: User's question
        analysis: Question analysis (domain, intent, keywords)
        top_k: Number of CFG patterns to retrieve

    Returns:
        Formatted CFG context for prompt
    """
    if not self.enable_cfg or not self.cfg_retriever:
        return ""

    result = self.cfg_retriever.retrieve_execution_patterns(
        question=question,
        analysis=analysis,
        top_k=top_k
    )

    if result['stats']['avg_relevance'] < 0.25:
        return ""

    return self._format_cfg_for_prompt(result['patterns'])

def _format_cfg_for_prompt(self, patterns: List[Dict]) -> str:
    """Format CFG patterns for inclusion in prompt."""
    lines = ["=== Execution Flow Patterns ===\n"]

    for pattern in patterns:
        if pattern['relevance_score'] < 0.3:
            continue

        lines.append(f"Function: {pattern['method_name']}")
        lines.append(f"Execution Sequence:")
        for i, step in enumerate(pattern['call_sequence'][:10], 1):
            lines.append(f"  {i}. {step}")

        if pattern.get('error_checks'):
            lines.append("Error Handling:")
            for check in pattern['error_checks'][:3]:
                lines.append(f"  - {check}")

        lines.append("")

    return '\n'.join(lines)

def build_full_enrichment_prompt_v2(self, hints: Dict, question: str, analysis: Dict):
    """Enhanced prompt builder with CFG support."""
    sections = []

    # 1. Documentation (from Phase 1)
    doc_context = self.build_documentation_context(question, analysis)
    if doc_context:
        sections.append(doc_context)

    # 2. CFG execution patterns (NEW in Phase 2)
    cfg_context = self.build_cfg_context(question, analysis)
    if cfg_context:
        sections.append(cfg_context)

    # 3. Enrichment tags
    tag_context = self.build_enrichment_context(hints, question, analysis)
    if tag_context:
        sections.append(tag_context)

    return '\n\n'.join(sections)
```

---

### Task 6: Execution-Pattern Enrichment Tags

**Objective**: Create new enrichment layer for execution patterns

**File**: `../cpg_enrichment/enrich_execution_patterns.sc`

**New Tag Category**: `execution-pattern`

**Tag Values**:
```json
{
  "execution-pattern": {
    "acquires-lock": "Methods that acquire locks",
    "releases-lock": "Methods that release locks",
    "checks-visibility": "MVCC visibility checks",
    "handles-error": "Error handling paths",
    "manages-transaction": "Transaction boundaries",
    "iterates-collection": "Loop/iteration patterns",
    "allocates-memory": "Memory allocation points",
    "performs-io": "I/O operations"
  }
}
```

**Enrichment Script**:
```scala
// Tag methods that acquire locks
cpg.call.name(".*Lock.*")
  .method
  .newTagNode("execution-pattern", "acquires-lock")
  .store

// Tag methods with error handling
cpg.method
  .where(_.controlStructure.condition.code(".*== NULL.*"))
  .newTagNode("execution-pattern", "handles-error")
  .store

// Tag MVCC visibility checks
cpg.call.name(".*Satisfies.*")
  .method
  .newTagNode("execution-pattern", "checks-visibility")
  .store
```

---

### Task 7: Flow-Based Query Templates

**Objective**: Create CPGQL templates that use CFG information

**File**: `src/generation/flow_query_templates.py`

**Templates**:

```python
FLOW_TEMPLATES = {
    'execution_sequence': '''
        cpg.method.name("{method_name}")
          .cfgFirst
          .repeat(_.cfgNext)(_.emit.times({max_steps}))
          .where(_.isCall)
          .map(call => (call.order, call.name))
          .l
    ''',

    'error_handling_flow': '''
        cpg.method.name("{method_name}")
          .controlStructure.controlStructureType("IF")
          .where(_.condition.code(".*{error_condition}.*"))
          .cfgNext
          .isCall.name("elog|ereport")
          .map(e => (e.argument.code.l, e.lineNumber))
          .l
    ''',

    'lock_protected_region': '''
        cpg.method.name("{method_name}")
          .call.name(".*Lock.*")
          .cfgNext
          .repeat(_.cfgNext)(_.until(_.isCall.name(".*Unlock.*")))
          .isCall.name
          .l
    ''',

    'transaction_flow': '''
        cpg.call.name("StartTransactionCommand")
          .method.name("{method_name}")
          .cfgNext
          .repeat(_.cfgNext)(_.until(_.isCall.name("CommitTransactionCommand")))
          .isCall
          .map(c => (c.name, c.lineNumber))
          .l
    '''
}
```

---

### Task 8: Validation & Testing

**Objective**: Validate Phase 2 improvements

**Test Suite**: Reuse `test_phase1_simple.py` with Phase 2 enhancements

**New Metrics**:
- Answer includes execution flow: Target >50%
- Answer explains control flow: Target >40%
- Answer mentions error handling: Target >30%
- Answer describes lock patterns: Target >25%

**Validation Questions** (subset from Phase 1):
1. "How does PostgreSQL's BRIN index work for range queries?"
   - Expected: Execution flow from bringetbitmap → heap_fetch → visibility check
2. "How does PostgreSQL handle transaction rollback and cleanup?"
   - Expected: Transaction boundary detection, cleanup sequence
3. "How does PostgreSQL maintain index consistency during concurrent updates?"
   - Expected: Lock acquisition patterns, critical sections

---

### Task 9: Integration Testing

**Objective**: End-to-end testing of CFG-enhanced pipeline

**Test Flow**:
```
User Question
    ↓
AnalyzerAgent (domain, keywords)
    ↓
DocumentationRetriever (Phase 1) → Top-3 documented methods
    ↓
CFGRetriever (Phase 2) → Top-3 execution patterns
    ↓
EnrichmentAgent → Enrichment tags
    ↓
EnrichmentPromptBuilder → Combined context (docs + CFG + tags)
    ↓
GeneratorAgent → CPGQL query (potentially CFG-aware)
    ↓
Execute & interpret results
```

**Success Criteria**:
- Pipeline executes without errors
- CFG context appears in prompts
- Answers include execution flow explanations
- Quality improvement over Phase 1 baseline

---

### Task 10: Documentation & Reporting

**Objective**: Document Phase 2 implementation and results

**Deliverables**:
1. `PHASE2_COMPLETION_SUMMARY.md` - Technical details
2. `cfg_exploration_results.json` - CFG API test results
3. `data/cfg_patterns.json` - Extracted CFG patterns
4. `phase2_validation_results.json` - Validation test results

---

## Expected Outcomes

### Quantitative Metrics
| Metric | Phase 1 Baseline | Phase 2 Target | Measurement |
|--------|------------------|----------------|-------------|
| Avg Relevance | 0.331 | 0.40+ | CFG pattern retrieval quality |
| Execution Flow Explanations | 0% | 50%+ | % answers with flow descriptions |
| Error Handling Mentions | 5% | 30%+ | % answers mentioning error paths |
| Lock Pattern Detection | 0% | 25%+ | % answers describing concurrency |

### Qualitative Improvements
**Before (Phase 1)**:
```
Q: How does PostgreSQL's BRIN index work?
A: BRIN uses visibility maps to ensure MVCC consistency. The bringetbitmap
   function stores oldest/newest transaction IDs in block range summaries.
   Key functions: bringetbitmap, brin_range_serialize, HeapTupleSatisfiesMVCC
```

**After (Phase 2)**:
```
Q: How does PostgreSQL's BRIN index work?
A: BRIN index scan follows this execution flow:

   **Entry**: bringetbitmap(IndexScanDesc scan)

   **Execution Sequence**:
   1. Initialize scan state and acquire snapshot
   2. Iterate block ranges via BrinDesc iterator
   3. For each range:
      a. Extract summary (oldest_xact, newest_xact)
      b. Check range overlap with snapshot
      c. If potentially visible → fetch heap tuples
   4. Per tuple: call HeapTupleSatisfiesMVCC for exact visibility
   5. Build result bitmap

   **Error Handling**: Invalid ranges trigger elog(WARNING), scan continues
   **Concurrency**: Uses LockBuffer(BUFFER_LOCK_SHARE) during range read
```

---

## Risk Mitigation

### Risk 1: CFG Query Performance
**Concern**: CFG traversals can be slow for large methods

**Mitigation**:
- Limit traversal depth (`.emit.times(20)` max)
- Cache CFG patterns for frequently queried methods
- Use batch extraction during offline processing
- Implement timeout mechanisms (30s max per query)

### Risk 2: CFG Coverage
**Concern**: Not all methods will have useful CFG patterns

**Mitigation**:
- Fallback to Phase 1 (documentation only) when CFG unavailable
- Combine multiple information sources
- Prioritize high-value methods (MVCC, locking, transaction control)

### Risk 3: Pattern Quality
**Concern**: Extracted CFG patterns may be noisy or incomplete

**Mitigation**:
- Manual review of top 100 extracted patterns
- Relevance threshold of 0.30 for inclusion in prompts
- Iterative refinement based on validation results
- User feedback collection

---

## Timeline

**Week 1** (Oct 18-24):
- [x] Day 1: Create CFG exploration test suite
- [ ] Day 2: Analyze CFG test results, document capabilities
- [ ] Day 3: Design CFG extraction patterns
- [ ] Day 4-5: Implement CFG extractor

**Week 2** (Oct 25-31):
- [ ] Day 1-2: Extract CFG patterns for 500 methods
- [ ] Day 3: Build CFG vector store
- [ ] Day 4: Integrate CFG retrieval into EnrichmentPromptBuilder
- [ ] Day 5: Create execution-pattern enrichment tags

**Week 3** (Nov 1-7):
- [ ] Day 1-2: Implement flow-based query templates
- [ ] Day 3: Run validation test suite
- [ ] Day 4: Analyze results, refine approach
- [ ] Day 5: Complete documentation

---

## Success Criteria

✅ **Phase 2 is successful if**:
1. CFG patterns extracted for ≥500 PostgreSQL methods
2. CFG retrieval achieves ≥0.35 average relevance
3. ≥50% of answers include execution flow explanations
4. End-to-end pipeline executes without errors
5. Measurable quality improvement over Phase 1

---

**Next Immediate Steps**:
1. ✅ Create CFG exploration test suite → DONE
2. 🚧 Run CFG tests and analyze results → IN PROGRESS
3. ⏳ Design CFG extraction patterns based on test results

**Status**: Task 1 (Research & Exploration) in progress
