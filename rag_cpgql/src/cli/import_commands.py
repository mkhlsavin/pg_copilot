"""
CLI Commands for Project Import.

Usage:
    python -m src.cli.import_commands full --repo https://github.com/org/repo
    python -m src.cli.import_commands clone --repo https://github.com/org/repo
    python -m src.cli.import_commands cpg --path ./workspace/repo
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
    )
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from src.project_import.models import (
    ImportMode,
    ProjectImportRequest,
    SupportedLanguage,
)
from src.project_import.pipeline import ProjectImportPipeline
from src.project_import.steps import JOERN_FRONTENDS

logger = logging.getLogger(__name__)

if RICH_AVAILABLE:
    console = Console()
else:
    console = None


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        prog="import-project",
        description="Import new codebase into RAG-CPGQL system",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Full pipeline command
    full_parser = subparsers.add_parser("full", help="Run full import pipeline")
    _add_common_args(full_parser)
    full_parser.add_argument(
        "--no-docs", action="store_true", help="Skip documentation import"
    )
    full_parser.add_argument(
        "--no-plugin", action="store_true", help="Skip domain plugin creation"
    )

    # Clone command
    clone_parser = subparsers.add_parser("clone", help="Clone repository")
    clone_parser.add_argument("--repo", required=True, help="Repository URL")
    clone_parser.add_argument("--branch", default="main", help="Branch to clone")
    clone_parser.add_argument(
        "--shallow", action="store_true", default=True, help="Use shallow clone"
    )
    clone_parser.add_argument("--depth", type=int, default=1, help="Shallow clone depth")
    clone_parser.add_argument("--output", help="Output directory")

    # Detect language command
    detect_parser = subparsers.add_parser("detect", help="Detect programming language")
    detect_parser.add_argument("--path", required=True, help="Path to source code")

    # CPG command
    cpg_parser = subparsers.add_parser("cpg", help="Create Joern CPG")
    cpg_parser.add_argument("--path", required=True, help="Path to source code")
    cpg_parser.add_argument(
        "--language",
        choices=[l.value for l in SupportedLanguage],
        help="Programming language",
    )
    cpg_parser.add_argument("--output", help="Output CPG path")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export CPG to DuckDB")
    export_parser.add_argument("--cpg", required=True, help="Path to CPG file")
    export_parser.add_argument("--output", help="Output DuckDB path")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate CPG export")
    validate_parser.add_argument("--db", required=True, help="Path to DuckDB file")

    # Docs command
    docs_parser = subparsers.add_parser("docs", help="Import documentation to ChromaDB")
    docs_parser.add_argument("--path", required=True, help="Path to source code")
    docs_parser.add_argument("--db", help="Path to DuckDB file (for comments)")

    # Domain command
    domain_parser = subparsers.add_parser("domain", help="Create domain plugin")
    domain_parser.add_argument("--path", required=True, help="Path to source code")
    domain_parser.add_argument("--name", help="Domain name")
    domain_parser.add_argument("--db", help="Path to DuckDB file")
    domain_parser.add_argument(
        "--language",
        choices=[l.value for l in SupportedLanguage],
        help="Programming language",
    )

    # Languages command
    subparsers.add_parser("languages", help="List supported languages")

    return parser


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add common arguments to parser."""
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--repo", help="Repository URL")
    source_group.add_argument("--path", help="Local path to source code")

    parser.add_argument(
        "--language",
        choices=[l.value for l in SupportedLanguage],
        help="Programming language (auto-detect if not specified)",
    )
    parser.add_argument("--branch", default="main", help="Git branch")
    parser.add_argument("--shallow", action="store_true", default=True, help="Shallow clone")
    parser.add_argument("--include", nargs="+", default=[], help="Paths to include")
    parser.add_argument("--exclude", nargs="+", default=[], help="Paths to exclude")
    parser.add_argument(
        "--mode",
        choices=["full", "selective", "incremental"],
        default="full",
        help="Import mode",
    )
    parser.add_argument("--workspace", help="Joern workspace path")
    parser.add_argument("--domain-name", help="Custom domain name")
    parser.add_argument(
        "--memory", type=int, default=16, help="Joern memory (GB)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=10000, help="DuckDB batch size"
    )


async def run_full_pipeline(args) -> int:
    """Run full import pipeline."""
    request = ProjectImportRequest(
        repo_url=getattr(args, "repo", None),
        local_path=getattr(args, "path", None),
        branch=args.branch,
        shallow_clone=args.shallow,
        language=SupportedLanguage(args.language) if args.language else None,
        mode=ImportMode(args.mode),
        include_paths=args.include,
        exclude_paths=args.exclude,
        workspace_path=args.workspace,
        domain_name=getattr(args, "domain_name", None),
        import_docs=not args.no_docs,
        create_domain_plugin=not args.no_plugin,
        joern_memory_gb=args.memory,
        batch_size=args.batch_size,
    )

    source = request.repo_url or request.local_path

    if RICH_AVAILABLE:
        console.print(
            Panel.fit(
                f"[bold]Importing project[/bold]\n"
                f"Source: {source}\n"
                f"Language: {request.language or 'auto-detect'}\n"
                f"Mode: {request.mode.value}",
                title="RAG-CPGQL Import",
            )
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Starting import...", total=100)

            def progress_callback(status):
                step_msg = status.current_step or ""
                msg = f"{step_msg}"
                if status.steps:
                    for s in status.steps:
                        if s.status.value == "in_progress":
                            msg = f"{s.name}: {s.message or ''}"
                            break
                progress.update(task, completed=status.overall_progress, description=msg)

            pipeline = ProjectImportPipeline(progress_callback=progress_callback)

            try:
                result = await pipeline.run(request)
                progress.update(task, completed=100, description="Completed!")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                return 1

        # Display results
        _display_results(result)

    else:
        # Fallback without rich
        print(f"Importing project from {source}...")

        def progress_callback(status):
            print(f"Progress: {status.overall_progress}% - {status.current_step}")

        pipeline = ProjectImportPipeline(progress_callback=progress_callback)

        try:
            result = await pipeline.run(request)
            print("Import completed!")
            print(f"CPG: {result.cpg_path}")
            print(f"DuckDB: {result.duckdb_path}")
            print(f"Language: {result.detected_language.value}")
        except Exception as e:
            print(f"Error: {e}")
            return 1

    return 0


def _display_results(result) -> None:
    """Display import results using Rich."""
    if not RICH_AVAILABLE:
        return

    table = Table(title="Import Results")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("CPG Path", result.cpg_path)
    table.add_row("DuckDB Path", result.duckdb_path)
    table.add_row("Language", result.detected_language.value)
    table.add_row("Duration", f"{result.import_duration_seconds:.1f}s")

    if result.validation_report:
        score = result.validation_report.get("quality_score", "N/A")
        table.add_row("Quality Score", str(score))

    if result.cpg_stats:
        table.add_row("Methods", str(result.cpg_stats.get("methods", "N/A")))
        table.add_row("Calls", str(result.cpg_stats.get("call_nodes", "N/A")))

    console.print(table)

    if result.domain_plugin_path:
        console.print(f"\n[green]Domain plugin created: {result.domain_plugin_path}[/green]")

    if result.chromadb_stats:
        console.print(f"ChromaDB indexed: {result.chromadb_stats}")


async def run_single_step(step_name: str, args) -> int:
    """Run a single import step."""
    print(f"Running step: {step_name}")

    pipeline = ProjectImportPipeline()

    # Build context based on step and args
    context = {"request": ProjectImportRequest()}

    if hasattr(args, "path") and args.path:
        context["source_path"] = Path(args.path)
    if hasattr(args, "cpg") and args.cpg:
        context["cpg_path"] = args.cpg
    if hasattr(args, "db") and args.db:
        context["duckdb_path"] = args.db
    if hasattr(args, "language") and args.language:
        context["detected_language"] = SupportedLanguage(args.language)
    if hasattr(args, "name") and args.name:
        context["request"] = ProjectImportRequest(domain_name=args.name)

    # For clone step
    if step_name == "clone":
        context["request"] = ProjectImportRequest(
            repo_url=args.repo,
            branch=args.branch,
            shallow_clone=args.shallow,
            shallow_depth=args.depth,
            workspace_path=args.output,
        )

    try:
        result = await pipeline.run_step(step_name, context)
        print(f"Step completed successfully")
        for key, value in result.items():
            print(f"  {key}: {value}")
        return 0
    except Exception as e:
        print(f"Step failed: {e}")
        return 1


def list_languages() -> int:
    """List supported languages."""
    if RICH_AVAILABLE:
        table = Table(title="Supported Languages")
        table.add_column("Language", style="cyan")
        table.add_column("Joern Command", style="green")
        table.add_column("Extensions")

        for lang, frontend in JOERN_FRONTENDS.items():
            table.add_row(
                lang.value,
                frontend.command,
                ", ".join(frontend.file_extensions),
            )

        console.print(table)
    else:
        print("Supported Languages:")
        for lang, frontend in JOERN_FRONTENDS.items():
            print(f"  {lang.value}: {frontend.command} ({', '.join(frontend.file_extensions)})")

    return 0


def main() -> int:
    """Main entry point for CLI."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "full":
        return asyncio.run(run_full_pipeline(args))
    elif args.command == "clone":
        return asyncio.run(run_single_step("clone", args))
    elif args.command == "detect":
        return asyncio.run(run_single_step("detect_language", args))
    elif args.command == "cpg":
        return asyncio.run(run_single_step("joern_import", args))
    elif args.command == "export":
        return asyncio.run(run_single_step("cpg_export", args))
    elif args.command == "validate":
        return asyncio.run(run_single_step("validate", args))
    elif args.command == "docs":
        return asyncio.run(run_single_step("chromadb_import", args))
    elif args.command == "domain":
        return asyncio.run(run_single_step("domain_setup", args))
    elif args.command == "languages":
        return list_languages()

    return 0


if __name__ == "__main__":
    sys.exit(main())
