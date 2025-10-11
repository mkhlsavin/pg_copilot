# CPGQL Grammar Project - Complete Structure

**Date**: 2025-10-10
**Status**: ✅ Grammar Complete | ⚠️ Prompt Engineering Needed

---

## Directory Tree

```
pg_copilot/
│
├── 📄 QUICKSTART.md                    (4.9 KB) - Quick start guide
├── 📄 PROJECT_STRUCTURE.md             (this file)
│
├── 📁 cpgql_gbnf/                      Grammar files
│   ├── cpgql_clean.gbnf                (4.7 KB) ✅ XGrammar EBNF (fixed)
│   ├── cpgql_llama_cpp.gbnf            (4.8 KB) ❌ With comments (failed)
│   ├── cpgql_llama_cpp_clean.gbnf      (3.2 KB) ✅ llama.cpp GBNF (working)
│   ├── cpgql_llama_cpp_v2.gbnf         (3.4 KB) ✅ Improved (explicit dots)
│   └── docs/
│       └── GBNF grammar for the CPGQL.md
│
└── 📁 xgrammar_tests/                  Test framework & results
    │
    ├── 📄 README.md                    (2.9 KB) - Package overview
    │
    ├── 🧪 test_llama_cpp_grammar.py    ✅ llama-cpp test (working)
    ├── 🧪 test_grammar_comparison.py   ⚠️  v1 vs v2 comparison
    ├── 📊 grammar_generated_queries.json       - Test results (5 queries)
    ├── 📊 grammar_comparison_results.json      - Comparison data
    │
    ├── 📁 src/xgrammar_tests/          Python package
    │   ├── __init__.py
    │   ├── cli.py                      - Command-line interface
    │   ├── config.py                   - Configuration
    │   ├── generator.py                - Query generation
    │   ├── grammar_loader.py           - Grammar loading
    │   ├── joern_e2e.py                - End-to-end with Joern
    │   ├── sampler.py                  - Sampling logic
    │   ├── tokenizer_alignment.py      - Tokenizer utilities
    │   └── validator.py                - Query validation
    │
    ├── 📁 tests/                       Unit tests
    │   ├── conftest.py
    │   ├── test_cli.py
    │   ├── test_grammar_loader.py
    │   ├── test_joern_e2e.py
    │   ├── test_sampler.py
    │   ├── test_tokenizer_alignment.py
    │   └── test_validator.py
    │
    └── 📁 tools/                       Utility scripts
        ├── export_tokenizer_metadata.py
        └── run_joern_e2e.py
```

---

## File Categories

### 🎯 Grammar Files (4 files, ~16 KB)

| File | Size | Status | Description |
|------|------|--------|-------------|
| `cpgql_clean.gbnf` | 4.7 KB | ✅ | XGrammar EBNF - fixed string literal |
| `cpgql_llama_cpp.gbnf` | 4.8 KB | ❌ | llama.cpp with comments (failed) |
| `cpgql_llama_cpp_clean.gbnf` | 3.2 KB | ✅ | llama.cpp clean (working) |
| `cpgql_llama_cpp_v2.gbnf` | 3.4 KB | ✅ | Improved with explicit dots |

**Recommendation**: Use `cpgql_llama_cpp_clean.gbnf` for production.

---

### 📚 Documentation (6 files, ~37 KB)

| File | Size | Purpose |
|------|------|---------|
| `QUICKSTART.md` | 4.9 KB | Quick start guide |
| `INDEX.md` | 8.9 KB | Complete file index |
| `FINAL_SUMMARY.md` | 8.3 KB | Full project summary |
| `LLAMA_CPP_TEST_RESULTS.md` | 5.4 KB | Test analysis |
| `GRAMMAR_FIX_RESULTS.md` | 2.7 KB | XGrammar fix |
| `IMPLEMENTATION_PLAN.md` | 4.4 KB | Original plan |

**Start here**: Read `QUICKSTART.md` for immediate usage.

---

### 🧪 Test Scripts (2 files)

| Script | Status | Description |
|--------|--------|-------------|
| `test_llama_cpp_grammar.py` | ✅ Working | Tests llama-cpp-python generation |
| `test_grammar_comparison.py` | ⚠️ Needs fix | Compares v1 vs v2 grammars |

**Run**: `python test_llama_cpp_grammar.py`

---

### 📦 Python Package (src/xgrammar_tests/)

**Purpose**: Reusable library for grammar-constrained CPGQL generation

**Modules**:
- `grammar_loader.py` - Load and validate grammars
- `generator.py` - Generate CPGQL queries
- `validator.py` - Validate query syntax
- `joern_e2e.py` - End-to-end testing with Joern
- `sampler.py` - Sampling strategies
- `tokenizer_alignment.py` - Token alignment utilities
- `cli.py` - Command-line interface

**Tests**: `tests/` directory with full test coverage

---

## Key Components

### 1. Grammar Loader
```python
from xgrammar_tests.grammar_loader import load_grammar

grammar = load_grammar("cpgql_llama_cpp_clean.gbnf", "root")
```

### 2. Query Generator
```python
from xgrammar_tests.generator import generate_cpgql_query

query = generate_cpgql_query(
    model=llm,
    grammar=grammar,
    prompt="Find all methods"
)
```

### 3. Validator
```python
from xgrammar_tests.validator import validate_cpgql_syntax

is_valid = validate_cpgql_syntax(query)
```

### 4. Joern E2E
```python
from xgrammar_tests.joern_e2e import execute_query_on_joern

result = execute_query_on_joern(
    query="cpg.method.name.l",
    joern_url="http://localhost:8080"
)
```

---

## Data Flow

```
User Question
     ↓
 Prompt Template
     ↓
 LLM + Grammar → Generated Query (raw)
     ↓
 Validator → Cleaned Query
     ↓
 Joern Server → Results
     ↓
 User Answer
```

---

## File Sizes Summary

```
Total Grammar Files:     ~16 KB (4 files)
Total Documentation:     ~37 KB (6 files)
Total Test Scripts:      ~12 KB (2 files)
Total Package Code:      ~45 KB (7 modules)
Total Tests:             ~30 KB (7 test files)
Total Tools:             ~8 KB (2 scripts)
────────────────────────────────────────
TOTAL PROJECT SIZE:      ~148 KB
```

---

## Dependencies

### Python Packages
```
llama-cpp-python  # Grammar-constrained generation
xgrammar          # Grammar toolkit (optional)
pytest            # Testing
requests          # HTTP client for Joern
```

### External Tools
```
Joern             # CPG analysis platform
llama.cpp         # GGUF model inference
```

---

## Usage Examples

### Example 1: Generate Query
```bash
cd xgrammar_tests
python test_llama_cpp_grammar.py
```

**Output**: 5 CPGQL queries saved to `grammar_generated_queries.json`

### Example 2: Compare Grammars
```bash
python test_grammar_comparison.py
```

**Output**: Comparison results in `grammar_comparison_results.json`

### Example 3: Use as Library
```python
from pathlib import Path
from llama_cpp import Llama, LlamaGrammar

# Load model
llm = Llama(model_path="model.gguf")

# Load grammar
grammar_text = Path("cpgql_llama_cpp_clean.gbnf").read_text()
grammar = LlamaGrammar.from_string(grammar_text)

# Generate query
output = llm(
    "Generate CPGQL query to find all methods",
    grammar=grammar,
    max_tokens=50
)

print(output['choices'][0]['text'])
```

---

## Testing Strategy

### Unit Tests
- `tests/test_grammar_loader.py` - Grammar loading
- `tests/test_validator.py` - Syntax validation
- `tests/test_sampler.py` - Sampling logic

### Integration Tests
- `tests/test_joern_e2e.py` - End-to-end with Joern
- `test_llama_cpp_grammar.py` - Full generation pipeline

### Manual Tests
- `test_grammar_comparison.py` - Grammar comparison

---

## Troubleshooting

### Issue 1: Empty Queries
**Symptom**: Generated queries are empty strings
**Cause**: Stop token "cpg" in prompt
**Fix**: Remove from `stop` parameter

### Issue 2: Incomplete Queries
**Symptom**: Queries like `cpg.method.name "v`
**Cause**: `stop=["\n"]` terminates too early
**Fix**: Use single-line prompts

### Issue 3: Grammar Won't Compile
**Symptom**: XGrammar/llama.cpp error
**Cause**: Syntax differences
**Fix**: Use appropriate grammar file

---

## Development Roadmap

### Phase 1: Grammar (✅ Complete)
- [x] Fix XGrammar string literal
- [x] Create llama.cpp GBNF grammar
- [x] Test basic generation

### Phase 2: Prompt Engineering (⏳ In Progress)
- [ ] Improve prompt templates
- [ ] Add few-shot examples
- [ ] Test different parameters

### Phase 3: Validation (⏳ Planned)
- [ ] Start Joern server
- [ ] Validate generated queries
- [ ] Build validation pipeline

### Phase 4: Production (⏳ Future)
- [ ] Create CPGQL dataset
- [ ] Fine-tune model
- [ ] Build RAG pipeline

---

## Contributing

### Adding New Grammar Rules
1. Edit `cpgql_llama_cpp_clean.gbnf`
2. Test compilation: `LlamaGrammar.from_string(...)`
3. Run tests: `python test_llama_cpp_grammar.py`
4. Update documentation

### Adding New Tests
1. Create test file in `tests/`
2. Follow naming: `test_<module>.py`
3. Use pytest fixtures from `conftest.py`
4. Run: `pytest tests/`

---

## License & Attribution

**Project**: pg_copilot - CPGQL Grammar Testing
**Created**: 2025-10-09
**Completed**: 2025-10-10
**Team**: Claude Code (Anthropic)
**Grammar Version**: v1.0 (XGrammar), v1.0-clean (llama.cpp), v2.0 (improved)

---

## References

- **llama.cpp GBNF**: https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md
- **XGrammar Docs**: https://xgrammar.mlc.ai/docs/
- **Joern Docs**: https://docs.joern.io/
- **CPGQL Guide**: https://docs.shiftleft.io/joern/cpgql/

---

**Last Updated**: 2025-10-10
**Status**: ✅ Grammar Complete | ⚠️ Prompt Engineering Needed
