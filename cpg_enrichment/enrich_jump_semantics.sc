// enrich_jump_semantics.sc - classify jump labels and targets
// Launch: :load enrich_jump_semantics.sc
//
// Tags emitted:
//   - `jump-kind`
//   - `jump-domain`
//   - `jump-scope`
//   - `tag-confidence`
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.semanticcpg.language._
import flatgraph.{DiffGraphApplier, DiffGraphBuilder}

import EnrichCommon._

val APPLY = sys.props.getOrElse("jump.apply", "true").toBoolean

println(s"[*] Apply jump semantics enrichment: $APPLY")

if (!APPLY) {
  println("[*] Jump semantics enrichment skipped (set -Djump.apply=true to run).")
} else {

  val diff = DiffGraphBuilder(cpg.graph.schema)
  var kindTagged = 0
  var domainTagged = 0
  var scopeTagged = 0

  val errorTokens = Seq("err", "fail", "panic", "error", "abort")
  val cleanupTokens = Seq("cleanup", "free", "release", "unlock", "finish", "done")
  val retryTokens = Seq("retry", "again", "restart")
  val continueTokens = Seq("cont", "continue")
  val breakTokens = Seq("break", "exit", "out")

  def lower(value: String): String = Option(value).getOrElse("").toLowerCase

  def classifyKind(name: String, parentCode: String): Option[String] = {
    val lowerName = lower(name)
    val lowerParent = lower(parentCode)
    if (errorTokens.exists(token => lowerName.contains(token) || lowerParent.contains(token))) Some("error-handler")
    else if (cleanupTokens.exists(token => lowerName.contains(token) || lowerParent.contains(token))) Some("cleanup")
    else if (retryTokens.exists(token => lowerName.contains(token))) Some("retry")
    else if (continueTokens.exists(token => lowerName.contains(token))) Some("loop-continue")
    else if (breakTokens.exists(token => lowerName.contains(token))) Some("loop-break")
    else if (lowerParent.contains("switch") || lowerParent.contains("case")) Some("dispatch")
    else None
  }

  def classifyDomain(code: String): Option[String] = {
    val lowerCode = lower(code)
    if (lowerCode.contains("executor")) Some("executor")
    else if (lowerCode.contains("planner")) Some("planner")
    else if (lowerCode.contains("heap") || lowerCode.contains("buffer")) Some("storage")
    else if (lowerCode.contains("lock")) Some("concurrency")
    else if (lowerCode.contains("wal")) Some("wal")
    else if (lowerCode.contains("catalog")) Some("catalog")
    else None
  }

  def classifyScope(node: AstNode): String = {
    val parents = node.astParents.l
    if (parents.exists(_.isInstanceOf[ControlStructure] && lower(_.asInstanceOf[ControlStructure].code).contains("loop"))) "loop"
    else if (parents.exists(_.isInstanceOf[ControlStructure] && lower(_.asInstanceOf[ControlStructure].code).contains("switch"))) "switch"
    else if (parents.exists(_.isInstanceOf[Method])) "function"
    else "global"
  }

  def tagJump(node: AstNode, nameOpt: Option[String], parentCode: String): Unit = {
    val scope = classifyScope(node)
    if (Tagging.addTag(node, TagCatalog.JumpScope.name, scope, diff)) {
      Tagging.addConfidence(node, "medium", diff)
      scopeTagged += 1
    }

    val kind = nameOpt.flatMap(name => classifyKind(name, parentCode))
    kind.foreach { label =>
      if (Tagging.addTag(node, TagCatalog.JumpKind.name, label, diff)) {
        Tagging.addConfidence(node, "medium", diff)
        kindTagged += 1
      }
    }

    val domain = classifyDomain(parentCode)
    domain.foreach { label =>
      if (Tagging.addTag(node, TagCatalog.JumpDomain.name, label, diff)) {
        Tagging.addConfidence(node, "low", diff)
        domainTagged += 1
      }
    }
  }

  cpg.jumpTarget.l.foreach { jt =>
    val parentCode = jt.astParent.code.headOption.getOrElse("")
    tagJump(jt, Option(jt.name), parentCode)
  }

  cpg.jumpLabel.l.foreach { label =>
    val parentCode = label.astParent.code.headOption.getOrElse("")
    tagJump(label, Option(label.name), parentCode)
  }

  println("[*] Applying jump semantics enrichment diff...")
  DiffGraphApplier.applyDiff(cpg.graph, diff)

  println(f"[+] Jump semantics enrichment complete. Kinds: $kindTagged%,d, domains: $domainTagged%,d, scope tags: $scopeTagged%,d")
}
