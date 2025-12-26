# Руководство по интеграции Yandex AI Studio

Руководство по интеграции Yandex Cloud AI Studio с CodeGraph с использованием API, совместимого с OpenAI.

## Содержание

- [Обзор](#overview)
- [Быстрое начало (3 шага)](#quick-setup-3-steps)
- [Шаг 1: Создание API-ключа](#step-1-create-api-key)
- [Шаг 2: Настройка переменных окружения](#step-2-set-environment-variables)
- [Шаг 3: Настройка config.yaml](#step-3-configure-configyaml)
- [Доступные модели](#available-models)
- [Модели генерации текста](#text-generation-models)
- [Модели эмбеддингов](#embedding-models)
- [Формат URI модели](#model-uri-format)
- [Использование в коде](#usage-in-code)
- [Базовое использование](#basic-usage)
- [Потоковая передача (Streaming)](#streaming)
- [Эмбеддинги](#embeddings)
- [Совместно с CodeGraph Workflow](#with-codegraph-workflow)
- [Справочник по настройке](#configuration-reference)
- [Пример полного config.yaml](#full-configyaml-example)
- [Переменные окружения](#environment-variables)
- [Параметры провайдера](#provider-parameters)
- [Конфиденциальность и соответствие требованиям](#privacy-and-compliance)
- [Обработка ошибок](#error-handling)
- [Ошибка аутентификации (401)](#authentication-error-401)
- [Превышение лимита запросов (429)](#rate-limit-exceeded-429)
- [Таймаут соединения](#connection-timeout)
- [Ошибка идентификатора папки](#folder-id-error)
- [Логика повторных попыток](#retry-logic)
- [Рекомендации](#best-practices)
- [Сравнение с другими провайдерами](#comparison-with-other-providers)
- [Ресурсы](#resources)
- [Дальнейшие шаги](#next-steps)

## Обзор {#overview}

Yandex Cloud AI Studio — это комплексная платформа ИИ, предоставляющая доступ к:
- Моделям семейства **YandexGPT** (YandexGPT, YandexGPT-Lite, YandexGPT-32k)
- **Открытым моделям** (Qwen3, DeepSeek, OpenAI OSS)
- **Моделям эмбеддингов** для семантического поиска

CodeGraph интегрируется с Yandex AI Studio через API, совместимый с OpenAI, что позволяет использовать стандартную библиотеку `openai` на Python.

**Основные возможности:**
- Совместимость с API OpenAI (используйте привычную библиотеку `openai`)
- Фокус на конфиденциальности: логирование отключено по умолчанию через заголовок `x-data-logging-enabled: false`
- Разнообразие моделей с параметрами от 20 млрд до 235 млрд
- Встроенная повторная отправка запросов с экспоненциальной задержкой

## Быстрая настройка (3 шага)

### Шаг 1: Создание API-ключа {#step-1-create-api-key}

1. Перейдите в [консоль Yandex Cloud](https://console.yandex.cloud/)
2. В левом меню выберите **AI Studio**
3. Нажмите **Создать новый ключ** в верхней панели
4. Выберите **Создать API-ключ**
5. В поле **Область доступа (Scope)** выберите `yc.ai.languageModels.execute`
6. Нажмите **Создать** и сохраните идентификатор (ID) и секретный ключ
7. Запишите ваш **ID папки**, который можно найти в селекторе папок в верхней панели

### Шаг 2: Установка переменных окружения {#step-2-set-environment-variables}

```
# Windows PowerShell {#windows-powershell}
$env:YANDEX_API_KEY = "AQVNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
$env:YANDEX_FOLDER_ID = "b1gxxxxxxxxxxxxxxxxx"

# Постоянная настройка (сохраняется после перезагрузки) {#permanent-survives-restart}
[System.Environment]::SetEnvironmentVariable('YANDEX_API_KEY', 'AQVNxxx...', 'User')
[System.Environment]::SetEnvironmentVariable('YANDEX_FOLDER_ID', 'b1gxxx...', 'User')
```

```
# Linux/Mac {#linuxmac}
export YANDEX_API_KEY="AQVNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export YANDEX_FOLDER_ID="b1gxxxxxxxxxxxxxxxxx"

# Добавьте в ~/.bashrc для постоянного эффекта {#add-to-bashrc-for-permanent}
echo 'export YANDEX_API_KEY="your_key"' >> ~/.bashrc
echo 'export YANDEX_FOLDER_ID="your_folder"' >> ~/.bashrc
```

### Шаг 3: Настройка config.yaml {#step-3-configure-configyaml}

```
llm:
  provider: yandex

  yandex:
    api_key: ${YANDEX_API_KEY}
    folder_id: ${YANDEX_FOLDER_ID}
    model: "qwen3-235b-a22b-fp8/latest"
    temperature: 0.7
    max_tokens: 2000
    timeout: 180
```

Проверка конфигурации:

```
python -c "
from src.llm.yandex_provider import YandexProvider
from src.llm.base_provider import LLMConfig

config = LLMConfig(provider_type='yandex')
provider = YandexProvider(config)
print(f'Поставщик: {provider}')
print('Подключение успешно!')
"
```

## Доступные модели {#available-models}

### Модели генерации текста {#text-generation-models}

| Модель | URI | Контекст | Рекомендуется для |
| --- | --- | --- | --- |
| Qwen3 235B | qwen3-235b-a22b-fp8/latest | 262K | Сложный анализ кода, проверка безопасности (по умолчанию) |
| gpt-oss-120b | gpt-oss-120b/latest | 131K | Модель OpenAI OSS для логических задач, сложные задания |
| gpt-oss-20b | gpt-oss-20b/latest | 131K | Модель OpenAI OSS, сбалансированная производительность |
| Gemma 3 27B | gemma-3-27b-it/latest | 131K | Открытая модель Google, оптимизирована под инструкции |
| YandexGPT Pro 5 | yandexgpt/latest | 32K | Универсальное применение, отличная поддержка русского языка |
| YandexGPT Pro 5.1 | yandexgpt/rc | 32K | Новейшие функции, улучшенные логические способности |
| YandexGPT Lite 5 | yandexgpt-lite | 32K | Быстрые ответы, простые запросы |
| Alice AI LLM | aliceai-llm | 32K | Диалоговые системы, разговорный ИИ |
| Тонко настроенная YandexGPT Lite | yandexgpt-lite/latest@<suffix> | 32K | Пользовательские тонко настроенные модели |

**Рекомендации:**
- **Анализ кода**: Используйте `qwen3-235b-a22b-fp8/latest` (контекст 262K, наилучшее качество)
- **Проверка безопасности**: Используйте `gpt-oss-120b/latest` (возможности логического анализа)
- **Быстрые запросы**: Используйте `yandexgpt-lite` для скорости
- **Русский язык**: Используйте `yandexgpt/latest` для родной поддержки русского
- **Большие файлы**: Используйте модели с контекстом 131K и выше (Qwen3, gpt-oss, Gemma)

### Модели эмбеддингов {#embedding-models}

| Модель | Размерность | Применение |
| --- | --- | --- |
| text-search-doc/latest | 256 | Эмбеддинги документов (по умолчанию) |
| text-search-query/latest | 256 | Эмбеддинги запросов |

## Формат URI модели {#model-uri-format}

Yandex требует использования определённого формата URI модели:

```
gpt://<folder_id>/<model_name>
emb://<folder_id>/<embedding_model>
```

Примеры:

```
gpt://b1g123456789/qwen3-235b-a22b-fp8/latest
gpt://b1g123456789/yandexgpt/latest
emb://b1g123456789/text-search-doc/latest
```

Поставщик CodeGraph автоматически формирует такой URI на основе ваших параметров `folder_id` и `model`.

## Использование в коде {#usage-in-code}

### Базовое использование {#basic-usage}

```
import os
from openai import OpenAI

# Инициализация клиента с использованием эндпоинта Yandex {#initialize-client-with-yandex-endpoint}
client = OpenAI(
    api_key=os.getenv("YANDEX_API_KEY"),
    base_url="https://llm.api.cloud.yandex.net/v1",
    default_headers={
        "x-data-logging-enabled": "false",  # Приватность
        "x-folder-id": os.getenv("YANDEX_FOLDER_ID"),
    },
)

# Формирование URI модели {#construct-model-uri}
folder_id = os.getenv("YANDEX_FOLDER_ID")
model_uri = f"gpt://{folder_id}/qwen3-235b-a22b-fp8/latest"

# Отправка запроса {#make-request}
response = client.chat.completions.create(
    model=model_uri,
    messages=[
        {"role": "system", "content": "Вы — эксперт по анализу кода."},
        {"role": "user", "content": "Объясните, что такое MVCC в PostgreSQL."},
    ],
    temperature=0.7,
    max_tokens=2000,
)

print(response.choices[0].message.content)
```

### Потоковая передача {#streaming}

```
# Потоковая передача ответа {#stream-response}
stream = client.chat.completions.create(
    model=model_uri,
    messages=[
        {"role": "user", "content": "Перечислите рекомендации по обеспечению безопасности в C-коде."},
    ],
    stream=True,
)

for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

### Эмбеддинги {#embeddings}

```
# Получение эмбеддингов {#get-embeddings}
embedding_uri = f"emb://{folder_id}/text-search-doc/latest"

response = client.embeddings.create(
    model=embedding_uri,
    input="Найти уязвимости переполнения буфера",
    encoding_format="float",
)

embedding = response.data[0].embedding
print(f"Размерность эмбеддинга: {len(embedding)}")  # 256
```

### Использование с рабочим процессом CodeGraph

```
from src.llm.yandex_provider import YandexProvider
from src.llm.base_provider import LLMConfig

# Инициализация провайдера (считывает данные из config.yaml) {#initialize-provider-reads-from-configyaml}
config = LLMConfig(
    provider_type='yandex',
    temperature=0.7,
    max_tokens=2000,
    extra_params={
        'api_key': os.getenv('YANDEX_API_KEY'),
        'folder_id': os.getenv('YANDEX_FOLDER_ID'),
        'model': 'qwen3-235b-a22b-fp8/latest',
    }
)
provider = YandexProvider(config)

# Генерация ответа {#generate-response}
response = provider.generate(
    system_prompt="Вы — эксперт по безопасности PostgreSQL.",
    user_prompt="Найдите уязвимости SQL-инъекций в модуле исполнителя."
)

print(response.content)
print(f"Использовано токенов: {response.metadata['tokens_used']}")
print(f"Задержка: {response.metadata['latency_ms']:.0f} мс")
```

Использование в рабочем процессе:

```
from src.workflow.orchestration.copilot import Copilot

# Copilot автоматически использует настроенный провайдер {#copilot-automatically-uses-configured-provider}
copilot = Copilot()
result = copilot.answer("Найдите функции выделения памяти в PostgreSQL")
print(result['answer'])
```

## Справочник по конфигурации

### Пример полного файла config.yaml {#full-configyaml-example}

```
llm:
  # Установить Yandex в качестве активного провайдера
  provider: yandex

  yandex:
    # Обязательно: Аутентификация
    api_key: ${YANDEX_API_KEY}      # API-ключ сервисного аккаунта
    folder_id: ${YANDEX_FOLDER_ID}  # Идентификатор каталога Yandex Cloud

    # Выбор модели
    model: "qwen3-235b-a22b-fp8/latest"  # Лучше всего подходит для анализа кода

    # Конечная точка API (по умолчанию, обычно не меняется)
    base_url: "https://llm.api.cloud.yandex.net/v1"

    # Таймауты
    timeout: 180  # секунд (увеличен для больших запросов)

    # Параметры генерации
    temperature: 0.7       # Уровень креативности (0.0–1.0)
    max_tokens: 2000       # Максимальная длина ответа
    top_p: null            # Использовать значение по умолчанию от Yandex

    # Модель эмбеддингов
    embedding_model: "text-search-doc/latest"
```

### Переменные окружения {#environment-variables}

| Переменная | Обязательно | Описание |
| --- | --- | --- |
| YANDEX_API_KEY | Да | API-ключ из консоли Yandex Cloud |
| YANDEX_FOLDER_ID | Да | Идентификатор каталога, в котором включён AI Studio |

### Параметры провайдера {#provider-parameters}

| Параметр | Тип | По умолчанию | Описание |
| --- | --- | --- | --- |
| api_key | строка | - | API-ключ Yandex Cloud (обязательный) |
| folder_id | строка | - | Идентификатор каталога Yandex Cloud (обязательный) |
| model | строка | qwen3-235b-a22b-fp8/latest | Модель генерации текста |
| base_url | строка | https://llm.api.cloud.yandex.net/v1 | Конечная точка API |
| timeout | целое | 60 | Таймаут запроса в секундах |
| temperature | число с плавающей точкой | 0.7 | Степень случайности ответа (0.0–1.0) |
| max_tokens | целое | 2000 | Максимальное количество токенов в ответе |
| top_p | число с плавающей точкой | null | Параметр выборки ядра (nucleus sampling) |
| embedding_model | строка | text-search-doc/latest | Модель для эмбеддингов |

## Конфиденциальность и соответствие требованиям {#privacy-and-compliance}

CodeGraph автоматически отключает логирование на стороне Яндекса в целях соблюдения требований конфиденциальности и GDPR:

```
default_headers={
    "x-data-logging-enabled": "false",  # Отключает логирование на стороне Яндекса
    "x-folder-id": folder_id,
}
```

Это гарантирует:
- Ваши запросы не сохраняются в логах Яндекса
- Данные ответов не хранятся
- Соответствие требованиям защиты данных

## Обработка ошибок {#error-handling}

### Ошибка аутентификации (401) {#authentication-error-401}

```
Error: 401 Unauthorized
```

**Решения:**

```
# Проверьте, установлены ли переменные {#check-if-variables-are-set}
echo $YANDEX_API_KEY
echo $YANDEX_FOLDER_ID

# Проверьте формат API-ключа (должен начинаться с AQVNw, AQVN_ или аналогичного) {#verify-api-key-format-should-start-with-aqvnw-aqvn-or-similar}
python -c "import os; key = os.getenv('YANDEX_API_KEY', ''); print(f'Префикс ключа: {key[:5]}...' if key else 'НЕ УСТАНОВЛЕН')"

# Убедитесь, что область действия API-ключа включает yc.ai.languageModels.execute {#verify-api-key-scope-includes-ycailanguagemodelsexecute}
```

### Превышено ограничение по частоте запросов (429) {#rate-limit-exceeded-429}

```
Error: 429 Too Many Requests
```

**Решения:**

```
# Встроенная повторная попытка автоматически обрабатывает эту ситуацию {#built-in-retry-handles-this-automatically}
# Но вы можете увеличить таймаут для сложных запросов {#but-you-can-increase-timeout-for-complex-requests}
yandex:
  timeout: 300  # 5 минут
```

Или реализуйте собственную логику повторных попыток:

```
import time

for attempt in range(3):
    try:
        response = provider.generate(system_prompt, user_prompt)
        break
    except YandexRateLimitError:
        time.sleep(2 ** attempt)  # Экспоненциальная задержка
```

### Таймаут соединения {#connection-timeout}

```
Error: Request timeout
```

**Решения:**

```
# Увеличьте таймаут для больших запросов или ответов {#increase-timeout-for-large-promptsresponses}
yandex:
  timeout: 300  # секунд
```

### Ошибка идентификатора каталога

```
Error: Folder not found or access denied
```

**Решения:**
1. Убедитесь, что идентификатор каталога указан верно (выпадающий список в верхней панели консоли Yandex Cloud)
2. Убедитесь, что AI Studio включён в этом каталоге
3. Проверьте, что у API-ключа есть доступ к данному каталогу

## Логика повторных попыток {#retry-logic}

Поставщик Yandex включает встроенную поддержку повторных попыток с экспоненциальной задержкой:

```
# Автоматические повторные попытки для: {#automatic-retry-for}
# - APITimeoutError (истекло время ожидания) {#apitimeouterror-timeout}
# - APIConnectionError (проблемы с подключением) {#apiconnectionerror-connection-issues}

# Параметры повтора: {#retry-parameters}
# - max_retries: 3 {#max-retries-3}
# - initial_delay: 2.0 секунды {#initial-delay-20-seconds}
# - max_delay: 30.0 секунд {#max-delay-300-seconds}
# - backoff_factor: 2.0 {#backoff-factor-20}
```

Пример последовательности повторных попыток:
1. Первая попытка не удалась -> ожидание 2 с
2. Вторая попытка не удалась -> ожидание 4 с
3. Третья попытка не удалась -> возникновение исключения

## Рекомендации {#best-practices}

1. **Используйте Qwen3-235B для анализа кода** — наилучшее качество для сложных запросов
2. **Используйте YandexGPT-Lite для простых запросов** — более быстрый отклик
3. **Устанавливайте подходящий таймаут** — 180 с для анализа безопасности, 60 с для простых запросов
4. **Контролируйте использование токенов** — в служебных данных ответа указано количество токенов
5. **Используйте потоковую передачу для длинных ответов** — улучшенный пользовательский опыт в интерактивных приложениях
6. **Храните учетные данные в переменных окружения** — никогда не сохраняйте ключи API в git

## Сравнение с другими провайдерами {#comparison-with-other-providers}

| Возможность | Yandex AI Studio | GigaChat | OpenAI |
| --- | --- | --- | --- |
| Совместимость с API | Совместимо с OpenAI | Собственный SDK | Родной формат |
| Лучшая модель | Qwen3 235B | GigaChat-2-Pro | GPT-4 |
| Заголовок конфиденциальности | Да (x-data-logging-enabled) | Нет | Нет |
| Поддержка русского языка | Отличная | Отличная | Хорошая |
| Тарифы | Плата за токен | Плата за токен | Плата за токен |
| Макс. контекст | 262K (Qwen3) | 32K | 128K (GPT-4) |
| Открытые модели | Qwen3, Gemma, gpt-oss | Нет | Нет |

## Ресурсы {#resources}

- [Обзор Yandex AI Studio](https://yandex.cloud/ru/services/ai-studio)
- [Документация по совместимости с OpenAI](https://yandex.cloud/ru/docs/ai-studio/concepts/openai-compatibility)
- [Доступные модели](https://yandex.cloud/ru/docs/ai-studio/concepts/generation/)
- [Yandex Cloud ML SDK](https://github.com/yandex-cloud/yandex-cloud-ml-sdk)
- [Руководство по интеграции с VS Code](https://yandex.cloud/ru/docs/ai-studio/tutorials/qwen-vsc-integration)

## Дальнейшие шаги {#next-steps}

- [Установка](../getting-started/INSTALLATION.md) — Полное руководство по настройке
- [Конфигурация](../getting-started/CONFIGURATION.md) — Все параметры
- [Руководство пользователя TUI](../guides/TUI_USER_GUIDE.md) — Работа с системой
- [Интеграция GigaChat](./GIGACHAT.md) — Альтернативный провайдер LLM
