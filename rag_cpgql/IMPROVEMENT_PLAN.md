# RAG-CPGQL Improvement Plan
**Date**: 2025-11-09
**Status**: Ready for Implementation
**Priority**: HIGH

---

## Executive Summary

The 10-question RAGAS evaluation completed successfully with **100% query validity** and **100% execution success**. However, all retrieval and enrichment metrics show 0.0 values. This is **NOT a pipeline failure** but a **data capture issue** in the workflow layer.

**Root Cause**: The workflow processes retrieval and enrichment data correctly (confirmed in logs) but doesn't return this data to the evaluation script.

---

## Problem Analysis

### Current State (RAGAS Results)

```
Total Samples: 10
Valid Queries: 10 (100.0%)
Execution Success: 10 (100.0%)

Semantic Mode Performance:
- Semantic queries (.map/.flatMap): 10/10 (100%)
- Comment access (cpg.comment): 10/10 (100%)
- Uses .headOption: 10/10 (100%)
- Uses .filter: 10/10 (100%)
- Average confidence: 0.00 ❌
- Average time per question: 311.9s ✅

Retrieval Quality:
- Avg Q&A Similarity: 0.000 ❌
- Avg CPGQL Similarity: 0.000 ❌

Context Coverage:
- Avg Enrichment Coverage: 0.000 ❌
- High Coverage (>=0.75): 0/10 ❌
- Low Coverage (<0.25): 10/10 ❌

Generation Quality:
- Validity Rate: 100% ✅
- Uses Enrichment Tags: 0.0% ❌
- Uses Name Filters: 100% ✅
```

### Evidence from Logs

The workflow DOES process the data:
```
Retrieved 3 Q&A pairs (avg sim: 0.811)
Retrieved 5 CPGQL examples (avg sim: 0.125)
Generated enrichment hints for domain='replication': 11 tag filters, coverage=0.13
Fallback improved coverage: 0.128 → 0.400 (+0.272)
Answer generated (confidence: 0.90)
```

But the test script receives:
```json
{
  "retrieval_stats": {
    "qa_retrieved": 0,
    "cpgql_retrieved": 0,
    "avg_qa_similarity": 0.0,
    "avg_cpgql_similarity": 0.0
  },
  "enrichment_coverage": 0.0,
  "enrichment_hints": {},
  "confidence": 0.0
}
```

### Missing Data in Workflow Return

File: `src/workflow/langgraph_workflow_simple.py:431-440`

Current return dict:
```python
return {
    "success": True,
    "state": final_state,
    "question": question,
    "query": final_state.get("cpgql_query"),
    "answer": final_state.get("answer"),
    "valid": final_state.get("query_valid"),
    "execution_success": final_state.get("execution_success"),
    "total_time": final_state["total_time"]
}
```

Missing fields:
- ❌ `similar_qa` (Q&A retrieval results)
- ❌ `cpgql_examples` (CPGQL example retrieval)
- ❌ `enrichment_hints` (with `coverage_score`)
- ❌ `analysis` (domain, intent, keywords, confidence)
- ❌ `generation_time` (individual timing)
- ❌ `retrieval_time` (individual timing)
- ❌ `confidence` (answer confidence score)

---

## Implementation Plan

### Phase 1: Fix Data Capture ⚡ **CRITICAL - HIGHEST PRIORITY**

**Objective**: Capture and return all intermediate pipeline data to enable accurate RAGAS evaluation.

#### Step 1.1: Extend Workflow State Schema

**File**: `src/workflow/langgraph_workflow_simple.py:50-75`

**Changes**:
```python
class RAGCPGQLState(TypedDict):
    """Simplified state for LangGraph workflow."""

    # Input
    question: str

    # Analysis (NEW)
    analysis: Optional[Dict]  # domain, intent, keywords, confidence

    # Retrieved context
    context: Optional[Dict]
    similar_qa: Optional[List[Dict]]  # NEW
    cpgql_examples: Optional[List[Dict]]  # NEW

    # Enrichment (NEW)
    enrichment_hints: Optional[Dict]  # with coverage_score

    # Generated query
    cpgql_query: Optional[str]
    query_valid: bool
    validation_error: Optional[str]
    retry_count: int

    # Execution
    execution_result: Optional[Dict]
    execution_success: bool

    # Answer
    answer: Optional[str]
    confidence: Optional[float]  # NEW

    # Metadata
    total_time: float
    generation_time: float  # NEW
    retrieval_time: float  # NEW
    execution_time: float  # NEW
    error: Optional[str]
```

#### Step 1.2: Update Analyze & Retrieve Node

**File**: `src/workflow/langgraph_workflow_simple.py` (find `analyze_and_retrieve` function)

**Current** (approximate):
```python
def analyze_and_retrieve(state: RAGCPGQLState) -> RAGCPGQLState:
    # ... analysis code ...
    # ... retrieval code ...

    return {
        **state,
        "context": context
    }
```

**New**:
```python
def analyze_and_retrieve(state: RAGCPGQLState) -> RAGCPGQLState:
    start_time = time.time()

    # Analyze
    analysis_result = _ANALYZER.analyze(state["question"])

    # Retrieve
    retrieval_result = _RETRIEVER.retrieve(
        state["question"],
        analysis_result.get("domain"),
        analysis_result.get("intent")
    )

    retrieval_time = time.time() - start_time

    return {
        **state,
        "analysis": analysis_result,  # NEW: Save analysis
        "context": retrieval_result,
        "similar_qa": retrieval_result.get("similar_qa", []),  # NEW
        "cpgql_examples": retrieval_result.get("cpgql_examples", []),  # NEW
        "retrieval_time": retrieval_time  # NEW
    }
```

#### Step 1.3: Update Enrichment Node

**File**: `src/workflow/langgraph_workflow_simple.py` (find `enrich` function)

**Changes**:
```python
def enrich(state: RAGCPGQLState) -> RAGCPGQLState:
    enrichment_hints = _ENRICHMENT.generate_hints(
        state["question"],
        state.get("analysis", {})
    )

    return {
        **state,
        "enrichment_hints": enrichment_hints  # NEW: Save enrichment hints
    }
```

#### Step 1.4: Update Generate Node

**File**: `src/workflow/langgraph_workflow_simple.py` (find `generate` function)

**Changes**:
```python
def generate(state: RAGCPGQLState) -> RAGCPGQLState:
    start_time = time.time()

    # ... generation code ...

    generation_time = time.time() - start_time

    return {
        **state,
        "cpgql_query": query,
        "query_valid": is_valid,
        "generation_time": generation_time  # NEW
    }
```

#### Step 1.5: Update Interpret Node

**File**: `src/workflow/langgraph_workflow_simple.py` (find `interpret` function)

**Changes**:
```python
def interpret(state: RAGCPGQLState) -> RAGCPGQLState:
    result = _INTERPRETER.interpret(
        state["question"],
        state.get("cpgql_query"),
        state.get("execution_result")
    )

    return {
        **state,
        "answer": result.get("answer"),
        "confidence": result.get("confidence", 0.0)  # NEW: Save confidence
    }
```

#### Step 1.6: Update run_workflow Return

**File**: `src/workflow/langgraph_workflow_simple.py:431-440`

**Current**:
```python
return {
    "success": True,
    "state": final_state,
    "question": question,
    "query": final_state.get("cpgql_query"),
    "answer": final_state.get("answer"),
    "valid": final_state.get("query_valid"),
    "execution_success": final_state.get("execution_success"),
    "total_time": final_state["total_time"]
}
```

**New**:
```python
return {
    "success": True,
    "state": final_state,
    "question": question,
    "query": final_state.get("cpgql_query"),
    "answer": final_state.get("answer"),
    "valid": final_state.get("query_valid"),
    "execution_success": final_state.get("execution_success"),
    "total_time": final_state["total_time"],

    # NEW: Add all missing data
    "analysis": final_state.get("analysis", {}),
    "similar_qa": final_state.get("similar_qa", []),
    "cpgql_examples": final_state.get("cpgql_examples", []),
    "enrichment_hints": final_state.get("enrichment_hints", {}),
    "confidence": final_state.get("confidence", 0.0),

    # NEW: Add individual timings
    "generation_time": final_state.get("generation_time", 0.0),
    "retrieval_time": final_state.get("retrieval_time", 0.0),
    "execution_time": final_state.get("execution_time", 0.0),

    # For RAGAS compatibility
    "ground_truth": "Valid CPGQL query",
    "execution_result": final_state.get("execution_result")
}
```

**Expected Results After Phase 1**:
```
Retrieval Quality:
- Avg Q&A Similarity: 0.40-0.80 (was 0.000)
- Avg CPGQL Similarity: 0.10-0.30 (was 0.000)

Context Coverage:
- Avg Enrichment Coverage: 0.20-0.40 (was 0.000)
- High Coverage (>=0.75): 0-2/10 (was 0/10)
- Low Coverage (<0.25): 3-5/10 (was 10/10)

Generation Quality:
- Validity Rate: 100% (maintained)
- Uses Enrichment Tags: 30-60% (was 0.0%)
- Average Confidence: 0.70-0.90 (was 0.00)
```

---

### Phase 2: Improve Enrichment Coverage 📈

**Objective**: Increase enrichment coverage from current low levels (13-36%) to target 50-70%.

#### Step 2.1: Enhance Fallback Strategies

**File**: `src/agents/enrichment_prompt_builder.py` (find `FallbackStrategySelector`)

**Analysis**: Current fallback improves coverage from 0.13 → 0.40, but we need better initial coverage.

**Changes**:
1. Add more keyword-to-tag mappings for common PostgreSQL concepts
2. Expand domain-to-tag mappings
3. Add intelligent tag inference based on question patterns

**Target Domains to Improve**:
- `replication` (current: 13% → target: 50%)
- `memory` (current: 36% → target: 60%)
- `general` (current: 0% → target: 30%)
- `wal` (current: 26% → target: 55%)

#### Step 2.2: Add Missing Tag Mappings

**File**: `src/agents/enrichment_agent.py`

**New Mappings**:
```python
DOMAIN_TAG_MAPPINGS = {
    "replication": [
        "arch:replication", "sys:wal", "pattern:message-passing",
        "func:synchronization", "pattern:worker-process", "sys:background-worker"
    ],
    "memory": [
        "sys:memory-context", "pattern:resource-management", "func:allocation",
        "pattern:caching", "sys:shared-memory", "pattern:memory-pool"
    ],
    "wal": [
        "sys:wal", "sys:xlog", "pattern:logging", "func:recovery",
        "pattern:crash-recovery", "sys:checkpointing"
    ],
    "storage": [
        "sys:buffer-manager", "sys:smgr", "pattern:page-management",
        "func:index-management", "sys:btree", "pattern:concurrency-control"
    ]
}

KEYWORD_TAG_MAPPINGS = {
    "replication": ["arch:replication", "pattern:worker-process"],
    "cache": ["pattern:caching", "sys:buffer-manager"],
    "lock": ["pattern:locking", "sys:lwlock"],
    "transaction": ["sys:transaction", "pattern:acid"],
    "index": ["sys:btree", "func:index-management"],
    "vacuum": ["sys:vacuum", "pattern:maintenance"],
    "checkpoint": ["sys:checkpointing", "sys:wal"],
}
```

#### Step 2.3: Improve Domain Detection

**File**: `src/agents/analyzer_agent.py`

**Enhancement**: Better keyword extraction and domain classification

**Expected Impact**:
- Reduce "unknown" domain from 100% to <20%
- Increase domain-specific coverage by 20-30%

---

### Phase 3: Improve CPGQL Retrieval Quality 🔍

**Objective**: Increase CPGQL example similarity from 0.10-0.30 to 0.35-0.50.

#### Step 3.1: Review CPGQL Examples Dataset

**File**: `data/cpgql_examples.json`

**Actions**:
1. Analyze distribution of examples across domains
2. Identify underrepresented query patterns
3. Add 50-100 new semantic query examples

**Focus Areas**:
- Semantic queries with `.map` and `.flatMap`
- Comment-based queries
- Complex filtering patterns
- Domain-specific queries

#### Step 3.2: Improve Embedding Quality

**File**: `src/retrieval/vector_store_real.py`

**Changes**:
1. Add query preprocessing to normalize similarity matching
2. Implement multi-stage retrieval (keyword + semantic)
3. Boost relevance of semantic query patterns

---

### Phase 4: Validation & Testing ✅

#### Test Plan

**Test 1: Data Capture Validation (After Phase 1)**
```bash
conda activate llama.cpp
python experiments/test_comprehensive_ragas.py --samples 3
```

**Success Criteria**:
- `qa_retrieved` > 0 for all samples
- `cpgql_retrieved` > 0 for all samples
- `enrichment_coverage` > 0 for all samples
- `confidence` > 0 for all samples
- All timing metrics populated

**Test 2: Enrichment Coverage (After Phase 2)**
```bash
python experiments/test_comprehensive_ragas.py --samples 10
```

**Success Criteria**:
- Avg enrichment coverage: 0.40-0.60 (up from 0.00)
- High coverage samples: 2-3/10 (up from 0/10)
- Low coverage samples: 3-5/10 (down from 10/10)

**Test 3: Full Pipeline (After Phase 3)**
```bash
python experiments/test_comprehensive_ragas.py --samples 30
```

**Success Criteria**:
- Validity Rate: >95%
- Avg Q&A Similarity: >0.50
- Avg CPGQL Similarity: >0.35
- Avg Enrichment Coverage: >0.55
- Tag Usage: >40%

---

## Implementation Timeline

### Day 1: Phase 1 (Data Capture) - 2-3 hours
- [ ] Update workflow state schema
- [ ] Modify all node functions
- [ ] Update run_workflow return
- [ ] Run Test 1 validation

### Day 2: Phase 2 (Enrichment) - 3-4 hours
- [ ] Add keyword-to-tag mappings
- [ ] Enhance fallback strategies
- [ ] Improve domain detection
- [ ] Run Test 2 validation

### Day 3: Phase 3 (Retrieval) - 2-3 hours
- [ ] Review CPGQL examples
- [ ] Add new semantic query patterns
- [ ] Improve embedding quality
- [ ] Run Test 3 validation

### Day 4: Documentation & Reporting - 1-2 hours
- [ ] Update README with new metrics
- [ ] Create performance comparison report
- [ ] Document improvements

**Total Estimated Time**: 8-12 hours

---

## Expected Impact

### Before Improvements
```
Validity Rate: 100%
Execution Success: 100%
Avg Q&A Similarity: 0.000
Avg CPGQL Similarity: 0.000
Avg Enrichment Coverage: 0.000
Tag Usage: 0.0%
Average Confidence: 0.00
```

### After Improvements (Target)
```
Validity Rate: >95%
Execution Success: >95%
Avg Q&A Similarity: >0.50
Avg CPGQL Similarity: >0.35
Avg Enrichment Coverage: >0.55
Tag Usage: >40%
Average Confidence: >0.75
Enrichment Impact: >+15%
```

---

## Risk Assessment

### Low Risk
- ✅ Phase 1 (Data Capture): Pure data plumbing, no algorithm changes
- ✅ Testing infrastructure already in place

### Medium Risk
- ⚠️ Phase 2 (Enrichment): New mappings may need tuning
- ⚠️ Phase 3 (Retrieval): Embedding changes could affect existing performance

### Mitigation
- Run validation tests after each phase
- Keep backups of working configurations
- Implement changes incrementally with git commits

---

## Success Metrics

### Primary Metrics (Must Achieve)
1. ✅ All RAGAS metrics populated (no 0.0 values)
2. ✅ Enrichment coverage >50% average
3. ✅ Validity rate maintained at >95%

### Secondary Metrics (Nice to Have)
1. Q&A similarity >0.60
2. CPGQL similarity >0.40
3. Tag usage >50%
4. Enrichment impact >+20%

---

## Next Steps

1. **Review this plan** with team/stakeholders
2. **Start Phase 1** implementation (data capture fix)
3. **Validate** with 3-question test
4. **Proceed** to Phase 2 and 3 based on results
5. **Document** improvements and update research paper metrics

---

## References

- RAGAS Results: `results/comprehensive_ragas_results_20251109_183519.json`
- Test Script: `experiments/test_comprehensive_ragas.py`
- Workflow: `src/workflow/langgraph_workflow_simple.py`
- README: `README.md` (performance metrics section)

---

**Status**: ✅ Plan Complete - Ready for Implementation
**Next Action**: Begin Phase 1 - Fix Data Capture
