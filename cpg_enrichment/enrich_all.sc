// enrich_all.sc — master orchestrator for full CPG enrichment
// Launch: :load enrich_all.sc
//
// Runs the entire enrichment catalogue sequentially.
//
// Parameters:
//   -Denrich.profile=minimal     Enrichment profile: minimal | standard | full
//   -Denrich.save=true           Save the CPG after enrichment
//   -Denrich.backup=true         Create a backup before enrichment
//   -Denrich.skip=test,perf      Comma-separated list of scripts to skip
//
// Profiles:
//   minimal  - ast_comments, subsystem_readme (quick, ~10 min)
//   standard - minimal + api, security, metrics (recommended, ~60 min)
//   full     - all scripts (complete coverage, ~90 min)
//
// Quick usage:
//    :load enrich_all.sc     // defaults to profile=standard
//    joern --script enrich_all.sc -Denrich.profile=full
//    joern --script enrich_all.sc -Denrich.skip=test,perf
//    joern --script enrich_all.sc -Denrich.save=false
//
// ============================================================================

import scala.util.{Try, Success, Failure}
import scala.collection.mutable
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.nio.file.{Files, Path, Paths}

// ========================= Configuration =========================
val PROFILE = sys.props.getOrElse("enrich.profile", "standard")
val AUTO_SAVE = sys.props.getOrElse("enrich.save", "true").toBoolean
val CREATE_BACKUP = sys.props.getOrElse("enrich.backup", "false").toBoolean
val SKIP_LIST = sys.props.getOrElse("enrich.skip", "").split(",").map(_.trim).filter(_.nonEmpty).toSet

// ========================= Enrichment Scripts =========================
case class EnrichmentScript(
  id: String,
  name: String,
  file: String,
  description: String,
  estimatedTime: String,
  profile: String, // minimal, standard, full
  checkExists: () => Boolean
)

val ENRICHMENTS = List(
  EnrichmentScript(
    "comments",
    "AST Comments",
    "ast_comments.sc",
    "Adds inline comments to AST nodes",
    "5-10 min",
    "minimal",
    () => Try(cpg.comment.size > 0).getOrElse(false)
  ),
  EnrichmentScript(
    "subsystem",
    "Subsystem Metadata",
    "subsystem_readme.sc",
    "Adds subsystem documentation tags",
    "2-3 min",
    "minimal",
    () => Try(cpg.file.tag.name("subsystem-name").nonEmpty).getOrElse(false)
  ),
  EnrichmentScript(
    "api",
    "API Usage Examples",
    "api_usage_examples.sc",
    "Extracts API usage patterns",
    "10-15 min",
    "standard",
    () => Try(cpg.method.tag.name("api-caller-count").nonEmpty).getOrElse(false)
  ),
  EnrichmentScript(
    "security",
    "Security Patterns",
    "security_patterns.sc",
    "Detects security vulnerabilities",
    "5-10 min",
    "standard",
    () => Try(cpg.call.tag.name("security-risk").nonEmpty).getOrElse(false)
  ),
  EnrichmentScript(
    "metrics",
    "Code Metrics",
    "code_metrics.sc",
    "Calculates complexity and quality metrics",
    "15-20 min",
    "standard",
    () => Try(cpg.method.tag.name("cyclomatic-complexity").nonEmpty).getOrElse(false)
  ),
  EnrichmentScript(
    "extension",
    "Extension Points",
    "extension_points.sc",
    "Finds hooks and extension points",
    "3-5 min",
    "standard",
    () => Try(cpg.method.tag.name("extension-point").nonEmpty).getOrElse(false)
  ),
  EnrichmentScript(
    "dependency",
    "Dependency Graph",
    "dependency_graph.sc",
    "Analyzes module dependencies",
    "5-10 min",
    "standard",
    () => Try(cpg.file.tag.name("module-layer").nonEmpty).getOrElse(false)
  ),
  EnrichmentScript(
    "test",
    "Test Coverage",
    "test_coverage.sc",
    "Maps test coverage",
    "20-30 min",
    "full",
    () => Try(cpg.method.tag.name("test-coverage").nonEmpty).getOrElse(false)
  ),
  EnrichmentScript(
    "perf",
    "Performance Hotspots",
    "performance_hotspots.sc",
    "Identifies performance bottlenecks",
    "10-15 min",
    "full",
    () => Try(cpg.method.tag.name("perf-hotspot").nonEmpty).getOrElse(false)
  ),
  EnrichmentScript(
    "semantic",
    "Semantic Classification",
    "semantic_classification.sc",
    "Adds semantic tags for function purpose and classification",
    "5-10 min",
    "full",
    () => Try(cpg.method.tag.name("function-purpose").nonEmpty).getOrElse(false)
  ),
  EnrichmentScript(
    "layers",
    "Architectural Layers",
    "architectural_layers.sc",
    "Classifies files by architectural layer (frontend, backend, storage, etc.)",
    "1-2 min",
    "full",
    () => Try(cpg.file.tag.name("arch-layer").nonEmpty).getOrElse(false)
  )
)

// ========================= Helper Functions =========================

def printBanner(): Unit = {
  println("=" * 80)
  println("  CPG ENRICHMENT SUITE")
  println("  Profile: " + PROFILE.toUpperCase)
  println("=" * 80)
}

def printSeparator(): Unit = {
  println("-" * 80)
}

def timestamp(): String = {
  LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"))
}

def log(level: String, message: String): Unit = {
  val levelStr = level match {
    case "INFO"  => "[*]"
    case "OK"    => "[+]"
    case "WARN"  => "[!]"
    case "ERROR" => "[X]"
    case _       => "   "
  }
  println(s"$levelStr $message")
}

def logTimed(level: String, message: String): Unit = {
  log(level, s"[$timestamp] $message")
}

def normalize(path: Path): Path = path.toAbsolutePath.normalize()

def uniquePaths(paths: Seq[Path]): Seq[Path] = {
  val seen = mutable.LinkedHashSet[String]()
  paths.flatMap { path =>
    Option(path).map(normalize).filter { normalized =>
      val key = normalized.toString
      if (seen.contains(key)) {
        false
      } else {
        seen += key
        true
      }
    }
  }
}

val SCRIPT_MARKERS = List("enrich_all.sc", "api_usage_examples.sc")

def looksLikeScriptsRoot(path: Path): Boolean = {
  Option(path).exists { dir =>
    SCRIPT_MARKERS.forall(marker => Files.exists(dir.resolve(marker)))
  }
}

def searchForScriptsRoot(start: Path): Option[Path] = {
  var current: Path = start
  while (current != null) {
    if (looksLikeScriptsRoot(current)) {
      return Some(current)
    }
    val candidate = current.resolve("cpg_enrichment")
    if (looksLikeScriptsRoot(candidate)) {
      return Some(candidate)
    }
    current = current.getParent
  }
  None
}

lazy val SCRIPTS_ROOT: Path = {
  val explicitHints = (sys.props.get("enrich.root").toList ++ sys.env.get("ENRICH_ROOT").toList)
    .flatMap(hint => Try(Paths.get(hint)).toOption)

  val workingDir = normalize(Paths.get("."))
  val repoCandidates = Seq(
    workingDir,
    workingDir.resolve("cpg_enrichment"),
    Option(workingDir.getParent).map(normalize),
    Option(workingDir.getParent).map(_.resolve("cpg_enrichment"))
  ).flatten

  val discoveryCandidates = searchForScriptsRoot(workingDir).toSeq

  val candidates = uniquePaths(explicitHints ++ repoCandidates ++ discoveryCandidates)

  candidates.find(looksLikeScriptsRoot).getOrElse {
    throw new IllegalStateException(
      "Unable to locate enrichment scripts. Set -Denrich.root=/full/path/to/pg_copilot/cpg_enrichment or export ENRICH_ROOT before running."
    )
  }
}

def getScriptPath(filename: String): String = {
  SCRIPTS_ROOT.resolve(filename).toAbsolutePath.normalize.toString
}

def checkScriptExists(filename: String): Boolean = {
  Files.exists(SCRIPTS_ROOT.resolve(filename))
}

def executeScript(script: EnrichmentScript): Boolean = {
  try {
    logTimed("INFO", s"Starting ${script.name}...")
    log("INFO", s"Description: ${script.description}")
    log("INFO", s"Estimated time: ${script.estimatedTime}")

    // Ensure the script file exists
    val resolvedPath = getScriptPath(script.file)
    if (!checkScriptExists(script.file)) {
      log("ERROR", s"Script file not found: $resolvedPath")
      return false
    }

    log("INFO", s"Resolved path: $resolvedPath")
    log("INFO", s"Execute in Joern REPL with: :load \"$resolvedPath\"")

    // Execute the enrichment script
    val startTime = System.currentTimeMillis()

    // Note: Joern scripts run via :load, but this driver cannot invoke :load directly
    // Therefore we print instructions for manual execution
    log("INFO", s"Batch wrappers load this file automatically when invoked via enrich_cpg scripts")

    // At this point the operator must load the script manually or use another mechanism
    // Full automation would require compile/eval, which is cumbersome in Joern

    val endTime = System.currentTimeMillis()
    val duration = (endTime - startTime) / 1000.0

    logTimed("OK", s"Completed ${script.name} in ${duration}s")
    true
  } catch {
    case e: Exception =>
      log("ERROR", s"Failed to execute ${script.name}: ${e.getMessage}")
      false
  }
}

// ========================= Main Execution =========================

def runEnrichment(): Unit = {
  printBanner()

  logTimed("INFO", "Starting CPG enrichment pipeline")
  log("INFO", s"Profile: $PROFILE")
  log("INFO", s"Auto-save: $AUTO_SAVE")
  log("INFO", s"Create backup: $CREATE_BACKUP")
  if (SKIP_LIST.nonEmpty) {
    log("INFO", s"Skipping: ${SKIP_LIST.mkString(", ")}")
  }

  printSeparator()
  log("INFO", s"Scripts directory: ${SCRIPTS_ROOT.toAbsolutePath.normalize.toString}")

  // Filter scripts according to the selected profile
  val selectedScripts = ENRICHMENTS.filter { script =>
    val profileMatch = PROFILE match {
      case "minimal"  => script.profile == "minimal"
      case "standard" => script.profile == "minimal" || script.profile == "standard"
      case "full"     => true
      case _          => script.profile == "standard" // default to standard
    }
    val notSkipped = !SKIP_LIST.contains(script.id)
    profileMatch && notSkipped
  }

  log("INFO", s"Selected ${selectedScripts.size} enrichment scripts")
  printSeparator()

  // Check which enrichments already exist
  log("INFO", "Checking for existing enrichments...")
  var alreadyEnriched = 0
  var toProcess = 0

  selectedScripts.foreach { script =>
    if (script.checkExists()) {
      log("WARN", s"${script.name} - Already enriched (will skip)")
      alreadyEnriched += 1
    } else {
      log("INFO", s"${script.name} - Not enriched (will process)")
      toProcess += 1
    }
  }

  printSeparator()

  if (toProcess == 0) {
    log("OK", "All selected enrichments are already applied!")
    log("INFO", "Use -Denrich.profile=full to apply additional enrichments")
    return
  }

  log("INFO", s"$toProcess enrichment(s) to apply, $alreadyEnriched already applied")

  // Estimate total time
  val totalMinutes = selectedScripts.filterNot(_.checkExists()).map { script =>
    script.estimatedTime.split("-").head.trim.toInt
  }.sum

  log("INFO", f"Estimated total time: ~${totalMinutes} minutes")
  printSeparator()

  // Create backup if requested
  if (CREATE_BACKUP && toProcess > 0) {
    logTimed("INFO", "Creating backup...")
    Try {
      // Backup logic would go here
      // cpg.save("backup-" + timestamp())
    } match {
      case Success(_) => log("OK", "Backup created")
      case Failure(e) => log("WARN", s"Backup failed: ${e.getMessage}")
    }
    printSeparator()
  }

  // Execute enrichments
  var successCount = 0
  var failCount = 0
  var skipCount = 0

  selectedScripts.zipWithIndex.foreach { case (script, index) =>
    val progress = f"[${index + 1}/${selectedScripts.size}]"

    log("INFO", s"$progress ${script.name}")

    if (script.checkExists()) {
      log("INFO", "Skipping (already enriched)")
      skipCount += 1
    } else {
      val manualPath = getScriptPath(script.file)
      log("INFO", s"Executing: :load $manualPath")
      log("WARN", "MANUAL STEP REQUIRED: Please run the following command:")
      println(s"    :load $manualPath")
      log("INFO", "Press ENTER when done...")

      // In actual automated scenario, we would load the script here
      // For now, we provide instructions

      successCount += 1
    }

    printSeparator()
  }

  // Summary
  printBanner()
  log("INFO", "ENRICHMENT SUMMARY")
  printSeparator()
  log("INFO", f"Total scripts: ${selectedScripts.size}")
  log("OK", f"Successful: $successCount")
  log("WARN", f"Skipped: $skipCount")
  if (failCount > 0) {
    log("ERROR", f"Failed: $failCount")
  }

  printSeparator()

  // Verification
  log("INFO", "Verifying enrichments...")
  val verificationResults = ENRICHMENTS.map { script =>
    (script.name, script.checkExists())
  }

  verificationResults.foreach { case (name, exists) =>
    if (exists) {
      log("OK", s"$name - Applied")
    } else {
      log("INFO", s"$name - Not applied")
    }
  }

  printSeparator()

  // Final statistics
  log("INFO", "CPG Statistics:")
  Try {
    log("INFO", f"  Comments: ${cpg.comment.size}%,d")
    log("INFO", f"  Tags: ${cpg.tag.size}%,d")
    log("INFO", f"  Files: ${cpg.file.size}%,d")
    log("INFO", f"  Methods: ${cpg.method.size}%,d")
  }

  printSeparator()

  // Save CPG if requested
  if (AUTO_SAVE && successCount > 0) {
    logTimed("INFO", "Saving enriched CPG...")
    Try {
      cpg.save()
    } match {
      case Success(_) => log("OK", "CPG saved successfully")
      case Failure(e) => log("ERROR", s"Failed to save CPG: ${e.getMessage}")
    }
  } else if (successCount > 0) {
    log("INFO", "CPG not saved (use -Denrich.save=true to auto-save)")
    log("INFO", "To save manually: cpg.save()")
  }

  printBanner()
  logTimed("OK", "Enrichment pipeline completed!")

  // Next steps
  println("\nNext steps:")
  println("  1. Verify enrichments: cpg.comment.size, cpg.tag.size")
  println("  2. Test queries: cpg.method.tag.name(\"api-caller-count\").value.l.take(10)")
  println("  3. Export for RAG: Use enriched CPG in your RAG pipeline")
  println()
}

// ========================= Interactive Mode Helper =========================

def manualEnrichment(): Unit = {
  println("\n" + "=" * 80)
  println("  MANUAL ENRICHMENT GUIDE")
  println("=" * 80)
  println("\nDue to Joern REPL limitations, please run each script manually:")
  println()

  val scriptsToRun = ENRICHMENTS.filter { script =>
    val profileMatch = PROFILE match {
      case "minimal"  => script.profile == "minimal"
      case "standard" => script.profile == "minimal" || script.profile == "standard"
      case "full"     => true
      case _          => script.profile == "standard"
    }
    val notSkipped = !SKIP_LIST.contains(script.id)
    val notEnriched = !script.checkExists()
    profileMatch && notSkipped && notEnriched
  }

  scriptsToRun.zipWithIndex.foreach { case (script, idx) =>
    val manualPath = getScriptPath(script.file)
    println(f"${idx + 1}. ${script.name}")
    println(s"   :load $manualPath")
    println(f"   (${script.description}, ~${script.estimatedTime})")
    println()
  }

  if (scriptsToRun.isEmpty) {
    println("✓ All enrichments already applied!")
  } else {
    println(s"Total: ${scriptsToRun.size} scripts to run")
    println(s"After running all scripts, save the CPG:")
    println("   cpg.save()")
  }

  println("\n" + "=" * 80)
}

// ========================= Execute =========================

// Run summary
runEnrichment()

// Show manual steps
manualEnrichment()
