// api_usage_examples.sc - API usage pattern extraction
// Launch: :load api_usage_examples.sc
//
// Goal: identify API-style entry points (adds TAG nodes and captures summary metadata for frequently used APIs).
//
// ============================================================================
// Parameters
// ============================================================================
// Optional JVM flags to adjust behaviour:
//   -Dapi.minCallers=5           minimum number of callers required to treat a method as an API
//   -Dapi.testDir="src/test"     location of test sources
//   -Dapi.apply=true             write tags back to the graph
//
// Defaults: minCallers=5, testDir="src/test", apply=true
//
// ============================================================================
// Tags emitted
// ============================================================================
// The script enriches identified APIs with the following tags:
// - `api-caller-count`: number of callers (fan-in)
// - `api-example`: representative snippet from existing usages
// - `api-typical-usage`: short description of common entry points
// - `api-public`: marks externally visible APIs
//
// ============================================================================
// Usage examples
// ============================================================================
//
// 1. Show the busiest APIs:
//    cpg.method.tag.name("api-caller-count").value.toList.sorted.reverse.take(10)
//
// 2. Inspect an example snippet for a specific API:
//    cpg.method.name("palloc").tag.name("api-example").value.l.headOption
//
// 3. Find frequently used APIs that still lack comments:
//    cpg.method
//      .where(_.tag.nameExact("api-caller-count").value.toInt > 20)
//      .where(_._astOut.collectAll[Comment].isEmpty)
//      .name.l
//
// 4. List public APIs with captured examples:
//    cpg.method
//      .where(_.tag.nameExact("api-public").valueExact("true"))
//      .where(_.tag.nameExact("api-example").exists)
//      .name.l
//
// 5. Prioritise onboarding documentation — surface the “hot” entry points:
//    cpg.method
//      .where(_.tag.nameExact("api-caller-count").value.toInt > 50)
//      .sortBy(_.tag.name("api-caller-count").value.toInt).reverse
//      .map(m => (m.name, m.tag.name("api-caller-count").value.headOption))
//      .l.take(20)
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.codepropertygraph.generated.{EdgeTypes, NodeTypes}
import flatgraph.DiffGraphBuilder

// ========================= Config =========================
val MIN_CALLERS = sys.props.getOrElse("api.minCallers", "5").toInt
val TEST_DIR = sys.props.getOrElse("api.testDir", "src/test")
val APPLY_TAGS = sys.props.getOrElse("api.apply", "true").toBoolean

println(s"[*] Min callers for API: $MIN_CALLERS")
println(s"[*] Test directory: $TEST_DIR")
println(s"[*] Apply tags: $APPLY_TAGS")

// ========================= Analysis Functions =========================

// Determine whether a method should be treated as a public-facing API
def isPublicAPI(m: Method): Boolean = {
  // In PostgreSQL a public API is typically:
  // 1. Not marked static
  // 2. Not prefixed with an underscore
  // 3. Declared in a header file
  val name = m.name
  val isStatic = m.code.contains("static ")
  val isPrivate = name.startsWith("_")

  !isStatic && !isPrivate
}

// Count how many callers reach the method
def countCallers(m: Method): Int = {
  try {
    cpg.call.name(m.name).size
  } catch {
    case _: Throwable => 0
  }
}

// Collect representative usages from unit tests or other callers
def findTestExamples(methodName: String): List[String] = {
  try {
    // Heuristic 1: gather caller snippets (lightweight extraction)
    val examples = cpg.call
      .nameExact(methodName)
      .method  // Get the method containing this call
      .code
      .l
      .map(extractMinimalExample)
      .distinct
      .take(3)

    examples
  } catch {
    case _: Throwable => List.empty
  }
}

// Summarise a typical usage location
def findTypicalUsage(m: Method): Option[String] = {
  try {
    // Look for the most common caller (again a lightweight heuristic)
    val callers = cpg.call.name(m.name).method.name.l
    if (callers.nonEmpty) {
      val mostCommonCaller = callers.groupBy(identity).maxBy(_._2.size)._1
      Some(s"Often called from: $mostCommonCaller")
    } else None
  } catch {
    case _: Throwable => None
  }
}

// Build a condensed example string based on the extracted snippet
def extractMinimalExample(code: String): String = {
  // Simple normalisation: strip comments and newlines, keep the essentials
  val lines = code.split("\n").map(_.trim).filter(l =>
    l.nonEmpty && !l.startsWith("//") && !l.startsWith("/*")
  )
  val joined = lines.mkString(" ")
  joined.take(200) + (if (joined.length > 200) "..." else "")
}

// ========================= Graph modification =========================

def applyAPITags(): Unit = {
  val diff = DiffGraphBuilder(cpg.graph.schema)
  var tagged = 0
  var apiCount = 0

  println("[*] Analyzing API usage patterns...")

  // Iterate across all methods
  val methods = cpg.method.l

  println(s"[*] Found ${methods.size} methods")
  println("[*] Counting callers and extracting examples...")

  methods.foreach { method =>
    val callerCount = countCallers(method)

    // Only tag methods that have enough callers to be considered APIs
    if (callerCount >= MIN_CALLERS) {
      apiCount += 1

      // TAG: caller count
      val tagCallerCount = NewTag()
        .name("api-caller-count")
        .value(callerCount.toString)

      diff.addNode(tagCallerCount)
      diff.addEdge(method, tagCallerCount, EdgeTypes.TAGGED_BY)

      // TAG: public API marker
      if (isPublicAPI(method)) {
        val tagPublic = NewTag()
          .name("api-public")
          .value("true")

        diff.addNode(tagPublic)
        diff.addEdge(method, tagPublic, EdgeTypes.TAGGED_BY)
      }

      // TAG: example from tests/usages
      val testExamples = findTestExamples(method.name)
      if (testExamples.nonEmpty) {
        val exampleCode = extractMinimalExample(testExamples.head)
        val tagExample = NewTag()
          .name("api-example")
          .value(exampleCode)

        diff.addNode(tagExample)
        diff.addEdge(method, tagExample, EdgeTypes.TAGGED_BY)
      }

      // TAG: typical usage pattern
      findTypicalUsage(method).foreach { usage =>
        val tagUsage = NewTag()
          .name("api-typical-usage")
          .value(usage)

        diff.addNode(tagUsage)
        diff.addEdge(method, tagUsage, EdgeTypes.TAGGED_BY)
      }

      tagged += 1

      if (tagged % 100 == 0) {
        println(s"[*] Processed $tagged APIs...")
      }
    }
  }

  println(s"[*] Applying tags to graph...")
  flatgraph.DiffGraphApplier.applyDiff(cpg.graph, diff)

  println(s"[+] Tagged $tagged methods with API usage information")
  println(s"[+] Found $apiCount APIs (methods with >= $MIN_CALLERS callers)")

  // Metrics
  val publicAPIs = cpg.method.where(_.tag.nameExact("api-public").valueExact("true")).size
  val withExamples = cpg.method.filter(_.tag.nameExact("api-example").nonEmpty).size

  println(s"[+] Public APIs: $publicAPIs")
  println(s"[+] APIs with examples: $withExamples")
}

// ========================= Initialization =========================

if (APPLY_TAGS) {
  applyAPITags()
  println("[*] Query examples:")
  println("""    cpg.method.tag.name("api-caller-count").value.l.sortBy(_.toInt).reverse.take(10)""")
  println("""    cpg.method.where(_.tag.nameExact("api-public").valueExact("true")).name.l.take(10)""")
} else {
  println("[*] Tag application disabled. Set -Dapi.apply=true to enable")
}
