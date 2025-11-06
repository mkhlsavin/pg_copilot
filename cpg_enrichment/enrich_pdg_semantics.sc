// enrich_pdg_semantics.sc - PDG-driven semantic propagation
// Launch: :load enrich_pdg_semantics.sc
//
// Tags emitted:
//   - `param-flow`
//   - `tag-confidence`
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.semanticcpg.language._
import flatgraph.{DiffGraphApplier, DiffGraphBuilder}

import EnrichCommon._

val APPLY = sys.props.getOrElse("pdgsemantics.apply", "true").toBoolean

println(s"[*] Apply PDG semantic enrichment: $APPLY")

if (!APPLY) {
  println("[*] PDG semantic enrichment skipped (set -Dpdgsemantics.apply=true to run).")
} else {

  val diff = DiffGraphBuilder(cpg.graph.schema)
  var flowTags = 0L
  var methodSummaries = 0L

  def addFlowTag(node: StoredNode, value: String, confidence: String = "medium"): Unit = {
    if (Tagging.addTag(node, TagCatalog.ParamFlow.name, value, diff)) {
      Tagging.addConfidence(node, confidence, diff)
      flowTags += 1
    }
  }

  cpg.method.l.foreach { method =>
    val params = method.parameter.l.collect { case in: MethodParameterIn => in }
    val returnNode = method.methodReturn

    val methodFlows = scala.collection.mutable.Set.empty[String]

    params.foreach { param =>
      val paramName = Option(param.name).getOrElse(s"param${param.order}")
      val paramId = param.id

      val reachesReturn = returnNode.reachingDefIn.collectAll[MethodParameterIn].exists(_.id == paramId)
      if (reachesReturn) {
        addFlowTag(returnNode, s"$paramName->return")
        methodFlows += s"$paramName->return"
      }

      method.call.l.foreach { call =>
        call.argument.l.foreach { arg =>
          val reachesArg = arg.reachingDefIn.collectAll[MethodParameterIn].exists(_.id == paramId)
          if (reachesArg) {
            val targetName = Option(call.name).getOrElse("call")
            addFlowTag(arg, s"$paramName->$targetName", "low")
            methodFlows += s"$paramName->$targetName"
          }
        }
      }
    }

    if (methodFlows.nonEmpty) {
      methodFlows.foreach { summary =>
        if (Tagging.addTag(method, TagCatalog.ParamFlow.name, summary, diff)) {
          Tagging.addConfidence(method, "low", diff)
        }
      }
      methodSummaries += 1
    }
  }

  println("[*] Applying PDG semantic enrichment diff...")
  DiffGraphApplier.applyDiff(cpg.graph, diff)
  println(f"[+] Parameter flow tags created: $flowTags%,d")
  println(f"[+] Methods summarised via PDG: $methodSummaries%,d")
}
