// performance_hotspots.sc — Performance hotspot detection
// Запуск: :load performance_hotspots.sc
//
// Теги: `perf-hotspot`, `allocation-heavy`, `io-bound`, `loop-depth`, `expensive-op`
// ПРИМЕРЫ: cpg.method.where(_.tag.nameExact("perf-hotspot").valueExact("hot")).name.l

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.codepropertygraph.generated.EdgeTypes
import flatgraph.DiffGraphBuilder

val APPLY = sys.props.getOrElse("perf.apply", "true").toBoolean

val ALLOC_FUNCS = Set("palloc", "malloc", "MemoryContextAlloc", "repalloc")
val IO_FUNCS = Set("read", "write", "fread", "fwrite", "fsync", "ReadBuffer", "WriteBuffer")
val SYNC_FUNCS = Set("LWLockAcquire", "LWLockRelease", "SpinLockAcquire", "pthread_mutex_lock")

def countLoopDepth(m: Method): Int = {
  try {
    // Подсчёт вложенности циклов
    val loops = m.ast.isControlStructure.controlStructureType("(FOR|WHILE|DO).*").l
    if (loops.isEmpty) 0 else loops.map(_.depth).max
  } catch {
    case _: Throwable => 0
  }
}

def isAllocationHeavy(m: Method): Boolean = {
  try {
    val allocCalls = m.ast.isCall.name.l.count(ALLOC_FUNCS.contains)
    allocCalls > 5
  } catch {
    case _: Throwable => false
  }
}

def isIOBound(m: Method): Boolean = {
  try {
    m.ast.isCall.name.l.exists(IO_FUNCS.contains)
  } catch {
    case _: Throwable => false
  }
}

def detectExpensiveOps(m: Method): List[String] = {
  var ops = List.empty[String]
  try {
    val calls = m.ast.isCall.name.l
    if (calls.exists(ALLOC_FUNCS.contains)) ops = ops :+ "memory-alloc"
    if (calls.exists(IO_FUNCS.contains)) ops = ops :+ "io"
    if (calls.exists(SYNC_FUNCS.contains)) ops = ops :+ "sync-lock"
  } catch {
    case _: Throwable =>
  }
  ops
}

def classifyHotspot(loopDepth: Int, isAlloc: Boolean, isIO: Boolean): String = {
  if (loopDepth >= 3 || (loopDepth >= 2 && (isAlloc || isIO))) "hot"
  else if (loopDepth >= 2 || isAlloc || isIO) "warm"
  else "cold"
}

def applyPerformanceTags(): Unit = {
  val diff = DiffGraphBuilder(cpg.graph.schema)
  var tagged = 0

  println("[*] Analyzing performance patterns...")

  cpg.method.l.foreach { method =>
    val loopDepth = countLoopDepth(method)
    val allocHeavy = isAllocationHeavy(method)
    val ioBound = isIOBound(method)
    val expensiveOps = detectExpensiveOps(method)
    val hotspot = classifyHotspot(loopDepth, allocHeavy, ioBound)

    if (loopDepth > 0 || allocHeavy || ioBound || hotspot != "cold") {
      val tagHotspot = NewTag().name("perf-hotspot").value(hotspot)
      val tagLoop = NewTag().name("loop-depth").value(loopDepth.toString)

      diff.addNode(tagHotspot)
      diff.addNode(tagLoop)
      diff.addEdge(method, tagHotspot, EdgeTypes.TAGGED_BY)
      diff.addEdge(method, tagLoop, EdgeTypes.TAGGED_BY)

      if (allocHeavy) {
        val tagAlloc = NewTag().name("allocation-heavy").value("true")
        diff.addNode(tagAlloc)
        diff.addEdge(method, tagAlloc, EdgeTypes.TAGGED_BY)
      }

      if (ioBound) {
        val tagIO = NewTag().name("io-bound").value("true")
        diff.addNode(tagIO)
        diff.addEdge(method, tagIO, EdgeTypes.TAGGED_BY)
      }

      expensiveOps.foreach { op =>
        val tagOp = NewTag().name("expensive-op").value(op)
        diff.addNode(tagOp)
        diff.addEdge(method, tagOp, EdgeTypes.TAGGED_BY)
      }

      tagged += 1
      if (tagged % 500 == 0) println(s"[*] Processed $tagged methods...")
    }
  }

  flatgraph.DiffGraphApplier.applyDiff(cpg.graph, diff)
  println(s"[+] Tagged $tagged methods")

  val hotPaths = cpg.method.where(_.tag.nameExact("perf-hotspot").valueExact("hot")).size
  println(f"[*] Hot paths found: $hotPaths")
}

if (APPLY) applyPerformanceTags()
