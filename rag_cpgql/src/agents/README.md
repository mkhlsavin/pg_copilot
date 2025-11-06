# Agents Module

This module contains the core agent implementations for the RAG-CPGQL system. Each agent handles a specific step in the query generation pipeline.

## Architecture Overview

The agent pipeline follows this sequence:
```
Question → Analyzer → Retriever → Enrichment → Generator → Interpreter
```

## Components

### 1. Analyzer Agent (`analyzer_agent.py`)
**Purpose**: Analyzes natural language questions to extract domain concepts, intent, and entities.

**Key Functions**:
- Domain classification (e.g., MVCC, WAL, indexing)
- Intent detection (e.g., finding methods, tracking data flow)
- Entity extraction (function names, concepts)

**Output**: Structured analysis used to guide retrieval and enrichment.

### 2. Retriever Agent (`retriever_agent.py`)
**Purpose**: Retrieves relevant context from vector stores.

**Data Sources**:
- Q&A pairs from PostgreSQL documentation and community
- CPGQL query examples
- CFG patterns (control flow graphs)
- DDG patterns (data dependency graphs)
- Documentation comments

**Output**: Top-k relevant documents for each context type.

### 3. Enrichment Agent (`enrichment_agent.py`)
**Purpose**: Enriches the query context with semantic metadata from the CPG.

**Key Features**:
- Integrates 12 semantic enrichment layers
- Builds three-dimensional context (Documentation + CFG + DDG)
- Uses `enrichment_prompt_builder.py` to construct structured prompts

**Enrichment Layers**:
1. Architectural layer tags
2. ACID pattern indicators
3. Access method markers
4. Complexity metrics
5. Concurrency pattern flags
6. Error handling attributes
7. Performance indicators
8. Security attributes
9. Transaction markers
10. Memory management tags
11. Storage engine patterns
12. System call annotations

**Output**: Enriched context with semantic tags and patterns.

### 4. Generator Agent (`generator_agent.py`)
**Purpose**: Generates CPGQL queries using Qwen3-Coder-30B LLM.

**Key Features**:
- Integrates enriched context into prompts
- Enforces CPGQL grammar constraints
- Validates generated queries
- Implements retry logic for invalid queries

**Model**: Qwen3-Coder-30B-A3B-Instruct (Q4_K_M quantized)

**Output**: Valid CPGQL query ready for execution.

### 5. Interpreter Agent (`interpreter_agent.py`)
**Purpose**: Interprets query execution results and generates natural language answers.

**Key Functions**:
- Result analysis
- Natural language explanation generation
- Error interpretation
- Success/failure reporting

**Output**: Human-readable answer to the original question.

## Supporting Components

### Enrichment Prompt Builder (`enrichment_prompt_builder.py`)
**Purpose**: Constructs structured prompts for the generator by combining:
- Retrieved Q&A context
- CFG patterns
- DDG patterns
- Documentation comments
- Semantic enrichment tags

**Key Features**:
- Context ranking and selection
- Prompt optimization
- Three-dimensional context integration

### Fallback Strategies (`fallback_strategies.py`)
**Purpose**: Implements fallback mechanisms when primary query generation fails.

**Strategies**:
1. Tag-only queries (using semantic tags)
2. Simplified pattern queries
3. Basic structural queries
4. Documentation-based queries

### Executor with Fallback (`executor_agent_with_fallback.py`)
**Purpose**: Executes queries with automatic fallback on failure.

**Features**:
- Multi-level fallback cascade
- Error analysis
- Strategy selection based on failure mode

### Tag Effectiveness Tracker (`tag_effectiveness_tracker.py`)
**Purpose**: Tracks which semantic tags are most effective for query generation.

**Metrics**:
- Tag usage frequency
- Query success rate by tag
- Coverage analysis

## Usage Example

```python
from src.agents.analyzer_agent import analyze_question
from src.agents.retriever_agent import retrieve_context
from src.agents.enrichment_agent import enrich_context
from src.agents.generator_agent import generate_query
from src.agents.interpreter_agent import interpret_results

# Pipeline execution
question = "How does PostgreSQL handle MVCC in heap access methods?"

# 1. Analyze
analysis = analyze_question(question)

# 2. Retrieve
context = retrieve_context(analysis)

# 3. Enrich
enriched_context = enrich_context(context, analysis)

# 4. Generate
query = generate_query(enriched_context)

# 5. Execute (via workflow)
# 6. Interpret
answer = interpret_results(query_results)
```

## Configuration

Agents are configured via `config.yaml`:
- Model paths and parameters
- Vector store locations
- Retrieval parameters (top-k, similarity thresholds)
- Enrichment layer selection

## Performance Metrics

- **Analyzer**: ~100ms per question
- **Retriever**: ~500ms (parallel vector store queries)
- **Enrichment**: ~200ms (CPG metadata lookup)
- **Generator**: ~2-5s (LLM inference)
- **Interpreter**: ~1-2s (result analysis)

**Total Pipeline**: ~4-8 seconds per question

## Dependencies

- `llama-cpp-python`: LLM inference
- `chromadb`: Vector store operations
- `langchain`: Agent orchestration utilities
- Custom extraction and retrieval modules

## See Also

- `/src/workflow/` - LangGraph orchestration
- `/src/retrieval/` - Vector store implementations
- `/src/extraction/` - CPG enrichment extractors
- `/src/generation/` - Prompt templates and LLM interface
