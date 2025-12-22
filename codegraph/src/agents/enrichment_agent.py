# ============================================================================
# BACKWARD COMPATIBILITY FACADE
# ============================================================================
# This file is kept for backward compatibility.
# All functionality has been moved to src/agents/enrichment/ package.
#
# New code should import directly from the package:
#   from src.agents.enrichment import EnrichmentAgent
# ============================================================================
"""
Enrichment Agent - Maps questions to CPG enrichment tags.

Backward compatibility facade - imports from enrichment package.
"""
from src.agents.enrichment import EnrichmentAgent

__all__ = ['EnrichmentAgent']
