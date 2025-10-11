open("pg17_full.cpg")
println("Workspace opened")

// architectural_layers.sc - PostgreSQL architectural layer classification
// Launch: :load architectural_layers.sc
//
// Classifies PostgreSQL source files into architectural layers such as frontend, executor, storage, replication, etc.
//
// ============================================================================
// Layer catalogue
// ============================================================================
// - frontend: client-facing code (libpq, ecpg, psql)
// - backend-entry: entry points (postmaster, postgres main)
// - query-frontend: parser, analyzer, rewriter
// - query-optimizer: planner and optimizer
// - query-executor: executor and SQL command handlers
// - storage: heap, index, buffer management internals
// - access: access methods (heap, index families, TOAST)
// - transaction: transaction management and snapshots
// - catalog: system catalog and caches
// - utils: shared utilities, error handling, memory helpers
// - replication: WAL, replication, crash recovery
// - background: background workers and maintenance daemons
// - infrastructure: postmaster, IPC, locking, port abstractions
// - extensions: contrib modules and extension hooks
// - test: test harnesses and fixtures
// - include: header files
//
// Quick checks:
//   cpg.file.where(_.tag.nameExact("arch-layer").valueExact("storage")).name.l
//   cpg.file.tag.nameExact("arch-layer").value.l.groupBy(identity).view.mapValues(_.size)
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.codepropertygraph.generated.EdgeTypes
import flatgraph.DiffGraphBuilder

val APPLY = sys.props.getOrElse("layer.apply", "true").toBoolean

println(s"[*] Apply architectural layers: $APPLY")
println(s"[*] Note: Script will auto-execute applyArchitecturalLayers() at the end")

// ============================================================================
// LAYER CLASSIFICATION PATTERNS
// ============================================================================

// Pattern catalogue used to classify files into architectural layers
val LAYER_PATTERNS = Map(
  // Frontend (client-side code)
  "frontend" -> List(
    ".*interfaces/libpq/.*",
    ".*interfaces/ecpg/.*",
    ".*bin/psql/.*",
    ".*bin/pg_dump/.*",
    ".*bin/pg_basebackup/.*",
    ".*bin/scripts/.*"
  ),

  // Backend Entry Points
  "backend-entry" -> List(
    ".*backend/main/main.c",
    ".*backend/postmaster/postmaster.c",
    ".*backend/tcop/postgres.c",
    ".*backend/bootstrap/.*"
  ),

  // Query Processing - Frontend (parsing, analysis)
  "query-frontend" -> List(
    ".*backend/parser/.*",
    ".*backend/nodes/.*",
    ".*backend/commands/define.c",
    ".*backend/commands/variable.c"
  ),

  // Query Optimizer (planner)
  "query-optimizer" -> List(
    ".*backend/optimizer/.*",
    ".*backend/partitioning/.*"
  ),

  // Query Executor
  "query-executor" -> List(
    ".*backend/executor/.*",
    ".*backend/commands/.*"
  ),

  // Storage Management
  "storage" -> List(
    ".*backend/storage/buffer/.*",
    ".*backend/storage/smgr/.*",
    ".*backend/storage/page/.*",
    ".*backend/storage/freespace/.*"
  ),

  // Access Methods (heap, index, TOAST)
  "access" -> List(
    ".*backend/access/heap/.*",
    ".*backend/access/index/.*",
    ".*backend/access/nbtree/.*",
    ".*backend/access/hash/.*",
    ".*backend/access/gin/.*",
    ".*backend/access/gist/.*",
    ".*backend/access/spgist/.*",
    ".*backend/access/brin/.*",
    ".*backend/access/table/.*",
    ".*backend/access/toast/.*",
    ".*backend/access/common/.*"
  ),

  // Transaction Management
  "transaction" -> List(
    ".*backend/access/transam/.*",
    ".*backend/storage/lmgr/.*",
    ".*backend/utils/time/.*"
  ),

  // System Catalog
  "catalog" -> List(
    ".*backend/catalog/.*",
    ".*backend/utils/cache/.*"
  ),

  // Utilities & Infrastructure
  "utils" -> List(
    ".*backend/utils/adt/.*",
    ".*backend/utils/error/.*",
    ".*backend/utils/init/.*",
    ".*backend/utils/fmgr/.*",
    ".*backend/utils/hash/.*",
    ".*backend/utils/mb/.*",
    ".*backend/utils/misc/.*",
    ".*backend/utils/mmgr/.*",
    ".*backend/utils/resowner/.*",
    ".*backend/utils/sort/.*"
  ),

  // Replication & Recovery
  "replication" -> List(
    ".*backend/replication/.*",
    ".*backend/access/rmgrdesc/.*",
    ".*backend/storage/ipc/.*",
    ".*backend/storage/sync/.*"
  ),

  // Background Workers
  "background" -> List(
    ".*backend/postmaster/autovacuum.c",
    ".*backend/postmaster/bgwriter.c",
    ".*backend/postmaster/checkpointer.c",
    ".*backend/postmaster/walwriter.c",
    ".*backend/postmaster/pgarch.c",
    ".*backend/postmaster/bgworker.c"
  ),

  // Infrastructure (IPC, process management)
  "infrastructure" -> List(
    ".*backend/postmaster/.*",
    ".*backend/libpq/.*",
    ".*backend/tcop/.*",
    ".*backend/port/.*",
    ".*port/.*"
  ),

  // Extensions & Contrib
  "extensions" -> List(
    ".*contrib/.*",
    ".*backend/utils/fmgrtab.c"
  ),

  // Test Code
  "test" -> List(
    ".*test/.*"
  ),

  // Common/Include (headers)
  "include" -> List(
    ".*include/.*\\.h"
  )
)

// Layer priority list (used to resolve overlapping matches)
val LAYER_PRIORITY = List(
  "test",           // Highest priority
  "frontend",
  "backend-entry",
  "query-frontend",
  "query-optimizer",
  "query-executor",
  "access",
  "storage",
  "transaction",
  "catalog",
  "replication",
  "background",
  "utils",
  "infrastructure",
  "extensions",
  "include"         // Lowest priority
)

// Layer descriptions
val LAYER_DESCRIPTIONS = Map(
  "frontend" -> "Client-side tools and libraries (psql, libpq, ecpg)",
  "backend-entry" -> "Backend entry points (main, postmaster)",
  "query-frontend" -> "Query parsing and semantic analysis",
  "query-optimizer" -> "Query planning and optimization",
  "query-executor" -> "Query execution and commands",
  "storage" -> "Low-level storage management (buffer, smgr)",
  "access" -> "Access methods (heap, index, TOAST)",
  "transaction" -> "Transaction and concurrency control",
  "catalog" -> "System catalog and metadata cache",
  "utils" -> "Utility functions and data structures",
  "replication" -> "Replication and WAL management",
  "background" -> "Background worker processes",
  "infrastructure" -> "Process management and IPC",
  "extensions" -> "Extensions and contrib modules",
  "test" -> "Test code and fixtures",
  "include" -> "Header files",
  "unknown" -> "Unclassified files"
)

// ============================================================================
// CLASSIFICATION FUNCTIONS
// ============================================================================

def classifyFileLayer(file: File): String = {
  // Normalize path: replace backslashes with forward slashes for cross-platform compatibility
  val filePath = file.name.replace('\\', '/')

  // Check each layer in priority order
  for (layer <- LAYER_PRIORITY) {
    val patterns = LAYER_PATTERNS.getOrElse(layer, List.empty)
    if (patterns.exists(pattern => filePath.matches(pattern))) {
      return layer
    }
  }

  // Fallback when no pattern matches
  "unknown"
}

def classifySubLayer(file: File, mainLayer: String): Option[String] = {
  // Normalize path for cross-platform compatibility
  val filePath = file.name.replace('\\', '/')

  // Additional heuristics for more specific sublayer tags
  mainLayer match {
    case "query-executor" =>
      if (filePath.contains("/commands/")) Some("commands")
      else if (filePath.contains("/executor/")) Some("execution-engine")
      else None

    case "access" =>
      if (filePath.contains("/heap/")) Some("heap")
      else if (filePath.contains("/nbtree/")) Some("btree-index")
      else if (filePath.contains("/hash/")) Some("hash-index")
      else if (filePath.contains("/gin/")) Some("gin-index")
      else if (filePath.contains("/gist/")) Some("gist-index")
      else if (filePath.contains("/toast/")) Some("toast")
      else None

    case "storage" =>
      if (filePath.contains("/buffer/")) Some("buffer-manager")
      else if (filePath.contains("/smgr/")) Some("storage-manager")
      else if (filePath.contains("/freespace/")) Some("freespace-map")
      else None

    case "transaction" =>
      if (filePath.contains("/transam/")) Some("transaction-manager")
      else if (filePath.contains("/lmgr/")) Some("lock-manager")
      else None

    case "replication" =>
      if (filePath.contains("/logical/")) Some("logical-replication")
      else if (filePath.contains("/walsender")) Some("wal-sender")
      else if (filePath.contains("/walreceiver")) Some("wal-receiver")
      else None

    case _ => None
  }
}

def getLayerDepth(layer: String): Int = {
  // Assign a notional depth for visualization (smaller numbers are closer to the user)
  layer match {
    case "frontend" => 0
    case "backend-entry" => 1
    case "query-frontend" => 2
    case "query-optimizer" => 3
    case "query-executor" => 4
    case "access" => 5
    case "storage" => 6
    case "transaction" => 4
    case "catalog" => 3
    case "utils" => 7
    case "replication" => 4
    case "background" => 2
    case "infrastructure" => 1
    case "extensions" => 8
    case "test" => 9
    case "include" => 10
    case _ => 99
  }
}

// ============================================================================
// APPLY ARCHITECTURAL LAYERS
// ============================================================================

def applyArchitecturalLayers(): Unit = {
  val diff = DiffGraphBuilder(cpg.graph.schema)
  var tagged = 0
  val layerCounts = scala.collection.mutable.Map[String, Int]().withDefaultValue(0)

  println("[*] Classifying files by architectural layer...")

  val allFiles = cpg.file.l
  println(s"[*] Found ${allFiles.size} total files in CPG")

  // TODO: Filter only PostgreSQL source files (exclude MinGW/system headers)
  // Strategy: Exclude mingw files, since CPG includes system headers
  val files = allFiles.filter { f =>
    val path = f.name.replace('\\', '/')
    !path.contains("mingw")
  }
  println(s"[*] Filtered to ${files.size} PostgreSQL source files (excluded ${allFiles.size - files.size} system headers)")

  files.foreach { file =>
    // Classify main layer
    val layer = classifyFileLayer(file)
    layerCounts(layer) += 1

    // TAG: arch-layer
    val tagLayer = NewTag()
      .name("arch-layer")
      .value(layer)
    diff.addNode(tagLayer)
    diff.addEdge(file, tagLayer, EdgeTypes.TAGGED_BY)

    // TAG: arch-layer-description
    val description = LAYER_DESCRIPTIONS.getOrElse(layer, "Unknown")
    val tagDesc = NewTag()
      .name("arch-layer-description")
      .value(description)
    diff.addNode(tagDesc)
    diff.addEdge(file, tagDesc, EdgeTypes.TAGGED_BY)

    // TAG: arch-layer-depth
    val depth = getLayerDepth(layer)
    val tagDepth = NewTag()
      .name("arch-layer-depth")
      .value(depth.toString)
    diff.addNode(tagDepth)
    diff.addEdge(file, tagDepth, EdgeTypes.TAGGED_BY)

    // TAG: arch-sublayer (if applicable)
    classifySubLayer(file, layer).foreach { sublayer =>
      val tagSublayer = NewTag()
        .name("arch-sublayer")
        .value(sublayer)
      diff.addNode(tagSublayer)
      diff.addEdge(file, tagSublayer, EdgeTypes.TAGGED_BY)
    }

    tagged += 1
    if (tagged % 200 == 0) {
      println(s"[*] Classified $tagged files...")
    }
  }

  println(s"[*] Applying architectural layer tags to graph...")
  flatgraph.DiffGraphApplier.applyDiff(cpg.graph, diff)

  println(s"[+] Tagged $tagged files with architectural layers")

  // Statistics
  println("\n[*] Architectural Layer Distribution:")
  println(s"${"=" * 70}")

  val sortedLayers = layerCounts.toList.sortBy(-_._2)
  var unknownCount = 0
  var classifiedCount = 0

  sortedLayers.foreach { case (layer, count) =>
    val description = LAYER_DESCRIPTIONS.getOrElse(layer, "")
    val percentage = (count.toDouble / files.size * 100).toInt

    if (layer == "unknown") {
      unknownCount = count
    } else {
      classifiedCount += count
    }

    println(f"  $layer%-20s : $count%5d files ($percentage%3d%%) - $description")
  }

  println(s"${"=" * 70}")
  val classifiedPercentage = (classifiedCount.toDouble / files.size * 100).toInt
  println(f"[*] Classification coverage: $classifiedPercentage%% ($classifiedCount of ${files.size} files)")
  println(f"[*] Unknown files: $unknownCount (${(unknownCount.toDouble / files.size * 100).toInt}%%)")

  // Layer dependencies analysis
  println("\n[*] Cross-Layer Dependencies Analysis:")
  println(s"${"=" * 70}")

  // Analyze which layers call which other layers
  val layerDeps = scala.collection.mutable.Map[(String, String), Int]().withDefaultValue(0)

  try {
    cpg.method.l.foreach { method =>
      val methodFile = method.file.headOption
      methodFile.foreach { file =>
        val sourceLayer = file.tag.nameExact("arch-layer").value.headOption.getOrElse("unknown")

        // Find calls to other methods
        method.ast.isCall.callee.l.foreach { callee =>
          callee.file.headOption.foreach { targetFile =>
            val targetLayer = targetFile.tag.nameExact("arch-layer").value.headOption.getOrElse("unknown")

            if (sourceLayer != targetLayer && sourceLayer != "unknown" && targetLayer != "unknown") {
              layerDeps((sourceLayer, targetLayer)) += 1
            }
          }
        }
      }
    }

    // Print top cross-layer dependencies
    val topDeps = layerDeps.toList.sortBy(-_._2).take(15)
    if (topDeps.nonEmpty) {
      println("  Top cross-layer call patterns:")
      topDeps.foreach { case ((from, to), count) =>
        println(f"    $from%-20s -> $to%-20s : $count%6d calls")
      }
    } else {
      println("  [!] Cross-layer analysis requires method-level data")
    }
  } catch {
    case e: Exception =>
      println(s"  [!] Could not analyze cross-layer dependencies: ${e.getMessage}")
  }

  println(s"${"=" * 70}")

  // Query examples
  println("\n[*] Query examples:")
  println("""    cpg.file.where(_.tag.nameExact("arch-layer").valueExact("storage")).name.l.take(5)""")
  println("""    cpg.file.tag.nameExact("arch-layer").value.l.groupBy(identity).view.mapValues(_.size)""")
  println("""    cpg.file.where(_.tag.nameExact("arch-layer").valueExact("query-executor"))""")
  println("""      .where(_.tag.nameExact("arch-sublayer").valueExact("commands")).name.l""")
  println("""    cpg.file.where(_.tag.nameExact("arch-layer-depth").value.toInt < 5).name.l.take(10)""")
}

// ============================================================================
// ANALYSIS HELPERS
// ============================================================================

def showLayerSummary(): Unit = {
  println("\n" + "=" * 80)
  println("  ARCHITECTURAL LAYER SUMMARY")
  println("=" * 80)

  val files = cpg.file.l
  val layerStats = files.groupBy { f =>
    f.tag.nameExact("arch-layer").value.headOption.getOrElse("unknown")
  }.view.mapValues(_.size).toMap

  println("\nLayer Distribution:")
  LAYER_PRIORITY.foreach { layer =>
    val count = layerStats.getOrElse(layer, 0)
    val desc = LAYER_DESCRIPTIONS.getOrElse(layer, "")
    if (count > 0) {
      println(f"  $layer%-20s : $count%5d files - $desc")
    }
  }

  val unknownCount = layerStats.getOrElse("unknown", 0)
  println(f"\n  ${"unknown"}%-20s : $unknownCount%5d files")

  println("\n" + "=" * 80)
}

def listLayerFiles(layer: String, limit: Int = 20): Unit = {
  println(s"\nFiles in layer: $layer")
  println("=" * 80)

  val files = cpg.file
    .where(_.tag.nameExact("arch-layer").valueExact(layer))
    .name.l.take(limit)

  files.foreach { f =>
    println(s"  $f")
  }

  val total = cpg.file.where(_.tag.nameExact("arch-layer").valueExact(layer)).size
  if (total > limit) {
    println(s"  ... and ${total - limit} more files")
  }

  println("=" * 80)
}

// ========================= Initialization =========================

if (APPLY) {
  applyArchitecturalLayers()
  println("\n[+] Architectural layer classification complete!")
  println("\n[*] Use showLayerSummary() to see the summary")
  println("[*] Use listLayerFiles(\"layer-name\") to list files in a layer")
} else {
  println("[*] Layer classification disabled. Set -Dlayer.apply=true to enable")
}
