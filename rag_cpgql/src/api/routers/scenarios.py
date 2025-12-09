"""
Scenarios Router.

Provides endpoints for accessing analysis scenarios.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

router = APIRouter()


# Request/Response Models
class ScenarioInfo(BaseModel):
    """Scenario information model."""
    id: str
    name: str
    description: str
    category: str
    keywords: List[str] = Field(default_factory=list)
    example_queries: List[str] = Field(default_factory=list)


class ScenarioQueryRequest(BaseModel):
    """Scenario-specific query request."""
    query: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[str] = None
    language: str = Field(default="en", pattern="^(en|ru)$")


class ScenarioQueryResponse(BaseModel):
    """Scenario query response model."""
    answer: str
    scenario_id: str
    confidence: float
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    session_id: str
    request_id: str
    processing_time_ms: float


# Predefined scenarios from TUI
SCENARIOS: List[ScenarioInfo] = [
    ScenarioInfo(
        id="onboarding",
        name="Onboarding",
        description="Get started with a codebase - find functions, trace call graphs, explain subsystems",
        category="Learning",
        keywords=["find", "where", "what", "how", "explain"],
        example_queries=["Where is the main() function?", "What does exec_simple_query do?"],
    ),
    ScenarioInfo(
        id="security",
        name="Security Audit",
        description="Find security vulnerabilities - SQL injection, buffer overflows, unsafe input handling",
        category="Security",
        keywords=["vulnerability", "injection", "unsafe", "exploit", "cve"],
        example_queries=["Find SQL injection vulnerabilities", "Check for buffer overflows"],
    ),
    ScenarioInfo(
        id="documentation",
        name="Documentation",
        description="Generate documentation for functions, modules, and architecture",
        category="Documentation",
        keywords=["document", "describe", "explain", "architecture"],
        example_queries=["Document the planner module", "Generate API documentation"],
    ),
    ScenarioInfo(
        id="feature_dev",
        name="Feature Development",
        description="Find integration points and extension hooks for new features",
        category="Development",
        keywords=["extend", "hook", "integrate", "add", "implement"],
        example_queries=["Where can I add a new executor node?", "Find extension points"],
    ),
    ScenarioInfo(
        id="refactoring",
        name="Refactoring",
        description="Identify code smells, duplication, and refactoring opportunities",
        category="Quality",
        keywords=["refactor", "duplicate", "smell", "cleanup", "improve"],
        example_queries=["Find duplicate code", "Identify dead code"],
    ),
    ScenarioInfo(
        id="performance",
        name="Performance Analysis",
        description="Find performance bottlenecks, hotspots, and optimization opportunities",
        category="Performance",
        keywords=["slow", "bottleneck", "optimize", "performance", "hotspot"],
        example_queries=["Find performance hotspots", "Identify expensive operations"],
    ),
    ScenarioInfo(
        id="test_coverage",
        name="Test Coverage",
        description="Analyze test coverage and generate test suggestions",
        category="Testing",
        keywords=["test", "coverage", "untested", "mock"],
        example_queries=["Find untested functions", "Suggest tests for module"],
    ),
    ScenarioInfo(
        id="compliance",
        name="Compliance Check",
        description="Check naming conventions, coding standards, and license headers",
        category="Quality",
        keywords=["style", "convention", "standard", "license"],
        example_queries=["Check naming conventions", "Find license violations"],
    ),
    ScenarioInfo(
        id="code_review",
        name="Code Review",
        description="Automated code review with impact analysis and best practices",
        category="Review",
        keywords=["review", "pr", "patch", "change", "diff"],
        example_queries=["Review this patch", "Analyze PR impact"],
    ),
    ScenarioInfo(
        id="cross_repo",
        name="Cross-Repository Analysis",
        description="Analyze dependencies and impacts across multiple repositories",
        category="Architecture",
        keywords=["cross", "repo", "dependency", "impact"],
        example_queries=["Find cross-repo dependencies", "Impact of API change"],
    ),
    ScenarioInfo(
        id="architecture",
        name="Architecture Violations",
        description="Detect circular dependencies and layering violations",
        category="Architecture",
        keywords=["circular", "dependency", "layer", "violation"],
        example_queries=["Find circular dependencies", "Check layer violations"],
    ),
    ScenarioInfo(
        id="tech_debt",
        name="Technical Debt",
        description="Quantify technical debt - TODOs, deprecated functions, complexity",
        category="Quality",
        keywords=["todo", "deprecated", "debt", "complexity"],
        example_queries=["Find TODO comments", "List deprecated functions"],
    ),
    ScenarioInfo(
        id="mass_refactoring",
        name="Mass Refactoring",
        description="Plan and execute large-scale code changes",
        category="Development",
        keywords=["rename", "bulk", "mass", "migration"],
        example_queries=["Rename function across codebase", "Migrate API usage"],
    ),
    ScenarioInfo(
        id="security_incident",
        name="Security Incident Response",
        description="Trace data flow for security incidents and vulnerability analysis",
        category="Security",
        keywords=["incident", "trace", "flow", "breach"],
        example_queries=["Trace data from vulnerability", "Find affected code paths"],
    ),
    ScenarioInfo(
        id="debugging",
        name="Debugging Support",
        description="Find logging points, trace execution paths, identify breakpoints",
        category="Development",
        keywords=["debug", "log", "trace", "breakpoint", "elog"],
        example_queries=["Find elog statements", "Trace execution path"],
    ),
    ScenarioInfo(
        id="entry_points",
        name="Entry Points Analysis",
        description="Find API endpoints, network functions, and attack surface",
        category="Security",
        keywords=["endpoint", "api", "entry", "network", "attack"],
        example_queries=["Find API endpoints", "Analyze attack surface"],
    ),
]

SCENARIOS_MAP = {s.id: s for s in SCENARIOS}


# Endpoints
@router.get(
    "",
    response_model=List[ScenarioInfo],
    summary="List scenarios",
    description="Get list of all available analysis scenarios.",
)
async def list_scenarios() -> List[ScenarioInfo]:
    """
    List all available scenarios.

    Returns:
        List of scenario information
    """
    return SCENARIOS


@router.get(
    "/{scenario_id}",
    response_model=ScenarioInfo,
    summary="Get scenario",
    description="Get information about a specific scenario.",
)
async def get_scenario(scenario_id: str) -> ScenarioInfo:
    """
    Get scenario information.

    Args:
        scenario_id: Scenario ID

    Returns:
        Scenario information
    """
    if scenario_id not in SCENARIOS_MAP:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario_id}' not found",
        )

    return SCENARIOS_MAP[scenario_id]


@router.post(
    "/{scenario_id}/query",
    response_model=ScenarioQueryResponse,
    summary="Query scenario",
    description="Send a query to a specific scenario.",
)
async def query_scenario(
    scenario_id: str,
    request: ScenarioQueryRequest,
    req: Request,
) -> ScenarioQueryResponse:
    """
    Send a query to a specific scenario.

    Args:
        scenario_id: Scenario ID
        request: Query request
        req: FastAPI request

    Returns:
        Scenario query response
    """
    if scenario_id not in SCENARIOS_MAP:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario_id}' not found",
        )

    request_id = getattr(req.state, "request_id", "unknown")

    # TODO: Implement actual scenario processing
    return ScenarioQueryResponse(
        answer=f"Scenario '{scenario_id}' query endpoint is under development.",
        scenario_id=scenario_id,
        confidence=0.0,
        evidence=[],
        session_id=request.session_id or "new_session",
        request_id=request_id,
        processing_time_ms=0.0,
    )
