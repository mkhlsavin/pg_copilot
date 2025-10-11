# RAG-CPGQL Quick Start Guide v2.0

## Current Status (Updated 2025-10-08)

✅ **Phase 1 Complete: Infrastructure Ready**

### What's Ready:

1. **Merged Dataset: 27,243 QA Pairs**
   - Hackers dataset: 10,101 pairs (PostgreSQL developer mailing lists)
   - PG Books dataset: 17,142 pairs (source code comments)
   - Train/Test split: 23,156 / 4,087 (85% / 15%)
   - Files: `data/train_split_merged.jsonl`, `data/test_split_merged.jsonl`

2. **Enriched CPG: 479 MB (Quality Score: 96/100)**
   - Location: `C:/Users/user/joern/workspace/pg17_full.cpg`
   - 11 enrichment layers applied:
     - Comments (12.6M comments)
     - Subsystem Documentation (83 subsystems)
     - API Usage Examples (14,380 APIs)
     - Security Patterns (4,508 risks)
     - Code Metrics (52K methods)
     - Extension Points (828 points)
     - Dependency Graph
     - Test Coverage (9% coverage)
     - Performance Hotspots (10,798 paths)
     - Semantic Classification (4 dimensions)
     - Architectural Layers (16 layers)

3. **Updated Prompts: Enrichment-Aware v2.0**
   - System prompt includes all 11 enrichment layers
   - 5 enrichment query pattern examples
   - Tag-based filtering instructions

4. **Configuration: Updated for Merged Dataset**
   - Points to merged train/test splits
   - Increased query timeout (60s for complex enrichment queries)
   - Ready for both fine-tuned and base models

## Quick Test (5 minutes)

### 1. Test Pipeline Components

```bash
cd C:/Users/user/pg_copilot/rag_cpgql
python test_pipeline_simple.py
```

This will verify:
- ✓ Data loading (27,243 QA pairs)
- ✓ Vector store initialization
- ✓ Joern server connection (enriched CPG)
- ✓ LLM model loading (fine-tuned 32B model)

Expected output:
```
ALL TESTS PASSED!
Pipeline components are ready:
  [OK] Data: 23,156 train + 4,087 test = 27,243 total QA pairs
  [OK] Vector Store: Initialized with embedding model
  [OK] Joern: Connected to enriched CPG (Quality: 96/100)
  [OK] LLM: Fine-tuned model loaded
```

### 2. Run Quick Experiment (2 examples)

```bash
cd experiments
python run_experiment.py --model finetuned --limit 2
```

This will:
1. Load 2 test questions
2. Retrieve similar QA pairs and CPGQL examples
3. Generate enrichment-aware CPGQL queries
4. Execute queries against enriched CPG
5. Interpret results using LLM
6. Evaluate against reference answers

Expected time: ~5 minutes

### 3. Run Small Test (20 examples)

```bash
python run_experiment.py --model finetuned --limit 20
```

Expected time: ~20-30 minutes
Output: `results/rag_finetuned_results.json`

## Full Experiment (Follow IMPLEMENTATION_PLAN.md)

### Experiment 1: RAG + Enriched CPG (Fine-tuned Model)

```bash
cd experiments
python run_experiment.py --model finetuned
```

- Test size: 4,087 examples
- Expected time: ~8-10 hours
- Output: `results/rag_finetuned_results.json`

### Experiment 2: RAG + Enriched CPG (Base Model)

```bash
python run_experiment.py --model base
```

- Test size: 4,087 examples
- Expected time: ~8-10 hours
- Output: `results/rag_base_results.json`

### Experiment 3: Compare Both Models

```bash
python run_experiment.py --model both
```

This will run both experiments sequentially.

## Monitoring Progress

During experiments, monitor:

1. **Query Validity Rate**: % of syntactically valid CPGQL queries
   - Target: >80%

2. **Execution Success Rate**: % of queries that execute without errors
   - Target: >70%

3. **Semantic Similarity**: Cosine similarity between generated and reference answers
   - Target: >0.6

4. **Enrichment Utilization**: % of queries using enrichment tags
   - Target: >50%

## Expected Results (from IMPLEMENTATION_PLAN.md)

### Key Metrics:

| Metric | Target | Notes |
|--------|--------|-------|
| Query Validity Rate | >80% | Syntactically correct CPGQL |
| Execution Success Rate | >70% | Queries execute without errors |
| Semantic Similarity | >0.6 | Answer quality vs reference |
| Enrichment Utilization | >50% | Queries use enrichment tags |
| Overall F1 | >0.7 | Entity precision/recall |

### Research Questions:

1. **Does fine-tuning improve CPGQL generation?**
   - Compare fine-tuned vs base model metrics
   - Statistical significance (p < 0.05)

2. **Do enrichments improve answer quality?**
   - Compare enrichment-aware vs plain queries
   - Measure enrichment utilization rate

3. **Which enrichments help which question types?**
   - Build question-enrichment correlation matrix
   - Identify most valuable enrichments

## Next Steps (After Experiments)

1. **Analyze Results**
   - Compare fine-tuned vs base model
   - Statistical significance testing
   - Enrichment impact analysis

2. **Ablation Study**
   - Test individual enrichment contributions
   - Build enrichment correlation matrix

3. **Advanced Use Cases** (Optional)
   - Patch review system
   - Security audit queries
   - Refactoring assistant

4. **Write Research Paper**
   - Document methodology
   - Present results and findings
   - Discuss enrichment framework

## Troubleshooting

### Joern Server Issues
- Check CPG exists: `ls C:/Users/user/joern/workspace/pg17_full.cpg`
- Increase wait time in test script if server startup is slow
- Check port 8080 is not in use: `netstat -ano | findstr :8080`

### Model Loading Issues
- Ensure model exists: `ls C:/Users/user/.lmstudio/models/llmxcpg/LLMxCPG-Q/`
- Check available VRAM: 24GB+ recommended for 32B model
- Try reducing `n_gpu_layers` if OOM errors occur

### Memory Issues
- Close other applications
- Reduce batch size in config.yaml
- Limit test examples with `--limit N`

## Files Created

```
rag_cpgql/
├── merge_datasets.py                    # [NEW] Dataset merger
├── test_pipeline_simple.py              # [NEW] Quick test script
├── QUICKSTART_v2.md                     # [NEW] This guide
├── data/
│   ├── train_split_merged.jsonl         # [NEW] 23,156 pairs
│   ├── test_split_merged.jsonl          # [NEW] 4,087 pairs
│   ├── all_qa_merged.jsonl              # [NEW] 27,243 pairs
│   └── dataset_merge_report.json        # [NEW] Merge statistics
├── config.yaml                          # [UPDATED] Points to merged data
└── src/generation/prompts.py            # [UPDATED] Enrichment-aware v2.0
```

## Summary

**Ready to start experiments!**

1. ✅ Datasets merged: 27,243 QA pairs
2. ✅ CPG enriched: 96/100 quality score
3. ✅ Prompts updated: Enrichment-aware v2.0
4. ✅ Configuration ready: Points to correct files
5. ✅ Test script ready: Verify all components

**Next action:** Run `python test_pipeline_simple.py` to verify everything works.

---

**Last Updated:** 2025-10-08
**Version:** 2.0
**Status:** Ready for Testing ✅
