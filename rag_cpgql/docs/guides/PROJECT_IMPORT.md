# Импорт новой кодовой базы

Руководство по импорту новых проектов в систему RAG-CPGQL.

## Обзор

Система поддерживает автоматический импорт кодовых баз с различными языками программирования. Процесс включает:

1. **Clone** - клонирование репозитория
2. **Detect Language** - определение языка программирования
3. **Create CPG** - создание Code Property Graph через Joern
4. **Export to DuckDB** - экспорт графа в SQL базу
5. **Validate** - валидация целостности CPG
6. **Import Docs** - индексация документации в ChromaDB
7. **Create Plugin** - генерация Domain Plugin

---

## Поддерживаемые языки

| Язык | Joern Frontend | Расширения файлов | Описание |
|------|----------------|-------------------|----------|
| C/C++ | c2cpg | `.c`, `.h`, `.cpp`, `.hpp`, `.cc`, `.cxx` | Исходный код C/C++ |
| C# | csharp2cpg | `.cs` | Исходный код C# |
| Go | gosrc2cpg | `.go` | Исходный код Go |
| Java (source) | javasrc2cpg | `.java` | Исходный код Java |
| Java (bytecode) | java2cpg | `.class`, `.jar`, `.war` | Байткод Java |
| JavaScript/TypeScript | jssrc2cpg | `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs` | JavaScript/TypeScript |
| Kotlin | kotlin2cpg | `.kt`, `.kts` | Исходный код Kotlin |
| PHP | php2cpg | `.php` | Исходный код PHP |
| Python | pysrc2cpg | `.py`, `.pyw` | Исходный код Python |
| Ruby | rubysrc2cpg | `.rb` | Исходный код Ruby |
| Swift | swiftsrc2cpg | `.swift` | Исходный код Swift |
| Ghidra (binary) | ghidra2cpg | `.exe`, `.dll`, `.so`, `.dylib`, `.bin`, `.elf` | Анализ бинарных файлов |

---

## CLI Использование

### Полный pipeline (одна команда)

```bash
# Импорт из GitHub репозитория
python -m src.cli.import_commands full \
    --repo https://github.com/llvm/llvm-project \
    --branch main \
    --shallow \
    --language c

# Импорт локального проекта
python -m src.cli.import_commands full \
    --path /path/to/project \
    --language java

# С выборочным импортом (только определённые директории)
python -m src.cli.import_commands full \
    --repo https://github.com/llvm/llvm-project \
    --include llvm/lib llvm/include \
    --exclude test tests

# Импорт с использованием Docker
python -m src.cli.import_commands full \
    --repo https://github.com/example/project \
    --docker
```

### Docker Support

Система поддерживает запуск Joern в Docker-контейнере для кроссплатформенной работы:

```bash
# Импорт с Docker (без локальной установки Joern)
python -m src.cli.import_commands full \
    --repo https://github.com/example/project \
    --docker

# С указанием образа Docker
python -m src.cli.import_commands full \
    --repo https://github.com/example/project \
    --docker \
    --docker-image ghcr.io/joernio/joern:v4.0.0
```

**Преимущества Docker:**
- Не требуется локальная установка Joern
- Одинаковое поведение на всех платформах (Windows, Linux, macOS)
- Изолированная среда выполнения
- Автоматическое управление ресурсами

### Управление сервером Joern

```bash
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

```bash
# Список всех импортированных проектов
python -m src.cli.import_commands projects list

# Информация о проекте
python -m src.cli.import_commands projects info my_project

# Активация проекта (установка как текущий)
python -m src.cli.import_commands projects activate my_project

# Удаление проекта (только метаданные)
python -m src.cli.import_commands projects delete my_project

# Удаление проекта с файлами (CPG, DuckDB)
python -m src.cli.import_commands projects delete my_project --delete-files
```

### Пошаговый импорт

```bash
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

# 5. Валидация
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

```bash
python -m src.cli.import_commands languages
```

---

## REST API Использование

### Получить список поддерживаемых языков

```http
GET /api/v1/import/languages
```

**Ответ:**
```json
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

```http
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
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Import started. Use job_id to track progress."
}
```

### Проверка статуса импорта

```http
GET /api/v1/import/status/{job_id}
```

**Ответ:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "project_name": "llvm-project",
  "status": "in_progress",
  "steps": [
    {"name": "Clone Repository", "status": "completed", "progress": 100},
    {"name": "Detect Language", "status": "completed", "progress": 100},
    {"name": "Create CPG", "status": "in_progress", "progress": 45, "message": "Creating CPG nodes..."},
    {"name": "Export to DuckDB", "status": "pending", "progress": 0},
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

```http
GET /api/v1/import/jobs?status_filter=in_progress&limit=10
```

### Отмена импорта

```http
DELETE /api/v1/import/cancel/{job_id}
```

### Запуск отдельного шага

```http
POST /api/v1/import/step
Content-Type: application/json

{
  "step_id": "validate",
  "context": {
    "duckdb_path": "./workspace/project.duckdb"
  }
}
```

### Импорт с Docker

```http
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
```http
GET /api/v1/import/server/status
```

**Ответ:**
```json
{
  "status": "running",
  "mode": "docker",
  "container_id": "abc123",
  "port": 8080,
  "uptime_seconds": 3600
}
```

**Запустить сервер:**
```http
POST /api/v1/import/server/start
Content-Type: application/json

{
  "use_docker": true,
  "docker_image": "ghcr.io/joernio/joern:latest"
}
```

**Остановить сервер:**
```http
POST /api/v1/import/server/stop
```

### Управление проектами

**Список проектов:**
```http
GET /api/v1/import/projects
```

**Ответ:**
```json
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

**Активировать проект:**
```http
POST /api/v1/import/projects/{project_id}/activate
```

**Удалить проект:**
```http
DELETE /api/v1/import/projects/{project_id}?delete_files=true
```

---

## WebSocket для отслеживания прогресса

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/jobs/550e8400-e29b-41d4-a716-446655440000');

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);

  switch (msg.type) {
    case 'job.progress':
      console.log(`Progress: ${msg.payload.progress}% - ${msg.payload.message}`);
      break;
    case 'job.completed':
      console.log('Import completed:', msg.payload.result);
      break;
    case 'job.failed':
      console.error('Import failed:', msg.payload.error);
      break;
  }
};
```

---

## Параметры импорта

### Режимы импорта (mode)

| Режим | Описание |
|-------|----------|
| `full` | Полный импорт всей кодовой базы |
| `selective` | Импорт только указанных путей (`include_paths`) |
| `incremental` | Импорт только изменений с последнего импорта |

### Опции клонирования

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| `shallow_clone` | `true` | Использовать shallow clone |
| `shallow_depth` | `1` | Глубина shallow clone |
| `branch` | `"main"` | Ветка для клонирования |

### Опции Joern

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| `joern_memory_gb` | `16` | Память для Joern (GB) |
| `batch_size` | `10000` | Размер батча для экспорта в DuckDB |
| `use_docker` | `false` | Использовать Docker для Joern |
| `docker_image` | `ghcr.io/joernio/joern:latest` | Docker образ Joern |

### Опции документации

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| `import_docs` | `true` | Импортировать документацию |
| `import_readme` | `true` | Индексировать README файлы |
| `import_comments` | `true` | Импортировать комментарии из кода |

---

## Результат импорта

После успешного импорта создаются:

```
workspace/
├── llvm-project/           # Исходный код
├── llvm-project.cpg        # Joern CPG файл
└── llvm-project.duckdb     # DuckDB база (граф)

chromadb_storage/
└── llvm_project_documentation/  # ChromaDB коллекция

src/domains/
└── llvm_project/           # Domain Plugin
    ├── __init__.py
    ├── plugin.py
    ├── subsystems.yaml
    └── prompts.yaml
```

### Структура результата (ProjectImportResult)

```json
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
  "validation_report": {
    "status": "passed",
    "quality_score": 85
  },
  "detected_language": "c",
  "import_duration_seconds": 3600.5
}
```

---

## Валидация CPG

### Quality Score (0-100)

Оценка качества импортированного CPG:

| Критерий | Баллы |
|----------|-------|
| Методы найдены | +50 |
| Файлы привязаны к методам (>50%) | +20 |
| AST edges присутствуют | +8 |
| CFG edges присутствуют | +7 |
| Нет ошибок валидации | +15 |

### Проверяемые метрики

- `methods_exist` - количество методов
- `calls_exist` - количество вызовов
- `edges_ast` - AST рёбра
- `edges_cfg` - CFG рёбра
- `methods_with_files` - методы с привязкой к файлам

---

## Domain Plugin

Автоматически генерируется плагин для работы с новым проектом.

### Структура плагина

```python
# src/domains/llvm_project/plugin.py

class LlvmProjectPlugin(DomainPlugin):
    @property
    def name(self) -> str:
        return "llvm_project"

    @property
    def display_name(self) -> str:
        return "Llvm Project"

    def _load_subsystems(self) -> Dict[str, SubsystemInfo]:
        # Загрузка из subsystems.yaml
        ...

    def get_vulnerability_function_mappings(self) -> Dict[str, List[str]]:
        return {
            "buffer_overflow": ["strcpy", "memcpy", ...],
            "sql_injection": [...],
            ...
        }
```

### Конфигурация subsystems.yaml

```yaml
subsystems:
  core:
    description: "Core application logic"
    key_functions:
      - main
      - init
      - start
    patterns:
      - "src"
      - "lib"
    related_files: []

  utils:
    description: "Utility functions"
    key_functions: []
    patterns:
      - "util"
      - "helper"
```

### Конфигурация prompts.yaml

```yaml
prompts:
  onboarding:
    system: |
      You are a Llvm Project expert helping developers understand the codebase.
    user_template: |
      Help me understand the following aspect: {query}

  security:
    system: |
      You are a security expert analyzing Llvm Project (C) code.
    user_template: |
      Analyze the following code for security vulnerabilities:
      {code}
```

---

## Активация Domain Plugin

После создания плагина добавьте его в конфигурацию:

```yaml
# config.yaml
domains:
  active: "llvm_project"
  available:
    - postgresql
    - llvm_project
```

Или программно:

```python
from src.domains import DomainRegistry

DomainRegistry.activate("llvm_project")
```

---

## Обработка больших репозиториев

### LLVM (миллионы строк кода)

```bash
# Используйте shallow clone
python -m src.cli.import_commands full \
    --repo https://github.com/llvm/llvm-project \
    --shallow \
    --depth 1

# Или выборочный импорт
python -m src.cli.import_commands full \
    --repo https://github.com/llvm/llvm-project \
    --include llvm/lib/Target/X86 \
    --mode selective

# Увеличьте память для Joern
python -m src.cli.import_commands full \
    --repo https://github.com/llvm/llvm-project \
    --memory 32
```

### Рекомендации

1. **Используйте shallow clone** для экономии места и времени
2. **Выберите нужные директории** через `--include`
3. **Исключите тесты** через `--exclude test tests`
4. **Увеличьте память Joern** для больших проектов (16-32GB)

---

## Python API

```python
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
    language=SupportedLanguage.JAVA,  # или None для автоопределения
    mode=ImportMode.FULL,
    include_paths=["src/main"],
    exclude_paths=["src/test"],
    create_domain_plugin=True,
    import_docs=True,
)

# Запуск pipeline
async def run_import():
    def progress_callback(status):
        print(f"Progress: {status.overall_progress}% - {status.current_step}")

    pipeline = ProjectImportPipeline(progress_callback=progress_callback)
    result = await pipeline.run(request)

    print(f"CPG: {result.cpg_path}")
    print(f"DuckDB: {result.duckdb_path}")
    print(f"Language: {result.detected_language}")
    print(f"Quality Score: {result.validation_report['quality_score']}")

import asyncio
asyncio.run(run_import())
```

### Запуск отдельного шага

```python
from src.project_import.pipeline import ProjectImportPipeline

pipeline = ProjectImportPipeline()

# Контекст для шага
context = {
    "request": ProjectImportRequest(),
    "source_path": Path("./workspace/project"),
    "duckdb_path": "./workspace/project.duckdb",
}

# Запуск шага валидации
result = await pipeline.run_step("validate", context)
print(result["validation_report"])
```

---

## Troubleshooting

### Joern frontend не найден

```
RuntimeError: Frontend not found at expected paths
```

**Решение:** Проверьте `JOERN_HOME` или укажите явно:
```bash
export JOERN_HOME=/path/to/joern
python -m src.cli.import_commands full --repo ...
```

### Недостаточно памяти для Joern

```
java.lang.OutOfMemoryError: Java heap space
```

**Решение:** Увеличьте память:
```bash
python -m src.cli.import_commands full --repo ... --memory 32
```

### Не определён язык

```
ValueError: No supported source files found
```

**Решение:** Укажите язык явно:
```bash
python -m src.cli.import_commands full --repo ... --language java
```

### CPG validation failed

```
Validation errors: ['methods_exist: expected >= 1, got 0']
```

**Решение:** Проверьте:
1. Путь к исходному коду корректный
2. Joern frontend соответствует языку
3. Файлы не исключены паттернами

---

## Конфигурация (config.yaml)

Настройки модуля `project_import` в файле `config.yaml`:

```yaml
project_import:
  joern:
    # Путь к локальной установке Joern (необязательно если Docker)
    home: ${JOERN_HOME}
    # Использовать Docker вместо локального Joern
    use_docker: false
    # Docker образ для Joern
    docker_image: "ghcr.io/joernio/joern:latest"
    # Таймаут подключения к серверу (секунды)
    server_timeout: 30
    # Память для JVM (GB)
    memory_gb: 16

  workspace:
    # Директория для клонированных репозиториев
    clone_dir: "./workspace"
    # Директория для CPG файлов
    cpg_dir: "./workspace"
    # Директория для DuckDB файлов
    duckdb_dir: "./workspace"

  defaults:
    # Глубина shallow clone по умолчанию
    shallow_depth: 1
    # Паттерны исключений по умолчанию
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

### JoernServerManager

Центральный компонент для управления сервером Joern:

```python
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

### ProjectRegistry

Реестр проектов в PostgreSQL:

```python
from src.project_import import ProjectRegistry

async with ProjectRegistry() as registry:
    # Список проектов
    projects = await registry.list_projects()

    # Активация проекта
    await registry.set_active_project("my_project")

    # Удаление проекта
    await registry.delete_project("old_project", delete_files=True)
```

### LocalJoernRunner / DockerJoernRunner

Раннеры для выполнения Joern команд:

```python
# Локальный запуск
from src.project_import import LocalJoernRunner
runner = LocalJoernRunner(joern_home="/path/to/joern")

# Docker запуск
from src.project_import import DockerJoernRunner
runner = DockerJoernRunner(image="ghcr.io/joernio/joern:latest")

# Запуск frontend
await runner.run_frontend("pysrc2cpg", source_path, output_cpg)
```

---

## См. также

- [REST API Documentation](../api/REST_API.md) - HTTP API endpoints
- [API Reference](../reference/API.md) - Python API
- [Scenarios Guide](SCENARIOS.md) - Сценарии анализа
