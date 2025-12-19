# API Reference

Complete API documentation for CodeGraph.

> **Looking for REST API documentation?** See [REST API Documentation](../api/REST_API.md) for HTTP endpoints, authentication, and usage examples.

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

## Security Hardening Classes

### HardeningScanner

D3FEND Source Code Hardening compliance scanner.

```python
from src.security import HardeningScanner, HardeningCategory, HardeningSeverity

scanner = HardeningScanner(cpg_service=cpg_service, language="c")
```

#### Methods

##### scan_all(limit_per_check: int = 50) -> List[HardeningFinding]
Run all applicable hardening checks.

```python
findings = scanner.scan_all(limit_per_check=50)
# Returns: [HardeningFinding(d3fend_id='D3-VI', severity='high', ...)]
```

##### scan_by_d3fend_id(d3fend_ids: List[str], limit: int = 50) -> List[HardeningFinding]
Run checks for specific D3FEND technique IDs.

```python
findings = scanner.scan_by_d3fend_id(["D3-VI", "D3-NPC", "D3-TL"])
# Returns: Findings for Variable Initialization, Null Pointer Checking, Trusted Library
```

##### scan_by_category(category: HardeningCategory, limit: int = 50) -> List[HardeningFinding]
Run checks for a specific category.

```python
findings = scanner.scan_by_category(HardeningCategory.MEMORY_SAFETY)
# Returns: Findings for all memory safety checks
```

##### scan_by_severity(min_severity: HardeningSeverity, limit: int = 50) -> List[HardeningFinding]
Run checks at or above a minimum severity level.

```python
findings = scanner.scan_by_severity(HardeningSeverity.HIGH)
# Returns: Findings with CRITICAL or HIGH severity
```

##### get_compliance_score(findings: List[HardeningFinding]) -> Dict
Calculate compliance scores from findings.

```python
scores = scanner.get_compliance_score(findings)
# Returns: {
#     'overall_score': 85.3,
#     'total_findings': 12,
#     'by_category': {'initialization': 3, 'pointer_safety': 5, ...},
#     'by_d3fend': {'D3-VI': 3, 'D3-NPC': 5, ...},
#     'by_severity': {'high': 2, 'medium': 6, 'low': 4},
#     'category_scores': {'initialization': 70, 'pointer_safety': 50, ...},
#     'd3fend_scores': {'D3-VI': 70, 'D3-NPC': 50, ...}
# }
```

##### get_remediation_report(findings: List[HardeningFinding]) -> str
Generate a Markdown remediation report.

```python
report = scanner.get_remediation_report(findings)
print(report)
# # D3FEND Source Code Hardening Report
# ## Summary
# - **Overall Compliance Score**: 85.3%
# - **Total Findings**: 12
# ...
```

##### get_checks_summary() -> Dict
Get summary of available checks.

```python
summary = scanner.get_checks_summary()
# Returns: {
#     'total_checks': 22,
#     'language': 'c',
#     'by_category': {...},
#     'by_d3fend': {...},
#     'domain_checks': 10
# }
```

---

### HardeningCategory

Enum for D3FEND-aligned hardening categories.

```python
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

Enum for severity levels.

```python
from src.security import HardeningSeverity

class HardeningSeverity(Enum):
    CRITICAL = "critical"  # Directly exploitable
    HIGH = "high"          # Significant security risk
    MEDIUM = "medium"      # Moderate security risk
    LOW = "low"            # Minor security concern
    INFO = "info"          # Best practice recommendation
```

---

### HardeningCheck

Definition of a hardening check.

```python
from src.security import HardeningCheck

@dataclass
class HardeningCheck:
    id: str                    # "D3-VI-001"
    d3fend_id: str             # "D3-VI"
    d3fend_name: str           # "Variable Initialization"
    category: HardeningCategory
    severity: HardeningSeverity
    description: str
    cpgql_query: str           # SQL query for CPG database
    cwe_ids: List[str]         # ["CWE-457"]
    language_scope: List[str]  # ["c", "cpp"] or ["*"]
    indicators: List[str]
    good_patterns: List[str]
    remediation: str
    example_code: str
    confidence_weight: float   # 0.0-1.0
```

#### Methods

##### applies_to_language(language: str) -> bool
Check if this check applies to the given language.

```python
check = get_check_by_id("D3-VI-001")
if check.applies_to_language("c"):
    print("Applies to C code")
```

---

### HardeningFinding

Result from running a hardening check.

```python
from src.security import HardeningFinding

@dataclass
class HardeningFinding:
    finding_id: str      # Unique ID
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

#### Methods

##### to_dict() -> Dict
Convert finding to dictionary for serialization.

```python
finding_dict = finding.to_dict()
# Returns: {'finding_id': 'a1b2c3', 'd3fend_id': 'D3-VI', ...}
```

##### from_check_and_row(check, row, confidence) -> HardeningFinding
Create a finding from a check definition and query result row.

```python
finding = HardeningFinding.from_check_and_row(check, row, confidence=0.9)
```

---

### Hardening Utility Functions

```python
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
Get a check by its ID.

```python
check = get_check_by_id("D3-VI-001")
```

##### get_checks_by_category(category: HardeningCategory) -> List[HardeningCheck]
Get all checks in a category.

```python
memory_checks = get_checks_by_category(HardeningCategory.MEMORY_SAFETY)
```

##### get_checks_by_d3fend_id(d3fend_id: str) -> List[HardeningCheck]
Get all checks for a D3FEND technique.

```python
null_checks = get_checks_by_d3fend_id("D3-NPC")
```

##### get_all_checks() -> List[HardeningCheck]
Get all registered hardening checks.

```python
all_checks = get_all_checks()
print(f"Total checks: {len(all_checks)}")
```

##### get_checks_for_language(language: str) -> List[HardeningCheck]
Get checks applicable to a specific language.

```python
c_checks = get_checks_for_language("c")
```

#### D3FEND Constants

```python
# Available D3FEND technique IDs
D3FEND_TECHNIQUE_IDS = [
    "D3-VI",   # Variable Initialization
    "D3-CS",   # Credential Scrubbing
    "D3-IRV",  # Integer Range Validation
    "D3-PV",   # Pointer Validation
    "D3-RN",   # Reference Nullification
    "D3-TL",   # Trusted Library
    "D3-VTV",  # Variable Type Validation
    "D3-MBSV", # Memory Block Start Validation
    "D3-NPC",  # Null Pointer Checking
    "D3-DLV",  # Domain Logic Validation
    "D3-OLV",  # Operational Logic Validation
]

# D3FEND technique metadata
D3FEND_TECHNIQUES = {
    "D3-VI": {
        "name": "Variable Initialization",
        "description": "Setting variables to a known value before use",
        "url": "https://next.d3fend.mitre.org/technique/d3f:VariableInitialization",
    },
    # ... other techniques
}
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
