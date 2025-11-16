"""Simplified semantic prompts for better LLM compliance."""

CPGQL_SEMANTIC_SIMPLE_SYSTEM_PROMPT = """Generate CPGQL queries that answer questions using code COMMENTS.

====================================================================================
CRITICAL RULES - READ CAREFULLY:
====================================================================================

✅ DO:
1. ALWAYS access cpg.comment to get explanations
2. Use .map {} to return structured results with "explanation" field
3. Use FUZZY patterns (.*pattern.*) when method name is uncertain
4. Study the RETRIEVED EXAMPLES - they show REAL methods that exist in the codebase
5. If question mentions a specific method name, use a FUZZY pattern to find similar methods

❌ DON'T:
1. DON'T invent method names from the question text
2. DON'T use exact method names unless you see them in retrieved examples
3. DON'T use literal strings from questions as method names (e.g., "Cache Key: ...")
4. DON'T assume a method exists just because the question mentions it

====================================================================================
REQUIRED QUERY STRUCTURE:
====================================================================================

```scala
cpg.method.name(".*FUZZY_PATTERN.*").l.headOption.map { m =>
  val comments = cpg.comment
    .filter(_.filename == m.filename)
    .filter(c => math.abs(c.lineNumber.getOrElse(0) - m.lineNumber.getOrElse(0)) < 10)
    .code.l;

  Map(
    "method" -> m.name,
    "file" -> m.filename,
    "line" -> m.lineNumber.getOrElse(0),
    "explanation" -> comments
  )
}
```

====================================================================================
CORRECT EXAMPLES:
====================================================================================

Q: "What does timestamp2time_t do?"  ← May not exist exactly!
✅ CORRECT:
```scala
cpg.method.name(".*timestamp.*time.*").l.headOption.map { m =>
  val comments = cpg.comment
    .filter(_.filename == m.filename)
    .filter(c => math.abs(c.lineNumber.getOrElse(0) - m.lineNumber.getOrElse(0)) < 10)
    .code.l;
  Map("method" -> m.name, "file" -> m.filename, "explanation" -> comments)
}
```
❌ WRONG: cpg.method.name("timestamp2time_t")  ← Too specific, may not exist!

Q: "Why does 'Cache Key: t1.two' fail?"  ← Not a method name!
✅ CORRECT:
```scala
cpg.method.name(".*cache.*key.*").l.headOption.map { m =>
  val comments = cpg.comment
    .filter(_.filename == m.filename)
    .filter(c => math.abs(c.lineNumber.getOrElse(0) - m.lineNumber.getOrElse(0)) < 10)
    .code.l;
  Map("method" -> m.name, "file" -> m.filename, "explanation" -> comments)
}
```
❌ WRONG: cpg.method.name(".*Cache Key: t1.two.*")  ← Literal string, not a method!

Q: "What does replication worker do?"
✅ CORRECT:
```scala
cpg.method.name(".*replicat.*worker.*|.*worker.*replicat.*").l.headOption.map { m =>
  val comments = cpg.comment
    .filter(_.filename == m.filename)
    .filter(c => math.abs(c.lineNumber.getOrElse(0) - m.lineNumber.getOrElse(0)) < 10)
    .code.l;
  Map("method" -> m.name, "file" -> m.filename, "explanation" -> comments)
}
```
OR even broader:
```scala
cpg.method.name(".*replicat.*").l.headOption.map { m =>
  val comments = cpg.comment
    .filter(_.filename == m.filename)
    .filter(c => math.abs(c.lineNumber.getOrElse(0) - m.lineNumber.getOrElse(0)) < 10)
    .code.l;
  Map("method" -> m.name, "file" -> m.filename, "explanation" -> comments)
}
```
❌ WRONG: cpg.method.name(".*replication_worker.*")  ← Too specific!

====================================================================================
PATTERN MATCHING TIPS:
====================================================================================

- Break compound words: "timestamp2time" → ".*timestamp.*time.*"
- Use broader patterns: "replication_worker" → ".*replicat.*" or ".*worker.*"
- For acronyms: "XLog" → ".*[Xx]log.*" or just ".*log.*"
- When uncertain: use the most general part (e.g., ".*alloc.*" for allocation)
- Use OR patterns: ".*read.*buffer.*|.*buffer.*read.*"

====================================================================================
"""

CPGQL_SEMANTIC_SIMPLE_USER_PROMPT = """Question: {question}

{retrieved_examples}

Generate CPGQL query following the template above. Include cpg.comment access.
REMEMBER: Use FUZZY patterns (.*pattern.*), DON'T invent exact method names!

Query:
```scala
"""
