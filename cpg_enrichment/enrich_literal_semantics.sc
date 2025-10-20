// enrich_literal_semantics.sc - classify literal nodes by domain and meaning
// Launch: :load enrich_literal_semantics.sc
//
// Tags emitted:
//   - `literal-kind`
//   - `literal-domain`
//   - `literal-constant`
//   - `literal-severity`
//   - `is-null-constant`
//   - `is-lock-constant`
//   - `is-bitmask`
//   - `error-level`
//   - `literal-interpretation`
//   - `boolean-meaning`
//   - `lock-mode`
//   - `tag-confidence`
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.semanticcpg.language._
import flatgraph.{DiffGraphApplier, DiffGraphBuilder}

import EnrichCommon._

val APPLY = sys.props.getOrElse("literal.apply", "true").toBoolean

println(s"[*] Apply literal semantics enrichment: $APPLY")

if (!APPLY) {
  println("[*] Literal enrichment skipped (set -Dliteral.apply=true to run).")
} else {

  case class LiteralAnnotation(
    kind: Option[String] = None,
    domain: Option[String] = None,
    constant: Option[String] = None,
    severity: Option[String] = None,
    isNull: Boolean = false,
    isLock: Boolean = false,
    isBitMask: Boolean = false,
    errorLevel: Option[String] = None,
    interpretation: Option[String] = None,
    booleanMeaning: Option[String] = None,
    lockMode: Option[String] = None,
    confidence: String = "medium"
  )

  val NUMERIC_CONSTANTS: Map[Long, LiteralAnnotation] = Map(
    0L          -> LiteralAnnotation(kind = Some("null-constant"), isNull = true, interpretation = Some("NULL / zero pointer"), confidence = "high"),
    1L          -> LiteralAnnotation(kind = Some("boolean-flag"), booleanMeaning = Some("true"), confidence = "medium"),
    -1L         -> LiteralAnnotation(kind = Some("special-value"), interpretation = Some("invalid / sentinel"), confidence = "medium"),
    8L          -> LiteralAnnotation(kind = Some("bit-mask"), domain = Some("visibility"), isBitMask = true, interpretation = Some("HeapTupleHeader XMAX invalid"), confidence = "medium"),
    16L         -> LiteralAnnotation(kind = Some("bit-mask"), domain = Some("visibility"), isBitMask = true, interpretation = Some("HeapTupleHeader XMAX committed"), confidence = "medium")
  )

  val ERROR_CONSTANTS: Map[String, LiteralAnnotation] = Map(
    "ERRCODE_SYNTAX_ERROR"        -> LiteralAnnotation(kind = Some("error-code"), domain = Some("error"), constant = Some("ERRCODE_SYNTAX_ERROR"), errorLevel = Some("elog-error"), confidence = "high"),
    "ERRCODE_UNDEFINED_TABLE"     -> LiteralAnnotation(kind = Some("error-code"), domain = Some("error"), constant = Some("ERRCODE_UNDEFINED_TABLE"), errorLevel = Some("elog-error"), confidence = "high"),
    "ERRCODE_LOCK_NOT_AVAILABLE"  -> LiteralAnnotation(kind = Some("error-code"), domain = Some("lock"), constant = Some("ERRCODE_LOCK_NOT_AVAILABLE"), errorLevel = Some("elog-error"), confidence = "high"),
    "ERRCODE_WARNING"             -> LiteralAnnotation(kind = Some("error-code"), domain = Some("error"), constant = Some("ERRCODE_WARNING"), errorLevel = Some("elog-warning"), confidence = "medium")
  )

  val LOCK_MODE_CONSTANTS: Map[String, String] = Map(
    "AccessShareLock"          -> "AccessShareLock",
    "RowShareLock"             -> "RowShareLock",
    "RowExclusiveLock"         -> "RowExclusiveLock",
    "ShareUpdateExclusiveLock" -> "ShareUpdateExclusiveLock",
    "ShareLock"                -> "ShareLock",
    "ShareRowExclusiveLock"    -> "ShareRowExclusiveLock",
    "ExclusiveLock"            -> "ExclusiveLock",
    "AccessExclusiveLock"      -> "AccessExclusiveLock"
  )

  val BITMASK_HINTS: Seq[(String, LiteralAnnotation)] = Seq(
    ("0x", LiteralAnnotation(kind = Some("bit-mask"), isBitMask = true, confidence = "medium")),
    ("1 <<", LiteralAnnotation(kind = Some("bit-mask"), isBitMask = true, confidence = "medium"))
  )

  val NULL_STRING_LITERALS: Set[String] = Set("NULL", "null", "Nil", "nullptr", "0")
  val BOOLEAN_TRUE_STRINGS: Set[String] = Set("true", "TRUE", "on", "ON")
  val BOOLEAN_FALSE_STRINGS: Set[String] = Set("false", "FALSE", "off", "OFF")

  def parseLongLiteral(value: String): Option[LiteralAnnotation] = {
    val trimmed = value.trim
    val base10 = trimmed.toLongOption.map(v => NUMERIC_CONSTANTS.getOrElse(v, LiteralAnnotation(kind = Some("magic-number"), confidence = "low")))
    base10.orElse {
      if (trimmed.startsWith("0x") || trimmed.startsWith("0X")) {
        Some(LiteralAnnotation(kind = Some("bit-mask"), isBitMask = true, confidence = "low"))
      } else None
    }
  }

  def classifyStringLiteral(code: String): LiteralAnnotation = {
    val trimmed = code.trim.stripPrefix("\"").stripSuffix("\"")
    if (NULL_STRING_LITERALS.contains(trimmed))
      LiteralAnnotation(kind = Some("null-constant"), isNull = true, interpretation = Some("NULL token"), confidence = "high")
    else if (BOOLEAN_TRUE_STRINGS.contains(trimmed))
      LiteralAnnotation(kind = Some("boolean-flag"), booleanMeaning = Some("true"), confidence = "medium")
    else if (BOOLEAN_FALSE_STRINGS.contains(trimmed))
      LiteralAnnotation(kind = Some("boolean-flag"), booleanMeaning = Some("false"), confidence = "medium")
    else if (trimmed.contains("ERROR") || trimmed.contains("PANIC"))
      LiteralAnnotation(kind = Some("error-code"), domain = Some("error"), severity = Some("error"), errorLevel = Some("elog-error"), confidence = "medium")
    else if (trimmed.contains("WARNING"))
      LiteralAnnotation(kind = Some("error-code"), domain = Some("error"), severity = Some("warning"), errorLevel = Some("elog-warning"), confidence = "low")
    else LiteralAnnotation(interpretation = Some(trimmed), confidence = "low")
  }

  def classifyNumericLiteral(code: String): LiteralAnnotation = {
    val pure = code.replace("_", "")
    NUMERIC_CONSTANTS
      .get(pure.toLongOption.getOrElse(Long.MinValue))
      .orElse(parseLongLiteral(pure))
      .getOrElse {
        if (BITMASK_HINTS.exists { case (hint, _) => code.contains(hint) })
          LiteralAnnotation(kind = Some("bit-mask"), isBitMask = true, confidence = "medium")
        else LiteralAnnotation(kind = Some("magic-number"), confidence = "low")
      }
  }

  val diff = DiffGraphBuilder(cpg.graph.schema)
  var tagged = 0

  cpg.literal.l.foreach { literal =>
    val codeOpt = Option(literal.code).filter(_.nonEmpty)
    val typeFullName = Option(literal.typeFullName).map(_.toLowerCase).getOrElse("")
    val nameContext = literal.astParent.code.headOption.getOrElse("")

    val annotation: LiteralAnnotation = codeOpt match {
      case Some(code) if typeFullName.contains("int") || typeFullName.contains("long") || code.matches("""^-?\d+([lL])?$""") =>
        classifyNumericLiteral(code)
      case Some(code) if typeFullName.contains("char") || typeFullName.contains("string") =>
        classifyStringLiteral(code)
      case Some(code) if code.startsWith("'") && code.endsWith("'") && code.length == 3 =>
        LiteralAnnotation(kind = Some("char-literal"), interpretation = Some(code))
      case Some(code) =>
        LiteralAnnotation(interpretation = Some(code.trim), confidence = "low")
      case None =>
        LiteralAnnotation(confidence = "low")
    }

    val enrichedAnnotation =
      if (annotation.kind.isEmpty && nameContext.contains("lock"))
        annotation.copy(kind = Some("lock-constant"), domain = Some("lock"), isLock = true, lockMode = LOCK_MODE_CONSTANTS.collectFirst { case (lock, _) if nameContext.contains(lock) => lock })
      else annotation

    val toApply = enrichedAnnotation.copy(
      lockMode = enrichedAnnotation.lockMode.orElse(
        LOCK_MODE_CONSTANTS.collectFirst { case (name, lock) if codeOpt.exists(_.contains(lock)) || nameContext.contains(lock) => lock }
      ),
      kind = enrichedAnnotation.kind.orElse {
        if (codeOpt.exists(_.matches("""0[xX][0-9a-fA-F]+"""))) Some("bit-mask") else None
      },
      domain = enrichedAnnotation.domain.orElse {
        if (nameContext.toLowerCase.contains("snapshot")) Some("visibility")
        else if (nameContext.toLowerCase.contains("buffer") || nameContext.toLowerCase.contains("page")) Some("buffer")
        else None
      }
    )

    val confidence = toApply.confidence

    def addTagIfPresent(name: String, valueOpt: Option[String]): Unit = {
      valueOpt.filter(_.nonEmpty).foreach { value =>
        if (Tagging.addTag(literal, name, value, diff)) {
          Tagging.addConfidence(literal, confidence, diff)
          tagged += 1
        }
      }
    }

    addTagIfPresent(TagCatalog.LiteralKind.name, toApply.kind)
    addTagIfPresent(TagCatalog.LiteralDomain.name, toApply.domain)
    addTagIfPresent(TagCatalog.LiteralConstant.name, toApply.constant)
    addTagIfPresent(TagCatalog.LiteralSeverity.name, toApply.severity)
    addTagIfPresent(TagCatalog.LiteralErrorLevel.name, toApply.errorLevel)
    addTagIfPresent(TagCatalog.LiteralInterpretation.name, toApply.interpretation)
    addTagIfPresent(TagCatalog.LiteralBoolMeaning.name, toApply.booleanMeaning)
    addTagIfPresent(TagCatalog.LiteralLockMode.name, toApply.lockMode)

    if (toApply.isNull) {
      Tagging.addTag(literal, TagCatalog.LiteralNullFlag.name, "true", diff)
      Tagging.addConfidence(literal, confidence, diff)
    }
    if (toApply.isBitMask) {
      Tagging.addTag(literal, TagCatalog.LiteralMaskFlag.name, "true", diff)
      Tagging.addConfidence(literal, confidence, diff)
    }
    if (toApply.isLock) {
      Tagging.addTag(literal, TagCatalog.LiteralLockFlag.name, "true", diff)
      Tagging.addConfidence(literal, confidence, diff)
    }
  }

  println("[*] Applying literal semantics enrichment diff...")
  DiffGraphApplier.applyDiff(cpg.graph, diff)

  println(f"[+] Literal semantics enrichment complete. Tagged $tagged%,d literals.")
}
