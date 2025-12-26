# CodeGraph Leads Microservice

Микросервис для сохранения заявок из CTA-формы на лендинге CodeGraph.

## Возможности

- **Сбор лидов**: Сохранение заявок на демо в PostgreSQL
- **Уведомления**: Оповещения в Telegram и по Email
- **Admin API**: Просмотр, фильтрация, экспорт и управление лидами
- **CLI**: Командная строка для работы с лидами
- **Rate Limiting**: Ограничение запросов по IP (защита от спама)

---

## Содержание

1. [Быстрый старт](#быстрый-старт)
2. [Локальная разработка](#локальная-разработка)
3. [Деплой на сервер](#деплой-на-сервер)
4. [Настройка уведомлений](#настройка-уведомлений)
5. [API документация](#api-документация)
6. [CLI команды](#cli-команды)
7. [Интеграция с лендингом](#интеграция-с-лендингом)
8. [Troubleshooting](#troubleshooting)

---

## Быстрый старт

### Требования

- Python 3.11+
- PostgreSQL 14+ (или Docker)
- Docker и Docker Compose (для production)

### Минимальная конфигурация

```bash
# 1. Перейти в директорию сервиса
cd services/leads

# 2. Создать .env файл
cp .env.example .env

# 3. Отредактировать минимальные настройки в .env:
#    - DATABASE_URL (обязательно)
#    - LEADS_API_KEY (обязательно для admin endpoints)
```

---

## Локальная разработка

### Шаг 1: Создание виртуального окружения

```bash
cd services/leads

# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Шаг 2: Установка зависимостей

```bash
pip install -r requirements.txt
```

### Шаг 3: Настройка базы данных

**Вариант A: Использовать PostgreSQL из основного docker-compose**

```bash
# Из корня проекта codegraph
docker-compose up -d postgres

# Создать базу данных для лидов
docker exec -it codegraph-postgres psql -U codegraph -c "CREATE DATABASE codegraph_leads;"
```

**Вариант B: Локальный PostgreSQL**

```bash
# Создать базу данных
psql -U postgres -c "CREATE DATABASE codegraph_leads;"
psql -U postgres -c "CREATE USER codegraph WITH PASSWORD 'your_password';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE codegraph_leads TO codegraph;"
```

### Шаг 4: Настройка .env

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```bash
# Минимальная конфигурация для локальной разработки
DATABASE_URL=postgresql+asyncpg://codegraph:your_password@localhost:5432/codegraph_leads
LEADS_API_KEY=dev-api-key-12345
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# Уведомления отключены (опционально настроить позже)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
SMTP_USER=
SMTP_PASSWORD=
ADMIN_EMAIL=
```

### Шаг 5: Применение миграций

```bash
alembic upgrade head
```

### Шаг 6: Запуск сервера

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

### Шаг 7: Проверка работы

Откройте в браузере:
- API Docs: http://localhost:8001/docs
- Health Check: http://localhost:8001/api/v1/health

Тестовый запрос:

```bash
curl -X POST http://localhost:8001/api/v1/leads \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Тест Тестов",
    "email": "test@example.com",
    "company": "ООО Тест"
  }'
```

---

## Деплой на сервер

### Вариант 1: Docker Compose (рекомендуется)

#### Шаг 1: Убедитесь что основной стек запущен

```bash
# Из корня проекта
docker-compose up -d
```

#### Шаг 2: Создайте базу данных для лидов

```bash
docker exec -it codegraph-postgres psql -U codegraph -c "CREATE DATABASE codegraph_leads;"
```

#### Шаг 3: Создайте .env для leads сервиса

```bash
cd services/leads
cp .env.example .env
```

Отредактируйте `.env`:

```bash
# Используем тот же пароль PostgreSQL что и в основном .env
DATABASE_URL=postgresql+asyncpg://codegraph:YOUR_POSTGRES_PASSWORD@codegraph-postgres:5432/codegraph_leads

# Сгенерируйте уникальный API ключ
LEADS_API_KEY=your-secure-api-key-here

# Production настройки
ENVIRONMENT=production
LOG_LEVEL=INFO
CORS_ALLOWED_ORIGINS=https://codegraph.ru,https://www.codegraph.ru
```

#### Шаг 4: Запустите сервис

```bash
docker-compose -f docker-compose.leads.yml up -d
```

#### Шаг 5: Примените миграции

```bash
docker exec -it codegraph-leads-api alembic upgrade head
```

#### Шаг 6: Проверьте статус

```bash
docker-compose -f docker-compose.leads.yml ps
docker-compose -f docker-compose.leads.yml logs -f
```

### Вариант 2: Systemd сервис

При использовании `scripts/install-ubuntu.sh` сервис автоматически настраивается:

```bash
# Запуск
sudo systemctl start codegraph-leads

# Остановка
sudo systemctl stop codegraph-leads

# Статус
sudo systemctl status codegraph-leads

# Логи
sudo journalctl -u codegraph-leads -f
```

---

## Настройка уведомлений

### Telegram уведомления

#### Шаг 1: Создайте бота

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям и получите токен вида `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

#### Шаг 2: Получите Chat ID

**Для личного чата:**
1. Напишите боту любое сообщение
2. Откройте `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Найдите `"chat":{"id":123456789}` - это ваш Chat ID

**Для канала/группы:**
1. Добавьте бота в канал/группу как администратора
2. Напишите сообщение в канал
3. Откройте `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
4. Chat ID канала будет отрицательным числом: `-1001234567890`

#### Шаг 3: Настройте .env

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=-1001234567890
```

#### Шаг 4: Проверьте подключение

```bash
# Через CLI
python -m src.cli.commands test-notifications

# Или через curl (отправьте тестовый лид)
curl -X POST http://localhost:8001/api/v1/leads \
  -H "Content-Type: application/json" \
  -d '{"name": "Тест", "email": "test@test.com", "company": "Тест"}'
```

### Email уведомления (Yandex)

#### Шаг 1: Настройте пароль приложения

1. Войдите в [Яндекс ID](https://id.yandex.ru/)
2. Перейдите в "Безопасность" → "Пароли приложений"
3. Создайте пароль для "Почта"

#### Шаг 2: Настройте .env

```bash
SMTP_HOST=smtp.yandex.ru
SMTP_PORT=587
SMTP_USER=your_email@yandex.ru
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=noreply@codegraph.ru
ADMIN_EMAIL=sales@codegraph.ru
```

### Email уведомления (Gmail)

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password  # App Password, не обычный пароль!
SMTP_FROM_EMAIL=your_email@gmail.com
ADMIN_EMAIL=admin@yourcompany.com
```

---

## API документация

### Базовый URL

- Локально: `http://localhost:8001`
- Production: `https://your-domain.com:8001` или через nginx proxy

### Публичные endpoints

#### POST /api/v1/leads - Создать лид

**Rate limit:** 10 запросов в минуту с одного IP

```bash
curl -X POST http://localhost:8001/api/v1/leads \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Иван Петров",
    "email": "ivan@company.ru",
    "company": "ООО Технологии",
    "position": "CTO",
    "team_size": "11-50",
    "language": "python"
  }'
```

**Поля:**
| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| `name` | string | Да | Имя контакта (1-100 символов) |
| `email` | string | Да | Email адрес |
| `company` | string | Да | Название компании (1-200 символов) |
| `position` | string | Нет | Должность |
| `team_size` | enum | Нет | Размер команды: `1-10`, `11-50`, `51-200`, `200+` |
| `language` | enum | Нет | Язык: `c-cpp`, `java`, `python`, `go`, `javascript`, `csharp`, `other` |

**Ответ (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Заявка успешно отправлена! Мы свяжемся с вами в ближайшее время."
}
```

#### GET /api/v1/health - Проверка здоровья

```bash
curl http://localhost:8001/api/v1/health
```

### Admin endpoints (требуется X-API-Key)

#### GET /api/v1/leads - Список лидов

```bash
curl -X GET "http://localhost:8001/api/v1/leads?page=1&page_size=20&status=new" \
  -H "X-API-Key: your-api-key"
```

**Query параметры:**
| Параметр | Тип | Описание |
|----------|-----|----------|
| `page` | int | Номер страницы (default: 1) |
| `page_size` | int | Размер страницы (default: 20, max: 100) |
| `status` | string | Фильтр по статусу |
| `company` | string | Поиск по компании |
| `language` | string | Фильтр по языку |
| `team_size` | string | Фильтр по размеру команды |
| `created_from` | datetime | Фильтр по дате (от) |
| `created_to` | datetime | Фильтр по дате (до) |
| `search` | string | Поиск по имени, email, компании |

#### GET /api/v1/leads/{id} - Получить лид

```bash
curl -X GET "http://localhost:8001/api/v1/leads/550e8400-e29b-41d4-a716-446655440000" \
  -H "X-API-Key: your-api-key"
```

#### GET /api/v1/leads/stats - Статистика

```bash
curl -X GET "http://localhost:8001/api/v1/leads/stats" \
  -H "X-API-Key: your-api-key"
```

#### GET /api/v1/leads/export - Экспорт в CSV

```bash
curl -X GET "http://localhost:8001/api/v1/leads/export?status=new" \
  -H "X-API-Key: your-api-key" \
  -o leads.csv
```

#### PATCH /api/v1/leads/{id} - Обновить лид

```bash
curl -X PATCH "http://localhost:8001/api/v1/leads/550e8400-e29b-41d4-a716-446655440000" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "contacted",
    "notes": "Созвонились, назначена демо на пятницу"
  }'
```

**Статусы лидов:**
- `new` - Новый
- `contacted` - Связались
- `qualified` - Квалифицирован
- `demo_scheduled` - Назначена демо
- `converted` - Конвертирован
- `closed` - Закрыт

#### DELETE /api/v1/leads/{id} - Удалить лид

```bash
curl -X DELETE "http://localhost:8001/api/v1/leads/550e8400-e29b-41d4-a716-446655440000" \
  -H "X-API-Key: your-api-key"
```

---

## CLI команды

### Установка CLI

CLI доступен внутри Docker контейнера или при локальной установке:

```bash
# Внутри контейнера
docker exec -it codegraph-leads-api python -m src.cli.commands --help

# Локально
cd services/leads
python -m src.cli.commands --help
```

### Список команд

```bash
# Список лидов
python -m src.cli.commands list
python -m src.cli.commands list --status new --limit 10
python -m src.cli.commands list --format json
python -m src.cli.commands list --format csv

# Детали лида
python -m src.cli.commands show <lead_id>

# Статистика
python -m src.cli.commands stats

# Экспорт в CSV
python -m src.cli.commands export -o leads.csv
python -m src.cli.commands export --status new --from-date 2024-01-01

# Обновление статуса
python -m src.cli.commands update <lead_id> --status contacted
python -m src.cli.commands update <lead_id> --notes "Комментарий"

# Тест уведомлений
python -m src.cli.commands test-notifications
```

---

## Интеграция с лендингом

### Как работает форма

Файл `docs/landing/js/main.js` содержит код отправки формы:

```javascript
// Определение URL API в зависимости от окружения
const isLocalhost = window.location.hostname === 'localhost';
const leadsApiUrl = isLocalhost
  ? 'http://localhost:8001/api/v1/leads'
  : '/api/leads';  // Через nginx proxy
```

### Настройка Nginx (production)

Добавьте в конфигурацию nginx:

```nginx
# Проксирование запросов к leads API
location /api/leads {
    proxy_pass http://codegraph-leads-api:8001/api/v1/leads;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # CORS заголовки (если нужны)
    add_header Access-Control-Allow-Origin $http_origin always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Content-Type" always;

    if ($request_method = OPTIONS) {
        return 204;
    }
}
```

### Тестирование формы локально

1. Запустите leads сервис на порту 8001
2. Откройте лендинг `docs/landing/index.html` в браузере
3. Заполните и отправьте форму
4. Проверьте что лид создан: `curl http://localhost:8001/api/v1/leads -H "X-API-Key: your-key"`

---

## Troubleshooting

### Проблема: Ошибка подключения к базе данных

**Симптом:**
```
sqlalchemy.exc.OperationalError: connection refused
```

**Решение:**
1. Убедитесь что PostgreSQL запущен
2. Проверьте DATABASE_URL в .env
3. Проверьте что база `codegraph_leads` создана
4. Проверьте что пользователь имеет права на БД

```bash
# Проверка подключения
docker exec -it codegraph-postgres psql -U codegraph -d codegraph_leads -c "SELECT 1;"
```

### Проблема: Telegram уведомления не приходят

**Решение:**
1. Проверьте токен бота: `curl https://api.telegram.org/bot<TOKEN>/getMe`
2. Проверьте Chat ID: `curl https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Убедитесь что бот добавлен в чат/канал
4. Для каналов: бот должен быть администратором

```bash
# Тест отправки
python -m src.cli.commands test-notifications
```

### Проблема: Email уведомления не отправляются

**Решение:**
1. Проверьте SMTP настройки (хост, порт)
2. Используйте пароль приложения, не обычный пароль
3. Проверьте что аккаунт не заблокирован за спам

### Проблема: Rate limit при тестировании

**Симптом:**
```
429 Too Many Requests
```

**Решение:**
- Подождите минуту между запросами
- Для разработки можно увеличить лимит в .env: `RATE_LIMIT_LEADS_CREATE=100/minute`

### Проблема: CORS ошибки в браузере

**Симптом:**
```
Access to fetch blocked by CORS policy
```

**Решение:**
1. Добавьте origin лендинга в `CORS_ALLOWED_ORIGINS`
2. При локальной разработке используйте `file://` или localhost

---

## Переменные окружения

| Переменная | Описание | По умолчанию | Обязательная |
|------------|----------|--------------|--------------|
| `DATABASE_URL` | PostgreSQL connection string | - | Да |
| `LEADS_API_KEY` | API ключ для admin endpoints | - | Да |
| `ENVIRONMENT` | Окружение (development/production) | `development` | Нет |
| `LOG_LEVEL` | Уровень логирования | `INFO` | Нет |
| `CORS_ALLOWED_ORIGINS` | Разрешенные CORS origins | `https://codegraph.ru` | Нет |
| `RATE_LIMIT_LEADS_CREATE` | Rate limit для создания лидов | `10/minute` | Нет |
| `SMTP_HOST` | SMTP сервер | `smtp.yandex.ru` | Нет |
| `SMTP_PORT` | SMTP порт | `587` | Нет |
| `SMTP_USER` | SMTP пользователь | - | Нет |
| `SMTP_PASSWORD` | SMTP пароль | - | Нет |
| `SMTP_FROM_EMAIL` | Email отправителя | `noreply@codegraph.ru` | Нет |
| `ADMIN_EMAIL` | Email для уведомлений | - | Нет |
| `TELEGRAM_BOT_TOKEN` | Токен Telegram бота | - | Нет |
| `TELEGRAM_CHAT_ID` | Chat ID для уведомлений | - | Нет |

---

## Архитектура

```
services/leads/
├── docker-compose.leads.yml   # Docker Compose конфигурация
├── Dockerfile                 # Multi-stage Docker build
├── requirements.txt           # Python зависимости
├── alembic.ini               # Конфигурация Alembic
├── .env.example              # Пример переменных окружения
│
├── src/
│   ├── __init__.py
│   ├── main.py               # FastAPI приложение, CORS, rate limiting
│   ├── config.py             # Pydantic Settings
│   │
│   ├── models/
│   │   └── lead.py           # Pydantic модели (request/response)
│   │
│   ├── database/
│   │   ├── connection.py     # Async SQLAlchemy connection
│   │   ├── models.py         # SQLAlchemy ORM модели
│   │   └── migrations/       # Alembic миграции
│   │
│   ├── routers/
│   │   ├── leads.py          # API endpoints для лидов
│   │   └── health.py         # Health check endpoint
│   │
│   ├── services/
│   │   ├── lead_service.py   # Бизнес-логика работы с лидами
│   │   └── export_service.py # Экспорт в CSV
│   │
│   ├── notifications/
│   │   ├── telegram.py       # Telegram Bot API интеграция
│   │   └── email.py          # SMTP email отправка
│   │
│   └── cli/
│       └── commands.py       # CLI команды (Click)
│
└── tests/
    ├── conftest.py           # Pytest фикстуры
    └── test_leads_api.py     # Тесты API
```

---

## Тестирование

```bash
# Запуск всех тестов
pytest tests/ -v

# С покрытием
pytest tests/ -v --cov=src --cov-report=html

# Только определенный тест
pytest tests/test_leads_api.py::TestLeadCreation -v
```

---

## Лицензия

Часть проекта CodeGraph.
