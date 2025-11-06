// enrich_data_flow.sc - high-level domain object flow tracking
// Launch: :load enrich_data_flow.sc
//
// Tags emitted:
//   - `param-flow` (on call nodes)
//   - `domain-concept` (on target methods)
//   - `tag-confidence`
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.semanticcpg.language._
import flatgraph.{DiffGraphApplier, DiffGraphBuilder}

import EnrichCommon._

val APPLY = sys.props.getOrElse("dataflow.apply", "true").toBoolean

println(s"[*] Apply domain data-flow enrichment: $APPLY")

if (!APPLY) {
  println("[*] Domain data-flow enrichment skipped (set -Ddataflow.apply=true to run).")
} else {

  val diff = DiffGraphBuilder(cpg.graph.schema)
  var callFlows = 0L
  var calleeDomains = 0L

  def domainForParam(param: MethodParameterIn): Seq[String] =
    param._taggedByOut.collectAll[Tag].filter(_.name == TagCatalog.ParamDomainConcept.name).map(_.value).toSeq

  cpg.method.l.foreach { method =>
    val domainParams = method.parameter.l.collect {
      case p: MethodParameterIn =>
        val domains = domainForParam(p)
        if (domains.nonEmpty) Some(p -> domains) else None
    }.flatten

    if (domainParams.nonEmpty) {
      method.call.l.foreach { call =>
        val calleeOpt = call.callee.headOption
        val callArgs = call.argument.l
        domainParams.foreach { case (param, domains) =>
          val reachesCall = callArgs.exists(arg => arg.reachingDefIn.collectAll[MethodParameterIn].exists(_.id == param.id))
          if (reachesCall) {
            domains.foreach { domain =>
              if (Tagging.addTag(call, TagCatalog.ParamFlow.name, s"${param.name}->$domain", diff)) {
                Tagging.addConfidence(call, "low", diff)
                callFlows += 1
              }
              calleeOpt.foreach { callee =>
                if (Tagging.addTag(callee, "domain-concept", domain, diff)) {
                  Tagging.addConfidence(callee, "low", diff)
                  calleeDomains += 1
                }
              }
            }
          }
        }
      }
    }
  }

  println("[*] Applying domain data-flow enrichment diff...")
  DiffGraphApplier.applyDiff(cpg.graph, diff)
  println(f"[+] Call-site flows tagged: $callFlows%,d")
  println(f"[+] Callee domain tags inferred: $calleeDomains%,d")
}
