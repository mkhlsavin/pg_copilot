# Импорт новой кодовой базы

Руководство по импорту новых проектов в систему CodeGraph.

> **Примечание:** В этом руководстве описывается создание новых данных CPG из исходного кода. Для использования существующих данных CPG просто настройте параметр `cpg.db_path` в файле `config.yaml`, указав путь к вашему файлу DuckDB.

## Содержание

- [Обзор](#obzor)
- [Поддерживаемые языки](#podderzhivaemye-yazyki)
- [Использование CLI](#ispolzovanie-cli)
- [Полный конвейер (одна команда)](#polnyy-konveyer-odna-komanda)
- [Поддержка Docker](#podderzhka-docker)
- [Управление сервером Joern](#upravlenie-serverom-joern)
- [Управление проектами](#upravlenie-proektami)
- [Пошаговый импорт](#poshagovyy-import)
- [Список поддерживаемых языков](#spisok-podderzhivaemyh-yazykov)
- [Использование REST API](#ispolzovanie-rest-api)
- [Получить список поддерживаемых языков](#poluchit-spisok-podderzhivaemyh-yazykov)
- [Запуск импорта (асинхронно)](#zapusk-importa-asinhronno)
- [Проверка статуса импорта](#proverka-statusa-importa)
- [Список всех задач импорта](#spisok-vseh-zadach-importa)
- [Отмена импорта](#otmena-importa)
- [Запуск отдельного шага](#zapusk-otdelnogo-shaga)
- [Импорт с использованием Docker](#import-s-ispolzovaniem-docker)
- [Управление сервером Joern](#upravlenie-serverom-joern)
- [Управление проектами](#upravlenie-proektami)
- [WebSocket для отслеживания прогресса](#websocket-dlya-otslezhivaniya-progressa)
- [Параметры импорта](#parametry-importa)
- [Режимы импорта](#rezhimy-importa)
- [Опции клонирования](#optsii-klonirovaniya)
- [Опции Joern](#optsii-joern)
- [Опции документации](#optsii-dokumentatsii)
- [Результат импорта](#rezultat-importa)
- [Структура результата (ProjectImportResult)](#struktura-rezultata-projectimportresult)
- [Проверка CPG](#proverka-cpg)
- [Оценка качества (0–100)](#otsenka-kachestva-0100)
- [Проверяемые метрики](#proveryaemye-metriki)
- [Импорт исходного кода](#import-ishodnogo-koda)
- [Как это работает](#kak-eto-rabotaet)
- [Поддерживаемые расширения файлов](#podderzhivaemye-rasshireniya-faylov)
- [Ограничение на размер файла](#ogranichenie-na-razmer-fayla)
- [Нормализация путей](#normalizatsiya-putey)
- [Статистика импорта](#statistika-importa)
- [Плагин предметной области (Domain Plugin)](#plagin-predmetnoy-oblasti-domain-plugin)
- [Структура плагина](#struktura-plagina)
- [Конфигурация: subsystems.yaml](#konfiguratsiya-subsystemsyaml)
- [Конфигурация: prompts.yaml](#konfiguratsiya-promptsyaml)
- [Активация плагина предметной области](#aktivatsiya-plagina-predmetnoy-oblasti)
- [Работа с большими репозиториями](#rabota-s-bolshimi-repozitoriyami)
- [LLVM (миллионы строк кода)](#llvm-milliony-strok-koda)
- [Рекомендации](#rekomendatsii)
- [Python API](#python-api)
- [Запуск отдельных шагов](#zapusk-otdelnyh-shagov)
- [Устранение неполадок](#ustranenie-nepoladok)
- [Joern Frontend не найден](#joern-frontend-ne-nayden)
- [Недостаточно памяти для Joern](#nedostatochno-pamyati-dlya-joern)
- [Язык не распознан](#yazyk-ne-raspoznan)
- [Проверка CPG не пройдена](#proverka-cpg-ne-proydena)
- [Конфигурация (config.yaml)](#konfiguratsiya-configyaml)
- [Архитектура компонентов](#arhitektura-komponentov)
- [JoernServerManager](#joernservermanager)
- [ProjectRegistry](#projectregistry)
- [LocalJoernRunner / DockerJoernRunner](#localjoernrunner-dockerjoernrunner)
- [См. также](#sm-takzhe)

## Обзор

Система поддерживает автоматический импорт кодовых баз на различных языках программирования. Процесс включает в себя:

1. **Клонирование** — клонирование репозитория
2. **Определение языка** — определение языка программирования
3. **Создание CPG** — построение графа свойств кода (требуется Joern для разбора исходного кода)
4. **Экспорт в DuckDB** — экспорт графа в SQL-базу данных
5. **Импорт исходного кода** — импорт полного содержимого исходных файлов в DuckDB
6. **Проверка** — проверка целостности CPG
7. **Импорт документации** — индексирование документации в ChromaDB
8. **Создание плагина** — генерация доменного плагина

---

## Поддерживаемые языки

| Язык | Фронтенд Joern | Расширения файлов | Описание |
| --- | --- | --- | --- |
| C/C++ | c2cpg | .c,.h,.cpp,.hpp,.cc,.cxx | Исходный код на C/C++ |
| C# | csharp2cpg | .cs | Исходный код на C# |
| Go | gosrc2cpg | .go | Исходный код на Go |
| Java (исходный код) | javasrc2cpg | .java | Исходный код на Java |
| Java (байт-код) | jimple2cpg | .class,.jar,.war,.ear | Анализ байт-кода Java через Jimple IR |
| JavaScript/TypeScript | jssrc2cpg | .js,.jsx,.ts,.tsx,.mjs | JavaScript/TypeScript |
| Kotlin | kotlin2cpg | .kt,.kts | Исходный код на Kotlin |
| PHP | php2cpg | .php | Исходный код на PHP |
| Python | pysrc2cpg | .py,.pyw | Исходный код на Python |
| Ruby | rubysrc2cpg | .rb | Исходный код на Ruby |
| Swift | swiftsrc2cpg | .swift | Исходный код на Swift |
| Ghidra (бинарные файлы) | ghidra2cpg | .exe,.dll,.so,.dylib,.bin,.elf | Анализ бинарных файлов |

## Использование CLI

### Полный конвейер (одна команда)

```
# Импорт из репозитория GitHub
python -m src.cli.import_commands full \
    --repo https://github.com/llvm/llvm-project \
    --branch main \
    --shallow \
    --language c

# Импорт локального проекта
python -m src.cli.import_commands full \
    --path /путь/к/проекту \
    --language java

# Избирательный импорт (только определённые директории)
python -m src.cli.import_commands full \
    --repo https://github.com/llvm/llvm-project \
    --include llvm/lib llvm/include \
    --exclude test tests

# Импорт с использованием Docker
python -m src.cli.import_commands full \
    --repo https://github.com/example/project \
    --docker
```

### Поддержка Docker

Система поддерживает запуск Joern в контейнере Docker для кроссплатформенной работы:

```
# Импорт с Docker (локальная установка Joern не требуется)
python -m src.cli.import_commands full \
    --repo https://github.com/example/project \
    --docker

# С указанием конкретного образа Docker
python -m src.cli.import_commands full \
    --repo https://github.com/example/project \
    --docker \
    --docker-image ghcr.io/joernio/joern:v4.0.0
```

**Преимущества использования Docker:**
- Не требуется локальная установка Joern
- Единообразное поведение на всех платформах (Windows, Linux, macOS)
- Изолированная среда выполнения
- Автоматическое управление ресурсами

### Управление сервером Joern

```
# Статус сервера
python -m src.cli.import_commands server status

# Запуск сервера (локальный Joern)
python -m src.cli.import_commands server start

# Запуск сервера в Docker
python -m src.cli.import_commands server start --docker

# Остановка сервера
python -m src.cli.import_commands server stop
```

### Управление проектами

```
# Список всех импортированных проектов
python -m src.cli.import_commands projects list

# Информация о проекте
python -m src.cli.import_commands projects info my_project

# Активация проекта (установка в качестве текущего)
python -m src.cli.import_commands projects activate my_project

# Удаление проекта (только метаданные)
python -m src.cli.import_commands projects delete my_project

# Удаление проекта вместе с файлами (CPG, DuckDB)
python -m src.cli.import_commands projects delete my_project --delete-files
```

### Пошаговый импорт

```
# 1. Клонирование репозитория
python -m src.cli.import_commands clone \
    --repo https://github.com/org/repo \
    --branch main \
    --shallow \
    --depth 1

# 2. Определение языка
python -m src.cli.import_commands detect --path ./workspace/repo

# 3. Создание CPG
python -m src.cli.import_commands cpg \
    --path ./workspace/repo \
    --language c

# 4. Экспорт в DuckDB
python -m src.cli.import_commands export --cpg ./workspace/repo.cpg

# 5. Проверка
python -m src.cli.import_commands validate --db ./workspace/repo.duckdb

# 6. Импорт документации
python -m src.cli.import_commands docs \
    --path ./workspace/repo \
    --db ./workspace/repo.duckdb

# 7. Создание Domain Plugin
python -m src.cli.import_commands domain \
    --path ./workspace/repo \
    --name my_project \
    --db ./workspace/repo.duckdb
```

### Список поддерживаемых языков

```
python -m src.cli.import_commands languages
```

---

## Использование REST API

### Получить список поддерживаемых языков

```
GET /api/v1/import/languages
```

**Ответ:**

```
{
  "languages": [
    {
      "id": "c",
      "name": "C",
      "extensions": [".c", ".h", ".cpp", ".hpp"],
      "joern_command": "c2cpg",
      "joern_flag": "C"
    },
    {
      "id": "java",
      "name": "JAVA",
      "extensions": [".java"],
      "joern_command": "javasrc2cpg",
      "joern_flag": "JAVASRC"
    }
  ]
}
```

### Запуск импорта (асинхронно)

```
POST /api/v1/import/start
Content-Type: application/json

{
  "repo_url": "https://github.com/llvm/llvm-project",
  "branch": "main",
  "shallow_clone": true,
  "language": null,
  "mode": "full",
  "include_paths": ["llvm/lib", "llvm/include"],
  "exclude_paths": ["test", "tests"],
  "create_domain_plugin": true,
  "import_docs": true
}
```

**Ответ:**

```
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Импорт запущен. Используйте job_id для отслеживания прогресса."
}
```

### Проверка статуса импорта

```
GET /api/v1/import/status/{job_id}
```

**Ответ:**

```
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "project_name": "llvm-project",
  "status": "in_progress",
  "steps": [
    {"name": "Clone Repository", "status": "completed", "progress": 100},
    {"name": "Detect Language", "status": "completed", "progress": 100},
    {"name": "Create CPG", "status": "in_progress", "progress": 45, "message": "Создание узлов CPG..."},
    {"name": "Export to DuckDB", "status": "pending", "progress": 0},
    {"name": "Import Source Code", "status": "pending", "progress": 0},
    {"name": "Validate CPG", "status": "pending", "progress": 0},
    {"name": "Import Documentation", "status": "pending", "progress": 0},
    {"name": "Setup Domain Plugin", "status": "pending", "progress": 0}
  ],
  "current_step": "joern_import",
  "overall_progress": 35,
  "created_at": "2024-12-09T10:00:00Z",
  "updated_at": "2024-12-09T10:05:00Z"
}
```

### Список всех задач импорта

```
GET /api/v1/import/jobs?status_filter=in_progress&limit=10
```

### Отмена импорта

```
DELETE /api/v1/import/cancel/{job_id}
```

### Выполнение отдельного шага

```
POST /api/v1/import/step
Content-Type: application/json

{
  "step_id": "validate",
  "context": {
    "duckdb_path": "./workspace/project.duckdb"
  }
}
```

### Импорт с использованием Docker

```
POST /api/v1/import/start
Content-Type: application/json

{
  "repo_url": "https://github.com/example/project",
  "branch": "main",
  "use_docker": true,
  "docker_image": "ghcr.io/joernio/joern:latest"
}
```

### Управление сервером Joern

**Получить статус сервера:**

```
GET /api/v1/import/server/status
```

**Ответ:**

```
{
  "status": "running",
  "mode": "docker",
  "container_id": "abc123",
  "port": 8080,
  "uptime_seconds": 3600
}
```

**Запуск сервера:**

```
POST /api/v1/import/server/start
Content-Type: application/json

{
  "use_docker": true,
  "docker_image": "ghcr.io/joernio/joern:latest"
}
```

**Остановка сервера:**

```
POST /api/v1/import/server/stop
```

### Управление проектами

**Список проектов:**

```
GET /api/v1/import/projects
```

**Ответ:**

```
{
  "projects": [
    {
      "id": "123",
      "name": "my_project",
      "language": "python",
      "cpg_path": "./workspace/my_project.cpg",
      "duckdb_path": "./workspace/my_project.duckdb",
      "is_active": true,
      "created_at": "2024-12-10T10:00:00Z"
    }
  ]
}
```

**Активация проекта:**

```
POST /api/v1/import/projects/{project_id}/activate
```

**Удаление проекта:**

```
DELETE /api/v1/import/projects/{project_id}?delete_files=true
```

## WebSocket для отслеживания хода выполнения

```
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/jobs/550e8400-e29b-41d4-a716-446655440000');

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);

  switch (msg.type) {
    case 'job.progress':
      console.log(`Ход выполнения: ${msg.payload.progress}% - ${msg.payload.message}`);
      break;
    case 'job.completed':
      console.log('Импорт завершён:', msg.payload.result);
      break;
    case 'job.failed':
      console.error('Импорт не удался:', msg.payload.error);
      break;
  }
};
```

## Параметры импорта

### Режимы импорта

| Режим | Описание |
| --- | --- |
| full | Полный импорт всей кодовой базы |
| selective | Импорт только указанных путей (include_paths) |
| incremental | Импорт только изменений с момента последнего импорта |

### Параметры клонирования

| Параметр | По умолчанию | Описание |
| --- | --- | --- |
| shallow_clone | true | Использовать неглубокое клонирование |
| shallow_depth | 1 | Глубина неглубокого клонирования |
| branch | "main" | Ветка для клонирования |

### Параметры Joern

| Параметр | По умолчанию | Описание |
| --- | --- | --- |
| joern_memory_gb | 16 | Объем памяти для Joern (в ГБ) |
| batch_size | 10000 | Размер пакета для экспорта в DuckDB |
| use_docker | false | Использовать Docker для Joern |
| docker_image | ghcr.io/joernio/joern:latest | Docker-образ Joern |

### Параметры документации

| Параметр | По умолчанию | Описание |
| --- | --- | --- |
| import_docs | true | Импортировать документацию |
| import_readme | true | Индексировать файлы README |
| import_comments | true | Импортировать комментарии в коде |

---

## Результат импорта

После успешного импорта создаются следующие элементы:

```
workspace/
├── llvm-project/           # Исходный код
├── llvm-project.cpg        # Файл CPG для Joern
└── llvm-project.duckdb     # База данных DuckDB (граф)

chromadb_storage/
└── llvm_project_documentation/  # Коллекция ChromaDB

src/domains/
└── llvm_project/           # Плагин домена
    ├── __init__.py
    ├── plugin.py
    ├── subsystems.yaml
    └── prompts.yaml
```

### Структура результата (ProjectImportResult)

```
{
  "cpg_path": "./workspace/llvm-project.cpg",
  "duckdb_path": "./workspace/llvm-project.duckdb",
  "domain_plugin_path": "./src/domains/llvm_project",
  "chromadb_collection": "llvm_project_documentation",
  "chromadb_stats": {
    "readme_indexed": 45,
    "docs_indexed": 230,
    "comments_indexed": 1500
  },
  "cpg_stats": {
    "methods": 125000,
    "calls": 450000,
    "identifiers": 890000
  },
  "source_code_stats": {
    "files_imported": 6307,
    "files_skipped_size": 12,
    "total_size_mb": 84.95
  },
  "validation_report": {
    "status": "passed",
    "quality_score": 85
  },
  "detected_language": "c",
  "import_duration_seconds": 3600.5
}
```

---

## Проверка CPG

### Оценка качества (0–100)

Оценка качества импортированного CPG:

| Критерий | Баллы |
| --- | --- |
| Найдены методы | +50 |
| Файлы, связанные с методами (>50%) | +20 |
| Наличие рёбер AST | +8 |
| Наличие рёбер CFG | +7 |
| Отсутствие ошибок проверки | +15 |

### Проверяемые метрики

- `methods_exist` — количество методов
- `calls_exist` — количество вызовов
- `edges_ast` — рёбра AST
- `edges_cfg` — рёбра CFG
- `methods_with_files` — методы, связанные с файлами

---

## Импорт исходного кода

Шаг `SourceContentStep` импортирует полное содержимое исходного кода в поле `nodes_file.content` для навигации по коду и его анализа.

### Принцип работы

1. Считывает файлы из пути `source_path`, указанного в конфигурации проекта
2. Заполняет поле `nodes_file.content` полным содержимым файлов
3. Автоматически нормализует пути к файлам для совместимости с `nodes_method` при выполнении JOIN
4. Определяет язык программирования по расширению файла

### Поддерживаемые расширения файлов

| Язык | Расширения |
| --- | --- |
| C/C++ | .c,.h,.cpp,.hpp,.cc,.cxx |
| Python | .py,.pyw |
| Java | .java |
| JavaScript/TypeScript | .js,.jsx,.ts,.tsx |
| Go | .go |
| Rust | .rs |
| Ruby | .rb |
| PHP | .php |
| C# | .cs |
| Kotlin | .kt,.kts |
| Swift | .swift |
| Scala | .scala |
| SQL | .sql |
| Shell | .sh,.bash |
| Конфигурационные файлы | .yaml,.yml,.json,.xml,.toml,.ini |

### Ограничение по размеру файла

Файлы размером более **500 КБ** пропускаются, чтобы поддерживать разумный объём базы данных. Это ограничение охватывает большинство исходных файлов, исключая при этом большие сгенерированные или бинарные файлы.

### Нормализация путей

Пути к файлам в поле `nodes_file.name` автоматически нормализуются для соответствия формату `nodes_method.filename`. Типичные префиксы, такие как `src/`, удаляются, чтобы обеспечить прямые JOIN-запросы:

```
-- Получение исходного кода метода по номеру строки
SELECT
    m.full_name,
    m.line_number,
    m.line_number_end,
    f.content
FROM nodes_method m
JOIN nodes_file f ON REPLACE(m.filename, '/', '\') = REPLACE(f.name, '/', '\')
WHERE m.full_name = 'exec_simple_query';
```

### Статистика импорта

После импорта доступна следующая статистика:

| Метрика | Описание |
| --- | --- |
| source_files_imported | Количество успешно импортированных файлов |
| source_files_skipped_size | Файлы, пропущенные из-за ограничения по размеру |
| source_files_skipped_not_found | Файлы, не найденные в указанном пути |
| source_files_total | Общее количество обработанных файлов |

---

## Плагин домена

Для работы с новым проектом автоматически генерируется плагин.

### Структура плагина

```
# src/domains/llvm_project/plugin.py

class LlvmProjectPlugin(DomainPlugin):
    @property
    def name(self) -> str:
        return "llvm_project"

    @property
    def display_name(self) -> str:
        return "Llvm Project"

    def _load_subsystems(self) -> Dict[str, SubsystemInfo]:
        # Загружается из subsystems.yaml
        ...

    def get_vulnerability_function_mappings(self) -> Dict[str, List[str]]:
        return {
            "buffer_overflow": ["strcpy", "memcpy", ...],
            "sql_injection": [...],
            ...
        }
```

### Конфигурация: subsystems.yaml

```
subsystems:
  core:
    description: "Основная логика приложения"
    key_functions:
      - main
      - init
      - start
    patterns:
      - "src"
      - "lib"
    related_files: []

  utils:
    description: "Вспомогательные функции"
    key_functions: []
    patterns:
      - "util"
      - "helper"
```

### Конфигурация: prompts.yaml

```
prompts:
  onboarding:
    system: |
      Вы являетесь экспертом по Llvm Project и помогаете разработчикам понять кодовую базу.
    user_template: |
      Помогите мне понять следующий аспект: {query}

  security:
    system: |
      Вы являетесь экспертом по безопасности и анализируете код Llvm Project (C).
    user_template: |
      Проанализируйте следующий код на наличие уязвимостей:
      {code}
```

---

## Активация плагина домена

После создания плагина добавьте его в конфигурацию:

```
# config.yaml
domains:
  active: "llvm_project"
  available:
    - postgresql
    - llvm_project
```

Или программно:

```
from src.domains import DomainRegistry

DomainRegistry.activate("llvm_project")
```

---

## Работа с большими репозиториями

### LLVM (миллионы строк кода)

```
# Использовать неглубокое клонирование
python -m src.cli.import_commands full \
    --repo https://github.com/llvm/llvm-project \
    --shallow \
    --depth 1

# Или выборочный импорт
python -m src.cli.import_commands full \
    --repo https://github.com/llvm/llvm-project \
    --include llvm/lib/Target/X86 \
    --mode selective

# Увеличить объем памяти для Joern
python -m src.cli.import_commands full \
    --repo https://github.com/llvm/llvm-project \
    --memory 32
```

### Рекомендации

1. **Используйте неглубокое клонирование**, чтобы сэкономить место и время
2. **Выбирайте нужные каталоги** с помощью параметра `--include`
3. **Исключайте тесты** с помощью `--exclude test tests`
4. **Увеличьте объем памяти Joern** для крупных проектов (16–32 ГБ)

---

## Python API {#python-api}

```
from src.project_import import (
    ProjectImportPipeline,
    ProjectImportRequest,
    SupportedLanguage,
    ImportMode,
)

# Создание запроса
request = ProjectImportRequest(
    repo_url="https://github.com/example/project",
    branch="main",
    shallow_clone=True,
    language=SupportedLanguage.JAVA,  # или None для автоматического определения
    mode=ImportMode.FULL,
    include_paths=["src/main"],
    exclude_paths=["src/test"],
    create_domain_plugin=True,
    import_docs=True,
)

# Запуск конвейера
async def run_import():
    def progress_callback(status):
        print(f"Прогресс: {status.overall_progress}% - {status.current_step}")

    pipeline = ProjectImportPipeline(progress_callback=progress_callback)
    result = await pipeline.run(request)

    print(f"CPG: {result.cpg_path}")
    print(f"DuckDB: {result.duckdb_path}")
    print(f"Язык: {result.detected_language}")
    print(f"Оценка качества: {result.validation_report['quality_score']}")

import asyncio
asyncio.run(run_import())
```

### Запуск отдельных шагов

```
from src.project_import.pipeline import ProjectImportPipeline

pipeline = ProjectImportPipeline()

# Контекст шага
context = {
    "request": ProjectImportRequest(),
    "source_path": Path("./workspace/project"),
    "duckdb_path": "./workspace/project.duckdb",
}

# Выполнение шага валидации
result = await pipeline.run_step("validate", context)
print(result["validation_report"])
```

---

## Устранение неполадок

### Не найден интерфейс Joern

```
RuntimeError: Frontend not found at expected paths
```

**Решение:** Проверьте переменную `JOERN_HOME` или укажите путь явно:

```
export JOERN_HOME=/путь/к/joern
python -m src.cli.import_commands full --repo ...
```

### Недостаточно памяти для Joern

```
java.lang.OutOfMemoryError: Java heap space
```

**Решение:** Увеличьте объём памяти:

```
python -m src.cli.import_commands full --repo ... --memory 32
```

### Язык не распознан

```
ValueError: No supported source files found
```

**Решение:** Укажите язык явно:

```
python -m src.cli.import_commands full --repo ... --language java
```

### Ошибка проверки CPG

```
Validation errors: ['methods_exist: expected >= 1, got 0']
```

**Решение:** Проверьте следующее:
1. Правильный ли путь к исходному коду
2. Соответствует ли интерфейс Joern языку исходного кода
3. Не исключаются ли файлы с помощью шаблонов

---

## Конфигурация (config.yaml)

Настройки модуля `project_import` в файле `config.yaml`:

```
project_import:
  joern:
    # Путь к локальной установке Joern (необязательно, если используется Docker)
    home: ${JOERN_HOME}
    # Использовать Docker вместо локальной установки Joern
    use_docker: false
    # Docker-образ для Joern
    docker_image: "ghcr.io/joernio/joern:latest"
    # Таймаут соединения с сервером (секунды)
    server_timeout: 30
    # Память JVM (ГБ)
    memory_gb: 16

  workspace:
    # Каталог для клонированных репозиториев
    clone_dir: "./workspace"
    # Каталог для файлов CPG
    cpg_dir: "./workspace"
    # Каталог для файлов DuckDB
    duckdb_dir: "./workspace"

  defaults:
    # Глубина по умолчанию для неглубокого клонирования
    shallow_depth: 1
    # Шаблоны исключения по умолчанию
    exclude_patterns:
      - "node_modules"
      - "venv"
      - ".venv"
      - "__pycache__"
      - ".git"
      - "test"
      - "tests"
      - "vendor"
      - "third_party"
```

---

## Архитектура компонентов

### JoernServerManager {#joernservermanager}

Центральный компонент для управления сервером Joern:

```
from src.project_import import JoernServerManager

# Создание менеджера
manager = JoernServerManager(use_docker=True)

# Запуск сервера
await manager.start()

# Получение клиента
client = manager.get_client()

# Остановка сервера
await manager.stop()
```

### ProjectRegistry {#projectregistry}

Реестр проектов в PostgreSQL:

```
from src.project_import import ProjectRegistry

async with ProjectRegistry() as registry:
    # Список проектов
    projects = await registry.list_projects()

    # Активация проекта
    await registry.set_active_project("my_project")

    # Удаление проекта
    await registry.delete_project("old_project", delete_files=True)
```

### LocalJoernRunner / DockerJoernRunner {#localjoernrunner-dockerjoernrunner}

Запускаторы для выполнения команд Joern:

```
# Локальное выполнение
from src.project_import import LocalJoernRunner
runner = LocalJoernRunner(joern_home="/path/to/joern")

# Выполнение в Docker
from src.project_import import DockerJoernRunner
runner = DockerJoernRunner(image="ghcr.io/joernio/joern:latest")

# Запуск frontend
await runner.run_frontend("pysrc2cpg", source_path, output_cpg)
```

---

## Смотрите также

- [Документация по REST API](../api/REST_API.md) - Точки доступа HTTP API
- [Справочник API](../reference/API.md) - Python API
- [Руководство по сценариям](SCENARIOS.md) - Сценарии анализа
