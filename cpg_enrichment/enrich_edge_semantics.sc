// enrich_edge_semantics.sc - annotate inter-node edges with semantic metadata
// Launch: :load enrich_edge_semantics.sc
//
// Tags emitted:
//   - `argument-param-name`
//   - `param-role` (propagated to argument nodes)
//   - `call-action`
//   - `call-side-effect`
//   - `call-receiver-role`
//   - `branch-kind`
//   - `data-flow-kind`
//   - `control-reason`
//   - `type-instance-category` (propagated to expressions)
//   - `param-flow`
//   - `tag-confidence`
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.semanticcpg.language._
import flatgraph.{DiffGraphApplier, DiffGraphBuilder}
import java.util.Locale

import scala.collection.mutable

import EnrichCommon._
import io.shiftleft.codepropertygraph.generated.PropertyNames

val APPLY = sys.props.getOrElse("edges.apply", "true").toBoolean

println(s"[*] Apply edge semantics enrichment: $APPLY")

if (!APPLY) {
  println("[*] Edge semantics enrichment skipped (set -Dedges.apply=true to run).")
} else {

  val diff = DiffGraphBuilder(cpg.graph.schema)
  var argumentNameTagged = 0L
  var argumentRoleTagged = 0L
  var callActionTagged = 0L
  var receiverTagged = 0L
  var branchTagged = 0L
  var dataFlowTagged = 0L
  var controlReasonTagged = 0L
  var typeCategoryTagged = 0L
  var paramFlowTagged = 0L

  def lower(value: String): String = Option(value).getOrElse("").toLowerCase(Locale.ROOT)

  def nonEmptyOption(value: String): Option[String] =
    Option(value).map(_.trim).filter(_.nonEmpty)

  def isComment(node: AstNode): Boolean = node.label == "COMMENT"

  def addTag(node: StoredNode, name: String, value: String, confidence: String): Unit = {
    if (value.nonEmpty && Tagging.addTag(node, name, value, diff)) {
      Tagging.addConfidence(node, confidence, diff)
    }
  }

  // ---------------------------------------------------------------------------
  //  Argument edge metadata
  // ---------------------------------------------------------------------------

  val methodCache = mutable.Map[String, Method]()

  def parametersFor(call: Call): Map[Int, MethodParameterIn] = {
    val direct = call.callee.headOption
    val resolved = direct.orElse {
      nonEmptyOption(call.methodFullName).flatMap { fullName =>
        methodCache.get(fullName).orElse {
          cpg.method.fullNameExact(fullName).headOption.map { method =>
            methodCache.put(fullName, method)
            method
          }
        }
      }
    }
    resolved
      .map(_.parameter.l.collect { case p: MethodParameterIn => p.order -> p })
      .map(_.toMap)
      .getOrElse(Map.empty[Int, MethodParameterIn])
  }

  def propagateArgumentMetadata(): Unit = {
    cpg.call.l.foreach { call =>
      val params = parametersFor(call)
      call.argument.l.foreach { arg =>
        val index = arg.order
        params.get(index).foreach { param =>
          val roles = param.tag.nameExact(TagCatalog.ParamRole.name).value.l
          val domainConcepts = param.tag.nameExact(TagCatalog.ParamDomainConcept.name).value.l
          if (roles.nonEmpty || domainConcepts.nonEmpty) {
            nonEmptyOption(param.name).foreach { name =>
              addTag(arg, TagCatalog.ArgumentParamName.name, name, "high")
              argumentNameTagged += 1
            }
            roles.foreach { role =>
              addTag(arg, TagCatalog.ParamRole.name, role, "medium")
              argumentRoleTagged += 1
            }
            domainConcepts.foreach { domain =>
              addTag(arg, TagCatalog.ParamDomainConcept.name, domain, "medium")
              argumentRoleTagged += 1
            }
          }
        }
      }
    }
  }

  // ---------------------------------------------------------------------------
  //  Call semantics (action + side effects + receivers)
  // ---------------------------------------------------------------------------

  val receiverHints: Seq[(String, String)] = Seq(
    "buffer" -> "buffer",
    "buf" -> "buffer",
    "page" -> "buffer",
    "rel" -> "relation",
    "relation" -> "relation",
    "snapshot" -> "snapshot",
    "snap" -> "snapshot",
    "lock" -> "lock",
    "ctx" -> "context",
    "context" -> "context",
    "tuple" -> "tuple",
    "index" -> "index",
    "xact" -> "transaction",
    "txn" -> "transaction"
  )

  def inferAction(nameLower: String, codeLower: String): Option[String] = {
    if (nameLower.contains("alloc") || nameLower.contains("create") || nameLower.contains("make")) Some("allocate-memory")
    else if (nameLower.contains("free") || nameLower.contains("release") || nameLower.contains("destroy")) Some("free-memory")
    else if (nameLower.contains("lock") && !nameLower.contains("unlock")) Some("lock-resource")
    else if (nameLower.contains("unlock") || nameLower.contains("unpin")) Some("unlock-resource")
    else if (nameLower.contains("init") || nameLower.contains("reset")) Some("initialize")
    else if (nameLower.contains("check") || nameLower.startsWith("is") || nameLower.contains("validate")) Some("check-condition")
    else if (nameLower.contains("get") || nameLower.contains("fetch") || nameLower.contains("lookup")) Some("fetch-data")
    else if (nameLower.contains("set") || nameLower.contains("write") || nameLower.contains("update") || nameLower.contains("store")) Some("write-data")
    else if (nameLower.contains("elog") || nameLower.contains("ereport") || codeLower.contains("elog")) Some("log")
    else if (nameLower.contains("notify") || nameLower.contains("signal")) Some("notify")
    else None
  }

  def inferSideEffect(action: Option[String], nameLower: String): String = {
    action match {
      case Some("check-condition") | Some("fetch-data") => "none"
      case Some("log") | Some("notify")                 => "local"
      case Some(value) if value.nonEmpty               => "global"
      case _ =>
        if (nameLower.contains("read") || nameLower.contains("peek")) "none"
        else if (nameLower.contains("log") || nameLower.contains("trace")) "local"
        else "global"
    }
  }

  def receiverRole(code: String): Option[String] = {
    val prefix = code.takeWhile(_ != '(')
    val segments =
      if (prefix.contains("->")) prefix.split("->").map(_.trim).toSeq
      else if (prefix.contains(".")) prefix.split("\\.").map(_.trim).toSeq
      else Seq.empty[String]
    segments.lastOption.flatMap { candidate =>
      val lowerCandidate = lower(candidate)
      receiverHints.collectFirst { case (hint, label) if lowerCandidate.contains(hint) => label }
    }
  }

  def annotateCalls(): Unit = {
    cpg.call.l.foreach { call =>
      val nameLower = lower(call.name)
      val codeLower = lower(call.code)
      val actionOpt = inferAction(nameLower, codeLower)
      actionOpt.foreach { value =>
        addTag(call, TagCatalog.CallAction.name, value, "medium")
        callActionTagged += 1
        val sideEffect = inferSideEffect(actionOpt, nameLower)
        addTag(call, TagCatalog.CallSideEffect.name, sideEffect, "medium")
      }
      receiverRole(call.code).foreach { value =>
        addTag(call, TagCatalog.CallReceiverRole.name, value, "low")
        receiverTagged += 1
      }
    }
  }

  // ---------------------------------------------------------------------------
  //  Branch tagging (CFG approximation)
  // ---------------------------------------------------------------------------

  def annotateBranchNodes(): Unit = {
    cpg.controlStructure.l.foreach { cs =>
      val csType = lower(cs.controlStructureType)
      val children = cs.astChildren.l.filterNot(isComment)
      def firstMeaningful(nodes: Seq[AstNode]): Option[AstNode] =
        nodes.collectFirst { case n if n.label != "BLOCK" => n }
          .orElse {
            nodes.collectFirst { case block: Block =>
              block.astChildren.l.filterNot(isComment).headOption.getOrElse(block)
            }
          }

      csType match {
        case "if" =>
          val condition = children.find(_.order == 1)
          val bodyNodes = children.filter(_.order > 1)
          val thenBody = bodyNodes.headOption
          thenBody.foreach { body =>
            val target = body match {
              case block: Block => block.astChildren.l.filterNot(isComment).headOption.getOrElse(block)
              case other        => other
            }
            addTag(target, TagCatalog.BranchKind.name, "true-path", "medium")
            branchTagged += 1
          }
          val elseBranch = bodyNodes.collectFirst { case ctrl: ControlStructure if lower(ctrl.controlStructureType) == "else" => ctrl }
          elseBranch.foreach { elseCtrl =>
            val elseTarget = elseCtrl.astChildren.l.filterNot(isComment).headOption
              .getOrElse(elseCtrl)
            addTag(elseTarget, TagCatalog.BranchKind.name, "false-path", "medium")
            branchTagged += 1
          }
        case "else" =>
          val target = firstMeaningful(children)
          target.foreach { node =>
            addTag(node, TagCatalog.BranchKind.name, "false-path", "medium")
            branchTagged += 1
          }
        case "for" | "while" | "dowhile" | "do" =>
          val body = children.filter(_.order >= 2).headOption
          body.foreach { node =>
            val target = node match {
              case block: Block => block.astChildren.l.filterNot(isComment).headOption.getOrElse(block)
              case other        => other
            }
            addTag(target, TagCatalog.BranchKind.name, "loop-body", "medium")
            branchTagged += 1
          }
        case _ => // ignore for now
      }
    }
  }

  // ---------------------------------------------------------------------------
  //  Data dependency enrichment (REACHING_DEF, etc.)
  // ---------------------------------------------------------------------------

  def annotateDataFlow(): Unit = {
    cpg.identifier.l.foreach { id =>
      val kinds =
        id.reachingDefIn.l.flatMap { source =>
          source match {
            case tagged: StoredNode =>
              val explicitKinds = tagged._taggedByOut.collectAll[Tag]
                .filter(_.name == TagCatalog.DataKind.name)
                .map(_.value)
              if (explicitKinds.nonEmpty) explicitKinds
              else {
                val sourceCode = lower(tagged.code)
                receiverHints.collectFirst { case (hint, label) if sourceCode.contains(hint) => label }
                  .map(Seq(_)).getOrElse(Seq("generic"))
              }
            case _ => Seq.empty[String]
          }
        }.distinct
      kinds.foreach { kind =>
        addTag(id, TagCatalog.DataFlowKind.name, kind, "low")
        dataFlowTagged += 1
      }
    }
  }

  // ---------------------------------------------------------------------------
  //  Control dependency enrichment (approximate)
  // ---------------------------------------------------------------------------

  val controlKeywords: Seq[(String, String)] = Seq(
    "null" -> "null-check",
    "bounds" -> "bounds-check",
    "<" -> "bounds-check",
    ">" -> "bounds-check",
    "error" -> "error-check",
    "fail" -> "error-check",
    "elog" -> "error-check",
    "ereport" -> "error-check",
    "lock" -> "lock-check",
    "visible" -> "visibility-check",
    "snapshot" -> "snapshot-check",
    "context" -> "resource-check"
  )

  def inferControlReason(code: String): Option[String] = {
    val lowered = lower(code)
    controlKeywords.collectFirst {
      case (hint, label) if lowered.contains(hint) => label
    }
  }

  def annotateControlReasons(): Unit = {
    cpg.controlStructure.l.foreach { cs =>
      val conditionOpt = cs.astChildren.l.find(_.order == 1).flatMap(node => nonEmptyOption(node.code))
      val reasonOpt = conditionOpt.flatMap(inferControlReason)
      reasonOpt.foreach { reason =>
        cs.astChildren.l.filter(_.order > 1).foreach {
          case block: Block =>
            block.astChildren.l.filterNot(isComment).foreach { child =>
              addTag(child, TagCatalog.ControlReason.name, reason, "low")
              controlReasonTagged += 1
            }
          case other if !isComment(other) =>
            addTag(other, TagCatalog.ControlReason.name, reason, "low")
            controlReasonTagged += 1
          case _ => ()
        }
      }
    }
  }

  // ---------------------------------------------------------------------------
  //  Other edges (EVAL_TYPE & PARAMETER_LINK approximations)
  // ---------------------------------------------------------------------------

  def classifyTypeCategory(typeFullName: String): Option[String] = {
    val lowerType = lower(typeFullName)
    if (typeFullName == null || typeFullName.isBlank) None
    else if (lowerType.contains("void") || lowerType.contains("int") || lowerType.contains("char") || lowerType.contains("bool") || lowerType.contains("float") || lowerType.contains("double") || lowerType.matches(".*u?int\\d+.*"))
      Some("primitive")
    else if (lowerType.contains("*") || lowerType.contains("ptr"))
      Some("pointer")
    else if (lowerType.contains("list") || lowerType.contains("array") || lowerType.contains("vector") || lowerType.contains("set") || lowerType.contains("map"))
      Some("container")
    else Some("custom")
  }

  def annotateTypeCategory(): Unit = {
    cpg.call.argument.l.foreach { arg =>
      val typeName = arg._evalTypeOut.collectAll[Type].headOption
        .flatMap(node => nonEmptyOption(node.fullName))
        .getOrElse("")
      classifyTypeCategory(typeName).foreach { category =>
        addTag(arg, TagCatalog.TypeInstanceCategory.name, category, "low")
        typeCategoryTagged += 1
      }
    }
  }

  def annotateParamFlows(): Unit = {
    cpg.method.l.foreach { method =>
      val paramRoles = method.parameter.l.collect {
        case p: MethodParameterIn =>
          p._taggedByOut.collectAll[Tag].filter(_.name == TagCatalog.ParamRole.name).map(_.value)
      }.flatten.distinct

      val returnRoles = method.methodReturn._taggedByOut.collectAll[Tag]
        .filter(t => t.name == TagCatalog.ReturnOutcome.name || t.name == TagCatalog.ReturnsError.name || t.name == TagCatalog.ReturnsNull.name)
        .map(t => s"return-${lower(t.value)}")
        .distinct

      val flows =
        (paramRoles.map(role => s"param-$role") ++ returnRoles).distinct

      flows.foreach { flow =>
        addTag(method, TagCatalog.ParamFlow.name, flow, "low")
        paramFlowTagged += 1
      }
    }
  }

  // ---------------------------------------------------------------------------
  //  Execute enrichment
  // ---------------------------------------------------------------------------

  propagateArgumentMetadata()
  annotateCalls()
  annotateBranchNodes()
  annotateDataFlow()
  annotateControlReasons()
  annotateTypeCategory()
  annotateParamFlows()

  println("[*] Applying edge semantics enrichment diff...")
  DiffGraphApplier.applyDiff(cpg.graph, diff)

  println(f"[+] Argument names tagged: $argumentNameTagged%,d")
  println(f"[+] Argument roles propagated: $argumentRoleTagged%,d")
  println(f"[+] Call actions tagged: $callActionTagged%,d")
  println(f"[+] Receivers tagged: $receiverTagged%,d")
  println(f"[+] Branch nodes tagged: $branchTagged%,d")
  println(f"[+] Data-flow annotations: $dataFlowTagged%,d")
  println(f"[+] Control reasons annotated: $controlReasonTagged%,d")
  println(f"[+] Type categories propagated: $typeCategoryTagged%,d")
  println(f"[+] Parameter flow summaries: $paramFlowTagged%,d")
}
