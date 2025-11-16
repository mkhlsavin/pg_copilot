# DuckDB CPG Schema Compliance Report

**Date:** 2025-11-16
**Comparison:** DuckDB Schema vs. Joern Original Schema (CPG Spec v1.1)

## Executive Summary

Текущая схема DuckDB реализует **основные узлы и рёбра** CPG спецификации v1.1, но **отсутствуют важные компоненты** для полноценной совместимости с оригинальной схемой Joern.

**Уровень соответствия:** ~70% (базовая функциональность)

**Критические несоответствия:**
- Отсутствуют 10+ типов узлов
- Отсутствует CDG (Control Dependence Graph) - критично для PDG
- Отсутствуют рёбра для связывания типов и файлов
- Отсутствуют некоторые важные свойства

---

## Детальное сравнение

### 1. Типы узлов (Node Types)

#### ✅ Реализованы в DuckDB (11 типов)

| DuckDB Table | Joern Node | Status | Completeness |
|--------------|------------|---------|--------------|
| `nodes_method` | METHOD | ✅ | 95% - отсутствует OFFSET |
| `nodes_call` | CALL | ✅ | 90% - отсутствует ARGUMENT_NAME |
| `nodes_identifier` | IDENTIFIER | ✅ | 100% |
| `nodes_literal` | LITERAL | ✅ | 100% |
| `nodes_local` | LOCAL | ✅ | 100% |
| `nodes_param` | METHOD_PARAMETER_IN | ✅ | 100% |
| `nodes_return` | RETURN | ✅ | 100% |
| `nodes_block` | BLOCK | ✅ | 100% |
| `nodes_control_structure` | CONTROL_STRUCTURE | ✅ | 100% |
| `nodes_type_decl` | TYPE_DECL | ✅ | 90% - отсутствует OFFSET |
| `nodes_metadata` | META_DATA | ✅ | 100% |

#### ❌ Отсутствуют важные узлы (10+ типов)

| Missing Node | Purpose | Criticality | Impact |
|--------------|---------|-------------|--------|
| **METHOD_PARAMETER_OUT** | Выходные параметры методов | HIGH | PDG/SSA analysis incomplete |
| **METHOD_RETURN** | Возвращаемое значение метода | HIGH | PDG incomplete |
| **FIELD_IDENTIFIER** | Доступ к полям класса/структуры | HIGH | OOP analysis impossible |
| **MEMBER** | Поля классов/структур | HIGH | Type analysis incomplete |
| **METHOD_REF** | Ссылки на методы (function pointers) | MEDIUM | Higher-order functions unsupported |
| **TYPE_REF** | Ссылки на типы | MEDIUM | Generic types unsupported |
| **NAMESPACE_BLOCK** | Блоки пространств имён | MEDIUM | Namespace analysis incomplete |
| **FILE** | Файлы исходного кода | MEDIUM | File-level queries incomplete |
| **UNKNOWN** | Неизвестные узлы AST | LOW | Error handling incomplete |
| **JUMP_TARGET** | Метки для goto | LOW | Rare pattern |
| **ANNOTATION** | Аннотации/атрибуты (Java @, C# []) | MEDIUM | Metadata analysis impossible |
| **TYPE_PARAMETER** | Параметры generic типов | MEDIUM | Generic analysis impossible |
| **TYPE_ARGUMENT** | Аргументы generic типов | MEDIUM | Generic analysis impossible |
| **MODIFIER** | Модификаторы (public, static, etc.) | MEDIUM | Visibility analysis incomplete |
| **COMMENT** | Комментарии в коде | LOW | Documentation analysis missing |
| **BINDING** | Связывание переменных | MEDIUM | Variable resolution incomplete |

**Рекомендация:** Добавить как минимум HIGH-priority узлы (METHOD_PARAMETER_OUT, METHOD_RETURN, FIELD_IDENTIFIER, MEMBER).

---

### 2. Типы рёбер (Edge Types)

#### ✅ Реализованы в DuckDB (10 типов)

| DuckDB Table | Joern Edge | Purpose | Status |
|--------------|------------|---------|---------|
| `edges_ast` | AST | Syntax tree | ✅ 100% |
| `edges_cfg` | CFG | Control flow | ✅ 100% |
| `edges_call` | CALL | Call graph | ✅ 100% |
| `edges_ref` | REF | Variable references | ✅ 100% |
| `edges_reaching_def` | REACHING_DEF | Data flow | ✅ 100% |
| `edges_argument` | ARGUMENT | Call arguments | ✅ 100% |
| `edges_receiver` | RECEIVER | Method receiver | ✅ 100% |
| `edges_condition` | CONDITION | Control conditions | ✅ 100% |
| `edges_dominate` | DOMINATE | Control dominators | ✅ 100% |
| `edges_post_dominate` | POST_DOMINATE | Post-dominators | ✅ 100% |

#### ❌ Отсутствуют критические рёбра

| Missing Edge | Purpose | Criticality | Impact |
|--------------|---------|-------------|--------|
| **CDG** | Control Dependence Graph | **CRITICAL** | PDG incomplete! |
| **BINDS** | Variable binding | HIGH | Variable resolution incomplete |
| **BINDS_TO** | Reverse binding | HIGH | Variable resolution incomplete |
| **SOURCE_FILE** | Method to file link | MEDIUM | File queries incomplete |
| **CONTAINS** | Container relationships | MEDIUM | Hierarchy queries incomplete |
| **INHERITS_FROM** | Type inheritance | MEDIUM | OOP analysis incomplete |
| **ALIAS_OF** | Type aliases | LOW | Type resolution incomplete |
| **CAPTURE** | Closure captures | LOW | Lambda analysis incomplete |
| **CAPTURED_BY** | Reverse capture | LOW | Lambda analysis incomplete |
| **EVAL_TYPE** | Dynamic types | LOW | Dynamic type analysis incomplete |

**Критическая проблема:** Отсутствие **CDG** делает невозможным построение полного Program Dependence Graph (PDG), который является ключевым для многих видов анализа (slicing, security analysis, etc.).

---

### 3. Свойства узлов (Properties)

#### ✅ Реализованные свойства

Большинство базовых свойств реализовано:
- ✅ NAME, FULL_NAME
- ✅ CODE, SIGNATURE
- ✅ LINE_NUMBER, COLUMN_NUMBER, LINE_NUMBER_END, COLUMN_NUMBER_END
- ✅ TYPE_FULL_NAME
- ✅ IS_EXTERNAL
- ✅ AST_PARENT_TYPE, AST_PARENT_FULL_NAME
- ✅ ORDER (order_index)
- ✅ INDEX (для параметров)
- ✅ IS_VARIADIC
- ✅ EVALUATION_STRATEGY
- ✅ HASH
- ✅ DISPATCH_TYPE

#### ❌ Отсутствующие важные свойства

| Missing Property | Used In | Purpose | Impact |
|-----------------|---------|---------|--------|
| **OFFSET** | All AST nodes | Byte offset в файле | Precise source mapping impossible |
| **OFFSET_END** | All AST nodes | Конец byte offset | Precise source mapping impossible |
| **PARSER_TYPE_NAME** | All AST nodes | Оригинальное имя AST узла | Parser-specific analysis impossible |
| **MODIFIER** | METHOD, TYPE_DECL, MEMBER | Модификаторы доступа | Visibility analysis impossible |
| **DYNAMIC_TYPE_HINT_FULL_NAME** | Expressions | Динамический тип | Dynamic analysis incomplete |
| **POSSIBLE_TYPES** | Expressions | Возможные типы | Type inference incomplete |
| **ARGUMENT_NAME** | CALL arguments | Именованные параметры | Named parameter support missing |
| **INHERITS_FROM_TYPE_FULL_NAME** | TYPE_DECL | Базовые типы | ✅ Есть! (но как массив) |
| **ALIAS_TYPE_FULL_NAME** | TYPE_DECL | Тип-алиас | ✅ Есть! |
| **LANGUAGE** | META_DATA | Язык программирования | ✅ Есть! |
| **VERSION** | META_DATA | Версия CPG spec | ✅ Есть! |
| **OVERLAYS** | META_DATA | Применённые overlays | ✅ Есть! |

**Рекомендация:** Добавить OFFSET/OFFSET_END для точного source mapping, MODIFIER для visibility analysis.

---

### 4. Константы и перечисления

#### Отсутствующие константы (должны быть документированы)

| Constant Set | Purpose | Missing Values |
|--------------|---------|----------------|
| **DispatchTypes** | Call dispatch mechanism | STATIC_DISPATCH, DYNAMIC_DISPATCH, INLINED (частично есть) |
| **EvaluationStrategies** | Parameter passing | BY_VALUE, BY_REFERENCE, BY_SHARING (есть в schema) |
| **ControlStructureTypes** | Control flow types | BREAK, CONTINUE, DO, WHILE, FOR, GOTO, IF, ELSE, TRY, THROW, SWITCH (документировано) |
| **Operators** | Operator types | +, -, *, /, ==, !=, <, >, etc. (отсутствует) |
| **ModifierTypes** | Access modifiers | PUBLIC, PRIVATE, PROTECTED, STATIC, ABSTRACT, NATIVE, etc. (отсутствует) |

---

## Критические проблемы

### 🔴 Проблема #1: Отсутствие CDG (Control Dependence Graph)

**Серьёзность:** CRITICAL

**Описание:** PDG (Program Dependence Graph) = DDG (Data Dependence Graph) + CDG (Control Dependence Graph). Без CDG невозможно:
- Program slicing
- Security taint analysis (полноценный)
- Dependence-based program transformations
- Compiler optimizations

**Текущее состояние:**
- ✅ DDG реализован через `edges_reaching_def`
- ❌ CDG отсутствует полностью

**Из Joern schema (Pdg.scala):**
```scala
val cdg = builder
  .addEdgeType(
    name = "CDG",
    comment = "A CDG edge expresses that the destination node is control dependent on the source node."
  )
```

**Решение:** Добавить `edges_cdg` таблицу:
```sql
CREATE TABLE edges_cdg (
    src BIGINT, -- Control structure node id
    dst BIGINT, -- Dependent node id
    PRIMARY KEY (src, dst)
);
```

---

### 🟠 Проблема #2: Отсутствие METHOD_PARAMETER_OUT

**Серьёзность:** HIGH

**Описание:** В Joern каждый METHOD_PARAMETER_IN имеет соответствующий METHOD_PARAMETER_OUT для SSA (Static Single Assignment) анализа. Без этого:
- Data flow analysis неполный
- SSA form невозможно построить
- Interprocedural analysis ограничен

**Текущее состояние:**
- ✅ nodes_param (METHOD_PARAMETER_IN) реализован
- ❌ METHOD_PARAMETER_OUT отсутствует

**Решение:** Добавить `nodes_param_out`:
```sql
CREATE TABLE nodes_param_out (
    id BIGINT PRIMARY KEY,
    name VARCHAR,
    type_full_name VARCHAR,
    code TEXT,
    order_index INTEGER,
    index INTEGER,
    is_variadic BOOLEAN,
    evaluation_strategy VARCHAR
);
```

---

### 🟠 Проблема #3: Отсутствие FIELD_IDENTIFIER и MEMBER

**Серьёзность:** HIGH

**Описание:** Без FIELD_IDENTIFIER и MEMBER невозможно анализировать:
- Доступ к полям объектов (obj.field)
- Структуры классов
- OOP patterns

**Решение:** Добавить оба типа узлов:
```sql
-- Поля классов/структур (объявления)
CREATE TABLE nodes_member (
    id BIGINT PRIMARY KEY,
    name VARCHAR,
    type_full_name VARCHAR,
    code TEXT,
    order_index INTEGER
);

-- Доступ к полям (использование)
CREATE TABLE nodes_field_identifier (
    id BIGINT PRIMARY KEY,
    canonical_name VARCHAR,
    code TEXT,
    line_number INTEGER,
    column_number INTEGER,
    order_index INTEGER,
    argument_index INTEGER
);
```

---

### 🟡 Проблема #4: Отсутствие FILE и NAMESPACE_BLOCK

**Серьёзность:** MEDIUM

**Описание:** Без FILE и NAMESPACE_BLOCK:
- Файловые запросы неполные (какие методы в файле?)
- Namespace analysis невозможен
- Модульная структура проекта не отражена

**Решение:** Добавить оба типа:
```sql
CREATE TABLE nodes_file (
    id BIGINT PRIMARY KEY,
    name VARCHAR,
    hash VARCHAR,
    content TEXT, -- Опционально, содержимое файла
    order_index INTEGER
);

CREATE TABLE nodes_namespace_block (
    id BIGINT PRIMARY KEY,
    name VARCHAR,
    full_name VARCHAR,
    filename VARCHAR,
    order_index INTEGER
);
```

---

## Рекомендации по улучшению

### Фаза 1: Критические дополнения (CRITICAL)

**Приоритет:** НЕМЕДЛЕННО

1. **Добавить CDG edges:**
   ```sql
   CREATE TABLE edges_cdg (
       src BIGINT,
       dst BIGINT,
       PRIMARY KEY (src, dst)
   );
   CREATE INDEX idx_cdg_src ON edges_cdg(src);
   CREATE INDEX idx_cdg_dst ON edges_cdg(dst);
   ```

2. **Добавить METHOD_PARAMETER_OUT:**
   ```sql
   CREATE TABLE nodes_param_out (
       id BIGINT PRIMARY KEY,
       name VARCHAR,
       type_full_name VARCHAR,
       code TEXT,
       order_index INTEGER,
       index INTEGER,
       evaluation_strategy VARCHAR
   );
   ```

3. **Добавить METHOD_RETURN (node, not statement):**
   ```sql
   CREATE TABLE nodes_method_return (
       id BIGINT PRIMARY KEY,
       type_full_name VARCHAR,
       code TEXT,
       order_index INTEGER,
       evaluation_strategy VARCHAR
   );
   ```

**Обоснование:** Без этих компонентов PDG неполный, что делает многие типы анализа невозможными.

---

### Фаза 2: Важные дополнения (HIGH)

**Приоритет:** В течение недели

1. **Добавить FIELD_IDENTIFIER и MEMBER** (см. выше)
2. **Добавить свойства OFFSET/OFFSET_END:**
   ```sql
   ALTER TABLE nodes_method ADD COLUMN offset INTEGER;
   ALTER TABLE nodes_method ADD COLUMN offset_end INTEGER;
   -- Repeat for all AST node types
   ```
3. **Добавить MODIFIER свойство:**
   ```sql
   ALTER TABLE nodes_method ADD COLUMN modifier VARCHAR[];
   ALTER TABLE nodes_type_decl ADD COLUMN modifier VARCHAR[];
   ```
4. **Добавить BINDS/BINDS_TO edges:**
   ```sql
   CREATE TABLE edges_binds (
       src BIGINT,  -- BINDING node
       dst BIGINT,  -- METHOD or TYPE_DECL
       PRIMARY KEY (src, dst)
   );
   CREATE TABLE edges_binds_to (
       src BIGINT,  -- Variable reference
       dst BIGINT,  -- BINDING node
       PRIMARY KEY (src, dst)
   );
   ```

---

### Фаза 3: Средние дополнения (MEDIUM)

**Приоритет:** В течение месяца

1. **Добавить FILE и NAMESPACE_BLOCK** (см. выше)
2. **Добавить METHOD_REF и TYPE_REF:**
   ```sql
   CREATE TABLE nodes_method_ref (
       id BIGINT PRIMARY KEY,
       method_full_name VARCHAR,
       code TEXT,
       order_index INTEGER,
       argument_index INTEGER
   );

   CREATE TABLE nodes_type_ref (
       id BIGINT PRIMARY KEY,
       type_full_name VARCHAR,
       code TEXT,
       order_index INTEGER,
       argument_index INTEGER
   );
   ```
3. **Добавить ANNOTATION support:**
   ```sql
   CREATE TABLE nodes_annotation (
       id BIGINT PRIMARY KEY,
       name VARCHAR,
       full_name VARCHAR,
       code TEXT,
       order_index INTEGER
   );
   ```
4. **Добавить SOURCE_FILE edge:**
   ```sql
   CREATE TABLE edges_source_file (
       src BIGINT,  -- METHOD or TYPE_DECL
       dst BIGINT,  -- FILE node
       PRIMARY KEY (src, dst)
   );
   ```

---

### Фаза 4: Дополнительные улучшения (LOW)

**Приоритет:** По необходимости

1. UNKNOWN, JUMP_TARGET nodes
2. TYPE_PARAMETER, TYPE_ARGUMENT nodes
3. CAPTURE/CAPTURED_BY edges
4. COMMENT nodes
5. INHERITS_FROM edges
6. ALIAS_OF edges

---

## Совместимость с Joern CPGQL

### Текущая совместимость: ~70%

**Что работает:**
- ✅ Базовые запросы методов: `cpg.method.name("foo")`
- ✅ Базовые call graph запросы: `cpg.method.callOut`
- ✅ Базовый data flow: `cpg.identifier.reachingDef`
- ✅ Control flow: `cpg.method.cfgNext`

**Что НЕ работает без дополнений:**
- ❌ Program slicing (нет CDG)
- ❌ OOP analysis (нет FIELD_IDENTIFIER, MEMBER)
- ❌ Полный PDG (нет CDG, METHOD_PARAMETER_OUT)
- ❌ Namespace queries (нет NAMESPACE_BLOCK)
- ❌ File-level queries (нет FILE)
- ❌ Generic type analysis (нет TYPE_PARAMETER/ARGUMENT)
- ❌ Annotation queries (нет ANNOTATION)

---

## План действий

### Немедленно (1-2 дня):

1. ✅ Прочитать и понять Joern schema (DONE)
2. ⚠️ Добавить **CDG edges** - КРИТИЧНО!
3. ⚠️ Добавить **METHOD_PARAMETER_OUT** - КРИТИЧНО!
4. ⚠️ Добавить **METHOD_RETURN node** - КРИТИЧНО!
5. ⚠️ Обновить экспортер для поддержки новых компонентов

### На этой неделе (3-7 дней):

6. Добавить FIELD_IDENTIFIER и MEMBER
7. Добавить OFFSET/OFFSET_END свойства
8. Добавить MODIFIER свойство
9. Добавить BINDS edges
10. Обновить документацию

### В течение месяца:

11. Добавить FILE и NAMESPACE_BLOCK
12. Добавить METHOD_REF и TYPE_REF
13. Добавить ANNOTATION support
14. Добавить SOURCE_FILE edges
15. Полное покрытие тестами

---

## Выводы

**Текущая схема DuckDB:**
- ✅ Покрывает базовые use cases (70% функциональности)
- ✅ Хорошо продумана и структурирована
- ❌ Не хватает критических компонентов для полной совместимости
- ❌ PDG неполный (отсутствует CDG)
- ❌ OOP analysis невозможен (нет FIELD_IDENTIFIER, MEMBER)

**Главная рекомендация:**

**Немедленно добавить CDG edges** - это критично для PDG и делает разницу между "toy implementation" и "production-ready CPG database".

**Вторая приоритетная задача:**

Добавить **METHOD_PARAMETER_OUT** и **METHOD_RETURN** для полноценного data flow analysis.

**Третья приоритетная задача:**

Добавить **FIELD_IDENTIFIER** и **MEMBER** для OOP analysis.

После этих дополнений схема будет на уровне ~90% совместимости с Joern.

---

**Автор:** Claude Code
**Дата:** 2025-11-16
**Статус:** Требуется действие
