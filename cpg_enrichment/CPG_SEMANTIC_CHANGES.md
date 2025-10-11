CPG Semantic Enrichment Summary
================================

The enrichment suite injects domain knowledge into the PostgreSQL 17.6 Code Property Graph (CPG) by attaching Tag nodes (`TAGGED_BY` edges) and, in the case of comments, ensuring that COMMENT nodes are reachable from their AST parents. This document records the semantics added by each script so that downstream tooling (RAG, quality gates, impact analysis) understands the available metadata.

File-Level Tags
---------------

| Tag Name | Source Script | Target Files | Description | Coverage Snapshot* |
|----------|---------------|--------------|-------------|--------------------|
| `subsystem-name`, `subsystem-path`, `subsystem-desc` | `subsystem_readme.sc` | Files whose directory contains a README | Associates files with subsystem documentation extracted from PostgreSQL READMEs. | 712 files mapped to 83 subsystems. |
| `module-layer` | `dependency_graph.sc` | Files grouped by dependency cluster | High-level module layer derived from include/usage analysis. | 2 254 files analysed. |
| `module-depends-on`, `module-dependents` | `dependency_graph.sc` | Files | Encodes outbound and inbound dependency lists (CSV string). | Populated where dependencies exist. |
| `circular-dependency` | `dependency_graph.sc` | Files | Marks modules that participate in circular dependency components. | Flagged wherever cycles detected. |
| `arch-layer`, `arch-layer-description`, `arch-layer-depth`, `arch-sublayer` | `architectural_layers.sc` / `run_layers_final.sc` | PostgreSQL source files (excluding MinGW/system headers) | Layer taxonomy (e.g., `query-optimizer`, `storage`) plus sublayer and depth for navigation. | 82 % of 2 111 files tagged after 2025‑10‑09 fix; 17 % remain `unknown`. |

\*Coverage numbers reflect the October 2025 full enrichment run.

Method-Level Tags
-----------------

| Tag Name | Source Script | Description | Population Highlights |
|----------|---------------|-------------|-----------------------|
| `api-caller-count` | `api_usage_examples.sc` | Number of direct call sites for a public API. | All 14 380 API entry points have counts. |
| `api-public` | `api_usage_examples.sc` | Boolean marker (`true`) for externally visible APIs. | Applied to public exports. |
| `api-example` | `api_usage_examples.sc` | Representative code snippet (trimmed) for invoking the API. | Present when usage snippet generated. |
| `api-typical-usage` | `api_usage_examples.sc` | Natural-language summary of common usage. | Populated alongside examples. |
| `cyclomatic-complexity` | `code_metrics.sc` | Integer complexity per method. | 52 303 methods scored. |
| `lines-of-code` | `code_metrics.sc` | Logical lines of code per method. | Same coverage as complexity. |
| `code-smell` | `code_metrics.sc` | One entry per detected smell (long method, deep nesting, etc.). | Applied where heuristics trigger. |
| `refactor-priority` | `code_metrics.sc` | Priority bucket (`critical`, `high`, `medium`, `low`). | Present on all methods inspected. |
| `extension-point`, `extensibility`, `extension-examples` | `extension_points.sc` | Annotates Pluggable hooks/callbacks, including prose description and examples. | 828 methods marked as extension points. |
| `test-coverage`, `test-count`, `tested-by` | `test_coverage.sc` | Coverage category (`tested`, `partial`, `untested`), number of tests, and list of regression test names (truncated to 200 chars). | 51 908 methods linked; ~9 % untested. |
| `perf-hotspot`, `loop-depth`, `allocation-heavy`, `io-bound`, `expensive-op` | `performance_hotspots.sc` | Performance diagnostics (thermal state, loop nesting depth, heavy allocation, I/O sensitivity, expensive operations encountered). | 10 798 methods labelled as `hot` or `warm`. |
| `function-purpose` | `semantic_classification.sc` | Primary functional role (e.g., `memory-management`, `statistics`). | 52 303 methods (100 %) covered. |
| `data-structure` | `semantic_classification.sc` | Dominant data structure manipulated (`linked-list`, `relation`, `hash-table`, etc.). | Multi-valued where applicable. |
| `algorithm-class` | `semantic_classification.sc` | Algorithm family (`searching`, `hashing`, `sorting`, …). | Complete coverage across methods. |
| `domain-concept` | `semantic_classification.sc` | PostgreSQL domain tags (`replication`, `mvcc`, `extension`, etc.). | Full coverage. |

Call-Level Tags
---------------

| Tag Name | Source Script | Description | Notes |
|----------|---------------|-------------|-------|
| `security-risk` | `security_patterns.sc` | Risk classification (e.g., `sql-injection`, `format-string`, `buffer-overflow`). | Derived from pattern detection and taint analysis heuristics. |
| `risk-severity` | `security_patterns.sc` | Severity bucket (`critical`, `high`, `medium`, `low`). | Aligned with security checklist heuristics. |
| `sanitization-point` | `security_patterns.sc` | Sanitisation status (`none`, `validated`, `escaped`, etc.). | Helps auditors confirm mitigations. |
| `trust-boundary` | `security_patterns.sc` | Boundary crossed (`user-input`, `network`, `filesystem`, …). | Highlights entry points crossing untrusted domains. |
| `privilege-level` | `security_patterns.sc` | Execution privilege context (e.g., `superuser`, `replication`). | Aids privilege escalation reviews. |

Comment Attachments
-------------------

- `ast_comments.sc` walks AST parents (files, methods, calls, control structures, locals, returns, type declarations) and ensures COMMENT nodes are linked via `_astOut`. No new tags are created; existing comments become reachable through standard traversals.

Additional Artefacts
--------------------

- `impact_analyzer_prototype.sc` consumes the tags above (especially `function-purpose`, `arch-layer`, `security-risk`, and `perf-hotspot`) to assemble change-impact reports. It does not create new graph elements.
- `test_cpg_quality.sc` reads enrichment tags to compute a quality score; it likewise leaves the CPG untouched.

Implementation Notes
--------------------

- All tag writers use `NewTag()` and attach via `EdgeTypes.TAGGED_BY`, ensuring compatibility with Joern augmentation directives (`run.commit` inside each script).
- Architectural scripts normalise file paths (`replace('\\', '/')`) and exclude MinGW/system headers before tagging.
- Scripts are idempotent: rerunning an enrichment first removes stale tags for the given key before adding fresh values (see individual script implementations).

Refer to the source `.sc` files for exact heuristics, thresholds, and diff-handling logic when extending or debugging the enrichment suite.
