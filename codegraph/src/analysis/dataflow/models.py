"""Data Flow Data Models.

Data structures for data flow analysis.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class DataFlowPath:
    """Represents a data flow path."""
    path_id: str
    variable_name: str
    source_location: Dict[str, Any]  # {method, file, line, type}
    sink_location: Dict[str, Any]    # {method, file, line, type}
    path_length: int
    intermediate_nodes: List[Dict[str, Any]] = field(default_factory=list)
    is_inter_procedural: bool = False  # Crosses function boundaries
    sanitization_points: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class VariableFlow:
    """Tracks flow of a single variable."""
    variable_name: str
    definition_points: List[Dict[str, Any]] = field(default_factory=list)
    use_points: List[Dict[str, Any]] = field(default_factory=list)
    flows: List[DataFlowPath] = field(default_factory=list)
