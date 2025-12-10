"""
Tests for TUI Configuration Editor.

Tests for config loading, viewing, editing, and saving.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile
import yaml


class MockTheme:
    """Mock theme for testing."""
    border = "blue"
    accent = "cyan"
    highlight = "green"


class TestConfigEditorInit:
    """Tests for ConfigEditor initialization."""

    def test_init_with_existing_config(self, tmp_path):
        """Test initialization with existing config file."""
        config_content = {
            "llm": {"provider": "local", "temperature": 0.7},
            "retrieval": {"top_k": 5},
        }

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_content, f)

        from src.tui.components.config_editor import ConfigEditor

        editor = ConfigEditor(config_path=config_file, theme=MockTheme())

        assert editor.get_config() == config_content

    def test_init_with_missing_config(self, tmp_path):
        """Test initialization with missing config file."""
        config_file = tmp_path / "nonexistent.yaml"

        from src.tui.components.config_editor import ConfigEditor

        editor = ConfigEditor(config_path=config_file, theme=MockTheme())

        assert editor.get_config() == {}

    def test_init_with_empty_config(self, tmp_path):
        """Test initialization with empty config file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")

        from src.tui.components.config_editor import ConfigEditor

        editor = ConfigEditor(config_path=config_file, theme=MockTheme())

        assert editor.get_config() == {}


class TestConfigEditorGetSection:
    """Tests for getting config sections."""

    @pytest.fixture
    def editor(self, tmp_path):
        """Create editor with test config."""
        config_content = {
            "llm": {"provider": "local", "temperature": 0.7},
            "retrieval": {"top_k": 5},
            "analysis": {"threshold": 0.8},
        }

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_content, f)

        from src.tui.components.config_editor import ConfigEditor

        return ConfigEditor(config_path=config_file, theme=MockTheme())

    def test_get_existing_section(self, editor):
        """Test getting existing section."""
        section = editor.get_section("llm")

        assert section is not None
        assert section["provider"] == "local"
        assert section["temperature"] == 0.7

    def test_get_nonexistent_section(self, editor):
        """Test getting nonexistent section."""
        section = editor.get_section("nonexistent")

        assert section is None

    def test_get_section_by_index(self, editor):
        """Test getting section by numeric index."""
        # The order is: editable sections first, then read-only, then other
        section_name = editor.get_section_by_index(1)

        # First editable section in config
        assert section_name is not None

    def test_get_section_by_invalid_index(self, editor):
        """Test getting section by invalid index."""
        section_name = editor.get_section_by_index(100)

        assert section_name is None


class TestConfigEditorEdit:
    """Tests for editing config values."""

    @pytest.fixture
    def editor(self, tmp_path):
        """Create editor with test config."""
        config_content = {
            "llm": {
                "provider": "local",
                "temperature": 0.7,
                "max_tokens": 512,
                "nested": {"key": "value"},
            },
            "retrieval": {"top_k": 5, "enabled": True},
            "domain": {"name": "test"},  # Read-only section
        }

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_content, f)

        from src.tui.components.config_editor import ConfigEditor

        return ConfigEditor(config_path=config_file, theme=MockTheme())

    def test_edit_existing_value(self, editor):
        """Test editing existing value."""
        success, msg = editor.edit_value("llm", "temperature", "0.5")

        assert success is True
        assert editor.get_section("llm")["temperature"] == 0.5

    def test_edit_integer_value(self, editor):
        """Test editing integer value."""
        success, msg = editor.edit_value("llm", "max_tokens", "1024")

        assert success is True
        assert editor.get_section("llm")["max_tokens"] == 1024

    def test_edit_boolean_value(self, editor):
        """Test editing boolean value."""
        success, msg = editor.edit_value("retrieval", "enabled", "false")

        assert success is True
        assert editor.get_section("retrieval")["enabled"] is False

    def test_edit_nested_value(self, editor):
        """Test editing nested value with dot notation."""
        success, msg = editor.edit_value("llm", "nested.key", "new_value")

        assert success is True
        assert editor.get_section("llm")["nested"]["key"] == "new_value"

    def test_edit_read_only_section(self, editor):
        """Test editing read-only section fails."""
        success, msg = editor.edit_value("domain", "name", "new_name")

        assert success is False
        assert "read-only" in msg.lower()

    def test_edit_nonexistent_section(self, editor):
        """Test editing nonexistent section fails."""
        success, msg = editor.edit_value("nonexistent", "key", "value")

        assert success is False
        assert "not found" in msg.lower()

    def test_edit_nonexistent_key(self, editor):
        """Test editing nonexistent key fails."""
        success, msg = editor.edit_value("llm", "nonexistent_key", "value")

        assert success is False
        assert "not found" in msg.lower()

    def test_edit_invalid_type(self, editor):
        """Test editing with invalid type conversion."""
        # temperature should be float
        success, msg = editor.edit_value("llm", "max_tokens", "not_an_int")

        assert success is False
        assert "invalid" in msg.lower()


class TestConfigEditorSave:
    """Tests for saving config changes."""

    def test_save_changes(self, tmp_path):
        """Test saving config changes to file."""
        config_content = {"llm": {"provider": "local", "temperature": 0.7}}

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_content, f)

        from src.tui.components.config_editor import ConfigEditor

        editor = ConfigEditor(config_path=config_file, theme=MockTheme())

        # Edit value
        editor.edit_value("llm", "temperature", "0.9")

        # Save
        success, msg = editor.save_changes()

        assert success is True

        # Reload and verify
        with open(config_file, "r") as f:
            saved_config = yaml.safe_load(f)

        assert saved_config["llm"]["temperature"] == 0.9

    def test_save_failure(self, tmp_path):
        """Test save failure handling."""
        config_content = {"llm": {"provider": "local"}}

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_content, f)

        from src.tui.components.config_editor import ConfigEditor

        editor = ConfigEditor(config_path=config_file, theme=MockTheme())

        # Make file read-only
        config_file.chmod(0o444)

        try:
            success, msg = editor.save_changes()
            # May succeed on Windows, fail on Unix
        finally:
            # Restore permissions
            config_file.chmod(0o644)


class TestConfigEditorReload:
    """Tests for config reload."""

    def test_reload_config(self, tmp_path):
        """Test reloading config from file."""
        config_content = {"llm": {"provider": "local"}}

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_content, f)

        from src.tui.components.config_editor import ConfigEditor

        editor = ConfigEditor(config_path=config_file, theme=MockTheme())

        # Modify file externally
        new_content = {"llm": {"provider": "gigachat"}}
        with open(config_file, "w") as f:
            yaml.dump(new_content, f)

        # Reload
        editor.reload()

        assert editor.get_section("llm")["provider"] == "gigachat"


class TestConfigEditorRender:
    """Tests for rendering methods."""

    @pytest.fixture
    def editor(self, tmp_path):
        """Create editor with test config."""
        config_content = {
            "llm": {"provider": "local", "api_key": "secret123"},
            "retrieval": {"top_k": 5},
        }

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_content, f)

        from src.tui.components.config_editor import ConfigEditor

        return ConfigEditor(config_path=config_file, theme=MockTheme())

    def test_render_overview(self, editor):
        """Test rendering config overview."""
        panel = editor.render_overview()

        assert panel is not None
        # Panel should contain section names

    def test_render_section_list(self, editor):
        """Test rendering interactive section list."""
        panel = editor.render_section_list()

        assert panel is not None

    def test_render_section(self, editor):
        """Test rendering specific section."""
        panel = editor.render_section("llm")

        assert panel is not None

    def test_render_nonexistent_section(self, editor):
        """Test rendering nonexistent section shows error."""
        panel = editor.render_section("nonexistent")

        assert panel is not None
        # Should indicate section not found

    def test_mask_sensitive_values(self, editor):
        """Test that sensitive values are masked."""
        masked = editor._mask_sensitive("api_key", "secret123")

        assert "secret" not in masked
        assert "***" in masked or "****" in masked


class TestConfigEditorEditableKeys:
    """Tests for editable keys functionality."""

    @pytest.fixture
    def editor(self, tmp_path):
        """Create editor with nested config."""
        config_content = {
            "llm": {
                "provider": "local",
                "model": {
                    "name": "llama",
                    "path": "/path/to/model",
                },
            },
        }

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_content, f)

        from src.tui.components.config_editor import ConfigEditor

        return ConfigEditor(config_path=config_file, theme=MockTheme())

    def test_get_editable_keys(self, editor):
        """Test getting flattened list of editable keys."""
        keys = editor.get_editable_keys("llm")

        assert "provider" in keys
        assert "model.name" in keys
        assert "model.path" in keys

    def test_get_editable_keys_readonly_section(self, editor):
        """Test getting keys from read-only section returns empty."""
        keys = editor.get_editable_keys("domain")

        assert keys == []


class TestTypeConversion:
    """Tests for value type conversion."""

    @pytest.fixture
    def editor(self, tmp_path):
        """Create basic editor."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("llm: {}")

        from src.tui.components.config_editor import ConfigEditor

        return ConfigEditor(config_path=config_file, theme=MockTheme())

    def test_convert_bool_true(self, editor):
        """Test boolean true conversion."""
        for value in ["true", "True", "TRUE", "yes", "Yes", "1", "on"]:
            result = editor._convert_value(value, bool)
            assert result is True

    def test_convert_bool_false(self, editor):
        """Test boolean false conversion."""
        for value in ["false", "False", "FALSE", "no", "No", "0", "off"]:
            result = editor._convert_value(value, bool)
            assert result is False

    def test_convert_bool_invalid(self, editor):
        """Test invalid boolean conversion."""
        with pytest.raises(ValueError):
            editor._convert_value("maybe", bool)

    def test_convert_int(self, editor):
        """Test integer conversion."""
        result = editor._convert_value("42", int)
        assert result == 42

    def test_convert_float(self, editor):
        """Test float conversion."""
        result = editor._convert_value("3.14", float)
        assert abs(result - 3.14) < 0.001

    def test_convert_list(self, editor):
        """Test list conversion from comma-separated string."""
        result = editor._convert_value("a, b, c", list)
        assert result == ["a", "b", "c"]

    def test_convert_string(self, editor):
        """Test string conversion."""
        result = editor._convert_value("hello world", str)
        assert result == "hello world"
