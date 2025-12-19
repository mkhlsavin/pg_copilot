"""
CodeGraph Terminal User Interface Application.

Main entry point for the interactive console.
"""

# Version
__version__ = "1.0.0"

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel

from .repl import TUIRepl
from .managers.session_manager import SessionManager
from .persistence.session_store import SessionStore
from .utils.themes import Theme, DEFAULT_THEME, get_theme
from .api_client import TUIApiClient, APIConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)
logger = logging.getLogger(__name__)


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

        # Initialize API client
        api_config = APIConfig.from_config(config_path)
        self.api_client = TUIApiClient(api_config)

        # REPL will be created when run() is called
        self.repl: Optional[TUIRepl] = None

    def _validate_config(self) -> bool:
        """
        Validate configuration and environment variables.

        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            from src.config.config_validator import ConfigValidator

            validator = ConfigValidator(self._config_path)
            result = validator.validate()

            # Show provider info
            provider = result.info.get("llm_provider", "unknown")
            self.console.print(f"[dim]LLM Provider: {provider}[/dim]")

            # Show warnings
            for warning in result.warnings:
                self.console.print(f"[yellow]Warning: {warning}[/yellow]")

            # Show errors
            if result.errors:
                error_text = "\n".join(f"  - {e}" for e in result.errors)
                self.console.print(
                    Panel(
                        f"[red bold]Configuration Errors[/red bold]\n\n{error_text}\n\n"
                        "[dim]Fix the errors above and restart the application.[/dim]",
                        title="[red]Configuration Invalid[/red]",
                        border_style="red",
                    )
                )
                return False

            return True

        except ImportError as e:
            logger.warning(f"Config validator not available: {e}")
            return True  # Continue without validation
        except Exception as e:
            logger.warning(f"Config validation error: {e}")
            return True  # Continue with warning

    def _init_copilot(self):
        """Initialize the MultiScenarioCopilot."""
        try:
            from src.workflow.multi_scenario_workflow import MultiScenarioCopilot

            self.console.print("[dim]Initializing copilot...[/dim]")
            self.copilot = MultiScenarioCopilot()
            self.console.print("[green]Copilot ready[/green]")

        except ImportError as e:
            missing_module = str(e).split("'")[-2] if "'" in str(e) else str(e)
            logger.warning(f"Could not import MultiScenarioCopilot: {e}")
            self.console.print(
                f"[yellow]Missing dependency: {missing_module}[/yellow]\n"
                "[dim]Running in demo mode. Install missing dependencies for full functionality.[/dim]"
            )
            self.copilot = None

        except Exception as e:
            logger.error(f"Failed to initialize copilot: {e}")
            self.console.print(
                f"[red]Error initializing copilot: {e}[/red]\n"
                "[yellow]Running in demo mode.[/yellow]"
            )
            self.copilot = None

    def run(self, session_id: Optional[str] = None):
        """
        Start the TUI application.

        Args:
            session_id: Optional session ID to restore
        """
        try:
            # Validate configuration first
            if not self._validate_config():
                self.console.print(
                    "\n[yellow]Configuration validation failed.[/yellow]\n"
                    "[dim]You can still use the TUI in demo mode, "
                    "but some features will be unavailable.[/dim]\n"
                )
                # Ask user if they want to continue
                try:
                    response = input("Continue in demo mode? [y/N]: ").strip().lower()
                    if response not in ("y", "yes"):
                        self.console.print("[cyan]Exiting...[/cyan]")
                        return
                except (KeyboardInterrupt, EOFError):
                    return

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
                api_client=self.api_client,
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
        description="CodeGraph Interactive Console",
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
