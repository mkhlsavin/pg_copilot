# Руководство по экспорту CPG

В этом руководстве описывается создание и экспорт графов свойств кода (Code Property Graphs, CPG) в DuckDB для анализа с помощью CodeGraph.

> **Примечание:** Для обычной работы с CodeGraph использование Joern **не требуется**. Данные CPG, как правило, уже предварительно экспортированы в DuckDB.
>
> Это руководство предназначено для пользователей, которым необходимо создать новые экспортные файлы CPG из исходного кода.

## Содержание

- [Обзор](#obzor)
- [Предварительные требования](#predvaritelnye-trebovaniya)
- [Для создания новой CPG (опционально)](#dlya-sozdaniya-novoy-cpg-optsionalno)
- [Для использования существующих данных CPG](#dlya-ispolzovaniya-suschestvuyuschih-dannyh-cpg)
- [Опционально](#optsionalno)
- [Установка зависимостей](#ustanovka-zavisimostey)
- [Быстрый старт](#bystryy-start)
- [Экспорт через CLI (рекомендуется)](#eksport-cherez-cli-rekomenduetsya)
- [Python API](#python-api)
- [Справочник по CLI](#spravochnik-po-cli)
- [Параметры](#parametry)
- [Распространённые команды](#rasprostranyonnye-komandy)
- [Процесс экспорта](#protsess-eksporta)
- [Шаг 1: Инициализация схемы](#shag-1-initsializatsiya-shemy)
- [Шаг 2: Экспорт узлов](#shag-2-eksport-uzlov)
- [Шаг 3: Экспорт рёбер](#shag-3-eksport-ryober)
- [Шаг 4: Создание графа свойств](#shag-4-sozdanie-grafa-svoystv)
- [Шаг 5: Проверка](#shag-5-proverka)
- [Сохранение состояния / Возобновление](#sohranenie-sostoyaniya-vozobnovlenie)
- [Проверка прогресса](#proverka-progressa)
- [Состояния прогресса](#sostoyaniya-progressa)
- [Проверка](#proverka)
- [Автоматическая проверка](#avtomaticheskaya-proverka)
- [Ручная проверка](#ruchnaya-proverka)
- [Обработка отсутствующих данных](#obrabotka-otsutstvuyuschih-dannyh)
- [Инкрементальные обновления](#inkrementalnye-obnovleniya)
- [Производительность](#proizvoditelnost)
- [Векторные вложения](#vektornye-vlozheniya)
- [Справочник по схеме](#spravochnik-po-sheme)
- [Основные таблицы узлов](#osnovnye-tablitsy-uzlov)
- [Основные таблицы рёбер](#osnovnye-tablitsy-ryober)
- [Полная схема](#polnaya-shema)
- [Запросы к CPG](#zaprosy-k-cpg)
- [SQL-запросы](#sql-zaprosy)
- [Запросы к графу свойств (DuckPGQ)](#zaprosy-k-grafu-svoystv-duckpgq)
- [Python-клиент](#python-klient)
- [Устранение неполадок](#ustranenie-nepoladok)
- [Ошибки соединения](#oshibki-soedineniya)
- [Нехватка памяти](#nehvatka-pamyati)
- [Медленный экспорт](#medlennyy-eksport)
- [Отсутствующие узлы](#otsutstvuyuschie-uzly)
- [Рекомендации по производительности](#rekomendatsii-po-proizvoditelnosti)
- [См. также](#sm-takzhe)

## Обзор

Система экспорта CPG создаёт данные анализа кода в формате DuckDB, что позволяет:

- Выполнять **SQL-запросы** для обхода графа
- Осуществлять **семантический поиск** с использованием векторных вложений
- Проводить **анализ безопасности** с генерацией гипотез
- Выполнять **инкрементальные обновления** через интеграцию с git

**Основные возможности:**
- Полное соответствие спецификации CPG v1.1 (22 типа узлов, 20 типов рёбер)
- Поддержка контрольных точек и возобновления для больших кодовых баз
- Автоматическая валидация
- Создание графа свойств для выполнения графовых запросов

---

## Предварительные требования

### Для создания новой CPG (опционально)

- Установленный **Joern** (только если создание новой CPG из исходного кода)
- **DuckDB** 0.9.0 и выше
- **Python** 3.10 и выше

### Для использования существующих данных CPG

- **DuckDB** 0.9.0 и выше
- **Python** 3.10 и выше
- Предварительно экспортированный файл базы данных CPG (`.duckdb`)

### Опционально

- Расширение **DuckPGQ** для выполнения запросов к графу свойств
- Библиотека **sentence-transformers** для семантических встраиваний

### Установка зависимостей

```
pip install duckdb cpgqls-client sentence-transformers
```

## Быстрый старт

### Экспорт через CLI (рекомендуется)

```
# Полный экспорт с проверкой
python -m src.cpg_export.exporter \
    --endpoint localhost:8080 \
    --workspace myproject.cpg \
    --db cpg.duckdb

# Проверка статуса экспорта
python -m src.cpg_export.exporter --db cpg.duckdb --status

# Проверка существующей базы данных
python -m src.cpg_export.exporter --db cpg.duckdb --validate-only
```

### Python API {#python-api}

```
from src.cpg_export import JoernToDuckDBExporter

# Создание экспортера
exporter = JoernToDuckDBExporter(
    server_endpoint="localhost:8080",
    workspace="myproject.cpg",
    db_path="cpg.duckdb",
    batch_size=10000
)

# Полный экспорт с автоматической проверкой
results = exporter.export_full_cpg()

# Проверка результатов
print(f"Экспортировано узлов: {sum(results['node_stats'].values())}")
print(f"Экспортировано рёбер: {sum(results['edge_stats'].values())}")
```

---

## Справочник CLI

### Параметры

| Параметр | По умолчанию | Описание |
| --- | --- | --- |
| --endpoint | localhost:8080 | Конечная точка сервера Joern |
| --workspace | pg17_full.cpg | Имя рабочей области/CPG в Joern |
| --db | cpg.duckdb | Путь к выходному файлу DuckDB |
| --batch-size | 10000 | Количество записей в пакете (соотношение память/скорость) |
| --limit | Нет | Ограничение количества записей на тип (для тестирования) |
| --force | False | Удалить и повторно создать все таблицы |
| --no-resume | False | Отключить возобновление из контрольной точки |
| --skip-validation | False | Пропустить проверку в конце |
| --status | False | Показывать только ход экспорта |
| --validate-only | False | Запустить только проверку |

### Распространённые команды

```
# Возобновление прерванного экспорта
python -m src.cpg_export.exporter --db cpg.duckdb

# Принудительный полный экспорт (удаляет существующие данные)
python -m src.cpg_export.exporter --db cpg.duckdb --force

# Тестирование с ограниченным объёмом данных
python -m src.cpg_export.exporter --db cpg.duckdb --limit 1000

# Обработка большого кода с меньшими пакетами
python -m src.cpg_export.exporter --db cpg.duckdb --batch-size 5000
```

## Процесс экспорта

Экспортёр выполняет 5-ступенчатый конвейер:

### Шаг 1: Инициализация схемы

Создаёт таблицы для всех типов узлов и рёбер CPG. Таблицы создаются с использованием `IF NOT EXISTS`, чтобы сохранить существующие данные, если только не указан флаг `--force`.

### Шаг 2: Экспорт узлов

Экспортирует все узлы CPG по типам:

| Приоритет | Типы узлов |
| --- | --- |
| P0 (Основные) | METHOD, CALL, IDENTIFIER, LITERAL, LOCAL, PARAM, RETURN, BLOCK, CONTROL_STRUCTURE |
| P0 (Структура) | FILE, NAMESPACE, NAMESPACE_BLOCK, MEMBER, TYPE, TYPE_DECL |
| P1 | METHOD_PARAMETER_OUT, METHOD_RETURN, FIELD_IDENTIFIER, TYPE_ARGUMENT, TYPE_PARAMETER |
| P2 | JUMP_LABEL, JUMP_TARGET, METHOD_REF, MODIFIER, TYPE_REF, UNKNOWN |
| P3 | BINDING, ANNOTATION |

### Шаг 3: Экспорт рёбер

Экспортирует все рёбра CPG:

| Приоритет | Типы рёбер |
| --- | --- |
| P0 (Основные) | AST, CFG, CALL, REF, ARGUMENT, RECEIVER, CONDITION |
| P0 (Анализ) | REACHING_DEF, DOMINATE, POST_DOMINATE, CDG, CONTAINS |
| P1 | EVAL_TYPE, INHERITS_FROM, ALIAS_OF |
| P2 | BINDS_TO, PARAMETER_LINK, SOURCE_FILE |
| P3 | TAGGED_BY, BINDS |

### Шаг 4: Создание графа свойств

Создаётся граф свойств DuckDB с именем `cpg` для выполнения запросов с обходом графа:

```
-- Запрос с использованием графа свойств
FROM GRAPH_TABLE(cpg
    MATCH (m:METHOD)-[c:CALLS]->(callee:METHOD)
    WHERE m.name = 'main'
    COLUMNS (m.name AS caller, callee.full_name AS callee)
)
```

### Шаг 5: Проверка

Сравниваются количества узлов в Joern и DuckDB для подтверждения полноты экспорта:

```
======================================================================
ОТЧЁТ О ПРОВЕРКЕ ЭКСПОРТА CPG
======================================================================
[OK]       nodes_method                      1234 /     1234 (100.0%)
[OK]       nodes_call                       45678 /    45678 (100.0%)
[ОТСУТСТВУЕТ]  nodes_identifier             89000 /    89012 ( 99.9%)
----------------------------------------------------------------------
ИТОГО                                     134912 /   134924 ( 99.9%)
======================================================================
```

## Сохранение состояния и возобновление

Экспортёр автоматически сохраняет прогресс после каждой партии данных. В случае прерывания:

```
# Просто запустите снова — возобновление произойдёт автоматически
python -m src.cpg_export.exporter --db cpg.duckdb
```

### Проверка прогресса

```
# Через CLI
python -m src.cpg_export.exporter --db cpg.duckdb --status
```

```
-- Прямой SQL-запрос
SELECT entity_type, status, exported_count, last_offset
FROM export_progress
ORDER BY entity_type;
```

### Состояния прогресса

| Статус | Описание |
| --- | --- |
| pending | Ещё не начато |
| in_progress | В процессе экспорта |
| completed | Успешно завершено |
| failed | Произошла ошибка |

---

## Проверка данных

### Автоматическая проверка

Проверка запускается автоматически в конце экспорта. Чтобы пропустить:

```
python -m src.cpg_export.exporter --db cpg.duckdb --skip-validation
```

### Ручная проверка

```
# CLI
python -m src.cpg_export.exporter --db cpg.duckdb --validate-only
```

```
# Python API
from src.cpg_export import validate_export
from src.execution.joern_client import JoernClient
import duckdb

joern = JoernClient("localhost:8080", "myproject.cpg")
conn = duckdb.connect("cpg.duckdb")

results = validate_export(joern, conn, print_report=True)
```

### Работа с отсутствующими данными

Если при проверке обнаруживаются отсутствующие записи:

1. **Проверьте логи Joern** на наличие ошибок парсинга
2. **Повторно экспортируйте определённые типы**, если произошёл частичный сбой
3. **Принудительно пересоздайте** базу, если подозревается повреждение данных

```
# Повторный экспорт только узлов
exporter = JoernToDuckDBExporter(...)
exporter.connect_db()
node_stats = exporter.export_nodes_only(limit=None)

# Повторный экспорт только рёбер
edge_stats = exporter.export_edges_only(limit=None)
```

---

## Инкрементальные обновления

Для репозиториев с активной разработкой используйте инкрементальный экспорт:

```
from src.cpg_export.incremental_exporter import IncrementalCPGExporter

exporter = IncrementalCPGExporter(
    repo_path="/path/to/repo",
    db_path="cpg.duckdb",
    joern_path="/path/to/joern"
)

# Обновление на основе изменений в git
result = exporter.update_from_git_diff(
    from_ref="HEAD~5",  # Последние 5 коммитов
    to_ref="HEAD"
)

print(f"Статус: {result.status}")
print(f"Изменённые файлы: {len(result.changed_files)}")
print(f"Обновлено узлов: {result.nodes_updated}")
print(f"Время выполнения: {result.duration_seconds} с")
```

### Производительность

| Операция | Полный экспорт | Инкрементальный |
| --- | --- | --- |
| 100K строк кода | ~20 мин | ~2 мин |
| 1M строк кода | ~3 часа | ~10 мин |

---

## Векторные вложения (Vector Embeddings)

Добавьте семантические вложения для поиска кода:

```
from src.cpg_export.add_vector_embeddings import add_embeddings_to_methods

# Добавить вложения в таблицу методов
add_embeddings_to_methods(
    db_path="cpg.duckdb",
    model_name="all-MiniLM-L6-v2",
    batch_size=100
)

# Семантический поиск
from src.cpg_export.add_vector_embeddings import find_similar_methods

results = find_similar_methods(
    db_path="cpg.duckdb",
    query="parse user input safely",
    top_k=10
)
```

---

## Справочник по схеме

### Основные таблицы узлов

| Таблица | Ключевые столбцы | Описание |
| --- | --- | --- |
| nodes_method | id, name, full_name, filename, line_number | Функции/методы |
| nodes_call | id, name, method_full_name, filename, line_number | Места вызовов |
| nodes_identifier | id, name, type_full_name, line_number | Ссылки на переменные |
| nodes_literal | id, code, type_full_name | Литеральные значения |
| nodes_local | id, name, type_full_name | Локальные переменные |
| nodes_param | id, name, type_full_name, index | Параметры |
| nodes_return | id, code, line_number | Операторы возврата |
| nodes_block | id, type_full_name, line_number | Блоки кода |
| nodes_control_structure | id, control_structure_type, line_number | if/for/while |
| nodes_type_decl | id, name, full_name, filename | Объявления типов |
| nodes_file | id, name, hash | Исходные файлы |

### Основные таблицы рёбер

| Таблица | Столбцы | Описание |
| --- | --- | --- |
| edges_ast | src, dst | Родитель-потомок в AST |
| edges_cfg | src, dst | Поток управления |
| edges_call | src, dst | Вызовы методов |
| edges_ref | src, dst | Ссылки на переменные |
| edges_reaching_def | src, dst, variable | Поток данных |
| edges_cdg | src, dst | Контрольная зависимость |
| edges_dominate | src, dst | Доминирование |

### Полная схема

Полная документация по схеме доступна в файле `src/cpg_export/duckdb_cpg_schema.md`.

---

## Запросы к CPG

### SQL-запросы

```
-- Найти все методы в файле
SELECT name, full_name, line_number
FROM nodes_method
WHERE filename LIKE '%auth%'
ORDER BY line_number;

-- Найти вызовы опасных функций
SELECT nc.code, nc.filename, nc.line_number
FROM nodes_call nc
WHERE nc.name IN ('system', 'exec', 'eval');

-- Подсчёт узлов по типам
SELECT 'METHOD' as type, COUNT(*) as cnt FROM nodes_method
UNION ALL
SELECT 'CALL', COUNT(*) FROM nodes_call
UNION ALL
SELECT 'IDENTIFIER', COUNT(*) FROM nodes_identifier;
```

### Запросы к графу свойств (DuckPGQ)

```
-- Найти цепочки вызовов
FROM GRAPH_TABLE(cpg
    MATCH (caller:METHOD)-[c:CALLS]->(callee:METHOD)
    WHERE caller.name = 'process_input'
    COLUMNS (
        caller.full_name AS caller,
        callee.full_name AS callee
    )
)
LIMIT 100;

-- Найти пути потока данных
FROM GRAPH_TABLE(cpg
    MATCH (src:IDENTIFIER)-[:REACHING_DEF*1..5]->(sink:CALL)
    WHERE sink.name = 'execute'
    COLUMNS (
        src.name AS source_var,
        sink.code AS sink_call,
        sink.line_number AS line
    )
)
```

### Python-клиент

```
from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

client = DuckDBCPGClient("cpg.duckdb")

# Найти методы по шаблону
methods = client.find_methods_by_name("parse%")

# Получить граф вызовов для метода
callgraph = client.get_callgraph("UserController::authenticate")

# Получить статистику
stats = client.get_stats()
print(f"Всего методов: {stats['nodes_method']}")
print(f"Всего вызовов: {stats['nodes_call']}")
```

## Устранение неполадок

### Ошибки подключения

```
Ошибка: Не удалось подключиться к серверу Joern
```

**Решение:** Убедитесь, что Joern запущен и доступен:

```
# Проверка подключения
curl http://localhost:8080/result
```

### Нехватка памяти

```
Ошибка: База данных исчерпала память
```

**Решения:**
1. Уменьшите размер пакета: `--batch-size 5000`
2. Используйте `--limit` для тестирования
3. Закройте другие приложения

### Медленный экспорт

Для больших кодовых баз (>1 млн строк кода):

1. Используйте инкрементальный экспорт для обновлений
2. Запускайте экспорт на ночь при первоначальном выполнении
3. Рассмотрите возможность разделения по каталогам

### Отсутствующие узлы

Если при проверке обнаруживаются отсутствующие узлы:

1. Проверьте логи парсинга Joern на наличие ошибок
2. Убедитесь, что рабочая область открыта корректно
3. Попробуйте принудительное пересоздание: `--force`

---

## Рекомендации по производительности

| Объём кодовой базы | Размер пакета | Оценочное время |
| --- | --- | --- |
| <50K строк кода | 10000 | <5 мин |
| 50K–200K строк кода | 10000 | 5–30 мин |
| 200K–1M строк кода | 5000 | 30 мин – 3 часа |
| >1M строк кода | 2000 | 3+ часа |

**Оптимизации:**
- Использование SSD-накопителя для базы данных
- Достаточный объём ОЗУ (8 ГБ и более для крупных кодовых баз)
- Отдельный запуск проверки, если требуется
- Использование инкрементальной экспорта для обновлений

---

## Смотрите также

- [Кулинарная книга SQL-запросов](../reference/SQL_QUERY_COOKBOOK.md) — примеры запросов
- [Справочник схемы](../reference/SCHEMA.md) — справочная информация о схеме базы данных
- [Документация Joern](https://docs.joern.io/)
- [Документация DuckDB](https://duckdb.org/docs/)
- [Спецификация CPG v1.1](https://cpg.joern.io/)
