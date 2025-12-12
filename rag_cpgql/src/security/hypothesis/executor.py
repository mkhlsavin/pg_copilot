"""
DuckDB Query Executor for Hypothesis Validation.

Executes SQL/PGQ queries against a CPG database stored in DuckDB.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import SecurityHypothesis, Evidence, ValidationStatus

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result from executing a query."""
    query: str
    success: bool
    row_count: int
    results: List[Dict[str, Any]]
    execution_time_ms: float
    error: Optional[str] = None


class QueryExecutor:
    """Executes queries against DuckDB CPG database.

    Handles connection management, query execution, and result parsing
    for hypothesis validation.
    """

    def __init__(
        self,
        db_path: str,
        read_only: bool = True,
        timeout_seconds: float = 30.0,
    ):
        """Initialize executor.

        Args:
            db_path: Path to DuckDB database file
            read_only: Open in read-only mode (default True for safety)
            timeout_seconds: Query timeout
        """
        self.db_path = db_path
        self.read_only = read_only
        self.timeout_seconds = timeout_seconds
        self._conn = None

    def connect(self) -> None:
        """Open database connection."""
        try:
            import duckdb
            self._conn = duckdb.connect(
                self.db_path,
                read_only=self.read_only,
            )
            logger.info(f"Connected to DuckDB: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to DuckDB: {e}")
            raise

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("Closed DuckDB connection")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def execute_query(self, query: str) -> QueryResult:
        """Execute a single SQL query.

        Args:
            query: SQL query to execute

        Returns:
            QueryResult with results or error
        """
        if not self._conn:
            self.connect()

        start_time = datetime.now()

        try:
            result = self._conn.execute(query)
            df = result.fetchdf()

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            return QueryResult(
                query=query,
                success=True,
                row_count=len(df),
                results=df.to_dict('records'),
                execution_time_ms=execution_time,
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.warning(f"Query failed: {e}")

            return QueryResult(
                query=query,
                success=False,
                row_count=0,
                results=[],
                execution_time_ms=execution_time,
                error=str(e),
            )

    def execute_hypothesis_query(
        self,
        hypothesis: SecurityHypothesis,
    ) -> QueryResult:
        """Execute the query associated with a hypothesis.

        Args:
            hypothesis: Hypothesis with sql_query field populated

        Returns:
            QueryResult
        """
        if not hypothesis.sql_query:
            return QueryResult(
                query="",
                success=False,
                row_count=0,
                results=[],
                execution_time_ms=0,
                error="No SQL query in hypothesis",
            )

        return self.execute_query(hypothesis.sql_query)

    def validate_hypothesis(
        self,
        hypothesis: SecurityHypothesis,
        min_results_for_confirmation: int = 1,
    ) -> SecurityHypothesis:
        """Execute query and update hypothesis with evidence.

        Args:
            hypothesis: Hypothesis to validate
            min_results_for_confirmation: Minimum results needed to confirm

        Returns:
            Updated hypothesis with evidence and status
        """
        result = self.execute_hypothesis_query(hypothesis)

        if not result.success:
            hypothesis.validation_status = ValidationStatus.INCONCLUSIVE
            hypothesis.notes += f"\nQuery error: {result.error}"
            return hypothesis

        # Create evidence from results
        if result.row_count > 0:
            evidence = Evidence(
                id=f"ev-{hypothesis.id[:8]}-{len(hypothesis.evidence)}",
                hypothesis_id=hypothesis.id,
                query_executed=result.query[:500],  # Truncate for storage
                result_count=result.row_count,
                findings=result.results[:100],  # Limit stored results
                confidence=min(0.9, 0.5 + (result.row_count * 0.1)),
                notes=f"Found {result.row_count} potential issues",
            )

            # Add location info from first result
            if result.results:
                first = result.results[0]
                evidence.filename = first.get('filename')
                evidence.line_number = first.get('line_number')
                evidence.code_snippet = first.get('code', '')[:200]

            hypothesis.add_evidence(evidence)

        # Update validation status
        if result.row_count >= min_results_for_confirmation:
            hypothesis.validation_status = ValidationStatus.CONFIRMED
        elif result.row_count == 0:
            hypothesis.validation_status = ValidationStatus.REJECTED
        else:
            hypothesis.validation_status = ValidationStatus.INCONCLUSIVE

        hypothesis.validated_at = datetime.utcnow()

        return hypothesis

    def validate_batch(
        self,
        hypotheses: List[SecurityHypothesis],
        min_results_for_confirmation: int = 1,
    ) -> List[SecurityHypothesis]:
        """Validate a batch of hypotheses.

        Args:
            hypotheses: List of hypotheses to validate
            min_results_for_confirmation: Minimum results needed to confirm

        Returns:
            List of updated hypotheses
        """
        results = []
        for h in hypotheses:
            validated = self.validate_hypothesis(h, min_results_for_confirmation)
            results.append(validated)
            logger.info(
                f"Validated {h.id[:8]}: {h.validation_status.value} "
                f"({len(h.evidence)} evidence items)"
            )
        return results

    def get_table_stats(self) -> Dict[str, int]:
        """Get row counts for CPG tables.

        Returns:
            Dictionary of table_name -> row_count
        """
        tables = [
            "nodes_method", "nodes_call", "nodes_identifier",
            "nodes_literal", "nodes_local", "nodes_param",
            "nodes_control_structure", "nodes_type_decl",
            "edges_ast", "edges_cfg", "edges_call",
            "edges_reaching_def", "edges_ref",
        ]

        stats = {}
        for table in tables:
            try:
                result = self.execute_query(f"SELECT COUNT(*) as cnt FROM {table}")
                if result.success and result.results:
                    stats[table] = result.results[0].get('cnt', 0)
            except Exception:
                stats[table] = 0

        return stats

    def check_database_health(self) -> Dict[str, Any]:
        """Check database health and connectivity.

        Returns:
            Health status dictionary
        """
        health = {
            "connected": False,
            "database_path": self.db_path,
            "database_exists": Path(self.db_path).exists(),
            "tables": {},
            "error": None,
        }

        try:
            self.connect()
            health["connected"] = True
            health["tables"] = self.get_table_stats()
        except Exception as e:
            health["error"] = str(e)
        finally:
            self.close()

        return health
