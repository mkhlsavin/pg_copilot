// ast_comments.sc — привязка комментариев ко всем ключевым AST-узлам (включая FILE).
// Запуск: :load ast_comments.sc
//
// ВАЖНО: скрипт МОДИФИЦИРУЕТ граф (добавляет COMMENT-ноды с AST-ребром к владельцу)
//
// ============================================================================
// НАСТРОЙКА
// ============================================================================
// Через системные свойства (опционально):
//   -Dplanner.glob=".*(optimizer|plan).*\\.c"  фильтр файлов (regex), по умолчанию ".*"
//   -Dplanner.maxdist=32                       глубина fallback-поиска блока вверх
//   -Dplanner.limit=0                          лимит узлов (0 = без лимита)
//
// ============================================================================
// ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ (после выполнения скрипта)
// ============================================================================
//
// 1. Общая статистика комментариев:
//    cpg.comment.size
//
// 2. Статистика по типам узлов с комментариями:
//    Map(
//      "FILE" -> cpg.file.filter(_._astOut.collectAll[Comment].nonEmpty).size,
//      "METHOD" -> cpg.method.filter(_._astOut.collectAll[Comment].nonEmpty).size,
//      "CALL" -> cpg.call.filter(_._astOut.collectAll[Comment].nonEmpty).size,
//      "CONTROL_STRUCTURE" -> cpg.controlStructure.filter(_._astOut.collectAll[Comment].nonEmpty).size,
//      "TYPE_DECL" -> cpg.typeDecl.filter(_._astOut.collectAll[Comment].nonEmpty).size,
//      "LOCAL" -> cpg.local.filter(_._astOut.collectAll[Comment].nonEmpty).size,
//      "RETURN" -> cpg.ret.filter(_._astOut.collectAll[Comment].nonEmpty).size
//    )
//
// 3. Показать FILE-комментарий (заголовок файла):
//    cpg.file.name(".*createplan\\.c").l.headOption.foreach { f =>
//      println(s"File: ${f.name}")
//      f._astOut.collectAll[Comment].code.l.foreach(println)
//    }
//
// 4. Показать 3 метода с их комментариями:
//    cpg.method.filter(_._astOut.collectAll[Comment].nonEmpty).l.take(3).foreach { m =>
//      println(s"\n=== Method: ${m.name} (${m.filename}:${m.lineNumber.getOrElse(0)}) ===")
//      m._astOut.collectAll[Comment].code.l.foreach(c => println(s"${c.take(150)}..."))
//    }
//
// 5. Показать 3 вызова (CALL) с их комментариями:
//    cpg.call.filter(_._astOut.collectAll[Comment].nonEmpty).l.take(3).foreach { c =>
//      println(s"\n=== Call: ${c.code.take(50)} (${c.filename}:${c.lineNumber.getOrElse(0)}) ===")
//      c._astOut.collectAll[Comment].code.l.foreach(cm => println(s"${cm.take(150)}..."))
//    }
//
// 6. Показать CONTROL_STRUCTURE с комментариями:
//    cpg.controlStructure.filter(_._astOut.collectAll[Comment].nonEmpty).l.take(3).foreach { cs =>
//      println(s"\n=== CS: ${cs.code.take(30)} (${cs.filename}:${cs.lineNumber.getOrElse(0)}) ===")
//      cs._astOut.collectAll[Comment].code.l.foreach(println)
//    }
//
// 7. Найти комментарий для конкретного метода:
//    cpg.method.name("planner").l.headOption.foreach { m =>
//      println(s"Method: ${m.name}")
//      m._astOut.collectAll[Comment].code.l.foreach(println)
//    }
//
// 8. Найти комментарий для конкретного вызова:
//    cpg.call.code(".*GetForeignRelSize.*").l.headOption.foreach { c =>
//      println(s"Call: ${c.code}")
//      c._astOut.collectAll[Comment].code.l.foreach(println)
//    }
//
// 9. Показать все комментарии в файле:
//    cpg.file.name(".*createplan\\.c").ast.collectAll[Comment].code.l.take(10).foreach(println)
//
// 10. RETURN узлы с комментариями:
//     cpg.ret.filter(_._astOut.collectAll[Comment].nonEmpty).l.take(3).foreach { r =>
//       println(s"\n=== Return at ${r.filename}:${r.lineNumber.getOrElse(0)} ===")
//       r._astOut.collectAll[Comment].code.l.foreach(println)
//     }
//
// ПРИМЕЧАНИЕ:
// - Используйте _._astOut для ПРЯМЫХ дочерних комментариев узла
// - Используйте .ast для ВСЕХ комментариев в поддереве узла
// ============================================================================

import java.util.regex.Pattern
import scala.util.Try
import scala.util.matching.Regex

import io.shiftleft.semanticcpg.language._
import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.codepropertygraph.generated.{EdgeTypes, NodeTypes, PropertyNames}
import flatgraph.DiffGraphBuilder
import io.shiftleft.codepropertygraph.generated.nodes.NewComment

// ========================= Config =========================
val FILE_GLOB       = sys.props.getOrElse("planner.glob", """.*""")
val MAX_FALLBACK    = Try(sys.props.get("planner.maxdist").map(_.toInt).getOrElse(32)).getOrElse(32)
val LIMIT_ROWS: Int = Try(sys.props.get("planner.limit").map(_.toInt).getOrElse(0)).getOrElse(0)
def limit[A](xs: Iterable[A]): Iterable[A] = if (LIMIT_ROWS > 0) xs.take(LIMIT_ROWS) else xs

// ========================= Small utils =========================
def fileOf(n: StoredNode): String =
  n.file.name.headOption.getOrElse("")

def lineOf(n: StoredNode): Int = n match {
  case x: Method            => x.lineNumber.getOrElse(Int.MaxValue)
  case x: ControlStructure  => x.lineNumber.getOrElse(Int.MaxValue)
  case x: Block             => x.lineNumber.getOrElse(Int.MaxValue)
  case x: Call              => x.lineNumber.getOrElse(Int.MaxValue)
  case x: TypeDecl          => x.lineNumber.getOrElse(Int.MaxValue)
  case x: Local             => x.lineNumber.getOrElse(Int.MaxValue)
  case x: Member            => x.lineNumber.getOrElse(Int.MaxValue)
  case x: MethodParameterIn => x.lineNumber.getOrElse(Int.MaxValue)
  case x: Return            => x.lineNumber.getOrElse(Int.MaxValue)
  case x: File              => 1
  case _                    => Int.MaxValue
}

// ---------- FILE content (cache) ----------
val fileCache = scala.collection.mutable.Map.empty[String, Array[String]]
val csEndCache = scala.collection.mutable.Map.empty[(String, Int), Int]
def quoteRe(lit: String): String = Pattern.quote(lit)
def toUnix(p: String): String = p.replace('\\', '/')

def fileLines(filename: String): Option[Array[String]] = {
  fileCache.get(filename).orElse {
    def get(name: String) = cpg.file.name(name).content.headOption.map(_.split("\n", -1))
    val exact  = get(quoteRe(filename))
    val unix   = if (exact.isEmpty) get(quoteRe(toUnix(filename))) else exact
    val tail   = if (unix.isEmpty)  get(".*" + quoteRe(filename) + "$") else unix
    val last   = if (tail.isEmpty)  get(".*" + quoteRe(toUnix(filename)) + "$") else tail
    last.foreach(arr => fileCache.update(filename, arr))
    last
  }
}

case class CommentSpan(start: Int, end: Int, text: String)

// ===== Комментарии: same-scope / tight-above / fallback / inside-after-brace =====
def isSkippable(s: String): Boolean = {
  val t = s.trim; t.isEmpty || t == "{" || t == "}"
}

def sameScope(lines: Array[String], fromIdx0: Int, anchorLine: Int): Boolean = {
  if (lines.isEmpty || fromIdx0 >= lines.length) return true
  var bal = 0
  var k = fromIdx0 + 1
  val last = math.min(anchorLine - 2, lines.length - 1)
  while (k <= last && k < lines.length) {
    val s = lines(k)
    bal += s.count(_ == '{')
    bal -= s.count(_ == '}')
    if (bal < 0) return false
    k += 1
  }
  true
}

def tightCommentAbove(lines: Array[String], anchorLine: Int): Option[CommentSpan] = {
  if (anchorLine <= 1 || lines.isEmpty) return None
  val maxIdx = lines.length - 1
  var i = math.min(anchorLine - 2, maxIdx)
  while (i >= 0 && i < lines.length && isSkippable(lines(i))) i -= 1
  if (i < 0 || i >= lines.length) return None

  if (lines(i).contains("*/")) {
    val end = i
    var start = i; var found = false
    while (start >= 0 && !found) { if (lines(start).contains("/*")) found = true else start -= 1 }
    if (!found) return None
    var k = end + 1; var tight = true
    val checkUntil = math.min(anchorLine - 2, maxIdx)
    while (tight && k <= checkUntil && k < lines.length) {
      if (!isSkippable(lines(k))) tight = false
      k += 1
    }
    if (tight && sameScope(lines, end, anchorLine))
      Some(CommentSpan(start + 1, end + 1, lines.slice(start, end + 1).mkString("\n")))
    else None
  } else {
    val buf = scala.collection.mutable.ArrayBuffer[String]()
    var j = i
    while (j >= 0 && j < lines.length && lines(j).trim.startsWith("//")) { buf.prepend(lines(j)); j -= 1 }
    if (buf.isEmpty) None
    else {
      val end = i; var k = end + 1; var tight = true
      val checkUntil = math.min(anchorLine - 2, maxIdx)
      while (tight && k <= checkUntil && k < lines.length) {
        if (!isSkippable(lines(k))) tight = false
        k += 1
      }
      if (tight && sameScope(lines, end, anchorLine))
        Some(CommentSpan(j + 2, end + 1, buf.mkString("\n")))
      else None
    }
  }
}

def fallbackNearestBlockSameScope(lines: Array[String], anchorLine: Int, maxDistance: Int): Option[CommentSpan] = {
  if (anchorLine <= 1 || lines.isEmpty) return None
  var i = math.min(anchorLine - 2, lines.length - 1)
  var scanned = 0
  while (i >= 0 && i < lines.length && scanned <= maxDistance) {
    val s = lines(i)
    if (s.contains("*/")) {
      val end = i
      var start = i; var found = false
      while (start >= 0 && start < lines.length && !found && scanned <= maxDistance) {
        if (lines(start).contains("/*")) found = true else { start -= 1; scanned += 1 }
      }
      if (found && sameScope(lines, end, anchorLine)) {
        return Some(CommentSpan(start + 1, end + 1, lines.slice(start, end + 1).mkString("\n")))
      }
    }
    i -= 1; scanned += 1
  }
  None
}

def topHeaderComment(lines: Array[String]): Option[CommentSpan] = {
  if (lines.isEmpty) return None
  var i = 0
  while (i < lines.length && lines(i).trim.isEmpty) i += 1
  if (i >= lines.length) return None
  if (lines(i).trim.startsWith("/*")) {
    val start = i
    while (i < lines.length && !lines(i).contains("*/")) i += 1
    if (i < lines.length) Some(CommentSpan(start + 1, i + 1, lines.slice(start, i + 1).mkString("\n"))) else None
  } else if (lines(i).trim.startsWith("//")) {
    val start = i
    while (i < lines.length && lines(i).trim.startsWith("//")) i += 1
    Some(CommentSpan(start + 1, i, lines.slice(start, i).mkString("\n")))
  } else None
}

// после «{» — первый комментарий до кода
def findBraceLine(lines: Array[String], startLine: Int): Option[Int] = {
  if (lines.isEmpty) return None
  val startIdx = math.max(0, startLine - 1)
  var i = startIdx; var look = 0
  while (i < lines.length && look <= 4) { if (lines(i).contains("{")) return Some(i); i += 1; look += 1 }
  None
}
def tightInsideAfterBrace(lines: Array[String], startLine: Int): Option[CommentSpan] = {
  if (lines.isEmpty) return None
  findBraceLine(lines, startLine).flatMap { braceLine =>
    var i = math.min(braceLine, lines.length - 1)
    while (i < lines.length && isSkippable(lines(i))) i += 1
    if (i >= lines.length) None
    else if (lines(i).trim.startsWith("/*")) {
      val s = i
      while (i < lines.length && !lines(i).contains("*/")) i += 1
      if (i < lines.length) Some(CommentSpan(s + 1, i + 1, lines.slice(s, i + 1).mkString("\n"))) else None
    } else if (lines(i).trim.startsWith("//")) {
      val s = i
      while (i < lines.length && lines(i).trim.startsWith("//")) i += 1
      Some(CommentSpan(s + 1, i, lines.slice(s, i).mkString("\n")))
    } else None
  }
}

// ===== CALL helpers =====
def recvName(c: Call): Option[String] = {
  val code = Option(c.code).getOrElse("")
  // Паттерн 1: var->method(...)
  val r1 = """([A-Za-z_]\w*)\s*->\s*\w+\s*\(""".r
  // Паттерн 2: (*var)(...)
  val r2 = """\(\*\s*([A-Za-z_]\w*)\s*\)\s*\(""".r

  r1.findFirstMatchIn(code).map(_.group(1))
    .orElse(r2.findFirstMatchIn(code).map(_.group(1)))
}
def findNearestAssignLine(lines: Array[String], callLine: Int, name: String): Option[Int] = {
  if (lines.isEmpty) return None
  val pattern = s"""\\b${Pattern.quote(name)}\\s*=\\s*.*?;""".r
  var i = math.min(callLine - 2, lines.length - 1)
  var checked = 0
  while (i >= 0 && i < lines.length && checked < 10) {
    val t = lines(i).trim
    if (t.nonEmpty) {
      checked += 1
      if (pattern.findFirstIn(lines(i)).isDefined) return Some(i + 1)
      if (!t.startsWith("//") && !t.contains("/*") && !t.contains("*/") && t != "{" && t != "}") return None
    }
    i -= 1
  }
  None
}
def isControlHead(s: String): Boolean = {
  val t = s.trim
  t.startsWith("if") || t.startsWith("else if") || t == "else" ||
  t.startsWith("for") || t.startsWith("while") || t.startsWith("do") ||
  t.startsWith("switch") || t.startsWith("return")
}
def isCodeLine(t: String): Boolean = {
  val s = t.trim
  s.nonEmpty && !s.startsWith("//") && !s.startsWith("/*") && !s.startsWith("*") && s != "{" && s != "}"
}
def prevNonCSStmt(lines: Array[String], line: Int): Option[Int] = {
  if (lines.isEmpty) return None
  var i = math.min(line - 2, lines.length - 1)
  while (i >= 0 && i < lines.length) { val t = lines(i); if (isCodeLine(t) && !isControlHead(t)) return Some(i + 1); i -= 1 }
  None
}
def prevStmt(lines: Array[String], line: Int): Option[Int] = {
  if (lines.isEmpty) return None
  var i = math.min(line - 2, lines.length - 1)
  while (i >= 0 && i < lines.length) { val t = lines(i); if (isCodeLine(t)) return Some(i + 1); i -= 1 }
  None
}
def estimateCsEnd(lines: Array[String], file: String, startLine: Int): Int = {
  csEndCache.getOrElseUpdate((file, startLine), {
    val n = lines.length
    if (n == 0) {
      startLine
    } else {
      val startIdx = math.max(0, startLine - 1)
      var i = startIdx; var br = -1; var look = 0
      while (i < n && look <= 4 && br == -1) { if (lines(i).contains("{")) br = i; i += 1; look += 1 }
      if (br == -1) {
        startLine
      } else {
        var bal = 0; var j = br
        var endLine = startLine
        while (j < n) {
          val s = lines(j)
          bal += s.count(_ == '{')
          bal -= s.count(_ == '}')
          if (bal == 0) {
            endLine = j + 1
            j = n // break
          } else {
            j += 1
          }
        }
        endLine
      }
    }
  })
}

// ========================= Anchors per node =========================
def anchorsForNode(n: StoredNode, lines: Array[String]): List[Int] = n match {
  case f: File =>
    val idx = lines.indexWhere(_.trim.nonEmpty)
    val anchor = if (idx == -1) 1 else idx + 1
    List(anchor)

  case m: Method =>
    List(lineOf(m))

  case cs: ControlStructure =>
    List(lineOf(cs))

  case b: Block =>
    List(lineOf(b))

  case c: Call =>
    val s = lineOf(c)
    val f = fileOf(c)
    val recv = recvName(c).flatMap(nm => findNearestAssignLine(lines, s, nm)).toList
    val prevN = prevNonCSStmt(lines, s).toList
    val csEnclosingStarts: List[Int] = {
      val all = Option(c.method).toList.flatMap(m => try m.controlStructure.toList catch { case _: Throwable => Nil })
        .filter(cs => fileOf(cs) == f && cs.lineNumber.exists(_ <= s))
      all.flatMap(_.lineNumber.flatMap { st =>
        val end = estimateCsEnd(lines, f, st); if (end >= s) Some(st) else None
      }).sorted(Ordering.Int.reverse)
    }
    val mStart = Option(c.method).flatMap(_.lineNumber).toList
    val pStmt  = prevStmt(lines, s).toList
    (List(s) ++ recv ++ prevN ++ csEnclosingStarts ++ mStart ++ pStmt).distinct

  case td: TypeDecl =>
    List(lineOf(td))

  case loc: Local =>
    List(lineOf(loc))

  case mem: Member =>
    List(lineOf(mem))

  case par: MethodParameterIn =>
    List(lineOf(par))

  case ret: Return =>
    List(lineOf(ret))

  case _ =>
    List(lineOf(n))
}

def pickCommentFor(n: StoredNode): Option[CommentSpan] = {
  val fname = fileOf(n)
  val linesOpt = fileLines(fname)
  linesOpt.flatMap { lines =>
    n match {
      case f: File =>
        topHeaderComment(lines)

      case m: Method =>
        val s = lineOf(m)
        tightCommentAbove(lines, s)
          .orElse(tightInsideAfterBrace(lines, s))
          .orElse(fallbackNearestBlockSameScope(lines, s, MAX_FALLBACK))

      case cs: ControlStructure =>
        val s = lineOf(cs)
        tightCommentAbove(lines, s)
          .orElse(tightInsideAfterBrace(lines, s))
          .orElse(fallbackNearestBlockSameScope(lines, s, MAX_FALLBACK))

      case b: Block =>
        val s = lineOf(b)
        tightCommentAbove(lines, s)
          .orElse(tightInsideAfterBrace(lines, s))
          .orElse(fallbackNearestBlockSameScope(lines, s, MAX_FALLBACK))

      case ret: Return =>
        val s = lineOf(ret)
        tightCommentAbove(lines, s)
          .orElse(fallbackNearestBlockSameScope(lines, s, MAX_FALLBACK))

      case _ =>
        val anchors = anchorsForNode(n, lines)
        anchors.iterator
          .map(a => tightCommentAbove(lines, a).orElse(fallbackNearestBlockSameScope(lines, a, MAX_FALLBACK)))
          .collectFirst { case Some(span) => span }
    }
  }
}

// ========================= Graph mutation =========================
def commentExistsForOwner(owner: StoredNode, span: CommentSpan): Boolean = {
  try {
    // Для flatgraph проверяем через _astOut
    val children = owner._astOut.toList
    children.exists {
      case c: Comment =>
        c.lineNumber.contains(span.start) && c.code == span.text
      case _ => false
    }
  } catch {
    case _: Throwable => false
  }
}

def attachComment(owner: StoredNode, span: CommentSpan, diff: DiffGraphBuilder): Unit = {
  val comment = NewComment()
    .code(span.text)
    .lineNumber(span.start)
    .columnNumber(-1)

  diff.addNode(comment)
  diff.addEdge(owner, comment, EdgeTypes.AST)
}

// ========================= Collect nodes & run =========================
println(s"[*] planner.glob  = $FILE_GLOB")
println(s"[*] max fallback  = $MAX_FALLBACK")
println(s"[*] limit         = ${if (LIMIT_ROWS>0) LIMIT_ROWS.toString else "no limit"}")

val files   = cpg.file.name(FILE_GLOB).toList
val methods = cpg.method.where(_.file.name(FILE_GLOB)).toList
val cs      = cpg.controlStructure.where(_.file.name(FILE_GLOB)).toList
val blocks  = cpg.block.where(_.file.name(FILE_GLOB)).toList
val calls   = cpg.call.where(_.file.name(FILE_GLOB)).toList
val tdecls  = cpg.typeDecl.where(_.file.name(FILE_GLOB)).toList
val locals  = cpg.local.where(_.file.name(FILE_GLOB)).toList
val params  = cpg.parameter.where(_.file.name(FILE_GLOB)).toList
val members = cpg.member.where(_.file.name(FILE_GLOB)).toList
val returns = cpg.ret.where(_.file.name(FILE_GLOB)).toList

val allNodes: List[StoredNode] =
  (limit(files) ++
   limit(methods) ++
   limit(cs) ++
   limit(blocks) ++
   limit(calls) ++
   limit(tdecls) ++
   limit(locals) ++
   limit(params) ++
   limit(members) ++
   limit(returns)).toList

println(f"[*] Candidates: ${allNodes.size}%d")

val diff = DiffGraphBuilder(cpg.graph.schema)
var added = 0
var skipped = 0

allNodes.foreach { n =>
  pickCommentFor(n) match {
    case Some(span) if span.text.trim.nonEmpty =>
      if (!commentExistsForOwner(n, span)) {
        attachComment(n, span, diff)
        added += 1
      } else {
        skipped += 1
      }
    case _ => skipped += 1
  }
}

flatgraph.DiffGraphApplier.applyDiff(cpg.graph, diff)

println(f"[+] COMMENTS added : $added%6d")
println(f"[ ] Skipped/exists : $skipped%6d")
