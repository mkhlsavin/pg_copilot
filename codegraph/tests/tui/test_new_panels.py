"""
Tests for new TUI panels: group, import, auth, session, health, project, extended_stats.
"""

import pytest
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch
from rich.console import Console
from rich.panel import Panel


def render_to_string(renderable) -> str:
    """Render a Rich renderable to string for testing."""
    console = Console(file=StringIO(), force_terminal=True, width=120)
    console.print(renderable)
    return console.file.getvalue()


class MockTheme:
    """Mock theme for testing."""
    border = "blue"
    accent = "cyan"
    highlight = "green"


class MockApiClient:
    """Mock API client for testing."""

    def __init__(self):
        self._token = "test_token"

        # Groups
        self.list_groups = AsyncMock(return_value={
            "groups": [
                {"id": "g1", "name": "test-group", "description": "Test", "project_count": 2}
            ],
            "total": 1,
        })
        self.create_group = AsyncMock(return_value={
            "id": "g2", "name": "new-group", "description": None
        })
        self.delete_group = AsyncMock(return_value=True)
        self.list_group_users = AsyncMock(return_value={
            "users": [
                {"username": "user1", "role": "admin", "created_at": "2024-01-01"}
            ],
            "total": 1,
        })
        self.add_group_user = AsyncMock(return_value={
            "username": "user2", "role": "editor"
        })
        self.remove_group_user = AsyncMock(return_value=True)

        # Import
        self.start_import = AsyncMock(return_value={
            "job_id": "job-123", "status": "pending"
        })
        self.get_import_status = AsyncMock(return_value={
            "job_id": "job-123",
            "project_name": "test-project",
            "status": "running",
            "overall_progress": 50,
            "current_step": "joern_import",
        })
        self.list_import_jobs = AsyncMock(return_value=[
            {"job_id": "job-123", "project_name": "test", "status": "completed", "overall_progress": 100}
        ])
        self.cancel_import = AsyncMock(return_value={"status": "cancelled"})

        # Auth
        self.login = AsyncMock(return_value={
            "access_token": "token123", "expires_in": 1800
        })
        self.logout = AsyncMock(return_value=True)
        self.get_current_user = AsyncMock(return_value={
            "username": "testuser", "email": "test@test.com", "role": "admin", "is_active": True
        })
        self.list_api_keys = AsyncMock(return_value=[
            {"id": "key1", "name": "test-key", "prefix": "rgc_", "is_revoked": False}
        ])
        self.create_api_key = AsyncMock(return_value={
            "id": "key2", "name": "new-key", "key": "rgc_secret123"
        })
        self.revoke_api_key = AsyncMock(return_value=True)

        # Sessions
        self.list_sessions = AsyncMock(return_value={
            "items": [
                {"id": "sess1", "current_scenario": "01", "turn_count": 5, "updated_at": "2024-01-01 12:00:00"}
            ],
            "total": 1, "page": 1
        })
        self.get_session = AsyncMock(return_value={
            "id": "sess1",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01",
            "current_scenario": "01",
            "dialogue_turns": [
                {"role": "user", "content": "Hello", "timestamp": "2024-01-01 12:00:00"},
                {"role": "assistant", "content": "Hi!", "timestamp": "2024-01-01 12:00:01"},
            ]
        })
        self.delete_session = AsyncMock(return_value=True)

        # Health
        self.get_health = AsyncMock(return_value={
            "status": "healthy",
            "version": "1.0.0",
            "uptime_seconds": 3600,
            "components": {
                "database": {"status": "healthy"},
                "llm": {"status": "healthy", "provider": "openai"},
                "joern": {"status": "unavailable"},
            }
        })

        # Stats
        self.get_stats = AsyncMock(return_value={
            "total_requests": 1000,
            "active_sessions": 5,
            "active_jobs": 2,
            "cache_hit_rate": 75.5,
            "avg_response_time_ms": 250,
        })
        self.get_scenario_stats = AsyncMock(return_value={
            "total_queries": 500,
            "scenarios": {
                "01": {"total": 100, "success": 95},
                "02": {"total": 80, "success": 75},
            }
        })
        self.get_performance_stats = AsyncMock(return_value={
            "avg_response_time_ms": 250,
            "p50_response_time_ms": 200,
            "p95_response_time_ms": 500,
            "p99_response_time_ms": 1000,
            "requests_per_minute": 10.5,
            "error_rate": 0.5,
        })

        # Projects
        self.list_projects = AsyncMock(return_value={
            "projects": [
                {"id": "p1", "name": "test-project", "language": "python", "is_active": True}
            ]
        })
        self.create_project = AsyncMock(return_value={
            "id": "p2", "name": "new-project"
        })

    @property
    def is_authenticated(self):
        return self._token is not None

    def clear_token(self):
        self._token = None


# ============================================================================
# GroupPanel Tests
# ============================================================================

class TestGroupPanel:
    """Tests for GroupPanel component."""

    @pytest.fixture
    def mock_api(self):
        return MockApiClient()

    @pytest.fixture
    def panel(self, mock_api):
        from src.tui.components.group_panel import GroupPanel
        return GroupPanel(theme=MockTheme(), api_client=mock_api)

    def test_render_help(self, panel):
        """Test help rendering."""
        result = panel.render_help()
        assert isinstance(result, Panel)
        assert "Group Management" in str(result.title)

    @pytest.mark.asyncio
    async def test_list_groups(self, panel, mock_api):
        """Test listing groups."""
        result = await panel.list_groups()
        mock_api.list_groups.assert_called_once()
        assert isinstance(result, Panel)
        rendered = render_to_string(result)
        assert "test-group" in rendered

    @pytest.mark.asyncio
    async def test_create_group(self, panel, mock_api):
        """Test creating a group."""
        result = await panel.create_group("new-group", "Description")
        mock_api.create_group.assert_called_once_with("new-group", "Description")
        assert isinstance(result, Panel)

    @pytest.mark.asyncio
    async def test_delete_group(self, panel, mock_api):
        """Test deleting a group."""
        result = await panel.delete_group("test-group")
        mock_api.list_groups.assert_called()
        mock_api.delete_group.assert_called_once()
        assert isinstance(result, Panel)

    @pytest.mark.asyncio
    async def test_list_users(self, panel, mock_api):
        """Test listing group users."""
        result = await panel.list_users("test-group")
        mock_api.list_group_users.assert_called()
        assert isinstance(result, Panel)

    @pytest.mark.asyncio
    async def test_add_user_invalid_role(self, panel, mock_api):
        """Test adding user with invalid role."""
        result = await panel.add_user("test-group", "user1", "invalid_role")
        rendered = render_to_string(result)
        assert "Invalid role" in rendered


# ============================================================================
# ImportPanel Tests
# ============================================================================

class TestImportPanel:
    """Tests for ImportPanel component."""

    @pytest.fixture
    def mock_api(self):
        return MockApiClient()

    @pytest.fixture
    def panel(self, mock_api):
        from src.tui.components.import_panel import ImportPanel
        return ImportPanel(theme=MockTheme(), api_client=mock_api)

    def test_render_help(self, panel):
        """Test help rendering."""
        result = panel.render_help()
        assert isinstance(result, Panel)
        assert "Import Management" in str(result.title)

    @pytest.mark.asyncio
    async def test_start_import(self, panel, mock_api):
        """Test starting import."""
        result = await panel.start_import("/path/to/code")
        mock_api.start_import.assert_called_once()
        assert isinstance(result, Panel)
        rendered = render_to_string(result)
        assert "job-123" in rendered

    @pytest.mark.asyncio
    async def test_get_status(self, panel, mock_api):
        """Test getting import status."""
        result = await panel.get_status("job-123")
        mock_api.get_import_status.assert_called_once_with("job-123")
        assert isinstance(result, Panel)
        rendered = render_to_string(result)
        assert "running" in rendered.lower()

    @pytest.mark.asyncio
    async def test_list_jobs(self, panel, mock_api):
        """Test listing jobs."""
        result = await panel.list_jobs()
        mock_api.list_import_jobs.assert_called_once()
        assert isinstance(result, Panel)

    @pytest.mark.asyncio
    async def test_cancel_job(self, panel, mock_api):
        """Test canceling job."""
        result = await panel.cancel_job("job-123")
        mock_api.cancel_import.assert_called_once_with("job-123")
        assert isinstance(result, Panel)


# ============================================================================
# AuthPanel Tests
# ============================================================================

class TestAuthPanel:
    """Tests for AuthPanel component."""

    @pytest.fixture
    def mock_api(self):
        return MockApiClient()

    @pytest.fixture
    def panel(self, mock_api):
        from src.tui.components.auth_panel import AuthPanel
        return AuthPanel(theme=MockTheme(), api_client=mock_api)

    def test_render_help(self, panel):
        """Test help rendering."""
        result = panel.render_help()
        assert isinstance(result, Panel)
        assert "Authentication" in str(result.title)

    @pytest.mark.asyncio
    async def test_logout(self, panel, mock_api):
        """Test logout."""
        result = await panel.logout()
        mock_api.logout.assert_called_once()
        assert isinstance(result, Panel)
        rendered = render_to_string(result)
        assert "logged out" in rendered.lower()

    @pytest.mark.asyncio
    async def test_get_current_user(self, panel, mock_api):
        """Test getting current user."""
        result = await panel.get_current_user()
        mock_api.get_current_user.assert_called_once()
        assert isinstance(result, Panel)
        rendered = render_to_string(result)
        assert "testuser" in rendered

    @pytest.mark.asyncio
    async def test_list_api_keys(self, panel, mock_api):
        """Test listing API keys."""
        result = await panel.list_api_keys()
        mock_api.list_api_keys.assert_called_once()
        assert isinstance(result, Panel)

    @pytest.mark.asyncio
    async def test_create_api_key(self, panel, mock_api):
        """Test creating API key."""
        result = await panel.create_api_key("new-key")
        mock_api.create_api_key.assert_called_once_with("new-key", 365)
        assert isinstance(result, Panel)
        rendered = render_to_string(result)
        assert "rgc_secret123" in rendered

    @pytest.mark.asyncio
    async def test_revoke_api_key(self, panel, mock_api):
        """Test revoking API key."""
        result = await panel.revoke_api_key("key1")
        mock_api.revoke_api_key.assert_called_once_with("key1")
        assert isinstance(result, Panel)


# ============================================================================
# SessionPanel Tests
# ============================================================================

class TestSessionPanel:
    """Tests for SessionPanel component."""

    @pytest.fixture
    def mock_api(self):
        return MockApiClient()

    @pytest.fixture
    def panel(self, mock_api):
        from src.tui.components.session_panel import SessionPanel
        return SessionPanel(theme=MockTheme(), api_client=mock_api)

    def test_render_help(self, panel):
        """Test help rendering."""
        result = panel.render_help()
        assert isinstance(result, Panel)
        assert "Session Management" in str(result.title)

    @pytest.mark.asyncio
    async def test_list_sessions(self, panel, mock_api):
        """Test listing sessions."""
        result = await panel.list_sessions()
        mock_api.list_sessions.assert_called_once()
        assert isinstance(result, Panel)

    @pytest.mark.asyncio
    async def test_delete_session(self, panel, mock_api):
        """Test deleting session."""
        result = await panel.delete_session("sess1")
        mock_api.delete_session.assert_called_once_with("sess1")
        assert isinstance(result, Panel)

    def test_format_markdown(self, panel):
        """Test markdown formatting."""
        session = {
            "id": "sess1",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01",
            "current_scenario": "01",
            "dialogue_turns": [
                {"role": "user", "content": "Hello", "timestamp": "2024-01-01"},
            ]
        }
        result = panel._format_markdown(session)
        assert "# Session Export" in result
        assert "Hello" in result


# ============================================================================
# HealthPanel Tests
# ============================================================================

class TestHealthPanel:
    """Tests for HealthPanel component."""

    @pytest.fixture
    def mock_api(self):
        return MockApiClient()

    @pytest.fixture
    def panel(self, mock_api):
        from src.tui.components.health_panel import HealthPanel
        return HealthPanel(theme=MockTheme(), api_client=mock_api)

    @pytest.mark.asyncio
    async def test_render(self, panel, mock_api):
        """Test rendering health panel."""
        result = await panel.render()
        mock_api.get_health.assert_called_once()
        assert isinstance(result, Panel)
        rendered = render_to_string(result)
        assert "healthy" in rendered.lower()

    def test_format_uptime(self, panel):
        """Test uptime formatting."""
        assert panel._format_uptime(30) == "30s"
        assert panel._format_uptime(120) == "2m"
        assert panel._format_uptime(7200) == "2.0h"
        assert panel._format_uptime(172800) == "2.0d"


# ============================================================================
# ExtendedStatsPanel Tests
# ============================================================================

class TestExtendedStatsPanel:
    """Tests for ExtendedStatsPanel component."""

    @pytest.fixture
    def mock_api(self):
        return MockApiClient()

    @pytest.fixture
    def panel(self, mock_api):
        from src.tui.components.extended_stats_panel import ExtendedStatsPanel
        return ExtendedStatsPanel(theme=MockTheme(), api_client=mock_api)

    @pytest.mark.asyncio
    async def test_get_scenario_stats(self, panel, mock_api):
        """Test getting scenario stats."""
        result = await panel.get_scenario_stats()
        mock_api.get_scenario_stats.assert_called_once()
        assert isinstance(result, Panel)

    @pytest.mark.asyncio
    async def test_get_performance_stats(self, panel, mock_api):
        """Test getting performance stats."""
        result = await panel.get_performance_stats()
        mock_api.get_performance_stats.assert_called_once()
        assert isinstance(result, Panel)

    @pytest.mark.asyncio
    async def test_get_api_stats(self, panel, mock_api):
        """Test getting API stats."""
        result = await panel.get_api_stats()
        mock_api.get_stats.assert_called_once()
        assert isinstance(result, Panel)


# ============================================================================
# ProjectPanel Tests
# ============================================================================

class TestProjectPanel:
    """Tests for ProjectPanel component."""

    @pytest.fixture
    def mock_api(self):
        return MockApiClient()

    @pytest.fixture
    def panel(self, mock_api):
        from src.tui.components.project_panel import ProjectPanel
        return ProjectPanel(theme=MockTheme(), api_client=mock_api)

    @pytest.mark.asyncio
    async def test_create_project(self, panel, mock_api):
        """Test creating project."""
        result = await panel.create_project("new-project", "test-group")
        mock_api.list_groups.assert_called()
        mock_api.create_project.assert_called()
        assert isinstance(result, Panel)


# ============================================================================
# Help Panel - New Commands Tests
# ============================================================================

class TestHelpPanelNewCommands:
    """Tests for new commands in help panel."""

    def test_new_commands_defined(self):
        """Test that all new commands are defined."""
        from src.tui.components.help_panel import COMMANDS

        new_commands = [
            "/group",
            "/import",
            "/auth",
            "/session",
            "/health",
        ]

        for cmd in new_commands:
            assert cmd in COMMANDS, f"New command {cmd} not defined"

    def test_new_commands_structure(self):
        """Test that new commands have required fields."""
        from src.tui.components.help_panel import COMMANDS

        new_commands = ["/group", "/import", "/auth", "/session", "/health"]

        for cmd in new_commands:
            info = COMMANDS[cmd]
            assert "args" in info, f"{cmd} missing 'args' field"
            assert "description" in info, f"{cmd} missing 'description' field"
            assert "examples" in info, f"{cmd} missing 'examples' field"
            assert len(info["examples"]) >= 1, f"{cmd} needs at least one example"

    def test_group_command_examples(self):
        """Test /group command has proper examples."""
        from src.tui.components.help_panel import COMMANDS

        group_cmd = COMMANDS["/group"]
        examples_str = " ".join(group_cmd["examples"])

        assert "list" in examples_str
        assert "create" in examples_str
        assert "delete" in examples_str
        assert "users" in examples_str

    def test_import_command_examples(self):
        """Test /import command has proper examples."""
        from src.tui.components.help_panel import COMMANDS

        import_cmd = COMMANDS["/import"]
        examples_str = " ".join(import_cmd["examples"])

        assert "start" in examples_str
        assert "status" in examples_str
        assert "jobs" in examples_str

    def test_auth_command_examples(self):
        """Test /auth command has proper examples."""
        from src.tui.components.help_panel import COMMANDS

        auth_cmd = COMMANDS["/auth"]
        examples_str = " ".join(auth_cmd["examples"])

        assert "login" in examples_str
        assert "logout" in examples_str
        assert "api-keys" in examples_str

    def test_stat_command_updated(self):
        """Test /stat command has new subcommands."""
        from src.tui.components.help_panel import COMMANDS

        stat_cmd = COMMANDS["/stat"]
        examples_str = " ".join(stat_cmd["examples"])

        assert "scenarios" in examples_str
        assert "performance" in examples_str

    def test_project_command_updated(self):
        """Test /project command has new subcommands."""
        from src.tui.components.help_panel import COMMANDS

        project_cmd = COMMANDS["/project"]

        assert "info" in project_cmd["args"]
        assert "create" in project_cmd["args"]
