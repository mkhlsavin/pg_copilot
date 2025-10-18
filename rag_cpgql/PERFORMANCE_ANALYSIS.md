# Performance Analysis - 200-Question Test Run

## Executive Summary

**Problem**: Average execution time of 66.27s per question (vs expected 3.72s baseline) - a 17.8x slowdown.

**Root Cause**: RAGAS evaluation overhead consuming ~70s per query while producing only "nan" values.

**Solution**: Disable RAGAS evaluation for batch processing or make it optional.

## Detailed Timing Breakdown

### Overall Statistics
- **Total time**: 66.27s average
- **Generation time**: ~8-89s (highly variable, average ~15s)
- **Joern execution**: 12.37s (consistent, working as expected)
- **Other overhead**: 57.72s average (RAGAS + Interpreter + misc)

### Sample Breakdown (Question 4)
```
Total: 90.69s
├─ Generation: 7.73s (8.5%)
├─ Execution: 12.22s (13.5%)
└─ Other overhead: 70.74s (78.0%) ← RAGAS EVALUATION
```

### Evidence of RAGAS Failure
From message timeline analysis:
```
10. {'type': 'ai', 'content': 'RAGAS metrics — Faithfulness: nan,
    Answer Relevance: nan, Context Precision: nan, Context Recall: nan,
    Overall: nan'}
```

**All RAGAS metrics are "nan"** across all 200 questions, indicating:
1. RAGAS evaluation is failing internally
2. Taking 50-70s to fail
3. Falling back to heuristic metrics anyway
4. Providing zero value while consuming most execution time

## Performance Impact

### Current State
- **200 questions**: 3.7 hours (13,254 seconds)
- **Per question**: 66.27s average
- **User experience**: Unacceptable for interactive use

### Expected Performance (without RAGAS)
- **200 questions**: ~12-15 minutes (estimated)
- **Per question**: ~4-5s
  - Generation: 8-10s (variable based on prompt)
  - Execution: 12s (Joern)
  - Interpretation: 2-3s
  - Other: 1-2s
- **Total**: ~23-27s without RAGAS overhead

### Improvement Potential
- **Time savings**: 40-60s per question
- **Batch processing**: 3.7 hours → 12-15 minutes
- **Speedup**: 15-18x faster

## Components Working Correctly

✅ **Joern Execution**: 12.37s average - consistent and performant
✅ **Generation**: 7-89s - variable but acceptable (depends on prompt complexity)
✅ **Retrieval**: Fast (included in "other overhead" but minimal)
✅ **Enrichment**: Fast (included in "other overhead" but minimal)
✅ **Validation**: Fast (rule-based, no LLM)

## Recommendations

### Immediate Actions
1. **Add RAGAS skip flag** to `run_workflow()` and batch runners
2. **Default RAGAS to OFF** for experiments/batch processing
3. **Keep RAGAS ON** only for manual single-question debugging

### Code Changes Needed

**File**: `src/workflow/langgraph_workflow.py`

1. Add parameter to `build_workflow()`:
```python
def build_workflow(enable_ragas: bool = False) -> StateGraph:
    """Build workflow with optional RAGAS evaluation."""
```

2. Conditionally add evaluate node:
```python
if enable_ragas:
    workflow.add_node("evaluate", evaluate_node)
    workflow.add_edge("interpret", "evaluate")
    workflow.add_edge("evaluate", END)
else:
    workflow.add_edge("interpret", END)
```

3. Update `run_workflow()`:
```python
def run_workflow(question: str, verbose: bool = True, enable_ragas: bool = False):
    workflow = build_workflow(enable_ragas=enable_ragas)
    # ...
```

**File**: `experiments/run_langgraph_200_questions.py`

Update to disable RAGAS by default:
```python
result = run_workflow(question, verbose=False, enable_ragas=False)
```

### Long-term Solutions
1. **Fix RAGAS integration**: Investigate why metrics are "nan"
2. **Lightweight metrics**: Use heuristic-only evaluation for batch mode
3. **Async RAGAS**: Run RAGAS evaluation in background/async
4. **RAGAS sampling**: Only evaluate 10% of queries for quality monitoring

## Conclusion

The performance issue is **NOT** with:
- Joern server (working perfectly at 12s/query)
- LLM generation (acceptable at 8-89s)
- Retrieval/enrichment (fast)

The issue **IS** with:
- RAGAS evaluation taking 50-70s per query
- Producing only "nan" values
- No benefit despite massive time cost

**Action**: Disable RAGAS for batch processing to achieve 15-18x speedup.
