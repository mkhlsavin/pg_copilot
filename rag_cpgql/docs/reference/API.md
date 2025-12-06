# API Reference

Complete API documentation for RAG-CPGQL.

## Core Services

### CPGQueryService

Database query execution service.

```python
from src.services.cpg_query_service import CPGQueryService

service = CPGQueryService(db_path="cpg.duckdb")
```

#### Methods

##### find_method(name: str) -> List[Dict]
Find methods by name.

```python
methods = service.find_method("CommitTransaction")
# Returns: [{'node_id': 123, 'name': 'CommitTransaction', 'file': 'xact.c', ...}]
```

##### find_callees(method_name: str) -> List[Dict]
Find methods called by the given method.

```python
callees = service.find_callees("CommitTransaction")
# Returns: [{'name': 'MarkBufferDirty', 'file': 'bufmgr.c', ...}]
```

##### find_callers(method_name: str) -> List[Dict]
Find methods that call the given method.

```python
callers = service.find_callers("LWLockAcquire")
# Returns: [{'name': 'heap_insert', 'file': 'heapam.c', ...}]
```

##### execute_sql(query: str) -> List[Dict]
Execute raw SQL query.

```python
results = service.execute_sql("SELECT * FROM nodes_method LIMIT 10")
```

##### count_methods() -> int
Get total method count.

```python
count = service.count_methods()
# Returns: 52303
```

---

### VectorStoreReal

Semantic vector search interface.

```python
from src.retrieval.vector_store_real import VectorStoreReal

store = VectorStoreReal(persist_directory="chromadb_storage")
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| qa_collection | Collection | Q&A pairs (23K docs) |
| examples_collection | Collection | Query examples (1K docs) |
| cfg_patterns | Collection | Control flow patterns (54K docs) |
| ddg_patterns_enriched | Collection | Data flow patterns (169K docs) |
| documentation | Collection | Method docs (638 docs) |

#### Methods

##### search_qa(query: str, top_k: int = 5) -> List[Dict]
Search Q&A collection.

```python
results = store.search_qa("How does transaction commit work?", top_k=3)
# Returns: [{'question': '...', 'answer': '...', 'score': 0.85}]
```

##### search_examples(query: str, top_k: int = 5) -> List[Dict]
Search CPGQL examples.

```python
examples = store.search_examples("find callers", top_k=3)
# Returns: [{'query': 'cpg.method...', 'description': '...'}]
```

##### search_documentation(query: str, top_k: int = 5) -> List[Dict]
Search method documentation.

```python
docs = store.search_documentation("buffer manager", top_k=5)
```

---

### HybridRetriever

Parallel hybrid search combining vector and graph.

```python
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

#### Methods

##### async retrieve(query: str, mode: str, query_type: str) -> List[RetrievalResult]
Perform hybrid retrieval.

```python
import asyncio

results = asyncio.run(retriever.retrieve(
    query="transaction commit handling",
    mode="hybrid",  # "hybrid", "vector_only", "graph_only"
    query_type="semantic"  # "semantic", "structural", "security"
))
```

#### RetrievalResult

```python
@dataclass
class RetrievalResult:
    content: str          # Retrieved content
    score: float          # Relevance score
    source: str           # "vector", "graph", or "hybrid"
    node_id: Optional[int]
    metadata: Dict
```

---

## Agent Classes

### AnalyzerAgent

Question understanding and intent extraction.

```python
from src.agents.analyzer_agent import AnalyzerAgent

analyzer = AnalyzerAgent(vector_store=vector_store)
```

#### Methods

##### analyze(question: str) -> Dict
Analyze question to extract intent and keywords.

```python
analysis = analyzer.analyze("What methods handle transaction commits?")
# Returns: {
#     'intent': 'find_methods',
#     'domain': 'transaction-manager',
#     'keywords': ['transaction', 'commit'],
#     'query_type': 'semantic'
# }
```

---

### RetrieverAgent

Hybrid retrieval with ranking.

```python
from src.agents.retriever_agent import RetrieverAgent

retriever = RetrieverAgent(
    vector_store=vector_store,
    analyzer_agent=analyzer,
    cpg_service=cpg_service,
    enable_hybrid=True
)
```

#### Methods

##### retrieve_hybrid(question: str, mode: str, query_type: str, top_k: int, use_ranker: bool) -> Dict
Perform retrieval with optional ranking.

```python
result = retriever.retrieve_hybrid(
    question="Find memory allocation patterns",
    mode="hybrid",
    query_type="structural",
    top_k=10,
    use_ranker=True
)
# Returns: {
#     'results': [...],
#     'ranked_results': [...],
#     'retrieval_stats': {...}
# }
```

---

### EnrichmentAgent

Semantic enrichment of CPG nodes.

```python
from src.agents.enrichment_agent import EnrichmentAgent

enrichment = EnrichmentAgent()
```

#### Methods

##### enrich_method(method_data: Dict) -> Dict
Add semantic tags to method.

```python
enriched = enrichment.enrich_method({
    'name': 'LWLockAcquire',
    'file': 'lwlock.c'
})
# Returns: {'tags': ['concurrency', 'lock-acquire'], ...}
```

---

### GeneratorAgent

Query generation from natural language.

```python
from src.agents.generator_agent import GeneratorAgent

generator = GeneratorAgent(vector_store=vector_store)
```

#### Methods

##### generate_query(question: str, analysis: Dict, examples: List) -> str
Generate CPGQL or SQL query.

```python
query = generator.generate_query(
    question="Find callers of CommitTransaction",
    analysis={'intent': 'find_callers'},
    examples=[...]
)
# Returns: "SELECT * FROM nodes_method WHERE..."
```

---

### InterpreterAgent

Result interpretation and answer synthesis.

```python
from src.agents.interpreter_agent import InterpreterAgent

interpreter = InterpreterAgent()
```

#### Methods

##### interpret(question: str, results: List, query: str) -> Dict
Generate natural language answer.

```python
answer = interpreter.interpret(
    question="What methods call LWLockAcquire?",
    results=[...],
    query="..."
)
# Returns: {
#     'answer': 'The following 15 methods call LWLockAcquire...',
#     'confidence': 0.85,
#     'sources': [...]
# }
```

---

## Workflow Classes

### LangGraphWorkflow

Main workflow orchestration.

```python
from src.workflow.langgraph_workflow_simple import create_workflow, run_workflow
```

#### Functions

##### run_workflow(question: str) -> Dict
Run complete analysis workflow.

```python
result = run_workflow("Find SQL injection vulnerabilities")
# Returns: {
#     'answer': '...',
#     'confidence': 0.85,
#     'query_used': '...',
#     'execution_time_ms': 1500
# }
```

---

### MultiScenarioWorkflow

Scenario-based analysis.

```python
from src.workflow.multi_scenario_workflow import create_workflow
```

#### Functions

##### create_workflow(scenario: str) -> Workflow
Create workflow for specific scenario.

```python
workflow = create_workflow(scenario="vulnerability_detection")
result = workflow.run("Find buffer overflow risks")
```

Available scenarios:
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

## Configuration Classes

### CPGConfig

Domain and LLM configuration.

```python
from src.config import CPGConfig

config = CPGConfig()
```

#### Methods

##### set_cpg_type(domain: str)
Set active domain.

```python
config.set_cpg_type("postgresql")  # or "linux_kernel", "llvm", "generic"
```

##### get_code_analyst_title() -> str
Get domain-specific analyst title.

```python
title = config.get_code_analyst_title()
# Returns: "PostgreSQL 17.6 expert"
```

---

### DomainRegistry

Domain plugin management.

```python
from src.domains import DomainRegistry, get_active_domain
```

#### Methods

##### activate(domain_name: str)
Activate a domain plugin.

```python
DomainRegistry.activate("postgresql")
```

##### get_active_or_none() -> Optional[DomainPlugin]
Get currently active domain.

```python
domain = DomainRegistry.get_active_or_none()
if domain:
    print(f"Active: {domain.name}")
```

---

## Data Types

### RelevanceScore

Ranking score with breakdown.

```python
@dataclass
class RelevanceScore:
    total_score: float
    breakdown: Dict[str, float]
    metadata: Dict
```

### WorkflowState

Workflow execution state.

```python
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

## Error Handling

### Common Exceptions

| Exception | Description |
|-----------|-------------|
| `CPGQueryError` | Database query failed |
| `VectorStoreError` | Vector search failed |
| `LLMError` | LLM generation failed |
| `WorkflowError` | Workflow execution failed |

### Error Handling Pattern

```python
try:
    result = run_workflow(question)
except CPGQueryError as e:
    print(f"Database error: {e}")
except LLMError as e:
    print(f"LLM error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Next Steps

- [Agents Reference](AGENTS.md) - Detailed agent documentation
- [Workflows Reference](WORKFLOWS.md) - Workflow system
- [User Guide](../guides/USER_GUIDE.md) - Usage examples
