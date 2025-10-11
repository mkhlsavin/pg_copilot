// test_coverage.sc — test coverage mapping
// Launch: :load test_coverage.sc
//
// Tags emitted: `test-coverage`, `test-count`, `tested-by`, `coverage-percentage`
// Example: cpg.method.where(_.tag.nameExact("test-coverage").valueExact("untested")).name.l

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.codepropertygraph.generated.EdgeTypes
import flatgraph.DiffGraphBuilder

val APPLY = sys.props.getOrElse("test.apply", "true").toBoolean
val TEST_PATTERNS = List("test_", "Test", "_test", "regress", "check_")

def isTestMethod(m: Method): Boolean = {
  val name = m.name
  val filename = m.filename
  TEST_PATTERNS.exists(p => name.contains(p) || filename.contains("/test/"))
}

def findTestsFor(method: Method): List[Method] = {
  try {
    cpg.call.name(method.name).method.filter(isTestMethod).l
  } catch {
    case _: Throwable => List.empty
  }
}

def applyTestCoverageTags(): Unit = {
  val diff = DiffGraphBuilder(cpg.graph.schema)
  var tagged = 0

  println("[*] Analyzing test coverage...")

  cpg.method.filterNot(isTestMethod(_)).l.foreach { method =>
    val tests = findTestsFor(method)
    val testCount = tests.size
    val coverage = if (testCount > 0) "covered" else "untested"

    val tagCoverage = NewTag().name("test-coverage").value(coverage)
    val tagCount = NewTag().name("test-count").value(testCount.toString)

    diff.addNode(tagCoverage)
    diff.addNode(tagCount)
    diff.addEdge(method, tagCoverage, EdgeTypes.TAGGED_BY)
    diff.addEdge(method, tagCount, EdgeTypes.TAGGED_BY)

    if (tests.nonEmpty) {
      val testNames = tests.map(_.name).mkString(", ")
      val tagTestedBy = NewTag().name("tested-by").value(testNames.take(200))
      diff.addNode(tagTestedBy)
      diff.addEdge(method, tagTestedBy, EdgeTypes.TAGGED_BY)
    }

    tagged += 1
    if (tagged % 1000 == 0) println(s"[*] Processed $tagged methods...")
  }

  flatgraph.DiffGraphApplier.applyDiff(cpg.graph, diff)
  println(s"[+] Tagged $tagged methods")

  val untested = cpg.method.where(_.tag.nameExact("test-coverage").valueExact("untested")).size
  val total = cpg.method.filterNot(isTestMethod(_)).size
  val coveragePct = ((total - untested).toDouble / total * 100).toInt

  println(f"[*] Coverage: $coveragePct%%  ($untested untested of $total)")
}

if (APPLY) applyTestCoverageTags()
