# Кулинарная книга SQL-запросов для DuckDB CPG

Практическая подборка SQL-запросов для типовых задач анализа кода на DuckDB CPG.

## Содержание

1. [Запросы методов](#method-queries)
2. [Анализ вызовов](#call-analysis)
3. [Управление потоком выполнения](#control-flow)
4. [Поток данных](#data-flow)
5. [Анализ файлов](#file-analysis)
6. [Шаблоны безопасности](#security-patterns)
7. [Качество кода](#code-quality)
8. [Статистика](#statistics)
9. [Расширенные шаблоны](#advanced-patterns)
10. [Графовые запросы SQL/PGQ](#sqlpgq-graph-queries)
11. [См. также](#see-also)

## Запросы к методам

### Найти метод по точному имени

```
SELECT id, name, full_name, filename, line_number, signature
FROM nodes_method
WHERE name = 'authenticate'
LIMIT 10;
```

### Найти методы по шаблону

```
SELECT id, name, full_name, filename, line_number
FROM nodes_method
WHERE name LIKE '%process%'
ORDER BY name
LIMIT 50;
```

### Методы по шаблону сигнатуры

```
SELECT name, full_name, signature, filename
FROM nodes_method
WHERE signature LIKE '%char*%'  -- Методы, принимающие параметр char*
ORDER BY name
LIMIT 100;
```

### Внешние и внутренние методы

```
-- Внешние методы (из библиотек)
SELECT name, full_name, COUNT(*) as count
FROM nodes_method
WHERE is_external = true
GROUP BY name, full_name
ORDER BY count DESC
LIMIT 20;

-- Внутренние методы (ваш код)
SELECT filename, COUNT(*) as method_count
FROM nodes_method
WHERE is_external = false
GROUP BY filename
ORDER BY method_count DESC
LIMIT 20;
```

### Методы по количеству строк

```
SELECT
    name,
    filename,
    line_number,
    line_number_end,
    (line_number_end - line_number) as lines_of_code
FROM nodes_method
WHERE line_number_end IS NOT NULL
  AND (line_number_end - line_number) > 50  -- Длинные методы
ORDER BY lines_of_code DESC
LIMIT 20;
```

## Анализ вызовов {#call-analysis}

### Прямые вызываемые функции (Какие функции вызывает X?)

```
SELECT DISTINCT
    callee.name,
    callee.full_name,
    callee.filename,
    callee.line_number
FROM edges_call ec
JOIN nodes_call c ON ec.src = c.id
JOIN nodes_method caller ON c.method_full_name LIKE '%' || caller.name || '%'
JOIN nodes_method callee ON ec.dst = callee.id
WHERE caller.name = 'main'
ORDER BY callee.name
LIMIT 100;
```

### Прямые вызывающие функции (Кто вызывает X?)

```
SELECT DISTINCT
    caller.name,
    caller.full_name,
    caller.filename,
    caller.line_number
FROM edges_call ec
JOIN nodes_call c ON ec.src = c.id
JOIN nodes_method callee ON ec.dst = callee.id
JOIN nodes_method caller ON c.method_full_name LIKE '%' || caller.name || '%'
WHERE callee.name = 'malloc'
ORDER BY caller.name
LIMIT 100;
```

### Цепочка вызовов (транзитивные вызываемые функции)

```
WITH RECURSIVE call_chain AS (
    -- Базовый случай: прямые вызовы из начальной функции
    SELECT
        ec.dst as method_id,
        1 as depth,
        m_start.name as start_method
    FROM edges_call ec
    JOIN nodes_call c ON ec.src = c.id
    JOIN nodes_method m_start ON c.method_full_name LIKE '%' || m_start.name || '%'
    WHERE m_start.name = 'main'

    UNION ALL

    -- Рекурсивный случай: продолжаем цепочку
    SELECT
        ec2.dst,
        cc.depth + 1,
        cc.start_method
    FROM edges_call ec2
    JOIN nodes_call c2 ON ec2.src = c2.id
    JOIN nodes_method m2 ON c2.method_full_name LIKE '%' || m2.name || '%'
    JOIN call_chain cc ON m2.id = cc.method_id
    WHERE cc.depth < 5
)
SELECT DISTINCT
    m.name,
    m.full_name,
    MIN(cc.depth) as min_depth
FROM call_chain cc
JOIN nodes_method m ON cc.method_id = m.id
GROUP BY m.id, m.name, m.full_name
ORDER BY min_depth, m.name
LIMIT 100;
```

### Наиболее активные вызывающие функции (функции, совершающие наибольшее число вызовов)

```
SELECT
    m.name,
    m.full_name,
    m.filename,
    COUNT(DISTINCT c.id) as outgoing_calls
FROM nodes_method m
LEFT JOIN nodes_call c ON c.method_full_name LIKE '%' || m.name || '%'
GROUP BY m.id, m.name, m.full_name, m.filename
ORDER BY outgoing_calls DESC
LIMIT 20;
```

### Наиболее часто вызываемые функции

```
SELECT
    m.name,
    m.full_name,
    m.filename,
    COUNT(ec.src) as incoming_calls
FROM nodes_method m
LEFT JOIN edges_call ec ON m.id = ec.dst
GROUP BY m.id, m.name, m.full_name, m.filename
ORDER BY incoming_calls DESC
LIMIT 20;
```

### Пары вызовов (частые шаблоны «вызывающий — вызываемый»)

```
SELECT
    caller.name as caller,
    callee.name as callee,
    COUNT(*) as frequency
FROM edges_call ec
JOIN nodes_call c ON ec.src = c.id
JOIN nodes_method caller ON c.method_full_name LIKE '%' || caller.name || '%'
JOIN nodes_method callee ON ec.dst = callee.id
GROUP BY caller.name, callee.name
ORDER BY frequency DESC
LIMIT 50;
```

### Листовые функции (функции без исходящих вызовов)

```
SELECT
    m.name,
    m.full_name,
    m.filename
FROM nodes_method m
WHERE NOT EXISTS (
    SELECT 1
    FROM nodes_call c
    WHERE c.method_full_name LIKE '%' || m.name || '%'
)
AND m.is_external = false
ORDER BY m.name
LIMIT 100;
```

### Корневые функции (функции, которые никто не вызывает)

```
SELECT
    m.name,
    m.full_name,
    m.filename,
    m.line_number
FROM nodes_method m
WHERE NOT EXISTS (
    SELECT 1
    FROM edges_call ec
    WHERE ec.dst = m.id
)
AND m.is_external = false
ORDER BY m.filename, m.line_number
LIMIT 100;
```

## Управление потоком выполнения {#control-flow}

### Методы с ветвлениями

```
-- Найти методы, содержащие структуры IF/SWITCH, через AST
SELECT DISTINCT
    m.name,
    m.full_name,
    m.filename,
    COUNT(DISTINCT cs.id) as branch_count
FROM nodes_method m
JOIN edges_ast ast ON m.id = ast.src
JOIN nodes_control_structure cs ON ast.dst = cs.id
WHERE cs.control_structure_type IN ('IF', 'SWITCH')
GROUP BY m.id, m.name, m.full_name, m.filename
ORDER BY branch_count DESC
LIMIT 20;
```

### Методы с циклами

```
-- Найти методы, содержащие структуры циклов, через AST
SELECT DISTINCT
    m.name,
    m.full_name,
    m.filename,
    COUNT(DISTINCT cs.id) as loop_count
FROM nodes_method m
JOIN edges_ast ast ON m.id = ast.src
JOIN nodes_control_structure cs ON ast.dst = cs.id
WHERE cs.control_structure_type IN ('WHILE', 'FOR', 'DO')
GROUP BY m.id, m.name, m.full_name, m.filename
ORDER BY loop_count DESC
LIMIT 20;
```

### Приближённая оценка цикломатической сложности

```
-- Оценка сложности по количеству управляющих структур
SELECT
    m.name,
    m.filename,
    1 + COUNT(DISTINCT cs.id) as approx_complexity
FROM nodes_method m
LEFT JOIN edges_ast ast ON m.id = ast.src
LEFT JOIN nodes_control_structure cs ON ast.dst = cs.id
WHERE m.is_external = false
GROUP BY m.id, m.name, m.filename
ORDER BY approx_complexity DESC
LIMIT 30;
```

### Обход графа потока управления (SQL/PGQ)

```
-- Следование по рёбрам CFG с использованием графа свойств
FROM GRAPH_TABLE(cpg
    MATCH (start:METHOD)-[:CFG*1..10]->(node:CPG_NODE)
    WHERE start.name = 'process_request'
    COLUMNS (
        start.name AS method_name,
        node.id AS node_id,
        node.node_type
    )
)
LIMIT 100;
```

## Поток данных {#data-flow}

### Пути потока переменных

```
WITH RECURSIVE var_flow AS (
    -- Базовый случай: начальные определения
    SELECT src, dst, variable, 1 as depth
    FROM edges_reaching_def
    WHERE variable = 'password'

    UNION ALL

    -- Рекурсивный случай: продолжение потока
    SELECT erd.src, erd.dst, erd.variable, vf.depth + 1
    FROM edges_reaching_def erd
    JOIN var_flow vf ON erd.src = vf.dst
    WHERE vf.depth < 10
)
SELECT
    variable,
    COUNT(DISTINCT src) as definition_points,
    COUNT(DISTINCT dst) as use_points,
    MAX(depth) as max_depth
FROM var_flow
GROUP BY variable;
```

### Загрязнённые параметры

```
-- Методы, получающие загрязнённые входные данные
SELECT DISTINCT
    m.name,
    m.full_name,
    p.name as parameter_name,
    p.type_full_name as parameter_type
FROM nodes_method m
JOIN nodes_param p ON p.method_full_name = m.full_name
WHERE p.name IN ('userInput', 'request', 'input', 'data')
ORDER BY m.name
LIMIT 50;
```

## Анализ файлов {#file-analysis}

### Методы по файлам

```
SELECT
    filename,
    COUNT(*) as method_count,
    SUM(CASE WHEN is_external THEN 1 ELSE 0 END) as external_methods,
    SUM(CASE WHEN is_external THEN 0 ELSE 1 END) as internal_methods
FROM nodes_method
GROUP BY filename
ORDER BY method_count DESC
LIMIT 30;
```

### Файлы по активности вызовов

```
SELECT
    m.filename,
    COUNT(DISTINCT c.id) as total_calls,
    COUNT(DISTINCT c.name) as unique_calls
FROM nodes_method m
JOIN nodes_call c ON c.method_full_name LIKE '%' || m.name || '%'
GROUP BY m.filename
ORDER BY total_calls DESC
LIMIT 20;
```

### Вызовы между файлами

```
SELECT
    caller.filename as from_file,
    callee.filename as to_file,
    COUNT(*) as call_count
FROM edges_call ec
JOIN nodes_call c ON ec.src = c.id
JOIN nodes_method caller ON c.method_full_name LIKE '%' || caller.name || '%'
JOIN nodes_method callee ON ec.dst = callee.id
WHERE caller.filename != callee.filename
GROUP BY caller.filename, callee.filename
ORDER BY call_count DESC
LIMIT 50;
```

## Шаблоны безопасности {#security-patterns}

### Проблемы управления памятью

```
-- Методы, которые вызывают malloc, но не вызывают free
SELECT DISTINCT m.name, m.full_name
FROM nodes_method m
WHERE EXISTS (
    SELECT 1 FROM nodes_call c
    WHERE c.method_full_name LIKE '%' || m.name || '%'
      AND c.name = 'malloc'
)
AND NOT EXISTS (
    SELECT 1 FROM nodes_call c
    WHERE c.method_full_name LIKE '%' || m.name || '%'
      AND c.name = 'free'
)
LIMIT 50;
```

### Опасные вызовы функций

```
SELECT
    m.name as caller,
    m.filename,
    c.name as dangerous_function,
    m.line_number
FROM nodes_call c
JOIN nodes_method m ON c.method_full_name LIKE '%' || m.name || '%'
WHERE c.name IN ('strcpy', 'sprintf', 'gets', 'system', 'eval')
ORDER BY m.filename, m.line_number
LIMIT 100;
```

### Кандидаты на SQL-инъекцию

```
SELECT DISTINCT
    m.name,
    m.full_name,
    m.filename
FROM nodes_method m
WHERE EXISTS (
    -- Есть вызовы, связанные с SQL
    SELECT 1 FROM nodes_call c
    WHERE c.method_full_name LIKE '%' || m.name || '%'
      AND (c.name LIKE '%query%' OR c.name LIKE '%execute%')
)
AND EXISTS (
    -- Получает пользовательский ввод
    SELECT 1 FROM nodes_param p
    WHERE p.method_full_name = m.full_name
      AND (p.name LIKE '%input%' OR p.name LIKE '%request%')
)
LIMIT 50;
```

### Кандидаты на обход аутентификации

```
SELECT
    m.name,
    m.full_name,
    m.filename
FROM nodes_method m
WHERE m.name LIKE '%auth%'
  OR m.name LIKE '%login%'
  OR m.name LIKE '%verify%'
ORDER BY m.name
LIMIT 100;
```

## Качество кода {#code-quality}

### Богатые методы (слишком длинные)

```
SELECT
    name,
    filename,
    line_number,
    line_number_end,
    (line_number_end - line_number) as loc
FROM nodes_method
WHERE line_number_end IS NOT NULL
  AND (line_number_end - line_number) > 100
ORDER BY loc DESC
LIMIT 20;
```

### Высокий fan-out (слишком много вызовов)

```
SELECT
    m.name,
    m.filename,
    COUNT(DISTINCT c.id) as fan_out
FROM nodes_method m
JOIN nodes_call c ON c.method_full_name LIKE '%' || m.name || '%'
GROUP BY m.id, m.name, m.filename
HAVING COUNT(DISTINCT c.id) > 10
ORDER BY fan_out DESC
LIMIT 20;
```

### Высокий fan-in (слишком много вызывающих)

```
SELECT
    m.name,
    m.filename,
    COUNT(DISTINCT ec.src) as fan_in
FROM nodes_method m
JOIN edges_call ec ON m.id = ec.dst
GROUP BY m.id, m.name, m.filename
HAVING COUNT(DISTINCT ec.src) > 10
ORDER BY fan_in DESC
LIMIT 20;
```

### Неиспользуемые методы (потенциальный мёртвый код)

```
SELECT
    m.name,
    m.full_name,
    m.filename
FROM nodes_method m
WHERE m.is_external = false
  AND NOT EXISTS (
      SELECT 1 FROM edges_call ec WHERE ec.dst = m.id
  )
  AND m.name NOT IN ('main', 'test%')  -- Исключаем точки входа
ORDER BY m.filename, m.name
LIMIT 100;
```

## Статистика {#statistics}

### Обзор CPG

```
SELECT
    (SELECT COUNT(*) FROM nodes_method) as total_methods,
    (SELECT COUNT(*) FROM nodes_method WHERE is_external = false) as internal_methods,
    (SELECT COUNT(*) FROM nodes_call) as total_calls,
    (SELECT COUNT(*) FROM edges_call) as call_edges,
    (SELECT COUNT(DISTINCT filename) FROM nodes_method) as file_count;
```

### Распределение вызовов

```
SELECT
    call_count_bucket,
    COUNT(*) as methods_in_bucket
FROM (
    SELECT
        m.id,
        CASE
            WHEN call_count = 0 THEN '0 вызовов'
            WHEN call_count <= 5 THEN '1-5 вызовов'
            WHEN call_count <= 10 THEN '6-10 вызовов'
            WHEN call_count <= 20 THEN '11-20 вызовов'
            ELSE '20+ вызовов'
        END as call_count_bucket
    FROM nodes_method m
    LEFT JOIN (
        SELECT
            m2.id,
            COUNT(c.id) as call_count
        FROM nodes_method m2
        LEFT JOIN nodes_call c ON c.method_full_name LIKE '%' || m2.name || '%'
        GROUP BY m2.id
    ) counts ON m.id = counts.id
)
GROUP BY call_count_bucket
ORDER BY
    CASE call_count_bucket
        WHEN '0 вызовов' THEN 1
        WHEN '1-5 вызовов' THEN 2
        WHEN '6-10 вызовов' THEN 3
        WHEN '11-20 вызовов' THEN 4
        ELSE 5
    END;
```

### Распределение языков (по расширению файла)

```
SELECT
    CASE
        WHEN filename LIKE '%.c' THEN 'C'
        WHEN filename LIKE '%.cpp' OR filename LIKE '%.cc' THEN 'C++'
        WHEN filename LIKE '%.java' THEN 'Java'
        WHEN filename LIKE '%.py' THEN 'Python'
        WHEN filename LIKE '%.js' THEN 'JavaScript'
        ELSE 'Другое'
    END as language,
    COUNT(*) as method_count
FROM nodes_method
WHERE is_external = false
GROUP BY language
ORDER BY method_count DESC;
```

### Сложность сигнатур методов

```
SELECT
    m.name,
    m.signature,
    LENGTH(m.signature) as sig_length,
    (LENGTH(m.signature) - LENGTH(REPLACE(m.signature, ',', ''))) + 1 as param_count
FROM nodes_method m
WHERE m.signature IS NOT NULL
  AND m.is_external = false
ORDER BY param_count DESC, sig_length DESC
LIMIT 30;
```

## Расширенные шаблоны {#advanced-patterns}

### Поиск цепочек вызовов методов (A → B → C)

```
WITH chain AS (
    SELECT
        caller.name as method_a,
        intermediate.name as method_b,
        callee.name as method_c
    FROM edges_call ec1
    JOIN nodes_call c1 ON ec1.src = c1.id
    JOIN nodes_method caller ON c1.method_full_name LIKE '%' || caller.name || '%'
    JOIN nodes_method intermediate ON ec1.dst = intermediate.id
    JOIN nodes_call c2 ON c2.method_full_name LIKE '%' || intermediate.name || '%'
    JOIN edges_call ec2 ON c2.id = ec2.src
    JOIN nodes_method callee ON ec2.dst = callee.id
    WHERE caller.name = 'main'
)
SELECT DISTINCT method_a, method_b, method_c
FROM chain
LIMIT 100;
```

### Связные компоненты (кластеры методов)

```
-- Найти методы в одном графе вызовов
WITH RECURSIVE component AS (
    SELECT id, name, id as root
    FROM nodes_method
    WHERE name = 'main'

    UNION

    SELECT m.id, m.name, c.root
    FROM nodes_method m
    JOIN edges_call ec ON m.id = ec.dst OR m.id IN (
        SELECT m2.id FROM nodes_method m2
        JOIN nodes_call nc ON nc.method_full_name LIKE '%' || m2.name || '%'
        WHERE nc.id = ec.src
    )
    JOIN component c ON ec.dst = c.id OR ec.src = c.id
)
SELECT
    root,
    COUNT(DISTINCT id) as component_size,
    STRING_AGG(DISTINCT name, ', ') as methods
FROM component
GROUP BY root
ORDER BY component_size DESC
LIMIT 10;
```

## Советы по использованию

1. **Всегда добавляйте LIMIT**, чтобы избежать возврата миллионов строк
2. **Используйте конкретные столбцы** вместо SELECT *
3. **Сначала тестируйте на небольших наборах данных**
4. **Добавляйте условия WHERE**, чтобы отфильтровать нерелевантные результаты
5. **Используйте EXPLAIN** для проверки планов выполнения запросов
6. **Контролируйте время выполнения** (для большинства запросов должно быть < 100 мс)

## Заметки о производительности

- Простые запросы: 1–3 мс
- JOIN’ы (1–2 таблицы): 2–5 мс
- Агрегации: 4–8 мс
- Рекурсивные CTE: 10–50 мс (зависит от глубины)

Все запросы выполнялись на тестовой базе данных с 5 методами и 4 вызовами.

Производительность растёт сублинейно с увеличением объёма данных благодаря использованию индексов.

## Графовые запросы на SQL/PGQ {#sqlpgq-graph-queries}

Расширение SQL/PGQ в DuckDB позволяет выполнять интуитивные запросы для обхода графов.

### Обход графа вызовов

```
-- Найти все методы, вызываемые из main (прямые и косвенные)
FROM GRAPH_TABLE(cpg
    MATCH (caller:METHOD)-[:CALLS*1..3]->(callee:METHOD)
    WHERE caller.name = 'main'
    COLUMNS (
        caller.name AS caller,
        callee.name AS callee,
        callee.filename
    )
)
LIMIT 100;
```

### Анализ потока данных

```
-- Отслеживание потока данных через достижимые определения
FROM GRAPH_TABLE(cpg
    MATCH (src:IDENTIFIER)-[:REACHING_DEF*1..5]->(sink:CALL_NODE)
    WHERE src.name = 'user_input'
    COLUMNS (
        src.name AS source_var,
        sink.name AS sink_function,
        sink.line_number
    )
)
LIMIT 100;
```

### Обход AST

```
-- Найти все узлы, находящиеся под методом в AST
FROM GRAPH_TABLE(cpg
    MATCH (method:METHOD)-[:AST*1..5]->(child:CPG_NODE)
    WHERE method.name = 'authenticate'
    COLUMNS (
        method.name AS method_name,
        child.id AS child_id,
        child.node_type
    )
)
LIMIT 100;
```

### Иерархия типов

```
-- Найти отношения наследования
FROM GRAPH_TABLE(cpg
    MATCH (derived:TYPE_DECL)-[:INHERITS_FROM]->(base:TYPE_NODE)
    COLUMNS (
        derived.name AS derived_type,
        base.full_name AS base_type
    )
)
```

---

## Дальнейшие действия

- Попробуйте эти запросы в своей базе данных CPG
- Измените параметры в соответствии со своими требованиями
- Комбинируйте шаблоны для сложного анализа
- Контролируйте производительность и оптимизируйте при необходимости
- Добавьте свои собственные шаблоны в эту книгу рецептов!

---

## Смотрите также

- [Модули анализа](./ANALYSIS_MODULES.md) — документация CFGAnalyzer, FieldSensitiveTracer
- [Руководство по экспорту CPG](../guides/CPG_EXPORT.md) — экспорт CPG в DuckDB
- [Система гипотез](./HYPOTHESIS_SYSTEM.md) — генерация гипотез безопасности
- [Документация по DuckDB SQL/PGQ](https://duckdb.org/docs/extensions/duckpgq)
- [Спецификация CPG v1.1](https://cpg.joern.io/)
