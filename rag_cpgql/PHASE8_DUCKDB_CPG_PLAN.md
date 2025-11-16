# Phase 8: CPG в DuckDB - Гибридная Архитектура

## 📋 Обзор

**Цель**: Реализовать гибридную архитектуру, использующую Joern для парсинга кода и генерации CPG, а DuckDB с SQL/PGQ для эффективного выполнения графовых запросов.

**Почему гибридный подход?**
- ✅ Joern: готовые парсеры C/C++, зрелая экосистема, проверенная генерация CPG
- ✅ DuckDB: SQL/PGQ знаком LLM, высокая производительность, легкая интеграция
- ✅ Решаем проблемы Phase 7: сложность CPGQL, парсинг Scala output, query patterns

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                   HYBRID CPG ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────┘

Phase 1: Parsing & Generation          Phase 2: Storage & Query
================================        ==========================
┌──────────────┐                        ┌──────────────┐
│    Joern     │───── Export ─────────>│   DuckDB     │
│  (C Parser)  │       CPG             │  (SQL/PGQ)   │
└──────────────┘                        └──────────────┘
      │                                         │
      │ 1. Parse PostgreSQL source              │ 3. SQL/PGQ queries
      │ 2. Build CPG (AST+CFG+PDG)             │ 4. Embeddings storage
      │                                         │ 5. Fast analytics
      ▼                                         ▼
┌──────────────────────────────────────────────────────┐
│                  LangGraph Workflow                   │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐            │
│  │ Analyze │─>│ Generate │─>│ Execute  │─> Answer   │
│  │ Question│  │   SQL    │  │  Query   │            │
│  └─────────┘  └──────────┘  └──────────┘            │
└──────────────────────────────────────────────────────┘
```

## 📊 Сравнение: Joern CPGQL vs DuckDB SQL/PGQ

| Аспект | Joern CPGQL | DuckDB SQL/PGQ |
|--------|-------------|----------------|
| **Парсинг кода** | ✅ Готовые парсеры C/C++/Java | ❌ Нужно импортировать из Joern |
| **Генерация CPG** | ✅ Автоматическая | ❌ Требуется экспорт |
| **Язык запросов** | ❌ Scala DSL (сложен для LLM) | ✅ SQL/PGQ (стандартный) |
| **Производительность** | ⚠️ Зависит от реализации | ✅ Колоночное хранение, векторизация |
| **LLM генерация** | ❌ DSL малоизвестен | ✅ SQL знаком LLM |
| **Интеграция** | ⚠️ Отдельный сервер | ✅ In-process, легко с Python |
| **Embeddings** | ❌ Сложно | ✅ Можно хранить в той же БД |
| **Инкрементальные обновления** | ✅ Поддерживается | ❌ Нужно пересоздавать граф |

**Вывод**: Используем Joern для генерации CPG (сильная сторона), затем экспортируем в DuckDB для запросов (сильная сторона DuckDB).

---

## 🎯 План реализации: 8 этапов

### **Phase 8A: Установка DuckDB и duckpgq**

**Цель**: Установить DuckDB Python API и расширение duckpgq для поддержки SQL/PGQ.

**Задачи**:
1. ✅ Установить `duckdb` Python package
2. ✅ Установить расширение `duckpgq`
3. ✅ Проверить работу SQL/PGQ на примере
4. ✅ Создать тестовую базу данных

**Файлы**:
- `requirements.txt` - добавить duckdb
- `scripts/setup_duckdb.py` - скрипт установки
- `test_duckdb_pgq.py` - проверка работы

**Ожидаемый результат**: Работающая установка DuckDB с поддержкой property graphs.

**Время**: 30 минут

---

### **Phase 8B: Экспортер CPG из Joern в DuckDB**

**Цель**: Создать скрипт для экспорта CPG из Joern в формат DuckDB (таблицы nodes + edges).

**Задачи**:
1. ✅ Изучить API Joern для экспорта узлов и ребер
2. ✅ Написать CPGQL запросы для извлечения всех узлов
3. ✅ Написать CPGQL запросы для извлечения всех ребер
4. ✅ Конвертировать в pandas DataFrame
5. ✅ Сохранить в DuckDB таблицы
6. ✅ Обработать специальные типы узлов (METHOD, CALL, LITERAL и т.д.)

**Файлы**:
- `scripts/export_cpg_to_duckdb.py` - основной экспортер
- `src/execution/cpg_exporter.py` - модуль экспорта

**Ключевые CPGQL запросы**:
```scala
// Экспорт всех узлов
cpg.all.l.map { node =>
  Map(
    "id" -> node.id,
    "type" -> node.label,
    "name" -> node.property("NAME", ""),
    "code" -> node.property("CODE", ""),
    "filename" -> node.property("FILENAME", ""),
    "line" -> node.lineNumber.getOrElse(0),
    "column" -> node.columnNumber.getOrElse(0)
  )
}

// Экспорт всех ребер
cpg.graph.E.l.map { edge =>
  Map(
    "src" -> edge.outNode.id,
    "dst" -> edge.inNode.id,
    "edge_type" -> edge.label
  )
}
```

**Ожидаемый результат**:
- Таблица `nodes` с ~1-2 млн узлов (для PostgreSQL 17)
- Таблица `edges` с ~5-10 млн ребер
- Файл `cpg.duckdb` размером ~500MB-1GB

**Время**: 3-4 часа

---

### **Phase 8C: Схема DuckDB CPG**

**Цель**: Спроектировать оптимальную схему таблиц для хранения CPG и создать property graph.

**Задачи**:
1. ✅ Определить структуру таблицы `nodes`
2. ✅ Определить структуру таблицы `edges`
3. ✅ Создать индексы для ускорения запросов
4. ✅ Создать property graph через `CREATE PROPERTY GRAPH`
5. ✅ Добавить таблицы для embeddings (опционально)

**SQL схема**:
```sql
-- Таблица узлов CPG
CREATE TABLE nodes (
    id BIGINT PRIMARY KEY,
    type VARCHAR NOT NULL,  -- METHOD, CALL, LITERAL, IDENTIFIER, etc.
    name VARCHAR,           -- имя функции/переменной
    code TEXT,              -- исходный код
    filename VARCHAR,       -- путь к файлу
    line INTEGER,           -- номер строки
    column INTEGER,         -- номер столбца

    -- Дополнительные свойства
    full_name VARCHAR,      -- полное имя (с namespace)
    signature VARCHAR,      -- сигнатура функции
    is_external BOOLEAN,    -- внешняя функция?

    -- Для будущих расширений
    embedding FLOAT[],      -- векторное представление
    metadata JSON           -- дополнительные метаданные
);

-- Индексы для ускорения поиска
CREATE INDEX idx_nodes_type ON nodes(type);
CREATE INDEX idx_nodes_name ON nodes(name);
CREATE INDEX idx_nodes_filename ON nodes(filename);
CREATE INDEX idx_nodes_line ON nodes(filename, line);

-- Таблица ребер CPG
CREATE TABLE edges (
    src BIGINT NOT NULL,        -- исходный узел
    dst BIGINT NOT NULL,        -- целевой узел
    edge_type VARCHAR NOT NULL, -- тип связи

    -- Свойства ребра
    order_num INTEGER,          -- порядок аргумента/инструкции
    label VARCHAR,              -- метка (для CFG: true/false branch)

    FOREIGN KEY (src) REFERENCES nodes(id),
    FOREIGN KEY (dst) REFERENCES nodes(id)
);

-- Индексы для ускорения обхода графа
CREATE INDEX idx_edges_src ON edges(src);
CREATE INDEX idx_edges_dst ON edges(dst);
CREATE INDEX idx_edges_type ON edges(edge_type);
CREATE INDEX idx_edges_src_type ON edges(src, edge_type);

-- Property Graph для SQL/PGQ
CREATE PROPERTY GRAPH cpg_graph
VERTEX TABLES (
    nodes
    PROPERTIES (type, name, code, filename, line, column)
)
EDGE TABLES (
    edges
    SOURCE KEY (src) REFERENCES nodes (id)
    DESTINATION KEY (dst) REFERENCES nodes (id)
    LABEL edge_type
    PROPERTIES (order_num, label)
);
```

**Типы узлов (node.type)**:
- `METHOD` - функция/метод
- `CALL` - вызов функции
- `IDENTIFIER` - использование переменной
- `LITERAL` - литерал (число, строка)
- `BLOCK` - блок кода
- `RETURN` - оператор return
- `IF`, `WHILE`, `FOR` - управляющие конструкции
- `FILE` - файл исходного кода
- `NAMESPACE` - пространство имен
- `TYPE` - определение типа

**Типы ребер (edge_type)**:
- `CALLS` - вызов функции
- `AST` - связь в дереве синтаксиса
- `CFG` - поток управления
- `DATA_FLOW` - поток данных
- `ARGUMENT` - аргумент функции
- `CONTAINS` - файл содержит функцию
- `REF` - ссылка на определение

**Ожидаемый результат**: Оптимизированная схема БД с индексами и property graph.

**Время**: 2 часа

---

### **Phase 8D: DuckDBCPGClient - клиент для SQL/PGQ запросов**

**Цель**: Создать Python клиент для выполнения SQL/PGQ запросов к CPG в DuckDB.

**Задачи**:
1. ✅ Создать класс `DuckDBCPGClient`
2. ✅ Реализовать базовые методы запросов
3. ✅ Добавить методы для типичных паттернов анализа
4. ✅ Обработка результатов (pandas DataFrame)

**Файлы**:
- `src/execution/duckdb_cpg_client.py`

**Интерфейс**:
```python
class DuckDBCPGClient:
    """Client for executing SQL/PGQ queries on CPG in DuckDB"""

    def __init__(self, db_path: str = "cpg.duckdb"):
        """Initialize connection to DuckDB"""

    def execute_sql(self, query: str) -> pd.DataFrame:
        """Execute raw SQL/PGQ query"""

    # === Graph traversal queries ===

    def find_callers(self, function_name: str, max_depth: int = 1) -> pd.DataFrame:
        """Find all functions calling target function"""

    def find_callees(self, function_name: str, max_depth: int = 1) -> pd.DataFrame:
        """Find all functions called by source function"""

    def find_call_chain(self, source: str, target: str, max_depth: int = 5) -> List[List[str]]:
        """Find all call paths from source to target"""

    # === Data flow analysis ===

    def find_dataflow(self, source: str, sink: str) -> pd.DataFrame:
        """Find data flow paths from source to sink"""

    def find_taint_flow(self, taint_sources: List[str], sinks: List[str]) -> pd.DataFrame:
        """Find potential taint flows (for vulnerability detection)"""

    # === Pattern matching ===

    def find_pattern(self, pattern_sql: str) -> pd.DataFrame:
        """Execute custom MATCH pattern"""

    def find_methods_by_name(self, name_pattern: str) -> pd.DataFrame:
        """Find methods matching name pattern"""

    def find_methods_in_file(self, filename: str) -> pd.DataFrame:
        """Find all methods in a file"""

    # === Statistics & metrics ===

    def get_call_graph_stats(self) -> Dict:
        """Get statistics about call graph"""

    def get_method_complexity(self, method_name: str) -> int:
        """Calculate cyclomatic complexity"""

    def get_method_metrics(self) -> pd.DataFrame:
        """Get metrics for all methods (LOC, complexity, etc.)"""
```

**Примеры SQL/PGQ запросов**:

```sql
-- 1. Найти все функции, вызывающие target_function
SELECT caller.name, caller.filename, caller.line
FROM GRAPH_TABLE (cpg_graph
  MATCH (caller:METHOD)-[:CALLS]->(target:METHOD)
  WHERE target.name = 'target_function'
  COLUMNS (caller.name, caller.filename, caller.line)
);

-- 2. Найти цепочки вызовов глубиной до 5
SELECT source.name, target.name, PATH_LENGTH() as depth
FROM GRAPH_TABLE (cpg_graph
  MATCH (source:METHOD)-[:CALLS*1..5]->(target:METHOD)
  WHERE target.name = 'dangerous_function'
  COLUMNS (source.name, target.name)
);

-- 3. Найти data flow от источника к приемнику
SELECT
    source.name AS source_func,
    source.filename AS source_file,
    sink.name AS sink_func,
    sink.filename AS sink_file
FROM GRAPH_TABLE (cpg_graph
  MATCH (source:CALL)-[:DATA_FLOW*]->(sink:CALL)
  WHERE source.name IN ('gets', 'scanf')
    AND sink.name IN ('system', 'exec')
  COLUMNS (source.name, source.filename, sink.name, sink.filename)
);

-- 4. Найти все вызовы функции с константными аргументами
SELECT
    caller.name,
    call_node.name AS called_func,
    arg.code AS argument_value
FROM GRAPH_TABLE (cpg_graph
  MATCH (caller:METHOD)-[:CONTAINS]->(call_node:CALL)-[:ARGUMENT]->(arg:LITERAL)
  WHERE call_node.name = 'strcpy'
  COLUMNS (caller.name, call_node.name, arg.code)
);

-- 5. Статистика: топ-10 самых вызываемых функций
SELECT
    target.name,
    COUNT(*) as call_count
FROM GRAPH_TABLE (cpg_graph
  MATCH (source:METHOD)-[:CALLS]->(target:METHOD)
  COLUMNS (target.name)
)
GROUP BY target.name
ORDER BY call_count DESC
LIMIT 10;
```

**Ожидаемый результат**: Полнофункциональный Python клиент для работы с CPG в DuckDB.

**Время**: 4-5 часов

---

### **Phase 8E: LLM → SQL генератор запросов**

**Цель**: Создать компонент для генерации SQL/PGQ запросов из natural language вопросов с помощью LLM.

**Задачи**:
1. ✅ Создать класс `SQLQueryGenerator`
2. ✅ Подготовить промпт с описанием схемы CPG
3. ✅ Добавить примеры SQL/PGQ запросов (few-shot learning)
4. ✅ Реализовать экстракцию SQL из ответа LLM
5. ✅ Валидация и коррекция сгенерированных запросов
6. ✅ Интеграция с LangGraph workflow

**Файлы**:
- `src/agents/sql_query_generator.py`
- `prompts/sql_generation_prompt.txt`

**Архитектура**:
```python
class SQLQueryGenerator:
    """Generate SQL/PGQ queries from natural language questions"""

    def __init__(self, llm, schema_path: str):
        self.llm = llm
        self.schema = self._load_schema(schema_path)
        self.examples = self._load_examples()

    def generate_query(self, question: str, context: Dict) -> str:
        """
        Generate SQL/PGQ query from question

        Args:
            question: Natural language question
            context: Analysis context (domain, keywords, file_hint)

        Returns:
            SQL/PGQ query string
        """
        prompt = self._build_prompt(question, context)
        response = self.llm.generate(prompt, max_tokens=500)
        sql = self._extract_sql(response)
        sql = self._validate_and_fix(sql)
        return sql

    def _build_prompt(self, question: str, context: Dict) -> str:
        """Build prompt with schema + examples + question"""
        return f"""
You are a SQL/PGQ query expert for Code Property Graph analysis.

{self.schema}

{self._format_examples()}

Now generate a SQL/PGQ query for this question:
Question: {question}

Context:
- Domain: {context.get('domain')}
- Keywords: {context.get('keywords')}
- File hint: {context.get('file_hint')}

Return ONLY the SQL query, no explanations.
"""
```

**Промпт с примерами (Few-shot)**:
```
CPG Database Schema:
====================

Nodes table:
- id: node identifier
- type: METHOD, CALL, LITERAL, IDENTIFIER, BLOCK, RETURN, IF, WHILE, FILE
- name: function/variable name
- code: source code text
- filename: source file path
- line, column: location

Edges table:
- src, dst: source and destination nodes
- edge_type: CALLS, AST, CFG, DATA_FLOW, ARGUMENT, CONTAINS, REF

Property Graph: cpg_graph

Example Queries:
================

Q: Find all functions that call 'malloc'
A:
SELECT caller.name, caller.filename, caller.line
FROM GRAPH_TABLE (cpg_graph
  MATCH (caller:METHOD)-[:CONTAINS]->(call:CALL)
  WHERE call.name = 'malloc'
  COLUMNS (caller.name, caller.filename, caller.line)
);

Q: Find call chains from 'main' to 'dangerous_function'
A:
SELECT source.name, target.name, PATH_LENGTH() as depth
FROM GRAPH_TABLE (cpg_graph
  MATCH (source:METHOD)-[:CALLS*1..5]->(target:METHOD)
  WHERE source.name = 'main' AND target.name = 'dangerous_function'
  COLUMNS (source.name, target.name)
);

Q: Find data flow from user input to system call
A:
SELECT source.name, sink.name
FROM GRAPH_TABLE (cpg_graph
  MATCH (source:CALL)-[:DATA_FLOW*]->(sink:CALL)
  WHERE source.name IN ('gets', 'scanf', 'read')
    AND sink.name IN ('system', 'exec', 'popen')
  COLUMNS (source.name, sink.name)
);
```

**Валидация и коррекция**:
```python
def _validate_and_fix(self, sql: str) -> str:
    """Validate and fix common SQL errors"""

    # Check for common mistakes
    errors = []

    # 1. Missing GRAPH_TABLE wrapper
    if "MATCH" in sql and "GRAPH_TABLE" not in sql:
        sql = f"SELECT * FROM GRAPH_TABLE (cpg_graph {sql} COLUMNS (*))"
        errors.append("Added missing GRAPH_TABLE wrapper")

    # 2. Wrong table/column names
    if "node." in sql:
        sql = sql.replace("node.", "")
        errors.append("Removed 'node.' prefix")

    # 3. Missing COLUMNS clause
    if "MATCH" in sql and "COLUMNS" not in sql:
        # Try to infer columns from SELECT
        errors.append("Warning: Missing COLUMNS clause")

    if errors:
        logger.warning(f"Fixed SQL errors: {errors}")

    return sql
```

**Ожидаемый результат**:
- LLM генерирует корректные SQL/PGQ запросы
- Поддержка 90%+ типичных вопросов о коде
- Валидация и автоматическая коррекция ошибок

**Время**: 4-5 часов

---

### **Phase 8F: Интеграция в LangGraph workflow**

**Цель**: Интегрировать DuckDB CPG path в существующий LangGraph workflow параллельно с Joern.

**Задачи**:
1. ✅ Добавить новый node `duckdb_execute` в workflow
2. ✅ Создать routing логику: Joern vs DuckDB
3. ✅ Адаптировать `control_flow_analyze` для результатов SQL
4. ✅ Обновить `logic_synthesizer` для работы с обоими форматами
5. ✅ Добавить fallback: если DuckDB не работает → Joern

**Архитектура workflow**:
```
analyze_question
      │
      ├──> classify_query_mode
      │           │
      │           ├─ "find-method" ──> semantic_retrieve
      │           │
      │           └─ "explain-logic"
      │                     │
      │                     ▼
      │           ┌─────────────────┐
      │           │  Route Query    │
      │           │  Backend        │
      │           └─────────────────┘
      │                 │       │
      │                 │       └─────────────┐
      │                 ▼                     ▼
      │         ┌───────────────┐    ┌──────────────┐
      │         │ DuckDB Path   │    │ Joern Path   │
      │         │ (SQL/PGQ)     │    │ (CPGQL)      │
      │         └───────────────┘    └──────────────┘
      │                 │                     │
      │                 └──────────┬──────────┘
      │                            ▼
      │                    control_flow_analyze
      │                            │
      └────────────────────────────┴──> logic_synthesize ──> END
```

**Routing логика**:
```python
def route_cpg_backend(state: GraphState) -> str:
    """Decide whether to use DuckDB or Joern for CPG queries"""

    # Check if DuckDB is available
    if not os.path.exists("cpg.duckdb"):
        logger.info("DuckDB not available, using Joern")
        return "joern_path"

    # Check query complexity
    keywords = state.get("keywords", [])

    # Simple queries → DuckDB (faster)
    simple_patterns = ["who calls", "find callers", "list functions"]
    if any(p in state["question"].lower() for p in simple_patterns):
        logger.info("Simple query detected, using DuckDB")
        return "duckdb_path"

    # Complex dataflow → Joern (more features)
    complex_patterns = ["data flow", "taint analysis", "vulnerability"]
    if any(p in state["question"].lower() for p in complex_patterns):
        logger.info("Complex query detected, using Joern")
        return "joern_path"

    # Default: try DuckDB first (faster), fallback to Joern
    logger.info("Using DuckDB by default")
    return "duckdb_path"
```

**Новый node: duckdb_execute**:
```python
def duckdb_execute_node(state: GraphState) -> GraphState:
    """Execute SQL/PGQ query on DuckDB CPG"""

    logger.info("=== DUCKDB EXECUTOR ===")

    # 1. Get SQL query from state (generated by sql_generator)
    sql_query = state.get("sql_query")
    if not sql_query:
        logger.error("No SQL query in state")
        return state

    # 2. Execute query
    client = get_duckdb_client()
    try:
        results_df = client.execute_sql(sql_query)

        # 3. Convert to format compatible with call_chain_analyzer
        cpg_results = {
            'entry_point': None,  # Will be extracted from results
            'methods': results_df.to_dict('records'),
            'call_graph': {}  # Will be constructed
        }

        state["cpg_results"] = cpg_results
        state["cpg_backend"] = "duckdb"
        logger.info(f"DuckDB query returned {len(results_df)} results")

    except Exception as e:
        logger.error(f"DuckDB query failed: {e}")
        # Fallback to Joern
        state["cpg_backend"] = "joern"
        logger.info("Falling back to Joern")

    return state
```

**Обновление workflow builder**:
```python
def build_workflow():
    """Build LangGraph workflow with DuckDB integration"""

    workflow = StateGraph(GraphState)

    # ... existing nodes ...

    # Add SQL generator node
    workflow.add_node("sql_generate", sql_generate_node)

    # Add DuckDB executor node
    workflow.add_node("duckdb_execute", duckdb_execute_node)

    # Add routing
    workflow.add_conditional_edges(
        "control_flow_generate",
        route_cpg_backend,
        {
            "duckdb_path": "sql_generate",
            "joern_path": "control_flow_execute"
        }
    )

    # Connect DuckDB path
    workflow.add_edge("sql_generate", "duckdb_execute")
    workflow.add_edge("duckdb_execute", "control_flow_analyze")

    # ... rest of workflow ...

    return workflow.compile()
```

**Ожидаемый результат**:
- Workflow поддерживает оба backend'а
- Автоматический routing и fallback
- Единый интерфейс для результатов

**Время**: 3-4 часа

---

### **Phase 8G: Бенчмарки и сравнение производительности**

**Цель**: Измерить и сравнить производительность DuckDB vs Joern на типичных запросах.

**Задачи**:
1. ✅ Создать набор бенчмарк-запросов (10-15 типичных паттернов)
2. ✅ Измерить время выполнения на DuckDB
3. ✅ Измерить время выполнения на Joern
4. ✅ Сравнить результаты (корректность + скорость)
5. ✅ Оптимизировать медленные запросы

**Бенчмарк-запросы**:
```python
BENCHMARK_QUERIES = [
    {
        "name": "Find direct callers",
        "question": "Who calls ApplyLogicalReplicationWorker?",
        "expected_min_results": 1
    },
    {
        "name": "Find call chain (depth 3)",
        "question": "Find call path from main to ShutdownXLOG",
        "expected_min_results": 1
    },
    {
        "name": "Find methods in file",
        "question": "List all functions in worker.c",
        "expected_min_results": 50
    },
    {
        "name": "Find methods by pattern",
        "question": "Find all functions with 'Replication' in name",
        "expected_min_results": 20
    },
    {
        "name": "Data flow analysis",
        "question": "Find data flow from gets to system",
        "expected_min_results": 0  # No such vulnerability in PostgreSQL
    },
    {
        "name": "Statistics query",
        "question": "Top 10 most called functions",
        "expected_min_results": 10
    }
]
```

**Метрики**:
- Время выполнения (ms)
- Количество результатов
- Память (MB)
- Корректность (сравнение с ground truth)

**Ожидаемые результаты** (гипотеза из исследования):
- DuckDB: 2-5x быстрее на аналитических запросах
- DuckDB: лучше на агрегациях и статистике
- Joern: сравнимо на простых графовых обходах
- Оба: одинаковая корректность

**Время**: 2-3 часа

---

### **Phase 8H: Документация и примеры**

**Цель**: Создать полную документацию по использованию DuckDB CPG.

**Задачи**:
1. ✅ Руководство по миграции (Joern → DuckDB)
2. ✅ Примеры SQL/PGQ запросов для типичных задач
3. ✅ API документация для DuckDBCPGClient
4. ✅ Troubleshooting guide
5. ✅ Сравнительная таблица: когда использовать DuckDB vs Joern

**Документы**:
- `docs/DUCKDB_CPG_GUIDE.md` - основное руководство
- `docs/SQL_QUERY_EXAMPLES.md` - примеры запросов
- `docs/MIGRATION_GUIDE.md` - миграция с Joern
- `docs/PERFORMANCE_COMPARISON.md` - результаты бенчмарков

**Время**: 3-4 часа

---

## 📈 Ожидаемые результаты Phase 8

### Метрики успеха:

1. **Производительность**:
   - ✅ DuckDB быстрее Joern на 50%+ аналитических запросах
   - ✅ Размер БД: ~500MB-1GB (сжато)
   - ✅ Время загрузки: <5 секунд

2. **LLM генерация**:
   - ✅ 90%+ корректных SQL запросов
   - ✅ Поддержка всех типов вопросов Phase 7
   - ✅ Автоматическая коррекция ошибок

3. **Интеграция**:
   - ✅ Бесшовная работа в LangGraph workflow
   - ✅ Fallback на Joern при проблемах
   - ✅ Единый интерфейс результатов

4. **Новые возможности**:
   - ✅ Комбинация CPG + embeddings
   - ✅ Быстрые статистические запросы
   - ✅ Легкая расширяемость (новые типы анализа)

### Преимущества решения:

| Аспект | До (Joern only) | После (Hybrid) |
|--------|-----------------|----------------|
| **Скорость запросов** | 5-10 секунд | 1-2 секунды |
| **LLM генерация** | 50% корректных | 90% корректных |
| **Интеграция** | Сложная | Простая (Python) |
| **Расширяемость** | Ограничена | Легкая (SQL) |
| **Embeddings** | Невозможно | Возможно |
| **Статистика** | Сложно | Тривиально |

---

## 🔄 Статус реализации

- [ ] Phase 8A: Установка DuckDB (в процессе)
- [ ] Phase 8B: Экспортер CPG
- [ ] Phase 8C: Схема БД
- [ ] Phase 8D: DuckDBCPGClient
- [ ] Phase 8E: SQL Generator
- [ ] Phase 8F: Workflow интеграция
- [ ] Phase 8G: Бенчмарки
- [ ] Phase 8H: Документация

**Начало**: 2025-11-11
**Ожидаемое завершение**: 2025-11-15 (4-5 дней)
**Общее время**: ~25-30 часов работы

---

## 📚 Ссылки

- [DuckDB Documentation](https://duckdb.org/docs/)
- [DuckPGQ Extension](https://duckpgq.org/)
- [SQL/PGQ Standard](https://www.iso.org/standard/76120.html)
- [Joern Documentation](https://docs.joern.io/)
- [Research Paper: DuckPGQ (VLDB 2023)](https://www.vldb.org/pvldb/vol16/p4034-wolde.pdf)

---

**Следующий шаг**: Начать Phase 8A - установка DuckDB и проверка работы SQL/PGQ на простом примере.
