// test_cpg_quality.sc  Comprehensive CPG enrichment quality tests
// Usage: joern --script test_cpg_quality.sc
//
// This script evaluates the enriched CPG for RAG pipeline quality
// across multiple dimensions and use cases.

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.semanticcpg.language._
import scala.collection.mutable.{LinkedHashMap, ListBuffer, LinkedHashSet}
import java.nio.file.{Files, Paths}
import java.nio.charset.StandardCharsets

println("=" * 80)
println("CPG ENRICHMENT QUALITY ASSESSMENT")
println("=" * 80)

val defaultCpgProp = sys.props.getOrElse("quality.cpg", "workspace/pg17_full.cpg/cpg.bin")
val defaultProjectName = sys.props.getOrElse("quality.project", "pg17_full.cpg")
val resolvedCpgPath = Paths.get(defaultCpgProp).toAbsolutePath.normalize()

val projectLoaded =
  if (workspace.projects.exists(_.name == defaultProjectName)) {
    open(defaultProjectName)
    true
  } else if (Files.exists(resolvedCpgPath)) {
    importCpg(resolvedCpgPath.toString, defaultProjectName, true)
    true
  } else {
    false
  }

if (!projectLoaded) {
  throw new IllegalStateException(
    s"Unable to load CPG for project '$defaultProjectName'. Override via -Dquality.cpg=<path>."
  )
}

def isSyntheticName(name: String): Boolean = {
  val lowered = name.toLowerCase
  val noiseNames = Set("null", "true", "false", "abort")
  val allCapsOrSymbols = name.nonEmpty && name.forall(ch => !ch.isLetter || ch.isUpper || ch == '_' || ch.isDigit)

  name.startsWith("<operator") ||
  name == "<global>" ||
  name.startsWith("<lambda>") ||
  name.startsWith("<init>") ||
  noiseNames.contains(lowered) ||
  allCapsOrSymbols
}

def distinctBy[T, K](items: Seq[T])(key: T => K): Seq[T] = {
  val seen = LinkedHashSet[K]()
  val buffer = ListBuffer[T]()
  items.foreach { item =>
    val k = key(item)
    if (!seen.contains(k)) {
      seen += k
      buffer += item
    }
  }
  buffer.toList
}

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

val stats = LinkedHashMap[String, Any]()
stats += "basic" -> Map(
  "files" -> totalFiles,
  "methods" -> totalMethods,
  "comments" -> totalComments,
  "tags" -> totalTags
)

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

stats += "subsystem" -> Map(
  "subsystem_count" -> subsystems.size,
  "coverage_percent" -> subsystemCoverage,
  "covered_files" -> filesWithSubsystem
)

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

stats += "api" -> Map(
  "tracked" -> totalAPIs,
  "public" -> publicAPIs
)

// Top 10 most called APIs
println("\n[TEST] Top 10 most called APIs:")
val topAPIsRaw = cpg.method
  .filter(_.tag.name("api-caller-count").nonEmpty)
  .l
  .map { m =>
    val callerCount = m.tag.nameExact("api-caller-count").value.headOption.map(_.toInt).getOrElse(0)
    (m.name, callerCount, Option(m.filename).getOrElse(""), m.fullName)
  }
  .filterNot { case (name, _, _, _) => isSyntheticName(name) }
  .groupBy(_._4)
  .values
  .map(_.maxBy(_._2))
  .toList
  .sortBy(-_._2)

val topAPIs = distinctBy(topAPIsRaw)(_._1).take(10)

topAPIs.foreach { case (name, count, file, _) =>
  println(f"    $name%-40s : $count%5d callers (e.g. $file)")
}

// Test: Find memory allocation APIs
println("\n[TEST] Memory allocation APIs:")
val memAPIsRaw = cpg.method
  .nameExact("palloc", "malloc", "MemoryContextAlloc", "repalloc")
  .filter(_.tag.name("api-caller-count").nonEmpty)
  .l
  .map { m =>
    val callerCount = m.tag.nameExact("api-caller-count").value.headOption.map(_.toInt).getOrElse(0)
    (m.name, callerCount)
  }
  .filterNot { case (name, _) => isSyntheticName(name) }
  .groupBy(_._1)
  .values
  .map(_.maxBy(_._2))
  .toList
  .sortBy(-_._2)

val memAPIs = distinctBy(memAPIsRaw)(_._1)

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

stats += "security" -> Map(
  "risk_distribution" -> securityRiskStats,
  "critical_unsanitized" -> criticalRisks
)

// Test: Find SQL injection candidates
println("\n[TEST] SQL injection candidates:")
val sqlInjections = cpg.call
  .filter(_.tag.nameExact("security-risk").valueExact("sql-injection").nonEmpty)
  .filter(_.tag.nameExact("sanitization-point").valueExact("none").nonEmpty)
  .l
  .map { c =>
    val file = c.file.name.headOption.getOrElse("unknown")
    (c.code, file, c.lineNumber.getOrElse(0))
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
    val file = c.file.name.headOption.getOrElse("unknown")
    (c.name, file, c.lineNumber.getOrElse(0))
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

stats += "metrics" -> Map(
  "high_complexity" -> highComplexity,
  "critical_refactor" -> criticalRefactor
)

// Top 10 most complex methods
println("\n[TEST] Top 10 most complex methods:")
val complexMethodsRaw = cpg.method
  .filter(_.tag.name("cyclomatic-complexity").nonEmpty)
  .l
  .map { m =>
    val complexity = m.tag.nameExact("cyclomatic-complexity").value.headOption.map(_.toInt).getOrElse(0)
    val loc = m.tag.nameExact("lines-of-code").value.headOption.map(_.toInt).getOrElse(0)
    (m.name, complexity, loc, Option(m.filename).getOrElse(""), m.fullName)
  }
  .filterNot { case (name, _, _, _, _) => isSyntheticName(name) }
  .groupBy(_._5)
  .values
  .map(_.maxBy(_._2))
  .toList
  .sortBy(-_._2)

val complexMethods = distinctBy(complexMethodsRaw)(_._1).take(10)

complexMethods.foreach { case (name, complexity, loc, file, _) =>
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

stats += "extension" -> Map(
  "hooks" -> hookCount,
  "callbacks" -> callbackCount
)

// Test: Find planner hooks
println("\n[TEST] Planner hooks:")
val plannerHooks = cpg.method
  .filter(_.tag.nameExact("extension-type").valueExact("hook").nonEmpty)
  .filter(_.name.toLowerCase.matches(".*plan.*|.*hook.*"))
  .name
  .l
  .filterNot(isSyntheticName)
  .distinct
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

stats += "dependencies" -> Map(
  "layers" -> layerStats,
  "circular_dependencies" -> circularDeps
)

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

stats += "test_coverage" -> Map(
  "tracked_methods" -> totalTracked,
  "untested_methods" -> untestedMethods,
  "coverage_percent" -> coveragePct
)

// ============================================================================
// 9. PERFORMANCE HOTSPOTS QUALITY
// ============================================================================
println("\n[9] PERFORMANCE HOTSPOTS")
println("-" * 80)

val hotPaths = cpg.method.filter(_.tag.nameExact("perf-hotspot").valueExact("hot").nonEmpty).size
val warmPaths = cpg.method.filter(_.tag.nameExact("perf-hotspot").valueExact("warm").nonEmpty).size

println(f"[*] Hot paths: $hotPaths")
println(f"[*] Warm paths: $warmPaths")

stats += "performance" -> Map(
  "hot_paths" -> hotPaths,
  "warm_paths" -> warmPaths
)

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
    val file = c.file.name.headOption.getOrElse("unknown")
    (c.name, risk, file, c.lineNumber.getOrElse(0))
  }
  .take(5)

println(f"    Found ${executorSecurityIssues.size} critical issues in executor:")
executorSecurityIssues.foreach { case (name, risk, file, line) =>
  println(f"    - $file:$line - $name() [$risk]")
}

// USE CASE 3: "What are the most complex functions that need refactoring?"
println("\n[UC3] Complex functions needing refactoring:")
val refactorCandidatesRaw = cpg.method
  .filter(_.tag.nameExact("refactor-priority").valueExact("critical").nonEmpty)
  .l
  .map { m =>
    val complexity = m.tag.nameExact("cyclomatic-complexity").value.headOption.map(_.toInt).getOrElse(0)
    val loc = m.tag.nameExact("lines-of-code").value.headOption.map(_.toInt).getOrElse(0)
    val smells = m.tag.nameExact("code-smell").value.l.mkString(", ")
    (m.name, complexity, loc, smells, m.filename)
  }
  .filterNot { case (name, _, _, _, _) => isSyntheticName(name) }
  .sortBy(-_._2)

val refactorCandidates = distinctBy(refactorCandidatesRaw)(_._1).take(5)

refactorCandidates.foreach { case (name, cc, loc, smells, file) =>
  println(f"    - $name%-35s : CC=$cc%3d, LOC=$loc%4d")
  if (smells.nonEmpty) println(f"      Smells: $smells")
}

// USE CASE 4: "Find extension points for custom planner"
println("\n[UC4] Planner extension points:")
val plannerExtensionsRaw = cpg.method
  .filter(_.tag.name("extension-type").nonEmpty)
  .filter(_.name.toLowerCase.matches(".*plan.*|.*optimizer.*|.*rewrite.*"))
  .l
  .map { m =>
    val extType = m.tag.nameExact("extension-type").value.headOption.getOrElse("unknown")
    val subsystem = m.file.tag.nameExact("subsystem-name").value.headOption.getOrElse("unknown")
    (m.name, extType, subsystem)
  }
  .filterNot { case (name, _, _) => isSyntheticName(name) }

val plannerExtensions = distinctBy(plannerExtensionsRaw)(_._1).take(10)

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
// 11. PARAMETER & RETURN SEMANTICS
// ============================================================================
println("\n[11] PARAMETER & RETURN SEMANTICS")
println("-" * 80)

val totalParams = cpg.parameter.size
val paramRoleCount = cpg.parameter.filter(_.tag.name("param-role").nonEmpty).size
val paramDomainCount = cpg.parameter.filter(_.tag.name("param-domain-concept").nonEmpty).size
val paramValidationCount = cpg.parameter.filter(_.tag.name("validation-required").nonEmpty).size
val totalReturns = cpg.methodReturn.size
val totalReturnStatements = cpg.ret.size
val returnKindCount = cpg.methodReturn.filter(_.tag.name("return-kind").nonEmpty).size
val returnFlagCount = cpg.methodReturn.filter(_.tag.name("return-flags").nonEmpty).size
val returnErrorCount = cpg.ret.filter(_.tag.nameExact("returns-error").valueExact("true").nonEmpty).size
val returnNullCount = cpg.ret.filter(_.tag.nameExact("returns-null").valueExact("true").nonEmpty).size
val totalLiterals = cpg.literal.size
val literalKindCount = cpg.literal.filter(_.tag.name("literal-kind").nonEmpty).size
val totalIdentifiers = cpg.identifier.size
val totalLocals = cpg.local.size
val identifierRoleCount = cpg.identifier.filter(_.tag.name("variable-role").nonEmpty).size
val localRoleCount = cpg.local.filter(_.tag.name("variable-role").nonEmpty).size
val totalModifiers = cpg.modifier.size
val modifierVisibilityCount = cpg.modifier.filter(_.tag.name("modifier-visibility").nonEmpty).size
val modifierConcurrencyCount = cpg.modifier.filter(_.tag.name("modifier-concurrency").nonEmpty).size
val modifierAttributeCount = cpg.modifier.filter(_.tag.name("modifier-attribute").nonEmpty).size
val totalMembers = cpg.member.size
val memberRoleCount = cpg.member.filter(_.tag.name("member-role").nonEmpty).size
val memberPointerCount = cpg.member.filter(_.tag.name("member-pointer").nonEmpty).size
val memberLengthCount = cpg.member.filter(_.tag.name("member-length-field").nonEmpty).size
val totalMethodRefs = cpg.methodRef.size
val methodRefKindCount = cpg.methodRef.filter(_.tag.name("method-ref-kind").nonEmpty).size
val methodRefUsageCount = cpg.methodRef.filter(_.tag.name("method-ref-usage").nonEmpty).size
val totalNamespaces = cpg.namespace.size + cpg.namespaceBlock.size
val namespaceLayerCount = cpg.namespace.filter(_.tag.name("namespace-layer").nonEmpty).size + cpg.namespaceBlock.filter(_.tag.name("namespace-layer").nonEmpty).size
val namespaceDomainCount = cpg.namespace.filter(_.tag.name("namespace-domain").nonEmpty).size + cpg.namespaceBlock.filter(_.tag.name("namespace-domain").nonEmpty).size
val namespaceLibraryCount = cpg.namespace.filter(_.tag.name("namespace-library-kind").nonEmpty).size + cpg.namespaceBlock.filter(_.tag.name("namespace-library-kind").nonEmpty).size
val namespaceScopeCount = cpg.namespace.filter(_.tag.name("namespace-scope").nonEmpty).size + cpg.namespaceBlock.filter(_.tag.name("namespace-scope").nonEmpty).size
val totalJumpTargets = cpg.jumpTarget.size + cpg.jumpLabel.size
val jumpKindCount = cpg.jumpTarget.filter(_.tag.name("jump-kind").nonEmpty).size + cpg.jumpLabel.filter(_.tag.name("jump-kind").nonEmpty).size
val jumpDomainCount = cpg.jumpTarget.filter(_.tag.name("jump-domain").nonEmpty).size + cpg.jumpLabel.filter(_.tag.name("jump-domain").nonEmpty).size
val jumpScopeCount = cpg.jumpTarget.filter(_.tag.name("jump-scope").nonEmpty).size + cpg.jumpLabel.filter(_.tag.name("jump-scope").nonEmpty).size
val totalTypeDecls = cpg.typeDecl.size
val typeCategoryCount = cpg.typeDecl.filter(_.tag.name("type-category").nonEmpty).size
val typeDomainCount = cpg.typeDecl.filter(_.tag.name("type-domain-entity").nonEmpty).size
val typeConcurrencyCount = cpg.typeDecl.filter(_.tag.name("type-concurrency-primitive").nonEmpty).size
val typeOwnershipCount = cpg.typeDecl.filter(_.tag.name("type-ownership-model").nonEmpty).size

println(f"[*] Parameters with roles: ${paramRoleCount}%,d / ${totalParams}%,d")
println(f"[*] Parameters with domain concepts: ${paramDomainCount}%,d")
println(f"[*] Parameters with validation hints: ${paramValidationCount}%,d")
println(f"[*] Method returns with semantics: ${returnKindCount}%,d / ${totalReturns}%,d")
println(f"[*] Return flags applied: ${returnFlagCount}%,d")
println(f"[*] Return statements flagged as errors: ${returnErrorCount}%,d / ${totalReturnStatements}%,d")
println(f"[*] Return statements flagged as null/empty: ${returnNullCount}%,d / ${totalReturnStatements}%,d")
println(f"[*] Literals tagged with semantics: ${literalKindCount}%,d / ${totalLiterals}%,d")
println(f"[*] Identifiers with roles: ${identifierRoleCount}%,d / ${totalIdentifiers}%,d")
println(f"[*] Locals with roles: ${localRoleCount}%,d / ${totalLocals}%,d")
println(f"[*] Modifiers with visibility tags: ${modifierVisibilityCount}%,d / ${totalModifiers}%,d")
println(f"[*] Modifiers with concurrency tags: ${modifierConcurrencyCount}%,d / ${totalModifiers}%,d")
println(f"[*] Modifiers with attribute tags: ${modifierAttributeCount}%,d / ${totalModifiers}%,d")
println(f"[*] Members with role tags: ${memberRoleCount}%,d / ${totalMembers}%,d")
println(f"[*] Members flagged as pointers: ${memberPointerCount}%,d / ${totalMembers}%,d")
println(f"[*] Member length fields: ${memberLengthCount}%,d / ${totalMembers}%,d")
println(f"[*] Method references with kind tags: ${methodRefKindCount}%,d / ${totalMethodRefs}%,d")
println(f"[*] Method references with usage tags: ${methodRefUsageCount}%,d / ${totalMethodRefs}%,d")
println(f"[*] Namespaces with layer tags: ${namespaceLayerCount}%,d / ${totalNamespaces}%,d")
println(f"[*] Namespaces with domain tags: ${namespaceDomainCount}%,d / ${totalNamespaces}%,d")
println(f"[*] Namespaces with library kind tags: ${namespaceLibraryCount}%,d / ${totalNamespaces}%,d")
println(f"[*] Namespaces with scope tags: ${namespaceScopeCount}%,d / ${totalNamespaces}%,d")
println(f"[*] Jump targets/labels with kind tags: ${jumpKindCount}%,d / ${totalJumpTargets}%,d")
println(f"[*] Jump targets/labels with domain tags: ${jumpDomainCount}%,d / ${totalJumpTargets}%,d")
println(f"[*] Jump targets/labels with scope tags: ${jumpScopeCount}%,d / ${totalJumpTargets}%,d")

println("[TEST] Method reference kinds:")
cpg.methodRef
  .tag
  .nameExact("method-ref-kind")
  .value
  .l
  .groupBy(identity)
  .view
  .mapValues(_.size)
  .toList
  .sortBy(-_._2)
  .take(5)
  .foreach { case (label, count) =>
    println(f"    ${label}%-25s : ${count}%,d refs")
  }

println("[TEST] Method reference usages:")
cpg.methodRef
  .tag
  .nameExact("method-ref-usage")
  .value
  .l
  .groupBy(identity)
  .view
  .mapValues(_.size)
  .toList
  .sortBy(-_._2)
  .take(5)
  .foreach { case (label, count) =>
    println(f"    ${label}%-25s : ${count}%,d refs")
  }

println(f"[*] Type declarations with category tags: ${typeCategoryCount}%,d / ${totalTypeDecls}%,d")
println(f"[*] Type declarations with domain tags: ${typeDomainCount}%,d / ${totalTypeDecls}%,d")
println(f"[*] Type declarations with concurrency tags: ${typeConcurrencyCount}%,d / ${totalTypeDecls}%,d")
println(f"[*] Type declarations with ownership tags: ${typeOwnershipCount}%,d / ${totalTypeDecls}%,d")

stats += "semantics" -> Map(
  "parameters" -> Map(
    "total" -> totalParams,
    "with_role" -> paramRoleCount,
    "with_domain" -> paramDomainCount,
    "with_validation" -> paramValidationCount
  ),
  "returns" -> Map(
    "total" -> totalReturns,
    "total_statements" -> totalReturnStatements,
    "with_kind" -> returnKindCount,
    "with_flags" -> returnFlagCount,
    "error_statements" -> returnErrorCount,
    "null_statements" -> returnNullCount
  ),
  "literals" -> Map(
    "total" -> totalLiterals,
    "with_kind" -> literalKindCount
  ),
  "identifiers" -> Map(
    "total" -> totalIdentifiers,
    "with_role" -> identifierRoleCount
  ),
  "locals" -> Map(
    "total" -> totalLocals,
    "with_role" -> localRoleCount
  ),
  "modifiers" -> Map(
    "total" -> totalModifiers,
    "with_visibility" -> modifierVisibilityCount,
    "with_concurrency" -> modifierConcurrencyCount,
    "with_attribute" -> modifierAttributeCount
  ),
  "members" -> Map(
    "total" -> totalMembers,
    "with_role" -> memberRoleCount,
    "pointer" -> memberPointerCount,
    "length_field" -> memberLengthCount
  ),
  "method_refs" -> Map(
    "total" -> totalMethodRefs,
    "with_kind" -> methodRefKindCount,
    "with_usage" -> methodRefUsageCount
  ),
  "namespaces" -> Map(
    "total" -> totalNamespaces,
    "with_layer" -> namespaceLayerCount,
    "with_domain" -> namespaceDomainCount,
    "with_library_kind" -> namespaceLibraryCount,
    "with_scope" -> namespaceScopeCount
  ),
  "jumps" -> Map(
    "total" -> totalJumpTargets,
    "with_kind" -> jumpKindCount,
    "with_domain" -> jumpDomainCount,
    "with_scope" -> jumpScopeCount
  ),
  "types" -> Map(
    "total" -> totalTypeDecls,
    "with_category" -> typeCategoryCount,
    "with_domain" -> typeDomainCount,
    "with_concurrency" -> typeConcurrencyCount,
    "with_ownership" -> typeOwnershipCount
  )
)

println("\n[TEST] Sample error return statements:")
cpg.ret
  .filter(_.tag.nameExact("returns-error").valueExact("true").nonEmpty)
  .l
  .take(5)
  .foreach { ret =>
    val method = ret.method.name
    val file = ret.file.name.headOption.getOrElse("unknown")
    val line = ret.lineNumber.getOrElse(0)
    val code = Option(ret.code).getOrElse("").trim
    println(f"    $file:$line - $method")
    if (code.nonEmpty) println(f"        ${code.take(80)}")
  }

println("\n[TEST] Sample null return statements:")
cpg.ret
  .filter(_.tag.nameExact("returns-null").valueExact("true").nonEmpty)
  .l
  .take(5)
  .foreach { ret =>
    val method = ret.method.name
    val file = ret.file.name.headOption.getOrElse("unknown")
    val line = ret.lineNumber.getOrElse(0)
    val code = Option(ret.code).getOrElse("").trim
    println(f"    $file:$line - $method")
    if (code.nonEmpty) println(f"        ${code.take(80)}")
  }

println("\n[TEST] Top parameter roles:")
cpg.parameter
  .tag
  .nameExact("param-role")
  .value
  .l
  .groupBy(identity)
  .view
  .mapValues(_.size)
  .toList
  .sortBy(-_._2)
  .take(10)
  .foreach { case (role, count) =>
    println(f"    ${role}%-25s : ${count}%,d params")
  }

println("\n[TEST] Sample validation-required parameters:")
cpg.parameter
  .filter(_.tag.nameExact("validation-required").nonEmpty)
  .l
  .take(5)
  .foreach { p =>
    val validations = p.tag.nameExact("validation-required").value.l.mkString(", ")
    println(f"    ${p.method.name}%-35s :: ${p.name}%-20s -> ${validations}")
  }

println("\n[TEST] Top local variable roles:")
cpg.local
  .tag
  .nameExact("variable-role")
  .value
  .l
  .groupBy(identity)
  .view
  .mapValues(_.size)
  .toList
  .sortBy(-_._2)
  .take(10)
  .foreach { case (role, count) =>
    println(f"    ${role}%-25s : ${count}%,d locals")
  }

println("\n[TEST] Modifier visibility breakdown:")
cpg.modifier
  .tag
  .nameExact("modifier-visibility")
  .value
  .l
  .groupBy(identity)
  .view
  .mapValues(_.size)
  .toList
  .sortBy(-_._2)
  .foreach { case (visibility, count) =>
    println(f"    ${visibility}%-12s : ${count}%,d modifiers")
  }

println("\n[TEST] Modifier concurrency tags:")
cpg.modifier
  .tag
  .nameExact("modifier-concurrency")
  .value
  .l
  .groupBy(identity)
  .view
  .mapValues(_.size)
  .toList
  .sortBy(-_._2)
  .take(5)
  .foreach { case (label, count) =>
    println(f"    ${label}%-25s : ${count}%,d modifiers")
  }

println("\n[TEST] Type domain entities:")
cpg.typeDecl
  .tag
  .nameExact("type-domain-entity")
  .value
  .l
  .groupBy(identity)
  .view
  .mapValues(_.size)
  .toList
  .sortBy(-_._2)
  .take(10)
  .foreach { case (label, count) =>
    println(f"    ${label}%-25s : ${count}%,d types")
  }

println("\n[TEST] Type concurrency primitives:")
cpg.typeDecl
  .tag
  .nameExact("type-concurrency-primitive")
  .value
  .l
  .groupBy(identity)
  .view
  .mapValues(_.size)
  .toList
  .sortBy(-_._2)
  .take(5)
  .foreach { case (label, count) =>
    println(f"    ${label}%-25s : ${count}%,d types")
  }

println("\n[TEST] Type ownership models:")
cpg.typeDecl
  .tag
  .nameExact("type-ownership-model")
  .value
  .l
  .groupBy(identity)
  .view
  .mapValues(_.size)
  .toList
  .sortBy(-_._2)
  .take(5)
  .foreach { case (label, count) =>
    println(f"    ${label}%-25s : ${count}%,d types")
  }

// ============================================================================
// 12. TAG COVERAGE SUMMARY
// ============================================================================
println("\n[12] TAG COVERAGE SUMMARY")
println("-" * 80)

def countTagsForNodes(nodes: Iterable[StoredNode]): Map[String, Int] = {
  nodes.flatMap { node =>
    try {
      node.tag.name.l.distinct
    } catch {
      case _: Throwable => Nil
    }
  }.groupBy(identity).view.mapValues(_.size).toMap
}

def topTags(entries: Map[String, Int], limit: Int): Seq[(String, Int)] =
  entries.toSeq.sortBy(-_._2).take(limit)

val tagTotalsMap = cpg.tag.name.l.groupBy(identity).view.mapValues(_.size).toMap
val topTagsOverall = topTags(tagTotalsMap, 20)

println("[*] Top tags across the CPG:")
topTagsOverall.foreach { case (tagName, count) =>
  println(f"    $tagName%-30s : $count%,d")
}

val coverageByEntityRaw = Map(
  "file" -> topTags(countTagsForNodes(cpg.file.l), 20),
  "method" -> topTags(countTagsForNodes(cpg.method.l), 20),
  "call" -> topTags(countTagsForNodes(cpg.call.l), 20),
  "return" -> topTags(countTagsForNodes(cpg.ret.l), 20)
)

coverageByEntityRaw.foreach { case (entity, entries) =>
  println(s"\n[TEST] Top tags on $entity nodes:")
  entries.foreach { case (tagName, count) =>
    println(f"    $tagName%-30s : $count%,d")
  }
}

val coverageByEntity = coverageByEntityRaw.map { case (entity, entries) =>
  entity -> entries.map { case (tagName, count) => Map("tag" -> tagName, "count" -> count) }
}

stats += "tags" -> Map(
  "total_unique_tags" -> tagTotalsMap.size,
  "top_tags" -> topTagsOverall.map { case (tagName, count) => Map("tag" -> tagName, "count" -> count) },
  "coverage_by_entity" -> coverageByEntity
)

// ============================================================================
// 13. ENRICHMENT QUALITY SCORE
// ============================================================================
println("\n[13] ENRICHMENT QUALITY SCORE")
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
if (hasAPIs) score += 12

// Check 4: Security analysis
val hasSecurity = securityRiskStats.nonEmpty
checks += (("Security patterns", hasSecurity, f"${securityRiskStats.size} risk types"))
if (hasSecurity) score += 13

// Check 5: Code metrics
val hasMetrics = highComplexity > 0
checks += (("Code metrics", hasMetrics, f"$highComplexity complex methods"))
if (hasMetrics) score += 12

// Check 6: Extension points
val hasExtensions = hookCount + callbackCount > 100
checks += (("Extension points", hasExtensions, f"${hookCount + callbackCount} extension points"))
if (hasExtensions) score += 8

// Check 7: Dependencies
val hasDependencies = layerStats.nonEmpty
checks += (("Dependency graph", hasDependencies, f"${layerStats.size} layers"))
if (hasDependencies) score += 8

// Check 8: Test coverage
val hasCoverage = totalTracked > 1000
checks += (("Test coverage", hasCoverage, f"$totalTracked methods tracked"))
if (hasCoverage) score += 10

// Check 9: Performance analysis
val hasPerf = hotPaths + warmPaths > 100
checks += (("Performance hotspots", hasPerf, f"${hotPaths + warmPaths} hotspots"))
if (hasPerf) score += 5

// Check 10: Parameter/return semantics
val hasParamSemantics = paramRoleCount > 5000 && returnKindCount > 2000
checks += (("Param/return semantics", hasParamSemantics, f"$paramRoleCount roles, $returnKindCount return kinds"))
if (hasParamSemantics) score += 12

println("\nQuality Checklist:")
checks.foreach { case (name, passed, info) =>
  val mark = if (passed) "" else ""
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

stats += "quality" -> Map(
  "score" -> score,
  "checks" -> checks.toList.map { case (name, passed, info) =>
    Map("name" -> name, "passed" -> passed, "info" -> info)
  }
)

println("\n" + "=" * 80)
println("QUALITY ASSESSMENT COMPLETE")
println("=" * 80)

def escapeJson(str: String): String =
  str.flatMap {
    case '"'  => "\\\""
    case '\\' => "\\\\"
    case '\n' => "\\n"
    case '\r' => "\\r"
    case '\t' => "\\t"
    case c if c.isControl => f"\\u${c.toInt}%04x"
    case c   => c.toString
  }

def toJson(value: Any): String = value match {
  case m: collection.Map[?, ?] =>
    val entries = m.iterator
      .map { case (k, v) => "\"" + escapeJson(k.toString) + "\":" + toJson(v) }
      .mkString(",")
    s"{$entries}"
  case iterable: Iterable[?] =>
    iterable.iterator.map(toJson).mkString("[", ",", "]")
  case s: String  => "\"" + escapeJson(s) + "\""
  case b: Boolean => if (b) "true" else "false"
  case n: Int     => n.toString
  case n: Long    => n.toString
  case n: Double  => if (n.isWhole) n.toLong.toString else n.toString
  case n: Float   => if (n.isWhole) n.toLong.toString else n.toString
  case n: BigInt  => n.toString()
  case n: BigDecimal => n.toString()
  case other      => "\"" + escapeJson(other.toString) + "\""
}

val statsDir = Paths.get("stats")
if (!Files.exists(statsDir)) {
  Files.createDirectories(statsDir)
}
val statsPath = statsDir.resolve("enrichment_quality.json")
Files.write(statsPath, toJson(stats).getBytes(StandardCharsets.UTF_8))
println(s"[+] Quality stats written to ${statsPath.toAbsolutePath}")
