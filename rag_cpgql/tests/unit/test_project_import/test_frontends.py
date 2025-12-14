"""Tests for project_import frontends module."""

from pathlib import Path

import pytest

from src.project_import.frontends import (
    EXTENSION_TO_LANGUAGE,
    FRONTENDS,
    JoernFrontend,
    detect_language,
    detect_language_with_stats,
    get_exclude_patterns,
    get_frontend,
    get_frontend_command_path,
    is_binary_language,
    list_supported_languages,
)


class TestFrontendRegistry:
    """Tests for frontend registry."""

    def test_all_frontends_defined(self):
        """Test all expected languages are in registry."""
        expected_languages = {
            "c", "csharp", "go", "java", "java_bytecode",
            "javascript", "kotlin", "php", "python", "ruby", "swift", "ghidra", "llvm"
        }
        assert expected_languages.issubset(set(FRONTENDS.keys()))

    def test_frontend_structure(self):
        """Test all frontends have required attributes."""
        for lang, frontend in FRONTENDS.items():
            assert isinstance(frontend, JoernFrontend)
            assert frontend.language == lang
            assert frontend.command
            assert frontend.language_flag
            assert isinstance(frontend.file_extensions, list)
            assert len(frontend.file_extensions) > 0

    def test_get_frontend(self):
        """Test getting frontend by name."""
        frontend = get_frontend("python")
        assert frontend is not None
        assert frontend.command == "pysrc2cpg"
        assert frontend.language_flag == "PYTHONSRC"
        assert ".py" in frontend.file_extensions

    def test_get_frontend_case_insensitive(self):
        """Test get_frontend is case insensitive."""
        assert get_frontend("PYTHON") == get_frontend("python")
        assert get_frontend("Python") == get_frontend("python")

    def test_get_frontend_not_found(self):
        """Test get_frontend returns None for unknown language."""
        assert get_frontend("nonexistent") is None

    def test_python_frontend(self):
        """Test Python frontend configuration."""
        frontend = get_frontend("python")
        assert frontend.command == "pysrc2cpg"
        assert frontend.language_flag == "PYTHONSRC"
        assert ".py" in frontend.file_extensions
        assert ".pyw" in frontend.file_extensions
        assert "venv" in frontend.exclude_patterns
        assert frontend.supports_joern_parse is True

    def test_java_frontend(self):
        """Test Java (source) frontend configuration."""
        frontend = get_frontend("java")
        assert frontend.command == "javasrc2cpg"
        assert frontend.language_flag == "JAVASRC"
        assert ".java" in frontend.file_extensions

    def test_java_bytecode_frontend(self):
        """Test Java bytecode frontend configuration."""
        frontend = get_frontend("java_bytecode")
        assert frontend.command == "jimple2cpg"
        assert ".class" in frontend.file_extensions
        assert ".jar" in frontend.file_extensions

    def test_javascript_frontend(self):
        """Test JavaScript frontend configuration."""
        frontend = get_frontend("javascript")
        assert frontend.command == "jssrc2cpg"
        assert ".js" in frontend.file_extensions
        assert ".ts" in frontend.file_extensions
        assert ".tsx" in frontend.file_extensions
        assert "node_modules" in frontend.exclude_patterns

    def test_c_frontend(self):
        """Test C/C++ frontend configuration."""
        frontend = get_frontend("c")
        assert frontend.command == "c2cpg"
        assert ".c" in frontend.file_extensions
        assert ".cpp" in frontend.file_extensions
        assert ".h" in frontend.file_extensions

    def test_ghidra_frontend(self):
        """Test Ghidra binary analysis frontend."""
        frontend = get_frontend("ghidra")
        assert frontend is not None
        assert frontend.command == "ghidra2cpg"
        assert ".exe" in frontend.file_extensions
        assert ".dll" in frontend.file_extensions
        assert ".so" in frontend.file_extensions
        assert ".dylib" in frontend.file_extensions
        assert ".elf" in frontend.file_extensions
        assert "binary" in frontend.description.lower() or "ghidra" in frontend.description.lower()

    def test_extension_to_language_mapping(self):
        """Test file extension to language mapping."""
        assert EXTENSION_TO_LANGUAGE[".py"] == "python"
        assert EXTENSION_TO_LANGUAGE[".java"] == "java"
        assert EXTENSION_TO_LANGUAGE[".js"] == "javascript"
        assert EXTENSION_TO_LANGUAGE[".c"] == "c"
        assert EXTENSION_TO_LANGUAGE[".go"] == "go"

    def test_extension_to_language_lowercase(self):
        """Test extension mapping uses lowercase."""
        # All keys should be lowercase
        for ext in EXTENSION_TO_LANGUAGE.keys():
            assert ext == ext.lower()


class TestGetFrontendCommandPath:
    """Tests for frontend command path resolution."""

    def test_get_frontend_command_path(self, tmp_path):
        """Test finding frontend command."""
        joern_home = tmp_path / "joern"
        joern_cli = joern_home / "joern-cli"
        joern_cli.mkdir(parents=True)

        # Create frontend binary
        frontend_bin = joern_cli / "pysrc2cpg"
        frontend_bin.touch()

        frontend = get_frontend("python")
        result = get_frontend_command_path(frontend, joern_home)
        assert result == frontend_bin

    def test_get_frontend_command_path_bat(self, tmp_path):
        """Test finding .bat frontend command."""
        joern_home = tmp_path / "joern"
        joern_cli = joern_home / "joern-cli"
        joern_cli.mkdir(parents=True)

        # Create .bat frontend
        frontend_bin = joern_cli / "pysrc2cpg.bat"
        frontend_bin.touch()

        frontend = get_frontend("python")
        result = get_frontend_command_path(frontend, joern_home)
        assert result == frontend_bin

    def test_get_frontend_command_path_not_found(self, tmp_path):
        """Test returns None when frontend not found."""
        joern_home = tmp_path / "joern"
        joern_cli = joern_home / "joern-cli"
        joern_cli.mkdir(parents=True)

        frontend = get_frontend("python")
        result = get_frontend_command_path(frontend, joern_home)
        assert result is None


class TestLanguageDetection:
    """Tests for automatic language detection."""

    def test_detect_python(self, tmp_path):
        """Test detecting Python project."""
        # Create Python files
        (tmp_path / "main.py").touch()
        (tmp_path / "utils.py").touch()
        (tmp_path / "lib" / "helper.py").mkdir(parents=True)
        (tmp_path / "lib" / "helper.py").touch()

        result = detect_language(tmp_path)
        assert result == "python"

    def test_detect_javascript(self, tmp_path):
        """Test detecting JavaScript project."""
        (tmp_path / "index.js").touch()
        (tmp_path / "app.js").touch()
        (tmp_path / "utils.ts").touch()

        result = detect_language(tmp_path)
        assert result == "javascript"

    def test_detect_java(self, tmp_path):
        """Test detecting Java project."""
        src = tmp_path / "src" / "main" / "java"
        src.mkdir(parents=True)
        (src / "Main.java").touch()
        (src / "App.java").touch()
        (src / "Utils.java").touch()

        result = detect_language(tmp_path)
        assert result == "java"

    def test_detect_c(self, tmp_path):
        """Test detecting C project."""
        (tmp_path / "main.c").touch()
        (tmp_path / "utils.c").touch()
        (tmp_path / "header.h").touch()

        result = detect_language(tmp_path)
        assert result == "c"

    def test_detect_mixed_codebase(self, tmp_path):
        """Test detecting language in mixed codebase."""
        # More Python files than JavaScript
        (tmp_path / "app.py").touch()
        (tmp_path / "main.py").touch()
        (tmp_path / "utils.py").touch()
        (tmp_path / "config.js").touch()

        result = detect_language(tmp_path)
        assert result == "python"

    def test_detect_with_include_paths(self, tmp_path):
        """Test detection with specific paths."""
        # Python in root
        (tmp_path / "config.py").touch()

        # Java in src
        src = tmp_path / "src"
        src.mkdir()
        (src / "Main.java").touch()
        (src / "App.java").touch()
        (src / "Utils.java").touch()

        # With include_paths, should find Java
        result = detect_language(tmp_path, include_paths=["src"])
        assert result == "java"

    def test_detect_skips_node_modules(self, tmp_path):
        """Test detection skips node_modules."""
        # Python in root
        (tmp_path / "main.py").touch()

        # Many JS files in node_modules (should be ignored)
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        for i in range(100):
            (node_modules / f"lib{i}.js").touch()

        result = detect_language(tmp_path)
        assert result == "python"

    def test_detect_skips_venv(self, tmp_path):
        """Test detection skips virtual environment."""
        (tmp_path / "main.js").touch()

        # Many Python files in venv (should be ignored)
        venv = tmp_path / "venv"
        venv.mkdir()
        for i in range(100):
            (venv / f"lib{i}.py").touch()

        result = detect_language(tmp_path)
        assert result == "javascript"

    def test_detect_no_supported_files(self, tmp_path):
        """Test detection returns None when no supported files."""
        (tmp_path / "readme.txt").touch()
        (tmp_path / "data.json").touch()

        result = detect_language(tmp_path)
        assert result is None

    def test_detect_empty_directory(self, tmp_path):
        """Test detection in empty directory."""
        result = detect_language(tmp_path)
        assert result is None


class TestDetectLanguageWithStats:
    """Tests for language detection with statistics."""

    def test_detect_with_stats(self, tmp_path):
        """Test detection returns file statistics."""
        (tmp_path / "main.py").touch()
        (tmp_path / "utils.py").touch()
        (tmp_path / "config.js").touch()

        language, stats = detect_language_with_stats(tmp_path)
        assert language == "python"
        assert stats["python"] == 2
        assert stats["javascript"] == 1

    def test_detect_with_stats_empty(self, tmp_path):
        """Test detection with no supported files."""
        language, stats = detect_language_with_stats(tmp_path)
        assert language is None
        assert stats == {}


class TestListSupportedLanguages:
    """Tests for listing supported languages."""

    def test_list_supported_languages(self):
        """Test listing all supported languages."""
        languages = list_supported_languages()

        assert isinstance(languages, list)
        assert len(languages) >= 10  # At least 10 languages

        # Check structure of each entry
        for lang in languages:
            assert "language" in lang
            assert "command" in lang
            assert "language_flag" in lang
            assert "extensions" in lang
            assert "description" in lang
            assert "supports_joern_parse" in lang

    def test_list_includes_python(self):
        """Test Python is in the list."""
        languages = list_supported_languages()
        python_langs = [l for l in languages if l["language"] == "python"]
        assert len(python_langs) == 1
        assert python_langs[0]["command"] == "pysrc2cpg"


class TestGetExcludePatterns:
    """Tests for getting exclude patterns."""

    def test_get_exclude_patterns_python(self):
        """Test Python exclude patterns."""
        patterns = get_exclude_patterns("python")
        assert "venv" in patterns
        assert ".venv" in patterns
        assert "__pycache__" in patterns

    def test_get_exclude_patterns_javascript(self):
        """Test JavaScript exclude patterns."""
        patterns = get_exclude_patterns("javascript")
        assert "node_modules" in patterns
        assert "dist" in patterns

    def test_get_exclude_patterns_unknown(self):
        """Test unknown language returns empty list."""
        patterns = get_exclude_patterns("nonexistent")
        assert patterns == []

    def test_get_exclude_patterns_returns_copy(self):
        """Test returns a copy, not the original."""
        patterns1 = get_exclude_patterns("python")
        patterns2 = get_exclude_patterns("python")
        patterns1.append("custom")
        assert "custom" not in patterns2


class TestIsBinaryLanguage:
    """Tests for binary language detection."""

    def test_ghidra_is_binary(self):
        """Test Ghidra is identified as binary."""
        assert is_binary_language("ghidra") is True

    def test_java_bytecode_is_binary(self):
        """Test Java bytecode is identified as binary."""
        assert is_binary_language("java_bytecode") is True

    def test_llvm_is_binary(self):
        """Test LLVM is identified as binary."""
        assert is_binary_language("llvm") is True

    def test_python_is_not_binary(self):
        """Test Python is not binary."""
        assert is_binary_language("python") is False

    def test_java_is_not_binary(self):
        """Test Java source is not binary."""
        assert is_binary_language("java") is False

    def test_javascript_is_not_binary(self):
        """Test JavaScript is not binary."""
        assert is_binary_language("javascript") is False
