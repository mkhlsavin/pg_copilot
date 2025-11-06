// enrich_modifier_semantics.sc - classify modifier nodes (visibility, concurrency, attributes)
// Launch: :load enrich_modifier_semantics.sc
//
// Tags emitted:
//   - `modifier-visibility`
//   - `modifier-concurrency`
//   - `modifier-attribute`
//   - `tag-confidence`
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.semanticcpg.language._
import flatgraph.{DiffGraphApplier, DiffGraphBuilder}
import java.util.Locale

import EnrichCommon._

val APPLY = sys.props.getOrElse("modifier.apply", "true").toBoolean

println(s"[*] Apply modifier semantics enrichment: $APPLY")

if (!APPLY) {
  println("[*] Modifier enrichment skipped (set -Dmodifier.apply=true to run).")
} else {

  val diff = DiffGraphBuilder(cpg.graph.schema)
  var visibilityTagged = 0
  var concurrencyTagged = 0
  var attributeTagged = 0

  def tagVisibility(modifier: Modifier, visibility: String): Unit = {
    if (Tagging.addTag(modifier, TagCatalog.ModifierVisibility.name, visibility, diff)) {
      Tagging.addConfidence(modifier, "high", diff)
      visibilityTagged += 1
    }
  }

  def tagConcurrency(modifier: Modifier, value: String, confidence: String): Unit = {
    if (Tagging.addTag(modifier, TagCatalog.ModifierConcurrency.name, value, diff)) {
      Tagging.addConfidence(modifier, confidence, diff)
      concurrencyTagged += 1
    }
  }

  def tagAttribute(modifier: Modifier, value: String, confidence: String): Unit = {
    if (Tagging.addTag(modifier, TagCatalog.ModifierAttribute.name, value, diff)) {
      Tagging.addConfidence(modifier, confidence, diff)
      attributeTagged += 1
    }
  }

  val modifiersByParent: Map[AstNode, List[Modifier]] =
    cpg.modifier.l
      .flatMap { modifier =>
        Option(modifier.astParent).collect { case parent: AstNode =>
          parent -> modifier
        }
      }
      .groupBy(_._1)
      .view
      .mapValues(_.map(_._2))
      .toMap

  modifiersByParent.foreach { case (_, modifiers) =>
    val types = modifiers.flatMap(m => Option(m.modifierType).map(_.toString.toUpperCase(Locale.ROOT))).toSet

    modifiers.foreach { modifier =>
      Option(modifier.modifierType).map(_.toString.toUpperCase(Locale.ROOT)) match {
        case Some("PUBLIC")    => tagVisibility(modifier, "public")
        case Some("PROTECTED") => tagVisibility(modifier, "protected")
        case Some("PRIVATE")   => tagVisibility(modifier, "private")
        case Some("INTERNAL")  => tagVisibility(modifier, "internal")
        case Some("CONST") | Some("CONSTEXPR") =>
          tagAttribute(modifier, "const", "high")
        case Some("FINAL") =>
          tagAttribute(modifier, "final", "medium")
        case Some("READONLY") =>
          tagAttribute(modifier, "readonly", "medium")
        case Some("INLINE") =>
          tagAttribute(modifier, "inline", "low")
        case Some("NOINLINE") =>
          tagAttribute(modifier, "noinline", "low")
        case Some("VOLATILE") =>
          tagConcurrency(modifier, if (types.contains("STATIC")) "static-volatile-global" else "volatile-access", "medium")
        case Some("STATIC") =>
          if (types.contains("VOLATILE")) {
            tagConcurrency(modifier, "static-volatile-global", "medium")
          } else {
            tagConcurrency(modifier, "static-storage", "medium")
          }
          tagAttribute(modifier, "static", "medium")
        case Some("THREAD_LOCAL") | Some("THREADLOCAL") =>
          tagConcurrency(modifier, "thread-local", "medium")
        case Some("ATOMIC") =>
          tagConcurrency(modifier, "atomic-access", "medium")
        case Some("SYNCHRONIZED") | Some("LOCKED") =>
          tagConcurrency(modifier, "synchronized", "medium")
        case Some("REENTRANT") =>
          tagConcurrency(modifier, "reentrant-hint", "low")
        case Some("VIRTUAL") =>
          tagAttribute(modifier, "virtual", "medium")
        case Some("LAMBDA") =>
          tagAttribute(modifier, "lambda-capture", "low")
        case _ => // no-op for now
      }
    }
  }

  println("[*] Applying modifier enrichment diff...")
  DiffGraphApplier.applyDiff(cpg.graph, diff)

  println(f"[+] Modifier enrichment complete. Visibility: $visibilityTagged%,d, concurrency: $concurrencyTagged%,d, attributes: $attributeTagged%,d")
}
