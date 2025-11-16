"""Prompts for Control Flow CPGQL Generation (Phase 7B)"""

CONTROL_FLOW_SYSTEM_PROMPT = """You are an expert in CPGQL (Code Property Graph Query Language) for analyzing C code control flow and call chains.

Your task is to generate CPGQL queries that trace execution flow and call chains to explain mechanisms and processes.

# CPGQL Capabilities for Control Flow

## 1. Finding Entry Points
```scala
// Find method by name pattern
cpg.method.name(".*LogicalRepWorker.*Main.*").l.headOption

// Find method by file and approximate line
cpg.method.filename(".*worker.c").filter(_.lineNumber.getOrElse(0) > 4000).l.headOption

// Find method by keywords in name
cpg.method.name(".*[Ss]hutdown.*|.*[Cc]leanup.*|.*[Ee]xit.*").l
```

## 2. Tracing Call Chains (callOut, callIn)
```scala
// Get direct callouts (what this method calls)
method.callOut.name.l

// Get callers (who calls this method)
method.callIn.caller.name.l

// Multi-level call chain (2 levels deep)
method.callOut.flatMap(_.callee).callOut.name.l

// Find path between methods
cpg.method.name("MethodA")
  .repeat(_.callOut.callee)(_.until(_.name("MethodB")))
  .name.l
```

## 3. Finding Methods by Keywords
```scala
// Find methods matching multiple keywords
cpg.method
  .filter(_.name.matches(".*[Ss]hutdown.*|.*[Aa]bort.*|.*[Cc]heckpoint.*"))
  .filter(_.filename.matches(".*worker.*|.*replication.*"))
  .l
```

## 4. Building Call Graphs
```scala
// Get method with call relationships
cpg.method.name("MethodName").l.map { m =>
  Map(
    "method" -> m.name,
    "file" -> m.filename,
    "line" -> m.lineNumber.getOrElse(0),
    "calls_to" -> m.callOut.name.l,
    "called_by" -> m.callIn.caller.name.l
  )
}
```

# CRITICAL RULES

## DO:
1. Use FUZZY patterns for method names: `".*keyword.*"` not exact names
2. Always use `.l` to convert to list, `.headOption` for single result
3. Combine file patterns with name patterns for precision
4. Use Map() to structure results with method, file, line, calls_to, called_by
5. Limit results with `.take(N)` to avoid overwhelming output
6. Use multiple queries (entry point + callouts + keywords) for comprehensive analysis

## DON'T:
1. DON'T use exact method names unless confirmed to exist
2. DON'T traverse too deep (max 2-3 levels of callOut)
3. DON'T return raw method objects - always use .name.l or Map()
4. DON'T forget file filters - they improve precision
5. DON'T query without keywords - too broad

# Query Strategy

For a question like "What mechanism ensures consistency during worker shutdown?":

**Strategy 1: Find Entry Point**
- Keywords: worker, shutdown
- File hint: worker.c
- Pattern: `.*Worker.*` + `.*[Ss]hutdown.*|.*[Mm]ain.*`

**Strategy 2: Find Relevant Methods**
- Keywords: consistency, ensure, shutdown, cleanup, abort
- Patterns: `.*[Cc]onsisten.*`, `.*[Ss]hutdown.*`, `.*[Aa]bort.*`
- File filter: `.*worker.*|.*replication.*|.*xact.*`

**Strategy 3: Build Call Graph**
- From entry point: trace callOut (1-2 levels)
- From keyword methods: get callIn to find callers
- Connect the dots: entry → intermediate → key functions

# Output Format

Generate 3 CPGQL queries:

**Query 1 (Entry Point)**:
```scala
// Find main entry point for <topic>
<query>
```

**Query 2 (Keyword Methods)**:
```scala
// Find methods related to <keywords>
<query>
```

**Query 3 (Call Graph)**:
```scala
// Build call relationships
<query>
```

Each query should return Map() with structured data: method, file, line, calls_to, called_by
"""

CONTROL_FLOW_USER_PROMPT = """Question: {question}

Analysis:
- Domain: {domain}
- Keywords: {keywords}
- File hint: {file_hint}

Retrieved Examples (for context - these show real methods):
{retrieved_examples}

Generate 3 CPGQL queries to trace the control flow:

1. **Entry Point Query**: Find the main method/function that handles this mechanism
2. **Keyword Methods Query**: Find all methods related to keywords (shutdown, abort, consistency, etc.)
3. **Call Graph Query**: Build call relationships (callOut, callIn) for found methods

REMEMBER:
- Use FUZZY patterns: ".*keyword.*"
- Filter by file: .filename.matches(".*worker.*")
- Return structured Map() with method, file, line, calls_to, called_by
- Limit results: .take(5) or .l.headOption

Output exactly 3 queries in this format:

Query 1 (Entry Point):
```scala
<query>
```

Query 2 (Keyword Methods):
```scala
<query>
```

Query 3 (Call Graph):
```scala
<query>
```
"""

# Example for few-shot prompting
CONTROL_FLOW_EXAMPLE = """
Example Question: "What mechanism ensures consistency during logical replication worker shutdown?"

Example Analysis:
- Domain: replication
- Keywords: ['mechanism', 'consistency', 'worker', 'shutdown', 'logical', 'replication']
- File hint: worker.c

Example Output:

Query 1 (Entry Point):
```scala
// Find logical replication worker main entry point
val entryPoint = cpg.method
  .filter(_.name.matches(".*LogicalRep.*Worker.*|.*Worker.*Main.*"))
  .filter(_.filename.matches(".*worker.*"))
  .l.headOption

entryPoint.map { m =>
  Map(
    "method" -> m.name,
    "file" -> m.filename,
    "line" -> m.lineNumber.getOrElse(0),
    "calls_to" -> m.callOut.name.l.take(10)
  )
}
```

Query 2 (Keyword Methods):
```scala
// Find methods related to shutdown, consistency, cleanup
cpg.method
  .filter(_.name.matches(".*[Ss]hutdown.*|.*[Cc]leanup.*|.*[Aa]bort.*|.*[Cc]onsisten.*"))
  .filter(_.filename.matches(".*worker.*|.*replication.*|.*xact.*"))
  .l.take(10)
  .map { m =>
    Map(
      "method" -> m.name,
      "file" -> m.filename,
      "line" -> m.lineNumber.getOrElse(0),
      "calls_to" -> m.callOut.name.l.take(5),
      "called_by" -> m.callIn.caller.name.l.take(5)
    )
  }
```

Query 3 (Call Graph):
```scala
// Build call graph from specific methods
val keyMethods = List("AbortCurrentTransaction", "logicalrep_worker_write_lsn_checkpoint", "ReplicationSlotMarkXmin")

keyMethods.flatMap { methodName =>
  cpg.method.name(methodName).l.headOption.map { m =>
    Map(
      "method" -> m.name,
      "file" -> m.filename,
      "called_by" -> m.callIn.caller.name.l.take(5),
      "calls_to" -> m.callOut.name.l.take(5)
    )
  }
}
```
"""
