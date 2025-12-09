"""
Detect Language Step.

Detects the primary programming language of a codebase.
"""

import logging
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..models import JoernFrontend, SupportedLanguage

logger = logging.getLogger(__name__)

# Mapping of file extensions to supported languages
EXTENSION_MAP: Dict[str, SupportedLanguage] = {
    # C/C++
    ".c": SupportedLanguage.C,
    ".h": SupportedLanguage.C,
    ".cpp": SupportedLanguage.C,
    ".cc": SupportedLanguage.C,
    ".cxx": SupportedLanguage.C,
    ".hpp": SupportedLanguage.C,
    ".hxx": SupportedLanguage.C,
    # C#
    ".cs": SupportedLanguage.CSHARP,
    # Go
    ".go": SupportedLanguage.GO,
    # Java
    ".java": SupportedLanguage.JAVA,
    # JavaScript/TypeScript
    ".js": SupportedLanguage.JAVASCRIPT,
    ".jsx": SupportedLanguage.JAVASCRIPT,
    ".ts": SupportedLanguage.JAVASCRIPT,
    ".tsx": SupportedLanguage.JAVASCRIPT,
    ".mjs": SupportedLanguage.JAVASCRIPT,
    # Kotlin
    ".kt": SupportedLanguage.KOTLIN,
    ".kts": SupportedLanguage.KOTLIN,
    # PHP
    ".php": SupportedLanguage.PHP,
    # Python
    ".py": SupportedLanguage.PYTHON,
    ".pyw": SupportedLanguage.PYTHON,
    # Ruby
    ".rb": SupportedLanguage.RUBY,
    # Swift
    ".swift": SupportedLanguage.SWIFT,
}

# Joern frontend configurations
JOERN_FRONTENDS: Dict[SupportedLanguage, JoernFrontend] = {
    SupportedLanguage.C: JoernFrontend(
        language=SupportedLanguage.C,
        command="c2cpg",
        joern_language_flag="C",
        file_extensions=[".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hxx"],
        exclude_patterns=["test", "tests", "vendor", "third_party"],
    ),
    SupportedLanguage.CSHARP: JoernFrontend(
        language=SupportedLanguage.CSHARP,
        command="csharp2cpg",
        joern_language_flag="CSHARPSRC",
        file_extensions=[".cs"],
        exclude_patterns=["bin", "obj", "test", "tests"],
    ),
    SupportedLanguage.GO: JoernFrontend(
        language=SupportedLanguage.GO,
        command="gosrc2cpg",
        joern_language_flag="GOLANG",
        file_extensions=[".go"],
        exclude_patterns=["vendor", "testdata", "_test.go"],
    ),
    SupportedLanguage.JAVA: JoernFrontend(
        language=SupportedLanguage.JAVA,
        command="javasrc2cpg",
        joern_language_flag="JAVASRC",
        file_extensions=[".java"],
        exclude_patterns=["test", "tests", "target", "build"],
    ),
    SupportedLanguage.JAVASCRIPT: JoernFrontend(
        language=SupportedLanguage.JAVASCRIPT,
        command="jssrc2cpg",
        joern_language_flag="JAVASCRIPT",
        file_extensions=[".js", ".jsx", ".ts", ".tsx", ".mjs"],
        exclude_patterns=["node_modules", "dist", "build", "test", "tests", "__tests__"],
    ),
    SupportedLanguage.KOTLIN: JoernFrontend(
        language=SupportedLanguage.KOTLIN,
        command="kotlin2cpg",
        joern_language_flag="KOTLIN",
        file_extensions=[".kt", ".kts"],
        exclude_patterns=["build", "test", "tests"],
    ),
    SupportedLanguage.PHP: JoernFrontend(
        language=SupportedLanguage.PHP,
        command="php2cpg",
        joern_language_flag="PHP",
        file_extensions=[".php"],
        exclude_patterns=["vendor", "test", "tests"],
    ),
    SupportedLanguage.PYTHON: JoernFrontend(
        language=SupportedLanguage.PYTHON,
        command="pysrc2cpg",
        joern_language_flag="PYTHONSRC",
        file_extensions=[".py", ".pyw"],
        exclude_patterns=[
            "venv",
            ".venv",
            "__pycache__",
            "test",
            "tests",
            "site-packages",
        ],
    ),
    SupportedLanguage.RUBY: JoernFrontend(
        language=SupportedLanguage.RUBY,
        command="rubysrc2cpg",
        joern_language_flag="RUBYSRC",
        file_extensions=[".rb"],
        exclude_patterns=["vendor", "spec", "test", "tests"],
    ),
    SupportedLanguage.SWIFT: JoernFrontend(
        language=SupportedLanguage.SWIFT,
        command="swiftsrc2cpg",
        joern_language_flag="SWIFTSRC",
        file_extensions=[".swift"],
        exclude_patterns=["Pods", "Carthage", "test", "tests"],
    ),
}


class DetectLanguageStep:
    """Step for detecting the programming language of a codebase."""

    def __init__(self, progress_callback: Optional[Callable[[int, str], None]] = None):
        """
        Initialize detect language step.

        Args:
            progress_callback: Optional callback for reporting progress.
        """
        self.progress_callback = progress_callback

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute language detection.

        Args:
            context: Pipeline context with 'request' and 'source_path'.

        Returns:
            Dictionary with detected language and frontend configuration.
        """
        request = context["request"]
        source_path = Path(context["source_path"])

        # If language is explicitly specified
        if request.language:
            frontend = JOERN_FRONTENDS.get(request.language)
            if not frontend:
                raise ValueError(f"Unsupported language: {request.language}")

            self._report_progress(100, f"Using specified language: {request.language.value}")
            return {
                "detected_language": request.language,
                "joern_frontend": frontend,
                "detection_method": "explicit",
                "file_stats": {},
            }

        # Auto-detection
        self._report_progress(10, "Scanning source files...")

        file_counts = self._count_files_by_language(source_path, request.include_paths)

        self._report_progress(50, "Analyzing file distribution...")

        if not file_counts:
            raise ValueError(
                f"No supported source files found in {source_path}. "
                f"Supported extensions: {list(EXTENSION_MAP.keys())}"
            )

        # Determine primary language
        language = file_counts.most_common(1)[0][0]
        frontend = JOERN_FRONTENDS.get(language)

        if not frontend:
            raise ValueError(f"No Joern frontend available for {language}")

        # Build file stats
        file_stats = {lang.value: count for lang, count in file_counts.items()}

        self._report_progress(100, f"Detected language: {language.value}")

        logger.info(
            f"Language detection complete: {language.value} "
            f"({file_counts[language]} files)"
        )
        logger.info(f"File distribution: {file_stats}")

        return {
            "detected_language": language,
            "joern_frontend": frontend,
            "detection_method": "auto",
            "file_stats": file_stats,
        }

    def _count_files_by_language(
        self, source_path: Path, include_paths: List[str]
    ) -> Counter:
        """
        Count source files by language.

        Args:
            source_path: Root path of the source code.
            include_paths: Optional list of paths to include.

        Returns:
            Counter mapping languages to file counts.
        """
        counter: Counter = Counter()

        # Determine paths to scan
        if include_paths:
            paths_to_scan = [source_path / p for p in include_paths]
        else:
            paths_to_scan = [source_path]

        # Common directories to skip
        skip_dirs = {
            ".git",
            ".svn",
            ".hg",
            "node_modules",
            "__pycache__",
            ".venv",
            "venv",
            "vendor",
            "third_party",
            "build",
            "dist",
            "target",
            "bin",
            "obj",
        }

        for base_path in paths_to_scan:
            if not base_path.exists():
                logger.warning(f"Path does not exist: {base_path}")
                continue

            for file_path in base_path.rglob("*"):
                # Skip directories in skip list
                if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
                    continue

                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    if ext in EXTENSION_MAP:
                        counter[EXTENSION_MAP[ext]] += 1

        return counter

    def _report_progress(self, progress: int, message: str) -> None:
        """Report progress to callback."""
        if self.progress_callback:
            self.progress_callback(progress, message)
        logger.info(f"Detect language step: {progress}% - {message}")
