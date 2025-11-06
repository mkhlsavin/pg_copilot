// test_cpg_capabilities.sc - Test what CPG capabilities are available
// Launch: :load test_cpg_capabilities.sc

println("=" * 80)
println("CPG CAPABILITIES TEST")
println("=" * 80)

// Test 1: Basic CPG Stats
println("\n=== 1. BASIC CPG STATS ===")
println(s"Total methods: ${cpg.method.size}")
println(s"Total files: ${cpg.file.size}")
println(s"Total calls: ${cpg.call.size}")
println(s"Total types: ${cpg.typeDecl.size}")

// Test 2: Comments
println("\n=== 2. COMMENT NODES ===")
try {
  val commentCount = cpg.comment.size
  println(s"Total comment nodes: ${commentCount}")

  val methodsWithComments = cpg.method.filter(_._astOut.collectAll[Comment].nonEmpty).size
  println(s"Methods with comments: ${methodsWithComments}")

  if (methodsWithComments > 0) {
    println("\nExample method with comment:")
    cpg.method.filter(_._astOut.collectAll[Comment].nonEmpty).l.headOption.foreach { m =>
      println(s"  Method: ${m.name} (${m.filename}:${m.lineNumber.getOrElse(0)})")
      val comments = m._astOut.collectAll[Comment].code.l
      comments.take(3).foreach { c =>
        println(s"  Comment: ${c.take(100)}...")
      }
    }
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
      println(s"CFG first nodes: ${m.cfgNode.code.l.take(3).mkString(", ")}")

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

// Test 4: Data Flow
println("\n=== 4. DATA FLOW ===")
try {
  val testMethod = cpg.method.name(".*ReadBuffer.*|.*lock.*").filter(_.parameter.nonEmpty).headOption
  testMethod match {
    case Some(m) =>
      println(s"Test method: ${m.name}")
      val params = m.parameter.l
      println(s"Parameters: ${params.size}")

      if (params.nonEmpty) {
        val p = params.head
        println(s"  First parameter: ${p.name} (${p.typeFullName})")

        // Test reachability
        val reachable = p.reachableBy(m.ast).size
        println(s"  Reachable nodes: ${reachable}")

        // Test if we can find uses
        val uses = m.ast.isIdentifier.filter(_.name == p.name).l
        println(s"  Uses of parameter: ${uses.size}")
      }
    case None =>
      println("  No suitable test method found")
  }
} catch {
  case e: Exception => println(s"  ERROR: ${e.getMessage}")
}

// Test 5: Call Graph
println("\n=== 5. CALL GRAPH ===")
try {
  val testMethod = cpg.method.name(".*ReadBuffer.*|.*malloc.*").headOption
  testMethod match {
    case Some(m) =>
      println(s"Test method: ${m.name}")

      // Calls made by this method
      val callsMade = m.call.name.l.take(5)
      println(s"Calls made: ${callsMade.size} (showing ${callsMade.take(5).mkString(", ")})")

      // Methods that call this method
      val callers = m.caller.name.l.take(5)
      println(s"Called by: ${callers.size} methods (showing ${callers.take(3).mkString(", ")})")
    case None =>
      println("  No suitable test method found")
  }
} catch {
  case e: Exception => println(s"  ERROR: ${e.getMessage}")
}

// Test 6: Tags
println("\n=== 6. TAGS ===")
try {
  val taggedMethods = cpg.method.filter(_.tag.nonEmpty).size
  println(s"Methods with tags: ${taggedMethods}")

  if (taggedMethods > 0) {
    println("\nExample tagged method:")
    cpg.method.filter(_.tag.nonEmpty).l.headOption.foreach { m =>
      println(s"  Method: ${m.name}")
      m.tag.l.take(3).foreach { t =>
        println(s"    Tag: ${t.name} = ${t.value}")
      }
    }
  }

  // Count tags by name
  val tagNames = cpg.tag.name.l.distinct
  println(s"\nUnique tag names: ${tagNames.size}")
  tagNames.take(10).foreach { name =>
    val count = cpg.tag.name(name).size
    println(s"  ${name}: ${count}")
  }
} catch {
  case e: Exception => println(s"  ERROR: ${e.getMessage}")
}

// Test 7: Try to access DDG/PDG if available
println("\n=== 7. ADVANCED GRAPHS (DDG/PDG) ===")
try {
  val testMethod = cpg.method.name(".*ReadBuffer.*").headOption
  testMethod match {
    case Some(m) =>
      println(s"Test method: ${m.name}")

      // Try various traversals
      try {
        println("  Testing .ddg...")
        val ddgSize = m.ddg.size
        println(s"    DDG size: ${ddgSize}")
      } catch {
        case e: Exception => println(s"    DDG not available: ${e.getMessage.take(50)}")
      }

      try {
        println("  Testing .pdg...")
        val pdgSize = m.pdg.size
        println(s"    PDG size: ${pdgSize}")
      } catch {
        case e: Exception => println(s"    PDG not available: ${e.getMessage.take(50)}")
      }

      try {
        println("  Testing .cdg...")
        val cdgSize = m.cdg.size
        println(s"    CDG size: ${cdgSize}")
      } catch {
        case e: Exception => println(s"    CDG not available: ${e.getMessage.take(50)}")
      }
    case None =>
      println("  No suitable test method found")
  }
} catch {
  case e: Exception => println(s"  ERROR: ${e.getMessage}")
}

// Test 8: Method Return Flow
println("\n=== 8. METHOD RETURN FLOW ===")
try {
  val testMethod = cpg.method.name(".*ReadBuffer.*").filter(_.methodReturn.nonEmpty).headOption
  testMethod match {
    case Some(m) =>
      println(s"Test method: ${m.name}")
      println(s"Return type: ${m.methodReturn.typeFullName.headOption.getOrElse("void")}")

      // Try to find flow to return
      val returns = m.ast.isReturn.l
      println(s"Return statements: ${returns.size}")

      if (returns.nonEmpty) {
        println(s"  Example return: ${returns.head.code.take(50)}")
      }
    case None =>
      println("  No suitable test method found")
  }
} catch {
  case e: Exception => println(s"  ERROR: ${e.getMessage}")
}

println("\n" + "=" * 80)
println("TEST COMPLETE")
println("=" * 80)
