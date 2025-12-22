"""
Workflow State Definitions.

Contains state classes used across all workflow scenarios.
These TypedDict classes define the shape of data flowing through LangGraph nodes.
"""

from typing import TypedDict, List, Optional, Dict, Any


class MultiScenarioState(TypedDict):
    """
    Shared state across all scenario workflows.

    This state is passed through the entire graph and accumulates
    information as it flows through nodes.

    Attributes:
        query: Original user question
        context: Optional context (file, subsystem, etc.)
        intent: Classified intent (e.g., "security_audit")
        scenario_id: Scenario ID (e.g., "scenario_2")
        confidence: Classification confidence (0.0-1.0)
        classification_method: How intent was classified ("keyword" or "llm")
        cpg_results: Results from CPG queries
        subsystems: Relevant subsystems
        methods: Method metadata
        call_graph: NetworkX graph (if needed)
        answer: Natural language answer
        evidence: Supporting evidence (CPG facts)
        metadata: Scenario-specific metadata
        retrieved_functions: List of retrieved function names (for IR metrics)
        error: Error message if any
        retry_count: Number of retries (default: 0)
    """
    # Input
    query: str
    context: Optional[Dict[str, Any]]

    # Intent Classification
    intent: Optional[str]
    scenario_id: Optional[str]
    confidence: Optional[float]
    classification_method: Optional[str]

    # CPG Data (populated by scenario workflows)
    cpg_results: Optional[List[Dict]]
    subsystems: Optional[List[str]]
    methods: Optional[List[Dict]]
    call_graph: Optional[Any]

    # Final Output
    answer: Optional[str]
    evidence: Optional[List[str]]
    metadata: Optional[Dict[str, Any]]
    retrieved_functions: Optional[List[str]]

    # Error Handling
    error: Optional[str]
    retry_count: int


class SecurityWorkflowState(TypedDict):
    """State specific to security analysis workflows."""
    # Inherited from MultiScenarioState
    query: str
    context: Optional[Dict[str, Any]]
    intent: Optional[str]

    # Security-specific
    vulnerabilities: Optional[List[Dict[str, Any]]]
    taint_paths: Optional[List[Dict[str, Any]]]
    security_findings: Optional[List[Dict[str, Any]]]
    risk_score: Optional[float]

    # Output
    answer: Optional[str]
    evidence: Optional[List[str]]
    error: Optional[str]


class PerformanceWorkflowState(TypedDict):
    """State specific to performance analysis workflows."""
    query: str
    context: Optional[Dict[str, Any]]
    intent: Optional[str]

    # Performance-specific
    hotspots: Optional[List[Dict[str, Any]]]
    complexity_metrics: Optional[Dict[str, Any]]
    bottlenecks: Optional[List[Dict[str, Any]]]
    optimization_suggestions: Optional[List[str]]

    # Output
    answer: Optional[str]
    evidence: Optional[List[str]]
    error: Optional[str]


class ArchitectureWorkflowState(TypedDict):
    """State specific to architecture analysis workflows."""
    query: str
    context: Optional[Dict[str, Any]]
    intent: Optional[str]

    # Architecture-specific
    dependencies: Optional[List[Dict[str, Any]]]
    layer_violations: Optional[List[Dict[str, Any]]]
    circular_deps: Optional[List[Dict[str, Any]]]
    subsystem_info: Optional[Dict[str, Any]]

    # Output
    answer: Optional[str]
    evidence: Optional[List[str]]
    error: Optional[str]


def create_initial_state(query: str, context: Optional[Dict[str, Any]] = None) -> MultiScenarioState:
    """
    Create an initial state for workflow execution.

    Args:
        query: User's question
        context: Optional additional context

    Returns:
        Initialized MultiScenarioState
    """
    return MultiScenarioState(
        query=query,
        context=context,
        intent=None,
        scenario_id=None,
        confidence=None,
        classification_method=None,
        cpg_results=None,
        subsystems=None,
        methods=None,
        call_graph=None,
        answer=None,
        evidence=None,
        metadata=None,
        retrieved_functions=None,
        error=None,
        retry_count=0,
    )
