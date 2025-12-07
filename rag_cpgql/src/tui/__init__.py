"""
RAG-CPGQL Terminal User Interface (TUI)

Interactive console for code analysis using Code Property Graphs.
Supports 16 workflow scenarios with dialogue history and configuration management.
"""

from .app import TUIApplication, main

__all__ = ['TUIApplication', 'main']
__version__ = '1.0.0'
