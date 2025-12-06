"""
Definition of Done (DoD) Module for Code Review System

This module handles:
- Extracting DoD from various sources (PR body, Jira, commit message, manual input)
- Generating DoD when not found (using LLM)
- Validating DoD against review findings
- Interactive confirmation workflow

Components:
- DoDExtractor: Multi-source DoD extraction
- DoDGenerator: LLM-based DoD generation
- DoDValidator: Validation against findings
"""

from .dod_extractor import DoDExtractor
from .dod_generator import DoDGenerator
from .dod_validator import DoDValidator

__all__ = [
    'DoDExtractor',
    'DoDGenerator',
    'DoDValidator',
]
