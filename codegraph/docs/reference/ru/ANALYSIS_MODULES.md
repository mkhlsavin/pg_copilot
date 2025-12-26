# Справочник модулей анализа

Полная документация по модулям анализа кода в `src/analysis/`.

## Содержание

- [Обзор](#overview)
- [CFGAnalyzer](#cfganalyzer)
- [Возможности](#features)
- [Ключевые классы](#key-classes)
- [Справочник API](#api-reference)
- [Используемые таблицы базы данных](#database-tables-used)
- [FieldSensitiveTracer](#fieldsensitivetracer)
- [Возможности](#features)
- [Ключевые классы](#key-classes)
- [Справочник API](#api-reference)
- [Категории чувствительных полей](#sensitive-field-categories)
- [Используемые таблицы базы данных](#database-tables-used)
- [DataFlowTracer](#dataflowtracer)
- [Методы интеграции](#integration-methods)
- [ControlFlowAnalyzer (Проверка патчей)](#controlflowanalyzer-patch-review)
- [Возможности](#features)
- [Интеграция с CFGAnalyzer](#integration-with-cfganalyzer)
- [Классификация критичности циклов](#loop-severity-classification)
- [Примеры использования](#usage-examples)
- [Аудит безопасности (Сценарий 2)](#security-audit-scenario-2)
- [Анализ сложности (Сценарий 5/6)](#complexity-analysis-scenario-56)
- [Проверка патчей (Сценарий 9)](#patch-review-scenario-9)
- [Справочник схемы базы данных](#database-schema-reference)
- [Ключевые таблицы для анализа](#key-tables-for-analysis)
- [Типы рёбер для потока данных](#edge-types-for-dataflow)
- [Устранение неполадок](#troubleshooting)
- [“Метод не найден”](#method-not-found)
- [“Данные CFG не найдены”](#no-cfg-data-found)
- [“Доступы к полям не найдены”](#no-field-accesses-found)
- [Соображения по производительности](#performance-considerations)
- [См. также](#see-also)

## Обзор {#overview}

Модули анализа обеспечивают расширенные возможности статического анализа на основе CPG (графа свойств кода), хранящегося в DuckDB:

| Модуль | Назначение | Ключевые сценарии |
| --- | --- | --- |
| CFGAnalyzer | Анализ графа потока управления, метрики сложности | 5, 6, 13 (рефакторинг, производительность) |
| FieldSensitiveTracer | Отслеживание загрязнения с учётом полей объектов | 2, 8, 14 (безопасность, соответствие требованиям, расследование инцидентов) |
| DataFlowTracer | Универсальный интерфейс для анализа потоков данных | 2, 14 (безопасность, реагирование на инциденты) |
| CallGraphAnalyzer | Обход графа вызовов | 1, 12 (ввод в систему, пересечение репозиториев) |
| ConcurrencyAnalyzer | Обнаружение шаблонов блокировок/mutex’ов | 16 (параллелизм) |
| CloneDetector | Обнаружение дублированного кода | 7, 13 (рефакторинг) |

---

## CFGAnalyzer {#cfganalyzer}

**Файл:** `src/analysis/cfg_analyzer.py`

Анализ на основе графа потока управления (CFG) с использованием таблицы `edges_cfg` для точного анализа потока управления.

### Возможности {#features}

- **Цикломатическая сложность**: Сложность Маккейба по формуле `M = E - N + 2`
- **Перечисление путей**: Поиск путей выполнения на основе DFS с обнаружением циклов
- **Анализ доминаторов**: Построение деревьев доминаторов и пост-доминаторов
- **Извлечение структуры CFG**: Получение узлов, рёбер, точек входа и выхода

### Основные классы

```
@dataclass
class CFGStructure:
    """Описывает структуру CFG метода"""
    method_name: str
    method_full_name: str
    nodes: List[int]
    edges: List[Tuple[int, int]]  # пары (источник, назначение)
    entry_nodes: List[int]
    exit_nodes: List[int]
    node_count: int
    edge_count: int

@dataclass
class CFGPath:
    """Описывает путь выполнения в CFG"""
    path_id: str
    nodes: List[int]
    length: int
    has_loop: bool = False
```

### Справочник API {#api-reference}

#### CFGAnalyzer(cpg_service)

Инициализация с экземпляром CPGQueryService или подключением DuckDB.

#### get_method_cfg(method_name: str) -> Optional[CFGStructure]

Получить структуру CFG для метода.

```
from src.analysis.cfg_analyzer import CFGAnalyzer

analyzer = CFGAnalyzer(cpg_service)
cfg = analyzer.get_method_cfg("heap_insert")
print(f"Узлы: {cfg.node_count}, Рёбра: {cfg.edge_count}")
```

#### compute_cyclomatic_complexity(method_name: str) -> int

Вычислить цикломатическую сложность Маккейба: `M = E - N + 2`

```
complexity = analyzer.compute_cyclomatic_complexity("heap_insert")
print(f"Сложность: {complexity}")  # например, 15
```

#### enumerate_paths(method_name: str, max_paths: int = 100) -> List[CFGPath]

Найти пути выполнения в CFG с обнаружением циклов.

```
paths = analyzer.enumerate_paths("process_query", max_paths=50)
for path in paths:
    print(f"Путь {path.path_id}: {path.length} узлов, цикл={path.has_loop}")
```

#### find_dominators(method_name: str) -> Dict[int, Set[int]]

Построить дерево доминаторов с использованием таблицы `edges_dominate`.

#### find_post_dominators(method_name: str) -> Dict[int, Set[int]]

Построить дерево пост-доминаторов с использованием таблицы `edges_post_dominate`.

#### analyze_complexity_distribution() -> Dict[str, Any]

Проанализировать распределение сложности по всем методам в кодовой базе.

```
dist = analyzer.analyze_complexity_distribution()
print(f"Средняя сложность: {dist['average']}")
print(f"Методы с высокой сложностью: {dist['high_complexity_methods']}")
```

### Используемые таблицы базы данных {#database-tables-used}

- `nodes_method` — Метаданные методов
- `edges_contains` — Связи методов с узлами
- `edges_cfg` — Рёбра графа потока управления (CFG) между узлами
- `edges_dominate` — Отношения доминирования
- `edges_post_dominate` — Отношения пост-доминирования

---

## FieldSensitiveTracer {#fieldsensitivetracer}

**Файл:** `src/analysis/field_sensitive_tracer.py`

Отслеживание путей полей для точного анализа заражения (taint analysis), с различением различных полей одного и того же объекта.

### Возможности

- **Разбор путей к полям**: Обработка цепочек вида `obj.field1.field2` и `obj->field->data`
- **Отслеживание доступа к полям**: Поиск всех чтений/записей в конкретные поля
- **Распространение заражения**: Отслеживание заражённых данных через доступ к полям
- **Обнаружение чувствительных полей**: Выявление потоков данных из чувствительных полей (пароль, токен и т.д.)

### Основные классы

```
@dataclass
class FieldPath:
    """Представляет путь доступа к полю, например obj.field1.field2"""
    base_variable: str
    field_chain: List[str]
    full_path: str
    node_ids: List[int]
    type_full_name: Optional[str]

@dataclass
class FieldAccess:
    """Представляет один доступ к полю в коде"""
    node_id: int
    base_variable: str
    field_name: str
    access_code: str
    line_number: int
    filename: str
    access_type: str  # 'read', 'write', 'call'
    containing_method: Optional[str]

@dataclass
class FieldSensitiveFlow:
    """Путь передачи данных с учётом полей"""
    source_path: FieldPath
    sink_path: FieldPath
    intermediate_fields: List[FieldPath]
    is_tainted: bool
    relationship: str  # 'exact', 'prefix', 'suffix', 'propagated'
    confidence: float
```

### Справочник API

#### FieldSensitiveTracer(cpg_service)

Инициализация с CPGQueryService или подключением DuckDB.

#### parse_field_path(code: str) -> FieldPath

Разбирает строку доступа к полю в структурированный объект `FieldPath`.

```
from src.analysis.field_sensitive_tracer import FieldSensitiveTracer

tracer = FieldSensitiveTracer(cpg_service)

# Разбор нотации указателей {#parse-pointer-notation}
path = tracer.parse_field_path("user->password")
print(path.base_variable)  # "user"
print(path.field_chain)    # ["password"]

# Разбор нотации через точку {#parse-dot-notation}
path = tracer.parse_field_path("request.data.buffer")
print(path.full_path)  # "request.data.buffer"
```

#### get_struct_fields(struct_name: str) -> List[Dict]

Получает поля, определённые в структуре, с информацией о типах.

```
fields = tracer.get_struct_fields("UserData")
for field in fields:
    print(f"{field['name']}: {field['type']}")
```

#### find_field_accesses(base_var: str, field_name: str) -> List[FieldAccess]

Находит все обращения к конкретному полю.

```
accesses = tracer.find_field_accesses("user", "password")
for access in accesses:
    print(f"{access.filename}:{access.line_number} - {access.access_type}")
```

#### trace_field_taint(source_field: str, sink_functions: List[str]) -> List[FieldSensitiveFlow]

Отслеживает заражение от исходного поля до функций-приёмников (sinks).

```
flows = tracer.trace_field_taint(
    source_field="credentials->password",
    sink_functions=["printf", "log", "send"]
)
for flow in flows:
    print(f"Заражённый поток: {flow.source_path} -> {flow.sink_path}")
```

#### find_sensitive_field_flows(sensitive_fields: List[str] = None, sink_functions: List[str] = None) -> List[FieldSensitiveFlow]

Находит потоки данных из чувствительных полей в опасные приёмники.

```
# Чувствительные поля по умолчанию: password, token, secret, private_key, credential, auth {#default-sensitive-fields-password-token-secret-private-key-credential-auth}
flows = tracer.find_sensitive_field_flows()
print(f"Найдено {len(flows)} потенциальных утечек чувствительных данных")
```

### Категории чувствительных полей {#sensitive-field-categories}

Чувствительные поля, отслеживаемые по умолчанию:
- `password`, `passwd`, `pwd`
- `token`, `auth_token`, `access_token`
- `secret`, `api_secret`, `client_secret`
- `private_key`, `secret_key`
- `credential`, `credentials`
- `auth`, `authorization`

### Используемые таблицы базы данных

- `nodes_field_identifier` — узлы доступа к полям
- `nodes_identifier` — идентификаторы переменных
- `nodes_member` — определения полей структур
- `edges_reaching_def` — рёбра достижимых определений
- `edges_argument` — рёбра аргументов функций

---

## DataFlowTracer {#dataflowtracer}

**Файл:** `src/analysis/dataflow_tracer.py`

Фасадный модуль, предоставляющий единый интерфейс к возможностям анализа потоков данных.

### Методы интеграции {#integration-methods}

DataFlowTracer обеспечивает интеграцию базового анализа потоков данных и анализа с учётом полей:

#### find_taint_paths_field_sensitive(source_functions, sink_functions, track_fields=True, max_depth=10) -> List[DataFlowPath]

Расширенный анализ заражения (taint analysis) с опциональным отслеживанием полей.

```
from src.analysis.dataflow_tracer import DataFlowTracer

tracer = DataFlowTracer(cpg_service)

# Поиск путей заражения с учётом полей {#find-taint-paths-with-field-sensitivity}
paths = tracer.find_taint_paths_field_sensitive(
    source_functions=["getenv", "fgets", "read"],
    sink_functions=["system", "exec", "popen"],
    track_fields=True,
    max_depth=10
)

for path in paths:
    print(f"Источник: {path.source} -> Приёмник: {path.sink}")
    print(f"Обращения к полям: {path.field_accesses}")
```

#### find_sensitive_data_flows(sensitive_fields=None, sink_functions=None) -> List[Dict]

Обёртка вокруг FieldSensitiveTracer для типовых задач анализа безопасности.

```
# Использование значений по умолчанию для распространённых шаблонов {#use-defaults-for-common-patterns}
flows = tracer.find_sensitive_data_flows()

# Или с настройкой под задачу {#or-customize}
flows = tracer.find_sensitive_data_flows(
    sensitive_fields=["api_key", "bearer_token"],
    sink_functions=["http_request", "socket_send"]
)
```

---

## ControlFlowAnalyzer (Просмотр изменений)

**Файл:** `src/patch_review/analyzers/control_flow_analyzer.py`

Анализирует влияние изменений на поток управления, теперь с использованием CFGAnalyzer для точного расчёта метрик.

### Возможности

- Расчёт дельты сложности (до/после внесения изменений)
- Обнаружение новых циклов с классификацией рисков
- Отслеживание изменений в обработке ошибок
- Оценка влияния на покрытие ветвлений

### Интеграция с CFGAnalyzer {#integration-with-cfganalyzer}

```
from src.patch_review.analyzers.control_flow_analyzer import PatchControlFlowAnalyzer

analyzer = PatchControlFlowAnalyzer(cpg_service)

# Анализ влияния изменений {#analyze-patch-impact}
result = analyzer.analyze_control_flow_changes(patch_data)

print(f"Дельта сложности: {result.complexity_delta}")
print(f"Новые циклы: {len(result.new_loops)}")
print(f"Изменения в обработке ошибок: {len(result.error_handling_changes)}")
```

### Классификация серьёзности циклов

Новые циклы классифицируются по уровню риска:
- **HIGH** (Высокий): Вложенные циклы, циклы с операциями ввода-вывода, неограниченные циклы
- **MEDIUM** (Средний): Циклы с внешними вызовами
- **LOW** (Низкий): Простые ограниченные циклы

---

## Примеры использования {#usage-examples}

### Аудит безопасности (Сценарий 2) {#security-audit-scenario-2}

```
from src.analysis.field_sensitive_tracer import FieldSensitiveTracer

tracer = FieldSensitiveTracer(cpg_service)

# Поиск утечек паролей {#find-password-leaks}
flows = tracer.find_sensitive_field_flows(
    sensitive_fields=["password", "credentials"],
    sink_functions=["printf", "fprintf", "syslog", "elog"]
)

for flow in flows:
    print(f"ОПАСНО: {flow.source_path} попадает в {flow.sink_path}")
```

### Анализ сложности (Сценарий 5/6) {#complexity-analysis-scenario-56}

```
from src.analysis.cfg_analyzer import CFGAnalyzer

analyzer = CFGAnalyzer(cpg_service)

# Анализ всех методов {#analyze-all-methods}
dist = analyzer.analyze_complexity_distribution()

# Поиск кандидатов на рефакторинг {#find-refactoring-candidates}
for method in dist['high_complexity_methods']:
    print(f"Кандидат на рефакторинг: {method['name']} (сложность={method['complexity']})")
```

### Проверка патча (Сценарий 9)

```
from src.patch_review.analyzers.control_flow_analyzer import PatchControlFlowAnalyzer

analyzer = PatchControlFlowAnalyzer(cpg_service)
result = analyzer.analyze_control_flow_changes(patch)

if result.complexity_delta > 10:
    print("ВНИМАНИЕ: Значительное увеличение сложности")

for loop in result.new_loops:
    if loop.severity == 'HIGH':
        print(f"ОПАСНО: Цикл высокого риска в методе {loop.method_name}")
```

## Справочник по схеме базы данных {#database-schema-reference}

### Основные таблицы для анализа {#key-tables-for-analysis}

| Таблица | Назначение |
| --- | --- |
| nodes_method | Определения методов |
| nodes_control_structure | Структуры управления потоком выполнения (if, for, while) |
| nodes_field_identifier | Выражения доступа к полям |
| nodes_identifier | Ссылки на переменные |
| edges_cfg | Рёбра графа потока управления |
| edges_contains | Отношения вложенности (содержимое) |
| edges_dominate | Отношения доминирования |
| edges_reaching_def | Рёбра достижимых определений |
| edges_argument | Рёбра аргументов функций |

### Типы рёбер для анализа потока данных {#edge-types-for-dataflow}

| Тип ребра | Таблица | Назначение |
| --- | --- | --- |
| CFG | edges_cfg | Поток управления между операторами |
| REACHING_DEF | edges_reaching_def | Цепочки «определение — использование» |
| ARGUMENT | edges_argument | Аргументы вызова функций |
| CONTAINS | edges_contains | Вложенность областей видимости |

## Устранение неполадок {#troubleshooting}

### “Метод не найден” {#method-not-found}

Имя метода должно совпадать точно (с учетом регистра). Используйте простое имя, а не полное квалифицированное.

```
# Правильно {#correct}
cfg = analyzer.get_method_cfg("heap_insert")

# Неправильно {#incorrect}
cfg = analyzer.get_method_cfg("heap_insert(Relation, HeapTuple)")
```

### “Данные CFG не найдены” {#no-cfg-data-found}

Убедитесь, что экспорт CPG включал ребра CFG. Проверьте, есть ли данные в таблице `edges_cfg`:

```
SELECT COUNT(*) FROM edges_cfg;
```

### “Обращения к полям не найдены”

Для отслеживания обращений к полям необходимы данные `nodes_field_identifier`:

```
SELECT COUNT(*) FROM nodes_field_identifier;
```

### Рекомендации по производительности

- Перечисление путей ограничено параметром `max_paths`, чтобы предотвратить экспоненциальный рост
- Используйте `max_depth` для ограничения глубины отслеживания передачи зараженных данных (taint)
- В больших методах может быть очень много путей; рассмотрите возможность выборки

## Смотрите также

- [Справочник по схеме](SCHEMA.md) — Полная схема базы данных
- [Кулинарная книга SQL-запросов](SQL_QUERY_COOKBOOK.md) — Примеры запросов
- [Справочник по агентам](AGENTS.md) — Конвейер агентов
- [Руководство по сценариям](../guides/SCENARIOS.md) — Сценарии использования
