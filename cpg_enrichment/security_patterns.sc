// security_patterns.sc - security vulnerability detection helpers
// Launch: :load security_patterns.sc
//
// IMPORTANT: this script mutates the graph (adds TAG nodes with security metadata).
//
// ============================================================================
// Parameters
// ============================================================================
// Optional JVM flags (defaults in parentheses):
//   -Dsecurity.apply=true        apply tags back to the graph (default: true)
//   -Dsecurity.strict=false      strict analysis mode (default: false, enables more aggressive heuristics)
//
// ============================================================================
// Tags emitted
// ============================================================================
// The script identifies security patterns and emits the following tags:
// - `security-risk`: "sql-injection" | "buffer-overflow" | "format-string" | "path-traversal" | "command-injection"
// - `trust-boundary`: "user-input" | "network-input" | "file-input" | "safe"
// - `sanitization-point`: "validated" | "escaped" | "sanitized" | "none"
// - `privilege-level`: "admin" | "user" | "unrestricted"
// - `risk-severity`: "critical" | "high" | "medium" | "low"
//
// ============================================================================
// Usage examples
// ============================================================================
//
// 1. List SQL injection candidates that lack sanitisation:
//    cpg.call
//      .where(_.tag.nameExact("security-risk").valueExact("sql-injection"))
//      .where(_.tag.nameExact("sanitization-point").valueExact("none"))
//      .l
//
// 2. Find high-impact buffer overflow risks:
//    cpg.call
//      .where(_.tag.nameExact("security-risk").valueExact("buffer-overflow"))
//      .where(_.tag.nameExact("risk-severity").valueExact("critical"))
//      .l
//
// 3. Surface unvalidated user input paths:
//    cpg.call
//      .where(_.tag.nameExact("trust-boundary").valueExact("user-input"))
//      .where(_.tag.nameExact("sanitization-point").valueExact("none"))
//      .l
//
// 4. Summarise risk distribution:
//    cpg.call.tag.name("security-risk").value.groupBy(identity).view.mapValues(_.size).toMap
//
// 5. Print critical incidents with file/line info:
//    cpg.call
//      .where(_.tag.nameExact("risk-severity").valueExact("critical"))
//      .map(c => (c.code, c.filename, c.lineNumber.getOrElse(0)))
//      .l
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.codepropertygraph.generated.{EdgeTypes, NodeTypes}
import flatgraph.DiffGraphBuilder

// ========================= Config =========================
val APPLY_TAGS = sys.props.getOrElse("security.apply", "true").toBoolean
val STRICT_MODE = sys.props.getOrElse("security.strict", "false").toBoolean

println(s"[*] Apply tags: $APPLY_TAGS")
println(s"[*] Strict mode: $STRICT_MODE")

// ========================= Security Patterns =========================

// Dangerous functions and their risks
val DANGEROUS_FUNCTIONS = Map(
  // Buffer overflow risks
  "strcpy" -> ("buffer-overflow", "critical"),
  "strcat" -> ("buffer-overflow", "critical"),
  "sprintf" -> ("buffer-overflow", "critical"),
  "vsprintf" -> ("buffer-overflow", "critical"),
  "gets" -> ("buffer-overflow", "critical"),
  "scanf" -> ("buffer-overflow", "high"),
  "memcpy" -> ("buffer-overflow", "high"),

  // Format string vulnerabilities
  "printf" -> ("format-string", "medium"),
  "fprintf" -> ("format-string", "medium"),
  "snprintf" -> ("format-string", "low"),

  // SQL injection risks (PostgreSQL specific)
  "SPI_exec" -> ("sql-injection", "critical"),
  "SPI_execute" -> ("sql-injection", "critical"),
  "SPI_execute_plan" -> ("sql-injection", "high"),

  // Path traversal
  "open" -> ("path-traversal", "high"),
  "fopen" -> ("path-traversal", "high"),
  "stat" -> ("path-traversal", "medium"),
  "access" -> ("path-traversal", "medium"),

  // Command injection
  "system" -> ("command-injection", "critical"),
  "popen" -> ("command-injection", "critical"),
  "exec" -> ("command-injection", "critical")
)

// Validation and sanitization helpers
val SANITIZATION_FUNCTIONS = Set(
  "quote_identifier",
  "quote_literal",
  "escape_string",
  "pg_strncpy",
  "strlcpy",
  "pqCheckOutBufferSpace",
  "check_stack_depth",
  "CheckTableNotInUse"
)

// User input sources (trust boundaries)
val USER_INPUT_FUNCTIONS = Set(
  "PQgetvalue",
  "recv",
  "recvfrom",
  "read",
  "fgets",
  "getenv",
  "PG_GETARG",
  "fcinfo"
)

// ========================= Analysis Functions =========================

def detectSecurityRisk(call: Call): Option[(String, String)] = {
  val callName = call.name
  DANGEROUS_FUNCTIONS.get(callName)
}

def detectTrustBoundary(call: Call): Option[String] = {
  val callName = call.name

  if (USER_INPUT_FUNCTIONS.exists(callName.contains(_))) {
    Some("user-input")
  } else if (callName.contains("recv") || callName.contains("socket")) {
    Some("network-input")
  } else if (callName.contains("fopen") || callName.contains("read") || callName.contains("File")) {
    Some("file-input")
  } else {
    None
  }
}

def detectSanitization(call: Call): String = {
  val callName = call.name

  if (SANITIZATION_FUNCTIONS.contains(callName)) {
    "validated"
  } else if (callName.contains("escape") || callName.contains("quote")) {
    "escaped"
  } else if (callName.contains("check") || callName.contains("validate")) {
    "sanitized"
  } else {
    "none"
  }
}

def detectPrivilegeLevel(method: Method): String = {
  val code = method.code.toLowerCase
  val name = method.name.toLowerCase

  if (name.contains("superuser") || code.contains("superuser_arg")) {
    "admin"
  } else if (name.contains("owner") || code.contains("pg_class_ownercheck")) {
    "user"
  } else {
    "unrestricted"
  }
}

// Trace data flow to verify sanitization between source and sink
def hasValidationBetween(source: Call, sink: Call): Boolean = {
  try {
  // Simple heuristic: check whether a sanitisation helper appears between source and sink
    val sourceLineOpt = source.lineNumber
    val sinkLineOpt = sink.lineNumber

    (sourceLineOpt, sinkLineOpt) match {
      case (Some(sourceLine), Some(sinkLine)) =>
        // Look for sanitisation calls between the two line numbers
        val sourceFileName = source.file.name.headOption
        sourceFileName match {
          case Some(fileName) =>
            val betweenCalls = cpg.call
              .where(_.file.nameExact(fileName))
              .where(_.lineNumber.filter(l => l > sourceLine && l < sinkLine))
              .name.l

            betweenCalls.exists(name => SANITIZATION_FUNCTIONS.contains(name) ||
                                         name.contains("check") ||
                                         name.contains("validate"))
          case None => false
        }
      case _ => false
    }
  } catch {
    case _: Throwable => false
  }
}

// ========================= Graph modification =========================

def applySecurityTags(): Unit = {
  val diff = DiffGraphBuilder(cpg.graph.schema)
  var tagged = 0
  var risksFound = 0

  println("[*] Analyzing security patterns...")

  // Analyze function calls
  val calls = cpg.call.l

  println(s"[*] Found ${calls.size} calls")
  println("[*] Detecting security risks...")

  calls.foreach { call =>
    var hasRisk = false

    // Flag security risks
    detectSecurityRisk(call).foreach { case (riskType, severity) =>
      hasRisk = true
      risksFound += 1

      val tagRisk = NewTag()
        .name("security-risk")
        .value(riskType)

      val tagSeverity = NewTag()
        .name("risk-severity")
        .value(severity)

      diff.addNode(tagRisk)
      diff.addNode(tagSeverity)
      diff.addEdge(call, tagRisk, EdgeTypes.TAGGED_BY)
      diff.addEdge(call, tagSeverity, EdgeTypes.TAGGED_BY)

      // Check for sanitization
      val sanitization = detectSanitization(call)
      val tagSanitization = NewTag()
        .name("sanitization-point")
        .value(sanitization)

      diff.addNode(tagSanitization)
      diff.addEdge(call, tagSanitization, EdgeTypes.TAGGED_BY)
    }

    // Flag trust boundary crossings
    detectTrustBoundary(call).foreach { boundary =>
      val tagBoundary = NewTag()
        .name("trust-boundary")
        .value(boundary)

      diff.addNode(tagBoundary)
      diff.addEdge(call, tagBoundary, EdgeTypes.TAGGED_BY)

      hasRisk = true
    }

    if (hasRisk) {
      tagged += 1

      if (tagged % 100 == 0) {
        println(s"[*] Processed $tagged security-relevant calls...")
      }
    }
  }

  // Analyze methods by privilege level
  println("[*] Analyzing privilege levels...")
  var methodsTagged = 0

  cpg.method.l.foreach { method =>
    val privLevel = detectPrivilegeLevel(method)

    if (privLevel != "unrestricted") {
      val tagPriv = NewTag()
        .name("privilege-level")
        .value(privLevel)

      diff.addNode(tagPriv)
      diff.addEdge(method, tagPriv, EdgeTypes.TAGGED_BY)
      methodsTagged += 1
    }
  }

  println(s"[*] Applying tags to graph...")
  flatgraph.DiffGraphApplier.applyDiff(cpg.graph, diff)

  println(s"[+] Tagged $tagged calls with security information")
  println(s"[+] Tagged $methodsTagged methods with privilege information")
  println(s"[+] Found $risksFound security risks")

  // Statistics
  println("\n[*] Security Risk Statistics:")
  val riskStats = cpg.call.tag.name("security-risk").value.l.groupBy(identity).view.mapValues(_.size).toMap
  riskStats.toList.sortBy(-_._2).foreach { case (risk, count) =>
    println(f"    $risk%-25s: $count%5d")
  }

  val criticalRisks = cpg.call
    .where(_.tag.nameExact("risk-severity").valueExact("critical"))
    .where(_.tag.nameExact("sanitization-point").valueExact("none"))
    .size

  println(f"\n[!] Critical unsanitized risks: $criticalRisks")
}

// ========================= Initialization =========================

if (APPLY_TAGS) {
  applySecurityTags()
  println("\n[*] Query examples:")
  println("""    cpg.call.where(_.tag.nameExact("security-risk").valueExact("sql-injection")).code.l""")
  println("""    cpg.call.where(_.tag.nameExact("risk-severity").valueExact("critical")).l.size""")
  println("""    cpg.call.tag.name("security-risk").value.groupBy(identity).view.mapValues(_.size).toMap""")
} else {
  println("[*] Tag application disabled. Set -Dsecurity.apply=true to enable")
}

