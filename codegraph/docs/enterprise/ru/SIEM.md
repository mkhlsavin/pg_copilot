# Интеграция с SIEM

> Руководство по интеграции для SOC-команд и команд мониторинга

---

## Обзор

CodeGraph поддерживает отправку событий безопасности в SIEM-системы в реальном времени. Поддерживаются три формата: Syslog (RFC 5424), CEF (ArcSight) и LEEF (QRadar).

### Ключевые возможности

- **3 формата вывода**: Syslog RFC 5424, CEF, LEEF
- **13 типов событий**: LLM, DLP, Auth, Vault, Rate Limiting
- **3 протокола транспорта**: UDP, TCP, TLS
- **Буферизация**: до 10,000 событий в очереди
- **Retry с backoff**: автоматический повтор при сбоях
- **Graceful degradation**: продолжение работы при недоступности SIEM

---

## Архитектура

### Компоненты системы

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ПРИЛОЖЕНИЕ                                   │
│                                                                     │
│  [LLM Provider] ──┐                                                 │
│                   │                                                 │
│  [DLP Scanner] ───┼──► [SecurityEvent] ──► [SIEMDispatcher]        │
│                   │                              │                  │
│  [Auth Module] ───┘                              │                  │
│                                                  │                  │
│                                           ┌──────▼──────┐           │
│                                           │ SIEMBuffer  │           │
│                                           │ (10K queue) │           │
│                                           └──────┬──────┘           │
│                                                  │                  │
│                    ┌─────────────────────────────┼─────────────────┐│
│                    │                             │                 ││
│                    ▼                             ▼                 ▼│
│           ┌──────────────┐            ┌──────────────┐    ┌──────────────┐│
│           │SysLogHandler │            │  CEFHandler  │    │ LEEFHandler  ││
│           │  (RFC 5424)  │            │  (ArcSight)  │    │  (QRadar)    ││
│           └──────┬───────┘            └──────┬───────┘    └──────┬───────┘│
└──────────────────┼───────────────────────────┼───────────────────┼────────┘
                   │                           │                   │
                   ▼                           ▼                   ▼
            ┌────────────┐              ┌────────────┐      ┌────────────┐
            │  Splunk    │              │  ArcSight  │      │  QRadar    │
            │  Graylog   │              │  Splunk    │      │            │
            │  rsyslog   │              │            │      │            │
            └────────────┘              └────────────┘      └────────────┘
```

---

## Типы событий

### SecurityEventType

| Тип события | Описание | Severity |
|-------------|----------|----------|
| `LLM_REQUEST` | Запрос к LLM-провайдеру | INFO (6) |
| `LLM_RESPONSE` | Ответ от LLM | INFO (6) |
| `LLM_ERROR` | Ошибка LLM-взаимодействия | ERROR (3) |
| `DLP_BLOCK` | Запрос заблокирован DLP | CRITICAL (2) |
| `DLP_MASK` | Данные маскированы | WARNING (4) |
| `DLP_WARN` | Предупреждение DLP | WARNING (4) |
| `DLP_LOG` | DLP логирование | INFO (6) |
| `AUTH_SUCCESS` | Успешная аутентификация | INFO (6) |
| `AUTH_FAILURE` | Неудачная аутентификация | WARNING (4) |
| `VAULT_ACCESS` | Доступ к секретам Vault | INFO (6) |
| `VAULT_ROTATE` | Ротация секретов | NOTICE (5) |
| `RATE_LIMIT` | Превышение лимита | WARNING (4) |
| `SECURITY_ALERT` | Критическое событие ИБ | ALERT (1) |

### Severity Levels (RFC 5424)

| Код | Уровень | Описание |
|:---:|---------|----------|
| 0 | EMERGENCY | Система неработоспособна |
| 1 | ALERT | Требуется немедленное действие |
| 2 | CRITICAL | Критическое состояние |
| 3 | ERROR | Ошибка |
| 4 | WARNING | Предупреждение |
| 5 | NOTICE | Важное уведомление |
| 6 | INFO | Информационное сообщение |
| 7 | DEBUG | Отладочное сообщение |

---

## Формат Syslog (RFC 5424)

### Структура сообщения

```
<PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID [STRUCTURED-DATA] MSG
```

### Пример сообщения

```
<134>1 2025-12-14T10:30:00.000Z codegraph-server codegraph 12345 DLP001
[dlp@12345 category="credentials" pattern="aws_access_key" action="BLOCK"]
DLP blocked request: AWS access key detected in user prompt
```

### Конфигурация

```yaml
security:
  siem:
    enabled: true
    syslog:
      enabled: true
      protocol: udp      # udp, tcp, tls
      host: "siem.company.com"
      port: 514
      facility: 16       # LOCAL0 (16-23)
      app_name: "codegraph"
      hostname: null     # Авто-определение
      tls:               # Только для protocol: tls
        ca_cert: "/path/to/ca.crt"
        client_cert: "/path/to/client.crt"
        client_key: "/path/to/client.key"
        verify: true
```

### Splunk интеграция

```conf
# inputs.conf
[udp://514]
sourcetype = syslog
index = security

# props.conf
[syslog]
TIME_FORMAT = %Y-%m-%dT%H:%M:%S.%3N%Z
SHOULD_LINEMERGE = false
```

---

## Формат CEF (ArcSight)

### Структура сообщения

```
CEF:Version|Device Vendor|Device Product|Device Version|Signature ID|Name|Severity|Extension
```

### Mapping Signature ID

| Event Type | Signature ID | Name |
|------------|--------------|------|
| `llm.request` | LLM001 | LLM Request |
| `llm.response` | LLM002 | LLM Response |
| `llm.error` | LLM003 | LLM Error |
| `dlp.block` | DLP001 | DLP Block |
| `dlp.mask` | DLP002 | DLP Mask |
| `dlp.warn` | DLP003 | DLP Warning |
| `auth.success` | AUTH01 | Auth Success |
| `auth.failure` | AUTH02 | Auth Failure |
| `vault.access` | VLT001 | Vault Access |
| `security.alert` | SEC001 | Security Alert |

### Пример сообщения

```
CEF:0|CodeGraph|CodeAnalysis|1.0|DLP001|DLP Block|8|
src=10.0.0.50 suser=analyst@company.com externalId=req-12345
msg=AWS access key detected rt=2025-12-14T10:30:00.000Z
cs1=GigaChat cs1Label=LLM Provider
cs4=credentials cs4Label=DLP Category
cs5=aws_access_key cs5Label=DLP Pattern
cn2=125 cn2Label=Latency MS
```

### Extension Fields

| Поле | CEF Key | Описание |
|------|---------|----------|
| IP адрес | `src` | IP источника |
| User ID | `suser` | Идентификатор пользователя |
| Request ID | `externalId` | ID запроса |
| Message | `msg` | Текст сообщения |
| Timestamp | `rt` | Время события |
| LLM Provider | `cs1` | Провайдер LLM |
| LLM Model | `cs2` | Модель LLM |
| Action | `cs3` | Выполненное действие |
| DLP Category | `cs4` | Категория DLP |
| DLP Pattern | `cs5` | Паттерн DLP |
| Tokens Used | `cn1` | Использовано токенов |
| Latency MS | `cn2` | Задержка в мс |

### Конфигурация CEF

```yaml
security:
  siem:
    cef:
      enabled: true
      host: "arcsight.company.com"
      port: 514
      protocol: tcp
      device_vendor: "CodeGraph"
      device_product: "CodeAnalysis"
      device_version: "1.0"
```

### ArcSight FlexConnector

```xml
<!-- connector.parser.xml -->
<parser>
  <name>CodeGraph CEF Parser</name>
  <pattern>CEF:0|CodeGraph|CodeAnalysis|.*</pattern>
</parser>
```

---

## Формат LEEF (QRadar)

### Структура сообщения

```
LEEF:Version|Vendor|Product|Version|EventID|Extension
```

### Пример сообщения

```
LEEF:2.0|CodeGraph|CodeAnalysis|1.0|DLP001|
cat=DLP	sev=8	src=10.0.0.50	usrName=analyst
msg=AWS access key detected	devTime=2025-12-14T10:30:00.000Z
```

### Конфигурация LEEF

```yaml
security:
  siem:
    leef:
      enabled: true
      host: "qradar.company.com"
      port: 514
      protocol: udp
      product_vendor: "CodeGraph"
      product_name: "CodeAnalysis"
      product_version: "1.0"
```

### QRadar Log Source

1. Admin → Log Sources → Add
2. Vendor: `CodeGraph`
3. Log Source Type: `Universal LEEF`
4. Protocol: Syslog
5. Port: 514

---

## Буферизация и надёжность

### Конфигурация буфера

```yaml
security:
  siem:
    buffer:
      max_size: 10000           # Максимум событий в очереди
      flush_interval_seconds: 5  # Интервал flush
      retry_attempts: 3          # Количество повторов
      retry_backoff_seconds: 2.0 # Задержка между повторами
```

### Поведение при сбоях

1. **Первая попытка** — немедленная отправка
2. **Сбой** — событие в буфер, retry через 2 сек
3. **Второй сбой** — retry через 4 сек (backoff × 2)
4. **Третий сбой** — retry через 8 сек
5. **После 3 сбоев** — событие в fallback-лог

### Статистика буфера

```python
dispatcher = get_siem_dispatcher()
stats = dispatcher.stats

print(f"События в очереди: {stats['queue_size']}")
print(f"Отправлено: {stats['sent_count']}")
print(f"Сбоев: {stats['failed_count']}")
print(f"Retry в ожидании: {stats['retry_pending']}")
```

---

## API Reference

### Создание событий

```python
from src.security.siem.base_handler import SecurityEvent, SecurityEventType
from src.security.siem.dispatcher import dispatch_security_event

# Создание события
event = SecurityEvent.create(
    event_type=SecurityEventType.DLP_BLOCK,
    message="AWS access key detected in user prompt",
    request_id="req-12345",
    severity=2,  # CRITICAL
    user_id="user_123",
    ip_address="10.0.0.50",
    dlp_category="credentials",
    dlp_pattern="aws_access_key",
    action="BLOCK"
)

# Отправка в SIEM
success = dispatch_security_event(event)
```

### SIEMDispatcher API

```python
from src.security.siem.dispatcher import SIEMDispatcher, init_siem_dispatcher
from src.security.config import get_security_config

# Инициализация
config = get_security_config()
dispatcher = init_siem_dispatcher(config.siem)

# Асинхронная отправка (через буфер)
dispatcher.dispatch(event)

# Синхронная отправка (bypass буфера, для критических)
dispatcher.dispatch_sync(event)

# Flush буфера
sent_count = dispatcher.flush()

# Статистика
print(dispatcher.stats)
print(f"Handlers: {dispatcher.handler_count}")
print(f"Enabled: {dispatcher.is_enabled}")

# Закрытие
dispatcher.close()
```

---

## Примеры событий

### DLP Block Event

```json
{
  "event_type": "dlp.block",
  "timestamp": "2025-12-14T10:30:00.000Z",
  "request_id": "req-12345",
  "severity": 2,
  "message": "DLP blocked request: AWS access key detected",
  "user_id": "analyst@company.com",
  "ip_address": "10.0.0.50",
  "dlp_category": "credentials",
  "dlp_pattern": "aws_access_key",
  "action": "BLOCK"
}
```

### LLM Request Event

```json
{
  "event_type": "llm.request",
  "timestamp": "2025-12-14T10:30:00.000Z",
  "request_id": "req-67890",
  "severity": 6,
  "message": "LLM request to GigaChat",
  "user_id": "analyst@company.com",
  "provider": "GigaChat",
  "model": "GigaChat-2-Pro",
  "tokens_used": 150,
  "latency_ms": 1250.5
}
```

### Auth Failure Event

```json
{
  "event_type": "auth.failure",
  "timestamp": "2025-12-14T10:30:00.000Z",
  "request_id": "req-11111",
  "severity": 4,
  "message": "Authentication failed: invalid credentials",
  "user_id": "unknown",
  "ip_address": "10.0.0.99",
  "details": {
    "reason": "invalid_password",
    "attempts": 3
  }
}
```

---

## Мониторинг и алерты

### Grafana Dashboard

```json
{
  "panels": [
    {
      "title": "SIEM Events per Minute",
      "query": "rate(siem_events_sent_total[1m])"
    },
    {
      "title": "SIEM Queue Size",
      "query": "siem_buffer_queue_size"
    },
    {
      "title": "SIEM Failures",
      "query": "rate(siem_events_failed_total[5m])"
    }
  ]
}
```

### Prometheus Alerts

```yaml
groups:
  - name: siem
    rules:
      - alert: SIEMQueueBacklog
        expr: siem_buffer_queue_size > 5000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "SIEM queue backlog detected"

      - alert: SIEMConnectionFailed
        expr: rate(siem_events_failed_total[5m]) > 10
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "SIEM connection failures detected"
```

---

## Troubleshooting

### Проверка подключения

```bash
# Тест UDP
echo "<134>1 test message" | nc -u siem.company.com 514

# Тест TCP
echo "<134>1 test message" | nc siem.company.com 514

# Тест TLS
openssl s_client -connect siem.company.com:6514
```

### Диагностика

```python
# Проверка статуса диспетчера
from src.security.siem.dispatcher import get_siem_dispatcher

dispatcher = get_siem_dispatcher()
if dispatcher:
    print(f"Enabled: {dispatcher.is_enabled}")
    print(f"Handlers: {dispatcher.handler_count}")
    print(f"Stats: {dispatcher.stats}")
else:
    print("SIEM dispatcher not initialized")
```

### Логирование

```yaml
# logging.yaml
loggers:
  src.security.siem:
    level: DEBUG
    handlers: [console, file]
```

---

## Связанные документы

- [Enterprise Security Brief](./SECURITY_BRIEF.md) — Обзор безопасности
- [DLP Security](./DLP_SECURITY.md) — DLP интеграция
- [LLM Security](./LLM_SECURITY.md) — Безопасность LLM

---

*Версия: 1.0 | Декабрь 2025*
