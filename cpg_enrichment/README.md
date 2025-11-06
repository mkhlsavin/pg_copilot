# CPG Enrichment Suite

**Purpose**: Semantic enrichment pipeline for PostgreSQL 17.6 Code Property Graph (CPG) that adds domain-specific metadata, comments, metrics, and semantic tags to enable advanced code analysis and RAG-based query generation.

**Location**: `C:\Users\user\pg_copilot\cpg_enrichment`

**Target CPG**: `C:\Users\user\joern\workspace\pg17_full.cpg` (~450K vertices)

**Quality Score**: **90/100** (Latest validation)

---

## Quick Start

### Prerequisites

- **Joern CLI**: Installed at `C:\Users\user\joern`
- **Base CPG**: `workspace\pg17_full.cpg\cpg.bin` (PostgreSQL 17.6)
- **PowerShell**: 5.1+ (Windows) or Bash (Linux/macOS)
- **JVM Memory**: 16-24GB heap (configured automatically)

### Running the Pipeline

```powershell
# Navigate to enrichment directory
cd C:\Users\user\pg_copilot\cpg_enrichment

# Run full enrichment suite
powershell.exe -ExecutionPolicy Bypass -File enrich_cpg.ps1 full

# Or run specific profile
powershell.exe -ExecutionPolicy Bypass -File enrich_cpg.ps1 standard
```

### Execution Profiles

| Profile | Scripts Included | Runtime* | Use Case |
|---------|------------------|----------|----------|
| **minimal** | `comments`, `subsystem` | ~10 min | Baseline comments and subsystem metadata |
| **standard** | `minimal` + core enrichers | ~50-60 min | Production profile with most metadata |
| **full** | All 30 enrichment scripts | ~90 min | Complete enrichment with all semantic layers |

\*Runtimes measured on PostgreSQL 17.6 (~450K vertices) with 16GB heap.

### Selective Execution

Skip already-completed scripts using `-Skip` parameter:

```powershell
# Skip heavy metrics and API scripts
./enrich_cpg.ps1 full -Skip "metrics,api"

# Rerun only specific enrichers
./enrich_cpg.ps1 full -Skip "comments,subsystem,api,security,metrics,extension,dependency"
```

---

## Current Enrichment Metrics (November 2025)

### Basic Coverage

| Metric | Count | Status |
|--------|-------|--------|
| **Total Files** | 2,254 | ✅ |
| **Total Methods** | 52,303 | ✅ |
| **Comments Attached** | 12,591,916 | ✅ |
| **Total Tags Applied** | 17,754,436 | ✅ |
| **Unique Tag Types** | 99 | ✅ |

### Subsystem Metadata

- **Subsystems Identified**: 43
- **Files Covered**: 773 (34%)
- **Coverage Status**: ⚠️ Needs improvement

### API Usage Tracking

- **APIs Tracked**: 14,380
- **Public APIs**: 12,624
- **Coverage**: ✅ 100% for public API detection

### Security Patterns

| Risk Type | Count |
|-----------|-------|
| Buffer Overflow | 1,927 |
| Format String | 2,269 |
| Path Traversal | 257 |
| Command Injection | 34 |
| SQL Injection | 21 |
| **Critical Unsanitized** | **583** |

### Code Metrics

- **High Complexity Methods**: 4,310
- **Critical Refactor Candidates**: 3,951
- **Methods with Complexity Tags**: 313,818

### Extension Points

- **Hooks Identified**: 477
- **Callbacks Detected**: 4,487
- **Total Extension Points**: 4,964

### Dependency Analysis

- **Architectural Layers**: 157
- **Circular Dependencies**: 0 ✅
- **Module Dependencies Tracked**: 1,196

### Test Coverage

- **Methods Tracked**: 51,908
- **Untested Methods**: 47,064
- **Coverage**: 9%

### Performance Analysis

- **Hot Paths Identified**: 10,798
- **Warm Paths**: 26

### Semantic Enrichment (Deep Analysis)

#### Parameters & Returns

- **Parameters Tagged**: 84,037
  - With role: 33,221 (39%)
  - With domain: 10,245 (12%)
  - Validation required: 42,466 (51%)
- **Return Statements**: 37,087
  - With outcome: 34,956 (94%)
  - With return kind: 28,885 (78%)
  - Error returns: 4,182 (11%)
  - Null returns: 1,735 (5%)

#### Variables & Identifiers

- **Local Variables**: 193,442
  - With role: 25,185 (13%)
- **Identifiers**: 847,669
  - With role: 130,936 (15%)

#### Types & Members

- **Types Classified**: 72,178
  - With category: 31,536 (44%)
  - With domain: 4,728 (7%)
  - With ownership model: 4,887 (7%)
  - Concurrency primitives: 450 (0.6%)
- **Structure Members**: 63,519
  - With role: 63,519 (100%) ✅
  - Pointer fields: 8,559 (13%)
  - Length fields: 4,577 (7%)

#### Literals & Constants

- **Total Literals**: 502,432
  - With kind classification: 404,852 (81%)
  - With interpretation: 256,732 (51%)
  - Null constants: 155,702 (31%)

#### Control Flow Elements

- **Jump Targets/Labels**: 18,301
  - With scope: 18,301 (100%) ✅
  - With domain: 6,512 (36%)
  - With kind: 208 (1%)
- **Modifiers**: 13,509
  - With concurrency tags: 13,506 (100%) ✅
  - With attributes: 13,508 (100%) ✅
  - With visibility: 1 (0.01%) ⚠️

#### Function References & Namespaces

- **Method References**: 28,375
  - With kind: 28,375 (100%) ✅
  - With usage: 3,182 (11%)
- **Namespaces**: 2,129
  - With scope: 2,129 (100%) ✅
  - With layer: 922 (43%)
  - With domain: 900 (42%)
  - With library kind: 393 (18%)

### Top-20 Most Used Tags

1. `tag-confidence` — 6,812,371
2. `type-instance-category` — 2,294,067
3. `data-flow-kind` — 1,219,286
4. `function-purpose` — 470,533
5. `param-flow` — 425,906
6. `literal-kind` — 404,852
7. `child-role` — 344,213
8. `refactor-priority` — 313,818
9. `lines-of-code` — 313,818
10. `cyclomatic-complexity` — 313,818
11. `test-count` — 311,448
12. `test-coverage` — 311,448
13. `is-pointer-to-struct` — 305,419
14. `literal-interpretation` — 256,732
15. `param-role` — 239,091
16. `lifetime` — 193,442
17. `mutability` — 193,442
18. `data-kind` — 188,697
19. `variable-role` — 156,121
20. `is-null-constant` — 155,702

---

## Enrichment Scripts Catalog

### Core Enrichers (Profile: standard)

| ID | Script | Target Nodes | Key Tags | Coverage |
|----|--------|--------------|----------|----------|
| `comments` | `ast_comments.sc` | FILE, METHOD, CALL, CONTROL_STRUCTURE, TYPE_DECL, LOCAL, RETURN | Comment associations | 12.6M comments |
| `subsystem` | `subsystem_readme.sc` | FILE | `subsystem-name`, `subsystem-path`, `subsystem-desc` | 773 files (34%) |
| `api` | `api_usage_examples.sc` | METHOD | `api-caller-count`, `api-public`, `api-example`, `api-typical-usage` | 14,380 APIs |
| `security` | `security_patterns.sc` | CALL | `security-risk`, `risk-severity`, `sanitization-point`, `trust-boundary` | 4,508 sites |
| `metrics` | `code_metrics.sc` | METHOD, FILE | `cyclomatic-complexity`, `lines-of-code`, `code-smell`, `refactor-priority` | 52,303 methods |
| `extension` | `extension_points.sc` | METHOD | `extension-point`, `extensibility`, `extension-examples` | 4,964 hooks |
| `dependency` | `dependency_graph.sc` | FILE | `module-layer`, `module-depends-on`, `module-dependents`, `circular-dependency` | 2,254 files |

### Advanced Enrichers (Profile: full)

| ID | Script | Target Nodes | Key Tags | Coverage |
|----|--------|--------------|----------|----------|
| `test` | `test_coverage.sc` | METHOD | `test-coverage`, `test-count`, `tested-by` | 51,908 methods (9%) |
| `perf` | `performance_hotspots.sc` | METHOD | `perf-hotspot`, `loop-depth`, `allocation-heavy`, `io-bound` | 10,798 hotspots |
| `semantic` | `semantic_classification.sc` | METHOD | `function-purpose`, `data-structure`, `algorithm-class`, `domain-concept` | 52,303 methods (100%) |
| `layers` | `architectural_layers.sc` | FILE | `arch-layer`, `arch-layer-description`, `arch-layer-depth`, `arch-sublayer` | 2,254 files |

### Deep Semantic Enrichers (Profile: full)

| ID | Script | Target Nodes | Key Tags | Coverage |
|----|--------|--------------|----------|----------|
| `paramroles` | `enrich_param_roles.sc` | METHOD_PARAMETER_IN/OUT, METHOD_RETURN | `param-role`, `param-domain-concept`, `validation-required`, `return-kind` | 84,037 params, 52,303 returns |
| `identifier` | `enrich_identifier_local.sc` | IDENTIFIER, LOCAL | `variable-role`, `data-kind`, `security-sensitivity`, `lifetime`, `mutability` | 847,669 identifiers, 193,442 locals |
| `fieldidentifier` | `enrich_field_identifier.sc` | FIELD_IDENTIFIER | `field-semantic`, `field-domain` | Key structure fields |
| `typedef` | `enrich_type_decl.sc` | TYPE_DECL | `type-category`, `type-domain-entity`, `type-concurrency-primitive`, `type-ownership-model` | 31,536 types |
| `typeusage` | `enrich_type_usage.sc` | TYPE, TYPE_ARGUMENT, TYPE_PARAMETER | `type-instance-category`, `type-instance-domain`, `type-generic-kind` | 72,178 types |
| `literal` | `enrich_literal_semantics.sc` | LITERAL | `literal-kind`, `literal-domain`, `literal-constant`, `literal-severity` | 502,432 literals |
| `modifier` | `enrich_modifier_semantics.sc` | MODIFIER | `modifier-visibility`, `modifier-concurrency`, `modifier-attribute` | 13,509 modifiers |
| `member` | `enrich_member_semantics.sc` | MEMBER | `member-role`, `member-pointer`, `member-length-field`, `member-unit` | 63,519 members (100%) |
| `methodref` | `enrich_method_ref.sc` | METHOD_REF | `method-ref-kind`, `method-ref-usage`, `method-ref-domain` | 28,375 refs (100%) |
| `namespace` | `enrich_namespace_semantics.sc` | NAMESPACE, NAMESPACE_BLOCK | `namespace-layer`, `namespace-domain`, `namespace-library-kind`, `namespace-scope` | 2,129 namespaces |
| `jump` | `enrich_jump_semantics.sc` | JUMP_TARGET, JUMP_LABEL | `jump-kind`, `jump-domain`, `jump-scope` | 18,301 jumps |
| `return` | `enrich_return_semantics.sc` | RETURN | `return-outcome`, `return-domain`, `returns-error`, `returns-null` | 37,087 returns |

### Cross-Layer Enrichers (Profile: full)

| ID | Script | Target Nodes | Description |
|----|--------|--------------|-------------|
| `childroles` | `enrich_child_roles.sc` | AST children | Labels AST children with roles (condition, loop body, return value) |
| `edges` | `enrich_edge_semantics.sc` | Edges | Adds argument/call semantics, branch kinds, data/control flow tags |
| `commentsem` | `enrich_comment_semantics.sc` | COMMENT | Mines documentation comments to refine parameter roles/domains |
| `pdg` | `enrich_pdg_semantics.sc` | PDG edges | Uses PDG links to summarize parameter flows and return propagation |
| `execution` | `enrich_execution_patterns.sc` | METHOD | Detects lock/unlock, allocation, error-handling patterns |
| `dataflow` | `enrich_data_flow.sc` | CALL | Traces domain entities forwarded through calls |

### Utilities & Quality Gates

| Script | Purpose |
|--------|---------|
| `enrich_common.sc` | Shared helper module with tag taxonomy, name heuristics, tagging utilities |
| `enrich_all.sc` | Orchestrator that runs selected script set and reports coverage |
| `test_cpg_quality.sc` | Post-run quality checker that scores enrichment (target: 96/100) |
| `run_layers_final.sc` | Hardened architectural layer classifier (fixed 2025-10-09) |
| `impact_analyzer_prototype.sc` | Change-impact assessment using enriched tags |

---

## Inspecting Results

### Via Joern CLI

```powershell
# Import enriched CPG
joern --import "C:\Users\user\joern\workspace\pg17_full.cpg\cpg.bin"
```

```scala
// Check comment coverage
cpg.comment.size
// Expected: 12,591,916

// Sample subsystem tags
cpg.file.tag.name("subsystem-name").value.dedup.take(10)

// Complexity distribution
cpg.method.tag.name("cyclomatic-complexity").value.l.map(_.toInt).sorted.reverse.take(10)

// Security risk sites
cpg.call.tag.name("security-risk").value.dedup

// Return semantics
cpg.ret.tag.name("return-outcome").value.dedup
// Expected: success, failure, partial-success, retry, not-applicable

// Parameter roles
cpg.parameter.tag.name("param-role").value.dedup.take(20)

// Data flow analysis
cpg.call.tag.name("data-flow-kind").value.dedup
```

### Quality Validation

Run automated quality check:

```powershell
cd C:\Users\user\joern
./joern.bat --script test_cpg_quality.sc

# View results
Get-Content stats/enrichment_quality.json
```

**Current Quality Score**: **90/100**

**Quality Checks**:
- ✅ Comments coverage (12.6M comments)
- ⚠️ Subsystem metadata (43 subsystems, 34% coverage)
- ✅ API usage tracking (14,380 APIs)
- ✅ Security patterns (5 risk types)
- ✅ Code metrics (4,310 complex methods)
- ✅ Extension points (4,964 extension points)
- ✅ Dependency graph (157 layers, 0 circular)
- ✅ Test coverage (51,908 methods tracked)
- ✅ Performance hotspots (10,824 hotspots)
- ✅ Param/return semantics (33,221 roles, 28,885 return kinds)

### Log Files

All enrichment runs generate detailed logs:

```
C:\Users\user\joern\logs\
├── enrich_comments_YYYYMMDD_HHMMSS.log
├── enrich_subsystem_YYYYMMDD_HHMMSS.log
├── enrich_api_YYYYMMDD_HHMMSS.log
└── ...
```

Check logs for errors, warnings, and detailed counters.

---

## Semantic Tag Taxonomy

### Parameter & Return Tags

| Tag | Description | Values |
|-----|-------------|--------|
| `param-role` | Semantic role of parameter | `snapshot`, `transaction-context`, `memory-context`, `buffer`, `relation`, `lock-mode`, `iterator`, `state-pointer` |
| `param-domain-concept` | PostgreSQL domain | `mvcc`, `visibility-map`, `heap-page`, `index-page`, `wal-record`, `catalog-cache`, `statistics` |
| `validation-required` | Parameter validation flags | `null-check`, `bounds-check`, `security-check`, `sanitise` |
| `return-kind` | Return value category | `boolean`, `status-code`, `error-code`, `pointer`, `struct`, `list`, `iterator`, `optional`, `allocated-pointer` |
| `return-flags` | Return qualifiers | `allocates-memory`, `nullable`, `ownership-transfer` |
| `return-outcome` | Return statement outcome | `success`, `failure`, `partial-success`, `retry`, `not-applicable` |
| `returns-error` | Error return flag | `true` |
| `returns-null` | Null return flag | `true` |

### Variable & Identifier Tags

| Tag | Description | Values |
|-----|-------------|--------|
| `variable-role` | Identifier semantic role | `iterator`, `counter`, `flag`, `state`, `buffer-manager`, `context-pointer`, `temporary` |
| `data-kind` | Domain-specific data | `transaction-id`, `snapshot`, `relation`, `buffer`, `lock`, `query`, `wal-pointer`, `lsn`, `tuple` |
| `security-sensitivity` | Sensitive data marker | `credential`, `auth-token`, `secret`, `personal-data` |
| `lifetime` | Storage duration | `auto`, `static` |
| `mutability` | Mutability | `mutable`, `immutable` |
| `is-lock` | Lock variable flag | `true` |
| `is-pointer-to-struct` | Struct pointer flag | `true` |

### Type & Member Tags

| Tag | Description | Values |
|-----|-------------|--------|
| `type-category` | Type declaration category | `struct`, `class`, `enum`, `union`, `interface`, `alias`, `typedef` |
| `type-domain-entity` | Domain entity | `relation`, `index`, `heap-tuple`, `buffer-desc`, `wal-record`, `catalog-entry`, `executor-state` |
| `type-concurrency-primitive` | Concurrency type | `spinlock`, `mutex`, `lwlock`, `semaphore`, `condition-variable`, `latched-flag` |
| `type-ownership-model` | Ownership semantics | `reference-counted`, `copy-on-write`, `pinned-buffer`, `stack-only`, `arena-managed` |
| `member-role` | Member semantic role | `data`, `reference`, `state`, `metadata`, `count`, `flag` |
| `member-pointer` | Pointer field flag | `true` |
| `member-length-field` | Length/count field flag | `true` |
| `member-unit` | Value unit | `bytes`, `blocks`, `pages`, `tuples`, `entries`, `rows` |

### Literal & Constant Tags

| Tag | Description | Values |
|-----|-------------|--------|
| `literal-kind` | Literal function | `error-code`, `special-value`, `bit-mask`, `null-constant`, `magic-number`, `boolean-flag`, `size-constant`, `timeout`, `path-string` |
| `literal-domain` | Literal domain | `transaction`, `visibility`, `buffer`, `lock`, `wal`, `catalog`, `error`, `general` |
| `literal-constant` | Named constant | e.g., `InvalidBlockNumber`, `ERRCODE_SYNTAX_ERROR` |
| `literal-severity` | Severity level | `error`, `warning`, `notice` |
| `is-null-constant` | Null/zero pointer flag | `true` |
| `is-lock-constant` | Lock mode flag | `true` |
| `is-bitmask` | Bitmask flag | `true` |

### Control Flow Tags

| Tag | Description | Values |
|-----|-------------|--------|
| `jump-kind` | Jump semantic role | `loop-break`, `loop-continue`, `error-handler`, `cleanup`, `retry`, `dispatch` |
| `jump-domain` | Jump domain context | `executor`, `storage`, `transaction`, `buffer`, `planner`, `utility` |
| `jump-scope` | Jump scope | `loop`, `function`, `switch`, `global` |
| `modifier-visibility` | Visibility level | `public`, `protected`, `private`, `internal` |
| `modifier-concurrency` | Concurrency implications | `static-volatile-global`, `volatile-access`, `atomic-access`, `thread-local`, `synchronized` |
| `modifier-attribute` | Additional attributes | `const`, `final`, `readonly`, `inline`, `constexpr`, `noinline` |

### Namespace & Reference Tags

| Tag | Description | Values |
|-----|-------------|--------|
| `namespace-layer` | Namespace layer | `planner`, `executor`, `storage`, `catalog`, `buffer`, `replication`, `utilities`, `tests` |
| `namespace-domain` | Namespace domain | `core`, `extension`, `client`, `server`, `tools`, `configuration` |
| `method-ref-kind` | Method reference kind | `callback`, `function-pointer`, `virtual-dispatch`, `signal-slot`, `interrupt-handler` |
| `method-ref-usage` | Reference usage | `comparator`, `predicate`, `allocator`, `cleanup`, `initializer`, `notifier` |

---

## Troubleshooting

### Script Failures

If a script fails, the wrapper prints the log tail immediately:

```powershell
# View full error log
Get-Content "C:\Users\user\joern\logs\enrich_<script>_<timestamp>.log"

# Rerun skipping successful scripts
./enrich_cpg.ps1 full -Skip "comments,subsystem,api"
```

### Performance Issues

The metrics script is the heaviest. Skip it when iterating on other enrichers:

```powershell
./enrich_cpg.ps1 full -Skip "metrics"
```

### Low Coverage Issues

**Subsystem Coverage (34%)**:
- Extend `subsystem_readme.sc` patterns to cover contrib modules
- Manual curation for unmapped files

**Modifier Visibility (0.01%)**:
- C language has limited visibility modifiers
- Most coverage comes from concurrency/attribute tags

**Variable Roles (13%)**:
- Heuristic-based inference needs expansion
- Focus on high-impact variables (locks, buffers, contexts)

### Workspace Persistence

Each script run reuses the same workspace, automatically saving changes:

```powershell
# Create checkpoint before risky operations
Copy-Item "C:\Users\user\joern\workspace\pg17_full.cpg\cpg.bin" `
          "C:\Users\user\joern\workspace\pg17_full.cpg\cpg.bin.backup"
```

---

## Future Enhancements

### Short-term (Q1 2025)

1. **Improve subsystem coverage** — Extend patterns to cover 83 subsystems → target 90% coverage
2. **Automate quality regression checks** — Integrate `test_cpg_quality.sc` into CI, fail on score < 90
3. **Persist metrics to disk** — Export JSON/CSV for trend analysis and reporting
4. **Harden impact analyzer** — Convert prototype to production CLI tool with markdown/JSON exports

### Medium-term (Q2 2025)

5. **Incremental enrichment** — Detect changed files/methods and reapply tags selectively
6. **RAG pipeline integration** — Update prompt templates to exploit new semantic tags
7. **Query cookbook** — Publish CPGQL query examples leveraging enrichment tags
8. **Cross-platform packaging** — Bundle as portable Docker/Conda distribution

### Long-term (Q3+ 2025)

9. **Machine learning enhancement** — Train models on tagged data to improve heuristics
10. **Multi-version support** — Extend to PostgreSQL 16, 15, MySQL, Linux kernel
11. **IDE integration** — VSCode/IntelliJ plugins for real-time enrichment queries
12. **Automated validation** — Unit tests for each enrichment script

---

## Integration with RAG-CPGQL

The enrichment suite directly supports the RAG-CPGQL query generation system at `C:\Users\user\pg_copilot\rag_cpgql`:

### Tag Usage in RAG Pipeline

- **`function-purpose`** → Identifies executor, planner, storage layer methods
- **`security-risk`** → Prioritizes security-critical code paths
- **`param-role`** + **`param-domain-concept`** → Improves parameter understanding in queries
- **`return-outcome`** → Disambiguates success/failure paths
- **`arch-layer`** → Filters queries by architectural layer
- **`data-flow-kind`** → Traces data movement across subsystems

### Enrichment Coverage Impact on RAG

Current RAG-CPGQL metrics show:
- **Enrichment Coverage**: 62.2% (improved from 44%)
- **Tag Usage**: 100% in generated queries
- **Query Validity**: 97.5% on 200-question benchmark

**Correlation**: Higher enrichment coverage → Better query generation accuracy

---

## Related Documentation

- **`ENRICHMENT_README.md`** — Complete playbook with detailed script descriptions
- **`ARCHITECTURAL_LAYERS_SUCCESS.md`** — Postmortem and metrics for October 9 architectural layer fix
- **`SESSION_SUMMARY_2025-10-07.md`** — Detailed 3-hour enrichment session log with bug analysis
- **`QUICK_START.md`** — Platform-specific manual execution commands
- **`enrich_common.sc`** — Shared taxonomy and helper utilities documentation

---

## Summary Statistics

| Category | Metric | Value | Target | Status |
|----------|--------|-------|--------|--------|
| **Overall** | Quality Score | 90/100 | 96/100 | ⚠️ |
| **Coverage** | Files Analyzed | 2,254 | 2,254 | ✅ |
| **Coverage** | Methods Analyzed | 52,303 | 52,303 | ✅ |
| **Coverage** | Comments Attached | 12.6M | >10M | ✅ |
| **Coverage** | Tags Applied | 17.7M | >15M | ✅ |
| **Subsystem** | Coverage | 34% | 90% | ⚠️ |
| **API** | Tracked APIs | 14,380 | >10K | ✅ |
| **Security** | Risk Sites | 4,508 | - | ✅ |
| **Metrics** | Complex Methods | 4,310 | - | ✅ |
| **Extension** | Extension Points | 4,964 | - | ✅ |
| **Test** | Coverage | 9% | 50% | ⚠️ |
| **Performance** | Hotspots | 10,798 | - | ✅ |
| **Semantic** | Params with Roles | 39% | 80% | ⚠️ |
| **Semantic** | Returns with Kind | 78% | 90% | ⚠️ |
| **Semantic** | Members with Roles | 100% | 100% | ✅ |

---

**Last Updated**: 2025-11-04
**Status**: Production-ready with identified improvement areas
**Next Actions**: Focus on subsystem coverage, test coverage, and parameter/return semantic enrichment
