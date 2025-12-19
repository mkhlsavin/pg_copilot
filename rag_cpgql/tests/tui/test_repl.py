"""
Tests for TUI REPL (Read-Eval-Print Loop).

Tests for command handling, query processing, and session management.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from rich.console import Console


class MockSessionManager:
    """Mock session manager for testing."""

    def __init__(self):
        self.current_session = MagicMock()
        self.current_session.current_scenario = "01"
        self._dialogue_manager = MagicMock()
        self._dialogue_manager.get_history.return_value = []
        self._dialogue_manager.get_context_for_query.return_value = {}
        self._dialogue_manager.__len__ = MagicMock(return_value=0)

    def get_dialogue_manager(self):
        return self._dialogue_manager

    def add_user_message(self, message: str):
        pass

    def add_assistant_message(self, message: str, metadata: dict = None):
        pass

    def set_scenario(self, scenario_id: str):
        pass

    def save_session(self):
        return "test_session_id"

    def load_session(self, session_id: str):
        pass

    def list_sessions(self):
        return []


class MockTheme:
    """Mock theme for testing."""
    border = "blue"
    accent = "cyan"
    highlight = "green"


class TestCommandHandler:
    """Tests for CommandHandler class."""

    @pytest.fixture
    def mock_repl(self):
        """Create mock REPL with dependencies."""
        repl = MagicMock()
        repl.console = Console(force_terminal=True, width=80)
        repl.session_manager = MockSessionManager()
        repl.copilot = None
        repl.theme = MockTheme()
        repl.scenario_panel = MagicMock()
        repl.dialogue_panel = MagicMock()
        repl.help_panel = MagicMock()
        repl.status_bar = MagicMock()
        repl.running = True
        return repl

    def test_handle_unknown_command(self, mock_repl):
        """Test handling of unknown command."""
        from src.tui.repl import CommandHandler

        handler = CommandHandler(mock_repl)

        result = handler.handle("unknown_cmd", [])

        assert result is True  # Command was "handled" (error printed)

    def test_handle_help_command(self, mock_repl):
        """Test /help command."""
        from src.tui.repl import CommandHandler

        mock_repl.help_panel.render.return_value = MagicMock()

        handler = CommandHandler(mock_repl)

        result = handler.handle("help", [])

        assert result is True
        mock_repl.help_panel.render.assert_called_once()

    def test_handle_help_alias(self, mock_repl):
        """Test /h as alias for /help."""
        from src.tui.repl import CommandHandler

        mock_repl.help_panel.render.return_value = MagicMock()

        handler = CommandHandler(mock_repl)

        result = handler.handle("h", [])

        assert result is True
        mock_repl.help_panel.render.assert_called_once()

    def test_handle_scenarios_command(self, mock_repl):
        """Test /scenarios command."""
        from src.tui.repl import CommandHandler

        mock_repl.scenario_panel.render.return_value = MagicMock()

        handler = CommandHandler(mock_repl)

        result = handler.handle("scenarios", [])

        assert result is True
        mock_repl.scenario_panel.render.assert_called_once()

    def test_handle_select_command(self, mock_repl):
        """Test /select command."""
        from src.tui.repl import CommandHandler

        mock_repl.scenario_panel.select_scenario.return_value = (True, "Selected")

        handler = CommandHandler(mock_repl)

        result = handler.handle("select", ["01"])

        assert result is True
        mock_repl.scenario_panel.select_scenario.assert_called_with("01")

    def test_handle_select_no_args(self, mock_repl):
        """Test /select without arguments."""
        from src.tui.repl import CommandHandler

        handler = CommandHandler(mock_repl)

        result = handler.handle("select", [])

        assert result is True
        # Should print usage message

    def test_handle_history_command(self, mock_repl):
        """Test /history command."""
        from src.tui.repl import CommandHandler

        mock_repl.dialogue_panel.render_history.return_value = []

        handler = CommandHandler(mock_repl)

        result = handler.handle("history", [])

        assert result is True

    def test_handle_history_with_limit(self, mock_repl):
        """Test /history with custom limit."""
        from src.tui.repl import CommandHandler

        mock_repl.dialogue_panel.render_history.return_value = []
        mock_dm = mock_repl.session_manager.get_dialogue_manager()
        mock_dm.get_history.return_value = [MagicMock()] * 5

        handler = CommandHandler(mock_repl)

        result = handler.handle("history", ["5"])

        assert result is True
        mock_dm.get_history.assert_called_with(limit=5)

    def test_handle_save_command(self, mock_repl):
        """Test /save command."""
        from src.tui.repl import CommandHandler

        handler = CommandHandler(mock_repl)

        result = handler.handle("save", [])

        assert result is True

    def test_handle_load_command_no_args(self, mock_repl):
        """Test /load command without session ID lists sessions."""
        from src.tui.repl import CommandHandler

        handler = CommandHandler(mock_repl)

        result = handler.handle("load", [])

        assert result is True

    def test_handle_clear_command(self, mock_repl):
        """Test /clear command."""
        from src.tui.repl import CommandHandler

        handler = CommandHandler(mock_repl)

        result = handler.handle("clear", [])

        assert result is True

    def test_handle_exit_command(self, mock_repl):
        """Test /exit command."""
        from src.tui.repl import CommandHandler

        handler = CommandHandler(mock_repl)

        result = handler.handle("exit", [])

        assert result is True
        assert mock_repl.running is False

    def test_handle_quit_alias(self, mock_repl):
        """Test /quit as alias for /exit."""
        from src.tui.repl import CommandHandler

        handler = CommandHandler(mock_repl)

        result = handler.handle("quit", [])

        assert result is True
        assert mock_repl.running is False

    def test_handle_q_alias(self, mock_repl):
        """Test /q as alias for /exit."""
        from src.tui.repl import CommandHandler

        handler = CommandHandler(mock_repl)

        result = handler.handle("q", [])

        assert result is True
        assert mock_repl.running is False

    def test_handle_command_exception(self, mock_repl):
        """Test handling of command exception."""
        from src.tui.repl import CommandHandler

        mock_repl.help_panel.render.side_effect = Exception("Test error")

        handler = CommandHandler(mock_repl)

        result = handler.handle("help", [])

        assert result is True  # Error was caught and handled


class TestTUIRepl:
    """Tests for TUIRepl class."""

    @pytest.fixture
    def mock_repl(self):
        """Create TUIRepl with mocked dependencies."""
        console = Console(force_terminal=True, width=80, record=True)
        session_manager = MockSessionManager()
        theme = MockTheme()

        with patch("src.tui.repl.ScenarioPanel"):
            with patch("src.tui.repl.DialoguePanel"):
                with patch("src.tui.repl.HelpPanel"):
                    with patch("src.tui.repl.StatusBar"):
                        from src.tui.repl import TUIRepl

                        repl = TUIRepl(
                            console=console,
                            session_manager=session_manager,
                            copilot=None,
                            theme=theme,
                        )
                        return repl

    def test_repl_initialization(self, mock_repl):
        """Test REPL initializes correctly."""
        assert mock_repl.running is False
        assert mock_repl.copilot is None
        assert mock_repl.command_handler is not None

    def test_build_prompt_with_scenario(self, mock_repl):
        """Test prompt building with active scenario."""
        mock_repl.scenario_panel.current_scenario = "01"
        mock_repl.scenario_panel.get_current_scenario.return_value = {"name": "Security"}

        prompt = mock_repl._build_prompt()

        assert "Security" in prompt

    def test_build_prompt_without_scenario(self, mock_repl):
        """Test prompt building without active scenario."""
        mock_repl.scenario_panel.current_scenario = None

        prompt = mock_repl._build_prompt()

        assert "codegraph" in prompt

    def test_handle_command_parsing(self, mock_repl):
        """Test command parsing from input."""
        mock_repl.command_handler = MagicMock()
        mock_repl.command_handler.handle.return_value = True

        mock_repl._handle_command("/help topic")

        mock_repl.command_handler.handle.assert_called_once_with("help", ["topic"])

    def test_handle_command_no_args(self, mock_repl):
        """Test command parsing without arguments."""
        mock_repl.command_handler = MagicMock()
        mock_repl.command_handler.handle.return_value = True

        mock_repl._handle_command("/help")

        mock_repl.command_handler.handle.assert_called_once_with("help", [])

    def test_process_query_no_copilot(self, mock_repl):
        """Test query processing without copilot."""
        mock_repl.dialogue_panel.render_turn.return_value = MagicMock()

        mock_repl._process_query("test query")

        # Should add user message
        # Mock response should be displayed

    def test_show_welcome(self, mock_repl):
        """Test welcome message display."""
        # app_module is imported inside show_welcome as: from . import app as app_module
        # Patch the module that gets imported
        with patch("src.tui.app.__version__", "1.0.0"):
            mock_repl.show_welcome()

        # Welcome should be printed (captured in console)


class TestCommandAliases:
    """Tests for command aliases."""

    def test_all_aliases_registered(self):
        """Test that all command aliases are properly registered."""
        mock_repl = MagicMock()

        from src.tui.repl import CommandHandler

        handler = CommandHandler(mock_repl)

        # Check main commands
        assert "help" in handler._commands
        assert "h" in handler._commands
        assert "scenarios" in handler._commands
        assert "select" in handler._commands
        assert "history" in handler._commands
        assert "save" in handler._commands
        assert "load" in handler._commands
        assert "config" in handler._commands
        assert "stat" in handler._commands
        assert "stats" in handler._commands
        assert "query" in handler._commands
        assert "sql" in handler._commands
        assert "demo" in handler._commands
        assert "review" in handler._commands
        assert "project" in handler._commands
        assert "proj" in handler._commands
        assert "clear" in handler._commands
        assert "exit" in handler._commands
        assert "quit" in handler._commands
        assert "q" in handler._commands

    def test_aliases_point_to_same_function(self):
        """Test that aliases point to the same handler function."""
        mock_repl = MagicMock()

        from src.tui.repl import CommandHandler

        handler = CommandHandler(mock_repl)

        # Check alias pairs - compare underlying functions since bound methods
        # are different objects but point to the same function
        assert handler._commands["help"].__func__ is handler._commands["h"].__func__
        assert handler._commands["exit"].__func__ is handler._commands["quit"].__func__
        assert handler._commands["exit"].__func__ is handler._commands["q"].__func__
        assert handler._commands["stat"].__func__ is handler._commands["stats"].__func__
        assert handler._commands["query"].__func__ is handler._commands["sql"].__func__
        assert handler._commands["project"].__func__ is handler._commands["proj"].__func__
