# Agents Reference

Detailed documentation for CodeGraph's 13 specialized agents.

## Agent Architecture

```
Question → AnalyzerAgent → RetrieverAgent → EnrichmentAgent → GeneratorAgent → InterpreterAgent → Answer
              ↓                  ↓                ↓                 ↓                ↓
         Intent/Domain    Hybrid Search    Semantic Tags      Query Gen       Answer Synth
```

## Core Agents

### 1. AnalyzerAgent

**Purpose:** Question understanding and intent extraction

**Location:** `src/agents/analyzer_agent.py`

**Responsibilities:**
- Extract user intent from natural language
- Identify target domain/subsystem
- Extract relevant keywords
- Classify query type (semantic/structural/security)

**Configuration:**
```python
from src.agents.analyzer_agent import AnalyzerAgent
from src.config import CPGConfig

config = CPGConfig()
config.set_cpg_type("postgresql")

analyzer = AnalyzerAgent(
    vector_store=vector_store,
    cpg_config=config
)
```

**Key Methods:**
```python
# Analyze a question
analysis = analyzer.analyze("What methods handle transactions?")

# Result structure
{
    'intent': 'find_methods',           # What user wants
    'domain': 'transaction-manager',    # Target subsystem
    'keywords': ['transaction'],        # Important terms
    'query_type': 'semantic',           # Query classification
    'confidence': 0.85
}
```

---

### 2. RetrieverAgent

**Purpose:** Hybrid retrieval combining semantic and structural search

**Location:** `src/agents/retriever_agent.py`

**Responsibilities:**
- Parallel async vector + graph search
- RRF-based result merging
- Cross-source ranking
- Result caching

**Configuration:**
```python
from src.agents.retriever_agent import RetrieverAgent

retriever = RetrieverAgent(
    vector_store=vector_store,
    analyzer_agent=analyzer,
    cpg_service=cpg_service,
    enable_hybrid=True
)
```

**Key Methods:**
```python
# Hybrid retrieval
result = retriever.retrieve_hybrid(
    question="Find memory allocation patterns",
    mode="hybrid",           # hybrid, vector_only, graph_only
    query_type="structural", # Affects weight distribution
    top_k=10,
    use_ranker=True
)

# Result structure
{
    'results': [...],             # Raw retrieval results
    'ranked_results': [...],      # Ranked with scores
    'retrieval_stats': {
        'total_retrieved': 15,
        'source_distribution': {'vector': 8, 'graph': 7}
    }
}
```

**Weight Adaptation:**
| Query Type | Vector Weight | Graph Weight |
|------------|---------------|--------------|
| semantic | 0.75 | 0.25 |
| structural | 0.25 | 0.75 |
| security | 0.50 | 0.50 |

---

### 3. EnrichmentAgent

**Purpose:** Add semantic metadata to CPG nodes

**Location:** `src/agents/enrichment_agent.py`

**Responsibilities:**
- 12-layer semantic enrichment
- Domain concept tagging
- ACID property detection
- Security attribute annotation

**Configuration:**
```python
from src.agents.enrichment_agent import EnrichmentAgent

enrichment = EnrichmentAgent()
```

**Enrichment Layers:**
1. Architectural layer (access-method, storage-engine, etc.)
2. ACID properties
3. Concurrency patterns
4. Performance indicators
5. Security attributes
6. Error handling patterns
7. Memory management
8. Lock primitives
9. Transaction boundaries
10. Data flow categories
11. Control flow patterns
12. Domain-specific concepts

**Key Methods:**
```python
# Enrich a method
enriched = enrichment.enrich_method({
    'name': 'LWLockAcquire',
    'file': 'lwlock.c',
    'signature': 'void LWLockAcquire(LWLock *lock, LWLockMode mode)'
})

# Result
{
    'name': 'LWLockAcquire',
    'tags': ['concurrency', 'lock-acquire', 'synchronization'],
    'layer': 'concurrency-primitive',
    'security': ['thread-safe'],
    'performance': ['blocking-operation']
}
```

---

### 4. GeneratorAgent

**Purpose:** Generate queries from natural language

**Location:** `src/agents/generator_agent.py`

**Responsibilities:**
- CPGQL query generation
- SQL query generation
- Template matching
- Query optimization

**Configuration:**
```python
from src.agents.generator_agent import GeneratorAgent

generator = GeneratorAgent(
    vector_store=vector_store,
    cpg_config=config
)
```

**Key Methods:**
```python
# Generate query from question
query = generator.generate_query(
    question="Find all callers of CommitTransaction",
    analysis={'intent': 'find_callers', 'keywords': ['CommitTransaction']},
    examples=[...]  # Retrieved examples
)

# Returns SQL or CPGQL query
# "SELECT caller.full_name FROM edges_call ec JOIN nodes_method caller..."
```

---

### 5. InterpreterAgent

**Purpose:** Convert results to natural language answers

**Location:** `src/agents/interpreter_agent.py`

**Responsibilities:**
- Result synthesis
- Confidence scoring
- Source attribution
- Answer formatting

**Configuration:**
```python
from src.agents.interpreter_agent import InterpreterAgent

interpreter = InterpreterAgent(
    llm_interface=llm,
    cpg_config=config
)
```

**Key Methods:**
```python
# Interpret results
answer = interpreter.interpret(
    question="What methods call LWLockAcquire?",
    results=[...],
    query="SELECT..."
)

# Result
{
    'answer': 'LWLockAcquire is called by 15 methods including...',
    'confidence': 0.85,
    'sources': [
        {'method': 'heap_insert', 'file': 'heapam.c', 'line': 234},
        ...
    ]
}
```

---

## Specialized Agents

### 6. CallChainAnalyzer

**Purpose:** Analyze function call dependencies

**Location:** `src/agents/call_chain_analyzer.py`

**Methods:**
```python
from src.agents.call_chain_analyzer import CallChainAnalyzer

analyzer = CallChainAnalyzer(cpg_service)

# Find call chain
chain = analyzer.find_chain(
    source="executor_start",
    target="heap_insert",
    max_depth=10
)
```

---

### 7. LogicSynthesizer

**Purpose:** Synthesize explanations for complex logic

**Location:** `src/agents/logic_synthesizer.py`

**Methods:**
```python
from src.agents.logic_synthesizer import LogicSynthesizer

synthesizer = LogicSynthesizer(llm)

# Explain logic
explanation = synthesizer.explain_function(
    function_name="CommitTransaction",
    context=retrieved_context
)
```

---

### 8. ControlFlowGenerator

**Purpose:** Generate control flow explanations

**Location:** `src/agents/control_flow_generator.py`

---

### 9. AdaptiveRefiner

**Purpose:** Refine queries based on execution feedback

**Location:** `src/agents/adaptive_refiner.py`

**Methods:**
```python
from src.agents.adaptive_refiner import AdaptiveRefiner

refiner = AdaptiveRefiner()

# Refine failed query
refined = refiner.refine_query(
    original_query="...",
    error="No results found",
    context=analysis
)
```

---

### 10. FallbackStrategies

**Purpose:** Handle errors and provide fallback behavior

**Location:** `src/agents/fallback_strategies.py`

---

## Domain-Specific Agents

### 11. SecurityAgent

**Purpose:** Security vulnerability detection

**Location:** `src/security/security_agents.py`

**Patterns Detected:**
- SQL Injection (CWE-89)
- Buffer Overflow (CWE-120)
- Command Injection (CWE-78)
- Format String (CWE-134)

---

### 12. PerformanceAgent

**Purpose:** Performance bottleneck detection

**Location:** `src/performance/performance_agents.py`

**Metrics:**
- Cyclomatic complexity
- Loop nesting depth
- Function length
- Memory allocation patterns

---

### 13. ArchitectureAgent

**Purpose:** Architectural pattern analysis

**Location:** `src/architecture/architecture_agents.py`

**Analysis:**
- Layer boundaries
- Module dependencies
- Design pattern detection
- Subsystem mapping

---

## Agent Communication

Agents communicate through a shared state:

```python
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

## Adding Custom Agents

Create a new agent by extending the base pattern:

```python
from typing import Dict, List, Optional

class CustomAgent:
    def __init__(self, cpg_config: Optional[CPGConfig] = None):
        self.cpg_config = cpg_config or get_global_cpg_config()

    def process(self, state: AgentState) -> AgentState:
        """Process state and return updated state."""
        # Your logic here
        state.custom_results = self._analyze(state.question)
        return state

    def _analyze(self, question: str) -> Dict:
        """Internal analysis method."""
        pass
```

Register in workflow:
```python
from src.workflow import register_agent

register_agent("custom", CustomAgent)
```

---

## Next Steps

- [Workflows Reference](WORKFLOWS.md) - Workflow orchestration
- [API Reference](API.md) - Complete API documentation
- [Contributing](../development/CONTRIBUTING.md) - Adding new agents
