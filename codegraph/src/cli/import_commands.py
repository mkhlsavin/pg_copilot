"""
CLI Commands for Project Import and Management.

Usage:
    # Import commands
    python -m src.cli.import_commands import --repo https://github.com/org/repo
    python -m src.cli.import_commands import --path ./local/code --docker

    # Project management
    python -m src.cli.import_commands projects list
    python -m src.cli.import_commands projects activate <name>
    python -m src.cli.import_commands projects delete <name>

    # Server management
    python -m src.cli.import_commands server status
    python -m src.cli.import_commands server start
    python -m src.cli.import_commands server stop
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

from src.project_import import (
    FRONTENDS,
    ImportMode,
    JoernServerManager,
    ProjectImportPipeline,
    ProjectImportRequest,
    SupportedLanguage,
    get_config,
    list_supported_languages,
)

logger = logging.getLogger(__name__)

if RICH_AVAILABLE:
    console = Console()
else:
    console = None


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        prog="codegraph",
        description="CodeGraph Project Import and Management CLI",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Import command (main entry point)
    import_parser = subparsers.add_parser("import", help="Import a new project")
    _add_import_args(import_parser)

    # Legacy "full" command alias
    full_parser = subparsers.add_parser("full", help="Run full import pipeline (alias for import)")
    _add_import_args(full_parser)

    # Projects management
    projects_parser = subparsers.add_parser("projects", help="Manage projects")
    projects_sub = projects_parser.add_subparsers(dest="projects_command")

    # projects list
    projects_list = projects_sub.add_parser("list", help="List all projects")
    projects_list.add_argument("--group", help="Filter by group name")
    projects_list.add_argument("--language", help="Filter by language")
    projects_list.add_argument("--active", action="store_true", help="Show only active project")

    # projects activate
    projects_activate = projects_sub.add_parser("activate", help="Activate a project")
    projects_activate.add_argument("name", help="Project name to activate")
    projects_activate.add_argument("--group", help="Project group name")

    # projects delete
    projects_delete = projects_sub.add_parser("delete", help="Delete a project")
    projects_delete.add_argument("name", help="Project name to delete")
    projects_delete.add_argument("--group", help="Project group name")
    projects_delete.add_argument(
        "--delete-files", action="store_true", help="Also delete CPG and DuckDB files"
    )

    # projects info
    projects_info = projects_sub.add_parser("info", help="Show project details")
    projects_info.add_argument("name", help="Project name")
    projects_info.add_argument("--group", help="Project group name")

    # Server management
    server_parser = subparsers.add_parser("server", help="Manage Joern server")
    server_sub = server_parser.add_subparsers(dest="server_command")

    # server status
    server_sub.add_parser("status", help="Check server status")

    # server start
    server_start = server_sub.add_parser("start", help="Start Joern server")
    server_start.add_argument("--docker", action="store_true", help="Use Docker")
    server_start.add_argument("--memory", type=int, default=16, help="Memory in GB")

    # server stop
    server_sub.add_parser("stop", help="Stop Joern server")

    # server restart
    server_restart = server_sub.add_parser("restart", help="Restart Joern server")
    server_restart.add_argument("--docker", action="store_true", help="Use Docker")

    # Single step commands
    clone_parser = subparsers.add_parser("clone", help="Clone repository")
    clone_parser.add_argument("--repo", required=True, help="Repository URL")
    clone_parser.add_argument("--branch", default="main", help="Branch to clone")
    clone_parser.add_argument("--shallow", action="store_true", default=True)
    clone_parser.add_argument("--depth", type=int, default=1)
    clone_parser.add_argument("--output", help="Output directory")

    detect_parser = subparsers.add_parser("detect", help="Detect programming language")
    detect_parser.add_argument("--path", required=True, help="Path to source code")

    cpg_parser = subparsers.add_parser("cpg", help="Create Joern CPG")
    cpg_parser.add_argument("--path", required=True, help="Path to source code")
    cpg_parser.add_argument("--language", choices=[l.value for l in SupportedLanguage])
    cpg_parser.add_argument("--output", help="Output CPG path")
    cpg_parser.add_argument("--docker", action="store_true", help="Use Docker")

    export_parser = subparsers.add_parser("export", help="Export CPG to DuckDB")
    export_parser.add_argument("--cpg", required=True, help="Path to CPG file")
    export_parser.add_argument("--output", help="Output DuckDB path")

    validate_parser = subparsers.add_parser("validate", help="Validate CPG export")
    validate_parser.add_argument("--db", required=True, help="Path to DuckDB file")

    # Languages command
    subparsers.add_parser("languages", help="List supported languages")

    # Jobs command
    jobs_parser = subparsers.add_parser("jobs", help="List import jobs")
    jobs_parser.add_argument("--limit", type=int, default=10, help="Max jobs to show")
    jobs_parser.add_argument("--status", choices=["pending", "running", "completed", "failed"])

    return parser


def _add_import_args(parser: argparse.ArgumentParser) -> None:
    """Add import arguments to parser."""
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--repo", help="Git repository URL")
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
    parser.add_argument("--group", default="default", help="Project group name")
    parser.add_argument(
        "--memory", type=int, default=16, help="Joern memory (GB)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=10000, help="DuckDB batch size"
    )
    parser.add_argument(
        "--docker", action="store_true", help="Use Docker for Joern"
    )
    parser.add_argument(
        "--no-docs", action="store_true", help="Skip documentation import"
    )
    parser.add_argument(
        "--no-plugin", action="store_true", help="Skip domain plugin creation"
    )


async def run_import(args) -> int:
    """Run import pipeline."""
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

    # Get config and enable Docker if requested
    config = get_config()
    if args.docker:
        config.joern.use_docker = True

    if RICH_AVAILABLE:
        console.print(
            Panel.fit(
                f"[bold]Importing project[/bold]\n"
                f"Source: {source}\n"
                f"Language: {request.language or 'auto-detect'}\n"
                f"Mode: {request.mode.value}\n"
                f"Docker: {'Yes' if args.docker else 'No'}",
                title="CodeGraph Import",
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

            pipeline = ProjectImportPipeline(
                progress_callback=progress_callback,
                config=config,
            )

            try:
                result = await pipeline.run(request)
                progress.update(task, completed=100, description="Completed!")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                return 1
            finally:
                pipeline.shutdown()

        _display_results(result)

    else:
        print(f"Importing project from {source}...")

        def progress_callback(status):
            print(f"Progress: {status.overall_progress}% - {status.current_step}")

        pipeline = ProjectImportPipeline(
            progress_callback=progress_callback,
            config=config,
        )

        try:
            result = await pipeline.run(request)
            print("Import completed!")
            print(f"CPG: {result.cpg_path}")
            print(f"DuckDB: {result.duckdb_path}")
            print(f"Language: {result.detected_language.value}")
        except Exception as e:
            print(f"Error: {e}")
            return 1
        finally:
            pipeline.shutdown()

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
        total_nodes = result.cpg_stats.get("total_nodes", "N/A")
        total_edges = result.cpg_stats.get("total_edges", "N/A")
        table.add_row("Total Nodes", str(total_nodes))
        table.add_row("Total Edges", str(total_edges))

    console.print(table)

    if result.domain_plugin_path:
        console.print(f"\n[green]Domain plugin created: {result.domain_plugin_path}[/green]")

    if result.chromadb_stats:
        console.print(f"ChromaDB indexed: {result.chromadb_stats}")


async def run_projects_command(args) -> int:
    """Handle projects subcommands."""
    if not args.projects_command:
        print("Usage: codegraph projects {list|activate|delete|info}")
        return 1

    # Import here to avoid circular imports
    from src.api.database import get_async_session
    from src.project_import import ProjectRegistry

    async with get_async_session() as session:
        registry = ProjectRegistry(session)

        if args.projects_command == "list":
            return await _projects_list(registry, args)
        elif args.projects_command == "activate":
            return await _projects_activate(registry, args)
        elif args.projects_command == "delete":
            return await _projects_delete(registry, args)
        elif args.projects_command == "info":
            return await _projects_info(registry, args)

    return 0


async def _projects_list(registry, args) -> int:
    """List projects."""
    group_id = None
    if args.group:
        groups = await registry.list_groups()
        for g in groups:
            if g.name == args.group:
                group_id = g.id
                break

    if args.active:
        project = await registry.get_active_project(group_id)
        projects = [project] if project else []
    else:
        projects = await registry.list_projects(
            group_id=group_id,
            language=args.language if hasattr(args, "language") else None,
        )

    if RICH_AVAILABLE:
        table = Table(title="Projects")
        table.add_column("Name", style="cyan")
        table.add_column("Language", style="green")
        table.add_column("Active", style="yellow")
        table.add_column("DuckDB Path")
        table.add_column("Created")

        for p in projects:
            table.add_row(
                p.name,
                p.language,
                "Yes" if p.is_active else "",
                p.db_path or "N/A",
                p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "N/A",
            )

        console.print(table)
    else:
        print("Projects:")
        for p in projects:
            active = " (active)" if p.is_active else ""
            print(f"  {p.name}{active} - {p.language}")

    return 0


async def _projects_activate(registry, args) -> int:
    """Activate a project."""
    group_id = None
    if args.group:
        groups = await registry.list_groups()
        for g in groups:
            if g.name == args.group:
                group_id = g.id
                break

    project = await registry.get_project_by_name(args.name, group_id)
    if not project:
        print(f"Project not found: {args.name}")
        return 1

    success = await registry.set_active_project(project.id)
    if success:
        print(f"Activated project: {args.name}")
        return 0
    else:
        print(f"Failed to activate project: {args.name}")
        return 1


async def _projects_delete(registry, args) -> int:
    """Delete a project."""
    group_id = None
    if args.group:
        groups = await registry.list_groups()
        for g in groups:
            if g.name == args.group:
                group_id = g.id
                break

    project = await registry.get_project_by_name(args.name, group_id)
    if not project:
        print(f"Project not found: {args.name}")
        return 1

    success = await registry.delete_project(
        project.id,
        delete_files=args.delete_files,
    )

    if success:
        print(f"Deleted project: {args.name}")
        if args.delete_files:
            print("Associated files were also deleted.")
        return 0
    else:
        print(f"Failed to delete project: {args.name}")
        return 1


async def _projects_info(registry, args) -> int:
    """Show project info."""
    group_id = None
    if args.group:
        groups = await registry.list_groups()
        for g in groups:
            if g.name == args.group:
                group_id = g.id
                break

    project = await registry.get_project_by_name(args.name, group_id)
    if not project:
        print(f"Project not found: {args.name}")
        return 1

    if RICH_AVAILABLE:
        table = Table(title=f"Project: {project.name}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("ID", str(project.id))
        table.add_row("Name", project.name)
        table.add_row("Language", project.language)
        table.add_row("Active", "Yes" if project.is_active else "No")
        table.add_row("Source Path", project.source_path or "N/A")
        table.add_row("CPG Path", project.cpg_path or "N/A")
        table.add_row("DuckDB Path", project.db_path or "N/A")
        table.add_row("Description", project.description or "N/A")
        table.add_row("Created", str(project.created_at))

        if project.metadata:
            for key, value in project.metadata.items():
                table.add_row(f"Meta: {key}", str(value)[:50])

        console.print(table)
    else:
        print(f"Project: {project.name}")
        print(f"  ID: {project.id}")
        print(f"  Language: {project.language}")
        print(f"  Active: {project.is_active}")
        print(f"  DuckDB: {project.db_path}")

    return 0


def run_server_command(args) -> int:
    """Handle server subcommands."""
    if not args.server_command:
        print("Usage: codegraph server {status|start|stop|restart}")
        return 1

    config = get_config()

    if args.server_command == "status":
        return _server_status(config)
    elif args.server_command == "start":
        if hasattr(args, "docker") and args.docker:
            config.joern.use_docker = True
        if hasattr(args, "memory"):
            config.joern.memory_gb = args.memory
        return _server_start(config)
    elif args.server_command == "stop":
        return _server_stop(config)
    elif args.server_command == "restart":
        if hasattr(args, "docker") and args.docker:
            config.joern.use_docker = True
        return _server_restart(config)

    return 0


def _server_status(config) -> int:
    """Check server status."""
    manager = JoernServerManager(config)

    is_running = manager.is_running()
    mode = "Docker" if config.joern.use_docker else "Local"
    endpoint = f"{config.joern.server_host}:{config.joern.server_port}"

    if RICH_AVAILABLE:
        status_color = "green" if is_running else "red"
        status_text = "Running" if is_running else "Stopped"
        console.print(f"Joern Server: [{status_color}]{status_text}[/{status_color}]")
        console.print(f"Mode: {mode}")
        console.print(f"Endpoint: {endpoint}")
    else:
        print(f"Joern Server: {'Running' if is_running else 'Stopped'}")
        print(f"Mode: {mode}")
        print(f"Endpoint: {endpoint}")

    return 0


def _server_start(config) -> int:
    """Start server."""
    manager = JoernServerManager(config)

    if manager.is_running():
        print("Server is already running")
        return 0

    print("Starting Joern server...")
    success = manager.start()

    if success:
        print("Server started successfully")
        return 0
    else:
        print("Failed to start server")
        return 1


def _server_stop(config) -> int:
    """Stop server."""
    manager = JoernServerManager(config)

    if not manager.is_running():
        print("Server is not running")
        return 0

    print("Stopping Joern server...")
    success = manager.stop()

    if success:
        print("Server stopped successfully")
        return 0
    else:
        print("Failed to stop server")
        return 1


def _server_restart(config) -> int:
    """Restart server."""
    manager = JoernServerManager(config)

    print("Restarting Joern server...")
    success = manager.restart()

    if success:
        print("Server restarted successfully")
        return 0
    else:
        print("Failed to restart server")
        return 1


async def run_single_step(step_name: str, args) -> int:
    """Run a single import step."""
    print(f"Running step: {step_name}")

    config = get_config()
    if hasattr(args, "docker") and args.docker:
        config.joern.use_docker = True

    pipeline = ProjectImportPipeline(config=config)

    context = {"request": ProjectImportRequest()}

    if hasattr(args, "path") and args.path:
        context["source_path"] = Path(args.path)
    if hasattr(args, "cpg") and args.cpg:
        context["cpg_path"] = args.cpg
    if hasattr(args, "db") and args.db:
        context["duckdb_path"] = args.db
    if hasattr(args, "language") and args.language:
        context["detected_language"] = SupportedLanguage(args.language)

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
        print("Step completed successfully")
        for key, value in result.items():
            if not key.startswith("_"):
                print(f"  {key}: {value}")
        return 0
    except Exception as e:
        print(f"Step failed: {e}")
        return 1
    finally:
        pipeline.shutdown()


def list_languages() -> int:
    """List supported languages."""
    languages = list_supported_languages()

    if RICH_AVAILABLE:
        table = Table(title="Supported Languages")
        table.add_column("Language", style="cyan")
        table.add_column("Command", style="green")
        table.add_column("Extensions")
        table.add_column("Description")

        for lang in languages:
            table.add_row(
                lang["language"],
                lang["command"],
                ", ".join(lang["extensions"][:4]),
                lang["description"][:40],
            )

        console.print(table)
    else:
        print("Supported Languages:")
        for lang in languages:
            exts = ", ".join(lang["extensions"][:3])
            print(f"  {lang['language']}: {lang['command']} ({exts})")

    return 0


async def run_jobs_command(args) -> int:
    """List import jobs."""
    from src.api.database import get_async_session
    from src.project_import import ProjectRegistry

    async with get_async_session() as session:
        registry = ProjectRegistry(session)
        jobs = await registry.list_import_jobs(
            status=args.status,
            limit=args.limit,
        )

    if RICH_AVAILABLE:
        table = Table(title="Import Jobs")
        table.add_column("ID", style="cyan")
        table.add_column("Project", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Progress")
        table.add_column("Created")

        for job in jobs:
            status_color = {
                "pending": "white",
                "running": "blue",
                "completed": "green",
                "failed": "red",
            }.get(job.status.value, "white")

            table.add_row(
                str(job.id)[:8],
                job.project_name,
                f"[{status_color}]{job.status.value}[/{status_color}]",
                f"{job.progress}%",
                job.created_at.strftime("%Y-%m-%d %H:%M") if job.created_at else "N/A",
            )

        console.print(table)
    else:
        print("Import Jobs:")
        for job in jobs:
            print(f"  {job.id}: {job.project_name} - {job.status.value} ({job.progress}%)")

    return 0


def main() -> int:
    """Main entry point for CLI."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Import commands
    if args.command in ("import", "full"):
        return asyncio.run(run_import(args))

    # Projects commands
    elif args.command == "projects":
        return asyncio.run(run_projects_command(args))

    # Server commands
    elif args.command == "server":
        return run_server_command(args)

    # Single step commands
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

    # Other commands
    elif args.command == "languages":
        return list_languages()
    elif args.command == "jobs":
        return asyncio.run(run_jobs_command(args))

    return 0


if __name__ == "__main__":
    sys.exit(main())
