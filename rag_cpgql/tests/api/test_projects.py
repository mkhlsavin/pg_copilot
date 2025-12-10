"""
Tests for Project Manager.

Tests for ProjectManager, Project dataclass, and project switching functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile
import yaml


class TestProjectDataclass:
    """Tests for Project dataclass."""

    def test_project_creation(self):
        """Test creating a Project instance."""
        from src.project_manager import Project

        project = Project(
            name="test_project",
            db_path="/path/to/db.duckdb",
            cpg_path="/path/to/cpg",
            language="python",
            description="Test project description",
            source_path="/path/to/source",
            metadata={"key": "value"},
        )

        assert project.name == "test_project"
        assert project.db_path == "/path/to/db.duckdb"
        assert project.cpg_path == "/path/to/cpg"
        assert project.language == "python"
        assert project.description == "Test project description"
        assert project.source_path == "/path/to/source"
        assert project.metadata == {"key": "value"}

    def test_project_defaults(self):
        """Test Project default values."""
        from src.project_manager import Project

        project = Project(
            name="minimal",
            db_path="db.duckdb",
            cpg_path="",
            language="c",
            description="Minimal project",
        )

        assert project.source_path is None
        assert project.metadata == {}

    def test_project_exists_true(self, tmp_path):
        """Test exists() returns True for existing file."""
        from src.project_manager import Project

        db_file = tmp_path / "test.duckdb"
        db_file.touch()

        project = Project(
            name="test",
            db_path=str(db_file),
            cpg_path="",
            language="c",
            description="Test",
        )

        assert project.exists() is True

    def test_project_exists_false(self):
        """Test exists() returns False for missing file."""
        from src.project_manager import Project

        project = Project(
            name="test",
            db_path="/nonexistent/path.duckdb",
            cpg_path="",
            language="c",
            description="Test",
        )

        assert project.exists() is False

    def test_project_to_dict(self):
        """Test to_dict() conversion."""
        from src.project_manager import Project

        project = Project(
            name="test",
            db_path="/path/db.duckdb",
            cpg_path="/path/cpg",
            language="python",
            description="Desc",
            source_path="/path/src",
            metadata={"extra": "data"},
        )

        result = project.to_dict()

        assert result["db_path"] == "/path/db.duckdb"
        assert result["cpg_path"] == "/path/cpg"
        assert result["language"] == "python"
        assert result["description"] == "Desc"
        assert result["source_path"] == "/path/src"
        assert result["extra"] == "data"


class TestProjectManagerInit:
    """Tests for ProjectManager initialization."""

    def test_init_creates_default_config(self, tmp_path):
        """Test initialization creates default config if missing."""
        from src.project_manager import ProjectManager

        config_path = tmp_path / "projects.yaml"

        manager = ProjectManager(str(config_path))

        assert config_path.exists()
        assert len(manager.list_projects()) > 0

    def test_init_loads_existing_config(self, tmp_path):
        """Test initialization loads existing config."""
        from src.project_manager import ProjectManager

        config_path = tmp_path / "projects.yaml"
        config = {
            "projects": {
                "custom": {
                    "db_path": "custom.duckdb",
                    "cpg_path": "/custom/cpg",
                    "language": "java",
                    "description": "Custom project",
                }
            },
            "active_project": "custom",
        }

        with open(config_path, "w") as f:
            yaml.dump(config, f)

        manager = ProjectManager(str(config_path))

        assert len(manager.list_projects()) == 1
        assert manager.get_active_project().name == "custom"

    def test_init_handles_empty_config(self, tmp_path):
        """Test initialization handles empty config file."""
        from src.project_manager import ProjectManager

        config_path = tmp_path / "projects.yaml"
        config_path.touch()  # Empty file

        manager = ProjectManager(str(config_path))

        # Should create defaults
        assert len(manager.list_projects()) > 0


class TestProjectManagerListProjects:
    """Tests for listing projects."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create ProjectManager with test config."""
        from src.project_manager import ProjectManager

        config_path = tmp_path / "projects.yaml"
        config = {
            "projects": {
                "project1": {
                    "db_path": "p1.duckdb",
                    "cpg_path": "",
                    "language": "c",
                    "description": "Project 1",
                },
                "project2": {
                    "db_path": "p2.duckdb",
                    "cpg_path": "",
                    "language": "python",
                    "description": "Project 2",
                },
            },
            "active_project": "project1",
        }

        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return ProjectManager(str(config_path))

    def test_list_projects(self, manager):
        """Test listing all projects."""
        projects = manager.list_projects()

        assert len(projects) == 2
        names = [p.name for p in projects]
        assert "project1" in names
        assert "project2" in names

    def test_list_projects_empty(self, tmp_path):
        """Test listing with no projects (edge case)."""
        from src.project_manager import ProjectManager

        # This will create default project
        manager = ProjectManager(str(tmp_path / "projects.yaml"))

        projects = manager.list_projects()
        assert len(projects) >= 1


class TestProjectManagerGetProject:
    """Tests for getting specific projects."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create ProjectManager with test config."""
        from src.project_manager import ProjectManager

        config_path = tmp_path / "projects.yaml"
        config = {
            "projects": {
                "myproject": {
                    "db_path": "my.duckdb",
                    "cpg_path": "/my/cpg",
                    "language": "rust",
                    "description": "My project",
                }
            },
            "active_project": "myproject",
        }

        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return ProjectManager(str(config_path))

    def test_get_project_exists(self, manager):
        """Test getting existing project."""
        project = manager.get_project("myproject")

        assert project is not None
        assert project.name == "myproject"
        assert project.language == "rust"

    def test_get_project_not_found(self, manager):
        """Test getting nonexistent project."""
        project = manager.get_project("nonexistent")

        assert project is None


class TestProjectManagerActiveProject:
    """Tests for active project management."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create ProjectManager with test config."""
        from src.project_manager import ProjectManager

        config_path = tmp_path / "projects.yaml"
        config = {
            "projects": {
                "default": {
                    "db_path": "default.duckdb",
                    "cpg_path": "",
                    "language": "c",
                    "description": "Default",
                },
                "alternate": {
                    "db_path": "alt.duckdb",
                    "cpg_path": "",
                    "language": "go",
                    "description": "Alternate",
                },
            },
            "active_project": "default",
        }

        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return ProjectManager(str(config_path))

    def test_get_active_project(self, manager):
        """Test getting active project."""
        active = manager.get_active_project()

        assert active is not None
        assert active.name == "default"

    def test_get_active_db_path(self, manager):
        """Test getting active database path."""
        db_path = manager.get_active_db_path()

        assert db_path == "default.duckdb"

    def test_get_active_db_path_no_project(self, tmp_path):
        """Test get_active_db_path when no project active."""
        from src.project_manager import ProjectManager

        # Create minimal config
        config_path = tmp_path / "projects.yaml"
        config = {"projects": {}, "active_project": None}

        with open(config_path, "w") as f:
            yaml.dump(config, f)

        # Will fall back to defaults
        manager = ProjectManager(str(config_path))

        # Should return default path
        db_path = manager.get_active_db_path()
        assert "duckdb" in db_path.lower()


class TestProjectManagerSwitchProject:
    """Tests for project switching."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create ProjectManager with test config."""
        from src.project_manager import ProjectManager

        config_path = tmp_path / "projects.yaml"
        config = {
            "projects": {
                "first": {
                    "db_path": "first.duckdb",
                    "cpg_path": "",
                    "language": "c",
                    "description": "First",
                },
                "second": {
                    "db_path": "second.duckdb",
                    "cpg_path": "",
                    "language": "python",
                    "description": "Second",
                },
            },
            "active_project": "first",
        }

        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return ProjectManager(str(config_path))

    def test_switch_project_success(self, manager):
        """Test successful project switch."""
        result = manager.switch_project("second")

        assert result is True
        assert manager.get_active_project().name == "second"

    def test_switch_project_not_found(self, manager):
        """Test switching to nonexistent project."""
        result = manager.switch_project("nonexistent")

        assert result is False
        # Active project unchanged
        assert manager.get_active_project().name == "first"

    def test_switch_project_saves_config(self, manager, tmp_path):
        """Test that switching saves config."""
        manager.switch_project("second")

        # Reload config
        config_path = tmp_path / "projects.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert config["active_project"] == "second"

    def test_switch_project_callback(self, manager):
        """Test switch callback is called."""
        callback_args = []

        def callback(old, new, project):
            callback_args.append((old, new, project.name))

        manager.on_project_switch(callback)
        manager.switch_project("second")

        assert len(callback_args) == 1
        assert callback_args[0] == ("first", "second", "second")


class TestProjectManagerAddProject:
    """Tests for adding projects."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create ProjectManager with test config."""
        from src.project_manager import ProjectManager

        config_path = tmp_path / "projects.yaml"
        config = {
            "projects": {
                "existing": {
                    "db_path": "existing.duckdb",
                    "cpg_path": "",
                    "language": "c",
                    "description": "Existing",
                }
            },
            "active_project": "existing",
        }

        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return ProjectManager(str(config_path))

    def test_add_project_success(self, manager):
        """Test adding a new project."""
        result = manager.add_project(
            name="new_project",
            db_path="new.duckdb",
            language="java",
            description="New project",
            cpg_path="/new/cpg",
            source_path="/new/src",
        )

        assert result is True
        assert manager.get_project("new_project") is not None

    def test_add_project_duplicate(self, manager):
        """Test adding duplicate project fails."""
        result = manager.add_project(
            name="existing",
            db_path="dup.duckdb",
            language="c",
            description="Duplicate",
        )

        assert result is False

    def test_add_project_switch_to(self, manager):
        """Test adding project with switch_to=True."""
        manager.add_project(
            name="new_active",
            db_path="active.duckdb",
            language="python",
            description="New active",
            switch_to=True,
        )

        assert manager.get_active_project().name == "new_active"


class TestProjectManagerRemoveProject:
    """Tests for removing projects."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create ProjectManager with test config."""
        from src.project_manager import ProjectManager

        config_path = tmp_path / "projects.yaml"
        config = {
            "projects": {
                "keep": {
                    "db_path": "keep.duckdb",
                    "cpg_path": "",
                    "language": "c",
                    "description": "Keep",
                },
                "remove_me": {
                    "db_path": "remove.duckdb",
                    "cpg_path": "",
                    "language": "python",
                    "description": "Remove",
                },
            },
            "active_project": "keep",
        }

        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return ProjectManager(str(config_path))

    def test_remove_project_success(self, manager):
        """Test removing a project."""
        result = manager.remove_project("remove_me")

        assert result is True
        assert manager.get_project("remove_me") is None

    def test_remove_project_not_found(self, manager):
        """Test removing nonexistent project."""
        result = manager.remove_project("nonexistent")

        assert result is False

    def test_remove_active_project_fails(self, manager):
        """Test removing active project fails."""
        result = manager.remove_project("keep")

        assert result is False
        # Project still exists
        assert manager.get_project("keep") is not None


class TestProjectManagerFormatList:
    """Tests for project list formatting."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create ProjectManager with test config."""
        from src.project_manager import ProjectManager

        # Create a db file for one project
        db_file = tmp_path / "exists.duckdb"
        db_file.touch()

        config_path = tmp_path / "projects.yaml"
        config = {
            "projects": {
                "exists": {
                    "db_path": str(db_file),
                    "cpg_path": "",
                    "language": "c",
                    "description": "Exists",
                },
                "missing": {
                    "db_path": "/nonexistent/missing.duckdb",
                    "cpg_path": "",
                    "language": "python",
                    "description": "Missing",
                },
            },
            "active_project": "exists",
        }

        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return ProjectManager(str(config_path))

    def test_format_project_list(self, manager):
        """Test project list formatting."""
        formatted = manager.format_project_list()

        assert "Available projects" in formatted
        assert "exists" in formatted
        assert "missing" in formatted
        assert "[OK]" in formatted
        assert "[MISSING]" in formatted

    def test_format_shows_active_marker(self, manager):
        """Test active project has marker."""
        formatted = manager.format_project_list()

        # Active project should have asterisk
        assert "*" in formatted


class TestProjectManagerSingleton:
    """Tests for global singleton."""

    def test_get_project_manager_singleton(self, tmp_path):
        """Test get_project_manager returns singleton."""
        from src.project_manager import (
            get_project_manager,
            reset_project_manager,
        )

        reset_project_manager()

        config_path = str(tmp_path / "projects.yaml")

        manager1 = get_project_manager(config_path)
        manager2 = get_project_manager(config_path)

        assert manager1 is manager2

        reset_project_manager()

    def test_reset_project_manager(self, tmp_path):
        """Test resetting singleton."""
        from src.project_manager import (
            get_project_manager,
            reset_project_manager,
        )

        reset_project_manager()

        config_path = str(tmp_path / "projects.yaml")

        manager1 = get_project_manager(config_path)
        reset_project_manager()
        manager2 = get_project_manager(config_path)

        # Should be different instances
        assert manager1 is not manager2

        reset_project_manager()


class TestProjectManagerRepr:
    """Tests for string representation."""

    def test_repr(self, tmp_path):
        """Test __repr__ method."""
        from src.project_manager import ProjectManager

        config_path = tmp_path / "projects.yaml"
        config = {
            "projects": {
                "test": {
                    "db_path": "test.duckdb",
                    "cpg_path": "",
                    "language": "c",
                    "description": "Test",
                }
            },
            "active_project": "test",
        }

        with open(config_path, "w") as f:
            yaml.dump(config, f)

        manager = ProjectManager(str(config_path))
        repr_str = repr(manager)

        assert "ProjectManager" in repr_str
        assert "projects=1" in repr_str
        assert "active=test" in repr_str
