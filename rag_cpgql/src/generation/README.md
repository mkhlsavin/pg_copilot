# Generation Module

This module handles CPGQL query generation using Large Language Models. It provides the interface between the enriched context and the LLM, managing prompts, inference, and query validation.

## Overview

The generation pipeline converts enriched context into valid CPGQL queries:

```
Enriched Context → Prompt Builder → LLM Inference → Query Validation → CPGQL Query
```

## Components

### 1. LLM Interface (`llm_interface.py`)

**Purpose**: Provides unified interface to Large Language Models.

**Supported Backends**:
- **llama.cpp** (Primary): Local inference via llama-cpp-python
- API-based models (extensible)

**Current Model**:
- **Model**: Qwen3-Coder-30B-A3B-Instruct
- **Quantization**: Q4_K_M (4-bit)
- **Size**: ~17GB
- **Context**: 32K tokens
- **Location**: `C:/Users/user/.lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/`

**Key Features**:
- Model loading and caching
- Temperature/sampling control
- Token limit management
- Streaming support (optional)
- Error handling and retries

**Configuration** (`config.yaml`):
```yaml
model:
  path: "C:/Users/user/.lmstudio/models/..."
  n_ctx: 32768
  n_gpu_layers: 35
  temperature: 0.1
  top_p: 0.95
  max_tokens: 2048
```

**Usage**:
```python
from src.generation.llm_interface import LLMInterface

llm = LLMInterface()
response = llm.generate(
    prompt="Generate CPGQL query...",
    temperature=0.1,
    max_tokens=1024
)
```

### 2. Prompt Templates (`prompts.py`)

**Purpose**: Manages all prompt templates for CPGQL query generation.

**Template Types**:

#### Base System Prompt
Defines the LLM's role and capabilities:
- CPGQL expert persona
- Syntax rules and constraints
- Output format requirements
- Error handling guidelines

#### Context-Enriched Prompts
Incorporates three-dimensional context:

1. **Q&A Context Section**:
   ```
   Relevant PostgreSQL Q&A pairs:
   Q: How does MVCC work?
   A: MVCC uses transaction IDs to determine tuple visibility...
   ```

2. **CPGQL Example Section**:
   ```
   Similar CPGQL queries:
   cpg.method("HeapTupleSatisfiesMVCC").tag.name(".*mvcc.*").l
   ```

3. **CFG Pattern Section**:
   ```
   Control flow patterns:
   Function: heap_insert
   Pattern: LockBuffer → Check visibility → UnlockBuffer
   Complexity: 12
   ```

4. **DDG Pattern Section**:
   ```
   Data flow patterns:
   xmin ← HeapTupleHeaderGetXmin(tuple->t_data)
   Concepts: [mvcc, heap-access]
   Flow depth: 3
   ```

5. **Documentation Section**:
   ```
   Function documentation:
   HeapTupleSatisfiesMVCC: Checks if tuple is visible to snapshot...
   ```

6. **Semantic Enrichment Section**:
   ```
   Available tags:
   - mvcc_transaction_visibility (42 methods)
   - wal_insertion (28 methods)
   - lock_acquisition (67 methods)
   ```

#### Query-Specific Prompts
- Simple queries (single method/tag)
- Complex queries (multi-step traversals)
- Aggregation queries (counts, statistics)
- Pattern matching queries (regex, filters)

**Key Functions**:
- `build_system_prompt()`: Base system instructions
- `build_enrichment_context(enriched_data)`: Format enrichment layers
- `build_full_prompt(question, context, enrichments)`: Complete prompt assembly
- `format_examples(examples)`: Format CPGQL examples
- `format_cfg_patterns(patterns)`: Format CFG context
- `format_ddg_patterns(patterns)`: Format DDG context

**Prompt Structure**:
```
[System Prompt]
You are a CPGQL expert...

[Context Section]
Question: {user_question}
Analysis: {domain, intent, entities}

[Retrieved Context]
- Q&A pairs
- CPGQL examples
- CFG patterns
- DDG patterns
- Documentation

[Enrichment Metadata]
- Semantic tags
- Metrics
- Patterns

[Generation Instructions]
Generate a valid CPGQL query that...
Output format: ```cpgql ... ```
```

**Usage**:
```python
from src.generation.prompts import build_full_prompt

prompt = build_full_prompt(
    question="How does PostgreSQL check tuple visibility?",
    context=retrieved_context,
    enrichments=enrichment_data
)
```

### 3. CPGQL Generator (`cpgql_generator.py`)

**Purpose**: Orchestrates the complete query generation process.

**Key Functions**:

#### `generate_query(question, context, enrichments)`
Main generation function:
1. Build prompt from context and enrichments
2. Call LLM via interface
3. Parse and extract CPGQL query
4. Validate syntax
5. Return query or error

#### `validate_cpgql_syntax(query)`
Basic syntax validation:
- Check for required elements (cpg., method., tag., etc.)
- Validate parentheses matching
- Check for common syntax errors
- Verify query completeness

#### `extract_query_from_response(llm_response)`
Parse LLM output:
- Extract code blocks (```cpgql ... ```)
- Clean whitespace
- Remove comments
- Handle multiple queries (take first valid)

**Generation Pipeline**:
```python
def generate_query(question, context, enrichments):
    # 1. Build prompt
    prompt = build_full_prompt(question, context, enrichments)

    # 2. Generate with LLM
    response = llm.generate(prompt, temperature=0.1)

    # 3. Extract query
    query = extract_query_from_response(response)

    # 4. Validate
    if validate_cpgql_syntax(query):
        return query
    else:
        raise ValidationError("Invalid CPGQL syntax")
```

**Error Handling**:
- Syntax errors → Retry with corrected prompt
- Generation timeout → Use fallback strategy
- Invalid output → Return error with diagnostics

**Usage**:
```python
from src.generation.cpgql_generator import generate_query

query = generate_query(
    question="Find all methods that acquire locks",
    context=retrieval_results,
    enrichments=enrichment_data
)
# Output: cpg.method.tag.name(".*lock_acquisition.*").name.l
```

## CPGQL Grammar Constraints

### Supported Constructs

**Basic Traversals**:
- `cpg.method` - All methods
- `cpg.method.name(".*foo.*")` - Methods by name
- `cpg.call` - All call sites
- `cpg.identifier` - All identifiers

**Filtering**:
- `.filter(m => m.tag.name("mvcc.*"))` - Tag-based filtering
- `.where(_.lineNumber > 100)` - Condition filtering
- `.name("^heap.*")` - Regex matching

**Traversal Steps**:
- `.caller` - Callers of methods
- `.callee` - Callees of methods
- `.parameter` - Method parameters
- `.ast` - AST children
- `.cfgNext` - CFG successors
- `.reachableBy` - Data flow reachability

**Aggregations**:
- `.l` - To list
- `.size` - Count
- `.name.l` - Extract names
- `.dedup` - Remove duplicates

**Tags**:
- `.tag` - All tags
- `.tag.name(".*mvcc.*")` - Tags by pattern
- `.tag.value` - Tag values

### Grammar File

CPGQL grammar constraints: `cpgql_gbnf/cpgql_llama_cpp_v2.gbnf`

Used for constrained generation (experimental).

## Performance Metrics

### Generation Latency
- **Prompt Building**: ~50ms
- **LLM Inference**: 2-5 seconds (30B model, Q4)
- **Validation**: ~10ms
- **Total**: ~2-6 seconds per query

### Generation Quality
- **Validity Rate**: 97.5% (on 200-question benchmark)
- **Execution Success**: 86.7% (on 30-question enrichment suite)
- **First-Try Success**: 89.2%
- **Retry Success**: 8.3% (after 1 retry)

### Model Performance
- **Throughput**: ~20 tokens/second (Q4_K_M quantization)
- **Memory Usage**: ~18GB RAM
- **GPU Acceleration**: 35 layers offloaded
- **Context Utilization**: avg 8,200 tokens per prompt

## Configuration

### Model Settings (`config.yaml`)

```yaml
generation:
  model:
    path: "C:/Users/user/.lmstudio/models/..."
    model_file: "qwen3-coder-30b-a3b-instruct-q4_k_m.gguf"
    n_ctx: 32768
    n_gpu_layers: 35

  inference:
    temperature: 0.1
    top_p: 0.95
    top_k: 40
    repeat_penalty: 1.1
    max_tokens: 2048

  retry:
    max_attempts: 2
    backoff: 1.5
```

### Prompt Configuration

```yaml
prompts:
  max_qa_examples: 10
  max_cpgql_examples: 5
  max_cfg_patterns: 10
  max_ddg_patterns: 15
  max_documentation: 5

  include_enrichments: true
  include_metrics: true
  include_examples: true
```

## Example Usage

### Complete Generation Flow

```python
from src.agents.analyzer_agent import analyze_question
from src.agents.retriever_agent import retrieve_context
from src.agents.enrichment_agent import enrich_context
from src.generation.cpgql_generator import generate_query

# Question
question = "How does PostgreSQL handle MVCC visibility checks?"

# 1. Analyze
analysis = analyze_question(question)

# 2. Retrieve
context = retrieve_context(analysis)

# 3. Enrich
enrichments = enrich_context(context, analysis)

# 4. Generate
query = generate_query(question, context, enrichments)

print(query)
# Output: cpg.method.name(".*HeapTupleSatisfies.*").tag.name(".*mvcc.*").l
```

## Dependencies

- `llama-cpp-python`: LLM inference engine
- `pyyaml`: Configuration management
- `re`: Regular expression parsing
- `logging`: Generation logging

## See Also

- `/src/agents/generator_agent.py` - High-level generation orchestration
- `/src/agents/enrichment_prompt_builder.py` - Advanced prompt construction
- `/src/workflow/` - LangGraph integration with retry logic
- `/cpgql_gbnf/` - Grammar constraints for structured generation
