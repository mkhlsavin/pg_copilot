"""Data Models for Refactoring Agents.

Contains dataclasses for code smell findings, impact analysis,
and refactoring tasks.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class CodeSmellFinding:
    """Represents a detected code smell."""
    finding_id: str
    pattern_id: str
    pattern_name: str
    category: str
    severity: str
    method_id: int
    method_name: str
    filename: str
    line_number: int
    code_snippet: str
    description: str
    symptoms: List[str]
    refactoring_technique: str
    effort_hours: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeadCodeFinding:
    """Represents a detected dead code instance."""
    finding_id: str
    pattern_id: str
    pattern_name: str
    detection_type: str  # 'uncalled', 'deprecated', 'disabled', 'orphan', etc.
    severity: str
    method_id: int
    method_name: str
    filename: str
    line_number: int
    line_count: int
    code_snippet: str
    reason: str
    confidence: float  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyInfo:
    """Represents dependency relationships."""
    dependency_id: str
    from_method: str
    from_file: str
    to_method: str
    to_file: str
    dependency_type: str  # "calls", "includes", "data"
    strength: str  # "strong", "medium", "weak"


@dataclass
class ImpactAnalysis:
    """Change impact analysis results."""
    analysis_id: str
    target_method: str
    target_file: str
    direct_dependents: List[str]
    indirect_dependents: List[str]
    affected_files: List[str]
    impact_score: float  # 0.0 to 1.0
    risk_level: str  # "low", "medium", "high"
    estimated_test_effort: float  # hours


@dataclass
class RefactoringTask:
    """A prioritized refactoring task."""
    task_id: str
    finding_id: str
    pattern_name: str
    target_method: str
    target_file: str
    priority: int  # 1-10, higher = more urgent
    effort_hours: float
    impact_score: float
    refactoring_steps: List[str]
    dependencies: List[str]  # Other tasks that should be done first
    estimated_value: float  # Benefit of completing this task


@dataclass
class RefactoringReport:
    """Comprehensive refactoring report."""
    report_id: str
    timestamp: str
    total_smells: int
    by_severity: Dict[str, int]
    by_category: Dict[str, int]
    findings: List[CodeSmellFinding]
    impact_analyses: List[ImpactAnalysis]
    tasks: List[RefactoringTask]
    total_effort_hours: float
    estimated_value: float
    summary: str
    recommendations: List[str]
