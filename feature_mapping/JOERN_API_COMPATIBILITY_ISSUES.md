# Joern API Compatibility Issues - Feature Mapping

**Date:** 2025-10-09
**Status:** Blocked by API incompatibilities

---

## Summary

The `feature_mapping` project was written for an earlier Joern API release and is incompatible with Joern 2.x. Every adaptation attempt so far has hit several critical blockers.

---

## Issues Identified

### 1. CLI API Changes

**Problem:** Command semantics shifted between releases

- `clearCpg` → removed in Joern 2.x
- `importCpg(path, project)` → creates a copy of the CPG in the workspace instead of a link
- `loadCpg(path)` → creates a project with a suffix (pg17_full.cpg → pg17_full.cpg1)
- `open(project)` → requires the project to already exist in the workspace

**Impact:** Existing CPGs cannot be loaded without creating redundant copies

### 2. Location API Changes

**Problem:** The API for retrieving locations was refactored

```scala
// Old API (no longer works):
node.location.map(_.filename)
node.location.flatMap(_.lineNumber)

// New API (working):
Option(node.location.filename)
Option(node.location.lineNumber).flatten
```

**Status:** ✅ Fixed in joern_client.py

### 3. Import Changes

**Problem:** Several imports have been removed

```scala
// Old (no longer works):
import overflowdb.traversal._
import scala.Option

// New (working):
import io.shiftleft.semanticcpg.language._
// Option is available by default now
```

**Status:** ✅ Fixed in joern_client.py

### 4. HTTP Server Limitations

**Problem:** The Joern HTTP server never returns stdout produced by `println()`

- `POST /query` responds only with `{success: true, uuid: "..."}`
- There is no way to capture script output over the HTTP API
- Traversal results cannot be retrieved

**Impact:** The HTTP API cannot be used to search for candidate nodes

---

## Attempted Solutions

### Attempt 1: Fix CLI import commands

**Status:** ❌ Failed

- `loadCpg()` always creates a suffixed copy
- `importCpg()` expects a project that does not exist yet
- `open()` cannot find the project

### Attempt 2: Use HTTP server

**Status:** ❌ Blocked

- The HTTP API never returns stdout
- Candidate search results cannot be retrieved

### Attempt 3: Direct server communication via cpgqls_client

**Status:** ⏳ In progress

- Reusing the working `cpgqls_client` from the RAG project
- Sending direct HTTP requests

---

## Recommended Approach

### Option A: Manual Feature Tagging (QUICK)

Create a lightweight `cpgqls_client` script that adds feature tags manually for the key features:

```python
from cpgqls_client import CPGQLSClient

client = CPGQLSClient("localhost:8080")

# Example: tag MERGE-related functions
query = '''
val mergeFiles = cpg.file.name(".*merge.*").l
mergeFiles.foreach(f => f.newTagNodePair("Feature", "MERGE").store)
run.commit
'''
result = client.execute(query)
```

**Pros:**

- Fast (minutes of work)
- Reuses the existing infrastructure
- Manual review keeps mapping quality high

**Cons:**

- Requires hands-on effort for each feature
- Does not cover all 394 features automatically

### Option B: Rewrite Feature Mapping (SLOW)

Rewrite `feature_mapping` to work with `cpgqls_client` and the HTTP API.

**Pros:**

- Fully automated
- Works for all 394 features

**Cons:**

- Takes several hours
- Candidate search logic must be rewritten
- Scoring needs to be adapted to the new API

### Option C: Use Joern CLI scripts directly (MEDIUM)

Run `joern --script` without loading the CPG inside the script (assumes the CPG is already imported).

**Status:** Not yet tested

---

## Recommendation for User

**For production, Option A is the fastest win:**

1. Prepare a list of 10–20 high-value PostgreSQL features:
   - MERGE
   - Logical replication
   - JSONB data type
   - Parallel query
   - Partitioning
   - WAL improvements
   - Security features (SCRAM, SSL)
   - Performance features (JIT, parallel)
   - Extension API
   - Replication slots

2. Write simple tagging queries for each feature:

   ```scala
   // MERGE
   cpg.file.name(".*merge.*").newTagNodePair("Feature", "MERGE").store
   cpg.method.name(".*merge.*").newTagNodePair("Feature", "MERGE").store
   run.commit

   // Logical replication
   cpg.file.name(".*logical.*repl.*").newTagNodePair("Feature", "Logical replication").store
   run.commit
   ```

3. Update the RAG prompts so they reference feature tags

4. Test the RAG flow with feature-based queries

**Time investment:** 1–2 hours instead of 5–8 hours for a full rewrite

---

## Files Modified

1. ✅ `feature_mapping/joern_client.py` - Location API fix
2. ✅ `feature_mapping/joern_http_client.py` - HTTP client created (still blocked)
3. ⏳ Need: Simple tagging script using cpgqls_client

---

## Next Steps

1. Create `add_feature_tags.py` backed by `cpgqls_client`
2. Tag the 10–20 key features
3. Update `rag_cpgql/src/generation/prompts.py` with feature tag examples
4. Test RAG queries that rely on feature tags
5. Document the outcomes

---

## Conclusion

Porting `feature_mapping` to Joern 2.x requires a substantial rewrite because of the API incompatibilities.

For production needs, manual tagging of 10–20 priority features delivers value in 1–2 hours versus 5–8 hours for a full rewrite.

After manual tagging, evaluate how feature tags impact the RAG flow and decide whether a complete automation effort is worthwhile.
