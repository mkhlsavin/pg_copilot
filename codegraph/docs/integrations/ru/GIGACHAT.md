# Руководство по интеграции GigaChat

Руководство по интеграции API GigaChat (российская языковая модель от Сбера) с CodeGraph.

## Содержание

- [Обзор](#overview)
- [Быстрая настройка (3 шага)](#quick-setup-3-steps)
- [Шаг 1: Установка ключа авторизации](#step-1-set-authorization-key)
- [Шаг 2: Настройка config.yaml](#step-2-configure-configyaml)
- [Шаг 3: Проверка](#step-3-verify)
- [Предустановленные параметры](#pre-configured-parameters)
- [Доступные модели](#available-models)
- [Автоматическая настройка](#automated-setup)
- [Скрипт PowerShell](#powershell-script)
- [Использование шаблона](#using-template)
- [Использование в коде](#usage-in-code)
- [Базовое использование](#basic-usage)
- [С CodeGraph](#with-codegraph)
- [Справочник по конфигурации](#configuration-reference)
- [Пример полного config.yaml](#full-configyaml-example)
- [Переменные окружения](#environment-variables)
- [Устранение неполадок](#troubleshooting)
- [Ошибка аутентификации (401)](#authentication-failed-401)
- [Таймаут соединения](#connection-timeout)
- [Ошибка SSL-сертификата](#ssl-certificate-error)
- [Ограничение частоты запросов](#rate-limiting)
- [Рекомендации](#best-practices)
- [Вопросы безопасности](#security-considerations)
- [Ресурсы](#resources)
- [Следующие шаги](#next-steps)

## Обзор {#overview}

GigaChat — российский провайдер языковых моделей от Сбербанка. CodeGraph поддерживает GigaChat как альтернативу OpenAI, Yandex AI Studio или локальным моделям.

> **Совет:** Для большего контекстного окна (до 262K токенов) рассмотрите использование [Yandex AI Studio](./YANDEX_AI_STUDIO.md) с моделями Qwen3-235B и другими.

## Быстрая настройка (3 шага) {#quick-setup-3-steps}

### Шаг 1: Установка ключа авторизации {#step-1-set-authorization-key}

```
# Windows PowerShell {#windows-powershell}
$env:GIGACHAT_AUTH_KEY = "ваш_ключ_авторизации"

# Постоянная установка (сохраняется после перезагрузки) {#permanent-survives-restart}
[System.Environment]::SetEnvironmentVariable('GIGACHAT_AUTH_KEY', 'ваш_ключ', 'User')
```

```
# Linux/Mac {#linuxmac}
export GIGACHAT_AUTH_KEY="ваш_ключ_авторизации"

# Добавьте в ~/.bashrc для постоянного действия {#add-to-bashrc-for-permanent}
echo 'export GIGACHAT_AUTH_KEY="ваш_ключ"' >> ~/.bashrc
```

### Шаг 2: Настройка config.yaml {#step-2-configure-configyaml}

```
llm:
  provider: gigachat

  gigachat:
    client_id: "019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6"
    scope: "GIGACHAT_API_PERS"
    model: "GigaChat-2-Pro"
    temperature: 0.7
    max_tokens: 2000
    timeout: 60
```

### Шаг 3: Проверка {#step-3-verify}

```
python test_gigachat.py
```

Ожидаемый вывод:

```
Подключение к GigaChat успешно установлено
Модель: GigaChat-2-Pro
Статус: Готов
```

## Предустановленные параметры {#pre-configured-parameters}

| Параметр | Значение |
| --- | --- |
| Client ID | 019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6 |
| Область (Scope) | GIGACHAT_API_PERS |
| Модель | GigaChat-2-Pro |
| Ключ авторизации | Устанавливается через переменную окружения |

## Доступные модели {#available-models}

| Модель | Описание | Рекомендуется для |
| --- | --- | --- |
| GigaChat-2-Pro | Наиболее мощная | Сложный анализ |
| GigaChat-2 | Стандартная | Общее использование |
| GigaChat-Lite | Самая быстрая | Простые запросы |

## Автоматическая настройка {#automated-setup}

### Скрипт PowerShell {#powershell-script}

```
# Запуск автоматической настройки {#run-automated-setup}
.\setup_gigachat.ps1
```

Скрипт выполнит:
1. Запросит ключ авторизации
2. Создаст config.yaml из шаблона
3. Установит SDK GigaChat
4. Проверит конфигурацию

### Использование шаблона {#using-template}

```
# Копирование шаблона {#copy-template}
cp config.gigachat.yaml.example config.yaml

# Редактирование с вашими настройками {#edit-with-your-settings}
notepad config.yaml
```

## Использование в коде {#usage-in-code}

### Базовое использование {#basic-usage}

```
import os
from langchain_gigachat import GigaChat

# Получение ключа авторизации из окружения {#get-auth-key-from-environment}
auth_key = os.getenv("GIGACHAT_AUTH_KEY")

# Инициализация клиента {#initialize-client}
llm = GigaChat(
    credentials=auth_key,
    scope="GIGACHAT_API_PERS",
    model="GigaChat-2-Pro",
    verify_ssl_certs=False
)

# Отправка запроса {#make-request}
response = llm.invoke("Что такое PostgreSQL?")
print(response.content)
```

### С CodeGraph {#with-codegraph}

```
from src.llm.gigachat_provider import GigaChatProvider

# Инициализация провайдера {#initialize-provider}
provider = GigaChatProvider()

# Использование в рабочем процессе {#use-with-workflow}
from src.workflow.langgraph_workflow_simple import run_workflow

result = run_workflow("Найти методы обработки транзакций")
print(result['answer'])
```

## Справочник по конфигурации {#configuration-reference}

### Пример полного config.yaml {#full-configyaml-example}

```
llm:
  provider: gigachat

  gigachat:
    # Обязательные
    client_id: "019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6"
    scope: "GIGACHAT_API_PERS"
    model: "GigaChat-2-Pro"

    # Опциональные
    temperature: 0.7          # Креативность (0.0–1.0)
    max_tokens: 2000          # Максимальная длина ответа
    timeout: 60               # Таймаут запроса (секунды)
    verify_ssl_certs: false   # Проверка SSL
    profanity_check: false    # Фильтр нежелательного контента

    # Ограничение частоты
    max_retries: 3
    retry_delay: 1.0
```

### Переменные окружения {#environment-variables}

```
# Обязательные {#required}
GIGACHAT_AUTH_KEY=ваш_ключ_авторизации

# Опциональные {#optional}
GIGACHAT_CLIENT_ID=019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6
GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_MODEL=GigaChat-2-Pro
```

## Устранение неполадок {#troubleshooting}

### Ошибка аутентификации (401) {#authentication-failed-401}

```
Ошибка: 401 Unauthorized
```

**Решение:**

```
# Проверка установки ключа {#check-if-key-is-set}
echo $GIGACHAT_AUTH_KEY

# Проверка формата ключа (должен быть в base64) {#verify-key-format-should-be-base64}
python -c "import base64; base64.b64decode('$GIGACHAT_AUTH_KEY')"
```

### Таймаут соединения {#connection-timeout}

```
Ошибка: Превышено время ожидания соединения
```

**Решение:**

```
# Увеличение таймаута в config.yaml {#increase-timeout-in-configyaml}
gigachat:
  timeout: 120  # секунд
```

### Ошибка SSL-сертификата {#ssl-certificate-error}

```
Ошибка: SSL: CERTIFICATE_VERIFY_FAILED
```

**Решение:**

```
# Отключение проверки SSL (не рекомендуется для продакшена) {#disable-ssl-verification-not-recommended-for-production}
gigachat:
  verify_ssl_certs: false
```

### Ограничение частоты запросов {#rate-limiting}

```
Ошибка: 429 Too Many Requests
```

**Решение:**

```
gigachat:
  max_retries: 5
  retry_delay: 2.0  # секунд
```

## Рекомендации {#best-practices}

1. **Никогда не сохраняйте ключи авторизации в репозитории** — используйте переменные окружения
2. **Используйте GigaChat-2-Pro** — наилучшее качество для анализа кода
3. **Установите подходящий таймаут** — 60 с для обычных задач, 120 с для сложных
4. **Включите повторные попытки** — для обработки временных сбоев

## Вопросы безопасности {#security-considerations}

- Храните ключи авторизации в переменных окружения
- Добавьте `.env` в `.gitignore`
- Используйте защищённое соединение (HTTPS)
- Рассмотрите возможность проверки SSL в продакшене

## Ресурсы {#resources}

- [Документация API GigaChat](https://developers.sber.ru/docs/ru/gigachat)
- [LangChain GigaChat](https://python.langchain.com/docs/integrations/chat/gigachat)

## Следующие шаги {#next-steps}

- [Установка](../getting-started/INSTALLATION.md) — Полная настройка
- [Конфигурация](../getting-started/CONFIGURATION.md) — Все параметры
- [Руководство пользователя TUI](../guides/TUI_USER_GUIDE.md) — Использование системы
- [Интеграция с Yandex AI Studio](./YANDEX_AI_STUDIO.md) — Альтернативный LLM-провайдер (больший контекст)
