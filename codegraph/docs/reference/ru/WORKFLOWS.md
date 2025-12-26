# Справочник по рабочим процессам

Документация по системе рабочих процессов CodeGraph.

## Содержание

- [Архитектура рабочего процесса](#workflow-architecture)
- [Основные рабочие процессы](#core-workflows)
- [LangGraphWorkflow (Простой)](#langgraphworkflow-simple)
- [HybridQueryWorkflow](#hybridqueryworkflow)
- [MultiScenarioWorkflow](#multiscenarioworkflow)
- [Состояние рабочего процесса](#workflow-state)
- [Узлы рабочего процесса](#workflow-nodes)
- [Узел анализатора](#analyzer-node)
- [Узел поиска](#retriever-node)
- [Узел генерации](#generator-node)
- [Узел исполнения](#executor-node)
- [Узел интерпретации](#interpreter-node)
- [Сценарные рабочие процессы](#scenario-workflows)
- [Расположение](#location)
- [Доступные сценарии](#available-scenarios)
- [Пример сценария](#scenario-example)
- [Обработка ошибок](#error-handling)
- [Логика повторных попыток](#retry-logic)
- [Резервные стратегии](#fallback-strategies)
- [Пользовательские рабочие процессы](#custom-workflows)
- [Создание пользовательского рабочего процесса](#creating-a-custom-workflow)
- [Условная маршрутизация](#conditional-routing)
- [Потоковая передача данных](#streaming)
- [Потоковая передача прогресса](#progress-streaming)
- [Дальнейшие шаги](#next-steps)

## Архитектура рабочего процесса {#workflow-architecture}

CodeGraph использует LangGraph для оркестрации рабочих процессов:

```
┌──────────────────┐
                    │   Точка входа    │
                    │   (Вопрос)       │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   Узел анализатора  │
                    │  (Интенция/Область) │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   Узел поиска     │
                    │ (Гибридный поиск) │
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
     ┌────────▼─────────┐         ┌────────▼─────────┐
     │ Узел обогащения  │         │ Узел генерации   │
     │  (Семантические теги) │     │   (Генерация запроса)    │
     └────────┬─────────┘         └────────┬─────────┘
              │                             │
              └──────────────┬──────────────┘
                             │
                    ┌────────▼─────────┐
                    │   Узел выполнения │
                    │  (Выполнение запроса)     │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ Узел интерпретации │
                    │ (Синтез ответа)   │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │    Вывод         │
                    │   (Ответ)        │
                    └──────────────────┘
```

## Основные рабочие процессы {#core-workflows}

### LangGraphWorkflow (Простой) {#langgraphworkflow-simple}

Базовый рабочий процесс для большинства запросов.

**Расположение:** `src/workflow/langgraph_workflow_simple.py`

```
from src.workflow.langgraph_workflow_simple import run_workflow

result = run_workflow("Найти методы, обрабатывающие транзакции")

# Структура результата {#result-structure}
{
    'answer': 'Методы обработки транзакций включают...',
    'confidence': 0.85,
    'query_used': 'SELECT * FROM nodes_method...',
    'execution_time_ms': 1500,
    'sources': [...]
}
```

### HybridQueryWorkflow {#hybridqueryworkflow}

Выполнение гибридного запроса с использованием векторного и графового поиска.

**Расположение:** `src/workflow/hybrid_query_workflow.py`

```
from src.workflow.orchestration.copilot import CopilotWorkflow

workflow = CopilotWorkflow(
    cpg_service=cpg_service,
    vector_store=vector_store
)

result = workflow.run("Найти вызывающие методы CommitTransaction")

# Объединение результатов векторного и графового поиска {#combines-vector-and-graph-search-results}
{
    'vector_result': {...},
    'graph_result': {...},
    'merged_result': {...},
    'retrieval_mode': 'hybrid'  # или 'vector' или 'graph'
}
```

### MultiScenarioWorkflow {#multiscenarioworkflow}

Маршрутизация на основе сценариев.

**Расположение:** `src/workflow/multi_scenario_workflow.py`

```
from src.workflow.multi_scenario_workflow import create_workflow

# Создание рабочего процесса, специфичного для сценария {#create-scenario-specific-workflow}
workflow = create_workflow(scenario="vulnerability_detection")
result = workflow.run("Найти уязвимости типа SQL-инъекция")
```

## Состояние рабочего процесса {#workflow-state}

Все рабочие процессы имеют общую структуру состояния:

```
@dataclass
class WorkflowState:
    # Входные данные
    question: str

    # Фаза анализа
    analysis: Optional[Dict] = None
    intent: Optional[str] = None
    domain: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    query_type: str = "semantic"

    # Фаза извлечения
    retrieval_results: List = field(default_factory=list)
    vector_results: List = field(default_factory=list)
    graph_results: List = field(default_factory=list)

    # Фаза обогащения
    enrichments: Dict = field(default_factory=dict)
    semantic_tags: List[str] = field(default_factory=list)

    # Фаза генерации
    generated_query: Optional[str] = None
    query_template: Optional[str] = None

    # Фаза выполнения
    execution_results: List = field(default_factory=list)
    execution_error: Optional[str] = None

    # Фаза интерпретации
    answer: Optional[str] = None
    confidence: float = 0.0
    sources: List[Dict] = field(default_factory=list)

    # Метаданные
    execution_time_ms: int = 0
    errors: List[str] = field(default_factory=list)
```

## Узлы рабочего процесса {#workflow-nodes}

### Узел анализатора {#analyzer-node}

Обрабатывает вопрос и извлекает намерение.

```
def analyzer_node(state: WorkflowState) -> WorkflowState:
    analysis = analyzer_agent.analyze(state.question)
    state.analysis = analysis
    state.intent = analysis['intent']
    state.domain = analysis['domain']
    state.keywords = analysis['keywords']
    state.query_type = analysis['query_type']
    return state
```

### Узел извлечения данных

Выполняет гибридное извлечение.

```
def retriever_node(state: WorkflowState) -> WorkflowState:
    results = retriever_agent.retrieve_hybrid(
        question=state.question,
        mode="hybrid",
        query_type=state.query_type
    )
    state.retrieval_results = results['results']
    return state
```

### Узел генерации {#generator-node}

Генерирует запрос на основе контекста.

```
def generator_node(state: WorkflowState) -> WorkflowState:
    query = generator_agent.generate_query(
        question=state.question,
        analysis=state.analysis,
        examples=state.retrieval_results
    )
    state.generated_query = query
    return state
```

### Узел выполнения

Выполняет сгенерированный запрос.

```
def executor_node(state: WorkflowState) -> WorkflowState:
    try:
        results = cpg_service.execute_sql(state.generated_query)
        state.execution_results = results
    except Exception as e:
        state.execution_error = str(e)
    return state
```

### Узел интерпретации {#interpreter-node}

Формирует итоговый ответ.

```
def interpreter_node(state: WorkflowState) -> WorkflowState:
    answer = interpreter_agent.interpret(
        question=state.question,
        results=state.execution_results,
        query=state.generated_query
    )
    state.answer = answer['answer']
    state.confidence = answer['confidence']
    state.sources = answer['sources']
    return state
```

## Рабочие процессы сценариев

### Расположение {#location}

`src/workflow/scenarios/`

### Доступные сценарии {#available-scenarios}

| Сценарий | Файл | Назначение |
| --- | --- | --- |
| security | security.py | Обнаружение уязвимостей |
| performance | performance.py | Анализ производительности |
| architecture | architecture.py | Архитектурный анализ |
| code_review | code_review.py | Автоматизация код-ревью |
| refactoring | refactoring.py | Планирование рефакторинга |
| debugging | debugging.py | Помощь в отладке |
| documentation | documentation.py | Генерация документации |
| tech_debt | tech_debt.py | Оценка технического долга |
| compliance | compliance.py | Проверка соответствия требованиям |
| cross_repo | cross_repo.py | Анализ между репозиториями |
| onboarding | onboarding.py | Помощь в адаптации |
| feature_dev | feature_dev.py | Разработка функций |
| test_coverage | test_coverage.py | Анализ покрытия тестами |
| mass_refactoring | mass_refactoring.py | Масштабный рефакторинг |
| security_incident | security_incident.py | Реагирование на инциденты безопасности |
| large_scale_refactoring | large_scale_refactoring.py | Рефакторинг корпоративного уровня |

### Пример сценария {#scenario-example}

```
# src/workflow/scenarios/security.py {#srcworkflowscenariossecuritypy}

class SecurityScenario:
    def __init__(self):
        self.patterns = load_security_patterns()
        self.agents = [
            AnalyzerAgent(),
            SecurityAgent(),
            VulnerabilityDetector()
        ]

    def run(self, question: str) -> Dict:
        state = WorkflowState(question=question)

        # Цепочка обработки для задач безопасности
        state = self.analyze(state)
        state = self.detect_vulnerabilities(state)
        state = self.generate_report(state)

        return {
            'vulnerabilities': state.vulnerabilities,
            'severity_counts': state.severity_counts,
            'recommendations': state.recommendations
        }
```

## Обработка ошибок {#error-handling}

### Логика повторных попыток {#retry-logic}

```
def executor_node_with_retry(state: WorkflowState) -> WorkflowState:
    max_retries = 2

    for attempt in range(max_retries + 1):
        try:
            results = cpg_service.execute_sql(state.generated_query)
            state.execution_results = results
            return state
        except Exception as e:
            if attempt < max_retries:
                # Уточнение запроса и повторная попытка
                state.generated_query = refiner.refine(
                    state.generated_query,
                    error=str(e)
                )
            else:
                state.errors.append(f"Выполнение не удалось: {e}")

    return state
```

### Резервные стратегии {#fallback-strategies}

```
def generator_node_with_fallback(state: WorkflowState) -> WorkflowState:
    try:
        # Попытка генерации с использованием LLM
        query = generator_agent.generate_query(...)
    except LLMError:
        # Резервный вариант — сопоставление с шаблоном
        query = template_matcher.match(state.intent, state.keywords)

    state.generated_query = query
    return state
```

## Пользовательские рабочие процессы {#custom-workflows}

### Создание пользовательского рабочего процесса {#creating-a-custom-workflow}

```
from langgraph.graph import StateGraph

def create_custom_workflow():
    # Определение графа
    workflow = StateGraph(WorkflowState)

    # Добавление узлов
    workflow.add_node("analyze", analyzer_node)
    workflow.add_node("custom_process", custom_node)
    workflow.add_node("interpret", interpreter_node)

    # Добавление связей
    workflow.add_edge("analyze", "custom_process")
    workflow.add_edge("custom_process", "interpret")

    # Установка начальной и конечной точек
    workflow.set_entry_point("analyze")
    workflow.set_finish_point("interpret")

    return workflow.compile()

# Использование рабочего процесса {#use-the-workflow}
workflow = create_custom_workflow()
result = workflow.invoke({"question": "..."})
```

### Условная маршрутизация {#conditional-routing}

```
def route_by_intent(state: WorkflowState) -> str:
    """Маршрутизация к разным узлам в зависимости от намерения."""
    if state.intent == "find_vulnerabilities":
        return "security_node"
    elif state.intent == "find_performance":
        return "performance_node"
    else:
        return "general_node"

# Добавление условной связи {#add-conditional-edge}
workflow.add_conditional_edges(
    "analyze",
    route_by_intent,
    {
        "security_node": "security",
        "performance_node": "performance",
        "general_node": "general"
    }
)
```

## Потоковая передача {#streaming}

### Потоковая передача прогресса {#progress-streaming}

```
from src.workflow.streaming_progress import StreamingWorkflow

workflow = StreamingWorkflow()

for event in workflow.stream("Найти SQL-инъекцию"):
    print(f"Шаг: {event['step']}")
    print(f"Прогресс: {event['progress']}%")
    if event['step'] == 'complete':
        print(f"Ответ: {event['result']['answer']}")
```

## Дальнейшие шаги {#next-steps}

- [Справка по API](API.md) — Полное описание API
- [Справка по агентам](AGENTS.md) — Подробности об агентах
- [Участие в разработке](../development/CONTRIBUTING.md) — Расширение рабочих процессов
