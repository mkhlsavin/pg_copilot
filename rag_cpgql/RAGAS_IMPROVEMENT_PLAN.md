# RAGAS Metrics Improvement Plan

## Overview

This document tracks the plan to improve RAGAS (Retrieval-Augmented Generation Assessment) metrics for the RAG-CPGQL system.

## Baseline Metrics (from test_with_ragas.py - 30 samples)

Based on previous evaluation:
- **Validity Rate**: ~100% (30/30 questions generated valid queries)
- **Q&A Similarity**: 0.791 (HIGH ✓)
- **CPGQL Similarity**: ~0.25-0.30 (LOW ⚠️)
- **Tag Usage Rate**: ~52% (MEDIUM ⚠️)
- **Enrichment Coverage**: 0.44 baseline → 0.622 after Phase 4 (HIGH ✓)

## Target Metrics

| Metric | Current | Target | Priority |
|--------|---------|--------|----------|
| Validity Rate | ~100% | >=95% | ✓ ACHIEVED |
| Q&A Similarity | 0.791 | >=0.75 | ✓ ACHIEVED |
| CPGQL Similarity | 0.25-0.30 | >=0.40 | HIGH |
| Tag Usage Rate | 52% | >=70% | MEDIUM |
| Enrichment Coverage | 0.622 | >=0.65 | MEDIUM |
| Answer Relevancy (RAGAS) | TBD | >=0.80 | HIGH |
| Faithfulness (RAGAS) | TBD | >=0.85 | HIGH |
| Context Precision (RAGAS) | TBD | >=0.75 | MEDIUM |
| Context Recall (RAGAS) | TBD | >=0.75 | MEDIUM |

## Identified Issues

### 1. Low CPGQL Example Similarity (~0.25-0.30)

**Problem**: Retrieved CPGQL examples have low relevance to questions.

**Root Causes**:
- CPGQL examples may use generic embeddings
- Example descriptions may not capture query intent
- Limited diversity in example dataset (1,072 examples)

**Proposed Solutions**:
1. **Improve Example Embeddings**:
   - Add detailed descriptions to CPGQL examples
   - Include domain/intent metadata in embeddings
   - Use enrichment tags in example metadata

2. **Enhance Retrieval Strategy**:
   - Combine semantic similarity with tag-based filtering
   - Use hybrid retrieval (keyword + semantic)
   - Boost examples that match domain/intent

3. **Expand Example Dataset**:
   - Add more diverse CPGQL examples
   - Include examples for all major domains
   - Add examples for different complexity levels

### 2. Moderate Tag Usage Rate (52%)

**Problem**: Only half of generated queries use enrichment tags.

**Root Causes**:
- Prompt may not emphasize tag usage strongly enough
- Some domains have low tag coverage
- Generator may prefer name-based queries

**Proposed Solutions**:
1. **Strengthen Prompt Engineering**:
   - Add explicit tag usage examples in prompts
   - Emphasize tag-based filtering in instructions
   - Show tag + name hybrid patterns

2. **Improve Tag Effectiveness Tracking**:
   - Boost confidence for successful tag patterns
   - Reduce confidence for unused tags
   - Add tag usage rewards in generation

3. **Expand Tag Coverage**:
   - Continue Phase 4 fallback improvements
   - Add more keyword-to-tag patterns
   - Improve fuzzy matching threshold

### 3. Enrichment Coverage Could Be Higher (0.622)

**Problem**: Coverage is good but could reach 0.65+.

**Root Causes**:
- Some generic domains still have low coverage
- Keyword patterns may miss edge cases
- Some enrichment layers underutilized

**Proposed Solutions**:
1. **Enhance Generic Domain Handling**:
   - Add more broad-purpose tags
   - Improve domain classification
   - Add cross-domain tag suggestions

2. **Add More Keyword Patterns**:
   - Review missed questions from evaluation
   - Add patterns for common PostgreSQL terms
   - Expand algorithm and data structure patterns

3. **Utilize All Enrichment Layers**:
   - Add API category suggestions
   - Expand architectural role mappings
   - Improve algorithm detection

## RAGAS-Specific Improvements

### Answer Relevancy

**Goal**: Ensure generated CPGQL queries are relevant to the question.

**Strategies**:
1. Add question-query alignment checks in prompts
2. Include intent verification in generation
3. Use domain-specific query patterns

### Faithfulness

**Goal**: Ensure queries use retrieved context appropriately.

**Strategies**:
1. Add explicit context-usage instructions in prompts
2. Reference retrieved Q&A and examples in generation
3. Validate query patterns against examples

### Context Precision

**Goal**: Ensure retrieved context is relevant.

**Strategies**:
1. Improve retrieval ranking with tag filtering
2. Add re-ranking based on enrichment hints
3. Filter low-relevance examples

### Context Recall

**Goal**: Ensure all relevant context is retrieved.

**Strategies**:
1. Increase retrieval count for complex questions
2. Add multi-round retrieval for low coverage
3. Use hybrid retrieval strategies

## Implementation Phases

### Phase 1: CPGQL Example Enhancement (Priority: HIGH)

**Tasks**:
1. ✅ Run comprehensive RAGAS evaluation (50-100 samples)
2. ⬜ Analyze CPGQL similarity scores by domain
3. ⬜ Add detailed descriptions to CPGQL examples
4. ⬜ Implement hybrid retrieval (semantic + tag-based)
5. ⬜ Re-evaluate CPGQL similarity

**Expected Impact**: +0.10-0.15 CPGQL similarity (0.30 → 0.40-0.45)

### Phase 2: Tag Usage Improvement (Priority: MEDIUM)

**Tasks**:
1. ⬜ Analyze tag usage patterns from evaluation
2. ⬜ Update prompts with stronger tag emphasis
3. ⬜ Add tag usage examples in prompts
4. ⬜ Implement tag usage rewards
5. ⬜ Re-evaluate tag usage rate

**Expected Impact**: +15-20% tag usage (52% → 67-72%)

### Phase 3: Coverage Enhancement (Priority: MEDIUM)

**Tasks**:
1. ⬜ Identify low-coverage question patterns
2. ⬜ Add missing keyword patterns
3. ⬜ Expand generic domain handling
4. ⬜ Add cross-domain suggestions
5. ⬜ Re-evaluate coverage

**Expected Impact**: +0.03-0.05 coverage (0.622 → 0.65-0.67)

### Phase 4: RAGAS Metric Optimization (Priority: HIGH)

**Tasks**:
1. ⬜ Analyze real RAGAS metrics from evaluation
2. ⬜ Implement targeted improvements for low metrics
3. ⬜ Add context-awareness in prompts
4. ⬜ Improve faithfulness with explicit instructions
5. ⬜ Re-evaluate all RAGAS metrics

**Expected Impact**: All RAGAS metrics >=0.75

## Evaluation Schedule

1. **Baseline Evaluation** (Current):
   - 50-100 samples from test split
   - All RAGAS metrics measured
   - Detailed analysis of issues

2. **Phase 1 Evaluation** (After CPGQL improvements):
   - Same 50-100 samples
   - Focus on CPGQL similarity
   - Measure impact on other metrics

3. **Phase 2 Evaluation** (After tag usage improvements):
   - Same samples + 50 new samples
   - Focus on tag usage rate
   - Measure generation quality

4. **Phase 3 Evaluation** (After coverage improvements):
   - 100 samples focusing on low-coverage domains
   - Measure coverage distribution
   - Validate fallback strategies

5. **Final Evaluation** (After all phases):
   - 200 samples comprehensive test
   - All RAGAS metrics
   - Publication-ready results

## Success Criteria

### Minimum Acceptable Performance (MAP)
- Validity Rate: >=95%
- CPGQL Similarity: >=0.35
- Tag Usage: >=60%
- Enrichment Coverage: >=0.60
- Answer Relevancy: >=0.75
- Faithfulness: >=0.80

### Target Performance (TP)
- Validity Rate: >=98%
- CPGQL Similarity: >=0.40
- Tag Usage: >=70%
- Enrichment Coverage: >=0.65
- Answer Relevancy: >=0.80
- Faithfulness: >=0.85
- Context Precision: >=0.75
- Context Recall: >=0.75

### Stretch Goals (SG)
- Validity Rate: 100%
- CPGQL Similarity: >=0.45
- Tag Usage: >=80%
- Enrichment Coverage: >=0.70
- All RAGAS metrics: >=0.85

## Current Status

- **Date**: 2025-10-17
- **Phase**: Baseline Evaluation (Phase 1 - running)
- **Samples Evaluated**: 50 (in progress)
- **Next Steps**:
  1. Complete baseline evaluation
  2. Analyze results and prioritize improvements
  3. Begin Phase 1 CPGQL enhancement

## Notes

- All improvements should maintain or improve validity rate (currently ~100%)
- Focus on metrics with highest impact on end-to-end quality
- Track metrics across evaluation runs to measure progress
- Document all changes and their impact on metrics
