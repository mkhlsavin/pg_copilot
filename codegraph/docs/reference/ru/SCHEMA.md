# Дизайн схемы DuckDB CPG (CPG Spec v1.1)

## Содержание {#table-of-contents}

- [Содержание](#table-of-contents)
- [Обзор](#overview)
- [Основные принципы проектирования](#core-design-principles)
- [Таблицы узлов](#node-tables)
- [nodes_method](#nodes_method)
- [nodes_call](#nodes_call)
- [nodes_identifier](#nodes_identifier)
- [nodes_field_identifier](#nodes_field_identifier)
- [nodes_literal](#nodes_literal)
- [nodes_local](#nodes_local)
- [nodes_param](#nodes_param)
- [nodes_param_out](#nodes_param_out)
- [nodes_method_return](#nodes_method_return)
- [nodes_return](#nodes_return)
- [nodes_block](#nodes_block)
- [nodes_control_structure](#nodes_control_structure)
- [nodes_member](#nodes_member)
- [nodes_type_decl](#nodes_type_decl)
- [nodes_metadata](#nodes_metadata)
- [nodes_file](#nodes_file)
- [nodes_namespace_block](#nodes_namespace_block)
- [nodes_method_ref](#nodes_method_ref)
- [nodes_type_ref](#nodes_type_ref)
- [nodes_unknown](#nodes_unknown)
- [nodes_jump_target](#nodes_jump_target)
- [nodes_type_parameter](#nodes_type_parameter)
- [nodes_type_argument](#nodes_type_argument)
- [nodes_binding](#nodes_binding)
- [nodes_closure_binding](#nodes_closure_binding)
- [nodes_comment](#nodes_comment)
- [Таблицы рёбер](#edge-tables)
- [edges_ast](#edges_ast)
- [edges_cfg](#edges_cfg)
- [edges_call](#edges_call)
- [edges_ref](#edges_ref)
- [edges_reaching_def](#edges_reaching_def)
- [edges_argument](#edges_argument)
- [edges_receiver](#edges_receiver)
- [edges_condition](#edges_condition)
- [edges_dominate](#edges_dominate)
- [edges_post_dominate](#edges_post_dominate)
- [edges_cdg](#edges_cdg)
- [edges_binds](#edges_binds)
- [edges_binds_to](#edges_binds_to)
- [edges_source_file](#edges_source_file)
- [edges_alias_of](#edges_alias_of)
- [edges_inherits_from](#edges_inherits_from)
- [edges_capture](#edges_capture)
- [edges_captured_by](#edges_captured_by)
- [Определение графа свойств](#property-graph-definition)
- [Шаг 1: Создание материализованной объединённой таблицы узлов](#step-1-create-materialized-unified-nodes-table)
- [Шаг 2: Создание комплексного графа свойств](#step-2-create-comprehensive-property-graph)
- [Примеры запросов](#example-queries)
- [Стандартный SQL-запрос: Поиск всех вызовов определённого метода](#standard-sql-query-find-all-calls-to-a-specific-method)
- [DuckDB PGQ-запрос: Поиск прямых цепочек вызовов (вызывающий -> вызываемый)](#duckdb-pgq-query-find-direct-call-chains-caller---callee)
- [DuckDB PGQ-запрос: Поиск методов и их дочерних элементов в AST](#duckdb-pgq-query-find-methods-and-their-ast-children)
- [DuckDB PGQ-запрос: Пути потока данных с использованием REACHING_DEF](#duckdb-pgq-query-data-flow-paths-using-reaching_def)
- [DuckDB PGQ-запрос: Пути CFG (управляющий поток)](#duckdb-pgq-query-cfg-paths-control-flow)
- [DuckDB PGQ-запрос: Поиск всех идентификаторов и их ссылок](#duckdb-pgq-query-find-all-identifiers-and-their-references)
- [DuckDB PGQ-запрос: Иерархия типов (наследование)](#duckdb-pgq-query-type-hierarchy-inheritance)
- [Комбинированный запрос: Методы с наибольшим количеством входящих вызовов](#combined-query-methods-with-most-incoming-calls)
- [Миграция с Joern](#migration-from-joern)
- [Этап 1 (КРИТИЧЕСКИЙ) — ЗАВЕРШЁН ✓](#phase-1-critical---completed-)
- [Этап 2 (ПОДДЕРЖКА ООП) — ЗАВЕРШЁН ✓](#phase-2-oop-support---completed-)
- [Этап 3 (ПОДДЕРЖКА ПРОСТРАНСТВ ИМЁН И ФАЙЛОВ) — ЗАВЕРШЁН ✓](#phase-3-namespace-and-file-support---completed-)
- [Этап 4 (ОСТАВШИЕСЯ ФУНКЦИИ) — ЗАВЕРШЁН ✓](#phase-4-remaining-features---completed-)
- [Соображения по производительности](#performance-considerations)
- [Версия схемы](#schema-version)
- [Журнал изменений](#changelog)
- [v5.0 (2025-11-16) — Полное соответствие Этапу 4](#v50-2025-11-16---phase-4-complete-compliance)
- [v4.0 (2025-11-16) — Поддержка пространств имён и файлов (Этап 3)](#v40-2025-11-16---phase-3-namespace-and-file-support)
- [v3.0 (2025-11-16) — Поддержка ООП (Этап 2)](#v30-2025-11-16---phase-2-oop-support)
- [v2.0 (2025-11-16) — Критические обновления (Этап 1)](#v20-2025-11-16---phase-1-critical-updates)
- [v1.0 (2025-11-15) — Первоначальный выпуск](#v10-2025-11-15---initial-release)
- [Расширение: Система семантических меток](#extension-semantic-tag-system)
- [Обзор](#overview)
- [nodes_tag](#nodes_tag)
- [edges_tagged_by](#edges_tagged_by)
- [Категории меток](#tag-categories)
- [Примеры запросов с метками](#example-tag-queries)
- [Статистика по меткам](#tag-statistics)
- [Примечания по интеграции](#integration-notes)

## Обзор {#overview}

Эта схема реализует спецификацию Code Property Graph версии 1.1 в DuckDB с использованием расширения duckpgq для эффективного выполнения запросов к графам свойств.

## Основные принципы проектирования {#core-design-principles}

1. **Таблицы узлов**: Отдельные таблицы для каждого основного типа узлов (METHOD, CALL, IDENTIFIER и т.д.)
2. **Таблицы рёбер**: Отдельные таблицы для каждого типа рёбер (AST, CFG, CALL, REF, REACHING_DEF и т.д.)
3. **Граф свойств**: Использование команды CREATE PROPERTY GRAPH из duckpgq для объединённых графовых запросов
4. **Эффективное индексирование**: Индексы B-дерева по полям id, full_name и другим часто используемым свойствам
5. **Пакетная обработка**: Поддержка массового импорта CPG (50K+ методов)

## Таблицы узлов {#node-tables}

### nodes_method

Основная таблица для объявлений функций/методов.

```
CREATE TABLE nodes_method (
    id BIGINT PRIMARY KEY,
    name VARCHAR,
    full_name VARCHAR,
    signature VARCHAR,
    filename VARCHAR,
    line_number INTEGER,
    column_number INTEGER,
    line_number_end INTEGER,
    column_number_end INTEGER,
    offset INTEGER,          -- НОВОЕ: Байтовое смещение в файле (Фаза 2)
    offset_end INTEGER,      -- НОВОЕ: Конечное байтовое смещение (Фаза 2)
    code TEXT,
    is_external BOOLEAN,
    ast_parent_type VARCHAR,
    ast_parent_full_name VARCHAR,
    order_index INTEGER,
    hash VARCHAR,
    modifier VARCHAR[]       -- НОВОЕ: Модификаторы доступа (Фаза 2)
);

CREATE INDEX idx_method_full_name ON nodes_method(full_name);
CREATE INDEX idx_method_name ON nodes_method(name);
CREATE INDEX idx_method_filename ON nodes_method(filename);
```

**Свойства** (из спецификации CPG):
- FULL_NAME, NAME, SIGNATURE: Идентификация метода
- IS_EXTERNAL: Определён ли в исходном коде
- AST_PARENT_FULL_NAME, AST_PARENT_TYPE: Контекст типа
- FILENAME, LINE_NUMBER, COLUMN_NUMBER: Расположение в исходном коде
- OFFSET, OFFSET_END: Точное расположение на уровне байтов (Фаза 2 - НОВОЕ!)
- CODE: Исходный код метода
- HASH: Сводный хеш
- MODIFIER: Модификаторы доступа (Фаза 2 - НОВОЕ!)
  - Значения: STATIC, PUBLIC, PROTECTED, PRIVATE, ABSTRACT, NATIVE, CONSTRUCTOR, VIRTUAL, INTERNAL, FINAL, READONLY, MODULE

**Примеры модификаторов:**
- `public void foo()` → modifier=[“PUBLIC”]
- `private static int bar()` → modifier=[“PRIVATE”, “STATIC”]
- `abstract void baz()` → modifier=[“ABSTRACT”]

### nodes_call

Представляет вызовы функций/методов.

```
CREATE TABLE nodes_call (
    id BIGINT PRIMARY KEY,
    method_full_name VARCHAR,
    name VARCHAR,
    signature VARCHAR,
    type_full_name VARCHAR,
    dispatch_type VARCHAR,
    code TEXT,
    line_number INTEGER,
    column_number INTEGER,
    order_index INTEGER,
    argument_index INTEGER,
    filename VARCHAR
);

CREATE INDEX idx_call_method_full_name ON nodes_call(method_full_name);
CREATE INDEX idx_call_name ON nodes_call(name);
```

**Свойства** (из спецификации CPG):
- METHOD_FULL_NAME: Целевой метод
- DISPATCH_TYPE: Механизм вызова (STATIC_DISPATCH, DYNAMIC_DISPATCH)
- TYPE_FULL_NAME: Возвращаемый тип
- SIGNATURE: Типы параметров

### nodes_identifier

Имена переменных и ссылок.

```
CREATE TABLE nodes_identifier (
    id BIGINT PRIMARY KEY,
    name VARCHAR,
    type_full_name VARCHAR,
    code TEXT,
    line_number INTEGER,
    column_number INTEGER,
    offset INTEGER,           -- НОВОЕ: Байтовое смещение в файле
    offset_end INTEGER,       -- НОВОЕ: Конечное байтовое смещение
    order_index INTEGER,
    argument_index INTEGER
);

CREATE INDEX idx_identifier_name ON nodes_identifier(name);
```

**Свойства** (из спецификации CPG):
- NAME: Идентификатор переменной
- TYPE_FULL_NAME: Тип переменной
- OFFSET/OFFSET_END: Точное расположение в исходном коде (Фаза 2)

### nodes_field_identifier

Идентификаторы доступа к полям (ООП — например, obj.field).

```
CREATE TABLE nodes_field_identifier (
    id BIGINT PRIMARY KEY,
    canonical_name VARCHAR,  -- Нормализованное имя поля
    code TEXT,               -- Как отображается в коде
    line_number INTEGER,
    column_number INTEGER,
    offset INTEGER,
    offset_end INTEGER,
    order_index INTEGER,
    argument_index INTEGER
);

CREATE INDEX idx_field_identifier_canonical ON nodes_field_identifier(canonical_name);
```

**Свойства** (из спецификации CPG):
- CANONICAL_NAME: Нормализованное имя (например, “myField” для a.myField и b.myField)
- CODE: Доступ к полю в исходном виде (например, “obj.field”)
- Назначение: Определение обращений к полям в ООП-коде (критично для анализа псевдонимов)

**Пример:**

```
struct Point { int x, y; };
Point p;
p.x = 10;  // <- "x" — FIELD_IDENTIFIER с canonical_name="x"
```

### nodes_literal

Константные значения.

```
CREATE TABLE nodes_literal (
    id BIGINT PRIMARY KEY,
    code TEXT,
    type_full_name VARCHAR,
    line_number INTEGER,
    column_number INTEGER,
    order_index INTEGER,
    argument_index INTEGER
);
```

**Свойства** (из спецификации CPG):
- TYPE_FULL_NAME: Тип литерала
- CODE: Значение литерала

### nodes_local

Объявления локальных переменных.

```
CREATE TABLE nodes_local (
    id BIGINT PRIMARY KEY,
    name VARCHAR,
    type_full_name VARCHAR,
    code TEXT,
    line_number INTEGER,
    column_number INTEGER,
    order_index INTEGER
);

CREATE INDEX idx_local_name ON nodes_local(name);
```

**Свойства** (из спецификации CPG):
- NAME: Имя локальной переменной
- TYPE_FULL_NAME: Объявленный тип

### nodes_param

Параметры метода (формальные параметры).

```
CREATE TABLE nodes_param (
    id BIGINT PRIMARY KEY,
    name VARCHAR,
    type_full_name VARCHAR,
    code TEXT,
    line_number INTEGER,
    column_number INTEGER,
    order_index INTEGER,
    index INTEGER,
    is_variadic BOOLEAN,
    evaluation_strategy VARCHAR
);

CREATE INDEX idx_param_name ON nodes_param(name);
```

**Свойства** (из спецификации CPG):
- INDEX: Позиция параметра
- IS_VARIADIC: Параметр переменной длины
- EVALUATION_STRATEGY: BY_VALUE, BY_REFERENCE, BY_SHARING

### nodes_param_out

Выходные параметры метода (для анализа SSA/потока данных).

```
CREATE TABLE nodes_param_out (
    id BIGINT PRIMARY KEY,
    name VARCHAR,
    type_full_name VARCHAR,
    code TEXT,
    line_number INTEGER,
    column_number INTEGER,
    order_index INTEGER,
    index INTEGER,
    is_variadic BOOLEAN,
    evaluation_strategy VARCHAR
);

CREATE INDEX idx_param_out_name ON nodes_param_out(name);
```

**Свойства** (из спецификации CPG):
- Соответствует METHOD_PARAMETER_IN для анализа потока данных
- INDEX: Позиция параметра (совпадает с входным параметром)
- EVALUATION_STRATEGY: BY_VALUE, BY_REFERENCE, BY_SHARING
- Требуется для анализа SSA (Static Single Assignment)

### nodes_method_return

Параметр возврата метода (формальный возврат).

```
CREATE TABLE nodes_method_return (
    id BIGINT PRIMARY KEY,
    type_full_name VARCHAR,
    code TEXT,
    line_number INTEGER,
    column_number INTEGER,
    order_index INTEGER,
    evaluation_strategy VARCHAR
);
```

**Свойства** (из спецификации CPG):
- TYPE_FULL_NAME: Тип возврата
- CODE: Обычно “RET” или пусто
- EVALUATION_STRATEGY: Способ передачи возвращаемого значения
- Один на метод (формальный параметр возврата, не оператор return)

### nodes_return

Операторы возврата (фактический return в коде).

```
CREATE TABLE nodes_return (
    id BIGINT PRIMARY KEY,
    code TEXT,
    line_number INTEGER,
    column_number INTEGER,
    order_index INTEGER,
    argument_index INTEGER
);
```

**Примечание:** Это узел оператора RETURN. Отличается от METHOD_RETURN, который является формальным параметром возврата.

### nodes_block

Составные операторы (блоки кода).

```
CREATE TABLE nodes_block (
    id BIGINT PRIMARY KEY,
    type_full_name VARCHAR,
    code TEXT,
    line_number INTEGER,
    column_number INTEGER,
    order_index INTEGER,
    argument_index INTEGER
);
```

### nodes_control_structure

Конструкции управления потоком (if, while, for и т.д.).

```
CREATE TABLE nodes_control_structure (
    id BIGINT PRIMARY KEY,
    control_structure_type VARCHAR, -- IF, WHILE, FOR, SWITCH, TRY и т.д.
    code TEXT,
    line_number INTEGER,
    column_number INTEGER,
    order_index INTEGER,
    parser_type_name VARCHAR
);
```

**Свойства** (из спецификации CPG):
- CONTROL_STRUCTURE_TYPE: BREAK, CONTINUE, DO, WHILE, FOR, GOTO, IF, ELSE, TRY, THROW, SWITCH

### nodes_member

Члены типов (поля классов/структур).

```
CREATE TABLE nodes_member (
    id BIGINT PRIMARY KEY,
    name VARCHAR,
    type_full_name VARCHAR,  -- Тип поля
    code TEXT,               -- Код объявления
    line_number INTEGER,
    column_number INTEGER,
    offset INTEGER,          -- НОВОЕ: Байтовое смещение
    offset_end INTEGER,      -- НОВОЕ: Конечное байтовое смещение
    order_index INTEGER,
    ast_parent_type VARCHAR, -- Обычно "TYPE_DECL"
    ast_parent_full_name VARCHAR
);

CREATE INDEX idx_member_name ON nodes_member(name);
CREATE INDEX idx_member_parent ON nodes_member(ast_parent_full_name);
```

**Свойства** (из спецификации CPG):
- NAME: Имя члена (например, “x”, “y”)
- TYPE_FULL_NAME: Тип члена (например, “int”, “std::string”)
- AST_PARENT_FULL_NAME: Содержащий тип
- Назначение: Представление полей/членов классов/структур

**Пример:**

```
struct Point {
    int x;     // <- MEMBER: name="x", type_full_name="int"
    int y;     // <- MEMBER: name="y", type_full_name="int"
};
```

### nodes_type_decl

Объявления типов (классы, структуры).

```
CREATE TABLE nodes_type_decl (
    id BIGINT PRIMARY KEY,
    name VARCHAR,
    full_name VARCHAR,
    is_external BOOLEAN,
    inherits_from_type_full_name VARCHAR[],
    alias_type_full_name VARCHAR,
    filename VARCHAR,
    code TEXT,
    line_number INTEGER,
    column_number INTEGER,
    offset INTEGER,          -- НОВОЕ: Байтовое смещение
    offset_end INTEGER,      -- НОВОЕ: Конечное байтовое смещение
    ast_parent_type VARCHAR,
    ast_parent_full_name VARCHAR,
    modifier VARCHAR[]       -- НОВОЕ: Модификаторы доступа (PUBLIC, PRIVATE и т.д.)
);

CREATE INDEX idx_type_decl_full_name ON nodes_type_decl(full_name);
CREATE INDEX idx_type_decl_name ON nodes_type_decl(name);
```

**Свойства** (из спецификации CPG):
- FULL_NAME, NAME: Идентификация типа
- IS_EXTERNAL: Определён ли в исходном коде
- INHERITS_FROM_TYPE_FULL_NAME: Базовые типы (массив)
- ALIAS_TYPE_FULL_NAME: Псевдоним типа
- MODIFIER: Модификаторы доступа (Фаза 2 - НОВОЕ!)
  - Значения: STATIC, PUBLIC, PROTECTED, PRIVATE, ABSTRACT, NATIVE, CONSTRUCTOR, VIRTUAL, INTERNAL, FINAL, READONLY, MODULE

**Примеры модификаторов:**
- `public class Foo` → modifier=[“PUBLIC”]
- `private static class Bar` → modifier=[“PRIVATE”, “STATIC”]
- `abstract class Baz` → modifier=[“ABSTRACT”]

### nodes_metadata

Метаданные CPG (требуются спецификацией).

```
CREATE TABLE nodes_metadata (
    id BIGINT PRIMARY KEY,
    language VARCHAR,
    version VARCHAR, -- "1.1"
    overlays VARCHAR[],
    root VARCHAR
);
```

**Свойства** (из спецификации CPG):
- LANGUAGE: Язык исходного кода
- VERSION: Версия спецификации CPG
- OVERLAYS: Применённые оверлеи
- ROOT: Корневой путь

### nodes_file

Узлы исходных файлов (требуются спецификацией).

```
CREATE TABLE nodes_file (
    id BIGINT PRIMARY KEY,
    name VARCHAR,           -- Путь к файлу (относительно корня)
    hash VARCHAR,           -- Хеш содержимого файла
    content TEXT,           -- Опционально: исходный код файла
    order_index INTEGER
);

CREATE INDEX idx_file_name ON nodes_file(name);
CREATE INDEX idx_file_hash ON nodes_file(hash);
```

**Свойства** (из спецификации CPG):
- NAME: Путь к файлу относительно корня (из METADATA.ROOT)
- HASH: Хеш SHA-256 или MD5 содержимого файла
- CONTENT: Опционально — полный исходный код файла
- ORDER_INDEX: Всегда 0 (у файлов нет соседей)

**Назначение:**
- Индекс для поиска всех элементов кода по файлу
- Корневые узлы деревьев синтаксического анализа (AST)
- Хранение метаданных исходных файлов
- Требуется для рёбер SOURCE_FILE

**Пример:**

```
name="src/main.c", hash="abc123...", order_index=0
```

**Примечание:** Каждый исходный файл ДОЛЖЕН иметь ровно один узел FILE. Узлы FILE служат корнями AST и позволяют переходить от файла ко всем содержащимся в нём элементам кода.

### nodes_namespace_block

Узлы блоков пространств имён (области видимости пространств имён).

```
CREATE TABLE nodes_namespace_block (
    id BIGINT PRIMARY KEY,
    name VARCHAR,           -- Имя пространства имён (с точками)
    full_name VARCHAR,      -- Уникальный идентификатор (файл + пространство имён)
    filename VARCHAR,       -- Содержащий файл
    order_index INTEGER
);

CREATE INDEX idx_namespace_block_name ON nodes_namespace_block(name);
CREATE INDEX idx_namespace_block_full_name ON nodes_namespace_block(full_name);
CREATE INDEX idx_namespace_block_filename ON nodes_namespace_block(filename);
```

**Свойства** (из спецификации CPG):
- NAME: Человекочитаемое имя пространства имён (например, “foo.bar”)
  - С точками: “foo.bar” означает пространство имён “bar” внутри “foo”
- FULL_NAME: Уникальный идентификатор, объединяющий файл и пространство имён
  - Должен включать информацию о файле для обеспечения уникальности
- FILENAME: Исходный файл, содержащий этот блок пространства имён
- ORDER_INDEX: Позиция в родительском AST

**Назначение:**
- Представление блоков пространств имён (C++ `namespace{}`, Java `package`)
- Структурирование кода на логические единицы
- Возможность запросов к коду по пространству имён
- Поддержка анализа многокомпонентных пространств имён

**Примеры:**

```
// C++:
namespace foo {
    namespace bar {
        // код
    }
}
// NAME="foo.bar", FULL_NAME="main.cpp:foo.bar"

// Java:
package com.example.myapp;
// NAME="com.example.myapp", FULL_NAME="Main.java:com.example.myapp"
```

**Примечание:** Узлы NAMESPACE (индексы) автоматически генерируются из узлов NAMESPACE_BLOCK при загрузке CPG.

### nodes_method_ref

Узлы ссылок на методы (метод как значение).

```
CREATE TABLE nodes_method_ref (
    id BIGINT PRIMARY KEY,
    method_full_name VARCHAR,  -- Полное имя ссылочного метода
    type_full_name VARCHAR,    -- Тип метода (тип указателя на функцию)
    code TEXT,                 -- Как отображается в коде
    line_number INTEGER,
    column_number INTEGER,
    "offset" INTEGER,
    "offset_end" INTEGER,
    order_index INTEGER,
    argument_index INTEGER
);

CREATE INDEX idx_method_ref_method_full_name ON nodes_method_ref(method_full_name);
CREATE INDEX idx_method_ref_type ON nodes_method_ref(type_full_name);
```

**Свойства** (из спецификации CPG):
- METHOD_FULL_NAME: Полное имя ссылочного метода
- TYPE_FULL_NAME: Тип метода (например, “int(*)(int, int)” в C)
- CODE: Как ссылка отображается в исходном коде
- OFFSET/OFFSET_END: Точное расположение в исходном коде

**Назначение:**
- Представление методов, передаваемых как аргументы (функции высшего порядка)
- Указ

## Таблицы рёбер {#edge-tables}

### edges_ast

Рёбра дерева абстрактного синтаксиса (отношения «родитель-потомок»).

```
CREATE TABLE edges_ast (
    src BIGINT,
    dst BIGINT,
    PRIMARY KEY (src, dst)
);

CREATE INDEX idx_ast_src ON edges_ast(src);
CREATE INDEX idx_ast_dst ON edges_ast(dst);
```

### edges_cfg

Рёбра графа потока управления (Control Flow Graph).

```
CREATE TABLE edges_cfg (
    src BIGINT,
    dst BIGINT,
    PRIMARY KEY (src, dst)
);

CREATE INDEX idx_cfg_src ON edges_cfg(src);
CREATE INDEX idx_cfg_dst ON edges_cfg(dst);
```

### edges_call

Рёбра от вызова метода к его объявлению.

```
CREATE TABLE edges_call (
    src BIGINT, -- ID узла CALL
    dst BIGINT, -- ID узла METHOD
    PRIMARY KEY (src, dst)
);

CREATE INDEX idx_call_edge_src ON edges_call(src);
CREATE INDEX idx_call_edge_dst ON edges_call(dst);
```

### edges_ref

Рёбра ссылок (идентификатор → объявление).

```
CREATE TABLE edges_ref (
    src BIGINT, -- ID узла IDENTIFIER/CALL
    dst BIGINT, -- ID узла DECLARATION (LOCAL, PARAM, METHOD, TYPE_DECL)
    PRIMARY KEY (src, dst)
);

CREATE INDEX idx_ref_src ON edges_ref(src);
CREATE INDEX idx_ref_dst ON edges_ref(dst);
```

### edges_reaching_def

Рёбра потока данных (достижимые определения).

```
CREATE TABLE edges_reaching_def (
    src BIGINT,
    dst BIGINT,
    variable VARCHAR, -- Имя переменной
    PRIMARY KEY (src, dst, variable)
);

CREATE INDEX idx_reaching_def_src ON edges_reaching_def(src);
CREATE INDEX idx_reaching_def_dst ON edges_reaching_def(dst);
CREATE INDEX idx_reaching_def_variable ON edges_reaching_def(variable);
```

**Свойства** (из спецификации CPG):
- VARIABLE: имя отслеживаемой переменной

### edges_argument

Рёбра аргументов (вызов → выражения аргументов, возврат → возвращаемое выражение).

```
CREATE TABLE edges_argument (
    src BIGINT,
    dst BIGINT,
    PRIMARY KEY (src, dst)
);

CREATE INDEX idx_argument_src ON edges_argument(src);
CREATE INDEX idx_argument_dst ON edges_argument(dst);
```

### edges_receiver

Рёбра получателя (вызов → выражение-получатель).

```
CREATE TABLE edges_receiver (
    src BIGINT, -- ID узла CALL
    dst BIGINT, -- ID выражения-получателя
    PRIMARY KEY (src, dst)
);
```

### edges_condition

Рёбра условия (управляющая структура → условное выражение).

```
CREATE TABLE edges_condition (
    src BIGINT, -- ID узла CONTROL_STRUCTURE
    dst BIGINT, -- ID узла выражения
    PRIMARY KEY (src, dst)
);
```

### edges_dominate

Рёбра непосредственного доминирования (доминирование в потоке управления).

```
CREATE TABLE edges_dominate (
    src BIGINT,
    dst BIGINT,
    PRIMARY KEY (src, dst)
);
```

### edges_post_dominate

Рёбра пост-доминирования.

```
CREATE TABLE edges_post_dominate (
    src BIGINT,
    dst BIGINT,
    PRIMARY KEY (src, dst)
);

CREATE INDEX idx_post_dominate_src ON edges_post_dominate(src);
CREATE INDEX idx_post_dominate_dst ON edges_post_dominate(dst);
```

### edges_cdg

Рёбра графа управляющих зависимостей (CRITICAL для PDG).

```
CREATE TABLE edges_cdg (
    src BIGINT, -- ID узла управляющей структуры (условие/ветвление)
    dst BIGINT, -- ID зависимого узла (кода, зависящего от условия)
    PRIMARY KEY (src, dst)
);

CREATE INDEX idx_cdg_src ON edges_cdg(src);
CREATE INDEX idx_cdg_dst ON edges_cdg(dst);
```

**Свойства** (из спецификации CPG):
- Ребро CDG означает: dst зависит от src по управлению
- Критически важно для построения графа зависимостей программы (PDG = DDG + CDG)
- Используется для срезов программы, анализа безопасности, оптимизаций компилятора
- Пример: операторы внутри блока IF зависят по управлению от условия IF

### edges_binds

Рёбра привязки имён (связывание имён).

```
CREATE TABLE edges_binds (
    src BIGINT, -- ID узла BINDING
    dst BIGINT, -- ID узла METHOD или TYPE_DECL
    PRIMARY KEY (src, dst)
);

CREATE INDEX idx_binds_src ON edges_binds(src);
CREATE INDEX idx_binds_dst ON edges_binds(dst);
```

**Свойства** (из спецификации CPG):
- Связывает узлы BINDING с их объявлениями
- Используется для разрешения имён переменных и функций
- Пример: оператор import связывает имя с фактическим определением

### edges_binds_to

Обратные рёбра привязки (использование имён).

```
CREATE TABLE edges_binds_to (
    src BIGINT, -- ID узла ссылки на переменную/функцию
    dst BIGINT, -- ID узла BINDING
    PRIMARY KEY (src, dst)
);

CREATE INDEX idx_binds_to_src ON edges_binds_to(src);
CREATE INDEX idx_binds_to_dst ON edges_binds_to(dst);
```

**Свойства** (из спецификации CPG):
- Обратное ребро к ребру BINDS
- Связывает использование имён с их привязками
- Пример: ссылка на переменную → привязка → объявление

**Последовательность BINDS:**

```
Объявление (METHOD/TYPE_DECL)
     ↑
   BINDS
     |
  Узел BINDING (оператор import/using)
     ↑
 BINDS_TO
     |
Ссылка (IDENTIFIER/CALL)
```

### edges_source_file

Рёбра исходного файла (сопоставление узлов с файлом).

```
CREATE TABLE edges_source_file (
    src BIGINT,  -- ID любого узла AST
    dst BIGINT,  -- ID узла FILE
    PRIMARY KEY (src, dst)
);

CREATE INDEX idx_source_file_src ON edges_source_file(src);
CREATE INDEX idx_source_file_dst ON edges_source_file(dst);
```

**Свойства** (из спецификации CPG):
- Связывает узлы с их исходным файлом FILE
- Создаётся автоматически на основе свойства FILENAME
- **НЕ ДОЛЖНО создаваться языковым фронтендом** — создаётся автоматически
- Отношение один к одному: каждый узел имеет ровно один исходный файл

**Назначение:**
- Сопоставление любого элемента кода с его исходным файлом
- Навигация от FILE ко всем содержащимся элементам
- Поддержка запросов и анализа на уровне файлов
- Реализация функции IDE «перейти к файлу»

**Пример:**

```
Узел METHOD (id=100) → SOURCE_FILE → Узел FILE (id=1, name="main.c")
Узел CALL (id=200) → SOURCE_FILE → Узел FILE (id=1, name="main.c")
Узел TYPE_DECL (id=300) → SOURCE_FILE → Узел FILE (id=2, name="types.h")
```

**Логика автоматического создания:**
1. Фронтенд устанавливает свойство FILENAME на узлах (METHOD, TYPE_DECL и т.д.)
2. Загрузчик CPG создаёт узлы FILE для уникальных имён файлов
3. Загрузчик CPG создаёт рёбра SOURCE_FILE от узлов к узлам FILE
4. Результат — полное сопоставление файл → код

### edges_alias_of

Рёбра псевдонимов типов.

```
CREATE TABLE edges_alias_of (
    src BIGINT,  -- Узел TYPE_DECL (псевдоним)
    dst BIGINT,  -- Узел TYPE (фактический тип)
    PRIMARY KEY (src, dst)
);

CREATE INDEX idx_alias_of_src ON edges_alias_of(src);
CREATE INDEX idx_alias_of_dst ON edges_alias_of(dst);
```

**Свойства** (из спецификации CPG):
- Связывает TYPE_DECL (псевдоним) с TYPE (фактическим типом)
- **НЕ ДОЛЖНО создаваться фронтендом** — создаётся автоматически из ALIAS_TYPE_FULL_NAME
- Отношение один к одному

**Назначение:**
- Представление псевдонимов типов (typedef в C, using, type aliases)
- Поддержка разрешения псевдонимов
- Анализ синонимов типов

**Примеры:**

```
// typedef в C:
typedef int Integer;
// TYPE_DECL "Integer" --ALIAS_OF--> TYPE "int"

// using в C++:
using String = std::string;
// TYPE_DECL "String" --ALIAS_OF--> TYPE "std::string"

// Псевдоним типа в Rust:
type Result<T> = std::result::Result<T, Error>;
// TYPE_DECL "Result" --ALIAS_OF--> TYPE "std::result::Result"
```

**Примечание:** Автоматически генерируется при загрузке CPG на основе свойства ALIAS_TYPE_FULL_NAME.

### edges_inherits_from

Рёбра наследования типов.

```
CREATE TABLE edges_inherits_from (
    src BIGINT,  -- Узел TYPE_DECL (производный)
    dst BIGINT,  -- Узел TYPE (базовый)
    PRIMARY KEY (src, dst)
);

CREATE INDEX idx_inherits_from_src ON edges_inherits_from(src);
CREATE INDEX idx_inherits_from_dst ON edges_inherits_from(dst);
```

**Свойства** (из спецификации CPG):
- Связывает TYPE_DECL (производный) с TYPE (базовым)
- **НЕ ДОЛЖНО создаваться фронтендом** — создаётся автоматически из INHERITS_FROM_TYPE_FULL_NAME
- Отношение один ко многим (поддерживается множественное наследование)

**Назначение:**
- Представление наследования классов/интерфейсов
- Поддержка анализа полиморфизма
- Запросы к иерархии типов
- Отслеживание цепочек наследования

**Примеры:**

```
// Одиночное наследование в Java:
class Dog extends Animal implements Comparable {
    ...
}
// TYPE_DECL "Dog" --INHERITS_FROM--> TYPE "Animal"
// TYPE_DECL "Dog" --INHERITS_FROM--> TYPE "Comparable"

// Множественное наследование в C++:
class D : public A, public B { };
// TYPE_DECL "D" --INHERITS_FROM--> TYPE "A"
// TYPE_DECL "D" --INHERITS_FROM--> TYPE "B"
```

**Примечание:** Автоматически генерируется при загрузке CPG на основе массива INHERITS_FROM_TYPE_FULL_NAME.

### edges_capture

Рёбра захвата замыканий.

```
CREATE TABLE edges_capture (
    src BIGINT,  -- Узел METHOD_REF или TYPE_REF
    dst BIGINT,  -- Узел CLOSURE_BINDING
    PRIMARY KEY (src, dst)
);

CREATE INDEX idx_capture_src ON edges_capture(src);
CREATE INDEX idx_capture_dst ON edges_capture(dst);
```

**Свойства** (из спецификации CPG):
- Связывает METHOD_REF/TYPE_REF с CLOSURE_BINDING
- Представляет захват переменных в замыкании/лямбде
- Отношение один ко многим (замыкание может захватывать несколько переменных)

**Назначение:**
- Отслеживание переменных, захваченных замыканиями
- Поддержка анализа выхода за пределы области видимости (escape analysis)
- Оптимизация замыканий
- Определение времени жизни захваченных переменных

**Примеры:**

```
function outer() {
    let x = 10;
    let y = 20;
    return function inner() {
        return x + y;  // захватывает x и y
    };
}
// METHOD_REF "inner" --CAPTURE--> CLOSURE_BINDING для x
// METHOD_REF "inner" --CAPTURE--> CLOSURE_BINDING для y
```

**Примечание:** Ребро CAPTURE связывает замыкание с захваченными переменными.

### edges_captured_by

Обратные рёбра захвата замыканий.

```
CREATE TABLE edges_captured_by (
    src BIGINT,  -- Узел LOCAL или METHOD_PARAMETER_IN
    dst BIGINT,  -- Узел CLOSURE_BINDING
    PRIMARY KEY (src, dst)
);

CREATE INDEX idx_captured_by_src ON edges_captured_by(src);
CREATE INDEX idx_captured_by_dst ON edges_captured_by(dst);
```

**Свойства** (из спецификации CPG):
- Связывает LOCAL/METHOD_PARAMETER_IN с CLOSURE_BINDING
- Обратное ребро к CAPTURE
- Указывает, какие замыкания захватывают данную переменную

**Назначение:**
- Отслеживание замыканий, захватывающих переменную
- Определение переменных, выходящих за пределы области видимости
- Анализ времени жизни переменных
- Поддержка рефакторинга, связанного с замыканиями

**Примеры:**

```
def make_counter():
    count = 0  # LOCAL
    def increment():
        nonlocal count
        count += 1
        return count
    return increment
# LOCAL "count" --CAPTURED_BY--> CLOSURE_BINDING {#local-count---captured-by---closure-binding}
```

**Последовательность для замыканий:**

```
LOCAL/PARAM "x"
     |
CAPTURED_BY
     ↓
CLOSURE_BINDING
     ↑
  CAPTURE
     |
METHOD_REF (замыкание/лямбда)
```

**Примечание:** CAPTURED_BY связывает захваченную переменную с привязкой замыкания.

## Определение графа свойств {#property-graph-definition}

Использование duckpgq для создания объединённого графа свойств с полной поддержкой схемы CPG.

**КЛЮЧЕВАЯ ИДЕЯ**: DuckDB PGQ не поддерживает представления (views) в вершинных таблицах (VERTEX TABLES), но мы можем использовать **материализованные таблицы** вместо них! Это позволяет полностью поддерживать полиморфные рёбра.

### Шаг 1: Создание материализованной объединённой таблицы узлов {#step-1-create-materialized-unified-nodes-table}

**Важно**: Используйте `CREATE TABLE` (а не `CREATE VIEW`), чтобы материализовать объединённый набор узлов.

```
-- Создание материализованной объединённой таблицы всех узлов CPG для поддержки полиморфных рёбер
DROP TABLE IF EXISTS cpg_nodes;

CREATE TABLE cpg_nodes AS
SELECT id, 'FILE' as node_type FROM nodes_file
UNION ALL SELECT id, 'NAMESPACE_BLOCK' FROM nodes_namespace_block
UNION ALL SELECT id, 'METHOD' FROM nodes_method
UNION ALL SELECT id, 'METHOD_REF' FROM nodes_method_ref
UNION ALL SELECT id, 'CALL' FROM nodes_call
UNION ALL SELECT id, 'IDENTIFIER' FROM nodes_identifier
UNION ALL SELECT id, 'FIELD_IDENTIFIER' FROM nodes_field_identifier
UNION ALL SELECT id, 'LITERAL' FROM nodes_literal
UNION ALL SELECT id, 'LOCAL' FROM nodes_local
UNION ALL SELECT id, 'PARAM' FROM nodes_param
UNION ALL SELECT id, 'PARAM_OUT' FROM nodes_param_out
UNION ALL SELECT id, 'METHOD_RETURN' FROM nodes_method_return
UNION ALL SELECT id, 'RETURN' FROM nodes_return
UNION ALL SELECT id, 'BLOCK' FROM nodes_block
UNION ALL SELECT id, 'CONTROL_STRUCTURE' FROM nodes_control_structure
UNION ALL SELECT id, 'MEMBER' FROM nodes_member
UNION ALL SELECT id, 'TYPE_DECL' FROM nodes_type_decl
UNION ALL SELECT id, 'TYPE_REF' FROM nodes_type_ref
UNION ALL SELECT id, 'TYPE_PARAMETER' FROM nodes_type_parameter
UNION ALL SELECT id, 'TYPE_ARGUMENT' FROM nodes_type_argument
UNION ALL SELECT id, 'UNKNOWN' FROM nodes_unknown
UNION ALL SELECT id, 'JUMP_TARGET' FROM nodes_jump_target
UNION ALL SELECT id, 'BINDING' FROM nodes_binding
UNION ALL SELECT id, 'CLOSURE_BINDING' FROM nodes_closure_binding
UNION ALL SELECT id, 'COMMENT' FROM nodes_comment;

-- Добавление первичного ключа и индексов
ALTER TABLE cpg_nodes ADD PRIMARY KEY (id);
CREATE INDEX idx_cpg_nodes_type ON cpg_nodes(node_type);
```

### Шаг 2: Создание комплексного графа свойств {#step-2-create-comprehensive-property-graph}

**Полная реализация** (со всеми типами рёбер, включая полиморфные):

```
CREATE PROPERTY GRAPH cpg
VERTEX TABLES (
    -- Материализованная объединённая таблица узлов для поддержки полиморфных рёбер
    cpg_nodes LABEL CPG_NODE,

    -- Отдельные типизированные таблицы узлов для специфических запросов
    nodes_file LABEL FILE_NODE,
    nodes_namespace_block LABEL NAMESPACE_BLOCK,
    nodes_method LABEL METHOD,
    nodes_method_ref LABEL METHOD_REF,
    nodes_call LABEL CALL_NODE,
    nodes_identifier LABEL IDENTIFIER,
    nodes_field_identifier LABEL FIELD_IDENTIFIER,
    nodes_literal LABEL LITERAL,
    nodes_local LABEL LOCAL,
    nodes_param LABEL PARAM,
    nodes_param_out LABEL PARAM_OUT,
    nodes_method_return LABEL METHOD_RETURN,
    nodes_return LABEL RETURN_NODE,
    nodes_block LABEL BLOCK,
    nodes_control_structure LABEL CONTROL_STRUCTURE,
    nodes_member LABEL MEMBER,
    nodes_type_decl LABEL TYPE_DECL,
    nodes_type_ref LABEL TYPE_REF,
    nodes_type_parameter LABEL TYPE_PARAMETER,
    nodes_type_argument LABEL TYPE_ARGUMENT,
    nodes_unknown LABEL UNKNOWN,
    nodes_jump_target LABEL JUMP_TARGET,
    nodes_binding LABEL BINDING,
    nodes_closure_binding LABEL CLOSURE_BINDING,
    nodes_comment LABEL COMMENT_NODE,
    nodes_metadata LABEL METADATA
)
EDGE TABLES (
    -- ========================================
    -- ПОЛИМОРФНЫЕ РЁБРА (через таблицу cpg_nodes)
    -- ========================================

    edges_ast
        SOURCE KEY (src) REFERENCES cpg_nodes (id)
        DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
        LABEL AST,

    edges_cfg
        SOURCE KEY (src) REFERENCES cpg_nodes (id)
        DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
        LABEL CFG,

    edges_ref
        SOURCE KEY (src) REFERENCES cpg_nodes (id)
        DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
        LABEL REF,

    edges_reaching_def
        SOURCE KEY (src) REFERENCES cpg_nodes (id)
        DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
        LABEL REACHING_DEF,

    edges_argument
        SOURCE KEY (src) REFERENCES cpg_nodes (id)
        DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
        LABEL ARGUMENT,

    edges_dominate
        SOURCE KEY (src) REFERENCES cpg_nodes (id)
        DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
        LABEL DOMINATE,

    edges_post_dominate
        SOURCE KEY (src) REFERENCES cpg_nodes (id)
        DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
        LABEL POST_DOMINATE,

    edges_cdg
        SOURCE KEY (src) REFERENCES cpg_nodes (id)
        DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
        LABEL CDG,

    edges_binds
        SOURCE KEY (src) REFERENCES cpg_nodes (id)
        DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
        LABEL BINDS,

    edges_binds_to
        SOURCE KEY (src) REFERENCES cpg_nodes (id)
        DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
        LABEL BINDS_TO,

    -- ========================================
    -- ТИПИЗИРОВАННЫЕ РЁБРА (конкретные источники/назначения)
    -- ========================================

    edges_call
        SOURCE KEY (src) REFERENCES nodes_call (id)
        DESTINATION KEY (dst) REFERENCES nodes_method (id)
        LABEL CALLS,

    edges_receiver
        SOURCE KEY (src) REFERENCES nodes_call (id)
        DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
        LABEL RECEIVER,

    edges_condition
        SOURCE KEY (src) REFERENCES nodes_control_structure (id)
        DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
        LABEL CONDITION,

    edges_source_file
        SOURCE KEY (src) REFERENCES cpg_nodes (id)
        DESTINATION KEY (dst) REFERENCES nodes_file (id)
        LABEL SOURCE_FILE,

    edges_alias_of
        SOURCE KEY (src) REFERENCES nodes_type_decl (id)
        DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
        LABEL ALIAS_OF,

    edges_inherits_from
        SOURCE KEY (src) REFERENCES nodes_type_decl (id)
        DESTINATION KEY (dst) REFERENCES cpg_nodes (id)
        LABEL INHERITS_FROM,

    edges_capture
        SOURCE KEY (src) REFERENCES cpg_nodes (id)
        DESTINATION KEY (dst) REFERENCES nodes_closure_binding (id)
        LABEL CAPTURE,

    edges_captured_by
        SOURCE KEY (src) REFERENCES cpg_nodes (id)
        DESTINATION KEY (dst) REFERENCES nodes_closure_binding (id)
        LABEL CAPTURED_BY
);
```

**Ключевые особенности**:
- ✅ **Полная поддержка схемы CPG** со всеми типами рёбер
- ✅ **Полиморфные рёбра** (AST, CFG, REF и т.д.) через материализованную таблицу `cpg_nodes`
- ✅ **Типизированные вершины** для эффективных целевых запросов
- ✅ **Совместимо с DuckDB PGQ** (используются таблицы, а не представления)
- ✅ **Полное соответствие спецификации Joern CPG v1.1**

## Примеры запросов {#example-queries}

### Стандартный SQL-запрос: Найти все вызовы определённого метода

```
SELECT c.*, m.name, m.filename, m.line_number
FROM nodes_call c
JOIN edges_call ec ON c.id = ec.src
JOIN nodes_method m ON ec.dst = m.id
WHERE m.full_name = 'com.example.MyClass.myMethod:void()';
```

### DuckDB PGQ-запрос: Найти прямые цепочки вызовов (вызывающий -> вызываемый)

```
SELECT *
FROM GRAPH_TABLE(cpg
    MATCH (caller:METHOD)-[:CALLS]-(call:CALL_NODE)-[:CALLS]->(callee:METHOD)
    WHERE caller.name = 'main'
    COLUMNS (caller.full_name AS caller_name, callee.full_name AS callee_name)
);
```

### DuckDB PGQ-запрос: Найти методы и их дочерние узлы AST

```
SELECT *
FROM GRAPH_TABLE(cpg
    MATCH (m:METHOD)-[:AST]->(child:CPG_NODE)
    COLUMNS (m.full_name AS method, child.id AS child_id)
);
```

### DuckDB PGQ-запрос: Пути потока данных с использованием REACHING_DEF

```
SELECT *
FROM GRAPH_TABLE(cpg
    MATCH (source:CPG_NODE)-[:REACHING_DEF*1..5]->(sink:CPG_NODE)
    COLUMNS (source.id, sink.id)
)
LIMIT 100;
```

### DuckDB PGQ-запрос: Пути CFG (управление выполнением)

```
SELECT *
FROM GRAPH_TABLE(cpg
    MATCH (start:CPG_NODE)-[:CFG*1..3]->(end:CPG_NODE)
    COLUMNS (start.id AS start_node, end.id AS end_node)
)
LIMIT 100;
```

### DuckDB PGQ-запрос: Найти все идентификаторы и их ссылки

```
SELECT *
FROM GRAPH_TABLE(cpg
    MATCH (id:IDENTIFIER)-[:REF]->(decl:CPG_NODE)
    COLUMNS (id.name AS identifier_name, decl.id AS declaration_id)
);
```

### DuckDB PGQ-запрос: Иерархия типов (наследование) {#duckdb-pgq-query-type-hierarchy-inheritance}

```
SELECT *
FROM GRAPH_TABLE(cpg
    MATCH (derived:TYPE_DECL)-[:INHERITS_FROM]->(base:CPG_NODE)
    COLUMNS (derived.full_name AS derived_type, base.id AS base_type)
);
```

### Комбинированный запрос: Методы с наибольшим количеством входящих вызовов {#combined-query-methods-with-most-incoming-calls}

```
SELECT m.full_name, COUNT(*) as call_count
FROM GRAPH_TABLE(cpg
    MATCH (c:CALL_NODE)-[:CALLS]->(m:METHOD)
    COLUMNS (m.full_name, m.id)
)
GROUP BY m.full_name
ORDER BY call_count DESC
LIMIT 10;
```

## Миграция с Joern {#migration-from-joern}

### Этап 1 (КРИТИЧЕСКИЙ) — ЗАВЕРШЁН ✓ {#phase-1-critical---completed-}

- ✓ nodes_method (со всеми свойствами)
- ✓ nodes_call (с method_full_name, name, signature)
- ✓ edges_call (от места вызова к методу)
- ✓ nodes_param_out (METHOD_PARAMETER_OUT) — НОВОЕ!
- ✓ nodes_method_return (METHOD_RETURN) — НОВОЕ!
- ✓ edges_cdg (граф управляющих зависимостей, Control Dependence Graph) — НОВОЕ!

### Этап 2 (ПОДДЕРЖКА ООП) — ЗАВЕРШЁН ✓ {#phase-2-oop-support---completed-}

- ✓ nodes_field_identifier (FIELD_IDENTIFIER) — НОВОЕ!
- ✓ nodes_member (MEMBER) — НОВОЕ!
- ✓ свойства OFFSET/OFFSET_END для METHOD, TYPE_DECL, IDENTIFIER — НОВОЕ!
- ✓ свойство MODIFIER для METHOD, TYPE_DECL — НОВОЕ!
- ✓ edges_binds (BINDS) — НОВОЕ!
- ✓ edges_binds_to (BINDS_TO) — НОВОЕ!

### Этап 3 (ПОДДЕРЖКА ПРОСТРАНСТВ ИМЁН И ФАЙЛОВ) — ЗАВЕРШЁН ✓ {#phase-3-namespace-and-file-support---completed-}

- ✓ nodes_file (FILE) — НОВОЕ!
- ✓ nodes_namespace_block (NAMESPACE_BLOCK) — НОВОЕ!
- ✓ nodes_method_ref (METHOD_REF) — НОВОЕ!
- ✓ nodes_type_ref (TYPE_REF) — НОВОЕ!
- ✓ edges_source_file (SOURCE_FILE) — НОВОЕ!

### Этап 4 (ОСТАВШИЕСЯ ФУНКЦИИ) — ЗАВЕРШЁН ✓ {#phase-4-remaining-features---completed-}

- ✓ Экспорт рёбер AST
- ✓ Экспорт рёбер CFG
- ✓ Экспорт рёбер REF, REACHING_DEF
- ✓ Экспорт дополнительных типов узлов (UNKNOWN, JUMP_TARGET, TYPE_PARAMETER, TYPE_ARGUMENT, BINDING, CLOSURE_BINDING, COMMENT)
- ✓ Экспорт оставшихся рёбер (ALIAS_OF, INHERITS_FROM, CAPTURE, CAPTURED_BY)

## Рекомендации по производительности

1. **Пакетная обработка**: Используйте пакеты по 10 000 строк для операций INSERT
2. **Индексирование**: Создавайте индексы после массовой загрузки для ускорения импорта
3. **Разделение на секции**: Рассмотрите возможность секционирования по имени файла для крупных кодовых баз
4. **Сжатие**: Используйте автоматическое сжатие DuckDB для столбцов типа TEXT
5. **Память**: Настройте лимит памяти DuckDB в зависимости от размера CPG

## Версия схемы {#schema-version}

- Спецификация CPG: v1.1
- DuckDB: 1.1.3+
- duckpgq: Последняя стабильная версия
- Версия схемы: 5.0 (Завершена полная совместимость с фазой 4)
- Последнее обновление: 2025-11-16

## Журнал изменений {#changelog}

### v5.0 (2025-11-16) — Завершение четвёртого этапа: полное соответствие схеме {#v50-2025-11-16---phase-4-complete-compliance}

**КРУПНОЕ ОБНОВЛЕНИЕ: Достигнуто 100% соответствие схеме Joern со всеми оставшимися функциями**

**Новые типы узлов:**
- `nodes_unknown` (UNKNOWN) — универсальный тип для неподдерживаемых конструкций AST
- `nodes_jump_target` (JUMP_TARGET) — метки для операторов goto/break/continue
- `nodes_type_parameter` (TYPE_PARAMETER) — формальные параметры шаблонов/дженериков
- `nodes_type_argument` (TYPE_ARGUMENT) — фактические аргументы шаблонов/дженериков
- `nodes_binding` (BINDING) — привязки для разрешения методов
- `nodes_closure_binding` (CLOSURE_BINDING) — захват переменных в замыканиях
- `nodes_comment` (COMMENT) — комментарии в исходном коде

**Новые типы рёбер:**
- `edges_alias_of` (ALIAS_OF) — связи псевдонимов типов
- `edges_inherits_from` (INHERITS_FROM) — связи наследования типов
- `edges_capture` (CAPTURE) — захват переменных в замыканиях
- `edges_captured_by` (CAPTURED_BY) — обратные связи захвата в замыканиях

**Влияние:**
- **Достигнуто 100% соответствие схеме Joern**
- Полное покрытие AST с использованием узлов UNKNOWN
- Полная поддержка дженериков и шаблонов
- Включён анализ замыканий и лямбд
- Поддержка разрешения псевдонимов и наследования типов
- Сохранение комментариев для документации
- Полноценные возможности анализа программ

**Соответствие:** ~95% → **100% схеме Joern**

### v4.0 (2025-11-16) — Третий этап: поддержка пространств имён и файлов

**КРУПНОЕ ОБНОВЛЕНИЕ: Добавлено сопоставление с файлами, поддержка пространств имён и ссылок на методы/типы**

**Новые типы узлов:**
- `nodes_file` (FILE) — узлы исходных файлов для индексации по файлам
- `nodes_namespace_block` (NAMESPACE_BLOCK) — блоки пространств имён (C++ namespace, Java package)
- `nodes_method_ref` (METHOD_REF) — ссылки на методы (функции высшего порядка, указатели на функции)
- `nodes_type_ref` (TYPE_REF) — ссылки на типы (рефлексия, приведение типов, дженерики)

**Новые типы рёбер:**
- `edges_source_file` (SOURCE_FILE) — сопоставление узлов с файлами (создаётся автоматически из FILENAME)

**Влияние:**
- Включена навигация по коду на уровне файлов
- Поддержка анализа с учётом пространств имён
- Отслеживание функций высшего порядка (колбэки, делегаты)
- Поддержка рефлексии и дженериков
- Полное сопоставление с исходными файлами (готово к интеграции с IDE)
- Улучшен анализ межфайловых зависимостей

**Соответствие:** ~90% → ~95% схеме Joern

### v3.0 (2025-11-16) — Второй этап: поддержка ООП

**КРУПНОЕ ОБНОВЛЕНИЕ: Добавлена поддержка анализа ООП и точное сопоставление с исходным кодом**

**Новые типы узлов:**
- `nodes_field_identifier` (FIELD_IDENTIFIER) — узлы доступа к полям для ООП
- `nodes_member` (MEMBER) — объявления полей классов/структур

**Новые типы рёбер:**
- `edges_binds` (BINDS) — рёбра привязки имён (операторы import/using)
- `edges_binds_to` (BINDS_TO) — обратные рёбра привязки (разрешение имён)

**Новые свойства:**
- OFFSET, OFFSET_END: точное сопоставление по байтам (добавлено к METHOD, TYPE_DECL, IDENTIFIER, FIELD_IDENTIFIER, MEMBER)
- MODIFIER: массив модификаторов доступа (добавлено к METHOD, TYPE_DECL)
- CANONICAL_NAME: нормализованное имя идентификатора (добавлено к FIELD_IDENTIFIER)

**Влияние:**
- Полная поддержка анализа ООП-кода (отслеживание доступа к полям)
- Точное сопоставление с местоположением в исходном коде (на уровне байтов)
- Включён анализ видимости (PUBLIC, PRIVATE, STATIC и т.д.)
- Улучшено разрешение имён переменных и функций
- Включён анализ псевдонимов (канонические имена)

**Соответствие:** ~80% → ~90% схеме Joern

### v2.0 (2025-11-16) — Первый этап: критические обновления

**КРУПНОЕ ОБНОВЛЕНИЕ: Добавлены критически важные компоненты для анализа PDG и SSA**

**Новые типы узлов:**
- `nodes_param_out` (METHOD_PARAMETER_OUT) — выходные параметры для анализа SSA
- `nodes_method_return` (METHOD_RETURN) — формальный параметр возврата

**Новые типы рёбер:**
- `edges_cdg` (Control Dependence Graph) — критически важен для PDG!

**Влияние:**
- Граф зависимостей программы (PDG) теперь полный (DDG + CDG)
- Теперь возможен анализ SSA
- Включено программное срезание (program slicing)
- Улучшен анализ утечки данных (taint analysis)

**Соответствие:** ~70% → ~80% схеме Joern

### v1.0 (2025-11-15) — Первоначальный выпуск {#v10-2025-11-15---initial-release}

- 11 типов узлов (METHOD, CALL, IDENTIFIER, LITERAL, LOCAL, PARAM, RETURN, BLOCK, CONTROL_STRUCTURE, TYPE_DECL, METADATA)
- 10 типов рёбер (AST, CFG, CALL, REF, REACHING_DEF, ARGUMENT, RECEIVER, CONDITION, DOMINATE, POST_DOMINATE)

---

## Расширение: Система семантических тегов {#extension-semantic-tag-system}

### Обзор

Система тегов расширяет CPG за счёт семантических аннотаций для методов и других элементов кода. Теги — это пользовательские расширения (не входящие в спецификацию CPG v1.1), которые позволяют выполнять семантический поиск, классификацию кода и интеллектуальный анализ.

### nodes_tag

Хранит определения тегов (семантические метки для элементов кода).

```
CREATE TABLE nodes_tag (
    id BIGINT PRIMARY KEY,
    name VARCHAR NOT NULL,     -- Категория тега (например, 'subsystem-name', 'security-risk')
    value VARCHAR              -- Значение тега (например, 'executor', 'high')
);

CREATE INDEX idx_tag_name ON nodes_tag(name);
CREATE INDEX idx_tag_value ON nodes_tag(value);
```

**Свойства:**
- NAME: Идентификатор категории тега (уникальное семантическое измерение)
- VALUE: Значение тега в рамках этой категории

### edges_tagged_by

Связывает элементы кода с их семантическими тегами.

```
CREATE TABLE edges_tagged_by (
    src BIGINT,                -- Идентификатор исходного узла (обычно METHOD)
    dst BIGINT,                -- Идентификатор узла тега
    PRIMARY KEY (src, dst)
);

CREATE INDEX idx_tagged_by_src ON edges_tagged_by(src);
CREATE INDEX idx_tagged_by_dst ON edges_tagged_by(dst);
```

**Связь:**
- Источник: любой узел CPG (обычно nodes_method)
- Назначение: запись в nodes_tag

### Категории тегов

| Категория | Описание | Примеры значений |
| --- | --- | --- |
| subsystem-name | Организационная единица кода | ‘executor’, ‘planner’, ‘parser’, ‘storage’ |
| security-risk | Классификация по уровню угрозы безопасности | ‘critical’, ‘high’, ‘medium’, ‘low’ |
| taint-source | Точка входа недоверённых данных | Булева разметка |
| taint-sink | Выход, чувствительный к вопросам безопасности | Булева разметка |
| perf-hotspot | Участки кода, критичные к производительности | Булева разметка |
| allocation-heavy | Методы, интенсивно использующие память | Булева разметка |
| test-coverage | Наличие связанных тестов | Булева разметка |
| cyclomatic-complexity | Метрика сложности кода | Числовые значения (например, ‘15’, ‘25’) |
| function-purpose | Семантическое описание | Произвольный текст описания |
| entry-point | Точка входа в систему | Булева разметка |

### Примеры запросов к тегам

```
-- Найти все методы с критическим уровнем угрозы безопасности
SELECT m.*
FROM nodes_method m
JOIN edges_tagged_by e ON m.id = e.src
JOIN nodes_tag t ON e.dst = t.id
WHERE t.name = 'security-risk' AND t.value = 'critical';

-- Вывести все подсистемы
SELECT DISTINCT t.value as subsystem
FROM nodes_tag t
WHERE t.name = 'subsystem-name'
ORDER BY t.value;

-- Найти методы в определённой подсистеме
SELECT m.full_name, m.filename, m.line_number
FROM nodes_method m
JOIN edges_tagged_by e ON m.id = e.src
JOIN nodes_tag t ON e.dst = t.id
WHERE t.name = 'subsystem-name' AND t.value = 'executor';

-- Найти участки с высокой сложностью
SELECT m.full_name, t.value as complexity
FROM nodes_method m
JOIN edges_tagged_by e ON m.id = e.src
JOIN nodes_tag t ON e.dst = t.id
WHERE t.name = 'cyclomatic-complexity'
  AND CAST(t.value AS INTEGER) > 20
ORDER BY CAST(t.value AS INTEGER) DESC;

-- Подсчитать количество тегов по категориям
SELECT t.name, COUNT(*) as count
FROM nodes_tag t
JOIN edges_tagged_by e ON t.id = e.dst
GROUP BY t.name
ORDER BY count DESC;
```

### Статистика по тегам

В текущей базе данных содержится приблизительно:
- **15,68 млн тегов** в рамках **98 категорий**
- Основные категории: subsystem-name, security-risk, function-purpose
- Теги позволяют выполнять семантический поиск по коду и интеллектуальный анализ

### Примечания по интеграции {#integration-notes}

Теги добавляются после генерации CPG с помощью:
1. **Статического анализа**: Запросы тегов в Joern (`cpg.method.tag.name(...)`)
2. **Обогащения с помощью ИИ**: Генерация описаний назначения функций с помощью LLM
3. **Вычисляемых метрик**: Цикломатическая сложность, полученная из анализа CFG
4. **Ручной аннотации**: Результаты аудита безопасности

Теги расширяют CPG без изменения основной схемы, обеспечивая совместимость со стандартными инструментами CPG и позволяя выполнять расширенный семантический анализ.
