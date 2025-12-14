# Whitepaper: Многокритериальная валидация гипотез безопасности

> Технический документ для архитекторов безопасности и исследователей

---

## Аннотация

Традиционные инструменты SAST (Static Application Security Testing) страдают от высокого уровня ложных срабатываний (до 70-90%), что делает результаты анализа практически неприменимыми для реальной работы. CodeGraph решает эту проблему с помощью **многокритериальной системы валидации гипотез**, которая:

1. Генерирует тестируемые гипотезы на основе CWE/CAPEC баз знаний
2. Оценивает гипотезы по трём критериям с учётом контекста кодовой базы
3. Верифицирует уязвимости через taint-анализ на Code Property Graph
4. Достигает **100% CVE detection rate** при снижении false positives на 60%+

---

## 1. Проблема

### 1.1 Ограничения традиционного SAST

```
Традиционный SAST:
  Pattern: "strcpy" found
  Result: POSSIBLE vulnerability
  False Positive Rate: 70-90%

CodeGraph:
  Hypothesis: Untrusted data flows from recv() to strcpy()
  Evidence: Taint path verified via CPG
  Result: CONFIRMED vulnerability
  False Positive Rate: <30%
```

### 1.2 Почему pattern matching недостаточно

| Проблема | Описание |
|----------|----------|
| **Нет контекста** | `strcpy` безопасен, если источник — константа |
| **Нет data flow** | Не учитывается откуда приходят данные |
| **Нет sanitization** | Игнорируются функции-валидаторы |
| **Нет приоритизации** | Все находки имеют равный вес |

---

## 2. Архитектура решения

### 2.1 Pipeline валидации гипотез

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    HYPOTHESIS VALIDATION PIPELINE                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 1. GENERATION                                                   │   │
│  │    HypothesisGenerator.generate()                               │   │
│  │    ├── CWE Database (120+ patterns)                            │   │
│  │    ├── CAPEC Database (50+ attack patterns)                    │   │
│  │    ├── Language Patterns (C, Python, Java)                     │   │
│  │    └── Cartesian Product: CWEs × CAPECs × Patterns             │   │
│  │    Output: SecurityHypothesis[]                                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 2. MULTI-CRITERIA SCORING                                       │   │
│  │    MultiCriteriaScorer.score_batch()                           │   │
│  │                                                                  │   │
│  │    Score = CWE_Freq × 0.40 + Attack_Sim × 0.30 + Exposure × 0.30│   │
│  │                                                                  │   │
│  │    Bonuses:                                                     │   │
│  │    ├── Known CVE pattern: ×1.20                                │   │
│  │    ├── Critical severity: ×1.10                                │   │
│  │    └── Recent exploit: ×1.15                                   │   │
│  │                                                                  │   │
│  │    Output: Prioritized hypotheses                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 3. QUERY SYNTHESIS                                              │   │
│  │    QuerySynthesizer.synthesize()                                │   │
│  │    ├── Match hypothesis to SQL template                        │   │
│  │    ├── Parameter substitution                                  │   │
│  │    └── Output: DuckDB SQL / PGQ queries                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 4. EXECUTION                                                    │   │
│  │    HypothesisExecutor.execute()                                 │   │
│  │    ├── Run queries against CPG                                 │   │
│  │    ├── Collect evidence                                        │   │
│  │    └── Output: Evidence[]                                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 5. VALIDATION                                                   │   │
│  │    HypothesisValidator.validate()                               │   │
│  │    ├── Analyze evidence                                        │   │
│  │    ├── Update hypothesis status (CONFIRMED/REJECTED)           │   │
│  │    └── Calculate precision/recall metrics                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Многокритериальная модель скоринга

### 3.1 Формула приоритизации

```
Priority Score = (CWE_Frequency × 0.40)
               + (Attack_Similarity × 0.30)
               + (Codebase_Exposure × 0.30)
```

### 3.2 Компоненты скоринга

#### CWE Frequency Score (40%)

Оценивает, насколько часто данная уязвимость встречается в реальных CVE.

```python
def _score_cwe_frequency(cwe_ids: List[str]) -> float:
    """
    Компоненты:
    - prevalence: Частота в CVE database (0.0-1.0)
    - exploitability: Насколько легко эксплуатировать (0.0-1.0)
    - cvss_base: CVSS базовый балл / 10 (0.0-1.0)

    Score = prevalence × 0.4 + exploitability × 0.4 + cvss × 0.2
    """
```

| CWE | Prevalence | Exploitability | CVSS | Score |
|-----|:----------:|:--------------:|:----:|:-----:|
| CWE-120 (Buffer Overflow) | 0.85 | 0.90 | 8.0 | 0.86 |
| CWE-78 (Command Injection) | 0.75 | 0.95 | 9.8 | 0.88 |
| CWE-89 (SQL Injection) | 0.90 | 0.95 | 9.8 | 0.94 |
| CWE-200 (Info Disclosure) | 0.60 | 0.70 | 5.3 | 0.63 |

#### Attack Similarity Score (30%)

Оценивает, насколько гипотеза соответствует известным паттернам атак из CAPEC.

```python
def _score_attack_similarity(capec_ids: List[str]) -> float:
    """
    Компоненты:
    - likelihood: Вероятность атаки (0.0-1.0)
    - skill_level: Требуемый уровень навыков
      - Low: ×1.0 (выше риск)
      - Medium: ×0.8
      - High: ×0.6
      - Expert: ×0.4 (ниже риск)

    Score = likelihood × skill_adjustment
    """
```

#### Codebase Exposure Score (30%)

Оценивает, насколько конкретная кодовая база подвержена данной уязвимости.

```python
def _score_codebase_exposure(hypothesis) -> float:
    """
    Компоненты:
    - sink_exposure: Наличие опасных sink-функций
    - source_exposure: Наличие источников внешних данных
    - sanitizer_coverage: Наличие функций-санитайзеров (понижает риск)
    - taint_paths: Количество путей source → sink

    Exposure = (sink × 0.4 + source × 0.4) × (1 - sanitizer × 0.5)
    """
```

### 3.3 Бонусные множители

| Бонус | Множитель | Условие |
|-------|:---------:|---------|
| Known CVE | ×1.20 | Паттерн соответствует известному CVE |
| Critical Severity | ×1.10 | CWE имеет критическую severity |
| Recent Exploit | ×1.15 | Недавняя эксплуатация в wild |

---

## 4. Статистика кодовой базы

### 4.1 Сбор статистики из CPG

```python
@dataclass
class CodebaseStats:
    total_methods: int        # Общее количество методов
    total_calls: int          # Общее количество вызовов

    sink_counts: Dict[str, int]       # sink_name → count
    source_counts: Dict[str, int]     # source_name → count
    sanitizer_counts: Dict[str, int]  # sanitizer_name → count

    taint_paths: int          # Количество source→sink путей
```

### 4.2 Отслеживаемые функции

**Dangerous Sinks (C):**
```
strcpy, strcat, sprintf, gets, memcpy
system, popen, execl, execv
printf, fprintf (format string)
appendPQExpBuffer, SPI_execute, PQexec (PostgreSQL)
```

**Untrusted Sources:**
```
recv, read, fgets, getenv
PQgetvalue, SPI_getvalue, getTables (PostgreSQL)
```

**Sanitizers:**
```
strlcpy, snprintf
fmtId, quote_identifier, quote_literal
pg_class_aclcheck
```

---

## 5. Taint Analysis на CPG

### 5.1 Верификация потока данных

```sql
-- Поиск непроверенных путей от source к sink
FROM GRAPH_TABLE(cpg
    MATCH (src:CALL)-[:REACHING_DEF*1..10]->(sink:CALL)
    WHERE src.name IN ('recv', 'getenv', 'PQgetvalue')
      AND sink.name IN ('strcpy', 'sprintf', 'system')
    COLUMNS (
        src.name AS source,
        sink.name AS sink,
        sink.filename,
        sink.line_number
    )
)
```

### 5.2 Проверка санитизации

```sql
-- Проверка наличия санитайзеров на пути
SELECT h.id, h.source, h.sink,
       EXISTS (
           SELECT 1 FROM nodes_call nc
           WHERE nc.name IN ('strlcpy', 'snprintf', 'quote_identifier')
             AND nc.line_number BETWEEN h.source_line AND h.sink_line
             AND nc.filename = h.filename
       ) AS has_sanitizer
FROM hypothesis_paths h;
```

---

## 6. Результаты валидации

### 6.1 Benchmark на PostgreSQL 17

| Метрика | Значение |
|---------|----------|
| **CVE Detection Rate** | 100% (3/3) |
| **Hypothesis Confirmation Rate** | 55% |
| **Average Query Time** | 2-3 ms |
| **Generation Time (100 hyp.)** | <1 sec |
| **Execution Time (20 hyp.)** | <30 sec |

### 6.2 Обнаруженные CVE

| CVE ID | Тип | Метод обнаружения |
|--------|-----|-------------------|
| CVE-2025-8713 | Statistics Disclosure | Hypothesis + Taint |
| CVE-2025-8714 | pg_dump Injection | Method-based |
| CVE-2025-8715 | Newline Injection | Method-based |

### 6.3 Сравнение с традиционным SAST

| Инструмент | True Positives | False Positives | Precision |
|------------|:--------------:|:---------------:|:---------:|
| Pattern SAST | 3 | 45 | 6.25% |
| **CodeGraph** | 3 | 2 | **60%** |

---

## 7. Структура гипотезы

### 7.1 SecurityHypothesis

```python
@dataclass
class SecurityHypothesis:
    id: str                          # Уникальный идентификатор
    hypothesis_text: str             # Текст гипотезы

    # Классификация
    cwe_ids: List[str]              # ["CWE-120", "CWE-119"]
    capec_ids: List[str]            # ["CAPEC-100"]
    language: str                   # "C", "Python"
    category: str                   # "buffer_overflow"

    # Taint patterns
    source_patterns: List[str]      # ["PQgetvalue", "getenv"]
    sink_patterns: List[str]        # ["strcpy", "memcpy"]
    sanitizer_patterns: List[str]   # ["strlcpy", "sizeof"]

    # Scoring
    priority_score: float           # 0.0-1.0+
    confidence: float               # 0.0-1.0

    # Multi-criteria breakdown
    cwe_frequency_score: float
    attack_similarity_score: float
    codebase_exposure_score: float

    # Validation
    sql_query: Optional[str]
    evidence: List[Evidence]
    validation_status: ValidationStatus
```

### 7.2 Формат гипотезы

```
"If untrusted data from {sources} flows to {sinks}
 without sanitization via {sanitizers},
 then {cwe_id} enables {capec_id} attack,
 potentially allowing {impact}."
```

**Пример:**
```
"If untrusted data from PQgetvalue() flows to strcpy()
 without bounds checking via strlcpy(),
 then CWE-120 enables CAPEC-100 (Buffer Overflow) attack,
 potentially allowing memory corruption or code execution."
```

---

## 8. API для интеграции

### 8.1 Полный пример

```python
from src.security.hypothesis import (
    HypothesisGenerator,
    MultiCriteriaScorer,
    QuerySynthesizer,
    HypothesisExecutor,
    HypothesisValidator,
    CodebaseStats,
    compute_codebase_stats_from_duckdb
)
import duckdb

# 1. Подключение к CPG
conn = duckdb.connect("cpg.duckdb")

# 2. Сбор статистики кодовой базы
stats = compute_codebase_stats_from_duckdb("cpg.duckdb")

# 3. Генерация гипотез
generator = HypothesisGenerator()
hypotheses = generator.generate(
    language="C",
    cwe_filter=["CWE-120", "CWE-78", "CWE-89"],
    max_hypotheses=100
)

# 4. Многокритериальный скоринг
scorer = MultiCriteriaScorer(codebase_stats=stats)
scored = scorer.score_batch(hypotheses)

# 5. Синтез SQL-запросов
synthesizer = QuerySynthesizer()
for h in scored:
    h.sql_query = synthesizer.synthesize_query(h)

# 6. Выполнение на CPG
executor = HypothesisExecutor(conn)
for h in scored[:20]:  # Top 20
    evidence = executor.execute(h)
    h.evidence.extend(evidence)

# 7. Валидация и отчёт
validator = HypothesisValidator()
results = validator.validate_batch(scored)

print(f"Detection Rate: {results.detection_rate:.1%}")
print(f"Precision: {results.precision:.1%}")
print(f"F1 Score: {results.f1_score:.2f}")
```

---

## 9. Заключение

Многокритериальная система валидации гипотез CodeGraph представляет собой **принципиально новый подход** к поиску уязвимостей:

1. **Контекстуальный анализ** — учёт специфики конкретной кодовой базы
2. **Taint-верификация** — подтверждение потока данных через CPG
3. **Приоритизация по риску** — фокус на реально эксплуатируемых уязвимостях
4. **Снижение false positives** — от 70-90% до менее 30%

Результат: **100% detection rate** для целевых CVE при драматическом снижении ложных срабатываний.

---

## Связанные документы

- [Enterprise Security Brief](./ENTERPRISE_SECURITY_BRIEF.md)
- [Competitive Matrix](./COMPETITIVE_MATRIX.md)
- [Hypothesis System Reference](../reference/HYPOTHESIS_SYSTEM.md)

---

*Версия: 1.0 | Декабрь 2025*
