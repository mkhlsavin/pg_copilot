// enrich_namespace_semantics.sc - annotate namespaces with layer/domain metadata
// Launch: :load enrich_namespace_semantics.sc
//
// Tags emitted:
//   - `namespace-layer`
//   - `namespace-domain`
//   - `namespace-library-kind`
//   - `namespace-scope`
//   - `tag-confidence`
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.semanticcpg.language._
import flatgraph.{DiffGraphApplier, DiffGraphBuilder}

import EnrichCommon._

val APPLY = sys.props.getOrElse("namespace.apply", "true").toBoolean

println(s"[*] Apply namespace enrichment: $APPLY")

if (!APPLY) {
  println("[*] Namespace enrichment skipped (set -Dnamespace.apply=true).")
} else {

  val diff = DiffGraphBuilder(cpg.graph.schema)
  var layerTagged = 0
  var domainTagged = 0
  var libraryTagged = 0
  var scopeTagged = 0

  def lower(value: String): String = Option(value).getOrElse("").toLowerCase

  val layerHints: Seq[(String, String)] = Seq(
    "executor" -> "executor",
    "exec" -> "executor",
    "planner" -> "planner",
    "plan" -> "planner",
    "storage" -> "storage",
    "heap" -> "storage",
    "buffer" -> "buffer",
    "wal" -> "replication",
    "logicalrep" -> "replication",
    "catalog" -> "catalog",
    "parser" -> "planner",
    "optimizer" -> "planner",
    "jit" -> "executor",
    "utils" -> "utilities",
    "test" -> "tests"
  )

  val domainHints: Seq[(String, String)] = Seq(
    "core" -> "core",
    "postgres" -> "core",
    "pgstat" -> "statistics",
    "test" -> "test",
    "mock" -> "test",
    "extension" -> "extension",
    "client" -> "client",
    "frontend" -> "client",
    "backend" -> "server",
    "tools" -> "tools",
    "config" -> "configuration"
  )

  val libraryHints: Seq[(String, String)] = Seq(
    "test" -> "test",
    "mock" -> "test",
    "extension" -> "extension",
    "utils" -> "utility",
    "tool" -> "utility",
    "core" -> "core"
  )

  def classifyScope(namespace: Namespace): String = {
    val name = Option(namespace.name).getOrElse("")
    if (name.isEmpty || name == "<global>") "global"
    else if (name.startsWith("(anonymous")) "anonymous"
    else "nested"
  }

  def tagNamespace(ns: Namespace): Unit = {
    val nameLower = lower(ns.name)
    val fullNameLower = lower(ns.fullName)

    val layer = layerHints.collectFirst {
      case (token, label) if nameLower.contains(token) || fullNameLower.contains(token) => label
    }

    val domain = domainHints.collectFirst {
      case (token, label) if nameLower.contains(token) || fullNameLower.contains(token) => label
    }

    val library = libraryHints.collectFirst {
      case (token, label) if nameLower.contains(token) || fullNameLower.contains(token) => label
    }

    val scope = classifyScope(ns)

    layer.foreach { label =>
      if (Tagging.addTag(ns, TagCatalog.NamespaceLayer.name, label, diff)) {
        Tagging.addConfidence(ns, "medium", diff)
        layerTagged += 1
      }
    }

    domain.foreach { label =>
      if (Tagging.addTag(ns, TagCatalog.NamespaceDomain.name, label, diff)) {
        Tagging.addConfidence(ns, "medium", diff)
        domainTagged += 1
      }
    }

    library.foreach { label =>
      if (Tagging.addTag(ns, TagCatalog.NamespaceLibraryKind.name, label, diff)) {
        Tagging.addConfidence(ns, "low", diff)
        libraryTagged += 1
      }
    }

    if (Tagging.addTag(ns, TagCatalog.NamespaceScope.name, scope, diff)) {
      Tagging.addConfidence(ns, "high", diff)
      scopeTagged += 1
    }
  }

  cpg.namespace.l.foreach(tagNamespace)
  cpg.namespaceBlock.l.foreach(tagNamespace)

  println("[*] Applying namespace enrichment diff...")
  DiffGraphApplier.applyDiff(cpg.graph, diff)

  println(f"[+] Namespace enrichment complete. Layers: $layerTagged%,d, domains: $domainTagged%,d, libraries: $libraryTagged%,d, scope tags: $scopeTagged%,d")
}
