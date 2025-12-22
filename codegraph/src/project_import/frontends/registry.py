"""
Joern Language Frontend Registry.

Complete configuration for all supported Joern language frontends.
Based on https://docs.joern.io/frontends/
"""

import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class JoernFrontend:
    """Configuration for a Joern language frontend."""

    language: str
    command: str
    language_flag: str
    file_extensions: List[str]
    exclude_patterns: List[str] = field(default_factory=list)
    supports_joern_parse: bool = True
    description: str = ""


# Complete registry of all Joern frontends
FRONTENDS: Dict[str, JoernFrontend] = {
    # C/C++
    "c": JoernFrontend(
        language="c",
        command="c2cpg",
        language_flag="C",
        file_extensions=[".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hxx", ".hh"],
        exclude_patterns=["test", "tests", "vendor", "third_party", "external", "deps"],
        supports_joern_parse=True,
        description="C/C++ source code analysis",
    ),

    # C#
    "csharp": JoernFrontend(
        language="csharp",
        command="csharp2cpg",
        language_flag="CSHARPSRC",
        file_extensions=[".cs"],
        exclude_patterns=["bin", "obj", "test", "tests", "packages", ".nuget"],
        supports_joern_parse=True,
        description="C# source code analysis",
    ),

    # Go
    "go": JoernFrontend(
        language="go",
        command="gosrc2cpg",
        language_flag="GOLANG",
        file_extensions=[".go"],
        exclude_patterns=["vendor", "testdata", "_test.go", "mock", "mocks"],
        supports_joern_parse=True,
        description="Go source code analysis",
    ),

    # Java (source)
    "java": JoernFrontend(
        language="java",
        command="javasrc2cpg",
        language_flag="JAVASRC",
        file_extensions=[".java"],
        exclude_patterns=["test", "tests", "target", "build", ".gradle", ".mvn"],
        supports_joern_parse=True,
        description="Java source code analysis",
    ),

    # Java (bytecode via Jimple)
    "java_bytecode": JoernFrontend(
        language="java_bytecode",
        command="jimple2cpg",
        language_flag="JAVA",
        file_extensions=[".class", ".jar", ".war", ".ear"],
        exclude_patterns=["test", "tests"],
        supports_joern_parse=True,
        description="Java bytecode analysis via Jimple IR",
    ),

    # JavaScript/TypeScript
    "javascript": JoernFrontend(
        language="javascript",
        command="jssrc2cpg",
        language_flag="JAVASCRIPT",
        file_extensions=[".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"],
        exclude_patterns=[
            "node_modules", "dist", "build", ".next", ".nuxt",
            "test", "tests", "__tests__", "spec", "coverage",
            "vendor", "bower_components",
        ],
        supports_joern_parse=True,
        description="JavaScript/TypeScript source code analysis",
    ),

    # Kotlin
    "kotlin": JoernFrontend(
        language="kotlin",
        command="kotlin2cpg",
        language_flag="KOTLIN",
        file_extensions=[".kt", ".kts"],
        exclude_patterns=["build", "test", "tests", ".gradle"],
        supports_joern_parse=True,
        description="Kotlin source code analysis",
    ),

    # PHP
    "php": JoernFrontend(
        language="php",
        command="php2cpg",
        language_flag="PHP",
        file_extensions=[".php", ".php3", ".php4", ".php5", ".phtml"],
        exclude_patterns=["vendor", "test", "tests", "cache", "storage"],
        supports_joern_parse=True,
        description="PHP source code analysis",
    ),

    # Python
    "python": JoernFrontend(
        language="python",
        command="pysrc2cpg",
        language_flag="PYTHONSRC",
        file_extensions=[".py", ".pyw", ".pyi"],
        exclude_patterns=[
            "venv", ".venv", "env", ".env",
            "__pycache__", ".pytest_cache", ".mypy_cache",
            "test", "tests", "testing",
            "site-packages", "dist-packages",
            "build", "dist", "*.egg-info",
        ],
        supports_joern_parse=True,
        description="Python source code analysis",
    ),

    # Ruby
    "ruby": JoernFrontend(
        language="ruby",
        command="rubysrc2cpg",
        language_flag="RUBYSRC",
        file_extensions=[".rb", ".rake", ".gemspec"],
        exclude_patterns=["vendor", "spec", "test", "tests", ".bundle", "tmp"],
        supports_joern_parse=True,
        description="Ruby source code analysis",
    ),

    # Swift
    "swift": JoernFrontend(
        language="swift",
        command="swiftsrc2cpg",
        language_flag="SWIFTSRC",
        file_extensions=[".swift"],
        exclude_patterns=[
            "Pods", "Carthage", ".build", "DerivedData",
            "test", "tests", "Tests", "UITests",
        ],
        supports_joern_parse=True,
        description="Swift source code analysis",
    ),

    # Ghidra (binary analysis)
    "ghidra": JoernFrontend(
        language="ghidra",
        command="ghidra2cpg",
        language_flag="GHIDRA",
        file_extensions=[".exe", ".dll", ".so", ".dylib", ".bin", ".elf", ".o", ".a"],
        exclude_patterns=[],
        supports_joern_parse=True,
        description="Binary analysis via Ghidra (requires Ghidra installation)",
    ),

    # LLVM bitcode
    "llvm": JoernFrontend(
        language="llvm",
        command="llvm2cpg",
        language_flag="LLVM",
        file_extensions=[".bc", ".ll"],
        exclude_patterns=[],
        supports_joern_parse=False,
        description="LLVM bitcode/IR analysis",
    ),
}


# Mapping of file extensions to language keys
EXTENSION_TO_LANGUAGE: Dict[str, str] = {}

for lang_key, frontend in FRONTENDS.items():
    for ext in frontend.file_extensions:
        # Don't overwrite if already mapped (first language wins)
        if ext.lower() not in EXTENSION_TO_LANGUAGE:
            EXTENSION_TO_LANGUAGE[ext.lower()] = lang_key


# Common directories to skip during language detection
SKIP_DIRECTORIES: Set[str] = {
    ".git", ".svn", ".hg", ".bzr",
    "node_modules", "__pycache__", ".venv", "venv",
    "vendor", "third_party", "external", "deps",
    "build", "dist", "target", "out", "bin", "obj",
    ".idea", ".vscode", ".vs",
    "test", "tests", "testing", "spec", "__tests__",
    ".cache", ".tox", ".eggs",
}


def get_frontend(language: str) -> Optional[JoernFrontend]:
    """
    Get frontend configuration by language name.

    Args:
        language: Language name (case-insensitive).

    Returns:
        JoernFrontend configuration or None if not found.
    """
    return FRONTENDS.get(language.lower())


def get_frontend_command_path(
    frontend: JoernFrontend,
    joern_home: Path,
) -> Optional[Path]:
    """
    Get full path to frontend binary.

    Checks multiple possible locations.

    Args:
        frontend: Frontend configuration.
        joern_home: Joern installation directory.

    Returns:
        Path to frontend binary or None if not found.
    """
    joern_cli = joern_home / "joern-cli"

    candidates = [
        joern_cli / frontend.command,
        joern_cli / f"{frontend.command}.bat",
        joern_cli / "bin" / frontend.command,
        joern_cli / "bin" / f"{frontend.command}.bat",
        joern_cli / "frontends" / frontend.command / "bin" / frontend.command,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def detect_language(
    source_path: Path,
    include_paths: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Auto-detect primary programming language from source files.

    Args:
        source_path: Root path to scan.
        include_paths: Optional list of relative paths to include.

    Returns:
        Language key or None if no supported files found.
    """
    counter: Counter = Counter()

    # Determine paths to scan
    if include_paths:
        paths_to_scan = [source_path / p for p in include_paths if (source_path / p).exists()]
    else:
        paths_to_scan = [source_path]

    if not paths_to_scan:
        paths_to_scan = [source_path]

    for base_path in paths_to_scan:
        if not base_path.exists():
            continue

        for file_path in base_path.rglob("*"):
            # Skip directories in skip list
            if any(skip_dir in file_path.parts for skip_dir in SKIP_DIRECTORIES):
                continue

            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in EXTENSION_TO_LANGUAGE:
                    counter[EXTENSION_TO_LANGUAGE[ext]] += 1

    if not counter:
        return None

    # Return most common language
    return counter.most_common(1)[0][0]


def detect_language_with_stats(
    source_path: Path,
    include_paths: Optional[List[str]] = None,
) -> tuple:
    """
    Auto-detect primary programming language with file statistics.

    Args:
        source_path: Root path to scan.
        include_paths: Optional list of relative paths to include.

    Returns:
        Tuple of (language_key, file_stats_dict) or (None, {}).
    """
    counter: Counter = Counter()

    if include_paths:
        paths_to_scan = [source_path / p for p in include_paths if (source_path / p).exists()]
    else:
        paths_to_scan = [source_path]

    if not paths_to_scan:
        paths_to_scan = [source_path]

    for base_path in paths_to_scan:
        if not base_path.exists():
            continue

        for file_path in base_path.rglob("*"):
            if any(skip_dir in file_path.parts for skip_dir in SKIP_DIRECTORIES):
                continue

            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in EXTENSION_TO_LANGUAGE:
                    counter[EXTENSION_TO_LANGUAGE[ext]] += 1

    if not counter:
        return None, {}

    # Build stats dict
    file_stats = {lang: count for lang, count in counter.items()}

    # Return most common language
    primary_lang = counter.most_common(1)[0][0]

    return primary_lang, file_stats


def list_supported_languages() -> List[Dict]:
    """
    List all supported languages with details.

    Returns:
        List of dictionaries with language information.
    """
    result = []

    for lang_key, frontend in FRONTENDS.items():
        result.append({
            "language": lang_key,
            "command": frontend.command,
            "language_flag": frontend.language_flag,
            "extensions": frontend.file_extensions,
            "description": frontend.description,
            "supports_joern_parse": frontend.supports_joern_parse,
        })

    return result


def get_exclude_patterns(language: str) -> List[str]:
    """
    Get default exclude patterns for a language.

    Args:
        language: Language key.

    Returns:
        List of exclude patterns.
    """
    frontend = get_frontend(language)
    if frontend:
        return frontend.exclude_patterns.copy()
    return []


def is_binary_language(language: str) -> bool:
    """
    Check if language analyzes binary files.

    Args:
        language: Language key.

    Returns:
        True if language analyzes binary files.
    """
    return language in {"ghidra", "java_bytecode", "llvm"}
