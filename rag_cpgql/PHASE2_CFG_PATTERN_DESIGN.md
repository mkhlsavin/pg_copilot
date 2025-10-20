# Phase 2: CFG Pattern Extraction Design
**Based on**: CFG exploration test results (5/8 tests successful)
**Date**: 2025-10-18
**Status**: Design Phase

---

## Test Results Summary

### Successful Capabilities ✅
1. **Basic CFG Access** - `.cfgFirst`, `.cfgNode`, `.cfgLast`
2. **Control Structures** - `.controlStructure`, `.controlStructureType`, `.condition`
3. **Error Handling Patterns** - IF statements with NULL checks
4. **Lock Patterns** - Call detection for lock functions
5. **Branching Analysis** - CFG node count, call count, control structure count

### Failed Capabilities ❌
1. **CFG Traversal** - `.repeat().emit.times()` not supported
2. **Execution Sequence** - Same traversal issue

### Key Limitation
The `.repeat(_.cfgNext)(_.emit.times(N))` pattern is NOT available in this Joern version.
Must use alternative approaches for CFG traversal.

---

## Alternative CFG Traversal Strategy

Since `.repeat().emit.times()` doesn't work, we'll use:

### Option 1: Manual Batch Extraction
```scala
// Get CFG nodes in batches by order range
cpg.method.name("someMethod")
  .cfgNode
  .order(0 to 100)  // First 100 nodes
  .map { node =>
    val nodeType = node.label
    val code = node.code.take(50)
    val order = node.order
    s"${order}|||${nodeType}|||${code}"
  }
  .l
```

### Option 2: Control Structure Focus (RECOMMENDED)
Instead of traversing ALL CFG nodes, extract key control structures and their contexts:
```scala
// Extract control structures with surrounding context
cpg.method.name("someMethod")
  .controlStructure
  .map { cs =>
    val csType = cs.controlStructureType
    val condition = cs.condition.code.headOption.getOrElse("NO_COND")
    val methodName = cs.method.name.head
    val lineNumber = cs.lineNumber.getOrElse(-1)
    s"${methodName}|||${lineNumber}|||${csType}|||${condition}"
  }
  .l
```

---

## Extraction Patterns to Implement

Based on successful tests, here are the CFG patterns we can extract:

### Pattern 1: Control Flow Structures
**What it captures**: IF/WHILE/FOR/SWITCH statements with conditions
**Why useful**: Explains branching logic and decision points

```python
{
  "pattern_type": "control_structure",
  "method_name": "HeapTupleSatisfiesMVCC",
  "file_path": "backend/access/heap/heapam_visibility.c",
  "line_number": 1234,
  "control_type": "IF",
  "condition": "!HeapTupleHeaderXminCommitted(tuple)",
  "description": "Checks if transaction is committed before visibility test"
}
```

**CPGQL Query**:
```scala
cpg.method.name(".*").take(100)
  .controlStructure
  .map { cs =>
    val method = cs.method.name.head
    val file = cs.file.name.headOption.getOrElse("UNKNOWN")
    val line = cs.lineNumber.getOrElse(-1)
    val csType = cs.controlStructureType
    val condition = cs.condition.code.headOption.getOrElse("NO_COND")
    s"${method}|||${file}|||${line}|||${csType}|||${condition}"
  }
  .l
```

---

### Pattern 2: Error Handling Patterns
**What it captures**: NULL checks, error returns, elog/ereport calls
**Why useful**: Documents error handling and validation logic

```python
{
  "pattern_type": "error_handling",
  "method_name": "brinbeginscan",
  "check_type": "NULL_CHECK",
  "condition": "tupcxt == NULL",
  "line_number": 545,
  "description": "Validates tuple context before processing"
}
```

**CPGQL Query**:
```scala
cpg.method.name(".*").take(100)
  .controlStructure.controlStructureType("IF")
  .where(_.condition.code(".*== NULL.*|.*!= NULL.*|.*elog.*|.*ereport.*"))
  .map { ifStmt =>
    val method = ifStmt.method.name.head
    val file = ifStmt.file.name.headOption.getOrElse("UNKNOWN")
    val line = ifStmt.lineNumber.getOrElse(-1)
    val condition = ifStmt.condition.code.head
    s"${method}|||${file}|||${line}|||NULL_CHECK|||${condition}"
  }
  .l
```

---

### Pattern 3: Lock/Unlock Patterns
**What it captures**: Lock acquisition, release, and pairing
**Why useful**: Explains concurrency control and resource protection

```python
{
  "pattern_type": "lock_pattern",
  "method_name": "heap_fetch",
  "lock_function": "LockBuffer",
  "lock_args": ["buf", "BUFFER_LOCK_EXCLUSIVE"],
  "line_number": 789,
  "unlock_count": 2,
  "description": "Acquires exclusive buffer lock before modification"
}
```

**CPGQL Query**:
```scala
cpg.call.name("LockBuffer|UnlockBuffer|LWLockAcquire|LWLockRelease").take(100)
  .map { lockCall =>
    val method = lockCall.method.name.head
    val file = lockCall.file.name.headOption.getOrElse("UNKNOWN")
    val line = lockCall.lineNumber.getOrElse(-1)
    val lockFunc = lockCall.name
    val args = lockCall.argument.code.l.mkString(", ")
    val unlockCount = lockCall.method.call.name("UnlockBuffer|LWLockRelease").size
    s"${method}|||${file}|||${line}|||${lockFunc}|||${args}|||${unlockCount}"
  }
  .l
```

---

### Pattern 4: Transaction Boundaries
**What it captures**: Transaction start, commit, abort calls
**Why useful**: Explains transaction lifecycle and atomicity boundaries

```python
{
  "pattern_type": "transaction",
  "method_name": "heap_insert",
  "transaction_call": "StartTransactionCommand",
  "line_number": 2341,
  "description": "Begins transaction for heap modification"
}
```

**CPGQL Query**:
```scala
cpg.call.name("StartTransactionCommand|CommitTransactionCommand|AbortTransaction.*").take(100)
  .map { txnCall =>
    val method = txnCall.method.name.head
    val file = txnCall.file.name.headOption.getOrElse("UNKNOWN")
    val line = txnCall.lineNumber.getOrElse(-1)
    val txnFunc = txnCall.name
    s"${method}|||${file}|||${line}|||${txnFunc}"
  }
  .l
```

---

### Pattern 5: Call Sequences (within control structures)
**What it captures**: Sequences of important calls within IF/WHILE blocks
**Why useful**: Explains what happens in different execution paths

```python
{
  "pattern_type": "call_sequence",
  "method_name": "vacuum_heap",
  "control_type": "IF",
  "condition": "needVacuum",
  "calls_in_branch": ["HeapTupleSatisfiesVacuum", "heap_page_prune", "lazy_record_dead_tuple"],
  "description": "Vacuum operations when page needs cleaning"
}
```

**CPGQL Query**:
```scala
cpg.method.name(".*").take(100)
  .controlStructure.controlStructureType("IF")
  .map { ifStmt =>
    val method = ifStmt.method.name.head
    val condition = ifStmt.condition.code.headOption.getOrElse("NO_COND")
    // Get calls within this control structure (approximate)
    val calls = ifStmt.ast.isCall.name.l.take(10).mkString(", ")
    s"${method}|||IF|||${condition}|||${calls}"
  }
  .l
```

---

### Pattern 6: CFG Complexity Metrics
**What it captures**: Method complexity indicators (nodes, branches, calls)
**Why useful**: Helps prioritize complex methods for detailed analysis

```python
{
  "pattern_type": "complexity",
  "method_name": "heap_vacuum_rel",
  "cfg_nodes": 1449,
  "call_count": 575,
  "control_structures": 52,
  "return_count": 1,
  "cyclomatic_complexity": 53,
  "description": "Highly complex method with extensive branching"
}
```

**CPGQL Query**:
```scala
cpg.method.name(".*").take(100)
  .map { m =>
    val name = m.name
    val file = m.file.name.headOption.getOrElse("UNKNOWN")
    val line = m.lineNumber.getOrElse(-1)
    val cfgNodes = m.cfgNode.size
    val calls = m.call.size
    val control = m.controlStructure.size
    val returns = m.methodReturn.size
    s"${name}|||${file}|||${line}|||${cfgNodes}|||${calls}|||${control}|||${returns}"
  }
  .l
```

---

## CFG Extractor Architecture

### File: `src/extraction/cfg_extractor.py`

```python
class CFGPatternExtractor:
    """Extract control flow patterns from Joern CPG."""

    def __init__(self, joern_client: JoernClient):
        self.client = joern_client
        self.logger = logging.getLogger(__name__)

    def extract_control_structures(self, batch_size: int = 100, total_limit: int = 10000) -> List[Dict]:
        """Extract control structure patterns."""
        patterns = []
        offset = 0

        while offset < total_limit:
            query = f"""
            cpg.method.name(".*").drop({offset}).take({batch_size})
              .controlStructure
              .map {{ cs =>
                val method = cs.method.name.head
                val file = cs.file.name.headOption.getOrElse("UNKNOWN")
                val line = cs.lineNumber.getOrElse(-1)
                val csType = cs.controlStructureType
                val condition = cs.condition.code.headOption.getOrElse("NO_COND")
                s"${{method}}|||${{file}}|||${{line}}|||${{csType}}|||${{condition}}"
              }}
              .l
            """
            result = self.client.execute_query(query)
            # Parse and store patterns
            ...

    def extract_error_handling(self, batch_size: int = 100) -> List[Dict]:
        """Extract error handling patterns."""
        ...

    def extract_lock_patterns(self, batch_size: int = 100) -> List[Dict]:
        """Extract lock/unlock patterns."""
        ...

    def extract_transaction_boundaries(self, batch_size: int = 100) -> List[Dict]:
        """Extract transaction start/commit/abort patterns."""
        ...

    def extract_complexity_metrics(self, batch_size: int = 100) -> List[Dict]:
        """Extract CFG complexity metrics for methods."""
        ...

    def extract_all_patterns(self, output_file: str):
        """Extract all CFG patterns and save to file."""
        all_patterns = {
            'control_structures': self.extract_control_structures(),
            'error_handling': self.extract_error_handling(),
            'lock_patterns': self.extract_lock_patterns(),
            'transaction_boundaries': self.extract_transaction_boundaries(),
            'complexity_metrics': self.extract_complexity_metrics()
        }

        with open(output_file, 'w') as f:
            json.dump(all_patterns, f, indent=2)
```

---

## Vector Store Schema

### Collection: `cfg_patterns`

Each CFG pattern will be stored as a document with embedding:

```python
{
  "id": "cfg_control_HeapTupleSatisfiesMVCC_1234",
  "text": "Control Structure: IF statement in HeapTupleSatisfiesMVCC\nCondition: !HeapTupleHeaderXminCommitted(tuple)\nDescription: Checks if transaction is committed before visibility test",
  "metadata": {
    "pattern_type": "control_structure",
    "method_name": "HeapTupleSatisfiesMVCC",
    "file_path": "backend/access/heap/heapam_visibility.c",
    "line_number": 1234,
    "control_type": "IF",
    "condition": "!HeapTupleHeaderXminCommitted(tuple)"
  },
  "embedding": [0.123, -0.456, ...]  // 384-dimensional vector
}
```

### Embedding Strategy

**What to embed**: Natural language description of the pattern's purpose
- "IF statement checks if transaction is committed"
- "Lock buffer with exclusive access before modification"
- "NULL check validates pointer before dereferencing"

**Why**: Enables semantic search for execution flow patterns relevant to user questions

---

## Integration with EnrichmentPromptBuilder

### New method: `build_cfg_context()`

```python
def build_cfg_context(self, question: str, analysis: Dict, top_k: int = 3) -> str:
    """Build CFG pattern context for execution flow understanding."""
    if not self.enable_cfg or not self.cfg_retriever:
        return ""

    try:
        result = self.cfg_retriever.retrieve_relevant_patterns(
            question=question,
            analysis=analysis,
            top_k=top_k
        )

        if not result['patterns'] or result['stats']['avg_relevance'] < 0.25:
            return ""

        # Format CFG patterns for prompt
        cfg_text = "## Execution Flow Patterns\n\n"
        for pattern in result['patterns']:
            cfg_text += f"**{pattern['pattern_type'].upper()}** in `{pattern['method_name']}`:\n"
            cfg_text += f"- {pattern['description']}\n"
            if 'condition' in pattern:
                cfg_text += f"- Condition: `{pattern['condition']}`\n"
            cfg_text += f"- Location: {pattern['file_path']}:{pattern['line_number']}\n\n"

        return cfg_text
    except Exception as e:
        self.logger.warning(f"Error retrieving CFG patterns: {e}")
        return ""
```

### Updated `build_full_enrichment_prompt()`

```python
def build_full_enrichment_prompt(self, hints: Dict, question: str, analysis: Dict,
                                 include_documentation: bool = True,
                                 include_cfg: bool = True) -> str:
    """Build complete enrichment prompt with documentation + CFG + tags."""
    sections = []

    # 1. Documentation context (WHAT functions do)
    if include_documentation:
        doc_context = self.build_documentation_context(question, analysis, top_k=3)
        if doc_context:
            sections.append(doc_context)

    # 2. CFG pattern context (HOW functions execute)
    if include_cfg:
        cfg_context = self.build_cfg_context(question, analysis, top_k=3)
        if cfg_context:
            sections.append(cfg_context)

    # 3. Enrichment tags
    tag_context = self.build_enrichment_context(hints, question, analysis)
    if tag_context:
        sections.append(tag_context)

    # 4. Intent-specific guidance
    intent = analysis.get('intent', 'explain-concept')
    guidance = self.get_tag_usage_guidance(intent)
    if guidance:
        sections.append(f"**Guidance**: {guidance}")

    return '\n\n'.join(sections)
```

---

## Validation Strategy

### Test Suite: `test_phase2_cfg.py`

**Questions to test CFG retrieval**:
1. "How does PostgreSQL handle transaction commit failures?" → Should retrieve transaction boundary patterns
2. "What locks does heap_update acquire?" → Should retrieve lock patterns
3. "How does BRIN index check for NULL values?" → Should retrieve error handling patterns
4. "What happens when HeapTupleSatisfiesMVCC detects uncommitted data?" → Should retrieve control structures

**Success Criteria**:
- 80%+ questions retrieve relevant CFG patterns
- Average relevance > 0.25
- Patterns accurately describe execution flow

---

## Implementation Timeline

### Week 1: Pattern Extraction
- Day 1: Implement `CFGPatternExtractor` class
- Day 2: Test control structure extraction
- Day 3: Test error handling + lock pattern extraction
- Day 4: Test transaction + complexity extraction
- Day 5: Full extraction run + validation

### Week 2: Vector Store + Retrieval
- Day 1: Create `cfg_vector_store.py` for ChromaDB integration
- Day 2: Create `cfg_retriever.py` for semantic search
- Day 3: Test CFG retrieval quality
- Day 4: Integrate into `EnrichmentPromptBuilder`
- Day 5: End-to-end testing

### Week 3: Validation + Documentation
- Day 1-2: Run Phase 2 validation suite
- Day 3: Analyze results and tune thresholds
- Day 4: Write Phase 2 completion report
- Day 5: Final testing and sign-off

---

## Risk Mitigation

### Risk 1: Pattern Extraction Performance
**Mitigation**: Use batched extraction (100 methods at a time), same as Phase 1

### Risk 2: Low Relevance Scores
**Mitigation**:
- Use descriptive embeddings (not raw code)
- Combine pattern type + condition + context in text
- Tune relevance threshold based on validation

### Risk 3: Too Many Patterns
**Mitigation**:
- Focus on high-value patterns (control structures, locks, errors)
- Skip simple patterns (e.g., basic assignments)
- Filter by complexity metrics

---

## Success Metrics

1. **Extraction Completeness**: Extract patterns from 500+ PostgreSQL methods
2. **Retrieval Quality**: Average relevance > 0.25 on validation suite
3. **Integration Success**: CFG context appears in prompts and improves query generation
4. **User Impact**: Answers explain "how" execution flows, not just "what" exists

---

**Next Steps**:
1. ✅ Design CFG patterns → COMPLETE (this document)
2. ⏳ Implement `CFGPatternExtractor` class
3. ⏳ Test extraction on sample methods
4. ⏳ Build vector store and retrieval
