// api_usage_examples.sc — API usage pattern extraction
// Запуск: :load api_usage_examples.sc
//
// ВАЖНО: скрипт МОДИФИЦИРУЕТ граф (добавляет TAG-ноды с информацией об использовании API)
//
// ============================================================================
// НАСТРОЙКА
// ============================================================================
// Через системные свойства (опционально):
//   -Dapi.minCallers=5           минимальное число вызовов для пометки как API
//   -Dapi.testDir="src/test"     директория с тестами
//   -Dapi.apply=true             применить теги к графу
//
// По умолчанию: minCallers=5, testDir="src/test", apply=true
//
// ============================================================================
// ОПИСАНИЕ
// ============================================================================
// Скрипт анализирует использование API и добавляет теги:
// - `api-caller-count`: Количество вызовов метода (популярность)
// - `api-example`: Пример использования из тестов
// - `api-typical-usage`: Типичный паттерн вызова
// - `api-public`: Является ли публичным API
//
// ============================================================================
// ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
// ============================================================================
//
// 1. Найти самые популярные API:
//    cpg.method.tag.name("api-caller-count").value.toList.sorted.reverse.take(10)
//
// 2. Получить пример использования API:
//    cpg.method.name("palloc").tag.name("api-example").value.l.headOption
//
// 3. Найти популярные но недокументированные API:
//    cpg.method
//      .where(_.tag.nameExact("api-caller-count").value.toInt > 20)
//      .where(_._astOut.collectAll[Comment].isEmpty)
//      .name.l
//
// 4. Найти все публичные API с примерами:
//    cpg.method
//      .where(_.tag.nameExact("api-public").valueExact("true"))
//      .where(_.tag.nameExact("api-example").exists)
//      .name.l
//
// 5. Анализ для онбординга - показать популярные entry points:
//    cpg.method
//      .where(_.tag.nameExact("api-caller-count").value.toInt > 50)
//      .sortBy(_.tag.name("api-caller-count").value.toInt).reverse
//      .map(m => (m.name, m.tag.name("api-caller-count").value.headOption))
//      .l.take(20)
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.codepropertygraph.generated.{EdgeTypes, NodeTypes}
import flatgraph.DiffGraphBuilder

// ========================= Config =========================
val MIN_CALLERS = sys.props.getOrElse("api.minCallers", "5").toInt
val TEST_DIR = sys.props.getOrElse("api.testDir", "src/test")
val APPLY_TAGS = sys.props.getOrElse("api.apply", "true").toBoolean

println(s"[*] Min callers for API: $MIN_CALLERS")
println(s"[*] Test directory: $TEST_DIR")
println(s"[*] Apply tags: $APPLY_TAGS")

// ========================= Analysis Functions =========================

// Определить является ли метод публичным API
def isPublicAPI(m: Method): Boolean = {
  // В PostgreSQL публичные API обычно:
  // 1. Не статичные
  // 2. Не начинаются с underscore
  // 3. Объявлены в .h файлах
  val name = m.name
  val isStatic = m.code.contains("static ")
  val isPrivate = name.startsWith("_")

  !isStatic && !isPrivate
}

// Подсчитать количество вызовов метода
def countCallers(m: Method): Int = {
  try {
    cpg.call.name(m.name).size
  } catch {
    case _: Throwable => 0
  }
}

// Найти примеры использования в тестах и других файлах
def findTestExamples(methodName: String): List[String] = {
  try {
    // Стратегия 1: Получить контекст вызовов (родительский метод)
    val examples = cpg.call
      .nameExact(methodName)
      .method  // Get the method containing this call
      .code
      .l
      .map(extractMinimalExample)
      .distinct
      .take(3)

    examples
  } catch {
    case _: Throwable => List.empty
  }
}

// Определить типичный паттерн использования
def findTypicalUsage(m: Method): Option[String] = {
  try {
    // Найти наиболее частый контекст вызова (родительский метод)
    val callers = cpg.call.name(m.name).method.name.l
    if (callers.nonEmpty) {
      val mostCommonCaller = callers.groupBy(identity).maxBy(_._2.size)._1
      Some(s"Often called from: $mostCommonCaller")
    } else None
  } catch {
    case _: Throwable => None
  }
}

// Извлечь минимальный пример использования
def extractMinimalExample(code: String): String = {
  // Упростить код: убрать комментарии и лишние пробелы
  val lines = code.split("\n").map(_.trim).filter(l =>
    l.nonEmpty && !l.startsWith("//") && !l.startsWith("/*")
  )
  lines.mkString(" ").take(200) + (if (lines.mkString(" ").length > 200) "..." else "")
}

// ========================= Graph modification =========================

def applyAPITags(): Unit = {
  val diff = DiffGraphBuilder(cpg.graph.schema)
  var tagged = 0
  var apiCount = 0

  println("[*] Analyzing API usage patterns...")

  // Получить все методы
  val methods = cpg.method.l

  println(s"[*] Found ${methods.size} methods")
  println("[*] Counting callers and extracting examples...")

  methods.foreach { method =>
    val callerCount = countCallers(method)

    // Пометить только методы с достаточным числом вызовов
    if (callerCount >= MIN_CALLERS) {
      apiCount += 1

      // TAG: caller count
      val tagCallerCount = NewTag()
        .name("api-caller-count")
        .value(callerCount.toString)

      diff.addNode(tagCallerCount)
      diff.addEdge(method, tagCallerCount, EdgeTypes.TAGGED_BY)

      // TAG: public API
      if (isPublicAPI(method)) {
        val tagPublic = NewTag()
          .name("api-public")
          .value("true")

        diff.addNode(tagPublic)
        diff.addEdge(method, tagPublic, EdgeTypes.TAGGED_BY)
      }

      // TAG: example from tests
      val testExamples = findTestExamples(method.name)
      if (testExamples.nonEmpty) {
        val exampleCode = extractMinimalExample(testExamples.head)
        val tagExample = NewTag()
          .name("api-example")
          .value(exampleCode)

        diff.addNode(tagExample)
        diff.addEdge(method, tagExample, EdgeTypes.TAGGED_BY)
      }

      // TAG: typical usage pattern
      findTypicalUsage(method).foreach { usage =>
        val tagUsage = NewTag()
          .name("api-typical-usage")
          .value(usage)

        diff.addNode(tagUsage)
        diff.addEdge(method, tagUsage, EdgeTypes.TAGGED_BY)
      }

      tagged += 1

      if (tagged % 100 == 0) {
        println(s"[*] Processed $tagged APIs...")
      }
    }
  }

  println(s"[*] Applying tags to graph...")
  flatgraph.DiffGraphApplier.applyDiff(cpg.graph, diff)

  println(s"[+] Tagged $tagged methods with API usage information")
  println(s"[+] Found $apiCount APIs (methods with >= $MIN_CALLERS callers)")

  // Статистика
  val publicAPIs = cpg.method.where(_.tag.nameExact("api-public").valueExact("true")).size
  val withExamples = cpg.method.filter(_.tag.nameExact("api-example").nonEmpty).size

  println(s"[+] Public APIs: $publicAPIs")
  println(s"[+] APIs with examples: $withExamples")
}

// ========================= Initialization =========================

if (APPLY_TAGS) {
  applyAPITags()
  println("[*] Query examples:")
  println("""    cpg.method.tag.name("api-caller-count").value.l.sortBy(_.toInt).reverse.take(10)""")
  println("""    cpg.method.where(_.tag.nameExact("api-public").valueExact("true")).name.l.take(10)""")
} else {
  println("[*] Tag application disabled. Set -Dapi.apply=true to enable")
}
