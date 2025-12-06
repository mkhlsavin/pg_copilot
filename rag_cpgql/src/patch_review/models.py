"""
Data models for Automated Patch-Based Code Review System

This module contains all core data structures used throughout the patch review system:
- Patch representation (PatchContext, FileDiff, HunkChange, ChangedMethod)
- Delta CPG structures (DeltaNode, DeltaEdge, DeltaCPG)
- Impact analysis (BlastRadius, RippleEffect, BreakingChange)
- Verdicts (SecurityVerdict, PerformanceVerdict, ErrorVerdict, ArchitectureVerdict)
- Final review output (ReviewVerdict, Finding, ReviewPolicy)

Phase: Core Infrastructure (Phase 1)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
import uuid


# =============================================================================
# ENUMS
# =============================================================================

class ChangeType(Enum):
    """Type of change in a patch"""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class Severity(Enum):
    """Severity levels for findings"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Recommendation(Enum):
    """Review recommendation types"""
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    BLOCK = "BLOCK"
    COMMENT = "COMMENT"


class FindingCategory(Enum):
    """Categories of review findings"""
    SECURITY = "security"
    PERFORMANCE = "performance"
    ERROR = "error"
    ARCHITECTURE = "architecture"


class ReviewStatus(Enum):
    """Status of a review session"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# PATCH REPRESENTATION
# =============================================================================

@dataclass
class HunkChange:
    """
    Single hunk (change block) within a file diff.

    A hunk represents a contiguous block of changes in a file,
    including context lines before and after.
    """
    old_start: int              # Starting line in original file
    old_lines: int              # Number of lines in original
    new_start: int              # Starting line in new file
    new_lines: int              # Number of lines in new
    context_before: List[str] = field(default_factory=list)
    removed_lines: List[str] = field(default_factory=list)
    added_lines: List[str] = field(default_factory=list)
    context_after: List[str] = field(default_factory=list)

    @property
    def net_change(self) -> int:
        """Net line change (positive = growth, negative = shrink)"""
        return len(self.added_lines) - len(self.removed_lines)


@dataclass
class FileDiff:
    """
    Single file change in a patch.

    Contains all hunks (change blocks) for a single file,
    along with metadata about the change type.
    """
    path: str                   # Current file path
    change_type: ChangeType     # added, modified, deleted, renamed
    hunks: List[HunkChange] = field(default_factory=list)
    language: str = ""          # Detected programming language
    old_path: Optional[str] = None  # For renames: original path

    @property
    def total_additions(self) -> int:
        """Total lines added across all hunks"""
        return sum(len(h.added_lines) for h in self.hunks)

    @property
    def total_deletions(self) -> int:
        """Total lines removed across all hunks"""
        return sum(len(h.removed_lines) for h in self.hunks)


@dataclass
class ChangedMethod:
    """
    Method (function) affected by the patch.

    Represents a method that was added, modified, or deleted.
    Links to CPG node IDs when available for delta analysis.
    """
    method_name: str
    full_name: str              # Fully qualified name
    filepath: str
    change_type: ChangeType
    line_start: int
    line_end: int
    method_id: Optional[int] = None      # CPG node ID (base CPG)
    delta_node_id: Optional[int] = None  # Delta CPG node ID
    old_signature: Optional[str] = None
    new_signature: Optional[str] = None
    complexity_before: Optional[int] = None
    complexity_after: Optional[int] = None


@dataclass
class PatchContext:
    """
    Complete context for a patch under review.

    Contains all information about a patch from any source
    (git diff, GitHub PR, GitLab MR) normalized to a common format.
    """
    patch_id: str
    source: str                 # "git_diff", "github_pr", "gitlab_mr"
    base_commit: str            # Commit hash before changes
    head_commit: str            # Commit hash after changes
    files: List[FileDiff]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Extracted during parsing
    changed_methods: List[ChangedMethod] = field(default_factory=list)

    @property
    def total_files_changed(self) -> int:
        return len(self.files)

    @property
    def total_additions(self) -> int:
        return sum(f.total_additions for f in self.files)

    @property
    def total_deletions(self) -> int:
        return sum(f.total_deletions for f in self.files)

    @property
    def affected_directories(self) -> List[str]:
        """Get unique directories affected by this patch"""
        dirs = set()
        for f in self.files:
            parts = f.path.rsplit('/', 1)
            if len(parts) > 1:
                dirs.add(parts[0])
        return sorted(dirs)


# =============================================================================
# DELTA CPG STRUCTURES
# =============================================================================

@dataclass
class DeltaNode:
    """
    Node in the delta CPG representing a changed element.

    Tracks the change type (added/modified/deleted) and stores
    both old and new values for modified nodes.
    """
    id: int
    session_id: str
    node_type: str              # METHOD, CALL, IDENTIFIER, etc.
    change_type: ChangeType
    name: str
    full_name: str
    filename: str
    line_number: int
    line_number_end: Optional[int] = None
    code: Optional[str] = None
    original_node_id: Optional[int] = None  # Reference to base CPG node
    old_values: Dict[str, Any] = field(default_factory=dict)
    new_values: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeltaEdge:
    """
    Edge in the delta CPG representing a changed relationship.

    Tracks edge additions and deletions between nodes.
    """
    id: int
    session_id: str
    edge_type: str              # AST, CFG, CALL, REACHING_DEF, etc.
    src: int                    # Source node ID
    dst: int                    # Destination node ID
    change_type: ChangeType     # added or deleted
    src_is_delta: bool = False  # True if src is a delta node
    dst_is_delta: bool = False  # True if dst is a delta node
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeltaCPG:
    """
    Complete delta CPG for a patch.

    Contains all changed nodes and edges, providing a virtual
    overlay on the base CPG representing the patch changes.
    """
    session_id: str
    patch_id: str
    nodes: List[DeltaNode] = field(default_factory=list)
    edges: List[DeltaEdge] = field(default_factory=list)
    changed_methods: List[ChangedMethod] = field(default_factory=list)

    # Statistics
    nodes_added: int = 0
    nodes_modified: int = 0
    nodes_deleted: int = 0
    edges_added: int = 0
    edges_deleted: int = 0

    def get_nodes_by_type(self, node_type: str) -> List[DeltaNode]:
        """Get all delta nodes of a specific type"""
        return [n for n in self.nodes if n.node_type == node_type]

    def get_added_methods(self) -> List[DeltaNode]:
        """Get all added method nodes"""
        return [n for n in self.nodes
                if n.node_type == 'METHOD' and n.change_type == ChangeType.ADDED]

    def get_modified_methods(self) -> List[DeltaNode]:
        """Get all modified method nodes"""
        return [n for n in self.nodes
                if n.node_type == 'METHOD' and n.change_type == ChangeType.MODIFIED]


# =============================================================================
# IMPACT ANALYSIS
# =============================================================================

@dataclass
class BlastRadius:
    """
    Impact blast radius for changed methods.

    Represents the "explosion radius" of a change - how many
    other methods are directly or transitively affected.
    """
    changed_methods: List[str]
    direct_callers: List[str]           # Methods directly calling changed methods
    indirect_callers: List[str]         # Transitive callers (depth 2+)
    direct_callees: List[str]           # Methods called by changed methods
    indirect_callees: List[str]         # Transitive callees
    affected_files: List[str]           # Files containing affected methods
    affected_subsystems: List[str]      # Directory/module groupings
    risk_score: float                   # 0.0-1.0 based on impact scope

    @property
    def total_affected(self) -> int:
        """Total unique methods affected"""
        all_methods = set(self.direct_callers + self.indirect_callers +
                         self.direct_callees + self.indirect_callees)
        return len(all_methods)


@dataclass
class RippleEffect:
    """
    Cascading effect of a change through the call graph.

    Uses BFS traversal with diminishing weights per depth level
    to compute how changes propagate.
    """
    source_method: str
    affected_methods: List[Tuple[str, int, float]]  # (method_name, depth, weight)
    max_depth: int
    total_weight: float


@dataclass
class BreakingChange:
    """
    API/signature change that breaks callers.

    Represents changes to method signatures that require
    updates to calling code.
    """
    method_name: str
    breaking_type: str          # "parameter_added", "parameter_removed",
                               # "type_changed", "method_removed"
    old_signature: str
    new_signature: Optional[str]
    affected_callers: List[str]
    severity: Severity


@dataclass
class TaintPathFinding:
    """
    A taint path found during data flow analysis.

    Represents a path from a taint source to a sink,
    potentially indicating a security vulnerability.
    """
    path_id: str
    source_function: str
    source_location: Dict[str, Any]
    sink_function: str
    sink_location: Dict[str, Any]
    path_length: int
    intermediate_nodes: List[Dict[str, Any]]
    sanitization_points: List[Dict[str, Any]]
    max_sanitization_confidence: float
    is_new: bool = True         # True if introduced by this patch


@dataclass
class SanitizationBypass:
    """
    Detected sanitization bypass in the patch.

    Represents a new path that bypasses existing sanitization
    or removed sanitization that was protecting a sink.
    """
    bypass_id: str
    bypass_type: str            # "removed_sanitization", "new_bypass_path"
    affected_sink: str
    original_sanitization: Optional[str]
    details: str
    severity: Severity


# =============================================================================
# FINDINGS
# =============================================================================

@dataclass
class Finding:
    """
    Individual finding from any verdict type.

    Common structure for all types of findings (security, performance,
    error, architecture) to enable unified handling and display.
    """
    category: FindingCategory
    severity: Severity
    title: str
    description: str
    location: str               # File:line format
    recommendation: str
    confidence: float           # 0.0-1.0

    # Optional fields with defaults
    id: str = field(default_factory=lambda: f"FINDING_{uuid.uuid4().hex[:12].upper()}")
    code_snippet: Optional[str] = None

    # Category-specific fields
    cwe_id: Optional[str] = None        # For security findings
    pattern_id: Optional[str] = None    # Pattern that detected this
    estimated_impact: Optional[str] = None  # For performance findings
    test_suggestion: Optional[str] = None   # Suggested test case

    # Metadata
    is_new: bool = True         # True if introduced by this patch
    related_findings: List[str] = field(default_factory=list)


# =============================================================================
# VERDICTS
# =============================================================================

@dataclass
class SecurityVerdict:
    """
    Security analysis verdict for the patch.

    Contains all security-related findings from pattern matching,
    taint analysis, and removed security controls detection.
    """
    findings: List[Finding]
    score: float                # 0-100, higher = more secure
    taint_paths: List[TaintPathFinding] = field(default_factory=list)
    sanitization_bypasses: List[SanitizationBypass] = field(default_factory=list)
    removed_controls: List[Dict[str, Any]] = field(default_factory=list)
    cwe_ids: List[str] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return len([f for f in self.findings if f.severity == Severity.CRITICAL])

    @property
    def high_count(self) -> int:
        return len([f for f in self.findings if f.severity == Severity.HIGH])

    @property
    def medium_count(self) -> int:
        return len([f for f in self.findings if f.severity == Severity.MEDIUM])

    @property
    def low_count(self) -> int:
        return len([f for f in self.findings if f.severity == Severity.LOW])


@dataclass
class ComplexityDelta:
    """
    Complexity change for a method.

    Tracks cyclomatic complexity before and after the patch.
    """
    method_name: str
    complexity_before: int
    complexity_after: int
    delta: int
    risk_level: str             # "low", "moderate", "high", "very_high"


@dataclass
class PerformanceVerdict:
    """
    Performance analysis verdict for the patch.

    Contains findings about performance bottlenecks, complexity
    increases, and impact on known hotspots.
    """
    findings: List[Finding]
    score: float                # 0-100, higher = better performance
    complexity_deltas: List[ComplexityDelta] = field(default_factory=list)
    hotspot_impacts: List[Dict[str, Any]] = field(default_factory=list)
    new_loops: List[Dict[str, Any]] = field(default_factory=list)
    estimated_impact: str = "unknown"  # "negligible", "minor", "moderate", "significant"

    @property
    def total_complexity_increase(self) -> int:
        return sum(d.delta for d in self.complexity_deltas if d.delta > 0)

    @property
    def hot_paths_affected(self) -> int:
        """Number of hot paths affected by this patch."""
        return len(self.hotspot_impacts)

    @property
    def critical_count(self) -> int:
        return len([f for f in self.findings if f.severity == Severity.CRITICAL])

    @property
    def high_count(self) -> int:
        return len([f for f in self.findings if f.severity == Severity.HIGH])

    @property
    def medium_count(self) -> int:
        return len([f for f in self.findings if f.severity == Severity.MEDIUM])

    @property
    def low_count(self) -> int:
        return len([f for f in self.findings if f.severity == Severity.LOW])


@dataclass
class ErrorVerdict:
    """
    Error detection verdict for the patch.

    Contains findings about potential bugs, null safety issues,
    resource leaks, and error handling problems.
    """
    findings: List[Finding]
    score: float                # 0-100, higher = fewer errors
    null_safety_issues: List[Dict[str, Any]] = field(default_factory=list)
    resource_leaks: List[Dict[str, Any]] = field(default_factory=list)
    error_handling_issues: List[Dict[str, Any]] = field(default_factory=list)
    test_suggestions: List[str] = field(default_factory=list)

    @property
    def error_probability(self) -> float:
        """Estimated probability of bugs (0.0-1.0)"""
        if not self.findings:
            return 0.0
        critical_weight = len([f for f in self.findings if f.severity == Severity.CRITICAL]) * 0.4
        high_weight = len([f for f in self.findings if f.severity == Severity.HIGH]) * 0.2
        return min(1.0, critical_weight + high_weight)

    @property
    def critical_count(self) -> int:
        return len([f for f in self.findings if f.severity == Severity.CRITICAL])

    @property
    def high_count(self) -> int:
        return len([f for f in self.findings if f.severity == Severity.HIGH])

    @property
    def medium_count(self) -> int:
        return len([f for f in self.findings if f.severity == Severity.MEDIUM])

    @property
    def low_count(self) -> int:
        return len([f for f in self.findings if f.severity == Severity.LOW])


@dataclass
class ArchitectureVerdict:
    """
    Architecture impact verdict for the patch.

    Contains findings about layer violations, circular dependencies,
    coupling changes, and API compatibility.
    """
    findings: List[Finding]
    score: float                # 0-100, higher = better architecture
    layer_violations: List[Dict[str, Any]] = field(default_factory=list)
    circular_deps: List[Dict[str, Any]] = field(default_factory=list)
    new_imports: List[Dict[str, Any]] = field(default_factory=list)
    coupling_delta: Dict[str, Any] = field(default_factory=dict)
    api_changes: List[BreakingChange] = field(default_factory=list)
    blast_radius_score: float = 100.0  # 0-100, higher = smaller blast radius

    @property
    def circular_dependencies(self) -> int:
        """Number of circular dependencies detected."""
        return len(self.circular_deps)

    @property
    def breaking_changes(self) -> int:
        """Number of breaking API changes detected."""
        return len(self.api_changes)

    @property
    def critical_count(self) -> int:
        return len([f for f in self.findings if f.severity == Severity.CRITICAL])

    @property
    def high_count(self) -> int:
        return len([f for f in self.findings if f.severity == Severity.HIGH])

    @property
    def medium_count(self) -> int:
        return len([f for f in self.findings if f.severity == Severity.MEDIUM])

    @property
    def low_count(self) -> int:
        return len([f for f in self.findings if f.severity == Severity.LOW])


# =============================================================================
# REVIEW POLICY
# =============================================================================

@dataclass
class PolicyRule:
    """
    Custom policy rule for blocking/warning.

    Allows teams to define custom rules beyond default thresholds.
    """
    rule_id: str
    name: str
    condition: str              # Expression to evaluate
    action: str                 # "block", "warn", "comment"
    message: str


@dataclass
class ReviewPolicy:
    """
    Configurable review policy for blocking/approval thresholds.

    Allows teams to customize what causes a patch to be blocked,
    request changes, or be approved.
    """
    # Blocking criteria
    block_on_critical_security: bool = True
    block_on_high_security: bool = False
    block_on_critical_errors: bool = True
    block_on_breaking_changes: bool = False

    # Score thresholds
    min_score_to_approve: float = 70.0
    min_score_to_comment: float = 60.0

    # Limits
    max_critical_findings: int = 0      # 0 = block on any critical
    max_high_findings: int = 5
    max_complexity_increase: int = 20

    # Custom rules
    custom_rules: List[PolicyRule] = field(default_factory=list)

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'ReviewPolicy':
        """Create policy from configuration dictionary"""
        return cls(
            block_on_critical_security=config.get('block_on_critical_security', True),
            block_on_high_security=config.get('block_on_high_security', False),
            block_on_critical_errors=config.get('block_on_critical_errors', True),
            block_on_breaking_changes=config.get('block_on_breaking_changes', False),
            min_score_to_approve=config.get('min_score_to_approve', 70.0),
            min_score_to_comment=config.get('min_score_to_comment', 60.0),
            max_critical_findings=config.get('max_critical_findings', 0),
            max_high_findings=config.get('max_high_findings', 5),
            max_complexity_increase=config.get('max_complexity_increase', 20),
            custom_rules=[
                PolicyRule(**r) for r in config.get('custom_rules', [])
            ]
        )


# =============================================================================
# FINAL REVIEW VERDICT
# =============================================================================

@dataclass
class ReviewVerdict:
    """
    Final aggregated review verdict.

    Combines all sub-verdicts (security, performance, error, architecture)
    into a single verdict with overall score and recommendation.
    """
    # Required fields
    patch_id: str
    overall_score: float
    recommendation: Recommendation
    security: SecurityVerdict
    performance: PerformanceVerdict
    error: ErrorVerdict  # Note: using 'error' to match aggregator
    architecture: ArchitectureVerdict

    # Aggregated findings
    all_findings: List[Finding] = field(default_factory=list)
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    # Impact metrics
    blast_radius_score: float = 100.0
    review_time_seconds: float = 0.0
    summary: str = ""
    reviewed_at: Optional[datetime] = None

    # Optional identification (for persistence)
    review_id: str = field(default_factory=lambda: f"REVIEW_{uuid.uuid4().hex[:12].upper()}")
    session_id: str = ""

    @property
    def total_findings(self) -> int:
        return self.critical_count + self.high_count + self.medium_count + self.low_count

    @property
    def critical_findings(self) -> List[Finding]:
        return [f for f in self.all_findings if f.severity == Severity.CRITICAL]

    @property
    def high_findings(self) -> List[Finding]:
        return [f for f in self.all_findings if f.severity == Severity.HIGH]

    @property
    def medium_findings(self) -> List[Finding]:
        return [f for f in self.all_findings if f.severity == Severity.MEDIUM]

    @property
    def low_findings(self) -> List[Finding]:
        return [f for f in self.all_findings if f.severity == Severity.LOW]

    @property
    def should_block(self) -> bool:
        return self.recommendation == Recommendation.BLOCK


# =============================================================================
# REVIEW SESSION
# =============================================================================

@dataclass
class ReviewSession:
    """
    Review session tracking.

    Manages the lifecycle of a patch review from creation to completion.
    """
    session_id: str
    patch_id: str
    base_commit: str
    head_commit: str
    status: ReviewStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    verdict: Optional[ReviewVerdict] = None
    persist_delta: bool = False         # Whether to keep delta CPG
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, patch: PatchContext) -> 'ReviewSession':
        """Create a new review session for a patch"""
        return cls(
            session_id=f"SESSION_{uuid.uuid4().hex[:12].upper()}",
            patch_id=patch.patch_id,
            base_commit=patch.base_commit,
            head_commit=patch.head_commit,
            status=ReviewStatus.PENDING,
            created_at=datetime.utcnow(),
            metadata=patch.metadata
        )
