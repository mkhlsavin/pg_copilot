# CPG Enrichment - Quick Start Guide

## Быстрый запуск (Windows PowerShell)

```powershell
# 1. Установить память
$env:JAVA_OPTS="-Xmx24G -Xms4G"

# 2. Запустить enrichment
# Вариант A: Если у вас .bin.zip файл
.\enrich_cpg.ps1 standard workspace/postgres-REL_17_6.bin.zip

# Вариант B: Если у вас уже готовый workspace
.\enrich_cpg.ps1 standard workspace/postgres-REL_17_6
```

## Быстрый запуск (Linux/macOS/Git Bash)

```bash
# 1. Установить память
export JAVA_OPTS="-Xmx24G -Xms4G"

# 2. Сделать исполняемым и запустить
chmod +x enrich_cpg.sh

# Вариант A: Если у вас .bin.zip файл
./enrich_cpg.sh standard workspace/postgres-REL_17_6.bin.zip

# Вариант B: Если у вас уже готовый workspace
./enrich_cpg.sh standard workspace/postgres-REL_17_6
```

**Примечание:** Скрипты автоматически определяют тип входного файла:
- Если это директория → используется как готовый workspace
- Если это файл (.bin.zip) → сначала импортируется в workspace, затем обогащается

## Ручной режим (если автоматический не работает)

### Шаг 1: Импортировать CPG (если ещё не в workspace)

```bash
# Установить память
export JAVA_OPTS="-Xmx24G -Xms4G"  # Windows PowerShell: $env:JAVA_OPTS="-Xmx24G -Xms4G"

# Запустить Joern
joern
```

```scala
// Если у вас .bin.zip файл, импортируйте его
importCpg("workspace/postgres-REL_17_6.bin.zip", "postgres-REL_17_6")

// Если уже импортировано, откройте workspace
open("postgres-REL_17_6")
```

### Шаг 2: Проверить что CPG загружен

```scala
cpg.file.size  // Должно быть > 0
```

### Шаг 3: В Joern REPL выполнить скрипты обогащения

```scala
// Minimal profile (~10 минут)
import $file.`ast_comments.sc`
import $file.`subsystem_readme.sc`

// Standard profile (добавить ещё ~50 минут)
import $file.`api_usage_examples.sc`
import $file.`security_patterns.sc`
import $file.`code_metrics.sc`
import $file.`extension_points.sc`
import $file.`dependency_graph.sc`

// Full profile (добавить ещё ~30 минут)
import $file.`test_coverage.sc`
import $file.`performance_hotspots.sc`

// Выйти (автоматически сохранит CPG)
close
```

## Проверка результатов

```bash
# Запустить Joern
joern
```

```scala
// Открыть workspace
open("postgres-REL_17_6")

// Проверить что обогащение сработало
cpg.comment.size  // Должно быть > 0
cpg.tag.size      // Должно быть > 0

// Примеры запросов
cpg.file.tag.name("subsystem-name").value.dedup.sorted.l.take(10)
cpg.method.tag.name("api-caller-count").value.l.map(_.toInt).sorted.reverse.take(10)
```

## Типичные проблемы

### Проблема: "Access is denied" при импорте workspace

**Причина:** Вы пытаетесь импортировать директорию workspace вместо .bin.zip файла.

**Решение:**
```bash
# ❌ Неправильно (директория)
joern --import workspace/postgres-REL_17_6

# ✅ Правильно (открыть существующий workspace)
joern
open("postgres-REL_17_6")

# ✅ Правильно (импортировать из .bin.zip файла)
joern
importCpg("workspace/postgres-REL_17_6.bin.zip", "postgres-REL_17_6")
```

### Проблема: "invalid escape character" (Windows)

**Причина:** Windows использует backslash (`\`) в путях, что конфликтует с Scala escape sequences.

**Решение:** Скрипты автоматически конвертируют пути в Unix-style (`/`). Если запускаете вручную:
```scala
// ❌ Неправильно
importCpg("workspace\postgres-REL_17_6")

// ✅ Правильно
importCpg("workspace/postgres-REL_17_6")
```

### Проблема: "Not found: $file" в batch скрипте

**Причина:** `import $file` работает только в интерактивном REPL, не в batch скриптах.

**Решение:** Автоматические скрипты (`enrich_cpg.ps1`, `enrich_cpg.sh`) уже решают эту проблему - они встраивают содержимое каждого .sc файла напрямую в batch скрипт.

Для ручного запуска используйте интерактивный REPL:
```scala
// ✅ В интерактивном REPL
import $file.`ast_comments.sc`

// ❌ В batch скрипте (не работает)
:load ast_comments.sc
import $file.`ast_comments.sc`
```

### Проблема: Out of Memory (OOM)

**Решение:** Увеличить heap:
```bash
# Bash
export JAVA_OPTS="-Xmx32G -Xms8G"

# PowerShell
$env:JAVA_OPTS="-Xmx32G -Xms8G"
```

### Проблема: Скрипт не находит файлы

**Решение:** Убедитесь что все `.sc` файлы в одной директории:
```bash
ls *.sc
# Должно показать: ast_comments.sc, subsystem_readme.sc, api_usage_examples.sc, ...
```

## Профили обогащения

| Профиль | Время | Скрипты | Когда использовать |
|---------|-------|---------|-------------------|
| **minimal** | ~10 мин | comments, subsystem | Быстрая демонстрация |
| **standard** | ~60 мин | minimal + api, security, metrics, extension, dependency | **Рекомендуется для production** |
| **full** | ~90 мин | standard + test, performance | Максимальная детализация |

## Переменные окружения

```bash
# Память для JVM
export JAVA_OPTS="-Xmx24G -Xms4G"

# Путь к Joern (если не в PATH)
export JOERN_PATH="/path/to/joern"

# Путь к исходникам PostgreSQL (для subsystem_readme.sc)
export subsystem.srcroot="C:\Users\user\postgres-REL_17_6\src"
```

## Дополнительно

- Полная документация: [ENRICHMENT_README.md](ENRICHMENT_README.md)
- План RAG проекта: [C:\Users\user\pg_copilot\rag_cpgql\IMPLEMENTATION_PLAN.md](C:\Users\user\pg_copilot\rag_cpgql\IMPLEMENTATION_PLAN.md)
