# RAG-CPGQL Quick Start Guide

## What We Built

A complete **RAG-based CPGQL query generation system** for PostgreSQL 17.6 source code analysis.

### System Components

✅ **Data Preparation** (1,328 Q&A pairs → 1,128 train / 200 test)
✅ **Vector Store** (ChromaDB with sentence-transformers)
✅ **LLM Interface** (llama-cpp-python with GPU support)
✅ **Joern Client** (HTTP API integration)
✅ **CPGQL Generation** (RAG with few-shot prompting)
✅ **Query Validation** (Syntax and safety checks)
✅ **Answer Interpretation** (LLM-based result interpretation)
✅ **Evaluation Framework** (Semantic similarity + Entity F1)
✅ **Experiment Runner** (Compare fine-tuned vs base models)

## Quick Test (No Joern Required)

Test the pipeline components without running full experiments:

```bash
cd C:/Users/user/pg_copilot/rag_cpgql

# 1. Verify data preparation
python prepare_data.py

# 2. Test vector store (no LLM needed)
python -c "
import sys; sys.path.insert(0, 'src')
from utils.config import load_config
from utils.data_loader import load_qa_pairs, load_cpgql_examples
from retrieval.vector_store import VectorStore

config = load_config()
train_data = load_qa_pairs(config.train_split)
cpgql_examples = load_cpgql_examples(config.cpgql_examples)

vs = VectorStore()
vs.create_qa_index(train_data[:100])  # Test with 100 examples
vs.create_cpgql_index(cpgql_examples[:100])

print('Vector store test passed!')
print(vs.get_stats())
"
```

## Full Pipeline Test (Requires GPU + Joern)

### Prerequisites
1. **GPU with 24GB+ VRAM** (for 32B model)
2. **Joern server running** at `localhost:8080`
3. **Models downloaded** (paths in config.yaml)

### Step 1: Start Joern (if not running)

```bash
# Check if Joern is already running
curl http://localhost:8080/ 2>/dev/null && echo "Joern is running" || echo "Joern not running"

# If not running, start it manually:
cd C:/Users/user/joern/joern-cli/src/universal
./joern --server --server-port 8080 --cpg C:/Users/user/joern/workspace/postgres-REL_17_6
```

### Step 2: Run Quick Test (5 examples)

```bash
cd C:/Users/user/pg_copilot/rag_cpgql/experiments

# Test fine-tuned model with 5 examples
python run_experiment.py --model finetuned --limit 5 --no-joern
```

Expected output:
```
============================================================
RAG-CPGQL EXPERIMENTS
============================================================
Loading test data... Loaded 200 test examples
Loading training data... Loaded 1128 training examples
...
Processing 1/5
...
RESULTS SUMMARY
============================================================
Model: LLMxCPG-Q-32B
Total Questions: 5
Query Validity Rate: 80.00%
Execution Success Rate: 60.00%
Avg Semantic Similarity: 0.650
Avg Overall F1: 0.550
```

### Step 3: Run Full Experiments

```bash
# Compare both models on 200 test examples
python run_experiment.py --model both --no-joern
```

This will:
1. Load 1,128 training examples into vector store
2. Run fine-tuned model on 200 test examples
3. Run base model on same 200 test examples
4. Save results to `results/` directory

**Expected Runtime:**
- ~2-3 hours for 200 examples with 32B model
- ~30 seconds per question (generation + execution + interpretation)

## Interpreting Results

### Results Files

After experiments, check:
```bash
cat results/rag_finetuned_results.json | jq '.aggregate_metrics'
cat results/rag_base_results.json | jq '.aggregate_metrics'
```

### Key Metrics

**Query Validity Rate** - Should be > 80%
**Execution Success Rate** - Should be > 70%
**Semantic Similarity** - Should be > 0.6
**Overall F1** - Should be > 0.5

### Example Result Entry

```json
{
  "question": "How does PostgreSQL validate transaction IDs?",
  "cpgql_query": "cpg.call.name('TransactionIdIsValid').l",
  "query_valid": true,
  "execution_result": {"success": true, "results": [...]},
  "generated_answer": "PostgreSQL validates transaction IDs using...",
  "metrics": {
    "semantic_similarity": 0.87,
    "overall_f1": 0.75,
    "entity_metrics": {
      "functions": {"precision": 0.8, "recall": 0.7, "f1": 0.75}
    }
  }
}
```

## Statistical Comparison

Compare fine-tuned vs base model performance:

```python
import json
from scipy.stats import wilcoxon

# Load results
with open('results/rag_finetuned_results.json') as f:
    finetuned = json.load(f)

with open('results/rag_base_results.json') as f:
    base = json.load(f)

# Extract semantic similarity scores
ft_scores = [r['metrics']['semantic_similarity']
             for r in finetuned['detailed_results']]
base_scores = [r['metrics']['semantic_similarity']
               for r in base['detailed_results']]

# Wilcoxon signed-rank test
statistic, p_value = wilcoxon(ft_scores, base_scores)

print(f"p-value: {p_value}")
print(f"Significant: {p_value < 0.05}")
```

## Troubleshooting

### Issue: Model OOM (Out of Memory)

**Solution:** Reduce GPU layers in `config.yaml`:
```yaml
llm:
  n_gpu_layers: 35  # Instead of -1 (all layers)
```

### Issue: Joern Connection Failed

**Solution:** Verify Joern is running:
```bash
curl http://localhost:8080/
# Should return 404 (means server is up)
```

### Issue: Query Validity Rate < 50%

**Possible causes:**
1. Model not understanding CPGQL syntax → Check few-shot examples
2. JSON parsing issues → Check prompt format
3. Model hallucinating → Reduce temperature

**Fix:** Adjust prompt in `src/generation/prompts.py`

### Issue: Execution Success Rate Low

**Possible causes:**
1. Queries are syntactically valid but semantically wrong
2. CPG doesn't contain expected nodes
3. Query timeout (30s default)

**Fix:** Increase timeout in `config.yaml`:
```yaml
joern:
  query_timeout: 60  # Increase to 60 seconds
```

## Next Steps for Research Paper

1. **Run full experiments** on 200 test examples
2. **Compute statistics** (mean, std, median, p-value)
3. **Error analysis** - Categorize failures:
   - Syntax errors
   - Execution timeouts
   - Semantic mismatches
4. **Ablation study** - Test without RAG (just examples, no Q&A retrieval)
5. **Visualizations** - Create plots for paper

### Suggested Visualizations

```python
import matplotlib.pyplot as plt
import numpy as np

# Load results
# ... (load finetuned and base results)

# Plot semantic similarity distribution
fig, ax = plt.subplots(1, 2, figsize=(12, 5))

ax[0].hist(ft_scores, bins=20, alpha=0.7, label='Fine-tuned')
ax[0].hist(base_scores, bins=20, alpha=0.7, label='Base')
ax[0].set_xlabel('Semantic Similarity')
ax[0].set_ylabel('Frequency')
ax[0].legend()
ax[0].set_title('Semantic Similarity Distribution')

# Box plot comparison
ax[1].boxplot([ft_scores, base_scores], labels=['Fine-tuned', 'Base'])
ax[1].set_ylabel('Semantic Similarity')
ax[1].set_title('Model Comparison')

plt.tight_layout()
plt.savefig('results/comparison.png', dpi=300)
```

## Files Summary

**Implementation:** 21 Python files (2,000+ LOC)
**Documentation:** README.md, IMPLEMENTATION_PLAN.md, QUICKSTART.md
**Configuration:** config.yaml, requirements.txt
**Data:** 1,328 Q&A pairs, 5,361 CPGQL examples
**Models:** 2 models (32B fine-tuned, 30B base)

Total project size: ~50MB (excluding models and data)
