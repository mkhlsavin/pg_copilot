# Documentation Builder

Система сборки двуязычной HTML-документации из Markdown с автоматическим переводом через LLM.

## Возможности

- Конвертация Markdown → HTML с сохранением стилей landing page
- Автоматический перевод EN → RU через YandexGPT/GigaChat
- Кэширование переводов для ускорения повторных сборок
- Валидация внутренних ссылок
- Генерация навигации и индексных страниц
- Поддержка тёмной/светлой темы
- Responsive дизайн

## Быстрый старт

```bash
# Полная сборка с переводом (по умолчанию)
python scripts/build_docs.py

# Сборка без перевода (только EN)
python scripts/build_docs.py --no-translate

# Сборка с переводом через YandexGPT
python scripts/build_docs.py --provider yandex

# Тестовая сборка с mock переводчиком
python scripts/build_docs.py --mock

# Только валидация ссылок
python scripts/build_docs.py --validate

# Проверить статус переводов
python scripts/build_docs.py --check-status

# Принудительно пересоздать переводы (игнорируя существующие RU файлы)
python scripts/build_docs.py --force-translate
```

## Установка зависимостей

```bash
pip install markdown pygments tqdm
```

Для перевода также требуется `openai` (используется YandexGPT через OpenAI-совместимый API):
```bash
pip install openai
```

## CLI опции

| Опция | Описание |
|-------|----------|
| `--translate` | Включить перевод (по умолчанию) |
| `--no-translate` | Отключить перевод, собрать только EN |
| `--provider {yandex,gigachat,openai}` | Выбор LLM провайдера |
| `--mock` | Использовать mock переводчик (для тестов) |
| `--validate` | Только валидация ссылок в существующем выводе |
| `--check-status` | Показать сводку по статусу переводов и выйти |
| `--force-translate` | Принудительно пересоздать все переводы (игнорировать существующие RU) |
| `-v, --verbose` | Подробный вывод |

## Структура проекта

```
scripts/
├── build_docs.py              # Главный скрипт-оркестратор
└── docs_builder/
    ├── __init__.py
    ├── config.py              # Константы и настройки
    ├── discovery.py           # Поиск MD файлов
    ├── translator.py          # LLM перевод с кэшированием
    ├── converter.py           # Markdown → HTML
    ├── template.py            # HTML шаблон
    ├── linker.py              # Валидация ссылок
    └── navigation.py          # Генерация навигации
```

## Входные данные

Скрипт обрабатывает следующие папки из `docs/`:

| Папка | Описание |
|-------|----------|
| `getting-started/` | Начало работы (установка, конфигурация) |
| `guides/` | Руководства пользователя |
| `api/` | API документация (REST, WebSocket) |
| `integrations/` | Интеграции (GigaChat, YandexGPT) |
| `reference/` | Техническая справка |
| `enterprise/` | Enterprise функции (уже двуязычная) |

## Выходные данные

```
docs/landing/docs/
├── en/
│   ├── index.html                    # Главный индекс EN
│   ├── getting-started/
│   │   ├── index.html                # Индекс секции
│   │   ├── INSTALLATION.html
│   │   └── CONFIGURATION.html
│   ├── guides/
│   ├── api/
│   ├── integrations/
│   ├── reference/
│   └── enterprise/
└── ru/
    └── (зеркальная структура)
```

## Конфигурация перевода

### Переменные окружения

Для YandexGPT:
```bash
export YANDEX_API_KEY="your-api-key"
export YANDEX_FOLDER_ID="your-folder-id"
```

Для GigaChat:
```bash
export GIGACHAT_CREDENTIALS="your-credentials"
```

### Кэширование

Переводы кэшируются в `.doc_translation_cache/`:
- Каждый перевод сохраняется по хэшу оригинала
- При повторной сборке используется кэш
- Для принудительного перевода используйте `--force-translate` или удалите папку кэша

## Модули

### config.py

Содержит константы:
- `SOURCE_FOLDERS` — список обрабатываемых папок
- `BILINGUAL_FOLDERS` — папки с двуязычной структурой (en/ и ru/ подпапки)
- `OUTPUT_EN`, `OUTPUT_RU` — пути вывода
- `DOC_SECTIONS` — метаданные секций (названия EN/RU)
- `UI_STRINGS` — переводы UI элементов (навигация, footer, prev/next)
- `FILE_ORDER` — порядок файлов в навигации по секциям

### discovery.py

```python
from scripts.docs_builder.discovery import (
    discover_docs,
    find_missing_translations,
    check_translation_status,
    print_translation_summary,
    extract_title,
)

# Найти все MD файлы
docs = discover_docs()

# Найти файлы без русского перевода
missing = find_missing_translations(docs)

# Проверить статус перевода конкретного файла
status = check_translation_status(docs_root, folder, filename)
# status.ru_exists - существует ли RU файл
# status.use_existing_ru - RU файл новее EN (использовать существующий)

# Вывести сводку по переводам
print_translation_summary()

# Извлечь заголовок из Markdown
title = extract_title(content)
```

### translator.py

```python
from scripts.docs_builder.translator import create_translator

# Создать переводчик
translator = create_translator(provider='yandex', use_cache=True)

# Перевести контент
ru_content = translator.translate(en_content)

# Статистика
print(translator.get_stats())
# {'translated': 10, 'cached': 5, 'errors': 0}
```

### converter.py

```python
from scripts.docs_builder.converter import (
    convert_markdown_to_html,
    transform_links,
    strip_frontmatter
)

# Преобразовать ссылки .md → .html
content = transform_links(md_content)

# Удалить YAML frontmatter
content = strip_frontmatter(content)

# Конвертировать в HTML
result = convert_markdown_to_html(content)
print(result.html)      # HTML контент
print(result.toc)       # Оглавление
print(result.title)     # Заголовок
print(result.headings)  # Список заголовков
```

### template.py

```python
from scripts.docs_builder.template import HTMLGenerator

# Создать генератор для русского языка
gen = HTMLGenerator(lang='ru')

# Сгенерировать страницу
html = gen.generate(
    title="Установка",
    content=html_content,
    relative_path="getting-started/INSTALLATION",
    section_id="getting-started",
    headings=headings,
    sidebar_html=sidebar,
)
```

### linker.py

```python
from scripts.docs_builder.linker import LinkValidator

# Создать валидатор
validator = LinkValidator(output_dir)

# Валидировать все файлы
result = validator.validate_all()

print(f"Всего ссылок: {result.total_links}")
print(f"Битых ссылок: {len(result.broken_links)}")

# Получить отчёт
print(validator.get_report())
```

### navigation.py

```python
from scripts.docs_builder.navigation import (
    generate_sidebar_html,
    generate_index_page,
    generate_section_index
)

# Сгенерировать sidebar
sidebar = generate_sidebar_html(
    sections=DOC_SECTIONS,
    files_by_section=files_dict,
    current_path="guides/CLI_GUIDE.html",
    lang="ru"
)

# Сгенерировать главный индекс
index = generate_index_page(lang="en", sections=DOC_SECTIONS, files_by_section=files_dict)
```

## HTML шаблон

Страницы генерируются на основе стилей `docs/landing/whitepaper.html`:

- CSS переменные из `docs/landing/css/styles.css`
- JavaScript из `docs/landing/js/main.js`
- SVG ассеты из `docs/landing/assets/svg/`

### Ключевые CSS классы

| Класс | Описание |
|-------|----------|
| `.doc-layout` | Flexbox контейнер (sidebar + main) |
| `.doc-sidebar` | Боковая навигация (sticky) |
| `.doc-main` | Основной контент (max-width: 900px) |
| `.doc-hero` | Заголовок страницы с градиентом |
| `.doc-content` | Контент статьи |
| `.doc-toc` | Оглавление страницы (sticky) |

### Responsive breakpoints

- `1200px` — скрывается TOC
- `1024px` — скрывается sidebar

## Примеры использования

### Добавить новую секцию

1. Создайте папку в `docs/`:
```bash
mkdir docs/tutorials
```

2. Добавьте секцию в `config.py`:
```python
DOC_SECTIONS.append({
    "id": "tutorials",
    "title_en": "Tutorials",
    "title_ru": "Обучение",
    "order": 7,
    "icon": "icon-docs.svg",
})

SOURCE_FOLDERS.append("tutorials")
```

3. Запустите сборку:
```bash
python scripts/build_docs.py
```

### Кастомизация перевода

Отредактируйте промпт в `translator.py`:

```python
TRANSLATION_SYSTEM_PROMPT = """
Your translation guidelines here...
"""
```

### Добавить валидацию внешних ссылок

```python
# В linker.py, метод validate_file():
if link_type == 'external':
    import requests
    try:
        response = requests.head(url, timeout=5)
        is_valid = response.status_code < 400
    except:
        is_valid = False
```

## CI/CD интеграция

### GitHub Actions

```yaml
# .github/workflows/docs.yml
name: Build Documentation

on:
  push:
    paths:
      - 'docs/**/*.md'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install markdown pygments tqdm openai

      - name: Build docs
        env:
          YANDEX_API_KEY: ${{ secrets.YANDEX_API_KEY }}
          YANDEX_FOLDER_ID: ${{ secrets.YANDEX_FOLDER_ID }}
        run: python scripts/build_docs.py --provider yandex

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: documentation
          path: docs/landing/docs/
```

## Troubleshooting

### Ошибка "markdown library not installed"

```bash
pip install markdown pygments
```

### Ошибка перевода "API key not found"

Проверьте переменные окружения:
```bash
echo $YANDEX_API_KEY
echo $YANDEX_FOLDER_ID
```

### Много битых ссылок

Большинство "broken links" — это ссылки на landing page (`../index.html`), которые выходят за пределы папки docs/. Они работают корректно в браузере.

### Очистка кэша переводов

```bash
# Использовать флаг для игнорирования кэша
python scripts/build_docs.py --force-translate

# Или удалить папку кэша полностью
rm -rf .doc_translation_cache/
```

## Лицензия

Часть проекта CodeGraph.
