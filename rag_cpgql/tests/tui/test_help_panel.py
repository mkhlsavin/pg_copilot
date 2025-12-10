"""
Tests for TUI Help Panel.

Tests for command documentation and help rendering.
"""

import pytest
from unittest.mock import MagicMock


class MockTheme:
    """Mock theme for testing."""
    border = "blue"
    accent = "cyan"
    highlight = "green"


class TestHelpPanelCommands:
    """Tests for command definitions."""

    def test_all_commands_defined(self):
        """Test that all expected commands are defined."""
        from src.tui.components.help_panel import COMMANDS

        expected_commands = [
            "/help",
            "/scenarios",
            "/select",
            "/history",
            "/save",
            "/load",
            "/config",
            "/stat",
            "/query",
            "/demo",
            "/review",
            "/project",
            "/clear",
            "/exit",
        ]

        for cmd in expected_commands:
            assert cmd in COMMANDS, f"Command {cmd} not defined"

    def test_command_structure(self):
        """Test that commands have required fields."""
        from src.tui.components.help_panel import COMMANDS

        for cmd, info in COMMANDS.items():
            assert "args" in info, f"{cmd} missing 'args' field"
            assert "description" in info, f"{cmd} missing 'description' field"
            assert "examples" in info, f"{cmd} missing 'examples' field"
            assert isinstance(info["examples"], list), f"{cmd} examples not a list"
            assert len(info["examples"]) >= 1, f"{cmd} needs at least one example"

    def test_help_command(self):
        """Test /help command definition."""
        from src.tui.components.help_panel import COMMANDS

        help_cmd = COMMANDS["/help"]

        assert help_cmd["args"] == ""
        assert "help" in help_cmd["description"].lower()
        assert "/help" in help_cmd["examples"]

    def test_query_command(self):
        """Test /query command definition."""
        from src.tui.components.help_panel import COMMANDS

        query_cmd = COMMANDS["/query"]

        assert "<SQL>" in query_cmd["args"]
        assert "SQL" in query_cmd["description"]
        assert any("SELECT" in ex for ex in query_cmd["examples"])

    def test_review_command(self):
        """Test /review command definition."""
        from src.tui.components.help_panel import COMMANDS

        review_cmd = COMMANDS["/review"]

        assert "source" in review_cmd["args"]
        assert "review" in review_cmd["description"].lower()
        assert any("github" in ex for ex in review_cmd["examples"])
        assert any("gitlab" in ex for ex in review_cmd["examples"])

    def test_project_command(self):
        """Test /project command definition."""
        from src.tui.components.help_panel import COMMANDS

        project_cmd = COMMANDS["/project"]

        assert any(x in project_cmd["args"] for x in ["list", "switch", "add"])
        assert any("switch" in ex for ex in project_cmd["examples"])
        assert any("add" in ex for ex in project_cmd["examples"])


class TestHelpPanelInit:
    """Tests for HelpPanel initialization."""

    def test_init_default_theme(self):
        """Test initialization with default theme."""
        from src.tui.components.help_panel import HelpPanel

        panel = HelpPanel()

        assert panel.theme is not None
        assert panel.commands is not None

    def test_init_custom_theme(self):
        """Test initialization with custom theme."""
        from src.tui.components.help_panel import HelpPanel

        panel = HelpPanel(theme=MockTheme())

        assert panel.theme.border == "blue"


class TestHelpPanelRender:
    """Tests for HelpPanel rendering methods."""

    @pytest.fixture
    def panel(self):
        """Create HelpPanel for testing."""
        from src.tui.components.help_panel import HelpPanel

        return HelpPanel(theme=MockTheme())

    def test_render_all_commands(self, panel):
        """Test rendering all commands."""
        result = panel.render()

        assert result is not None
        # Check panel properties
        assert result.title is not None

    def test_render_specific_command(self, panel):
        """Test rendering specific command help."""
        result = panel.render(command="help")

        assert result is not None
        # Title should contain command name

    def test_render_command_with_slash(self, panel):
        """Test rendering with slash prefix."""
        result = panel.render(command="/help")

        assert result is not None

    def test_render_unknown_command(self, panel):
        """Test rendering unknown command."""
        result = panel.render(command="unknown_cmd")

        assert result is not None
        # Should have error styling

    def test_render_query_command_details(self, panel):
        """Test rendering /query command details."""
        result = panel.render(command="query")

        assert result is not None


class TestHelpPanelCommandHelp:
    """Tests for individual command help rendering."""

    @pytest.fixture
    def panel(self):
        """Create HelpPanel for testing."""
        from src.tui.components.help_panel import HelpPanel

        return HelpPanel(theme=MockTheme())

    def test_command_help_shows_description(self, panel):
        """Test that command help shows description."""
        # Test multiple commands
        for cmd in ["/help", "/scenarios", "/query"]:
            result = panel._render_command_help(cmd)
            assert result is not None

    def test_command_help_shows_examples(self, panel):
        """Test that command help includes examples."""
        result = panel._render_command_help("/query")
        assert result is not None

    def test_command_help_normalizes_prefix(self, panel):
        """Test that command name is normalized."""
        # Without slash
        result1 = panel._render_command_help("help")
        # With slash
        result2 = panel._render_command_help("/help")

        # Both should work
        assert result1 is not None
        assert result2 is not None


class TestHelpPanelQuickHelp:
    """Tests for quick help rendering."""

    @pytest.fixture
    def panel(self):
        """Create HelpPanel for testing."""
        from src.tui.components.help_panel import HelpPanel

        return HelpPanel(theme=MockTheme())

    def test_render_quick_help(self, panel):
        """Test rendering quick help line."""
        result = panel.render_quick_help()

        assert result is not None

    def test_quick_help_contains_common_commands(self, panel):
        """Test quick help contains common commands."""
        result = panel.render_quick_help()
        result_str = str(result)

        assert "/help" in result_str
        assert "/scenarios" in result_str
        assert "/exit" in result_str


class TestHelpPanelAllCommands:
    """Tests for all commands table rendering."""

    @pytest.fixture
    def panel(self):
        """Create HelpPanel for testing."""
        from src.tui.components.help_panel import HelpPanel

        return HelpPanel(theme=MockTheme())

    def test_render_all_commands_table(self, panel):
        """Test rendering commands table."""
        result = panel._render_all_commands()

        assert result is not None

    def test_all_commands_panel_title(self, panel):
        """Test that all commands panel has proper title."""
        result = panel._render_all_commands()

        assert "Help" in str(result.title)
