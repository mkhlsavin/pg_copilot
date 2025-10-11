// test_cpg_quality.sc — Comprehensive CPG enrichment quality tests
// Usage: joern --script test_cpg_quality.sc
//
// This script evaluates the enriched CPG for RAG pipeline quality
// across multiple dimensions and use cases.

import io.shiftleft.codepropertygraph.generated.nodes._
import scala.collection.mutable.ListBuffer

println("=" * 80)
println("CPG ENRICHMENT QUALITY ASSESSMENT")
println("=" * 80)

// ============================================================================
// 1. BASIC STATISTICS
// ============================================================================
println("\n[1] BASIC CPG STATISTICS")
println("-" * 80)

val totalFiles = cpg.file.size
val totalMethods = cpg.method.size
val totalComments = cpg.comment.size
val totalTags = cpg.tag.size

println(f"Files:    $totalFiles%,d")
println(f"Methods:  $totalMethods%,d")
println(f"Comments: $totalComments%,d")
println(f"Tags:     $totalTags%,d")

// ============================================================================
// 2. SUBSYSTEM METADATA QUALITY
// ============================================================================
println("\n[2] SUBSYSTEM METADATA")
println("-" * 80)

val subsystems = cpg.file.tag.name("subsystem-name").value.dedup.l.sorted
println(f"[*] Found ${subsystems.size} subsystems:")
subsystems.take(10).foreach(s => println(f"    - $s"))
if (subsystems.size > 10) println(f"    ... and ${subsystems.size - 10} more")

val filesWithSubsystem = cpg.file.filter(_.tag.name("subsystem-name").nonEmpty).size
val subsystemCoverage = (filesWithSubsystem.toDouble / totalFiles * 100).toInt
println(f"\n[*] Subsystem coverage: $subsystemCoverage%% ($filesWithSubsystem of $totalFiles files)")

// Test: Find executor subsystem files
val executorFiles = cpg.file.where(_.tag.nameExact("subsystem-name").valueExact("executor")).name.l
println(f"\n[TEST] Executor subsystem files: ${executorFiles.size}")
if (executorFiles.nonEmpty) {
  println("    Sample files:")
  executorFiles.take(3).foreach(f => println(f"    - $f"))
}

// ============================================================================
// 3. API USAGE PATTERNS QUALITY
// ============================================================================
println("\n[3] API USAGE PATTERNS")
println("-" * 80)

val publicAPIs = cpg.method.filter(_.tag.nameExact("api-public").valueExact("true").nonEmpty).size
val totalAPIs = cpg.method.filter(_.tag.name("api-caller-count").nonEmpty).size

println(f"[*] Total APIs tracked: $totalAPIs%,d")
println(f"[*] Public APIs: $publicAPIs%,d")

// Top 10 most called APIs
println("\n[TEST] Top 10 most called APIs:")
val topAPIs = cpg.method
  .filter(_.tag.name("api-caller-count").nonEmpty)
  .l
  .map { m =>
    val callerCount = m.tag.nameExact("api-caller-count").value.headOption.map(_.toInt).getOrElse(0)
    (m.name, callerCount, m.filename)
  }
  .sortBy(-_._2)
  .take(10)

topAPIs.foreach { case (name, count, file) =>
  println(f"    $name%-40s : $count%5d callers")
}

// Test: Find memory allocation APIs
println("\n[TEST] Memory allocation APIs:")
val memAPIs = cpg.method
  .nameExact("palloc", "malloc", "MemoryContextAlloc", "repalloc")
  .filter(_.tag.name("api-caller-count").nonEmpty)
  .l
  .map { m =>
    val callerCount = m.tag.nameExact("api-caller-count").value.headOption.map(_.toInt).getOrElse(0)
    (m.name, callerCount)
  }
  .sortBy(-_._2)

memAPIs.foreach { case (name, count) =>
  println(f"    $name%-30s : $count%5d callers")
}

// ============================================================================
// 4. SECURITY PATTERNS QUALITY
// ============================================================================
println("\n[4] SECURITY VULNERABILITIES")
println("-" * 80)

val securityRiskStats = cpg.call.tag.name("security-risk").value.l.groupBy(identity).view.mapValues(_.size).toMap
println("[*] Security risk distribution:")
securityRiskStats.toList.sortBy(-_._2).foreach { case (risk, count) =>
  println(f"    $risk%-30s : $count%5d")
}

val criticalRisks = cpg.call
  .filter(_.tag.nameExact("risk-severity").valueExact("critical").nonEmpty)
  .filter(_.tag.nameExact("sanitization-point").valueExact("none").nonEmpty)
  .size

println(f"\n[!] CRITICAL unsanitized risks: $criticalRisks")

// Test: Find SQL injection candidates
println("\n[TEST] SQL injection candidates:")
val sqlInjections = cpg.call
  .filter(_.tag.nameExact("security-risk").valueExact("sql-injection").nonEmpty)
  .filter(_.tag.nameExact("sanitization-point").valueExact("none").nonEmpty)
  .l
  .map { c =>
    (c.code, c.filename, c.lineNumber.getOrElse(0))
  }
  .take(5)

sqlInjections.foreach { case (code, file, line) =>
  println(f"    $file:$line")
  println(f"        ${code.take(80)}")
}

// Test: Find buffer overflow risks
println("\n[TEST] Buffer overflow risks:")
val bufferOverflows = cpg.call
  .filter(_.tag.nameExact("security-risk").valueExact("buffer-overflow").nonEmpty)
  .filter(_.tag.nameExact("risk-severity").valueExact("critical").nonEmpty)
  .l
  .map { c =>
    (c.name, c.filename, c.lineNumber.getOrElse(0))
  }
  .take(5)

bufferOverflows.foreach { case (name, file, line) =>
  println(f"    $file:$line - $name()")
}

// ============================================================================
// 5. CODE METRICS QUALITY
// ============================================================================
println("\n[5] CODE QUALITY METRICS")
println("-" * 80)

val highComplexity = cpg.method
  .filter(_.tag.nameExact("cyclomatic-complexity").value.headOption.exists(_.toInt > 15))
  .size

val criticalRefactor = cpg.method
  .filter(_.tag.nameExact("refactor-priority").valueExact("critical").nonEmpty)
  .size

println(f"[*] Methods with complexity > 15: $highComplexity")
println(f"[*] Critical refactoring candidates: $criticalRefactor")

// Top 10 most complex methods
println("\n[TEST] Top 10 most complex methods:")
val complexMethods = cpg.method
  .filter(_.tag.name("cyclomatic-complexity").nonEmpty)
  .l
  .map { m =>
    val complexity = m.tag.nameExact("cyclomatic-complexity").value.headOption.map(_.toInt).getOrElse(0)
    val loc = m.tag.nameExact("lines-of-code").value.headOption.map(_.toInt).getOrElse(0)
    (m.name, complexity, loc, m.filename)
  }
  .sortBy(-_._2)
  .take(10)

complexMethods.foreach { case (name, complexity, loc, file) =>
  println(f"    $name%-40s : CC=$complexity%3d, LOC=$loc%4d")
}

// Code smells distribution
println("\n[TEST] Code smells distribution:")
val codeSmells = cpg.method.tag.nameExact("code-smell").value.l.groupBy(identity).view.mapValues(_.size).toMap
codeSmells.toList.sortBy(-_._2).foreach { case (smell, count) =>
  println(f"    $smell%-30s : $count%5d")
}

// ============================================================================
// 6. EXTENSION POINTS QUALITY
// ============================================================================
println("\n[6] EXTENSION POINTS")
println("-" * 80)

val hookCount = cpg.method.filter(_.tag.nameExact("extension-type").valueExact("hook").nonEmpty).size
val callbackCount = cpg.method.filter(_.tag.nameExact("extension-type").valueExact("callback").nonEmpty).size

println(f"[*] Hooks: $hookCount")
println(f"[*] Callbacks: $callbackCount")

// Test: Find planner hooks
println("\n[TEST] Planner hooks:")
val plannerHooks = cpg.method
  .filter(_.tag.nameExact("extension-type").valueExact("hook").nonEmpty)
  .filter(_.name.toLowerCase.matches(".*plan.*|.*hook.*"))
  .name
  .l
  .take(10)

plannerHooks.foreach(h => println(f"    - $h"))

// ============================================================================
// 7. DEPENDENCY GRAPH QUALITY
// ============================================================================
println("\n[7] MODULE DEPENDENCIES")
println("-" * 80)

val layerStats = cpg.file.tag.nameExact("module-layer").value.l.groupBy(identity).view.mapValues(_.size).toMap
println("[*] Files by layer:")
layerStats.toList.sortBy(-_._2).foreach { case (layer, count) =>
  println(f"    $layer%-20s : $count%5d")
}

val circularDeps = cpg.file.filter(_.tag.nameExact("circular-dependency").valueExact("true").nonEmpty).size
println(f"\n[!] Circular dependencies: $circularDeps")

// Test: Find storage layer files
println("\n[TEST] Storage layer files sample:")
cpg.file
  .filter(_.tag.nameExact("module-layer").valueExact("storage").nonEmpty)
  .name
  .l
  .take(5)
  .foreach(f => println(f"    - $f"))

// ============================================================================
// 8. TEST COVERAGE QUALITY
// ============================================================================
println("\n[8] TEST COVERAGE")
println("-" * 80)

val untestedMethods = cpg.method
  .filter(_.tag.nameExact("test-coverage").valueExact("untested").nonEmpty)
  .size

val totalTracked = cpg.method
  .filter(_.tag.name("test-coverage").nonEmpty)
  .size

val coveragePct = if (totalTracked > 0) ((totalTracked - untestedMethods).toDouble / totalTracked * 100).toInt else 0

println(f"[*] Coverage: $coveragePct%% ($untestedMethods untested of $totalTracked)")

// ============================================================================
// 9. PERFORMANCE HOTSPOTS QUALITY
// ============================================================================
println("\n[9] PERFORMANCE HOTSPOTS")
println("-" * 80)

val hotPaths = cpg.method.filter(_.tag.nameExact("perf-hotspot").valueExact("hot").nonEmpty).size
val warmPaths = cpg.method.filter(_.tag.nameExact("perf-hotspot").valueExact("warm").nonEmpty).size

println(f"[*] Hot paths: $hotPaths")
println(f"[*] Warm paths: $warmPaths")

// Test: Find allocation-heavy methods
println("\n[TEST] Allocation-heavy hot methods:")
cpg.method
  .filter(_.tag.nameExact("perf-hotspot").valueExact("hot").nonEmpty)
  .filter(_.tag.nameExact("allocation-heavy").valueExact("true").nonEmpty)
  .l
  .map { m =>
    val loopDepth = m.tag.nameExact("loop-depth").value.headOption.map(_.toInt).getOrElse(0)
    (m.name, loopDepth, m.filename)
  }
  .take(5)
  .foreach { case (name, depth, file) =>
    println(f"    $name%-40s : loop-depth=$depth")
  }

// ============================================================================
// 10. RAG USE CASE TESTS
// ============================================================================
println("\n[10] RAG USE CASE TESTS")
println("-" * 80)

// USE CASE 1: "How does PostgreSQL handle memory allocation?"
println("\n[UC1] Memory allocation API discovery:")
val memoryAPIs = cpg.method
  .name(".*alloc.*|.*MemoryContext.*")
  .filter(_.tag.name("api-caller-count").nonEmpty)
  .l
  .map { m =>
    val callers = m.tag.nameExact("api-caller-count").value.headOption.map(_.toInt).getOrElse(0)
    val isPublic = m.tag.nameExact("api-public").value.headOption.getOrElse("false")
    (m.name, callers, isPublic)
  }
  .sortBy(-_._2)
  .take(5)

println("    Top memory APIs:")
memoryAPIs.foreach { case (name, callers, isPublic) =>
  println(f"    - $name%-35s : $callers%5d callers, public=$isPublic")
}

// USE CASE 2: "Find security vulnerabilities in executor"
println("\n[UC2] Security issues in executor subsystem:")
val executorSecurityIssues = cpg.call
  .filter(_.file.tag.nameExact("subsystem-name").valueExact("executor").nonEmpty)
  .filter(_.tag.name("security-risk").nonEmpty)
  .filter(_.tag.nameExact("risk-severity").valueExact("critical").nonEmpty)
  .l
  .map { c =>
    val risk = c.tag.nameExact("security-risk").value.headOption.getOrElse("unknown")
    (c.name, risk, c.filename, c.lineNumber.getOrElse(0))
  }
  .take(5)

println(f"    Found ${executorSecurityIssues.size} critical issues in executor:")
executorSecurityIssues.foreach { case (name, risk, file, line) =>
  println(f"    - $file:$line - $name() [$risk]")
}

// USE CASE 3: "What are the most complex functions that need refactoring?"
println("\n[UC3] Complex functions needing refactoring:")
val refactorCandidates = cpg.method
  .filter(_.tag.nameExact("refactor-priority").valueExact("critical").nonEmpty)
  .l
  .map { m =>
    val complexity = m.tag.nameExact("cyclomatic-complexity").value.headOption.map(_.toInt).getOrElse(0)
    val loc = m.tag.nameExact("lines-of-code").value.headOption.map(_.toInt).getOrElse(0)
    val smells = m.tag.nameExact("code-smell").value.l.mkString(", ")
    (m.name, complexity, loc, smells, m.filename)
  }
  .sortBy(-_._2)
  .take(5)

refactorCandidates.foreach { case (name, cc, loc, smells, file) =>
  println(f"    - $name%-35s : CC=$cc%3d, LOC=$loc%4d")
  if (smells.nonEmpty) println(f"      Smells: $smells")
}

// USE CASE 4: "Find extension points for custom planner"
println("\n[UC4] Planner extension points:")
val plannerExtensions = cpg.method
  .filter(_.tag.name("extension-type").nonEmpty)
  .filter(_.name.toLowerCase.matches(".*plan.*|.*optimizer.*|.*rewrite.*"))
  .l
  .map { m =>
    val extType = m.tag.nameExact("extension-type").value.headOption.getOrElse("unknown")
    val subsystem = m.file.tag.nameExact("subsystem-name").value.headOption.getOrElse("unknown")
    (m.name, extType, subsystem)
  }
  .take(10)

plannerExtensions.foreach { case (name, extType, subsystem) =>
  println(f"    - $name%-40s [$extType in $subsystem]")
}

// USE CASE 5: "Which modules depend on the storage layer?"
println("\n[UC5] Modules depending on storage layer:")
val storageDependents = cpg.file
  .filter(_.tag.nameExact("module-layer").valueExact("storage").nonEmpty)
  .tag
  .nameExact("module-dependents")
  .value
  .l
  .flatMap(_.split(", "))
  .distinct
  .sorted
  .take(10)

storageDependents.foreach(d => println(f"    - $d"))

// ============================================================================
// 11. ENRICHMENT QUALITY SCORE
// ============================================================================
println("\n[11] ENRICHMENT QUALITY SCORE")
println("=" * 80)

var score = 0
val checks = ListBuffer[(String, Boolean, String)]()

// Check 1: Comments
val hasComments = totalComments > 1000000
checks += (("Comments coverage", hasComments, f"$totalComments%,d comments"))
if (hasComments) score += 10

// Check 2: Subsystem tags
val hasSubsystems = subsystems.size > 50
checks += (("Subsystem metadata", hasSubsystems, f"${subsystems.size} subsystems"))
if (hasSubsystems) score += 10

// Check 3: API tracking
val hasAPIs = totalAPIs > 10000
checks += (("API usage tracking", hasAPIs, f"$totalAPIs APIs tracked"))
if (hasAPIs) score += 15

// Check 4: Security analysis
val hasSecurity = securityRiskStats.nonEmpty
checks += (("Security patterns", hasSecurity, f"${securityRiskStats.size} risk types"))
if (hasSecurity) score += 15

// Check 5: Code metrics
val hasMetrics = highComplexity > 0
checks += (("Code metrics", hasMetrics, f"$highComplexity complex methods"))
if (hasMetrics) score += 15

// Check 6: Extension points
val hasExtensions = hookCount + callbackCount > 100
checks += (("Extension points", hasExtensions, f"${hookCount + callbackCount} extension points"))
if (hasExtensions) score += 10

// Check 7: Dependencies
val hasDependencies = layerStats.nonEmpty
checks += (("Dependency graph", hasDependencies, f"${layerStats.size} layers"))
if (hasDependencies) score += 10

// Check 8: Test coverage
val hasCoverage = totalTracked > 1000
checks += (("Test coverage", hasCoverage, f"$totalTracked methods tracked"))
if (hasCoverage) score += 10

// Check 9: Performance analysis
val hasPerf = hotPaths + warmPaths > 100
checks += (("Performance hotspots", hasPerf, f"${hotPaths + warmPaths} hotspots"))
if (hasPerf) score += 5

println("\nQuality Checklist:")
checks.foreach { case (name, passed, info) =>
  val mark = if (passed) "✓" else "✗"
  println(f"  [$mark] $name%-30s : $info")
}

println("\n" + "=" * 80)
println(f"OVERALL QUALITY SCORE: $score/100")
println("=" * 80)

if (score >= 80) {
  println("[+] EXCELLENT: CPG is well-enriched for RAG pipeline")
} else if (score >= 60) {
  println("[*] GOOD: CPG has sufficient enrichment, minor improvements possible")
} else if (score >= 40) {
  println("[!] FAIR: CPG needs more enrichment for production RAG use")
} else {
  println("[X] POOR: CPG enrichment is insufficient for RAG pipeline")
}

println("\n" + "=" * 80)
println("QUALITY ASSESSMENT COMPLETE")
println("=" * 80)
