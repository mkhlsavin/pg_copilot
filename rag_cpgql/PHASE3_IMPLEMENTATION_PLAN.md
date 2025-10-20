# Phase 3: DDG (Data Dependency Graph) Integration - Implementation Plan

**Date**: 2025-10-19
**Status**: Planning
**Goal**: Extract and index data flow patterns to enable "WHERE does data come from/go to" analysis

---

## Executive Summary

Phase 3 will add data dependency tracking to the RAG pipeline, completing the three-dimensional context system:

1. **Phase 1**: Documentation (WHAT) - Comments and docstrings
2. **Phase 2**: CFG (HOW) - Execution flow patterns
3. **Phase 3**: DDG (WHERE) - Data flow and dependencies

This will enable the system to answer questions like:
- "Where does this variable get its value from?"
- "What functions does this parameter flow into?"
- "How does data flow from input to output?"
- "What are the sources and sinks for this variable?"

---

## Phase 3 Objectives

### Primary Goals
1. Extract data dependency patterns from PostgreSQL codebase
2. Index patterns for semantic search
3. Integrate DDG retrieval into EnrichmentPromptBuilder
4. Enable data flow queries in the RAG pipeline

### Success Metrics
- Extract 30,000+ data flow patterns
- 100% extraction success rate
- Complete extraction in <60 minutes
- Average relevance score > 0.25
- Successful ChromaDB integration

---

## DDG Pattern Types

Based on data flow analysis capabilities, we'll extract these pattern types:

### 1. Parameter Flow Patterns
Track how function parameters flow through the code:
- Parameter to local variable assignments
- Parameter to function call arguments
- Parameter to return values
- Parameter to field accesses

**Example Natural Language**:
"Parameter 'relation' in heap_fetch flows to variable 'rel' and is passed to LockBuffer"

### 2. Local Variable Dependencies
Track local variable data flow:
- Variable definitions (assignments)
- Variable uses (reads)
- Variable-to-variable flow
- Variable-to-call flow

**Example**:
"Variable 'tuple' is assigned from HeapTupleSatisfiesMVCC result and flows to return statement"

### 3. Return Value Sources
Track what data flows into return statements:
- Direct parameter returns
- Local variable returns
- Function call result returns
- Computed expression returns

**Example**:
"Function heap_fetch returns 'tuple' which originates from parameter 'tid' through GetTupleForTrigger"

### 4. Call Argument Sources
Track data flow into function calls:
- Parameter-to-argument flow
- Local-to-argument flow
- Constant-to-argument flow
- Expression-to-argument flow

**Example**:
"Call to elog receives argument 'ERROR' (constant) and message constructed from 'relname' parameter"

### 5. Field Access Patterns
Track structure field data flow:
- Field reads and their uses
- Field writes and their sources
- Field-to-field dependencies
- Field-to-call dependencies

**Example**:
"Field 'relation->rd_rel->relname' is read and flows to elog call for error reporting"

### 6. Taint Analysis Patterns
Track potentially unsafe data flow:
- User input to sensitive sinks
- Unvalidated data flow
- Cross-boundary data flow
- Sanitization points

**Example**:
"Parameter 'snapshot' flows through 5 functions before reaching HeapTupleSatisfiesMVCC without validation"

---

## Architecture Design

### 3.1 DDG Extractor (`src/extraction/ddg_extractor.py`)

```python
@dataclass
class ParameterFlowPattern:
    """Parameter data flow pattern"""
    method_name: str
    file_path: str
    line_number: int
    param_name: str
    param_type: str
    flow_targets: List[str]  # Where parameter flows to
    description: str  # Natural language

@dataclass
class LocalVarDependency:
    """Local variable data dependency"""
    method_name: str
    file_path: str
    var_name: str
    var_type: str
    def_site: str  # Where defined
    use_sites: List[str]  # Where used
    description: str

# Similar dataclasses for other pattern types...

class DDGExtractor:
    """Extract data dependency patterns from CPG"""

    def extract_parameter_flows(self, batch_size=100, limit=10000):
        """Extract parameter flow patterns"""

    def extract_local_dependencies(self, batch_size=100, limit=10000):
        """Extract local variable dependencies"""

    def extract_return_sources(self, batch_size=100, limit=5000):
        """Extract return value data sources"""

    def extract_call_arg_sources(self, batch_size=100, limit=10000):
        """Extract call argument data sources"""

    def extract_field_access_flow(self, batch_size=100, limit=5000):
        """Extract field access data flow"""
```

### 3.2 DDG Vector Store (`src/retrieval/ddg_vector_store.py`)

Similar to Phase 2, create ChromaDB collection for DDG patterns:

```python
class DDGVectorStore:
    """Vector store for DDG patterns"""

    def __init__(self):
        self.collection_name = "ddg_patterns"
        self.client = chromadb.PersistentClient(path="./chroma_db")

    def index_patterns(self, patterns: List[DDGPattern]):
        """Index DDG patterns with embeddings"""

    def search(self, query: str, top_k: int = 10, relevance_threshold: float = 0.25):
        """Search for relevant DDG patterns"""
```

### 3.3 DDG Retriever (`src/retrieval/ddg_retriever.py`)

High-level API for DDG pattern retrieval:

```python
class DDGRetriever:
    """High-level DDG pattern retrieval API"""

    def retrieve_data_flow(self, query: str, top_k: int = 10):
        """Retrieve relevant data flow patterns"""

    def get_parameter_flows(self, method_name: str):
        """Get parameter flow for specific method"""

    def get_variable_dependencies(self, var_name: str):
        """Get dependencies for variable"""
```

### 3.4 Integration with EnrichmentPromptBuilder

Add DDG context to existing prompt builder:

```python
# In src/agents/enrichment_prompt_builder.py

def build_enriched_context(self, query: str) -> str:
    """Build enriched context with all three dimensions"""

    # Phase 1: Documentation context
    doc_context = self.doc_retriever.retrieve(query)

    # Phase 2: CFG context
    cfg_context = self.cfg_retriever.retrieve_patterns(query)

    # Phase 3: DDG context (NEW)
    ddg_context = self.ddg_retriever.retrieve_data_flow(query)

    return self._format_context(doc_context, cfg_context, ddg_context)
```

---

## Implementation Phases

### Phase 3.1: Exploration & Design (1-2 hours)
- [x] Create DDG exploration script
- [ ] Run DDG API tests
- [ ] Analyze Joern DDG capabilities
- [ ] Design DDG pattern types
- [ ] Document API findings

### Phase 3.2: Core Implementation (3-4 hours)
- [ ] Implement DDGExtractor
- [ ] Create pattern dataclasses
- [ ] Write extraction logic for each pattern type
- [ ] Add natural language description generation
- [ ] Implement batching and pagination

### Phase 3.3: Testing & Validation (1 hour)
- [ ] Test extractor with sample methods
- [ ] Validate pattern quality
- [ ] Check natural language descriptions
- [ ] Verify data completeness

### Phase 3.4: Full Extraction (30-60 minutes)
- [ ] Run full extraction on PostgreSQL codebase
- [ ] Monitor progress and handle errors
- [ ] Validate extraction results
- [ ] Save patterns to JSON

### Phase 3.5: Vector Store Integration (2 hours)
- [ ] Implement DDGVectorStore
- [ ] Create ChromaDB collection
- [ ] Index DDG patterns with embeddings
- [ ] Test pattern retrieval

### Phase 3.6: Retriever & Integration (2 hours)
- [ ] Implement DDGRetriever
- [ ] Add filtering and ranking
- [ ] Integrate into EnrichmentPromptBuilder
- [ ] Test end-to-end retrieval

### Phase 3.7: Documentation (1 hour)
- [ ] Document DDG pattern design
- [ ] Write extraction results analysis
- [ ] Create Phase 3 completion summary
- [ ] Update overall project documentation

---

## Expected Outputs

### Data Files
- `data/ddg_patterns.json` - Extracted DDG patterns (~100-200 MB)
- `data/ddg_extraction.log` - Extraction progress log
- `data/ddg_indexing.log` - Indexing progress log

### Code Files
- `src/extraction/ddg_extractor.py` - DDG pattern extractor
- `src/retrieval/ddg_vector_store.py` - DDG ChromaDB integration
- `src/retrieval/ddg_retriever.py` - High-level DDG retrieval API
- `src/agents/enrichment_prompt_builder.py` - Updated with DDG support

### Test Files
- `test_ddg_exploration.py` - DDG API exploration
- `test_ddg_extractor.py` - Extractor validation
- `ddg_exploration_results.json` - API test results
- `ddg_extractor_test_results.json` - Validation results

### Documentation
- `PHASE3_DDG_PATTERN_DESIGN.md` - Detailed pattern specifications
- `PHASE3_IMPLEMENTATION_PLAN.md` - This document
- `PHASE3_EXTRACTION_RESULTS.md` - Extraction analysis
- `PHASE3_COMPLETION_SUMMARY.md` - Final summary
- `PHASE3_STATUS.md` - Progress tracking

---

## Risk Assessment

### Technical Risks

**1. DDG API Limitations**
- Risk: Joern's DDG API may not support all desired traversals
- Mitigation: Explore API thoroughly, use alternative approaches if needed
- Status: In exploration

**2. Performance Concerns**
- Risk: Data flow analysis may be computationally expensive
- Mitigation: Use batching, optimize queries, set reasonable limits
- Status: Monitoring

**3. Pattern Relevance**
- Risk: DDG patterns may not provide useful semantic context
- Mitigation: Use natural language descriptions, filter by relevance
- Status: Design phase

**4. Data Volume**
- Risk: May extract too many low-value patterns
- Mitigation: Focus on high-value flows, set extraction limits
- Status: Planning

### Mitigation Strategies

1. **Incremental Development**: Test with small samples before full extraction
2. **Batch Processing**: Handle large datasets efficiently
3. **Quality Metrics**: Measure pattern usefulness early
4. **Fallback Options**: Design system to work without DDG if needed

---

## Success Criteria

### Phase 3 Complete When:
1. ✅ DDG patterns extracted successfully
2. ✅ Patterns indexed in ChromaDB
3. ✅ DDGRetriever integrated into EnrichmentPromptBuilder
4. ✅ End-to-end data flow queries work
5. ✅ Complete documentation written

### Quality Metrics:
- Extraction success rate: > 95%
- Pattern count: > 30,000
- Average relevance: > 0.25
- Extraction time: < 60 minutes
- Integration: Seamless with existing pipeline

---

## Timeline Estimate

**Total Estimated Time**: 10-12 hours

- Exploration & Design: 1-2 hours
- Core Implementation: 3-4 hours
- Testing & Validation: 1 hour
- Full Extraction: 30-60 minutes
- Vector Store Integration: 2 hours
- Retriever & Integration: 2 hours
- Documentation: 1 hour

**Expected Completion**: 2025-10-19 to 2025-10-20

---

## Next Steps

1. ✅ Create DDG exploration script
2. ⏳ Run DDG API tests (in progress)
3. ⏳ Analyze test results
4. ⏳ Finalize DDG pattern design
5. ⏳ Begin implementation

---

**Status**: Phase 3 planning complete, exploration in progress
**Last Updated**: 2025-10-19
