"""Base class for call graph analysis modules.

Provides common query execution logic for all analyzers.
"""
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class BaseAnalyzer:
    """Base class with query execution support.

    Provides:
    - Query execution abstraction
    - Support for both execute_query and execute_sql_dict interfaces
    """

    def __init__(self, cpg_service):
        """
        Initialize analyzer with CPG service.

        Args:
            cpg_service: CPGQueryService instance for database access
        """
        self.cpg = cpg_service

        # Support both execute_query and execute_sql_dict interfaces
        if hasattr(cpg_service, 'execute_query'):
            self._execute_base = cpg_service.execute_query
            self._use_inline_params = False
        elif hasattr(cpg_service, 'execute_sql_dict'):
            self._execute_base = cpg_service.execute_sql_dict
            self._use_inline_params = True
        else:
            raise ValueError("CPG service must have execute_query or execute_sql_dict method")

    def _execute(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute query with proper parameter handling for both interfaces."""
        if self._use_inline_params and params:
            # Inline parameters for execute_sql_dict (doesn't support params)
            for p in params:
                if isinstance(p, str):
                    query = query.replace('?', f"'{p}'", 1)
                else:
                    query = query.replace('?', str(p), 1)
            return self._execute_base(query)
        elif params:
            return self._execute_base(query, params)
        else:
            return self._execute_base(query)
