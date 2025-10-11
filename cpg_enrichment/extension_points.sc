// extension_points.sc — Extension points and hooks detection
// Запуск: :load extension_points.sc
//
// Теги: `extension-point`, `extensibility`, `extension-examples`
// ПРИМЕРЫ: cpg.method.where(_.tag.nameExact("extension-point").valueExact("hook")).name.l

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.codepropertygraph.generated.EdgeTypes
import flatgraph.DiffGraphBuilder

val APPLY = sys.props.getOrElse("ext.apply", "true").toBoolean

val HOOK_PATTERNS = List("_hook$", "_callback$", "Handler$", "Routine$")
val PLUGIN_API_PATTERNS = List("^FDW", "^PG_", "Register", "^Extension")

def isExtensionPoint(m: Method): Option[String] = {
  val name = m.name

  if (HOOK_PATTERNS.exists(p => name.matches(s".*$p.*"))) {
    Some("hook")
  } else if (PLUGIN_API_PATTERNS.exists(p => name.matches(s"$p.*"))) {
    Some("plugin-api")
  } else if (m.code.contains("typedef") && m.code.contains("(*")) {
    Some("callback")
  } else {
    None
  }
}

def determineExtensibility(m: Method): String = {
  val code = m.code
  val isStatic = code.contains("static ")
  val isPrivate = m.name.startsWith("_")

  if (isStatic || isPrivate) "internal-hook"
  else if (m.filename.contains(".h")) "public-api"
  else "sealed"
}

def findExtensionExamples(methodName: String): Option[String] = {
  try {
    // Ищем примеры в contrib/
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

      val tagExt = NewTag().name("extension-point").value(extType)
      val tagExtensibility = NewTag().name("extensibility").value(extensibility)

      diff.addNode(tagExt)
      diff.addNode(tagExtensibility)
      diff.addEdge(method, tagExt, EdgeTypes.TAGGED_BY)
      diff.addEdge(method, tagExtensibility, EdgeTypes.TAGGED_BY)

      // Найти примеры использования
      findExtensionExamples(method.name).foreach { example =>
        val tagExample = NewTag().name("extension-examples").value(example)
        diff.addNode(tagExample)
        diff.addEdge(method, tagExample, EdgeTypes.TAGGED_BY)
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
