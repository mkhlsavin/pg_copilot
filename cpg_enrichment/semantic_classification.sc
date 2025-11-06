// semantic_classification.sc - semantic classification and purpose detection
// Launch: :load semantic_classification.sc
//
// Tags emitted:
// - `function-purpose`: functional intent (memory-management, query-planning, etc.)
// - `data-structure`: dominant data structures (hash-table, linked-list, etc.)
// - `algorithm-class`: algorithmic family (sorting, searching, caching, etc.)
// - `domain-concept`: PostgreSQL domain concepts (transaction, mvcc, wal, etc.)
//
// Examples:
//   cpg.method.where(_.tag.nameExact("function-purpose").valueExact("memory-management")).name.l
//   cpg.method.where(_.tag.nameExact("algorithm-class").valueExact("sorting")).name.l
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.codepropertygraph.generated.EdgeTypes
import io.shiftleft.semanticcpg.language._
import flatgraph.DiffGraphBuilder

import EnrichCommon._
import scala.io.Source
import scala.util.Using
import java.nio.file.{Files, Paths}
import scala.collection.mutable

val APPLY = sys.props.getOrElse("semantic.apply", "true").toBoolean

println(s"[*] Apply semantic tags: $APPLY")

// ============================================================================
// CLASSIFICATION PATTERNS
// ============================================================================

// Function intent (function-purpose)
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

// Data structures (data-structure)
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

// Algorithmic class (algorithm-class)
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
  ),

  "tree-maintenance" -> List(
    "page_split", "split", "rebalance", "rotate",
    "vacuum_page", "btinsert", "btree_split", "insertion"
  ),

  "index-build" -> List(
    "bulkload", "build", "createindex", "ginbuild",
    "gistbuild", "spgbuild", "brinbuild"
  ),

  "buffer-management" -> List(
    "buffering", "ring", "strategy_init", "buffer_strategy",
    "buffer_alloc", "sharedbuffer"
  ),

  "vacuuming" -> List(
    "vacuum", "prune", "page_cleanup", "heap_page_prune",
    "lazy_vacuum", "vacuum_index"
  ),

  "heuristic-search" -> List(
    "geqo", "hill", "anneal", "genetic",
    "join_search", "geqo_eval"
  ),

  "graph-traversal" -> List(
    "dijkstra", "bfs", "dfs", "shortestpath",
    "graph_search", "path_search"
  ),

  "join-ordering" -> List(
    "joinrels", "join_search", "make_join_rel",
    "joinorder", "join_search_one_level"
  ),

  "dynamic-programming" -> List(
    "dynamic", "memo", "dp", "matrix",
    "memoize", "state_array"
  ),

  "sampling" -> List(
    "sample", "reservoir", "bernoulli",
    "system_rows", "system_time"
  )
)

case class AlgorithmHint(phrase: String, category: String, contexts: Set[String], count: Int) {
  lazy val searchTerms: Seq[String] = {
    val base = phrase.replace("-", " ").trim
    val combined =
      Seq(phrase, base, base.replace(" ", ""), base.replace(" ", "_")) ++
        base.split("\\s+").filter(_.length >= 4)
    combined.map(_.toLowerCase).distinct
  }

  lazy val contextTerms: Seq[String] = {
    contexts.toSeq.flatMap { ctx =>
      val norm = ctx.replace('\\', '/')
      val parts = norm.split("/").filter(_.nonEmpty)
      val parent = if (parts.length > 1) parts.init.mkString("/") else norm
      val tail2 = if (parts.length >= 2) parts.takeRight(2).mkString("/") else norm
      val last = parts.lastOption.toSeq
      Seq(norm, parent, tail2) ++ last
    }.map(_.toLowerCase).filter(_.nonEmpty).distinct
  }
}

def inferAlgorithmCategory(token: String, contexts: Set[String]): String = {
  val t = token.toLowerCase
  val ctx = contexts.mkString(" ")
  def ctxHas(value: String): Boolean = ctx.contains(value)

  if (t.contains("sort")) "sorting"
  else if (t.contains("search") || t.contains("scan") || t.contains("lookup") || t.contains("probe")) "searching"
  else if (t.contains("split") || t.contains("merge") || t.contains("rebalance") ||
           ctxHas("btree") || ctxHas("gin") || ctxHas("gist") || ctxHas("spgist"))
    "tree-maintenance"
  else if (t.contains("buffer")) "buffer-management"
  else if (t.contains("build") && (ctxHas("index") || ctxHas("gin") || ctxHas("gist") || ctxHas("spgist")))
    "index-build"
  else if (t.contains("insert") || t.contains("insertion")) "tree-maintenance"
  else if (t.contains("delete") || t.contains("cleanup") || t.contains("vacuum") || ctxHas("vacuum"))
    "vacuuming"
  else if (t.contains("plan") || t.contains("cost") || ctxHas("optimizer") || ctxHas("planner"))
    "optimization"
  else if (t.contains("dynamic")) "dynamic-programming"
  else if (t.contains("greedy") || t.contains("hill") || t.contains("genetic") || ctxHas("geqo"))
    "heuristic-search"
  else if (t.contains("graph") || t.contains("spath") || ctxHas("graph"))
    "graph-traversal"
  else if (t.contains("join")) "join-ordering"
  else if (t.contains("hash")) "hashing"
  else if (t.contains("aggregate")) "aggregation"
  else if (t.contains("sample")) "sampling"
  else if (ctxHas("gin") || ctxHas("gist") || ctxHas("btree") || ctxHas("spgist"))
    "index-build"
  else "general-algorithm"
}

def buildAlgorithmLexicon(): Seq[AlgorithmHint] = {
  val path = Paths.get("algorithms.txt")
  if (!Files.exists(path)) {
    println("[*] algorithms.txt not found; using built-in algorithm patterns only.")
    Seq.empty
  } else {
    val tokenRegex = "(?i)([A-Za-z0-9_-]+(?:\\s+[A-Za-z0-9_-]+)?)\\s+algorithm(?:s|ic)?".r
    val stopWords = Set(
      "the", "this", "these", "those", "other", "general", "original",
      "overall", "existing", "current", "simple", "complex", "entire",
      "whole", "main", "same", "above", "following", "described"
    )
    val tokenCounts = mutable.Map.empty[String, Int]
    val tokenContexts = mutable.Map.empty[String, mutable.Set[String]]

    Using.resource(Source.fromFile(path.toFile)) { source =>
      var currentFile = ""
      source.getLines().foreach { line =>
        val trimmed = line.trim
        if (
          trimmed.nonEmpty &&
          trimmed.endsWith(":") &&
          (trimmed.contains("\\") || trimmed.contains("/")) &&
          !trimmed.headOption.exists(_.isDigit)
        ) {
          currentFile = trimmed.dropRight(1).replace('\\', '/').toLowerCase
        } else {
          tokenRegex.findAllMatchIn(line).foreach { m =>
            val raw = m.group(1).toLowerCase
            val cleaned = raw.replaceAll("[^a-z0-9\\s-]", " ").replaceAll("\\s+", " ").trim
            if (cleaned.length >= 4) {
              val words = cleaned.split("\\s+")
              if (!words.exists(stopWords.contains)) {
                val phrase = cleaned.replace(" ", "-")
                tokenCounts.update(phrase, tokenCounts.getOrElse(phrase, 0) + 1)
                if (currentFile.nonEmpty) {
                  val ctxSet = tokenContexts.getOrElseUpdate(phrase, mutable.Set.empty[String])
                  ctxSet += currentFile
                }
              }
            }
          }
        }
      }
    }

    val hints = tokenCounts.toSeq
      .filter { case (_, count) => count >= 3 }
      .sortBy { case (_, count) => -count }
      .take(200)
      .flatMap { case (phrase, count) =>
        val contexts = tokenContexts.getOrElse(phrase, mutable.Set.empty[String]).toSeq
          .sortBy(_.length)
          .take(20)
          .toSet
        val category = inferAlgorithmCategory(phrase, contexts)
        if (category == "general-algorithm") None
        else Some(AlgorithmHint(phrase, category, contexts, count))
      }

    if (hints.nonEmpty) {
      println(s"[*] Derived ${hints.size} algorithm hints from algorithms.txt")
      hints
        .groupBy(_.category)
        .view
        .mapValues(_.size)
        .toSeq
        .sortBy { case (_, size) => -size }
        .take(5)
        .foreach { case (cat, size) =>
          println(f"    $cat%-20s : $size%3d hints")
        }
    }

    hints
  }
}

val ALGORITHM_HINTS: Seq[AlgorithmHint] = buildAlgorithmLexicon()

// Domain-specific concepts (domain-concept)
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
  val paramNames = method.parameter.name.l.map(_.toLowerCase)
  val paramTypes = method.parameter.typeFullName.l.map(_.toLowerCase)

  val baseMatches = PURPOSE_PATTERNS.flatMap { case (purpose, patterns) =>
    if (patterns.exists(p => name.contains(p.toLowerCase) ||
                             code.contains(p.toLowerCase) ||
                             filename.contains(p.toLowerCase))) {
      Some(purpose)
    } else None
  }.toList

  val signatureMatches = scala.collection.mutable.ListBuffer[String]()
  if (paramTypes.exists(_.contains("lock")) || paramNames.exists(_.contains("lock"))) {
    signatureMatches += "synchronization"
  }
  if (paramTypes.exists(_.contains("context")) || paramNames.exists(_.contains("ctx"))) {
    signatureMatches += "context-management"
  }
  if (paramTypes.exists(_.contains("snapshot")) || paramNames.exists(_.contains("snapshot"))) {
    signatureMatches += "snapshot-handling"
  }
  if (paramNames.exists(_.contains("plan")) || paramTypes.exists(_.contains("planner"))) {
    signatureMatches += "planning"
  }

  val merged = (baseMatches ++ signatureMatches).distinct
  if (merged.isEmpty) List("general") else merged.take(3)
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
  val name = Option(method.name).map(_.toLowerCase).getOrElse("")
  val code = Option(method.code).map(_.toLowerCase).getOrElse("")
  val filename = Option(method.filename).map(_.toLowerCase.replace('\\', '/')).getOrElse("")

  val baseMatches = ALGORITHM_PATTERNS.flatMap { case (algo, patterns) =>
    if (patterns.exists { p =>
          val needle = p.toLowerCase
          name.contains(needle) || code.contains(needle) || filename.contains(needle)
        }) {
      Some(algo)
    } else None
  }.toList

  val lexiconMatches = ALGORITHM_HINTS.flatMap { hint =>
    val termMatch = hint.searchTerms.exists { term =>
      val t = term.toLowerCase
      val inName = t.nonEmpty && name.contains(t)
      val inFile = t.nonEmpty && filename.contains(t)
      val inCode = t.length >= 7 && code.contains(t)
      inName || inFile || inCode
    }
    val contextMatch = hint.contextTerms.exists(ct => filename.contains(ct))
    if (termMatch || contextMatch) Some(hint.category) else None
  }

  (baseMatches ++ lexiconMatches).distinct.take(3)
}

def classifyDomainConcepts(method: Method): List[String] = {
  val name = method.name.toLowerCase
  val code = method.code.toLowerCase
  val filename = method.filename.toLowerCase
  val paramDomains = method.parameter
    .flatMap(_.tag.nameExact(TagCatalog.ParamDomainConcept.name).value.l)
    .map(_.toLowerCase)
    .distinct
  val paramTypes = method.parameter.typeFullName.l.map(_.toLowerCase)
  val returnType = method.methodReturn.typeFullName.toLowerCase

  val baseMatches = DOMAIN_CONCEPT_PATTERNS.flatMap { case (concept, patterns) =>
    if (patterns.exists(p => name.contains(p.toLowerCase) ||
                             code.contains(p.toLowerCase) ||
                             filename.contains(p.toLowerCase))) {
      Some(concept)
    } else None
  }.toList

  val derived = scala.collection.mutable.ListBuffer[String]()
  if (paramDomains.contains("mvcc") || paramTypes.exists(_.contains("snapshot")) || returnType.contains("snapshot")) {
    derived += "mvcc"
  }
  if (paramDomains.contains("heap-page") || paramTypes.exists(t => t.contains("buffer") || t.contains("block"))) {
    derived += "storage"
  }
  if (paramDomains.contains("wal-record") || returnType.contains("xlog") || name.contains("wal")) {
    derived += "wal"
  }
  if (paramDomains.contains("catalog-cache") || filename.contains("catalog") || name.contains("catalog")) {
    derived += "catalog"
  }
  if (paramDomains.contains("autovacuum") || name.contains("vacuum")) {
    derived += "vacuum"
  }
  if (paramDomains.contains("replication") || paramTypes.exists(_.contains("slot")) || name.contains("replication")) {
    derived += "replication"
  }

  (baseMatches ++ derived).distinct.take(3)
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

  // Statistics
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

  try {
    import EnrichCommon.{NamePattern, PatternMatcher}

    val paramRoleProbe = Seq(
      NamePattern("snapshot", Seq("snapshot"), weight = 4, requireFullToken = false),
      NamePattern("transaction-context", Seq("transaction", "txn", "xact"), weight = 3, requireFullToken = false),
      NamePattern("memory-context", Seq("mcxt", "memcxt", "memorycontext"), weight = 2, requireFullToken = false),
      NamePattern("buffer", Seq("buffer", "buf", "block"), weight = 2, requireFullToken = false)
    )

    val sampledParams = cpg.parameter.l.take(2000)
    val hintHits = sampledParams.flatMap { param =>
      PatternMatcher.bestMatch(param.name, paramRoleProbe).map(_.label)
    }

    if (sampledParams.nonEmpty) {
      val coverage = hintHits.size.toDouble / sampledParams.size * 100
      println(f"\n[*] Param-role hint sample coverage: $coverage%.1f%% (${hintHits.size}/${sampledParams.size})")
    }
  } catch {
    case _: Throwable =>
      println("\n[*] Param-role hint sampling skipped (enrich_common.sc not loaded).")
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




