"""SQL query executor component for direct database access."""

import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..utils.themes import Theme, DEFAULT_THEME

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = Path("cpg.duckdb")

# Blocked SQL keywords (write operations)
BLOCKED_KEYWORDS = [
    "DROP",
    "DELETE",
    "INSERT",
    "UPDATE",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "REPLACE",
    "GRANT",
    "REVOKE",
    "ATTACH",
    "DETACH",
    "COPY",
]


class QueryExecutor:
    """
    SQL query executor for DuckDB CPG database.

    Provides safe read-only query execution with
    result formatting and validation.
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        theme: Theme = DEFAULT_THEME,
        timeout: float = 30.0,
        max_rows: int = 100,
    ):
        """
        Initialize query executor.

        Args:
            db_path: Path to DuckDB database
            theme: Color theme
            timeout: Query timeout in seconds
            max_rows: Maximum rows to return
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self.theme = theme
        self.timeout = timeout
        self.max_rows = max_rows

    def validate_query(self, query: str) -> Tuple[bool, str]:
        """
        Validate query for safety.

        Args:
            query: SQL query string

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not query or not query.strip():
            return False, "Empty query"

        # Normalize query for checking
        query_upper = query.upper().strip()

        # Check for blocked keywords at start of query or after semicolons
        for keyword in BLOCKED_KEYWORDS:
            # Check at start
            if query_upper.startswith(keyword):
                return False, f"Write operation not allowed: {keyword}"

            # Check after potential statement separator
            if f"; {keyword}" in query_upper or f";{keyword}" in query_upper:
                return False, f"Write operation not allowed: {keyword}"

        # Check for multiple statements (prevent injection)
        # Allow semicolon only at the end
        query_stripped = query.strip().rstrip(";")
        if ";" in query_stripped:
            return False, "Multiple statements not allowed"

        return True, ""

    def execute(self, query: str) -> Tuple[List[Dict[str, Any]], float]:
        """
        Execute SQL query.

        Args:
            query: SQL query string

        Returns:
            Tuple of (results_list, duration_seconds)

        Raises:
            Exception: On database errors
        """
        import duckdb

        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        # Add LIMIT if not present
        query_upper = query.upper().strip()
        if "LIMIT" not in query_upper:
            query = f"{query.rstrip().rstrip(';')} LIMIT {self.max_rows}"

        start_time = time.time()

        # Execute query
        conn = duckdb.connect(str(self.db_path), read_only=True)
        try:
            result = conn.execute(query)
            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()

            # Convert to list of dicts
            results = [dict(zip(columns, row)) for row in rows]

            duration = time.time() - start_time
            return results, duration

        finally:
            conn.close()

    def render_results(
        self,
        results: List[Dict[str, Any]],
        query: str,
        duration: float,
    ) -> Panel:
        """
        Render query results as Rich panel.

        Args:
            results: List of result dictionaries
            query: Original query string
            duration: Execution duration in seconds

        Returns:
            Rich Panel with results table
        """
        # Truncate query for display
        query_display = query[:80] + "..." if len(query) > 80 else query

        # Header
        header = Text()
        header.append("Query: ", style="bold")
        header.append(query_display, style="cyan")
        header.append(f"\nRows: {len(results)}", style="dim")
        header.append(f" | Time: {duration:.3f}s", style="dim")

        if not results:
            return Panel(
                header,
                title="[bold]Query Results[/bold]",
                subtitle="[dim]No rows returned[/dim]",
                border_style=self.theme.border,
            )

        # Build table
        table = Table(
            show_header=True,
            header_style="bold",
            border_style="dim",
            expand=True,
            show_lines=False,
        )

        # Add columns
        columns = list(results[0].keys())
        for col in columns:
            table.add_column(col, overflow="fold")

        # Add rows
        for row in results[:self.max_rows]:
            values = []
            for col in columns:
                val = row[col]
                # Format value for display
                if val is None:
                    values.append("[dim]NULL[/dim]")
                elif isinstance(val, str) and len(val) > 50:
                    values.append(val[:47] + "...")
                else:
                    values.append(str(val))
            table.add_row(*values)

        # Show truncation notice
        subtitle = ""
        if len(results) >= self.max_rows:
            subtitle = f"[yellow]Showing first {self.max_rows} rows[/yellow]"

        from rich.console import Group

        return Panel(
            Group(header, table),
            title="[bold]Query Results[/bold]",
            subtitle=subtitle,
            border_style=self.theme.border,
        )

    def render_error(self, error: Exception, query: str) -> Panel:
        """
        Render error panel.

        Args:
            error: Exception that occurred
            query: Original query string

        Returns:
            Rich Panel with error details
        """
        # Truncate query for display
        query_display = query[:80] + "..." if len(query) > 80 else query

        content = Text()
        content.append("Query: ", style="bold")
        content.append(query_display, style="cyan")
        content.append("\n\n")
        content.append("Error: ", style="bold red")
        content.append(str(error), style="red")

        return Panel(
            content,
            title="[bold red]Query Error[/bold red]",
            border_style="red",
        )

    def get_table_info(self) -> List[str]:
        """
        Get list of available tables.

        Returns:
            List of table names
        """
        try:
            results, _ = self.execute("SHOW TABLES")
            return [row.get("name", "") for row in results]
        except Exception:
            return []

    def describe_table(self, table_name: str) -> Panel:
        """
        Describe a table's schema.

        Args:
            table_name: Table to describe

        Returns:
            Rich Panel with table schema
        """
        # Validate table name (prevent injection)
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
            return Panel(
                f"[red]Invalid table name: {table_name}[/red]",
                title="Error",
                border_style="red",
            )

        try:
            results, duration = self.execute(f"DESCRIBE {table_name}")
            return self.render_results(results, f"DESCRIBE {table_name}", duration)
        except Exception as e:
            return self.render_error(e, f"DESCRIBE {table_name}")

    def render_help(self) -> Panel:
        """
        Render query help.

        Returns:
            Rich Panel with query help
        """
        content = Text()
        content.append("SQL Query Help\n\n", style="bold cyan")

        content.append("Usage:\n", style="bold")
        content.append("  /query SELECT * FROM nodes_method LIMIT 5\n", style="dim")
        content.append("  /query SELECT name FROM nodes_call WHERE name LIKE '%alloc%'\n", style="dim")
        content.append("  /sql DESCRIBE nodes_method\n\n", style="dim")

        content.append("Common Tables:\n", style="bold")
        tables = [
            ("nodes_method", "Function/method definitions"),
            ("nodes_call", "Method invocations"),
            ("nodes_identifier", "Variable references"),
            ("nodes_literal", "Constant values"),
            ("nodes_local", "Local variable declarations"),
            ("edges_ast", "AST parent-child edges"),
            ("edges_cfg", "Control flow edges"),
            ("edges_call", "Call graph edges"),
            ("edges_ref", "Reference edges"),
            ("edges_reaching_def", "Data flow edges"),
        ]

        for name, desc in tables:
            content.append(f"  {name:22}", style="cyan")
            content.append(f" - {desc}\n", style="dim")

        content.append("\nLimitations:\n", style="bold")
        content.append("  - Read-only queries only (SELECT, DESCRIBE, SHOW)\n", style="dim")
        content.append("  - Results limited to 100 rows by default\n", style="dim")
        content.append("  - Single statement queries only\n", style="dim")

        return Panel(
            content,
            title="[bold]/query Help[/bold]",
            border_style=self.theme.border,
        )
