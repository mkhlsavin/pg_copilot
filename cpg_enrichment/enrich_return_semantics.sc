// enrich_return_semantics.sc - classify RETURN statements
// Launch: :load enrich_return_semantics.sc
//
// Tags emitted:
//   - `return-outcome`
//   - `return-domain`
//   - `returns-error`
//   - `returns-null`
//   - `tag-confidence`
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.semanticcpg.language._
import flatgraph.{DiffGraphApplier, DiffGraphBuilder}
import scala.util.Try

import EnrichCommon._

val APPLY = sys.props.getOrElse("return.apply", "true").toBoolean

println(s"[*] Apply return semantics enrichment: $APPLY")

if (!APPLY) {
  println("[*] Return semantics enrichment skipped (set -Dreturn.apply=true).")
} else {

  def lower(value: String): String = Option(value).getOrElse("").toLowerCase

  val diff = DiffGraphBuilder(cpg.graph.schema)
  var outcomeTagged = 0
  var domainTagged = 0
  var errorTagged = 0
  var nullTagged = 0

  val failureTokens = Seq("fail", "failure", "error", "panic", "fatal", "elog", "ereport", "return false", "return eof")
  val successTokens = Seq("ok", "success", "true", "done", "completed", "return 1")
  val retryTokens = Seq("retry", "again", "loop")
  val pointerTypeHints = Seq("*", "ptr", "pointer", "datum", "node", "tuple", "list", "slot", "desc", "context", "entry")
  val nullKeywords = Seq("null", "nullptr", "nil", "pg_nil", "pg_null")
  val errorIdentifierHints = Seq("error", "errcode", "fail", "failure", "panic", "fatal", "elog", "ereport", "pgfatal")
  val errorLiteralHints = Seq("false", "failure", "error", "eof", "exit_failure", "panic")
  val ZeroLiteralRegex = """^\s*0(?:u|ul|ull|l|ll)?\s*$""".r
  val NegativeOneLiteralRegex = """^\s*-1(?:u|ul|ull|l|ll)?\s*$""".r

  def methodReturnType(ret: Ret): String =
    Try(ret.method.methodReturn.typeFullName).getOrElse("")

  def isBooleanReturn(ret: Ret): Boolean = {
    val typeName = lower(methodReturnType(ret))
    typeName.contains("bool") || typeName.contains("boolean")
  }

  def isPointerLikeReturn(ret: Ret): Boolean = {
    val typeName = lower(methodReturnType(ret))
    typeName.contains("*") || pointerTypeHints.exists(hint => typeName.contains(hint))
  }

  def literalValues(ret: Ret): Seq[String] =
    ret.astChildren.isLiteral.code.l.map(code => lower(Option(code).getOrElse("")).trim)

  def identifierValues(ret: Ret): Seq[String] =
    ret.astChildren.isIdentifier.name.l.map(name => lower(Option(name).getOrElse("")).trim)

  def callNames(ret: Ret): Seq[String] =
    ret.astChildren.isCall.name.l.map(name => lower(Option(name).getOrElse("")).trim)

  def classifyOutcome(ret: Ret): Option[String] = {
    val codeText = lower(ret.code)
    val surrounding = lower(ret.astParent.code.headOption.getOrElse(""))
    val booleanReturn = isBooleanReturn(ret)

    if (failureTokens.exists(token => codeText.contains(token) || surrounding.contains(token))) Some("failure")
    else if (booleanReturn && (codeText.contains("return 0") || codeText.contains("return false"))) Some("failure")
    else if (successTokens.exists(token => codeText.contains(token) || surrounding.contains(token))) Some("success")
    else if (retryTokens.exists(codeText.contains)) Some("retry")
    else if (codeText.contains("return")) Some("partial-success")
    else None
  }

  def classifyDomain(ret: Ret): Option[String] = {
    val methodName = lower(ret.method.name)
    if (methodName.contains("executor") || methodName.contains("exec")) Some("executor")
    else if (methodName.contains("plan") || methodName.contains("planner")) Some("planner")
    else if (methodName.contains("heap") || methodName.contains("buffer")) Some("storage")
    else if (methodName.contains("catalog") || methodName.contains("pgstat")) Some("catalog")
    else if (methodName.contains("lock") || methodName.contains("lwlock")) Some("concurrency")
    else if (methodName.contains("wal")) Some("wal")
    else None
  }

  def isErrorReturn(ret: Ret, outcomeOpt: Option[String]): Boolean = {
    val codeLower = lower(ret.code)
    val literals = literalValues(ret)
    val identifiers = identifierValues(ret)
    val calls = callNames(ret)
    val booleanReturn = isBooleanReturn(ret)

    val failureOutcome = outcomeOpt.contains("failure")
    val literalFalse = literals.exists(_.equals("false"))
    val identifierFalse = identifiers.exists(_.equals("false"))
    val zeroLiteral = literals.exists(value => ZeroLiteralRegex.pattern.matcher(value).matches())
    val boolZeroFailure = booleanReturn && (zeroLiteral || codeLower.contains("return 0"))
    val negativeLiteral = literals.exists(value => NegativeOneLiteralRegex.pattern.matcher(value).matches())
    val literalErrorHint = literals.exists(value => errorLiteralHints.exists(hint => value.contains(hint)))
    val identifierErrorHint = identifiers.exists(name => errorIdentifierHints.exists(hint => name.contains(hint)))
    val callErrorHint = calls.exists(name => errorIdentifierHints.exists(hint => name.contains(hint)))
    val codeErrorHint = errorIdentifierHints.exists(hint => codeLower.contains(hint))

    failureOutcome ||
    literalFalse ||
    identifierFalse ||
    boolZeroFailure ||
    negativeLiteral ||
    literalErrorHint ||
    identifierErrorHint ||
    callErrorHint ||
    codeErrorHint
  }

  def isNullReturn(ret: Ret): Boolean = {
    val codeLower = lower(ret.code)
    val literals = literalValues(ret)
    val identifiers = identifierValues(ret)
    val calls = callNames(ret)
    val pointerReturn = isPointerLikeReturn(ret)

    val explicitNullKeyword = nullKeywords.exists(keyword => codeLower.contains(s"return $keyword"))
    val literalNull = literals.exists(value => nullKeywords.contains(value))
    val identifierNull = identifiers.exists { name =>
      nullKeywords.contains(name) || name.endsWith("_null") || name.endsWith("_nil")
    }
    val callNullHint = calls.exists(name => nullKeywords.exists(name.contains) || name.contains("getnull"))
    val zeroLiteral = literals.exists(value => ZeroLiteralRegex.pattern.matcher(value).matches())
    val zeroInCode = codeLower.contains("return 0") || codeLower.replaceAll("\\s+", "").contains("return(datum)0")

    explicitNullKeyword ||
    literalNull ||
    identifierNull ||
    callNullHint ||
    (pointerReturn && (zeroLiteral || zeroInCode))
  }

  cpg.ret.l.foreach { ret =>
    val outcomeOpt = classifyOutcome(ret)
    val errorReturn = isErrorReturn(ret, outcomeOpt)
    val nullReturn = isNullReturn(ret)

    outcomeOpt.foreach { outcome =>
      if (Tagging.addTag(ret, TagCatalog.ReturnOutcome.name, outcome, diff)) {
        Tagging.addConfidence(ret, "medium", diff)
        outcomeTagged += 1
      }
    }

    if (errorReturn) {
      if (Tagging.addTag(ret, TagCatalog.ReturnsError.name, "true", diff)) {
        Tagging.addConfidence(ret, "medium", diff)
        errorTagged += 1
      }
    }

    if (nullReturn) {
      if (Tagging.addTag(ret, TagCatalog.ReturnsNull.name, "true", diff)) {
        Tagging.addConfidence(ret, "medium", diff)
        nullTagged += 1
      }
    }

    classifyDomain(ret).foreach { domain =>
      if (Tagging.addTag(ret, TagCatalog.ReturnDomain.name, domain, diff)) {
        Tagging.addConfidence(ret, "low", diff)
        domainTagged += 1
      }
    }
  }

  println("[*] Applying return semantics enrichment diff...")
  DiffGraphApplier.applyDiff(cpg.graph, diff)

  println(f"[+] Return semantics enrichment complete. Outcomes: $outcomeTagged%,d, domains: $domainTagged%,d, error tags: $errorTagged%,d, null tags: $nullTagged%,d")
}
