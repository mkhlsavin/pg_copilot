// extension_points.sc - Extension points and hooks detection
// Launch: :load extension_points.sc
//
// Adds: `extension-point`, `extensibility`, `extension-examples`
// Example query: cpg.method.where(_.tag.nameExact("extension-point").valueExact("hook")).name.l

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.codepropertygraph.generated.EdgeTypes
import flatgraph.DiffGraphBuilder

import EnrichCommon._

val APPLY = sys.props.getOrElse("ext.apply", "true").toBoolean

// Extension point detection patterns - more comprehensive
val HOOK_SUFFIX_PATTERNS = List("_hook", "_callback", "Handler", "Routine", "_func", "_fn")
val HOOK_PREFIX_PATTERNS = List("call_", "invoke_", "execute_", "trigger_")
val PLUGIN_API_PATTERNS = List("FDW", "PG_", "Register", "Extension", "fmgr_", "planner_hook")
val CALLBACK_KEYWORDS = List("typedef", "(*)", "funct", "callback")

def isExtensionPoint(m: Method): Option[String] = {
  val name = m.name
  val nameLower = name.toLowerCase
  val codeLower = Option(m.code).map(_.toLowerCase).getOrElse("")
  val signatureLower = Option(m.signature).map(_.toLowerCase).getOrElse("")
  val parameterNames =
    try m.parameter.name.l.map(_.toLowerCase)
    catch {
      case _: Throwable => Nil
    }

  // Check for hook suffix patterns
  if (HOOK_SUFFIX_PATTERNS.exists(p => nameLower.endsWith(p.toLowerCase))) {
    Some("hook")
  }
  // Check for hook prefix patterns
  else if (HOOK_PREFIX_PATTERNS.exists(p => nameLower.startsWith(p.toLowerCase))) {
    Some("hook")
  }
  // Check for plugin API patterns (anywhere in name)
  else if (PLUGIN_API_PATTERNS.exists(p => name.contains(p) || nameLower.contains(p.toLowerCase))) {
    Some("plugin-api")
  }
  // Check for function pointer typedefs/signatures
  else if (
    signatureLower.contains("(*)") ||
    signatureLower.contains("callback") ||
    CALLBACK_KEYWORDS.exists(k => codeLower.contains(k.toLowerCase))
  ) {
    Some("callback")
  }
  else if (parameterNames.exists(p => p.contains("callback") || p.contains("funcptr") || p.contains("handler"))) {
    Some("callback")
  }
  else if (parameterNames.exists(_.contains("hook"))) {
    Some("hook")
  }
  // Check for common PostgreSQL hook/callback names
  else if (nameLower.contains("planner") || nameLower.contains("executor") ||
           nameLower.contains("optimizer") || nameLower.contains("hook")) {
    Some("hook")
  }
  else if (codeLower.contains("hook->") || codeLower.contains("set_hook") || codeLower.contains("register_hook")) {
    Some("hook")
  }
  else {
    None
  }
}

def determineExtensibility(m: Method): String = {
  val codeLower = Option(m.code).map(_.toLowerCase).getOrElse("")
  val fileLower = Option(m.filename).map(_.toLowerCase).getOrElse("")
  val isStatic = codeLower.contains("static ")
  val isPrivate = m.name.startsWith("_")

  if (fileLower.endsWith(".h")) "public-api"
  else if (isStatic || isPrivate) "internal-hook"
  else "sealed"
}

def findExtensionExamples(methodName: String): Option[String] = {
  try {
    // Search examples under contrib/
    val examples = cpg.call.name(methodName)
      .where(_.file.name(".*contrib.*"))
      .code.l.take(2)

    if (examples.nonEmpty) Some(examples.mkString("; ").take(150))
    else None
  } catch {
    case _: Throwable => None
  }
}

def applyExtensionTags(): Unit = {
  val diff = DiffGraphBuilder(cpg.graph.schema)
  var tagged = 0

  println("[*] Detecting extension points...")

  cpg.method.l.foreach { method =>
    isExtensionPoint(method).foreach { extType =>
      val extensibility = determineExtensibility(method)

      if (Tagging.addTag(method, "extension-point", extType, diff)) {
        Tagging.addConfidence(method, "medium", diff)
      }
      if (Tagging.addTag(method, "extension-type", extType, diff)) {
        Tagging.addConfidence(method, "medium", diff)
      }
      if (Tagging.addTag(method, "extensibility", extensibility, diff)) {
        Tagging.addConfidence(method, "medium", diff)
      }

      // Attach sample usages when available
      findExtensionExamples(method.name).foreach { example =>
        if (Tagging.addTag(method, "extension-examples", example, diff)) {
          Tagging.addConfidence(method, "low", diff)
        }
      }

      tagged += 1
    }
  }

  flatgraph.DiffGraphApplier.applyDiff(cpg.graph, diff)
  println(s"[+] Tagged $tagged extension points")

  val hooks = cpg.method.where(_.tag.nameExact("extension-point").valueExact("hook")).size
  val pluginAPIs = cpg.method.where(_.tag.nameExact("extension-point").valueExact("plugin-api")).size

  println(f"[*] Hooks: $hooks")
  println(f"[*] Plugin APIs: $pluginAPIs")
}

if (APPLY) applyExtensionTags()
