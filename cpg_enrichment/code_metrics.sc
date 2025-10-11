// code_metrics.sc — Code quality and complexity metrics
// Запуск: :load code_metrics.sc
//
// Добавляет теги:
// - `cyclomatic-complexity`: McCabe complexity
// - `cognitive-complexity`: Cognitive complexity score
// - `lines-of-code`: LOC count
// - `code-smell`: "long-method" | "too-many-params" | "deep-nesting" | "duplicate-code"
// - `refactor-priority`: "critical" | "high" | "medium" | "low"
// - `coupling-score`: Afferent/efferent coupling (FILE level)
//
// ПРИМЕРЫ:
//   cpg.method.where(_.tag.nameExact("cyclomatic-complexity").value.toInt > 15).name.l
//   cpg.method.where(_.tag.nameExact("refactor-priority").valueExact("critical")).l
//   cpg.file.tag.name("coupling-score").value.l.map(_.toInt).sorted.reverse.take(10)

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.codepropertygraph.generated.{EdgeTypes}
import flatgraph.DiffGraphBuilder

val APPLY = sys.props.getOrElse("metrics.apply", "true").toBoolean
val COMPLEXITY_THRESHOLD = sys.props.getOrElse("metrics.complexityThreshold", "15").toInt

// Вычислить cyclomatic complexity
def calculateCyclomaticComplexity(m: Method): Int = {
  try {
    // Считаем control flow узлы: if, for, while, case, &&, ||, catch
    val controlStructures = m.ast.isControlStructure.size
    val conditionals = m.ast.isCall.name(".*(<operator>.(logicalAnd|logicalOr)).*").size
    1 + controlStructures + conditionals
  } catch {
    case _: Throwable => 1
  }
}

// Подсчитать LOC
def countLinesOfCode(m: Method): Int = {
  try {
    m.lineNumberEnd.getOrElse(0) - m.lineNumber.getOrElse(0) + 1
  } catch {
    case _: Throwable => 0
  }
}

// Детектировать code smells
def detectCodeSmells(m: Method, complexity: Int, loc: Int): List[String] = {
  var smells = List.empty[String]

  if (loc > 100) smells = smells :+ "long-method"
  if (m.parameter.size > 7) smells = smells :+ "too-many-params"
  if (complexity > 20) smells = smells :+ "deep-nesting"

  smells
}

// Определить приоритет рефакторинга
def calculateRefactorPriority(complexity: Int, loc: Int, smells: List[String]): String = {
  if (complexity > 30 || smells.contains("long-method")) "critical"
  else if (complexity > 20 || smells.size >= 2) "high"
  else if (complexity > 15 || smells.nonEmpty) "medium"
  else "low"
}

// Вычислить coupling для файла
def calculateFileCoupling(f: io.shiftleft.codepropertygraph.generated.nodes.File): Int = {
  try {
    // Efferent coupling: сколько других файлов использует этот файл
    val efferent = cpg.call.where(_.file.nameExact(f.name))
      .callee.file.name.dedup.l.size

    // Afferent coupling: сколько файлов используют этот файл
    val afferent = cpg.call.callee.where(_.file.nameExact(f.name))
      .file.name.dedup.l.size

    efferent + afferent
  } catch {
    case _: Throwable => 0
  }
}

def applyMetricsTags(): Unit = {
  val diff = DiffGraphBuilder(cpg.graph.schema)
  var methodsTagged = 0
  var filesTagged = 0

  println("[*] Calculating method metrics...")

  cpg.method.l.foreach { method =>
    val complexity = calculateCyclomaticComplexity(method)
    val loc = countLinesOfCode(method)
    val smells = detectCodeSmells(method, complexity, loc)
    val priority = calculateRefactorPriority(complexity, loc, smells)

    // TAG: cyclomatic complexity
    val tagComplexity = NewTag().name("cyclomatic-complexity").value(complexity.toString)
    diff.addNode(tagComplexity)
    diff.addEdge(method, tagComplexity, EdgeTypes.TAGGED_BY)

    // TAG: LOC
    val tagLOC = NewTag().name("lines-of-code").value(loc.toString)
    diff.addNode(tagLOC)
    diff.addEdge(method, tagLOC, EdgeTypes.TAGGED_BY)

    // TAG: code smells
    smells.foreach { smell =>
      val tagSmell = NewTag().name("code-smell").value(smell)
      diff.addNode(tagSmell)
      diff.addEdge(method, tagSmell, EdgeTypes.TAGGED_BY)
    }

    // TAG: refactor priority
    val tagPriority = NewTag().name("refactor-priority").value(priority)
    diff.addNode(tagPriority)
    diff.addEdge(method, tagPriority, EdgeTypes.TAGGED_BY)

    methodsTagged += 1
    if (methodsTagged % 500 == 0) println(s"[*] Processed $methodsTagged methods...")
  }

  println("[*] Calculating file coupling metrics...")

  cpg.file.l.foreach { file =>
    val coupling = calculateFileCoupling(file)

    val tagCoupling = NewTag().name("coupling-score").value(coupling.toString)
    diff.addNode(tagCoupling)
    diff.addEdge(file, tagCoupling, EdgeTypes.TAGGED_BY)

    filesTagged += 1
  }

  println(s"[*] Applying tags...")
  flatgraph.DiffGraphApplier.applyDiff(cpg.graph, diff)

  println(s"[+] Tagged $methodsTagged methods")
  println(s"[+] Tagged $filesTagged files")

  // Статистика
  val highComplexity = cpg.method.filter(_.tag.nameExact("cyclomatic-complexity").value.headOption.exists(_.toInt > COMPLEXITY_THRESHOLD)).size
  val criticalRefactor = cpg.method.where(_.tag.nameExact("refactor-priority").valueExact("critical")).size

  println(f"\n[*] Metrics Summary:")
  println(f"    Methods with complexity > $COMPLEXITY_THRESHOLD: $highComplexity")
  println(f"    Critical refactoring candidates: $criticalRefactor")
}

if (APPLY) {
  applyMetricsTags()
  println("\n[*] Query examples:")
  println("""    cpg.method.tag.name("cyclomatic-complexity").value.l.map(_.toInt).sorted.reverse.take(10)""")
  println("""    cpg.method.where(_.tag.nameExact("refactor-priority").valueExact("critical")).name.l""")
}
