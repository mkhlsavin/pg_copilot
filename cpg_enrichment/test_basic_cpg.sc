// test_basic_cpg.sc - Test what basic CPG capabilities are available
// Launch: :load test_basic_cpg.sc

println("=" * 80)
println("BASIC CPG CAPABILITIES TEST")
println("=" * 80)

// Test 1: Basic CPG Stats
println("\n=== 1. BASIC CPG STATS ===")
println(s"Total methods: ${cpg.method.size}")
println(s"Total files: ${cpg.file.size}")
println(s"Total calls: ${cpg.call.size}")
println(s"Total types: ${cpg.typeDecl.size}")
println(s"Total identifiers: ${cpg.identifier.size}")
println(s"Total literals: ${cpg.literal.size}")

// Test 2: AST Traversal
println("\n=== 2. AST TRAVERSAL ===")
try {
  val testMethod = cpg.method.name(".*ReadBuffer.*").headOption
  testMethod match {
    case Some(m) =>
      println(s"Test method: ${m.name}")
      println(s"AST nodes: ${m.ast.size}")
      println(s"Parameters: ${m.parameter.size}")
      println(s"Local variables: ${m.local.size}")
    case None =>
      println("  No suitable test method found")
  }
} catch {
  case e: Exception => println(s"  ERROR: ${e.getMessage}")
}

// Test 3: CFG (Control Flow Graph)
println("\n=== 3. CONTROL FLOW GRAPH ===")
try {
  val testMethod = cpg.method.name(".*ReadBuffer.*|.*CommitTransaction.*").headOption
  testMethod match {
    case Some(m) =>
      println(s"Test method: ${m.name}")
      println(s"CFG nodes: ${m.cfgNode.size}")

      // Get first few CFG nodes
      val cfgSample = m.cfgNode.code.l.take(3)
      println(s"First CFG nodes: ${cfgSample.mkString(", ")}")

      // Test control structures
      val ctrlStructs = m.controlStructure.l
      println(s"Control structures: ${ctrlStructs.size}")
      if (ctrlStructs.nonEmpty) {
        println(s"  Example: ${ctrlStructs.head.controlStructureType} at line ${ctrlStructs.head.lineNumber.getOrElse(0)}")
      }
    case None =>
      println("  No suitable test method found")
  }
} catch {
  case e: Exception => println(s"  ERROR: ${e.getMessage}")
}

// Test 4: Call Sites
println("\n=== 4. CALL SITES ===")
try {
  val testMethod = cpg.method.name(".*ReadBuffer.*|.*malloc.*").headOption
  testMethod match {
    case Some(m) =>
      println(s"Test method: ${m.name}")

      // Calls made by this method
      val callsMade = m.call.name.l.take(10)
      println(s"Calls made: ${callsMade.size} total (showing first 10)")
      callsMade.foreach(c => println(s"  - ${c}"))
    case None =>
      println("  No suitable test method found")
  }
} catch {
  case e: Exception => println(s"  ERROR: ${e.getMessage}")
}

// Test 5: Tags (our enrichment)
println("\n=== 5. TAGS (ENRICHMENT) ===")
try {
  val taggedMethods = cpg.method.filter(_.tag.nonEmpty).size
  println(s"Methods with tags: ${taggedMethods}")

  if (taggedMethods > 0) {
    println("\nExample tagged method:")
    cpg.method.filter(_.tag.nonEmpty).l.headOption.foreach { m =>
      println(s"  Method: ${m.name}")
      m.tag.l.take(5).foreach { t =>
        println(s"    Tag: ${t.name} = ${t.value}")
      }
    }
  }

  // Count tags by name
  val tagNames = cpg.tag.name.l.distinct
  println(s"\nUnique tag names: ${tagNames.size}")
  tagNames.sorted.take(15).foreach { name =>
    val count = cpg.tag.name(name).size
    println(s"  ${name}: ${count}")
  }
} catch {
  case e: Exception => println(s"  ERROR: ${e.getMessage}")
}

// Test 6: Method Metadata
println("\n=== 6. METHOD METADATA ===")
try {
  val testMethod = cpg.method.name(".*ReadBuffer.*").headOption
  testMethod match {
    case Some(m) =>
      println(s"Method: ${m.name}")
      println(s"  File: ${m.filename}")
      println(s"  Line: ${m.lineNumber.getOrElse(0)}")
      println(s"  Signature: ${m.signature}")
      println(s"  Full name: ${m.fullName}")
      println(s"  Return type: ${m.methodReturn.typeFullName.headOption.getOrElse("void")}")
    case None =>
      println("  No suitable test method found")
  }
} catch {
  case e: Exception => println(s"  ERROR: ${e.getMessage}")
}

// Test 7: Return Statements
println("\n=== 7. RETURN STATEMENTS ===")
try {
  val testMethod = cpg.method.name(".*ReadBuffer.*").filter(_.methodReturn.nonEmpty).headOption
  testMethod match {
    case Some(m) =>
      println(s"Method: ${m.name}")
      val returns = m.ast.isReturn.l
      println(s"Return statements: ${returns.size}")

      if (returns.nonEmpty) {
        println("  Examples:")
        returns.take(3).foreach { r =>
          println(s"    ${r.code.take(60)}")
        }
      }
    case None =>
      println("  No suitable test method found")
  }
} catch {
  case e: Exception => println(s"  ERROR: ${e.getMessage}")
}

// Test 8: Check if enrichment scripts are loaded
println("\n=== 8. AVAILABLE ENRICHMENT METHODS ===")
try {
  // Try to check what custom traversals might be available
  println("Checking for custom traversals...")

  // Check if we can access method bodies
  val methodWithBody = cpg.method.name(".*ReadBuffer.*").headOption
  methodWithBody.foreach { m =>
    println(s"Method ${m.name}:")
    println(s"  Has body: ${m.block.size > 0}")
    println(s"  Statements: ${m.ast.isExpression.size}")
  }
} catch {
  case e: Exception => println(s"  ERROR: ${e.getMessage}")
}

println("\n" + "=" * 80)
println("BASIC CPG TEST COMPLETE")
println("=" * 80)
