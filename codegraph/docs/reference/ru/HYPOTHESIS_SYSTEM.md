# Справочная система гипотез

В этом документе описывается многокритериальная система формирования и проверки гипотез безопасности, используемая для автоматического обнаружения уязвимостей в CodeGraph.

## Содержание

- [Обзор](#overview)
- [Архитектура конвейера](#pipeline-architecture)
- [Основные модели данных](#core-data-models)
- [SecurityHypothesis](#securityhypothesis)
- [Evidence](#evidence)
- [ValidationStatus](#validationstatus)
- [Уровни серьёзности](#severity-levels)
- [Генерация гипотез](#hypothesis-generation)
- [Формат шаблона](#template-format)
- [Шаблоны категорий](#category-templates)
- [Алгоритм генерации](#generation-algorithm)
- [Сопоставление категорий CWE](#cwe-category-mapping)
- [Многокритериальная оценка](#multi-criteria-scoring)
- [Формула оценки](#scoring-formula)
- [Компоненты оценки](#score-components)
- [Множители бонусов](#bonus-multipliers)
- [Использование](#usage)
- [Синтез запросов](#query-synthesis)
- [Шаблоны SQL](#sql-templates)
- [Примеры шаблонов](#template-examples)
- [Выполнение гипотез](#hypothesis-execution)
- [Использование исполнителя](#executor-usage)
- [Сбор доказательств](#evidence-collection)
- [Проверка](#validation)
- [Процесс проверки](#validation-process)
- [Результаты проверки](#validation-results)
- [База знаний](#knowledge-base)
- [База данных CWE](#cwe-database)
- [Языковые шаблоны](#language-patterns)
- [Поддерживаемые CWE (частичный список)](#supported-cwes-partial-list)
- [Python API](#python-api)
- [Полный пример](#complete-example)
- [Производительность](#performance)
- [Результаты тестирования](#benchmark-results)
- [Проверенные CVE (PostgreSQL 17)](#validated-cves-postgresql-17)
- [См. также](#see-also)

## Обзор {#overview}

Система гипотез формирует проверяемые гипотезы безопасности, комбинируя:

- **Шаблоны уязвимостей CWE** (Common Weakness Enumeration — Перечень типовых уязвимостей)
- **Шаблоны атак CAPEC** (Common Attack Pattern Enumeration — Перечень типовых атак)
- **Языковые шаблоны** (стоки, источники, средства санации)
- **Контекст кодовой базы** (на основе анализа CPG)

### Архитектура конвейера {#pipeline-architecture}

```
+-----------------------------------------------------------+
|                  КОНВЕЙЕР ГИПОТЕЗ                           |
+-----------------------------------------------------------+

1. ГЕНЕРАЦИЯ
   HypothesisGenerator.generate()
   +-- База данных CWE (более 120 шаблонов)
   +-- База данных CAPEC (более 50 шаблонов атак)
   +-- Языковые шаблоны (C, Python, Java)
   +-- Декартово произведение: CWE × CAPEC × шаблоны
   +-- Инстанцирование шаблонов
   +-- Результат: SecurityHypothesis[]

2. ОЦЕНКА
   MultiCriteriaScorer.score_batch()
   +-- Оценка частоты CWE (вес 0,40)
   +-- Оценка схожести атаки (вес 0,30)
   +-- Оценка экспозиции кодовой базы (вес 0,30)
   +-- Бонусы: наличие известных CVE, критическая серьёзность
   +-- Результат: приоритетные оценки [0,0–1,0]

3. СИНТЕЗ ЗАПРОСОВ
   QuerySynthesizer.synthesize()
   +-- Сопоставление гипотезы с шаблоном SQL
   +-- Подстановка параметров
   +-- Результат: SQL-запросы DuckDB / PGQ

4. ВЫПОЛНЕНИЕ
   HypothesisExecutor.execute()
   +-- Выполнение запросов к CPG
   +-- Сбор доказательств
   +-- Результат: Evidence[]

5. ВАЛИДАЦИЯ
   HypothesisValidator.validate()
   +-- Анализ доказательств
   +-- Обновление статуса гипотезы
   +-- Расчёт метрик
   +-- Результат: ValidationResults
```

## Основные модели данных {#core-data-models}

### SecurityHypothesis {#securityhypothesis}

Центральная структура данных для анализа безопасности на основе гипотез.

```
@dataclass
class SecurityHypothesis:
    id: str                          # Уникальный идентификатор
    hypothesis_text: str             # Читаемое утверждение

    # Классификация
    cwe_ids: List[str]              # ["CWE-120", "CWE-119"]
    capec_ids: List[str]            # ["CAPEC-100"]
    language: str                   # "C", "Python" и т.д.
    category: str                   # "buffer_overflow", "injection"

    # Шаблоны передачи заражённых данных (taint)
    source_patterns: List[str]      # ["PQgetvalue", "getenv"]
    sink_patterns: List[str]        # ["strcpy", "memcpy"]
    sanitizer_patterns: List[str]   # ["strlcpy", "sizeof"]

    # Оценки
    priority_score: float           # 0.0–1.0, общая важность
    confidence: float               # 0.0–1.0, достоверность гипотезы

    # Детализация по нескольким критериям
    cwe_frequency_score: float
    attack_similarity_score: float
    codebase_exposure_score: float

    # Сгенерированный SQL-запрос
    sql_query: Optional[str]

    # Подтверждение
    evidence: List[Evidence]
    validation_status: ValidationStatus
```

### Evidence {#evidence}

Содержит результаты запросов, подтверждающие или опровергающие гипотезу.

```
@dataclass
class Evidence:
    id: str
    hypothesis_id: str
    query_executed: str             # SQL-запрос, который нашёл это
    result_count: int
    findings: List[Dict[str, Any]]  # Результаты запроса
    filename: Optional[str]
    line_number: Optional[int]
    code_snippet: Optional[str]
    confidence: float               # 0.0–1.0
```

### ValidationStatus {#validationstatus}

```
class ValidationStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"
```

### Уровни серьёзности {#severity-levels}

```
class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
```

---

## Генерация гипотез {#hypothesis-generation}

### Формат шаблона {#template-format}

Гипотезы следуют шаблону:

```
"Если [источник] передаёт данные в [приёмник] без [средства очистки], то [CWE] позволяет осуществить [атаку]"
```

### Шаблоны категорий {#category-templates}

| Категория | Шаблон |
| --- | --- |
| buffer_overflow | “Если недоверённые данные из {sources} передаются в {sinks} без проверки границ через {sanitizers}, то {cwe} позволяет осуществить атаку {attack}, потенциально приводящую к повреждению памяти или выполнению кода.” |
| sql_injection | “Если пользовательский ввод из {sources} включается в SQL-запросы через {sinks} без параметризации ({sanitizers}), то {cwe} позволяет осуществить атаку {attack}.” |
| command_injection | “Если недоверённые данные из {sources} передаются в выполнение команд через {sinks} без надлежащего экранирования ({sanitizers}), то {cwe} позволяет осуществить атаку {attack}.” |
| information_disclosure | “Если к конфиденциальным данным осуществляется доступ через {sinks} без проверки авторизации ({sanitizers}), то {cwe} позволяет осуществить атаку {attack}.” |

### Алгоритм генерации {#generation-algorithm}

```
from src.security.hypothesis import HypothesisGenerator

generator = HypothesisGenerator()

# Генерация для конкретного CWE {#generate-for-specific-cwe}
hypotheses = generator.generate(
    language="C",
    cwe_filter=["CWE-120", "CWE-78"],
    max_hypotheses=50
)

# Генерация по категории {#generate-for-category}
buffer_hypotheses = generator.generate_by_category("buffer_overflow")

# Полное перечисление {#full-enumeration}
all_hypotheses = generator.generate_all(language="C")
```

### Сопоставление CWE и категорий {#cwe-category-mapping}

| CWE | Категория |
| --- | --- |
| CWE-120, CWE-119, CWE-787, CWE-125 | buffer_overflow |
| CWE-78, CWE-77, CWE-88 | command_injection |
| CWE-89 | sql_injection |
| CWE-94, CWE-95 | code_injection |
| CWE-134 | format_string |
| CWE-200, CWE-209, CWE-862 | information_disclosure |
| CWE-416 | use_after_free |
| CWE-190, CWE-191 | integer_overflow |

---

## Многокритериальная оценка {#multi-criteria-scoring}

### Формула оценки {#scoring-formula}

```
Приоритет = (Частота_CWE × 0.40)
          + (Схожесть_атаки × 0.30)
          + (Экспозиция_кода × 0.30)
```

### Компоненты оценки {#score-components}

| Компонент | Вес | Описание |
| --- | --- | --- |
| Частота CWE | 0.40 | Насколько часто данный CWE встречается в базе CVE |
| Схожесть атаки | 0.30 | Насколько атака похожа на известные шаблоны атак |
| Экспозиция кодовой базы | 0.30 | Насколько широко кодовая база подвержена воздействию |

### Бонусные множители

| Бонус | Множитель | Условие |
| --- | --- | --- |
| Известный CVE | 1.20 (+20%) | Соответствует известному шаблону CVE |
| Критическая серьёзность | 1.10 (+10%) | CWE критической степени серьёзности |
| Недавнее использование | 1.15 (+15%) | Недавно использовался в реальных атаках |

### Использование {#usage}

```
from src.security.hypothesis import MultiCriteriaScorer, CodebaseStats

# Сбор статистики по кодовой базе {#gather-codebase-statistics}
stats = CodebaseStats(
    total_methods=52000,
    total_calls=110000,
    sink_counts={"strcpy": 150, "memcpy": 800},
    source_counts={"getenv": 50, "recv": 30}
)

# Оценка гипотез {#score-hypotheses}
scorer = MultiCriteriaScorer(weights={
    'cwe_frequency': 0.40,
    'attack_similarity': 0.30,
    'codebase_exposure': 0.30
})

scored_hypotheses = scorer.score_batch(hypotheses, stats)

# Получение наиболее приоритетных {#get-top-priority}
top_10 = sorted(scored_hypotheses, key=lambda h: h.priority_score, reverse=True)[:10]
```

## Синтез запросов {#query-synthesis}

### Шаблоны SQL {#sql-templates}

Система генерирует запросы DuckDB SQL для каждой категории гипотез:

```
from src.security.hypothesis import QuerySynthesizer

synthesizer = QuerySynthesizer()
query = synthesizer.synthesize_query(hypothesis)
```

### Примеры шаблонов {#template-examples}

**Обнаружение переполнения буфера:**

```
SELECT DISTINCT nc.id, nc.name AS sink_function, nc.code,
       nc.filename, nc.line_number
FROM nodes_call nc
WHERE nc.name IN ('strcpy', 'strcat', 'sprintf', 'memcpy')
LIMIT 100;
```

**Обнаружение инъекции команд:**

```
SELECT DISTINCT nc.id, nc.name AS sink_function, nc.code,
       nc.filename, nc.line_number
FROM nodes_call nc
WHERE nc.name IN ('system', 'popen', 'execl', 'execv')
LIMIT 100;
```

**Анализ потока данных с использованием SQL/PGQ:**

```
FROM GRAPH_TABLE(cpg
    MATCH (src:IDENTIFIER)-[:REACHING_DEF*1..5]->(sink:CALL_NODE)
    WHERE src.name IN ('user_input', 'request')
      AND sink.name IN ('execute', 'query')
    COLUMNS (
        src.name AS source_var,
        sink.name AS sink_function,
        sink.filename,
        sink.line_number
    )
)
LIMIT 100;
```

---

## Выполнение гипотезы {#hypothesis-execution}

### Использование исполнителя {#executor-usage}

```
from src.security.hypothesis import HypothesisExecutor
import duckdb

conn = duckdb.connect("cpg.duckdb")
executor = HypothesisExecutor(conn)

# Выполнить одну гипотезу {#execute-single-hypothesis}
evidence = executor.execute(hypothesis)

# Выполнить пакетно {#execute-batch}
results = executor.execute_batch(hypotheses, parallel=True)
```

### Сбор доказательств {#evidence-collection}

Для каждого выполняемого запроса:
1. Выполнить SQL-запрос к CPG
2. Зафиксировать количество результатов и найденные фрагменты
3. Извлечь имя файла, номер строки, фрагмент кода
4. Рассчитать уровень достоверности доказательства
5. Связать доказательства с гипотезой

---

## Валидация

### Процесс валидации

```
from src.security.hypothesis import HypothesisValidator

validator = HypothesisValidator()

# Валидация одной гипотезы {#validate-single-hypothesis}
validator.validate(hypothesis)

# Валидация пакета {#validate-batch}
results = validator.validate_batch(hypotheses)
```

### Результаты валидации

```
@dataclass
class ValidationResults:
    batch_id: str
    total_hypotheses: int
    executed_queries: int

    # Метрики обнаружения CVE
    cves_found: List[str]
    cves_missed: List[str]

    # Точность/полнота
    true_positives: int
    false_positives: int
    false_negatives: int

    # Качество гипотез
    confirmed_hypotheses: int
    rejected_hypotheses: int
    inconclusive_hypotheses: int

    # Вычисляемые метрики
    @property
    def detection_rate(self) -> float: ...
    @property
    def precision(self) -> float: ...
    @property
    def recall(self) -> float: ...
    @property
    def f1_score(self) -> float: ...
```

---

## База знаний {#knowledge-base}

### База данных CWE {#cwe-database}

```
from src.security.hypothesis import get_knowledge_base

kb = get_knowledge_base()

# Получение записи CWE {#get-cwe-entry}
cwe = kb.get_cwe("CWE-120")
print(f"Название: {cwe.name}")
print(f"Серьёзность: {cwe.severity}")
print(f"CVSS: {cwe.cvss_base}")

# Получение по категории {#get-by-category}
memory_cwes = kb.get_cwes_by_category("memory")

# Получение связанных CAPEC {#get-related-capecs}
capecs = kb.get_capecs_for_cwe("CWE-120")
```

### Языковые паттерны

```
# Получение паттернов для C {#get-c-patterns}
c_patterns = kb.get_language_patterns("C")

for pattern in c_patterns:
    print(f"Категория: {pattern.category}")
    print(f"Приёмники: {pattern.sinks}")
    print(f"Источники: {pattern.sources}")
    print(f"Санитайзеры: {pattern.sanitizers}")
```

### Поддерживаемые CWE (частичный список) {#supported-cwes-partial-list}

| CWE ID | Название | Серьёзность | CVSS |
| --- | --- | --- | --- |
| CWE-120 | Копирование буфера без проверки размера | ВЫСОКАЯ | 8.0 |
| CWE-119 | Недостаточное ограничение операций | ВЫСОКАЯ | 8.0 |
| CWE-78 | Инъекция команд ОС | КРИТИЧЕСКАЯ | 9.8 |
| CWE-89 | SQL-инъекция | КРИТИЧЕСКАЯ | 9.8 |
| CWE-200 | Раскрытие конфиденциальной информации | СРЕДНЯЯ | 5.3 |
| CWE-416 | Использование после освобождения | ВЫСОКАЯ | 8.1 |
| CWE-190 | Переполнение целого числа | ВЫСОКАЯ | 7.5 |

---

## Python API {#python-api}

### Полный пример {#complete-example}

```
from src.security.hypothesis import (
    HypothesisGenerator,
    MultiCriteriaScorer,
    QuerySynthesizer,
    HypothesisExecutor,
    HypothesisValidator,
    CodebaseStats
)
import duckdb

# 1. Подключение к CPG {#1-connect-to-cpg}
conn = duckdb.connect("cpg.duckdb")

# 2. Сбор статистики по кодовой базе {#2-gather-codebase-statistics}
stats = CodebaseStats(
    total_methods=conn.execute("SELECT COUNT(*) FROM nodes_method").fetchone()[0],
    total_calls=conn.execute("SELECT COUNT(*) FROM nodes_call").fetchone()[0]
)

# 3. Генерация гипотез {#3-generate-hypotheses}
generator = HypothesisGenerator()
hypotheses = generator.generate(language="C", max_hypotheses=100)

# 4. Оценка и приоритизация {#4-score-and-prioritize}
scorer = MultiCriteriaScorer()
scored = scorer.score_batch(hypotheses, stats)

# 5. Генерация SQL-запросов {#5-synthesize-sql-queries}
synthesizer = QuerySynthesizer()
for h in scored:
    h.sql_query = synthesizer.synthesize_query(h)

# 6. Выполнение запросов к CPG {#6-execute-against-cpg}
executor = HypothesisExecutor(conn)
for h in scored[:20]:  # Топ-20
    evidence = executor.execute(h)
    h.evidence.extend(evidence)

# 7. Проверка и отчёт {#7-validate-and-report}
validator = HypothesisValidator()
results = validator.validate_batch(scored)

print(f"Частота обнаружения: {results.detection_rate:.1%}")
print(f"Точность: {results.precision:.1%}")
print(f"Полнота: {results.recall:.1%}")
print(f"F1-мера: {results.f1_score:.2f}")
```

---

## Производительность {#performance}

### Результаты тестирования {#benchmark-results}

| Метрика | Значение |
| --- | --- |
| Уровень обнаружения уязвимостей CVE | 100% (3 из 3 целевых CVE) |
| Уровень подтверждения гипотез | 55% |
| Среднее время запроса | 2–3 мс |
| Время генерации (100 гипотез) | <1 с |
| Время выполнения (20 гипотез) | <30 с |

### Подтверждённые уязвимости CVE (PostgreSQL 17) {#validated-cves-postgresql-17}

| CVE | Тип | Метод обнаружения |
| --- | --- | --- |
| CVE-2025-8713 | Раскрытие статистики | Гипотеза + метод |
| CVE-2025-8714 | Инъекция в pg_dump | На основе метода |
| CVE-2025-8715 | Инъекция символа новой строки | На основе метода |

---

## См. также {#see-also}

- [Руководство по экспорту CPG](../guides/CPG_EXPORT.md) — экспорт CPG для анализа
- [Кулинарная книга SQL-запросов](./SQL_QUERY_COOKBOOK.md) — примеры запросов
- [Модули анализа](./ANALYSIS_MODULES.md) — документация по расширенному анализу
- [База данных CWE](https://cwe.mitre.org/)
- [База данных CAPEC](https://capec.mitre.org/)
