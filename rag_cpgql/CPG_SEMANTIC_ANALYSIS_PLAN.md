# CPG Semantic Analysis Enhancement Plan

## Problem Statement

### Current Limitations

**Test Results Analysis (200-question suite):**
- **98% execution success** but **low answer quality**
- Answers are **lists of function names**, not explanations of "how" functionality works
- Example:
  - **Question**: "How does PostgreSQL handle visibility checks for BRIN index entries?"
  - **Current answer**: "62 functions: heap_fetch, heap_insert, heap_lock_tuple..."
  - **Expected answer**: Explanation of BRIN visibility mechanism using visibility maps, transaction IDs, snapshot checks

### Root Cause

**We only extract AST structure information**, missing:

1. **Comments** - developer intent, algorithm descriptions, invariants
2. **Control Flow Graphs (CFG)** - execution paths, branching logic
3. **Data Flow** - how data flows between functions/variables
4. **Control Dependence (CDG)** - what controls what
5. **Data Dependence (DDG)** - data dependencies between operations
6. **Program Dependence (PDG)** - combined control+data dependencies

**Current queries return "WHAT"** (which functions exist), **not "HOW"** (how they implement functionality).

---

## Deep Analysis

### 1. What Information Are We Missing?

#### A. Comments & Documentation
```cpgql
// CURRENTLY NOT USED
cpg.comment.code  // Function-level documentation
cpg.comment.where(_.file.name(".*brin.*")).code  // File-level comments explaining algorithms
```

**Potential:**
- Algorithm descriptions from comments
- Invariant specifications
- Developer notes about edge cases
- References to research papers/docs

#### B. Control Flow Information
```cpgql
// CURRENTLY NOT USED
cpg.method.name("brinGetTupleForHeapBlock")
  .cfgFirst  // Entry point
  .cfgNext   // Next control flow step
  .repeat(_.cfgNext)(_.emitAll)  // Full CFG traversal
```

**Potential:**
- Understand execution order
- Identify error handling paths
- Detect lock acquisition/release patterns
- Find transaction boundary logic

#### C. Data Flow Information
```cpgql
// CURRENTLY NOT USED
cpg.method.name("heap_fetch")
  .ast.isIdentifier.name("tuple")
  .reachableBy(cpg.call)  // Who produces this data?
  .reachingDef           // Reaching definitions
```

**Potential:**
- Track how MVCC snapshot flows through visibility checks
- Understand tuple version chain traversal
- Identify lock propagation paths

#### D. Call Relationships (Beyond Simple Call Graphs)
```cpgql
// PARTIALLY USED (only .caller/.callee)
cpg.method.name("HeapTupleSatisfiesMVCC")
  .callIn  // Where is this called?
  .where(_.method.name.contains("brin"))  // Specific to BRIN context
```

**Potential:**
- Understand calling context (is this in index scan or tuple fetch?)
- Detect patterns like "always called with lock held"

### 2. Joern CPG Capabilities We're Not Using

Based on Joern documentation and CPG specification:

#### Available Graph Layers:
1. **AST** ✅ Currently using (basic)
2. **CFG** ❌ Not using
3. **DDG** ❌ Not using
4. **CDG** ❌ Not using
5. **PDG** ❌ Not using
6. **Call Graph** ⚠️ Minimally using
7. **Type System** ⚠️ Minimally using
8. **Comments** ❌ Not using

#### Available Traversals:
```cpgql
// Control Flow
.cfgFirst, .cfgLast, .cfgNext, .cfgPrev

// Data Flow
.reachingDef, .reachableBy, .ddg

// Dominance (for understanding control dependencies)
.dominates, .postDominates

// Points-to analysis
.referencedTypes, .evalType
```

### 3. Gap Between Current vs. Desired Output

| Aspect | Current Output | Desired Output |
|--------|---------------|----------------|
| **Question Type** | "Which functions handle X?" | "How does PostgreSQL implement X?" |
| **Answer Format** | List of 62 function names | Step-by-step algorithm explanation |
| **Information Source** | AST nodes + semantic tags | CFG + comments + data flow + domain knowledge |
| **Depth** | Structural (syntax tree) | Semantic (behavior & intent) |
| **Context** | Isolated functions | Call context, execution flow, data dependencies |

---

## Solution Architecture

### Phase 1: Comment & Documentation Integration (Immediate - 1 week)

#### 1.1 Extract & Index Comments
**Objective:** Leverage developer-written documentation in source code

**Implementation:**
```python
# New enrichment layer: code-comments
def extract_function_comments():
    """
    Extract comments associated with methods, with context
    """
    query = '''
    cpg.method
      .map { method =>
        val comments = method.file.comment
          .filter(c =>
            c.lineNumber.get < method.lineNumber.get &&
            c.lineNumber.get > (method.lineNumber.get - 20)
          )
          .code.l
        (method.name, method.filename, comments)
      }
    '''
```

**Vector Store Enhancement:**
- Create separate ChromaDB collection: `function_documentation`
- Index: `{function_name, file, comment_text, summary}`
- Retrieval: When question mentions a concept, retrieve relevant commented functions

**Example Benefit:**
- Question: "How does BRIN handle visibility?"
- Retrieves comment from `bringetbitmap.c`:
  ```c
  /*
   * BRIN visibility is handled via visibility maps.
   * We check oldest/newest xact in range summary...
   */
  ```

#### 1.2 Generate Documentation Embeddings
**Objective:** Semantic search over code comments

```python
class DocumentationRetriever:
    def __init__(self):
        self.doc_vectorstore = ChromaDB(collection="code_docs")

    def retrieve_relevant_docs(self, question: str, top_k=5):
        """Retrieve function comments relevant to question"""
        return self.doc_vectorstore.similarity_search(
            query=question,
            k=top_k,
            filter={"has_comment": True}
        )
```

**Integration Point:** Add to `EnrichmentAgent.get_enrichment_hints()`

---

### Phase 2: Control Flow Analysis (Medium-term - 2-3 weeks)

#### 2.1 CFG Pattern Extraction
**Objective:** Understand execution flow patterns

**Key Patterns to Detect:**
1. **Lock acquisition patterns**
   ```cpgql
   cpg.method.name(".*lock.*")
     .cfgFirst.repeat(_.cfgNext)(_.until(_.isCall.name(".*unlock.*")))
     .path  // Detects lock-protected regions
   ```

2. **Error handling paths**
   ```cpgql
   cpg.method.controlStructure.controlStructureType("IF")
     .condition.code(".*== NULL.*")
     .cfgNext  // What happens on error path?
   ```

3. **Transaction boundaries**
   ```cpgql
   cpg.call.name("StartTransactionCommand")
     .cfgNext.repeat(_.cfgNext)(_.until(_.isCall.name("CommitTransactionCommand")))
   ```

#### 2.2 Flow-Based Query Patterns
**New CPGQL Query Templates:**

Instead of:
```cpgql
// Current: flat function list
cpg.method.where(_.tag.nameExact("function-purpose").valueExact("transaction-control")).name.l
```

Generate:
```cpgql
// New: flow-aware query
cpg.method.name("HeapTupleSatisfiesMVCC")
  .cfgFirst
  .repeat(_.cfgNext)(_.emit.times(10))  // First 10 steps of execution
  .where(_.isCall)
  .map(call => (call.name, call.argument.code.l))  // Function calls + arguments
```

**Answer Improvement:**
- Before: "Functions: HeapTupleSatisfiesMVCC, XidInMVCCSnapshot, ..."
- After: "Visibility check follows these steps:
  1. Call HeapTupleSatisfiesMVCC with tuple and snapshot
  2. Extract tuple->t_xmin (creating transaction)
  3. Check if xmin is in snapshot via XidInMVCCSnapshot
  4. If committed, check tuple->t_xmax (deleting transaction)
  5. Return visibility result based on MVCC rules"

#### 2.3 CFG-Based Enrichment Tags
**New tag category:** `execution-pattern`

```json
{
  "execution-pattern": {
    "acquires-lock": ["LockBuffer", "LockTuple"],
    "checks-visibility": ["HeapTupleSatisfiesMVCC"],
    "handles-errors": ["ereport", "elog"],
    "manages-transaction": ["StartTransactionCommand"]
  }
}
```

---

### Phase 3: Data Flow Integration (Long-term - 3-4 weeks)

#### 3.1 Data Dependency Analysis
**Objective:** Track how data (especially MVCC snapshots, transaction IDs) flows

**Implementation:**
```cpgql
// Track snapshot propagation
cpg.identifier.name("snapshot")
  .reachingDef  // Where is snapshot defined?
  .isCall       // Which function produces it?
  .name.l       // Function name(s)

// Result: GetActiveSnapshot -> HeapTupleSatisfiesMVCC -> XidInMVCCSnapshot
```

**Use Case:**
- Question: "How does BRIN use MVCC snapshots?"
- Data flow analysis shows:
  ```
  bringetbitmap()
    -> GetActiveSnapshot() [produces snapshot]
    -> brin_scan() [propagates snapshot]
    -> HeapTupleSatisfiesMVCC(tuple, snapshot) [consumes snapshot]
  ```

#### 3.2 Variable-Level Context
**Track key data structures through execution:**

```cpgql
// Find all places that modify HeapTuple->t_infomask
cpg.identifier.name("t_infomask")
  .astParent.isCall.name(".*=.*")  // Assignment
  .method.name.l                    // Which functions modify it?
```

**Answer Enhancement:**
- Include: "The tuple's infomask is updated in heap_update, heap_lock_tuple to track lock state"

---

### Phase 4: Multi-Level Query Synthesis (Advanced - 4-6 weeks)

#### 4.1 Hierarchical Query Generation
**Problem:** Single CPGQL query can't answer complex "how" questions

**Solution:** Query Decomposition

```python
class SemanticQueryPlanner:
    def plan_query(self, question: str) -> List[CPGQLQuery]:
        """
        Break complex question into sub-queries
        """
        if "how does X work" in question:
            return [
                self.get_entry_points(X),      # Which functions initiate X?
                self.get_call_chain(X),        # What's the call sequence?
                self.get_data_flow(X),         # How does data flow?
                self.get_comments(X)           # What do comments say?
            ]
        elif "how does X ensure Y" in question:
            return [
                self.find_mechanism(X, Y),     # Find implementation
                self.find_invariant_checks(Y), # Find assertions
                self.find_error_handlers(Y)    # Find error cases
            ]
```

**Example for "How does BRIN handle visibility?":**

1. **Entry point query:**
   ```cpgql
   cpg.method.name("bringetbitmap").ast.isCall.name.l
   ```
   Result: `[brin_scan, heap_fetch, HeapTupleSatisfiesMVCC]`

2. **Visibility check flow:**
   ```cpgql
   cpg.method.name("HeapTupleSatisfiesMVCC")
     .cfgFirst.repeat(_.cfgNext)(_.emit.times(15))
     .where(_.isCall).name.l
   ```
   Result: `[XidInMVCCSnapshot, TransactionIdDidCommit, ...]`

3. **Comment extraction:**
   ```cpgql
   cpg.file.name(".*brin.*").comment
     .code(".*visibility.*")
   ```
   Result: Documentation explaining visibility map usage

4. **Synthesis:**
   Combine results into coherent explanation

#### 4.2 Template-Based Answer Generation
**InterpreterAgent Enhancement:**

```python
def synthesize_how_answer(self, question, query_results):
    """
    Generate structured explanation from multi-query results
    """
    if "how does" in question.lower():
        return f"""
        {question}

        **Entry Point:**
        {query_results['entry_points']}

        **Execution Flow:**
        {self.format_control_flow(query_results['cfg'])}

        **Data Dependencies:**
        {self.format_data_flow(query_results['ddg'])}

        **Key Mechanisms:**
        {query_results['comments']}

        **Implementation Details:**
        Functions involved: {query_results['functions']}
        """
```

---

## Implementation Phases

### Phase 1: Comments & Docs (Week 1-2)
- [ ] Extract comments via Joern
- [ ] Create `code_documentation` ChromaDB collection
- [ ] Integrate with EnrichmentAgent
- [ ] Update prompts to include comment context
- [ ] Test on 20 "how does X" questions

**Expected Improvement:**
- Answer quality: 30-40% (from current ~10%)
- Includes actual algorithm descriptions from code comments

### Phase 2: CFG Integration (Week 3-5)
- [ ] Add CFG traversal to CPGQL generator
- [ ] Create execution-pattern enrichment tags
- [ ] Implement flow-based query templates
- [ ] Update InterpreterAgent for flow synthesis
- [ ] Test on 50 complex questions

**Expected Improvement:**
- Answer quality: 55-65%
- Includes execution order and control flow explanations

### Phase 3: Data Flow (Week 6-9)
- [ ] Implement data dependency extraction
- [ ] Add variable-flow tracking
- [ ] Create data-flow enrichment layer
- [ ] Multi-query orchestration in GeneratorAgent
- [ ] Full 200-question re-evaluation

**Expected Improvement:**
- Answer quality: 75-85%
- Explains both "what" and "how" with data flow context

### Phase 4: Advanced Synthesis (Week 10-15)
- [ ] Hierarchical query planner
- [ ] Template-based answer generation
- [ ] Context-aware explanation synthesis
- [ ] Integration with existing Q&A knowledge base
- [ ] Publication-ready evaluation

**Expected Improvement:**
- Answer quality: 85-95%
- Comparable to expert-written explanations

---

## Technical Challenges & Mitigations

### Challenge 1: Query Complexity
**Problem:** CFG/DDG queries can be very slow (graph traversals)

**Mitigation:**
- Cache CFG patterns for common functions
- Use `take(N)` limits on traversals
- Pre-compute CFG summaries during enrichment phase
- Implement timeout mechanisms

### Challenge 2: Comment Quality
**Problem:** Not all code has good comments, comments can be outdated

**Mitigation:**
- Fallback to Q&A knowledge base when comments unavailable
- Combine multiple information sources
- Use LLM to detect comment-code inconsistencies
- Prioritize recently updated files/functions

### Challenge 3: Scalability
**Problem:** Enriching 450k vertices with CFG/DDG data is expensive

**Mitigation:**
- Incremental enrichment: start with most-queried functions
- On-demand CFG analysis (compute when needed, cache results)
- Separate "hot path" functions (MVCC, locking) for deep enrichment
- Use statistical sampling for less critical code

### Challenge 4: Answer Coherence
**Problem:** Multiple query results need synthesis into single narrative

**Mitigation:**
- Use LLM for synthesis (InterpreterAgent)
- Template-based generation for common patterns
- Chain-of-thought prompting: "Explain step-by-step based on CFG"
- Few-shot examples of good vs bad explanations

---

## Evaluation Metrics

### Current Baseline (200-question suite):
- Execution success: **98%**
- Answer contains function names: **100%**
- Answer explains "how": **~10%** ❌
- Answer cites specific code: **5%** ❌
- Answer includes control flow: **0%** ❌

### Phase 1 Target (Comments):
- Answer explains "how": **35%**
- Answer cites comments/docs: **60%**
- Answer includes algorithm descriptions: **30%**

### Phase 2 Target (CFG):
- Answer explains "how": **60%**
- Answer includes execution order: **50%**
- Answer shows error handling: **40%**

### Phase 3 Target (Data Flow):
- Answer explains "how": **80%**
- Answer traces data dependencies: **65%**
- Answer explains MVCC snapshot propagation: **70%**

### Phase 4 Target (Full System):
- Answer explains "how": **90%**
- Answer comparable to expert explanation: **80%**
- Answer includes multi-level context: **85%**

---

## Resource Requirements

### Development Time:
- Phase 1: 2 weeks (1 developer)
- Phase 2: 3 weeks (1 developer)
- Phase 3: 4 weeks (1-2 developers)
- Phase 4: 5 weeks (1-2 developers)
- **Total:** 14-16 weeks

### Infrastructure:
- Joern server: Already running ✅
- Additional ChromaDB collections: +500MB
- CFG cache storage: ~2-5GB
- LLM inference: No change (same Qwen3-Coder)

### Testing:
- 20-question dev set per phase
- Full 200-question evaluation after each phase
- Human evaluation: 50 questions (expert comparison)

---

## Expected Outcomes

### Answer Quality Transformation

**Before (Phase 0):**
```
Q: How does BRIN handle visibility checks?
A: The system found 62 functions related to MVCC and transaction control:
   heap_fetch, heap_insert, heap_lock_tuple, HeapCheckForSerializableConflictOut, ...
```

**After (Phase 1 - Comments):**
```
Q: How does BRIN handle visibility checks?
A: BRIN uses visibility maps to ensure MVCC consistency. According to the
   implementation in bringetbitmap.c, the system stores oldest/newest transaction
   IDs in each block range summary. During scan, it checks these ranges against
   the current snapshot to determine visibility...
   Key functions: bringetbitmap, brin_range_serialize, HeapTupleSatisfiesMVCC
```

**After (Phase 2 - CFG):**
```
Q: How does BRIN handle visibility checks?
A: The BRIN visibility check follows this execution path:
   1. bringetbitmap() initiates bitmap index scan
   2. For each block range, extract summary (oldest_xact, newest_xact)
   3. Compare range against snapshot via XidInMVCCSnapshot()
   4. If range potentially visible:
      - Call heap_fetch() for actual tuples
      - Perform tuple-level visibility via HeapTupleSatisfiesMVCC()
   5. Build result bitmap

   Error handling: Invalid ranges trigger elog(WARNING) and skip to next range.
   Lock management: Uses LockBuffer(BUFFER_LOCK_SHARE) during scan.
```

**After (Phase 3 - Data Flow):**
```
Q: How does BRIN handle visibility checks?
A: BRIN visibility checking integrates block-range summaries with MVCC:

   **Data Flow:**
   - Snapshot: GetActiveSnapshot() → bringetbitmap() → HeapTupleSatisfiesMVCC()
   - Transaction IDs flow: BrinDesc->oldest_xact → XidInMVCCSnapshot(snapshot)
   - Tuple data: heap_fetch(buffer) → tuple->t_xmin/t_xmax → visibility decision

   **Execution Sequence:**
   1. bringetbitmap(IndexScanDesc scan)
      - Acquires snapshot from scan->xs_snapshot
      - Iterates block ranges via BrinDesc iterator
   2. For each range summary:
      - Checks if [oldest_xact, newest_xact] overlaps snapshot
      - Uses TransactionIdPrecedes() for range comparison
   3. On potential visibility:
      - Calls heap_page_prune() to remove dead tuples
      - Invokes HeapTupleSatisfiesMVCC(tuple, snapshot)
   4. HeapTupleSatisfiesMVCC checks:
      - tuple->t_infomask flags (HEAP_XMIN_COMMITTED, etc.)
      - XidInMVCCSnapshot(tuple->t_xmin, snapshot)
      - Transaction commit status via CLOG lookup

   **Key Invariant:** Range-level visibility is conservative (may include
   invisible tuples), tuple-level check provides exact MVCC semantics.
```

---

## Next Steps

1. **Week 1:** Start Phase 1 implementation
   - Extract comments from Joern CPG
   - Build documentation ChromaDB collection
   - Test retrieval quality on 10 sample questions

2. **Week 2:** Integrate comments into workflow
   - Update EnrichmentAgent with doc retrieval
   - Modify prompts to include comment context
   - Run 20-question evaluation

3. **Week 3-4:** Begin Phase 2 (CFG)
   - Research Joern CFG API capabilities
   - Implement basic CFG traversal queries
   - Design execution-pattern enrichment schema

4. **Continuous:** Documentation & Evaluation
   - Document each phase in IMPLEMENTATION_PLAN.md
   - Track metrics in evaluation spreadsheet
   - Prepare examples for paper

---

## Conclusion

The current system successfully generates valid CPGQL queries (98% success) but produces **shallow answers** (function lists instead of explanations). By leveraging **comments**, **CFG**, **data flow**, and **multi-query synthesis**, we can transform answers from "what exists" to "how it works".

**Key Insight:** CPG contains the semantic information we need - we're just not querying the right graph layers yet.

**Feasibility:** ✅ **High** - All required capabilities exist in Joern, no fundamental blockers.

**Impact:** ✅ **Very High** - This addresses the core limitation preventing production deployment.

**Recommendation:** **Proceed with Phase 1 immediately** (comments integration) - low risk, high value, 2-week timeline.
