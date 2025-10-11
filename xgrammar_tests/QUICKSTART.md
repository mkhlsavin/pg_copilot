# CPGQL Grammar-Constrained Generation - Quick Start

**Last Updated**: 2025-10-10

## TL;DR

✅ **CPGQL grammar works with llama-cpp-python**
✅ **Grammar constrains generation to valid CPGQL syntax**
⚠️ **Query quality needs prompt engineering improvements**

---

## Quick Commands

### Test Grammar Generation
```bash
cd C:/Users/user/pg_copilot/xgrammar_tests
python test_llama_cpp_grammar.py
```

**Expected output**: 5 CPGQL queries (syntactically valid, semantically incomplete)

### View Results
```bash
# See generated queries
cat grammar_generated_queries.json

# Read full summary
cat FINAL_SUMMARY.md
```

---

## File Locations

### Grammars
```
cpgql_gbnf/
├── cpgql_llama_cpp_clean.gbnf  ← Use this one (working ✅)
├── cpgql_llama_cpp_v2.gbnf     ← Improved version (testing)
└── cpgql_clean.gbnf            ← For XGrammar (blocked)
```

### Documentation
```
xgrammar_tests/
├── INDEX.md                     ← Full file index
├── FINAL_SUMMARY.md             ← Complete results
├── LLAMA_CPP_TEST_RESULTS.md    ← Test analysis
└── GRAMMAR_FIX_RESULTS.md       ← XGrammar fix details
```

---

## Example Generated Query

**Prompt**: "Generate CPGQL query to find all methods"

**Generated**: `cpg.method.name l.name l.signature l.returnst`

**Expected**: `cpg.method.name.l`

**Issues**:
- Missing dots (`.`) between properties
- Incomplete/nonsensical properties

---

## Next Actions

### Fix Prompts (Immediate)
Current prompts have newlines that cause early termination:
```python
# ❌ Current (stops at \n)
prompt = "Task: Generate CPGQL query\nExample: cpg.method.name.l\nQuery:"

# ✅ Better
prompt = "Generate CPGQL query to find methods. Example: cpg.method.name.l | Your query:"
```

### Test Improved Grammar (Short-term)
```bash
# Edit test_llama_cpp_grammar.py to use v2 grammar
# Change: GRAMMAR_PATH = Path(".../cpgql_llama_cpp_v2.gbnf")
python test_llama_cpp_grammar.py
```

### Validate with Joern (Medium-term)
```bash
# Start Joern server
cd C:/Users/user/joern
./joern --server --server-host localhost --server-port 8080

# Test queries against real CPG
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{"query": "cpg.method.name.l"}'
```

---

## Success Criteria

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Grammar compiles | 100% | 100% | ✅ |
| Syntax validity | 100% | 100% | ✅ |
| Semantic completeness | 80% | 40% | ⚠️ |
| Joern executability | 80% | 0% | ❌ |

---

## Common Issues

### Issue 1: Empty Generated Queries
**Symptom**: All queries are empty strings
**Cause**: Stop token `"cpg"` in prompt
**Fix**: Remove `"cpg"` from `stop` parameter

### Issue 2: Incomplete Queries
**Symptom**: Queries like `cpg.method.name "v`
**Cause**: `stop=["\n"]` terminates too early
**Fix**: Use single-line prompts without newlines

### Issue 3: Missing Dots
**Symptom**: `cpg.method.name l` instead of `cpg.method.name.l`
**Cause**: Grammar allows optional dots
**Fix**: Use v2 grammar with explicit dot requirements

---

## Key Files to Modify

### 1. Improve Prompts
**File**: `test_llama_cpp_grammar.py`
**Lines**: 41-56 (prompt definitions)

```python
# Change from:
"""Task: Generate CPGQL query
Example: cpg.method.name.l
Query:"""

# To:
"Generate CPGQL query to find all methods. Example: cpg.method.name.l | Query:"
```

### 2. Test Different Grammar
**File**: `test_llama_cpp_grammar.py`
**Line**: 15

```python
# Change from:
GRAMMAR_PATH = Path(".../cpgql_llama_cpp_clean.gbnf")

# To:
GRAMMAR_PATH = Path(".../cpgql_llama_cpp_v2.gbnf")
```

### 3. Adjust Generation Parameters
**File**: `test_llama_cpp_grammar.py`
**Lines**: 64-74

```python
output = llm(
    prompt,
    max_tokens=150,        # Increase from 100
    temperature=0.6,       # Decrease for more focused
    stop=[]                # Remove stop tokens entirely
)
```

---

## Project Structure

```
pg_copilot/
├── QUICKSTART.md (this file)
├── cpgql_gbnf/
│   └── *.gbnf (grammar files)
└── xgrammar_tests/
    ├── INDEX.md (file index)
    ├── FINAL_SUMMARY.md (results)
    ├── test_*.py (test scripts)
    └── src/ (package code)
```

---

## External Resources

- **llama.cpp GBNF Guide**: https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md
- **Joern CPGQL Docs**: https://docs.joern.io/cpgql/
- **XGrammar Docs**: https://xgrammar.mlc.ai/docs/

---

## Support

For detailed analysis, see:
- `xgrammar_tests/FINAL_SUMMARY.md` - Complete project summary
- `xgrammar_tests/INDEX.md` - Full file index and references

---

**Status**: Grammar working ✅ | Prompt engineering needed ⚠️
