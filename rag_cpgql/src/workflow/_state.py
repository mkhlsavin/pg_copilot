"""LangGraph Workflow State Schema

Contains the RAGCPGQLState TypedDict that is passed between LangGraph nodes.
"""

from typing import TypedDict, List, Optional, Dict, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class RAGCPGQLState(TypedDict):
    """State passed between LangGraph nodes.

    This state is maintained throughout the entire workflow execution
    and is passed between all agent nodes.
    """

    # Input
    question: str

    # Analysis (Analyzer Agent)
    intent: Optional[str]  # "find-function", "explain-concept", "security-check"
    domain: Optional[str]  # "memory", "query-planning", "wal", "vacuum", etc.
    keywords: Optional[List[str]]
    complexity: Optional[str]  # "simple", "medium", "complex"

    # Phase 7: Query Mode Classification
    query_mode: Optional[str]  # "find-method" or "explain-logic"
    query_mode_confidence: Optional[float]  # Classification confidence

    # Retrieval (Retriever Agent)
    similar_qa: Optional[List[Dict]]  # Top-K similar Q&A pairs
    cpgql_examples: Optional[List[Dict]]  # Top-K CPGQL examples
    retrieval_metadata: Optional[Dict]  # Similarity scores, etc.

    # Enrichment (Enrichment Agent)
    enrichment_hints: Optional[List[str]]  # Relevant enrichment tags
    enrichment_coverage: Optional[float]  # Coverage score (0-1)

    # Generation (Generator Agent)
    cpgql_query: Optional[str]
    generation_time: Optional[float]
    query_variants: Optional[List[Dict]]  # Multi-query variants
    use_multi_query: Optional[bool]  # Feature flag for multi-query approach

    # Validation (Validator Agent)
    query_valid: bool
    validation_error: Optional[str]
    retry_count: int

    # Execution (Executor Agent)
    execution_result: Optional[Dict]
    execution_success: bool
    execution_time: Optional[float]
    execution_error: Optional[str]
    fallback_count: Optional[int]  # Number of fallbacks used
    specificity_used: Optional[str]  # Which variant succeeded (precise/balanced/broad)

    # Ranking (ResultRanker - Phase 2)
    ranked_results: Optional[List[Dict]]  # Results ranked by relevance with scores
    ranking_metadata: Optional[Dict]  # Top scores, ranking stats

    # Adaptive Refinement (AdaptiveQueryRefiner)
    question_type: Optional[str]  # Classified question type
    result_count: Optional[int]  # Number of results returned
    refinement_applied: Optional[bool]  # Whether refinement was applied
    refinement_strategy: Optional[str]  # Which strategy was used
    refinement_suggestions: Optional[List[Dict]]  # All suggestions generated

    # Interpretation (Interpreter Agent)
    answer: Optional[str]
    answer_confidence: Optional[float]

    # Phase 7: Control Flow Mode
    control_flow_queries: Optional[Dict]  # Generated CPGQL queries (entry point, keyword methods, call graph)
    control_flow_metadata: Optional[Dict]  # Query generation metadata
    entry_point_result: Optional[Dict]  # Entry point query result
    keyword_methods_result: Optional[List[Dict]]  # Keyword methods results
    call_graph_result: Optional[List[Dict]]  # Call graph results
    call_chain_analysis: Optional[Dict]  # Call chain analysis from CallChainAnalyzer
    logic_explanation: Optional[str]  # Synthesized logic explanation

    # Evaluation (RAGAS)
    faithfulness: Optional[float]
    answer_relevance: Optional[float]
    context_precision: Optional[float]
    context_recall: Optional[float]
    overall_score: Optional[float]

    # Metadata
    messages: Annotated[List[BaseMessage], add_messages]
    iteration: int
    total_time: Optional[float]
    error: Optional[str]


__all__ = ['RAGCPGQLState']
