// enrich_identifier_local.sc - classify identifier and local variable semantics
// Launch: :load enrich_identifier_local.sc
//
// Tags emitted:
//   - `variable-role`          : iterator, counter, flag, etc.
//   - `data-kind`              : domain concepts (transaction-id, snapshot, buffer, ...)
//   - `security-sensitivity`   : credential, auth-token, secret, personal-data
//   - `is-lock`                : flags variables representing locks
//   - `is-pointer-to-struct`   : flags pointers to structured data
//   - `lifetime`               : storage duration (auto/static) for LOCAL nodes
//   - `mutability`             : const vs mutable for LOCAL nodes
//   - `init-value`             : captured literal initialisation for LOCAL nodes
//   - `tag-confidence`         : heuristic confidence indicator
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.semanticcpg.language._
import flatgraph.{DiffGraphApplier, DiffGraphBuilder}

import EnrichCommon._

val APPLY = sys.props.getOrElse("identifier.apply", "true").toBoolean

println(s"[*] Apply identifier/local enrichment: $APPLY")

if (!APPLY) {
  println("[*] Identifier/local enrichment skipped (set -Didentifier.apply=true to run).")
} else {

  case class PatternScore(pattern: NamePattern, nameScore: Int, typeScore: Int) {
    def total: Int = nameScore * 2 + typeScore
    def confidence: String =
      if (nameScore >= 2 || (nameScore > 0 && typeScore > 0)) "high"
      else if (total > 0) "medium"
      else "low"
  }

  def evaluatePattern(name: String, typeFullName: String, pattern: NamePattern): PatternScore = {
    val ns = pattern.score(name)
    val ts = pattern.score(typeFullName)
    PatternScore(pattern, ns, ts)
  }

  def bestPattern(name: String, typeFullName: String, patterns: Seq[NamePattern]): Option[PatternScore] = {
    patterns
      .map(p => evaluatePattern(name, typeFullName, p))
      .filter(_.total > 0)
      .sortBy(score => (-score.total, -score.nameScore))
      .headOption
  }

  val dataKindPatterns = Seq(
    NamePattern("transaction-id", Seq("xmin", "xmax", "xid", "transaction", "xact"), weight = 4, requireFullToken = false),
    NamePattern("snapshot", Seq("snapshot", "snap"), weight = 3, requireFullToken = false),
    NamePattern("relation", Seq("relation", "rel", "table"), weight = 3, requireFullToken = false),
    NamePattern("buffer", Seq("buf", "buffer", "page", "block", "slot"), weight = 2, requireFullToken = false),
    NamePattern("lock", Seq("lock", "latch", "semaphore", "mutex"), weight = 3, requireFullToken = false),
    NamePattern("query", Seq("query", "sql", "cmd", "stmt"), weight = 2, requireFullToken = false),
    NamePattern("wal-pointer", Seq("wal", "xlog"), weight = 2, requireFullToken = false),
    NamePattern("lsn", Seq("lsn"), weight = 3, requireFullToken = true),
    NamePattern("tuple", Seq("tuple", "heap", "row"), weight = 2, requireFullToken = false)
  )

  val securityPatterns = Seq(
    NamePattern("credential", Seq("password", "passwd", "pwd", "credential", "passphrase"), weight = 4, requireFullToken = false),
    NamePattern("auth-token", Seq("token", "secret", "auth", "oauth"), weight = 3, requireFullToken = false),
    NamePattern("secret", Seq("key", "salt", "hash", "cert", "certificate"), weight = 2, requireFullToken = false),
    NamePattern("personal-data", Seq("email", "address", "phone", "ssn"), weight = 2, requireFullToken = false)
  )

  def classifyVariableRole(name: String, typeFullName: String): Option[(String, String)] = {
    val lower = name.toLowerCase
    val typeLower = typeFullName.toLowerCase
    if (lower.contains("iter") || lower.contains("cursor") || lower.endsWith("idx") || lower.endsWith("index") ||
        lower.matches("(?i)[ijk]$") || typeLower.contains("iterator"))
      Some("iterator" -> "high")
    else if (lower.contains("count") || lower.contains("cnt") || lower.contains("num") || lower.contains("total") ||
             lower.endsWith("len") || lower.endsWith("size"))
      Some("counter" -> "medium")
    else if ((name.startsWith("is") && name.lift(2).exists(_.isUpper)) ||
             (name.startsWith("has") && name.lift(3).exists(_.isUpper)) ||
             lower.contains("flag") || lower.contains("enabled") || lower.contains("disable"))
      Some("flag" -> "medium")
    else if (lower.contains("state") || lower.contains("status") || lower.contains("phase") || lower.contains("mode"))
      Some("state" -> "medium")
    else if (lower.contains("ctx") || lower.contains("context") || typeLower.contains("context"))
      Some("context-pointer" -> "medium")
    else if (lower.contains("tmp") || lower.contains("temp") || lower.contains("scratch"))
      Some("temporary" -> "low")
    else None
  }

  def classifyDataKind(name: String, typeFullName: String): Option[(String, String)] = {
    bestPattern(name, typeFullName, dataKindPatterns).map(score => score.pattern.label -> score.confidence)
  }

  def classifySecurity(name: String, typeFullName: String): Option[(String, String)] = {
    bestPattern(name, typeFullName, securityPatterns).map(score => score.pattern.label -> score.confidence)
  }

  def isLock(name: String, typeFullName: String): Boolean = {
    val lower = name.toLowerCase
    val typeLower = typeFullName.toLowerCase
    lower.contains("lock") || lower.contains("latch") || lower.contains("mutex") ||
    typeLower.contains("lock") || typeLower.contains("latch") || typeLower.contains("mutex") || typeLower.contains("spinlock")
  }

  def isPointerToStruct(typeFullName: String): Boolean = {
    val lower = typeFullName.toLowerCase
    (lower.contains("*") || lower.contains("ptr")) &&
    !lower.contains("char*") && !lower.contains("wchar") && !lower.contains("byte*")
  }

  def extractInitValue(local: Local): Option[String] = {
    val literal = local.ast.isLiteral.code.headOption
    val call = if (literal.isEmpty) local.ast.isCall.code.headOption else None
    val value = literal.orElse(call).map(_.trim).filter(_.nonEmpty)
    value.map(v => if (v.length > 80) v.take(77) + "..." else v)
  }

  val diff = DiffGraphBuilder(cpg.graph.schema)
  var identifierTagged = 0
  var localTagged = 0

  def annotateIdentifier(id: Identifier): Unit = {
    val name = Option(id.name).getOrElse("")
    val typeName = Option(id.typeFullName).getOrElse("")

    classifyVariableRole(name, typeName).foreach { case (role, confidence) =>
      if (Tagging.addTag(id, TagCatalog.VariableRole.name, role, diff)) {
        identifierTagged += 1
        Tagging.addConfidence(id, confidence, diff)
      }
    }

    classifyDataKind(name, typeName).foreach { case (kind, confidence) =>
      if (Tagging.addTag(id, TagCatalog.DataKind.name, kind, diff)) {
        Tagging.addConfidence(id, confidence, diff)
      }
    }

    classifySecurity(name, typeName).foreach { case (label, confidence) =>
      if (Tagging.addTag(id, TagCatalog.SecuritySensitivity.name, label, diff)) {
        Tagging.addConfidence(id, confidence, diff)
      }
    }

    if (isLock(name, typeName)) {
      Tagging.addTag(id, TagCatalog.LockIndicator.name, "true", diff)
    }
    if (isPointerToStruct(typeName)) {
      Tagging.addTag(id, TagCatalog.PointerStruct.name, "true", diff)
    }
  }

  def annotateLocal(local: Local): Unit = {
    val name = Option(local.name).getOrElse("")
    val typeName = Option(local.typeFullName).getOrElse("")

    classifyVariableRole(name, typeName).foreach { case (role, confidence) =>
      if (Tagging.addTag(local, TagCatalog.VariableRole.name, role, diff)) {
        localTagged += 1
        Tagging.addConfidence(local, confidence, diff)
      }
    }

    classifyDataKind(name, typeName).foreach { case (kind, confidence) =>
      if (Tagging.addTag(local, TagCatalog.DataKind.name, kind, diff)) {
        Tagging.addConfidence(local, confidence, diff)
      }
    }

    classifySecurity(name, typeName).foreach { case (label, confidence) =>
      if (Tagging.addTag(local, TagCatalog.SecuritySensitivity.name, label, diff)) {
        Tagging.addConfidence(local, confidence, diff)
      }
    }

    val modifiers = local.ast.isModifier.modifierType.l.map(_.toUpperCase).toSet
    val lifetime = if (modifiers.contains("STATIC")) "static" else "auto"
    if (Tagging.addTag(local, TagCatalog.Lifetime.name, lifetime, diff)) {
      Tagging.addConfidence(local, "high", diff)
    }

    val mutability = if (modifiers.contains("CONST")) "immutable" else "mutable"
    if (Tagging.addTag(local, TagCatalog.Mutability.name, mutability, diff)) {
      Tagging.addConfidence(local, "high", diff)
    }

    extractInitValue(local).foreach { value =>
      if (Tagging.addTag(local, TagCatalog.InitValue.name, value, diff)) {
        Tagging.addConfidence(local, "medium", diff)
      }
    }

    if (isLock(name, typeName)) {
      Tagging.addTag(local, TagCatalog.LockIndicator.name, "true", diff)
    }
    if (isPointerToStruct(typeName)) {
      Tagging.addTag(local, TagCatalog.PointerStruct.name, "true", diff)
    }
  }

  println("[*] Classifying identifiers...")
  cpg.identifier.l.foreach(annotateIdentifier)

  println("[*] Classifying local variables...")
  cpg.local.l.foreach(annotateLocal)

  println("[*] Applying identifier/local enrichment diff...")
  DiffGraphApplier.applyDiff(cpg.graph, diff)

  println("[+] Identifier/local enrichment complete.")
  Diagnostics.counter("Identifiers with variable-role", identifierTagged)
  Diagnostics.counter("Locals with variable-role", localTagged)
}
