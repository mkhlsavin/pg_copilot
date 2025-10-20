// enrich_field_identifier.sc - field identifier semantic tagging
// Launch: :load enrich_field_identifier.sc
//
// Tags emitted:
//   - `field-semantic`  : semantic description (e.g., visibility-bit-mask, xmin-creator-transaction)
//   - `field-domain`    : domain grouping (heap-tuple, heap-page, visibility-map, ...)
//   - `tag-confidence`  : heuristic confidence indicator
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.semanticcpg.language._
import flatgraph.{DiffGraphApplier, DiffGraphBuilder}

import EnrichCommon._

val APPLY = sys.props.getOrElse("fieldid.apply", "true").toBoolean

println(s"[*] Apply field identifier enrichment: $APPLY")

if (!APPLY) {
  println("[*] Field identifier enrichment skipped (set -Dfieldid.apply=true to run).")
} else {

  case class FieldSemantic(label: String, domain: String, confidence: String)

  val exactMappings: Map[String, FieldSemantic] = Map(
    "t_infomask"   -> FieldSemantic("visibility-bit-mask", "heap-tuple", "high"),
    "t_infomask2"  -> FieldSemantic("visibility-bit-mask", "heap-tuple", "high"),
    "xmin"         -> FieldSemantic("xmin-creator-transaction", "transaction-metadata", "high"),
    "xmax"         -> FieldSemantic("xmax-remover-transaction", "transaction-metadata", "high"),
    "ctid"         -> FieldSemantic("ctid-tuple-pointer", "heap-tuple", "high"),
    "cmin"         -> FieldSemantic("command-min", "transaction-metadata", "medium"),
    "cmax"         -> FieldSemantic("command-max", "transaction-metadata", "medium"),
    "combo_cid"    -> FieldSemantic("combo-command-id", "transaction-metadata", "medium"),
    "pd_flags"     -> FieldSemantic("page-flag", "heap-page", "high"),
    "pd_prune_xid" -> FieldSemantic("page-prune-xid", "heap-page", "high"),
    "pd_linp"      -> FieldSemantic("line-pointer-array", "heap-page", "medium"),
    "pd_lower"     -> FieldSemantic("page-lower-bound", "heap-page", "medium"),
    "pd_upper"     -> FieldSemantic("page-upper-bound", "heap-page", "medium"),
    "pd_special"   -> FieldSemantic("page-special-bound", "heap-page", "medium"),
    "pd_checksum"  -> FieldSemantic("page-checksum", "heap-page", "medium"),
    "pd_pagesize_version" -> FieldSemantic("page-metadata", "heap-page", "medium"),
    "vm_activemap" -> FieldSemantic("visibility-map-bit", "visibility-map", "medium"),
    "vm_frozenmap" -> FieldSemantic("visibility-map-bit", "visibility-map", "medium"),
    "nextxid"      -> FieldSemantic("next-transaction-id", "transaction-metadata", "medium"),
    "latestRemovedXid" -> FieldSemantic("latest-removed-transaction", "transaction-metadata", "medium")
  ).map { case (k, v) => k.toLowerCase -> v }

  val suffixHeuristics: Seq[(String, FieldSemantic)] = Seq(
    ("_lock", FieldSemantic("lock-flag", "lock-management", "medium")),
    ("_mutex", FieldSemantic("lock-flag", "lock-management", "medium")),
    ("_lsn", FieldSemantic("lsn-pointer", "wal", "medium")),
    ("_lsn_hi", FieldSemantic("lsn-pointer", "wal", "low")),
    ("_lsn_lo", FieldSemantic("lsn-pointer", "wal", "low")),
    ("_count", FieldSemantic("counter", "heap-page", "low")),
    ("_offset", FieldSemantic("offset", "heap-page", "low"))
  )

  val diff = DiffGraphBuilder(cpg.graph.schema)
  var tagged = 0

  cpg.fieldIdentifier.l.foreach { field =>
    val rawName = Option(field.canonicalName).filter(_.nonEmpty).getOrElse(Option(field.code).getOrElse(""))
    val name = rawName.toLowerCase

    val semanticOpt =
      exactMappings.get(name).orElse {
        suffixHeuristics.collectFirst {
          case (suffix, semantic) if name.endsWith(suffix) => semantic.copy(confidence = "low")
        }
      }

    semanticOpt.foreach { semantic =>
      val addedSemantic = Tagging.addTag(field, TagCatalog.FieldSemantic.name, semantic.label, diff)
      val addedDomain = Tagging.addTag(field, TagCatalog.FieldDomain.name, semantic.domain, diff)

      if (addedSemantic || addedDomain) {
        Tagging.addConfidence(field, semantic.confidence, diff)
        tagged += 1
      }
    }
  }

  println("[*] Applying field identifier enrichment diff...")
  DiffGraphApplier.applyDiff(cpg.graph, diff)

  println(f"[+] Field identifier enrichment complete. Tagged $tagged%,d nodes.")
}
