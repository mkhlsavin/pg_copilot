// enrich_method_ref.sc - classify METHOD_REF nodes
// Launch: :load enrich_method_ref.sc
//
// Tags emitted:
//   - `method-ref-kind`
//   - `method-ref-usage`
//   - `method-ref-domain`
//   - `tag-confidence`
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.semanticcpg.language._
import flatgraph.{DiffGraphApplier, DiffGraphBuilder}

import EnrichCommon._

val APPLY = sys.props.getOrElse("methodref.apply", "true").toBoolean

println(s"[*] Apply method reference enrichment: $APPLY")

if (!APPLY) {
  println("[*] Method reference enrichment skipped (set -Dmethodref.apply=true).")
} else {

  def lower(value: String): String = Option(value).getOrElse("").toLowerCase

  val usageHints: Seq[(String, String)] = Seq(
    "compare" -> "comparator",
    "cmp" -> "comparator",
    "less" -> "comparator",
    "greater" -> "comparator",
    "predicate" -> "predicate",
    "filter" -> "predicate",
    "alloc" -> "allocator",
    "create" -> "initializer",
    "init" -> "initializer",
    "cleanup" -> "cleanup",
    "destroy" -> "cleanup",
    "free" -> "cleanup",
    "notify" -> "notifier",
    "callback" -> "callback"
  )

  val diff = DiffGraphBuilder(cpg.graph.schema)
  var kindTagged = 0
  var usageTagged = 0
  var domainTagged = 0

  cpg.methodRef.l.foreach { ref =>
    val fullName = Option(ref.methodFullName).getOrElse("")
    val typeName = Option(ref.typeFullName).getOrElse("")
    val parentCode = ref.astParent.code.headOption.getOrElse("")

    val isFunctionPointer = typeName.contains("(*)") || typeName.contains("(*)") || typeName.contains("(*"") || typeName.contains("std::function")
    val isCallback = fullName.toLowerCase.contains("callback") || parentCode.toLowerCase.contains("callback")
    val isVirtual = typeName.toLowerCase.contains("virtual")
    val isSignal = parentCode.toLowerCase.contains("signal") || parentCode.toLowerCase.contains("slot")

    val refKind =
      if (isCallback) Some("callback")
      else if (isSignal) Some("signal-slot")
      else if (isVirtual) Some("virtual-dispatch")
      else if (isFunctionPointer) Some("function-pointer")
      else Some("function-pointer")

    refKind.foreach { kind =>
      if (Tagging.addTag(ref, TagCatalog.MethodRefKind.name, kind, diff)) {
        Tagging.addConfidence(ref, "medium", diff)
        kindTagged += 1
      }
    }

    val usage = usageHints.collectFirst {
      case (token, label) if lower(fullName).contains(token) || lower(parentCode).contains(token) => label
    }

    usage.foreach { label =>
      if (Tagging.addTag(ref, TagCatalog.MethodRefUsage.name, label, diff)) {
        Tagging.addConfidence(ref, "low", diff)
        usageTagged += 1
      }
    }

    // Domain inference via call target if available
    ref._refOut.collectAll[Method].headOption.foreach { target =>
      val domainTag = target._taggedByOut.collectAll[Tag].find(_.name == TagCatalog.ParamDomainConcept.name).map(_.value)
      domainTag.foreach { domain =>
        if (Tagging.addTag(ref, TagCatalog.MethodRefTargetDomain.name, domain, diff)) {
          Tagging.addConfidence(ref, "low", diff)
          domainTagged += 1
        }
      }
    }
  }

  println("[*] Applying method reference enrichment diff...")
  DiffGraphApplier.applyDiff(cpg.graph, diff)

  println(f"[+] Method reference enrichment complete. Kinds: $kindTagged%,d, usages: $usageTagged%,d, domains: $domainTagged%,d")
}
