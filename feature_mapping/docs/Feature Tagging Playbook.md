# Feature Tagging Playbook

This playbook captures the end-to-end workflow for mapping PostgreSQL features to Code Property Graph (CPG) nodes using the automated pipeline.

## 1. Preparation Checklist

- Joern 2.x installed locally (`JOERN_HOME` set, or pass `--joern-binary`).
- PostgreSQL 17 source tree available (defaults to `C:\Users\user\postgres-REL_17_6\src`).
- Prebuilt CPG for PostgreSQL 17 (`pg17_full.cpg`) registered with Joern.
- Python 3.10+ with `pip install -r requirements.txt`.
- Optional: ensure `JOERN_MAX_HEAP` is set (e.g., `-Xmx8G`) for large batch runs.

## 2. Review-First (No Mutation) Run

Generate candidates and per-feature summaries without mutating the CPG:

```powershell
python -m feature_mapping.cli `
  --dry-run `
  --skip-tagging `
  --summary-dir summaries/full-matrix `
  --batch-size 15 `
  --output full_matrix_candidates.json
```

Artifacts:
- `summaries/full-matrix/*.json` — one file per feature, capturing candidates and scores.
- `full_matrix_candidates.json` — aggregated view for dashboards or QA.

Use these files for peer review before approving tag writes.

## 3. Applying Tags After Review

Once candidates are approved, re-run without `--skip-tagging`:

```powershell
python -m feature_mapping.cli `
  --summary-dir summaries/full-matrix `
  --output full_matrix_candidates.json
```

Features already tagged will be skipped automatically. Summaries are refreshed for audit history.

## 4. Curated Feature Runs

For targeted updates, use the helper script:

```powershell
python add_feature_tags_manual.py `
  --summary-dir summaries/curated `
  --max-nodes 10 `
  --feature "Logical replication" `
  --feature "MERGE"
```

The script relies on the same pipeline controls and accepts the review flags shown above.

## 5. Resuming Interrupted Runs

If a job stops midway, resume from the last processed feature:

```powershell
python -m feature_mapping.cli `
  --resume-from "Parallel query" `
  --summary-dir summaries/full-matrix
```

The pipeline continues tagging from `Parallel query` onward, leaving previous summaries intact.

## 6. Post-Run Verification

1. Spot-check summaries in `summaries/` (diff against previous runs when possible).
2. Run the coverage reporter to identify features lacking tags:
   ```powershell
   python verify_tag_coverage.py --output coverage.json
   ```
   Inspect `coverage.json` (or the console warnings) and ensure every feature expected in scope reports `tagged_nodes > 0`.
3. Query Joern to confirm tags exist for representative features:
   ```scala
   cpg.tag.value("MERGE").file.name.l.take(20)
   cpg.file.name("src/backend/access/brin/brin.c").tag.valueExact("Feature").value.l
   ```
4. Track the total Feature tag count:
   ```scala
   cpg.tag.nameExact("Feature").size
   ```

## 7. Test Suite

Before rolling out changes:

```powershell
python -m pytest
```

The suite covers:
- Feature matrix parsing.
- Heuristic expansion and scoring.
- Pipeline smoke tests with a stub Joern client (summaries, resume, idempotent tagging).

## 8. Operational Notes

- **Runtime**: Expect ~10 minutes for the full matrix on a workstation with adequate RAM. Adjust `--batch-size` if Joern memory pressure is observed.
- **Storage**: Full summaries plus aggregated JSON typically consume <5 MB.
- **Log Review**: The pipeline logs candidate counts, filtered nodes, and tagging decisions. Capture logs alongside summaries for traceability.
- **Cleanup**: Archive the summary directory after each run; keep at least one historical copy for diffing future runs.

## 9. Rollback Plan

If a tagging run produces undesired results:
1. Restore the last-known-good `pg17_full.cpg` backup (or revert via Joern/CPG snapshots).
2. Investigate the offending feature summaries to fine-tune heuristics or overrides.
3. Re-run using `--skip-tagging` until the candidate set is satisfactory, then apply tags again.

Following this playbook ensures the feature tagging pipeline remains deterministic, auditable, and safe to operate in production environments.

## 10. Acceptance Criteria

A tagging run is considered production-ready when:

- All features in scope report at least one tagged node (`verify_tag_coverage.py` shows zero uncovered items).
- Summaries have been reviewed for the highest-risk features (new heuristics or manual overrides).
- Spot-check Joern queries confirm tags for both positive and negative control features.
- Test suite passes (`python -m pytest`) with no unexpected failures.
- A previous CPG snapshot is archived for rollback.
