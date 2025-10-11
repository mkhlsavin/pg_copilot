# Grammar Test Findings

**Date:** 2025-10-10
**Test:** Comparison of query generation WITH vs WITHOUT grammar constraints

## Executive Summary

**Result: Grammar constraints are NECESSARY but NOT SUFFICIENT**

- **WITH Grammar**: 100% syntactically valid but generic/useless queries
- **WITHOUT Grammar**: Model generates verbose explanations instead of clean queries
- **Root Cause**: The problem is NOT the grammar - it's the prompt and lack of RAG context

## Test Results

### WITHOUT Grammar (Test Output)

The model generated:

1. **Query 1** (Memory management):
   ```
   cpg.method.name(".*SharedBuffer.*").parameter.name.l
   pgsql.method.name(".*SharedBuffer.*").parameter.name.l
   ```
   **Issues**:
   - Duplicated output
   - Uses `pgsql` instead of `cpg` (invalid)

2. **Query 2** (Vacuum operations):
   ```
   pg.method.name(".*vacuum").l

   PGQL Query:
   cpg.method.name(".*vacuum").l
   ```
   **Issues**:
   - Multiple outputs with explanatory text
   - Uses `pg` instead of `cpg` (invalid)

3. **Query 3** (WAL system):
   ```
   - Find all methods related to WAL: cpg.method.name(".*wal.*").l
   : The query you provided is designed to find all methods related to the WAL(Write-Ahead Log)system...
   [Continues with long explanation about case-insensitive search]
   ```
   **Issues**:
   - Includes verbose explanation (200+ words)
   - Not a clean query output
   - Model acting as a chatbot instead of query generator

4. **Query 4** (Buffer pool):
   ```
   :: cpg.method.name(".*pool.*").l
   ```
   **Issue**: Prefixed with `::`

5. **Query 5** (MVCC):
   ```
   - Find SQL-related methods: cpg.method.name(".*sql.*").l

   The provided CPGQL query is a good start...
   [Lists 6 different queries and continues explaining]
   ```
   **Issues**:
   - Model provides multiple queries instead of one
   - Extensive explanation
   - Wrong query for the question

6. **Query 6** (Hash tables):
   ```
   .org
   : cpg.method.name(".*hash.*").l
   ```
   **Issue**: Invalid prefix `.org`

7. **Query 7** (Query planning):
   ```
   pg.method.name(".*query.*plan.*").l
   ```
   **Issue**: Uses `pg` instead of `cpg`

8. **Query 8** (Spinlocks):
   ```
   .spinlock.usage.l
   ```
   **Issue**: Doesn't start with `cpg` - completely invalid

## Analysis

### Why Grammar is Necessary

Without grammar, the model:
1. **Generates explanations** instead of clean queries
2. **Produces invalid syntax** (wrong prefixes, duplicates)
3. **Acts like a chatbot** providing multiple options and education
4. **Cannot be reliably parsed** for execution

### Why Grammar Alone is Insufficient

With grammar (from previous tests):
1. **Queries are TOO GENERIC**: `cpg.method.l`, `cpg.call.l`
2. **Don't use enrichment tags**: Missing semantic classification, features, etc.
3. **Won't scale to large graphs**: Need specific filters for 450k vertices

### Real Root Causes

1. **Prompt Quality**
   - Current prompt in `cpgql_generator.py` has only 8 simple examples
   - No examples using enrichment tags
   - No examples showing complex filters
   - Missing context about PostgreSQL domain

2. **Missing RAG Context**
   - Not retrieving similar Q&A pairs
   - Not retrieving relevant CPGQL examples from training data
   - Model has no context about what similar questions need

3. **No Enrichment Awareness**
   - Prompt doesn't emphasize using tags
   - No examples showing: `.tag.nameExact("feature").valueExact("MVCC")`
   - Model doesn't know enriched CPG exists

## Recommendations

### Keep Grammar BUT Fix Everything Else

1. **Improve Prompts** (`cpgql_generator.py` line 102-124)
   - Add enrichment tag examples
   - Show complex filtering patterns
   - Include domain-specific context

2. **Integrate Real RAG** (Currently mocked)
   - Connect vector store for similar Q&A retrieval
   - Retrieve relevant CPGQL examples from 5,361 training samples
   - Use enrichment layer info in context

3. **Architecture Redesign** (User's suggestion)
   - Use LangGraph/LangChain for orchestration
   - Multi-step workflow:
     1. Question analysis
     2. RAG retrieval
     3. Query generation with context
     4. Query refinement
   - Use RAGAS for evaluation metrics

4. **Add Enrichment Hints**
   - Query enriched CPG metadata first
   - Provide relevant tags as context
   - Example: "Available features: MVCC, TOAST, Partitioning..."

## Evidence from Previous Tests

From `expanded_test_results.json`, queries that WORKED used enrichment:
```json
{
  "query": "cpg.method.where(_.tag.nameExact(\"data-structure\").valueExact(\"hash-table\")).name.l.take(10)",
  "success": true
}
```

But current simple prompts generate:
```
cpg.method.l  // Too generic - will return all 450k methods!
```

## Conclusion

**Grammar must stay enabled** to prevent chatbot-style responses.

**But the real fix is:**
1. Better prompts with enrichment examples
2. Real RAG retrieval (not mocked)
3. Architecture redesign with LangGraph + RAGAS
4. Enrichment-aware query generation

**Next Steps:**
1. ✅ Keep grammar enabled in `config.yaml`
2. Design LangGraph architecture
3. Integrate RAGAS for metrics
4. Connect real vector store
5. Improve prompts with enrichment examples
