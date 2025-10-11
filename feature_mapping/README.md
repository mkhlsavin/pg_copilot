PostgreSQL 17 Feature Mapping Toolkit
=====================================

This package implements the workflow described in
`docs/Mapping PostgreSQL 17 Features to Code Graph Nodes.md`. It:

- downloads the official PostgreSQL 17 feature matrix,
- expands each feature name into a reusable set of search heuristics,
- queries a Joern-generated Code Property Graph (CPG) for candidate nodes,
- and, when requested, writes `Feature` tags back into the CPG to provide bidirectional traceability.

Workstation defaults
--------------------

- PostgreSQL sources: `C:\Users\user\postgres-REL_17_6\src`
- Joern installation: `C:\Users\user\joern`
- Prebuilt CPG: `C:\Users\user\joern\workspace\pg17_full.cpg`

The CLI warns whenever one of these resources is missing and every path can be overridden.

Prerequisites
-------------

- Python 3.10 or newer (validated with 3.13.5)
- Joern 2.x installed locally
- A PostgreSQL 17 CPG exported as `pg17_full.cpg`
- Internet access to fetch the feature matrix (or supply `--feature-matrix-url` pointing to an offline copy)

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Architecture
------------

The `feature_mapping` package mirrors the phases of the mapping algorithm.

1. **Configuration bootstrap (`feature_mapping/config.py`)**
   - Discovers Joern binaries and validates the presence of PostgreSQL sources and the CPG.
   - Exposes defaults while permitting CLI overrides.

2. **Feature acquisition (`feature_mapping/feature_matrix.py`)**
   - Downloads and parses the PostgreSQL feature matrix.
   - Normalises feature data (name, category, description, detail URL).
   - Keeps only rows marked as available in version 17 (`fm_yes` or `fm_obs`).

3. **Heuristic enrichment (`feature_mapping/heuristics.py`)**
   - Tokenises feature names, removes stop words, and injects synonyms or category hints (for example, `Logical replication` becomes tokens such as `logical`, `replication`, `wal`).
   - Supplies scoring helpers that compare tokens against identifier text and filenames.

4. **Joern integration (`feature_mapping/joern_client.py`)**
   - Wraps Joern CLI execution and automatically runs `clearCpg` followed by `importCpg` for `pg17_full.cpg`.
   - Generates Scala traversals that query files, methods, type declarations, and (optionally) call sites / namespaces with conjunctive token matching and directory hints.
   - Parses Joern output into structured `CandidateNode` objects, supports retry/backoff, and batches `Feature` tag creation.

5. **Pipeline orchestration (`feature_mapping/pipeline.py`)**
   - Coordinates feature processing, heuristic expansion, Joern candidate searches, score filtering, and optional tagging.
   - Provides configuration for score thresholds, candidate caps, batching, resume markers, review summaries, and skip-tagging behaviour to keep reruns idempotent.

6. **Command-line interface (`feature_mapping/cli.py`)**
   - Offers logging, feature filtering, JSON export, dry-run controls, review-first options (summaries, skip-tagging), and resume markers.
   - Defaults to local paths but accepts overrides for the Joern binary, CPG, and feature matrix source.

Data flow summary
-----------------

```
fetch_feature_matrix()                     # Feature list
        |
FeatureMappingPipeline.map_feature()       # Token expansion and hints
        |
JoernClient.find_candidates()              # Scala traversal executed by Joern
        |
Candidate scoring and filtering            # Heuristic ranking
        |
FeatureMappingPipeline.apply_tags()        # Optional (skipped in dry-run)
```

Usage
-----

### Review-first run (no graph mutations, summaries only)

```powershell
python -m feature_mapping.cli --dry-run --skip-tagging --summary-dir summaries
```

- Collects candidates for every feature without touching the CPG.
- Writes one JSON file per feature into `summaries/` for human review.
- Combine with `--feature` / `--feature-file` to narrow the review scope.

### Dry-run (no graph mutations)

```powershell
python -m feature_mapping.cli --dry-run --output mappings.json
```

- Produces `mappings.json` containing candidate nodes and heuristic scores for every feature.
- Ideal for reviewing matches before modifying the CPG.

### Persist feature tags

```powershell
python -m feature_mapping.cli --output mappings.json --summary-dir summaries
```

- Applies `Feature` tags to the CPG (skipping nodes that are already tagged) and still writes:
  - `mappings.json` containing the aggregated candidate data.
  - per-feature summary files under `summaries/` for audit trails.
- Inspect the enriched graph inside Joern:

```scala
cpg.tag.value("MERGE SQL command").file.name.l
cpg.file.name("auth.c").tag.value.l
```

### Limit execution to selected features

```powershell
python -m feature_mapping.cli --dry-run --feature "MERGE SQL command" --feature "Logical replication"
```

Provide a newline-delimited list via `--feature-file` for larger batches.

### Resume a long run

If a run is interrupted, resume from the feature that was last processed:

```powershell
python -m feature_mapping.cli --resume-from "Parallel query" --summary-dir summaries
```

The pipeline skips all earlier features, loads previously written summaries, and continues tagging where it left off.

### Override defaults

- `--feature-matrix-url` targets an offline HTML copy of the matrix.
- `--joern-binary` and `--cpg` allow testing alternative Joern installations or graphs.
- `--score-threshold`, `--max-nodes`, `--max-per-kind`, and `--max-candidates-total` tune the matching sensitivity.
- `--include-calls` / `--include-namespaces` broaden candidate search to additional node kinds.
- `--batch-size` controls how many features are processed per Joern invocation batch.
- `--skip-tagging` keeps the run read-only while still producing summaries.

### Curated feature tagging

The helper script `add_feature_tags_manual.py` now delegates to the pipeline for a curated list of high-impact features:

```powershell
python add_feature_tags_manual.py --summary-dir curated_summaries
```

You may supply additional `--feature` arguments to extend the curated list, or reuse the new review/skip flags documented above.

### Coverage report

Generate a coverage snapshot showing how many nodes are tagged for each feature:

```powershell
python verify_tag_coverage.py --output coverage.json
```

- Reports features lacking tags and totals across the selection.
- Works with the full matrix or any subset supplied via `--feature` / `--feature-file`.
- Optional JSON export makes it easy to chart coverage over time.

### Test suite

Run unit tests (parsers, heuristics, pipeline smoke tests) via:

```powershell
python -m pytest
```

The tests rely on fixture snapshots under `tests/fixtures/` and stub Joern clients, so they do not require a live CPG.

Usage scenarios
---------------

- **Developer onboarding:** map feature names to concrete files and functions to accelerate ramp-up.
- **Security and compliance audits:** filter security-related features and inspect the associated code paths systematically.
- **Documentation and RAG:** feed `mappings.json` into documentation generators or retrieval-augmented assistants for instant answers such as “where is feature X implemented?”
- **Impact analysis:** before enhancing or deprecating a feature, enumerate tagged nodes to understand the change surface.
- **Incident response:** during regressions, traverse from the affected feature to tagged nodes to isolate likely culprits quickly.

Operational considerations
--------------------------

- **Runtime:** Full-matrix tagging (~394 features) takes several minutes depending on Joern database cache warm-up and the size of the summary directory. Use `--batch-size` to match available CPU/RAM.
- **Joern settings:** Ensure Joern has sufficient heap (e.g., `JOERN_MAX_HEAP=8G`) when running full-matrix jobs; the pipeline will retry transient CLI failures automatically.
- **Storage:** Expect roughly 2–3 MB of JSON across `mappings.json` plus per-feature summaries after a full run.
- **Review workflow:** Keep summary directories under version control or artifact storage to review changes over time before pushing tags to production CPGs.

Future improvements
-------------------

1. **Richer heuristics:** add trigram or embedding-based similarity and use feature descriptions to capture terminology missing from identifiers.
2. **Incremental runs:** cache candidate sets per feature and re-query Joern only when the CPG or feature list changes.
3. **Interactive review:** build a TUI or GUI to accept or reject candidates before tagging, preserving reviewer decisions.
4. **Expanded node coverage:** extend the Scala script to include comments, literals, and configuration files.
5. **Metrics and reporting:** generate dashboards highlighting unmapped features, heavily shared modules, or score distributions.
6. **Documentation export:** automatically produce Markdown or HTML reports per feature linking descriptions to tagged code for internal portals or onboarding packs.

By iterating on these enhancements the toolkit can evolve from an automated bootstrapper into a continuously curated traceability system that benefits engineering, security, documentation, and operations stakeholders.
