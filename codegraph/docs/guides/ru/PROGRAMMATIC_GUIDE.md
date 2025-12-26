# Руководство пользователя

Полное руководство по использованию CodeGraph для анализа кода.

## Содержание

- [Обзор](#obzor)
- [Базовое использование](#bazovoe-ispolzovanie)
- [Интерактивный режим](#interaktivnyy-rezhim)
- [Программное использование](#programmnoe-ispolzovanie)
- [Типы вопросов](#tipy-voprosov)
- [Запросы определений](#zaprosy-opredeleniy)
- [Запросы связей](#zaprosy-svyazey)
- [Семантические запросы](#semanticheskie-zaprosy)
- [Запросы безопасности](#zaprosy-bezopasnosti)
- [Понимание результатов](#ponimanie-rezultatov)
- [Структура результата](#struktura-rezultata)
- [Уровни достоверности](#urovni-dostovernosti)
- [Расширенные функции](#rasshirennye-funktsii)
- [Гибридный режим поиска](#gibridnyy-rezhim-poiska)
- [Анализ нескольких доменов](#analiz-neskolkih-domenov)
- [Сценарный анализ](#stsenarnyy-analiz)
- [Рекомендации](#rekomendatsii)
- [Формулирование эффективных вопросов](#formulirovanie-effektivnyh-voprosov)
- [Оптимизация производительности](#optimizatsiya-proizvoditelnosti)
- [Интерпретация ответов](#interpretatsiya-otvetov)
- [Интеграция в рабочие процессы](#integratsiya-v-rabochie-protsessy)
- [Интеграция с CI/CD](#integratsiya-s-cicd)
- [Код-ревью](#kod-revyu)
- [Генерация документации](#generatsiya-dokumentatsii)
- [Дальнейшие шаги](#dalneyshie-shagi)

## Обзор

CodeGraph отвечает на вопросы на естественном языке о кодовой базе, комбинируя:
- **Семантический поиск** — Поиск кода по смыслу и назначению
- **Структурный поиск** — Обход графов вызовов и потоков данных
- **Синтез с помощью LLM** — Генерация ответов, понятных человеку

## Базовое использование

### Интерактивный режим

```
python examples/demo_simple.py
```

Введите вопросы в командной строке:

```
> Что делает CommitTransaction?
> Найди методы, отвечающие за выделение памяти
> Покажи цепочку вызовов от исполнителя к хранилищу
```

### Программное использование

```
from src.workflow import MultiScenarioCopilot

copilot = MultiScenarioCopilot()
question = "Какие методы обрабатывают фиксацию транзакций?"
result = copilot.run(question)

print(f"Ответ: {result['answer']}")
print(f"Достоверность: {result.get('confidence', 'N/A')}")
```

## Типы вопросов

### Запросы определений

Поиск мест определения кода:

```
Найди метод 'heap_insert'
Где определён AbortTransaction?
Покажи мне функцию RelationGetBufferForTuple
```

### Запросы связей

Анализ связей в коде:

```
Какие методы вызывают LWLockAcquire?
Найди вызывающие функции MemoryContextCreate
Что вызывает heap_insert?
```

### Семантические запросы

Вопросы о поведении и назначении:

```
Как PostgreSQL обрабатывает MVCC?
Объясни процесс фиксации транзакций
Какой механизм обеспечивает долговечность?
```

### Запросы безопасности

Поиск уязвимостей:

```
Найди потенциальные точки SQL-инъекций
Покажи пути с необработанным пользовательским вводом
Найди риски переполнения буфера
```

## Понимание результатов

### Структура результата

```
{
    "answer": "CommitTransaction завершает транзакцию путём...",
    "confidence": 0.85,
    "sources": [
        {"method": "CommitTransaction", "file": "xact.c", "line": 1234},
        {"method": "CommitTransactionCommand", "file": "xact.c", "line": 1456}
    ],
    "query_used": "cpg.method.name('CommitTransaction')...",
    "execution_time_ms": 150
}
```

### Уровни достоверности

| Уровень | Значение |
| --- | --- |
| > 0.9 | Высокая достоверность — прямое совпадение |
| 0.7–0.9 | Хорошая достоверность — семантическое совпадение |
| 0.5–0.7 | Умеренная — требуется логический вывод |
| < 0.5 | Низкая — ответ по возможности |

## Расширенные функции

### Гибридный режим поиска

Комбинированный семантический и структурный поиск:

```
from src.agents.retriever_agent import RetrieverAgent

retriever = RetrieverAgent(
    enable_hybrid=True,
    vector_weight=0.6,
    graph_weight=0.4
)

results = retriever.retrieve_hybrid(
    question="Найти шаблоны выделения памяти",
    mode="hybrid",
    query_type="structural"
)
```

### Анализ нескольких доменов

Переключение между кодовыми базами:

```
from src.config import CPGConfig

# Анализ PostgreSQL
pg_config = CPGConfig()
pg_config.set_cpg_type("postgresql")

# Анализ ядра Linux
lk_config = CPGConfig()
lk_config.set_cpg_type("linux_kernel")
```

### Сценарный анализ

Использование сопровождающего агента для анализа по сценариям (тип сценария определяется автоматически):

```
from src.workflow import MultiScenarioCopilot

copilot = MultiScenarioCopilot()

# Анализ безопасности — тип определяется автоматически
result = copilot.run("Найти уязвимости к SQL-инъекциям")
print(f"Сценарий: {result.get('intent')}")  # → 'security'

# Анализ производительности
result = copilot.run("Найти функции с высокой цикломатической сложностью")
print(f"Сценарий: {result.get('intent')}")  # → 'performance'
```

## Рекомендации

### Формулирование эффективных вопросов

**Хорошие вопросы:**
- “Какие функции обрабатывают выделение памяти в менеджере буферов?”
- “Покажи путь вызовов от парсера к исполнителю”
- “Найди необработанные пользовательские входы, попадающие в SQL-запросы”

**Менее эффективные:**
- “Расскажи мне о коде” (слишком расплывчато)
- “Исправь эту ошибку” (запрос действия, а не анализа)
- “Всё о транзакциях” (слишком широко)

### Оптимизация производительности

1. **Будьте конкретны** — Чёткие вопросы дают более быстрые ответы
2. **Используйте структурные запросы** — Когда вы знаете шаблон
3. **Включите кэширование** — Для повторяющихся похожих запросов
4. **Ограничьте область** — Добавьте ограничения по файлам или подсистемам

### Интерпретация ответов

1. **Проверьте источники** — Убедитесь в корректности ссылок на код
2. **Учитывайте достоверность** — Низкая достоверность = требуется ручная проверка
3. **Уточняйте** — Задавайте дополнительные вопросы
4. **Сверяйте** — Сравнивайте с реальным кодом

## Интеграция в рабочие процессы

### Интеграция с CI/CD

```
# .github/workflows/code-analysis.yml
- name: Запустить анализ кода
  run: |
    python -c "
    from src.workflow import MultiScenarioCopilot
    copilot = MultiScenarioCopilot()
    result = copilot.run('Найти потенциальные проблемы безопасности')
    if result.get('critical_count', 0) > 0:
        exit(1)
    "
```

### Код-ревью

```
# Анализ изменений
python examples/demo_patch_review.py --patch changes.diff

# Вывод: Найденные проблемы безопасности, производительности и архитектуры
```

### Генерация документации

```
from src.workflow import MultiScenarioCopilot

copilot = MultiScenarioCopilot()
result = copilot.run("Документируй подсистему транзакций")

# result['answer'] содержит сгенерированную документацию
print(result['answer'])
```

## Дальнейшие шаги

- [Сценарии](SCENARIOS.md) — Все 16 вариантов использования
- [Руководство CLI](CLI_GUIDE.md) — Интерфейс командной строки
- [Справка по API](../reference/API.md) — Программный доступ
- [Устранение неполадок](TROUBLESHOOTING.md) — Типичные проблемы
