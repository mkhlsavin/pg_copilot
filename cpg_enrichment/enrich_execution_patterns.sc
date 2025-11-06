// enrich_execution_patterns.sc - recognise common execution patterns
// Launch: :load enrich_execution_patterns.sc
//
// Tags emitted:
//   - `domain-concept` (on methods)
//   - `param-flow` (pattern summaries)
//   - `tag-confidence`
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.semanticcpg.language._
import flatgraph.{DiffGraphApplier, DiffGraphBuilder}

import EnrichCommon._
import java.util.Locale

val APPLY = sys.props.getOrElse("executionpatterns.apply", "true").toBoolean

println(s"[*] Apply execution pattern enrichment: $APPLY")

if (!APPLY) {
  println("[*] Execution pattern enrichment skipped (set -Dexecutionpatterns.apply=true to run).")
} else {

  val diff = DiffGraphBuilder(cpg.graph.schema)
  var concurrencyTagged = 0L
  var memoryTagged = 0L
  var errorTagged = 0L

  def addMethodTag(method: Method, name: String, value: String, confidence: String = "medium"): Unit = {
    if (Tagging.addTag(method, name, value, diff)) {
      Tagging.addConfidence(method, confidence, diff)
      value match {
        case "concurrency" => concurrencyTagged += 1
        case "memory"      => memoryTagged += 1
        case "error-path"  => errorTagged += 1
        case _             => ()
      }
    }
  }

  cpg.method.l.foreach { method =>
    val callNames = method.call.name.l.map(_.toLowerCase(Locale.ROOT))
    val callCodes = method.call.code.l.map(_.toLowerCase(Locale.ROOT))

    val hasLock = callNames.exists(name => name.contains("lock") || name.contains("lwlockacquire") || name.contains("spinlock"))
    val hasUnlock = callNames.exists(name => name.contains("unlock") || name.contains("release") || name.contains("unpin"))
    if (hasLock && hasUnlock) {
      addMethodTag(method, "domain-concept", "concurrency", "medium")
    }

    val alloc = callNames.exists(name => name.contains("palloc") || name.contains("alloc") || name.contains("new") || name.contains("create"))
    val free = callNames.exists(name => name.contains("pfree") || name.contains("free") || name.contains("delete") || name.contains("destroy"))
    if (alloc && free) {
      addMethodTag(method, "domain-concept", "memory", "low")
      addMethodTag(method, TagCatalog.ParamFlow.name, "manages-memory", "low")
    }

    val errorPaths = callCodes.exists(code => code.contains("elog(") || code.contains("ereport(") || code.contains("error"))
    if (errorPaths) {
      addMethodTag(method, TagCatalog.ParamFlow.name, "error-path", "low")
      addMethodTag(method, "domain-concept", "error-handling", "low")
    }
  }

  println("[*] Applying execution pattern enrichment diff...")
  DiffGraphApplier.applyDiff(cpg.graph, diff)
  println(f"[+] Concurrency-aware methods tagged: $concurrencyTagged%,d")
  println(f"[+] Memory-management methods tagged: $memoryTagged%,d")
  println(f"[+] Error-handling paths tagged: $errorTagged%,d")
}
