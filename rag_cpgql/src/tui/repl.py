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
            "demo": self._cmd_demo,
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
        """View/edit config."""
        if not args:
            # Show config summary
            self.repl.console.print("[bold]Configuration:[/bold]")
            self.repl.console.print("[dim]Use /config <section> to view details[/dim]")
            self.repl.console.print("[dim]Sections: llm, retrieval, analysis, generation[/dim]")
        else:
            self.repl.console.print(f"[dim]Config section: {args[0]}[/dim]")
            self.repl.console.print("[yellow]Config editing not yet implemented[/yellow]")
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
    ):
        """
        Initialize REPL.

        Args:
            console: Rich Console for output
            session_manager: Session manager
            copilot: MultiScenarioCopilot instance
            theme: Color theme
        """
        self.console = console
        self.session_manager = session_manager
        self.copilot = copilot
        self.theme = theme

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
        return "[bold cyan]rag-cpgql[/] > "

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
        welcome = Panel(
            "[bold cyan]RAG-CPGQL Interactive Console[/bold cyan]\n\n"
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
