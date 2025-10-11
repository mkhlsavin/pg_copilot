CPG Enrichment Suite
=====================

This directory contains the Scala scripts, batch wrappers, and operations notes used to enrich the PostgreSQL 17.6 Code Property Graph (CPG) with domain-specific metadata for downstream RAG and analytics workloads. The suite populates tags, comment nodes, and derived metrics across files, methods, and calls so that higher-level questions (“which executor functions lack tests?”, “where are the WAL entry points?”) can be answered directly from the graph.

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
| standard | minimal + `api_usage_examples.sc`, `security_patterns.sc`, `code_metrics.sc`, `extension_points.sc`, `dependency_graph.sc` | ~50–60 min | Default production profile, populates most method/file metadata. |
| full | standard + `test_coverage.sc`, `performance_hotspots.sc`, `architectural_layers.sc` (via `run_layers_final.sc`), `semantic_classification.sc` | ~90 min | Adds coverage, performance, and semantic layers. |

\*Runtimes measured on PostgreSQL 17.6 (~450 k vertices) with `JAVA_OPTS="-Xmx24G -Xms4G"`.

Script Catalog
--------------

### Core Enrichers

| Script | Target Nodes | Key Tags / Output | Status & Coverage Highlights |
|--------|--------------|-------------------|-------------------------------|
| `ast_comments.sc` | FILE, METHOD, CALL, CONTROL_STRUCTURE, TYPE_DECL, LOCAL, RETURN | Attaches existing `COMMENT` nodes to AST parents for traversal. | ~2.4 M comment associations populated (Oct 7 run). |
| `subsystem_readme.sc` | FILE | `subsystem-name`, `subsystem-path`, `subsystem-desc` sourced from README.md files. | 712 files mapped to 83 subsystems. |
| `api_usage_examples.sc` | METHOD | `api-caller-count`, `api-public`, `api-example`, `api-typical-usage`. | 14 380 APIs classified; 100 % coverage for public API detection. |
| `security_patterns.sc` | CALL | `security-risk`, `risk-severity`, `sanitization-point`, `trust-boundary`, `privilege-level`. | 4 508 risky call sites tagged; severity grading restored. |
| `code_metrics.sc` | METHOD, FILE | `cyclomatic-complexity`, `lines-of-code`, `code-smell`, `refactor-priority`, `coupling-score`. | 52 303 methods scored; high-complexity thresholds flagged. |
| `extension_points.sc` | METHOD | `extension-point`, `extensibility`, `extension-examples`. | 828 extensibility hooks annotated. |
| `dependency_graph.sc` | FILE | `module-layer`, `module-depends-on`, `module-dependents`, `circular-dependency`. | 2 254 files analysed, circular dependencies surfaced. |
| `test_coverage.sc` | METHOD | `test-coverage`, `test-count`, `tested-by`. | 51 908 methods linked to regression tests (9 % coverage gap). |
| `performance_hotspots.sc` | METHOD | `perf-hotspot`, `loop-depth`, `allocation-heavy`, `io-bound`, `expensive-op`. | 10 798 routines flagged for performance tuning. |
| `architectural_layers.sc` / `run_layers_final.sc` | FILE | `arch-layer`, `arch-layer-description`, `arch-layer-depth`, `arch-sublayer`. | Bug-fixed on 2025-10-09; 82 % (1 748 / 2 111) files classified, unknown reduced to 17 %. |
| `semantic_classification.sc` | METHOD | `function-purpose`, `data-structure`, `algorithm-class`, `domain-concept`. | 52 303 methods (100 %) semantically labelled across 30+ taxonomies. |

### Utilities & Quality Gates

- `enrich_all.sc` – Aggregates the core scripts, supports profile selection, emits coverage dashboards, and guards against double-application.
- `enrich_cpg.sh` / `enrich_cpg.ps1` – Platform-specific runners that unzip/import the workspace, configure JVM heap (24 GB default), and call `enrich_all.sc`.
- `run_layers_final.sc` – Thin wrapper that opens the Joern workspace, filters MinGW headers, normalises path separators, and re-applies architectural tags (post-bug-fix script).
- `test_cpg_quality.sc` – Scores the enriched graph (target: 96/100) by sampling comments, APIs, security flags, metrics, coverage, and layer tags.
- `impact_analyzer_prototype.sc` – Demonstrates how enrichment tags drive change-impact analysis (e.g., call graph fan-out, subsystem context, risk-aware prioritisation).

Recent Results (2025-10-09)
---------------------------

- **Architectural layers:** classification coverage improved from 7 % to 82 % (1 748 / 2 111 files) after path/regex fixes; MinGW headers excluded; unknown bucket now 17 %.
- **Semantic classification:** 52 303 methods mapped to four semantic dimensions (purpose, data structure, algorithm class, domain concept) with 100 % coverage.
- **API catalog:** 14 380 methods tagged, public API detection active, top callers instantly queryable.
- **Security patterns:** 4 508 call sites labelled with risk type, severity, trust boundaries, and sanitisation status.
- **Performance hotspots:** 10 798 routines analysed for loop depth, allocation intensity, and expensive operations.
- **Quality score:** `test_cpg_quality.sc` reports 96 / 100 when the full profile is re-applied to `pg17_full.cpg`.

Future Enhancements
-------------------

1. **Close the remaining 17 % “unknown” architectural files** – extend `LAYER_PATTERNS` to cover contrib modules and tests, or feed unknowns into a manual curation loop.
2. **Persist enrichment metrics to disk** – capture JSON/CSV outputs for CI reporting (coverage deltas, counts per tag).
3. **Automate regression checks** – wire `test_cpg_quality.sc` into the enrichment wrappers and fail the run when quality drops below the 96/100 baseline.
4. **Introduce incremental updates** – detect changed files/methods and reapply tags selectively instead of rerunning full passes.
5. **Harden `impact_analyzer_prototype.sc`** – convert the prototype into a CLI module that accepts method lists and exports markdown/JSON reports.
6. **Integrate with the RAG pipeline** – update prompt templates to exploit new tags (`arch-layer`, `function-purpose`, `security-risk`) and publish a “query cookbook”.
7. **Cross-platform packaging** – bundle JVM heap presets and Joern path discovery into a shared PowerShell/Bash module to simplify invocation.

Related Documentation
---------------------

- `ARCHITECTURAL_LAYERS_SUCCESS.md` – Postmortem and metrics for the October 9 fix.
- `SESSION_SUMMARY_2025-10-07.md` – Detailed 3 h enrichment session log, including bug root cause analysis.
- `QUICK_START.md` – Platform-specific commands for running the profiles manually.
