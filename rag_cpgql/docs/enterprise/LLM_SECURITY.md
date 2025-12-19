# Безопасность LLM-интеграции

> Руководство по защите данных при работе с LLM-провайдерами

---

## Обзор

Модуль `SecureLLMProvider` обеспечивает комплексную защиту при работе с внешними LLM-провайдерами (GigaChat, OpenAI и др.). Модуль реализует принцип "defence in depth" — многоуровневую защиту данных.

### Гарантии безопасности

| Гарантия | Реализация |
|----------|------------|
| **Код не передаётся** | Только NL-запросы отправляются в LLM |
| **Pre-request DLP** | Сканирование до отправки |
| **Post-response DLP** | Маскирование в ответах |
| **Полный аудит** | Логирование каждого запроса |
| **SIEM интеграция** | События в реальном времени |
| **Секреты в Vault** | API-ключи в HashiCorp Vault |

---

## Архитектура

### Конвейер обработки запроса

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SecureLLMProvider                               │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     1. PRE-REQUEST PHASE                         │   │
│  │                                                                  │   │
│  │  User Query ──► [DLP Scanner] ──┬──► BLOCK ──► DLPBlockedException │
│  │                                 │                                │   │
│  │                                 ├──► MASK ──► Masked Query       │   │
│  │                                 │                                │   │
│  │                                 └──► PASS ──► Original Query     │   │
│  │                                                    │              │   │
│  │                                    ┌───────────────┘              │   │
│  │                                    ▼                              │   │
│  │                             [SIEM Event]                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                       │                                 │
│                                       ▼                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    2. LLM PROVIDER CALL                          │   │
│  │                                                                  │   │
│  │  [VaultClient] ──► API Key ──► [GigaChat/OpenAI] ──► Response   │   │
│  │                                                                  │   │
│  │  • API ключ из Vault                                            │   │
│  │  • TLS соединение                                               │   │
│  │  • Request ID tracking                                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                       │                                 │
│                                       ▼                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   3. POST-RESPONSE PHASE                         │   │
│  │                                                                  │   │
│  │  Response ──► [DLP Scanner] ──► Mask Sensitive Data ──► User    │   │
│  │                     │                                            │   │
│  │                     ▼                                            │   │
│  │              [SIEM Event]                                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                       │                                 │
│                                       ▼                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     4. AUDIT LOGGING                             │   │
│  │                                                                  │   │
│  │  • Request ID                  • Token usage                     │   │
│  │  • User ID                     • Latency                         │   │
│  │  • Session ID                  • DLP matches                     │   │
│  │  • IP address                  • Error details                   │   │
│  │                                                                  │   │
│  │  ──► [PostgreSQL] + [SIEM]                                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Принципы защиты данных

### 1. Исходный код не передаётся

```
┌──────────────────────────────────────────────────────────────────┐
│                      ПЕРИМЕТР ОРГАНИЗАЦИИ                         │
│                                                                  │
│   [Source Code] ──► [CPG Analysis] ──► [DuckDB]                 │
│                                           │                      │
│                                           ▼                      │
│   [User] ──► "Find buffer overflow in function X"               │
│                           │                                      │
│                           ▼                                      │
│                   [RAG Query Engine]                            │
│                           │                                      │
│                           ▼                                      │
│               NL Query (no code snippets)                       │
│                           │                                      │
└───────────────────────────┼──────────────────────────────────────┘
                            │
                            ▼
                     [GigaChat API]
                            │
                            ▼
               NL Response (explanation)
```

**Что передаётся LLM:**
- Текстовые запросы пользователей
- Метаданные (имена функций, файлов)
- Структурированные данные из CPG

**Что НЕ передаётся:**
- Исходный код
- Содержимое файлов
- Строки подключения
- Секреты и учётные данные

---

## API Reference

### SecureLLMProvider

```python
from src.security.llm import SecureLLMProvider
from src.security.config import get_security_config
from src.llm.gigachat import GigaChatProvider

# Создание защищённого провайдера
base_provider = GigaChatProvider(config)
secure_provider = SecureLLMProvider(
    wrapped_provider=base_provider,
    config=get_security_config()
)

# Использование (с контекстом безопасности)
response = secure_provider.generate(
    system_prompt="You are a security analyst.",
    user_prompt="Analyze this function for vulnerabilities.",
    _user_id="analyst@company.com",
    _session_id="sess-12345",
    _ip_address="10.0.0.50"
)
```

### Методы

| Метод | Описание |
|-------|----------|
| `generate(system_prompt, user_prompt, **kwargs)` | Генерация с полной защитой |
| `generate_simple(prompt, **kwargs)` | Упрощённый вызов |
| `generate_stream(system_prompt, user_prompt, **kwargs)` | Потоковая генерация |
| `is_available()` | Проверка доступности провайдера |

### Контекстные параметры

| Параметр | Описание |
|----------|----------|
| `_user_id` | ID пользователя для аудита |
| `_session_id` | ID сессии |
| `_ip_address` | IP-адрес клиента |

---

## Конфигурация

### Полная конфигурация (config.yaml)

```yaml
security:
  enabled: true

  # Логирование LLM-взаимодействий
  llm_logging:
    enabled: true
    log_prompts: true           # Логировать промпты
    redact_prompts: true        # Редактировать чувствительные данные
    max_prompt_length: 2000     # Макс. длина в логе
    log_responses: true         # Логировать ответы
    max_response_length: 5000   # Макс. длина ответа в логе
    log_token_usage: true       # Логировать использование токенов
    log_latency: true           # Логировать задержку
    log_to_database: true       # Сохранять в PostgreSQL
    log_to_siem: true           # Отправлять в SIEM

  # DLP конфигурация
  dlp:
    enabled: true
    pre_request:
      enabled: true
      default_action: WARN
    post_response:
      enabled: true
      default_action: MASK

  # SIEM интеграция
  siem:
    enabled: true
    syslog:
      enabled: true
      host: "siem.company.com"
      port: 514

  # HashiCorp Vault
  vault:
    enabled: true
    url: "https://vault.company.com:8200"
    auth_method: "approle"
    llm_secrets_path: "codegraph/llm"
```

---

## Обработка ошибок

### DLPBlockedException

```python
from src.security.dlp import DLPBlockedException

try:
    response = secure_provider.generate(
        system_prompt="...",
        user_prompt=user_input
    )
except DLPBlockedException as e:
    # Запрос заблокирован DLP
    logger.warning(f"DLP blocked: {e.message}")

    # Информация о нарушениях
    for match in e.matches:
        print(f"Category: {match.category}")
        print(f"Pattern: {match.pattern_name}")
        print(f"Severity: {match.severity}")

    # Вернуть ошибку клиенту
    return {
        "error": "dlp_blocked",
        "message": "Request contains sensitive data",
        "categories": e.to_dict()["categories"]
    }
```

### Структура ошибки

```json
{
  "error": "dlp_blocked",
  "message": "Request blocked by DLP policy. Detected 2 violation(s) in categories: credentials, pii. Please remove sensitive data before retrying.",
  "categories": ["credentials", "pii"],
  "violation_count": 2
}
```

---

## Управление секретами

### Интеграция с HashiCorp Vault

```python
from src.security.vault import VaultClient
from src.security.config import get_security_config

config = get_security_config()
vault = VaultClient(config.vault)

# Получение учётных данных LLM
credentials = vault.get_llm_credentials()

# Результат:
# {
#   "gigachat_credentials": "...",
#   "openai_api_key": "sk-...",
#   "anthropic_api_key": "sk-ant-..."
# }
```

### Fallback на переменные окружения

При недоступности Vault используются переменные окружения:

| Переменная | Провайдер |
|------------|-----------|
| `GIGACHAT_CREDENTIALS` | GigaChat |
| `OPENAI_API_KEY` | OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI |

---

## Аудит и логирование

### Структура лога запроса

```json
{
  "timestamp": "2025-12-14T10:30:00.000Z",
  "request_id": "req-12345",
  "event": "llm_request",
  "provider": "GigaChatProvider",
  "model": "GigaChat-2-Pro",
  "user_id": "analyst@company.com",
  "session_id": "sess-67890",
  "ip_address": "10.0.0.50",
  "latency_ms": 1250.5,
  "tokens": {
    "prompt_tokens": 150,
    "completion_tokens": 450,
    "total_tokens": 600
  },
  "dlp": {
    "pre_request_matches": 0,
    "post_response_matches": 1,
    "action": "MASK"
  }
}
```

### SIEM события

| Событие | Когда отправляется |
|---------|-------------------|
| `LLM_REQUEST` | При отправке запроса |
| `LLM_RESPONSE` | При получении ответа |
| `LLM_ERROR` | При ошибке |
| `DLP_BLOCK` | При блокировке DLP |
| `DLP_MASK` | При маскировании |

---

## Потоковая генерация

### Особенности streaming mode

```python
# Потоковая генерация с защитой
for chunk in secure_provider.generate_stream(
    system_prompt="You are a security analyst.",
    user_prompt="Explain this vulnerability.",
    _user_id="analyst@company.com"
):
    # Chunk уже прошёл pre-request DLP
    print(chunk, end="", flush=True)

# Post-response DLP выполняется после завершения потока
# Если обнаружены чувствительные данные - событие в SIEM
```

**Ограничения streaming:**
- Pre-request DLP работает полностью
- Post-response DLP логирует совпадения, но не может модифицировать уже отправленные chunks
- Рекомендуется для интерактивных сценариев с низким риском

---

## Метрики и мониторинг

### Prometheus метрики

```promql
# Количество LLM-запросов
rate(llm_requests_total[5m])

# Количество DLP-блокировок
rate(dlp_blocks_total{phase="llm_request"}[5m])

# Средняя задержка LLM
histogram_quantile(0.95, rate(llm_latency_seconds_bucket[5m]))

# Использование токенов
sum(rate(llm_tokens_total[1h])) by (provider, model)

# Ошибки LLM
rate(llm_errors_total[5m])
```

### Grafana Dashboard

```json
{
  "panels": [
    {
      "title": "LLM Requests per Minute",
      "query": "rate(llm_requests_total[1m])"
    },
    {
      "title": "DLP Block Rate",
      "query": "rate(dlp_blocks_total{phase='llm_request'}[5m]) / rate(llm_requests_total[5m])"
    },
    {
      "title": "P95 Latency",
      "query": "histogram_quantile(0.95, rate(llm_latency_seconds_bucket[5m]))"
    },
    {
      "title": "Token Usage by Model",
      "query": "sum(rate(llm_tokens_total[1h])) by (model)"
    }
  ]
}
```

---

## Лучшие практики

### Для разработчиков

1. **Всегда передавайте контекст** — `_user_id`, `_session_id`, `_ip_address`
2. **Обрабатывайте DLPBlockedException** — информируйте пользователя
3. **Используйте streaming осторожно** — понимайте ограничения post-DLP
4. **Не логируйте ответы целиком** — используйте `max_response_length`

### Для операторов

1. **Мониторьте DLP block rate** — высокий показатель может указывать на проблему
2. **Настройте алерты на LLM_ERROR** — ошибки провайдера требуют внимания
3. **Ротируйте API-ключи** — используйте Vault с auto-rotation
4. **Аудит токенов** — отслеживайте аномальное потребление

### Для compliance

1. **Документируйте data flow** — какие данные и куда передаются
2. **Храните логи** — минимум 1 год для compliance
3. **Регулярный аудит** — проверяйте эффективность DLP
4. **Incident response** — план реагирования на DLP_BLOCK

---

## Связанные документы

- [Enterprise Security Brief](./ENTERPRISE_SECURITY_BRIEF.md) — Обзор безопасности
- [DLP Security](./DLP_SECURITY.md) — DLP паттерны и конфигурация
- [SIEM Integration](./SIEM_INTEGRATION.md) — Интеграция с SIEM
- [Vault Integration](#) — Управление секретами

---

*Версия: 1.0 | Декабрь 2025*
