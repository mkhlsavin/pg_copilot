"""
Detect Language Step.

Detects the primary programming language of a codebase.
Uses the unified frontend registry.
"""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..frontends import (
    FRONTENDS,
    JoernFrontend,
    detect_language_with_stats,
    get_frontend,
)
from ..models import SupportedLanguage

logger = logging.getLogger(__name__)


# Mapping from SupportedLanguage enum to frontend registry keys
LANGUAGE_TO_FRONTEND_KEY: Dict[SupportedLanguage, str] = {
    SupportedLanguage.C: "c",
    SupportedLanguage.CSHARP: "csharp",
    SupportedLanguage.GO: "go",
    SupportedLanguage.JAVA: "java",
    SupportedLanguage.JAVA_BYTECODE: "java_bytecode",
    SupportedLanguage.JAVASCRIPT: "javascript",
    SupportedLanguage.KOTLIN: "kotlin",
    SupportedLanguage.PHP: "php",
    SupportedLanguage.PYTHON: "python",
    SupportedLanguage.RUBY: "ruby",
    SupportedLanguage.SWIFT: "swift",
    SupportedLanguage.GHIDRA: "ghidra",
}


# Reverse mapping
FRONTEND_KEY_TO_LANGUAGE: Dict[str, SupportedLanguage] = {
    v: k for k, v in LANGUAGE_TO_FRONTEND_KEY.items()
}


# Export JOERN_FRONTENDS for backward compatibility
JOERN_FRONTENDS: Dict[SupportedLanguage, JoernFrontend] = {
    lang: FRONTENDS[key] for lang, key in LANGUAGE_TO_FRONTEND_KEY.items()
    if key in FRONTENDS
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
            frontend_key = LANGUAGE_TO_FRONTEND_KEY.get(request.language)
            if not frontend_key:
                raise ValueError(f"Unsupported language: {request.language}")

            frontend = get_frontend(frontend_key)
            if not frontend:
                raise ValueError(f"No frontend available for: {request.language}")

            self._report_progress(100, f"Using specified language: {request.language.value}")

            return {
                "detected_language": request.language,
                "joern_frontend": frontend,
                "detection_method": "explicit",
                "file_stats": {},
            }

        # Auto-detection using frontend registry
        self._report_progress(10, "Scanning source files...")

        include_paths = getattr(request, 'include_paths', None)
        detected_key, file_stats = detect_language_with_stats(source_path, include_paths)

        self._report_progress(50, "Analyzing file distribution...")

        if not detected_key:
            raise ValueError(
                f"No supported source files found in {source_path}. "
                f"Supported languages: {list(FRONTENDS.keys())}"
            )

        # Convert frontend key to SupportedLanguage
        detected_language = FRONTEND_KEY_TO_LANGUAGE.get(detected_key)
        if not detected_language:
            raise ValueError(f"Unknown language key: {detected_key}")

        frontend = get_frontend(detected_key)
        if not frontend:
            raise ValueError(f"No Joern frontend available for {detected_key}")

        # Convert file stats to use language names
        language_stats = {}
        for key, count in file_stats.items():
            lang = FRONTEND_KEY_TO_LANGUAGE.get(key)
            if lang:
                language_stats[lang.value] = count
            else:
                language_stats[key] = count

        self._report_progress(100, f"Detected language: {detected_language.value}")

        logger.info(
            f"Language detection complete: {detected_language.value} "
            f"({file_stats.get(detected_key, 0)} files)"
        )
        logger.info(f"File distribution: {language_stats}")

        return {
            "detected_language": detected_language,
            "joern_frontend": frontend,
            "detection_method": "auto",
            "file_stats": language_stats,
        }

    def _report_progress(self, progress: int, message: str) -> None:
        """Report progress to callback."""
        if self.progress_callback:
            self.progress_callback(progress, message)
        logger.info(f"Detect language step: {progress}% - {message}")
