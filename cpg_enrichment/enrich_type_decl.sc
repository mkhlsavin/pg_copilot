// enrich_type_decl.sc - classify type declarations by domain and category
// Launch: :load enrich_type_decl.sc
//
// Tags emitted:
//   - `type-category`
//   - `type-domain-entity`
//   - `type-concurrency-primitive`
//   - `type-ownership-model`
//   - `tag-confidence`
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.semanticcpg.language._
import flatgraph.{DiffGraphApplier, DiffGraphBuilder}

import EnrichCommon._
import scala.jdk.CollectionConverters._

val APPLY = sys.props.getOrElse("typedef.apply", "true").toBoolean

println(s"[*] Apply type declaration enrichment: $APPLY")

if (!APPLY) {
  println("[*] Type declaration enrichment skipped (set -Dtypedef.apply=true to run).")
} else {

  case class TypeAnnotation(
    category: Option[String] = None,
    domain: Option[String] = None,
    concurrency: Option[String] = None,
    ownership: Option[String] = None,
    confidence: String = "medium"
  )

  val dataStructurePatterns: Seq[(String, String)] = Seq(
    "list" -> "struct",
    "array" -> "struct",
    "hash" -> "struct",
    "tree" -> "struct",
    "map" -> "struct",
    "queue" -> "struct",
    "stack" -> "struct",
    "graph" -> "struct",
    "cache" -> "struct",
    "buffer" -> "struct",
    "set" -> "struct",
    "tuple" -> "struct",
    "record" -> "struct"
  )

  val domainPatterns: Seq[(String, String)] = Seq(
    "relation" -> "relation",
    "relationdata" -> "relation",
    "relcache" -> "catalog-entry",
    "catcache" -> "catalog-entry",
    "heap" -> "heap-tuple",
    "buffer" -> "buffer-desc",
    "bufdesc" -> "buffer-desc",
    "wal" -> "wal-record",
    "xlog" -> "wal-record",
    "snapshot" -> "executor-state",
    "executor" -> "executor-state",
    "planstate" -> "executor-state",
    "pgstat" -> "statistics",
    "lock" -> "lock-management",
    "lwlock" -> "lock-management",
    "spinlock" -> "lock-management",
    "fsm" -> "fsm",
    "visibilitymap" -> "visibility-map"
  )

  val concurrencyPatterns: Seq[(String, String)] = Seq(
    "spinlock" -> "spinlock",
    "mutex" -> "mutex",
    "lwlock" -> "lwlock",
    "semaphore" -> "semaphore",
    "condition" -> "condition-variable",
    "atomic" -> "atomic",
    "slock" -> "spinlock"
  )

  val ownershipPatterns: Seq[(String, String)] = Seq(
    "context" -> "arena-managed",
    "cache" -> "reference-counted",
    "buffer" -> "pinned-buffer",
    "handle" -> "reference-counted",
    "cursor" -> "stack-only",
    "state" -> "stack-only"
  )

  def lowerSafe(value: String): String = Option(value).getOrElse("").toLowerCase

  def classifyTypeDecl(typeDecl: TypeDecl): TypeAnnotation = {
    val nameLower = lowerSafe(typeDecl.name)
    val fullLower = lowerSafe(typeDecl.fullName)
    val inherits = typeDecl.inheritsFromTypeFullName.asScala.map(_.toLowerCase)

    val category =
      if (nameLower.contains("enum")) Some("enum")
      else if (nameLower.contains("union")) Some("union")
      else if (nameLower.contains("class")) Some("class")
      else if (nameLower.contains("struct") || fullLower.contains("struct"))
        Some("struct")
      else if (nameLower.contains("interface")) Some("interface")
      else if (inherits.exists(_.contains("std::vector") | _.contains("List")))
        Some("struct")
      else if (nameLower.contains("typedef") || typeDecl.aliasTypeFullName != null && typeDecl.aliasTypeFullName.nonEmpty)
        Some("alias")
      else None

    val domain =
      domainPatterns.collectFirst {
        case (token, label) if nameLower.contains(token) || fullLower.contains(token) => label
      }

    val concurrency =
      concurrencyPatterns.collectFirst {
        case (token, label) if nameLower.contains(token) || fullLower.contains(token) => label
      }

    val ownership =
      ownershipPatterns.collectFirst {
        case (token, label) if nameLower.contains(token) || fullLower.contains(token) => label
      }

    val derivedCategory =
      if (category.isDefined) category
      else if (domain.contains("lock-management")) Some("struct")
      else if (nameLower.endsWith("state") || nameLower.endsWith("context")) Some("struct")
      else None

    TypeAnnotation(
      category = derivedCategory,
      domain = domain,
      concurrency = concurrency,
      ownership = ownership,
      confidence = "medium"
    )
  }

  val diff = DiffGraphBuilder(cpg.graph.schema)
  var categoryTagged = 0
  var domainTagged = 0
  var concurrencyTagged = 0
  var ownershipTagged = 0

  cpg.typeDecl.l.foreach { typeDecl =>
    val annotation = classifyTypeDecl(typeDecl)

    annotation.category.foreach { value =>
      if (Tagging.addTag(typeDecl, TagCatalog.TypeCategory.name, value, diff)) {
        Tagging.addConfidence(typeDecl, annotation.confidence, diff)
        categoryTagged += 1
      }
    }

    annotation.domain.foreach { value =>
      if (Tagging.addTag(typeDecl, TagCatalog.TypeDomainEntity.name, value, diff)) {
        Tagging.addConfidence(typeDecl, annotation.confidence, diff)
        domainTagged += 1
      }
    }

    annotation.concurrency.foreach { value =>
      if (Tagging.addTag(typeDecl, TagCatalog.TypeConcurrencyPrimitive.name, value, diff)) {
        Tagging.addConfidence(typeDecl, "medium", diff)
        concurrencyTagged += 1
      }
    }

    annotation.ownership.foreach { value =>
      if (Tagging.addTag(typeDecl, TagCatalog.TypeOwnershipModel.name, value, diff)) {
        Tagging.addConfidence(typeDecl, "low", diff)
        ownershipTagged += 1
      }
    }
  }

  println("[*] Applying type declaration enrichment diff...")
  DiffGraphApplier.applyDiff(cpg.graph, diff)

  println(f"[+] Type declaration enrichment complete. Categories: $categoryTagged%,d, domains: $domainTagged%,d, concurrency: $concurrencyTagged%,d, ownership: $ownershipTagged%,d")
}
