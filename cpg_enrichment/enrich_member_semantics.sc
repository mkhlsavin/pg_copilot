// enrich_member_semantics.sc - annotate structure members
// Launch: :load enrich_member_semantics.sc
//
// Tags emitted:
//   - `member-role`
//   - `member-pointer`
//   - `member-length-field`
//   - `member-unit`
//   - `tag-confidence`
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.semanticcpg.language._
import flatgraph.{DiffGraphApplier, DiffGraphBuilder}

import EnrichCommon._

val APPLY = sys.props.getOrElse("member.apply", "true").toBoolean

println(s"[*] Apply member semantics enrichment: $APPLY")

if (!APPLY) {
  println("[*] Member enrichment skipped (set -Dmember.apply=true to run).")
} else {

  val diff = DiffGraphBuilder(cpg.graph.schema)
  var roleTagged = 0
  var pointerTagged = 0
  var lengthTagged = 0
  var unitTagged = 0

  val lengthTokens = Seq("len", "length", "count", "nitems", "nentries", "ntuples", "nblocks", "ndatum", "size", "rows")
  val pointerTokens = Seq("ptr", "pointer", "ref", "link", "next", "prev", "head", "tail")
  val stateTokens = Seq("state", "status", "flag", "mode", "phase", "level", "enabled")
  val referenceTokens = Seq("parent", "child", "left", "right", "owner", "target")
  val metadataTokens = Seq("info", "meta", "stats", "stat", "desc")

  def lower(value: String): String = Option(value).getOrElse("").toLowerCase

  def classifyRole(name: String, typeName: String): String = {
    val lowerName = name.toLowerCase
    val lowerType = typeName.toLowerCase
    if (stateTokens.exists(lowerName.contains)) "state"
    else if (lengthTokens.exists(lowerName.contains)) "count"
    else if (metadataTokens.exists(lowerName.contains)) "metadata"
    else if (referenceTokens.exists(lowerName.contains) || pointerTokens.exists(lowerName.contains) || lowerType.contains("*") || lowerType.contains("ptr")) "reference"
    else "data"
  }

  def detectPointer(name: String, typeName: String): Boolean = {
    val lowerName = name.toLowerCase
    val lowerType = typeName.toLowerCase
    pointerTokens.exists(lowerName.contains) || lowerType.contains("*") || lowerType.contains("ptr") || lowerType.contains("struct ")
  }

  def detectLength(name: String): Boolean = {
    val lowerName = name.toLowerCase
    lengthTokens.exists(lowerName.contains)
  }

  def inferUnit(name: String): Option[String] = {
    val lowerName = name.toLowerCase
    if (lowerName.contains("byte") || lowerName.contains("size")) Some("bytes")
    else if (lowerName.contains("block") || lowerName.contains("blk")) Some("blocks")
    else if (lowerName.contains("page")) Some("pages")
    else if (lowerName.contains("tuple") || lowerName.contains("row")) Some("tuples")
    else if (lowerName.contains("entry") || lowerName.contains("item")) Some("entries")
    else None
  }

  cpg.member.l.foreach { mem =>
    val name = Option(mem.name).getOrElse("")
    val typeName = Option(mem.typeFullName).getOrElse("")
    if (name.nonEmpty) {
      val role = classifyRole(name, typeName)
      if (Tagging.addTag(mem, TagCatalog.MemberRole.name, role, diff)) {
        Tagging.addConfidence(mem, "medium", diff)
        roleTagged += 1
      }

      if (detectPointer(name, typeName)) {
        if (Tagging.addTag(mem, TagCatalog.MemberPointer.name, "true", diff)) {
          Tagging.addConfidence(mem, "medium", diff)
          pointerTagged += 1
        }
      }

      if (detectLength(name)) {
        if (Tagging.addTag(mem, TagCatalog.MemberLengthField.name, "true", diff)) {
          Tagging.addConfidence(mem, "medium", diff)
          lengthTagged += 1
        }
      }

      inferUnit(name).foreach { unit =>
        if (Tagging.addTag(mem, TagCatalog.MemberUnit.name, unit, diff)) {
          Tagging.addConfidence(mem, "low", diff)
          unitTagged += 1
        }
      }
    }
  }

  println("[*] Applying member enrichment diff...")
  DiffGraphApplier.applyDiff(cpg.graph, diff)

  println(f"[+] Member enrichment complete. Roles: $roleTagged%,d, pointers: $pointerTagged%,d, length fields: $lengthTagged%,d, units: $unitTagged%,d")
}
