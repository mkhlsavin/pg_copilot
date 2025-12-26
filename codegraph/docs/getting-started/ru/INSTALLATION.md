# Руководство по установке

Полная инструкция по установке CodeGraph.

## Содержание

- [Системные требования](#sistemnye-trebovaniya)
- [Аппаратные требования](#apparatnye-trebovaniya)
- [Программное обеспечение](#programmnoe-obespechenie)
- [Шаг 1: Настройка окружения](#shag-1-nastroyka-okruzheniya)
- [Шаг 2: Настройка базы данных PostgreSQL](#shag-2-nastroyka-bazy-dannyh-postgresql)
- [Установка PostgreSQL](#ustanovka-postgresql)
- [Проверка установки PostgreSQL](#proverka-ustanovki-postgresql)
- [Настройка пароля базы данных](#nastroyka-parolya-bazy-dannyh)
- [Шаг 3: Инициализация базы данных](#shag-3-initsializatsiya-bazy-dannyh)
- [Проверка базы данных](#proverka-bazy-dannyh)
- [Шаг 4: Создание администратора](#shag-4-sozdanie-administratora)
- [Шаг 5: Настройка поставщика LLM (опционально)](#shag-5-nastroyka-postavschika-llm-optsionalno)
- [Вариант A: GigaChat (рекомендуется для России)](#variant-a-gigachat-rekomenduetsya-dlya-rossii)
- [Вариант B: Локальная LLM (llama-cpp-python)](#variant-b-lokalnaya-llm-llama-cpp-python)
- [Вариант C: OpenAI API](#variant-c-openai-api)
- [Шаг 6: Запуск сервера API](#shag-6-zapusk-servera-api)
- [Шаг 7: Проверка установки](#shag-7-proverka-ustanovki)
- [Доступ к документации API](#dostup-k-dokumentatsii-api)
- [Проверка работоспособности (health endpoint)](#proverka-rabotosposobnosti-health-endpoint)
- [Проверка аутентификации](#proverka-autentifikatsii)
- [Проверка защищённого эндпоинта](#proverka-zaschischyonnogo-endpointa)
- [Шаг 8: Настройка данных CPG](#shag-8-nastroyka-dannyh-cpg)
- [Устранение неполадок](#ustranenie-nepoladok)
- [Не удалось подключиться к PostgreSQL](#ne-udalos-podklyuchitsya-k-postgresql)
- [Ошибка аутентификации по паролю](#oshibka-autentifikatsii-po-parolyu)
- [База данных не существует](#baza-dannyh-ne-suschestvuet)
- [Порт 8000 уже используется](#port-8000-uzhe-ispolzuetsya)
- [CUDA не найдена (для локальной LLM)](#cuda-ne-naydena-dlya-lokalnoy-llm)
- [Нехватка памяти](#nehvatka-pamyati)
- [Дальнейшие шаги](#dalneyshie-shagi)

## Системные требования

### Аппаратные требования

- **Процессор**: рекомендуется 8 и более ядер
- **Оперативная память**: минимум 16 ГБ (32 ГБ и более для крупных кодовых баз с локальной языковой моделью)
- **Видеокарта**: NVIDIA RTX 3090 или выше (опционально, для локальной языковой модели)
- **Место на диске**: 50 ГБ свободного места

### Программное обеспечение

- Windows 10/11 или Linux
- Python 3.10+ (рекомендуется 3.11)
- PostgreSQL 15+ (требуется для сервера API)
- Git
- CUDA Toolkit 11.8+ (опционально, для ускорения локальной языковой модели с помощью GPU)

## Шаг 1: Настройка окружения

```
# Клонировать репозиторий
git clone <адрес-репозитория>
cd codegraph

# Создать окружение conda (рекомендуется)
conda create -n codegraph python=3.11
conda activate codegraph

# ИЛИ создать виртуальное окружение venv
python -m venv venv
source venv/bin/activate  # В Windows: venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt
```

## Шаг 2: Настройка базы данных PostgreSQL

### Установка PostgreSQL

**Windows:**

```
# Скачайте и установите PostgreSQL 17 по адресу:
# https://www.postgresql.org/download/windows/

# Или используйте Chocolatey:
choco install postgresql
```

**Linux:**

```
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# Fedora/RHEL
sudo dnf install postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

### Проверка установки PostgreSQL

```
# Проверьте, запущен ли PostgreSQL
# Windows (PowerShell):
Get-Service postgresql*

# Linux:
sudo systemctl status postgresql
```

### Настройка пароля базы данных

Задайте пароль для пользователя postgres:

```
# Linux:
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'your_password';"

# Windows:
# Запустите psql от имени пользователя postgres и выполните:
# ALTER USER postgres PASSWORD 'your_password';
```

**Важно:** Запомните этот пароль — он понадобится вам для формирования строки DATABASE_URL.

## Шаг 3: Инициализация базы данных

Установите строку подключения к базе данных в качестве переменной окружения:

```
# Замените 'your_password' на реальный пароль от PostgreSQL
export DATABASE_URL="postgresql+asyncpg://postgres:your_password@localhost:5432/codegraph"

# Windows PowerShell:
$env:DATABASE_URL="postgresql+asyncpg://postgres:your_password@localhost:5432/codegraph"
```

Инициализируйте базу данных с помощью CLI проекта:

```
# Создание базы данных и выполнение миграций
python -m src.api.cli init-db
```

Эта команда выполнит следующее:
1. Создаст базу данных `codegraph`
2. Запустит миграции Alembic для создания всех таблиц
3. Инициализирует схему базы данных

### Проверка базы данных

```
# Проверьте, что таблицы были созданы
# Windows:
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -d codegraph -c "\dt"

# Linux:
psql -U postgres -d codegraph -c "\dt"
```

Ожидаемые таблицы:
- users
- api_keys
- sessions
- dialogue_turns
- audit_log
- background_jobs
- token_blacklist

## Шаг 4: Создание администратора

```
# Создание пользователя-администратора с именем и паролем
python -m src.api.cli create-admin --username admin --password <ваш_пароль_администратора>

# При необходимости можно добавить электронную почту
python -m src.api.cli create-admin --username admin --password <пароль> --email admin@example.com
```

Сохраните учетные данные администратора — они понадобятся для доступа к API.

## Шаг 5: Настройка поставщика LLM (необязательно)

Сервер API может работать без настроенного поставщика LLM (для тестирования). Настройте поставщика LLM для полной функциональности:

### Вариант A: GigaChat (рекомендуется для России)

```
# Установите переменную окружения
export GIGACHAT_AUTH_KEY="ваш_ключ_аутентификации"

# Обновите config.yaml
# llm:
#   provider: gigachat
```

Подробности см. в разделе [Интеграция GigaChat](../integrations/GIGACHAT.md).

### Вариант B: Локальная LLM (llama-cpp-python)

```
# Установите llama-cpp-python с поддержкой CUDA
CMAKE_ARGS="-DLLAMA_CUDA=on" pip install llama-cpp-python

# Скачайте модель (рекомендуется Qwen3-Coder-30B)
# Поместите в: ~/.lmstudio/models/

# Обновите config.yaml
# llm:
#   provider: local
#   model_path: путь/к/модели.gguf
```

### Вариант C: OpenAI API

```
export OPENAI_API_KEY="ваш_api_ключ"

# Обновите config.yaml
# llm:
#   provider: openai
#   model: gpt-4
```

## Шаг 6: Запуск сервера API

```
# Установите URL базы данных (если ещё не установлен)
export DATABASE_URL="postgresql+asyncpg://postgres:your_password@localhost:5432/codegraph"

# Запуск сервера
python -m src.api.cli run --host 127.0.0.1 --port 8000

# Для разработки с автоматической перезагрузкой:
python -m src.api.cli run --host 127.0.0.1 --port 8000 --reload
```

Сервер запустится по адресу http://127.0.0.1:8000

## Шаг 7: Проверка установки

### Доступ к документации API

Откройте браузер и перейдите по следующим ссылкам:
- **Swagger UI**: http://127.0.0.1:8000/api/docs
- **ReDoc**: http://127.0.0.1:8000/api/redoc

### Проверка эндпоинта работоспособности

```
curl http://127.0.0.1:8000/api/v1/health
```

Ожидаемый ответ:

```
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "database": {
      "status": "healthy",
      "database": "postgresql",
      "version": "PostgreSQL 17.x ..."
    }
  }
}
```

### Проверка аутентификации

```
# Получение токена доступа
curl -X POST http://127.0.0.1:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_admin_password"}'
```

Ожидаемый ответ:

```
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Проверка защищённого эндпоинта

```
# Замените TOKEN на полученный ранее access_token
curl http://127.0.0.1:8000/api/v1/scenarios \
  -H "Authorization: Bearer TOKEN"
```

## Шаг 8: Настройка данных CPG

CodeGraph использует предварительно экспортированные данные CPG, хранящиеся в DuckDB. Если у вас есть данные CPG:

```
# Поместите вашу базу данных CPG в каталог проекта
cp /путь/к/cpg.duckdb ./cpg.duckdb

# Обновите config.yaml с указанием пути
# cpg:
#   db_path: cpg.duckdb
```

Чтобы создать новые экспортные файлы CPG из исходного кода, см. [Руководство по экспорту CPG](../guides/CPG_EXPORT.md).

> **Примечание:** Для обычной работы Joern больше не требуется. Данные CPG предварительно экспортируются в формат DuckDB.
>
> Для устаревшей интеграции с Joern см. [Руководство по устаревшему Joern](../archive/JOERN_LEGACY.md).

## Устранение неполадок

### Не удалось подключиться к PostgreSQL

**Ошибка:** `connection to server at "localhost" failed`

**Решение:**

```
# Проверьте, запущен ли PostgreSQL
# Windows:
Get-Service postgresql*

# Linux:
sudo systemctl status postgresql

# Запустите, если не запущен
sudo systemctl start postgresql
```

### Ошибка аутентификации по паролю

**Ошибка:** `password authentication failed for user "postgres"`

**Решение:**

```
# Сбросьте пароль пользователя postgres
# Linux:
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'new_password';"

# Обновите DATABASE_URL с новым паролем
export DATABASE_URL="postgresql+asyncpg://postgres:new_password@localhost:5432/codegraph"
```

### База данных не существует

**Ошибка:** `database "codegraph" does not exist`

**Решение:**

```
# Вручную создайте базу данных
psql -U postgres -c "CREATE DATABASE codegraph ENCODING 'UTF8';"

# Затем снова выполните init-db
python -m src.api.cli init-db
```

### Порт 8000 уже используется

**Ошибка:** `error while attempting to bind on address ('127.0.0.1', 8000)`

**Решение:**

```
# Найдите процесс, использующий порт 8000
# Windows:
netstat -ano | findstr :8000

# Завершите процесс (замените PID на реальный идентификатор процесса)
taskkill /F /PID <PID>

# Linux:
lsof -ti:8000 | xargs kill -9

# Или используйте другой порт
python -m src.api.cli run --host 127.0.0.1 --port 8001
```

### CUDA не найдена (для локальной LLM)

**Ошибка:** `CUDA not available`

**Решение:**

```
# Проверьте установку CUDA
nvcc --version
nvidia-smi

# Переустановите PyTorch с поддержкой CUDA
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### Недостаточно памяти

Для систем с ограниченным объёмом ОЗУ:

```
# Уменьшите параметры в config.yaml
retrieval:
  batch_size: 50  # Было 100
  top_k: 5        # Было 10
```

## Дальнейшие шаги

- [Конфигурация](CONFIGURATION.md) — Настройка параметров API, аутентификации и провайдеров
- [Краткое руководство](README.md) — Начало работы с типовыми сценариями использования
- [Руководство пользователя TUI](../guides/TUI_USER_GUIDE.md) — Изучение работы с системой
- [Справочник API](../api/REST_API.md) — Обзор конечных точек API
- [Устранение неполадок](../guides/TROUBLESHOOTING.md) — Распространённые проблемы и их решения
