# Analysis & Paper Plan

This document defines the evaluation and publication workflow for RAG-CPGQL. The goal is to demonstrate the value of enrichment-aware RAG for CPGQL generation, quantify model performance, and produce a conference-ready research package.

## Purpose

- Establish statistically significant evidence of improvements delivered by semantic enrichments, LangGraph orchestration, and grammar-constrained decoding.
- Produce publication-quality figures, tables, and narrative suitable for a Tier-1 software engineering venue (ICSE/FSE/ASE).
- Release reproducible artifacts (code, data subsets, Docker package) accompanying the paper.

## Inputs and Resources

- **Datasets:** `data/train_split_merged.jsonl`, `data/test_split_merged.jsonl`, enrichment metadata exports.
- **Models:** LLMxCPG-Q (fine-tuned) and Qwen3-Coder baseline checkpoints.
- **Pipelines:** LangGraph workflow (`src/workflow/langgraph_workflow_simple.py`), grammar-constrained generator, evaluation scripts in `experiments/`.
- **Metrics:** Validity, execution success, enrichment utilization, semantic similarity, entity-level F1, runtime statistics.
- **Infrastructure:** Enriched `pg17_full.cpg`, Joern server/batch execution, ChromaDB vector store.

## Phase Overview

| Phase | Duration | Objectives | Key Deliverables |
| --- | --- | --- | --- |
| 1. Data Collection | Days 1-2 | Run benchmark suites and ablations | Raw result JSON/CSV, logs, checkpoints |
| 2. Statistical Analysis | Days 3-4 | Quantify improvements and significance | Summary tables, significance tests, effect sizes |
| 3. Enrichment Impact Study | Days 5-6 | Attribute gains to specific enrichments | Contribution matrix, error taxonomy, qualitative cases |
| 4. Paper Drafting | Days 7-10 | Write research paper and figures | 8-12 page draft, figure/table assets, bibliography |
| 5. Artifact Packaging | Day 11 | Prepare reproducibility materials | Docker image, scripts, README, archived datasets |

## Phase Details

### Phase 1 - Data Collection

- Run the 200-question benchmark for each configuration: baseline, RAG without enrichment, RAG + enrichment (base model), RAG + enrichment (LLMxCPG-Q).
- Execute enrichment ablations (individual layers and grouped features) on a 50-question subset to bound runtime.
- Capture LangGraph execution traces for a representative subset (>=10 runs) to illustrate retry behavior and answer interpretation.
- Archive raw outputs under `results/` with metadata (model version, commit hash, seeds, hardware).

### Phase 2 - Statistical Analysis

- Compute descriptive statistics (mean, median, std) for each metric across configurations.
- Apply paired tests (Wilcoxon signed-rank or paired t-test) between baseline and enriched runs; report p-values and effect sizes.
- Generate violin/box plots for validity, execution success, and semantic similarity; include runtime trade-off visuals.
- Summarize findings in a master table for direct inclusion in the paper.

### Phase 3 - Enrichment Impact Study

- Build a contribution matrix that maps question categories to enrichment layers used in successful queries.
- Perform cumulative ablation (incrementally adding enrichment layers) to show marginal gains.
- Conduct focused error analysis for failed cases: categorize by cause (tag invention, execution error, retrieval miss, enrichment gap).
- Extract qualitative exemplars (before/after enrichment) for inclusion in the discussion section.

### Phase 4 - Paper Drafting

- Paper structure: Introduction, Background, Approach, Enrichment Framework, Evaluation, Discussion, Threats to Validity, Related Work, Conclusion.
- Target length: 8-12 pages, double-column; follow the ICSE/FSE template.
- Create eight figures (architecture, workflow, evaluation charts) and six tables (datasets, metrics, ablation results, runtime, enrichment usage, threats).
- Schedule internal reviews (technical and editorial) before final polishing.

### Phase 5 - Artifact Packaging

- Prepare a Docker image (or Conda environment) that reproduces training, evaluation, and key experiments.
- Curate a smaller shareable dataset (respecting licensing) with instructions for re-running benchmark scripts.
- Publish code and artifacts to a public repo plus a Zenodo archive for DOI issuance.
- Draft the artifact evaluation checklist aligning with the target venue's guidelines.

## Supporting Tasks and Dependencies

- **Joern automation:** Execution benchmarks depend on reliable server/batch mode; coordinate with implementation tasks to ensure availability.
- **Query quality improvements:** Incorporate any prompt/enrichment updates completed during implementation before final benchmark runs.
- **Resource planning:** Secure GPU and storage quotas for multi-day runs; log reservations in the experiment tracker.
- **Documentation sync:** Ensure the README and implementation plan stay aligned with analysis deliverables.

## Communication and Checkpoints

- Daily status updates during the 11-day cycle.
- Interim sync after Phase 2 to review preliminary statistics and adjust ablation priorities.
- Final review meeting before paper submission and artifact release.

## Completion Criteria

- Benchmarks executed with reproducible configurations and archived outputs.
- Statistical significance established for key claims (p < 0.05 where applicable) with effect sizes reported.
- Enrichment impact articulated through quantitative and qualitative evidence.
- Paper draft complete, peer-reviewed, and aligned with venue requirements.
- Reproducibility package validated on a clean environment.

For implementation progress and system details, see `README.md` and `IMPLEMENTATION_PLAN.md`.
