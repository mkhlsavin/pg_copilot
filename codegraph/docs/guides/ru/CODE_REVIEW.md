# Система автоматического код-ревью на основе патчей

## Содержание

- [Обзор](#обзор)
- [Быстрый старт](#быстрый-старт)
- [Базовое использование](#базовое-использование)
- [Использование в коде](#использование-в-коде)
- [Архитектура](#архитектура)
- [Конвейер рабочего процесса](#конвейер-рабочего-процесса)
- [Компоненты](#компоненты)
- [Критерии готовности (Definition of Done, DoD)](#критерии-готовности-definition-of-done-dod)
- [Источники DoD](#источники-dod)
- [Форматы DoD](#форматы-dod)
- [Определение готовности (Definition of Done)](#определение-готовности-definition-of-done)
- [Типы критериев](#типы-критериев)
- [Интерактивное подтверждение DoD](#интерактивное-подтверждение-dod)
- [Проверка DoD](#проверка-dod)
- [Конфигурация](#конфигурация)
- [config/code_review.yaml](#configcode_reviewyaml)
- [Переменные окружения](#переменные-окружения)
- [Справка по API](#справка-по-api)
- [ReviewWorkflow](#reviewworkflow)
- [ReviewVerdict](#reviewverdict)
- [DoDValidationResult](#dodvalidationresult)
- [Форматы вывода](#форматы-вывода)
- [Вывод в формате JSON](#вывод-в-формате-json)
- [Вывод в формате Markdown](#вывод-в-формате-markdown)
- [Сводка по проверке изменений (Patch Review Summary)](#сводка-по-проверке-изменений-patch-review-summary)
- [Критерии готовности](#критерии-готовности)
- [Обнаруженные уязвимости безопасности](#обнаруженные-уязвимости-безопасности)
- [Устранение неполадок](#устранение-неполадок)
- [“DoD не найден”](#dod-не-найден)
- [“Проверка DoD пропущена”](#проверка-dod-пропущена)
- [“Извлечение данных из Jira не удалось”](#извлечение-данных-из-jira-не-удалось)
- [Примеры](#примеры)
- [Интеграция с GitHub PR](#интеграция-с-github-pr)
- [Интеграция с GitLab MR](#интеграция-с-gitlab-mr)
- [Создание DoD вручную](#создание-dod-вручную)

## Обзор

Система автоматического анализа кода анализирует изменения (git diff, GitHub PR, GitLab MR) с использованием анализа графа свойств кода (Code Property Graph, CPG) для предоставления всесторонней обратной связи по ревью, включая:

- Обнаружение уязвимостей в безопасности
- Анализ влияния на производительность
- Оценку риска ошибок
- Анализ влияния на архитектуру
- Проверку соответствия критериям завершения (Definition of Done, DoD)

## Быстрый старт

### Базовое использование

```
# Запуск демо-версии с настройками по умолчанию
python demo_patch_review.py

# С пользовательской базой данных
python demo_patch_review.py --db /путь/к/cpg.duckdb

# Без функции DoD
python demo_patch_review.py --no-dod

# Автоматическая генерация DoD вместо извлечения из PR
python demo_patch_review.py --auto-dod

# Интерактивное подтверждение DoD (просмотр и редактирование перед продолжением)
python demo_patch_review.py --interactive
python demo_patch_review.py -i
```

### Программное использование

```
import duckdb
from src.patch_review import ReviewWorkflow

# Подключение к базе данных CPG
conn = duckdb.connect('cpg.duckdb')

# Настройка параметров DoD
dod_config = {
    'auto_generate': True,
    'interactive': False,  # Установите True для интерактивного подтверждения DoD
    'extraction': {
        'sources': ['pr_body', 'jira', 'commit_message'],
        'formats': ['checklist', 'yaml', 'markdown'],
    },
}

# Создание рабочего процесса
workflow = ReviewWorkflow(conn, dod_config=dod_config)

# Запуск проверки
verdict = workflow.run(
    patch_source='git_diff',
    patch_data={'diff': содержание_diff},
    pr_body=описание_pr,  # Для извлечения DoD
    task_description=описание_задачи,  # Для генерации DoD
    interactive_mode=False,  # Установите True для интерактивного подтверждения DoD
)

# Доступ к результатам
print(f"Оценка: {verdict.overall_score}/100")
print(f"Рекомендация: {verdict.recommendation.value}")

# Результаты проверки DoD
if verdict.dod_validation:
    print(f"Соответствие DoD: {verdict.dod_validation.compliance_score}%")
```

## Архитектура

### Конвейер рабочего процесса

```
parse_patch → extract_dod → [generate_dod] → [confirm_dod] → generate_delta_cpg
    ↓
run_analyzers → generate_verdicts → aggregate → validate_dod → format_output
```

**Примечания:**
- `[generate_dod]` выполняется только если DoD не найден в источниках
- `[confirm_dod]` выполняется только в интерактивном режиме (флаг `--interactive`)

### Компоненты

| Компонент | Описание |
| --- | --- |
| PatchParser | Парсит git-диффы, GitHub PR, GitLab MR |
| DoDExtractor | Извлекает DoD из тела PR, Jira, сообщения коммита |
| DoDGenerator | Генерирует DoD с помощью LLM, если он не найден |
| DoDConfirmer | Интерактивное подтверждение DoD через CLI (просмотр, редактирование, пропуск) |
| DeltaCPGGenerator | Создаёт дельта-наложение CPG для изменений |
| Analyzers | Анализаторы: вызовов, потока данных, управления, зависимостей |
| VerdictGenerators | Генераторы вердиктов: безопасность, производительность, ошибки, архитектура |
| DoDValidator | Проверяет соответствие DoD результатам ревью |
| VerdictAggregator | Объединяет вердикты в итоговое ревью |

## Определение готовности (DoD)

### Источники DoD

Система может извлекать DoD из нескольких источников (с настраиваемым приоритетом):

1. **Описание PR** — Markdown-чек-лист в описании PR/MR
2. **Jira** — пользовательское поле или описание из привязанного тикета
3. **Сообщение коммита** — раздел DoD в первом коммите
4. **Ручной ввод** — ввод через CLI или API
5. **Автогенерация** — LLM генерирует на основе описания задачи

### Форматы DoD

Поддерживаемые форматы извлечения DoD:

#### Markdown-чек-лист

```
- [ ] Покрытие тестами не менее 80%
- [ ] Прошёл CI/CD
- [ ] Обновлена документация
- [ ] Проведён код-ревью
```

## Определение завершённости (Definition of Done)

- [ ] Функциональность работает, как ожидается
- [ ] Не внесено уязвимостей безопасности
- [ ] Добавлены модульные тесты
- [ ] Обновлена документация

```
#### Блок YAML
```yaml
```yaml
dod:
  - description: Функциональность работает, как ожидается
    type: functional
  - description: Модульные тесты проходят
    type: test
```

```
#### Блок JSON
```json
```json
{
  "dod": [
    {"description": "Функциональность работает", "type": "functional"},
    {"description": "Тесты проходят", "type": "test"}
  ]
}
```

```
### Типы критериев

| Тип | Описание | Проверка |
|------|-------------|------------|
| `functional` | Требования к функциональности | Ручная проверка (невозможно автоматически проверить) |
| `security` | Отсутствие уязвимостей | Оценка по результатам анализа безопасности |
| `test` | Наличие и прохождение тестов | Рекомендации по ошибкам |
| `documentation` | Обновление документации | Ручная проверка |
| `performance` | Отсутствие регрессии производительности | Оценка производительности |
| `code_quality` | Соответствие стилю кода | Оценка архитектуры |

### Интерактивное подтверждение DoD

При запуске с флагом `--interactive` пользователь может просмотреть и изменить DoD перед началом проверки:
```

============================================================
ОПРЕДЕЛЕНИЕ ЗАВЕРШЁННОСТИ — ПОДТВЕРЖДЕНИЕ
============================================================

## Текущее DoD (из pr_body):

1. [FUNC] Функциональность работает, как ожидается
2. [SECU] Не внесено уязвимостей безопасности
3. [TEST] Добавлены модульные тесты для новой функциональности
4. [PERF] Отсутствие регрессии производительности
5. [CODE] Код соответствует стилю проекта

---

Всего: 5 пунктов

Опции:
  [c] Подтвердить и продолжить
  [e] Редактировать пункты
  [a] Добавить новый пункт
  [r] Удалить пункт
  [s] Пропустить проверку DoD
  [q] Отменить проверку

```
**Опции:**
- **Подтвердить (c)** — Принять текущее DoD и продолжить проверку
- **Редактировать (e)** — Изменить описания и типы пунктов
- **Добавить (a)** — Добавить новые пункты DoD с выбором типа
- **Удалить (r)** — Удалить пункты из списка
- **Пропустить (s)** — Пропустить проверку DoD полностью (проверка продолжится без DoD)
- **Отмена (q)** — Отменить процесс проверки

**Горячие клавиши для добавления/редактирования:**
| Клавиша | Тип |
|----------|------|
| `f` | Функциональный |
| `s` | Безопасность |
| `t` | Тестирование |
| `d` | Документация |
| `p` | Производительность |
| `q` | Качество кода |

### Проверка DoD

Каждый пункт DoD проверяется на соответствие результатам анализа:

- **Безопасность**: Проверяется по результатам анализа безопасности (наличие критических или серьёзных уязвимостей приводит к провалу)
- **Тесты**: Проверяется по количеству рекомендаций по тестам
- **Производительность**: Проверяется по оценке производительности
- **Качество кода**: Проверяется по оценке архитектуры
- **Функциональность/Документация**: Не могут быть проверены автоматически (требуется ручная проверка)

## Конфигурация

### config/code_review.yaml

```yaml
# Конфигурация определения готовности (Definition of Done)
dod:
  sources:  # Источники получения критериев готовности
    - pr_body
    - jira
    - commit_message
    - manual
  source_priority:  # Приоритет источников при объединении данных
    - pr_body
    - jira
    - commit_message
  formats:  # Поддерживаемые форматы описания критериев
    - checklist
    - yaml
    - markdown
    - json
  auto_generate: true  # Автоматически генерировать критерии, если не найдены
  interactive_confirm: false  # Включить подтверждение в CLI (диалоговые запросы)

  # Интеграция с Jira
  jira:
    url: ${JIRA_URL}
    api_key: ${JIRA_API_KEY}
    dod_field: "customfield_10001"  # ID кастомного поля в Jira для критериев готовности

  # Настройки валидации
  validation:
    strict_mode: false  # Строгий режим валидации (прерывать при ошибках)
    blocking_severities:  # Уровни серьёзности, блокирующие мердж
      - critical
      - high

# Политика ревью
policy:
  block_on_critical_security: true  # Блокировать слияние при критических уязвимостях
  min_score_to_approve: 70.0  # Минимальный общий балл для одобрения ревью
  require_dod_compliance: false  # Требовать соответствие критериям готовности
  min_dod_compliance_score: 60.0  # Минимальный балл соответствия DoD

# Веса вердиктов
verdicts:
  weights:
    security: 0.35      # Безопасность
    performance: 0.20   # Производительность
    error: 0.25         # Обработка ошибок
    architecture: 0.20  # Архитектура
  dod_compliance_weight: 0.10  # Вес соответствия критериям готовности
```

### Переменные окружения

| Переменная | Описание |
| --- | --- |
| JIRA_URL | URL-адрес сервера Jira для извлечения критериев готовности |
| JIRA_API_KEY | Ключ аутентификации для API Jira |
| GITHUB_TOKEN | Токен API GitHub для доступа к PR |
| GITLAB_TOKEN | Токен API GitLab для доступа к MR |

## Справочная документация по API

### ReviewWorkflow

```
workflow = ReviewWorkflow(
    conn: duckdb.DuckDBPyConnection,
    config: Optional[AggregationConfig] = None,
    policy: Optional[ReviewPolicy] = None,
    dod_config: Optional[Dict[str, Any]] = None,
)

verdict = workflow.run(
    patch_source: str,  # 'git_diff', 'github_pr', 'gitlab_mr'
    patch_data: Dict[str, Any],
    session_id: Optional[str] = None,
    policy: Optional[ReviewPolicy] = None,
    task_description: Optional[str] = None,
    pr_body: Optional[str] = None,
    jira_ticket: Optional[str] = None,
    interactive_mode: bool = False,
)
```

### ReviewVerdict

```
class ReviewVerdict:
    patch_id: str
    overall_score: float  # 0–100
    recommendation: Recommendation  # APPROVE, REQUEST_CHANGES, BLOCK, COMMENT

    # Подрезультаты
    security: SecurityVerdict
    performance: PerformanceVerdict
    error: ErrorVerdict
    architecture: ArchitectureVerdict

    # Обнаруженные проблемы
    all_findings: List[Finding]
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int

    # Проверка соответствия Definition of Done (DoD)
    dod_validation: Optional[DoDValidationResult]
    dod_compliance_score: float  # 0–100
```

### DoDValidationResult

```
class DoDValidationResult:
    dod: DefinitionOfDone
    total_items: int
    satisfied_count: int
    failed_count: int
    pending_count: int
    compliance_score: float  # 0–100
    blocking_failures: List[DoDItem]
    is_compliant: bool  # True, если все пункты выполнены
```

## Форматы вывода

### Вывод в формате JSON

```
{
  "patch_id": "PATCH_abc123",
  "overall_score": 45.5,
  "recommendation": "REQUEST_CHANGES",
  "dod_compliance_score": 60.0,
  "findings": [...],
  "dod_validation": {
    "compliance_score": 60.0,
    "items": [
      {"description": "...", "satisfied": true, "evidence": "..."},
      {"description": "...", "satisfied": false, "evidence": "..."}
    ]
  }
}
```

### Вывод в формате Markdown

```

```

## Резюме проверки изменений

**Общий балл:** 45/100

**Рекомендация:** ТРЕБУЮТСЯ_ИЗМЕНЕНИЯ

### Критерии завершённости (Definition of Done)

**Уровень соответствия:** 60%

- ✅ Функция работает, как ожидается
- ❌ Не внесены уязвимости в плане безопасности
- Доказательство: Обнаружены проблемы безопасности: SQL-инъекция
- ⏳ Добавлены модульные тесты (ожидает ручной проверки)

### Результаты анализа безопасности

1. [ВЫСОКИЙ] Уязвимость к SQL-инъекции
   - Местоположение: src/auth/login.py:14
   - CWE-89

## Устранение неполадок

### «DoD не найден»

Если DoD не извлекается:

1. Убедитесь, что тело PR содержит раздел DoD с правильным форматом
2. Проверьте, что `dod.sources` включает ваш тип источника
3. Убедитесь, что `dod.formats` включает ваш формат DoD
4. Включите `auto_generate: true`, чтобы создавать DoD при его отсутствии

### «Проверка DoD пропущена»

Для проверки DoD необходимо:
- Успешное извлечение или создание DoD
- Сформированный результат проверки
- Отсутствие ошибок в рабочем процессе

### «Извлечение данных из Jira не удалось»

1. Убедитесь, что заданы переменные окружения JIRA_URL и JIRA_API_KEY
2. Проверьте права доступа к Jira API
3. Убедитесь, что параметр `dod_field` указывает на правильное пользовательское поле

## Примеры

### Интеграция с GitHub PR

```
# Обработка события из GitHub PR
pr_data = {
    'number': 123,
    'title': 'Добавить аутентификацию',
    'body': pr_body_with_dod,
    'diff_url': 'https://api.github.com/repos/...',
}

verdict = workflow.run(
    patch_source='github_pr',
    patch_data=pr_data,
    pr_body=pr_data['body'],
)
```

### Интеграция с GitLab MR

```
mr_data = {
    'iid': 456,
    'title': 'Добавить аутентификацию',
    'description': mr_description_with_dod,
}

verdict = workflow.run(
    patch_source='gitlab_mr',
    patch_data=mr_data,
    pr_body=mr_data['description'],
)
```

### Ручное создание списка DoD

```
from src.patch_review.dod import DoDExtractor

extractor = DoDExtractor()
dod = extractor.create_manual_dod(
    items=[
        "Функция работает как ожидается",
        "Отсутствуют уязвимости безопасности",
        "Добавлены модульные тесты",
    ],
    types=["functional", "security", "test"],
)
```
