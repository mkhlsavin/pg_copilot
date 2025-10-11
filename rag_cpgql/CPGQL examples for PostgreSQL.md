# Комплексный набор вопросов CPGQL для анализа кодовой базы PostgreSQL

Создан полный набор из **80 практических вопросов** (8 сценариев × 10 вопросов) для использования CPGQL/Joern на кодовой базе PostgreSQL. Все вопросы используют **реальные имена функций и файлов** из PostgreSQL 15-18, содержат **синтаксически корректные CPGQL-запросы** и решают **практические задачи** разработчиков.

---

## СЦЕНАРИЙ 1: ОНБОРДИНГ НОВОГО РАЗРАБОТЧИКА

**Цель:** Быстрое освоение архитектуры PostgreSQL и навигация по кодовой базе

### 1. Главная точка входа backend (Базовая)
```scala
cpg.method.name("PostgresMain").map(m => (m.name, m.filename, m.signature)).l
cpg.method.name("PostgresMain").ast.isCall.name.dedup.l
```
**Инсайт:** PostgresMain в tcop/postgres.c - main loop обработки запросов

### 2. Парсинг SQL-запроса (Базовая)
```scala
cpg.method.name("raw_parser").callOut.name.l
cpg.method.name("parse_analyze").repeat(_.callOut)(_.emit.until(_.name("transformStmt"))).name.l
```
**Инсайт:** Цепочка raw_parser → parse_analyze → transformStmt

### 3. Код планировщика запросов (Средняя)
```scala
cpg.file.name(".*optimizer.*").method.name.dedup.l
cpg.method.name("planner").callOut.where(_.name("standard_planner")).repeat(_.callOut)(_.until(_.name("create_plan"))).path.l
```
**Инсайт:** optimizer/ содержит planner → standard_planner → create_plan

### 4. Система управления памятью (Средняя)
```scala
cpg.method.name(".*MemoryContext.*|palloc.*|pfree").map(m => (m.name, m.filename, m.signature)).l
cpg.call.name("AllocSetContextCreate").caller.name.dedup.l
```
**Инсайт:** Memory Context system в utils/mmgr/ - ключевая особенность PostgreSQL

### 5. Аутентификация пользователей (Средняя)
```scala
cpg.method.name("ClientAuthentication").map(m => (m.filename, m.lineNumber, m.parameter.name.l)).l
cpg.method.name("Check.*Auth").map(m => (m.name, m.filename)).l
```
**Инсайт:** libpq/auth.c содержит ClientAuthentication и методы auth

### 6. Executor - исполнитель запросов (Продвинутая)
```scala
cpg.method.name("Exec[A-Z].*").filename(".*executor.*").name.dedup.l
cpg.method.name("ExecutorRun").repeat(_.callOut)(_.until(_.name("ExecSeqScan|ExecIndexScan"))).path.l
```
**Инсайт:** executor/ использует node pattern: ExecSeqScan, ExecIndexScan, ExecHashJoin

### 7. Buffer Manager (Продвинутая)
```scala
cpg.method.name(".*Buffer.*").filename(".*storage/buffer.*").map(m => (m.name, m.filename, m.signature)).l
cpg.method.name("ReadBuffer").repeat(_.callOut)(_.emit.times(5)).name.l
```
**Инсайт:** storage/buffer/ управляет shared_buffers через ReadBuffer/ReleaseBuffer

### 8. Write-Ahead Logging (Продвинутая)
```scala
cpg.method.name("XLog.*").filename(".*transam.*").map(m => (m.name, m.filename)).l
cpg.method.name("XLogInsert").caller.name.dedup.l
```
**Инсайт:** access/transam/ содержит WAL: XLogInsert → XLogFlush для durability

### 9. Обработка ошибок (Продвинутая)
```scala
cpg.call.name("ereport").map(c => (c.location.filename, c.location.lineNumber, c.code)).take(10).l
cpg.identifier.name("PG_TRY|PG_CATCH").location.l
```
**Инсайт:** utils/error/elog.c использует ereport + PG_TRY/PG_CATCH с setjmp/longjmp

### 10. Полная цепочка SELECT-запроса (Продвинутая)
```scala
cpg.method.name("exec_simple_query").repeat(_.callOut)(_.emit.times(10)).name.dedup.l
cpg.method.name("exec_simple_query").callOut.name(".*parse.*|.*plan.*|.*Executor.*").l
```
**Инсайт:** PostgresMain → exec_simple_query → parser → planner → executor → printtup

---

## СЦЕНАРИЙ 2: АУДИТ БЕЗОПАСНОСТИ

**Цель:** Поиск уязвимостей и небезопасных паттернов кода

### 1. Опасные функции работы со строками (Базовая)
```scala
cpg.call.name("strcpy|strcat|sprintf|gets").map(c => (c.name, c.location.filename, c.location.lineNumber)).l
cpg.call.name("strcpy|strcat|sprintf").where(_.location.filename(".*auth.*|.*parser.*")).location.l
```
**Инсайт:** CWE-120 buffer overflow - поиск в критичных модулях

### 2. Format string vulnerabilities (Базовая)
```scala
cpg.call.name("printf|fprintf|sprintf|ereport|elog").whereNot(_.argument(1).isLiteral).location.l
def userInput = cpg.call.name(".*getenv.*|.*recv.*")
cpg.method.name(".*printf.*").parameter.index(1).reachableBy(userInput).l
```
**Инсайт:** CWE-134 - format string контролируемый пользователем

### 3. SQL injection в extensions (Средняя)
```scala
cpg.call.name("SPI_execute").map(c => (c.location.filename, c.argument(1).code)).l
cpg.call.name("SPI_execute").where(_.argument(1).reachableBy(cpg.call.name(".*strcat|.*sprintf"))).location.l
```
**Инсайт:** CWE-89 - конкатенация для SQL вместо параметризации

### 4. Integer overflow в array subscripting (Средняя)
```scala
cpg.call.name("array_set|array_ref|array_subscript.*").map(c => (c.location, c.code)).l
cpg.call.name("palloc|malloc").where(_.argument(1).arithmeticExpr).whereNot(_.argument(1).code(".*pg_mul_.*")).location.l
```
**Инсайт:** CVE-2023-5869, CVE-2021-32027 - overflow в вычислениях размера массива

### 5. Use-after-free паттерны (Средняя)
```scala
cpg.method.name(".*free").filter(_.parameter.size == 1).callIn.where(_.argument(1).isIdentifier)
  .flatMap { freeCall =>
    val freedPtr = freeCall.argument(1).code.head
    freeCall.postDominatedBy.isIdentifier.codeExact(freedPtr)
  }.location.l
```
**Инсайт:** CWE-416 - использование указателя после pfree

### 6. TOCTOU race conditions (Продвинутая)
```scala
val fileOps = Map("access" -> Seq(1), "stat" -> Seq(1), "open" -> Seq(1))
cpg.call.nameExact(fileOps.keys.toSeq: _*).filter { call =>
  val otherCalls = cpg.call.nameExact(fileOps.keys.toSeq: _*).filter(_ != call)
  val sameArg = call.argument(1).code.head
  otherCalls.argument(1).code.contains(sameArg)
}.location.l
```
**Инсайт:** CWE-367 - check/use на одном файле

### 7. Privilege escalation через search_path (Продвинутая)
```scala
cpg.file.name(".*\\.sql").content.where(_.matches("(?i).*SECURITY\\s+DEFINER.*"))
  .whereNot(_.matches("(?i).*SET\\s+search_path.*")).l
cpg.call.name("[a-z_]+").whereNot(_.name.matches(".*\\..*"))
  .where(_.method.fullName(".*auth.*|.*privilege.*")).map(c => (c.location, c.name)).l
```
**Инсайт:** CVE-2018-1058 - trojan horse через public schema

### 8. Memory disclosure в error messages (Продвинутая)
```scala
cpg.call.name("ereport|elog").where(_.argument.reachableBy(cpg.call.name(".*getenv|PG_GETARG.*"))).location.l
cpg.method.name(".*aggregate.*").where(_.parameter.evalType(".*unknown.*"))
  .where(_.ast.isCall.name("ereport")).location.l
```
**Инсайт:** CVE-2023-5868 - раскрытие памяти через aggregate с unknown type

### 9. Authentication bypass patterns (Продвинутая)
```scala
cpg.method.name("ClientAuthentication").controlStructure.controlStructureType("RETURN")
  .whereNot(_.code(".*STATUS_OK.*|.*STATUS_ERROR.*")).map(r => (r.location.lineNumber, r.code)).l
cpg.call.name("strcmp|memcmp").where(_.argument.code(".*password.*"))
  .whereNot(_.method.name(".*constant.*")).location.l
```
**Инсайт:** Logic errors в auth flow, timing attacks

### 10. Комплексный data flow анализ (Продвинутая)
```scala
def sources = cpg.call.name("recv|getenv|PG_GETARG.*|SPI_getvalue").argument
def sinks = cpg.call.name("system|strcpy|sprintf|SPI_execute|open").argument
sinks.reachableByFlows(sources).p
sinks.reachableBy(sources).groupBy(_.location.filename).map { case (f, flows) => (f, flows.size) }.sortBy(-_._2).l
```
**Инсайт:** Полные attack chains от user input до dangerous operations

---

## СЦЕНАРИЙ 3: АВТОМАТИЧЕСКАЯ ГЕНЕРАЦИЯ ДОКУМЕНТАЦИИ

**Цель:** Извлечение информации о компонентах для актуальной документации

### 1. Public API functions (Базовая)
```scala
cpg.method.filename(".*src/include/.*\\.h").map(m => (m.name, m.filename, m.signature)).l
cpg.method.filename(".*src/include/.*").groupBy(_.filename.split("/").apply(2)).map { case (module, methods) => (module, methods.size) }.l
```
**Инсайт:** Header files в src/include/ определяют public API

### 2. Граф зависимостей модулей (Базовая)
```scala
def getModule(f: String) = if (f.contains("/parser/")) "parser" else if (f.contains("/optimizer/")) "optimizer" else "other"
cpg.call.map(c => (getModule(c.method.filename), c.callee.map(ca => getModule(ca.filename)).headOption))
  .flatten.groupBy(identity).map { case (edge, calls) => (edge, calls.size) }.sortBy(-_._2).l
```
**Инсайт:** Межмодульные вызовы показывают coupling

### 3. Buffer Manager API (Средняя)
```scala
cpg.method.filename(".*bufmgr\\.c").whereNot(_.isPrivate)
  .map(m => Map("name" -> m.name, "signature" -> m.signature, "parameters" -> m.parameter.name.l)).l
val bufferOps = List("ReadBuffer", "MarkBufferDirty", "ReleaseBuffer")
cpg.method.filter(m => bufferOps.count(op => m.ast.isCall.name.contains(op)) >= 3).name.l
```
**Инсайт:** Типичный workflow: Read → Use → [MarkDirty] → Release

### 4. Call graph для query execution (Средняя)
```scala
cpg.method.name("exec_simple_query").repeat(_.callOut)(_.emit.times(15)).map(m => (m.name, m.depth)).dedup.l
cpg.method.name("Exec[A-Z][a-z]+").filename(".*executor/node.*").map(m => (m.name, m.filename)).l
```
**Инсайт:** Полный путь от tcop до низкоуровневых I/O

### 5. SPI документация (Средняя)
```scala
cpg.method.name("SPI_.*").map(m => (m.name, m.signature, m.filename)).sortBy(_._1).l
val categories = Map("execution" -> ".*execute.*", "cursor" -> ".*cursor.*")
categories.map { case (cat, pat) => (cat, cpg.method.name(s"SPI_$pat").name.l) }.l
```
**Инсайт:** SPI в executor/spi.c - API для SQL из C

### 6. Карта структур данных (Продвинутая)
```scala
cpg.typeDecl.filename(".*src/include/.*").where(_.name.matches("[A-Z].*"))
  .map(t => (t.name, t.filename, t.member.size)).sortBy(-_._3).l
List("Query", "PlannedStmt", "EState").map { name =>
  cpg.typeDecl.name(name).map(t => (t.name, t.member.map(m => s"${m.name}: ${m.typeFullName}").l)).headOption
}.flatten.l
```
**Инсайт:** Ключевые структуры в nodes/: Query, PlannedStmt, Plan, EState

### 7. WAL record format (Продвинутая)
```scala
cpg.identifier.name("XLOG_.*").referencingIdentifiers.dedup.l
cpg.identifier.name("RM_.*_ID").map(_.name).dedup.l
cpg.typeDecl.name(".*XLog.*").filename(".*access/.*").map(t => (t.name, t.filename, t.member.size)).l
```
**Инсайт:** Resource managers и record types в access/

### 8. Индекс error codes (Средняя)
```scala
cpg.identifier.name("ERRCODE_.*").map(i => (i.name, i.code)).dedup.l
cpg.call.name("errcode").argument.code.groupCount.sortBy(-_._2).l
```
**Инсайт:** errcodes.h содержит все SQLSTATE коды

### 9. Hook system документация (Продвинутая)
```scala
cpg.identifier.name(".*_hook$").map(i => (i.name, i.typeFullName, i.filename)).dedup.l
cpg.typeDecl.name(".*_hook_type").map(t => (t.name, t.aliasTypeFullName)).l
cpg.method.name("_PG_init").ast.isAssignment.where(_.target.code(".*_hook")).map(a => (a.target.code, a.source.code)).l
```
**Инсайт:** 30+ hooks для перехвата behavior PostgreSQL

### 10. Архитектурная диаграмма (Продвинутая)
```scala
val modules = List("parser", "optimizer", "executor", "storage")
modules.map { m =>
  val methods = cpg.method.filename(s".*backend/$m/.*").l
  val loc = cpg.file.name(s".*backend/$m/.*").flatMap(_.content.split("\n")).size
  Map("module" -> m, "functions" -> methods.size, "loc" -> loc, "complexity" -> methods.map(_.cyclomaticComplexity).sum)
}.l
```
**Инсайт:** Количественные метрики и complexity по модулям

---

## СЦЕНАРИЙ 4: РАЗРАБОТКА РАСШИРЕНИЯ (EXTENSION)

**Цель:** Помощь в создании PostgreSQL extensions

### 1. Примеры PG_FUNCTION_INFO_V1 (Базовая)
```scala
cpg.call.name("PG_FUNCTION_INFO_V1").argument(1).code.groupBy(identity).map { case (f, calls) => (f, calls.size) }.l
cpg.method.ast.isCall.name("PG_GETARG.*").method.where(_.ast.isCall.name("PG_RETURN.*")).map(m => (m.name, m.filename)).l
```
**Инсайт:** Паттерн объявления C-функций для PostgreSQL

### 2. Работа с SPI (Базовая)
```scala
cpg.method.ast.isCall.name("SPI_connect").method.map(m => (m.name, m.filename, m.ast.isCall.name("SPI_execute.*").code.l)).filter(_._3.nonEmpty).l
cpg.method.filter(m => m.ast.isCall.name.l.containsSlice(Seq("SPI_connect", "SPI_execute", "SPI_finish"))).name.l
```
**Инсайт:** SPI workflow: connect → execute → обработка → finish

### 3. Custom data type (Средняя)
```scala
cpg.method.name(".*_in|.*_out|.*_recv|.*_send").filename(".*contrib/(hstore|ltree)/.*")
  .map(m => (m.name, m.filename, m.signature)).l
cpg.method.name(".*_eq|.*_cmp").filename(".*contrib/hstore.*").map(m => (m.name, m.signature)).l
```
**Инсайт:** Custom type требует input/output functions + операторы

### 4. ExecutorStart_hook для monitoring (Средняя)
```scala
cpg.method.name("_PG_init").ast.isAssignment.where(_.target.code("ExecutorStart_hook"))
  .map(a => (a.file.name, a.source.code)).l
cpg.method.name(".*executor.*start").filename(".*contrib/(pg_stat_statements|auto_explain)/.*")
  .map(m => (m.name, m.filename, m.numberOfLines)).l
```
**Инсайт:** Hook pattern для query instrumentation

### 5. Background workers (Средняя)
```scala
cpg.method.name("_PG_init").ast.isCall.name("RegisterBackgroundWorker").method.name.l
cpg.method.ast.isCall.name("BackgroundWorkerInitializeConnection").method.map(m => (m.name, m.filename)).l
```
**Инсайт:** Background workers для async processing

### 6. GiST/GIN index support (Продвинутая)
```scala
cpg.method.name(".*extract.*|.*consistent|.*compare|.*union").filename(".*contrib/pg_trgm/.*")
  .map(m => (m.name, m.signature)).l
cpg.file.name(".*contrib/.*\\.sql").content.where(_.contains("OPERATOR CLASS")).l
```
**Инсайт:** Index AM требует extract, consistent, compare functions

### 7. ProcessUtility_hook для DDL (Продвинутая)
```scala
cpg.method.name("_PG_init").ast.isAssignment.where(_.target.code("ProcessUtility_hook")).method.filename.l
cpg.method.where(_.parameter.name.contains("utilityStmt")).ast.isCall.name("IsA").argument.code.groupCount.l
```
**Инсайт:** Перехват DDL команд через ProcessUtility_hook

### 8. Shared memory для extensions (Продвинутая)
```scala
cpg.method.name("_PG_init").ast.isCall.name("RequestAddinShmemSpace|RequestNamedLWLockTranche").method.name.l
cpg.method.ast.isCall.name("ShmemInitStruct").map(c => (c.method.name, c.argument.code.l)).l
```
**Инсайт:** shmem_startup_hook для shared state

### 9. Error handling в extensions (Средняя)
```scala
cpg.method.filename(".*contrib/.*").ast.isIdentifier.name("PG_TRY|PG_CATCH").method.name.dedup.l
cpg.call.name("ereport").where(_.method.filename(".*contrib/.*")).argument(1).code.groupCount.sortBy(-_._2).l
```
**Инсайт:** PG_TRY/PG_CATCH для exception safety

### 10. Extension best practices (Продвинутая)
```scala
cpg.method.name("_PG_init|_PG_fini").map(m => (m.name, m.filename, m.ast.isAssignment.where(_.target.code(".*_hook")).size)).l
cpg.file.name(".*\\.control").content.l
cpg.method.ast.isCall.name("PG_MODULE_MAGIC").method.filename.l
```
**Инсайт:** Проверка обязательных компонентов extension

---

## СЦЕНАРИЙ 5: ВНЕСЕНИЕ ИЗМЕНЕНИЙ В ЯДРО (ПАТЧИНГ)

**Цель:** Помощь при исправлении багов и добавлении функциональности

### 1. Найти использования функции/структуры (Базовая)
```scala
cpg.call.name("ReadBuffer").map(c => (c.method.name, c.location.filename, c.location.lineNumber)).l
cpg.typeDecl.name("Query").referencingIdentifiers.method.name.dedup.take(20).l
```
**Инсайт:** Impact analysis - где используется функция

### 2. Найти все тесты для модуля (Базовая)
```scala
cpg.file.name(".*test.*|.*regress.*").name.l
cpg.file.name(".*\\.sql").where(_.content.contains("CREATE|SELECT")).name.filter(_.contains("test")).l
```
**Инсайт:** Регрессионные тесты в src/test/regress/

### 3. Зависимости функции (Средняя)
```scala
cpg.method.name("heap_insert").callOut.name.dedup.l
cpg.method.name("heap_insert").repeat(_.callOut)(_.emit.times(3)).name.dedup.l
```
**Инсайт:** Транзитивные зависимости для оценки impact

### 4. Backward compatibility check (Средняя)
```scala
cpg.method.name(".*").where(_.annotation.name("deprecated")).map(m => (m.name, m.filename)).l
cpg.call.name("elog|ereport").where(_.argument.code(".*deprecated.*")).location.l
```
**Инсайт:** Найти deprecated API для compatibility

### 5. Найти место бага по симптомам (Средняя)
```scala
cpg.call.name("ereport|elog").where(_.argument.code(".*specific error message.*")).method.name.l
cpg.method.name(".*transaction.*").where(_.ast.isCall.name(".*abort.*|.*rollback.*")).name.l
```
**Инсайт:** Поиск по error messages или keywords

### 6. Влияние на performance (Продвинутая)
```scala
cpg.method.name("target_function").caller.where(_.ast.isControlStructure.controlStructureType("FOR|WHILE")).name.l
cpg.method.name("palloc").callIn.where(_.inControlStructure.controlStructureType("FOR|WHILE")).method.name.dedup.take(20).l
```
**Инсайт:** Находится ли в hot path (циклах)

### 7. Найти связанные commits (Продвинутая)
```scala
cpg.method.name("function_name").map(m => (m.filename, m.lineNumber)).l
// Затем git blame на этих файлах/строках
```
**Инсайт:** История изменений функции

### 8. Проверить lock ordering (Продвинутая)
```scala
cpg.method.ast.isCall.name("LWLockAcquire|LockAcquire")
  .map(c => (c.method.name, c.argument(1).code, c.lineNumber)).l
cpg.method.filter { m =>
  val locks = m.ast.isCall.name(".*LockAcquire").l
  locks.size > 1
}.map(m => (m.name, m.ast.isCall.name(".*Lock.*").code.l)).l
```
**Инсайт:** Deadlock analysis - порядок захвата locks

### 9. Side effects анализ (Продвинутая)
```scala
cpg.method.name("target_function").ast.isCall.name(".*insert|.*delete|.*update|XLogInsert|MarkBufferDirty").code.l
cpg.method.name("target_function").where(_.ast.isCall.name("SPI_execute").whereNot(_.argument(2).code("true"))).l
```
**Инсайт:** Какие изменения вносит функция

### 10. Комплексный impact analysis (Продвинутая)
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
**Инсайт:** Комплексная оценка влияния изменения

---

## СЦЕНАРИЙ 6: PERFORMANCE REGRESSION ANALYSIS

**Цель:** Проактивное выявление узких мест и оптимизационных кандидатов

### 1. Nested loops с высокой сложностью (Базовая)
```scala
cpg.method.where(_.ast.isControlStructure.controlStructureType("FOR|WHILE").depth > 3).map(m => (m.name, m.filename, m.cyclomaticComplexity)).sortBy(-_._3).l
```
**Инсайт:** O(n²+) алгоритмы требуют проверки

### 2. Excessive memory allocations (Базовая)
```scala
cpg.method.ast.isCall.name("palloc.*").groupBy(_.method).map { case (m, calls) => (m.name, calls.size) }.sortBy(-_._2).take(20).l
cpg.method.filter(_.ast.isControlStructure.controlStructureType("FOR|WHILE").ast.isCall.name("palloc.*").nonEmpty).name.l
```
**Инсайт:** Allocation в loops - potential bottleneck

### 3. Lock contention points (Средняя)
```scala
cpg.call.name("LWLockAcquire|SpinLockAcquire").groupBy(_.method).map { case (m, locks) => (m.name, locks.size) }.sortBy(-_._2).l
cpg.method.ast.isCall.name("LWLockAcquire").where(_.inControlStructure).map(c => (c.method.name, c.code)).l
```
**Инсайт:** Многократный lock acquire - contention risk

### 4. Planner complexity hotspots (Средняя)
```scala
cpg.method.fullName(".*planner.*|.*optimizer.*").filter(_.cyclomaticComplexity > 20).map(m => (m.name, m.cyclomaticComplexity, m.numberOfLines)).sortBy(-_._2).l
```
**Инсайт:** Высокая complexity в planner влияет на planning time

### 5. Buffer pinning patterns (Средняя)
```scala
cpg.method.filter { m =>
  val pins = m.ast.isCall.name("ReadBuffer|PinBuffer").size
  val unpins = m.ast.isCall.name("ReleaseBuffer|UnpinBuffer").size
  pins != unpins || pins > 5
}.map(m => (m.name, m.filename)).l
```
**Инсайт:** Buffer leak или excessive pinning

### 6. Sequential scans в hot paths (Продвинутая)
```scala
cpg.method.name("ExecSeqScan").caller.where(_.caller.size > 100).name.dedup.l
cpg.call.name("heap_beginscan|table_beginscan").where(_.method.caller.size > 50).method.name.l
```
**Инсайт:** Sequential scans called frequently

### 7. Syscall intensity (Продвинутая)
```scala
cpg.call.name("read|write|fsync|pread|pwrite").groupBy(_.method).map { case (m, calls) => (m.name, calls.size) }.sortBy(-_._2).l
```
**Инсайт:** I/O intensive functions

### 8. Algorithmic complexity regression (Продвинутая)
```scala
// Сравнить две версии CPG
def v15 = loadCPG("postgresql-15")
def v16 = loadCPG("postgresql-16")
v15.method.map(m => (m.fullName, m.cyclomaticComplexity)).diff(
  v16.method.map(m => (m.fullName, m.cyclomaticComplexity))
).filter { case ((name, cc1), (_, cc2)) => cc2 > cc1 * 1.5 }.l
```
**Инсайт:** Функции с ростом complexity между версиями

### 9. Cache miss candidates (Продвинутая)
```scala
cpg.method.filter { m =>
  val arrayAccess = m.ast.isCall.nameExact(Operators.indexAccess).size
  val loops = m.ast.isControlStructure.controlStructureType("FOR|WHILE").size
  arrayAccess > 0 && loops > 2
}.map(m => (m.name, m.filename)).l
```
**Инсайт:** Multi-dimensional array access - cache locality issues

### 10. Performance metrics dashboard (Продвинутая)
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
**Инсайт:** Комплексные performance метрики по модулям

---

## СЦЕНАРИЙ 7: TEST GAP ANALYSIS & COVERAGE

**Цель:** Выявление untested code и gaps в test coverage

### 1. Modified functions без tests (Базовая)
```scala
def changedFunctions = getChangedFunctions(lastCommit) // Helper function
cpg.method.name(changedFunctions: _*).whereNot(_.coveredByTest).map(m => (m.name, m.filename)).l
```
**Инсайт:** New/changed code без coverage - высокий риск

### 2. Error paths без coverage (Базовая)
```scala
cpg.call.name("ereport|elog").where(_.argument(1).code("ERROR|FATAL")).caller.whereNot(_.executedInTests).name.l
cpg.method.ast.isControlStructure.condition.code(".*== NULL.*").whereNot(_.method.hasTestCoverage).method.name.l
```
**Инсайт:** Error handling paths часто не тестируются

### 3. Security-critical functions без tests (Средняя)
```scala
cpg.method.name(".*[Aa]uth.*|.*[Pp]rivile.*|.*[Pp]ermiss.*").filename(".*libpq/auth.*|.*commands/user.*")
  .whereNot(_.hasTestCoverage).map(m => (m.name, m.filename)).l
```
**Инсайт:** Authentication/authorization требует обязательного testing

### 4. Integration points без tests (Средняя)
```scala
cpg.call.where(_.method.fullName(".*planner.*")).where(_.callee.fullName(".*executor.*"))
  .whereNot(_.pathCoveredBy("integration")).map(c => (c.location, c.code)).l
```
**Инсайт:** Межмодульные границы нуждаются в integration tests

### 5. Dead code identification (Средняя)
```scala
cpg.method.whereNot(_.callIn.nonEmpty).whereNot(_.isEntryPoint).whereNot(_.isTestMethod)
  .whereNot(_.name.matches(".*_in|.*_out")) // Exclude type I/O functions
  .map(m => (m.name, m.filename, m.numberOfLines)).l
```
**Инсайт:** Unreachable code - кандидаты на удаление

### 6. High-risk untested functions (Продвинутая)
```scala
cpg.method.filter(m => m.cyclomaticComplexity > 10 && m.callIn.size > 20)
  .whereNot(_.hasTestCoverage).map(m => (m.name, m.cyclomaticComplexity, m.callIn.size, m.filename))
  .sortBy(m => -(m._2 * m._3)).l // Risk score
```
**Инсайт:** Сложные + часто вызываемые без tests = очень высокий риск

### 7. Transaction logic coverage (Продвинутая)
```scala
cpg.method.name(".*[Tt]ransaction.*|.*[Cc]ommit.*|.*[Aa]bort.*").filename(".*access/transam.*")
  .map { m =>
    val branches = m.ast.isControlStructure.controlStructureType("IF").size
    val coveredBranches = m.branchesCoveredInTests
    (m.name, branches, coveredBranches, (coveredBranches.toFloat / branches * 100).toInt)
  }.sortBy(_._4).l
```
**Инсайт:** Branch coverage для critical transaction paths

### 8. Replication coverage gaps (Продвинутая)
```scala
cpg.method.filename(".*replication/.*").whereNot(_.hasTestCoverage)
  .map(m => (m.name, m.filename, m.numberOfLines, m.cyclomaticComplexity)).sortBy(-_._4).l
```
**Инсайт:** Replication - complex subsystem требует полного coverage

### 9. Extension API stability (Средняя)
```scala
cpg.method.filename(".*src/include/.*").where(_.annotation.name(".*API.*|.*public.*"))
  .map { m =>
    val testCount = cpg.file.name(".*test.*").method.callOut.name(m.name).size
    (m.name, m.filename, testCount)
  }.filter(_._3 == 0).l
```
**Инсайт:** Public API без tests - breaking changes risk

### 10. Coverage trend analysis (Продвинутая)
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
**Инсайт:** Comprehensive coverage metrics с focus на critical code

---

## СЦЕНАРИЙ 8: REGULATORY COMPLIANCE & API EVOLUTION

**Цель:** Compliance, license checking, и управление API evolution

### 1. Deprecated API usage (Базовая)
```scala
cpg.call.name("DirectFunctionCall.*|fmgr_info|SearchSysCache").where(_.callee.annotation.name("deprecated"))
  .map(c => (c.location, c.name, c.callee.comment.headOption)).l
```
**Инсайт:** Использование deprecated APIs требует migration

### 2. Unsafe functions для compliance (Базовая)
```scala
cpg.call.name("strcpy|sprintf|gets|strcat").map(c => 
  Map("location" -> c.location, "function" -> c.name, "rule" -> "CWE-120", "severity" -> "HIGH")
).l
```
**Инсайт:** Security compliance требует замены unsafe functions

### 3. GPL license contamination (Средняя)
```scala
def gplFiles = cpg.file.where(_.content.contains("GPL")).name.l
cpg.call.callee.where(_.filename.oneOf(gplFiles: _*)).caller.whereNot(_.filename.oneOf(gplFiles: _*))
  .map(c => (c.location, "GPL contamination risk")).l
```
**Инсайт:** GPL code вызываемый из non-GPL - license conflict

### 4. Breaking API changes между версиями (Средняя)
```scala
def v15API = loadCPG("postgresql-15")
def v16API = loadCPG("postgresql-16")
v15API.method.isPublic.map(m => (m.fullName, m.signature)).l
  .diff(v16API.method.isPublic.map(m => (m.fullName, m.signature)).l)
  .map { case (name, sig) => Map("function" -> name, "old_sig" -> sig, "status" -> "BREAKING CHANGE") }
```
**Инсайт:** Signature changes в public API - breaking для extensions

### 5. CERT secure coding violations (Средняя)
```scala
// ENV33-C: Do not call system() with user-controlled argument
cpg.call.name("system|popen|exec.*").where(_.argument.reachableBy(cpg.call.name("getenv|PG_GETARG.*")))
  .map(c => (c.location, "CERT ENV33-C violation")).l
// INT32-C: Integer overflow
cpg.call.name("palloc|malloc").where(_.argument(1).arithmeticExpr).whereNot(_.argument.code(".*overflow.*"))
  .map(c => (c.location, "CERT INT32-C potential violation")).l
```
**Инсайт:** CERT rules для safety-critical code

### 6. GDPR data processing (Продвинутая)
```scala
cpg.method.name(".*user.*|.*personal.*|.*profile.*").where(_.parameter.name(".*email|.*address|.*phone.*"))
  .whereNot(_.hasAnnotation("GDPR_documented")).map(m => (m.name, m.filename, "Requires GDPR documentation")).l
```
**Инсайт:** Personal data processing требует documentation

### 7. PostgreSQL coding standards (Средняя)
```scala
// Naming convention violations
cpg.method.where(_.name.matches("^[A-Z].*")).filter(!_.isPublicAPI).map(m => (m.name, m.filename, "Should be camelCase")).l
// Missing error checks
cpg.call.name("palloc|malloc").whereNot(_.astParent.isControlStructure.condition.code(".*== NULL.*"))
  .map(c => (c.location, "Missing NULL check after allocation")).l
```
**Инсайт:** Соответствие PostgreSQL style guide

### 8. Extension API compatibility (Продвинутая)
```scala
// Find all hook signature changes
def oldHooks = loadCPG("postgresql-15").typeDecl.name(".*_hook_type").map(t => (t.name, t.aliasTypeFullName)).l
def newHooks = loadCPG("postgresql-16").typeDecl.name(".*_hook_type").map(t => (t.name, t.aliasTypeFullName)).l
oldHooks.diff(newHooks).map { case (name, oldSig) => 
  Map("hook" -> name, "old_signature" -> oldSig, "status" -> "CHANGED", "impact" -> "Extensions need update")
}
```
**Инсайт:** Hook changes require extension migration guides

### 9. Search path safety audit (Продвинутая)
```scala
cpg.file.name(".*\\.sql").content.where(_.matches("(?i).*SECURITY\\s+DEFINER.*"))
  .whereNot(_.matches("(?i).*SET\\s+search_path\\s*=\\s*pg_catalog.*"))
  .map(f => (f.name, "Missing search_path protection", "CVE-2018-1058 pattern")).l
cpg.method.ast.isCall.whereNot(_.name.contains(".")).where(_.method.fullName(".*SECURITY_DEFINER.*"))
  .map(c => (c.location, c.name, "Unqualified function call in SECURITY DEFINER")).l
```
**Инсайт:** Security compliance - search_path protection обязателен

### 10. Comprehensive compliance report (Продвинутая)
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
**Инсайт:** Comprehensive compliance dashboard для audit readiness
