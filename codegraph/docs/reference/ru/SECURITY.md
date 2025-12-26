# Модуль корпоративной безопасности

## Содержание

- [Обзор](#overview)
- [Возможности](#features)
- [1. Логирование запросов/ответов LLM](#1-llm-requestresponse-logging)
- [2. Интеграция с SIEM](#2-siem-integration)
- [3. DLP (предотвращение утечки данных)](#3-dlp-data-loss-prevention)
- [4. Интеграция с HashiCorp Vault](#4-hashicorp-vault-integration)
- [Архитектура](#architecture)
- [Конфигурация](#configuration)
- [Включение модуля безопасности](#enable-security-module)
- [Полная конфигурация (config.yaml)](#full-configuration-configyaml)
- [Переменные окружения](#environment-variables)
- [Примеры использования](#usage-examples)
- [Базовое использование (автоматическое)](#basic-usage-automatic)
- [Ручная обертка безопасности](#manual-security-wrapper)
- [Только сканирование DLP](#dlp-scanning-only)
- [Отправка событий в SIEM](#siem-event-dispatch)
- [Шаблоны DLP](#dlp-patterns)
- [Встроенные шаблоны](#built-in-patterns)
- [Пользовательские шаблоны](#custom-patterns)
- [Таблицы базы данных](#database-tables)
- [llm_audit_log](#llm_audit_log)
- [dlp_events](#dlp_events)
- [Форматы событий SIEM](#siem-event-formats)
- [SysLog (RFC 5424)](#syslog-rfc-5424)
- [CEF](#cef)
- [LEEF](#leef)
- [Интеграция через вебхуки](#webhook-integration)
- [Рекомендации по безопасности](#security-best-practices)
- [Соответствие требованиям](#compliance)
- [Расширенные функции безопасности](#advanced-security-features)
- [5. Сканер безопасности на основе файлов](#5-file-based-security-scanner)
- [6. Сканер с проверкой заражения (taint-verified)](#6-taint-verified-scanner)
- [7. Проверки укрепления безопасности по MITRE D3FEND](#7-mitre-d3fend-hardening-checks)
- [8. Сравнение с SAST](#8-sast-comparison)
- [9. Генератор отчетов по безопасности](#9-security-report-generator)
- [10. Решатель контекста CPG](#10-cpg-context-resolver)
- [Структура модуля безопасности](#security-module-structure)
- [Краткое руководство](#quick-start-guide)
- [1. Включение функций безопасности](#1-enable-security-features)
- [2. Запуск аудита безопасности](#2-run-security-audit)
- [3. Просмотр отчетов](#3-review-reports)
- [4. Интеграция с CI/CD](#4-integrate-with-cicd)
- [См. также](#see-also)

## Обзор {#overview}

CodeGraph включает модуль безопасности корпоративного уровня для защиты конфиденциальных данных при использовании внешних поставщиков LLM (GigaChat, Yandex AI, OpenAI). Этот модуль обеспечивает соответствие требованиям защиты данных и предоставляет расширенные возможности аудита.

## Возможности {#features}

### 1. Журналирование запросов и ответов LLM

- Полная аудиторская запись всех взаимодействий с LLM
- Настройка маскирования промптов перед записью в лог
- Метрики использования токенов и задержки
- Хранение в базе данных с политиками хранения

### 2. Интеграция с SIEM {#2-siem-integration}

Потоковая передача логов в корпоративные системы SIEM в реальном времени:
- **SysLog (RFC 5424)** — Стандартный syslog со структурированными данными
- **CEF (Common Event Format)** — Для интеграции с ArcSight
- **LEEF (Log Event Extended Format)** — Для интеграции с IBM QRadar

### 3. DLP (предотвращение утечки данных) {#3-dlp-data-loss-prevention}

Сканирование по шаблонам для предотвращения утечек данных:
- **Обнаружение учётных данных** — Ключи API, пароли, приватные ключи
- **Обнаружение персональных данных (PII)** — Электронная почта, телефоны, номера кредитных карт, ИНН/СНИЛС
- **Пути к исходному коду** — Внутренние пути, строки подключения
- **Пользовательские ключевые слова** — Чёрные списки, специфичные для организации

Настройка действий для каждой категории:
- `BLOCK` — Полностью отклонить запрос
- `MASK` — Заменить конфиденциальные данные на `[REDACTED]`
- `WARN` — Зарегистрировать предупреждение, но разрешить запрос
- `LOG_ONLY` — Записать в лог только для аудита

### 4. Интеграция с HashiCorp Vault {#4-hashicorp-vault-integration}

Безопасное управление секретами:
- Динамическое получение учётных данных
- Поддержка нескольких методов аутентификации (Token, AppRole, Kubernetes)
- Автоматическая ротация секретов
- Кэширование с ограничением времени жизни (TTL)

## Архитектура {#architecture}

```
┌─────────────────────────────────────────────────────────────────┐
│                        Пользовательский запрос                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SecureLLMProvider                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Сканер DLP  │  │ Фильтр      │  │  Журнал запросов к   │  │
│  │  (до/после)  │  │ контента     │  │  LLM (БД + SIEM)     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐
│  Действия DLP│     │ BaseLLMProv. │     │   Отправка в SIEM    │
│  BLOCK/MASK  │     │ (GigaChat)   │     │  ┌────┐┌────┐┌────┐ │
│  /WARN/LOG   │     │              │     │  │Sys ││CEF ││LEEF│ │
└──────────────┘     └──────────────┘     │  │Log ││    ││    │ │
         │                                 │  └────┘└────┘└────┘ │
         ▼                                 └──────────────────────┘
┌──────────────┐                                    │
│ Вебхук DLP   │                                    ▼
│ (внешний)    │                           ┌──────────────┐
└──────────────┘                           │    SIEM      │
                                           │  (Splunk/    │
┌──────────────┐                           │   QRadar)    │
│ HashiCorp    │◄── Ротация секретов       └──────────────┘
│ Vault        │
└──────────────┘
```

## Конфигурация {#configuration}

### Включение модуля безопасности {#enable-security-module}

Установите переменные окружения или обновите файл `config.yaml`:

```
export SECURITY_ENABLED=true
export SIEM_ENABLED=true
export DLP_ENABLED=true
```

### Полная конфигурация (config.yaml) {#full-configuration-configyaml}

```
security:
  # Главный переключатель
  enabled: true

  # Логирование LLM
  llm_logging:
    enabled: true
    log_prompts: true
    redact_prompts: true
    max_prompt_length: 2000
    log_responses: true
    log_token_usage: true
    log_latency: true
    log_to_database: true

  # SIEM
  siem:
    enabled: true
    syslog:
      enabled: true
      protocol: "tls"  # udp, tcp, tls
      host: "siem.company.com"
      port: 6514
      facility: 16  # local0
      app_name: "codegraph"
    cef:
      enabled: true
      host: "arcsight.company.com"
      port: 514
    leef:
      enabled: false

  # DLP
  dlp:
    enabled: true
    pre_request:
      enabled: true
      default_action: "WARN"
    post_response:
      enabled: true
      default_action: "MASK"
    categories:
      credentials:
        enabled: true
        action: "BLOCK"
        severity: "critical"
      pii:
        enabled: true
        action: "MASK"
        severity: "high"
    webhook:
      enabled: true
      endpoint: "https://dlp.company.com/api/alerts"
      notify_on: ["BLOCK", "WARN"]

  # Vault
  vault:
    enabled: true
    url: "https://vault.company.com:8200"
    auth_method: "approle"
    secrets_mount_point: "secret"
    llm_secrets_path: "codegraph/llm"
```

### Переменные окружения

| Переменная | Описание | По умолчанию |
| --- | --- | --- |
| SECURITY_ENABLED | Включить модуль безопасности | false |
| SIEM_ENABLED | Включить интеграцию с SIEM | false |
| SIEM_SYSLOG_HOST | Хост сервера SysLog | localhost |
| SIEM_SYSLOG_PORT | Порт сервера SysLog | 514 |
| SIEM_CEF_HOST | Хост сервера CEF | localhost |
| SIEM_LEEF_HOST | Хост сервера LEEF | localhost |
| DLP_ENABLED | Включить сканирование DLP | true |
| DLP_WEBHOOK_URL | Конечная точка вебхука DLP | — |
| DLP_WEBHOOK_AUTH | Заголовок авторизации вебхука DLP | — |
| VAULT_ENABLED | Включить интеграцию с Vault | false |
| VAULT_ADDR | URL сервера Vault | http://localhost:8200 |
| VAULT_TOKEN | Токен Vault | — |
| VAULT_ROLE_ID | Идентификатор роли AppRole | — |
| VAULT_SECRET_ID | Секретный идентификатор AppRole | — |

## Примеры использования {#usage-examples}

### Базовое использование (автоматическое) {#basic-usage-automatic}

Безопасность обеспечивается автоматически при включении:

```
from src.llm import create_llm_provider

# Поставщик автоматически оборачивается в защитный слой {#provider-is-automatically-wrapped-with-security-layer}
provider = create_llm_provider()

# Теперь все запросы фильтруются и записываются в лог {#all-requests-are-now-filtered-and-logged}
response = provider.generate(
    system_prompt="Вы — аналитик кода",
    user_prompt="Проанализируйте эту функцию",
)
```

### Ручная обертка безопасности {#manual-security-wrapper}

```
from src.llm import GigaChatProvider
from src.security import get_security_config, SecureLLMProvider

# Создание базового поставщика {#create-base-provider}
base_provider = GigaChatProvider(config)

# Оборачивание в защитный слой {#wrap-with-security}
secure_provider = SecureLLMProvider(
    wrapped_provider=base_provider,
    config=get_security_config()
)

# Использование защищённого поставщика {#use-secure-provider}
response = secure_provider.generate(
    system_prompt="Проанализируй код",
    user_prompt="def process_payment(card_number='4111111111111111')...",
    _user_id="user-123",  # Опционально: контекст пользователя
    _ip_address="192.168.1.100",  # Опционально: IP для аудита
)
```

### Только сканирование DLP {#dlp-scanning-only}

```
from src.security.dlp import ContentScanner
from src.security.config import get_security_config

config = get_security_config()
scanner = ContentScanner(config.dlp)

# Сканирование содержимого {#scan-content}
result = scanner.scan_request("API_KEY=sk-1234567890abcdef")

if result.blocked:
    print(f"Контент заблокирован! Совпадения: {result.matches}")
elif result.has_matches:
    print(f"Обнаружены конфиденциальные данные: {result.matches}")
    # Использовать замаскированный контент
    safe_content = result.modified_content
```

### Отправка событий в SIEM {#siem-event-dispatch}

```
from src.security.siem import (
    SecurityEvent, SecurityEventType,
    init_siem_dispatcher
)
from src.security.config import get_security_config

# Инициализация диспетчера {#initialize-dispatcher}
dispatcher = init_siem_dispatcher(get_security_config().siem)

# Создание и отправка события {#create-and-dispatch-event}
event = SecurityEvent.create(
    event_type=SecurityEventType.DLP_BLOCK,
    message="Учётные данные обнаружены в запросе LLM",
    severity=3,  # Ошибка
    user_id="user-123",
    request_id="req-456",
    details={"pattern": "aws_key", "category": "credentials"}
)

dispatcher.dispatch(event)
```

## Шаблоны DLP {#dlp-patterns}

### Встроенные шаблоны {#built-in-patterns}

#### Учётные данные

- `api_key` - Общие ключи API
- `aws_key` - Идентификаторы ключей доступа AWS (AKIA…)
- `aws_secret` - Секретные ключи AWS
- `private_key` - Закрытые ключи в формате PEM
- `password` - Шаблоны паролей
- `jwt_token` - JSON Web Token (JWT)
- `bearer_token` - Токены аутентификации Bearer
- `basic_auth` - Base64 строки аутентификации Basic

#### Персональные данные (русская локаль)

- `email` - Адреса электронной почты
- `phone_ru` - Российские номера телефонов
- `credit_card` - Номера кредитных карт
- `inn` - Российский ИНН
- `snils` - Российский СНИЛС
- `passport_ru` - Номера российских паспортов

#### Исходный код

- `connection_string` - Строки подключения к базам данных
- `internal_path` - Внутренние пути к файлам
- `ip_address` - IP-адреса

### Пользовательские шаблоны {#custom-patterns}

Добавьте пользовательские шаблоны через конфигурацию:

```
dlp:
  categories:
    custom:
      enabled: true
      action: "WARN"
      severity: "medium"
      patterns:
        - name: "project_code"
          regex: "PROJECT-[A-Z]{2,4}-\d{4,6}"
          mask_with: "[PROJECT-ID]"
```

## Таблицы базы данных {#database-tables}

### llm_audit_log

Содержит все взаимодействия с LLM:

| Столбец | Тип | Описание |
| --- | --- | --- |
| request_id | UUID | Уникальный идентификатор запроса |
| user_id | UUID | Пользователь, отправивший запрос |
| provider | VARCHAR | Название провайдера LLM |
| model | VARCHAR | Название модели |
| system_prompt_hash | VARCHAR | SHA256 системного промпта |
| user_prompt_preview | TEXT | Предварительный просмотр промпта (с отредактированными данными) |
| response_preview | TEXT | Предварительный просмотр ответа |
| prompt_tokens | INT | Количество токенов в промпте |
| completion_tokens | INT | Количество токенов в ответе |
| latency_ms | FLOAT | Задержка запроса (в миллисекундах) |
| dlp_action | VARCHAR | Применённое действие DLP |
| dlp_categories | ARRAY | Категории DLP, совпавшие с запросом |
| timestamp | TIMESTAMP | Время запроса |

### dlp_events

Детальные события срабатывания DLP:

| Столбец | Тип | Описание |
| --- | --- | --- |
| request_id | UUID | Идентификатор запроса |
| action | VARCHAR | Принятое действие |
| category | VARCHAR | Категория DLP |
| pattern_name | VARCHAR | Имя совпавшего шаблона |
| severity | VARCHAR | Уровень серьёзности совпадения |
| timestamp | TIMESTAMP | Время события |

## Форматы событий SIEM {#siem-event-formats}

### SysLog (RFC 5424) {#syslog-rfc-5424}

```
<134>1 2024-12-09T10:30:00.000Z codegraph.company.com codegraph - llm.dlp.block [llm@12345 requestId="req-123" userId="user-456" provider="GigaChat" action="BLOCK" category="credentials"] DLP BLOCK: 2 patterns in request
```

### CEF {#cef}

```
CEF:0|CodeGraph|CodeAnalysis|1.0|llm.dlp.block|DLP Block|7|rt=Dec 09 2024 10:30:00 src=192.168.1.100 suser=user-456 cs1=req-123 cs1Label=RequestID cs2=GigaChat cs2Label=Provider act=BLOCK cat=credentials
```

### LEEF {#leef}

```
LEEF:2.0|CodeGraph|CodeAnalysis|1.0|llm.dlp.block|  devTime=Dec 09 2024 10:30:00    src=192.168.1.100   usrName=user-456    requestId=req-123   provider=GigaChat   action=BLOCK    category=credentials
```

## Интеграция через вебхук {#webhook-integration}

Формат полезной нагрузки вебхука DLP:

```
{
  "alert_id": "a1b2c3d4e5f6",
  "timestamp": "2024-12-09T10:30:00.000Z",
  "action": "BLOCK",
  "match_count": 2,
  "categories": ["credentials"],
  "patterns": ["api_key", "aws_key"],
  "request_id": "req-123",
  "user_id": "user-456",
  "ip_address": "192.168.1.100",
  "severity": "critical",
  "context": {}
}
```

## Рекомендации по обеспечению безопасности {#security-best-practices}

1. **Включите TLS** для подключений SIEM в рабочей среде
2. **Используйте AppRole** или аутентификацию через Kubernetes для Vault (а не простые токены)
3. **Настройте соответствующие действия DLP** — БЛОКИРОВКА для учетных данных, МАСКИРОВАНИЕ для персональных данных
4. **Настройте хранение логов** в вашей системе SIEM для соответствия требованиям
5. **Мониторьте события DLP_BLOCK** на предмет попыток несанкционированного копирования данных
6. **Регулярно обновляйте шаблоны** для обнаружения новых форматов учетных данных
7. **Тестируйте шаблоны DLP** перед развертыванием в рабочей среде

## Соответствие требованиям {#compliance}

Модуль безопасности помогает выполнить требования следующих нормативных актов:
- **GDPR** — обнаружение и маскировка персональных данных (PII)
- **PCI DSS** — обнаружение номеров кредитных карт
- **SOX** — полный аудит всех действий
- **HIPAA** — защита медицинской информации (PHI) (с использованием пользовательских шаблонов)
- **152-ФЗ** — российский закон о персональных данных (шаблоны PII)

---

## Расширенные функции безопасности {#advanced-security-features}

### 5. Сканер безопасности на основе файлов {#5-file-based-security-scanner}

Быстрое сканирование на уровне файлов для оперативной оценки безопасности без построения CPG.

#### Использование

```
from src.security.file_scanner import FileSecurityScanner

scanner = FileSecurityScanner()
result = scanner.scan("/путь/к/проекту")

print(f"Критические: {result.critical_count}")
print(f"Высокий уровень: {result.high_count}")

for finding in result.findings:
    print(f"{finding.severity}: {finding.description}")
    print(f"  Файл: {finding.file_path}:{finding.line_number}")
```

#### Использование через CLI

```
# Быстрое сканирование {#quick-scan}
python -m src.cli.security_audit quick --path ./myproject

# Полное сканирование с отчётом {#full-scan-with-report}
python -m src.cli.security_audit full --path ./myproject --format all
```

### 6. Сканер с проверкой заражения данных (Taint-Verified Scanner)

Снижает количество ложных срабатываний за счёт анализа потока данных от источников к уязвимым местам с использованием CPG.

#### Концепция

Традиционное сопоставление шаблонов приводит к большому количеству ложных срабатываний. Сканер с проверкой заражения данных:
1. Выявляет потенциальные уязвимости с помощью шаблонов
2. Отслеживает путь данных от источников заражения (ввод пользователя) к уязвимым функциям (sink)
3. Сообщает только о проблемах, для которых подтверждён путь заражения

#### Источники заражения данных (Python/Django)

```
# Данные запроса Django {#django-request-data}
request.GET, request.POST, request.data
request.body, request.FILES, request.META

# Данные запроса Flask {#flask-request-data}
request.args, request.form, request.json

# Обычный ввод {#generic-input}
input(), raw_input(), sys.stdin, os.getenv()

# Ввод из файлов или сети {#filenetwork-input}
open(), read(), recv(), urlopen()
```

#### Опасные уязвимые места (sinks) по категориям

| Категория | Уязвимые места |
| --- | --- |
| SQL-инъекция | execute,raw,cursor.execute,RawSQL |
| Инъекция команд | os.system,subprocess.run,eval,exec |
| Обход пути (Path Traversal) | open,os.path.join,send_file |
| XSS | mark_safe,HttpResponse |
| Десериализация | pickle.loads,yaml.load,marshal.loads |

#### Использование

```
from src.security.taint_verified_scanner import TaintVerifiedScanner

scanner = TaintVerifiedScanner(duckdb_path="cpg.duckdb")

# Проверка результатов, связанных с SQL-инъекцией {#verify-sql-injection-findings}
verified = scanner.verify_sql_injection_findings(raw_findings)

for finding in verified:
    print(f"Подтверждено: {finding['description']}")
    print(f"Путь заражения: {finding['taint_path']}")
```

### 7. Проверки усиления безопасности по MITRE D3FEND {#7-mitre-d3fend-hardening-checks}

Реализует все методы усиления безопасности исходного кода из MITRE D3FEND.

#### Поддерживаемые проверки

| D3FEND ID | Название | Описание |
| --- | --- | --- |
| D3-VI | Инициализация переменных | Обнаружение неинициализированных переменных |
| D3-CS | Очистка учётных данных | Гарантия удаления учётных данных из памяти |
| D3-IRV | Проверка диапазона целых чисел | Проверка рисков переполнения целых чисел |
| D3-RN | Обнуление ссылок | Проверка очистки указателей после освобождения памяти |
| D3-TL | Проверка доверенных библиотек | Проверка использования безопасных функций библиотек |
| D3-VTV | Проверка типов переменных | Проверка безопасности типов |
| D3-MBSV | Проверка начала блока памяти | Проверка границ блоков памяти |
| D3-NPC | Проверка на null-указатели | Обнаружение отсутствующих проверок на null |
| D3-DLV | Проверка бизнес-логики | Проверка валидации бизнес-логики |
| D3-OLV | Проверка операционной логики | Проверка операционных ограничений |

#### Использование

```
from src.security.hardening import HardeningScanner

scanner = HardeningScanner(duckdb_path="cpg.duckdb")
results = scanner.run_all_checks()

for result in results:
    print(f"[{result.check.d3fend_id}] {result.check.d3fend_name}")
    print(f"  Нарушения: {len(result.violations)}")
    print(f"  Рекомендации: {result.check.remediation}")
```

#### Конфигурация

```
security:
  hardening:
    enabled: true
    checks:
      D3-VI: true    # Инициализация переменных
      D3-CS: true    # Очистка учётных данных
      D3-NPC: true   # Проверка на null-указатели
    severity_threshold: "medium"  # Пропускать низкий уровень угроз
```

### 8. Сравнение с SAST-инструментами {#8-sast-comparison}

Сравнение результатов CodeGraph с внешними SAST-инструментами для проверки точности.

#### Поддерживаемые инструменты

- **Bandit** — анализатор безопасности для Python
- **Semgrep** — статический анализатор для нескольких языков

#### Использование

```
from src.security.sast_comparison import SASTComparison

comparison = SASTComparison(project_path="./myproject")

# Сравнение с Bandit {#compare-with-bandit}
result = comparison.compare_with_bandit(our_findings)

print(f"Точность: {result.precision:.2%}")
print(f"Полнота: {result.recall:.2%}")
print(f"F1-мера: {result.f1_score:.2%}")
print(f"Уникальные для нас: {len(result.only_ours)}")
print(f"Пропущенные нами: {len(result.only_theirs)}")
```

#### Использование через CLI

```
# Сравнение с Bandit {#compare-with-bandit}
python -m src.cli.security_audit full --path ./myproject --compare bandit

# Сравнение с Semgrep {#compare-with-semgrep}
python -m src.cli.security_audit full --path ./myproject --compare semgrep
```

### 9. Генератор отчётов по безопасности

Генерация комплексных отчётов по безопасности в различных форматах.

#### Поддерживаемые форматы

| Формат | Назначение |
| --- | --- |
| JSON | Интеграция в CI/CD, программный доступ |
| Markdown | Документация, ручной анализ |
| SARIF | Оповещения безопасности GitHub, интеграция в IDE |

#### Языки

Поддержка локализации отчётов:
- Английский (`en`)
- Русский (`ru`)

#### Использование

```
from src.security.report_generator import SecurityReportGenerator

generator = SecurityReportGenerator(language="en")

# Генерация отчёта на основе результатов сканирования {#generate-report-from-scan-results}
report = generator.generate(
    project_name="MyProject",
    project_path="./myproject",
    file_findings=file_scan.findings,
    cpg_findings=cpg_scan.findings,
    hardening_findings=hardening_results,
)

# Экспорт в разные форматы {#export-to-different-formats}
generator.export_json(report, "report.json")
generator.export_markdown(report, "report.md")
generator.export_sarif(report, "report.sarif")
```

#### Разделы отчёта

1. **Резюме** — общее количество выявленных проблем
2. **Критические уязвимости** — требуют немедленного устранения
3. **Высокий уровень угроз** — необходимо устранить до развёртывания
4. **Соответствие D3FEND** — результаты проверок усиления безопасности
5. **Подробные уязвимости** — полный список с рекомендациями по устранению
6. **Метрики** — покрытие, точность, полнота

### 10. Резолвер контекста CPG {#10-cpg-context-resolver}

Обогащает результаты анализа безопасности контекстом CPG для лучшего понимания.

#### Возможности

- Контекст вызовов (вызывающие/вызываемые функции)
- Пути потока данных
- Анализ потока управления
- Границы модулей

#### Использование

```
from src.security.cpg_context_resolver import CPGContextResolver

resolver = CPGContextResolver(duckdb_path="cpg.duckdb")

# Обогащение результата контекстом {#enrich-finding-with-context}
enriched = resolver.enrich_finding(finding)

print(f"Вызывающие: {enriched['callers']}")
print(f"Поток данных: {enriched['data_flow_path']}")
print(f"Модуль: {enriched['module']}")
```

---

## Структура модуля безопасности {#security-module-structure}

```
src/security/
├── __init__.py          # Экспорты модуля
├── _base.py             # Базовые классы (Severity, Category)
├── config.py            # Конфигурация безопасности
│
├── dlp/                 # Предотвращение утечки данных (DLP)
│   ├── patterns.py      # Шаблоны DLP (учетные данные, персональные данные)
│   ├── scanner.py       # Сканер содержимого
│   ├── actions.py       # Действия DLP (BLOCK, MASK, WARN)
│   └── webhook.py       # Вебхуки оповещений
│
├── siem/                # Интеграция с SIEM
│   ├── base_handler.py  # Базовый класс обработчика
│   ├── syslog_handler.py
│   ├── cef_handler.py
│   ├── leef_handler.py
│   ├── buffer.py        # Буферизация событий
│   └── dispatcher.py    # Диспетчеризация между несколькими обработчиками
│
├── vault/               # HashiCorp Vault
│   ├── client.py        # Клиент API Vault
│   └── secret_manager.py
│
├── llm/                 # Безопасность LLM
│   ├── secure_provider.py  # Обёртка SecureLLMProvider
│   └── request_logger.py   # Аудит и логирование запросов
│
├── hardening/           # Усиление безопасности (D3FEND)
│   ├── base.py          # Определения проверок
│   ├── d3fend_checks.py # Все проверки D3FEND
│   └── hardening_scanner.py
│
├── patterns/            # Шаблоны уязвимостей
│   ├── injection.py     # Инъекции SQL/команд
│   ├── memory.py        # Безопасность работы с памятью
│   ├── crypto.py        # Криптографические проблемы
│   ├── auth.py          # Ошибки аутентификации
│   ├── concurrency.py   # Гонки данных (race conditions)
│   └── python_django.py # Специфичные для Python/Django
│
├── file_scanner.py      # Сканирование на основе файлов
├── taint_verified_scanner.py  # Анализ загрязнения (taint analysis)
├── cpg_context_resolver.py    # Обогащение CPG
├── sast_comparison.py   # Сравнение инструментов SAST
├── report_generator.py  # Генерация отчётов
└── report_localizer.py  # Поддержка интернационализации (i18n)
```

## Краткое руководство по началу работы {#quick-start-guide}

### 1. Включение функций безопасности {#1-enable-security-features}

```
# Переменные окружения {#environment-variables}
export SECURITY_ENABLED=true
export DLP_ENABLED=true
export SIEM_ENABLED=true
```

### 2. Запуск аудита безопасности {#2-run-security-audit}

```
# Полный аудит со всеми проверками {#full-audit-with-all-checks}
python -m src.cli.security_audit full \
    --path ./myproject \
    --format all \
    --verbose
```

### 3. Просмотр отчётов

```
# Отчёты сохраняются в ./security_reports/ {#reports-are-saved-to-security-reports}
ls security_reports/
# security_audit_20241209_103000.json {#security-audit-20241209-103000json}
# security_audit_20241209_103000.md {#security-audit-20241209-103000md}
# security_audit_20241209_103000.sarif {#security-audit-20241209-103000sarif}
```

### 4. Интеграция с CI/CD {#4-integrate-with-cicd}

```
# .github/workflows/security.yml {#githubworkflowssecurityyml}
- name: Security Audit
  run: |
    python -m src.cli.security_audit full \
      --path . \
      --format sarif \
      --output security.sarif

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: security.sarif
```

## Смотрите также

- [Руководство по CLI](../guides/CLI_GUIDE.md) — использование CLI для аудита безопасности
- [Руководство пользователя TUI](../guides/TUI_USER_GUIDE.md) — интерактивный сценарий безопасности
- [Документация по API](../api/REST_API.md) — конечные точки безопасности
