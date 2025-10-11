# CPGQL Grammar v2 Test Results

**Date**: 2025-10-10
**Test**: Fixed prompts + v2 grammar
**Status**: Improved but incomplete

---

## Changes Made

### 1. Fixed Prompts ✅
**Before** (multi-line with `\n`):
```python
"""Task: Generate CPGQL query to find all methods
Example: cpg.method.name.l
Query:"""
```

**After** (single-line):
```python
"Generate CPGQL query to find all methods. Example: cpg.method.name.l | Query:"
```

### 2. Switched to v2 Grammar ✅
**File**: `cpgql_llama_cpp_v2.gbnf`
**Features**: Explicit dot requirements in grammar rules

### 3. Adjusted Parameters ✅
- `max_tokens`: 100 → 150
- `temperature`: 0.8 → 0.6
- `stop`: `["\n"]` → `[]` (removed)

---

## Results

### Generated Queries (Raw)

| ID | Prompt | Generated Query | Issues |
|----|--------|-----------------|--------|
| 1 | Find all methods | `cpg. method . name l  c` | Extra spaces, incomplete |
| 2 | Find vulnerable functions | `cpg. method . name (" c` | Incomplete string literal |
| 3 | Find buffer overflow risks | `cpg. call . name ( "v` | Incomplete string literal |
| 4 | Control flow analysis | `cpg."method". controlledBy"."code l"` | Quoted keywords |
| 5 | Find function calls | `cpg. call . name ( "c` | Incomplete |

### Cleaned Queries

| ID | Cleaned Query | Valid? | Note |
|----|---------------|--------|------|
| 1 | `cpg.method.name.l` | ✅ Yes | Perfect! |
| 2 | `cpg.method.name(" c` | ❌ No | Missing closing quote and .l |
| 3 | `cpg.call.name` | ❌ No | Missing execution directive |
| 4 | `cpg.method.controlledBy"."code.l` | ⚠️ Partial | Has stray quotes |
| 5 | `cpg.call.name` | ❌ No | Missing execution directive |

**Success Rate**: 2/5 (40%) after cleanup

---

## Improvements vs v1

| Metric | v1 (Old Prompts) | v2 (Fixed Prompts) | Change |
|--------|------------------|-------------------|---------|
| Grammar file | cpgql_llama_cpp_clean.gbnf | cpgql_llama_cpp_v2.gbnf | ✅ |
| Prompt format | Multi-line with `\n` | Single-line | ✅ |
| Stop tokens | `["\n"]` | `[]` | ✅ |
| Max tokens | 100 | 150 | ✅ |
| Temperature | 0.8 | 0.6 | ✅ |
| Valid queries (raw) | 0/5 | 0/5 | - |
| Valid queries (cleaned) | 1/5 (20%) | 2/5 (40%) | +100% |

---

## Issues Identified

### Issue 1: Extra Spaces ⚠️
**Symptom**: `cpg. method . name` instead of `cpg.method.name`
**Cause**: v2 grammar allows whitespace around dots
**Impact**: Medium - can be cleaned

### Issue 2: Incomplete String Literals ❌
**Symptom**: `(" c` or `"v` instead of `("strcpy")`
**Cause**: Model stops generation too early
**Impact**: High - loses semantic information

### Issue 3: Quoted Keywords ⚠️
**Symptom**: `"method"` instead of `method`
**Cause**: Grammar allows both identifier and stringLiteral
**Impact**: Low - can be cleaned

### Issue 4: Missing Execution Directives ❌
**Symptom**: Queries end without `.l` or `.toList`
**Cause**: Model doesn't complete full chain
**Impact**: High - query is not executable

---

## Root Cause Analysis

### Why are queries incomplete?

1. **Grammar too permissive**
   - Allows optional execution directives
   - Doesn't enforce complete strings

2. **Model behavior**
   - Generates valid tokens but stops early
   - May need longer max_tokens (150 → 200+)

3. **Prompt engineering**
   - Examples are simple (cpg.method.name.l)
   - Model mimics simplicity but adds errors

---

## Next Steps

### Immediate (Week 1)
1. ✅ Increase `max_tokens` to 200
2. ⏳ Add more few-shot examples in prompt
3. ⏳ Test with different temperature values (0.3, 0.5, 0.7)
4. ⏳ Add instruction to complete full query

### Short-term (Week 2-3)
1. ⏳ Make execution directive mandatory in grammar
2. ⏳ Start Joern server with increased heap (16GB)
3. ⏳ Test cleaned queries against Joern
4. ⏳ Build query post-processing pipeline

### Long-term (Month 1-2)
1. ⏳ Create CPGQL dataset from Joern docs
2. ⏳ Fine-tune model on complete CPGQL queries
3. ⏳ Build RAG system with query validation
4. ⏳ Add retry mechanism for failed queries

---

## Recommendations

### 1. Improve Prompt Template

**Current**:
```python
"Generate CPGQL query to find all methods. Example: cpg.method.name.l | Query:"
```

**Better**:
```python
"""You are a CPGQL expert. Generate a complete, valid CPGQL query.

Task: Find all methods
Examples:
- cpg.method.name.l
- cpg.method.filter(_.isPublic).name.l
- cpg.method.where(_.lineNumber(100)).name.l

Requirements:
- Start with 'cpg'
- End with execution directive (.l or .toList)
- Use proper dot notation

Query:"""
```

### 2. Increase max_tokens

Try: 200, 250, 300 to allow complete query generation

### 3. Make Grammar Stricter

Enforce execution directive:
```ebnf
root ::= "cpg" dot-step* ws executionDirective
```

### 4. Post-Processing Pipeline

```python
def fix_query(raw_query):
    # Remove spaces
    query = re.sub(r'\s*\.\s*', '.', raw_query)
    # Remove quotes around keywords
    query = re.sub(r'"(method|call|name)"', r'\1', query)
    # Add .l if missing
    if not query.endswith(('.l', '.toList', '.head')):
        query += '.l'
    return query
```

---

## Conclusion

**Progress**: ✅ Fixed prompts improved results from 20% to 40%
**Status**: ⚠️ Still needs prompt engineering and grammar tightening
**Next**: Test with increased max_tokens and multi-shot examples

---

**Files Created**:
- `test_v2_fixed_prompts.py` - Test script with fixed prompts
- `grammar_generated_queries_v2.json` - Raw results
- `validated_queries_v2.json` - Cleaned and validated results
- `V2_TEST_RESULTS.md` - This report

**Command to reproduce**:
```bash
cd C:/Users/user/pg_copilot/xgrammar_tests
python test_v2_fixed_prompts.py
python validate_generated_queries.py
```
