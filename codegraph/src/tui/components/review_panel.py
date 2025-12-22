"""Code review panel component for TUI."""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from ..utils.themes import Theme, DEFAULT_THEME

logger = logging.getLogger(__name__)

# Default config
DEFAULT_DB_PATH = Path("cpg.duckdb")

# Severity icons
SEVERITY_ICONS = {
    "critical": "[red bold]CRIT[/]",
    "high": "[red]HIGH[/]",
    "medium": "[yellow]MED[/]",
    "low": "[green]LOW[/]",
    "info": "[dim]INFO[/]",
}

# Category icons
CATEGORY_ICONS = {
    "security": "[red]SEC[/]",
    "performance": "[yellow]PERF[/]",
    "error": "[magenta]ERR[/]",
    "architecture": "[cyan]ARCH[/]",
}

# Recommendation colors
RECOMMENDATION_STYLES = {
    "APPROVE": "[green bold]APPROVE[/]",
    "COMMENT": "[cyan]COMMENT[/]",
    "REQUEST_CHANGES": "[yellow]REQUEST_CHANGES[/]",
    "BLOCK": "[red bold]BLOCK[/]",
}


class ReviewPanel:
    """
    Code review UI component for TUI.

    Provides:
    - Multi-source input (GitHub PR, GitLab MR, git diff, file, paste)
    - Integration with patch_review workflow
    - Multiple output formats (MD, JSON, YAML, inline)
    """

    def __init__(
        self,
        theme: Theme = DEFAULT_THEME,
        db_path: Optional[Path] = None,
    ):
        """
        Initialize review panel.

        Args:
            theme: Color theme
            db_path: Path to DuckDB CPG database
        """
        self.theme = theme
        self.db_path = db_path or DEFAULT_DB_PATH
        self.github_available = self._check_github()
        self.gitlab_available = self._check_gitlab()

    def _check_github(self) -> bool:
        """Check if GitHub integration is configured."""
        return bool(os.environ.get("GITHUB_TOKEN"))

    def _check_gitlab(self) -> bool:
        """Check if GitLab integration is configured."""
        return bool(os.environ.get("GITLAB_TOKEN"))

    def render_source_menu(self) -> Panel:
        """
        Render input source selection menu.

        Returns:
            Rich Panel with numbered source options
        """
        content = Text()
        content.append("Select input source:\n\n", style="dim")

        # GitHub option
        if self.github_available:
            content.append("[1] ", style="cyan bold")
            content.append("GitHub PR     ", style="bold")
            content.append("- Review pull request\n", style="dim")
        else:
            content.append("[1] ", style="dim")
            content.append("GitHub PR     ", style="dim")
            content.append("- [red]GITHUB_TOKEN not set[/]\n")

        # GitLab option
        if self.gitlab_available:
            content.append("[2] ", style="cyan bold")
            content.append("GitLab MR     ", style="bold")
            content.append("- Review merge request\n", style="dim")
        else:
            content.append("[2] ", style="dim")
            content.append("GitLab MR     ", style="dim")
            content.append("- [red]GITLAB_TOKEN not set[/]\n")

        # Always available options
        content.append("[3] ", style="cyan bold")
        content.append("Git diff      ", style="bold")
        content.append("- Review working directory changes\n", style="dim")

        content.append("[4] ", style="cyan bold")
        content.append("Diff file     ", style="bold")
        content.append("- Load .diff/.patch file\n", style="dim")

        content.append("[5] ", style="cyan bold")
        content.append("Paste diff    ", style="bold")
        content.append("- Enter diff manually\n", style="dim")

        # Status footer
        content.append("\n")
        content.append("Integration Status:\n", style="bold")
        gh_status = "[green]configured[/]" if self.github_available else "[red]not configured[/]"
        gl_status = "[green]configured[/]" if self.gitlab_available else "[red]not configured[/]"
        content.append(f"  GitHub: {gh_status}\n")
        content.append(f"  GitLab: {gl_status}\n")

        return Panel(
            content,
            title="[bold]Code Review[/bold]",
            subtitle="Enter number to select",
            border_style=self.theme.border,
        )

    def render_help(self) -> Panel:
        """
        Render help panel for /review command.

        Returns:
            Rich Panel with usage help
        """
        content = Text()
        content.append("Code Review Command Help\n\n", style="bold cyan")

        content.append("Usage:\n", style="bold")
        content.append("  /review                    ", style="cyan")
        content.append("Show input source menu\n", style="dim")
        content.append("  /review github <PR#>       ", style="cyan")
        content.append("Review GitHub pull request\n", style="dim")
        content.append("  /review gitlab <MR#>       ", style="cyan")
        content.append("Review GitLab merge request\n", style="dim")
        content.append("  /review git                ", style="cyan")
        content.append("Review current git changes\n", style="dim")
        content.append("  /review file <path>        ", style="cyan")
        content.append("Review diff file\n", style="dim")
        content.append("  /review diff               ", style="cyan")
        content.append("Paste diff interactively\n", style="dim")

        content.append("\nOptions:\n", style="bold")
        content.append("  --format <fmt>  ", style="cyan")
        content.append("Output format: md, json, yaml\n", style="dim")
        content.append("  --inline        ", style="cyan")
        content.append("Show inline comments on code lines\n", style="dim")
        content.append("  --help          ", style="cyan")
        content.append("Show this help\n", style="dim")

        content.append("\nExamples:\n", style="bold")
        content.append("  /review github 123 --format json\n", style="dim")
        content.append("  /review git --inline\n", style="dim")
        content.append("  /review file changes.patch\n", style="dim")

        return Panel(
            content,
            title="[bold]/review Help[/bold]",
            border_style=self.theme.border,
        )

    def get_input_by_choice(
        self,
        choice: str,
        console: Console,
    ) -> Optional[Any]:
        """
        Get patch input based on menu choice.

        Args:
            choice: Menu selection (1-5)
            console: Rich console for prompts

        Returns:
            PatchContext or None if cancelled
        """
        if choice == "1":
            if not self.github_available:
                console.print("[red]GitHub not configured. Set GITHUB_TOKEN.[/red]")
                return None
            pr_num = Prompt.ask("Enter PR number")
            return self.get_github_pr(int(pr_num), console)

        elif choice == "2":
            if not self.gitlab_available:
                console.print("[red]GitLab not configured. Set GITLAB_TOKEN.[/red]")
                return None
            mr_iid = Prompt.ask("Enter MR number")
            return self.get_gitlab_mr(int(mr_iid), console)

        elif choice == "3":
            return self.get_git_diff(console)

        elif choice == "4":
            path = Prompt.ask("Enter diff file path")
            return self.get_diff_file(path, console)

        elif choice == "5":
            return self.get_pasted_diff(console)

        else:
            console.print("[red]Invalid choice[/red]")
            return None

    def get_github_pr(
        self,
        pr_number: int,
        console: Console,
    ) -> Optional[Any]:
        """
        Fetch GitHub PR and parse as patch.

        Args:
            pr_number: Pull request number
            console: Rich console

        Returns:
            PatchContext or None
        """
        try:
            from src.patch_review.integrations.github_integration import (
                GitHubIntegration,
                GitHubConfig,
            )
            from src.patch_review.patch_parser import PatchParser

            token = os.environ.get("GITHUB_TOKEN")
            owner = os.environ.get("GITHUB_OWNER", "")
            repo = os.environ.get("GITHUB_REPO", "")

            if not owner or not repo:
                console.print("[yellow]GITHUB_OWNER and GITHUB_REPO not set.[/yellow]")
                owner = Prompt.ask("Repository owner")
                repo = Prompt.ask("Repository name")

            config = GitHubConfig(token=token, owner=owner, repo=repo)
            github = GitHubIntegration(config)

            console.print(f"[dim]Fetching PR #{pr_number}...[/dim]")
            diff = github.fetch_pr_diff(pr_number)

            parser = PatchParser()
            patch = parser.parse("git_diff", diff)
            patch.metadata["source"] = "github_pr"
            patch.metadata["pr_number"] = pr_number
            return patch

        except ImportError as e:
            console.print(f"[red]GitHub integration not available: {e}[/red]")
            return None
        except Exception as e:
            console.print(f"[red]Failed to fetch PR: {e}[/red]")
            return None

    def get_gitlab_mr(
        self,
        mr_iid: int,
        console: Console,
    ) -> Optional[Any]:
        """
        Fetch GitLab MR and parse as patch.

        Args:
            mr_iid: Merge request IID
            console: Rich console

        Returns:
            PatchContext or None
        """
        try:
            from src.patch_review.integrations.gitlab_integration import (
                GitLabIntegration,
                GitLabConfig,
            )
            from src.patch_review.patch_parser import PatchParser

            token = os.environ.get("GITLAB_TOKEN")
            project_id = os.environ.get("GITLAB_PROJECT_ID", "")

            if not project_id:
                console.print("[yellow]GITLAB_PROJECT_ID not set.[/yellow]")
                project_id = Prompt.ask("Project ID or path")

            config = GitLabConfig(token=token, project_id=project_id)
            gitlab = GitLabIntegration(config)

            console.print(f"[dim]Fetching MR !{mr_iid}...[/dim]")
            diff = gitlab.fetch_mr_diff(mr_iid)

            parser = PatchParser()
            patch = parser.parse("git_diff", diff)
            patch.metadata["source"] = "gitlab_mr"
            patch.metadata["mr_iid"] = mr_iid
            return patch

        except ImportError as e:
            console.print(f"[red]GitLab integration not available: {e}[/red]")
            return None
        except Exception as e:
            console.print(f"[red]Failed to fetch MR: {e}[/red]")
            return None

    def get_git_diff(self, console: Console) -> Optional[Any]:
        """
        Get diff from current git working directory.

        Args:
            console: Rich console

        Returns:
            PatchContext or None
        """
        try:
            from src.patch_review.patch_parser import PatchParser

            console.print("[dim]Getting git diff...[/dim]")

            # Try staged changes first, then unstaged
            result = subprocess.run(
                ["git", "diff", "--cached"],
                capture_output=True,
                text=True,
            )
            diff = result.stdout

            if not diff.strip():
                result = subprocess.run(
                    ["git", "diff"],
                    capture_output=True,
                    text=True,
                )
                diff = result.stdout

            if not diff.strip():
                console.print("[yellow]No changes found in working directory.[/yellow]")
                return None

            parser = PatchParser()
            patch = parser.parse("git_diff", diff)
            patch.metadata["source"] = "git_working_dir"
            return patch

        except FileNotFoundError:
            console.print("[red]Git not found. Make sure git is installed.[/red]")
            return None
        except Exception as e:
            console.print(f"[red]Failed to get git diff: {e}[/red]")
            return None

    def get_diff_file(
        self,
        path: str,
        console: Console,
    ) -> Optional[Any]:
        """
        Load diff from file.

        Args:
            path: Path to diff/patch file
            console: Rich console

        Returns:
            PatchContext or None
        """
        try:
            from src.patch_review.patch_parser import PatchParser

            filepath = Path(path)
            if not filepath.exists():
                console.print(f"[red]File not found: {path}[/red]")
                return None

            console.print(f"[dim]Loading {filepath.name}...[/dim]")
            diff = filepath.read_text(encoding="utf-8")

            parser = PatchParser()
            patch = parser.parse("git_diff", diff)
            patch.metadata["source"] = "file"
            patch.metadata["file_path"] = str(filepath)
            return patch

        except Exception as e:
            console.print(f"[red]Failed to load diff file: {e}[/red]")
            return None

    def get_pasted_diff(self, console: Console) -> Optional[Any]:
        """
        Get diff from user paste.

        Args:
            console: Rich console

        Returns:
            PatchContext or None
        """
        try:
            from src.patch_review.patch_parser import PatchParser

            console.print("[cyan]Paste diff content (Ctrl+D or empty line to finish):[/cyan]")
            lines = []
            try:
                while True:
                    line = input()
                    if not line and lines and not lines[-1]:
                        break
                    lines.append(line)
            except EOFError:
                pass

            diff = "\n".join(lines)
            if not diff.strip():
                console.print("[yellow]No diff content provided.[/yellow]")
                return None

            parser = PatchParser()
            patch = parser.parse("git_diff", diff)
            patch.metadata["source"] = "pasted"
            return patch

        except Exception as e:
            console.print(f"[red]Failed to parse pasted diff: {e}[/red]")
            return None

    def run_review(
        self,
        patch: Any,
        console: Console,
    ) -> Optional[Any]:
        """
        Run the review workflow on a patch.

        Args:
            patch: PatchContext to review
            console: Rich console

        Returns:
            ReviewVerdict or None
        """
        try:
            from src.patch_review.workflow.review_workflow import ReviewWorkflow
            from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient

            if not self.db_path.exists():
                console.print(f"[red]CPG database not found: {self.db_path}[/red]")
                console.print("[dim]Run CPG export first to create the database.[/dim]")
                return None

            with DuckDBCPGClient(str(self.db_path)) as client:
                workflow = ReviewWorkflow(client.conn, config={})

                # Run workflow
                result = workflow.run(
                    patch_source="git_diff",
                    patch_data={"diff": patch},
                )

                return result.get("review_verdict")

        except ImportError as e:
            console.print(f"[red]Review workflow not available: {e}[/red]")
            return None
        except Exception as e:
            logger.exception("Review failed")
            console.print(f"[red]Review failed: {e}[/red]")
            return None

    def render_verdict(
        self,
        verdict: Any,
        output_format: str = "md",
        show_inline: bool = False,
    ) -> Panel:
        """
        Render review verdict.

        Args:
            verdict: ReviewVerdict
            output_format: Output format (md, json, yaml)
            show_inline: Whether to show inline comments

        Returns:
            Rich Panel with formatted verdict
        """
        if verdict is None:
            return Panel(
                "[red]No verdict available[/red]",
                title="[bold]Review Results[/bold]",
                border_style="red",
            )

        if output_format == "json":
            return self._render_json(verdict)
        elif output_format == "yaml":
            return self._render_yaml(verdict)
        else:
            return self._render_markdown(verdict, show_inline)

    def _render_markdown(
        self,
        verdict: Any,
        show_inline: bool = False,
    ) -> Panel:
        """Render verdict as markdown."""
        panels = []

        # Score summary
        panels.append(self._render_score_summary(verdict))

        # Category scores
        panels.append(self._render_category_scores(verdict))

        # Findings
        if hasattr(verdict, "all_findings") and verdict.all_findings:
            panels.append(self._render_findings_table(verdict.all_findings))

        # Inline comments
        if show_inline and hasattr(verdict, "all_findings"):
            inline_panel = self._render_inline_comments(verdict.all_findings)
            if inline_panel:
                panels.append(inline_panel)

        return Panel(
            Group(*panels),
            title="[bold]Review Results[/bold]",
            border_style=self.theme.border,
        )

    def _render_score_summary(self, verdict: Any) -> Panel:
        """Render score summary panel."""
        score = getattr(verdict, "overall_score", 0)
        recommendation = getattr(verdict, "recommendation", "COMMENT")

        if hasattr(recommendation, "value"):
            recommendation = recommendation.value

        rec_style = RECOMMENDATION_STYLES.get(recommendation, f"[bold]{recommendation}[/]")

        # Score bar
        filled = int(score / 10)
        empty = 10 - filled
        bar = "[green]" + "=" * filled + "[/][dim]" + "-" * empty + "[/]"

        content = Text()
        content.append(f"Score: {score:.0f}/100  ", style="bold")
        content.append(f"[{bar}]  ")
        content.append(f"Recommendation: {rec_style}\n")

        # Counts
        critical = getattr(verdict, "critical_count", 0)
        high = getattr(verdict, "high_count", 0)
        medium = getattr(verdict, "medium_count", 0)
        low = getattr(verdict, "low_count", 0)

        content.append("\nFindings: ")
        if critical:
            content.append(f"{critical} critical  ", style="red bold")
        if high:
            content.append(f"{high} high  ", style="red")
        if medium:
            content.append(f"{medium} medium  ", style="yellow")
        if low:
            content.append(f"{low} low", style="green")

        return Panel(
            content,
            title="[bold]Summary[/bold]",
            border_style="dim",
        )

    def _render_category_scores(self, verdict: Any) -> Panel:
        """Render category score bars."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Category", width=15)
        table.add_column("Score", width=30)

        categories = [
            ("Security", getattr(verdict, "security_verdict", None)),
            ("Performance", getattr(verdict, "performance_verdict", None)),
            ("Error", getattr(verdict, "error_verdict", None)),
            ("Architecture", getattr(verdict, "architecture_verdict", None)),
        ]

        for name, cat_verdict in categories:
            if cat_verdict:
                score = getattr(cat_verdict, "score", 0)
                filled = int(score / 10)
                empty = 10 - filled
                bar = "[green]" + "=" * filled + "[/][dim]" + "-" * empty + "[/]"
                table.add_row(f"[cyan]{name}[/]", f"[{bar}] {score:.0f}")
            else:
                table.add_row(f"[dim]{name}[/]", "[dim]N/A[/]")

        return Panel(table, title="[bold]Categories[/bold]", border_style="dim")

    def _render_findings_table(self, findings: List[Any]) -> Panel:
        """Render findings as table."""
        table = Table(
            show_header=True,
            header_style="bold",
            border_style="dim",
            expand=True,
        )
        table.add_column("Sev", width=5)
        table.add_column("Cat", width=5)
        table.add_column("Finding", min_width=30)
        table.add_column("Location", width=25)

        # Sort by severity
        severity_order = ["critical", "high", "medium", "low", "info"]
        sorted_findings = sorted(
            findings,
            key=lambda f: severity_order.index(
                getattr(f, "severity", "info").value
                if hasattr(getattr(f, "severity", "info"), "value")
                else "info"
            ),
        )

        for finding in sorted_findings[:20]:  # Limit display
            severity = getattr(finding, "severity", "info")
            if hasattr(severity, "value"):
                severity = severity.value
            category = getattr(finding, "category", "error")
            if hasattr(category, "value"):
                category = category.value

            sev_icon = SEVERITY_ICONS.get(severity, "[dim]?[/]")
            cat_icon = CATEGORY_ICONS.get(category, "[dim]?[/]")
            title = getattr(finding, "title", "Unknown")
            location = getattr(finding, "location", "")

            table.add_row(sev_icon, cat_icon, title, f"[dim]{location}[/]")

        if len(findings) > 20:
            table.add_row("", "", f"[dim]... +{len(findings) - 20} more[/]", "")

        return Panel(table, title="[bold]Findings[/bold]", border_style="dim")

    def _render_inline_comments(self, findings: List[Any]) -> Optional[Panel]:
        """Render findings as inline code comments."""
        # Group findings by file
        by_file: Dict[str, List] = {}
        for finding in findings:
            location = getattr(finding, "location", "")
            if ":" in location:
                file_path = location.split(":")[0]
                if file_path not in by_file:
                    by_file[file_path] = []
                by_file[file_path].append(finding)

        if not by_file:
            return None

        content = Text()
        for file_path, file_findings in list(by_file.items())[:5]:
            content.append(f"\n{file_path}\n", style="cyan bold")
            for finding in file_findings[:3]:
                location = getattr(finding, "location", "")
                line = location.split(":")[-1] if ":" in location else "?"
                severity = getattr(finding, "severity", "info")
                if hasattr(severity, "value"):
                    severity = severity.value
                sev_icon = SEVERITY_ICONS.get(severity, "")
                title = getattr(finding, "title", "")
                desc = getattr(finding, "description", "")[:50]

                content.append(f"  L{line}: ", style="dim")
                content.append(f"{sev_icon} {title}\n")
                if desc:
                    content.append(f"        {desc}...\n", style="dim")

        return Panel(content, title="[bold]Inline Comments[/bold]", border_style="dim")

    def _render_json(self, verdict: Any) -> Panel:
        """Render verdict as JSON."""
        try:
            from src.patch_review.formatters.json_formatter import JSONFormatter

            formatter = JSONFormatter()
            json_str = formatter.format_full(verdict)

            return Panel(
                Syntax(json_str, "json", theme="monokai"),
                title="[bold]Review Results (JSON)[/bold]",
                border_style=self.theme.border,
            )
        except ImportError:
            # Fallback to basic JSON
            data = self._verdict_to_dict(verdict)
            json_str = json.dumps(data, indent=2, default=str)
            return Panel(
                Syntax(json_str, "json", theme="monokai"),
                title="[bold]Review Results (JSON)[/bold]",
                border_style=self.theme.border,
            )

    def _render_yaml(self, verdict: Any) -> Panel:
        """Render verdict as YAML."""
        data = self._verdict_to_dict(verdict)
        yaml_str = yaml.safe_dump(data, default_flow_style=False, sort_keys=False)

        return Panel(
            Syntax(yaml_str, "yaml", theme="monokai"),
            title="[bold]Review Results (YAML)[/bold]",
            border_style=self.theme.border,
        )

    def _verdict_to_dict(self, verdict: Any) -> Dict:
        """Convert verdict to dictionary for serialization."""
        result = {
            "overall_score": getattr(verdict, "overall_score", 0),
            "recommendation": str(getattr(verdict, "recommendation", "COMMENT")),
            "findings_count": {
                "critical": getattr(verdict, "critical_count", 0),
                "high": getattr(verdict, "high_count", 0),
                "medium": getattr(verdict, "medium_count", 0),
                "low": getattr(verdict, "low_count", 0),
            },
            "findings": [],
        }

        if hasattr(verdict, "all_findings"):
            for f in verdict.all_findings[:50]:
                result["findings"].append({
                    "title": getattr(f, "title", ""),
                    "category": str(getattr(f, "category", "")),
                    "severity": str(getattr(f, "severity", "")),
                    "location": getattr(f, "location", ""),
                    "description": getattr(f, "description", ""),
                })

        return result
