# DLP: Предотвращение утечки данных

> Техническая документация для команд ИБ и compliance

---

## Обзор

Модуль DLP (Data Loss Prevention) в CodeGraph обеспечивает защиту от утечки конфиденциальных данных при работе с LLM. Система сканирует как входящие запросы пользователей, так и исходящие ответы LLM.

### Ключевые возможности

- **25+ паттернов** для обнаружения конфиденциальных данных
- **Pre-request сканирование** — блокировка до отправки в LLM
- **Post-response сканирование** — маскирование в ответах LLM
- **4 режима действий**: BLOCK, MASK, WARN, LOG_ONLY
- **Интеграция с SIEM** — отправка событий в реальном времени
- **Webhook уведомления** — интеграция с внешними DLP-системами

---

## Архитектура

### Конвейер обработки

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          ПОЛЬЗОВАТЕЛЬ                                    │
│                              │                                          │
│                              ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    PRE-REQUEST SCANNER                             │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │ │
│  │  │ Credentials │  │    PII      │  │ Source Code │               │ │
│  │  │   (HIGH)    │  │  (MEDIUM)   │  │    (LOW)    │               │ │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘               │ │
│  │         │                │                │                       │ │
│  │         └────────────────┴────────────────┘                       │ │
│  │                          │                                        │ │
│  │              ┌───────────┴───────────┐                           │ │
│  │              ▼           ▼           ▼                           │ │
│  │          [BLOCK]     [MASK]     [WARN/LOG]                       │ │
│  │              │           │           │                           │ │
│  │              │     ┌─────┴─────┐     │                           │ │
│  │              │     │ Замена на │     │                           │ │
│  │              │     │[REDACTED] │     │                           │ │
│  │              │     └─────┬─────┘     │                           │ │
│  └──────────────┼───────────┼───────────┼────────────────────────────┘ │
│                 │           │           │                              │
│                 │      ┌────┴────┐      │                              │
│                 │      ▼         ▼      │                              │
│            SIEM Event     GigaChat API  │                              │
│                               │         │                              │
│                               ▼         │                              │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                   POST-RESPONSE SCANNER                           │ │
│  │                          │                                        │ │
│  │              Маскирование конфиденциальных                        │ │
│  │              данных в ответе LLM                                  │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              │                                          │
│                              ▼                                          │
│                    ОТВЕТ ПОЛЬЗОВАТЕЛЮ                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Категории обнаружения

### 1. Credentials (Учётные данные) — HIGH Severity

| Паттерн | Regex | Описание |
|---------|-------|----------|
| `api_key_generic` | `(?i)(api[_-]?key\|apikey)["\s:=]+["\']?([a-zA-Z0-9_\-]{20,})["\']?` | Универсальный API-ключ |
| `aws_access_key` | `AKIA[0-9A-Z]{16}` | AWS Access Key ID |
| `aws_secret_key` | `(?i)aws[_\s]*secret[_\s]*access[_\s]*key["\s:=]+["\']?([a-zA-Z0-9/+=]{40})["\']?` | AWS Secret Access Key |
| `private_key` | `-----BEGIN (RSA \|EC \|OPENSSH \|DSA )?PRIVATE KEY-----` | Приватный ключ (RSA, EC, DSA) |
| `password_pattern` | `(?i)(password\|passwd\|pwd)["\s:=]+["\']?([^\s"\']{8,})["\']?` | Пароль в конфиге/коде |
| `bearer_token` | `(?i)bearer\s+[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+` | JWT Bearer токен |
| `github_token` | `gh[pousr]_[A-Za-z0-9_]{36,}` | GitHub Personal Access Token |

**Действие по умолчанию**: `BLOCK`

### 2. PII (Персональные данные) — MEDIUM Severity

| Паттерн | Regex | Маска | Описание |
|---------|-------|-------|----------|
| `email` | `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` | `[EMAIL]` | Email адрес |
| `phone_ru` | `(\+7\|8)?[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}` | `[PHONE]` | Телефон РФ |
| `phone_us` | `(\+1)?[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}` | `[PHONE]` | Телефон США |
| `ssn` | `\b\d{3}-\d{2}-\d{4}\b` | `[SSN]` | US SSN |
| `credit_card` | `\b(?:\d{4}[\s-]?){3}\d{4}\b` | `[CARD]` | Банковская карта |
| `ip_address` | `\b(?:\d{1,3}\.){3}\d{1,3}\b` | `[IP]` | IPv4 адрес |
| `passport_ru` | `\b\d{2}\s?\d{2}\s?\d{6}\b` | `[PASSPORT]` | Паспорт РФ |

**Действие по умолчанию**: `MASK`

### 3. Source Code (Исходный код) — LOW Severity

| Паттерн | Regex | Маска | Описание |
|---------|-------|-------|----------|
| `connection_string` | `(?i)(jdbc\|mysql\|postgresql\|mongodb\|redis)://[^\s"\'<>]+` | `[CONN_STRING]` | Строка подключения |
| `internal_path_unix` | `(/home/\|/var/\|/etc/\|/opt/)[^\s"\'<>\|]+` | `[PATH]` | Unix путь |
| `internal_path_windows` | `[A-Z]:\\(Users\|Windows\|Program)[^\s"\'<>\|]*` | `[PATH]` | Windows путь |

**Действие по умолчанию**: `WARN`

---

## Действия DLP

### Иерархия приоритетов

| Приоритет | Действие | Описание | Результат |
|:---------:|----------|----------|-----------|
| 4 (макс.) | `BLOCK` | Полная блокировка | Запрос отклонён, ошибка клиенту |
| 3 | `MASK` | Маскирование | Данные заменены на `[REDACTED]` |
| 2 | `WARN` | Предупреждение | Запрос пропущен, событие в SIEM |
| 1 | `LOG_ONLY` | Только логирование | Запись в аудит-лог |

### Логика выбора действия

```python
# При множественных совпадениях выбирается максимальный приоритет
action_priority = {
    DLPAction.BLOCK: 4,
    DLPAction.MASK: 3,
    DLPAction.WARN: 2,
    DLPAction.LOG_ONLY: 1,
}

# Пример: найдены API-ключ (BLOCK) и email (MASK)
# Результат: BLOCK (приоритет 4 > 3)
```

---

## Конфигурация

### Базовая конфигурация (config.yaml)

```yaml
security:
  enabled: true

  dlp:
    enabled: true

    # Pre-request сканирование (до отправки в LLM)
    pre_request:
      enabled: true
      default_action: WARN

    # Post-response сканирование (после получения от LLM)
    post_response:
      enabled: true
      default_action: MASK

    # Категории и паттерны
    categories:
      credentials:
        enabled: true
        action: BLOCK
        patterns: []  # Используются паттерны по умолчанию

      pii:
        enabled: true
        action: MASK
        patterns:
          - name: custom_inn
            regex: '\b\d{10,12}\b'
            mask_with: '[INN]'
            description: 'ИНН физ/юр лица'

      source_code:
        enabled: true
        action: WARN
        patterns: []

    # Пользовательские ключевые слова
    keywords:
      sensitive_terms:
        words:
          - "конфиденциально"
          - "секретно"
          - "для служебного пользования"
        case_sensitive: false

    keywords_action: LOG_ONLY

    # Webhook для внешней DLP-системы
    webhook:
      enabled: false
      endpoint: "https://dlp.company.com/api/scan"
      auth_header: "Bearer ${DLP_WEBHOOK_TOKEN}"
      timeout_seconds: 10
      notify_on:
        - BLOCK
        - WARN
```

### Добавление пользовательских паттернов

```python
from src.security.dlp.patterns import PatternRegistry
from src.security.config import DLPAction

registry = PatternRegistry(config)

# Добавить паттерн для ИНН
registry.add_pattern(
    category="pii",
    name="inn_ru",
    regex=r'\b\d{10,12}\b',
    action=DLPAction.MASK,
    mask_with="[INN]"
)

# Добавить ключевые слова
registry.add_keywords(
    list_name="internal_projects",
    keywords=["Project Alpha", "Codename Beta"],
    case_sensitive=False
)
```

---

## API Reference

### ContentScanner

```python
from src.security.dlp.scanner import ContentScanner, DLPBlockedException
from src.security.config import get_security_config

# Инициализация сканера
config = get_security_config()
scanner = ContentScanner(config.dlp)

# Pre-request сканирование
result = scanner.scan_request(user_prompt)

if result.blocked:
    # Запрос заблокирован
    raise DLPBlockedException(result.matches)
elif result.action == DLPAction.MASK:
    # Использовать маскированный контент
    user_prompt = result.modified_content

# Отправка в LLM...
llm_response = await llm_client.complete(user_prompt)

# Post-response сканирование
result = scanner.scan_response(llm_response)
if result.has_matches:
    # Маскирование ответа
    llm_response = result.modified_content

return llm_response
```

### ScanResult

```python
@dataclass
class ScanResult:
    has_matches: bool           # Найдены ли совпадения
    matches: List[DLPMatch]     # Список совпадений
    action: DLPAction           # Рекомендуемое действие
    modified_content: str       # Маскированный контент
    blocked: bool               # Блокировать ли запрос
```

### DLPMatch

```python
@dataclass
class DLPMatch:
    category: str          # Категория (credentials, pii, source_code)
    pattern_name: str      # Имя паттерна
    match_type: MatchType  # REGEX или KEYWORD
    matched_text: str      # Найденный текст
    start: int             # Позиция начала
    end: int               # Позиция конца
    action: DLPAction      # Действие для этого совпадения
    mask_with: str         # Текст замены
    severity: str          # Критичность (critical, high, medium, low)
```

---

## Интеграция с SIEM

### События DLP

При каждом срабатывании DLP отправляется событие в SIEM:

```json
{
  "event_type": "DLP_BLOCK",
  "timestamp": "2025-12-14T10:30:00.000Z",
  "severity": "CRITICAL",
  "user_id": "user_123",
  "session_id": "sess_456",
  "category": "credentials",
  "pattern_name": "aws_access_key",
  "action_taken": "BLOCK",
  "match_count": 1,
  "masked_preview": "Found AWS key: AKIA...",
  "request_path": "/api/v1/scenarios/execute",
  "ip_address": "10.0.0.50"
}
```

### Типы событий

| Событие | Severity | Описание |
|---------|----------|----------|
| `DLP_BLOCK` | CRITICAL | Запрос заблокирован |
| `DLP_MASK` | WARNING | Данные маскированы |
| `DLP_WARN` | WARNING | Предупреждение |
| `DLP_LOG` | INFO | Только логирование |

---

## Webhook интеграция

### Формат запроса к внешней DLP

```json
POST /api/scan HTTP/1.1
Host: dlp.company.com
Authorization: Bearer xxx
Content-Type: application/json

{
  "scan_id": "scan_789",
  "timestamp": "2025-12-14T10:30:00.000Z",
  "content_type": "request",
  "user_id": "user_123",
  "matches": [
    {
      "category": "credentials",
      "pattern_name": "aws_access_key",
      "severity": "high",
      "action": "BLOCK"
    }
  ],
  "action_taken": "BLOCK"
}
```

---

## Лучшие практики

### Для настройки

1. **Начните с WARN** — установите все категории в WARN для оценки ложных срабатываний
2. **Постепенно ужесточайте** — переводите критичные категории в BLOCK после тестирования
3. **Настройте исключения** — добавьте whitelist для известных безопасных паттернов
4. **Мониторьте SIEM** — отслеживайте статистику срабатываний

### Для разработчиков

1. **Не логируйте matched_text** в production без маскирования
2. **Обрабатывайте DLPBlockedException** в API — возвращайте понятную ошибку
3. **Тестируйте паттерны** — используйте regex101.com для проверки

### Для compliance

1. **Документируйте паттерны** — ведите реестр используемых паттернов
2. **Регулярный аудит** — проверяйте эффективность обнаружения
3. **152-ФЗ compliance** — убедитесь, что PII-паттерны покрывают российские типы данных

---

## Метрики и мониторинг

### Prometheus метрики

```promql
# Количество блокировок
rate(dlp_blocks_total[5m])

# Количество масок
rate(dlp_masks_total[5m])

# Распределение по категориям
dlp_matches_total{category="credentials"}
dlp_matches_total{category="pii"}

# Среднее время сканирования
histogram_quantile(0.95, rate(dlp_scan_duration_seconds_bucket[5m]))
```

### Grafana Dashboard

```json
{
  "panels": [
    {
      "title": "DLP Blocks per Minute",
      "query": "rate(dlp_blocks_total[1m])"
    },
    {
      "title": "Top Triggered Patterns",
      "query": "topk(10, dlp_matches_total)"
    }
  ]
}
```

---

## Связанные документы

- [Enterprise Security Brief](./ENTERPRISE_SECURITY_BRIEF.md) — Обзор безопасности
- [SIEM Integration](./SIEM_INTEGRATION.md) — Интеграция с SIEM
- [LLM Security](./LLM_SECURITY.md) — Безопасность LLM

---

*Версия: 1.0 | Декабрь 2025*
