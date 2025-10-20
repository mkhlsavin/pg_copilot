// enrich_type_usage.sc - classify TYPE, TYPE_ARGUMENT, and TYPE_PARAMETER nodes
// Launch: :load enrich_type_usage.sc
//
// Tags emitted:
//   - `type-instance-category`
//   - `type-instance-domain`
//   - `type-generic-kind`
//   - `type-argument-kind`
//   - `type-parameter-role`
//   - `type-concurrency-primitive` (propagated)
//   - `type-ownership-model` (propagated)
//   - `tag-confidence`
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.semanticcpg.language._
import flatgraph.{DiffGraphApplier, DiffGraphBuilder}

import EnrichCommon._
import scala.jdk.CollectionConverters._

val APPLY = sys.props.getOrElse("typeusage.apply", "true").toBoolean

println(s"[*] Apply type usage enrichment: $APPLY")

if (!APPLY) {
  println("[*] Type usage enrichment skipped (set -Dtypeusage.apply=true to run).")
} else {

  case class DeclInfo(
    domain: Option[String],
    concurrency: Option[String],
    ownership: Option[String]
  )

  val typeDeclInfo: Map[String, DeclInfo] = cpg.typeDecl.l.map { td =>
    val domain = td.tag.nameExact(TagCatalog.TypeDomainEntity.name).value.headOption
    val concurrency = td.tag.nameExact(TagCatalog.TypeConcurrencyPrimitive.name).value.headOption
    val ownership = td.tag.nameExact(TagCatalog.TypeOwnershipModel.name).value.headOption
    td.fullName -> DeclInfo(domain, concurrency, ownership)
  }.toMap

  val primitiveTypes = Set(
    "void", "bool", "boolean", "char", "wchar_t", "short", "int", "long", "float", "double",
    "size_t", "ptrdiff_t", "uint8", "uint16", "uint32", "uint64", "int8", "int16", "int32", "int64"
  )

  val diff = DiffGraphBuilder(cpg.graph.schema)
  var typeTagged = 0
  var typeArgTagged = 0
  var typeParamTagged = 0

  def classifyTypeInstance(name: String, fullName: String): (Option[String], Option[String]) = {
    val lower = name.toLowerCase
    val fullLower = fullName.toLowerCase

    val category =
      if (primitiveTypes.contains(lower)) Some("primitive")
      else if (fullLower.contains("[]")) Some("array")
      else if (fullLower.contains("(*)") || fullLower.contains("(*") || fullLower.contains("function")) Some("function-pointer")
      else if (fullLower.contains("<") && fullLower.contains(">")) Some("generic-instance")
      else if (lower.contains("ptr") || fullLower.contains("*")) Some("pointer")
      else Some("custom")

    val genericKind =
      if (name.length == 1 && name.head.isUpper) Some("generic-parameter")
      else if (fullLower.contains("<") && fullLower.contains(">")) Some("generic-instance")
      else Some("concrete")

    (category, genericKind)
  }

  def annotateTypeNode(t: Type): Unit = {
    val name = Option(t.name).getOrElse("")
    val full = Option(t.fullName).getOrElse("")
    val (categoryOpt, genericKindOpt) = classifyTypeInstance(name, full)

    categoryOpt.foreach { category =>
      if (Tagging.addTag(t, TagCatalog.TypeInstanceCategory.name, category, diff)) {
        Tagging.addConfidence(t, "medium", diff)
        typeTagged += 1
      }
    }

    genericKindOpt.foreach { kind =>
      if (Tagging.addTag(t, TagCatalog.TypeGenericKind.name, kind, diff)) {
        Tagging.addConfidence(t, "medium", diff)
      }
    }

    val declInfoOpt = typeDeclInfo.get(Option(t.typeDeclFullName).getOrElse(""))

    declInfoOpt.flatMap(_.domain).foreach { domain =>
      if (Tagging.addTag(t, TagCatalog.TypeInstanceDomain.name, domain, diff)) {
        Tagging.addConfidence(t, "medium", diff)
      }
    }

    declInfoOpt.flatMap(_.concurrency).foreach { label =>
      if (Tagging.addTag(t, TagCatalog.TypeConcurrencyPrimitive.name, label, diff)) {
        Tagging.addConfidence(t, "medium", diff)
      }
    }

    declInfoOpt.flatMap(_.ownership).foreach { label =>
      if (Tagging.addTag(t, TagCatalog.TypeOwnershipModel.name, label, diff)) {
        Tagging.addConfidence(t, "low", diff)
      }
    }
  }

  def classifyTypeArgument(code: String, idx: Int): String = {
    val lower = code.toLowerCase
    if (lower.contains("key")) "key-type"
    else if (lower.contains("value")) "value-type"
    else if (lower.contains("element") || lower.contains("item")) "element-type"
    else if (lower.contains("compare") || lower.contains("less")) "comparator-type"
    else if (lower.contains("alloc")) "allocator-type"
    else if (lower.contains("ptr") || lower.contains("*")) "pointer-type"
    else if (idx == 0 && lower.contains("pair")) "key-type"
    else if (idx == 1 && lower.contains("pair")) "value-type"
    else "concrete"
  }

  def classifyTypeParameter(name: String): String = {
    val lower = name.toLowerCase
    if (lower.contains("key")) "key-parameter"
    else if (lower.contains("value")) "value-parameter"
    else if (lower.contains("elem") || lower.contains("item")) "element-parameter"
    else if (lower.contains("iter")) "iterator-parameter"
    else "generic-parameter"
  }

  cpg.typ.l.foreach(annotateTypeNode)

  cpg.typeArgument.l.foreach { arg =>
    val code = Option(arg.code).getOrElse("")
    val idx = arg.argumentIndex
    val kind = classifyTypeArgument(code, idx)
    if (Tagging.addTag(arg, TagCatalog.TypeArgumentKind.name, kind, diff)) {
      Tagging.addConfidence(arg, "low", diff)
      typeArgTagged += 1
    }

    // propagate domain from referenced type if available
    arg._refOut.collectAll[Type].foreach { refType =>
      val domainTag = refType._taggedByOut.collectAll[Tag].find(_.name == TagCatalog.TypeInstanceDomain.name).map(_.value)
      domainTag.foreach { domain =>
        if (Tagging.addTag(arg, TagCatalog.TypeInstanceDomain.name, domain, diff)) {
          Tagging.addConfidence(arg, "low", diff)
        }
      }
    }
  }

  cpg.typeParameter.l.foreach { param =>
    val name = Option(param.name).getOrElse("")
    val role = classifyTypeParameter(name)
    if (Tagging.addTag(param, TagCatalog.TypeParameterRole.name, role, diff)) {
      Tagging.addConfidence(param, "medium", diff)
      typeParamTagged += 1
    }
  }

  println("[*] Applying type usage enrichment diff...")
  DiffGraphApplier.applyDiff(cpg.graph, diff)

  println(f"[+] Type usage enrichment complete. TYPE nodes tagged: $typeTagged%,d, arguments: $typeArgTagged%,d, parameters: $typeParamTagged%,d")
}
