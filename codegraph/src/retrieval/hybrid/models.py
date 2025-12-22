"""
Hybrid Retrieval Data Models

Contains dataclasses for retrieval results and configuration.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class RetrievalResult:
    """Unified retrieval result from any source"""
    id: str
    content: str
    score: float
    source: str  # "vector", "graph", or "hybrid"
    metadata: Dict[str, Any] = field(default_factory=dict)
    node_id: Optional[int] = None  # CPG node ID (for deduplication)

    def __hash__(self):
        """Enable set operations for deduplication"""
        return hash(self.id)

    def __eq__(self, other):
        """Equality based on ID"""
        if not isinstance(other, RetrievalResult):
            return False
        return self.id == other.id


@dataclass
class HybridRetrievalConfig:
    """Configuration for hybrid retrieval"""
    vector_weight: float = 0.6  # Weight for vector search results
    graph_weight: float = 0.4   # Weight for graph search results
    vector_top_k: int = 20      # Top-K from vector search
    graph_top_k: int = 20       # Top-K from graph search
    final_top_k: int = 10       # Final results after merging
    min_score_threshold: float = 0.1  # Minimum score to consider
    enable_reranking: bool = False  # LLM-based re-ranking (expensive)

    def __post_init__(self):
        """Validate configuration"""
        total_weight = self.vector_weight + self.graph_weight
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")


__all__ = ['RetrievalResult', 'HybridRetrievalConfig']
