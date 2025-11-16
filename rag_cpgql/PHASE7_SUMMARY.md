# Phase 7: Control Flow Analysis - Quick Start

**Status**: 📋 READY TO START
**Priority**: ⚠️ CRITICAL - Fundamental capability gap
**Timeline**: 2 days (16 hours)

---

## The Problem We Discovered

**Current System (Phases 1-6)**: Name-based method search only
- Input: "What mechanism ensures consistency during worker shutdown?"
- Output: "Function assign_session_replication_role found in trigger.c" ❌
- **Issue**: Wrong method, no logic explanation, no call chain

**Target System (Phase 7)**: Logic and control flow explanation
- Input: "What mechanism ensures consistency during worker shutdown?"
- Output: "LogicalRepWorkerMain() handles signals via HandleInterrupts() → AbortCurrentTransaction() → logicalrep_worker_write_lsn_checkpoint() → ReplicationSlotMarkXmin()" ✅
- **Achievement**: Right call chain, explains HOW and WHY

---

## The Solution

**Architecture Change**:
```
BEFORE (Phase 6):
Question → Semantic Mode → Find method by name → Return comments

AFTER (Phase 7):
Question → Intent Classification → Route:
            ↓                       ↓
      "find-method"          "explain-logic"
            ↓                       ↓
      Semantic Mode          Control Flow Mode [NEW]
            ↓                       ↓
    Name + Comments          Call Chain + Logic
```

**Key Components**:
1. **Intent Classifier**: Detect "explain mechanism" vs "find method"
2. **Control Flow Generator**: Generate CPGQL for call chains
3. **Call Chain Analyzer**: Build graph from CPGQL results
4. **Logic Synthesizer**: LLM explains the flow

---

## Implementation Checklist

### Phase 7A: Intent Classification (2h)
- [ ] Add intent classification to `analyzer_agent.py`
- [ ] Keywords: "mechanism", "ensures", "handles", "process" → "explain-logic"
- [ ] Keywords: "purpose of", "what is", "what does" → "find-method"
- [ ] Add `intent` field to `RAGCPGQLState`
- [ ] Test on 10 sample questions

### Phase 7B: Control Flow CPGQL Generator (4h)
- [ ] Create `prompts_control_flow.py`
- [ ] Create `control_flow_generator.py`
- [ ] Implement 3 query strategies:
  - Find entry point (LogicalRepWorkerMain)
  - Find relevant methods by keywords (shutdown, abort, checkpoint)
  - Build call graph (callOut, callIn)
- [ ] Test query generation

### Phase 7C: Call Chain Analyzer (3h)
- [ ] Create `call_chain_analyzer.py`
- [ ] Parse CPGQL results → build graph
- [ ] DFS traversal from entry point (max depth 5)
- [ ] Extract key functions matching question
- [ ] Return structured call chain JSON

### Phase 7D: Logic Synthesizer (3h)
- [ ] Create `prompts_logic_explanation.py`
- [ ] Create `logic_synthesizer.py`
- [ ] Build prompt: call chain + comments + question
- [ ] LLM generates: mechanism → flow → purpose → context
- [ ] Output: 600-1000 char explanation

### Phase 7E: Workflow Integration (2h)
- [ ] Add nodes: `classify_intent`, `generate_control_flow`, `analyze_call_chain`, `synthesize_logic`
- [ ] Add conditional routing after intent classification
- [ ] Wire control flow branch
- [ ] Test end-to-end

### Phase 7F: Validation (2h)
- [ ] Test on reference question (worker shutdown)
- [ ] Verify call chain extracted
- [ ] Compare output vs target answer
- [ ] Success criteria: ≥300 chars, includes call chain, explains mechanism

---

## CPGQL Query Examples

### Example 1: Find Entry Point + Callouts
```scala
val entryPoint = cpg.method.name(".*LogicalRepWorker.*Main.*").l.headOption

entryPoint.map { m =>
  Map(
    "method" -> m.name,
    "file" -> m.filename,
    "direct_calls" -> m.callOut.name.l
  )
}
```

### Example 2: Find Methods by Keywords
```scala
cpg.method
  .filter(_.name.matches(".*[Ss]hutdown.*|.*[Aa]bort.*|.*[Cc]heckpoint.*"))
  .filter(_.filename.matches(".*worker.*|.*replication.*"))
  .l
  .map { m =>
    Map(
      "method" -> m.name,
      "file" -> m.filename,
      "calls_to" -> m.callOut.name.l,
      "called_by" -> m.callIn.caller.name.l
    )
  }
```

### Example 3: Find Specific Method Context
```scala
val abortMethod = cpg.method.name("AbortCurrentTransaction").l.headOption

abortMethod.map { m =>
  Map(
    "method" -> m.name,
    "called_by" -> m.callIn.caller.name.l.take(10),
    "calls_to" -> m.callOut.name.l.take(10)
  )
}
```

---

## Expected Results

**Test Question**:
```
In PostgreSQL 17, what mechanism ensures consistency during logical
replication worker shutdown in worker.c:4097?
```

**Phase 6 Output** (Current):
```
Function assign_session_replication_role found in trigger.c:6665
[150 chars, confidence 0.60, WRONG]
```

**Phase 7 Expected Output**:
```
During logical replication worker shutdown, PostgreSQL ensures consistency
through LogicalRepWorkerMain() which handles signal interruptions via
HandleInterrupts(). Upon SIGTERM, the worker calls AbortCurrentTransaction()
to roll back uncommitted changes, then logicalrep_worker_write_lsn_checkpoint()
writes the final LSN marker, and ReplicationSlotMarkXmin() logs progress to
enable resumption after restart.

Call chain: LogicalRepWorkerMain → HandleInterrupts → AbortCurrentTransaction
→ logicalrep_worker_write_lsn_checkpoint → ReplicationSlotMarkXmin

[600 chars, confidence 0.80, CORRECT]
```

---

## Files to Create

```
src/
  agents/
    control_flow_generator.py      [NEW]
    call_chain_analyzer.py         [NEW]
    logic_synthesizer.py           [NEW]
  generation/
    prompts_control_flow.py        [NEW]
    prompts_logic_explanation.py   [NEW]
```

## Files to Modify

```
src/
  agents/
    analyzer_agent.py              [+intent classification]
  workflow/
    langgraph_workflow_simple.py   [+control flow branch]
```

---

## Risk Mitigation

**Risk**: CPGQL call chain queries too slow
- **Mitigation**: Max depth 5, timeout 3 min, parallel execution

**Risk**: Call chain incomplete (function pointers)
- **Mitigation**: Hybrid approach (callOut + name-based search)

**Risk**: LLM hallucination in synthesis
- **Mitigation**: Strict grounding prompt, validate against call chain

---

## Next Steps

1. **Start with Phase 7A**: Intent classification is simplest and validates approach
2. **Test manually**: Classify 10 questions, check accuracy
3. **Iterate**: If accuracy <80%, refine keywords
4. **Move to 7B**: Once classification works, implement CPGQL generation

---

## Success Criteria

**Must Achieve**:
- ✅ Intent classification ≥80% accurate
- ✅ Call chain ≥3 methods extracted
- ✅ Reference question gets ≥300 char explanation with call chain
- ✅ No regressions in semantic mode (Phase 6)

**Timeline**: 2 days if all goes smoothly

---

**Status**: Ready to begin Phase 7A
**First Task**: Implement intent classification in `analyzer_agent.py`
**Estimated Time**: 2 hours

---

For detailed documentation, see: `PHASE7_CONTROL_FLOW_ANALYSIS.md`
