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
import java.util.Locale

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

  def lower(value: String): String = Option(value).getOrElse("").toLowerCase(Locale.ROOT)

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

  val domainHints: Seq[(Seq[String], String)] = Seq(
    Seq("executor", "exec") -> "executor",
    Seq("plan", "planner", "optimizer") -> "planner",
    Seq("heap", "buffer", "brin", "gist", "gin", "hash", "index", "smgr", "storage") -> "storage",
    Seq("lock", "lwlock", "spinlock", "semaphore", "mutex") -> "concurrency",
    Seq("wal", "xlog", "lsn", "replication", "logicalrep") -> "wal",
    Seq("catalog", "pgstat", "syscache", "namespace") -> "catalog",
    Seq("analyze", "statistics", "vacuum") -> "statistics",
    Seq("parser", "scan", "lexer") -> "parser"
  )

  def classifyDomain(methodOpt: Option[Method], parentCodeLower: String): Option[String] = {
    val methodNameLower = methodOpt.map(m => lower(Option(m.name).getOrElse(""))).getOrElse("")
    val methodFullNameLower = methodOpt.map(m => lower(Option(m.fullName).getOrElse(""))).getOrElse("")
    val fileLower = methodOpt
      .flatMap(m => Option(m.filename))
      .map(lower)
      .getOrElse("")

    val searchSpace = s"$methodNameLower $methodFullNameLower $fileLower $parentCodeLower"
    domainHints.collectFirst {
      case (tokens, label) if tokens.exists(token => searchSpace.contains(token)) => label
    }
  }

  def classifyScope(parentCodeLower: String, methodNameLower: String): String = {
    if (parentCodeLower.contains("loop") || parentCodeLower.contains("while") || parentCodeLower.contains("for")) "loop"
    else if (parentCodeLower.contains("switch") || parentCodeLower.contains("case")) "switch"
    else if (methodNameLower.nonEmpty) "function"
    else "global"
  }

  def tagJump(node: AstNode, nameOpt: Option[String], parentCode: String, methodOpt: Option[Method]): Unit = {
    val parentCodeLower = lower(parentCode)
    val methodNameLower = methodOpt.map(m => lower(Option(m.name).getOrElse(""))).getOrElse("")

    val scope = classifyScope(parentCodeLower, methodNameLower)
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

    val domain = classifyDomain(methodOpt, parentCodeLower)
    domain.foreach { label =>
      if (Tagging.addTag(node, TagCatalog.JumpDomain.name, label, diff)) {
        Tagging.addConfidence(node, "low", diff)
        domainTagged += 1
      }
    }
  }

  cpg.jumpTarget.l.foreach { jt =>
    val parentCode = jt.astParent.code.headOption.map(_.toString).getOrElse("")
    tagJump(jt, Option(jt.name), parentCode, Option(jt.method))
  }

  cpg.jumpLabel.l.foreach { label =>
    val parentCode = label.astParent.code.headOption.map(_.toString).getOrElse("")
    tagJump(label, Option(label.name), parentCode, None)
  }

  println("[*] Applying jump semantics enrichment diff...")
  DiffGraphApplier.applyDiff(cpg.graph, diff)

  println(f"[+] Jump semantics enrichment complete. Kinds: $kindTagged%,d, domains: $domainTagged%,d, scope tags: $scopeTagged%,d")
}
