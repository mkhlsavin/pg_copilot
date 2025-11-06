# Evaluation Module

This module implements comprehensive evaluation metrics for the RAG-CPGQL system, including RAGAS (Retrieval Augmented Generation Assessment) framework integration.

## Overview

The evaluation system assesses multiple dimensions of the RAG pipeline:

```
Generated Output → Metrics Computation → RAGAS Evaluation → Quality Scores
```

## Purpose

Quantitatively measure system performance across:
- **Generation Quality**: Query validity, syntax correctness
- **Retrieval Quality**: Context relevance, precision, recall
- **Execution Quality**: Success rate, correctness
- **End-to-End Quality**: Answer faithfulness, relevance

## Components

### 1. Metrics Module (`metrics.py`)

**Purpose**: Core metrics computation for query generation and execution.

**Implemented Metrics**:

#### Generation Metrics

**1. Validity Rate**
```python
def validity_rate(results):
    """Percentage of syntactically valid CPGQL queries"""
    valid = sum(1 for r in results if r['valid'])
    return valid / len(results)
```
- **Target**: >95%
- **Current**: 97.5% (200-question benchmark)

**2. Syntax Error Rate**
```python
def syntax_error_rate(results):
    """Percentage of queries with syntax errors"""
    errors = sum(1 for r in results if r.get('syntax_error'))
    return errors / len(results)
```
- **Target**: <5%
- **Current**: 2.5%

#### Execution Metrics

**3. Execution Success Rate**
```python
def execution_success_rate(results):
    """Percentage of valid queries that execute successfully"""
    valid = [r for r in results if r['valid']]
    success = sum(1 for r in valid if r['execution_success'])
    return success / len(valid) if valid else 0
```
- **Target**: >80%
- **Current**: 86.7% (30-question enrichment suite)

**4. Empty Result Rate**
```python
def empty_result_rate(results):
    """Percentage of successful queries returning empty results"""
    success = [r for r in results if r['execution_success']]
    empty = sum(1 for r in success if not r['output'])
    return empty / len(success) if success else 0
```
- **Target**: <20%
- **Current**: 14.3%

#### Enrichment Metrics

**5. Enrichment Coverage**
```python
def enrichment_coverage(results):
    """Percentage of queries using enrichment layers"""
    enriched = sum(1 for r in results if r.get('enrichments_used'))
    return enriched / len(results)
```
- **Target**: >60%
- **Current**: 62.2%

**6. Tag Effectiveness**
```python
def tag_effectiveness(results):
    """Success rate for queries using semantic tags"""
    tag_queries = [r for r in results if r.get('uses_tags')]
    success = sum(1 for r in tag_queries if r['execution_success'])
    return success / len(tag_queries) if tag_queries else 0
```
- **Current**: 89.4%

#### Retrieval Metrics

**7. Context Precision**
```python
def context_precision(retrieved, relevant):
    """Precision of retrieved context"""
    relevant_retrieved = set(retrieved) & set(relevant)
    return len(relevant_retrieved) / len(retrieved) if retrieved else 0
```

**8. Context Recall**
```python
def context_recall(retrieved, relevant):
    """Recall of retrieved context"""
    relevant_retrieved = set(retrieved) & set(relevant)
    return len(relevant_retrieved) / len(relevant) if relevant else 0
```

### 2. RAGAS Evaluator (`ragas_evaluator.py`)

**Purpose**: Integration with RAGAS framework for comprehensive RAG evaluation.

**RAGAS Framework**: Industry-standard evaluation for RAG systems measuring:
- Faithfulness (answer based on retrieved context)
- Answer Relevance (answer addresses question)
- Context Precision (relevant context ranked higher)
- Context Recall (all relevant context retrieved)
- Context Relevancy (retrieved context is relevant)

**Implementation**:

```python
from src.evaluation.ragas_evaluator import RAGASEvaluator

evaluator = RAGASEvaluator()

# Evaluate single example
result = evaluator.evaluate_single(
    question="How does PostgreSQL handle MVCC?",
    answer="PostgreSQL uses HeapTupleSatisfiesMVCC to check visibility...",
    contexts=[
        "MVCC uses transaction IDs for visibility...",
        "HeapTupleSatisfiesMVCC checks tuple visibility..."
    ],
    ground_truth="PostgreSQL implements MVCC through transaction IDs..."
)

print(result)
# {
#     'faithfulness': 0.92,
#     'answer_relevancy': 0.88,
#     'context_precision': 0.85,
#     'context_recall': 0.78,
#     'context_relevancy': 0.90
# }
```

**Batch Evaluation**:

```python
# Evaluate multiple examples
test_cases = [
    {
        'question': '...',
        'answer': '...',
        'contexts': [...],
        'ground_truth': '...'
    },
    # ... more examples
]

results = evaluator.evaluate_batch(test_cases)

print(f"Average Faithfulness: {results['faithfulness_avg']}")
print(f"Average Answer Relevancy: {results['answer_relevancy_avg']}")
```

**RAGAS Metrics Detail**:

#### 1. Faithfulness
**Definition**: How grounded is the answer in the retrieved context?
**Computation**:
- Extract claims from answer
- Verify each claim against context
- Score = verified_claims / total_claims

**Target**: >0.85
**Current**: 0.78-0.92 (varies by question complexity)

#### 2. Answer Relevancy
**Definition**: How well does the answer address the question?
**Computation**:
- Semantic similarity between question and answer
- Penalize off-topic content
- Reward direct answers

**Target**: >0.80
**Current**: 0.72-0.88

#### 3. Context Precision
**Definition**: Are relevant contexts ranked higher?
**Computation**:
- Measure relevance of top-k contexts
- Penalize relevant context appearing late
- Score = Σ (relevance_i × precision_at_i)

**Target**: >0.75
**Current**: 0.78-0.92

#### 4. Context Recall
**Definition**: Did we retrieve all relevant context?
**Computation**:
- Identify all relevant context in corpus
- Measure how much was retrieved
- Score = retrieved_relevant / total_relevant

**Target**: >0.70
**Current**: 0.65-0.84

#### 5. Context Relevancy (Custom)
**Definition**: Overall relevance of retrieved context
**Computation**:
- Semantic similarity between question and contexts
- Average across all retrieved contexts

**Target**: >0.75
**Current**: 0.524-0.839

**RAGAS Configuration**:

```yaml
ragas:
  metrics:
    - faithfulness
    - answer_relevancy
    - context_precision
    - context_recall
    - context_relevancy

  embeddings:
    model: "sentence-transformers/all-MiniLM-L6-v2"

  llm:
    model: "gpt-3.5-turbo"  # For claim verification
    temperature: 0.0

  batch_size: 10
  timeout: 300
```

**Recent RAGAS Results** (50-question sample):

| Metric | Min | Max | Mean | Std Dev |
|--------|-----|-----|------|---------|
| Faithfulness | 0.78 | 0.92 | 0.85 | 0.04 |
| Answer Relevancy | 0.72 | 0.88 | 0.81 | 0.05 |
| Context Precision | 0.78 | 0.92 | 0.86 | 0.04 |
| Context Recall | 0.65 | 0.84 | 0.74 | 0.06 |
| Context Relevancy | 0.52 | 0.84 | 0.68 | 0.09 |

### Integration with Experiments

**Comprehensive Evaluation Script**: `experiments/test_comprehensive_ragas.py`

```python
# Run comprehensive RAGAS evaluation
python experiments/test_comprehensive_ragas.py

# Output:
# - results/comprehensive_ragas_results_YYYYMMDD_HHMMSS.json
# - results/ragas_summary_YYYYMMDD_HHMMSS.txt
```

**Evaluation Pipeline**:
1. Load test questions
2. Generate queries with RAG-CPGQL
3. Execute queries (if enabled)
4. Collect contexts and answers
5. Compute RAGAS metrics
6. Generate summary statistics
7. Save detailed results

## Evaluation Datasets

### Test Sets

**1. Statistical Validation Set** (200 questions)
- Purpose: Large-scale validity testing
- Source: Sampled from test_split_merged.jsonl
- Metrics: Validity rate, execution success, enrichment coverage

**2. Enrichment Suite** (30 questions)
- Purpose: Deep enrichment effectiveness testing
- Source: Hand-selected diverse questions
- Metrics: All metrics + manual correctness checks

**3. RAGAS Evaluation Set** (50 questions)
- Purpose: RAG quality assessment
- Source: Questions with ground truth answers
- Metrics: Full RAGAS suite

### Ground Truth

**Question-Answer Pairs**:
- Source: PostgreSQL documentation, books, pg_hackers
- Format: JSONL with question, answer, context
- Size: 4,087 test pairs

**Query Templates**:
- Source: Manual CPGQL examples
- Format: JSON with query, description, expected behavior
- Size: 1,072 templates

## Performance Benchmarks

### Current System Performance

**Generation** (200-question test):
- Validity: 97.5%
- Syntax errors: 2.5%
- Avg generation time: 3.2s

**Execution** (30-question test):
- Success rate: 86.7%
- Empty results: 14.3%
- Avg execution time: 8.7s

**Enrichment** (30-question test):
- Coverage: 62.2%
- Tag usage: 100% (in enriched queries)
- Improvement over baseline: +18.2%

**RAGAS** (50-question test):
- Faithfulness: 0.85 ± 0.04
- Answer Relevancy: 0.81 ± 0.05
- Context Precision: 0.86 ± 0.04
- Context Recall: 0.74 ± 0.06

### Comparison with Baselines

| System Variant | Validity | Exec Success | Enrichment | Time (s) |
|----------------|----------|--------------|------------|----------|
| RAG-CPGQL (Full) | 97.5% | 86.7% | 62.2% | 8.4 |
| No Enrichment | 94.2% | 72.3% | 0% | 6.1 |
| No CFG/DDG | 95.8% | 78.1% | 44.0% | 7.2 |
| No Retrieval | 89.1% | 58.4% | 0% | 3.5 |

**Improvement over No-Enrichment Baseline**:
- Validity: +3.5%
- Execution Success: +19.9%
- Enrichment Coverage: +62.2pp

## Usage Examples

### Example 1: Compute Basic Metrics

```python
from src.evaluation.metrics import (
    validity_rate,
    execution_success_rate,
    enrichment_coverage
)

results = [...]  # List of query results

print(f"Validity: {validity_rate(results):.1%}")
print(f"Execution Success: {execution_success_rate(results):.1%}")
print(f"Enrichment Coverage: {enrichment_coverage(results):.1%}")
```

### Example 2: Run RAGAS Evaluation

```python
from src.evaluation.ragas_evaluator import RAGASEvaluator

evaluator = RAGASEvaluator()

test_case = {
    'question': 'How does PostgreSQL check tuple visibility?',
    'answer': 'Uses HeapTupleSatisfiesMVCC with MVCC snapshot...',
    'contexts': ['...', '...'],
    'ground_truth': 'PostgreSQL checks tuple visibility...'
}

scores = evaluator.evaluate_single(**test_case)
print(f"Faithfulness: {scores['faithfulness']:.2f}")
```

### Example 3: Full Evaluation Pipeline

```python
from src.workflow.langgraph_workflow import create_workflow
from src.evaluation.ragas_evaluator import RAGASEvaluator
from src.evaluation.metrics import *

workflow = create_workflow()
evaluator = RAGASEvaluator()

questions = [...]  # Test questions
results = []

for q in questions:
    result = workflow.invoke({'question': q})
    results.append(result)

# Basic metrics
print(f"Validity: {validity_rate(results):.1%}")
print(f"Success: {execution_success_rate(results):.1%}")

# RAGAS metrics
ragas_results = evaluator.evaluate_batch(results)
print(f"Faithfulness: {ragas_results['faithfulness_avg']:.2f}")
```

## Dependencies

- `ragas`: RAGAS framework
- `langchain`: LLM utilities for evaluation
- `sentence-transformers`: Embedding models
- `scikit-learn`: Metric computations

## See Also

- `/experiments/test_comprehensive_ragas.py` - Full evaluation script
- `/results/` - Evaluation results and reports
- Root README.md - Performance metrics summary
- Research paper - Evaluation methodology section
