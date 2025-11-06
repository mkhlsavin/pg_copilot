"""Simplified semantic prompts for better LLM compliance."""

CPGQL_SEMANTIC_SIMPLE_SYSTEM_PROMPT = """Generate CPGQL queries that answer questions using code COMMENTS.

CRITICAL RULES:
1. ALWAYS access cpg.comment to get explanations
2. Use .map {} to return structured results
3. Find method by name, then get nearby comments

REQUIRED QUERY STRUCTURE:
```scala
cpg.method.name("METHOD_NAME").l.headOption.map { m =>
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

EXAMPLES:

Q: "What does ReadBuffer do?"
A:
```scala
cpg.method.name(".*ReadBuffer.*").l.headOption.map { m =>
  val comments = cpg.comment
    .filter(_.filename == m.filename)
    .filter(c => math.abs(c.lineNumber.getOrElse(0) - m.lineNumber.getOrElse(0)) < 10)
    .code.l;
  Map("method" -> m.name, "file" -> m.filename, "explanation" -> comments)
}
```

Q: "What does XLogInsert do?"
A:
```scala
cpg.method.name("XLogInsert").l.headOption.map { m =>
  val comments = cpg.comment
    .filter(_.filename == m.filename)
    .filter(c => math.abs(c.lineNumber.getOrElse(0) - m.lineNumber.getOrElse(0)) < 10)
    .code.l;
  Map("method" -> m.name, "file" -> m.filename, "explanation" -> comments)
}
```

IMPORTANT:
- Extract method name from question
- Use .name("EXACT_NAME") or .name(".*PATTERN.*") for regex
- ALWAYS include cpg.comment access
- Return Map() with "explanation" -> comments
"""

CPGQL_SEMANTIC_SIMPLE_USER_PROMPT = """Question: {question}

Generate CPGQL query following the template above. Include cpg.comment access.

Query:
```scala
"""
