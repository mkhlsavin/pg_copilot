"""
Feature-to-code mapping toolkit for PostgreSQL 17.

This package implements the end-to-end pipeline described in
``docs/Mapping PostgreSQL 17 Features to Code Graph Nodes.md``.
"""

from .pipeline import FeatureMappingPipeline

__all__ = ["FeatureMappingPipeline"]
