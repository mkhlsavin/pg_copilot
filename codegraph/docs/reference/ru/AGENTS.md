# Справочник агентов

Подробная документация по 13 специализированным агентам CodeGraph.

## Содержание

- [Архитектура агентов](#agent-architecture)
- [Основные агенты](#core-agents)
- [1. AnalyzerAgent](#1-analyzeragent)
- [2. RetrieverAgent](#2-retrieveragent)
- [3. EnrichmentAgent](#3-enrichmentagent)
- [4. GeneratorAgent](#4-generatoragent)
- [5. InterpreterAgent](#5-interpreteragent)
- [Специализированные агенты](#specialized-agents)
- [6. CallChainAnalyzer](#6-callchainanalyzer)
- [7. LogicSynthesizer](#7-logicsynthesizer)
- [8. ControlFlowGenerator](#8-controlflowgenerator)
- [9. AdaptiveRefiner](#9-adaptiverefiner)
- [10. FallbackStrategies](#10-fallbackstrategies)
- [Агенты для специфических предметных областей](#domain-specific-agents)
- [11. SecurityAgent](#11-securityagent)
- [12. PerformanceAgent](#12-performanceagent)
- [13. ArchitectureAgent](#13-architectureagent)
- [Взаимодействие агентов](#agent-communication)
- [Добавление пользовательских агентов](#adding-custom-agents)
- [Дальнейшие шаги](#next-steps)

## Архитектура агента

```
Вопрос → AnalyzerAgent → RetrieverAgent → EnrichmentAgent → GeneratorAgent → InterpreterAgent → Ответ
              ↓                  ↓                ↓                 ↓                ↓
         Намерение/Домен    Гибридный поиск    Семантические теги   Генерация запроса   Синтез ответа
```

## Основные агенты {#core-agents}

### 1. AnalyzerAgent {#1-analyzeragent}

**Назначение:** Понимание вопроса и извлечение намерений

**Расположение:** `src/agents/analyzer_agent.py`

**Обязанности:**
- Извлечение намерений пользователя из естественного языка
- Определение целевой области/подсистемы
- Извлечение релевантных ключевых слов
- Классификация типа запроса (семантический/структурный/безопасность)

**Конфигурация:**

```
from src.agents.analyzer_agent import AnalyzerAgent
from src.config import CPGConfig

config = CPGConfig()
config.set_cpg_type("postgresql")

analyzer = AnalyzerAgent(
    vector_store=vector_store,
    cpg_config=config
)
```

**Ключевые методы:**

```
# Анализ вопроса {#analyze-a-question}
analysis = analyzer.analyze("Какие методы обрабатывают транзакции?")

# Структура результата {#result-structure}
{
    'intent': 'find_methods',           # Что хочет пользователь
    'domain': 'transaction-manager',    # Целевая подсистема
    'keywords': ['transaction'],        # Важные термины
    'query_type': 'semantic',           # Классификация запроса
    'confidence': 0.85
}
```

---

### 2. RetrieverAgent {#2-retrieveragent}

**Назначение:** Гибридный поиск, объединяющий семантический и структурный поиск

**Расположение:** `src/agents/retriever_agent.py`

**Обязанности:**
- Параллельный асинхронный поиск по векторам и графу
- Объединение результатов на основе RRF (Reciprocal Rank Fusion)
- Ранжирование из разных источников
- Кэширование результатов

**Конфигурация:**

```
from src.agents.retriever_agent import RetrieverAgent

retriever = RetrieverAgent(
    vector_store=vector_store,
    analyzer_agent=analyzer,
    cpg_service=cpg_service,
    enable_hybrid=True
)
```

**Ключевые методы:**

```
# Гибридный поиск {#hybrid-retrieval}
result = retriever.retrieve_hybrid(
    question="Найти шаблоны выделения памяти",
    mode="hybrid",           # hybrid, vector_only, graph_only
    query_type="structural", # Влияет на распределение весов
    top_k=10,
    use_ranker=True
)

# Структура результата {#result-structure}
{
    'results': [...],             # Сырые результаты поиска
    'ranked_results': [...],      # Ранжированные с оценками
    'retrieval_stats': {
        'total_retrieved': 15,
        'source_distribution': {'vector': 8, 'graph': 7}
    }
}
```

**Адаптация весов:**
| Тип запроса | Вес вектора | Вес графа |
|------------|---------------|--------------|
| semantic | 0.75 | 0.25 |
| structural | 0.25 | 0.75 |
| security | 0.50 | 0.50 |

---

### 3. EnrichmentAgent {#3-enrichmentagent}

**Назначение:** Добавление семантических метаданных к узлам CPG

**Расположение:** `src/agents/enrichment_agent.py`

**Обязанности:**
- 12-уровневое семантическое обогащение
- Маркировка доменных концепций
- Обнаружение свойств ACID
- Аннотация атрибутов безопасности

**Конфигурация:**

```
from src.agents.enrichment_agent import EnrichmentAgent

enrichment = EnrichmentAgent()
```

**Слои обогащения:**
1. Архитектурный уровень (access-method, storage-engine и т.д.)
2. Свойства ACID
3. Шаблоны многопоточности
4. Показатели производительности
5. Атрибуты безопасности
6. Шаблоны обработки ошибок
7. Управление памятью
8. Примитивы блокировок
9. Границы транзакций
10. Категории потоков данных
11. Шаблоны потоков управления
12. Доменно-специфичные концепции

**Ключевые методы:**

```
# Обогащение метода {#enrich-a-method}
enriched = enrichment.enrich_method({
    'name': 'LWLockAcquire',
    'file': 'lwlock.c',
    'signature': 'void LWLockAcquire(LWLock *lock, LWLockMode mode)'
})

# Результат {#result}
{
    'name': 'LWLockAcquire',
    'tags': ['concurrency', 'lock-acquire', 'synchronization'],
    'layer': 'concurrency-primitive',
    'security': ['thread-safe'],
    'performance': ['blocking-operation']
}
```

---

### 4. GeneratorAgent {#4-generatoragent}

**Назначение:** Генерация запросов на основе естественного языка

**Расположение:** `src/agents/generator_agent.py`

**Обязанности:**
- Генерация SQL-запросов к базе данных CPG
- Сопоставление с шаблонами
- Оптимизация запросов

**Конфигурация:**

```
from src.agents.generator_agent import GeneratorAgent

generator = GeneratorAgent(
    vector_store=vector_store,
    cpg_config=config
)
```

**Ключевые методы:**

```
# Генерация запроса из вопроса {#generate-query-from-question}
query = generator.generate_query(
    question="Найти всех вызывающих CommitTransaction",
    analysis={'intent': 'find_callers', 'keywords': ['CommitTransaction']},
    examples=[...]  # Извлечённые примеры
)

# Возвращает SQL-запрос {#returns-sql-query}
# "SELECT caller.full_name FROM edges_call ec JOIN nodes_method caller..." {#select-callerfull-name-from-edges-call-ec-join-nodes-method-caller}
```

---

### 5. InterpreterAgent {#5-interpreteragent}

**Назначение:** Преобразование результатов в ответы на естественном языке

**Расположение:** `src/agents/interpreter_agent.py`

**Обязанности:**
- Синтез результатов
- Оценка достоверности
- Указание источников
- Форматирование ответа

**Конфигурация:**

```
from src.agents.interpreter_agent import InterpreterAgent

interpreter = InterpreterAgent(
    llm_interface=llm,
    cpg_config=config
)
```

**Ключевые методы:**

```
# Интерпретация результатов {#interpret-results}
answer = interpreter.interpret(
    question="Какие методы вызывают LWLockAcquire?",
    results=[...],
    query="SELECT..."
)

# Результат {#result}
{
    'answer': 'LWLockAcquire вызывается 15 методами, включая...',
    'confidence': 0.85,
    'sources': [
        {'method': 'heap_insert', 'file': 'heapam.c', 'line': 234},
        ...
    ]
}
```

## Специализированные агенты {#specialized-agents}

### 6. CallChainAnalyzer {#6-callchainanalyzer}

**Назначение:** Анализ зависимостей вызовов функций

**Расположение:** `src/agents/call_chain_analyzer.py`

**Методы:**

```
from src.agents.call_chain_analyzer import CallChainAnalyzer

analyzer = CallChainAnalyzer(cpg_service)

# Найти цепочку вызовов {#find-call-chain}
chain = analyzer.find_chain(
    source="executor_start",
    target="heap_insert",
    max_depth=10
)
```

---

### 7. LogicSynthesizer {#7-logicsynthesizer}

**Назначение:** Генерация объяснений для сложной логики

**Расположение:** `src/agents/logic_synthesizer.py`

**Методы:**

```
from src.agents.logic_synthesizer import LogicSynthesizer

synthesizer = LogicSynthesizer(llm)

# Объяснить логику {#explain-logic}
explanation = synthesizer.explain_function(
    function_name="CommitTransaction",
    context=retrieved_context
)
```

---

### 8. ControlFlowGenerator {#8-controlflowgenerator}

**Назначение:** Генерация объяснений потоков управления

**Расположение:** `src/agents/control_flow_generator.py`

---

### 9. AdaptiveRefiner {#9-adaptiverefiner}

**Назначение:** Уточнение запросов на основе обратной связи от выполнения

**Расположение:** `src/agents/adaptive_refiner.py`

**Методы:**

```
from src.agents.adaptive_refiner import AdaptiveRefiner

refiner = AdaptiveRefiner()

# Уточнить неудачный запрос {#refine-failed-query}
refined = refiner.refine_query(
    original_query="...",
    error="Результаты не найдены",
    context=analysis
)
```

---

### 10. FallbackStrategies {#10-fallbackstrategies}

**Назначение:** Обработка ошибок и предоставление резервного поведения

**Расположение:** `src/agents/fallback_strategies.py`

---

## Агенты для специфических предметных областей {#domain-specific-agents}

### 11. SecurityAgent {#11-securityagent}

**Назначение:** Обнаружение уязвимостей безопасности

**Расположение:** `src/security/security_agents.py`

**Обнаруживаемые шаблоны:**
- SQL-инъекции (CWE-89)
- Переполнение буфера (CWE-120)
- Инъекции команд (CWE-78)
- Строки форматирования (CWE-134)

---

### 12. PerformanceAgent {#12-performanceagent}

**Назначение:** Обнаружение узких мест в производительности

**Расположение:** `src/performance/performance_agents.py`

**Метрики:**
- Цикломатическая сложность
- Глубина вложенности циклов
- Длина функций
- Шаблоны выделения памяти

---

### 13. ArchitectureAgent {#13-architectureagent}

**Назначение:** Анализ архитектурных шаблонов

**Расположение:** `src/architecture/architecture_agents.py`

**Анализ:**
- Границы слоёв
- Зависимости между модулями
- Обнаружение шаблонов проектирования
- Сопоставление подсистем

---

## Взаимодействие агентов {#agent-communication}

Агенты взаимодействуют через общее состояние:

```
@dataclass
class AgentState:
    question: str
    analysis: Optional[Dict] = None
    retrieval_results: List = field(default_factory=list)
    enrichments: Dict = field(default_factory=dict)
    generated_query: Optional[str] = None
    execution_results: List = field(default_factory=list)
    answer: Optional[str] = None
    confidence: float = 0.0
    errors: List[str] = field(default_factory=list)
```

## Добавление пользовательских агентов {#adding-custom-agents}

Создайте нового агента, расширив базовый шаблон:

```
from typing import Dict, List, Optional

class CustomAgent:
    def __init__(self, cpg_config: Optional[CPGConfig] = None):
        self.cpg_config = cpg_config or get_global_cpg_config()

    def process(self, state: AgentState) -> AgentState:
        """Обрабатывает состояние и возвращает обновлённое состояние."""
        # Ваша логика здесь
        state.custom_results = self._analyze(state.question)
        return state

    def _analyze(self, question: str) -> Dict:
        """Внутренний метод анализа."""
        pass
```

Зарегистрируйте в рабочем процессе:

```
from src.workflow import register_agent

register_agent("custom", CustomAgent)
```

---

## Дальнейшие шаги {#next-steps}

- [Справочник по рабочим процессам](WORKFLOWS.md) — Оркестрация рабочих процессов
- [Справочник API](API.md) — Полная документация по API
- [Участие в разработке](../development/CONTRIBUTING.md) — Добавление новых агентов
