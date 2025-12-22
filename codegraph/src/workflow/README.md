# Workflow Module

This module implements the multi-scenario workflow orchestration system that coordinates agents and manages end-to-end query processing with specialized scenarios for different use cases.

## Overview

The workflow system uses a scenario-based architecture where each analysis type has its own specialized workflow with tailored CPG queries, LLM prompts, and result interpretation.

```
Question → Scenario Router → [Scenario Workflow] → CPG Analysis → LLM Interpretation → Answer
                                    |
                                    ├── Security Workflow
                                    ├── Performance Workflow
                                    ├── Onboarding Workflow
                                    ├── Documentation Workflow
                                    └── ... (16 scenarios total)
```

## Architecture

```
src/workflow/
├── scenarios/               # Scenario-specific workflows
│   ├── __init__.py          # Exports all workflows
│   ├── security.py          # Security vulnerability analysis
│   ├── performance.py       # Performance and complexity analysis
│   ├── onboarding.py        # Codebase onboarding and navigation
│   ├── documentation.py     # Documentation generation
│   ├── architecture.py      # Architecture and dependency analysis
│   ├── refactoring.py       # Refactoring assistance
│   ├── compliance.py        # Compliance and standards checking
│   ├── code_review.py       # Code review assistance
│   ├── tech_debt.py         # Technical debt quantification
│   ├── cross_repo.py        # Cross-repository impact analysis
│   ├── debugging.py         # Debugging support
│   ├── feature_dev.py       # Feature development assistance
│   ├── coverage.py          # Test coverage analysis
│   ├── concurrency.py       # Concurrency pattern analysis
│   ├── simple_query.py      # Generic simple queries
│   ├── _language_utils.py   # Language/localization utilities
│   └── _keyword_mappings.py # Scenario keyword mappings
├── core/                    # Core workflow infrastructure
│   └── __init__.py          # Core exports
├── state.py                 # Workflow state definitions
├── query_handlers.py        # Query type handlers
└── streaming_progress.py    # Real-time progress tracking
```

## Available Scenarios

| Scenario ID | Name | Description |
|-------------|------|-------------|
| `security` | Security Audit | Find vulnerabilities, SQL injection, buffer overflows |
| `security_incident` | Security Incident | Trace data flow for incident response |
| `performance` | Performance Analysis | Find bottlenecks, hotspots, complexity |
| `onboarding` | Codebase Onboarding | Navigate codebase, find functions, trace calls |
| `documentation` | Documentation | Generate docs for functions and modules |
| `architecture` | Architecture | Detect circular dependencies, layer violations |
| `refactoring` | Refactoring | Identify code smells, duplication |
| `mass_refactoring` | Mass Refactoring | Large-scale code changes |
| `code_review` | Code Review | Automated review with impact analysis |
| `compliance` | Compliance Check | Check naming conventions, standards |
| `tech_debt` | Technical Debt | Quantify TODOs, deprecated functions |
| `cross_repo` | Cross-Repository | Analyze cross-repo dependencies |
| `debugging` | Debugging Support | Find logging points, trace execution |
| `feature_dev` | Feature Development | Find integration points, extension hooks |
| `test_coverage` | Test Coverage | Analyze coverage, suggest tests |
| `concurrency` | Concurrency | Analyze locks, synchronization patterns |

## State Management

```python
class MultiScenarioState(TypedDict):
    query: str              # Original user question
    scenario: str           # Scenario ID
    language: str           # Response language (en/ru)
    session_id: str         # Session identifier
    user_id: Optional[str]  # User identifier
    cpg_results: List[Any]  # CPG query results
    analysis: Dict          # Analysis metadata
    answer: str             # Generated answer
    confidence: float       # Answer confidence (0-1)
    evidence: List[Dict]    # Supporting evidence
    error: Optional[str]    # Error message if any
```

## Usage

### Direct Workflow Invocation

```python
from src.workflow.scenarios import onboarding_workflow, security_workflow

# Execute onboarding workflow
state = {
    'query': 'Where is the main() function defined?',
    'scenario': 'onboarding',
    'language': 'en',
    'session_id': 'session-123',
    'cpg_results': [],
    'analysis': {},
    'answer': '',
    'confidence': 0.0,
    'evidence': [],
    'error': None,
}

result = onboarding_workflow(state)
print(result['answer'])
```

### Via API

```python
import requests

response = requests.post(
    'http://localhost:8000/api/v1/scenarios/security/query',
    headers={'Authorization': 'Bearer <token>'},
    json={
        'query': 'Find SQL injection vulnerabilities',
        'language': 'en',
    }
)
print(response.json()['answer'])
```

## Scenario Workflow Pattern

Each scenario follows a common pattern:

```python
def scenario_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    1. Parse query and detect specific query type
    2. Execute CPG queries for relevant analysis
    3. Process results with domain-specific logic
    4. Generate answer using LLM with scenario prompt
    5. Return enriched state with answer and evidence
    """
    # Step 1: Query analysis
    query_info = detect_query_type(state['query'])

    # Step 2: CPG queries
    with CPGQueryService() as cpg:
        results = cpg.execute_scenario_queries(query_info)

    # Step 3: Process results
    processed = process_results(results, query_info)

    # Step 4: Generate answer
    answer = generate_answer(state['query'], processed, state['language'])

    # Step 5: Return state
    state['cpg_results'] = results
    state['answer'] = answer
    state['confidence'] = calculate_confidence(results)
    return state
```

## Key Features

### Query Type Detection

Each scenario has specialized query type detection:

```python
# Onboarding query types
- definition: "Where is X defined?"
- call_graph: "What calls X?" / "What does X call?"
- dataflow: "How does data flow through X?"
- subsystem_explain: "Explain the Y subsystem"

# Security query types
- vulnerability_scan: "Find vulnerabilities"
- input_validation: "Check input handling"
- privilege_escalation: "Find privilege issues"
```

### Language Support

Workflows support multilingual responses:

```python
from src.workflow.scenarios._language_utils import add_language_instruction

# Adds language instruction to LLM prompt
prompt = add_language_instruction(base_prompt, language='ru')
```

### Progress Tracking

Real-time progress updates via `streaming_progress.py`:

```python
from src.workflow.streaming_progress import ProgressTracker

tracker = ProgressTracker()
tracker.update('cpg_query', 50, 'Executing CPG queries...')
```

## Performance Metrics

| Scenario | Avg Time | Success Rate |
|----------|----------|--------------|
| Onboarding | ~2s | 92% |
| Security | ~5s | 88% |
| Performance | ~4s | 90% |
| Documentation | ~3s | 85% |
| Code Review | ~6s | 82% |

## Configuration

```yaml
workflow:
  default_language: en
  max_results: 50
  timeout: 300  # 5 minutes

  scenarios:
    security:
      enabled: true
      max_vulnerabilities: 100
    performance:
      enabled: true
      complexity_threshold: 10
```

## Error Handling

Workflows handle errors gracefully:

1. **CPG Connection Error**: Returns cached results if available
2. **LLM Error**: Falls back to template-based answers
3. **Timeout**: Returns partial results with warning
4. **Invalid Query**: Returns helpful error message

## Dependencies

- `src/services/cpg_query_service.py` - CPG database queries
- `src/llm/` - LLM interface for answer generation
- `src/prompts/` - Prompt templates for each scenario
- `src/analysis/` - Code analysis utilities

## See Also

- `/src/agents/` - Agent implementations
- `/src/api/routers/scenarios.py` - API endpoint
- `/docs/guides/` - User guides for each scenario
- `/tests/benchmark/` - Benchmark scenarios
