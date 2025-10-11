// subsystem_readme.sc — связывание узлов CPG с README подсистем PostgreSQL
// Запуск: :load subsystem_readme.sc
//
// ВАЖНО: скрипт МОДИФИЦИРУЕТ граф (добавляет TAG-ноды с информацией о подсистеме)
//
// ============================================================================
// НАСТРОЙКА
// ============================================================================
// Через системные свойства (опционально):
//   -Dsubsystem.srcroot="C:\Users\user\postgres-REL_17_6\src"  путь к src PostgreSQL
//   -Dsubsystem.apply=true                                      применить теги к графу
//
// По умолчанию: C:\Users\user\postgres-REL_17_6\src
//
// ============================================================================
// ОПИСАНИЕ
// ============================================================================
// Скрипт находит все README файлы в подсистемах PostgreSQL и:
// 1. Позволяет запрашивать README по узлам CPG
// 2. ДОБАВЛЯЕТ ТЕГИ к узлам FILE с информацией о подсистеме:
//    - subsystem-name: имя подсистемы (например, "executor")
//    - subsystem-path: путь к README (например, "src/backend/executor/README")
//    - subsystem-desc: ПОЛНОЕ содержимое README для RAG контекста
//
// ============================================================================
// ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
// ============================================================================
//
// === БАЗОВЫЕ ЗАПРОСЫ (через функции) ===
//
// 1. Показать все доступные подсистемы с README:
//    listAllSubsystems()
//
// 2. Найти README для конкретного файла:
//    getSubsystemReadme("src/backend/executor/execMain.c").foreach { case (path, content) =>
//      println(s"README: $path")
//      println(content.take(500))
//    }
//
// 3. Получить полное описание подсистемы по имени:
//    getSubsystemByName("executor").foreach { case (path, content) =>
//      println(s"=== $path ===")
//      println(content)
//    }
//
// 4. Найти README для метода:
//    cpg.method.name("ExecutorStart").l.headOption.foreach { m =>
//      println(s"Method: ${m.name} in ${m.filename}")
//      getSubsystemReadmeForNode(m).foreach { case (path, content) =>
//        println(s"\nSubsystem: $path")
//        println(content.take(500))
//      }
//    }
//
// 5. Статистика: файлы по подсистемам:
//    getFilesGroupedBySubsystem().foreach { case (subsys, files) =>
//      println(s"$subsys: ${files.size} files")
//    }
//
// === ПОИСК ПО ТЕГАМ (после применения к графу) ===
//
// 6. Показать все подсистемы через теги:
//    cpg.file.tag.name("subsystem-name").value.dedup.sorted.l
//
// 7. Статистика по подсистемам через теги:
//    cpg.file.tag.name("subsystem-name").value.groupBy(identity).view.mapValues(_.size).toMap
//
// 8. Найти все файлы в подсистеме executor:
//    cpg.file.where(_.tag.nameExact("subsystem-name").valueExact("executor")).name.l.take(5)
//
// 9. Получить ПОЛНОЕ описание подсистемы из тега:
//    cpg.file.name(".*execMain.*").tag.name("subsystem-desc").value.l.headOption.foreach(println)
//
// 10. Получить путь к README из тега:
//     cpg.file.name(".*execMain.*").tag.name("subsystem-path").value.l.headOption
//
// === RAG: ПОЛНЫЙ КОНТЕКСТ ДЛЯ АНАЛИЗА ===
//
// 11. Получить контекст метода для RAG (код + комментарии + документация):
//     cpg.method.name("ExecutorStart").l.headOption.foreach { m =>
//       println(s"=== Method: ${m.name} ===")
//       println(s"File: ${m.filename}")
//       println(s"Line: ${m.lineNumber.getOrElse(0)}")
//       println(s"Code:\n${m.code}")
//
//       // Комментарий к методу (требует ast_comments.sc)
//       m._astOut.collectAll[Comment].code.l.headOption.foreach { comment =>
//         println(s"\nMethod Documentation:\n$comment")
//       }
//
//       // Описание подсистемы
//       m.file.tag.name("subsystem-name").value.l.headOption.foreach { subsys =>
//         println(s"\nSubsystem: $subsys")
//       }
//       m.file.tag.name("subsystem-desc").value.l.headOption.foreach { desc =>
//         println(s"\nSubsystem Documentation:\n$desc")
//       }
//     }
//
// 12. Получить контекст файла для RAG:
//     cpg.file.name(".*execMain.*").l.headOption.foreach { f =>
//       println(s"=== File: ${f.name} ===")
//
//       // Заголовок файла (комментарий)
//       f._astOut.collectAll[Comment].code.l.headOption.foreach { comment =>
//         println(s"\nFile Header:\n$comment")
//       }
//
//       // Информация о подсистеме
//       f.tag.name("subsystem-name").value.l.headOption.foreach { subsys =>
//         println(s"\nSubsystem: $subsys")
//       }
//       f.tag.name("subsystem-path").value.l.headOption.foreach { path =>
//         println(s"README: $path")
//       }
//       f.tag.name("subsystem-desc").value.l.headOption.foreach { desc =>
//         println(s"\nSubsystem Context:\n$desc")
//       }
//     }
//
// 13. Получить контекст вызова (CALL) для RAG:
//     cpg.call.code(".*ExecInitNode.*").l.headOption.foreach { c =>
//       println(s"=== Call: ${c.code} ===")
//       println(s"File: ${c.filename}:${c.lineNumber.getOrElse(0)}")
//
//       // Комментарий к вызову
//       c._astOut.collectAll[Comment].code.l.headOption.foreach { comment =>
//         println(s"\nCall Documentation:\n$comment")
//       }
//
//       // Контекст подсистемы
//       c.file.tag.name("subsystem-desc").value.l.headOption.foreach { desc =>
//         println(s"\nSubsystem Context:\n${desc.take(500)}...")
//       }
//     }
//
// 14. Найти все методы в подсистеме с их контекстом:
//     cpg.file.where(_.tag.nameExact("subsystem-name").valueExact("executor"))
//       .ast.isMethod.name.dedup.sorted.l.take(10)
//
// 15. Экспорт контекста для RAG промпта:
//     def getRAGContext(methodName: String): String = {
//       cpg.method.name(methodName).l.headOption.map { m =>
//         val code = s"Method: ${m.name}\nFile: ${m.filename}:${m.lineNumber.getOrElse(0)}\n\nCode:\n${m.code}"
//         val comment = m._astOut.collectAll[Comment].code.l.headOption.map(c => s"\n\nDocumentation:\n$c").getOrElse("")
//         val subsys = m.file.tag.name("subsystem-name").value.l.headOption.map(s => s"\n\nSubsystem: $s").getOrElse("")
//         val subsysDesc = m.file.tag.name("subsystem-desc").value.l.headOption.map(d => s"\n\nSubsystem Context:\n$d").getOrElse("")
//         code + comment + subsys + subsysDesc
//       }.getOrElse("Method not found")
//     }
//     // Использование:
//     println(getRAGContext("ExecutorStart"))
//
// ============================================================================

import java.io.File
import scala.io.Source
import scala.util.{Try, Success, Failure}
import java.nio.file.{Files, Paths, Path}
import scala.jdk.CollectionConverters._
import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.codepropertygraph.generated.{EdgeTypes, NodeTypes}
import flatgraph.DiffGraphBuilder

// ========================= Config =========================
val SRC_ROOT = sys.props.getOrElse("subsystem.srcroot", """C:\Users\user\postgres-REL_17_6\src""")
val APPLY_TAGS = sys.props.getOrElse("subsystem.apply", "true").toBoolean

// Кеш для README файлов: путь -> содержимое
val readmeCache = scala.collection.mutable.Map.empty[String, String]

// Функция для нормализации путей (Windows/Unix)
def normalizePath(p: String): String = {
  p.replace('\\', '/').replaceFirst("^[A-Za-z]:", "").toLowerCase
}

// Поиск всех README файлов в структуре проекта
def findAllReadmes(rootPath: String = SRC_ROOT): Map[String, String] = {
  if (readmeCache.nonEmpty) return readmeCache.toMap

  val root = new File(rootPath).getAbsoluteFile
  if (!root.exists) {
    println(s"[!] WARNING: Source root does not exist: ${root.getAbsolutePath}")
    println(s"[!] Set correct path via -Dsubsystem.srcroot=<path>")
    return Map.empty
  }

  println(s"[*] Scanning for README files in: ${root.getAbsolutePath}")

  def scanDir(dir: File, depth: Int = 0): List[(String, String)] = {
    if (depth > 10 || !dir.exists || !dir.isDirectory) return List.empty

    val readmeFile = new File(dir, "README")
    val result = if (readmeFile.exists && readmeFile.isFile) {
      Try {
        val content = Source.fromFile(readmeFile, "UTF-8").mkString
        val relativePath = root.toPath.relativize(readmeFile.toPath).toString
        readmeCache.update(normalizePath(relativePath), content)
        List((normalizePath(relativePath), content))
      }.getOrElse(List.empty)
    } else List.empty

    val subdirs = Try(dir.listFiles.filter(_.isDirectory).toList).getOrElse(List.empty)
    result ++ subdirs.flatMap(d => scanDir(d, depth + 1))
  }

  val readmes = scanDir(root)
  println(s"[+] Found ${readmes.size} README files")
  readmeCache.toMap
}

// Получить подсистему для файла (путь от README к корню подсистемы)
def getSubsystemForFile(filePath: String, readmes: Map[String, String]): Option[(String, String)] = {
  val normalized = normalizePath(filePath)
  val parts = normalized.split("/").toList

  // Ищем наиболее конкретный README (самый глубокий в иерархии)
  val candidates = readmes.toList.flatMap { case (readmePath, content) =>
    val readmeDir = readmePath.split("/").dropRight(1).mkString("/")
    if (normalized.contains(readmeDir) && readmeDir.nonEmpty) {
      Some((readmeDir.split("/").length, readmePath, content))
    } else None
  }

  if (candidates.isEmpty) None
  else {
    val (_, path, content) = candidates.maxBy(_._1)
    Some((path, content))
  }
}

// API: Получить README для конкретного пути файла
def getSubsystemReadme(filePath: String): Option[(String, String)] = {
  val readmes = findAllReadmes()
  getSubsystemForFile(filePath, readmes)
}

// API: Получить README для любого узла CPG
def getSubsystemReadmeForNode(node: io.shiftleft.codepropertygraph.generated.nodes.StoredNode): Option[(String, String)] = {
  val filename = node.file.name.headOption.getOrElse("")
  if (filename.isEmpty) None
  else getSubsystemReadme(filename)
}

// API: Список всех подсистем
def listAllSubsystems(): List[String] = {
  val readmes = findAllReadmes()
  readmes.keys.toList.sorted.map { path =>
    val subsysName = path.split("/").dropRight(1).lastOption.getOrElse("root")
    f"$subsysName%-20s -> $path"
  }
}

// API: Получить README по имени подсистемы (например, "executor")
def getSubsystemByName(subsysName: String): Option[(String, String)] = {
  val readmes = findAllReadmes()
  readmes.find { case (path, _) =>
    path.toLowerCase.contains(subsysName.toLowerCase)
  }
}

// API: Сгруппировать файлы CPG по подсистемам
def getFilesGroupedBySubsystem(): Map[String, List[String]] = {
  val readmes = findAllReadmes()
  cpg.file.l.groupBy { f =>
    getSubsystemForFile(f.name, readmes)
      .map(_._1.split("/").dropRight(1).lastOption.getOrElse("unknown"))
      .getOrElse("unknown")
  }.view.mapValues(_.map(_.name)).toMap
}

// ========================= Graph modification =========================

// Применить теги к FILE узлам
def applySubsystemTags(): Unit = {
  val readmes = findAllReadmes()
  if (readmes.isEmpty) {
    println("[!] No README files found, skipping tag application")
    return
  }

  val diff = DiffGraphBuilder(cpg.graph.schema)
  var tagged = 0
  var totalDescSize = 0L

  println("[*] Applying subsystem tags to FILE nodes...")

  cpg.file.l.foreach { file =>
    getSubsystemForFile(file.name, readmes).foreach { case (readmePath, content) =>
      val subsysName = readmePath.split("/").dropRight(1).lastOption.getOrElse("unknown")

      // Сохраняем ПОЛНОЕ содержимое README для RAG
      val fullDesc = content.trim

      // Создаем теги
      val tagName = NewTag()
        .name("subsystem-name")
        .value(subsysName)

      val tagPath = NewTag()
        .name("subsystem-path")
        .value(readmePath)

      val tagDesc = NewTag()
        .name("subsystem-desc")
        .value(fullDesc)

      diff.addNode(tagName)
      diff.addNode(tagPath)
      diff.addNode(tagDesc)

      diff.addEdge(file, tagName, EdgeTypes.TAGGED_BY)
      diff.addEdge(file, tagPath, EdgeTypes.TAGGED_BY)
      diff.addEdge(file, tagDesc, EdgeTypes.TAGGED_BY)

      tagged += 1
      totalDescSize += fullDesc.length
    }
  }

  flatgraph.DiffGraphApplier.applyDiff(cpg.graph, diff)
  println(s"[+] Tagged $tagged FILE nodes with subsystem information")
  println(s"[+] Total README content size: ${totalDescSize / 1024} KB")
}

// ========================= Initialization =========================

println(s"[*] Source root: $SRC_ROOT")
println(s"[*] Apply tags: $APPLY_TAGS")

val allReadmes = findAllReadmes()
println(s"[+] Loaded ${allReadmes.size} README files into cache")
println("[*] Use listAllSubsystems() to see all available subsystems")

if (APPLY_TAGS && allReadmes.nonEmpty) {
  applySubsystemTags()
  println("[*] Query examples:")
  println("""    cpg.file.tag.name("subsystem-name").value.dedup.sorted.l""")
  println("""    cpg.file.where(_.tag.nameExact("subsystem-name").valueExact("executor")).name.l""")
} else if (APPLY_TAGS) {
  println("[!] Skipping tag application (no README files found)")
} else {
  println("[*] Tag application disabled. Set -Dsubsystem.apply=true to enable")
}
