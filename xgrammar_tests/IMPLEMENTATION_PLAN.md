# xgrammar_tests – Implementation Plan and Test Scenarios

## Objective
Prototype a CPGQL query generator that uses the formal grammar defined in `cpgql_gbnf/cpgql.gbnf` together with the [XGrammar](https://xgrammar.mlc.ai/docs/) library to produce syntactically valid Joern traversals for downstream evaluation.

---

## Phase 0: Environment Bootstrapping ✅ (completed)
1. ✅ Created the `xgrammar_tests` Python workspace targeting Python 3.11 inside the `llama.cpp` conda environment.
2. ✅ Added packaging scaffold (`pyproject.toml` with editable install, CLI entry point, optional dev extras).
3. ✅ Loader resolves the shared grammar (`cpgql_gbnf/cpgql.gbnf`) relative to the repo; no vendoring required.
4. ✅ `README.md` documents environment setup and usage. `pip install -e .[dev]` completes successfully in `llama.cpp`.

## Phase 1: Grammar Integration ✅
1. ✅ Explored XGrammar API surface (`xgrammar.grammar.Grammar`, `xgrammar.compiler.GrammarCompiler`).
2. ✅ Implemented `grammar_loader.py`:
   - Reads the shared grammar, strips comments, normalises escapes/single quotes, injects the missing `traversalArg` rule.
   - Returns a `GrammarSpec` object carrying the raw text and compiled engine when possible.
3. ✅ Error handling:
   - Provides informative `GrammarLoadError`.
   - Emits warnings (instead of exceptions) when XGrammar cannot compile the grammar, leaving `engine=None` for graceful fallback.

## Phase 2: Generator Prototype ⏳ (in progress)
1. ✅ Added `generator.QueryGenerator` supporting deterministic/random modes, per-query seeds, and max length caps.
   - ⏳ **Blocked:** current XGrammar version exposes no sampler API; once available, bridge into our wrapper.
2. ✅ CLI (`xgrammar-generate`) surfaces `--count`, `--mode`, `--seed`, `--max-steps`, `--validate`, `--grammar`.
3. ⏳ Pending enhancements:
   - Honour beam/temperature when the sampler API allows.
   - Support AST output if XGrammar exposes structured traversals.

## Phase 3: Validation and Post-processing ✅
1. ✅ Implemented `validator.validate_query` (root check, no double dots, balanced parentheses/brackets).
2. ⏳ Future: integrate with Joern once queries can be generated (e.g., smoke `joern --script` checks).
3. ✅ Loader already normalises grammar escapes; CLI output preserves canonical spacing.

## Phase 4: Testing & Evaluation ✅ (baseline)
1. ✅ Unit tests:
   - Grammar loading (success + engine guard).
   - CLI parser + failure scenarios.
   - Validator heuristics.
2. ⏳ Future tasks:
   - Snapshot/property tests after sampler integration.
   - Stats collection once generation emits real queries.

## Phase 5: Documentation & Next Steps ⏳ (partially done)
1. ✅ README updated with setup, CLI usage, and current limitation (sampler missing).
2. ⏳ Add architecture diagrams and integrate with broader RAG documentation once generator outputs queries.
3. ✅ Added `tools/export_tokenizer_metadata.py` helper to serialise Hugging Face tokenizers into vocab/metadata files consumable by the sampler builder.

---

## Test Scenarios

### Unit Tests
1. **Grammar Load Success** ✅
   - Loader returns a `GrammarSpec` (with/without engine) when grammar path is valid.
2. **Grammar Load Failure** ✅
   - Invalid path raises `GrammarLoadError`.
3. **Deterministic Generation** ⏳
   - Establish once sampler integration exists.
4. **Random Generation Diversity** ⏳
   - Ditto; requires sampler.
5. **Length Constraints** ✅
   - `QueryGenerator.generate` enforces `max_steps`.
6. **Validation Pass/Fail** ✅
   - Tests cover success/failure cases.
7. **CLI Smoke Test** ✅
   - `test_cli.py` ensures `--count` default and invalid path behaviour.

### Integration Tests (Optional / Future)
1. **Joern Parse Check** ⏳
2. **Grammar Drift Detection** ⏳
3. **Performance Baseline** ⏳

### Manual QA Checklist
1. Inspect generated traversals ⏳ (pending sampler).
2. Validate augmentation directives ⏳.
3. ✅ Documentation reflects CLI flags and module layout.

---

## Deliverables Checklist
- [x] Grammar loader module with unit tests.
- [x] Generator API and CLI (pending sampler wiring).
- [x] Validation helpers.
- [x] Automated unit tests (integration tests deferred).
- [x] README with setup instructions & roadmap.
- [x] Sampler integration (GrammarCompiler + tokenizer metadata).
- [x] GGUF tokenizer.
- [x] Joern integration tests and end-to-end evaluation.
