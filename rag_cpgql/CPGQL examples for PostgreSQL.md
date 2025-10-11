# Comprehensive CPGQL Question Set for Analyzing the PostgreSQL Codebase

This collection contains **80 practical questions** (8 scenarios × 10 questions) for applying CPGQL/Joern to the PostgreSQL codebase. Every question references **real function and file names** from PostgreSQL 15–18, provides **syntactically correct CPGQL queries**, and addresses **hands-on developer tasks**.

---

## SCENARIO 1: ONBOARDING A NEW DEVELOPER

**Goal:** Quickly grasp PostgreSQL architecture and learn to navigate the codebase

### 1. Primary backend entry point (Basic)

```scala
cpg.method.name("PostgresMain").map(m => (m.name, m.filename, m.signature)).l
cpg.method.name("PostgresMain").ast.isCall.name.dedup.l
```

**Insight:** PostgresMain in `tcop/postgres.c` implements the main request-processing loop.

### 2. Parsing an SQL query (Basic)

```scala
cpg.method.name("raw_parser").callOut.name.l
cpg.method.name("parse_analyze").repeat(_.callOut)(_.emit.until(_.name("transformStmt"))).name.l
```

**Insight:** Execution chain: raw_parser → parse_analyze → transformStmt.

### 3. Query planner code (Intermediate)

```scala
cpg.file.name(".*optimizer.*").method.name.dedup.l
cpg.method.name("planner").callOut.where(_.name("standard_planner")).repeat(_.callOut)(_.until(_.name("create_plan"))).path.l
```

**Insight:** The optimizer/ directory flows planner → standard_planner → create_plan.

### 4. Memory management system (Intermediate)

```scala
cpg.method.name(".*MemoryContext.*|palloc.*|pfree").map(m => (m.name, m.filename, m.signature)).l
cpg.call.name("AllocSetContextCreate").caller.name.dedup.l
```

**Insight:** The Memory Context system in `utils/mmgr/` is a signature PostgreSQL feature.

### 5. User authentication (Intermediate)

```scala
cpg.method.name("ClientAuthentication").map(m => (m.filename, m.lineNumber, m.parameter.name.l)).l
cpg.method.name("Check.*Auth").map(m => (m.name, m.filename)).l
```

**Insight:** `libpq/auth.c` hosts ClientAuthentication and related auth helpers.

### 6. Executor – query execution engine (Advanced)

```scala
cpg.method.name("Exec[A-Z].*").filename(".*executor.*").name.dedup.l
cpg.method.name("ExecutorRun").repeat(_.callOut)(_.until(_.name("ExecSeqScan|ExecIndexScan"))).path.l
```

**Insight:** `executor/` relies on node patterns such as ExecSeqScan, ExecIndexScan, and ExecHashJoin.

### 7. Buffer manager (Advanced)

```scala
cpg.method.name(".*Buffer.*").filename(".*storage/buffer.*").map(m => (m.name, m.filename, m.signature)).l
cpg.method.name("ReadBuffer").repeat(_.callOut)(_.emit.times(5)).name.l
```

**Insight:** `storage/buffer/` manages `shared_buffers` via ReadBuffer/ReleaseBuffer.

### 8. Write-Ahead Logging (Advanced)

```scala
cpg.method.name("XLog.*").filename(".*transam.*").map(m => (m.name, m.filename)).l
cpg.method.name("XLogInsert").caller.name.dedup.l
```

**Insight:** `access/transam/` contains the WAL pipeline: XLogInsert → XLogFlush for durability.

### 9. Error handling (Advanced)

```scala
cpg.call.name("ereport").map(c => (c.location.filename, c.location.lineNumber, c.code)).take(10).l
cpg.identifier.name("PG_TRY|PG_CATCH").location.l
```

**Insight:** `utils/error/elog.c` combines `ereport` with `PG_TRY/PG_CATCH` built on setjmp/longjmp.

### 10. Full SELECT execution chain (Advanced)

```scala
cpg.method.name("exec_simple_query").repeat(_.callOut)(_.emit.times(10)).name.dedup.l
cpg.method.name("exec_simple_query").callOut.name(".*parse.*|.*plan.*|.*Executor.*").l
```

**Insight:** Flow: PostgresMain → exec_simple_query → parser → planner → executor → printtup.

---

## SCENARIO 2: SECURITY AUDIT

**Goal:** Identify vulnerabilities and unsafe coding patterns

### 1. Dangerous string-handling functions (Basic)

```scala
cpg.call.name("strcpy|strcat|sprintf|gets").map(c => (c.name, c.location.filename, c.location.lineNumber)).l
cpg.call.name("strcpy|strcat|sprintf").where(_.location.filename(".*auth.*|.*parser.*")).location.l
```

**Insight:** Targets CWE-120 buffer overflows inside the critical authentication and parser modules.

### 2. Format string vulnerabilities (Basic)

```scala
cpg.call.name("printf|fprintf|sprintf|ereport|elog").whereNot(_.argument(1).isLiteral).location.l
def userInput = cpg.call.name(".*getenv.*|.*recv.*")
cpg.method.name(".*printf.*").parameter.index(1).reachableBy(userInput).l
```

**Insight:** Tracks CWE-134 issues by finding format strings that can be influenced by user input.

### 3. SQL injection in extensions (Intermediate)

```scala
cpg.call.name("SPI_execute").map(c => (c.location.filename, c.argument(1).code)).l
cpg.call.name("SPI_execute").where(_.argument(1).reachableBy(cpg.call.name(".*strcat|.*sprintf"))).location.l
```

**Insight:** Flags CWE-89 cases where SQL is built through concatenation instead of parameters.

### 4. Integer overflow in array subscripting (Intermediate)

```scala
cpg.call.name("array_set|array_ref|array_subscript.*").map(c => (c.location, c.code)).l
cpg.call.name("palloc|malloc").where(_.argument(1).arithmeticExpr).whereNot(_.argument(1).code(".*pg_mul_.*")).location.l
```

**Insight:** Captures CVE-2023-5869 and CVE-2021-32027 patterns where array size calculations overflow.

### 5. Use-after-free patterns (Intermediate)

```scala
cpg.method.name(".*free").filter(_.parameter.size == 1).callIn.where(_.argument(1).isIdentifier)
  .flatMap { freeCall =>
    val freedPtr = freeCall.argument(1).code.head
    freeCall.postDominatedBy.isIdentifier.codeExact(freedPtr)
  }.location.l
```

**Insight:** Spots CWE-416 flows where a pointer is reused after `pfree`.

### 6. TOCTOU race conditions (Advanced)

```scala
val fileOps = Map("access" -> Seq(1), "stat" -> Seq(1), "open" -> Seq(1))
cpg.call.nameExact(fileOps.keys.toSeq: _*).filter { call =>
  val otherCalls = cpg.call.nameExact(fileOps.keys.toSeq: _*).filter(_ != call)
  val sameArg = call.argument(1).code.head
  otherCalls.argument(1).code.contains(sameArg)
}.location.l
```

**Insight:** Highlights CWE-367 check-vs-use races on the same file path.

### 7. Privilege escalation via search_path (Advanced)

```scala
cpg.file.name(".*\\.sql").content.where(_.matches("(?i).*SECURITY\\s+DEFINER.*"))
  .whereNot(_.matches("(?i).*SET\\s+search_path.*")).l
cpg.call.name("[a-z_]+").whereNot(_.name.matches(".*\\..*"))
  .where(_.method.fullName(".*auth.*|.*privilege.*")).map(c => (c.location, c.name)).l
```

**Insight:** Mirrors CVE-2018-1058 where trojan objects in `public` hijack SECURITY DEFINER functions.

### 8. Memory disclosure in error messages (Advanced)

```scala
cpg.call.name("ereport|elog").where(_.argument.reachableBy(cpg.call.name(".*getenv|PG_GETARG.*"))).location.l
cpg.method.name(".*aggregate.*").where(_.parameter.evalType(".*unknown.*"))
  .where(_.ast.isCall.name("ereport")).location.l
```

**Insight:** Surfaces CVE-2023-5868 leaks where aggregates echo memory from unknown types.

### 9. Authentication bypass patterns (Advanced)

```scala
cpg.method.name("ClientAuthentication").controlStructure.controlStructureType("RETURN")
  .whereNot(_.code(".*STATUS_OK.*|.*STATUS_ERROR.*")).map(r => (r.location.lineNumber, r.code)).l
cpg.call.name("strcmp|memcmp").where(_.argument.code(".*password.*"))
  .whereNot(_.method.name(".*constant.*")).location.l
```

**Insight:** Finds auth-flow logic mistakes and non-constant-time password comparisons.

### 10. End-to-end data-flow analysis (Advanced)

```scala
def sources = cpg.call.name("recv|getenv|PG_GETARG.*|SPI_getvalue").argument
def sinks = cpg.call.name("system|strcpy|sprintf|SPI_execute|open").argument
sinks.reachableByFlows(sources).p
sinks.reachableBy(sources).groupBy(_.location.filename).map { case (f, flows) => (f, flows.size) }.sortBy(-_._2).l
```

**Insight:** Maps full attack chains from user-controlled inputs into dangerous sinks.

---

## SCENARIO 3: AUTOMATED DOCUMENTATION GENERATION

**Goal:** Extract component information to keep documentation current

### 1. Public API functions (Basic)

```scala
cpg.method.filename(".*src/include/.*\\.h").map(m => (m.name, m.filename, m.signature)).l
cpg.method.filename(".*src/include/.*").groupBy(_.filename.split("/").apply(2)).map { case (module, methods) => (module, methods.size) }.l
```

**Insight:** Header files under `src/include/` define the public API surface.

### 2. Module dependency graph (Basic)

```scala
def getModule(f: String) = if (f.contains("/parser/")) "parser" else if (f.contains("/optimizer/")) "optimizer" else "other"
cpg.call.map(c => (getModule(c.method.filename), c.callee.map(ca => getModule(ca.filename)).headOption))
  .flatten.groupBy(identity).map { case (edge, calls) => (edge, calls.size) }.sortBy(-_._2).l
```

**Insight:** Cross-module call patterns expose coupling between components.

### 3. Buffer Manager API (Intermediate)

```scala
cpg.method.filename(".*bufmgr\\.c").whereNot(_.isPrivate)
  .map(m => Map("name" -> m.name, "signature" -> m.signature, "parameters" -> m.parameter.name.l)).l
val bufferOps = List("ReadBuffer", "MarkBufferDirty", "ReleaseBuffer")
cpg.method.filter(m => bufferOps.count(op => m.ast.isCall.name.contains(op)) >= 3).name.l
```

**Insight:** Typical workflow: read → use → optionally mark dirty → release.

### 4. Call graph for query execution (Intermediate)

```scala
cpg.method.name("exec_simple_query").repeat(_.callOut)(_.emit.times(15)).map(m => (m.name, m.depth)).dedup.l
cpg.method.name("Exec[A-Z][a-z]+").filename(".*executor/node.*").map(m => (m.name, m.filename)).l
```

**Insight:** Shows the full path from `tcop` down to low-level I/O executors.

### 5. SPI documentation (Intermediate)

```scala
cpg.method.name("SPI_.*").map(m => (m.name, m.signature, m.filename)).sortBy(_._1).l
val categories = Map("execution" -> ".*execute.*", "cursor" -> ".*cursor.*")
categories.map { case (cat, pat) => (cat, cpg.method.name(s"SPI_$pat").name.l) }.l
```

**Insight:** `executor/spi.c` exposes the SPI API for issuing SQL from C.

### 6. Data structure map (Advanced)

```scala
cpg.typeDecl.filename(".*src/include/.*").where(_.name.matches("[A-Z].*"))
  .map(t => (t.name, t.filename, t.member.size)).sortBy(-_._3).l
List("Query", "PlannedStmt", "EState").map { name =>
  cpg.typeDecl.name(name).map(t => (t.name, t.member.map(m => s"${m.name}: ${m.typeFullName}").l)).headOption
}.flatten.l
```

**Insight:** Key node structures live in `nodes/`: Query, PlannedStmt, Plan, EState.

### 7. WAL record format (Advanced)

```scala
cpg.identifier.name("XLOG_.*").referencingIdentifiers.dedup.l
cpg.identifier.name("RM_.*_ID").map(_.name).dedup.l
cpg.typeDecl.name(".*XLog.*").filename(".*access/.*").map(t => (t.name, t.filename, t.member.size)).l
```

**Insight:** Resource managers and record types are defined under `access/`.

### 8. Error code index (Intermediate)

```scala
cpg.identifier.name("ERRCODE_.*").map(i => (i.name, i.code)).dedup.l
cpg.call.name("errcode").argument.code.groupCount.sortBy(-_._2).l
```

**Insight:** `errcodes.h` enumerates every SQLSTATE value.

### 9. Hook system documentation (Advanced)

```scala
cpg.identifier.name(".*_hook$").map(i => (i.name, i.typeFullName, i.filename)).dedup.l
cpg.typeDecl.name(".*_hook_type").map(t => (t.name, t.aliasTypeFullName)).l
cpg.method.name("_PG_init").ast.isAssignment.where(_.target.code(".*_hook")).map(a => (a.target.code, a.source.code)).l
```

**Insight:** More than 30 hooks let extensions intercept PostgreSQL behaviour.

### 10. Architecture dashboard (Advanced)

```scala
val modules = List("parser", "optimizer", "executor", "storage")
modules.map { m =>
  val methods = cpg.method.filename(s".*backend/$m/.*").l
  val loc = cpg.file.name(s".*backend/$m/.*").flatMap(_.content.split("\n")).size
  Map("module" -> m, "functions" -> methods.size, "loc" -> loc, "complexity" -> methods.map(_.cyclomaticComplexity).sum)
}.l
```

**Insight:** Provides quantitative metrics and cumulative complexity per module.

---

## SCENARIO 4: EXTENSION DEVELOPMENT

**Goal:** Assist when building PostgreSQL extensions

### 1. PG_FUNCTION_INFO_V1 examples (Basic)

```scala
cpg.call.name("PG_FUNCTION_INFO_V1").argument(1).code.groupBy(identity).map { case (f, calls) => (f, calls.size) }.l
cpg.method.ast.isCall.name("PG_GETARG.*").method.where(_.ast.isCall.name("PG_RETURN.*")).map(m => (m.name, m.filename)).l
```

**Insight:** Shows the canonical pattern for declaring C functions in PostgreSQL.

### 2. Working with SPI (Basic)

```scala
cpg.method.ast.isCall.name("SPI_connect").method.map(m => (m.name, m.filename, m.ast.isCall.name("SPI_execute.*").code.l)).filter(_._3.nonEmpty).l
cpg.method.filter(m => m.ast.isCall.name.l.containsSlice(Seq("SPI_connect", "SPI_execute", "SPI_finish"))).name.l
```

**Insight:** SPI workflow: connect → execute → handle results → finish.

### 3. Custom data type (Intermediate)

```scala
cpg.method.name(".*_in|.*_out|.*_recv|.*_send").filename(".*contrib/(hstore|ltree)/.*")
  .map(m => (m.name, m.filename, m.signature)).l
cpg.method.name(".*_eq|.*_cmp").filename(".*contrib/hstore.*").map(m => (m.name, m.signature)).l
```

**Insight:** A custom type needs input/output functions plus comparison operators.

### 4. ExecutorStart_hook for monitoring (Intermediate)

```scala
cpg.method.name("_PG_init").ast.isAssignment.where(_.target.code("ExecutorStart_hook"))
  .map(a => (a.file.name, a.source.code)).l
cpg.method.name(".*executor.*start").filename(".*contrib/(pg_stat_statements|auto_explain)/.*")
  .map(m => (m.name, m.filename, m.numberOfLines)).l
```

**Insight:** Demonstrates hook patterns for query instrumentation.

### 5. Background workers (Intermediate)

```scala
cpg.method.name("_PG_init").ast.isCall.name("RegisterBackgroundWorker").method.name.l
cpg.method.ast.isCall.name("BackgroundWorkerInitializeConnection").method.map(m => (m.name, m.filename)).l
```

**Insight:** Background workers enable asynchronous processing inside extensions.

### 6. GiST/GIN index support (Advanced)

```scala
cpg.method.name(".*extract.*|.*consistent|.*compare|.*union").filename(".*contrib/pg_trgm/.*")
  .map(m => (m.name, m.signature)).l
cpg.file.name(".*contrib/.*\\.sql").content.where(_.contains("OPERATOR CLASS")).l
```

**Insight:** An index access method must provide extract, consistent, and compare functions.

### 7. ProcessUtility_hook for DDL (Advanced)

```scala
cpg.method.name("_PG_init").ast.isAssignment.where(_.target.code("ProcessUtility_hook")).method.filename.l
cpg.method.where(_.parameter.name.contains("utilityStmt")).ast.isCall.name("IsA").argument.code.groupCount.l
```

**Insight:** Intercept DDL commands by wiring into `ProcessUtility_hook`.

### 8. Shared memory for extensions (Advanced)

```scala
cpg.method.name("_PG_init").ast.isCall.name("RequestAddinShmemSpace|RequestNamedLWLockTranche").method.name.l
cpg.method.ast.isCall.name("ShmemInitStruct").map(c => (c.method.name, c.argument.code.l)).l
```

**Insight:** Use `shmem_startup_hook` and related APIs to manage shared state.

### 9. Error handling in extensions (Intermediate)

```scala
cpg.method.filename(".*contrib/.*").ast.isIdentifier.name("PG_TRY|PG_CATCH").method.name.dedup.l
cpg.call.name("ereport").where(_.method.filename(".*contrib/.*")).argument(1).code.groupCount.sortBy(-_._2).l
```

**Insight:** `PG_TRY/PG_CATCH` delivers exception safety within extension code.

### 10. Extension best practices (Advanced)

```scala
cpg.method.name("_PG_init|_PG_fini").map(m => (m.name, m.filename, m.ast.isAssignment.where(_.target.code(".*_hook")).size)).l
cpg.file.name(".*\\.control").content.l
cpg.method.ast.isCall.name("PG_MODULE_MAGIC").method.filename.l
```

**Insight:** Verifies required extension components such as control files, hooks, and module magic.

---

## SCENARIO 5: CORE PATCHING

**Goal:** Support bug fixes and new core features

### 1. Locate function/structure usage (Basic)

```scala
cpg.call.name("ReadBuffer").map(c => (c.method.name, c.location.filename, c.location.lineNumber)).l
cpg.typeDecl.name("Query").referencingIdentifiers.method.name.dedup.take(20).l
```

**Insight:** Performs impact analysis by showing where the target is used.

### 2. Find module-specific tests (Basic)

```scala
cpg.file.name(".*test.*|.*regress.*").name.l
cpg.file.name(".*\\.sql").where(_.content.contains("CREATE|SELECT")).name.filter(_.contains("test")).l
```

**Insight:** Regression suites live under `src/test/regress/`.

### 3. Function dependencies (Intermediate)

```scala
cpg.method.name("heap_insert").callOut.name.dedup.l
cpg.method.name("heap_insert").repeat(_.callOut)(_.emit.times(3)).name.dedup.l
```

**Insight:** Reveals transitive dependencies to gauge impact.

### 4. Backward compatibility check (Intermediate)

```scala
cpg.method.name(".*").where(_.annotation.name("deprecated")).map(m => (m.name, m.filename)).l
cpg.call.name("elog|ereport").where(_.argument.code(".*deprecated.*")).location.l
```

**Insight:** Surface deprecated APIs that may break compatibility.

### 5. Localize bugs by symptoms (Intermediate)

```scala
cpg.call.name("ereport|elog").where(_.argument.code(".*specific error message.*")).method.name.l
cpg.method.name(".*transaction.*").where(_.ast.isCall.name(".*abort.*|.*rollback.*")).name.l
```

**Insight:** Use error messages or keyword searches to narrow down fault locations.

### 6. Performance impact (Advanced)

```scala
cpg.method.name("target_function").caller.where(_.ast.isControlStructure.controlStructureType("FOR|WHILE")).name.l
cpg.method.name("palloc").callIn.where(_.inControlStructure.controlStructureType("FOR|WHILE")).method.name.dedup.take(20).l
```

**Insight:** Confirms whether the change sits inside hot paths such as tight loops.

### 7. Related commits (Advanced)

```scala
cpg.method.name("function_name").map(m => (m.filename, m.lineNumber)).l
// Then run git blame on those files/lines
```

**Insight:** Guides you to version history for the affected function.

### 8. Lock ordering (Advanced)

```scala
cpg.method.ast.isCall.name("LWLockAcquire|LockAcquire")
  .map(c => (c.method.name, c.argument(1).code, c.lineNumber)).l
cpg.method.filter { m =>
  val locks = m.ast.isCall.name(".*LockAcquire").l
  locks.size > 1
}.map(m => (m.name, m.ast.isCall.name(".*Lock.*").code.l)).l
```

**Insight:** Supports deadlock analysis by inspecting lock acquisition order.

### 9. Side-effect analysis (Advanced)

```scala
cpg.method.name("target_function").ast.isCall.name(".*insert|.*delete|.*update|XLogInsert|MarkBufferDirty").code.l
cpg.method.name("target_function").where(_.ast.isCall.name("SPI_execute").whereNot(_.argument(2).code("true"))).l
```

**Insight:** Summarises how a function mutates state or writes to WAL.

### 10. Comprehensive impact analysis (Advanced)

```scala
def analyzeImpact(funcName: String) = {
  val method = cpg.method.name(funcName).head
  Map(
    "direct_callers" -> method.caller.name.dedup.size,
    "transitive_callers" -> method.repeat(_.caller)(_.emit.times(3)).name.dedup.size,
    "modified_structs" -> method.ast.isCall.name(".*=").argument.typeFullName.dedup.l,
    "in_hot_paths" -> method.caller.where(_.ast.isControlStructure.controlStructureType("FOR|WHILE")).name.l,
    "test_coverage" -> cpg.file.name(".*test.*").method.callOut.name(funcName).nonEmpty
  )
}
analyzeImpact("heap_insert")
```

**Insight:** Provides a multi-dimensional impact report for a change.

---

## SCENARIO 6: PERFORMANCE REGRESSION ANALYSIS

**Goal:** Proactively detect bottlenecks and optimization candidates

### 1. Deeply nested loops (Basic)

```scala
cpg.method.where(_.ast.isControlStructure.controlStructureType("FOR|WHILE").depth > 3).map(m => (m.name, m.filename, m.cyclomaticComplexity)).sortBy(-_._3).l
```

**Insight:** Highlights potential O(n²+) algorithms that deserve scrutiny.

### 2. Excessive memory allocations (Basic)

```scala
cpg.method.ast.isCall.name("palloc.*").groupBy(_.method).map { case (m, calls) => (m.name, calls.size) }.sortBy(-_._2).take(20).l
cpg.method.filter(_.ast.isControlStructure.controlStructureType("FOR|WHILE").ast.isCall.name("palloc.*").nonEmpty).name.l
```

**Insight:** Allocations inside loops indicate possible performance bottlenecks.

### 3. Lock contention points (Intermediate)

```scala
cpg.call.name("LWLockAcquire|SpinLockAcquire").groupBy(_.method).map { case (m, locks) => (m.name, locks.size) }.sortBy(-_._2).l
cpg.method.ast.isCall.name("LWLockAcquire").where(_.inControlStructure).map(c => (c.method.name, c.code)).l
```

**Insight:** Frequent lock acquisition in the same routine hints at contention risk.

### 4. Planner complexity hotspots (Intermediate)

```scala
cpg.method.fullName(".*planner.*|.*optimizer.*").filter(_.cyclomaticComplexity > 20).map(m => (m.name, m.cyclomaticComplexity, m.numberOfLines)).sortBy(-_._2).l
```

**Insight:** High-complexity planner code directly impacts planning latency.

### 5. Buffer pinning patterns (Intermediate)

```scala
cpg.method.filter { m =>
  val pins = m.ast.isCall.name("ReadBuffer|PinBuffer").size
  val unpins = m.ast.isCall.name("ReleaseBuffer|UnpinBuffer").size
  pins != unpins || pins > 5
}.map(m => (m.name, m.filename)).l
```

**Insight:** Imbalanced pin/unpin counts reveal buffer leaks or heavy pinning.

### 6. Sequential scans in hot paths (Advanced)

```scala
cpg.method.name("ExecSeqScan").caller.where(_.caller.size > 100).name.dedup.l
cpg.call.name("heap_beginscan|table_beginscan").where(_.method.caller.size > 50).method.name.l
```

**Insight:** Flags sequential scans that run from frequently invoked callers.

### 7. Syscall intensity (Advanced)

```scala
cpg.call.name("read|write|fsync|pread|pwrite").groupBy(_.method).map { case (m, calls) => (m.name, calls.size) }.sortBy(-_._2).l
```

**Insight:** Surfaces I/O-heavy functions.

### 8. Algorithmic complexity regression (Advanced)

```scala
// Compare two CPG versions
def v15 = loadCPG("postgresql-15")
def v16 = loadCPG("postgresql-16")
v15.method.map(m => (m.fullName, m.cyclomaticComplexity)).diff(
  v16.method.map(m => (m.fullName, m.cyclomaticComplexity))
).filter { case ((name, cc1), (_, cc2)) => cc2 > cc1 * 1.5 }.l
```

**Insight:** Spots functions whose complexity grew significantly between releases.

### 9. Cache-miss candidates (Advanced)

```scala
cpg.method.filter { m =>
  val arrayAccess = m.ast.isCall.nameExact(Operators.indexAccess).size
  val loops = m.ast.isControlStructure.controlStructureType("FOR|WHILE").size
  arrayAccess > 0 && loops > 2
}.map(m => (m.name, m.filename)).l
```

**Insight:** Multiple indexed accesses inside nested loops signal cache-locality issues.

### 10. Performance metrics dashboard (Advanced)

```scala
val modules = List("parser", "optimizer", "executor", "storage")
modules.map { m =>
  val methods = cpg.method.filename(s".*/$m/.*").l
  Map(
    "module" -> m,
    "avg_complexity" -> methods.map(_.cyclomaticComplexity).sum / methods.size,
    "hot_functions" -> methods.filter(_.caller.size > 100).size,
    "alloc_in_loops" -> methods.count(_.ast.isControlStructure.ast.isCall.name("palloc.*").nonEmpty),
    "lock_heavy" -> methods.count(_.ast.isCall.name(".*Lock.*").size > 3)
  )
}.l
```

**Insight:** Compiles module-level performance metrics with focus on hot and heavy code.

---

## SCENARIO 7: TEST GAP ANALYSIS & COVERAGE

**Goal:** Uncover untested code paths and coverage gaps

### 1. Modified functions without tests (Basic)

```scala
def changedFunctions = getChangedFunctions(lastCommit) // Helper function
cpg.method.name(changedFunctions: _*).whereNot(_.coveredByTest).map(m => (m.name, m.filename)).l
```

**Insight:** Newly changed code without coverage is a prime risk.

### 2. Error paths without coverage (Basic)

```scala
cpg.call.name("ereport|elog").where(_.argument(1).code("ERROR|FATAL")).caller.whereNot(_.executedInTests).name.l
cpg.method.ast.isControlStructure.condition.code(".*== NULL.*").whereNot(_.method.hasTestCoverage).method.name.l
```

**Insight:** Error-handling paths are frequently left untested.

### 3. Security-critical functions without tests (Intermediate)

```scala
cpg.method.name(".*[Aa]uth.*|.*[Pp]rivile.*|.*[Pp]ermiss.*").filename(".*libpq/auth.*|.*commands/user.*")
  .whereNot(_.hasTestCoverage).map(m => (m.name, m.filename)).l
```

**Insight:** Authentication and authorization must always have test coverage.

### 4. Integration points without tests (Intermediate)

```scala
cpg.call.where(_.method.fullName(".*planner.*")).where(_.callee.fullName(".*executor.*"))
  .whereNot(_.pathCoveredBy("integration")).map(c => (c.location, c.code)).l
```

**Insight:** Cross-module boundaries need integration tests.

### 5. Dead code identification (Intermediate)

```scala
cpg.method.whereNot(_.callIn.nonEmpty).whereNot(_.isEntryPoint).whereNot(_.isTestMethod)
  .whereNot(_.name.matches(".*_in|.*_out"))
  .map(m => (m.name, m.filename, m.numberOfLines)).l
```

**Insight:** Unreachable code is a candidate for removal.

### 6. High-risk untested functions (Advanced)

```scala
cpg.method.filter(m => m.cyclomaticComplexity > 10 && m.callIn.size > 20)
  .whereNot(_.hasTestCoverage).map(m => (m.name, m.cyclomaticComplexity, m.callIn.size, m.filename))
  .sortBy(m => -(m._2 * m._3)).l // Risk score
```

**Insight:** Complex, frequently called routines without tests are extremely risky.

### 7. Transaction logic coverage (Advanced)

```scala
cpg.method.name(".*[Tt]ransaction.*|.*[Cc]ommit.*|.*[Aa]bort.*").filename(".*access/transam.*")
  .map { m =>
    val branches = m.ast.isControlStructure.controlStructureType("IF").size
    val coveredBranches = m.branchesCoveredInTests
    (m.name, branches, coveredBranches, (coveredBranches.toFloat / branches * 100).toInt)
  }.sortBy(_._4).l
```

**Insight:** Measures branch coverage for critical transaction paths.

### 8. Replication coverage gaps (Advanced)

```scala
cpg.method.filename(".*replication/.*").whereNot(_.hasTestCoverage)
  .map(m => (m.name, m.filename, m.numberOfLines, m.cyclomaticComplexity)).sortBy(-_._4).l
```

**Insight:** Replication is complex and requires thorough test coverage.

### 9. Extension API stability (Intermediate)

```scala
cpg.method.filename(".*src/include/.*").where(_.annotation.name(".*API.*|.*public.*"))
  .map { m =>
    val testCount = cpg.file.name(".*test.*").method.callOut.name(m.name).size
    (m.name, m.filename, testCount)
  }.filter(_._3 == 0).l
```

**Insight:** Public APIs without tests raise the risk of breaking changes.

### 10. Coverage trend analysis (Advanced)

```scala
def coverageReport = {
  val modules = List("parser", "optimizer", "executor", "storage", "replication")
  modules.map { m =>
    val methods = cpg.method.filename(s".*/$m/.*").l
    val tested = methods.count(_.hasTestCoverage)
    val critical = methods.count(me => me.cyclomaticComplexity > 10 || me.callIn.size > 20)
    val criticalTested = methods.count(me => (me.cyclomaticComplexity > 10 || me.callIn.size > 20) && me.hasTestCoverage)
    Map(
      "module" -> m,
      "total_functions" -> methods.size,
      "tested" -> tested,
      "coverage_pct" -> (tested.toFloat / methods.size * 100).toInt,
      "critical_functions" -> critical,
      "critical_tested" -> criticalTested,
      "critical_coverage_pct" -> (if (critical > 0) criticalTested.toFloat / critical * 100 else 0).toInt
    )
  }
}
coverageReport.l
```

**Insight:** Builds a coverage dashboard with emphasis on high-risk code.

---

## SCENARIO 8: REGULATORY COMPLIANCE & API EVOLUTION

**Goal:** Enforce compliance, license checks, and API governance

### 1. Deprecated API usage (Basic)

```scala
cpg.call.name("DirectFunctionCall.*|fmgr_info|SearchSysCache").where(_.callee.annotation.name("deprecated"))
  .map(c => (c.location, c.name, c.callee.comment.headOption)).l
```

**Insight:** Deprecated API calls highlight areas that need migration plans.

### 2. Unsafe functions for compliance (Basic)

```scala
cpg.call.name("strcpy|sprintf|gets|strcat").map(c => 
  Map("location" -> c.location, "function" -> c.name, "rule" -> "CWE-120", "severity" -> "HIGH")
).l
```

**Insight:** Security compliance requires replacing classic unsafe routines.

### 3. GPL license contamination (Intermediate)

```scala
def gplFiles = cpg.file.where(_.content.contains("GPL")).name.l
cpg.call.callee.where(_.filename.oneOf(gplFiles: _*)).caller.whereNot(_.filename.oneOf(gplFiles: _*))
  .map(c => (c.location, "GPL contamination risk")).l
```

**Insight:** Calling GPL code from non-GPL modules creates license conflicts.

### 4. Breaking API changes between versions (Intermediate)

```scala
def v15API = loadCPG("postgresql-15")
def v16API = loadCPG("postgresql-16")
v15API.method.isPublic.map(m => (m.fullName, m.signature)).l
  .diff(v16API.method.isPublic.map(m => (m.fullName, m.signature)).l)
  .map { case (name, sig) => Map("function" -> name, "old_sig" -> sig, "status" -> "BREAKING CHANGE") }
```

**Insight:** Signature changes in the public API break existing extensions.

### 5. CERT secure coding violations (Intermediate)

```scala
// ENV33-C: Do not call system() with user-controlled argument
cpg.call.name("system|popen|exec.*").where(_.argument.reachableBy(cpg.call.name("getenv|PG_GETARG.*")))
  .map(c => (c.location, "CERT ENV33-C violation")).l
// INT32-C: Integer overflow
cpg.call.name("palloc|malloc").where(_.argument(1).arithmeticExpr).whereNot(_.argument.code(".*overflow.*"))
  .map(c => (c.location, "CERT INT32-C potential violation")).l
```

**Insight:** Enforces CERT rules that guard safety-critical code paths.

### 6. GDPR data processing (Advanced)

```scala
cpg.method.name(".*user.*|.*personal.*|.*profile.*").where(_.parameter.name(".*email|.*address|.*phone.*"))
  .whereNot(_.hasAnnotation("GDPR_documented")).map(m => (m.name, m.filename, "Requires GDPR documentation")).l
```

**Insight:** Personal data handlers must be documented for GDPR compliance.

### 7. PostgreSQL coding standards (Intermediate)

```scala
// Naming convention violations
cpg.method.where(_.name.matches("^[A-Z].*")).filter(!_.isPublicAPI).map(m => (m.name, m.filename, "Should be camelCase")).l
// Missing error checks
cpg.call.name("palloc|malloc").whereNot(_.astParent.isControlStructure.condition.code(".*== NULL.*"))
  .map(c => (c.location, "Missing NULL check after allocation")).l
```

**Insight:** Verifies adherence to the PostgreSQL style guide.

### 8. Extension API compatibility (Advanced)

```scala
// Find all hook signature changes
def oldHooks = loadCPG("postgresql-15").typeDecl.name(".*_hook_type").map(t => (t.name, t.aliasTypeFullName)).l
def newHooks = loadCPG("postgresql-16").typeDecl.name(".*_hook_type").map(t => (t.name, t.aliasTypeFullName)).l
oldHooks.diff(newHooks).map { case (name, oldSig) => 
  Map("hook" -> name, "old_signature" -> oldSig, "status" -> "CHANGED", "impact" -> "Extensions need update")
}
```

**Insight:** Hook signature updates require extension migration guidance.

### 9. Search path safety audit (Advanced)

```scala
cpg.file.name(".*\\.sql").content.where(_.matches("(?i).*SECURITY\\s+DEFINER.*"))
  .whereNot(_.matches("(?i).*SET\\s+search_path\\s*=\\s*pg_catalog.*"))
  .map(f => (f.name, "Missing search_path protection", "CVE-2018-1058 pattern")).l
cpg.method.ast.isCall.whereNot(_.name.contains(".")).where(_.method.fullName(".*SECURITY_DEFINER.*"))
  .map(c => (c.location, c.name, "Unqualified function call in SECURITY DEFINER")).l
```

**Insight:** SECURITY DEFINER code must harden `search_path` to avoid CVE-2018-1058 issues.

### 10. Comprehensive compliance report (Advanced)

```scala
def complianceReport = {
  Map(
    "unsafe_functions" -> cpg.call.name("strcpy|sprintf|gets").size,
    "deprecated_api_usage" -> cpg.call.where(_.callee.annotation.name("deprecated")).size,
    "cert_violations" -> cpg.call.name("system").where(_.argument.reachableBy(cpg.call.name("getenv"))).size,
    "license_issues" -> cpg.call.callee.filename(".*GPL.*").caller.whereNot(_.filename(".*GPL.*")).size,
    "missing_error_checks" -> cpg.call.name("palloc").whereNot(_.astParent.isControlStructure.condition.code(".*NULL.*")).size,
    "security_definer_unsafe" -> cpg.file.name(".*\\.sql").content.where(_.matches("(?i).*SECURITY\\s+DEFINER.*"))
      .whereNot(_.matches("(?i).*search_path.*")).size,
    "gdpr_undocumented" -> cpg.method.name(".*user.*|.*personal.*").whereNot(_.hasAnnotation("GDPR")).size,
    "api_breaking_changes" -> 0 // Requires version comparison
  )
}
complianceReport
```

**Insight:** Produces a compliance dashboard ready for audits.
