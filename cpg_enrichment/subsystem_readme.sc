// subsystem_readme.sc - associate CPG nodes with PostgreSQL subsystem README files
// Launch: :load subsystem_readme.sc
//
// Parameters (defaults shown):
//   -Dsubsystem.srcroot="C:/Users/user/postgres-REL_17_6/src"  PostgreSQL source root
//   -Dsubsystem.apply=true                                      apply tags to the graph
//
// The script discovers README files within PostgreSQL subsystems and:
// 1. Exposes helper APIs to fetch README content for CPG nodes
// 2. Adds FILE-level tags with subsystem metadata:
//    - subsystem-name: subsystem identifier (e.g., "executor")
//    - subsystem-path: path to the README (e.g., "src/backend/executor/README")
//    - subsystem-desc: full README content for RAG context
//
// Useful helpers:
//   listAllSubsystems()
//   getSubsystemReadme("src/backend/executor/execMain.c")
//   getSubsystemByName("executor")
//   getSubsystemReadmeForNode(cpg.method.name("ExecutorStart").head)
//
// Query examples:
//   cpg.file.tag.name("subsystem-name").value.dedup.sorted.l
//   cpg.file.where(_.tag.nameExact("subsystem-name").valueExact("executor")).name.l.take(5)
//   cpg.file.name(".*execMain.*").tag.name("subsystem-desc").value.l.headOption
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.codepropertygraph.generated.{EdgeTypes, NodeTypes}
import flatgraph.DiffGraphBuilder

// ========================= Config =========================
val SRC_ROOT = sys.props.getOrElse("subsystem.srcroot", """C:\Users\user\postgres-REL_17_6\src""")
val APPLY_TAGS = sys.props.getOrElse("subsystem.apply", "true").toBoolean

// README cache: path -> contents
val readmeCache = scala.collection.mutable.Map.empty[String, String]

// Normalize paths for Windows/Unix
def normalizePath(p: String): String = {
  p.replace('\\', '/').replaceFirst("^[A-Za-z]:", "").toLowerCase
}

// Scan the project tree for README files
def findAllReadmes(rootPath: String = SRC_ROOT): Map[String, String] = {
  if (readmeCache.nonEmpty) return readmeCache.toMap

  val root = new File(rootPath).getAbsoluteFile
  if (!root.exists) {
    println(s"[!] WARNING: Source root does not exist: ${root.getAbsolutePath}")
    println(s"[!] Set correct path via -Dsubsystem.srcroot=<path>")
    return Map.empty
  }

  println(s"[*] Scanning for README files in: ${root.getAbsolutePath}")

  def scanDir(dir: File, depth: Int = 0): List[(String, String)] = {
    if (depth > 10 || !dir.exists || !dir.isDirectory) return List.empty

    val readmeFile = new File(dir, "README")
    val result = if (readmeFile.exists && readmeFile.isFile) {
      Try {
        val content = Source.fromFile(readmeFile, "UTF-8").mkString
        val relativePath = root.toPath.relativize(readmeFile.toPath).toString
        readmeCache.update(normalizePath(relativePath), content)
        List((normalizePath(relativePath), content))
      }.getOrElse(List.empty)
    } else List.empty

    val subdirs = Try(dir.listFiles.filter(_.isDirectory).toList).getOrElse(List.empty)
    result ++ subdirs.flatMap(d => scanDir(d, depth + 1))
  }

  val readmes = scanDir(root)
  println(s"[+] Found ${readmes.size} README files")
  readmeCache.toMap
}

// Determine the subsystem for a file (derive from README path)
def getSubsystemForFile(filePath: String, readmes: Map[String, String]): Option[(String, String)] = {
  val normalized = normalizePath(filePath)
  val parts = normalized.split("/").toList

  // Pick the most specific README (deepest hierarchy match)
  val candidates = readmes.toList.flatMap { case (readmePath, content) =>
    val readmeDir = readmePath.split("/").dropRight(1).mkString("/")
    if (normalized.contains(readmeDir) && readmeDir.nonEmpty) {
      Some((readmeDir.split("/").length, readmePath, content))
    } else None
  }

  if (candidates.isEmpty) None
  else {
    val (_, path, content) = candidates.maxBy(_._1)
    Some((path, content))
  }
}

// API: Get README for a specific file path
def getSubsystemReadme(filePath: String): Option[(String, String)] = {
  val readmes = findAllReadmes()
  getSubsystemForFile(filePath, readmes)
}

// API: Get README for any CPG node
def getSubsystemReadmeForNode(node: io.shiftleft.codepropertygraph.generated.nodes.StoredNode): Option[(String, String)] = {
  val filename = node.file.name.headOption.getOrElse("")
  if (filename.isEmpty) None
  else getSubsystemReadme(filename)
}

// API: List all subsystems
def listAllSubsystems(): List[String] = {
  val readmes = findAllReadmes()
  readmes.keys.toList.sorted.map { path =>
    val subsysName = path.split("/").dropRight(1).lastOption.getOrElse("root")
    f"$subsysName%-20s -> $path"
  }
}

// API: Get README by subsystem name (e.g., "executor")
def getSubsystemByName(subsysName: String): Option[(String, String)] = {
  val readmes = findAllReadmes()
  readmes.find { case (path, _) =>
    path.toLowerCase.contains(subsysName.toLowerCase)
  }
}

// API: Group CPG files by subsystem
def getFilesGroupedBySubsystem(): Map[String, List[String]] = {
  val readmes = findAllReadmes()
  cpg.file.l.groupBy { f =>
    getSubsystemForFile(f.name, readmes)
      .map(_._1.split("/").dropRight(1).lastOption.getOrElse("unknown"))
      .getOrElse("unknown")
  }.view.mapValues(_.map(_.name)).toMap
}

// ========================= Graph modification =========================

// Apply tags to FILE nodes
def applySubsystemTags(): Unit = {
  val readmes = findAllReadmes()
  if (readmes.isEmpty) {
    println("[!] No README files found, skipping tag application")
    return
  }

  val diff = DiffGraphBuilder(cpg.graph.schema)
  var tagged = 0
  var totalDescSize = 0L

  println("[*] Applying subsystem tags to FILE nodes...")

  cpg.file.l.foreach { file =>
    getSubsystemForFile(file.name, readmes).foreach { case (readmePath, content) =>
      val subsysName = readmePath.split("/").dropRight(1).lastOption.getOrElse("unknown")

      // Store complete README text for RAG
      val fullDesc = content.trim

      // Create tags
      val tagName = NewTag()
        .name("subsystem-name")
        .value(subsysName)

      val tagPath = NewTag()
        .name("subsystem-path")
        .value(readmePath)

      val tagDesc = NewTag()
        .name("subsystem-desc")
        .value(fullDesc)

      diff.addNode(tagName)
      diff.addNode(tagPath)
      diff.addNode(tagDesc)

      diff.addEdge(file, tagName, EdgeTypes.TAGGED_BY)
      diff.addEdge(file, tagPath, EdgeTypes.TAGGED_BY)
      diff.addEdge(file, tagDesc, EdgeTypes.TAGGED_BY)

      tagged += 1
      totalDescSize += fullDesc.length
    }
  }

  flatgraph.DiffGraphApplier.applyDiff(cpg.graph, diff)
  println(s"[+] Tagged $tagged FILE nodes with subsystem information")
  println(s"[+] Total README content size: ${totalDescSize / 1024} KB")
}

// ========================= Initialization =========================

println(s"[*] Source root: $SRC_ROOT")
println(s"[*] Apply tags: $APPLY_TAGS")

val allReadmes = findAllReadmes()
println(s"[+] Loaded ${allReadmes.size} README files into cache")
println("[*] Use listAllSubsystems() to see all available subsystems")

if (APPLY_TAGS && allReadmes.nonEmpty) {
  applySubsystemTags()
  println("[*] Query examples:")
  println("""    cpg.file.tag.name("subsystem-name").value.dedup.sorted.l""")
  println("""    cpg.file.where(_.tag.nameExact("subsystem-name").valueExact("executor")).name.l""")
} else if (APPLY_TAGS) {
  println("[!] Skipping tag application (no README files found)")
} else {
  println("[*] Tag application disabled. Set -Dsubsystem.apply=true to enable")
}
