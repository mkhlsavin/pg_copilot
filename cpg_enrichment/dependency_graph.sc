// dependency_graph.sc - Module dependency analysis
// Launch: :load dependency_graph.sc
//
// Adds: `module-depends-on`, `module-dependents`, `module-layer`, `circular-dependency`
// Example query: cpg.file.where(_.tag.nameExact("circular-dependency").valueExact("true")).name.l

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.codepropertygraph.generated.EdgeTypes
import flatgraph.DiffGraphBuilder

val APPLY = sys.props.getOrElse("dep.apply", "true").toBoolean

val LAYER_PATTERNS = Map(
  "storage" -> List("/access/", "/storage/", "/bufmgr/"),
  "executor" -> List("/executor/", "/execMain", "/execProcnode"),
  "optimizer" -> List("/optimizer/", "/planner/", "/rewrite/"),
  "parser" -> List("/parser/", "/scan.l", "/gram.y"),
  "catalog" -> List("/catalog/", "/syscache/"),
  "utils" -> List("/utils/", "/adt/", "/cache/")
)

def detectLayer(filename: String): String = {
  LAYER_PATTERNS.find { case (_, patterns) =>
    patterns.exists(filename.contains)
  }.map(_._1).getOrElse("unknown")
}

def getFileDependencies(file: io.shiftleft.codepropertygraph.generated.nodes.File): List[String] = {
  try {
    // Files this file calls into
    file.ast.isCall.callee.file.name.dedup.l.filterNot(_ == file.name)
  } catch {
    case _: Throwable => List.empty
  }
}

def getFileDependents(file: io.shiftleft.codepropertygraph.generated.nodes.File): List[String] = {
  try {
    // Files that call into this file
    cpg.call.callee.where(_.file.nameExact(file.name)).file.name.dedup.l.filterNot(_ == file.name)
  } catch {
    case _: Throwable => List.empty
  }
}

def detectCircularDependency(file: io.shiftleft.codepropertygraph.generated.nodes.File, dependencies: List[String]): Boolean = {
  try {
    // Simple heuristic: if any dependency also depends on this file
    dependencies.exists { depFile =>
      cpg.file.name(depFile).ast.isCall.callee.file.name.l.contains(file.name)
    }
  } catch {
    case _: Throwable => false
  }
}

def applyDependencyTags(): Unit = {
  val diff = DiffGraphBuilder(cpg.graph.schema)
  var tagged = 0
  var circularCount = 0

  println("[*] Analyzing module dependencies...")

  cpg.file.l.foreach { file =>
    val layer = detectLayer(file.name)
    val dependencies = getFileDependencies(file)
    val dependents = getFileDependents(file)
    val hasCircular = detectCircularDependency(file, dependencies)

    // TAG: layer
    val tagLayer = NewTag().name("module-layer").value(layer)
    diff.addNode(tagLayer)
    diff.addEdge(file, tagLayer, EdgeTypes.TAGGED_BY)

    // TAG: dependencies
    if (dependencies.nonEmpty) {
      val depsStr = dependencies.take(10).mkString(", ")
      val tagDeps = NewTag().name("module-depends-on").value(depsStr)
      diff.addNode(tagDeps)
      diff.addEdge(file, tagDeps, EdgeTypes.TAGGED_BY)
    }

    // TAG: dependents
    if (dependents.nonEmpty) {
      val depsStr = dependents.take(10).mkString(", ")
      val tagDependents = NewTag().name("module-dependents").value(depsStr)
      diff.addNode(tagDependents)
      diff.addEdge(file, tagDependents, EdgeTypes.TAGGED_BY)
    }

    // TAG: circular dependency
    if (hasCircular) {
      val tagCircular = NewTag().name("circular-dependency").value("true")
      diff.addNode(tagCircular)
      diff.addEdge(file, tagCircular, EdgeTypes.TAGGED_BY)
      circularCount += 1
    }

    tagged += 1
    if (tagged % 200 == 0) println(s"[*] Processed $tagged files...")
  }

  flatgraph.DiffGraphApplier.applyDiff(cpg.graph, diff)
  println(s"[+] Tagged $tagged files")
  println(f"[!] Circular dependencies found: $circularCount")

  // Quick layer-level summary
  println("\n[*] Files by layer:")
  cpg.file.tag.name("module-layer").value.l.groupBy(identity).view.mapValues(_.size).toList.sortBy(-_._2).foreach {
    case (layer, count) => println(f"    $layer%-15s: $count")
  }
}

if (APPLY) applyDependencyTags()
