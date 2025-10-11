# Implementation Plan: Comprehensive Feature Tag Coverage

## Objectives
- Replace the current manual tagging workaround with an automated workflow that handles **all PostgreSQL features listed in the official matrix**.
- Preserve the ability to run targeted subsets (for testing or incremental adoption) while making it trivial to generate tags for every feature in a single run.
- Ensure the resulting feature tags remain queryable in Joern and consumable by downstream RAG components.

## Current State Recap
- `feature_matrix.py` already parses the public matrix and yields ~400 feature entries for v17.
- `pipeline.py` and `joern_client.py` provide an automated path to score and tag candidates, but they were tuned for experiments on a handful of features and rely on simplistic heuristics.
- `add_feature_tags_manual.py` hard-codes 9 features with cpgqls_client queries; this script cannot scale to the full matrix and duplicates logic that should live in the pipeline.
- Tagging output is logged but not persisted for auditing beyond ad-hoc JSON exports.

## Workstream 1 – Matrix Ingestion & Baselines
- [x] **Verify parser coverage** by running `fetch_feature_matrix()` against the live matrix and counting results; adjust `SUPPORTED_CLASSES` or version detection if any v17 entries are missed (e.g., clarify handling of `fm_new`/`fm_dev` if they appear).  
  _Status:_ Confirmed 394 v17 features via script; broadened `SUPPORTED_CLASSES` to accept future `fm_new`/`fm_dev` statuses.
- [x] **Normalise feature naming** (e.g., strip trailing whitespace, drop footnote markers) so downstream tokenisation is stable.  
  _Status:_ Added whitespace + footnote scrubbing helpers in `feature_matrix.py` and applied them to names, categories, and descriptions.
- [x] **Persist raw matrix snapshot** optionally (CSV/JSON) to enable reproducible runs or offline analysis if network access is restricted.  
  _Status:_ `cli.py` now supports `--matrix-output` to write the fetched feature list (via `Feature.to_dict()`).

## Workstream 2 – Token & Heuristic Enhancements
- [x] Expand `DEFAULT_STOPWORDS`, `SYNONYM_MAP`, and `CATEGORY_HINT_TOKENS` in `heuristics.py` to handle categories beyond the current focus (e.g., `Backup`, `Monitoring`, `Data Types`, `Partitioning`, `SQL features`).  
  _Status:_ Added broader stopword coverage and new synonyms/category hint mappings for monitoring, backup, FDW, etc.
- [x] Introduce **description-driven tokens**: leverage `Feature.description` strings when present, extracting nouns/verbs to widen search coverage.  
  _Status:_ `Feature.tokens()` now optionally folds in description-derived tokens with a configurable cap.
- [x] Add **feature-specific overrides** (YAML/JSON map) for edge cases where generic tokenisation fails (e.g., short names like "FDW API" or acronyms).  
  _Status:_ Created `feature_overrides.json` and loader utilities to inject custom tokens/stopwords/directory hints.
- [x] Update scoring (`score_text`) to consider partial matches in file paths (e.g., directory names) with tunable weights, reducing false negatives for deeply nested files.  
  _Status:_ Introduced `score_path` and wired it into Joern candidate scoring.

## Workstream 3 – Joern Integration Scalability
- [x] Modify `_build_candidate_script` to:
  - Query additional node kinds (e.g., `call`, `namespaceBlock`) behind flags to capture procedural code where filenames don't match tokens.
  - Accept a **per-feature max nodes** cap and honour it server-side to avoid transferring hundreds of low-quality candidates.  
  _Status:_ Script now honours `max_total_results` and conditionally emits `call`/`namespaceBlock` nodes via CLI flags (`--include-calls`, `--include-namespaces`).
- [x] Implement **batched execution** in `FeatureMappingPipeline.run` (e.g., process features in groups, optionally with concurrency limits) so Joern invocations do not monopolise resources.  
  _Status:_ Pipeline iterates in configurable batches (`batch_size`) with progress logging per slice.
- [x] Surface clearer telemetry (timings, candidate counts, rejection reasons) to the logger for large runs.  
  _Status:_ Added per-feature timing logs plus filter summaries and threshold guidance.
- [x] Harden `JoernClient.run_script`:
  - Retry transient Joern failures with exponential backoff.
  - Propagate stderr context into `JoernClientError` for easier debugging when a specific feature script fails.  
  _Status:_ `JoernClient` now retries with exponential backoff, structured warnings, and enriched failure messages.

## Workstream 4 – Tag Application & Outputs
- [x] Replace the manual script with pipeline-driven tagging; deprecate or rewrite `add_feature_tags_manual.py` to call into `FeatureMappingPipeline` for curated runs.  
  _Status:_ Script now bootstraps the pipeline for curated features, exposing the same configuration knobs as the CLI.
- [x] Enhance `FeatureMappingPipeline.apply_tags` to:  
   - Skip already-tagged node/feature pairs (requires a pre-flight query) to support reruns without duplication.  
   - Write per-feature JSON summaries (file, node type, score) into a configurable output directory for auditing.  
  _Status:_ `apply_tags` filters existing Feature tags via Joern, while `_write_summary` emits JSON artefacts when `summary_output_dir` is set.
- [x] Add a CLI flag (`--resume-from` / `--skip-tagging`) to enable long-running bulk runs to recover from interruptions.  
  _Status:_ CLI (and helper script) accept new flags for resume markers, skip-tagging, and summary output directories.
- [x] Optionally integrate a **dry-run review mode** that emits candidate CSV/Markdown for human approval before mutating the CPG.  
  _Status:_ Combination of `--skip-tagging` plus JSON summaries provides a review-first workflow; summaries are stored per feature in the configured directory.

## Workstream 5 – Validation & Quality Gates
- [x] Develop unit tests for:
   - HTML parsing edge cases in `feature_matrix.py`.
   - Token expansion and scoring functions in `heuristics.py`, including new synonym/description logic.  
  _Status:_ Added `tests/test_feature_matrix.py` with archived fixtures plus `tests/test_heuristics.py` covering tokenisation, synonym expansion, scoring, and overrides.
- [x] Add an integration smoke test (can run against a fixture CPG) that executes the pipeline for a tiny curated list and asserts deterministic tagging output.  
  _Status:_ Implemented `tests/test_pipeline_smoke.py` with a stub Joern client to validate batching, resume, summaries, and idempotent tagging without requiring a real CPG.
- [x] Author verification scripts (possibly using cpgqls_client) to confirm that every feature in the matrix now has at least one tag, producing coverage statistics (e.g., histogram of tag counts per feature).  
  _Status:_ Added `verify_tag_coverage.py`, plus `JoernClient.feature_tag_counts()` and coverage parsing tests; script outputs JSON/console warnings for uncovered features.
- [x] Document manual acceptance criteria: review sampling guidelines, thresholds for acceptable false positives, and rollback steps if Joern tagging corrupts the CPG.  
  _Status:_ Playbook now codifies verification steps (coverage report, spot checks, tests) and enumerates acceptance criteria prior to production runs.

## Workstream 6 – Documentation & Ops
- [x] Update `README.md` and `docs/Mapping PostgreSQL 17 Features to Code Graph Nodes.md` with the automated workflow, expected runtime, and new CLI flags.  
  _Status:_ README now documents review-first runs, summaries, resume markers, curated script usage, and operational considerations; the mapping doc highlights idempotent tagging and testing strategy.
- [x] Produce a new `docs/Feature Tagging Playbook.md` (or equivalent section in README) describing how to run full-matrix tagging, inspect output artefacts, and recover from partial runs.  
  _Status:_ Added dedicated playbook detailing preparation, review-first runs, tagging, resume flow, verification, and rollback.
- [x] Capture infrastructure requirements (Joern heap size, expected runtime for 400 features) so operators can provision adequate resources.  
  _Status:_ README’s operational considerations now call out runtime expectations, Joern heap sizing, and storage footprints.
- [x] Record change log entries in `FEATURE_TAGGING_RESULTS.md` to reflect the expanded coverage, methodology updates, and any observed metrics (e.g., total tags created).  
  _Status:_ Results document notes the migration to the automated pipeline and summarises key code/documentation updates from 2025-10-12.

## Deliverables & Exit Criteria
- Automated CLI run that tags all official features without manual intervention, with documented runtime characteristics.
- Comprehensive heuristics that achieve acceptable precision/recall (target benchmarks to be defined with stakeholders).
- Tests covering parsing and heuristics, plus smoke tests for pipeline execution.
- Updated documentation and operational guidelines for full-matrix tagging.
- Sunset (or documented replacement of) the manual tagging script.
