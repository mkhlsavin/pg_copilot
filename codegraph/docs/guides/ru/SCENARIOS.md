# Руководство по сценариям рабочих процессов

CodeGraph поддерживает 16 специализированных сценариев анализа.

## Содержание

- [Обзор сценариев](#obzor-stsenariev)
- [1. Поиск определений](#1-poisk-opredeleniy)
- [Примеры вопросов](#primery-voprosov)
- [Использование](#ispolzovanie)
- [2. Анализ графа вызовов](#2-analiz-grafa-vyzovov)
- [Примеры вопросов](#primery-voprosov)
- [Использование](#ispolzovanie)
- [3. Трассировка потока данных](#3-trassirovka-potoka-dannyh)
- [Примеры вопросов](#primery-voprosov)
- [Использование](#ispolzovanie)
- [4. Обнаружение уязвимостей](#4-obnaruzhenie-uyazvimostey)
- [Примеры вопросов](#primery-voprosov)
- [Обнаруживаемые шаблоны безопасности](#obnaruzhivaemye-shablony-bezopasnosti)
- [Использование](#ispolzovanie)
- [5. Обнаружение неиспользуемого кода](#5-obnaruzhenie-neispolzuemogo-koda)
- [Примеры вопросов](#primery-voprosov)
- [Шаблоны неиспользуемого кода](#shablony-neispolzuemogo-koda)
- [Использование](#ispolzovanie)
- [6. Анализ производительности](#6-analiz-proizvoditelnosti)
- [Примеры вопросов](#primery-voprosov)
- [Анализируемые метрики](#analiziruemye-metriki)
- [Использование](#ispolzovanie)
- [7. Обнаружение дублирования кода](#7-obnaruzhenie-dublirovaniya-koda)
- [Примеры вопросов](#primery-voprosov)
- [Использование](#ispolzovanie)
- [8. Поиск точек входа](#8-poisk-tochek-vhoda)
- [Примеры вопросов](#primery-voprosov)
- [Шаблоны точек входа в PostgreSQL](#shablony-tochek-vhoda-v-postgresql)
- [Использование](#ispolzovanie)
- [9. Анализ многопоточности](#9-analiz-mnogopotochnosti)
- [Примеры вопросов](#primery-voprosov)
- [Анализируемые шаблоны](#analiziruemye-shablony)
- [Использование](#ispolzovanie)
- [10. Анализ зависимостей](#10-analiz-zavisimostey)
- [Примеры вопросов](#primery-voprosov)
- [Использование](#ispolzovanie)
- [11. Генерация документации](#11-generatsiya-dokumentatsii)
- [Примеры вопросов](#primery-voprosov)
- [Использование](#ispolzovanie)
- [12. Оценка технического долга](#12-otsenka-tehnicheskogo-dolga)
- [Примеры вопросов](#primery-voprosov)
- [Показатели долга](#pokazateli-dolga)
- [Использование](#ispolzovanie)
- [13. Реагирование на инциденты безопасности](#13-reagirovanie-na-intsidenty-bezopasnosti)
- [Примеры вопросов](#primery-voprosov)
- [Использование](#ispolzovanie)
- [14. Организация рефакторинга](#14-organizatsiya-refaktoringa)
- [Примеры вопросов](#primery-voprosov)
- [Использование](#ispolzovanie)
- [15. Автоматизация код-ревью](#15-avtomatizatsiya-kod-revyu)
- [Примеры вопросов](#primery-voprosov)
- [Использование](#ispolzovanie)
- [16. Анализ архитектуры](#16-analiz-arhitektury)
- [Примеры вопросов](#primery-voprosov)
- [Использование](#ispolzovanie)
- [Комбинирование сценариев](#kombinirovanie-stsenariev)
- [Следующие шаги](#sleduyuschie-shagi)

## Обзор сценариев

| # | Сценарий | Пример использования |
| --- | --- | --- |
| 1 | Поиск определений | Поиск определений функций/классов |
| 2 | Анализ графа вызовов | Отслеживание связей вызовов |
| 3 | Анализ потока данных | Отслеживание распространения данных |
| 4 | Обнаружение уязвимостей | Поиск проблем безопасности |
| 5 | Обнаружение мертвого кода | Поиск неиспользуемого кода |
| 6 | Анализ производительности | Выявление узких мест |
| 7 | Обнаружение дублирования кода | Поиск клонов кода |
| 8 | Поиск точек входа | Определение границ API |
| 9 | Анализ многопоточности | Проверка потокобезопасности |
| 10 | Анализ зависимостей | Зависимости между модулями |
| 11 | Генерация документации | Автоматическая генерация документации |
| 12 | Оценка технического долга | Поиск участков с высоким уровнем долга |
| 13 | Реагирование на инциденты безопасности | Расследование инцидентов |
| 14 | Организация рефакторинга | Планирование рефакторинга |
| 15 | Автоматизация код-ревью | Автоматические проверки кода |
| 16 | Архитектурный анализ | Выявление архитектурных паттернов |

---

## 1. Поиск определений

Поиск мест, где определены функции, классы или переменные.

### Примеры запросов

```
Найти метод 'heap_insert'
Где определена функция AbortTransaction?
Показать определение структуры RelFileNode
Найти все методы в файле 'xact.c'
```

### Использование

```
from src.workflow import MultiScenarioCopilot

copilot = MultiScenarioCopilot()
result = copilot.run("Найти метод 'CommitTransaction'", scenario="definition_search")

print(result['definitions'])
# [{'name': 'CommitTransaction', 'file': 'xact.c', 'line': 2156}]
```

## 2. Анализ графа вызовов

Отслеживание взаимосвязей между вызовами функций.

### Примеры запросов

```
Какие функции вызывают LWLockAcquire?
Показать вызывающие функции для heap_insert
Найти цепочку вызовов от executor_start до heap_insert
Какие функции вызывает ProcessQuery?
```

### Использование

```
copilot = MultiScenarioCopilot()
result = copilot.run("Найти все функции, вызывающие MemoryContextCreate", scenario="call_graph")

for caller in result['callers']:
    print(f"{caller['name']} вызывает MemoryContextCreate в строке {caller['line']}")
```

---

## 3. Трассировка потока данных

Отслеживание перемещения данных по системе.

### Примеры вопросов

```
Как пользовательский ввод доходит до выполнения SQL?
Проследить путь строки запроса от парсера к исполнителю
Куда попадает результат heap_fetch?
Найти все пути от ввода данных до записи в базу
```

### Использование

```
copilot = MultiScenarioCopilot()
result = copilot.run("Проследи путь от пользовательского ввода до выполнения запроса", scenario="data_flow")

for path in result['data_flows']:
    print(f"Поток: {' -> '.join(path['nodes'])}")
```

## 4. Обнаружение уязвимостей

Поиск потенциальных проблем с безопасностью с отображением на CWE.

### Примеры запросов

```
Найти уязвимости, связанные с SQL-инъекциями
Показать потенциальные переполнения буфера
Найти несанитизированный пользовательский ввод
Обнаружить уязвимости, связанные с форматными строками
```

### Обнаруживаемые шаблоны безопасности

- SQL-инъекция (CWE-89)
- Переполнение буфера (CWE-120)
- Инъекция команд (CWE-78)
- Форматная строка (CWE-134)
- Переполнение целого числа (CWE-190)

### Использование

```
workflow = create_workflow(scenario="vulnerability_detection")
result = workflow.run("Найти уязвимости, связанные с SQL-инъекциями")

for vuln in result['vulnerabilities']:
    print(f"CWE-{vuln['cwe']}: {vuln['description']}")
    print(f"  Файл: {vuln['file']}:{vuln['line']}")
    print(f"  Уровень серьёзности: {vuln['severity']}")
```

## 5. Обнаружение мёртвого кода

Поиск недостижимого или неиспользуемого кода.

### Примеры запросов

```
Найти недостижимые функции
Показать неиспользуемые статические функции
Найти код после операторов return
Обнаружить функции, у которых нет вызывающих
```

### Паттерны мёртвого кода

- Функции, которые нигде не вызываются
- Недостижимые блоки кода
- Неиспользуемые статические функции
- Ненужные присваивания (dead stores)
- Закомментированный код

### Использование

```
workflow = create_workflow(scenario="dead_code")
result = workflow.run("Найти неиспользуемые функции")

for dead in result['dead_code']:
    print(f"Неиспользуется: {dead['name']} в {dead['file']}")
```

## 6. Анализ производительности

Выявление узких мест в производительности.

### Примеры запросов

```
Найти функции с высокой цикломатической сложностью
Показать ресурсоёмкие циклы
Найти паттерны со сложностью O(n^2)
Определить «горячие» участки при выполнении запросов
```

### Анализируемые метрики

- Цикломатическая сложность
- Глубина вложенности циклов
- Длина функций
- Частота вызовов
- Паттерны выделения памяти

### Использование

```
workflow = create_workflow(scenario="performance")
result = workflow.run("Найти функции со сложностью > 20")

for func in result['complex_functions']:
    print(f"{func['name']}: complexity={func['complexity']}")
```

## 7. Дублирование кода

Обнаружение похожих фрагментов кода.

### Примеры запросов

```
Найти дублирующиеся блоки кода
Показать похожие функции
Обнаружить шаблоны копирования-вставки
Найти возможности для рефакторинга дубликатов
```

### Использование

```
workflow = create_workflow(scenario="duplication")
result = workflow.run("Найти похожие фрагменты кода")

for clone in result['clones']:
    print(f"Пара дубликатов: {clone['location1']} <-> {clone['location2']}")
    print(f"Схожесть: {clone['similarity']:.0%}")
```

## 8. Обнаружение точек входа

Определение границ API и точек входа.

### Примеры вопросов

```
Каковы публичные точки входа API?
Найти все экспортированные функции
Показать основные точки входа
Найти функции-перехватчики (hook-функции)
```

### Шаблоны точек входа в PostgreSQL

- Макросы `PG_FUNCTION_INFO_V1`
- `PostgresMain` и обработчики команд
- Функции регистрации хуков

### Использование

```
workflow = create_workflow(scenario="entry_points")
result = workflow.run("Найти точки входа API")

for entry in result['entry_points']:
    print(f"Точка входа: {entry['name']} ({entry['type']})")
```

## 9. Анализ многопоточности

Анализ потокобезопасности и синхронизации.

### Примеры вопросов

```
Найти гонки данных (race conditions)
Показать проблемы с порядком блокировок
Найти отсутствующие захваты блокировок
Обнаружить потенциальные взаимные блокировки (deadlock)
```

### Анализируемые шаблоны

- Пары захвата/освобождения блокировок
- Доступ к общим переменным
- Охват критических секций
- Нарушения иерархии блокировок

### Использование

```
workflow = create_workflow(scenario="concurrency")
result = workflow.run("Найти потенциальные гонки данных")

for issue in result['concurrency_issues']:
    print(f"Проблема: {issue['type']} в {issue['location']}")
```

## 10. Анализ зависимостей

Анализ зависимостей между модулями.

### Примеры запросов

```
Какие модули зависят от модуля storage?
Покажи граф зависимостей
Найди циклические зависимости
Какие модули используют buffer manager?
```

### Использование

```
workflow = create_workflow(scenario="dependencies")
result = workflow.run("Покажи зависимости модуля transaction")

for dep in result['dependencies']:
    print(f"{dep['from']} -> {dep['to']}")
```

## 11. Генерация документации

Генерация документации из исходного кода.

### Примеры запросов

```
Документируй подсистему транзакций
Создай документацию API для исполнителя
Создай краткое описание менеджера буферов
Создай документацию для функций кучи
```

### Использование

```
workflow = create_workflow(scenario="documentation")
result = workflow.run("Document the transaction subsystem")

print(result['documentation'])
# Документация в формате Markdown
```

## 12. Оценка технического долга

Выявление зон с высокой концентрацией технического долга.

### Примеры вопросов

```
Найти код с чрезмерной связанностью
Показать модули, требующие рефакторинга
Найти запахи кода
Определить участки, сложные в сопровождении
```

### Признаки долга

- Высокая сложность
- Глубокая вложенность
- Длинные функции
- Сильная связанность
- Отсутствие обработки ошибок

### Использование

```
workflow = create_workflow(scenario="tech_debt")
result = workflow.run("Найти участки с техническим долгом")

for debt in result['debt_items']:
    print(f"{debt['location']}: {debt['type']} (серьёзность: {debt['severity']})")
```

## 13. Реагирование на инциденты безопасности

Исследование инцидентов безопасности.

### Примеры вопросов

```
Проследить последствия уязвимости CVE-XXXX
Найти все кодовые пути, затронутые этой уязвимостью
Показать пути эксплуатации
Определить затронутые функции
```

### Использование

```
workflow = create_workflow(scenario="security_incident")
result = workflow.run("Проследить влияние уязвимости в parse_query")

for path in result['impact_paths']:
    print(f"Воздействие: {path['description']}")
```

## 14. Организация рефакторинга

Планирование и выполнение рефакторинга.

### Примеры запросов

```
Запланировать рефакторинг менеджера буферов
Найти возможности для выделения методов в исполнителе
Найти функции, которые можно разбить
Предложить улучшения интерфейса
```

### Использование

```
workflow = create_workflow(scenario="refactoring")
result = workflow.run("Запланировать рефакторинг менеджера буферов")

for step in result['refactoring_plan']:
    print(f"Шаг {step['order']}: {step['action']}")
```

---

## 15. Автоматизация проверки кода

Автоматическая помощь в проверке кода.

### Примеры запросов

```
Проверь этот патч на наличие проблем с безопасностью
Найди потенциальные ошибки в этом изменении
Проверь наличие нарушений стиля кодирования
Проанализируй покрытие тестами внесённых изменений
```

### Использование

```
python demo_patch_review.py --patch changes.diff
```

Или программно:

```
workflow = create_workflow(scenario="code_review")
result = workflow.run_on_patch("path/to/changes.diff")

for finding in result['findings']:
    print(f"{finding['severity']}: {finding['description']}")
```

---

## 16. Анализ архитектуры

Изучение архитектурных паттернов.

### Примеры вопросов

```
Отобразить архитектуру подсистем
Показать границы слоёв
Найти нарушения архитектуры
Определить используемые паттерны проектирования
```

### Использование

```
workflow = create_workflow(scenario="architecture")
result = workflow.run("Отобразить архитектуру PostgreSQL")

for subsystem in result['subsystems']:
    print(f"{subsystem['name']}: {subsystem['description']}")
```

---

## Комбинирование сценариев

Запуск нескольких сценариев вместе:

```
from src.workflow import MultiScenarioWorkflow

workflow = MultiScenarioWorkflow()
workflow.add_scenario("vulnerability_detection")
workflow.add_scenario("performance")
workflow.add_scenario("tech_debt")

result = workflow.run("Проанализировать модуль executor")

print(f"Проблемы безопасности: {len(result['vulnerabilities'])}")
print(f"Проблемы производительности: {len(result['performance_issues'])}")
print(f"Элементы технического долга: {len(result['debt_items'])}")
```

## Дальнейшие шаги

- [Руководство пользователя TUI](TUI_USER_GUIDE.md) — Общее использование
- [Справка по API](../reference/API.md) — Программный доступ
- [Справка по шаблонам](../development/PATTERNS.md) — Шаблоны обнаружения
