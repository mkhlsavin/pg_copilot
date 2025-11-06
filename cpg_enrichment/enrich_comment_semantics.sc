// enrich_comment_semantics.sc - mine documentation comments for semantic hints
// Launch: :load enrich_comment_semantics.sc
//
// Tags emitted:
//   - `domain-concept`
//   - `param-role`
//   - `param-domain-concept`
//   - `validation-required`
//   - `tag-confidence`
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.semanticcpg.language._
import flatgraph.{DiffGraphApplier, DiffGraphBuilder}
import java.util.Locale

import EnrichCommon._

val APPLY = sys.props.getOrElse("commentsemantics.apply", "true").toBoolean

println(s"[*] Apply comment-driven semantic enrichment: $APPLY")

if (!APPLY) {
  println("[*] Comment semantic enrichment skipped (set -Dcommentsemantics.apply=true to run).")
} else {

  val diff = DiffGraphBuilder(cpg.graph.schema)
  var methodTagged = 0L
  var paramRoleTagged = 0L
  var paramDomainTagged = 0L
  var validationTagged = 0L

  def lower(value: String): String = Option(value).getOrElse("").toLowerCase(Locale.ROOT)

  val domainHints: Seq[(String, String)] = Seq(
    "visibility map" -> "visibility-map",
    "heap page" -> "heap-page",
    "heap tuple" -> "heap-tuple",
    "logical replication" -> "replication",
    "wal record" -> "wal",
    "xlog" -> "wal",
    "catalog cache" -> "catalog-cache",
    "autovacuum" -> "autovacuum",
    "free space" -> "fsm",
    "buffer manager" -> "buffer"
  )

  val paramRoleHints: Seq[(String, String)] = Seq(
    "snapshot" -> "snapshot",
    "transaction" -> "transaction-context",
    "lock" -> "lock-mode",
    "context" -> "memory-context",
    "buffer" -> "buffer",
    "page" -> "buffer",
    "tuple" -> "tuple",
    "visibility" -> "snapshot"
  )

  val validationHints: Seq[(String, String)] = Seq(
    "must not be null" -> "null-check",
    "cannot be null" -> "null-check",
    "must be non-null" -> "null-check",
    "must be valid" -> "bounds-check",
    "length must" -> "bounds-check",
    "sanitiz" -> "sanitise",
    "must be locked" -> "lock-check"
  )

  def applyMethodDomain(method: Method, comment: String): Unit = {
    domainHints.collectFirst { case (phrase, domain) if comment.contains(phrase) => domain }.foreach { domain =>
      if (Tagging.addTag(method, "domain-concept", domain, diff)) {
        Tagging.addConfidence(method, "medium", diff)
        methodTagged += 1
      }
    }
  }

  def updateParamFromDoc(param: StoredNode, doc: String): Unit = {
    val text = lower(doc)
    param match {
      case p: MethodParameterIn =>
        paramRoleHints.collectFirst { case (phrase, role) if text.contains(phrase) => role }.foreach { role =>
          if (Tagging.addTag(p, TagCatalog.ParamRole.name, role, diff)) {
            Tagging.addConfidence(p, "medium", diff)
            paramRoleTagged += 1
          }
        }
        domainHints.collectFirst { case (phrase, domain) if text.contains(phrase) => domain }.foreach { domain =>
          if (Tagging.addTag(p, TagCatalog.ParamDomainConcept.name, domain, diff)) {
            Tagging.addConfidence(p, "medium", diff)
            paramDomainTagged += 1
          }
        }
        validationHints.collectFirst { case (phrase, validation) if text.contains(phrase) => validation }.foreach { validation =>
          if (Tagging.addTag(p, TagCatalog.ParamValidation.name, validation, diff)) {
            Tagging.addConfidence(p, "medium", diff)
            validationTagged += 1
          }
        }
      case p: MethodParameterOut =>
        domainHints.collectFirst { case (phrase, domain) if text.contains(phrase) => domain }.foreach { domain =>
          if (Tagging.addTag(p, TagCatalog.ParamDomainConcept.name, domain, diff)) {
            Tagging.addConfidence(p, "medium", diff)
            paramDomainTagged += 1
          }
        }
        if (text.contains("written") || text.contains("will be set")) {
          if (Tagging.addTag(p, TagCatalog.ParamRole.name, "output-flag", diff)) {
            Tagging.addConfidence(p, "medium", diff)
            paramRoleTagged += 1
          }
        }
      case _ => ()
    }
  }

  def parseParamDocs(comment: String): Map[String, String] = {
    comment
      .split("[\\r\\n]+")
      .iterator
      .map(_.trim)
      .filter(_.nonEmpty)
      .flatMap { line =>
        val lowerLine = lower(line)
        if (lowerLine.startsWith("@param")) {
          val parts = line.split("\\s+", 3)
          if (parts.length >= 3) Some(parts(1) -> parts(2)) else None
        } else None
      }
      .toMap
  }

  cpg.method.l.foreach { method =>
    val commentOpt = CommentUtil.primaryComment(method).map(_.trim).filter(_.nonEmpty)
    commentOpt.foreach { rawComment =>
      val lowered = lower(rawComment)
      applyMethodDomain(method, lowered)

      val paramDocs = parseParamDocs(rawComment)

      method.parameter.l.collect { case p: MethodParameterIn => p }.foreach { param =>
        val perParamDoc = paramDocs.getOrElse(param.name, rawComment)
        updateParamFromDoc(param, perParamDoc)
      }

    }
  }

  println("[*] Applying comment semantic enrichment diff...")
  DiffGraphApplier.applyDiff(cpg.graph, diff)
  println(f"[+] Methods tagged via comments: $methodTagged%,d")
  println(f"[+] Parameters with comment roles: $paramRoleTagged%,d")
  println(f"[+] Parameters with comment domains: $paramDomainTagged%,d")
  println(f"[+] Validation hints from comments: $validationTagged%,d")
}
