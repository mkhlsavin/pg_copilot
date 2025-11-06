// dependency_graph.sc - Module dependency analysis
// Launch: :load dependency_graph.sc
//
// Adds: `module-layer`, `module-depends-on`, `module-dependents`, `circular-dependency`
// Example query: cpg.file.tag.nameExact("module-layer").value.dedup.l

import io.shiftleft.codepropertygraph.generated.nodes._
import flatgraph.DiffGraphBuilder

import EnrichCommon._

val APPLY = sys.props.getOrElse("dep.apply", "true").toBoolean

def normalizePath(path: String): String = Option(path).getOrElse("").replace('\\', '/').toLowerCase

def sanitizeSegment(segment: String): String =
  Option(segment).getOrElse("").replaceAll("[^a-z0-9._-]", "-")

def formatLayer(base: String, detail: String): String = {
  val cleanBase = sanitizeSegment(base)
  val cleanDetail = sanitizeSegment(detail)
  if (cleanDetail.isEmpty || cleanDetail == "root") cleanBase else s"$cleanBase/$cleanDetail"
}

def clearExistingModuleTags(): Unit = {
  val cleanup = DiffGraphBuilder(cpg.graph.schema)
  val tagNames = Set("module-layer", "module-depends-on", "module-dependents", "circular-dependency")
  tagNames.foreach { name =>
    cpg.tag.nameExact(name).l.foreach { tag =>
      cleanup.removeNode(tag)
    }
  }
  flatgraph.DiffGraphApplier.applyDiff(cpg.graph, cleanup)
}

val backendTopDirs =
  List(
    "access",
    "archive",
    "backup",
    "bootstrap",
    "catalog",
    "commands",
    "executor",
    "foreign",
    "jit",
    "lib",
    "libpq",
    "main",
    "nodes",
    "optimizer",
    "parser",
    "partitioning",
    "po",
    "port",
    "postmaster",
    "regex",
    "replication",
    "rewrite",
    "snowball",
    "statistics",
    "storage",
    "tcop",
    "tsearch",
    "utils"
  )

val backendAccessDirs =
  List(
    "brin",
    "common",
    "gin",
    "gist",
    "hash",
    "heap",
    "index",
    "nbtree",
    "rmgrdesc",
    "sequence",
    "spgist",
    "table",
    "tablesample",
    "transam"
  )

val backendOptimizerDirs = List("geqo", "path", "plan", "prep", "util")
val backendStorageDirs = List("aio", "buffer", "file", "freespace", "ipc", "large_object", "lmgr", "page", "smgr", "sync")
val backendUtilsDirs =
  List("activity", "adt", "cache", "error", "fmgr", "hash", "init", "mb", "misc", "mmgr", "resowner", "sort", "time")

val includeTopDirs =
  List(
    "access",
    "archive",
    "backup",
    "bootstrap",
    "catalog",
    "commands",
    "common",
    "datatype",
    "executor",
    "fe_utils",
    "foreign",
    "jit",
    "lib",
    "libpq",
    "mb",
    "nodes",
    "optimizer",
    "parser",
    "partitioning",
    "pch",
    "port",
    "portability",
    "postmaster",
    "regex",
    "replication",
    "rewrite",
    "snowball",
    "statistics",
    "storage",
    "tcop",
    "tsearch",
    "utils"
  )

val binApps =
  List(
    "initdb",
    "pg_amcheck",
    "pg_archivecleanup",
    "pg_basebackup",
    "pg_checksums",
    "pg_combinebackup",
    "pg_config",
    "pg_controldata",
    "pg_ctl",
    "pg_dump",
    "pg_resetwal",
    "pg_rewind",
    "pg_test_fsync",
    "pg_test_timing",
    "pg_upgrade",
    "pg_verifybackup",
    "pg_waldump",
    "pg_walsummary",
    "pgbench",
    "pgevent",
    "psql",
    "scripts"
  )

val interfaceDirs = List("ecpg", "libpq")
val plLangs = List("plperl", "plpgsql", "plpython", "tcl")
val testSuites =
  List(
    "authentication",
    "examples",
    "icu",
    "isolation",
    "kerberos",
    "ldap",
    "locale",
    "mb",
    "modules",
    "perl",
    "recovery",
    "regress",
    "ssl",
    "subscription"
  )

val toolDirs = List("ci", "editors", "ifaddrs", "perlcheck", "pg_bsd_indent", "pginclude", "pgindent")

val anchorMap: List[(String, String)] = (
  backendAccessDirs.flatMap { d =>
      List(
        s"/src/backend/access/$d/" -> s"backend/access/$d",
        s"/backend/access/$d/" -> s"backend/access/$d"
      )
    } ++
    backendOptimizerDirs.flatMap { d =>
      List(
        s"/src/backend/optimizer/$d/" -> s"backend/optimizer/$d",
        s"/backend/optimizer/$d/" -> s"backend/optimizer/$d"
      )
    } ++
    backendStorageDirs.flatMap { d =>
      List(
        s"/src/backend/storage/$d/" -> s"backend/storage/$d",
        s"/backend/storage/$d/" -> s"backend/storage/$d"
      )
    } ++
    backendUtilsDirs.flatMap { d =>
      List(
        s"/src/backend/utils/$d/" -> s"backend/utils/$d",
        s"/backend/utils/$d/" -> s"backend/utils/$d"
      )
    } ++
    backendTopDirs.flatMap { d =>
      List(
        s"/src/backend/$d/" -> s"backend/$d",
        s"/backend/$d/" -> s"backend/$d"
      )
    } ++
    includeTopDirs.flatMap { d =>
      List(
        s"/src/include/$d/" -> s"include/$d",
        s"/include/$d/" -> s"include/$d"
      )
    } ++
    binApps.flatMap { d =>
      List(
        s"/src/bin/$d/" -> s"bin/$d",
        s"/bin/$d/" -> s"bin/$d"
      )
    } ++
    interfaceDirs.flatMap { d =>
      List(
        s"/src/interfaces/$d/" -> s"interfaces/$d",
        s"/interfaces/$d/" -> s"interfaces/$d"
      )
    } ++
    plLangs.flatMap { d =>
      List(
        s"/src/pl/$d/" -> s"pl/$d",
        s"/pl/$d/" -> s"pl/$d"
      )
    } ++
    testSuites.flatMap { d =>
      List(
        s"/src/test/$d/" -> s"test/$d",
        s"/test/$d/" -> s"test/$d"
      )
    } ++
    toolDirs.flatMap { d =>
      List(
        s"/src/tools/$d/" -> s"tools/$d",
        s"/tools/$d/" -> s"tools/$d"
      )
    } ++
    List(
      "/src/backend/access/" -> "backend/access",
      "/backend/access/" -> "backend/access",
      "/src/backend/optimizer/" -> "backend/optimizer",
      "/backend/optimizer/" -> "backend/optimizer",
      "/src/backend/storage/" -> "backend/storage",
      "/backend/storage/" -> "backend/storage",
      "/src/backend/utils/" -> "backend/utils",
      "/backend/utils/" -> "backend/utils",
      "/src/backend/" -> "backend",
      "/backend/" -> "backend",
      "/src/include/" -> "include",
      "/include/" -> "include",
      "/src/bin/" -> "bin",
      "/bin/" -> "bin",
      "/src/common/unicode/" -> "common/unicode",
      "/src/common/" -> "common",
      "/common/" -> "common",
      "/src/fe_utils/" -> "fe_utils",
      "/fe_utils/" -> "fe_utils",
      "/src/interfaces/" -> "interfaces",
      "/interfaces/" -> "interfaces",
      "/src/makefiles/" -> "build/makefiles",
      "/src/port/" -> "port",
      "/port/" -> "port",
      "/src/template/" -> "build/template",
      "/src/test/" -> "test",
      "/test/" -> "test",
      "/src/pl/" -> "pl",
      "/pl/" -> "pl",
      "/src/tools/" -> "tools",
      "/tools/" -> "tools",
      "/src/timezone/" -> "timezone",
      "/timezone/" -> "timezone",
      "/src/tutorial/" -> "tutorial",
      "/src/lib/" -> "lib",
      "/lib/" -> "lib",
      "/src/scripts/" -> "scripts",
      "/scripts/" -> "scripts",
      "/contrib/" -> "contrib",
      "/doc/" -> "docs",
      "/config/" -> "config",
      "/interfaces/" -> "interfaces",
      "/common/" -> "common",
      "/include/" -> "include"
    )
).toList

def deriveLayer(path: String): String = {
  val normalized = normalizePath(path)

  if (normalized.isEmpty) {
    "unknown"
  } else {
    if (normalized.startsWith("<") && normalized.endsWith(">")) {
      val inner = normalized.substring(1, normalized.length - 1).replaceAll("[^a-z0-9._-]", "-")
      return if (inner.nonEmpty) s"virtual/$inner" else "virtual"
    }

    val canonical = if (normalized.startsWith("/")) normalized else "/" + normalized

    def detailAfter(marker: String): String = {
      val idx = canonical.indexOf(marker)
      if (idx >= 0) {
        val remainder = canonical.substring(idx + marker.length)
        val segment = remainder.takeWhile(_ != '/')
        if (segment.nonEmpty && !segment.contains(".")) segment else "root"
      } else {
        "root"
      }
    }

    anchorMap.collectFirst {
      case (marker, base) if canonical.contains(marker) =>
        formatLayer(base, detailAfter(marker))
    } match {
      case Some(layer) => layer
      case None =>
        val segments = canonical.stripPrefix("/").split("/").filter(_.nonEmpty).toList
        val withoutDrive = segments.dropWhile(_.matches("^[a-z]:$"))
        val dropWorkspace = withoutDrive.dropWhile(seg =>
          seg == "users" ||
            seg == "user" ||
            seg == "joern" ||
            seg == "workspace" ||
            seg.endsWith(".cpg") ||
            seg.startsWith("postgres") ||
            seg == "tmp" ||
            seg == "temp" ||
            seg == "appdata" ||
            seg == "local" ||
            seg == "share"
        )

        val fallback = if (dropWorkspace.nonEmpty) dropWorkspace else withoutDrive

        val fallbackKey =
          fallback.headOption
            .map { head =>
              val second = fallback.lift(1).getOrElse("root")
              (head, second)
            }
            .getOrElse(("external", "root"))

        fallbackKey match {
          case (base, detail)
              if base.contains("program files") ||
                base.contains("windows kits") ||
                base.contains("microsoft") =>
            formatLayer("external/windows", detail)
          case (base, detail) if base.contains("mingw") || base.contains("msys") =>
            formatLayer("external/mingw", detail)
          case (base, detail) if base == "usr" || base == "lib" || base == "include" =>
            formatLayer("external/system", detail)
          case (base, detail) if base == "llvm" || base == "clang" || base == "gcc" =>
            formatLayer("external/toolchain", detail)
          case (base, detail) if base.startsWith("contrib") =>
            formatLayer("contrib", detail)
          case (base, detail) =>
            val combined = sanitizeSegment(List(base, detail).mkString("-"))
            if (combined.isEmpty || combined == "root") "external"
            else formatLayer("external", combined)
        }
    }
  }
}

def dependentLayersFor(file: File): Set[String] = {
  try {
    file.ast.isCall.callee.file.name.l
      .filterNot(_ == file.name)
      .map(deriveLayer)
      .filterNot(_ == "unknown")
      .toSet
  } catch {
    case _: Throwable => Set.empty
  }
}

def dependentLayersOn(file: File): Set[String] = {
  try {
    cpg.call
      .callee
      .where(_.file.nameExact(file.name))
      .file
      .name
      .l
      .filterNot(_ == file.name)
      .map(deriveLayer)
      .filterNot(_ == "unknown")
      .toSet
  } catch {
    case _: Throwable => Set.empty
  }
}

def applyDependencyTags(): Unit = {
  println("[*] Clearing existing module dependency tags...")
  clearExistingModuleTags()

  val diff = DiffGraphBuilder(cpg.graph.schema)
  var processed = 0
  var circularCount = 0

  println("[*] Analyzing module dependencies...")

  cpg.file.l.foreach { file =>
    val rawName = Option(file.name).getOrElse("")
    val layer = deriveLayer(rawName)
    val dependencies = dependentLayersFor(file)
    val dependents = dependentLayersOn(file)
    val circular = dependencies.intersect(dependents).nonEmpty

    if (Tagging.addTag(file, "module-layer", layer, diff)) {
      Tagging.addConfidence(file, if (layer == "unknown") "low" else "medium", diff)
    }

    val group = layer.takeWhile(ch => ch != '/' && ch != '-')
    val layerGroup = if (group.nonEmpty) group else layer
    if (Tagging.addTag(file, "module-layer-group", layerGroup, diff)) {
      Tagging.addConfidence(file, "low", diff)
    }

    if (dependencies.nonEmpty) {
      val depsStr = dependencies.toList.sorted.take(10).mkString(", ")
      if (Tagging.addTag(file, "module-depends-on", depsStr, diff)) {
        Tagging.addConfidence(file, "medium", diff)
      }
    }

    if (dependents.nonEmpty) {
      val depsStr = dependents.toList.sorted.take(10).mkString(", ")
      if (Tagging.addTag(file, "module-dependents", depsStr, diff)) {
        Tagging.addConfidence(file, "low", diff)
      }
    }

    if (circular) {
      if (Tagging.addTag(file, "circular-dependency", "true", diff)) {
        Tagging.addConfidence(file, "low", diff)
        circularCount += 1
      }
    }

    processed += 1
    if (processed % 200 == 0) println(s"[*] Processed $processed files...")
  }

  flatgraph.DiffGraphApplier.applyDiff(cpg.graph, diff)
  println(s"[+] Tagged $processed files")
  println(f"[!] Circular dependencies found: $circularCount")

  println("\n[*] Files by layer:")
  cpg.file.tag.name("module-layer").value.l
    .groupBy(identity)
    .view
    .mapValues(_.size)
    .toList
    .sortBy(-_._2)
    .foreach { case (layer, count) => println(f"    $layer%-20s : $count%5d") }
}

if (APPLY) applyDependencyTags()
