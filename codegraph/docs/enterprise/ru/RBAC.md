# RBAC и Авторизация

> Техническая документация для команд ИТ и информационной безопасности

---

## Table of Contents

- [Обзор](#обзор)
  - [Ключевые возможности](#ключевые-возможности)
- [Архитектура RBAC](#архитектура-rbac)
  - [Иерархия ролей](#иерархия-ролей)
  - [Наследование разрешений](#наследование-разрешений)
- [Каталог разрешений](#каталог-разрешений)
  - [Разрешения по категориям](#разрешения-по-категориям)
- [Методы аутентификации](#методы-аутентификации)
  - [1. JWT Bearer Token](#1-jwt-bearer-token)
  - [2. API-ключи](#2-api-ключи)
  - [3. OAuth2/OIDC (готово к интеграции)](#3-oauth2oidc-готово-к-интеграции)
  - [4. LDAP/Active Directory (готово к интеграции)](#4-ldapactive-directory-готово-к-интеграции)
- [API Reference](#api-reference)
  - [Middleware зависимости](#middleware-зависимости)
  - [Примеры использования в FastAPI](#примеры-использования-в-fastapi)
  - [AuthContext](#authcontext)
- [Аудит и логирование](#аудит-и-логирование)
  - [События авторизации](#события-авторизации)
  - [Формат лога](#формат-лога)
- [Лучшие практики](#лучшие-практики)
  - [Для администраторов](#для-администраторов)
  - [Для разработчиков](#для-разработчиков)
- [Связанные документы](#связанные-документы)

## Обзор

CodeGraph реализует комплексную систему контроля доступа на основе ролей (RBAC) с поддержкой множества методов аутентификации. Система обеспечивает гранулярный контроль доступа к функциям платформы.

### Ключевые возможности

- **4 уровня ролей** с иерархическим наследованием
- **21 гранулярное разрешение** по категориям функциональности
- **Множество методов аутентификации**: JWT, API-ключи, OAuth2, LDAP
- **Blacklisting токенов** для мгновенного отзыва доступа
- **Интеграция с SIEM** для аудита событий авторизации

---

## Архитектура RBAC

### Иерархия ролей

```
                           ┌─────────────────────┐
                           │       ADMIN         │
                           │    (admin:all)      │
                           │   Полный доступ     │
                           └──────────┬──────────┘
                                      │
                           ┌──────────▼──────────┐
                           │      REVIEWER       │
                           │  Код-ревью + GitHub │
                           │      + GitLab       │
                           └──────────┬──────────┘
                                      │
                           ┌──────────▼──────────┐
                           │      ANALYST        │
                           │  Выполнение запросов│
                           │  + API-ключи        │
                           └──────────┬──────────┘
                                      │
                           ┌──────────▼──────────┐
                           │       VIEWER        │
                           │  Только чтение      │
                           └─────────────────────┘
```

### Наследование разрешений

Каждая роль наследует все разрешения нижестоящих ролей:
- `ADMIN` → все разрешения (`admin:all`)
- `REVIEWER` → разрешения `ANALYST` + код-ревью
- `ANALYST` → разрешения `VIEWER` + выполнение/экспорт
- `VIEWER` → только чтение (базовый уровень)

---

## Каталог разрешений

### Разрешения по категориям

#### Сценарии (`scenarios:*`)
| Разрешение | Описание | VIEWER | ANALYST | REVIEWER | ADMIN |
|------------|----------|:------:|:-------:|:--------:|:-----:|
| `scenarios:read` | Просмотр списка сценариев | ✓ | ✓ | ✓ | ✓ |
| `scenarios:execute` | Запуск сценариев анализа | | ✓ | ✓ | ✓ |

#### Запросы (`query:*`)
| Разрешение | Описание | VIEWER | ANALYST | REVIEWER | ADMIN |
|------------|----------|:------:|:-------:|:--------:|:-----:|
| `query:execute` | Выполнение SQL-запросов к CPG | | ✓ | ✓ | ✓ |
| `query:validate` | Валидация синтаксиса запросов | | ✓ | ✓ | ✓ |

#### Код-ревью (`review:*`)
| Разрешение | Описание | VIEWER | ANALYST | REVIEWER | ADMIN |
|------------|----------|:------:|:-------:|:--------:|:-----:|
| `review:execute` | Запуск автоматического ревью | | | ✓ | ✓ |
| `review:github` | Интеграция с GitHub PR | | | ✓ | ✓ |
| `review:gitlab` | Интеграция с GitLab MR | | | ✓ | ✓ |

#### Сессии (`sessions:*`)
| Разрешение | Описание | VIEWER | ANALYST | REVIEWER | ADMIN |
|------------|----------|:------:|:-------:|:--------:|:-----:|
| `sessions:read` | Просмотр сессий | ✓ | ✓ | ✓ | ✓ |
| `sessions:write` | Создание/изменение сессий | | ✓ | ✓ | ✓ |
| `sessions:delete` | Удаление сессий | | ✓ | ✓ | ✓ |

#### История (`history:*`)
| Разрешение | Описание | VIEWER | ANALYST | REVIEWER | ADMIN |
|------------|----------|:------:|:-------:|:--------:|:-----:|
| `history:read` | Просмотр истории запросов | ✓ | ✓ | ✓ | ✓ |
| `history:export` | Экспорт истории | | ✓ | ✓ | ✓ |

#### Пользователи (`users:*`)
| Разрешение | Описание | VIEWER | ANALYST | REVIEWER | ADMIN |
|------------|----------|:------:|:-------:|:--------:|:-----:|
| `users:read` | Просмотр списка пользователей | | | | ✓ |
| `users:write` | Создание/редактирование | | | | ✓ |
| `users:delete` | Удаление пользователей | | | | ✓ |

#### API-ключи (`api_keys:*`)
| Разрешение | Описание | VIEWER | ANALYST | REVIEWER | ADMIN |
|------------|----------|:------:|:-------:|:--------:|:-----:|
| `api_keys:read` | Просмотр своих ключей | | ✓ | ✓ | ✓ |
| `api_keys:write` | Создание ключей | | ✓ | ✓ | ✓ |
| `api_keys:delete` | Удаление любых ключей | | | | ✓ |

#### Метрики (`stats:*`, `metrics:*`)
| Разрешение | Описание | VIEWER | ANALYST | REVIEWER | ADMIN |
|------------|----------|:------:|:-------:|:--------:|:-----:|
| `stats:read` | Просмотр статистики | ✓ | ✓ | ✓ | ✓ |
| `metrics:read` | Prometheus метрики | | | | ✓ |

#### Администрирование
| Разрешение | Описание | VIEWER | ANALYST | REVIEWER | ADMIN |
|------------|----------|:------:|:-------:|:--------:|:-----:|
| `admin:all` | Полный доступ | | | | ✓ |

---

## Методы аутентификации

### 1. JWT Bearer Token

Основной метод для веб-приложений и интерактивных сессий.

#### Структура токена

```python
class TokenPayload:
    sub: str       # User ID
    jti: str       # JWT ID (уникальный идентификатор)
    exp: datetime  # Время истечения
    iat: datetime  # Время выдачи
    type: str      # "access" или "refresh"
    scopes: list   # Список разрешений
    role: str      # Роль пользователя
```

#### Параметры токенов

| Тип токена | TTL | Назначение |
|------------|-----|------------|
| Access Token | 30 минут | Авторизация API-запросов |
| Refresh Token | 7 дней | Обновление access-токена |

#### Пример использования

```bash
# Получение токена
curl -X POST /api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "analyst", "password": "***"}'

# Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}

# Использование токена
curl -X GET /api/v1/scenarios \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### Отзыв токена (Blacklisting)

```bash
# Logout - добавление токена в blacklist
curl -X POST /api/v1/auth/logout \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

После добавления в blacklist токен мгновенно становится недействительным.

---

### 2. API-ключи

Для интеграций, CI/CD и автоматизации.

#### Формат API-ключа

```
Prefix: cgk_          (CodeGraph Key)
Secret: [36 символов] (UUID v4)

Пример: cgk_550e8400-e29b-41d4-a716-446655440000
```

#### Безопасность хранения

- Ключи хешируются SHA-256 перед сохранением
- Полный ключ показывается только при создании
- Поддержка срока действия и отзыва

#### Пример использования

```bash
# Создание API-ключа
curl -X POST /api/v1/auth/api-keys \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"name": "CI Pipeline", "scopes": ["query:execute", "scenarios:execute"]}'

# Response:
{
  "id": "key_123",
  "key": "cgk_550e8400-e29b-41d4-a716-446655440000",  # Показывается только один раз!
  "name": "CI Pipeline",
  "scopes": ["query:execute", "scenarios:execute"],
  "expires_at": "2026-01-01T00:00:00Z"
}

# Использование API-ключа
curl -X GET /api/v1/scenarios \
  -H "X-API-Key: cgk_550e8400-e29b-41d4-a716-446655440000"
```

#### Разрешения по умолчанию для API-ключей

```python
default_scopes = [
    "scenarios:read",
    "scenarios:execute",
    "query:execute",
    "sessions:read",
    "sessions:write",
    "history:read",
]
```

---

### 3. OAuth2/OIDC (готово к интеграции)

Поддержка корпоративных провайдеров идентификации.

#### Поддерживаемые провайдеры

| Провайдер | Статус | Сценарий |
|-----------|--------|----------|
| GitHub | ✅ Готово | Разработчики, open-source |
| GitLab | ✅ Готово | Корпоративные GitLab |
| Google | ✅ Готово | Google Workspace |
| Keycloak | ✅ Готово | Enterprise IdP |
| Azure AD | ✅ Готово | Microsoft 365 |

#### Конфигурация (пример для Keycloak)

```yaml
oauth2:
  providers:
    keycloak:
      enabled: true
      client_id: "codegraph"
      client_secret: "${KEYCLOAK_SECRET}"
      authorize_url: "https://keycloak.company.com/realms/main/protocol/openid-connect/auth"
      token_url: "https://keycloak.company.com/realms/main/protocol/openid-connect/token"
      userinfo_url: "https://keycloak.company.com/realms/main/protocol/openid-connect/userinfo"
      scopes: ["openid", "profile", "email", "groups"]
      role_claim: "realm_access.roles"
      role_mapping:
        codegraph-admin: admin
        codegraph-reviewer: reviewer
        codegraph-analyst: analyst
        codegraph-viewer: viewer
```

---

### 4. LDAP/Active Directory (готово к интеграции)

Интеграция с корпоративным каталогом.

#### Конфигурация

```yaml
ldap:
  enabled: true
  server: "ldaps://ldap.company.com:636"
  base_dn: "dc=company,dc=com"
  bind_dn: "cn=codegraph,ou=services,dc=company,dc=com"
  bind_password: "${LDAP_PASSWORD}"
  user_search_base: "ou=users,dc=company,dc=com"
  user_search_filter: "(sAMAccountName={username})"
  group_search_base: "ou=groups,dc=company,dc=com"
  group_membership_attr: "memberOf"
  group_mapping:
    "CN=CodeGraph-Admins,OU=Groups,DC=company,DC=com": admin
    "CN=CodeGraph-Reviewers,OU=Groups,DC=company,DC=com": reviewer
    "CN=CodeGraph-Analysts,OU=Groups,DC=company,DC=com": analyst
    "CN=CodeGraph-Viewers,OU=Groups,DC=company,DC=com": viewer
  sync_interval_minutes: 15
```

#### Синхронизация групп

- Автоматическая синхронизация ролей с группами AD
- Поддержка вложенных групп
- Кэширование с настраиваемым TTL

---

## API Reference

### Middleware зависимости

```python
from src.api.auth.middleware import (
    get_auth_context,     # Получить контекст (без ошибки если не авторизован)
    require_auth,         # Требовать любую аутентификацию
    require_permission,   # Требовать конкретное разрешение
    require_role,         # Требовать конкретную роль
    require_admin,        # Shortcut для admin
    require_analyst,      # Shortcut для analyst+
    require_reviewer,     # Shortcut для reviewer+
)
```

### Примеры использования в FastAPI

```python
from fastapi import Depends, APIRouter
from src.api.auth.middleware import require_permission, require_admin
from src.api.auth.permissions import Permission

router = APIRouter()

# Требовать конкретное разрешение
@router.post("/query/execute")
async def execute_query(
    query: str,
    auth = Depends(require_permission(Permission.QUERY_EXECUTE))
):
    # auth.user_id, auth.role, auth.scopes доступны
    return {"result": "..."}

# Требовать одно из нескольких разрешений
@router.get("/reviews")
async def list_reviews(
    auth = Depends(require_any_permission(
        Permission.REVIEW_EXECUTE,
        Permission.REVIEW_GITHUB,
        Permission.REVIEW_GITLAB
    ))
):
    return {"reviews": [...]}

# Требовать роль Admin
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    auth = Depends(require_admin)
):
    return {"deleted": user_id}
```

### AuthContext

```python
class AuthContext:
    user_id: str          # ID пользователя
    username: str         # Имя пользователя
    role: Role            # Роль (VIEWER, ANALYST, REVIEWER, ADMIN)
    scopes: List[str]     # Список разрешений
    auth_method: str      # "jwt", "api_key", "oauth2", "ldap"

    @property
    def is_authenticated(self) -> bool:
        """Проверка аутентификации"""

    def has_permission(self, permission: Permission) -> bool:
        """Проверка конкретного разрешения"""
```

---

## Аудит и логирование

### События авторизации

Все события авторизации логируются и отправляются в SIEM:

| Событие | Severity | Описание |
|---------|----------|----------|
| `AUTH_SUCCESS` | INFO | Успешная аутентификация |
| `AUTH_FAILURE` | WARNING | Неудачная попытка |
| `TOKEN_ISSUED` | INFO | Выдан новый токен |
| `TOKEN_REVOKED` | INFO | Токен отозван |
| `PERMISSION_DENIED` | WARNING | Отказ в доступе |
| `API_KEY_CREATED` | INFO | Создан API-ключ |
| `API_KEY_REVOKED` | INFO | API-ключ отозван |

### Формат лога

```json
{
  "timestamp": "2025-12-14T10:30:00.000Z",
  "event_type": "AUTH_SUCCESS",
  "user_id": "user_123",
  "username": "analyst@company.com",
  "role": "analyst",
  "auth_method": "jwt",
  "ip_address": "10.0.0.50",
  "user_agent": "Mozilla/5.0...",
  "request_path": "/api/v1/scenarios",
  "request_method": "GET"
}
```

---

## Лучшие практики

### Для администраторов

1. **Принцип наименьших привилегий** — назначайте минимально необходимые роли
2. **Используйте API-ключи с ограниченными scopes** для автоматизации
3. **Настройте синхронизацию с LDAP/AD** для централизованного управления
4. **Включите SIEM-интеграцию** для мониторинга событий безопасности
5. **Регулярно проводите аудит** активных сессий и API-ключей

### Для разработчиков

1. **Используйте JWT для веб-приложений**, API-ключи для CI/CD
2. **Храните refresh-токены безопасно** (httpOnly cookies)
3. **Обрабатывайте 401/403** корректно в UI
4. **Не логируйте токены и ключи** в открытом виде

---

## Связанные документы

- [Enterprise Security Brief](./SECURITY_BRIEF.md) — Обзор безопасности
- [DLP Security](./DLP_SECURITY.md) — Защита от утечки данных
- [SIEM Integration](./SIEM.md) — Интеграция с SIEM
- [REST API Reference](../api/REST_API.md) — Справочник API

---

*Версия: 1.0 | Декабрь 2025*
