# Руководство по настройке

Настройте CodeGraph для вашей среды.

## Содержание

- [Файлы конфигурации](#fayly-konfiguratsii)
- [Конфигурация сервера API](#konfiguratsiya-servera-api)
- [Настройки сервера](#nastroyki-servera)
- [Конфигурация базы данных](#konfiguratsiya-bazy-dannyh)
- [Конфигурация аутентификации](#konfiguratsiya-autentifikatsii)
- [Конфигурация ограничения частоты запросов](#konfiguratsiya-ogranicheniya-chastoty-zaprosov)
- [Конфигурация CORS](#konfiguratsiya-cors)
- [Конфигурация демо-эндпоинта](#konfiguratsiya-demo-endpointa)
- [Конфигурация поставщика LLM](#konfiguratsiya-postavschika-llm)
- [GigaChat](#gigachat)
- [Локальная LLM (llama-cpp-python)](#lokalnaya-llm-llama-cpp-python)
- [OpenAI](#openai)
- [Yandex Cloud AI Studio (YandexGPT)](#yandex-cloud-ai-studio-yandexgpt)
- [Конфигурация домена](#konfiguratsiya-domena)
- [Конфигурация базы данных CPG](#konfiguratsiya-bazy-dannyh-cpg)
- [Настройки поиска](#nastroyki-poiska)
- [Ограничения запросов](#ogranicheniya-zaprosov)
- [Настройки анализа](#nastroyki-analiza)
- [Справочник переменных окружения](#spravochnik-peremennyh-okruzheniya)
- [Оптимизация производительности](#optimizatsiya-proizvoditelnosti)
- [Для продакшена (несколько воркеров)](#dlya-prodakshena-neskolko-vorkerov)
- [Для разработки (быстрая перезагрузка)](#dlya-razrabotki-bystraya-perezagruzka)
- [Для ограниченных ресурсов](#dlya-ogranichennyh-resursov)
- [Рекомендации по безопасности](#rekomendatsii-po-bezopasnosti)
- [Проверка конфигурации](#proverka-konfiguratsii)
- [Дальнейшие шаги](#dalneyshie-shagi)

## Файлы конфигурации

| Файл | Назначение |
| --- | --- |
| .env | Переменные окружения (ключи API, URL баз данных) |
| config.yaml | Основная конфигурация (LLM, поиск, анализ) |
| src/api/config.py | Конфигурация сервера API |
| config/prompts/*.yaml | Шаблоны промптов |

## Конфигурация сервера API

### Настройки сервера

Настройте хост, порт и количество воркеров через переменные окружения или аргументы командной строки:

**Через переменные окружения:**

```
export API_HOST="0.0.0.0"        # Привязка ко всем интерфейсам
export API_PORT="8000"            # Номер порта
export API_WORKERS="4"            # Количество процессов-воркеров
export API_DEBUG="false"          # Режим отладки (автоперезагрузка)
```

**Через аргументы командной строки:**

```
python -m src.api.cli run --host 0.0.0.0 --port 8000 --workers 4
```

### Конфигурация базы данных

API требует PostgreSQL для управления пользователями, сессиями и журналами аудита.

**Формат строки подключения:**

```
postgresql+asyncpg://имя_пользователя:пароль@хост:порт/база_данных
```

**Конфигурация через переменную окружения:**

```
export DATABASE_URL="postgresql+asyncpg://postgres:your_password@localhost:5432/codegraph"
```

**Настройки пула соединений:**

Измените `src/api/config.py`, чтобы настроить пул соединений:

```
class DatabaseConfig(BaseModel):
    url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/codegraph"
    pool_size: int = 10          # Количество поддерживаемых соединений
    max_overflow: int = 20        # Дополнительные соединения при заполнении пула
    pool_timeout: int = 30        # Время ожидания соединения (в секундах)
    pool_recycle: int = 1800      # Пересоздание соединений после 30 минут
    echo: bool = False            # Логирование всех SQL-запросов (только для отладки)
```

### Конфигурация аутентификации

#### JWT-аутентификация

Настройте параметры JWT-токенов:

```
# Секретный ключ для подписи токенов (ОБЯЗАТЕЛЬНО ИЗМЕНИТЬ В ПРОДАКШЕНЕ!)
export API_JWT_SECRET="ваш-секретный-ключ-минимум-64-символа-рекомендуется"

# Время жизни токена (по умолчанию: 30 минут для доступа, 7 дней для обновления)
export API_JWT_ACCESS_EXPIRE_MINUTES="30"
export API_JWT_REFRESH_EXPIRE_DAYS="7"
```

**В config.py:**

```
class JWTConfig(BaseModel):
    secret_key: str = "замените-в-продакшене-минимум-64-символа"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
```

**Сгенерируйте надёжный секретный ключ:**

```
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

#### API-ключи

Включите аутентификацию по API-ключам для программного доступа:

```
class AuthConfig(BaseModel):
    api_keys_enabled: bool = True  # Включить аутентификацию по API-ключам
```

Создание API-ключей через API:

```
# Требуется JWT-токен
curl -X POST http://localhost:8000/api/v1/auth/api-keys \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Мой API-ключ",
    "expires_days": 365,
    "scopes": ["scenarios:read", "query:execute"]
  }'
```

#### Провайдеры OAuth

Настройте провайдеров OAuth 2.0 (GitHub, Google, GitLab, Keycloak):

```
# OAuth для GitHub
export OAUTH_GITHUB_CLIENT_ID="ваш_client_id_для_github"
export OAUTH_GITHUB_CLIENT_SECRET="ваш_client_secret_для_github"

# OAuth для Google
export OAUTH_GOOGLE_CLIENT_ID="ваш_client_id_для_google"
export OAUTH_GOOGLE_CLIENT_SECRET="ваш_client_secret_для_google"

# Keycloak
export OAUTH_KEYCLOAK_SERVER_URL="https://keycloak.example.com"
export OAUTH_KEYCLOAK_REALM="ваш_realm"
export OAUTH_KEYCLOAK_CLIENT_ID="ваш_client_id"
export OAUTH_KEYCLOAK_CLIENT_SECRET="ваш_client_secret"
```

#### LDAP/Active Directory

Настройте LDAP для корпоративной аутентификации:

```
export LDAP_SERVER="ldap.example.com"
export LDAP_BASE_DN="dc=example,dc=com"
export LDAP_BIND_USER="cn=admin,dc=example,dc=com"
export LDAP_BIND_PASSWORD="admin_password"
export LDAP_USER_SEARCH_BASE="ou=users,dc=example,dc=com"
export LDAP_GROUP_SEARCH_BASE="ou=groups,dc=example,dc=com"
```

### Настройка ограничения частоты запросов (Rate Limiting)

Защитите ваш API с помощью ограничения частоты запросов:

```
class RateLimitConfig(BaseModel):
    enabled: bool = True
    storage: str = "memory"  # "memory" или "redis://localhost:6379"
    default_limits: List[str] = ["100/minute", "1000/hour"]

    endpoint_limits: Dict[str, str] = {
        "/api/v1/review/*": "10/minute",
        "/api/v1/chat": "60/minute",
        "/api/v1/chat/stream": "30/minute",
        "/api/v1/query/execute": "30/minute",
        "/api/v1/demo/chat": "30/minute",
    }
```

**Используйте Redis в продакшене** (для общего доступа между воркерами):

```
export RATE_LIMIT_STORAGE="redis://localhost:6379"
```

### Настройка CORS

Настройте обмен ресурсами между источниками (CORS) для веб-интерфейсов:

```
class CORSConfig(BaseModel):
    allowed_origins: List[str] = [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    allowed_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allowed_headers: List[str] = ["*"]
    allow_credentials: bool = True
    max_age: int = 600  # Время кэширования preflight-запросов (в секундах)
```

### Конфигурация демо-эндпоинта

Настройте публичный демо-эндпоинт:

```
export DEMO_ENABLED="true"
export DEMO_RATE_LIMIT="30/minute"
```

```
class DemoConfig(BaseModel):
    enabled: bool = True
    rate_limit: str = "30/minute"
    allowed_scenarios: List[str] = ["onboarding"]
    max_query_length: int = 500
```

## Настройка провайдера LLM

Настройте провайдера LLM, используемого для анализа кода и генерации запросов.

### GigaChat {#gigachat}

```
export GIGACHAT_AUTH_KEY="ваш_ключ_gigachat"
```

```
# config.yaml
llm:
  provider: gigachat
  model: GigaChat-2-Pro
  temperature: 0.1
  max_tokens: 4096
```

### Локальный LLM (llama-cpp-python)

```
export LLMXCPG_MODEL_PATH="/путь/к/модели/llmxcpg/model.gguf"
```

```
# config.yaml
llm:
  provider: local
  model_path: ${LLMXCPG_MODEL_PATH}
  n_gpu_layers: -1   # Использовать все GPU-слои (-1)
  n_ctx: 8192        # Размер окна контекста
  n_threads: 8       # Количество CPU-потоков для инференса
  temperature: 0.1
  max_tokens: 4096
```

### OpenAI {#openai}

```
export OPENAI_API_KEY="ваш_ключ_openai"
```

```
# config.yaml
llm:
  provider: openai
  model: gpt-4
  temperature: 0.1
  max_tokens: 4096
  api_base: https://api.openai.com/v1
```

### Yandex Cloud AI Studio (YandexGPT) {#yandex-cloud-ai-studio-yandexgpt}

```
export YANDEX_API_KEY="ваш_ключ_api_yandex"
export YANDEX_FOLDER_ID="ваш_id_папки"
```

```
# config.yaml
llm:
  provider: yandex
  yandex:
    api_key: ${YANDEX_API_KEY}
    folder_id: ${YANDEX_FOLDER_ID}
    model: yandexgpt/latest      # или: yandexgpt-lite/latest, yandexgpt/rc
    base_url: https://llm.api.cloud.yandex.net/v1
    temperature: 0.7
    max_tokens: 2000
    timeout: 60
    embedding_model: text-search-doc/latest
```

Доступные модели:
- `yandexgpt/latest` — YandexGPT (основная модель)
- `yandexgpt-lite/latest` — YandexGPT Lite (быстрее, меньше по размеру)
- `yandexgpt/rc` — Кандидат в релиз с возможностью логического вывода
- `yandexgpt-32k/latest` — Расширенный контекст (32K токенов)

## Конфигурация домена

Переключение между различными кодовыми базами для анализа:

```
# config.yaml
domain:
  name: postgresql  # postgresql, linux_kernel, llvm, generic
  auto_activate: true
```

Доступные домены:
- `postgresql` — база данных PostgreSQL 17.6
- `linux_kernel` — ядро Linux 6.x
- `llvm` — инфраструктура компилятора LLVM 18.x
- `generic` — универсальная кодовая база C/C++

## Конфигурация базы данных CPG

Настройка базы данных Code Property Graph (для анализа кода):

```
# config.yaml
cpg:
  type: postgresql  # Тип базы данных для хранения CPG
  db_path: cpg.duckdb  # Устаревшее: путь к DuckDB (если используется DuckDB)
```

## Настройки поиска

Настройка семантического поиска и извлечения:

```
# config.yaml
retrieval:
  embedding_model: all-MiniLM-L6-v2  # Модель sentence transformer
  embedding_dimension: 384            # Размерность вектора
  top_k_qa: 3                         # Количество лучших результатов для поиска по вопросам и ответам
  top_k_graph: 5                      # Количество лучших результатов для поиска по графу (SQL)
  max_results: 50                     # Максимальное количество результатов поиска
  chunk_size: 512                     # Размер фрагмента текста для создания эмбеддингов

  # Гибридный поиск (векторный + графовый)
  hybrid:
    enabled: true
    vector_weight: 0.6      # Вес семантического поиска
    graph_weight: 0.4       # Вес структурного поиска
    rrf_k: 60               # Константа Reciprocal Rank Fusion
```

### Ограничения запросов

```
# config.yaml
query:
  default_limit: 100   # Значение LIMIT по умолчанию для SQL-запросов
  max_limit: 1000      # Максимально допустимое значение LIMIT
```

## Настройки анализа

Настройте пороговые значения анализа:

```
# config.yaml
analysis:
  sanitization_confidence_threshold: 0.7  # Уровень уверенности для обнаружения очистки данных
  similarity_threshold: 0.8                # Порог семантического сходства
  complexity_threshold: 10                 # Порог цикломатической сложности
```

## Справочник переменных окружения

Создайте файл `.env` в корне проекта:

```
# =============================================================================
# Конфигурация API-сервера
# =============================================================================
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_DEBUG=false

# =============================================================================
# Конфигурация базы данных
# =============================================================================
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/codegraph

# =============================================================================
# Аутентификация
# =============================================================================
API_JWT_SECRET=ваш-секретный-ключ-минимум-64-символа-измените-в-продакшене
API_JWT_ALGORITHM=HS256

# Пользователь-администратор (для первоначальной настройки)
API_ADMIN_USERNAME=admin
API_ADMIN_PASSWORD=замените-этот-пароль

# =============================================================================
# Поставщики LLM API
# =============================================================================
GIGACHAT_AUTH_KEY=ваш_ключ_gigachat
OPENAI_API_KEY=ваш_ключ_openai
YANDEX_API_KEY=ваш_ключ_yandex_api
YANDEX_FOLDER_ID=ваш_идентификатор_папки_yandex

# =============================================================================
# Пути к локальным моделям
# =============================================================================
LLMXCPG_MODEL_PATH=/путь/к/llmxcpg/model.gguf
QWEN3_MODEL_PATH=/путь/к/qwen3/model.gguf

# =============================================================================
# Поставщики OAuth (опционально)
# =============================================================================
OAUTH_GITHUB_CLIENT_ID=ваш_id_клиента_github
OAUTH_GITHUB_CLIENT_SECRET=ваш_секрет_клиента_github
OAUTH_GOOGLE_CLIENT_ID=ваш_id_клиента_google
OAUTH_GOOGLE_CLIENT_SECRET=ваш_секрет_клиента_google

# =============================================================================
# Конфигурация LDAP (опционально)
# =============================================================================
LDAP_SERVER=ldap.example.com
LDAP_BASE_DN=dc=example,dc=com
LDAP_BIND_USER=cn=admin,dc=example,dc=com
LDAP_BIND_PASSWORD=admin_password
LDAP_USER_SEARCH_BASE=ou=users,dc=example,dc=com
LDAP_GROUP_SEARCH_BASE=ou=groups,dc=example,dc=com

# =============================================================================
# Ограничение частоты запросов (Rate Limiting)
# =============================================================================
RATE_LIMIT_STORAGE=memory  # или redis://localhost:6379

# =============================================================================
# Демонстрационный эндпоинт
# =============================================================================
DEMO_ENABLED=true
DEMO_RATE_LIMIT=30/minute

# =============================================================================
# Настройки базы данных CPG
# =============================================================================
CPG_DB_PATH=cpg.duckdb
# CPG_TYPE=postgresql  # Тип домена для анализа

# =============================================================================
# Логирование
# =============================================================================
LOG_LEVEL=INFO
LLM_VERBOSE=false

# =============================================================================
# Производительность
# =============================================================================
CUDA_VISIBLE_DEVICES=0
OMP_NUM_THREADS=8
```

## Оптимизация производительности

### Для промышленной эксплуатации (несколько воркеров)

```
# Используйте несколько воркеров для лучшей пропускной способности
python -m src.api.cli run --host 0.0.0.0 --port 8000 --workers 4

# Используйте Redis для ограничения частоты запросов (общий доступ между воркерами)
export RATE_LIMIT_STORAGE="redis://localhost:6379"

# Увеличьте размер пула соединений с базой данных
# Отредактируйте src/api/config.py:
# pool_size: 20
# max_overflow: 40
```

### Для разработки (автоматическая перезагрузка)

```
# Один воркер с автоматической перезагрузкой
python -m src.api.cli run --host 127.0.0.1 --port 8000 --reload --log-level debug

# Включите логирование SQL-запросов
# Отредактируйте src/api/config.py:
# echo: True
```

### При ограниченных ресурсах

```
# config.yaml
retrieval:
  batch_size: 50    # Уменьшено с 100
  top_k_qa: 3       # Уменьшено с 10
  top_k_graph: 3

llm:
  max_tokens: 2048  # Уменьшено с 4096
```

## Рекомендации по обеспечению безопасности

1. **Измените пароли по умолчанию:**
   ```bash
   # Сгенерируйте надежный секретный ключ JWT
   python -c “import secrets; print(secrets.token_urlsafe(64))”

# Установите надежный пароль администратора
   python -m src.api.cli create-admin –username admin –password <надежный_пароль>
   ```

1. **Используйте переменные окружения для хранения секретов:**
   - Никогда не добавляйте файлы `.env` в систему контроля версий
   - Добавьте `.env` в файл `.gitignore`
2. **Включите HTTPS в продакшене:**
   - Используйте обратный прокси (nginx, Caddy, Traefik)
   - Либо настройте uvicorn с SSL-сертификатами
3. **Ограничьте источники CORS:**

```
python
   allowed_origins: List[str] = [
       "https://yourapp.example.com",  # Только фронтенд продакшена
   ]
```
4. **Настройте ограничение частоты запросов (rate limiting):**
   - Используйте Redis для распределенного ограничения частоты запросов
   - Настройте лимиты в соответствии с возможностями вашей системы

## Проверка

Проверьте свою конфигурацию:

```
# Проверка подключения к базе данных
python -c "
from src.api.database.connection import check_db_connection
import asyncio
print('База данных ОК' if asyncio.run(check_db_connection()) else 'Ошибка базы данных')
"

# Проверка работоспособности API
curl http://localhost:8000/api/v1/health
```

## Дальнейшие шаги

- [Руководство по установке](INSTALLATION.md) — Настройка системы
- [Краткое руководство](README.md) — Быстрый старт
- [Руководство пользователя TUI](../guides/TUI_USER_GUIDE.md) — Изучение использования системы
- [Справка по API](../api/REST_API.md) — Обзор конечных точек API
