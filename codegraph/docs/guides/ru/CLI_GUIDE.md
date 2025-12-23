# Руководство по CLI

Полная документация по интерфейсу командной строки для CodeGraph.

---

## Содержание

- [Краткий справочник](#quick-reference)
- [CLI codegraph](#codegraph-cli)
- [Команда импорта](#import-command)
- [Управление проектами](#projects-management)
- [Управление сервером](#server-management)
- [Команды в один шаг](#single-step-commands)
- [CLI API-сервера](#api-server-cli)
- [CLI security-audit](#security-audit-cli)
- [Полит аудит](#full-audit)
- [Быстрое сканирование](#quick-scan)
- [Сканирование настроек](#settings-scan)
- [Сканирование секретов](#secrets-scan)
- [CLI patch-review](#patch-review-cli)
- [Команда analyze](#analyze-command)
- [Просмотр diff](#diff-review)
- [Просмотр PR в GitHub](#github-pr-review)
- [Просмотр MR в GitLab](#gitlab-mr-review)
- [Инструменты тестирования и анализа](#benchmark--analysis-tools)
- [Переменные окружения](#environment-variables)
- [Коды завершения](#exit-codes)
- [Интеграция с CI/CD](#cicd-integration)
- [Устранение неполадок](#troubleshooting)

---

## Краткий справочник

| Инструмент | Назначение | Типичное использование |
| --- | --- | --- |
| python -m src.api.cli run | Запуск сервера REST API | Сервер для разработки и производства |
| codegraph import | Импорт проекта в CPG | Клонирование репозитория + создание CPG |
| codegraph projects | Управление импортированными проектами | Список, активация, удаление проектов |
| security-audit full | Аудит безопасности | Сканирование проекта на уязвимости |
| patch-review analyze | Проверка кода | Анализ кодовой базы на наличие проблем |
| patch-review github | Проверка PR | Анализ pull request’ов в GitHub |

---

## CLI codegraph

Основной интерфейс командной строки для импорта проектов и управления системой CodeGraph.

### Установка

```
# Из директории codegraph
pip install -e .

# Или запуск напрямую
python -m src.cli.import_commands [команда] [опции]
```

### Команда импорта

Импорт проекта из репозитория Git или локального пути.

```
codegraph import [опции]
```

**Опции:**

| Опция | Описание | По умолчанию |
| --- | --- | --- |
| --repo | URL Git-репозитория | - |
| --path | Локальный путь к исходному коду | - |
| --language | Язык программирования (автоопределение, если не указан) | авто |
| --branch | Ветка Git для клонирования | main |
| --shallow | Использовать неглубокое клонирование | true |
| --include | Включаемые пути (несколько значений) | все |
| --exclude | Исключаемые пути (несколько значений) | нет |
| --mode | Режим импорта:full,selective,incremental | full |
| --workspace | Путь к рабочей области Joern | авто |
| --domain-name | Пользовательское доменное имя | авто |
| --group | Имя группы проекта | default |
| --memory | Объём памяти Joern в ГБ | 16 |
| --batch-size | Размер пакета DuckDB | 10000 |
| --docker | Использовать Docker для Joern | false |
| --no-docs | Пропустить импорт документации | false |
| --no-plugin | Пропустить создание плагина домена | false |

**Примеры:**

```
# Импорт из GitHub
codegraph import --repo https://github.com/postgres/postgres --branch REL_17_STABLE

# Импорт локального кода с использованием Docker
codegraph import --path ./myproject --docker

# Импорт с указанием языка
codegraph import --repo https://github.com/org/repo --language python

# Выборочный импорт (только указанные пути)
codegraph import --path ./code --mode selective --include src/core src/api

# Импорт в определённую группу
codegraph import --repo https://github.com/org/repo --group security-team
```

### Управление проектами

Управление импортированными проектами.

```
codegraph projects [подкоманда] [опции]
```

#### Список проектов

```
codegraph projects list [опции]
```

| Опция | Описание |
| --- | --- |
| --group | Фильтрация по имени группы |
| --language | Фильтрация по языку |
| --active | Показывать только активные проекты |

**Примеры:**

```
# Список всех проектов
codegraph projects list

# Список проектов в группе
codegraph projects list --group security-team

# Показать только активные проекты
codegraph projects list --active
```

#### Активация проекта

```
codegraph projects activate <имя> [--group <группа>]
```

#### Удаление проекта

```
codegraph projects delete <имя> [опции]
```

| Опция | Описание |
| --- | --- |
| --group | Имя группы проекта |
| --delete-files | Также удалить файлы CPG и DuckDB |

#### Информация о проекте

```
codegraph projects info <имя> [--group <группа>]
```

### Управление сервером

Управление сервером Joern.

```
codegraph server [подкоманда] [опции]
```

**Подкоманды:**

```
# Проверка состояния сервера
codegraph server status

# Запуск сервера
codegraph server start [--docker] [--memory 16]

# Остановка сервера
codegraph server stop

# Перезапуск сервера
codegraph server restart [--docker]
```

### Команды пошагового выполнения

Выполнение отдельных шагов конвейера.

```
# Клонирование репозитория
codegraph clone --repo <url> [--branch main] [--shallow] [--depth 1] [--output dir]

# Определение языка программирования
codegraph detect --path <путь_к_исходникам>

# Создание CPG для Joern
codegraph cpg --path <путь_к_исходникам> [--language c] [--output cpg.bin] [--docker]

# Экспорт CPG в DuckDB
codegraph export --cpg <путь_cpg> [--output db.duckdb]

# Проверка экспорта
codegraph validate --db <путь_duckdb>

# Список поддерживаемых языков
codegraph languages
```

**Поддерживаемые языки:**

| Язык | Команда Joern | Расширения |
| --- | --- | --- |
| c | c2cpg | .c, .h |
| cpp | c2cpg | .cpp, .hpp, .cc, .cxx |
| python | pysrc2cpg | .py |
| java | javasrc2cpg | .java |
| go | gosrc2cpg | .go |
| javascript | jssrc2cpg | .js, .jsx, .ts, .tsx |
| php | php2cpg | .php |

---

## CLI-сервера API

**Модуль:** `src.api.cli`

```
python -m src.api.cli <команда> [опции]
```

### run— Запуск сервера API

```
python -m src.api.cli run [опции]
```

| Опция | По умолчанию | Описание |
| --- | --- | --- |
| --host | 0.0.0.0 | IP-адрес, к которому привязываться |
| --port | 8000 | Порт для прослушивания |
| --workers | 1 | Количество процессов-воркеров uvicorn |
| --reload | false | Включить автоматическую перезагрузку (для разработки) |
| --log-level | info | Уровень логирования (debug, info, warning, error) |

**Примеры:**

```
# Запуск сервера с параметрами по умолчанию
python -m src.api.cli run

# Режим разработки с автоперезагрузкой
python -m src.api.cli run --reload --log-level debug

# Работа в продакшене с несколькими воркерами
python -m src.api.cli run --host 0.0.0.0 --port 8080 --workers 4
```

### init-db— Инициализация базы данных

```
python -m src.api.cli init-db
```

### migrate— Выполнить миграции

```
python -m src.api.cli migrate [--revision REVISION]
```

### create-admin— Создать администратора

```
python -m src.api.cli create-admin --username ИМЯ_ПОЛЬЗОВАТЕЛЯ --password ПАРОЛЬ [--email EMAIL]
```

## CLI security-audit

Консольная утилита для сканирования безопасности проектов на Python/Django.

**Модуль:** `src.cli.security_audit`

```
python -m src.cli.security_audit <команда> [опции]
```

### Полит аудит

Запуск полного аудита безопасности с поддержкой нескольких форматов вывода.

```
security-audit full --path <путь_к_проекту> [опции]
```

| Опция | Короткая | Описание | По умолчанию |
| --- | --- | --- | --- |
| --path | -p | Путь к проекту для аудита | обязательно |
| --output | -o | Директория для сохранения отчётов | ./security_reports |
| --format | -f | Формат(ы) вывода: json, markdown, sarif, all | json markdown sarif |
| --exclude-dirs |  | Дополнительные директории для исключения | нет |
| --no-cpg |  | Пропустить анализ на основе CPG (быстрее) | false |
| --verbose | -v | Подробный вывод | false |

**Примеры:**

```
# Полный аудит со всеми форматами
security-audit full --path ./myproject

# Только JSON-вывод
security-audit full --path ./myproject --format json

# Исключение директорий
security-audit full --path ./myproject --exclude-dirs vendor third_party

# Быстрое сканирование по файлам (без CPG)
security-audit full --path ./myproject --no-cpg
```

**Вывод:**

Аудит генерирует отчёты в указанной директории:
- `security_audit_YYYYMMDD_HHMMSS.json`
- `security_audit_YYYYMMDD_HHMMSS.md`
- `security_audit_YYYYMMDD_HHMMSS.sarif`

### Быстрое сканирование

Быстрое сканирование по файлам без полного анализа CPG.

```
security-audit quick --path <путь_к_проекту> [--output <файл>]
```

### Сканирование настроек

Проверка файла настроек Django на наличие проблем безопасности.

```
security-audit settings --path <путь_к_настройкам>
```

**Проверки:**
- DEBUG = True в продакшене
- Слабый SECRET_KEY
- Настройка ALLOWED_HOSTS
- CSRF_COOKIE_SECURE
- SESSION_COOKIE_SECURE
- SECURE_SSL_REDIRECT
- Жёстко прописанные учётные данные базы данных

### Сканирование секретов

Поиск жёстко прописанных секретов и учётных данных.

```
security-audit secrets --path <путь_к_проекту>
```

**Обнаруживает:**
- Ключи API (AWS, GCP, Azure, GitHub и др.)
- Приватные ключи (RSA, SSH)
- Строки подключения к базам данных
- Секреты JWT
- Токены OAuth
- Общие пароли в коде

### Уровни серьёзности уязвимостей

| Серьёзность | Иконка | Описание |
| --- | --- | --- |
| Критическая | [X] | Требует немедленных действий |
| Высокая | [!] | Необходимо устранить до развёртывания |
| Средняя | [~] | Должна быть исправлена |
| Низкая | [o] | Незначительные проблемы |
| Информационная | [i] | Информационные сведения |

### Исключённые директории (по умолчанию)

Сканер автоматически исключает:
- `__pycache__`, `.git`
- `.venv`, `venv`, `env`
- `node_modules`
- `.tox`, `.pytest_cache`, `.mypy_cache`
- `migrations`
- `static`, `media`
- `dist`, `build`

---

## patch-review CLI

Автоматический анализ кода с использованием анализа Code Property Graph (CPG).

**Модуль:** `src.patch_review.cli`

```
python -m src.patch_review.cli [команда] [опции]
```

### Команда Analyze

Запускает анализ безопасности и неиспользуемого кода для всей кодовой базы.

```
patch-review analyze [опции]
```

| Опция | Короткая | Описание | По умолчанию |
| --- | --- | --- | --- |
| --type | -t | Тип анализа:security,dead-code,all | all |
| --severity | -s | Минимальный уровень серьёзности:critical,high,medium,low,all | all |
| --patterns | -p | Список ID шаблонов через запятую для проверки | все шаблоны |
| --limit | -l | Максимум найденных уязвимостей на шаблон | 50 |

**Примеры:**

```
# Полный анализ (безопасность + неиспользуемый код)
patch-review analyze --db cpg.duckdb

# Только безопасность, критическая серьёзность
patch-review analyze --type security --severity critical

# Конкретные шаблоны
patch-review analyze --patterns SQL_INJECTION,BUFFER_OVERFLOW,DEAD_CODE
```

### Просмотр изменений (Diff Review)

Анализ изменений из файла в формате unified diff.

```
patch-review diff [файл] [опции]
```

| Опция | Описание |
| --- | --- |
| file | Путь к файлу diff (или-для stdin) |
| --dead-code | Включить анализ неиспользуемого кода |
| --security-only | Выполнять только анализ безопасности |

**Примеры:**

```
# Просмотр файла diff
patch-review diff changes.diff

# Чтение из stdin
git diff | patch-review diff -

# С анализом неиспользуемого кода
patch-review diff changes.diff --dead-code
```

### Просмотр GitHub PR

Получение и анализ Pull Request из GitHub.

```
patch-review github <номер_pr> [опции]
```

| Опция | Описание |
| --- | --- |
| --owner | Владелец репозитория (или переменная окруженияGITHUB_OWNER) |
| --repo | Название репозитория (или переменная окруженияGITHUB_REPO) |
| --token | Токен GitHub (или переменная окруженияGITHUB_TOKEN) |
| --post-review | Опубликовать комментарии анализа в PR |
| --dead-code | Включить анализ неиспользуемого кода |

**Пример:**

```
patch-review github 123 --owner myorg --repo myrepo --token $GITHUB_TOKEN --post-review
```

### Просмотр GitLab MR

Получение и анализ Merge Request из GitLab.

```
patch-review gitlab <mr_iid> [опции]
```

| Опция | Описание |
| --- | --- |
| --project | ID или путь проекта (или переменная окруженияGITLAB_PROJECT_ID) |
| --token | Токен GitLab (или переменная окруженияGITLAB_TOKEN) |
| --post-review | Опубликовать комментарии анализа в MR |

### Глобальные опции

| Опция | Короткая | Описание | По умолчанию |
| --- | --- | --- | --- |
| --db | -d | Путь к базе данных DuckDB CPG | cpg.duckdb |
| --output | -o | Формат вывода:json,markdown,summary,score | markdown |
| --output-file | -f | Записать результат в файл | stdout |
| --verbose | -v | Включить подробное логирование | false |
| --quiet | -q | Выводить только результат, без служебных сообщений | false |
| --security-threshold |  | Минимальный балл безопасности для прохождения | 60.0 |
| --block-on-critical |  | Блокировать, если найдены критические уязвимости | true |

---

## Инструменты тестирования и анализа

### demo_benchmark.py

Демонстрирует работу тестовой платформы на примере синтетических результатов поиска.

```
python examples/demo_benchmark.py
```

**Возможности:**
- Имитация векторного, графового и гибридного поиска
- Демонстрация метрик P@K, R@K, F1@K, MRR, NDCG
- Воспроизводимость результатов благодаря фиксированному seed’у генератора случайных чисел

### demo_patch_review.py

Демонстрирует конвейер автоматического анализа изменений (патчей).

```
python examples/demo_patch_review.py [--db cpg.duckdb]
```

**Выходные файлы:**
- `demo_review_output.json` — структурированные результаты анализа
- `demo_review_output.md` — отчёт в формате Markdown

### tests/benchmark/run_benchmark.py

Полноценный запуск тестирования для множества сценариев.

```
python tests/benchmark/run_benchmark.py [ОПЦИИ]
```

| Аргумент | Описание |
| --- | --- |
| --quick | Быстрое тестирование (подмножество запросов) |
| --scenario N | Запуск конкретного сценария (1–17) |
| --all-scenarios | Запуск всех 17 сценариев |
| --output DIR | Каталог для сохранения результатов |

---

## Переменные окружения

| Переменная | Описание | Используется |
| --- | --- | --- |
| DATABASE_URL | URL подключения к PostgreSQL | сервер API |
| GIGACHAT_CREDENTIALS | Учётные данные для API GigaChat | поставщик LLM |
| OPENAI_API_KEY | Ключ API OpenAI | поставщик LLM |
| JOERN_HOME | Каталог установки Joern | инструменты импорта |
| JOERN_SERVER_HOST | Хост сервера Joern | codegraph |
| JOERN_SERVER_PORT | Порт сервера Joern | codegraph |
| DUCKDB_PATH | Путь к базе данных DuckDB | все инструменты |
| LOG_LEVEL | Уровень логирования по умолчанию | все инструменты |
| GITHUB_TOKEN | Токен API GitHub | patch-review |
| GITHUB_OWNER | Владелец репозитория по умолчанию | patch-review |
| GITHUB_REPO | Название репозитория по умолчанию | patch-review |
| GITLAB_TOKEN | Токен API GitLab | patch-review |
| GITLAB_PROJECT_ID | Идентификатор проекта GitLab по умолчанию | patch-review |

---

## Коды завершения

### codegraph

| Код | Значение |
| --- | --- |
| 0 | Команда успешно выполнена |
| 1 | Произошла ошибка |
| 2 | Недопустимые аргументы |

### security-audit

| Код | Значение |
| --- | --- |
| 0 | Аудит успешно завершён |
| 1 | Ошибка или критические проблемы |

### patch-review

| Код | Значение |
| --- | --- |
| 0 | Просмотр одобрен / Критические проблемы отсутствуют |
| 1 | Требуются изменения / Проблемы высокой серьёзности |
| 2 | Объединение заблокировано / Критические проблемы |

---

## Интеграция CI/CD

### GitHub Actions

```
name: Анализ безопасности
on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Настройка Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Установка зависимостей
        run: pip install -e .

      - name: Аудит безопасности
        run: |
          security-audit full --path . --format sarif --output ./reports

      - name: Загрузка SARIF
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: reports/security_audit_*.sarif

      - name: Проверка изменений
        if: github.event_name == 'pull_request'
        run: |
          patch-review analyze --type security --severity high --output json > analysis.json
          exit_code=$?
          if [ $exit_code -eq 2 ]; then
            echo "Обнаружены критические уязвимости!"
            exit 1
          fi
```

### GitLab CI

```
stages:
  - security

security_scan:
  stage: security
  script:
    - pip install -e .
    - security-audit full --path . --format json --output ./reports
    - patch-review analyze --type security --severity critical
  artifacts:
    reports:
      sast: reports/security_audit_*.json
  allow_failure: false
```

---

## Устранение неполадок

### Ошибка подключения к базе данных

```
# Проверьте, существует ли база данных и доступна ли для чтения
ls -la cpg.duckdb

# Попробуйте с указанием полного пути
patch-review analyze --db /полный/путь/до/cpg.duckdb
```

### Нет результатов

```
# Проверьте с подробным логированием
patch-review analyze --verbose

# Понизьте порог серьёзности
patch-review analyze --severity all
```

### Проблемы с сервером Joern

```
# Проверьте состояние сервера
codegraph server status

# Перезапустите с увеличением объёма памяти
codegraph server restart --memory 32
```

### Ошибки импорта

```
# Проверьте поддерживаемые языки
codegraph languages

# Попробуйте с использованием Docker
codegraph import --path ./code --docker

# Проверьте статус заданий импорта
codegraph jobs --status failed
```

## Смотрите также

- [Руководство по импорту проектов](./PROJECT_IMPORT.md) — Подробная документация по импорту
- [Руководство по экспорту CPG](./CPG_EXPORT.md) — Экспорт CPG в DuckDB
- [Справочник REST API](../api/REST_API.md) — Конечные точки API
- [Руководство пользователя TUI](./TUI_USER_GUIDE.md) — Интерактивный терминальный интерфейс
- [Документация по безопасности](../reference/SECURITY.md) — Функции безопасности
