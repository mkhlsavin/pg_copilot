CPG Enrichment Suite
=====================

This directory contains the Scala scripts, batch wrappers, and operations notes used to enrich the PostgreSQL17.6 Code Property Graph (CPG) with domain-specific metadata for downstream RAG and analytics workloads. The suite populates tags, comment nodes, and derived metrics across files, methods, and calls so that higher-level questions (which executor functions lack tests?, where are the WAL entry points?) can be answered directly from the graph.

Contents Overview
-----------------

| Path | Purpose |
|------|---------|
| `*.sc` | Joern scripts that perform individual enrichment passes or quality checks. |
| `enrich_cpg.{sh,ps1}` | Automation wrappers that execute predefined enrichment profiles (minimal, standard, full). |
| `enrich_all.sc` | Orchestrator that runs the selected script set and reports coverage. |
| `run_layers_final.sc` | Hardened architectural layer classifier (fixes 2025-10-09). |
| `test_cpg_quality.sc` | Post-run sanity checker that scores enrichment coverage. |
| `impact_analyzer_prototype.sc` | Exploratory report for change-impact assessment using enriched tags. |
| `*.md` | Process documentation, status logs, and this consolidated guide. |

Execution Profiles
------------------

| Profile | Scripts Included | Typical Runtime* | Notes |
|---------|------------------|------------------|-------|
| minimal | `ast_comments.sc`, `subsystem_readme.sc` | ~10 min | Establishes baseline comments and subsystem tags. |
| standard | minimal + `api_usage_examples.sc`, `security_patterns.sc`, `code_metrics.sc`, `extension_points.sc`, `dependency_graph.sc` | ~5060 min | Default production profile, populates most method/file metadata. |
| full | standard + `test_coverage.sc`, `performance_hotspots.sc`, `architectural_layers.sc` (via `run_layers_final.sc`), `semantic_classification.sc` | ~90 min | Adds coverage, performance, and semantic layers. |

\*Runtimes measured on PostgreSQL17.6 (~450k vertices) with `JAVA_OPTS="-Xmx16G -Xms4G"`.

Launch Notes
-------------

- Open a shell in `pg_copilot/cpg_enrichment` before running `enrich_cpg.ps1` or `enrich_cpg.sh`. Each wrapper now exports `ENRICH_ROOT` and probes `$env:JOERN_PATH`, the system `PATH`, and sibling Joern folders. Set `JOERN_PATH` explicitly only when Joern lives elsewhere (e.g. `$env:JOERN_PATH="C:\tools\joern\joern.bat"` or `export JOERN_PATH=/opt/joern/joern`).
- When launching `enrich_all.sc` directly with `joern --script`, the script resolves sibling `.sc` files via `ENRICH_ROOT`/`-Denrich.root`. Run it from `pg_copilot/cpg_enrichment` or provide `-Denrich.root=/full/path/to/pg_copilot/cpg_enrichment`.

Script Catalog
--------------

### Core Enrichers

| Script | Target Nodes | Key Tags / Output | Status & Coverage Highlights |
|--------|--------------|-------------------|-------------------------------|
| `ast_comments.sc` | FILE, METHOD, CALL, CONTROL_STRUCTURE, TYPE_DECL, LOCAL, RETURN | Attaches existing `COMMENT` nodes to AST parents for traversal. | ~2.4M comment associations populated (Oct7 run). |
| `subsystem_readme.sc` | FILE | `subsystem-name`, `subsystem-path`, `subsystem-desc` sourced from README.md files. | 712 files mapped to 83 subsystems. |
| `api_usage_examples.sc` | METHOD | `api-caller-count`, `api-public`, `api-example`, `api-typical-usage`. | 14380 APIs classified; 100% coverage for public API detection. |
| `security_patterns.sc` | CALL | `security-risk`, `risk-severity`, `sanitization-point`, `trust-boundary`, `privilege-level`. | 4508 risky call sites tagged; severity grading restored. |
| `code_metrics.sc` | METHOD, FILE | `cyclomatic-complexity`, `lines-of-code`, `code-smell`, `refactor-priority`, `coupling-score`. | 52303 methods scored; high-complexity thresholds flagged. |
| `extension_points.sc` | METHOD | `extension-point`, `extensibility`, `extension-examples`. | 828 extensibility hooks annotated. |
| `dependency_graph.sc` | FILE | `module-layer`, `module-depends-on`, `module-dependents`, `circular-dependency`. | 2254 files analysed, circular dependencies surfaced. |
| `test_coverage.sc` | METHOD | `test-coverage`, `test-count`, `tested-by`. | 51908 methods linked to regression tests (9% coverage gap). |
| `performance_hotspots.sc` | METHOD | `perf-hotspot`, `loop-depth`, `allocation-heavy`, `io-bound`, `expensive-op`. | 10798 routines flagged for performance tuning. |
| `architectural_layers.sc` / `run_layers_final.sc` | FILE | `arch-layer`, `arch-layer-description`, `arch-layer-depth`, `arch-sublayer`. | Bug-fixed on 2025-10-09; 82% (1748 / 2111) files classified, unknown reduced to 17%. |
| `semantic_classification.sc` | METHOD | `function-purpose`, `data-structure`, `algorithm-class`, `domain-concept`. | 52303 methods (100%) semantically labelled across 30+ taxonomies. |
| `enrich_param_roles.sc` | METHOD_PARAMETER_IN/OUT, METHOD_RETURN | `param-role`, `param-domain-concept`, `validation-required`, `return-kind`, `return-flags` | Adds semantic roles to parameters and classifies method returns. |
| `enrich_identifier_local.sc` | IDENTIFIER, LOCAL | `variable-role`, `data-kind`, `security-sensitivity`, `lifetime`, `mutability`, `init-value`, `is-lock`, `is-pointer-to-struct` | Infers identifier/local roles, data kinds, storage traits, and sensitivity flags. |
| `enrich_field_identifier.sc` | FIELD_IDENTIFIER | `field-semantic`, `field-domain` | Annotates key PostgreSQL structure fields with semantic labels and domains. |
| `enrich_literal_semantics.sc` | LITERAL | `literal-kind`, `literal-domain`, `literal-constant`, `literal-severity`, `is-null-constant`, `is-lock-constant`, `is-bitmask`, `error-level`, `literal-interpretation`, `boolean-meaning`, `lock-mode` | Classifies numeric/string constants into domain-specific categories. |
| `enrich_type_decl.sc` | TYPE_DECL | `type-category`, `type-domain-entity`, `type-concurrency-primitive`, `type-ownership-model` | Classifies type declarations into structural and domain categories. |
| `enrich_type_usage.sc` | TYPE, TYPE_ARGUMENT, TYPE_PARAMETER | `type-instance-category`, `type-instance-domain`, `type-generic-kind`, `type-argument-kind`, `type-parameter-role`, `type-concurrency-primitive`, `type-ownership-model` | Classifies type usages, template arguments, and parameters. |
| `enrich_member_semantics.sc` | MEMBER | `member-role`, `member-pointer`, `member-length-field`, `member-unit` | Classes structure fields into roles and captures pointer/length/unit metadata. |
| `enrich_method_ref.sc` | METHOD_REF | `method-ref-kind`, `method-ref-usage`, `method-ref-domain` | Classifies function references (callbacks, function pointers) with usage semantics. |
| `enrich_namespace_semantics.sc` | NAMESPACE, NAMESPACE_BLOCK | `namespace-layer`, `namespace-domain`, `namespace-library-kind`, `namespace-scope` | Annotates namespaces with architectural layer, domain, and scope metadata. |
| `enrich_jump_semantics.sc` | JUMP_TARGET, JUMP_LABEL | `jump-kind`, `jump-domain`, `jump-scope` | Classifies jump labels/targets (cleanup, error, retry, etc.). |
| `enrich_return_semantics.sc` | RETURN | `return-outcome`, `return-domain`, `returns-error`, `returns-null` | Classifies return statements by outcome, domain, and flags error/null returns. |
| `enrich_modifier_semantics.sc` | MODIFIER | `modifier-visibility`, `modifier-concurrency`, `modifier-attribute` | Classifies modifiers for visibility, concurrency, and additional attributes. |

### Utilities & Quality Gates

- `enrich_common.sc` - Shared helper module providing tag taxonomy metadata, name/comment heuristics, and tagging utilities for enrichment scripts.
- `enrich_cpg.sh` / `enrich_cpg.ps1` - Platform-specific runners that unzip/import the workspace, configure JVM heap (24GB default), and call `enrich_all.sc`.
- `run_layers_final.sc` - Thin wrapper that opens the Joern workspace, filters MinGW headers, normalises path separators, and re-applies architectural tags (post-bug-fix script).
- `test_cpg_quality.sc` - Scores the enriched graph (target: 96/100) by sampling comments, APIs, security flags, metrics, coverage, and layer tags.
- `impact_analyzer_prototype.sc` - Demonstrates how enrichment tags drive change-impact analysis (e.g., call graph fan-out, subsystem context, risk-aware prioritisation).

Recent Results (2025-10-09)
---------------------------

- **Architectural layers:** classification coverage improved from 7% to 82% (1748 / 2111 files) after path/regex fixes; MinGW headers excluded; unknown bucket now 17%.
- **Semantic classification:** 52303 methods mapped to four semantic dimensions (purpose, data structure, algorithm class, domain concept) with 100% coverage.
- **API catalog:** 14380 methods tagged, public API detection active, top callers instantly queryable.
- **Security patterns:** 4508 call sites labelled with risk type, severity, trust boundaries, and sanitisation status.
- **Performance hotspots:** 10798 routines analysed for loop depth, allocation intensity, and expensive operations.
- **Quality score:** `test_cpg_quality.sc` reports 96/100 when the full profile is re-applied to `pg17_full.cpg`.

Future Enhancements
-------------------

1. **Close the remaining 17% unknown architectural files**  extend `LAYER_PATTERNS` to cover contrib modules and tests, or feed unknowns into a manual curation loop.
2. **Persist enrichment metrics to disk**  capture JSON/CSV outputs for CI reporting (coverage deltas, counts per tag).
3. **Automate regression checks**  wire `test_cpg_quality.sc` into the enrichment wrappers and fail the run when quality drops below the 96/100 baseline.
4. **Introduce incremental updates**  detect changed files/methods and reapply tags selectively instead of rerunning full passes.
5. **Harden `impact_analyzer_prototype.sc`**  convert the prototype into a CLI module that accepts method lists and exports markdown/JSON reports.
6. **Integrate with the RAG pipeline**  update prompt templates to exploit new tags (`arch-layer`, `function-purpose`, `security-risk`) and publish a query cookbook.
7. **Cross-platform packaging**  bundle JVM heap presets and Joern path discovery into a shared PowerShell/Bash module to simplify invocation.

Semantic Tag Taxonomy (Phase 0 / 1 additions)
---------------------------------------------

| Tag Name | Description | Typical Values |
|----------|-------------|----------------|
| `param-role` | Semantic role of a parameter or argument (what entity it represents). | `snapshot`, `transaction-context`, `memory-context`, `buffer`, `relation`, `lock-mode`, `iterator`, `state-pointer` |
| `param-domain-concept` | PostgreSQL domain mapped to the parameter. | `mvcc`, `visibility-map`, `heap-page`, `index-page`, `wal-record`, `catalog-cache`, `statistics` |
| `validation-required` | Indicates the parameter must be validated at call sites. | `null-check`, `bounds-check`, `security-check`, `sanitise` |
| `return-kind` | High-level semantic category of a return value. | `boolean`, `status-code`, `error-code`, `pointer`, `struct`, `list`, `iterator`, `optional`, `allocated-pointer` |
| `return-flags` | Qualifiers for return value semantics. | `allocates-memory`, `nullable`, `ownership-transfer` |
| `tag-confidence` | Confidence level attached to enrichment decisions. | `high`, `medium`, `low` |
| `variable-role` | Semantic role of identifiers/locals. | `iterator`, `counter`, `flag`, `state`, `buffer-manager`, `context-pointer`, `temporary` |
| `data-kind` | Domain-specific data carried by a variable. | `transaction-id`, `snapshot`, `relation`, `buffer`, `lock`, `query`, `wal-pointer`, `lsn`, `tuple` |
| `security-sensitivity` | Marks sensitive data variables. | `credential`, `auth-token`, `secret`, `personal-data` |
| `lifetime` | Storage duration of a local variable. | `auto`, `static` |
| `mutability` | Mutability classification for locals. | `mutable`, `immutable` |
| `init-value` | Captured literal initialisation for locals. | *(initial literal or call code)* |
| `is-lock` | Flags lock/synchronisation variables. | `true` |
| `is-pointer-to-struct` | Flags pointer variables targeting structured data. | `true` |
| `field-semantic` | Semantic description of structure fields. | `visibility-bit-mask`, `xmin-creator-transaction`, `page-flag`, `ctid-tuple-pointer` |
| `field-domain` | Domain associated with structure fields. | `heap-tuple`, `heap-page`, `visibility-map`, `transaction-metadata`, `wal`, `fsm`, `general` |
| `literal-kind` | Classifies literal nodes by function. | `error-code`, `special-value`, `bit-mask`, `null-constant`, `magic-number`, `boolean-flag`, `size-constant`, `timeout`, `path-string` |
| `literal-domain` | Domain grouping for literals. | `transaction`, `visibility`, `buffer`, `lock`, `wal`, `catalog`, `error`, `general` |
| `literal-constant` | Named constant represented by a literal. | *(e.g., `InvalidBlockNumber`, `ERRCODE_SYNTAX_ERROR`)* |
| `literal-severity` | Severity classification derived from literal usage. | `error`, `warning`, `notice` |
| `is-null-constant` | Flags literals representing null/zero pointers. | `true` |
| `is-lock-constant` | Flags literals representing lock modes. | `true` |
| `is-bitmask` | Marks literals encoding bit masks. | `true` |
| `error-level` | Error level associated with literal codes. | `elog-error`, `elog-warning`, `elog-notice`, `elog-debug` |
| `literal-interpretation` | Human-readable explanation of literal meaning. | *(extracted text)* |
| `boolean-meaning` | Meaning of boolean/string literal flags. | `true`, `false`, `on`, `off` |
| `lock-mode` | Specific lock mode signified by the literal. | `AccessShareLock`, `RowShareLock`, `RowExclusiveLock`, `ShareUpdateExclusiveLock`, `ShareLock`, `ShareRowExclusiveLock`, `ExclusiveLock`, `AccessExclusiveLock` |
| `modifier-visibility` | Visibility level derived from modifiers. | `public`, `protected`, `private`, `internal` |
| `modifier-concurrency` | Concurrency implications of modifiers. | `static-volatile-global`, `volatile-access`, `atomic-access`, `thread-local`, `synchronized`, `reentrant-hint` |
| `modifier-attribute` | Additional attributes inferred from modifiers. | `const`, `final`, `readonly`, `inline`, `constexpr`, `noinline` |
| `type-category` | High-level category of a type declaration. | `struct`, `class`, `enum`, `union`, `interface`, `alias`, `typedef`, `record`, `view` |
| `type-domain-entity` | Domain entity represented by the type. | `relation`, `index`, `heap-tuple`, `buffer-desc`, `wal-record`, `catalog-entry`, `executor-state`, `configuration` |
| `member-role` | Semantic role of a structure member. | `data`, `reference`, `state`, `metadata`, `count`, `flag` |
| `member-pointer` | Flags members that are pointer fields. | `true` |
| `member-length-field` | Marks members that store length/count information. | `true` |
| `member-unit` | Unit associated with a member value. | `bytes`, `blocks`, `pages`, `tuples`, `entries`, `rows` |
| `method-ref-kind` | Classifies method references. | `callback`, `function-pointer`, `virtual-dispatch`, `signal-slot`, `interrupt-handler` |
| `method-ref-usage` | Usage intention for a method reference. | `comparator`, `predicate`, `allocator`, `cleanup`, `initializer`, `notifier` |
| `method-ref-domain` | Domain context inferred for the referenced method. | `executor`, `planner`, `storage`, `catalog`, `buffer`, `concurrency`, `wal`, `configuration` |
| `namespace-layer` | High-level layer classification for namespaces. | `planner`, `executor`, `storage`, `catalog`, `buffer`, `replication`, `utilities`, `tests` |
| `namespace-domain` | Domain context of the namespace. | `core`, `extension`, `client`, `server`, `tools`, `configuration` |
| `namespace-library-kind` | Library/component kind for the namespace. | `core`, `extension`, `test`, `utility`, `interface` |
| `namespace-scope` | Scope level inferred (global vs nested). | `global`, `nested`, `anonymous` |
| `jump-kind` | Semantic role of a jump target or label. | `loop-break`, `loop-continue`, `error-handler`, `cleanup`, `retry`, `dispatch` |
| `jump-domain` | Domain context inferred for a jump location. | `executor`, `storage`, `transaction`, `buffer`, `planner`, `utility` |
| `jump-scope` | Scope classification for jump targets/labels. | `loop`, `function`, `switch`, `global` |
| `return-outcome` | Outcome classification for RETURN nodes. | `success`, `failure`, `partial-success`, `retry`, `not-applicable` |
| `return-domain` | Domain context inferred for the return statement. | `executor`, `planner`, `storage`, `catalog`, `buffer`, `concurrency`, `wal` |
| `returns-error` | Flags return statements representing error/failure outcomes. | `true` |
| `returns-null` | Flags return statements returning null/0 pointers. | `true` |
| `type-concurrency-primitive` | Marks types that represent concurrency primitives. | `spinlock`, `mutex`, `lwlock`, `semaphore`, `condition-variable`, `latched-flag` |
| `type-ownership-model` | Ownership / lifecycle semantics for a type declaration. | `reference-counted`, `copy-on-write`, `pinned-buffer`, `stack-only`, `arena-managed` |
Related Documentation
---------------------

- `ARCHITECTURAL_LAYERS_SUCCESS.md`  Postmortem and metrics for the October9 fix.
- `SESSION_SUMMARY_2025-10-07.md`  Detailed 3h enrichment session log, including bug root cause analysis.
- `QUICK_START.md`  Platform-specific commands for running the profiles manually.
