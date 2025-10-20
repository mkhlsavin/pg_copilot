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
