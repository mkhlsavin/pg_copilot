// export_tags.sc — extraction of all TAG nodes and summaries
// Launch: :load export_tags.sc
//
// JVM parameters (opt.):
//   -Dtags.out=tags.json
//   -Dtags.csv=tags.csv
//   -Dtags.limit=0 - limit on the number of rows output in summaries for tag names and (name, value) pairs. 0 = no limit. Any value >0 truncates the list to the specified count.
//   -Dtags.attachments=false - whether to collect examples of nodes to which each tag is attached. false — do not collect (faster, smaller file), true — add an "attachments" field with a sample of nodes for each (name, value) pair.
//   -Dtags.sample=5 - how many sample nodes to take for each (name, value) pair when attachments=true. Ignored if attachments=false.

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.semanticcpg.language._
import java.nio.file.{Files, Paths}
import java.nio.charset.StandardCharsets
import scala.util.Try

// --------- config ----------
val OUT_JSON      = sys.props.get("tags.out").filter(_.nonEmpty)
val OUT_CSV       = sys.props.get("tags.csv").filter(_.nonEmpty)
val LIMIT         = sys.props.getOrElse("tags.limit", "0").toInt
val WITH_ATTACH   = sys.props.getOrElse("tags.attachments", "false").toBoolean
val SAMPLE_PER_KV = math.max(0, sys.props.getOrElse("tags.sample", "5").toInt)

// --------- utils ----------
def escapeJson(s: String): String =
  Option(s).getOrElse("").flatMap {
    case '"'  => "\\\""
    case '\\' => "\\\\"
    case '\b' => "\\b"
    case '\f' => "\\f"
    case '\n' => "\\n"
    case '\r' => "\\r"
    case '\t' => "\\t"
    case c    => c.toString
  }

case class NodeBrief(id: Long, label: String, name: String, file: String, line: Int)

def fileOf(n: StoredNode): String =
  Try(n.file.name.headOption.getOrElse("")).getOrElse("")

def lineOf(n: StoredNode): Int = n match {
  case x: Method            => x.lineNumber.getOrElse(0)
  case x: Call              => x.lineNumber.getOrElse(0)
  case x: TypeDecl          => x.lineNumber.getOrElse(0)
  case x: Identifier        => x.lineNumber.getOrElse(0)
  case x: MethodParameterIn => x.lineNumber.getOrElse(0)
  case x: Local             => x.lineNumber.getOrElse(0)
  case x: Member            => x.lineNumber.getOrElse(0)
  case x: ControlStructure  => x.lineNumber.getOrElse(0)
  case x: Block             => x.lineNumber.getOrElse(0)
  case x: Return            => x.lineNumber.getOrElse(0)
  case _                    => 0
}

def nameOf(n: StoredNode): String = n match {
  case m: Method            => m.name
  case c: Call              => c.name
  case t: TypeDecl          => t.name
  case i: Identifier        => i.name
  case p: MethodParameterIn => p.name
  case l: Local             => l.name
  case f: File              => f.name
  case _                    => ""
}

def brief(n: StoredNode): NodeBrief =
  NodeBrief(n.id, n.label, nameOf(n), fileOf(n), lineOf(n))

// --------- tag collection ----------
val tags = cpg.tag.l
val totalTags = tags.size
val distinctNames = tags.map(_.name).distinct.sorted

// summary by (name,value)
val kvCounts = tags.groupBy(t => (t.name, t.value)).view.mapValues(_.size).toList
  .sortBy{ case ((name, value), cnt) => (-cnt, name, value) }

// summary by name
val nameCounts = kvCounts.groupBy(_._1._1).map { case (name, rows) =>
  val total = rows.map(_._2).sum
  (name, total)
}.toList.sortBy{ case (name, total) => (-total, name) }

// --------- printing brief summary ----------
println(s"[*] Total TAG nodes: $totalTags")
println(s"[*] Distinct tag names: ${distinctNames.size}")
println("[*] Top tag names:")
nameCounts.take(if (LIMIT>0) LIMIT else nameCounts.size).foreach { case (name, total) =>
  println(f"    $name%-28s  $total%7d")
}

println("[*] Top (name, value) pairs:")
kvCounts.take(if (LIMIT>0) LIMIT else kvCounts.size).foreach { case ((name, value), cnt) =>
  val v = Option(value).getOrElse("")
  val pair = s"($name, $v)"
  println(f"    ${pair}%-64s ${cnt}%7d")
}

// --------- attachments (on request) ----------
case class KV(keyName: String, keyValue: String, count: Int, nodes: List[NodeBrief])
val kvWithNodes: List[KV] =
  if (!WITH_ATTACH || SAMPLE_PER_KV <= 0) Nil
  else kvCounts.map { case ((name, value), cnt) =>
    val nodes = Try {
      cpg.all.where(_.tag.nameExact(name).valueExact(value))
        .take(SAMPLE_PER_KV).l.map(brief)
    }.getOrElse(Nil)
    KV(name, Option(value).getOrElse(""), cnt, nodes)
  }

// --------- CSV ----------
OUT_CSV.foreach { path =>
  val header = "tag_name,tag_value,count\n"
  val body = kvCounts.map { case ((name, value), cnt) =>
    val n = name.replace("\"","\"\""); val v = Option(value).getOrElse("").replace("\"","\"\"")
    s"\"$n\",\"$v\",$cnt"
  }.mkString("\n")
  Files.write(Paths.get(path), (header + body + "\n").getBytes(StandardCharsets.UTF_8))
  println(s"[+] CSV -> $path")
}

// --------- JSON ----------
OUT_JSON.foreach { path =>
  val sb = new StringBuilder(1 << 20)
  sb.append("{")
  sb.append("\"summary\":{")
  sb.append(s"\"total_tags\":$totalTags,")
  sb.append(s"\"distinct_names\":${distinctNames.size}")
  sb.append("},")

  sb.append("\"names\":[")
  sb.append(
    nameCounts.map{ case (name,total) =>
      s"""{"name":"${escapeJson(name)}","total":$total}"""
    }.mkString(",")
  )
  sb.append("],")

  sb.append("\"pairs\":[")
  sb.append(
    kvCounts.map{ case ((name,value),cnt) =>
      s"""{"name":"${escapeJson(name)}","value":"${escapeJson(Option(value).getOrElse(""))}","count":$cnt}"""
    }.mkString(",")
  )
  sb.append("]")

  if (WITH_ATTACH) {
    sb.append(",\"attachments\":[")
    sb.append(
      kvWithNodes.map { kv =>
        val nodesJson = kv.nodes.map { n =>
          s"""{"id":${n.id},"label":"${escapeJson(n.label)}","name":"${escapeJson(n.name)}","file":"${escapeJson(n.file)}","line":${n.line}}"""
        }.mkString(",")
        s"""{"name":"${escapeJson(kv.keyName)}","value":"${escapeJson(kv.keyValue)}","count":${kv.count},"nodes":[$nodesJson]}"""
      }.mkString(",")
    )
    sb.append("]")
  }

  sb.append("}")
  Files.write(Paths.get(path), sb.toString.getBytes(StandardCharsets.UTF_8))
  println(s"[+] JSON  -> $path")
}

println("[*] Done.")
