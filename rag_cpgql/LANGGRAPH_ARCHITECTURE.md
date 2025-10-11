# RAG-CPGQL v2: LangGraph Architecture Design

**Date:** 2025-10-10
**Status:** Design Phase
**Goal:** Redesign RAG pipeline using LangGraph for orchestration and RAGAS for evaluation

## Current Architecture Problems

### Existing System (`rag_pipeline.py`)
```
Question → Mock RAG → Simple Prompt → Grammar LLM → Query → Mock Joern → Answer
```

**Issues:**
1. ❌ **No real RAG**: Vector store is mocked
2. ❌ **Simple prompts**: Only 8 basic examples, no enrichment context
3. ❌ **No retrieval**: Not using 5,361 CPGQL training examples
4. ❌ **Generic queries**: `cpg.method.l` - won't work on 450k vertex graph
5. ❌ **No evaluation loop**: Can't measure/improve quality
6. ❌ **Linear flow**: No retries, refinement, or adaptation

## Proposed LangGraph Architecture

### Multi-Agent Workflow with State Management

```
┌─────────────────────────────────────────────────────────────────┐
│                      LangGraph StateGraph                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │  Question    │──────▶│   Analyzer   │──────▶│  Retriever   │  │
│  │  Input       │      │    Agent     │      │    Agent     │  │
│  └──────────────┘      └──────────────┘      └──────────────┘  │
│                              │                      │            │
│                              ▼                      ▼            │
│                        Extract intent      Retrieve:            │
│                        Identify domain     - Similar Q&A (3)    │
│                        Detect keywords     - CPGQL examples (5) │
│                                           - Enrichment tags     │
│                                                   │             │
│                                                   ▼             │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │   Executor   │◀─────│  Generator   │◀─────│  Enrichment  │ │
│  │    Agent     │      │    Agent     │      │    Agent     │ │
│  └──────────────┘      └──────────────┘      └──────────────┘ │
│        │                     │                      │           │
│        │                     │                      ▼           │
│        │                     │              Build context with  │
│        │                     │              relevant tags       │
│        │                     │                                  │
│        │                     ▼                                  │
│        │              Generate CPGQL                            │
│        │              with grammar + context                    │
│        │                     │                                  │
│        ▼                     ▼                                  │
│   Execute on          ┌──────────────┐                         │
│   Joern server        │  Validator   │                         │
│        │              │    Agent     │                         │
│        │              └──────────────┘                         │
│        │                     │                                  │
│        │                     ▼                                  │
│        │              Syntax check                              │
│        │              Safety check                              │
│        │                     │                                  │
│        │                     ▼                                  │
│        │              ┌──────────────┐                         │
│        │              │   Refiner    │                         │
│        │              │    Agent     │◀────────┐               │
│        │              └──────────────┘         │               │
│        │                     │                 │               │
│        │                     ▼                 │               │
│        │              If error: refine         │               │
│        │              (max 2 retries)          │               │
│        │                     │                 │               │
│        └─────────────────────┴─────────────────┘               │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │  Evaluator   │◀─────│ Interpreter  │◀─────│   Results    │ │
│  │  (RAGAS)     │      │    Agent     │      │              │ │
│  └──────────────┘      └──────────────┘      └──────────────┘ │
│        │                     │                                  │
│        ▼                     ▼                                  │
│   Compute metrics      Convert results                         │
│   - Faithfulness       to natural language                     │
│   - Answer relevance                                           │
│   - Context precision                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## State Schema

```python
from typing import TypedDict, List, Optional
from langchain_core.messages import BaseMessage

class RAGCPGQLState(TypedDict):
    """State passed between LangGraph nodes."""

    # Input
    question: str

    # Analysis
    intent: str  # "find-function", "explain-concept", "security-check"
    domain: str  # "memory", "query-planning", "wal", "vacuum", etc.
    keywords: List[str]

    # Retrieval
    similar_qa: List[dict]  # Top-3 similar Q&A pairs
    cpgql_examples: List[dict]  # Top-5 CPGQL examples
    enrichment_tags: dict  # Relevant tags from enriched CPG

    # Generation
    cpgql_query: str
    query_valid: bool
    validation_error: Optional[str]
    retry_count: int

    # Execution
    execution_result: Optional[dict]
    execution_success: bool
    execution_error: Optional[str]

    # Interpretation
    answer: str

    # Evaluation (RAGAS)
    faithfulness: float
    answer_relevance: float
    context_precision: float
    overall_score: float

    # Metadata
    messages: List[BaseMessage]
    iteration: int
```

## Agent Definitions

### 1. Analyzer Agent

**Purpose:** Understand question intent and domain

```python
from langgraph.graph import StateGraph

def analyze_question(state: RAGCPGQLState) -> RAGCPGQLState:
    """
    Analyze question to extract:
    - Intent (find/explain/check)
    - Domain (vacuum/wal/query-planning/etc.)
    - Keywords for retrieval
    """
    question = state["question"]

    # Use LLM to classify
    prompt = f"""Analyze this PostgreSQL question:

Question: {question}

Extract:
1. Intent: find-function | explain-concept | security-check
2. Domain: memory | query-planning | wal | vacuum | mvcc | replication | other
3. Keywords: List 3-5 key terms

Output JSON:
{{"intent": "...", "domain": "...", "keywords": [...]}}
"""

    result = llm.invoke(prompt)
    parsed = json.loads(result)

    state["intent"] = parsed["intent"]
    state["domain"] = parsed["domain"]
    state["keywords"] = parsed["keywords"]

    return state
```

### 2. Retriever Agent

**Purpose:** Retrieve relevant context from vector store

```python
def retrieve_context(state: RAGCPGQLState) -> RAGCPGQLState:
    """
    Retrieve from ChromaDB:
    - Similar Q&A pairs (top-3)
    - CPGQL examples (top-5)
    """
    question = state["question"]
    keywords = state["keywords"]
    domain = state["domain"]

    # Vector store retrieval
    vector_store = VectorStore()

    # Retrieve Q&A pairs
    similar_qa = vector_store.retrieve_qa(
        query=question,
        top_k=3,
        filter={"domain": domain}  # Domain-specific
    )

    # Retrieve CPGQL examples
    cpgql_examples = vector_store.retrieve_cpgql(
        query=question,
        keywords=keywords,
        top_k=5
    )

    state["similar_qa"] = similar_qa
    state["cpgql_examples"] = cpgql_examples

    return state
```

### 3. Enrichment Agent

**Purpose:** Get relevant enrichment tags from CPG metadata

```python
def get_enrichment_hints(state: RAGCPGQLState) -> RAGCPGQLState:
    """
    Query enriched CPG metadata to find relevant tags.

    Example: For "MVCC" question, find:
    - feature: "MVCC"
    - domain-concept: "mvcc"
    - function-purpose: "transaction-management"
    """
    domain = state["domain"]
    keywords = state["keywords"]

    # Query CPG metadata (can be cached)
    enrichment_tags = {
        "features": [],
        "domain_concepts": [],
        "data_structures": []
    }

    # Map domain/keywords to known enrichment tags
    tag_mapping = load_enrichment_mapping()

    for keyword in keywords:
        if keyword.lower() in tag_mapping:
            enrichment_tags["features"].extend(
                tag_mapping[keyword.lower()].get("features", [])
            )
            enrichment_tags["domain_concepts"].extend(
                tag_mapping[keyword.lower()].get("concepts", [])
            )

    state["enrichment_tags"] = enrichment_tags

    return state
```

### 4. Generator Agent

**Purpose:** Generate CPGQL query with full context

```python
from generation.prompts import build_enriched_prompt

def generate_cpgql(state: RAGCPGQLState) -> RAGCPGQLState:
    """
    Generate CPGQL query using:
    - Grammar constraints (mandatory)
    - Retrieved Q&A examples
    - CPGQL examples
    - Enrichment tag context
    """
    question = state["question"]
    similar_qa = state["similar_qa"]
    cpgql_examples = state["cpgql_examples"]
    enrichment_tags = state["enrichment_tags"]

    # Build rich prompt
    prompt = build_enriched_prompt(
        question=question,
        similar_qa=similar_qa,
        cpgql_examples=cpgql_examples,
        enrichment_tags=enrichment_tags
    )

    # Generate with grammar
    generator = CPGQLGenerator(llm, use_grammar=True)
    query = generator.generate_query(
        question=question,
        enrichment_hints=format_enrichment_hints(enrichment_tags)
    )

    state["cpgql_query"] = query
    state["retry_count"] = 0

    return state
```

### 5. Validator Agent

**Purpose:** Validate query syntax and safety

```python
def validate_query(state: RAGCPGQLState) -> RAGCPGQLState:
    """Validate generated query."""
    query = state["cpgql_query"]

    validator = QueryValidator()
    is_valid, error = validator.validate(query)

    state["query_valid"] = is_valid
    state["validation_error"] = error

    return state
```

### 6. Refiner Agent

**Purpose:** Refine query if validation fails

```python
def refine_query(state: RAGCPGQLState) -> RAGCPGQLState:
    """
    Refine query based on validation error.
    Max 2 retries.
    """
    if state["retry_count"] >= 2:
        # Give up, use fallback
        state["cpgql_query"] = "cpg.method.name.l"
        state["query_valid"] = True
        return state

    error = state["validation_error"]
    previous_query = state["cpgql_query"]

    # Refine using LLM
    prompt = f"""The query has an error. Fix it.

Previous query: {previous_query}
Error: {error}

Generate corrected query:
"""

    generator = CPGQLGenerator(llm, use_grammar=True)
    refined = generator.generate_query(prompt)

    state["cpgql_query"] = refined
    state["retry_count"] += 1

    return state
```

### 7. Executor Agent

**Purpose:** Execute query on Joern server

```python
def execute_query(state: RAGCPGQLState) -> RAGCPGQLState:
    """Execute CPGQL query on Joern server."""
    query = state["cpgql_query"]

    joern = JoernClient()
    result = joern.execute_query(query)

    state["execution_result"] = result
    state["execution_success"] = result.get("success", False)
    state["execution_error"] = result.get("error")

    return state
```

### 8. Interpreter Agent

**Purpose:** Convert results to natural language

```python
def interpret_results(state: RAGCPGQLState) -> RAGCPGQLState:
    """Convert query results to natural language answer."""
    question = state["question"]
    query = state["cpgql_query"]
    results = state["execution_result"]

    if not state["execution_success"]:
        state["answer"] = f"Query failed: {state['execution_error']}"
        return state

    # Use LLM to interpret
    prompt = f"""Answer the question using query results.

Question: {question}
Query: {query}
Results: {results}

Natural language answer:
"""

    answer = llm.invoke(prompt)
    state["answer"] = answer

    return state
```

### 9. Evaluator Agent (RAGAS)

**Purpose:** Evaluate answer quality

```python
from ragas import SingleTurnSample
from ragas.metrics import Faithfulness, AnswerRelevancy, ContextPrecision

async def evaluate_answer(state: RAGCPGQLState) -> RAGCPGQLState:
    """Evaluate answer using RAGAS metrics."""

    # Build RAGAS sample
    sample = SingleTurnSample(
        user_input=state["question"],
        response=state["answer"],
        retrieved_contexts=[
            qa["answer"] for qa in state["similar_qa"]
        ],
        reference=state.get("reference_answer")  # If available from test set
    )

    # Evaluate
    faithfulness = await Faithfulness(llm=evaluator_llm).single_turn_ascore(sample)
    answer_relevance = await AnswerRelevancy(llm=evaluator_llm).single_turn_ascore(sample)
    context_precision = await ContextPrecision(llm=evaluator_llm).single_turn_ascore(sample)

    state["faithfulness"] = faithfulness
    state["answer_relevance"] = answer_relevance
    state["context_precision"] = context_precision
    state["overall_score"] = (faithfulness + answer_relevance + context_precision) / 3

    return state
```

## Graph Construction

```python
from langgraph.graph import StateGraph, END

def build_rag_graph() -> StateGraph:
    """Build the RAG workflow graph."""

    # Create graph
    workflow = StateGraph(RAGCPGQLState)

    # Add nodes
    workflow.add_node("analyze", analyze_question)
    workflow.add_node("retrieve", retrieve_context)
    workflow.add_node("enrich", get_enrichment_hints)
    workflow.add_node("generate", generate_cpgql)
    workflow.add_node("validate", validate_query)
    workflow.add_node("refine", refine_query)
    workflow.add_node("execute", execute_query)
    workflow.add_node("interpret", interpret_results)
    workflow.add_node("evaluate", evaluate_answer)

    # Define edges
    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "retrieve")
    workflow.add_edge("retrieve", "enrich")
    workflow.add_edge("enrich", "generate")
    workflow.add_edge("generate", "validate")

    # Conditional: refine if invalid
    workflow.add_conditional_edges(
        "validate",
        lambda state: "refine" if not state["query_valid"] else "execute",
        {
            "refine": "refine",
            "execute": "execute"
        }
    )

    # Refine -> validate (loop)
    workflow.add_edge("refine", "validate")

    workflow.add_edge("execute", "interpret")
    workflow.add_edge("interpret", "evaluate")
    workflow.add_edge("evaluate", END)

    return workflow.compile()
```

## Benefits of This Architecture

### 1. **Modular & Testable**
- Each agent is independent
- Easy to test individual components
- Can swap implementations (e.g., different retrievers)

### 2. **Stateful & Resumable**
- LangGraph maintains state across steps
- Can pause for human review
- Automatically handles retries

### 3. **Context-Aware**
- Real RAG retrieval (not mocked)
- Enrichment-aware generation
- Domain-specific filtering

### 4. **Self-Improving**
- RAGAS metrics identify weak points
- Feedback loop for prompt refinement
- Can A/B test different strategies

### 5. **Production-Ready**
- Error handling at each step
- Graceful degradation
- Observable and debuggable

## Implementation Plan

### Phase 1: Setup (1-2 days)
- [ ] Install LangGraph, RAGAS, LangChain
- [ ] Setup ChromaDB vector store
- [ ] Index Q&A pairs and CPGQL examples

### Phase 2: Core Agents (2-3 days)
- [ ] Implement Analyzer agent
- [ ] Implement Retriever agent
- [ ] Implement Enrichment agent
- [ ] Implement Generator agent with enriched prompts

### Phase 3: Validation & Execution (1-2 days)
- [ ] Implement Validator agent
- [ ] Implement Refiner agent with retry logic
- [ ] Connect to real Joern server
- [ ] Implement Executor agent

### Phase 4: Evaluation (1-2 days)
- [ ] Implement Interpreter agent
- [ ] Integrate RAGAS metrics
- [ ] Create evaluation dashboard

### Phase 5: Testing (2-3 days)
- [ ] Test on 30 questions
- [ ] Compare with current system
- [ ] Iterate based on RAGAS scores
- [ ] Full 200-question evaluation

## Expected Improvements

| Metric | Current | Target |
|--------|---------|--------|
| Query Validity | 100% | 100% (maintain) |
| Query Quality | 45/100 | 80+/100 |
| Uses Enrichment | 0% | 80%+ |
| Answer Accuracy | Unknown | 70%+ (RAGAS) |
| Generation Time | 12-19s | <5s (caching) |

## Next Steps

1. Install dependencies
2. Start with Phase 1 (vector store setup)
3. Build incrementally, testing each agent
4. Integrate RAGAS early for feedback
