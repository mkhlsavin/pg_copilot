"""
Repository Analysis Patterns - Scenario 10: Cross-Repository Analysis

Defines patterns and data structures for multi-repository analysis:
- Repository metadata and indexing
- Code duplication detection
- Cross-repo dependencies
- Consolidation opportunities

Author: Cross-Repository Analysis Team
Date: 2025-11-23
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


# ============================================================================
# ENUMS
# ============================================================================

class DuplicationSeverity(Enum):
    """Severity of code duplication"""
    CRITICAL = "critical"  # >90% similarity, 100+ lines
    HIGH = "high"          # >80% similarity, 50+ lines
    MEDIUM = "medium"      # >70% similarity, 20+ lines
    LOW = "low"            # >60% similarity, 10+ lines
    INFO = "info"          # <60% similarity


class DependencyType(Enum):
    """Type of cross-repository dependency"""
    API_CALL = "api_call"              # HTTP/RPC calls
    IMPORT = "import"                  # Code imports
    DATABASE = "database"              # Shared database
    MESSAGE_QUEUE = "message_queue"    # Pub/sub messaging
    CONFIG_REF = "config_reference"    # Shared configuration
    SHARED_LIB = "shared_library"      # Common library


class RiskLevel(Enum):
    """Risk level for dependencies"""
    CRITICAL = "critical"  # High coupling, single point of failure
    HIGH = "high"          # Significant coupling
    MEDIUM = "medium"      # Moderate coupling
    LOW = "low"            # Minimal coupling
    INFO = "info"          # Informational


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class RepositoryInfo:
    """
    Metadata about a repository.

    Attributes:
        repo_id: Unique identifier (e.g., "repo-001")
        name: Repository name
        path: File system path
        language: Primary programming language
        file_count: Number of files
        method_count: Number of methods/functions
        line_count: Total lines of code
        primary_subsystems: Top-level directories/modules
        cpg_indexed: Whether CPG has been generated
    """
    repo_id: str
    name: str
    path: str
    language: str
    file_count: int = 0
    method_count: int = 0
    line_count: int = 0
    primary_subsystems: List[str] = field(default_factory=list)
    cpg_indexed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeInstance:
    """
    A specific instance of code (for duplication detection).

    Attributes:
        repo_id: Repository identifier
        file_path: File path within repository
        method_name: Method/function name
        start_line: Starting line number
        end_line: Ending line number
        code_snippet: Code content
        signature: Method signature
    """
    repo_id: str
    file_path: str
    method_name: str
    start_line: int
    end_line: int
    code_snippet: str
    signature: str


@dataclass
class CodeDuplication:
    """
    Detected code duplication across repositories.

    Attributes:
        pattern_id: Unique identifier
        pattern_name: Human-readable name
        similarity_score: Similarity percentage (0-100)
        severity: Duplication severity
        instances: List of duplicate code instances
        recommendation: How to consolidate
        estimated_consolidation_effort: Hours to consolidate
        potential_savings: Lines of code that could be eliminated
    """
    pattern_id: str
    pattern_name: str
    similarity_score: float
    severity: DuplicationSeverity
    instances: List[CodeInstance]
    recommendation: str
    estimated_consolidation_effort: float
    potential_savings: int


@dataclass
class DependencyCall:
    """
    A specific dependency call between repositories.

    Attributes:
        source_method: Calling method
        source_file: Calling file
        target_endpoint: Target API/function
        call_count: Number of calls (if known)
        call_code: Code snippet of the call
    """
    source_method: str
    source_file: str
    target_endpoint: str
    call_count: int = 1
    call_code: str = ""


@dataclass
class CrossRepoDependency:
    """
    Dependency relationship between two repositories.

    Attributes:
        dependency_id: Unique identifier
        source_repo: Source repository ID
        target_repo: Target repository ID
        dependency_type: Type of dependency
        coupling_score: Coupling strength (0-100)
        risk_level: Risk assessment
        calls: List of specific dependency calls
        mitigation: How to reduce coupling
    """
    dependency_id: str
    source_repo: str
    target_repo: str
    dependency_type: DependencyType
    coupling_score: float
    risk_level: RiskLevel
    calls: List[DependencyCall]
    mitigation: str


@dataclass
class ConsolidationOpportunity:
    """
    An opportunity to consolidate code across repositories.

    Attributes:
        opportunity_id: Unique identifier
        title: Brief description
        affected_repos: List of repository IDs
        duplication_count: Number of duplicated instances
        estimated_effort: Hours to implement
        estimated_savings: Lines of code saved
        priority: 1-5 (1=highest)
        action_plan: Steps to consolidate
    """
    opportunity_id: str
    title: str
    affected_repos: List[str]
    duplication_count: int
    estimated_effort: float
    estimated_savings: int
    priority: int
    action_plan: str


@dataclass
class ConsolidationReport:
    """
    Complete cross-repository analysis report.

    Attributes:
        total_repos: Number of repositories analyzed
        total_methods: Total methods across all repos
        duplications: Detected code duplications
        dependencies: Cross-repo dependencies
        opportunities: Consolidation opportunities
        dependency_graph: Repository dependency map
        estimated_total_savings: Total LOC that could be eliminated
        risk_summary: Summary of high-risk dependencies
    """
    total_repos: int
    total_methods: int
    duplications: List[CodeDuplication]
    dependencies: List[CrossRepoDependency]
    opportunities: List[ConsolidationOpportunity]
    dependency_graph: Dict[str, List[str]]
    estimated_total_savings: int
    risk_summary: Dict[str, int]


# ============================================================================
# DUPLICATION DETECTION PATTERNS
# ============================================================================

DUPLICATION_PATTERNS = {
    "EXACT_MATCH": {
        "name": "Exact Code Duplication",
        "description": "Identical code across repositories",
        "similarity_threshold": 100.0,
        "min_lines": 10,
        "severity": DuplicationSeverity.CRITICAL,
    },

    "HIGH_SIMILARITY": {
        "name": "High Similarity Code",
        "description": "Very similar code with minor variations",
        "similarity_threshold": 80.0,
        "min_lines": 20,
        "severity": DuplicationSeverity.HIGH,
    },

    "SIMILAR_LOGIC": {
        "name": "Similar Business Logic",
        "description": "Similar algorithms/logic with different implementations",
        "similarity_threshold": 70.0,
        "min_lines": 30,
        "severity": DuplicationSeverity.MEDIUM,
    },

    "UTILITY_DUPLICATION": {
        "name": "Duplicated Utility Functions",
        "description": "Common utilities reimplemented in each repo",
        "similarity_threshold": 75.0,
        "min_lines": 5,
        "severity": DuplicationSeverity.MEDIUM,
    },
}


# ============================================================================
# DEPENDENCY PATTERNS
# ============================================================================

DEPENDENCY_PATTERNS = {
    "HTTP_API": {
        "type": DependencyType.API_CALL,
        "detection_keywords": ["requests.get", "requests.post", "http.client", "urllib", "fetch("],
        "risk_threshold": 50.0,
        "description": "HTTP API calls between services",
    },

    "RPC_CALL": {
        "type": DependencyType.API_CALL,
        "detection_keywords": ["grpc", "thrift", "xmlrpc"],
        "risk_threshold": 60.0,
        "description": "RPC calls between services",
    },

    "IMPORT_DEPENDENCY": {
        "type": DependencyType.IMPORT,
        "detection_keywords": ["import", "require", "include"],
        "risk_threshold": 70.0,
        "description": "Direct code imports",
    },

    "DATABASE_SHARING": {
        "type": DependencyType.DATABASE,
        "detection_keywords": ["db.connect", "database", "sql.connect"],
        "risk_threshold": 80.0,
        "description": "Shared database access",
    },

    "MESSAGE_QUEUE": {
        "type": DependencyType.MESSAGE_QUEUE,
        "detection_keywords": ["kafka", "rabbitmq", "pubsub", "queue"],
        "risk_threshold": 40.0,
        "description": "Message queue communication",
    },
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_similarity(code1: str, code2: str) -> float:
    """
    Calculate similarity between two code snippets.

    Uses simple token-based similarity (real implementation would use AST).
    Returns similarity score 0-100.
    """
    # Normalize whitespace
    tokens1 = set(code1.split())
    tokens2 = set(code2.split())

    if not tokens1 or not tokens2:
        return 0.0

    # Jaccard similarity
    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)

    return (intersection / union) * 100.0


def classify_duplication_severity(similarity: float, line_count: int) -> DuplicationSeverity:
    """Classify duplication severity based on similarity and size"""
    if similarity >= 90 and line_count >= 100:
        return DuplicationSeverity.CRITICAL
    elif similarity >= 80 and line_count >= 50:
        return DuplicationSeverity.HIGH
    elif similarity >= 70 and line_count >= 20:
        return DuplicationSeverity.MEDIUM
    elif similarity >= 60 and line_count >= 10:
        return DuplicationSeverity.LOW
    else:
        return DuplicationSeverity.INFO


def calculate_coupling_score(call_count: int, repo_pair_methods: int) -> float:
    """
    Calculate coupling score between two repositories.

    Args:
        call_count: Number of calls from source to target
        repo_pair_methods: Total methods in both repos

    Returns:
        Coupling score 0-100 (higher = more coupled)
    """
    if repo_pair_methods == 0:
        return 0.0

    # Normalize by total methods, scale to 0-100
    raw_score = (call_count / repo_pair_methods) * 1000
    return min(raw_score, 100.0)


def classify_risk_level(coupling_score: float, dependency_type: DependencyType) -> RiskLevel:
    """Classify dependency risk level"""
    # Database sharing is inherently risky
    if dependency_type == DependencyType.DATABASE:
        return RiskLevel.CRITICAL if coupling_score > 30 else RiskLevel.HIGH

    # Direct imports create tight coupling
    if dependency_type == DependencyType.IMPORT:
        return RiskLevel.HIGH if coupling_score > 50 else RiskLevel.MEDIUM

    # API calls are more flexible
    if dependency_type == DependencyType.API_CALL:
        if coupling_score > 70:
            return RiskLevel.HIGH
        elif coupling_score > 40:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    # Message queues are loosely coupled
    if dependency_type == DependencyType.MESSAGE_QUEUE:
        return RiskLevel.LOW if coupling_score < 60 else RiskLevel.MEDIUM

    return RiskLevel.INFO
