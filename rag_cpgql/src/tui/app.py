"""
RAG-CPGQL Terminal User Interface Application.

Main entry point for the interactive console.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

from .repl import TUIRepl
from .managers.session_manager import SessionManager
from .persistence.session_store import SessionStore
from .utils.themes import Theme, DEFAULT_THEME, get_theme

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)
logger = logging.getLogger(__name__)


class SimpleCopilotWrapper:
    """Wrapper to make simple workflow compatible with TUI."""

    def __init__(self, workflow):
        self.workflow = workflow

    def run(self, query: str, context: dict = None) -> dict:
        """Run the simple workflow."""
        try:
            result = self.workflow.invoke({"question": query})
            return {
                "answer": result.get("answer", "No answer available"),
                "intent": result.get("intent", "unknown"),
                "scenario_id": "simple",
                "confidence": 0.7,
                "evidence": result.get("retrieved_functions", []),
            }
        except Exception as e:
            return {
                "answer": f"Error processing query: {e}",
                "intent": "error",
                "scenario_id": "simple",
                "confidence": 0,
                "evidence": [],
            }


class TUIApplication:
    """
    Main TUI Application class.

    Entry point for the interactive terminal interface.
    Coordinates all TUI components.
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        theme: str = "default",
        session_dir: Optional[Path] = None,
    ):
        """
        Initialize TUI application.

        Args:
            config_path: Path to config.yaml
            theme: Theme name (default, dark, light)
            session_dir: Directory for session storage
        """
        # Initialize Rich console
        self.console = Console()

        # Windows UTF-8 support
        if sys.platform == "win32":
            try:
                sys.stdout.reconfigure(encoding="utf-8")
            except Exception:
                pass

        # Load theme
        self.theme = get_theme(theme)

        # Initialize session management
        store = SessionStore(base_dir=session_dir)
        self.session_manager = SessionManager(store=store, auto_save=True)

        # Initialize copilot (lazy load to avoid import issues)
        self.copilot = None
        self._config_path = config_path

        # REPL will be created when run() is called
        self.repl: Optional[TUIRepl] = None

    def _init_copilot(self):
        """Initialize the MultiScenarioCopilot or fallback to simple mode."""
        # First try the full MultiScenarioCopilot
        try:
            from src.workflow.multi_scenario_workflow import MultiScenarioCopilot

            self.console.print("[dim]Initializing copilot...[/dim]")
            self.copilot = MultiScenarioCopilot()
            self.console.print("[green]Copilot ready[/green]")
            return

        except ImportError as e:
            missing_module = str(e).split("'")[-2] if "'" in str(e) else str(e)
            logger.warning(f"Could not import MultiScenarioCopilot: {e}")
            self.console.print(
                f"[yellow]Missing dependency: {missing_module}[/yellow]"
            )

        except Exception as e:
            logger.error(f"Failed to initialize copilot: {e}")
            self.console.print(
                f"[red]Error initializing copilot: {e}[/red]"
            )

        # Try fallback to simple DuckDB-only workflow
        try:
            from src.workflow.langgraph_workflow_simple import create_simple_workflow

            self.console.print("[dim]Trying simple workflow (DuckDB only)...[/dim]")
            self.copilot = SimpleCopilotWrapper(create_simple_workflow())
            self.console.print("[green]Simple workflow ready[/green]")
            return

        except Exception as e:
            logger.warning(f"Simple workflow also failed: {e}")

        # Final fallback to demo mode
        self.console.print(
            "[yellow]Running in demo mode.[/yellow]\n"
            "[dim]To enable full functionality, install: pip install chromadb[/dim]"
        )
        self.copilot = None

    def run(self, session_id: Optional[str] = None):
        """
        Start the TUI application.

        Args:
            session_id: Optional session ID to restore
        """
        try:
            # Initialize copilot
            self._init_copilot()

            # Create or restore session
            if session_id:
                try:
                    self.session_manager.load_session(session_id)
                    self.console.print(f"[green]Restored session: {session_id}[/green]")
                except Exception as e:
                    logger.warning(f"Could not restore session: {e}")
                    self.session_manager.new_session()
            else:
                self.session_manager.new_session()

            # Create REPL
            self.repl = TUIRepl(
                console=self.console,
                session_manager=self.session_manager,
                copilot=self.copilot,
                theme=self.theme,
            )

            # Update status bar with session info
            info = self.session_manager.get_session_info()
            if info:
                self.repl.status_bar.update(
                    session_id=info["session_id"],
                    scenario=info.get("current_scenario"),
                    message_count=info.get("message_count", 0),
                )

            # Show welcome
            self.repl.show_welcome()

            # Run REPL
            self.repl.run()

        except KeyboardInterrupt:
            self.console.print("\n[cyan]Interrupted. Goodbye![/cyan]")

        except Exception as e:
            logger.exception("Application error")
            self.console.print(f"[red]Fatal error: {e}[/red]")
            sys.exit(1)

        finally:
            # Save session on exit
            try:
                if self.session_manager.current_session:
                    self.session_manager.save_session()
            except Exception:
                pass


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="RAG-CPGQL Interactive Console",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.tui.app                    # Start new session
  python -m src.tui.app --session my_id    # Restore session
  python -m src.tui.app --theme dark       # Use dark theme
        """,
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to config.yaml",
        default=None,
    )

    parser.add_argument(
        "--session",
        type=str,
        help="Session ID to restore",
        default=None,
    )

    parser.add_argument(
        "--theme",
        type=str,
        choices=["default", "dark", "light"],
        default="default",
        help="Color theme",
    )

    parser.add_argument(
        "--session-dir",
        type=Path,
        help="Directory for session storage",
        default=None,
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Configure debug logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create and run application
    app = TUIApplication(
        config_path=args.config,
        theme=args.theme,
        session_dir=args.session_dir,
    )

    app.run(session_id=args.session)


if __name__ == "__main__":
    main()
