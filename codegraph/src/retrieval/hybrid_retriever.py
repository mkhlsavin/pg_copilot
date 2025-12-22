# ============================================================================
# BACKWARD COMPATIBILITY FACADE
# ============================================================================
# This file is kept for backward compatibility.
# All functionality has been moved to src/retrieval/hybrid/ package.
#
# New code should import directly from the package:
#   from src.retrieval.hybrid import HybridRetriever, SpecializedRetriever
# ============================================================================
"""
Hybrid Retriever - Phase 1 Implementation

Backward compatibility facade - imports from hybrid package.
"""
from src.retrieval.hybrid import (
    # Data models
    RetrievalResult,
    HybridRetrievalConfig,
    # Main retriever
    HybridRetriever,
    # Specialized retrievers
    SpecializedRetriever,
    create_specialized_retriever,
    SubsystemMapper,
    create_subsystem_mapper,
    # Domain plugin
    get_subsystems,
    # Convenience functions
    hybrid_search_methods,
    semantic_search,
    structural_search,
)

# Re-export internal function for backward compatibility
from src.retrieval.hybrid.domain_plugin import _get_subsystems_from_domain_plugin

__all__ = [
    'RetrievalResult',
    'HybridRetrievalConfig',
    'HybridRetriever',
    'SpecializedRetriever',
    'create_specialized_retriever',
    'SubsystemMapper',
    'create_subsystem_mapper',
    'get_subsystems',
    '_get_subsystems_from_domain_plugin',
    'hybrid_search_methods',
    'semantic_search',
    'structural_search',
]
