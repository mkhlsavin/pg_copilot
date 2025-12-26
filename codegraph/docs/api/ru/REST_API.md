# Документация по REST API CodeGraph

Полная документация по серверу REST API CodeGraph.

## Содержание

- [Обзор](#overview)
- [Быстрый старт](#quick-start)
- [1. Установка зависимостей](#1-install-dependencies)
- [2. Настройка окружения](#2-configure-environment)
- [3. Инициализация базы данных](#3-initialize-database)
- [4. Создание администратора](#4-create-admin-user)
- [5. Запуск сервера](#5-start-server)
- [Переменные окружения](#environment-variables)
- [Обязательные](#required)
- [Настройки сервера](#server-settings)
- [Аутентификация](#authentication)
- [Провайдеры OAuth2](#oauth2-providers)
- [LDAP/Active Directory](#ldapactive-directory)
- [Ограничение частоты запросов](#rate-limiting)
- [Демо-эндпоинт](#demo-endpoint)
- [Аутентификация](#authentication)
- [Аутентификация по JWT-токену](#jwt-token-authentication)
- [Аутентификация по API-ключу](#api-key-authentication)
- [Аутентификация через OAuth2](#oauth2-authentication)
- [Аутентификация через LDAP](#ldap-authentication)
- [API-эндпоинты](#api-endpoints)
- [Демо (публичный — без аутентификации)](#demo-public---no-auth-required)
- [Чат](#chat)
- [Сценарии](#scenarios)
- [Доступные сценарии (всего 16)](#available-scenarios-16-total)
- [Рецензирование кода](#code-review)
- [Сессии](#sessions)
- [История](#history)
- [Запрос (SQL)](#query-sql)
- [Импорт проекта](#project-import)
- [WebSocket-эндпоинты](#websocket-endpoints)
- [/ws/chat](#wschat)
- [/ws/jobs/{job_id}](#wsjobsjob_id)
- [/ws/notifications](#wsnotifications)
- [Ограничение частоты запросов](#rate-limiting)
- [Стандартные лимиты](#default-limits)
- [Лимиты для конкретных эндпоинтов](#endpoint-specific-limits)
- [Заголовки ограничения частоты](#rate-limit-headers)
- [Использование Redis для ограничения частоты](#using-redis-for-rate-limiting)
- [Роли RBAC](#rbac-roles)
- [Настройка базы данных](#database-setup)
- [Подключение к PostgreSQL](#postgresql-connection)
- [Миграции Alembic](#alembic-migrations)
- [Схема базы данных](#database-schema)
- [Команды CLI](#cli-commands)
- [Примеры использования (curl)](#example-usage-curl)
- [Демо-эндпоинт (без аутентификации)](#demo-endpoint-no-auth)
- [Вход в систему](#login)
- [Чат с JWT](#chat-with-jwt)
- [Просмотр списка сценариев](#list-scenarios)
- [Создание API-ключа](#create-api-key)
- [Использование API-ключа](#use-api-key)
- [Рецензирование патча](#review-patch)
- [Формат ошибок](#error-responses)
- [Распространённые HTTP-статусы](#common-http-status-codes)
- [Сопутствующая документация](#related-documentation)

## Обзор {#overview}

- **Фреймворк:** FastAPI
- **Базовый URL:** `http://localhost:8000/api/v1`
- **Документация OpenAPI:** `/docs` (Swagger UI), `/redoc` (ReDoc)
- **Аутентификация:** JWT-токены, API-ключи, OAuth2, LDAP

---

## Быстрый старт {#quick-start}

### 1. Установка зависимостей {#1-install-dependencies}

```
pip install -r requirements.txt
```

### 2. Настройка окружения {#2-configure-environment}

Создайте файл `.env` (см. [Переменные окружения](#environment-variables)):

```
cp .env.example .env
# Отредактируйте .env под свои настройки {#edit-env-with-your-settings}
```

### 3. Инициализация базы данных {#3-initialize-database}

```
# Создание таблиц {#create-tables}
python -m src.api.cli init-db

# Выполнение миграций {#run-migrations}
python -m src.api.cli migrate
```

### 4. Создание администратора {#4-create-admin-user}

```
python -m src.api.cli create-admin --username admin --password ваш-надёжный-пароль
```

### 5. Запуск сервера {#5-start-server}

```
python -m src.api.cli run --host 0.0.0.0 --port 8000
```

---

## Переменные окружения {#environment-variables}

### Обязательные {#required}

| Переменная | Описание | По умолчанию |
| --- | --- | --- |
| DATABASE_URL | Строка подключения к PostgreSQL | postgresql+asyncpg://postgres:postgres@localhost:5432/codegraph |
| API_JWT_SECRET | Секрет для подписи JWT (не менее 64 символов) | change-me-in-production... |

### Настройки сервера {#server-settings}

| Переменная | Описание | По умолчанию |
| --- | --- | --- |
| API_HOST | Адрес, на котором запускается сервер | 0.0.0.0 |
| API_PORT | Порт сервера | 8000 |
| API_WORKERS | Количество воркеров | 4 |
| API_DEBUG | Режим отладки | false |

### Аутентификация {#authentication}

| Переменная | Описание | По умолчанию |
| --- | --- | --- |
| API_JWT_ALGORITHM | Алгоритм JWT | HS256 |
| API_ADMIN_USERNAME | Имя администратора по умолчанию | admin |
| API_ADMIN_PASSWORD | Пароль администратора по умолчанию | admin |

### Провайдеры OAuth2 {#oauth2-providers}

#### GitHub

| Переменная | Описание |
| --- | --- |
| OAUTH_GITHUB_CLIENT_ID | Идентификатор клиента приложения GitHub OAuth |
| OAUTH_GITHUB_CLIENT_SECRET | Секрет клиента приложения GitHub OAuth |

#### Google

| Переменная | Описание |
| --- | --- |
| OAUTH_GOOGLE_CLIENT_ID | Идентификатор клиента Google OAuth |
| OAUTH_GOOGLE_CLIENT_SECRET | Секрет клиента Google OAuth |

#### Keycloak

| Переменная | Описание |
| --- | --- |
| OAUTH_KEYCLOAK_SERVER_URL | URL сервера Keycloak |
| OAUTH_KEYCLOAK_REALM | Realm в Keycloak |
| OAUTH_KEYCLOAK_CLIENT_ID | Идентификатор клиента Keycloak |
| OAUTH_KEYCLOAK_CLIENT_SECRET | Секрет клиента Keycloak |

### LDAP/Active Directory {#ldapactive-directory}

| Переменная | Описание |
| --- | --- |
| LDAP_SERVER | Имя хоста LDAP-сервера |
| LDAP_BASE_DN | Базовый DN для поиска |
| LDAP_BIND_USER | DN пользователя для привязки (bind) |
| LDAP_BIND_PASSWORD | Пароль пользователя для привязки |
| LDAP_USER_SEARCH_BASE | База поиска пользователей |
| LDAP_GROUP_SEARCH_BASE | База поиска групп |

### Ограничение частоты запросов {#rate-limiting}

| Переменная | Описание | По умолчанию |
| --- | --- | --- |
| RATE_LIMIT_STORAGE | Бэкенд хранилища (memoryилиredis://...) | memory |

### Демо-эндпоинт {#demo-endpoint}

| Переменная | Описание | По умолчанию |
| --- | --- | --- |
| DEMO_ENABLED | Включить демо-эндпоинт | true |
| DEMO_RATE_LIMIT | Ограничение частоты для демо | 30/minute |

---

## Аутентификация

### Аутентификация по JWT-токену {#jwt-token-authentication}

#### Вход (получение токена)

```
POST /api/v1/auth/token
Content-Type: application/json

{
  "username": "admin",
  "password": "ваш-пароль"
}
```

**Ответ:**

```
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### Обновление токена

```
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

#### Использование JWT в запросах

```
Authorization: Bearer <access_token>
```

### Аутентификация по API-ключу {#api-key-authentication}

#### Создание API-ключа {#create-api-key}

```
POST /api/v1/auth/api-keys
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "my-integration",
  "expires_days": 365,
  "scopes": ["scenarios:read", "query:execute"]
}
```

**Ответ:**

```
{
  "id": "key_abc123",
  "name": "my-integration",
  "key": "rak_xxxxxxxxxxxxxxxxxxxx",
  "prefix": "rak_xxxx",
  "scopes": ["scenarios:read", "query:execute"],
  "expires_at": "2025-12-09T00:00:00Z",
  "created_at": "2024-12-09T00:00:00Z"
}
```

#### Использование API-ключа в запросах {#use-api-key}

```
X-API-Key: rak_xxxxxxxxxxxxxxxxxxxx
```

#### Список API-ключей

```
GET /api/v1/auth/api-keys
Authorization: Bearer <token>
```

#### Удаление API-ключа

```
DELETE /api/v1/auth/api-keys/{key_id}
Authorization: Bearer <token>
```

### Аутентификация через OAuth2 {#oauth2-authentication}

#### Запуск OAuth-процесса

```
GET /api/v1/auth/oauth/{provider}/authorize
```

Поддерживаемые провайдеры: `github`, `google`, `gitlab`, `keycloak`

#### Обратный вызов OAuth

```
GET /api/v1/auth/oauth/{provider}/callback?code=xxx&state=xxx
```

### Аутентификация через LDAP {#ldap-authentication}

```
POST /api/v1/auth/ldap
Content-Type: application/json

{
  "username": "jdoe",
  "password": "ldap-пароль"
}
```

## Конечные точки API {#api-endpoints}

### Демо (Публичный - Без аутентификации) {#demo-public---no-auth-required}

#### POST /api/v1/demo/chat

Публичная демо-конечная точка для интеграции с целевой страницей. Ограничение по количеству запросов на IP-адрес.

**Запрос:**

```
{
  "query": "Как работает MVCC?",
  "language": "ru"
}
```

**Ответ:**

```
{
  "answer": "MVCC (Multi-Version Concurrency Control)...",
  "scenario_id": "onboarding",
  "processing_time_ms": 1523.45
}
```

**Ограничение по частоте:** 30 запросов в минуту с одного IP

#### GET /api/v1/demo/status

Проверка статуса демо-конечной точки.

**Ответ:**

```
{
  "enabled": true,
  "rate_limit": "30/minute",
  "max_query_length": 500,
  "allowed_scenarios": ["onboarding"]
}
```

---

### Чат {#chat}

#### POST /api/v1/chat

Отправка запроса в систему CodeGraph.

**Запрос:**

```
{
  "query": "Найти уязвимости к SQL-инъекциям",
  "session_id": "необязательный-id-сессии",
  "scenario_id": "security",
  "language": "en"
}
```

**Ответ:**

```
{
  "answer": "Найдено 3 потенциальные уязвимости к SQL-инъекциям...",
  "scenario_id": "security",
  "confidence": 0.85,
  "evidence": [
    {
      "type": "code",
      "source": "src/executor.c:123",
      "content": "sprintf(query, \"SELECT * FROM %s\", user_input);",
      "relevance": 0.95
    }
  ],
  "session_id": "sess_abc123",
  "request_id": "req_xyz789",
  "processing_time_ms": 2341.5
}
```

#### POST /api/v1/chat/stream

Отправка запроса и получение потокового ответа через Server-Sent Events (SSE).

**Запрос:** То же, что и `/chat`

**Ответ:** Поток SSE

```
data: {"type": "start", "session_id": "sess_abc123"}

data: {"type": "chunk", "content": "Найдено 3 потенциальные "}

data: {"type": "chunk", "content": "уязвимости к SQL-инъекциям..."}

data: {"type": "end", "scenario_id": "security"}
```

---

### Сценарии {#scenarios}

#### GET /api/v1/scenarios

Список всех 16 доступных сценариев анализа.

**Ответ:**

```
[
  {
    "id": "onboarding",
    "name": "Onboarding",
    "description": "Начало работы с кодовой базой — поиск функций, построение графов вызовов",
    "category": "Learning",
    "keywords": ["find", "where", "what", "how", "explain"],
    "example_queries": ["Где находится функция main()?", "Что делает exec_simple_query?"]
  },
  {
    "id": "security",
    "name": "Security Audit",
    "description": "Поиск уязвимостей — SQL-инъекции, переполнения буфера",
    "category": "Security",
    "keywords": ["vulnerability", "injection", "unsafe"],
    "example_queries": ["Найти уязвимости к SQL-инъекциям"]
  }
  // ... ещё 14 сценариев
]
```

#### GET /api/v1/scenarios/{scenario_id}

Получение информации о конкретном сценарии.

#### POST /api/v1/scenarios/{scenario_id}/query

Отправка запроса к конкретному сценарию.

**Запрос:**

```
{
  "query": "Найти уязвимости к переполнению буфера",
  "session_id": "необязательный-id-сессии",
  "language": "en"
}
```

---

### Доступные сценарии (всего 16) {#available-scenarios-16-total}

| ID | Название | Категория | Описание |
| --- | --- | --- | --- |
| onboarding | Onboarding | Learning | Начало работы с кодовой базой |
| security | Security Audit | Security | Поиск уязвимостей |
| documentation | Documentation | Documentation | Генерация документации |
| feature_dev | Feature Development | Development | Поиск точек интеграции |
| refactoring | Refactoring | Quality | Выявление код-смэллов |
| performance | Performance Analysis | Performance | Поиск узких мест |
| test_coverage | Test Coverage | Testing | Анализ покрытия тестами |
| compliance | Compliance Check | Quality | Проверка стандартов кодирования |
| code_review | Code Review | Review | Автоматический код-ревью |
| cross_repo | Cross-Repository | Architecture | Анализ зависимостей |
| architecture | Architecture Violations | Architecture | Обнаружение нарушений |
| tech_debt | Technical Debt | Quality | Оценка технического долга |
| mass_refactoring | Mass Refactoring | Development | Масштабные изменения |
| security_incident | Security Incident | Security | Реагирование на инциденты |
| debugging | Debugging Support | Development | Поиск точек логирования |
| entry_points | Entry Points | Security | Поиск поверхности атаки |

---

### Код-ревью {#code-review}

#### POST /api/v1/review/patch

Ревью git-патча/диффа.

**Запрос:**

```
{
  "patch_content": "diff --git a/src/file.c b/src/file.c\n...",
  "task_description": "Исправить утечку памяти в обработчике транзакций",
  "dod_items": ["Нет утечек памяти", "Проходят модульные тесты"],
  "output_format": "json"
}
```

**Ответ:**

```
{
  "recommendation": "REQUEST_CHANGES",
  "confidence": 0.82,
  "findings": [
    {
      "category": "error",
      "severity": "high",
      "location": {"file": "src/file.c", "line_start": 45},
      "message": "Потенциальная утечка памяти: выделенная память не освобождается на пути ошибки",
      "suggested_fix": "Добавить free(ptr) перед оператором return"
    }
  ],
  "dod_status": [
    {"description": "Нет утечек памяти", "satisfied": false, "evidence": "Найдена 1 потенциальная утечка"}
  ],
  "summary": "Найдена 1 проблема высокой серьёзности, которую необходимо устранить."
}
```

#### POST /api/v1/review/github-pr

Ревью Pull Request в GitHub.

**Запрос:**

```
{
  "owner": "postgres",
  "repo": "postgres",
  "pr_number": 123,
  "github_token": "ghp_xxx"
}
```

#### POST /api/v1/review/gitlab-mr

Ревью Merge Request в GitLab.

**Запрос:**

```
{
  "project_id": "123",
  "mr_iid": 456,
  "gitlab_token": "glpat-xxx",
  "gitlab_url": "https://gitlab.com"
}
```

---

### Сессии {#sessions}

#### GET /api/v1/sessions

Список сессий пользователя.

#### POST /api/v1/sessions

Создание новой сессии.

#### GET /api/v1/sessions/{session_id}

Получение деталей сессии.

#### DELETE /api/v1/sessions/{session_id}

Удаление сессии.

---

### История {#history}

#### GET /api/v1/history

Получение истории диалогов.

**Параметры запроса:**
- `session_id` — фильтрация по сессии
- `limit` — количество элементов (по умолчанию: 50)
- `offset` — смещение для пагинации

#### GET /api/v1/history/{message_id}

Получение конкретного сообщения.

#### GET /api/v1/history/export

Экспорт истории диалогов.

**Параметры запроса:**
- `format` — формат экспорта (`json`, `csv`, `markdown`)
- `session_id` — фильтрация по сессии

---

### Запрос (SQL) {#query-sql}

#### POST /api/v1/query/execute

Выполнение SQL-запроса напрямую к базе данных CPG.

**Запрос:**

```
{
  "query": "SELECT name, file FROM nodes_method WHERE name LIKE '%transaction%' LIMIT 10",
  "timeout_ms": 30000
}
```

**Ответ:**

```
{
  "results": [
    {"name": "StartTransaction", "file": "xact.c"},
    {"name": "CommitTransaction", "file": "xact.c"}
  ],
  "row_count": 2,
  "execution_time_ms": 45.2
}
```

---

### Импорт проекта {#project-import}

Импорт новых кодовых баз в систему CodeGraph.

> **Подробная документация:** см. [Руководство по импорту проектов](../guides/PROJECT_IMPORT.md) для примеров использования.

#### GET /api/v1/import/languages

Получение списка поддерживаемых языков программирования.

**Ответ:**

```
{
  "languages": [
    {
      "id": "c",
      "name": "C",
      "extensions": [".c", ".h", ".cpp", ".hpp"],
      "joern_command": "c2cpg",
      "joern_flag": "C"
    },
    {
      "id": "java",
      "name": "JAVA",
      "extensions": [".java"],
      "joern_command": "javasrc2cpg",
      "joern_flag": "JAVASRC"
    }
  ]
}
```

**Поддерживаемые языки (10):**

| ID | Название | Команда Joern | Расширения |
| --- | --- | --- | --- |
| c | C/C++ | c2cpg | .c,.h,.cpp,.hpp,.cc,.cxx |
| csharp | C# | csharp2cpg | .cs |
| go | Go | gosrc2cpg | .go |
| java | Java | javasrc2cpg | .java |
| javascript | JavaScript/TypeScript | jssrc2cpg | .js,.jsx,.ts,.tsx,.mjs |
| kotlin | Kotlin | kotlin2cpg | .kt,.kts |
| php | PHP | php2cpg | .php |
| python | Python | pysrc2cpg | .py,.pyw |
| ruby | Ruby | rubysrc2cpg | .rb |
| swift | Swift | swiftsrc2cpg | .swift |

#### POST /api/v1/import/start

Запуск асинхронного импорта новой кодовой базы.

**Запрос:**

```
{
  "repo_url": "https://github.com/llvm/llvm-project",
  "branch": "main",
  "shallow_clone": true,
  "language": null,
  "mode": "full",
  "include_paths": ["llvm/lib", "llvm/include"],
  "exclude_paths": ["test", "tests"],
  "create_domain_plugin": true,
  "import_docs": true,
  "joern_memory_gb": 16,
  "batch_size": 10000
}
```

**Параметры запроса:**

| Параметр | Тип | По умолчанию | Описание |
| --- | --- | --- | --- |
| repo_url | строка | - | URL Git-репозитория (обязателен, если нетlocal_path) |
| local_path | строка | - | Локальный путь (обязателен, если нетrepo_url) |
| branch | строка | "main" | Ветка Git для клонирования |
| shallow_clone | boolean | true | Использовать неглубокое клонирование |
| shallow_depth | int | 1 | Глубина неглубокого клонирования |
| language | строка | null | ID языка (автоопределение, если null) |
| mode | строка | "full" | Режим импорта:full,selective,incremental |
| include_paths | список | [] | Включаемые пути |
| exclude_paths | список | [] | Исключаемые пути |
| create_domain_plugin | boolean | true | Генерировать Domain Plugin |
| domain_name | строка | null | Пользовательское имя домена |
| import_docs | boolean | true | Импортировать документацию |
| import_readme | boolean | true | Индексировать файлы README |
| import_comments | boolean | true | Импортировать комментарии в коде |
| joern_memory_gb | int | 16 | Память для Joern (ГБ) |
| batch_size | int | 10000 | Размер пакета для DuckDB |

**Ответ:**

```
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Импорт запущен. Используйте job_id для отслеживания прогресса."
}
```

#### GET /api/v1/import/status/{job_id}

Получение текущего статуса задачи импорта.

**Ответ:**

```
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "project_name": "llvm-project",
  "status": "in_progress",
  "steps": [
    {"name": "Clone Repository", "status": "completed", "progress": 100},
    {"name": "Detect Language", "status": "completed", "progress": 100},
    {"name": "Create CPG", "status": "in_progress", "progress": 45, "message": "Создание узлов CPG..."},
    {"name": "Export to DuckDB", "status": "pending", "progress": 0},
    {"name": "Validate CPG", "status": "pending", "progress": 0},
    {"name": "Import Documentation", "status": "pending", "progress": 0},
    {"name": "Setup Domain Plugin", "status": "pending", "progress": 0}
  ],
  "current_step": "joern_import",
  "overall_progress": 35,
  "created_at": "2024-12-09T10:00:00Z",
  "updated_at": "2024-12-09T10:05:00Z"
}
```

**Статусы импорта:**
- `pending` — Ожидание запуска
- `in_progress` — Выполняется
- `completed` — Успешно завершено
- `failed` — Произошла ошибка
- `cancelled` — Отменено пользователем

#### GET /api/v1/import/jobs

Список всех задач импорта.

**Параметры запроса:**
- `status_filter` — фильтрация по статусу (например, `in_progress`, `completed`)
- `limit` — максимальное количество задач (по умолчанию: 20)

**Ответ:** М

## Конечные точки WebSocket {#websocket-endpoints}

### /ws/chat {#wschat}

Соединение для чата в реальном времени.

**Подключение:**

```
const ws = new WebSocket('ws://localhost:8000/ws/chat?token=<jwt_token>');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Получено:', data);
};

ws.send(JSON.stringify({
  type: 'query',
  query: 'Найти уязвимости к SQL-инъекциям',
  scenario_id: 'security'
}));
```

### /ws/jobs/{job_id} {#wsjobsjob_id}

Мониторинг хода выполнения фоновой задачи.

### /ws/notifications {#wsnotifications}

Получение уведомлений в реальном времени.

---

## Ограничение частоты запросов

### Ограничения по умолчанию

- **Глобальные:** 100 запросов/минуту, 1000 запросов/час

### Ограничения для конкретных конечных точек

| Конечная точка | Ограничение |
| --- | --- |
| /api/v1/review/* | 10/минуту |
| /api/v1/chat | 60/минуту |
| /api/v1/chat/stream | 30/минуту |
| /api/v1/query/execute | 30/минуту |
| /api/v1/demo/chat | 30/минуту на один IP |

### Заголовки ограничения частоты {#rate-limit-headers}

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1702123456
```

### Использование Redis для ограничения частоты запросов {#using-redis-for-rate-limiting}

Для продакшена с несколькими экземплярами используйте Redis:

```
RATE_LIMIT_STORAGE=redis://localhost:6379
```

---

## Роли RBAC {#rbac-roles}

| Роль | Разрешения |
| --- | --- |
| viewer | Просмотр сценариев, просмотр истории |
| analyst | Все разрешения viewer + выполнение запросов, создание сессий |
| reviewer | Все разрешения analyst + проверка кода, проверка патчей |
| admin | Полный доступ, включая управление пользователями |

---

## Настройка базы данных {#database-setup}

### Подключение PostgreSQL {#postgresql-connection}

Требуется PostgreSQL 12+ с поддержкой асинхронных операций.

```
# Создание базы данных {#create-database}
createdb codegraph

# Установка строки подключения {#set-connection-string}
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/codegraph"
```

### Миграции Alembic {#alembic-migrations}

```
# Применить все миграции {#apply-all-migrations}
python -m src.api.cli migrate

# Перейти к определённой ревизии {#migrate-to-specific-revision}
python -m src.api.cli migrate --revision abc123
```

### Схема базы данных {#database-schema}

Основные таблицы:
- `users` — учетные записи пользователей
- `api_keys` — хранение API-ключей
- `sessions` — сессии чата
- `messages` — история сообщений
- `jobs` — статус фоновых задач

---

## Команды CLI {#cli-commands}

```
# Запустить сервер API {#run-api-server}
python -m src.api.cli run [--host HOST] [--port PORT] [--workers N] [--reload]

# Инициализировать базу данных {#initialize-database}
python -m src.api.cli init-db

# Выполнить миграции {#run-migrations}
python -m src.api.cli migrate [--revision REV]

# Создать учётную запись администратора {#create-admin-user}
python -m src.api.cli create-admin --username USER --password PASS [--email EMAIL]
```

## Пример использования (curl) {#example-usage-curl}

### Демо-эндпоинт (без аутентификации) {#demo-endpoint-no-auth}

```
curl -X POST http://localhost:8000/api/v1/demo/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Как работает MVCC?", "language": "ru"}'
```

### Вход в систему {#login}

```
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "secret"}'
```

### Чат с использованием JWT {#chat-with-jwt}

```
export TOKEN="eyJhbGciOiJIUzI1NiIs..."

curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Find SQL injection vulnerabilities", "scenario_id": "security"}'
```

### Список сценариев

```
curl http://localhost:8000/api/v1/scenarios \
  -H "Authorization: Bearer $TOKEN"
```

### Создание API-ключа

```
curl -X POST http://localhost:8000/api/v1/auth/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-integration", "expires_days": 365}'
```

### Использование API-ключа

```
curl http://localhost:8000/api/v1/scenarios \
  -H "X-API-Key: rak_xxxxxxxxxxxxxxxxxxxx"
```

### Проверка патча

```
curl -X POST http://localhost:8000/api/v1/review/patch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patch_content": "diff --git a/src/file.c ...",
    "task_description": "Fix memory leak",
    "output_format": "json"
  }'
```

## Ответы с ошибками

Все ошибки возвращают JSON следующей структуры:

```
{
  "detail": "Текст ошибки здесь",
  "error_code": "VALIDATION_ERROR",
  "request_id": "req_abc123"
}
```

### Общие коды состояния HTTP

| Код | Описание |
| --- | --- |
| 400 | Неверный запрос — некорректные входные данные |
| 401 | Неавторизованный доступ — отсутствует или неверна аутентификация |
| 403 | Доступ запрещён — недостаточно прав |
| 404 | Не найдено |
| 429 | Слишком много запросов — превышен лимит запросов |
| 500 | Ошибка внутреннего сервера |
| 503 | Сервис недоступен |

---

## Связанная документация

- [Руководство пользователя TUI](../guides/TUI_USER_GUIDE.md)
- [Руководство по сценариям](../guides/SCENARIOS.md)
- [Руководство по импорту проекта](../guides/PROJECT_IMPORT.md)
- [Справочник API (внутренний)](../reference/API.md)
- [Устранение неполадок](../guides/TROUBLESHOOTING.md)
