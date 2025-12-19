"""REPL (Read-Eval-Print Loop) for TUI."""

import sys
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

from .components.scenario_panel import ScenarioPanel
from .components.dialogue_panel import DialoguePanel
from .components.help_panel import HelpPanel
from .components.status_bar import StatusBar
from .managers.dialogue_manager import DialogueManager
from .managers.session_manager import SessionManager
from .utils.themes import Theme, DEFAULT_THEME
from .utils.formatters import format_result, format_error
from .api_client import TUIApiClient

logger = logging.getLogger(__name__)


class CommandHandler:
    """Handles TUI commands."""

    def __init__(self, repl: "TUIRepl"):
        self.repl = repl
        self._commands: Dict[str, Callable] = {
            "help": self._cmd_help,
            "h": self._cmd_help,
            "scenarios": self._cmd_scenarios,
            "select": self._cmd_select,
            "history": self._cmd_history,
            "save": self._cmd_save,
            "load": self._cmd_load,
            "config": self._cmd_config,
            "stat": self._cmd_stat,
            "stats": self._cmd_stat,  # alias
            "query": self._cmd_query,
            "sql": self._cmd_query,  # alias
            "demo": self._cmd_demo,
            "review": self._cmd_review,
            "project": self._cmd_project,
            "proj": self._cmd_project,  # alias
            # New commands
            "group": self._cmd_group,
            "groups": self._cmd_group,  # alias
            "import": self._cmd_import,
            "auth": self._cmd_auth,
            "session": self._cmd_session,
            "sessions": self._cmd_session,  # alias
            "health": self._cmd_health,
            # End new commands
            "clear": self._cmd_clear,
            "exit": self._cmd_exit,
            "quit": self._cmd_exit,
            "q": self._cmd_exit,
        }

    def handle(self, command: str, args: List[str]) -> bool:
        """
        Handle command execution.

        Returns True if command was handled.
        """
        if command not in self._commands:
            self.repl.console.print(f"[red]Unknown command: /{command}[/red]")
            self.repl.console.print("Use /help to see available commands.")
            return True

        try:
            return self._commands[command](args)
        except Exception as e:
            self.repl.console.print(format_error(e, f"Command /{command} failed"))
            return True

    def _cmd_help(self, args: List[str]) -> bool:
        """Show help."""
        topic = args[0] if args else None
        panel = self.repl.help_panel.render(topic)
        self.repl.console.print(panel)
        return True

    def _cmd_scenarios(self, args: List[str]) -> bool:
        """List scenarios."""
        panel = self.repl.scenario_panel.render()
        self.repl.console.print(panel)
        return True

    def _cmd_select(self, args: List[str]) -> bool:
        """Select a scenario."""
        if not args:
            self.repl.console.print("[yellow]Usage: /select <number>[/yellow]")
            return True

        success, message = self.repl.scenario_panel.select_scenario(args[0])
        if success:
            self.repl.console.print(f"[green]{message}[/green]")
            self.repl.session_manager.set_scenario(args[0].zfill(2))
            self.repl.status_bar.update(scenario=args[0].zfill(2))
        else:
            self.repl.console.print(f"[red]{message}[/red]")
        return True

    def _cmd_history(self, args: List[str]) -> bool:
        """Show history."""
        limit = int(args[0]) if args else 10
        dm = self.repl.session_manager.get_dialogue_manager()
        history = dm.get_history(limit=limit)

        if not history:
            self.repl.console.print("[dim]No conversation history[/dim]")
            return True

        panels = self.repl.dialogue_panel.render_history(history)
        for panel in panels:
            self.repl.console.print(panel)
        return True

    def _cmd_save(self, args: List[str]) -> bool:
        """Save session."""
        try:
            session_id = self.repl.session_manager.save_session()
            self.repl.console.print(f"[green]Session saved: {session_id}[/green]")
        except Exception as e:
            self.repl.console.print(f"[red]Failed to save: {e}[/red]")
        return True

    def _cmd_load(self, args: List[str]) -> bool:
        """Load session."""
        if not args:
            # List available sessions
            sessions = self.repl.session_manager.list_sessions()
            if not sessions:
                self.repl.console.print("[dim]No saved sessions[/dim]")
                return True

            self.repl.console.print("[bold]Available sessions:[/bold]")
            for s in sessions[:10]:
                self.repl.console.print(
                    f"  {s.session_id} - {s.message_count} msgs "
                    f"({s.updated_at.strftime('%Y-%m-%d %H:%M')})"
                )
            return True

        try:
            self.repl.session_manager.load_session(args[0])
            self.repl.console.print(f"[green]Session loaded: {args[0]}[/green]")
            self.repl.status_bar.update(
                session_id=args[0],
                scenario=self.repl.session_manager.current_session.current_scenario,
            )
        except Exception as e:
            self.repl.console.print(f"[red]Failed to load: {e}[/red]")
        return True

    def _cmd_config(self, args: List[str]) -> bool:
        """View/edit config interactively."""
        from .components.config_editor import ConfigEditor

        editor = ConfigEditor(theme=self.repl.theme)

        if not args:
            # Show interactive section list
            panel = editor.render_section_list()
            self.repl.console.print(panel)
            return True

        # Check if first arg is a number (section index)
        section = args[0]
        if section.isdigit():
            section = editor.get_section_by_index(int(section))
            if not section:
                self.repl.console.print(f"[red]Invalid section number: {args[0]}[/red]")
                return True

        if len(args) == 1:
            # Show section details
            panel = editor.render_section(section)
            self.repl.console.print(panel)

        elif len(args) == 2:
            # Show specific key
            data = editor.get_section(section)
            if data:
                key = args[1]
                keys = key.split(".")
                value = data
                for k in keys:
                    if isinstance(value, dict) and k in value:
                        value = value[k]
                    else:
                        self.repl.console.print(f"[red]Key not found: {key}[/red]")
                        return True
                self.repl.console.print(f"[cyan]{section}.{key}[/cyan] = {value}")
            else:
                self.repl.console.print(f"[red]Section not found: {section}[/red]")

        elif len(args) >= 3:
            # Edit: /config section key value
            key = args[1]
            value = " ".join(args[2:])
            success, msg = editor.edit_value(section, key, value)
            if success:
                save_success, save_msg = editor.save_changes()
                if save_success:
                    self.repl.console.print(f"[green]{msg}[/green]")
                    self.repl.console.print(f"[dim]{save_msg}[/dim]")
                else:
                    self.repl.console.print(f"[yellow]{msg} (not saved: {save_msg})[/yellow]")
            else:
                self.repl.console.print(f"[red]{msg}[/red]")

        return True

    def _cmd_stat(self, args: List[str]) -> bool:
        """Show system statistics."""
        # Check for extended API-based stats subcommands
        if args and args[0].lower() in ("scenarios", "performance", "api"):
            import asyncio
            from .components.extended_stats_panel import ExtendedStatsPanel

            panel = ExtendedStatsPanel(
                theme=self.repl.theme,
                api_client=self.repl.api_client,
            )

            try:
                subcommand = args[0].lower()
                if subcommand == "scenarios":
                    result = asyncio.run(panel.get_scenario_stats())
                elif subcommand == "performance":
                    result = asyncio.run(panel.get_performance_stats())
                elif subcommand == "api":
                    result = asyncio.run(panel.get_api_stats())
                else:
                    result = asyncio.run(panel.get_all_stats())

                self.repl.console.print(result)
            except Exception as e:
                self.repl.console.print(f"[red]Error getting stats: {e}[/red]")
            return True

        # Default: show local CPG/ChromaDB stats
        from pathlib import Path
        from .components.stats_display import StatsDisplay
        from src.project_manager import get_project_manager

        pm = get_project_manager()
        db_path = Path(pm.get_active_db_path())

        display = StatsDisplay(theme=self.repl.theme, duckdb_path=db_path)
        stats = display.collect_stats()
        panel = display.render(stats)
        self.repl.console.print(panel)
        return True

    def _cmd_query(self, args: List[str]) -> bool:
        """Execute SQL query on CPG database."""
        from pathlib import Path
        from .components.query_executor import QueryExecutor
        from src.project_manager import get_project_manager

        pm = get_project_manager()
        db_path = Path(pm.get_active_db_path())

        executor = QueryExecutor(db_path=db_path, theme=self.repl.theme)

        if not args:
            # Show query help
            panel = executor.render_help()
            self.repl.console.print(panel)
            return True

        # Join args as query
        query = " ".join(args)

        # Validate query
        valid, error = executor.validate_query(query)
        if not valid:
            self.repl.console.print(f"[red]Query validation failed: {error}[/red]")
            return True

        # Execute query
        try:
            with self.repl.console.status("[yellow]Executing query...[/yellow]"):
                results, duration = executor.execute(query)

            panel = executor.render_results(results, query, duration)
            self.repl.console.print(panel)

        except FileNotFoundError as e:
            self.repl.console.print(f"[red]Database not found: {e}[/red]")
        except Exception as e:
            panel = executor.render_error(e, query)
            self.repl.console.print(panel)

        return True

    def _cmd_demo(self, args: List[str]) -> bool:
        """Run quick demo with one question per scenario."""
        from .components.demo_runner import DemoRunner

        # Check if copilot is available
        if not self.repl.copilot:
            self.repl.console.print(
                "[red]Copilot not available.[/red]\n"
                "[dim]Demo requires full mode. Install chromadb or check configuration.[/dim]"
            )
            return True

        # Parse arguments
        scenarios = None
        language = "en"

        for i, arg in enumerate(args):
            if arg == "--scenarios" and i + 1 < len(args):
                scenarios = [s.strip().zfill(2) for s in args[i + 1].split(",")]
            elif arg == "--lang" and i + 1 < len(args):
                language = args[i + 1]

        # Create runner
        runner = DemoRunner(
            console=self.repl.console,
            copilot=self.repl.copilot,
            theme=self.repl.theme,
        )

        # Load questions
        self.repl.console.print("[cyan]Loading demo questions...[/cyan]")
        questions = runner.load_demo_questions(language)

        if not questions:
            self.repl.console.print("[red]No demo questions found.[/red]")
            return True

        # Run demo
        self.repl.console.print(
            f"[cyan]Running demo with {len(questions)} scenarios...[/cyan]\n"
        )

        results = runner.run_demo(scenarios=scenarios, language=language)

        # Display results
        self.repl.console.print()
        self.repl.console.print(runner.render_results(results))

        # Save results to JSON
        if results:
            output_file = runner.save_results_json(results)
            self.repl.console.print(
                f"\n[dim]Results saved to:[/dim] [cyan]{output_file}[/cyan]"
            )

        return True

    def _cmd_review(self, args: List[str]) -> bool:
        """Launch code review mode."""
        from .components.review_panel import ReviewPanel

        panel = ReviewPanel(theme=self.repl.theme)

        # Parse arguments
        if not args or args[0] == "--help":
            self.repl.console.print(panel.render_help())
            return True

        # Parse flags
        format_override = None
        show_inline = False
        source_args = []

        i = 0
        while i < len(args):
            if args[i] == "--format" and i + 1 < len(args):
                format_override = args[i + 1]
                i += 2
            elif args[i] == "--inline":
                show_inline = True
                i += 1
            else:
                source_args.append(args[i])
                i += 1

        # If no source args, show menu
        if not source_args:
            self.repl.console.print(panel.render_source_menu())
            try:
                choice = Prompt.ask(
                    "Select source",
                    choices=["1", "2", "3", "4", "5"],
                    default="3"
                )
                patch = panel.get_input_by_choice(choice, self.repl.console)
            except KeyboardInterrupt:
                self.repl.console.print("\n[yellow]Review cancelled[/yellow]")
                return True
        elif source_args[0] == "github":
            pr_num = int(source_args[1]) if len(source_args) > 1 else None
            patch = panel.get_github_pr(pr_num, self.repl.console)
        elif source_args[0] == "gitlab":
            mr_iid = int(source_args[1]) if len(source_args) > 1 else None
            patch = panel.get_gitlab_mr(mr_iid, self.repl.console)
        elif source_args[0] == "file":
            path = source_args[1] if len(source_args) > 1 else None
            patch = panel.get_diff_file(path, self.repl.console)
        elif source_args[0] == "diff":
            patch = panel.get_pasted_diff(self.repl.console)
        elif source_args[0] == "git":
            patch = panel.get_git_diff(self.repl.console)
        else:
            self.repl.console.print(
                f"[red]Unknown source: {source_args[0]}[/red]\n"
                "[dim]Use /review --help for usage[/dim]"
            )
            return True

        if not patch:
            return True

        # Run review with progress
        verdict = panel.run_review(patch, self.repl.console)

        if not verdict:
            return True

        # Render output
        output_format = format_override or "md"
        result_panel = panel.render_verdict(verdict, output_format, show_inline)
        self.repl.console.print(result_panel)

        return True

    def _cmd_project(self, args: List[str]) -> bool:
        """Manage projects: list, switch, add."""
        from src.project_manager import get_project_manager

        pm = get_project_manager()

        if not args:
            # Show current project
            project = pm.get_active_project()
            if project:
                self.repl.console.print(
                    f"[bold]Current project:[/bold] [cyan]{project.name}[/cyan]\n"
                    f"  Database: {project.db_path}\n"
                    f"  Language: {project.language}\n"
                    f"  Description: {project.description}"
                )
            else:
                self.repl.console.print("[yellow]No active project[/yellow]")
            return True

        subcommand = args[0].lower()

        if subcommand == "list":
            # List all projects
            self.repl.console.print(pm.format_project_list())
            return True

        elif subcommand == "switch":
            if len(args) < 2:
                self.repl.console.print("[yellow]Usage: /project switch <name>[/yellow]")
                return True

            name = args[1]
            if pm.switch_project(name):
                project = pm.get_active_project()
                self.repl.console.print(
                    f"[green]Switched to project: {name}[/green]\n"
                    f"  Database: {project.db_path}\n"
                    f"  Language: {project.language}"
                )
                # Update status bar
                self.repl.status_bar.update(project_name=name)
                # Reinitialize copilot with new database
                self._reinitialize_copilot(project.db_path)
                # Activate corresponding domain
                self._activate_domain_for_language(project.language)
            else:
                self.repl.console.print(f"[red]Failed to switch to project: {name}[/red]")
            return True

        elif subcommand == "add":
            if len(args) < 3:
                self.repl.console.print(
                    "[yellow]Usage: /project add <name> <db_path> [language] [description][/yellow]"
                )
                return True

            name = args[1]
            db_path = args[2]
            language = args[3] if len(args) > 3 else "unknown"
            description = " ".join(args[4:]) if len(args) > 4 else ""

            if pm.add_project(name, db_path, language, description):
                self.repl.console.print(f"[green]Added project: {name}[/green]")
            else:
                self.repl.console.print(f"[red]Failed to add project: {name}[/red]")
            return True

        elif subcommand == "remove":
            if len(args) < 2:
                self.repl.console.print("[yellow]Usage: /project remove <name>[/yellow]")
                return True

            name = args[1]
            if pm.remove_project(name):
                self.repl.console.print(f"[green]Removed project: {name}[/green]")
            else:
                self.repl.console.print(f"[red]Failed to remove project: {name}[/red]")
            return True

        elif subcommand == "info":
            # Show detailed project info
            if len(args) < 2:
                self.repl.console.print("[yellow]Usage: /project info <name>[/yellow]")
                return True

            import asyncio
            from .components.project_panel import ProjectPanel

            panel = ProjectPanel(theme=self.repl.theme, api_client=self.repl.api_client)
            try:
                result = asyncio.run(panel.get_project_info(args[1]))
                self.repl.console.print(result)
            except Exception as e:
                self.repl.console.print(f"[red]Error: {e}[/red]")
            return True

        elif subcommand == "create":
            # Create project in a group
            # Parse arguments: /project create <name> --group <group_name>
            name = None
            group_name = None
            language = None
            description = None

            i = 1
            while i < len(args):
                if args[i] == "--group" and i + 1 < len(args):
                    group_name = args[i + 1]
                    i += 2
                elif args[i] == "--language" and i + 1 < len(args):
                    language = args[i + 1]
                    i += 2
                elif args[i] == "--description" and i + 1 < len(args):
                    description = " ".join(args[i + 1:])
                    break
                elif not name:
                    name = args[i]
                    i += 1
                else:
                    i += 1

            if not name:
                self.repl.console.print(
                    "[yellow]Usage: /project create <name> --group <group_name> "
                    "[--language <lang>] [--description <text>][/yellow]"
                )
                return True

            if not group_name:
                self.repl.console.print(
                    "[yellow]Please specify --group <group_name>[/yellow]"
                )
                return True

            import asyncio
            from .components.project_panel import ProjectPanel

            panel = ProjectPanel(theme=self.repl.theme, api_client=self.repl.api_client)
            try:
                result = asyncio.run(panel.create_project(
                    name=name,
                    group_name=group_name,
                    language=language,
                    description=description,
                ))
                self.repl.console.print(result)
            except Exception as e:
                self.repl.console.print(f"[red]Error: {e}[/red]")
            return True

        else:
            self.repl.console.print(
                f"[red]Unknown subcommand: {subcommand}[/red]\n"
                "[dim]Available: list, switch, add, remove, info, create[/dim]"
            )
            return True

    def _reinitialize_copilot(self, db_path: str) -> None:
        """Reinitialize copilot with new database path."""
        if not self.repl.copilot:
            return

        try:
            # Update CPGQueryService in copilot
            if hasattr(self.repl.copilot, 'cpg_service'):
                self.repl.copilot.cpg_service.set_database(db_path)
            elif hasattr(self.repl.copilot, 'query_service'):
                self.repl.copilot.query_service.set_database(db_path)

            self.repl.console.print(f"[dim]Copilot reinitialized with {db_path}[/dim]")
        except Exception as e:
            logger.warning(f"Failed to reinitialize copilot: {e}")

    def _activate_domain_for_language(self, language: str) -> None:
        """Activate the appropriate domain plugin for a language."""
        from src.domains import DomainRegistry

        # Map language to domain name
        language_to_domain = {
            "c": "postgresql",  # Use PostgreSQL domain for C (has C patterns)
            "cpp": "generic_cpp",
            "c++": "generic_cpp",
            "python": "python_django",
            "py": "python_django",
        }

        domain_name = language_to_domain.get(language.lower())
        if domain_name and DomainRegistry.is_registered(domain_name):
            try:
                DomainRegistry.activate(domain_name)
                self.repl.console.print(f"[dim]Domain activated: {domain_name}[/dim]")
            except Exception as e:
                logger.warning(f"Failed to activate domain {domain_name}: {e}")
        else:
            # Fall back to generic_cpp for unknown languages
            try:
                DomainRegistry.activate("generic_cpp")
                self.repl.console.print(f"[dim]Domain activated: generic_cpp (fallback)[/dim]")
            except Exception as e:
                logger.warning(f"Failed to activate fallback domain: {e}")

    # =========================================================================
    # New commands: /group, /import, /auth, /session, /health
    # =========================================================================

    def _cmd_group(self, args: List[str]) -> bool:
        """Manage project groups."""
        import asyncio
        from .components.group_panel import GroupPanel

        panel = GroupPanel(
            theme=self.repl.theme,
            api_client=self.repl.api_client,
        )

        if not args:
            self.repl.console.print(panel.render_help())
            return True

        subcommand = args[0].lower()

        try:
            if subcommand == "list":
                result = asyncio.run(panel.list_groups())
                self.repl.console.print(result)

            elif subcommand == "create":
                if len(args) < 2:
                    self.repl.console.print("[yellow]Usage: /group create <name> [description][/yellow]")
                    return True
                name = args[1]
                description = " ".join(args[2:]) if len(args) > 2 else None
                result = asyncio.run(panel.create_group(name, description))
                self.repl.console.print(result)

            elif subcommand == "delete":
                if len(args) < 2:
                    self.repl.console.print("[yellow]Usage: /group delete <name>[/yellow]")
                    return True
                result = asyncio.run(panel.delete_group(args[1]))
                self.repl.console.print(result)

            elif subcommand == "users":
                if len(args) < 2:
                    self.repl.console.print("[yellow]Usage: /group users <name>[/yellow]")
                    return True
                result = asyncio.run(panel.list_users(args[1]))
                self.repl.console.print(result)

            elif subcommand == "add-user":
                if len(args) < 4:
                    self.repl.console.print(
                        "[yellow]Usage: /group add-user <group> <user_id> <role>[/yellow]\n"
                        "[dim]Roles: viewer, editor, admin[/dim]"
                    )
                    return True
                result = asyncio.run(panel.add_user(args[1], args[2], args[3]))
                self.repl.console.print(result)

            elif subcommand == "remove-user":
                if len(args) < 3:
                    self.repl.console.print("[yellow]Usage: /group remove-user <group> <user_id>[/yellow]")
                    return True
                result = asyncio.run(panel.remove_user(args[1], args[2]))
                self.repl.console.print(result)

            else:
                self.repl.console.print(f"[red]Unknown subcommand: {subcommand}[/red]")
                self.repl.console.print(panel.render_help())

        except Exception as e:
            self.repl.console.print(f"[red]Error: {e}[/red]")

        return True

    def _cmd_import(self, args: List[str]) -> bool:
        """Manage project imports."""
        import asyncio
        from .components.import_panel import ImportPanel

        panel = ImportPanel(
            theme=self.repl.theme,
            api_client=self.repl.api_client,
        )

        if not args:
            self.repl.console.print(panel.render_help())
            return True

        subcommand = args[0].lower()

        try:
            if subcommand == "start":
                if len(args) < 2:
                    self.repl.console.print(
                        "[yellow]Usage: /import start <repo_url|path> [--language <lang>] [--group <name>][/yellow]"
                    )
                    return True

                # Parse arguments
                source = args[1]
                language = None
                group_name = None

                i = 2
                while i < len(args):
                    if args[i] == "--language" and i + 1 < len(args):
                        language = args[i + 1]
                        i += 2
                    elif args[i] == "--group" and i + 1 < len(args):
                        group_name = args[i + 1]
                        i += 2
                    else:
                        i += 1

                result = asyncio.run(panel.start_import(source, language, group_name))
                self.repl.console.print(result)

            elif subcommand == "status":
                job_id = args[1] if len(args) > 1 else None
                result = asyncio.run(panel.get_status(job_id))
                self.repl.console.print(result)

            elif subcommand == "watch":
                if len(args) < 2:
                    self.repl.console.print("[yellow]Usage: /import watch <job_id>[/yellow]")
                    return True
                asyncio.run(panel.watch_progress(args[1], self.repl.console))

            elif subcommand == "jobs":
                result = asyncio.run(panel.list_jobs())
                self.repl.console.print(result)

            elif subcommand == "cancel":
                if len(args) < 2:
                    self.repl.console.print("[yellow]Usage: /import cancel <job_id>[/yellow]")
                    return True
                result = asyncio.run(panel.cancel_job(args[1]))
                self.repl.console.print(result)

            else:
                self.repl.console.print(f"[red]Unknown subcommand: {subcommand}[/red]")
                self.repl.console.print(panel.render_help())

        except Exception as e:
            self.repl.console.print(f"[red]Error: {e}[/red]")

        return True

    def _cmd_auth(self, args: List[str]) -> bool:
        """Authentication management."""
        import asyncio
        from .components.auth_panel import AuthPanel

        panel = AuthPanel(
            theme=self.repl.theme,
            api_client=self.repl.api_client,
        )

        if not args:
            self.repl.console.print(panel.render_help())
            return True

        subcommand = args[0].lower()

        try:
            if subcommand == "login":
                result = asyncio.run(panel.login(self.repl.console))
                self.repl.console.print(result)

            elif subcommand == "logout":
                result = asyncio.run(panel.logout())
                self.repl.console.print(result)

            elif subcommand == "me":
                result = asyncio.run(panel.get_current_user())
                self.repl.console.print(result)

            elif subcommand == "api-keys":
                if len(args) < 2 or args[1] == "list":
                    result = asyncio.run(panel.list_api_keys())
                elif args[1] == "create":
                    if len(args) < 3:
                        self.repl.console.print("[yellow]Usage: /auth api-keys create <name>[/yellow]")
                        return True
                    result = asyncio.run(panel.create_api_key(args[2]))
                elif args[1] == "revoke":
                    if len(args) < 3:
                        self.repl.console.print("[yellow]Usage: /auth api-keys revoke <key_id>[/yellow]")
                        return True
                    result = asyncio.run(panel.revoke_api_key(args[2]))
                else:
                    self.repl.console.print(f"[red]Unknown api-keys subcommand: {args[1]}[/red]")
                    return True
                self.repl.console.print(result)

            else:
                self.repl.console.print(f"[red]Unknown subcommand: {subcommand}[/red]")
                self.repl.console.print(panel.render_help())

        except Exception as e:
            self.repl.console.print(f"[red]Error: {e}[/red]")

        return True

    def _cmd_session(self, args: List[str]) -> bool:
        """Manage chat sessions."""
        import asyncio
        from .components.session_panel import SessionPanel

        panel = SessionPanel(
            theme=self.repl.theme,
            api_client=self.repl.api_client,
        )

        if not args:
            self.repl.console.print(panel.render_help())
            return True

        subcommand = args[0].lower()

        try:
            if subcommand == "list":
                result = asyncio.run(panel.list_sessions())
                self.repl.console.print(result)

            elif subcommand == "switch":
                if len(args) < 2:
                    self.repl.console.print("[yellow]Usage: /session switch <session_id>[/yellow]")
                    return True
                # Switch session locally
                try:
                    self.repl.session_manager.load_session(args[1])
                    self.repl.console.print(f"[green]Switched to session: {args[1]}[/green]")
                    self.repl.status_bar.update(session_id=args[1])
                except Exception as e:
                    self.repl.console.print(f"[red]Failed to switch session: {e}[/red]")

            elif subcommand == "export":
                if len(args) < 2:
                    self.repl.console.print("[yellow]Usage: /session export <session_id> [format][/yellow]")
                    return True
                session_id = args[1]
                fmt = args[2] if len(args) > 2 else "json"
                result = asyncio.run(panel.export_session(session_id, fmt))
                self.repl.console.print(result)

            elif subcommand == "delete":
                if len(args) < 2:
                    self.repl.console.print("[yellow]Usage: /session delete <session_id>[/yellow]")
                    return True
                result = asyncio.run(panel.delete_session(args[1]))
                self.repl.console.print(result)

            else:
                self.repl.console.print(f"[red]Unknown subcommand: {subcommand}[/red]")
                self.repl.console.print(panel.render_help())

        except Exception as e:
            self.repl.console.print(f"[red]Error: {e}[/red]")

        return True

    def _cmd_health(self, args: List[str]) -> bool:
        """Show system health status."""
        import asyncio
        from .components.health_panel import HealthPanel

        panel = HealthPanel(
            theme=self.repl.theme,
            api_client=self.repl.api_client,
        )

        try:
            result = asyncio.run(panel.render())
            self.repl.console.print(result)
        except Exception as e:
            self.repl.console.print(f"[red]Failed to get health status: {e}[/red]")

        return True

    def _cmd_clear(self, args: List[str]) -> bool:
        """Clear screen."""
        self.repl.console.clear()
        return True

    def _cmd_exit(self, args: List[str]) -> bool:
        """Exit application."""
        # Save session before exit
        try:
            if self.repl.session_manager.current_session:
                self.repl.session_manager.save_session()
                self.repl.console.print("[dim]Session saved[/dim]")
        except Exception:
            pass

        self.repl.console.print("[cyan]Goodbye![/cyan]")
        self.repl.running = False
        return True


class TUIRepl:
    """
    Main Read-Eval-Print Loop for the TUI.

    Handles:
    - Command parsing
    - Query processing
    - Rich console output
    - Session management
    """

    def __init__(
        self,
        console: Console,
        session_manager: SessionManager,
        copilot: Optional[Any] = None,
        theme: Theme = DEFAULT_THEME,
        api_client: Optional[TUIApiClient] = None,
    ):
        """
        Initialize REPL.

        Args:
            console: Rich Console for output
            session_manager: Session manager
            copilot: MultiScenarioCopilot instance
            theme: Color theme
            api_client: API client for server communication
        """
        self.console = console
        self.session_manager = session_manager
        self.copilot = copilot
        self.theme = theme
        self.api_client = api_client or TUIApiClient()

        # UI Components
        self.scenario_panel = ScenarioPanel(theme)
        self.dialogue_panel = DialoguePanel(theme)
        self.help_panel = HelpPanel(theme)
        self.status_bar = StatusBar(theme)

        # Command handler
        self.command_handler = CommandHandler(self)

        # State
        self.running = False

    def run(self):
        """Main REPL entry point."""
        self.running = True

        while self.running:
            try:
                # Show status bar
                self.console.print(self.status_bar.render())

                # Get input
                user_input = self._get_input()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    self._handle_command(user_input)
                else:
                    self._process_query(user_input)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use /exit to quit[/yellow]")

            except EOFError:
                self.running = False

            except Exception as e:
                logger.exception("Error in REPL loop")
                self.console.print(format_error(e, "Unexpected error"))

    def _get_input(self) -> str:
        """Get user input with prompt."""
        try:
            prompt_text = self._build_prompt()
            user_input = Prompt.ask(prompt_text)
            return user_input.strip()
        except KeyboardInterrupt:
            raise
        except Exception:
            return ""

    def _build_prompt(self) -> str:
        """Build the prompt string."""
        scenario = self.scenario_panel.current_scenario
        if scenario:
            info = self.scenario_panel.get_current_scenario()
            name = info["name"] if info else scenario
            return f"[bold green]{name}[/] > "
        return "[bold cyan]codegraph[/] > "

    def _handle_command(self, input_str: str):
        """Handle a command input."""
        # Parse command
        parts = input_str[1:].split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1].split() if len(parts) > 1 else []

        self.command_handler.handle(command, args)

    def _process_query(self, query: str):
        """Process a natural language query."""
        # Update status
        self.status_bar.update(is_processing=True, status_message="Thinking...")

        # Add user message
        self.session_manager.add_user_message(query)

        # Show user message
        user_panel = self.dialogue_panel.render_turn(
            role="user",
            content=query,
            is_latest=True,
        )
        self.console.print(user_panel)

        # Process with copilot
        if self.copilot:
            try:
                with self.console.status("[yellow]Processing...[/yellow]"):
                    # Get context from dialogue manager
                    dm = self.session_manager.get_dialogue_manager()
                    context = dm.get_context_for_query()

                    # Run workflow
                    result = self._run_copilot(query, context)

                    # Extract answer
                    answer = result.get("answer", "No answer available")
                    metadata = {
                        "intent": result.get("intent"),
                        "scenario_id": result.get("scenario_id"),
                        "confidence": result.get("confidence", 0),
                    }

                    # Add response
                    self.session_manager.add_assistant_message(answer, metadata)

                    # Display result
                    result_panel = format_result(result, self.theme)
                    self.console.print(result_panel)

            except Exception as e:
                logger.exception("Query processing failed")
                error_msg = f"Error: {str(e)}"
                self.session_manager.add_assistant_message(error_msg)
                self.console.print(format_error(e, "Query failed"))

        else:
            # No copilot - mock response
            response = f"[Mock response for: {query}]"
            self.session_manager.add_assistant_message(response)

            panel = self.dialogue_panel.render_turn(
                role="assistant",
                content=response,
                is_latest=True,
            )
            self.console.print(panel)

        # Update status
        dm = self.session_manager.get_dialogue_manager()
        self.status_bar.update(
            is_processing=False,
            message_count=len(dm),
            status_message="Ready",
        )

    def _run_copilot(self, query: str, context: Dict) -> Dict:
        """Run the copilot workflow."""
        if hasattr(self.copilot, "run"):
            return self.copilot.run(query, context=context)
        elif hasattr(self.copilot, "invoke"):
            return self.copilot.invoke({"question": query, **context})
        else:
            raise ValueError("Copilot has no run or invoke method")

    def show_welcome(self):
        """Show welcome message."""
        from . import app as app_module

        version = getattr(app_module, "__version__", "unknown")
        welcome = Panel(
            f"[bold cyan]CodeGraph Interactive Console[/bold cyan] [dim]v{version}[/dim]\n\n"
            "Ask questions about your codebase using natural language.\n"
            "Type [bold]/help[/bold] for commands, [bold]/scenarios[/bold] to see available scenarios.\n"
            "Press [bold]Ctrl+C[/bold] to cancel, [bold]/exit[/bold] to quit.",
            title="Welcome",
            border_style=self.theme.border,
        )
        self.console.print(welcome)
        self.console.print()

    def show_quick_help(self):
        """Show quick help line."""
        self.console.print(self.help_panel.render_quick_help())
