"""Streaming Progress Tracker for LangGraph Workflow

This module provides real-time progress visualization using Rich console
for the RAG-CPGQL LangGraph workflow. It supports:

1. Live progress bars for each agent
2. Colorized status indicators
3. Real-time metrics display
4. Spinner animations during operations
5. TTY-friendly output with fallback for non-TTY environments

Usage:
    tracker = ProgressTracker(enabled=True)
    tracker.start_agent("analyzer")
    # ... agent work ...
    tracker.complete_agent("analyzer", {"domain": "memory", "intent": "find-function"})
"""

import sys
import time
from typing import Optional, Dict, Any
from contextlib import contextmanager

try:
    from rich.console import Console
    from rich.live import Live
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
    from rich.panel import Panel
    from rich.text import Text
    from rich.layout import Layout
    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False


class ProgressTracker:
    """
    Real-time progress tracker for LangGraph workflow.

    Provides visual feedback for each agent's execution with:
    - Agent status (pending/running/completed/failed)
    - Execution time tracking
    - Key metrics display
    - Live console updates
    """

    AGENT_NAMES = [
        "analyzer",
        "retriever",
        "enrichment",
        "generator",
        "validator",
        "refiner",
        "executor",
        "interpreter",
        "evaluator"
    ]

    AGENT_EMOJI = {
        "analyzer": "🔍",
        "retriever": "📚",
        "enrichment": "🏷️",
        "generator": "⚡",
        "validator": "✓",
        "refiner": "🔧",
        "executor": "▶️",
        "interpreter": "💬",
        "evaluator": "📊"
    }

    def __init__(self, enabled: bool = True, use_rich: bool = True):
        """
        Initialize progress tracker.

        Args:
            enabled: Whether to show progress output
            use_rich: Whether to use Rich library (falls back to simple print if False or unavailable)
        """
        self.enabled = enabled
        self.use_rich = use_rich and _RICH_AVAILABLE and sys.stdout.isatty()

        # State tracking
        self.agent_status: Dict[str, str] = {agent: "pending" for agent in self.AGENT_NAMES}
        self.agent_times: Dict[str, float] = {}
        self.agent_start_times: Dict[str, float] = {}
        self.agent_metrics: Dict[str, Dict[str, Any]] = {}
        self.current_agent: Optional[str] = None
        self.workflow_start_time: Optional[float] = None

        # Rich components
        if self.use_rich:
            self.console = Console()
            self.live: Optional[Live] = None
            self.progress: Optional[Progress] = None
            self.task_ids: Dict[str, TaskID] = {}
        else:
            self.console = None
            self.live = None
            self.progress = None
            self.task_ids = {}

    def start_workflow(self, question: str):
        """Start tracking a new workflow execution."""
        if not self.enabled:
            return

        self.workflow_start_time = time.time()
        self.agent_status = {agent: "pending" for agent in self.AGENT_NAMES}
        self.agent_times = {}
        self.agent_start_times = {}
        self.agent_metrics = {}
        self.current_agent = None

        if self.use_rich:
            self.console.print("\n" + "="*80)
            self.console.print(Panel.fit(
                f"[bold cyan]RAG-CPGQL LangGraph Workflow[/bold cyan]\n\n"
                f"[yellow]Question:[/yellow] {question}",
                border_style="cyan"
            ))
            self.console.print()
        else:
            print("\n" + "="*80)
            print(f"RAG-CPGQL LangGraph Workflow")
            print(f"Question: {question}")
            print("="*80 + "\n")

    def start_agent(self, agent_name: str):
        """Mark an agent as started."""
        if not self.enabled:
            return

        self.current_agent = agent_name
        self.agent_status[agent_name] = "running"
        self.agent_start_times[agent_name] = time.time()

        if self.use_rich:
            emoji = self.AGENT_EMOJI.get(agent_name, "▶")
            self.console.print(f"{emoji} [bold blue]{agent_name.upper()}[/bold blue] [dim]starting...[/dim]")
        else:
            print(f"▶ {agent_name.upper()} starting...")

    def update_agent(self, agent_name: str, status: str):
        """Update agent status during execution."""
        if not self.enabled:
            return

        if self.use_rich:
            emoji = self.AGENT_EMOJI.get(agent_name, "▶")
            self.console.print(f"  {emoji} [dim]{status}[/dim]")
        else:
            print(f"  ▶ {status}")

    def complete_agent(self, agent_name: str, metrics: Optional[Dict[str, Any]] = None):
        """Mark an agent as completed with optional metrics."""
        if not self.enabled:
            return

        self.agent_status[agent_name] = "completed"

        if agent_name in self.agent_start_times:
            elapsed = time.time() - self.agent_start_times[agent_name]
            self.agent_times[agent_name] = elapsed
        else:
            elapsed = 0.0

        if metrics:
            self.agent_metrics[agent_name] = metrics

        if self.use_rich:
            emoji = self.AGENT_EMOJI.get(agent_name, "✓")
            metrics_str = self._format_metrics(metrics) if metrics else ""
            self.console.print(
                f"{emoji} [bold green]{agent_name.upper()}[/bold green] "
                f"[dim]completed in {elapsed:.2f}s[/dim] {metrics_str}"
            )
        else:
            metrics_str = self._format_metrics_plain(metrics) if metrics else ""
            print(f"✓ {agent_name.upper()} completed in {elapsed:.2f}s {metrics_str}")

    def fail_agent(self, agent_name: str, error: str):
        """Mark an agent as failed."""
        if not self.enabled:
            return

        self.agent_status[agent_name] = "failed"

        if agent_name in self.agent_start_times:
            elapsed = time.time() - self.agent_start_times[agent_name]
            self.agent_times[agent_name] = elapsed

        if self.use_rich:
            emoji = self.AGENT_EMOJI.get(agent_name, "✗")
            self.console.print(
                f"{emoji} [bold red]{agent_name.upper()}[/bold red] "
                f"[red]failed:[/red] {error}"
            )
        else:
            print(f"✗ {agent_name.upper()} failed: {error}")

    def complete_workflow(self, final_state: Dict[str, Any]):
        """Complete workflow and show final summary."""
        if not self.enabled:
            return

        if self.workflow_start_time:
            total_time = time.time() - self.workflow_start_time
        else:
            total_time = 0.0

        if self.use_rich:
            self._print_rich_summary(final_state, total_time)
        else:
            self._print_plain_summary(final_state, total_time)

    def _format_metrics(self, metrics: Optional[Dict[str, Any]]) -> str:
        """Format metrics for Rich console."""
        if not metrics:
            return ""

        parts = []
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                if isinstance(value, float) and 0 <= value <= 1:
                    parts.append(f"[cyan]{key}[/cyan]={value:.2f}")
                else:
                    parts.append(f"[cyan]{key}[/cyan]={value}")
            else:
                parts.append(f"[cyan]{key}[/cyan]={value}")

        return "[dim]│[/dim] " + " [dim]│[/dim] ".join(parts) if parts else ""

    def _format_metrics_plain(self, metrics: Optional[Dict[str, Any]]) -> str:
        """Format metrics for plain text output."""
        if not metrics:
            return ""

        parts = []
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                if isinstance(value, float) and 0 <= value <= 1:
                    parts.append(f"{key}={value:.2f}")
                else:
                    parts.append(f"{key}={value}")
            else:
                parts.append(f"{key}={value}")

        return "| " + " | ".join(parts) if parts else ""

    def _print_rich_summary(self, final_state: Dict[str, Any], total_time: float):
        """Print Rich-formatted summary."""
        self.console.print("\n" + "="*80)

        # Create summary table
        table = Table(show_header=True, header_style="bold magenta", border_style="blue")
        table.add_column("Agent", style="cyan", width=15)
        table.add_column("Status", width=12)
        table.add_column("Time", justify="right", width=10)
        table.add_column("Key Metrics", style="dim")

        for agent in self.AGENT_NAMES:
            status = self.agent_status.get(agent, "pending")
            elapsed = self.agent_times.get(agent, 0.0)
            metrics = self.agent_metrics.get(agent, {})

            # Status with color
            if status == "completed":
                status_text = Text("✓ Completed", style="green")
            elif status == "running":
                status_text = Text("▶ Running", style="blue")
            elif status == "failed":
                status_text = Text("✗ Failed", style="red")
            else:
                status_text = Text("○ Pending", style="dim")

            # Format metrics
            metrics_str = ", ".join(f"{k}={v}" for k, v in list(metrics.items())[:3])

            table.add_row(
                f"{self.AGENT_EMOJI.get(agent, '▶')} {agent.capitalize()}",
                status_text,
                f"{elapsed:.2f}s" if elapsed > 0 else "-",
                metrics_str
            )

        self.console.print(table)

        # Final results
        self.console.print("\n[bold]Final Results:[/bold]")
        self.console.print(f"  [cyan]Query Valid:[/cyan] {final_state.get('query_valid', False)}")
        self.console.print(f"  [cyan]Execution:[/cyan] {'SUCCESS' if final_state.get('execution_success') else 'FAILED'}")
        self.console.print(f"  [cyan]RAGAS Score:[/cyan] {final_state.get('overall_score', 0.0):.3f}")
        self.console.print(f"  [cyan]Total Time:[/cyan] {total_time:.2f}s")

        if final_state.get('cpgql_query'):
            query_preview = str(final_state['cpgql_query'])[:100]
            self.console.print(f"\n[bold]Generated Query:[/bold]\n  {query_preview}...")

        self.console.print("\n" + "="*80 + "\n")

    def _print_plain_summary(self, final_state: Dict[str, Any], total_time: float):
        """Print plain text summary."""
        print("\n" + "="*80)
        print("WORKFLOW SUMMARY")
        print("="*80)

        for agent in self.AGENT_NAMES:
            status = self.agent_status.get(agent, "pending")
            elapsed = self.agent_times.get(agent, 0.0)

            status_symbol = {
                "completed": "✓",
                "running": "▶",
                "failed": "✗",
                "pending": "○"
            }.get(status, "?")

            print(f"{status_symbol} {agent.capitalize():15} | {status:10} | {elapsed:6.2f}s")

        print("\n" + "-"*80)
        print(f"Query Valid:      {final_state.get('query_valid', False)}")
        print(f"Execution:        {'SUCCESS' if final_state.get('execution_success') else 'FAILED'}")
        print(f"RAGAS Score:      {final_state.get('overall_score', 0.0):.3f}")
        print(f"Total Time:       {total_time:.2f}s")
        print("="*80 + "\n")

    @contextmanager
    def agent_context(self, agent_name: str):
        """
        Context manager for agent execution tracking.

        Usage:
            with tracker.agent_context("analyzer"):
                # agent work here
                pass
        """
        try:
            self.start_agent(agent_name)
            yield self
        except Exception as e:
            self.fail_agent(agent_name, str(e))
            raise
        else:
            self.complete_agent(agent_name)


# Global singleton tracker (can be replaced with dependency injection if needed)
_global_tracker: Optional[ProgressTracker] = None


def get_tracker(enabled: bool = True, use_rich: bool = True) -> ProgressTracker:
    """Get or create global progress tracker."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = ProgressTracker(enabled=enabled, use_rich=use_rich)
    return _global_tracker


def set_tracker(tracker: Optional[ProgressTracker]):
    """Set global progress tracker."""
    global _global_tracker
    _global_tracker = tracker


def reset_tracker():
    """Reset global tracker."""
    global _global_tracker
    _global_tracker = None
