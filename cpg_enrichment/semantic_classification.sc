// semantic_classification.sc — Semantic classification and purpose detection
// Запуск: :load semantic_classification.sc
//
// Добавляет семантические теги для улучшения RAG-запросов:
// - `function-purpose`: назначение функции (memory-management, query-planning, etc.)
// - `data-structure`: используемые структуры данных (hash-table, linked-list, etc.)
// - `algorithm-class`: алгоритмический класс (sorting, searching, caching, etc.)
// - `domain-concept`: domain-specific понятия (transaction, mvcc, wal, etc.)
//
// ПРИМЕРЫ:
//   cpg.method.where(_.tag.nameExact("function-purpose").valueExact("memory-management")).name.l
//   cpg.method.where(_.tag.nameExact("algorithm-class").valueExact("sorting")).name.l

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.codepropertygraph.generated.EdgeTypes
import flatgraph.DiffGraphBuilder

val APPLY = sys.props.getOrElse("semantic.apply", "true").toBoolean

println(s"[*] Apply semantic tags: $APPLY")

// ============================================================================
// CLASSIFICATION PATTERNS
// ============================================================================

// Назначение функции (function-purpose)
val PURPOSE_PATTERNS = Map(
  "memory-management" -> List(
    "alloc", "free", "MemoryContext", "palloc", "pfree", "repalloc",
    "MemAlloc", "AllocSet", "mcxt"
  ),

  "query-planning" -> List(
    "plan", "planner", "optimizer", "rewrite", "subquery",
    "create_plan", "make_plan", "build_plan", "set_plan"
  ),

  "query-execution" -> List(
    "exec", "executor", "ExecProc", "ExecInit", "ExecEnd",
    "execute", "ProcessQuery", "ExecutePlan"
  ),

  "transaction-control" -> List(
    "xact", "transaction", "commit", "abort", "TransactionId",
    "StartTransaction", "CommitTransaction", "AbortTransaction",
    "XactCallback"
  ),

  "storage-access" -> List(
    "buffer", "heap", "index", "ReadBuffer", "WriteBuffer",
    "ReleaseBuffer", "heap_insert", "heap_update", "heap_delete",
    "index_insert", "bt_", "gin_", "gist_", "hash_"
  ),

  "concurrency-control" -> List(
    "lock", "LWLock", "SpinLock", "MVCC", "snapshot",
    "LockAcquire", "LockRelease", "GetSnapshotData"
  ),

  "parsing" -> List(
    "parse", "parser", "gram", "scan", "lex",
    "transformStmt", "analyze"
  ),

  "type-system" -> List(
    "type", "typmod", "typecast", "coerce",
    "TypeName", "GetTypeOid", "format_type"
  ),

  "error-handling" -> List(
    "error", "elog", "ereport", "errcode", "errmsg",
    "ERROR", "WARNING", "FATAL", "PANIC"
  ),

  "catalog-access" -> List(
    "catalog", "syscache", "relcache", "catcache",
    "SearchSysCache", "RelationIdGetRelation"
  ),

  "wal-logging" -> List(
    "wal", "xlog", "XLog", "WAL", "XLOG",
    "XLogInsert", "XLogRecPtr", "XLogBegin"
  ),

  "networking" -> List(
    "socket", "pq", "libpq", "fe_", "be_",
    "pqcomm", "port", "StreamConnection"
  ),

  "statistics" -> List(
    "stat", "stats", "analyze", "vacuum",
    "pgstat", "PgStat", "UpdateStats"
  ),

  "utilities" -> List(
    "utility", "util", "misc", "helper",
    "format", "string", "array", "list"
  )
)

// Структуры данных (data-structure)
val DATA_STRUCTURE_PATTERNS = Map(
  "hash-table" -> List(
    "Hash", "HTAB", "htab", "hash_create", "hash_search",
    "hashfunc", "hashvalue", "dynahash"
  ),

  "linked-list" -> List(
    "List", "list", "dlist", "slist", "DList", "SList",
    "lappend", "lcons", "foreach", "list_nth"
  ),

  "binary-tree" -> List(
    "RBTree", "rbtree", "BTree", "btree", "GinBtree",
    "rb_insert", "rb_delete", "bt_search"
  ),

  "array" -> List(
    "Array", "array", "ArrayType", "array_",
    "construct_array", "deconstruct_array"
  ),

  "bitmap" -> List(
    "Bitmap", "bitmap", "Bitmapset", "bms_",
    "bms_make", "bms_add_member", "bms_is_member"
  ),

  "queue" -> List(
    "Queue", "queue", "shm_mq", "mq_",
    "enqueue", "dequeue"
  ),

  "buffer" -> List(
    "StringInfo", "stringinfo", "appendStringInfo",
    "makeStringInfo", "initStringInfo"
  ),

  "relation" -> List(
    "Relation", "relation", "RelationData",
    "heap_open", "table_open", "relation_open"
  )
)

// Алгоритмический класс (algorithm-class)
val ALGORITHM_PATTERNS = Map(
  "sorting" -> List(
    "sort", "qsort", "tuplesort", "orderby",
    "comparator", "cmp", "compare"
  ),

  "searching" -> List(
    "search", "lookup", "find", "locate",
    "binary_search", "linear_search"
  ),

  "hashing" -> List(
    "hash", "hashfunc", "hashvalue",
    "hash_any", "hash_uint32"
  ),

  "caching" -> List(
    "cache", "catcache", "relcache", "syscache",
    "CacheInvalidate", "CacheLookup"
  ),

  "compression" -> List(
    "compress", "decompress", "toast",
    "pglz", "lz", "varatt"
  ),

  "parsing" -> List(
    "lex", "yacc", "gram", "token",
    "scanner", "parser"
  ),

  "optimization" -> List(
    "optimize", "cost", "estimate",
    "cost_seqscan", "estimate_num_groups"
  ),

  "aggregation" -> List(
    "aggregate", "agg", "group",
    "advance_aggregates", "finalize_aggregates"
  )
)

// Domain-specific концепты (domain-concept)
val DOMAIN_CONCEPT_PATTERNS = Map(
  "mvcc" -> List(
    "mvcc", "MVCC", "visibility", "snapshot",
    "xmin", "xmax", "HeapTupleSatisfies"
  ),

  "vacuum" -> List(
    "vacuum", "Vacuum", "autovacuum",
    "lazy_vacuum", "heap_page_prune"
  ),

  "replication" -> List(
    "replication", "walsender", "walreceiver",
    "logical", "physical", "slot"
  ),

  "partitioning" -> List(
    "partition", "Partition", "partitioned",
    "PartitionKey", "PartitionDesc"
  ),

  "parallelism" -> List(
    "parallel", "Parallel", "worker",
    "ParallelContext", "LaunchParallelWorkers"
  ),

  "extension" -> List(
    "extension", "hook", "callback",
    "planner_hook", "ExecutorStart_hook"
  ),

  "foreign-data" -> List(
    "fdw", "FDW", "foreign", "ForeignScan",
    "GetForeignPlan", "IterateForeignScan"
  ),

  "jit" -> List(
    "jit", "JIT", "llvm", "LLVM",
    "llvm_compile", "jit_compile"
  )
)

// ============================================================================
// CLASSIFICATION FUNCTIONS
// ============================================================================

def classifyPurpose(method: Method): List[String] = {
  val name = method.name.toLowerCase
  val code = method.code.toLowerCase
  val filename = method.filename.toLowerCase

  val matches = PURPOSE_PATTERNS.flatMap { case (purpose, patterns) =>
    if (patterns.exists(p => name.contains(p.toLowerCase) ||
                             code.contains(p.toLowerCase) ||
                             filename.contains(p.toLowerCase))) {
      Some(purpose)
    } else None
  }.toList

  if (matches.isEmpty) List("general") else matches.take(2)
}

def classifyDataStructures(method: Method): List[String] = {
  val name = method.name.toLowerCase
  val code = method.code.toLowerCase

  DATA_STRUCTURE_PATTERNS.flatMap { case (ds, patterns) =>
    if (patterns.exists(p => name.contains(p.toLowerCase) ||
                             code.contains(p.toLowerCase))) {
      Some(ds)
    } else None
  }.toList.take(3)
}

def classifyAlgorithm(method: Method): List[String] = {
  val name = method.name.toLowerCase
  val code = method.code.toLowerCase

  ALGORITHM_PATTERNS.flatMap { case (algo, patterns) =>
    if (patterns.exists(p => name.contains(p.toLowerCase) ||
                             code.contains(p.toLowerCase))) {
      Some(algo)
    } else None
  }.toList.take(2)
}

def classifyDomainConcepts(method: Method): List[String] = {
  val name = method.name.toLowerCase
  val code = method.code.toLowerCase
  val filename = method.filename.toLowerCase

  DOMAIN_CONCEPT_PATTERNS.flatMap { case (concept, patterns) =>
    if (patterns.exists(p => name.contains(p.toLowerCase) ||
                             code.contains(p.toLowerCase) ||
                             filename.contains(p.toLowerCase))) {
      Some(concept)
    } else None
  }.toList.take(2)
}

// ============================================================================
// APPLY SEMANTIC TAGS
// ============================================================================

def applySemanticTags(): Unit = {
  val diff = DiffGraphBuilder(cpg.graph.schema)
  var tagged = 0

  println("[*] Classifying methods semantically...")

  val methods = cpg.method.l
  println(s"[*] Found ${methods.size} methods to classify")

  methods.foreach { method =>
    var hasClassification = false

    // TAG: function-purpose
    classifyPurpose(method).foreach { purpose =>
      val tag = NewTag().name("function-purpose").value(purpose)
      diff.addNode(tag)
      diff.addEdge(method, tag, EdgeTypes.TAGGED_BY)
      hasClassification = true
    }

    // TAG: data-structure
    classifyDataStructures(method).foreach { ds =>
      val tag = NewTag().name("data-structure").value(ds)
      diff.addNode(tag)
      diff.addEdge(method, tag, EdgeTypes.TAGGED_BY)
      hasClassification = true
    }

    // TAG: algorithm-class
    classifyAlgorithm(method).foreach { algo =>
      val tag = NewTag().name("algorithm-class").value(algo)
      diff.addNode(tag)
      diff.addEdge(method, tag, EdgeTypes.TAGGED_BY)
      hasClassification = true
    }

    // TAG: domain-concept
    classifyDomainConcepts(method).foreach { concept =>
      val tag = NewTag().name("domain-concept").value(concept)
      diff.addNode(tag)
      diff.addEdge(method, tag, EdgeTypes.TAGGED_BY)
      hasClassification = true
    }

    if (hasClassification) {
      tagged += 1
      if (tagged % 1000 == 0) println(s"[*] Classified $tagged methods...")
    }
  }

  println(s"[*] Applying semantic tags to graph...")
  flatgraph.DiffGraphApplier.applyDiff(cpg.graph, diff)

  println(s"[+] Tagged $tagged methods with semantic classification")

  // Статистика
  println("\n[*] Semantic Classification Statistics:")

  println("\n  Function Purposes:")
  cpg.method.tag.nameExact("function-purpose").value.l
    .groupBy(identity).view.mapValues(_.size).toList
    .sortBy(-_._2).take(10)
    .foreach { case (purpose, count) =>
      println(f"    $purpose%-30s : $count%5d")
    }

  println("\n  Data Structures:")
  cpg.method.tag.nameExact("data-structure").value.l
    .groupBy(identity).view.mapValues(_.size).toList
    .sortBy(-_._2).take(10)
    .foreach { case (ds, count) =>
      println(f"    $ds%-30s : $count%5d")
    }

  println("\n  Algorithm Classes:")
  cpg.method.tag.nameExact("algorithm-class").value.l
    .groupBy(identity).view.mapValues(_.size).toList
    .sortBy(-_._2).take(10)
    .foreach { case (algo, count) =>
      println(f"    $algo%-30s : $count%5d")
    }

  println("\n  Domain Concepts:")
  cpg.method.tag.nameExact("domain-concept").value.l
    .groupBy(identity).view.mapValues(_.size).toList
    .sortBy(-_._2).take(10)
    .foreach { case (concept, count) =>
      println(f"    $concept%-30s : $count%5d")
    }

  val coverage = (tagged.toDouble / methods.size * 100).toInt
  println(f"\n[*] Semantic coverage: $coverage%% ($tagged of ${methods.size} methods)")
}

// ========================= Initialization =========================

if (APPLY) {
  applySemanticTags()
  println("\n[*] Query examples:")
  println("""    cpg.method.where(_.tag.nameExact("function-purpose").valueExact("memory-management")).name.l.take(10)""")
  println("""    cpg.method.where(_.tag.nameExact("data-structure").valueExact("hash-table")).name.l.take(10)""")
  println("""    cpg.method.where(_.tag.nameExact("algorithm-class").valueExact("sorting")).name.l""")
  println("""    cpg.method.where(_.tag.nameExact("domain-concept").valueExact("mvcc")).name.l""")
} else {
  println("[*] Semantic tagging disabled. Set -Dsemantic.apply=true to enable")
}
