# Workflows Reference

Documentation for CodeGraph's workflow system.

## Table of Contents

- [Workflow Architecture](#workflow-architecture)
- [Core Workflows](#core-workflows)
  - [LangGraphWorkflow (Simple)](#langgraphworkflow-simple)
  - [HybridQueryWorkflow](#hybridqueryworkflow)
  - [MultiScenarioWorkflow](#multiscenarioworkflow)
- [Workflow State](#workflow-state)
- [Workflow Nodes](#workflow-nodes)
  - [Analyzer Node](#analyzer-node)
  - [Retriever Node](#retriever-node)
  - [Generator Node](#generator-node)
  - [Executor Node](#executor-node)
  - [Interpreter Node](#interpreter-node)
- [Scenario Workflows](#scenario-workflows)
  - [Location](#location)
  - [Available Scenarios](#available-scenarios)
  - [Scenario Example](#scenario-example)
- [Error Handling](#error-handling)
  - [Retry Logic](#retry-logic)
  - [Fallback Strategies](#fallback-strategies)
- [Custom Workflows](#custom-workflows)
  - [Creating a Custom Workflow](#creating-a-custom-workflow)
  - [Conditional Routing](#conditional-routing)
- [Streaming](#streaming)
  - [Progress Streaming](#progress-streaming)
- [Next Steps](#next-steps)

## Workflow Architecture

CodeGraph uses LangGraph for workflow orchestration:

```
                    ┌──────────────────┐
                    │   Entry Point    │
                    │   (Question)     │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   Analyzer Node  │
                    │  (Intent/Domain) │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  Retriever Node  │
                    │ (Hybrid Search)  │
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
     ┌────────▼─────────┐         ┌────────▼─────────┐
     │ Enrichment Node  │         │  Generator Node  │
     │  (Semantic Tags) │         │   (Query Gen)    │
     └────────┬─────────┘         └────────┬─────────┘
              │                             │
              └──────────────┬──────────────┘
                             │
                    ┌────────▼─────────┐
                    │  Executor Node   │
                    │  (Run Query)     │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ Interpreter Node │
                    │ (Answer Synth)   │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │    Output        │
                    │   (Answer)       │
                    └──────────────────┘
```

## Core Workflows

### LangGraphWorkflow (Simple)

Basic workflow for most queries.

**Location:** `src/workflow/langgraph_workflow_simple.py`

```python
from src.workflow.langgraph_workflow_simple import run_workflow

result = run_workflow("Find methods that handle transactions")

# Result structure
{
    'answer': 'The transaction handling methods include...',
    'confidence': 0.85,
    'query_used': 'SELECT * FROM nodes_method...',
    'execution_time_ms': 1500,
    'sources': [...]
}
```

### HybridQueryWorkflow

Hybrid vector + graph query execution.

**Location:** `src/workflow/hybrid_query_workflow.py`

```python
from src.workflow.orchestration.copilot import CopilotWorkflow

workflow = CopilotWorkflow(
    cpg_service=cpg_service,
    vector_store=vector_store
)

result = workflow.run("Find callers of CommitTransaction")

# Combines vector and graph search results
{
    'vector_result': {...},
    'graph_result': {...},
    'merged_result': {...},
    'retrieval_mode': 'hybrid'  # or 'vector' or 'graph'
}
```

### MultiScenarioWorkflow

Scenario-based routing.

**Location:** `src/workflow/multi_scenario_workflow.py`

```python
from src.workflow.multi_scenario_workflow import create_workflow

# Create scenario-specific workflow
workflow = create_workflow(scenario="vulnerability_detection")
result = workflow.run("Find SQL injection vulnerabilities")
```

## Workflow State

All workflows share a common state structure:

```python
@dataclass
class WorkflowState:
    # Input
    question: str

    # Analysis phase
    analysis: Optional[Dict] = None
    intent: Optional[str] = None
    domain: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    query_type: str = "semantic"

    # Retrieval phase
    retrieval_results: List = field(default_factory=list)
    vector_results: List = field(default_factory=list)
    graph_results: List = field(default_factory=list)

    # Enrichment phase
    enrichments: Dict = field(default_factory=dict)
    semantic_tags: List[str] = field(default_factory=list)

    # Generation phase
    generated_query: Optional[str] = None
    query_template: Optional[str] = None

    # Execution phase
    execution_results: List = field(default_factory=list)
    execution_error: Optional[str] = None

    # Interpretation phase
    answer: Optional[str] = None
    confidence: float = 0.0
    sources: List[Dict] = field(default_factory=list)

    # Metadata
    execution_time_ms: int = 0
    errors: List[str] = field(default_factory=list)
```

## Workflow Nodes

### Analyzer Node

Processes the question and extracts intent.

```python
def analyzer_node(state: WorkflowState) -> WorkflowState:
    analysis = analyzer_agent.analyze(state.question)
    state.analysis = analysis
    state.intent = analysis['intent']
    state.domain = analysis['domain']
    state.keywords = analysis['keywords']
    state.query_type = analysis['query_type']
    return state
```

### Retriever Node

Performs hybrid retrieval.

```python
def retriever_node(state: WorkflowState) -> WorkflowState:
    results = retriever_agent.retrieve_hybrid(
        question=state.question,
        mode="hybrid",
        query_type=state.query_type
    )
    state.retrieval_results = results['results']
    return state
```

### Generator Node

Generates query from context.

```python
def generator_node(state: WorkflowState) -> WorkflowState:
    query = generator_agent.generate_query(
        question=state.question,
        analysis=state.analysis,
        examples=state.retrieval_results
    )
    state.generated_query = query
    return state
```

### Executor Node

Runs the generated query.

```python
def executor_node(state: WorkflowState) -> WorkflowState:
    try:
        results = cpg_service.execute_sql(state.generated_query)
        state.execution_results = results
    except Exception as e:
        state.execution_error = str(e)
    return state
```

### Interpreter Node

Synthesizes the answer.

```python
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

## Scenario Workflows

### Location

`src/workflow/scenarios/`

### Available Scenarios

| Scenario | File | Purpose |
|----------|------|---------|
| security | security.py | Vulnerability detection |
| performance | performance.py | Performance analysis |
| architecture | architecture.py | Architectural analysis |
| code_review | code_review.py | Code review automation |
| refactoring | refactoring.py | Refactoring planning |
| debugging | debugging.py | Debugging assistance |
| documentation | documentation.py | Doc generation |
| tech_debt | tech_debt.py | Tech debt assessment |
| compliance | compliance.py | Compliance checking |
| cross_repo | cross_repo.py | Cross-repo analysis |
| onboarding | onboarding.py | Onboarding assistance |
| feature_dev | feature_dev.py | Feature development |
| test_coverage | test_coverage.py | Test coverage analysis |
| mass_refactoring | mass_refactoring.py | Large-scale refactoring |
| security_incident | security_incident.py | Incident response |
| large_scale_refactoring | large_scale_refactoring.py | Enterprise refactoring |

### Scenario Example

```python
# src/workflow/scenarios/security.py

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

        # Security-specific pipeline
        state = self.analyze(state)
        state = self.detect_vulnerabilities(state)
        state = self.generate_report(state)

        return {
            'vulnerabilities': state.vulnerabilities,
            'severity_counts': state.severity_counts,
            'recommendations': state.recommendations
        }
```

## Error Handling

### Retry Logic

```python
def executor_node_with_retry(state: WorkflowState) -> WorkflowState:
    max_retries = 2

    for attempt in range(max_retries + 1):
        try:
            results = cpg_service.execute_sql(state.generated_query)
            state.execution_results = results
            return state
        except Exception as e:
            if attempt < max_retries:
                # Refine query and retry
                state.generated_query = refiner.refine(
                    state.generated_query,
                    error=str(e)
                )
            else:
                state.errors.append(f"Execution failed: {e}")

    return state
```

### Fallback Strategies

```python
def generator_node_with_fallback(state: WorkflowState) -> WorkflowState:
    try:
        # Try LLM-based generation
        query = generator_agent.generate_query(...)
    except LLMError:
        # Fallback to template matching
        query = template_matcher.match(state.intent, state.keywords)

    state.generated_query = query
    return state
```

## Custom Workflows

### Creating a Custom Workflow

```python
from langgraph.graph import StateGraph

def create_custom_workflow():
    # Define graph
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("analyze", analyzer_node)
    workflow.add_node("custom_process", custom_node)
    workflow.add_node("interpret", interpreter_node)

    # Add edges
    workflow.add_edge("analyze", "custom_process")
    workflow.add_edge("custom_process", "interpret")

    # Set entry and exit
    workflow.set_entry_point("analyze")
    workflow.set_finish_point("interpret")

    return workflow.compile()

# Use the workflow
workflow = create_custom_workflow()
result = workflow.invoke({"question": "..."})
```

### Conditional Routing

```python
def route_by_intent(state: WorkflowState) -> str:
    """Route to different nodes based on intent."""
    if state.intent == "find_vulnerabilities":
        return "security_node"
    elif state.intent == "find_performance":
        return "performance_node"
    else:
        return "general_node"

# Add conditional edge
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

## Streaming

### Progress Streaming

```python
from src.workflow.streaming_progress import StreamingWorkflow

workflow = StreamingWorkflow()

for event in workflow.stream("Find SQL injection"):
    print(f"Step: {event['step']}")
    print(f"Progress: {event['progress']}%")
    if event['step'] == 'complete':
        print(f"Answer: {event['result']['answer']}")
```

## Next Steps

- [API Reference](API.md) - Complete API
- [Agents Reference](AGENTS.md) - Agent details
- [Contributing](../development/CONTRIBUTING.md) - Extending workflows
