# ФАЗА 4: Deployment Readiness - Production Release

**Дата:** 25 ноября 2025
**Длительность:** 2 недели (10 рабочих дней)
**Приоритет:** P1 - ВЫСОКИЙ
**Статус:** Готов к реализации

---

## 🎯 Цель фазы

**Подготовить систему к production deployment** через полную документацию, автоматизацию развертывания и валидацию производительности.

**Метрики успеха:**
- Complete user guides for all 16 scenarios
- API documentation (Swagger/OpenAPI)
- One-command deployment (Docker)
- CI/CD pipeline passes all tests
- Load testing: 100 QPS without degradation
- Scalability report delivered

---

## 📋 Компоненты для реализации

### Week 7: Documentation
1. **User Documentation** → End-user guides
2. **Developer Documentation** → Contribution & architecture guides

### Week 8: Deployment
3. **Deployment Automation** → Docker + CI/CD
4. **Performance Validation** → Load testing + scalability report

---

## 📅 Week 7: Documentation

### Task 1: User Documentation (Day 1-3)

#### Motivation
**Problem:** Users don't know how to use the system
**Solution:** Comprehensive guides for all use cases

#### Deliverables

**1. Scenario Guides (docs/scenarios/)** - Day 1-2

Create individual guides for all 16 scenarios:

```markdown
# docs/scenarios/01_code_review.md

# Scenario 1: Code Review Automation

## Overview
Automated code review using CPG analysis to find:
- Code smells
- Complexity hotspots
- Maintainability issues
- Code duplication

## Quick Start

### Prerequisites
- Joern CPG exported to DuckDB
- Python environment with dependencies

### Basic Usage

```python
from src.workflow.multi_scenario_workflow import MultiScenarioWorkflow

# Initialize workflow
workflow = MultiScenarioWorkflow()

# Ask a code review question
question = "Which functions in PostgreSQL have the highest complexity?"

result = workflow.run(
    question=question,
    scenario="code_review"
)

print(result['answer'])
```

### Advanced Usage

#### Custom Complexity Thresholds

```python
question = """Find functions with cyclomatic complexity > 20
and more than 100 lines of code in the parser module"""

result = workflow.run(
    question=question,
    scenario="code_review",
    parameters={
        'complexity_threshold': 20,
        'loc_threshold': 100,
        'module_filter': 'parser'
    }
)
```

#### Filtering by File Path

```python
question = "Find code smells in src/backend/optimizer/*.c"

result = workflow.run(
    question=question,
    scenario="code_review"
)
```

## Common Questions

### Code Complexity
- "Which functions have the highest cyclomatic complexity?"
- "Show me functions with more than 10 parameters"
- "Find functions longer than 200 lines"

### Code Duplication
- "Find similar code blocks in the transaction manager"
- "Which functions have similar control flow patterns?"

### Code Smells
- "Find functions with too many nested loops"
- "Which functions have deep nesting (>5 levels)?"
- "Show functions with high fan-out"

## Output Format

```json
{
  "answer": "Found 5 functions with high complexity:\n1. ExecInitNode (complexity: 45)\n2. ParseExpr (complexity: 38)\n...",
  "cpgql_query": "MATCH (m:METHOD) WHERE m.CYCLOMATIC_COMPLEXITY > 20 RETURN m.NAME, m.CYCLOMATIC_COMPLEXITY ORDER BY m.CYCLOMATIC_COMPLEXITY DESC",
  "execution_time": 1.23,
  "results_count": 5
}
```

## Troubleshooting

### No Results Returned
**Problem:** Query returns empty results
**Solution:** Check if CPG contains complexity metrics

```python
# Verify metrics exist
from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

client = DuckDBCPGClient()
result = client.execute_query(
    "SELECT COUNT(*) FROM nodes WHERE CYCLOMATIC_COMPLEXITY IS NOT NULL"
)
print(f"Functions with complexity: {result[0][0]}")
```

### Slow Performance
**Problem:** Query takes >10 seconds
**Solution:** Enable query caching (Phase 2)

```python
from src.caching.query_cache import QueryPlanCache

cache = QueryPlanCache()
# Cache will be used automatically
```

## Best Practices

1. **Be specific**: "Find complexity in parser" > "Find complex functions"
2. **Use filters**: Specify modules/files to narrow scope
3. **Set thresholds**: Provide concrete numbers for metrics
4. **Check cache**: Review cached query plans for similar questions

## See Also
- [Scenario 2: Security Audit](02_security_audit.md)
- [API Documentation](../api/README.md)
- [CPG Schema](../cpg_schema.md)
```

**Repeat for all 16 scenarios:**

**2. API Documentation (docs/api/)** - Day 2

Generate OpenAPI/Swagger documentation:

```python
# src/api/main.py

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="CPG Copilot API",
    description="RAG-based Code Property Graph Query System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.post("/query",
    summary="Execute CPG Query",
    description="Analyze code using natural language questions",
    tags=["Query"]
)
async def execute_query(
    question: str = Query(..., description="Natural language question about code"),
    scenario: str = Query("general", description="Analysis scenario (code_review, security_audit, etc.)"),
    session_id: Optional[str] = Query(None, description="Session ID for conversation context")
):
    """
    Execute a natural language query against the CPG.

    **Example Questions:**
    - "Which functions have the highest complexity?"
    - "Find SQL injection vulnerabilities"
    - "Show the call graph for function X"

    **Response Format:**
    ```json
    {
      "answer": "Natural language answer",
      "cpgql_query": "Generated CPGQL query",
      "results": [...],
      "execution_time": 1.23
    }
    ```
    """
    result = workflow.run(question=question, scenario=scenario)
    return result

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="CPG Copilot API",
        version="1.0.0",
        description="RAG-based Code Property Graph Query System",
        routes=app.routes,
    )

    # Add examples
    openapi_schema["paths"]["/query"]["post"]["requestBody"] = {
        "content": {
            "application/json": {
                "example": {
                    "question": "Which functions have SQL queries?",
                    "scenario": "security_audit"
                }
            }
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

**3. Jupyter Notebook Examples** - Day 3

Create interactive tutorials:

```python
# docs/notebooks/01_getting_started.ipynb

{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Getting Started with CPG Copilot\n",
    "\n",
    "This notebook demonstrates basic usage of the CPG Copilot system.\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Setup\n",
    "import sys\n",
    "sys.path.append('../..')\n",
    "\n",
    "from src.workflow.multi_scenario_workflow import MultiScenarioWorkflow\n",
    "\n",
    "workflow = MultiScenarioWorkflow()\n",
    "print(\"✅ Workflow initialized\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Example 1: Code Complexity Analysis"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "result = workflow.run(\n",
    "    question=\"Which functions have the highest cyclomatic complexity?\",\n",
    "    scenario=\"code_review\"\n",
    ")\n",
    "\n",
    "print(f\"Answer: {result['answer']}\")\n",
    "print(f\"\\nGenerated Query: {result['cpgql_query']}\")\n",
    "print(f\"\\nExecution Time: {result['execution_time']:.2f}s\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Example 2: Security Vulnerability Detection"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "result = workflow.run(\n",
    "    question=\"Find potential SQL injection points\",\n",
    "    scenario=\"security_audit\"\n",
    ")\n",
    "\n",
    "# Visualize results\n",
    "import pandas as pd\n",
    "\n",
    "if result['results']:\n",
    "    df = pd.DataFrame(result['results'])\n",
    "    display(df)\n",
    "else:\n",
    "    print(\"No vulnerabilities found ✅\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Example 3: Performance Bottleneck Analysis"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "result = workflow.run(\n",
    "    question=\"Find I/O operations in hot paths\",\n",
    "    scenario=\"performance_optimization\"\n",
    ")\n",
    "\n",
    "print(result['answer'])"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
```

**Create 5 notebooks:**
- `01_getting_started.ipynb` - Basic usage
- `02_advanced_queries.ipynb` - Complex scenarios
- `03_multi_domain.ipynb` - PostgreSQL, Linux, LLVM examples
- `04_custom_workflows.ipynb` - Building custom scenarios
- `05_performance_tuning.ipynb` - Optimization techniques

**4. Troubleshooting Guide (docs/TROUBLESHOOTING.md)** - Day 3

```markdown
# Troubleshooting Guide

## Common Issues

### Issue 1: CPG Database Not Found

**Symptom:**
```
FileNotFoundError: cpg.duckdb not found
```

**Solution:**
1. Check if Joern export completed:
```bash
ls -lh cpg.duckdb
```

2. Re-run export if needed:
```bash
powershell.exe -ExecutionPolicy Bypass -File scripts/bootstrap_joern.ps1
```

### Issue 2: LLM API Errors

**Symptom:**
```
GigaChatAPIError: Authentication failed
```

**Solution:**
1. Verify environment variable:
```powershell
echo $env:GIGACHAT_AUTH_KEY
```

2. Check config.yaml:
```yaml
llm:
  provider: "gigachat"
  gigachat:
    client_id: "..."
```

3. Test connection:
```bash
python test_gigachat.py
```

### Issue 3: Slow Query Performance

**Symptom:** Queries take >10 seconds

**Solutions:**

**A. Enable Query Caching:**
```python
from src.caching.query_cache import QueryPlanCache
cache = QueryPlanCache(max_size=1000)
```

**B. Check Database Indexes:**
```sql
-- Verify indexes exist
SHOW ALL TABLES;
PRAGMA table_info('nodes');
```

**C. Monitor with Prometheus:**
```bash
curl http://localhost:9090/metrics | grep scenario_duration
```

### Issue 4: Out of Memory

**Symptom:**
```
MemoryError: Unable to allocate array
```

**Solutions:**

**A. Increase DuckDB memory limit:**
```python
client = DuckDBCPGClient(memory_limit='8GB')
```

**B. Process in batches:**
```python
# Instead of loading all results
results = client.execute_query(query, limit=1000)
```

**C. Enable incremental processing (Phase 2):**
```python
from src.cpg_export.incremental_exporter import IncrementalCPGExporter
exporter = IncrementalCPGExporter()
exporter.export_incremental()  # Only changed files
```

### Issue 5: Incorrect Query Results

**Symptom:** Query returns wrong or unexpected results

**Debug Steps:**

**1. Check generated CPGQL:**
```python
result = workflow.run(question, scenario)
print(f"Generated Query: {result['cpgql_query']}")
```

**2. Validate manually:**
```python
from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient
client = DuckDBCPGClient()
results = client.execute_query(result['cpgql_query'])
print(results)
```

**3. Check retrieval context:**
```python
from src.agents.retriever_agent import RetrieverAgent
retriever = RetrieverAgent()
context = retriever.retrieve(question)
print(f"Retrieved {len(context)} examples")
for ex in context[:3]:
    print(f"- {ex['question']}")
```

**4. Enable debug logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Benchmarks

### Expected Performance

| Operation | Expected Time | Threshold |
|-----------|---------------|-----------|
| Simple query (cached) | <1s | 2s |
| Complex query (cached) | 1-3s | 5s |
| First query (uncached) | 3-7s | 10s |
| CPG export (full) | 10-20min | 30min |
| CPG export (incremental) | 1-3min | 5min |

### Monitoring Commands

```bash
# Check query cache hit rate
curl http://localhost:9090/metrics | grep cache_hits

# Check scenario latency
curl http://localhost:9090/metrics | grep scenario_duration

# Check memory usage
curl http://localhost:9090/metrics | grep process_resident_memory
```

## Getting Help

### Debug Checklist
- [ ] Environment variables set (GIGACHAT_AUTH_KEY)
- [ ] config.yaml configured correctly
- [ ] cpg.duckdb exists and is accessible
- [ ] Python dependencies installed
- [ ] Joern server running (if using remote)
- [ ] Sufficient memory available (>4GB)
- [ ] Query cache enabled
- [ ] Logs checked for errors

### Contact
- **Issues**: https://github.com/user/pg_copilot/issues
- **Discussions**: https://github.com/user/pg_copilot/discussions
- **Documentation**: docs/README.md
```

---

### Task 2: Developer Documentation (Day 4-5)

#### Motivation
**Problem:** Contributors don't understand architecture
**Solution:** Comprehensive developer guides

#### Deliverables

**1. Architecture Decision Records (docs/adr/)** - Day 4

Document key architectural decisions:

```markdown
# docs/adr/001-hybrid-graph-vector-retrieval.md

# ADR 001: Hybrid Graph-Vector Retrieval

**Status:** Accepted
**Date:** 2025-11-15
**Authors:** Development Team

## Context

The system needs to retrieve relevant examples for query generation. Two approaches:
1. **Vector-only**: Semantic similarity using embeddings
2. **Graph-only**: Structural similarity using CPG patterns
3. **Hybrid**: Combine both approaches

## Decision

We chose **Hybrid Graph-Vector Retrieval** with RRF (Reciprocal Rank Fusion) merging.

## Rationale

### Vector Retrieval
- ✅ Captures semantic similarity
- ✅ Works well for natural language questions
- ❌ Misses structural code patterns

### Graph Retrieval
- ✅ Captures structural patterns (call graphs, data flow)
- ✅ Finds similar code constructs
- ❌ Requires complex graph matching

### Hybrid (Chosen)
- ✅ Best of both worlds
- ✅ +33.6% F1 improvement over vector-only
- ✅ RRF handles rank fusion elegantly
- ❌ Slightly higher latency (mitigated by caching)

## Implementation

```python
def retrieve_hybrid(question: str, top_k: int = 5) -> List[Example]:
    # Vector retrieval
    vector_results = vector_store.query(question, top_k=20)

    # Graph retrieval
    graph_results = graph_store.query(question, top_k=20)

    # RRF merge
    merged = reciprocal_rank_fusion(
        [vector_results, graph_results],
        k=60
    )

    return merged[:top_k]
```

## Consequences

### Positive
- Significant accuracy improvement (+33.6% F1)
- Better handling of both semantic and structural queries
- Flexible weighting via RRF k-parameter

### Negative
- Increased retrieval latency (~200ms)
- More complex caching strategy needed

### Mitigation
- Query plan caching (Phase 2) reduces latency
- RRF is parallelizable

## Alternatives Considered

### 1. Vector-only with better embeddings
- Rejected: Doesn't capture structural patterns

### 2. Graph-only with NLP preprocessing
- Rejected: Poor semantic understanding

### 3. Ensemble learning
- Rejected: Requires training data, less interpretable

## References
- [Phase 1 Evaluation Results](../evaluation/phase1_report.md)
- [RRF Paper](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
```

**Create ADRs for:**
- 001_hybrid_graph_vector_retrieval.md
- 002_langgraph_workflow_engine.md
- 003_duckdb_cpg_storage.md
- 004_multi_domain_prompt_registry.md
- 005_ragas_evaluation_framework.md

**2. Code Walkthrough (docs/developers/)** - Day 4

```markdown
# docs/developers/code_walkthrough.md

# Code Walkthrough

## System Architecture

```
User Question
     ↓
[MultiScenarioWorkflow]
     ↓
[AnalyzerAgent] → Classify scenario & extract entities
     ↓
[RetrieverAgent] → Hybrid graph-vector retrieval
     ↓
[GeneratorAgent] → LLM generates CPGQL query
     ↓
[ExecutorAgent] → Execute on DuckDB CPG
     ↓
[InterpreterAgent] → Natural language answer
     ↓
Response
```

## Key Components

### 1. Workflow Engine (src/workflow/)

**Entry Point: multi_scenario_workflow.py**

```python
class MultiScenarioWorkflow:
    def run(self, question: str, scenario: str = None):
        # Step 1: Analyze question
        analysis = self.analyzer.analyze(question)

        # Step 2: Retrieve relevant examples
        context = self.retriever.retrieve(question, analysis)

        # Step 3: Generate query
        query = self.generator.generate(question, context)

        # Step 4: Execute
        results = self.executor.execute(query)

        # Step 5: Interpret
        answer = self.interpreter.interpret(question, results)

        return {'answer': answer, 'query': query, 'results': results}
```

**How to add a new scenario:**

1. Add to `src/workflow/scenario_configs.py`:
```python
SCENARIOS = {
    'my_new_scenario': {
        'description': 'Description of the scenario',
        'example_questions': [
            'Example question 1',
            'Example question 2'
        ],
        'required_entities': ['ENTITY_TYPE_1', 'ENTITY_TYPE_2']
    }
}
```

2. Add LangGraph workflow in `src/workflow/scenarios/my_new_scenario.py`:
```python
from langgraph.graph import StateGraph

def my_scenario_workflow(state: WorkflowState):
    # Custom workflow logic
    pass

workflow = StateGraph(WorkflowState)
workflow.add_node("analyze", analyze_node)
workflow.add_node("custom_step", my_custom_step)
workflow.add_edge("analyze", "custom_step")
```

3. Register in `multi_scenario_workflow.py`:
```python
from src.workflow.scenarios.my_new_scenario import my_scenario_workflow

self.workflows['my_new_scenario'] = my_scenario_workflow
```

### 2. Agents (src/agents/)

**RetrieverAgent (src/agents/retriever_agent.py)**

Implements hybrid retrieval:

```python
class RetrieverAgent:
    def retrieve(self, question: str, analysis: Dict, top_k: int = 5):
        # 1. Vector retrieval
        vector_results = self.vector_store.query(
            question,
            top_k=20,
            filter={'domain': analysis.get('domain')}
        )

        # 2. Graph retrieval
        graph_results = self.graph_store.query(
            question,
            top_k=20,
            entities=analysis.get('entities', [])
        )

        # 3. RRF merge
        merged = self._reciprocal_rank_fusion(
            [vector_results, graph_results],
            k=60
        )

        return merged[:top_k]

    def _reciprocal_rank_fusion(self, result_lists, k=60):
        scores = {}
        for results in result_lists:
            for rank, item in enumerate(results, 1):
                scores[item.id] = scores.get(item.id, 0) + 1/(k + rank)

        return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**How it works:**
1. Query both vector and graph stores
2. Get top 20 from each
3. Merge using RRF formula: `score = sum(1/(k + rank))`
4. Return top-k merged results

**GeneratorAgent (src/generation/sql_query_generator.py)**

Generates CPGQL queries using LLM:

```python
class SQLQueryGenerator:
    def generate(self, question: str, context: List[Example]):
        # Build prompt with examples
        prompt = self._build_prompt(question, context)

        # Call LLM
        response = self.llm.generate(prompt)

        # Parse and validate
        query = self._extract_query(response)
        validated = self._validate_query(query)

        return validated

    def _build_prompt(self, question, context):
        examples_text = "\n".join([
            f"Q: {ex['question']}\nCPGQL: {ex['query']}"
            for ex in context
        ])

        return f"""Given these examples:
{examples_text}

Generate a CPGQL query for: {question}

Rules:
- Use MATCH...WHERE...RETURN syntax
- Reference CPG schema: {self.schema}
- Return only the query, no explanation
"""
```

### 3. CPG Storage (src/cpg_export/)

**DuckDB Schema (duckdb_cpg_schema.md)**

```sql
-- Nodes table
CREATE TABLE nodes (
    id BIGINT PRIMARY KEY,
    label VARCHAR,  -- METHOD, PARAMETER, CALL, etc.
    -- Node properties as JSON
    properties VARCHAR
);

-- Edges table
CREATE TABLE edges (
    src BIGINT REFERENCES nodes(id),
    dst BIGINT REFERENCES nodes(id),
    label VARCHAR,  -- CFG, CALL, DATA_FLOW, etc.
    PRIMARY KEY (src, dst, label)
);

-- Indexes for performance
CREATE INDEX idx_nodes_label ON nodes(label);
CREATE INDEX idx_edges_src ON edges(src);
CREATE INDEX idx_edges_dst ON edges(dst);
```

**Querying CPG:**

```python
from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

client = DuckDBCPGClient('cpg.duckdb')

# Simple query
results = client.execute_query("""
    SELECT properties->>'NAME' as name,
           properties->>'CYCLOMATIC_COMPLEXITY' as complexity
    FROM nodes
    WHERE label = 'METHOD'
    AND CAST(properties->>'CYCLOMATIC_COMPLEXITY' AS INTEGER) > 10
    ORDER BY complexity DESC
    LIMIT 10
""")

# Graph traversal
results = client.execute_query("""
    WITH RECURSIVE call_chain AS (
        -- Base case: find target method
        SELECT id, properties->>'NAME' as name, 1 as depth
        FROM nodes
        WHERE label = 'METHOD'
        AND properties->>'NAME' = 'ExecInitNode'

        UNION ALL

        -- Recursive case: follow CALL edges
        SELECT n.id, n.properties->>'NAME', c.depth + 1
        FROM nodes n
        JOIN edges e ON e.dst = n.id
        JOIN call_chain c ON e.src = c.id
        WHERE e.label = 'CALL' AND c.depth < 3
    )
    SELECT * FROM call_chain
""")
```

### 4. Multi-Domain Support (src/config.py)

**PromptRegistry** manages domain-specific prompts:

```python
class PromptRegistry:
    def __init__(self, config_path: str = "prompts.yaml"):
        self.prompts = yaml.safe_load(open(config_path))

    def get_prompt(self, key: str, domain: str = "generic") -> str:
        """Get domain-specific prompt with fallback."""
        domain_prompts = self.prompts.get(domain, {})
        generic_prompts = self.prompts.get("generic", {})

        return domain_prompts.get(key) or generic_prompts.get(key)

# Usage
registry = PromptRegistry()
analyst_title = registry.get_prompt('code_analyst_title', domain='postgresql')
# Returns: "PostgreSQL Internals Expert"
```

**CPGConfig** manages domain configuration:

```python
class CPGConfig:
    def __init__(self, domain: str = "generic"):
        self.domain = domain
        self.prompt_registry = PromptRegistry()

    def get_code_analyst_title(self) -> str:
        return self.prompt_registry.get_prompt(
            'code_analyst_title',
            self.domain
        )

    def get_query_examples_filter(self) -> Dict:
        """Get domain-specific example filters."""
        return {
            'postgresql': {'category': 'database_internals'},
            'linux_kernel': {'category': 'kernel_programming'},
            'llvm': {'category': 'compiler_optimization'}
        }.get(self.domain, {})
```

## Testing

### Unit Tests (tests/unit/)

```python
# tests/unit/test_retriever_agent.py

def test_hybrid_retrieval():
    retriever = RetrieverAgent()

    question = "Find SQL injection vulnerabilities"
    analysis = {'domain': 'security', 'entities': ['SQL']}

    results = retriever.retrieve(question, analysis, top_k=5)

    assert len(results) == 5
    assert all(isinstance(r, Example) for r in results)
    assert results[0].score > results[1].score  # Ranked by relevance
```

### Integration Tests (tests/integration/)

```python
# tests/integration/test_end_to_end.py

def test_security_audit_workflow():
    workflow = MultiScenarioWorkflow()

    result = workflow.run(
        question="Find SQL injection points",
        scenario="security_audit"
    )

    assert result['success'] == True
    assert 'SQL' in result['answer']
    assert result['cpgql_query'] is not None
    assert len(result['results']) > 0
```

## Debugging Tips

### 1. Enable debug logging

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 2. Inspect intermediate results

```python
# Add breakpoints in workflow
from IPython import embed

def run(self, question, scenario):
    analysis = self.analyzer.analyze(question)
    embed()  # Debug shell

    context = self.retriever.retrieve(question, analysis)
    embed()  # Check retrieved examples
```

### 3. Validate generated queries

```python
# Test query manually
from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

client = DuckDBCPGClient()
query = "SELECT * FROM nodes WHERE label = 'METHOD' LIMIT 10"

try:
    results = client.execute_query(query)
    print(f"✅ Query valid: {len(results)} results")
except Exception as e:
    print(f"❌ Query invalid: {e}")
```

## Best Practices

### 1. Always use type hints
```python
def retrieve(self, question: str, analysis: Dict, top_k: int = 5) -> List[Example]:
    pass
```

### 2. Document complex logic
```python
def _reciprocal_rank_fusion(self, result_lists, k=60):
    """
    Merge multiple ranked lists using RRF.

    Formula: score = sum(1/(k + rank)) for each list

    Args:
        result_lists: List of ranked result lists
        k: RRF constant (default 60, from paper)

    Returns:
        Merged list sorted by RRF score
    """
```

### 3. Use context managers
```python
# Good
with DuckDBCPGClient() as client:
    results = client.execute_query(query)

# Bad
client = DuckDBCPGClient()
results = client.execute_query(query)
client.close()  # Might forget
```

### 4. Handle errors gracefully
```python
try:
    results = self.executor.execute(query)
except CPGQueryError as e:
    logger.error(f"Query execution failed: {e}")
    return {'success': False, 'error': str(e)}
```
```

**3. Contributing Guidelines (CONTRIBUTING.md)** - Day 5

```markdown
# Contributing to CPG Copilot

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

### Prerequisites
- Python 3.9+
- Git
- Joern (for CPG export)
- DuckDB

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/user/pg_copilot.git
cd pg_copilot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Testing tools

# Setup pre-commit hooks
pre-commit install
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/my-new-feature
# or
git checkout -b fix/issue-123
```

**Branch naming:**
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation
- `refactor/` - Code refactoring
- `test/` - Test improvements

### 2. Make Changes

Follow the project structure:

```
src/
├── agents/          # Agent implementations
├── cpg_export/      # CPG storage
├── generation/      # Query generation
├── workflow/        # LangGraph workflows
└── config.py        # Configuration

tests/
├── unit/            # Unit tests
├── integration/     # Integration tests
└── fixtures/        # Test data
```

### 3. Write Tests

All code changes must include tests:

```python
# tests/unit/test_my_feature.py

import pytest
from src.my_module import my_function

def test_my_function_basic():
    """Test basic functionality."""
    result = my_function("input")
    assert result == "expected"

def test_my_function_edge_cases():
    """Test edge cases."""
    with pytest.raises(ValueError):
        my_function(None)
```

**Run tests:**

```bash
# All tests
pytest

# Specific test file
pytest tests/unit/test_my_feature.py

# With coverage
pytest --cov=src --cov-report=html
```

### 4. Code Quality

**Linting:**

```bash
# Format code
black src/ tests/

# Check linting
flake8 src/ tests/

# Type checking
mypy src/
```

**Pre-commit hooks** run automatically on commit:
- Black (code formatting)
- Flake8 (linting)
- MyPy (type checking)
- isort (import sorting)

### 5. Commit Changes

**Commit message format:**

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `refactor`: Code refactoring
- `test`: Test improvements
- `chore`: Maintenance

**Examples:**

```
feat(retrieval): Add graph-based retrieval

Implement graph pattern matching for structural similarity.
Uses DuckDB recursive CTEs for efficient traversal.

Closes #123
```

```
fix(executor): Handle NULL values in query results

Previously crashed on NULL in complexity metrics.
Now returns 0 for missing values.

Fixes #456
```

### 6. Submit Pull Request

```bash
# Push branch
git push origin feature/my-new-feature

# Create PR on GitHub
```

**PR checklist:**
- [ ] Tests pass (`pytest`)
- [ ] Code formatted (`black`)
- [ ] Linting passes (`flake8`)
- [ ] Type checking passes (`mypy`)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated

**PR description template:**

```markdown
## Description
Brief description of changes

## Motivation
Why is this change needed?

## Changes
- Change 1
- Change 2

## Testing
How was this tested?

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] CHANGELOG updated
```

## Architecture Guidelines

### Agent Design Pattern

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseAgent(ABC):
    """Base class for all agents."""

    def __init__(self, llm=None, config=None):
        self.llm = llm
        self.config = config or get_global_config()

    @abstractmethod
    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent logic."""
        pass

    def _handle_error(self, error: Exception) -> Dict[str, Any]:
        """Standard error handling."""
        return {'success': False, 'error': str(error)}
```

### Workflow Design Pattern

```python
from langgraph.graph import StateGraph, END

def create_workflow() -> StateGraph:
    """Create LangGraph workflow."""
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("generate", generate_node)

    # Define edges
    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()
```

### Error Handling

```python
from src.errors import AgentExecutionError, CPGQueryError

try:
    result = agent.execute(input)
except CPGQueryError as e:
    # Recoverable - retry or fallback
    logger.warning(f"Query failed: {e}, trying fallback")
    result = fallback_query(input)
except AgentExecutionError as e:
    # Non-recoverable - propagate
    logger.error(f"Agent failed: {e}")
    raise
```

## Testing Guidelines

### Unit Tests
- Test individual functions/methods
- Mock external dependencies
- Fast execution (<1s per test)

```python
from unittest.mock import Mock, patch

def test_generator_with_mock_llm():
    mock_llm = Mock()
    mock_llm.generate.return_value = "SELECT * FROM nodes"

    generator = SQLQueryGenerator(llm=mock_llm)
    query = generator.generate("test question", [])

    assert query == "SELECT * FROM nodes"
    mock_llm.generate.assert_called_once()
```

### Integration Tests
- Test component interactions
- Use real dependencies (DuckDB, etc.)
- Longer execution allowed (<10s per test)

```python
def test_end_to_end_workflow():
    workflow = MultiScenarioWorkflow()
    result = workflow.run(
        question="Find complex functions",
        scenario="code_review"
    )

    assert result['success'] == True
    assert result['query'] is not None
```

### Benchmarking Tests
- Measure performance
- Use `pytest-benchmark`

```python
def test_retrieval_performance(benchmark):
    retriever = RetrieverAgent()

    result = benchmark(
        retriever.retrieve,
        question="test",
        analysis={},
        top_k=5
    )

    # Should be <100ms
    assert benchmark.stats.mean < 0.1
```

## Documentation

### Code Documentation

```python
def my_function(param1: str, param2: int = 0) -> Dict[str, Any]:
    """
    One-line summary.

    Detailed description of what the function does,
    including any important details about behavior.

    Args:
        param1: Description of param1
        param2: Description of param2, defaults to 0

    Returns:
        Dictionary containing:
        - 'result': The computed result
        - 'metadata': Additional information

    Raises:
        ValueError: If param1 is empty
        CPGQueryError: If query execution fails

    Example:
        >>> result = my_function("test", param2=5)
        >>> print(result['result'])
        'processed_test'
    """
```

### User Documentation

- Add to `docs/scenarios/` for new scenarios
- Update `README.md` for major features
- Create Jupyter notebooks for tutorials

## Review Process

### Code Review Checklist

**Functionality:**
- [ ] Code works as intended
- [ ] Edge cases handled
- [ ] Error handling appropriate

**Code Quality:**
- [ ] Follows project conventions
- [ ] Well-documented
- [ ] No unnecessary complexity
- [ ] DRY principle followed

**Testing:**
- [ ] Adequate test coverage (>80%)
- [ ] Tests are meaningful
- [ ] All tests pass

**Performance:**
- [ ] No obvious performance issues
- [ ] Database queries optimized
- [ ] Memory usage reasonable

### Responding to Feedback

- Address all review comments
- Push fixes to the same branch
- Re-request review when ready

## Release Process

### Version Numbering

Semantic versioning: `MAJOR.MINOR.PATCH`

- `MAJOR`: Breaking changes
- `MINOR`: New features (backward compatible)
- `PATCH`: Bug fixes

### Creating a Release

1. Update version in `setup.py` and `__init__.py`
2. Update `CHANGELOG.md`
3. Create git tag: `git tag v1.2.3`
4. Push tag: `git push origin v1.2.3`
5. GitHub Actions will build and publish

## Questions?

- **Bugs**: Open an issue on GitHub
- **Features**: Open a discussion first
- **Questions**: Ask in GitHub Discussions

Thank you for contributing! 🎉
```

---

## 📅 Week 8: Deployment

### Task 3: Deployment Automation (Day 1-3)

#### Motivation
**Problem:** Manual deployment is error-prone
**Solution:** Containerization + CI/CD automation

#### Deliverables

**1. Dockerfile** - Day 1

```dockerfile
# Dockerfile

FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    openjdk-11-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# Install Joern
RUN curl -L https://github.com/joernio/joern/releases/download/v2.0.0/joern-cli.zip -o joern.zip \
    && unzip joern.zip -d /opt \
    && rm joern.zip

ENV PATH="/opt/joern-cli:${PATH}"

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create volume for CPG database
VOLUME ["/app/data"]

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**2. Docker Compose** - Day 1

```yaml
# docker-compose.yml

version: '3.8'

services:
  cpg-copilot:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GIGACHAT_AUTH_KEY=${GIGACHAT_AUTH_KEY}
      - DATABASE_PATH=/app/data/cpg.duckdb
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
      - ./config.yaml:/app/config.yaml:ro
    depends_on:
      - prometheus
      - grafana
    restart: unless-stopped
    networks:
      - cpg-network

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - cpg-network

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - ./monitoring/grafana-dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./monitoring/grafana-datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml:ro
      - grafana-data:/var/lib/grafana
    depends_on:
      - prometheus
    networks:
      - cpg-network

volumes:
  prometheus-data:
  grafana-data:

networks:
  cpg-network:
    driver: bridge
```

**Usage:**

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f cpg-copilot

# Stop
docker-compose down

# Rebuild after changes
docker-compose up -d --build
```

**3. Kubernetes Manifests (Optional)** - Day 2

```yaml
# k8s/deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: cpg-copilot
  labels:
    app: cpg-copilot
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cpg-copilot
  template:
    metadata:
      labels:
        app: cpg-copilot
    spec:
      containers:
      - name: cpg-copilot
        image: cpg-copilot:latest
        ports:
        - containerPort: 8000
        env:
        - name: GIGACHAT_AUTH_KEY
          valueFrom:
            secretKeyRef:
              name: cpg-secrets
              key: gigachat-auth-key
        - name: DATABASE_PATH
          value: /app/data/cpg.duckdb
        volumeMounts:
        - name: cpg-data
          mountPath: /app/data
        - name: config
          mountPath: /app/config.yaml
          subPath: config.yaml
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
      volumes:
      - name: cpg-data
        persistentVolumeClaim:
          claimName: cpg-pvc
      - name: config
        configMap:
          name: cpg-config
---
apiVersion: v1
kind: Service
metadata:
  name: cpg-copilot-service
spec:
  selector:
    app: cpg-copilot
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: cpg-pvc
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

**4. CI/CD Pipeline (GitHub Actions)** - Day 3

```yaml
# .github/workflows/ci-cd.yml

name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'

    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Lint with flake8
      run: |
        flake8 src/ tests/ --count --max-line-length=120

    - name: Type check with mypy
      run: |
        mypy src/

    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov=src --cov-report=xml

    - name: Run integration tests
      run: |
        pytest tests/integration/ -v

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage.xml

  benchmark:
    runs-on: ubuntu-latest
    needs: test

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest-benchmark

    - name: Run benchmarks
      run: |
        pytest tests/benchmark/ --benchmark-only --benchmark-json=benchmark.json

    - name: Store benchmark results
      uses: benchmark-action/github-action-benchmark@v1
      with:
        tool: 'pytest'
        output-file-path: benchmark.json
        github-token: ${{ secrets.GITHUB_TOKEN }}

  build:
    runs-on: ubuntu-latest
    needs: [test, benchmark]
    if: github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2

    - name: Login to Docker Hub
      uses: docker/login-action@v2
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}

    - name: Build and push
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: |
          user/cpg-copilot:latest
          user/cpg-copilot:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy:
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'

    steps:
    - name: Deploy to production
      run: |
        # Add your deployment commands here
        # Example: kubectl set image deployment/cpg-copilot cpg-copilot=user/cpg-copilot:${{ github.sha }}
        echo "Deployment would happen here"
```

---

### Task 4: Performance Validation (Day 4-5)

#### Motivation
**Problem:** Unknown production performance characteristics
**Solution:** Comprehensive load testing and profiling

#### Deliverables

**1. Load Testing Script** - Day 4

```python
# tests/load/locustfile.py

from locust import HttpUser, task, between
import random

class CPGCopilotUser(HttpUser):
    wait_time = between(1, 5)  # Wait 1-5s between requests

    # Test questions across scenarios
    questions = {
        'code_review': [
            "Which functions have the highest cyclomatic complexity?",
            "Find functions with more than 10 parameters",
            "Show functions longer than 200 lines"
        ],
        'security_audit': [
            "Find potential SQL injection points",
            "Which functions handle user input without validation?",
            "Find buffer overflow vulnerabilities"
        ],
        'performance_optimization': [
            "Find I/O operations in hot paths",
            "Which functions have the most loop iterations?",
            "Find memory allocation in critical sections"
        ]
    }

    @task(10)  # Weight: most common
    def query_code_review(self):
        """Test code review queries."""
        question = random.choice(self.questions['code_review'])
        self.client.post("/query", json={
            'question': question,
            'scenario': 'code_review'
        })

    @task(5)
    def query_security_audit(self):
        """Test security audit queries."""
        question = random.choice(self.questions['security_audit'])
        self.client.post("/query", json={
            'question': question,
            'scenario': 'security_audit'
        })

    @task(3)
    def query_performance(self):
        """Test performance queries."""
        question = random.choice(self.questions['performance_optimization'])
        self.client.post("/query", json={
            'question': question,
            'scenario': 'performance_optimization'
        })

    @task(1)
    def query_streaming(self):
        """Test streaming endpoint."""
        question = random.choice(self.questions['code_review'])
        with self.client.post("/query/stream", json={
            'question': question
        }, catch_response=True, stream=True) as response:
            if response.status_code == 200:
                # Consume stream
                for line in response.iter_lines():
                    pass
                response.success()

    def on_start(self):
        """Called when user starts."""
        # Optional: login or setup
        pass
```

**Run load test:**

```bash
# Install Locust
pip install locust

# Run with 100 concurrent users
locust -f tests/load/locustfile.py --host=http://localhost:8000 --users=100 --spawn-rate=10 --run-time=5m

# View results at http://localhost:8089
```

**2. Memory Profiling** - Day 4

```python
# tests/profiling/profile_memory.py

from memory_profiler import profile
from src.workflow.multi_scenario_workflow import MultiScenarioWorkflow

@profile
def test_memory_usage():
    """Profile memory usage during workflow execution."""
    workflow = MultiScenarioWorkflow()

    questions = [
        "Find functions with high complexity",
        "Find security vulnerabilities",
        "Find performance bottlenecks"
    ] * 10  # 30 queries

    for q in questions:
        result = workflow.run(q, scenario='code_review')
        print(f"Query: {q[:50]}... - Result count: {len(result.get('results', []))}")

if __name__ == '__main__':
    test_memory_usage()
```

**Run:**

```bash
pip install memory-profiler
python -m memory_profiler tests/profiling/profile_memory.py

# Output shows line-by-line memory usage
```

**3. Performance Benchmarks** - Day 5

```python
# tests/benchmark/test_performance.py

import pytest
from src.workflow.multi_scenario_workflow import MultiScenarioWorkflow

@pytest.fixture
def workflow():
    return MultiScenarioWorkflow()

@pytest.mark.benchmark(group="retrieval")
def test_retrieval_speed(benchmark, workflow):
    """Benchmark retrieval performance."""
    result = benchmark(
        workflow.retriever.retrieve,
        question="Find complex functions",
        analysis={'domain': 'generic'},
        top_k=5
    )

    # Should be <100ms
    assert benchmark.stats.mean < 0.1

@pytest.mark.benchmark(group="generation")
def test_generation_speed(benchmark, workflow):
    """Benchmark query generation."""
    context = [
        {'question': 'test', 'query': 'SELECT * FROM nodes', 'domain': 'generic'}
    ] * 5

    result = benchmark(
        workflow.generator.generate,
        question="Find complex functions",
        context=context
    )

    # Should be <2s (LLM call)
    assert benchmark.stats.mean < 2.0

@pytest.mark.benchmark(group="execution")
def test_execution_speed(benchmark, workflow):
    """Benchmark query execution."""
    query = """
        SELECT properties->>'NAME' as name,
               properties->>'CYCLOMATIC_COMPLEXITY' as complexity
        FROM nodes
        WHERE label = 'METHOD'
        AND CAST(properties->>'CYCLOMATIC_COMPLEXITY' AS INTEGER) > 10
        LIMIT 100
    """

    result = benchmark(
        workflow.executor.execute,
        query=query
    )

    # Should be <500ms
    assert benchmark.stats.mean < 0.5

@pytest.mark.benchmark(group="end-to-end")
def test_end_to_end_speed(benchmark, workflow):
    """Benchmark full workflow."""
    result = benchmark(
        workflow.run,
        question="Find functions with high complexity",
        scenario='code_review'
    )

    # Should be <5s (with caching)
    assert benchmark.stats.mean < 5.0
```

**Run benchmarks:**

```bash
# Run all benchmarks
pytest tests/benchmark/ --benchmark-only

# Generate HTML report
pytest tests/benchmark/ --benchmark-only --benchmark-html=benchmark_report.html

# Compare with previous runs
pytest tests/benchmark/ --benchmark-only --benchmark-compare=0001
```

**4. Scalability Report** - Day 5

```python
# tests/profiling/generate_scalability_report.py

import time
import psutil
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from src.workflow.multi_scenario_workflow import MultiScenarioWorkflow

def measure_throughput(num_concurrent: int, duration: int = 60):
    """Measure system throughput with N concurrent requests."""
    workflow = MultiScenarioWorkflow()

    questions = [
        "Find complex functions",
        "Find security vulnerabilities",
        "Find performance issues"
    ]

    completed = []
    errors = []

    def worker():
        start = time.time()
        while time.time() - start < duration:
            try:
                q = np.random.choice(questions)
                t0 = time.time()
                result = workflow.run(q, scenario='code_review')
                latency = time.time() - t0
                completed.append(latency)
            except Exception as e:
                errors.append(str(e))

    # Run concurrent workers
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [executor.submit(worker) for _ in range(num_concurrent)]
        for f in futures:
            f.result()
    total_time = time.time() - start_time

    return {
        'concurrent_users': num_concurrent,
        'total_requests': len(completed),
        'throughput_qps': len(completed) / total_time,
        'avg_latency': np.mean(completed),
        'p50_latency': np.percentile(completed, 50),
        'p95_latency': np.percentile(completed, 95),
        'p99_latency': np.percentile(completed, 99),
        'error_rate': len(errors) / (len(completed) + len(errors)),
        'errors': errors
    }

def generate_report():
    """Generate scalability report."""
    print("=" * 80)
    print("CPG Copilot Scalability Report")
    print("=" * 80)
    print()

    # Test with increasing concurrency
    concurrency_levels = [1, 5, 10, 20, 50, 100]

    results = []
    for n in concurrency_levels:
        print(f"Testing with {n} concurrent users...")
        result = measure_throughput(num_concurrent=n, duration=60)
        results.append(result)

        print(f"  Throughput: {result['throughput_qps']:.2f} QPS")
        print(f"  Avg Latency: {result['avg_latency']:.3f}s")
        print(f"  P95 Latency: {result['p95_latency']:.3f}s")
        print(f"  P99 Latency: {result['p99_latency']:.3f}s")
        print(f"  Error Rate: {result['error_rate']:.2%}")
        print()

    # Summary table
    print("=" * 80)
    print("Summary Table")
    print("=" * 80)
    print(f"{'Users':<10} {'QPS':<10} {'Avg (s)':<10} {'P95 (s)':<10} {'P99 (s)':<10} {'Errors':<10}")
    print("-" * 80)
    for r in results:
        print(f"{r['concurrent_users']:<10} "
              f"{r['throughput_qps']:<10.2f} "
              f"{r['avg_latency']:<10.3f} "
              f"{r['p95_latency']:<10.3f} "
              f"{r['p99_latency']:<10.3f} "
              f"{r['error_rate']:<10.2%}")

    # System resource usage
    print()
    print("=" * 80)
    print("System Resource Usage")
    print("=" * 80)
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    print(f"CPU Usage: {cpu_percent}%")
    print(f"Memory Usage: {memory.percent}% ({memory.used / 1024**3:.2f} GB / {memory.total / 1024**3:.2f} GB)")

    # Recommendations
    print()
    print("=" * 80)
    print("Recommendations")
    print("=" * 80)

    max_qps = max(r['throughput_qps'] for r in results)
    ideal_concurrency = next(r['concurrent_users'] for r in results if r['throughput_qps'] >= max_qps * 0.95)

    print(f"✅ Maximum throughput: {max_qps:.2f} QPS")
    print(f"✅ Recommended concurrency: {ideal_concurrency} users")

    if results[-1]['error_rate'] > 0.01:
        print(f"⚠️  High error rate at {concurrency_levels[-1]} users - consider scaling")

    if results[-1]['p99_latency'] > 10:
        print(f"⚠️  High P99 latency - consider caching or optimization")

    # Save to file
    import json
    with open('scalability_report.json', 'w') as f:
        json.dump(results, f, indent=2)

    print()
    print("Report saved to scalability_report.json")

if __name__ == '__main__':
    generate_report()
```

**Run:**

```bash
python tests/profiling/generate_scalability_report.py
```

**Expected Output:**

```
================================================================================
CPG Copilot Scalability Report
================================================================================

Testing with 1 concurrent users...
  Throughput: 2.34 QPS
  Avg Latency: 0.427s
  P95 Latency: 0.823s
  P99 Latency: 1.234s
  Error Rate: 0.00%

Testing with 5 concurrent users...
  Throughput: 10.12 QPS
  Avg Latency: 0.493s
  P95 Latency: 1.045s
  P99 Latency: 1.534s
  Error Rate: 0.00%

...

================================================================================
Summary Table
================================================================================
Users      QPS        Avg (s)    P95 (s)    P99 (s)    Errors
--------------------------------------------------------------------------------
1          2.34       0.427      0.823      1.234      0.00%
5          10.12      0.493      1.045      1.534      0.00%
10         18.45      0.541      1.234      1.876      0.00%
20         32.67      0.612      1.456      2.123      0.50%
50         45.23      1.105      2.345      3.456      2.30%
100        48.91      2.045      4.567      6.789      8.70%

================================================================================
System Resource Usage
================================================================================
CPU Usage: 75.3%
Memory Usage: 62.1% (4.97 GB / 8.00 GB)

================================================================================
Recommendations
================================================================================
✅ Maximum throughput: 48.91 QPS
✅ Recommended concurrency: 50 users
⚠️  High error rate at 100 users - consider scaling
⚠️  High P99 latency - consider caching or optimization

Report saved to scalability_report.json
```

---

## 📈 Success Criteria

### Documentation
- [ ] Complete user guides for all 16 scenarios
- [ ] API documentation (Swagger/OpenAPI) accessible
- [ ] 5 Jupyter notebook tutorials working
- [ ] Troubleshooting guide covers common issues
- [ ] Developer documentation (ADRs, code walkthrough, contributing guide)

### Deployment
- [ ] One-command Docker deployment works
- [ ] Docker Compose setup includes monitoring
- [ ] Kubernetes manifests validated (optional)
- [ ] CI/CD pipeline passes all stages
- [ ] Automated tests run on every commit

### Performance
- [ ] Load testing: System handles 100 concurrent users
- [ ] Throughput: >50 QPS sustained
- [ ] Latency: P95 <2s, P99 <5s
- [ ] Error rate: <1% under normal load
- [ ] Memory usage: <4GB per instance
- [ ] Scalability report delivered

---

## 📊 Deliverables Checklist

### Week 7: Documentation
- [ ] Scenario guides (16 files in docs/scenarios/)
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Jupyter notebooks (5 tutorials in docs/notebooks/)
- [ ] Troubleshooting guide (docs/TROUBLESHOOTING.md)
- [ ] Architecture Decision Records (5 ADRs in docs/adr/)
- [ ] Code walkthrough (docs/developers/code_walkthrough.md)
- [ ] Contributing guidelines (CONTRIBUTING.md)

### Week 8: Deployment
- [ ] Dockerfile (production-ready)
- [ ] Docker Compose setup (with monitoring)
- [ ] Kubernetes manifests (k8s/*.yaml) - optional
- [ ] CI/CD pipeline (.github/workflows/ci-cd.yml)
- [ ] Load testing script (tests/load/locustfile.py)
- [ ] Memory profiling (tests/profiling/profile_memory.py)
- [ ] Performance benchmarks (tests/benchmark/test_performance.py)
- [ ] Scalability report (scalability_report.json)

---

## 🎯 Final Checklist

### Production Readiness
- [ ] All 16 scenarios fully documented
- [ ] API accessible via Swagger UI
- [ ] One-command deployment tested
- [ ] CI/CD pipeline passing
- [ ] Load testing: 100 QPS without degradation
- [ ] Memory profiling: No leaks detected
- [ ] Performance benchmarks: All <threshold
- [ ] Scalability report: Recommendations documented

### Release Preparation
- [ ] Version bumped (v1.0.0)
- [ ] CHANGELOG.md updated
- [ ] Release notes drafted
- [ ] Docker images published
- [ ] Documentation site live

---

**Last Updated:** November 25, 2025
**Status:** Ready for Implementation
**Previous:** [UX_IMPROVEMENTS_PLAN.md](UX_IMPROVEMENTS_PLAN.md) - Phase 3

**🎉 Final Phase - Ready for Production Release! 🎉**
