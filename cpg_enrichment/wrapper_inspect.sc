val cpgPath = "dummy"
val projectName = "dummy"
if (workspace.projectExists(projectName)) {
  open(projectName)
} else {
  importCpg(cpgPath, projectName, true)
}
def persist(): Unit = workspace.exportCpg(cpgPath)

// enrich_common.sc - shared helpers for enrichment scripts
// Launch (as dependency): :load enrich_common.sc
//
// Purpose:
//   * Centralise tag metadata (name, description, suggested values, confidence levels)
//   * Provide lightweight helper utilities for name-pattern matching, comment harvesting,
//     and safe tag attachment that can be reused across enrichment passes.
//   * Offer common diagnostics (timed logging, pretty counters) to keep individual scripts concise.
//
// Usage:
//   :load enrich_common.sc
//   import EnrichCommon._
//   val diff = DiffGraphBuilder(cpg.graph.schema)
//   Tagging.addTag(method, TagCatalog.ParamRole.name, "snapshot-reader", diff)
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.codepropertygraph.generated.EdgeTypes
import flatgraph.{DiffGraphBuilder, DiffGraphApplier}

import scala.collection.mutable
import scala.util.matching.Regex
import java.time.{Duration, Instant}

object EnrichCommon {

  // ---------------------------------------------------------------------------
  //  Tag metadata (taxonomy)
  // ---------------------------------------------------------------------------

  case class TagSpec(
    name: String,
    description: String,
    expectedValues: Seq[String] = Seq.empty,
    confidenceLevels: Seq[String] = Seq("high", "medium", "low")
  )

  object TagCatalog {
    val ParamRole = TagSpec(
      name = "param-role",
      description = "Semantic role of a parameter or argument (e.g. snapshot, context, buffer, lock-mode).",
      expectedValues = Seq(
        "snapshot",
        "transaction-context",
        "memory-context",
        "lock-mode",
        "relation",
        "buffer",
        "tuple",
        "output-flag",
        "row-count",
        "error-holder",
        "iterator",
        "state-pointer"
      )
    )

    val ParamDomainConcept = TagSpec(
      name = "param-domain-concept",
      description = "Domain concept attached to a parameter/variable (maps to PostgreSQL subsystems).",
      expectedValues = Seq(
        "mvcc",
        "visibility-map",
        "heap-page",
        "index-page",
        "wal-record",
        "freeze-limit",
        "catalog-cache",
        "statistics",
        "autovacuum"
      )
    )

    val ParamValidation = TagSpec(
      name = "validation-required",
      description = "Marks parameters requiring value validation at the call boundary (e.g. must-be-non-null).",
      expectedValues = Seq("null-check", "bounds-check", "security-check", "sanitise")
    )

    val ReturnKind = TagSpec(
      name = "return-kind",
      description = "Describes the semantics of a return value (boolean flag, pointer, struct, list, iterator, etc.).",
      expectedValues = Seq(
        "boolean",
        "status-code",
        "error-code",
        "pointer",
        "struct",
        "list",
        "iterator",
        "optional",
        "allocated-pointer"
      )
    )

    val ReturnFlags = TagSpec(
      name = "return-flags",
      description = "Additional qualifiers for return values (allocates memory, optional, nullable).",
      expectedValues = Seq("allocates-memory", "nullable", "ownership-transfer")
    )

    val TagConfidence = TagSpec(
      name = "tag-confidence",
      description = "Confidence indicator attached to enrichment tags when heuristics are probabilistic.",
      expectedValues = Seq("high", "medium", "low")
    )

    val VariableRole = TagSpec(
      name = "variable-role",
      description = "Semantic role of a variable or identifier (iterator, counter, flag, etc.).",
      expectedValues = Seq(
        "iterator",
        "counter",
        "flag",
        "state",
        "buffer-manager",
        "context-pointer",
        "temporary"
      )
    )

    val DataKind = TagSpec(
      name = "data-kind",
      description = "Domain-specific data kind carried by a variable or identifier.",
      expectedValues = Seq(
        "transaction-id",
        "snapshot",
        "relation",
        "buffer",
        "lock",
        "query",
        "wal-pointer",
        "lsn",
        "tuple"
      )
    )

    val SecuritySensitivity = TagSpec(
      name = "security-sensitivity",
      description = "Marks variables that carry security-sensitive data.",
      expectedValues = Seq("credential", "auth-token", "secret", "personal-data")
    )

    val LockIndicator = TagSpec(
      name = "is-lock",
      description = "Flags variables that represent locks or synchronization primitives.",
      expectedValues = Seq("true")
    )

    val PointerStruct = TagSpec(
      name = "is-pointer-to-struct",
      description = "Marks variables that are pointers to structured data.",
      expectedValues = Seq("true")
    )

    val Lifetime = TagSpec(
      name = "lifetime",
      description = "Storage duration of a local variable.",
      expectedValues = Seq("auto", "static")
    )

    val Mutability = TagSpec(
      name = "mutability",
      description = "Mutability of a local variable.",
      expectedValues = Seq("mutable", "immutable")
    )

    val InitValue = TagSpec(
      name = "init-value",
      description = "Initialization literal captured for a local variable.",
      expectedValues = Seq.empty
    )

    val FieldSemantic = TagSpec(
      name = "field-semantic",
      description = "Semantic description of a FIELD_IDENTIFIER inside PostgreSQL structures.",
      expectedValues = Seq(
        "visibility-bit-mask",
        "xmin-creator-transaction",
        "xmax-remover-transaction",
        "ctid-tuple-pointer",
        "heap-header-flags",
        "page-flag",
        "page-prune-xid",
        "page-lower-bound",
        "page-upper-bound",
        "page-special-bound",
        "visibility-map-bit"
      )
    )

    val FieldDomain = TagSpec(
      name = "field-domain",
      description = "Domain to which the field semantic belongs.",
      expectedValues = Seq(
        "heap-tuple",
        "heap-page",
        "visibility-map",
        "transaction-metadata",
        "page-header",
        "wal",
        "fsm",
        "general"
      )
    )

    val LiteralKind = TagSpec(
      name = "literal-kind",
      description = "Classifies literal nodes by their functional meaning.",
      expectedValues = Seq(
        "error-code",
        "special-value",
        "bit-mask",
        "null-constant",
        "magic-number",
        "boolean-flag",
        "size-constant",
        "timeout",
        "path-string"
      )
    )

    val LiteralDomain = TagSpec(
      name = "literal-domain",
      description = "Domain grouping for literals (transaction, buffer, lock, etc.).",
      expectedValues = Seq(
        "transaction",
        "visibility",
        "buffer",
        "lock",
        "wal",
        "catalog",
        "error",
        "general"
      )
    )

    val LiteralConstant = TagSpec(
      name = "literal-constant",
      description = "Specific named constant represented by a literal (InvalidBlockNumber, etc.).",
      expectedValues = Seq.empty
    )

    val LiteralSeverity = TagSpec(
      name = "literal-severity",
      description = "Severity level derived from literal context (error/notice/warning).",
      expectedValues = Seq("error", "warning", "notice")
    )

    val LiteralNullFlag = TagSpec(
      name = "is-null-constant",
      description = "Indicates literals that represent null/zero pointers or equivalent.",
      expectedValues = Seq("true")
    )

    val LiteralLockFlag = TagSpec(
      name = "is-lock-constant",
      description = "Flags numeric or string constants representing lock modes.",
      expectedValues = Seq("true")
    )

    val LiteralMaskFlag = TagSpec(
      name = "is-bitmask",
      description = "Marks literals that encode bit masks.",
      expectedValues = Seq("true")
    )

    val LiteralErrorLevel = TagSpec(
      name = "error-level",
      description = "Categorises literal error codes or severity levels.",
      expectedValues = Seq("elog-error", "elog-warning", "elog-notice", "elog-debug")
    )

    val LiteralInterpretation = TagSpec(
      name = "literal-interpretation",
      description = "Human-readable explanation of literal meaning.",
      expectedValues = Seq.empty
    )

    val LiteralBoolMeaning = TagSpec(
      name = "boolean-meaning",
      description = "Meaning of boolean/string literal when used as FLAG: true/false, on/off, etc.",
      expectedValues = Seq("true", "false", "on", "off")
    )

    val LiteralLockMode = TagSpec(
      name = "lock-mode",
      description = "Specific lock mode represented by the literal.",
      expectedValues = Seq(
        "AccessShareLock",
        "RowShareLock",
        "RowExclusiveLock",
        "ShareUpdateExclusiveLock",
        "ShareLock",
        "ShareRowExclusiveLock",
        "ExclusiveLock",
        "AccessExclusiveLock"
      )
    )

    val ModifierVisibility = TagSpec(
      name = "modifier-visibility",
      description = "Visibility level derived from modifiers.",
      expectedValues = Seq("public", "protected", "private", "internal")
    )

    val ModifierConcurrency = TagSpec(
      name = "modifier-concurrency",
      description = "Concurrency implications of modifiers.",
      expectedValues = Seq("static-volatile-global", "volatile-access", "atomic-access", "thread-local", "synchronized", "reentrant-hint")
    )

    val ModifierAttribute = TagSpec(
      name = "modifier-attribute",
      description = "Additional attributes from modifiers (immutability, inlining, etc.).",
      expectedValues = Seq("const", "final", "readonly", "inline", "constexpr", "noinline")
    )

    val MemberRole = TagSpec(
      name = "member-role",
      description = "Semantic role of a structure member.",
      expectedValues = Seq("data", "reference", "state", "metadata", "count", "flag")
    )

    val MemberPointer = TagSpec(
      name = "member-pointer",
      description = "Flags members that are pointer fields.",
      expectedValues = Seq("true")
    )

    val MemberLengthField = TagSpec(
      name = "member-length-field",
      description = "Marks members that store length/count information.",
      expectedValues = Seq("true")
    )

    val MemberUnit = TagSpec(
      name = "member-unit",
      description = "Unit associated with a member value.",
      expectedValues = Seq("bytes", "blocks", "pages", "tuples", "entries", "rows")
    )

    val TypeCategory = TagSpec(
      name = "type-category",
      description = "High-level category of a type declaration.",
      expectedValues = Seq("struct", "class", "enum", "union", "interface", "alias", "typedef", "record", "view")
    )

    val TypeDomainEntity = TagSpec(
      name = "type-domain-entity",
      description = "Domain entity represented by the type (table, index, buffer, etc.).",
      expectedValues = Seq(
        "relation",
        "index",
        "heap-tuple",
        "buffer-desc",
        "wal-record",
        "catalog-entry",
        "executor-state",
        "configuration"
      )
    )

    val TypeConcurrencyPrimitive = TagSpec(
      name = "type-concurrency-primitive",
      description = "Marks types that represent concurrency primitives.",
      expectedValues = Seq("spinlock", "mutex", "lwlock", "semaphore", "condition-variable", "latched-flag")
    )

    val TypeOwnershipModel = TagSpec(
      name = "type-ownership-model",
      description = "Ownership / lifecycle semantics for a type declaration.",
      expectedValues = Seq("reference-counted", "copy-on-write", "pinned-buffer", "stack-only", "arena-managed")
    )

    val TypeInstanceCategory = TagSpec(
      name = "type-instance-category",
      description = "Category of a TYPE node instantiation.",
      expectedValues = Seq("primitive", "pointer", "array", "function-pointer", "custom", "generic-instance")
    )

    val TypeInstanceDomain = TagSpec(
      name = "type-instance-domain",
      description = "Domain inferred for a TYPE node from its declaration.",
      expectedValues = Seq("relation", "index", "heap-tuple", "buffer-desc", "wal-record", "catalog-entry", "executor-state", "configuration", "lock-management")
    )

    val MethodRefKind = TagSpec(
      name = "method-ref-kind",
      description = "Classifies method references (callback, function pointer, etc.).",
      expectedValues = Seq("callback", "function-pointer", "virtual-dispatch", "signal-slot", "interrupt-handler")
    )

    val MethodRefUsage = TagSpec(
      name = "method-ref-usage",
      description = "Usage intention for the method reference.",
      expectedValues = Seq("comparator", "predicate", "allocator", "cleanup", "initializer", "notifier")
    )

    val MethodRefTargetDomain = TagSpec(
      name = "method-ref-domain",
      description = "Domain context inferred for the referenced method.",
      expectedValues = Seq("executor", "planner", "storage", "catalog", "buffer", "concurrency", "wal", "configuration")
    )

    val NamespaceLayer = TagSpec(
      name = "namespace-layer",
      description = "High-level layer classification for namespaces.",
      expectedValues = Seq("planner", "executor", "storage", "catalog", "buffer", "replication", "utilities", "tests")
    )

    val NamespaceDomain = TagSpec(
      name = "namespace-domain",
      description = "Domain context of the namespace.",
      expectedValues = Seq("core", "extension", "client", "server", "tools", "configuration")
    )

    val NamespaceLibraryKind = TagSpec(
      name = "namespace-library-kind",
      description = "Library/component kind for the namespace.",
      expectedValues = Seq("core", "extension", "test", "utility", "interface")
    )

    val NamespaceScope = TagSpec(
      name = "namespace-scope",
      description = "Scope of the namespace within PostgreSQL (core subsystem, extension, test, tooling, etc.).",
      expectedValues = Seq("core", "extension", "subsystem", "test", "utility")
    )

    val JumpKind = TagSpec(
      name = "jump-kind",
      description = "Semantic role of a jump target or label.",
      expectedValues = Seq("loop-break", "loop-continue", "error-handler", "cleanup", "retry", "dispatch")
    )

    val JumpDomain = TagSpec(
      name = "jump-domain",
      description = "Domain context inferred for the jump location.",
      expectedValues = Seq("executor", "storage", "transaction", "buffer", "planner", "utility")
    )

    val JumpScope = TagSpec(
      name = "jump-scope",
      description = "Scope or region that the jump applies to (loop, function, cleanup, error handler, etc.).",
      expectedValues = Seq("loop", "function", "cleanup", "error-handler", "retry", "dispatch")
    )

    val ReturnOutcome = TagSpec(
      name = "return-outcome",
      description = "Outcome classification for RETURN nodes.",
      expectedValues = Seq("success", "failure", "partial-success", "retry", "not-applicable")
    )

    val ReturnDomain = TagSpec(
      name = "return-domain",
      description = "Domain context inferred for the return statement.",
      expectedValues = Seq("executor", "planner", "storage", "catalog", "buffer", "concurrency", "wal")
    )

    val ReturnsError = TagSpec(
      name = "returns-error",
      description = "Flags return statements representing error/failure outcomes.",
      expectedValues = Seq("true")
    )

    val ReturnsNull = TagSpec(
      name = "returns-null",
      description = "Flags return statements returning null/0 pointers or equivalents.",
      expectedValues = Seq("true")
    )

      name = "jump-scope",
      description = "Scope classification for a jump target (within loop, function-wide, etc.).",
      expectedValues = Seq("loop", "function", "switch", "global")
    )

      name = "namespace-scope",
      description = "Scope level inferred for the namespace (global vs nested).",
      expectedValues = Seq("global", "nested", "anonymous")
    )

    val TypeGenericKind = TagSpec(
      name = "type-generic-kind",
      description = "Describes whether a type is generic, template specialization, etc.",
      expectedValues = Seq("generic-parameter", "generic-instance", "concrete", "partial-specialization")
    )

    val TypeArgumentKind = TagSpec(
      name = "type-argument-kind",
      description = "Role of a type argument in a generic instantiation.",
      expectedValues = Seq("element-type", "key-type", "value-type", "comparator-type", "allocator-type", "custom")
    )

    val TypeParameterRole = TagSpec(
      name = "type-parameter-role",
      description = "Semantic hint for a type parameter (template parameter).",
      expectedValues = Seq("generic-parameter", "iterator-parameter", "key-parameter", "value-parameter", "element-parameter", "trait-parameter")
    )

    val All: Seq[TagSpec] = Seq(
      ParamRole,
      ParamDomainConcept,
      ParamValidation,
      ReturnKind,
      ReturnFlags,
      ReturnsError,
      ReturnsNull,
      TagConfidence,
      VariableRole,
      DataKind,
      SecuritySensitivity,
      LockIndicator,
      PointerStruct,
      Lifetime,
      Mutability,
      InitValue,
      FieldSemantic,
      FieldDomain,
      LiteralKind,
      LiteralDomain,
      LiteralConstant,
      LiteralSeverity,
      LiteralNullFlag,
      LiteralLockFlag,
      LiteralMaskFlag,
      LiteralErrorLevel,
      LiteralInterpretation,
      LiteralBoolMeaning,
      LiteralLockMode,
      ModifierVisibility,
      ModifierConcurrency,
      ModifierAttribute,
      MemberRole,
      MemberPointer,
      MemberLengthField,
      MemberUnit,
      NamespaceLayer,
      NamespaceDomain,
      NamespaceLibraryKind,
      NamespaceScope,
      JumpKind,
      JumpDomain,
      JumpScope,
      ReturnOutcome,
      ReturnDomain,
      ReturnsError,
      ReturnsNull,
      TypeCategory,
      TypeDomainEntity,
      TypeConcurrencyPrimitive,
      TypeOwnershipModel,
      TypeInstanceCategory,
      TypeInstanceDomain,
      TypeGenericKind,
      TypeArgumentKind,
      TypeParameterRole
    )
  }

  // ---------------------------------------------------------------------------
  //  Name pattern helpers
  // ---------------------------------------------------------------------------

  case class NamePattern(
    label: String,
    tokens: Seq[String],
    weight: Int = 1,
    requireFullToken: Boolean = true
  ) {
    private val normalisedTokens = tokens.map(_.toLowerCase)

    def score(name: String): Int = {
      val lowered = name.toLowerCase
      var matches = 0
      normalisedTokens.foreach { token =>
        val hit =
          if (requireFullToken) lowered.split("[^a-z0-9_]+").exists(_.equals(token))
          else lowered.contains(token)
        if (hit) matches += 1
      }
      matches * weight
    }
  }

  object PatternMatcher {
    def bestMatch(name: String, patterns: Seq[NamePattern], minScore: Int = 1): Option[NamePattern] = {
      val scored = patterns.map(p => p -> p.score(name)).filter(_._2 >= minScore)
      scored.sortBy(-_._2).headOption.map(_._1)
    }

    def allMatches(name: String, patterns: Seq[NamePattern], minScore: Int = 1): Seq[(NamePattern, Int)] =
      patterns
        .map(p => p -> p.score(name))
        .filter(_._2 >= minScore)
        .sortBy { case (_, score) => -score }
  }

  // ---------------------------------------------------------------------------
  //  Comment helpers
  // ---------------------------------------------------------------------------

  object CommentUtil {
    def primaryComment(node: StoredNode): Option[String] = node match {
      case ast: AstNode =>
        ast._astOut.collectAll[Comment].headOption.map(_.code.trim).filter(_.nonEmpty)
      case _ => None
    }

    def containsHint(node: StoredNode, hints: Seq[Regex]): Option[String] =
      primaryComment(node).flatMap { text =>
        hints.collectFirst { case regex if regex.findFirstIn(text).nonEmpty => text }
      }
  }

  // ---------------------------------------------------------------------------
  //  Tagging helpers
  // ---------------------------------------------------------------------------

  object Tagging {
    def hasTag(node: StoredNode, name: String, value: String): Boolean =
      node._taggedByOut.collectAll[Tag].exists(t => t.name == name && t.value == value)

    def addTag(node: StoredNode, name: String, value: String, diff: DiffGraphBuilder): Boolean = {
      if (hasTag(node, name, value)) return false
      val tag = NewTag().name(name).value(value)
      diff.addNode(tag)
      diff.addEdge(node, tag, EdgeTypes.TAGGED_BY)
      true
    }

    def addConfidence(node: StoredNode, confidence: String, diff: DiffGraphBuilder): Unit = {
      addTag(node, TagCatalog.TagConfidence.name, confidence, diff)
    }
  }

  // ---------------------------------------------------------------------------
  //  Diagnostics
  // ---------------------------------------------------------------------------

  object Diagnostics {
    def timed[A](label: String)(block: => A): (A, Duration) = {
      val started = Instant.now()
      val result = block
      val duration = Duration.between(started, Instant.now())
      println(f"[time] $label%-32s -> ${duration.toMillis / 1000.0}%.2fs")
      (result, duration)
    }

    def counter(label: String, value: Long): Unit = {
      println(f"[count] $label%-32s : $value%,d")
    }
  }
}


// ast_comments.sc - attaches source comments to every major AST node (including FILE).
// Launch: :load ast_comments.sc
//
// IMPORTANT: this script MUTATES the graph (creates COMMENT nodes and links them to their owners via AST edges).
//
// ============================================================================
// Parameters
// ============================================================================
// Optional JVM flags (defaults shown):
//   -Dplanner.glob=".*(optimizer|plan).*\\.c"  file filter (regex), default ".*"
//   -Dplanner.maxdist=32                        fallback search window (lines) when scanning upward
//   -Dplanner.limit=0                           limit the number of nodes processed (0 = no limit)
//
// ============================================================================
// Post-run diagnostics (execute after the script completes)
// ============================================================================
//
// 1. Count total comment nodes:
//    cpg.comment.size
//
// 2. Inspect coverage by node type:
//    Map(
//      "FILE" -> cpg.file.filter(_._astOut.collectAll[Comment].nonEmpty).size,
//      "METHOD" -> cpg.method.filter(_._astOut.collectAll[Comment].nonEmpty).size,
//      "CALL" -> cpg.call.filter(_._astOut.collectAll[Comment].nonEmpty).size,
//      "CONTROL_STRUCTURE" -> cpg.controlStructure.filter(_._astOut.collectAll[Comment].nonEmpty).size,
//      "TYPE_DECL" -> cpg.typeDecl.filter(_._astOut.collectAll[Comment].nonEmpty).size,
//      "LOCAL" -> cpg.local.filter(_._astOut.collectAll[Comment].nonEmpty).size,
//      "RETURN" -> cpg.ret.filter(_._astOut.collectAll[Comment].nonEmpty).size
//    )
//
// 3. Show a FILE-level header comment:
//    cpg.file.name(".*createplan\\.c").l.headOption.foreach { f =>
//      println(s"File: ${f.name}")
//      f._astOut.collectAll[Comment].code.l.foreach(println)
//    }
//
// 4. Print three methods and their comments:
//    cpg.method.filter(_._astOut.collectAll[Comment].nonEmpty).l.take(3).foreach { m =>
//      println(s"\n=== Method: ${m.name} (${m.filename}:${m.lineNumber.getOrElse(0)}) ===")
//      m._astOut.collectAll[Comment].code.l.foreach(c => println(s"${c.take(150)}..."))
//    }
//
// 5. Print three call sites with comments:
//    cpg.call.filter(_._astOut.collectAll[Comment].nonEmpty).l.take(3).foreach { c =>
//      println(s"\n=== Call: ${c.code.take(50)} (${c.filename}:${c.lineNumber.getOrElse(0)}) ===")
//      c._astOut.collectAll[Comment].code.l.foreach(cm => println(s"${cm.take(150)}..."))
//    }
//
// 6. Inspect CONTROL_STRUCTURE nodes with comments:
//    cpg.controlStructure.filter(_._astOut.collectAll[Comment].nonEmpty).l.take(3).foreach { cs =>
//      println(s"\n=== CS: ${cs.code.take(30)} (${cs.filename}:${cs.lineNumber.getOrElse(0)}) ===")
//      cs._astOut.collectAll[Comment].code.l.foreach(println)
//    }
//
// 7. Verify comments for a specific method:
//    cpg.method.name("planner").l.headOption.foreach { m =>
//      println(s"Method: ${m.name}")
//      m._astOut.collectAll[Comment].code.l.foreach(println)
//    }
//
// 8. Verify comments for a specific call site:
//    cpg.call.code(".*GetForeignRelSize.*").l.headOption.foreach { c =>
//      println(s"Call: ${c.code}")
//      c._astOut.collectAll[Comment].code.l.foreach(println)
//    }
//
// 9. List all comments in a file:
//    cpg.file.name(".*createplan\\.c").ast.collectAll[Comment].code.l.take(10).foreach(println)
//
// 10. RETURN nodes with comments:
//     cpg.ret.filter(_._astOut.collectAll[Comment].nonEmpty).l.take(3).foreach { r =>
//       println(s"\n=== Return at ${r.filename}:${r.lineNumber.getOrElse(0)} ===")
//       r._astOut.collectAll[Comment].code.l.foreach(println)
//     }
//
// Notes:
// - Use _._astOut for direct child comments of a node
// - Use .ast to traverse the entire subtree and collect nested comments
// ============================================================================
// ========================= Config =========================
val FILE_GLOB       = sys.props.getOrElse("planner.glob", """.*""")
val MAX_FALLBACK    = Try(sys.props.get("planner.maxdist").map(_.toInt).getOrElse(32)).getOrElse(32)
val LIMIT_ROWS: Int = Try(sys.props.get("planner.limit").map(_.toInt).getOrElse(0)).getOrElse(0)
def limit[A](xs: Iterable[A]): Iterable[A] = if (LIMIT_ROWS > 0) xs.take(LIMIT_ROWS) else xs

// ========================= Small utils =========================
def fileOf(n: StoredNode): String =
  n.file.name.headOption.getOrElse("")

def lineOf(n: StoredNode): Int = n match {
  case x: Method            => x.lineNumber.getOrElse(Int.MaxValue)
  case x: ControlStructure  => x.lineNumber.getOrElse(Int.MaxValue)
  case x: Block             => x.lineNumber.getOrElse(Int.MaxValue)
  case x: Call              => x.lineNumber.getOrElse(Int.MaxValue)
  case x: TypeDecl          => x.lineNumber.getOrElse(Int.MaxValue)
  case x: Local             => x.lineNumber.getOrElse(Int.MaxValue)
  case x: Member            => x.lineNumber.getOrElse(Int.MaxValue)
  case x: MethodParameterIn => x.lineNumber.getOrElse(Int.MaxValue)
  case x: Return            => x.lineNumber.getOrElse(Int.MaxValue)
  case x: File              => 1
  case _                    => Int.MaxValue
}

// ---------- FILE content (cache) ----------
val fileCache = scala.collection.mutable.Map.empty[String, Array[String]]
val csEndCache = scala.collection.mutable.Map.empty[(String, Int), Int]
def quoteRe(lit: String): String = Pattern.quote(lit)
def toUnix(p: String): String = p.replace('\\', '/')

def fileLines(filename: String): Option[Array[String]] = {
  fileCache.get(filename).orElse {
    def get(name: String) = cpg.file.name(name).content.headOption.map(_.split("\n", -1))
    val exact  = get(quoteRe(filename))
    val unix   = if (exact.isEmpty) get(quoteRe(toUnix(filename))) else exact
    val tail   = if (unix.isEmpty)  get(".*" + quoteRe(filename) + "$") else unix
    val last   = if (tail.isEmpty)  get(".*" + quoteRe(toUnix(filename)) + "$") else tail
    last.foreach(arr => fileCache.update(filename, arr))
    last
  }
}

case class CommentSpan(start: Int, end: Int, text: String)

// ===== Comment strategy: same-scope / tight-above / fallback / inside-after-brace =====
def isSkippable(s: String): Boolean = {
  val t = s.trim; t.isEmpty || t == "{" || t == "}"
}

def sameScope(lines: Array[String], fromIdx0: Int, anchorLine: Int): Boolean = {
  if (lines.isEmpty || fromIdx0 >= lines.length) return true
  var bal = 0
  var k = fromIdx0 + 1
  val last = math.min(anchorLine - 2, lines.length - 1)
  while (k <= last && k < lines.length) {
    val s = lines(k)
    bal += s.count(_ == '{')
    bal -= s.count(_ == '}')
    if (bal < 0) return false
    k += 1
  }
  true
}

def tightCommentAbove(lines: Array[String], anchorLine: Int): Option[CommentSpan] = {
  if (anchorLine <= 1 || lines.isEmpty) return None
  val maxIdx = lines.length - 1
  var i = math.min(anchorLine - 2, maxIdx)
  while (i >= 0 && i < lines.length && isSkippable(lines(i))) i -= 1
  if (i < 0 || i >= lines.length) return None

  if (lines(i).contains("*/")) {
    val end = i
    var start = i; var found = false
    while (start >= 0 && !found) { if (lines(start).contains("/*")) found = true else start -= 1 }
    if (!found) return None
    var k = end + 1; var tight = true
    val checkUntil = math.min(anchorLine - 2, maxIdx)
    while (tight && k <= checkUntil && k < lines.length) {
      if (!isSkippable(lines(k))) tight = false
      k += 1
    }
    if (tight && sameScope(lines, end, anchorLine))
      Some(CommentSpan(start + 1, end + 1, lines.slice(start, end + 1).mkString("\n")))
    else None
  } else {
    val buf = scala.collection.mutable.ArrayBuffer[String]()
    var j = i
    while (j >= 0 && j < lines.length && lines(j).trim.startsWith("//")) { buf.prepend(lines(j)); j -= 1 }
    if (buf.isEmpty) None
    else {
      val end = i; var k = end + 1; var tight = true
      val checkUntil = math.min(anchorLine - 2, maxIdx)
      while (tight && k <= checkUntil && k < lines.length) {
        if (!isSkippable(lines(k))) tight = false
        k += 1
      }
      if (tight && sameScope(lines, end, anchorLine))
        Some(CommentSpan(j + 2, end + 1, buf.mkString("\n")))
      else None
    }
  }
}

def fallbackNearestBlockSameScope(lines: Array[String], anchorLine: Int, maxDistance: Int): Option[CommentSpan] = {
  if (anchorLine <= 1 || lines.isEmpty) return None
  var i = math.min(anchorLine - 2, lines.length - 1)
  var scanned = 0
  while (i >= 0 && i < lines.length && scanned <= maxDistance) {
    val s = lines(i)
    if (s.contains("*/")) {
      val end = i
      var start = i; var found = false
      while (start >= 0 && start < lines.length && !found && scanned <= maxDistance) {
        if (lines(start).contains("/*")) found = true else { start -= 1; scanned += 1 }
      }
      if (found && sameScope(lines, end, anchorLine)) {
        return Some(CommentSpan(start + 1, end + 1, lines.slice(start, end + 1).mkString("\n")))
      }
    }
    i -= 1; scanned += 1
  }
  None
}

def topHeaderComment(lines: Array[String]): Option[CommentSpan] = {
  if (lines.isEmpty) return None
  var i = 0
  while (i < lines.length && lines(i).trim.isEmpty) i += 1
  if (i >= lines.length) return None
  if (lines(i).trim.startsWith("/*")) {
    val start = i
    while (i < lines.length && !lines(i).contains("*/")) i += 1
    if (i < lines.length) Some(CommentSpan(start + 1, i + 1, lines.slice(start, i + 1).mkString("\n"))) else None
  } else if (lines(i).trim.startsWith("//")) {
    val start = i
    while (i < lines.length && lines(i).trim.startsWith("//")) i += 1
    Some(CommentSpan(start + 1, i, lines.slice(start, i).mkString("\n")))
  } else None
}

// After '{' capture the first comment before executable code
def findBraceLine(lines: Array[String], startLine: Int): Option[Int] = {
  if (lines.isEmpty) return None
  val startIdx = math.max(0, startLine - 1)
  var i = startIdx; var look = 0
  while (i < lines.length && look <= 4) { if (lines(i).contains("{")) return Some(i); i += 1; look += 1 }
  None
}
def tightInsideAfterBrace(lines: Array[String], startLine: Int): Option[CommentSpan] = {
  if (lines.isEmpty) return None
  findBraceLine(lines, startLine).flatMap { braceLine =>
    var i = math.min(braceLine, lines.length - 1)
    while (i < lines.length && isSkippable(lines(i))) i += 1
    if (i >= lines.length) None
    else if (lines(i).trim.startsWith("/*")) {
      val s = i
      while (i < lines.length && !lines(i).contains("*/")) i += 1
      if (i < lines.length) Some(CommentSpan(s + 1, i + 1, lines.slice(s, i + 1).mkString("\n"))) else None
    } else if (lines(i).trim.startsWith("//")) {
      val s = i
      while (i < lines.length && lines(i).trim.startsWith("//")) i += 1
      Some(CommentSpan(s + 1, i, lines.slice(s, i).mkString("\n")))
    } else None
  }
}

// ===== CALL helpers =====
def recvName(c: Call): Option[String] = {
  val code = Option(c.code).getOrElse("")
  // Pattern 1: var->method(...)
  val r1 = """([A-Za-z_]\w*)\s*->\s*\w+\s*\(""".r
  // Pattern 2: (*var)(...)
  val r2 = """\(\*\s*([A-Za-z_]\w*)\s*\)\s*\(""".r

  r1.findFirstMatchIn(code).map(_.group(1))
    .orElse(r2.findFirstMatchIn(code).map(_.group(1)))
}
def findNearestAssignLine(lines: Array[String], callLine: Int, name: String): Option[Int] = {
  if (lines.isEmpty) return None
  val pattern = s"""\\b${Pattern.quote(name)}\\s*=\\s*.*?;""".r
  var i = math.min(callLine - 2, lines.length - 1)
  var checked = 0
  while (i >= 0 && i < lines.length && checked < 10) {
    val t = lines(i).trim
    if (t.nonEmpty) {
      checked += 1
      if (pattern.findFirstIn(lines(i)).isDefined) return Some(i + 1)
      if (!t.startsWith("//") && !t.contains("/*") && !t.contains("*/") && t != "{" && t != "}") return None
    }
    i -= 1
  }
  None
}
def isControlHead(s: String): Boolean = {
  val t = s.trim
  t.startsWith("if") || t.startsWith("else if") || t == "else" ||
  t.startsWith("for") || t.startsWith("while") || t.startsWith("do") ||
  t.startsWith("switch") || t.startsWith("return")
}
def isCodeLine(t: String): Boolean = {
  val s = t.trim
  s.nonEmpty && !s.startsWith("//") && !s.startsWith("/*") && !s.startsWith("*") && s != "{" && s != "}"
}
def prevNonCSStmt(lines: Array[String], line: Int): Option[Int] = {
  if (lines.isEmpty) return None
  var i = math.min(line - 2, lines.length - 1)
  while (i >= 0 && i < lines.length) { val t = lines(i); if (isCodeLine(t) && !isControlHead(t)) return Some(i + 1); i -= 1 }
  None
}
def prevStmt(lines: Array[String], line: Int): Option[Int] = {
  if (lines.isEmpty) return None
  var i = math.min(line - 2, lines.length - 1)
  while (i >= 0 && i < lines.length) { val t = lines(i); if (isCodeLine(t)) return Some(i + 1); i -= 1 }
  None
}
def estimateCsEnd(lines: Array[String], file: String, startLine: Int): Int = {
  csEndCache.getOrElseUpdate((file, startLine), {
    val n = lines.length
    if (n == 0) {
      startLine
    } else {
      val startIdx = math.max(0, startLine - 1)
      var i = startIdx; var br = -1; var look = 0
      while (i < n && look <= 4 && br == -1) { if (lines(i).contains("{")) br = i; i += 1; look += 1 }
      if (br == -1) {
        startLine
      } else {
        var bal = 0; var j = br
        var endLine = startLine
        while (j < n) {
          val s = lines(j)
          bal += s.count(_ == '{')
          bal -= s.count(_ == '}')
          if (bal == 0) {
            endLine = j + 1
            j = n // break
          } else {
            j += 1
          }
        }
        endLine
      }
    }
  })
}

// ========================= Anchors per node =========================
def anchorsForNode(n: StoredNode, lines: Array[String]): List[Int] = n match {
  case f: File =>
    val idx = lines.indexWhere(_.trim.nonEmpty)
    val anchor = if (idx == -1) 1 else idx + 1
    List(anchor)

  case m: Method =>
    List(lineOf(m))

  case cs: ControlStructure =>
    List(lineOf(cs))

  case b: Block =>
    List(lineOf(b))

  case c: Call =>
    val s = lineOf(c)
    val f = fileOf(c)
    val recv = recvName(c).flatMap(nm => findNearestAssignLine(lines, s, nm)).toList
    val prevN = prevNonCSStmt(lines, s).toList
    val csEnclosingStarts: List[Int] = {
      val all = Option(c.method).toList.flatMap(m => try m.controlStructure.toList catch { case _: Throwable => Nil })
        .filter(cs => fileOf(cs) == f && cs.lineNumber.exists(_ <= s))
      all.flatMap(_.lineNumber.flatMap { st =>
        val end = estimateCsEnd(lines, f, st); if (end >= s) Some(st) else None
      }).sorted(Ordering.Int.reverse)
    }
    val mStart = Option(c.method).flatMap(_.lineNumber).toList
    val pStmt  = prevStmt(lines, s).toList
    (List(s) ++ recv ++ prevN ++ csEnclosingStarts ++ mStart ++ pStmt).distinct

  case td: TypeDecl =>
    List(lineOf(td))

  case loc: Local =>
    List(lineOf(loc))

  case mem: Member =>
    List(lineOf(mem))

  case par: MethodParameterIn =>
    List(lineOf(par))

  case ret: Return =>
    List(lineOf(ret))

  case _ =>
    List(lineOf(n))
}

def pickCommentFor(n: StoredNode): Option[CommentSpan] = {
  val fname = fileOf(n)
  val linesOpt = fileLines(fname)
  linesOpt.flatMap { lines =>
    n match {
      case f: File =>
        topHeaderComment(lines)

      case m: Method =>
        val s = lineOf(m)
        tightCommentAbove(lines, s)
          .orElse(tightInsideAfterBrace(lines, s))
          .orElse(fallbackNearestBlockSameScope(lines, s, MAX_FALLBACK))

      case cs: ControlStructure =>
        val s = lineOf(cs)
        tightCommentAbove(lines, s)
          .orElse(tightInsideAfterBrace(lines, s))
          .orElse(fallbackNearestBlockSameScope(lines, s, MAX_FALLBACK))

      case b: Block =>
        val s = lineOf(b)
        tightCommentAbove(lines, s)
          .orElse(tightInsideAfterBrace(lines, s))
          .orElse(fallbackNearestBlockSameScope(lines, s, MAX_FALLBACK))

      case ret: Return =>
        val s = lineOf(ret)
        tightCommentAbove(lines, s)
          .orElse(fallbackNearestBlockSameScope(lines, s, MAX_FALLBACK))

      case _ =>
        val anchors = anchorsForNode(n, lines)
        anchors.iterator
          .map(a => tightCommentAbove(lines, a).orElse(fallbackNearestBlockSameScope(lines, a, MAX_FALLBACK)))
          .collectFirst { case Some(span) => span }
    }
  }
}

// ========================= Graph mutation =========================
def commentExistsForOwner(owner: StoredNode, span: CommentSpan): Boolean = {
  try {
    // For flatgraph we inspect the eager _astOut listing
    val children = owner._astOut.toList
    children.exists {
      case c: Comment =>
        c.lineNumber.contains(span.start) && c.code == span.text
      case _ => false
    }
  } catch {
    case _: Throwable => false
  }
}

def attachComment(owner: StoredNode, span: CommentSpan, diff: DiffGraphBuilder): Unit = {
  val comment = NewComment()
    .code(span.text)
    .lineNumber(span.start)
    .columnNumber(-1)

  diff.addNode(comment)
  diff.addEdge(owner, comment, EdgeTypes.AST)
}

// ========================= Collect nodes & run =========================
println(s"[*] planner.glob  = $FILE_GLOB")
println(s"[*] max fallback  = $MAX_FALLBACK")
println(s"[*] limit         = ${if (LIMIT_ROWS>0) LIMIT_ROWS.toString else "no limit"}")

val files   = cpg.file.name(FILE_GLOB).toList
val methods = cpg.method.where(_.file.name(FILE_GLOB)).toList
val cs      = cpg.controlStructure.where(_.file.name(FILE_GLOB)).toList
val blocks  = cpg.block.where(_.file.name(FILE_GLOB)).toList
val calls   = cpg.call.where(_.file.name(FILE_GLOB)).toList
val tdecls  = cpg.typeDecl.where(_.file.name(FILE_GLOB)).toList
val locals  = cpg.local.where(_.file.name(FILE_GLOB)).toList
val params  = cpg.parameter.where(_.file.name(FILE_GLOB)).toList
val members = cpg.member.where(_.file.name(FILE_GLOB)).toList
val returns = cpg.ret.where(_.file.name(FILE_GLOB)).toList

val allNodes: List[StoredNode] =
  (limit(files) ++
   limit(methods) ++
   limit(cs) ++
   limit(blocks) ++
   limit(calls) ++
   limit(tdecls) ++
   limit(locals) ++
   limit(params) ++
   limit(members) ++
   limit(returns)).toList

println(f"[*] Candidates: ${allNodes.size}%d")

val diff = DiffGraphBuilder(cpg.graph.schema)
var added = 0
var skipped = 0

allNodes.foreach { n =>
  pickCommentFor(n) match {
    case Some(span) if span.text.trim.nonEmpty =>
      if (!commentExistsForOwner(n, span)) {
        attachComment(n, span, diff)
        added += 1
      } else {
        skipped += 1
      }
    case _ => skipped += 1
  }
}

flatgraph.DiffGraphApplier.applyDiff(cpg.graph, diff)

println(f"[+] COMMENTS added : $added%6d")
println(f"[ ] Skipped/exists : $skipped%6d")


persist()
