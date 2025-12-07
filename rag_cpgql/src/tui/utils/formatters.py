"""Output formatters for TUI display."""

from typing import Any, Dict, List, Optional
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.text import Text

from .themes import Theme, DEFAULT_THEME


def format_result(
    result: Dict[str, Any],
    theme: Theme = DEFAULT_THEME
) -> Panel:
    """
    Format a workflow result for display.

    Args:
        result: Workflow result dictionary
        theme: Color theme

    Returns:
        Rich Panel with formatted result
    """
    answer = result.get('answer', 'No answer available')
    scenario_id = result.get('scenario_id', 'unknown')
    confidence = result.get('confidence', 0.0)
    evidence = result.get('evidence', [])

    # Build content
    content = Text()
    content.append(answer + "\n\n", style=theme.assistant_message)

    # Add evidence if available
    if evidence:
        content.append("Evidence:\n", style="bold")
        for i, item in enumerate(evidence[:5], 1):
            content.append(f"  {i}. ", style="dim")
            content.append(f"{item}\n", style=theme.file_path)

    # Add metadata
    content.append(f"\n[Scenario: {scenario_id}]", style="dim")
    content.append(f" [Confidence: {confidence:.0%}]", style="dim")

    return Panel(
        content,
        title="[bold]Answer[/bold]",
        border_style=theme.border,
    )


def format_error(
    error: Exception,
    context: Optional[str] = None,
    theme: Theme = DEFAULT_THEME
) -> Panel:
    """
    Format an error for display.

    Args:
        error: Exception that occurred
        context: Optional context message
        theme: Color theme

    Returns:
        Rich Panel with formatted error
    """
    content = Text()

    if context:
        content.append(f"{context}\n\n", style="dim")

    content.append(str(error), style=theme.error_message)

    return Panel(
        content,
        title="[bold red]Error[/bold red]",
        border_style="red",
    )


def format_sql_query(
    query: str,
    rows_affected: Optional[int] = None,
    theme: Theme = DEFAULT_THEME
) -> Panel:
    """Format SQL query for display."""
    syntax = Syntax(query, "sql", theme="monokai", line_numbers=False)

    title = "SQL Query"
    if rows_affected is not None:
        title += f" ({rows_affected} rows)"

    return Panel(
        syntax,
        title=f"[bold]{title}[/bold]",
        border_style=theme.sql_query,
    )


def format_function_list(
    functions: List[Dict[str, Any]],
    theme: Theme = DEFAULT_THEME
) -> Table:
    """Format a list of functions as a table."""
    table = Table(title="Functions Found", border_style=theme.border)

    table.add_column("Name", style=theme.function_name)
    table.add_column("File", style=theme.file_path)
    table.add_column("Line", justify="right")

    for func in functions[:20]:  # Limit to 20
        table.add_row(
            func.get('name', 'unknown'),
            func.get('file', 'unknown'),
            str(func.get('line', '-')),
        )

    if len(functions) > 20:
        table.add_row("...", f"(+{len(functions) - 20} more)", "")

    return table


def format_scenario_result(
    scenario_id: str,
    status: str,
    details: Dict[str, Any],
    theme: Theme = DEFAULT_THEME
) -> Panel:
    """Format a scenario execution result."""
    content = Text()

    # Status indicator
    if status == "success":
        content.append("SUCCESS", style=theme.success_message)
    elif status == "partial":
        content.append("PARTIAL", style=theme.warning_message)
    else:
        content.append("FAILED", style=theme.error_message)

    content.append(f" - Scenario: {scenario_id}\n\n")

    # Details
    for key, value in details.items():
        content.append(f"{key}: ", style="bold")
        content.append(f"{value}\n")

    return Panel(
        content,
        title=f"[bold]Scenario Result[/bold]",
        border_style=theme.border,
    )
