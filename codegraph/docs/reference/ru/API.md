# Справочник API

Полная документация по API для CodeGraph.

> **Ищете документацию по REST API?** См. [Документация по REST API](../api/REST_API.md) для получения информации о HTTP-эндпоинтах, аутентификации и примерах использования.

## Содержание

- [Основные сервисы](#core-services)
- [CPGQueryService](#cpgqueryservice)
- [VectorStoreReal](#vectorstorereal)
- [HybridRetriever](#hybridretriever)
- [Классы агентов](#agent-classes)
- [AnalyzerAgent](#analyzeragent)
- [RetrieverAgent](#retrieveragent)
- [EnrichmentAgent](#enrichmentagent)
- [GeneratorAgent](#generatoragent)
- [InterpreterAgent](#interpreteragent)
- [Классы рабочих процессов](#workflow-classes)
- [LangGraphWorkflow](#langgraphworkflow)
- [MultiScenarioWorkflow](#multiscenarioworkflow)
- [Классы конфигурации](#configuration-classes)
- [CPGConfig](#cpgconfig)
- [DomainRegistry](#domainregistry)
- [Типы данных](#data-types)
- [RelevanceScore](#relevancescore)
- [WorkflowState](#workflowstate)
- [Классы усиления безопасности](#security-hardening-classes)
- [HardeningScanner](#hardeningscanner)
- [HardeningCategory](#hardeningcategory)
- [HardeningSeverity](#hardeningseverity)
- [HardeningCheck](#hardeningcheck)
- [HardeningFinding](#hardeningfinding)
- [Вспомогательные функции для усиления безопасности](#hardening-utility-functions)
- [Обработка ошибок](#error-handling)
- [Общие исключения](#common-exceptions)
- [Шаблон обработки ошибок](#error-handling-pattern)
- [Дальнейшие шаги](#next-steps)

## Основные сервисы {#core-services}

### CPGQueryService {#cpgqueryservice}

Сервис выполнения запросов к базе данных.

```
from src.services.cpg_query_service import CPGQueryService

service = CPGQueryService(db_path="cpg.duckdb")
```

#### Методы

##### find_method(name: str) -> List[Dict]

Поиск методов по имени.

```
methods = service.find_method("CommitTransaction")
# Возвращает: [{'node_id': 123, 'name': 'CommitTransaction', 'file': 'xact.c', ...}] {#returns-node-id-123-name-committransaction-file-xactc}
```

##### find_callees(method_name: str) -> List[Dict]

Поиск методов, вызываемых указанным методом.

```
callees = service.find_callees("CommitTransaction")
# Возвращает: [{'name': 'MarkBufferDirty', 'file': 'bufmgr.c', ...}] {#returns-name-markbufferdirty-file-bufmgrc}
```

##### find_callers(method_name: str) -> List[Dict]

Поиск методов, которые вызывают указанный метод.

```
callers = service.find_callers("LWLockAcquire")
# Возвращает: [{'name': 'heap_insert', 'file': 'heapam.c', ...}] {#returns-name-heap-insert-file-heapamc}
```

##### execute_sql(query: str) -> List[Dict]

Выполнение произвольного SQL-запроса.

```
results = service.execute_sql("SELECT * FROM nodes_method LIMIT 10")
```

##### count_methods() -> int

Получить общее количество методов.

```
count = service.count_methods()
# Возвращает: 52303 {#returns-52303}
```

---

### VectorStoreReal {#vectorstorereal}

Интерфейс семантического поиска по векторам.

```
from src.retrieval.vector_store_real import VectorStoreReal

store = VectorStoreReal(persist_directory="chromadb_storage")
```

#### Атрибуты

| Атрибут | Тип | Описание |
| --- | --- | --- |
| qa_collection | Collection | Пара вопросы-ответы (23K документов) |
| examples_collection | Collection | Примеры запросов (1K документов) |
| cfg_patterns | Collection | Шаблоны управления потоком выполнения (54K документов) |
| ddg_patterns_enriched | Collection | Шаблоны потока данных (169K документов) |
| documentation | Collection | Документация по методам (638 документов) |

#### Методы

##### search_qa(query: str, top_k: int = 5) -> List[Dict]

Поиск в коллекции вопросов и ответов.

```
results = store.search_qa("Как работает фиксация транзакции?", top_k=3)
# Возвращает: [{'question': '...', 'answer': '...', 'score': 0.85}] {#returns-question-answer-score-085}
```

##### search_examples(query: str, top_k: int = 5) -> List[Dict]

Поиск примеров SQL-запросов.

```
examples = store.search_examples("найти вызывающие методы", top_k=3)
# Возвращает: [{'query': 'SELECT ...', 'description': '...'}] {#returns-query-select-description}
```

##### search_documentation(query: str, top_k: int = 5) -> List[Dict]

Поиск документации по методам.

```
docs = store.search_documentation("менеджер буферов", top_k=5)
```

---

### HybridRetriever {#hybridretriever}

Параллельный гибридный поиск, объединяющий векторный и графовый подходы.

```
from src.retrieval.hybrid_retriever import HybridRetriever, HybridRetrievalConfig

config = HybridRetrievalConfig(
    vector_weight=0.6,
    graph_weight=0.4,
    final_top_k=10
)

retriever = HybridRetriever(
    vector_store=vector_store,
    cpg_service=cpg_service,
    config=config
)
```

#### Методы

##### async retrieve(query: str, mode: str, query_type: str) -> List[RetrievalResult]

Выполнить гибридный поиск.

```
import asyncio

results = asyncio.run(retriever.retrieve(
    query="обработка фиксации транзакции",
    mode="hybrid",  # "hybrid", "vector_only", "graph_only"
    query_type="semantic"  # "semantic", "structural", "security"
))
```

#### RetrievalResult

```
@dataclass
class RetrievalResult:
    content: str          # Найденное содержимое
    score: float          # Оценка релевантности
    source: str           # "vector", "graph" или "hybrid"
    node_id: Optional[int]
    metadata: Dict
```

## Классы агентов {#agent-classes}

### AnalyzerAgent {#analyzeragent}

Понимание вопросов и извлечение намерений.

```
from src.agents.analyzer_agent import AnalyzerAgent

analyzer = AnalyzerAgent(vector_store=vector_store)
```

#### Методы

##### analyze(question: str) -> Dict

Анализирует вопрос для извлечения намерения и ключевых слов.

```
analysis = analyzer.analyze("Какие методы обрабатывают фиксацию транзакций?")
# Возвращает: { {#returns}
# 'intent': 'find_methods', {#intent-find-methods}
# 'domain': 'transaction-manager', {#domain-transaction-manager}
# 'keywords': ['transaction', 'commit'], {#keywords-transaction-commit}
# 'query_type': 'semantic' {#query-type-semantic}
# }
```

---

### RetrieverAgent {#retrieveragent}

Гибридное извлечение с ранжированием.

```
from src.agents.retriever_agent import RetrieverAgent

retriever = RetrieverAgent(
    vector_store=vector_store,
    analyzer_agent=analyzer,
    cpg_service=cpg_service,
    enable_hybrid=True
)
```

#### Методы

##### retrieve_hybrid(question: str, mode: str, query_type: str, top_k: int, use_ranker: bool) -> Dict

Выполняет извлечение с опциональным ранжированием.

```
result = retriever.retrieve_hybrid(
    question="Найти шаблоны выделения памяти",
    mode="hybrid",
    query_type="structural",
    top_k=10,
    use_ranker=True
)
# Возвращает: { {#returns}
# 'results': [...], {#results}
# 'ranked_results': [...], {#ranked-results}
# 'retrieval_stats': {...} {#retrieval-stats}
# }
```

---

### EnrichmentAgent {#enrichmentagent}

Семантическое обогащение узлов CPG.

```
from src.agents.enrichment_agent import EnrichmentAgent

enrichment = EnrichmentAgent()
```

#### Методы

##### enrich_method(method_data: Dict) -> Dict

Добавляет семантические теги к методу.

```
enriched = enrichment.enrich_method({
    'name': 'LWLockAcquire',
    'file': 'lwlock.c'
})
# Возвращает: {'tags': ['concurrency', 'lock-acquire'], ...} {#returns-tags-concurrency-lock-acquire}
```

---

### GeneratorAgent {#generatoragent}

Генерация запросов из естественного языка.

```
from src.agents.generator_agent import GeneratorAgent

generator = GeneratorAgent(vector_store=vector_store)
```

#### Методы

##### generate_query(question: str, analysis: Dict, examples: List) -> str

Генерирует SQL-запрос к базе данных CPG.

```
query = generator.generate_query(
    question="Найти вызывающие метод CommitTransaction",
    analysis={'intent': 'find_callers'},
    examples=[...]
)
# Возвращает: "SELECT * FROM nodes_method WHERE..." {#returns-select-from-nodes-method-where}
```

---

### InterpreterAgent {#interpreteragent}

Интерпретация результатов и формирование ответа.

```
from src.agents.interpreter_agent import InterpreterAgent

interpreter = InterpreterAgent()
```

#### Методы

##### interpret(question: str, results: List, query: str) -> Dict

Формирует ответ на естественном языке.

```
answer = interpreter.interpret(
    question="Какие методы вызывают LWLockAcquire?",
    results=[...],
    query="..."
)
# Возвращает: { {#returns}
# 'answer': 'Следующие 15 методов вызывают LWLockAcquire...', {#answer-the-following-15-methods-call-lwlockacquire}
# 'confidence': 0.85, {#confidence-085}
# 'sources': [...] {#sources}
# }
```

## Классы рабочих процессов {#workflow-classes}

### LangGraphWorkflow {#langgraphworkflow}

Основная оркестровка рабочего процесса.

```
from src.workflow.langgraph_workflow_simple import create_workflow, run_workflow
```

#### Функции {#hardening-utility-functions}

##### run_workflow(question: str) -> Dict

Запускает полный анализ рабочего процесса.

```
result = run_workflow("Найти уязвимости к SQL-инъекциям")
# Возвращает: { {#returns}
# 'answer': '...', {#answer}
# 'confidence': 0.85, {#confidence-085}
# 'query_used': '...', {#query-used}
# 'execution_time_ms': 1500 {#execution-time-ms-1500}
# }
```

---

### MultiScenarioWorkflow {#multiscenarioworkflow}

Анализ на основе сценариев.

```
from src.workflow.multi_scenario_workflow import create_workflow
```

#### Функции

##### create_workflow(scenario: str) -> Workflow

Создаёт рабочий процесс для определённого сценария.

```
workflow = create_workflow(scenario="vulnerability_detection")
result = workflow.run("Найти риски переполнения буфера")
```

Доступные сценарии:
- `definition_search`
- `call_graph`
- `data_flow`
- `vulnerability_detection`
- `dead_code`
- `performance`
- `duplication`
- `entry_points`
- `concurrency`
- `dependencies`
- `documentation`
- `tech_debt`
- `security_incident`
- `refactoring`
- `code_review`
- `architecture`

---

## Классы конфигурации {#configuration-classes}

### CPGConfig {#cpgconfig}

Конфигурация домена и языковой модели (LLM).

```
from src.config import CPGConfig

config = CPGConfig()
```

#### Методы

##### set_cpg_type(domain: str)

Установить активный домен.

```
config.set_cpg_type("postgresql")  # или "linux_kernel", "llvm", "generic"
```

##### get_code_analyst_title() -> str

Получить название аналитика, специфичное для домена.

```
title = config.get_code_analyst_title()
# Возвращает: "PostgreSQL 17.6 expert" {#returns-postgresql-176-expert}
```

---

### DomainRegistry {#domainregistry}

Управление плагинами доменов.

```
from src.domains import DomainRegistry, get_active_domain
```

#### Методы

##### activate(domain_name: str)

Активировать плагин домена.

```
DomainRegistry.activate("postgresql")
```

##### get_active_or_none() -> Optional[DomainPlugin]

Получить текущий активный домен.

```
domain = DomainRegistry.get_active_or_none()
if domain:
    print(f"Активен: {domain.name}")
```

---

## Типы данных {#data-types}

### RelevanceScore {#relevancescore}

Рейтинговая оценка с детализацией.

```
@dataclass
class RelevanceScore:
    total_score: float
    breakdown: Dict[str, float]
    metadata: Dict
```

### WorkflowState {#workflowstate}

Состояние выполнения рабочего процесса.

```
@dataclass
class WorkflowState:
    question: str
    analysis: Dict
    retrieval_results: List
    query: str
    execution_results: List
    answer: str
    confidence: float
    errors: List[str]
```

---

## Классы усиления безопасности {#security-hardening-classes}

### HardeningScanner {#hardeningscanner}

Сканер соответствия усилению безопасности исходного кода D3FEND.

```
from src.security import HardeningScanner, HardeningCategory, HardeningSeverity

scanner = HardeningScanner(cpg_service=cpg_service, language="c")
```

#### Методы

##### scan_all(limit_per_check: int = 50) -> List[HardeningFinding] {#hardeningfinding}

Запускает все применимые проверки усиления безопасности.

```
findings = scanner.scan_all(limit_per_check=50)
# Возвращает: [HardeningFinding(d3fend_id='D3-VI', severity='high', ...)] {#returns-hardeningfindingd3fend-idd3-vi-severityhigh}
```

##### scan_by_d3fend_id(d3fend_ids: List[str], limit: int = 50) -> List[HardeningFinding]

Запускает проверки для конкретных идентификаторов техник D3FEND.

```
findings = scanner.scan_by_d3fend_id(["D3-VI", "D3-NPC", "D3-TL"])
# Возвращает: Результаты для инициализации переменных, проверки нулевых указателей, доверенных библиотек {#returns-findings-for-variable-initialization-null-pointer-checking-trusted-library}
```

##### scan_by_category(category: HardeningCategory, limit: int = 50) -> List[HardeningFinding] {#hardeningcategory}

Запускает проверки для конкретной категории.

```
findings = scanner.scan_by_category(HardeningCategory.MEMORY_SAFETY)
# Возвращает: Результаты для всех проверок безопасности памяти {#returns-findings-for-all-memory-safety-checks}
```

##### scan_by_severity(min_severity: HardeningSeverity, limit: int = 50) -> List[HardeningFinding] {#hardeningseverity}

Запускает проверки с уровнем серьёзности не ниже заданного.

```
findings = scanner.scan_by_severity(HardeningSeverity.HIGH)
# Возвращает: Результаты с серьёзностью CRITICAL или HIGH {#returns-findings-with-critical-or-high-severity}
```

##### get_compliance_score(findings: List[HardeningFinding]) -> Dict

Рассчитывает показатели соответствия на основе результатов.

```
scores = scanner.get_compliance_score(findings)
# Возвращает: { {#returns}
# 'overall_score': 85.3, {#overall-score-853}
# 'total_findings': 12, {#total-findings-12}
# 'by_category': {'initialization': 3, 'pointer_safety': 5, ...}, {#by-category-initialization-3-pointer-safety-5}
# 'by_d3fend': {'D3-VI': 3, 'D3-NPC': 5, ...}, {#by-d3fend-d3-vi-3-d3-npc-5}
# 'by_severity': {'high': 2, 'medium': 6, 'low': 4}, {#by-severity-high-2-medium-6-low-4}
# 'category_scores': {'initialization': 70, 'pointer_safety': 50, ...}, {#category-scores-initialization-70-pointer-safety-50}
# 'd3fend_scores': {'D3-VI': 70, 'D3-NPC': 50, ...} {#d3fend-scores-d3-vi-70-d3-npc-50}
# }
```

##### get_remediation_report(findings: List[HardeningFinding]) -> str

Генерирует отчёт по устранению проблем в формате Markdown.

```
report = scanner.get_remediation_report(findings)
print(report)
# # Отчёт по усилению безопасности исходного кода D3FEND {#d3fend-source-code-hardening-report}
# ## Сводка {#summary}
# - **Общий показатель соответствия**: 85.3% {#overall-compliance-score-853}
# - **Общее количество проблем**: 12 {#total-findings-12}
# ...
```

##### get_checks_summary() -> Dict

Получает сводку по доступным проверкам.

```
summary = scanner.get_checks_summary()
# Возвращает: { {#returns}
# 'total_checks': 22, {#total-checks-22}
# 'language': 'c', {#language-c}
# 'by_category': {...}, {#by-category}
# 'by_d3fend': {...}, {#by-d3fend}
# 'domain_checks': 10 {#domain-checks-10}
# }
```

---

### HardeningCategory

Перечисление категорий усиления безопасности, соответствующих D3FEND.

```
from src.security import HardeningCategory

class HardeningCategory(Enum):
    INITIALIZATION = "initialization"           # D3-VI
    CREDENTIAL_MANAGEMENT = "credential_mgmt"   # D3-CS
    INTEGER_SAFETY = "integer_safety"           # D3-IRV
    POINTER_SAFETY = "pointer_safety"           # D3-PV, D3-NPC, D3-MBSV
    MEMORY_SAFETY = "memory_safety"             # D3-RN
    LIBRARY_SAFETY = "library_safety"           # D3-TL
    TYPE_SAFETY = "type_safety"                 # D3-VTV
    DOMAIN_VALIDATION = "domain_validation"     # D3-DLV
    OPERATIONAL_VALIDATION = "operational"      # D3-OLV
```

---

### HardeningSeverity

Перечисление уровней серьёзности.

```
from src.security import HardeningSeverity

class HardeningSeverity(Enum):
    CRITICAL = "critical"  # Подвержено прямой эксплуатации
    HIGH = "high"          # Значительный риск безопасности
    MEDIUM = "medium"      # Умеренный риск безопасности
    LOW = "low"            # Незначительная проблема безопасности
    INFO = "info"          # Рекомендация по лучшим практикам
```

---

### HardeningCheck {#hardeningcheck}

Определение проверки усиления безопасности.

```
from src.security import HardeningCheck

@dataclass
class HardeningCheck:
    id: str                    # "D3-VI-001"
    d3fend_id: str             # "D3-VI"
    d3fend_name: str           # "Variable Initialization"
    category: HardeningCategory
    severity: HardeningSeverity
    description: str
    sql_query: str             # SQL-запрос к базе данных CPG
    cwe_ids: List[str]         # ["CWE-457"]
    language_scope: List[str]  # ["c", "cpp"] или ["*"]
    indicators: List[str]
    good_patterns: List[str]
    remediation: str
    example_code: str
    confidence_weight: float   # 0.0-1.0
```

#### Методы

##### applies_to_language(language: str) -> bool

Проверяет, применима ли данная проверка к указанному языку.

```
check = get_check_by_id("D3-VI-001")
if check.applies_to_language("c"):
    print("Применимо к коду на C")
```

---

### HardeningFinding

Результат выполнения проверки усиления безопасности.

```
from src.security import HardeningFinding

@dataclass
class HardeningFinding:
    finding_id: str      # Уникальный идентификатор
    check_id: str        # "D3-VI-001"
    d3fend_id: str       # "D3-VI"
    category: str        # "initialization"
    severity: str        # "high"
    method_name: str     # "process_input"
    filename: str        # "src/input.c"
    line_number: int     # 142
    code_snippet: str    # "int x; use(x);"
    description: str
    cwe_ids: List[str]
    remediation: str
    confidence: float    # 0.0-1.0
    metadata: Dict
```

#### Методы

##### to_dict() -> Dict

Преобразует результат в словарь для сериализации.

```
finding_dict = finding.to_dict()
# Возвращает: {'finding_id': 'a1b2c3', 'd3fend_id': 'D3-VI', ...} {#returns-finding-id-a1b2c3-d3fend-id-d3-vi}
```

##### from_check_and_row(check, row, confidence) -> HardeningFinding

Создаёт результат на основе определения проверки и строки результата запроса.

```
finding = HardeningFinding.from_check_and_row(check, row, confidence=0.9)
```

---

### Вспомогательные функции усиления безопасности

```
from src.security import (
    get_check_by_id,
    get_checks_by_category,
    get_checks_by_d3fend_id,
    get_all_checks,
    get_checks_for_language,
    D3FEND_TECHNIQUES,
    D3FEND_TECHNIQUE_IDS,
)
```

##### get_check_by_id(check_id: str) -> Optional[HardeningCheck]

Получает проверку по её идентификатору.

```
check = get_check_by_id("D3-VI-001")
```

##### get_checks_by_category(category: HardeningCategory) -> List[HardeningCheck]

Получает все проверки в указанной категории.

```
memory_checks = get_checks_by_category(HardeningCategory.MEMORY_SAFETY)
```

##### get_checks_by_d3fend_id(d3fend_id: str) -> List[HardeningCheck]

Получает все проверки для техники D3FEND.

```
null_checks = get_checks_by_d3fend_id("D3-NPC")
```

##### get_all_checks() -> List[HardeningCheck]

Получает все зарегистрированные проверки усиления безопасности.

```
all_checks = get_all_checks()
print(f"Общее количество проверок: {len(all_checks)}")
```

##### get_checks_for_language(language: str) -> List[HardeningCheck]

Получает проверки, применимые к конкретному языку.

```
c_checks = get_checks_for_language("c")
```

#### Константы D3FEND

```
# Доступные идентификаторы техник D3FEND {#available-d3fend-technique-ids}
D3FEND_TECHNIQUE_IDS = [
    "D3-VI",   # Инициализация переменных
    "D3-CS",   # Очистка учётных данных
    "D3-IRV",  # Проверка диапазона целых чисел
    "D3-PV",   # Проверка указателей
    "D3-RN",   # Обнуление ссылок
    "D3-TL",   # Доверенная библиотека
    "D3-VTV",  # Проверка типа переменных
    "D3-MBSV", # Проверка начала блока памяти
    "D3-NPC",  # Проверка нулевых указателей
    "D3-DLV",  # Проверка логики домена
    "D3-OLV",  # Проверка операционной логики
]

# Метаданные техник D3FEND {#d3fend-technique-metadata}
D3FEND_TECHNIQUES = {
    "D3-VI": {
        "name": "Инициализация переменных",
        "description": "Присвоение переменным известного значения до использования",
        "url": "https://next.d3fend.mitre.org/technique/d3f:VariableInitialization",
    },
    # ... другие техники
}
```

## Обработка ошибок {#error-handling}

### Распространённые исключения

| Исключение | Описание |
| --- | --- |
| CPGQueryError | Ошибка выполнения запроса к базе данных |
| VectorStoreError | Ошибка векторного поиска |
| LLMError | Ошибка генерации модели LLM |
| WorkflowError | Ошибка выполнения рабочего процесса |

### Шаблон обработки ошибок {#error-handling-pattern}

```
try:
    result = run_workflow(question)
except CPGQueryError as e:
    print(f"Ошибка базы данных: {e}")
except LLMError as e:
    print(f"Ошибка LLM: {e}")
except Exception as e:
    print(f"Неожиданная ошибка: {e}")
```

## Дальнейшие шаги {#next-steps}

- [Справочник агентов](AGENTS.md) — подробная документация по агентам
- [Справочник рабочих процессов](WORKFLOWS.md) — система рабочих процессов
- [Руководство пользователя TUI](../guides/TUI_USER_GUIDE.md) — примеры использования
