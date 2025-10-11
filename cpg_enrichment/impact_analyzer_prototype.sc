// impact_analyzer_prototype.sc — Прототип анализатора impact для patch review
// Использование: :load impact_analyzer_prototype.sc
//
// ============================================================================
// НАЗНАЧЕНИЕ
// ============================================================================
// Анализирует "взрывной радиус" изменений в патче:
// - Какие API изменились
// - Сколько caller'ов затронуто
// - Какие слои и подсистемы затронуты
// - Уровень риска (LOW/MEDIUM/HIGH/CRITICAL)
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import scala.collection.mutable

// ============================================================================
// DATA STRUCTURES
// ============================================================================

case class ImpactReport(
  modifiedMethods: List[MethodImpact],
  affectedLayers: Set[String],
  affectedSubsystems: Set[String],
  overallRisk: RiskLevel,
  totalCallersAffected: Int,
  crossLayerImpact: Boolean
)

case class MethodImpact(
  methodName: String,
  fullName: String,
  file: String,
  callerCount: Int,
  callers: List[CallerInfo],
  layer: Option[String],
  subsystem: Option[String],
  isPublicAPI: Boolean,
  riskLevel: RiskLevel
)

case class CallerInfo(
  methodName: String,
  file: String,
  layer: Option[String],
  subsystem: Option[String]
)

sealed trait RiskLevel {
  def value: Int
}
object RiskLevel {
  case object LOW extends RiskLevel { val value = 1 }
  case object MEDIUM extends RiskLevel { val value = 2 }
  case object HIGH extends RiskLevel { val value = 3 }
  case object CRITICAL extends RiskLevel { val value = 4 }

  def fromCallerCount(count: Int, isPublicAPI: Boolean, crossLayer: Boolean): RiskLevel = {
    (count, isPublicAPI, crossLayer) match {
      case (c, true, true) if c > 200  => CRITICAL
      case (c, true, _) if c > 100     => CRITICAL
      case (c, _, true) if c > 50      => HIGH
      case (c, _, _) if c > 50         => HIGH
      case (c, _, true) if c > 10      => MEDIUM
      case (c, _, _) if c > 10         => MEDIUM
      case _                           => LOW
    }
  }
}

// ============================================================================
// MAIN ANALYSIS FUNCTIONS
// ============================================================================

/**
 * Анализирует impact для списка методов (например, измененных в патче)
 */
def analyzeMethodsImpact(methodNames: List[String]): ImpactReport = {
  println(s"[*] Analyzing impact for ${methodNames.size} methods...")

  val methodImpacts = methodNames.flatMap { methodName =>
    analyzeMethodImpact(methodName)
  }

  val totalCallers = methodImpacts.map(_.callerCount).sum
  val affectedLayers = methodImpacts.flatMap(_.layer).toSet
  val affectedSubsystems = methodImpacts.flatMap(_.subsystem).toSet

  // Проверка cross-layer impact
  val crossLayer = methodImpacts.exists { mi =>
    mi.callers.exists(c => c.layer.isDefined && c.layer != mi.layer)
  }

  // Определяем overall risk
  val maxRisk = if (methodImpacts.isEmpty) RiskLevel.LOW
    else methodImpacts.map(_.riskLevel.value).max match {
      case 4 => RiskLevel.CRITICAL
      case 3 => RiskLevel.HIGH
      case 2 => RiskLevel.MEDIUM
      case _ => RiskLevel.LOW
    }

  ImpactReport(
    methodImpacts,
    affectedLayers,
    affectedSubsystems,
    maxRisk,
    totalCallers,
    crossLayer
  )
}

/**
 * Анализирует impact для одного метода
 */
def analyzeMethodImpact(methodName: String): Option[MethodImpact] = {
  // Найти метод в CPG
  val methods = cpg.method.name(methodName).l

  if (methods.isEmpty) {
    println(s"[!] Method not found: $methodName")
    return None
  }

  // Берем первый найденный (можно улучшить через fullName)
  val method = methods.head

  // Найти всех вызывающих
  val callers = cpg.method.fullNameExact(method.fullName).caller.l

  // Собираем информацию о caller'ах
  val callerInfos = callers.map { caller =>
    CallerInfo(
      caller.name,
      caller.file.name.headOption.getOrElse("unknown"),
      caller.file.tag.nameExact("arch-layer").value.headOption,
      caller.file.tag.nameExact("subsystem-name").value.headOption
    )
  }

  // Определяем метаданные метода
  val methodLayer = method.file.tag.nameExact("arch-layer").value.headOption
  val methodSubsystem = method.file.tag.nameExact("subsystem-name").value.headOption
  val isPublicAPI = method.tag.nameExact("api-public").value.headOption.contains("true")

  // Cross-layer check
  val crossLayer = callerInfos.exists(c =>
    c.layer.isDefined && methodLayer.isDefined && c.layer != methodLayer
  )

  // Определяем risk level
  val riskLevel = RiskLevel.fromCallerCount(
    callers.size,
    isPublicAPI,
    crossLayer
  )

  Some(MethodImpact(
    method.name,
    method.fullName,
    method.file.name.headOption.getOrElse("unknown"),
    callers.size,
    callerInfos,
    methodLayer,
    methodSubsystem,
    isPublicAPI,
    riskLevel
  ))
}

/**
 * Ищет методы в файле (для patch analysis)
 */
def getMethodsInFile(filePath: String): List[String] = {
  cpg.file.name(s".*$filePath.*").method.name.dedup.l
}

/**
 * Ищет методы в диапазоне строк (для patch hunks)
 */
def getMethodsInLineRange(
  filePath: String,
  startLine: Int,
  endLine: Int
): List[String] = {
  cpg.file.name(s".*$filePath.*")
    .method
    .filter { m =>
      val methodStart = m.lineNumber.getOrElse(0)
      val methodEnd = m.lineNumberEnd.getOrElse(0)

      // Метод пересекается с диапазоном
      methodStart <= endLine && methodEnd >= startLine
    }
    .name.dedup.l
}

// ============================================================================
// REPORTING FUNCTIONS
// ============================================================================

def printImpactReport(report: ImpactReport): Unit = {
  println("\n" + "=" * 80)
  println("  IMPACT ANALYSIS REPORT")
  println("=" * 80)

  println(s"\n[*] Overall Risk: ${report.overallRisk}")
  println(s"[*] Total Methods Analyzed: ${report.modifiedMethods.size}")
  println(s"[*] Total Callers Affected: ${report.totalCallersAffected}")
  println(s"[*] Cross-Layer Impact: ${if (report.crossLayerImpact) "YES ⚠️" else "NO ✓"}")

  println(s"\n[*] Affected Layers (${report.affectedLayers.size}):")
  report.affectedLayers.toList.sorted.foreach { layer =>
    println(s"    - $layer")
  }

  println(s"\n[*] Affected Subsystems (${report.affectedSubsystems.size}):")
  report.affectedSubsystems.toList.sorted.foreach { subsystem =>
    println(s"    - $subsystem")
  }

  println("\n" + "-" * 80)
  println("  METHOD-BY-METHOD BREAKDOWN")
  println("-" * 80)

  // Сортируем по risk level и caller count
  val sortedMethods = report.modifiedMethods.sortBy(m => (-m.riskLevel.value, -m.callerCount))

  sortedMethods.foreach { mi =>
    val riskBadge = mi.riskLevel match {
      case RiskLevel.CRITICAL => "🔴 CRITICAL"
      case RiskLevel.HIGH     => "🟠 HIGH"
      case RiskLevel.MEDIUM   => "🟡 MEDIUM"
      case RiskLevel.LOW      => "🟢 LOW"
    }

    val apiBadge = if (mi.isPublicAPI) "[PUBLIC API]" else ""

    println(s"\n${mi.methodName} $apiBadge")
    println(s"  Risk: $riskBadge")
    println(s"  File: ${mi.file}")
    println(s"  Layer: ${mi.layer.getOrElse("unknown")}")
    println(s"  Subsystem: ${mi.subsystem.getOrElse("unknown")}")
    println(s"  Callers: ${mi.callerCount}")

    if (mi.callerCount > 0 && mi.callerCount <= 10) {
      println(s"  Top callers:")
      mi.callers.take(10).foreach { caller =>
        val layerInfo = caller.layer.map(l => s"[$l]").getOrElse("")
        println(s"    - ${caller.methodName} in ${caller.file} $layerInfo")
      }
    } else if (mi.callerCount > 10) {
      println(s"  Top 10 callers:")
      mi.callers.take(10).foreach { caller =>
        val layerInfo = caller.layer.map(l => s"[$l]").getOrElse("")
        println(s"    - ${caller.methodName} in ${caller.file} $layerInfo")
      }
      println(s"  ... and ${mi.callerCount - 10} more")
    }

    // Cross-layer warnings
    val crossLayerCallers = mi.callers.filter(c =>
      c.layer.isDefined && mi.layer.isDefined && c.layer != mi.layer
    )
    if (crossLayerCallers.nonEmpty) {
      println(s"  ⚠️  Cross-layer callers: ${crossLayerCallers.size}")
      crossLayerCallers.take(5).foreach { c =>
        println(s"    - ${c.layer.getOrElse("unknown")} → ${mi.layer.getOrElse("unknown")}")
      }
    }
  }

  println("\n" + "=" * 80)
}

def generateMarkdownReport(report: ImpactReport): String = {
  val sb = new StringBuilder

  sb.append("# Impact Analysis Report\n\n")

  // Summary
  sb.append("## Summary\n\n")
  sb.append(s"**Overall Risk:** ${report.overallRisk}\n\n")
  sb.append(s"**Statistics:**\n")
  sb.append(s"- Methods analyzed: ${report.modifiedMethods.size}\n")
  sb.append(s"- Total callers affected: ${report.totalCallersAffected}\n")
  sb.append(s"- Cross-layer impact: ${if (report.crossLayerImpact) "YES ⚠️" else "NO ✓"}\n")
  sb.append(s"- Affected layers: ${report.affectedLayers.size}\n")
  sb.append(s"- Affected subsystems: ${report.affectedSubsystems.size}\n\n")

  // Risk distribution
  val riskDistribution = report.modifiedMethods.groupBy(_.riskLevel).view.mapValues(_.size).toMap
  sb.append("**Risk Distribution:**\n")
  sb.append(s"- 🔴 CRITICAL: ${riskDistribution.getOrElse(RiskLevel.CRITICAL, 0)}\n")
  sb.append(s"- 🟠 HIGH: ${riskDistribution.getOrElse(RiskLevel.HIGH, 0)}\n")
  sb.append(s"- 🟡 MEDIUM: ${riskDistribution.getOrElse(RiskLevel.MEDIUM, 0)}\n")
  sb.append(s"- 🟢 LOW: ${riskDistribution.getOrElse(RiskLevel.LOW, 0)}\n\n")

  // Affected layers
  sb.append("## Affected Components\n\n")
  sb.append("### Layers\n\n")
  report.affectedLayers.toList.sorted.foreach { layer =>
    val methodCount = report.modifiedMethods.count(_.layer.contains(layer))
    sb.append(s"- **$layer** ($methodCount methods)\n")
  }

  sb.append("\n### Subsystems\n\n")
  report.affectedSubsystems.toList.sorted.foreach { subsystem =>
    val methodCount = report.modifiedMethods.count(_.subsystem.contains(subsystem))
    sb.append(s"- **$subsystem** ($methodCount methods)\n")
  }

  // Critical/High risk methods
  val criticalMethods = report.modifiedMethods.filter(_.riskLevel == RiskLevel.CRITICAL)
  val highRiskMethods = report.modifiedMethods.filter(_.riskLevel == RiskLevel.HIGH)

  if (criticalMethods.nonEmpty) {
    sb.append("\n## 🔴 Critical Risk Methods\n\n")
    criticalMethods.foreach { mi =>
      sb.append(s"### `${mi.methodName}`\n\n")
      sb.append(s"- **File:** `${mi.file}`\n")
      sb.append(s"- **Layer:** ${mi.layer.getOrElse("unknown")}\n")
      sb.append(s"- **Callers:** ${mi.callerCount}\n")
      if (mi.isPublicAPI) sb.append(s"- **Type:** PUBLIC API\n")
      sb.append("\n")
    }
  }

  if (highRiskMethods.nonEmpty) {
    sb.append("\n## 🟠 High Risk Methods\n\n")
    highRiskMethods.foreach { mi =>
      sb.append(s"### `${mi.methodName}`\n\n")
      sb.append(s"- **File:** `${mi.file}`\n")
      sb.append(s"- **Callers:** ${mi.callerCount}\n\n")
    }
  }

  // Detailed breakdown
  sb.append("\n## Detailed Method Breakdown\n\n")
  report.modifiedMethods.sortBy(m => (-m.riskLevel.value, -m.callerCount)).foreach { mi =>
    val riskEmoji = mi.riskLevel match {
      case RiskLevel.CRITICAL => "🔴"
      case RiskLevel.HIGH     => "🟠"
      case RiskLevel.MEDIUM   => "🟡"
      case RiskLevel.LOW      => "🟢"
    }

    sb.append(s"### $riskEmoji `${mi.methodName}`\n\n")
    sb.append(s"- **Full name:** `${mi.fullName}`\n")
    sb.append(s"- **File:** `${mi.file}`\n")
    sb.append(s"- **Layer:** ${mi.layer.getOrElse("unknown")}\n")
    sb.append(s"- **Subsystem:** ${mi.subsystem.getOrElse("unknown")}\n")
    sb.append(s"- **Callers:** ${mi.callerCount}\n")
    sb.append(s"- **Public API:** ${if (mi.isPublicAPI) "Yes" else "No"}\n")

    if (mi.callerCount > 0) {
      sb.append(s"\n**Top callers:**\n\n")
      mi.callers.take(10).foreach { c =>
        sb.append(s"- `${c.methodName}` in `${c.file}`")
        c.layer.foreach(l => sb.append(s" [$l]"))
        sb.append("\n")
      }
      if (mi.callerCount > 10) {
        sb.append(s"\n*... and ${mi.callerCount - 10} more callers*\n")
      }
    }

    sb.append("\n---\n\n")
  }

  sb.toString()
}

// ============================================================================
// EXAMPLE USAGE
// ============================================================================

def exampleUsage(): Unit = {
  println("\n=== EXAMPLE USAGE ===\n")

  // Example 1: Analyze specific methods
  println("Example 1: Analyze impact of changing create_plan():")
  println("  val report = analyzeMethodsImpact(List(\"create_plan\"))")
  println("  printImpactReport(report)")

  // Example 2: Analyze methods in a file
  println("\nExample 2: Analyze all methods in a file:")
  println("  val methods = getMethodsInFile(\"planner.c\")")
  println("  val report = analyzeMethodsImpact(methods)")
  println("  printImpactReport(report)")

  // Example 3: Analyze methods in line range (for patch hunk)
  println("\nExample 3: Analyze methods in a specific line range:")
  println("  val methods = getMethodsInLineRange(\"optimizer/plan/planner.c\", 100, 200)")
  println("  val report = analyzeMethodsImpact(methods)")
  println("  printImpactReport(report)")

  // Example 4: Generate markdown report
  println("\nExample 4: Generate markdown report:")
  println("  val report = analyzeMethodsImpact(List(\"ExecInitNode\"))")
  println("  val markdown = generateMarkdownReport(report)")
  println("  java.nio.file.Files.write(")
  println("    java.nio.file.Paths.get(\"impact-report.md\"),")
  println("    markdown.getBytes)")
}

// ============================================================================
// DEMO: Analyze some popular PostgreSQL functions
// ============================================================================

def runDemo(): Unit = {
  println("\n" + "=" * 80)
  println("  IMPACT ANALYZER DEMO")
  println("=" * 80)

  // Analyze some core PostgreSQL functions
  val testMethods = List(
    "palloc",           // Very popular memory allocation
    "MemoryContextAlloc", // Core memory context API
    "ExecInitNode",     // Executor initialization
    "standard_planner"  // Query planner entry point
  )

  println(s"\n[*] Running demo analysis on ${testMethods.size} methods...")
  println(s"[*] Methods: ${testMethods.mkString(\", \")}\n")

  val report = analyzeMethodsImpact(testMethods)
  printImpactReport(report)

  println("\n[*] Generating markdown report...")
  val markdown = generateMarkdownReport(report)

  try {
    val outputPath = java.nio.file.Paths.get("impact-demo-report.md")
    java.nio.file.Files.write(outputPath, markdown.getBytes)
    println(s"[+] Markdown report saved to: $outputPath")
  } catch {
    case e: Exception =>
      println(s"[!] Failed to save markdown report: ${e.getMessage}")
  }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

println("[+] Impact Analyzer Prototype loaded!")
println("[*] Available functions:")
println("    - analyzeMethodsImpact(methodNames: List[String]): ImpactReport")
println("    - analyzeMethodImpact(methodName: String): Option[MethodImpact]")
println("    - getMethodsInFile(filePath: String): List[String]")
println("    - getMethodsInLineRange(file: String, start: Int, end: Int): List[String]")
println("    - printImpactReport(report: ImpactReport): Unit")
println("    - generateMarkdownReport(report: ImpactReport): String")
println("    - exampleUsage(): Unit")
println("    - runDemo(): Unit")
println()
println("[*] Try running: runDemo()")
