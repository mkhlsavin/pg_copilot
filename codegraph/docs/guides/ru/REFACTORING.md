# Руководство по анализу рефакторинга

В этом руководстве описывается использование модуля анализа рефакторинга для выявления запахов кода, анализа влияния и планирования задач рефакторинга.

## Содержание

- [Обзор](#обзор)
- [Быстрый старт](#быстрый-старт)
- [Обнаружение запахов кода](#обнаружение-запахов-кода)
- [Поддерживаемые категории шаблонов](#поддерживаемые-категории-шаблонов)
- [Уровни серьезности](#уровни-серьезности)
- [Методы обнаружения](#методы-обнаружения)
- [Структура находки запаха кода](#структура-находки-запаха-кода)
- [Анализ влияния](#анализ-влияния)
- [Анализ изменений методов](#анализ-изменений-методов)
- [Структура анализа влияния](#структура-анализа-влияния)
- [Анализ зависимостей](#анализ-зависимостей)
- [Планирование рефакторинга](#планирование-рефакторинга)
- [Создание плана рефакторинга](#создание-плана-рефакторинга)
- [Приоритизация задач](#приоритизация-задач)
- [Структура задачи рефакторинга](#структура-задачи-рефакторинга)
- [Отчёт по рефакторингу](#отчёт-по-рефакторингу)
- [Генерация полного отчёта](#генерация-полного-отчёта)
- [Структура отчёта](#структура-отчёта)
- [Поддерживаемые шаблоны](#поддерживаемые-шаблоны)
- [Шаблоны «раздувания» (Bloater)](#шаблоны-раздувания-bloater)
- [Шаблоны сложности](#шаблоны-сложности)
- [Шаблоны дублирования](#шаблоны-дублирования)
- [Шаблоны мёртвого кода](#шаблоны-мёртвого-кода)
- [SQL-запросы для обнаружения](#sql-запросы-для-обнаружения)
- [См. также](#см-также)

## Обзор

Модуль рефакторинга предоставляет три специализированных агента:

1. **TechnicalDebtDetector** — обнаруживает запахи кода с использованием библиотеки шаблонов
2. **ImpactAnalyzer** — анализирует влияние изменений и зависимости
3. **RefactoringPlanner** — создает приоритизированные планы рефакторинга

---

## Быстрый старт

```
from src.refactoring import (
    TechnicalDebtDetector,
    ImpactAnalyzer,
    RefactoringPlanner
)
from src.services.cpg_query_service import CPGQueryService
import duckdb

# Подключение к CPG
conn = duckdb.connect("cpg.duckdb")
query_service = CPGQueryService(conn)

# Инициализация агентов
detector = TechnicalDebtDetector(query_service)
analyzer = ImpactAnalyzer(query_service)
planner = RefactoringPlanner(query_service)

# Обнаружение запахов кода
findings = detector.detect_all()

# Анализ влияния для метода
impact = analyzer.analyze("heap_insert", "backend/access/heap/heapam.c")

# Создание плана рефакторинга
plan = planner.create_plan(findings, max_tasks=10)
```

---

## Обнаружение запахов кода

### Поддерживаемые категории шаблонов

| Категория | Описание | Примеры |
| --- | --- | --- |
| bloater | Крупные методы, длинные списки параметров | Бог-метод, Длинный список параметров |
| complexity | Высокая цикломатическая сложность | Сложные условные выражения, Глубокая вложенность |
| duplicate | Повторяющийся код | Дублирование кода, Похожие функции |
| dead_code | Неиспользуемый или недостижимый код | Мёртвый код, Неиспользуемые переменные |
| documentation | Отсутствующая или устаревшая документация | Отсутствуют комментарии, Устаревшая документация |

### Уровни серьёзности

| Серьёзность | Описание | Действие |
| --- | --- | --- |
| CRITICAL | Серьёзная проблема, требующая немедленного исправления | Исправить немедленно |
| HIGH | Значительная проблема | Исправить в текущем спринте |
| MEDIUM | Умеренная проблема | Запланировать на следующий спринт |
| LOW | Незначительная проблема | Исправить при удобной возможности |
| INFO | Информационное сообщение | Рассмотреть для улучшения |

### Методы обнаружения

**Обнаружение всех шаблонов:**

```
findings = detector.detect_all(
    file_filter="backend/parser/*.c",  # Опционально: фильтр по пути
    severity_filter=["CRITICAL", "HIGH"]  # Опционально: фильтр по уровню серьёзности
)

for finding in findings:
    print(f"{finding.severity}: {finding.pattern_name}")
    print(f"  Расположение: {finding.filename}:{finding.line_number}")
    print(f"  Рекомендуемое исправление: {finding.refactoring_technique}")
```

**Обнаружение по категории:**

```
# Найти все шаблоны категории bloater
bloaters = detector.detect_by_category("bloater")

# Найти проблемы сложности
complexity = detector.detect_by_category("complexity")
```

**Обнаружение только критических проблем:**

```
critical = detector.detect_critical()
```

### Структура найденного запаха кода

```
@dataclass
class CodeSmellFinding:
    finding_id: str
    pattern_id: str
    pattern_name: str
    category: str
    severity: str
    method_id: int
    method_name: str
    filename: str
    line_number: int
    code_snippet: str
    description: str
    symptoms: List[str]
    refactoring_technique: str
    effort_hours: float
    metadata: Dict[str, Any]
```

---

## Анализ влияния

### Анализ изменений метода

```
impact = analyzer.analyze(
    method_name="heap_insert",
    filename="backend/access/heap/heapam.c"
)

print(f"Уровень риска: {impact.risk_level}")
print(f"Оценка влияния: {impact.impact_score:.2f}")
print(f"Непосредственно затронутые методы: {len(impact.direct_dependents)}")
print(f"Косвенно затронутые методы: {len(impact.indirect_dependents)}")
print(f"Файлы, требующие тестирования: {len(impact.affected_files)}")
print(f"Оценочные трудозатраты на тестирование: {impact.estimated_test_effort}ч")
```

### Структура анализа влияния

```
@dataclass
class ImpactAnalysis:
    analysis_id: str
    target_method: str
    target_file: str
    direct_dependents: List[str]    # Методы, вызывающие целевой
    indirect_dependents: List[str]  # Транзитивные вызывающие
    affected_files: List[str]       # Файлы, требующие проверки
    impact_score: float             # От 0.0 до 1.0
    risk_level: str                 # "low", "medium", "high"
    estimated_test_effort: float    # Часы
```

### Анализ зависимостей

```
# Получить все зависимости метода
deps = analyzer.get_dependencies("heap_insert")

for dep in deps:
    print(f"{dep.from_method} -> {dep.to_method}")
    print(f"  Тип: {dep.dependency_type}")
    print(f"  Сила связи: {dep.strength}")
```

---

## Планирование рефакторинга

### Создание плана рефакторинга

```
plan = planner.create_plan(
    findings=findings,
    max_tasks=20,
    priority_threshold=5  # Включать только приоритет >= 5
)

print(f"Общее количество задач: {len(plan.tasks)}")
print(f"Общие трудозатраты: {plan.total_effort_hours}ч")
print(f"Расчётная продолжительность: {plan.estimated_weeks} недель")

for task in plan.tasks:
    print(f"\nЗадача {task.task_id}: {task.pattern_name}")
    print(f"  Цель: {task.target_file}:{task.target_method}")
    print(f"  Приоритет: {task.priority}/10")
    print(f"  Трудозатраты: {task.effort_hours}ч")
    print(f"  Шаги:")
    for step in task.refactoring_steps:
        print(f"    - {step}")
```

### Приоритизация задач

Задачи упорядочиваются по следующим критериям:

1. **Вес серьёзности** (40%) — выше серьёзность = выше приоритет
2. **Оценка влияния** (30%) — сильнее влияние = выше приоритет
3. **Эффективность трудозатрат** (30%) — соотношение ценности к трудозатратам

### Структура задачи рефакторинга

```
@dataclass
class RefactoringTask:
    task_id: str
    finding_id: str
    pattern_name: str
    target_method: str
    target_file: str
    priority: int              # 1-10
    effort_hours: float
    impact_score: float
    refactoring_steps: List[str]
    dependencies: List[str]    # Задачи, которые нужно выполнить в первую очередь
    estimated_value: float
```

---

## Отчёт по рефакторингу

### Генерация полного отчёта

```
report = planner.generate_report(
    findings=findings,
    include_impact=True,
    format="markdown"
)

# Сохранение отчёта
with open("refactoring_report.md", "w") as f:
    f.write(report.to_markdown())
```

### Структура отчёта

```
@dataclass
class RefactoringReport:
    report_id: str
    generated_at: datetime
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    findings_by_category: Dict[str, int]
    tasks: List[RefactoringTask]
    total_effort_hours: float
    estimated_weeks: float
    recommendations: List[str]
```

---

## Поддерживаемые шаблоны

### Шаблоны «раздутого кода» (Bloater Patterns)

| Шаблон | Обнаружение | Метод устранения |
| --- | --- | --- |
| Богатый метод (God Method) | Строк > 200, Сложность > 20 | Выделить метод (Extract Method) |
| Длинный список параметров (Long Parameter List) | Параметров > 5 | Ввести объект параметров (Introduce Parameter Object) |
| Большой класс (Large Class) | Методов > 30 | Выделить класс (Extract Class) |
| Скопление данных (Data Clumps) | Повторяющиеся группы параметров | Выделить класс (Extract Class) |

### Шаблоны сложности (Complexity Patterns)

| Шаблон | Обнаружение | Метод устранения |
| --- | --- | --- |
| Сложные условные выражения (Complex Conditionals) | Глубина вложенности > 4 | Разложить условное выражение (Decompose Conditional) |
| Операторы switch (Switch Statements) | Более 5 вариантов | Заменить полиморфизмом (Replace with Polymorphism) |
| Зависть к функциональности (Feature Envy) | Высокая связанность | Переместить метод (Move Method) |

### Шаблоны дублирования (Duplicate Patterns)

| Шаблон | Обнаружение | Метод устранения |
| --- | --- | --- |
| Дублированный код (Duplicate Code) | Похожие блоки кода | Выделить метод (Extract Method) |
| Похожие функции (Similar Functions) | Похожие сигнатуры | Выделить суперкласс (Extract Superclass) |

### Шаблоны неиспользуемого кода (Dead Code Patterns)

| Шаблон | Обнаружение | Метод устранения |
| --- | --- | --- |
| Неиспользуемые методы (Unused Methods) | Нет вызывающих мест | Удалить метод (Remove Method) |
| Неиспользуемые параметры (Unused Parameters) | Не используются в теле | Удалить параметр (Remove Parameter) |
| Избыточная общность (Speculative Generality) | Неиспользуемые абстракции | Удалить абстракцию (Remove Abstraction) |

---

## SQL-запросы для обнаружения

Модуль использует SQL-запросы к CPG для выявления шаблонов:

**Длинные методы:**

```
SELECT name, full_name, filename, line_number,
       (line_number_end - line_number) as lines
FROM nodes_method
WHERE (line_number_end - line_number) > 200
  AND is_external = false
ORDER BY lines DESC;
```

**Высокая сложность:**

```
SELECT m.name, m.filename, COUNT(cs.id) as complexity
FROM nodes_method m
JOIN edges_ast a ON m.id = a.src
JOIN nodes_control_structure cs ON a.dst = cs.id
WHERE cs.control_structure_type IN ('IF', 'WHILE', 'FOR', 'SWITCH')
GROUP BY m.id, m.name, m.filename
HAVING COUNT(cs.id) > 15
ORDER BY complexity DESC;
```

**Неиспользуемые методы:**

```
SELECT m.name, m.full_name, m.filename
FROM nodes_method m
WHERE m.is_external = false
  AND NOT EXISTS (
      SELECT 1 FROM edges_call ec WHERE ec.dst = m.id
  )
  AND m.name NOT LIKE 'test%'
  AND m.name NOT IN ('main', 'init');
```

## См. также

- [Кулинарная книга SQL-запросов](../reference/SQL_QUERY_COOKBOOK.md) — дополнительные запросы для обнаружения
- [Руководство по экспорту CPG](./CPG_EXPORT.md) — подготовка CPG к анализу
- [Справочник схемы](../reference/SCHEMA.md) — справочная информация по схеме базы данных
