// enrich_param_roles.sc - parameter and return-value semantic enrichment
// Launch: :load enrich_param_roles.sc (ensure enrich_common.sc is loaded first)
//
// Tags emitted:
//   - `param-role`             : semantic role for METHOD_PARAMETER_(IN|OUT) nodes
//   - `param-domain-concept`   : PostgreSQL concept associated with the parameter
//   - `validation-required`    : validation expectations for parameters
//   - `return-kind`            : semantic category for METHOD_RETURN nodes
//   - `return-flags`           : qualifiers for return semantics (allocates-memory, nullable, ...)
//   - `tag-confidence`         : confidence level for each tagged node
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.codepropertygraph.generated.EdgeTypes
import io.shiftleft.semanticcpg.language._
import flatgraph.{DiffGraphApplier, DiffGraphBuilder}
import scala.collection.mutable

import EnrichCommon._

val APPLY = sys.props.getOrElse("paramroles.apply", "true").toBoolean

println(s"[*] Apply parameter / return enrichment: $APPLY")

if (!APPLY) {
  println("[*] Parameter/return enrichment skipped (set -Dparamroles.apply=true to run).")
} else {

  // -------------------------------------------------------------------------
  //  Pattern dictionaries
  // -------------------------------------------------------------------------

  case class PatternScore(pattern: NamePattern, nameScore: Int, typeScore: Int) {
    def total: Int = nameScore * 2 + typeScore

    def confidence: String =
      if (nameScore > 0 && typeScore > 0) "high"
      else if (nameScore > 0 || typeScore > 0) "medium"
      else "low"
  }

  def bestPattern(name: String, typeFullName: String, patterns: Seq[NamePattern]): Option[PatternScore] = {
    val evaluated = patterns.map { pattern =>
      val ns = pattern.score(name)
      val ts = pattern.score(typeFullName)
      PatternScore(pattern, ns, ts)
    }.filter(_.total > 0)
    if (evaluated.isEmpty) None else Some(evaluated.maxBy(_.total))
  }

  val rolePatterns = Seq(
    NamePattern("snapshot", Seq("snapshot", "snap"), weight = 4, requireFullToken = false),
    NamePattern("transaction-context", Seq("xact", "transaction", "txn", "xid"), weight = 3, requireFullToken = false),
    NamePattern("memory-context", Seq("memorycontext", "memcxt", "mcxt", "context"), weight = 3, requireFullToken = false),
    NamePattern("relation", Seq("relation", "rel", "table", "index"), weight = 2, requireFullToken = false),
    NamePattern("buffer", Seq("buffer", "buf", "block"), weight = 2, requireFullToken = false),
    NamePattern("tuple", Seq("tuple", "slot", "heap"), weight = 2, requireFullToken = false),
    NamePattern("lock-mode", Seq("lockmode", "lmgr", "lock", "lwlock", "spinlock"), weight = 2, requireFullToken = false),
    NamePattern("iterator", Seq("iter", "cursor", "scan"), weight = 1, requireFullToken = false),
    NamePattern("state-pointer", Seq("state", "data", "info", "ctx"), weight = 1, requireFullToken = false),
    NamePattern("output-flag", Seq("is", "has", "should"), weight = 1, requireFullToken = false)
  )

  val domainPatterns = Seq(
    NamePattern("mvcc", Seq("mvcc", "visibility", "xmin", "xmax"), weight = 4, requireFullToken = false),
    NamePattern("heap-page", Seq("heap", "page", "blkno", "buffer"), weight = 3, requireFullToken = false),
    NamePattern("index-page", Seq("index", "btree", "bt_", "spg", "gin", "gist"), weight = 3, requireFullToken = false),
    NamePattern("wal-record", Seq("wal", "xlog", "xlogrecord", "xl"), weight = 3, requireFullToken = false),
    NamePattern("catalog-cache", Seq("syscache", "relcache", "catcache"), weight = 2, requireFullToken = false),
    NamePattern("statistics", Seq("stat", "anl", "vacuum", "analyze"), weight = 2, requireFullToken = false),
    NamePattern("autovacuum", Seq("autovacuum", "avworker", "av", "worker"), weight = 2, requireFullToken = false)
  )

  val validationHints = Seq(
    "null" -> Seq("ptr", "pointer", "context", "ctx", "info"),
    "bounds" -> Seq("len", "length", "size", "offset", "index"),
    "security" -> Seq("role", "priv", "auth", "acl"),
    "sanitise" -> Seq("str", "query", "sql", "input")
  )

  val commentNullPhrases = Seq(
    "must not be null",
    "cannot be null",
    "must be non-null",
    "null on error"
  )

  val commentBoundsPhrases = Seq(
    "bounds check",
    "length check",
    "validated against"
  )

  def lower(value: String): String = Option(value).getOrElse("").toLowerCase

  def classifyParamData(
      nameRaw: String,
      typeNameRaw: String,
      commentRaw: Option[String]
  ): (Option[(String, String)], Option[(String, String)], Seq[(String, String)]) = {
    val name = lower(nameRaw)
    val typeName = lower(typeNameRaw)

    val role = bestPattern(name, typeName, rolePatterns).map { score =>
      (score.pattern.label, score.confidence)
    }.orElse {
      if (typeName.contains("snapshot")) Some("snapshot" -> "high")
      else if (typeName.contains("memorycontext")) Some("memory-context" -> "medium")
      else if (typeName.contains("relationdata") || typeName.contains("relation")) Some("relation" -> "high")
      else if (typeName.contains("buffer") || typeName.contains("page")) Some("buffer" -> "medium")
      else None
    }

    val domain = bestPattern(name, typeName, domainPatterns).map { score =>
      (score.pattern.label, score.confidence)
    }

    val comment = commentRaw.map(lower).getOrElse("")

    val validations = mutable.ListBuffer.empty[(String, String)]

    validationHints.foreach { case (tagValue, tokens) =>
      if (tokens.exists(t => name.contains(t)) || tokens.exists(t => typeName.contains(t))) {
        val confidence = if (tokens.exists(t => name.contains(t))) "medium" else "low"
        validations += ((tagValue match {
          case "null"      => "null-check"
          case "bounds"    => "bounds-check"
          case "security"  => "security-check"
          case "sanitise"  => "sanitise"
          case other       => other
        }, confidence))
      }
    }

    if (typeName.contains("*") || typeName.contains("ptr")) {
      validations += "null-check" -> "medium"
    }

    if (commentNullPhrases.exists(comment.contains)) {
      validations += "null-check" -> "high"
    }

    if (commentBoundsPhrases.exists(comment.contains)) {
      validations += "bounds-check" -> "high"
    }

    (role, domain, validations.distinct.toSeq)
  }

  def classifyParam(param: MethodParameterIn): (Option[(String, String)], Option[(String, String)], Seq[(String, String)]) =
    classifyParamData(param.name, param.typeFullName, CommentUtil.primaryComment(param))

  def classifyParamOut(param: MethodParameterOut): (Option[(String, String)], Option[(String, String)], Seq[(String, String)]) =
    classifyParamData(param.name, param.typeFullName, CommentUtil.primaryComment(param))

  case class ReturnClassification(kind: Option[String], flags: Seq[String], confidence: String)

  def classifyReturn(method: Method, ret: MethodReturn): ReturnClassification = {
    val methodName = lower(method.name)
    val typeName = lower(ret.typeFullName)
    val comment = CommentUtil.primaryComment(method).map(lower).getOrElse("")

    val pointerLike = typeName.contains("*") || typeName.contains("ptr") || typeName.endsWith("_t")
    val booleanLike = typeName.contains("bool")
    val listLike = typeName.contains("list") || typeName.contains("array") || methodName.contains("list")
    val structLike = typeName.contains("struct") || typeName.contains("tuple") || typeName.contains("state")
    val numericLike = Seq("int", "uint", "oid", "size", "long", "short").exists(typeName.contains)

    val flags = mutable.ListBuffer.empty[String]

    val kind: Option[String] =
      if (booleanLike) {
        Some("boolean")
      } else if (pointerLike && listLike) {
        flags += "nullable"
        Some("list")
      } else if (pointerLike && structLike) {
        flags += "nullable"
        Some("struct")
      } else if (pointerLike) {
        flags += "nullable"
        Some("pointer")
      } else if (listLike) {
        Some("list")
      } else if (structLike) {
        Some("struct")
      } else if (numericLike && (methodName.contains("status") || methodName.contains("result"))) {
        Some("status-code")
      } else if (numericLike && (methodName.contains("err") || comment.contains("error"))) {
        Some("error-code")
      } else if (numericLike) {
        Some("status-code")
      } else {
        None
      }

    if (pointerLike && (methodName.contains("alloc") || methodName.contains("create") || comment.contains("allocated"))) {
      flags += "allocates-memory"
    }

    if (pointerLike && methodName.contains("get")) {
      flags += "optional"
    }

    val confidence =
      if (kind.contains("boolean") || kind.contains("pointer") || kind.contains("struct") || kind.contains("list")) "high"
      else if (kind.nonEmpty) "medium"
      else "low"

    ReturnClassification(kind, flags.distinct.toSeq, confidence)
  }

  // -------------------------------------------------------------------------
  //  Enrichment execution
  // -------------------------------------------------------------------------

  val diff = DiffGraphBuilder(cpg.graph.schema)

  var roleTagged = 0
  var domainTagged = 0
  var validationTagged = 0
  var returnTagged = 0
  var returnFlagTagged = 0

  def annotateParam(param: MethodParameterIn): Unit = {
    val (roleOpt, domainOpt, validations) = classifyParam(param)

    roleOpt.foreach { case (role, confidence) =>
      if (Tagging.addTag(param, TagCatalog.ParamRole.name, role, diff)) {
        roleTagged += 1
        Tagging.addConfidence(param, confidence, diff)
      }
    }

    domainOpt.foreach { case (domain, confidence) =>
      if (Tagging.addTag(param, TagCatalog.ParamDomainConcept.name, domain, diff)) {
        domainTagged += 1
        Tagging.addConfidence(param, confidence, diff)
      }
    }

    validations.foreach { case (validation, confidence) =>
      if (Tagging.addTag(param, TagCatalog.ParamValidation.name, validation, diff)) {
        validationTagged += 1
        Tagging.addConfidence(param, confidence, diff)
      }
    }
  }

  def annotateParamOut(param: MethodParameterOut): Unit = {
    val (roleOpt, domainOpt, validations) = classifyParamOut(param)

    roleOpt.foreach { case (role, confidence) =>
      if (Tagging.addTag(param, TagCatalog.ParamRole.name, role, diff)) {
        roleTagged += 1
        Tagging.addConfidence(param, confidence, diff)
      }
    }

    domainOpt.foreach { case (domain, confidence) =>
      if (Tagging.addTag(param, TagCatalog.ParamDomainConcept.name, domain, diff)) {
        domainTagged += 1
        Tagging.addConfidence(param, confidence, diff)
      }
    }

    validations.foreach { case (validation, confidence) =>
      if (Tagging.addTag(param, TagCatalog.ParamValidation.name, validation, diff)) {
        validationTagged += 1
        Tagging.addConfidence(param, confidence, diff)
      }
    }
  }

  Diagnostics.timed("parameter-role-classification") {
    cpg.parameter.l.foreach(annotateParam)
    cpg.methodParameterOut.l.foreach(annotateParamOut)
  }

  Diagnostics.timed("return-kind-classification") {
    cpg.method.l.foreach { method =>
      val ret = method.methodReturn
      val classification = classifyReturn(method, ret)

      classification.kind.foreach { kind =>
        if (Tagging.addTag(ret, TagCatalog.ReturnKind.name, kind, diff)) {
          returnTagged += 1
          Tagging.addConfidence(ret, classification.confidence, diff)
        }
      }

      classification.flags.foreach { flag =>
        if (Tagging.addTag(ret, TagCatalog.ReturnFlags.name, flag, diff)) {
          returnFlagTagged += 1
          Tagging.addConfidence(ret, classification.confidence, diff)
        }
      }
    }
  }

  println("[*] Applying parameter / return enrichment diff...")
  DiffGraphApplier.applyDiff(cpg.graph, diff)

  println("[+] Parameter / return enrichment complete.")
  Diagnostics.counter("Parameters tagged with param-role", roleTagged)
  Diagnostics.counter("Parameters tagged with param-domain-concept", domainTagged)
  Diagnostics.counter("Parameter validations annotated", validationTagged)
  Diagnostics.counter("Method returns tagged with return-kind", returnTagged)
  Diagnostics.counter("Return flags added", returnFlagTagged)
}
