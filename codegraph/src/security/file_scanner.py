"""
File-Based Security Scanner

Direct file scanning for security vulnerabilities without requiring CPG generation.
This scanner is used for pre-CPG analysis and can detect issues through regex patterns.
"""

import os
import re
import glob
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.security._base import VulnerabilitySeverity, VulnerabilityCategory
from src.security.patterns.python_django import FILE_PATTERNS, FilePattern

logger = logging.getLogger(__name__)


@dataclass
class FileFinding:
    """Represents a security finding from file scanning."""
    pattern_id: str
    pattern_name: str
    severity: VulnerabilitySeverity
    category: VulnerabilityCategory
    file_path: str
    line_number: int
    line_content: str
    match_text: str
    description: str
    cwe_ids: List[str]
    remediation: str
    confidence: float = 0.8  # Default confidence for file-based patterns

    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "pattern_name": self.pattern_name,
            "severity": self.severity.value,
            "category": self.category.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "line_content": self.line_content[:200] + "..." if len(self.line_content) > 200 else self.line_content,
            "match_text": self.match_text[:100] + "..." if len(self.match_text) > 100 else self.match_text,
            "description": self.description,
            "cwe_ids": self.cwe_ids,
            "remediation": self.remediation,
            "confidence": self.confidence,
        }


@dataclass
class ScanResult:
    """Result of a complete security scan."""
    project_path: str
    scan_time: datetime
    duration_seconds: float
    files_scanned: int
    findings: List[FileFinding] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def severity_counts(self) -> Dict[str, int]:
        """Count findings by severity."""
        counts = {s.value: 0 for s in VulnerabilitySeverity}
        for finding in self.findings:
            counts[finding.severity.value] += 1
        return counts

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == VulnerabilitySeverity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == VulnerabilitySeverity.HIGH)

    def to_dict(self) -> Dict[str, Any]:
        """Convert scan result to dictionary."""
        return {
            "project_path": self.project_path,
            "scan_time": self.scan_time.isoformat(),
            "duration_seconds": self.duration_seconds,
            "files_scanned": self.files_scanned,
            "total_findings": len(self.findings),
            "severity_counts": self.severity_counts,
            "findings": [f.to_dict() for f in self.findings],
            "errors": self.errors,
        }


class FileSecurityScanner:
    """
    File-based security scanner for Python/Django projects.

    Scans source files directly using regex patterns to detect
    security vulnerabilities without requiring CPG generation.
    """

    def __init__(
        self,
        patterns: Dict[str, FilePattern] = None,
        exclude_dirs: List[str] = None,
        exclude_files: List[str] = None,
    ):
        """
        Initialize scanner.

        Args:
            patterns: Custom file patterns (uses defaults if None)
            exclude_dirs: Directories to exclude from scanning
            exclude_files: File patterns to exclude
        """
        self.patterns = patterns or FILE_PATTERNS
        self.exclude_dirs = exclude_dirs or [
            '__pycache__', '.git', '.venv', 'venv', 'env',
            'node_modules', '.tox', '.pytest_cache', '.mypy_cache',
            'migrations', 'static', 'media', 'dist', 'build',
        ]
        self.exclude_files = exclude_files or [
            '*_test.py', 'test_*.py', 'conftest.py',
            '*_tests.py', 'tests.py',
        ]

    def scan_project(self, project_path: str) -> ScanResult:
        """
        Scan entire project for security issues.

        Args:
            project_path: Path to project root

        Returns:
            ScanResult with all findings
        """
        start_time = datetime.now()
        project_path = os.path.abspath(project_path)

        if not os.path.isdir(project_path):
            return ScanResult(
                project_path=project_path,
                scan_time=start_time,
                duration_seconds=0,
                files_scanned=0,
                errors=[f"Project path does not exist: {project_path}"],
            )

        findings: List[FileFinding] = []
        errors: List[str] = []
        files_scanned = 0

        # Scan Python files
        python_files = self._find_python_files(project_path)

        for file_path in python_files:
            try:
                file_findings = self._scan_file(file_path, project_path)
                findings.extend(file_findings)
                files_scanned += 1
            except Exception as e:
                errors.append(f"Error scanning {file_path}: {str(e)}")
                logger.error(f"Error scanning {file_path}: {e}")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        return ScanResult(
            project_path=project_path,
            scan_time=start_time,
            duration_seconds=duration,
            files_scanned=files_scanned,
            findings=sorted(findings, key=lambda f: (
                list(VulnerabilitySeverity).index(f.severity),
                f.file_path,
                f.line_number
            )),
            errors=errors,
        )

    def scan_django_settings(self, settings_path: str) -> List[FileFinding]:
        """
        Scan Django settings file specifically.

        Args:
            settings_path: Path to settings.py

        Returns:
            List of findings from settings file
        """
        if not os.path.isfile(settings_path):
            logger.warning(f"Settings file not found: {settings_path}")
            return []

        # Filter patterns relevant to settings files
        settings_patterns = {
            k: v for k, v in self.patterns.items()
            if 'settings' in v.file_pattern or 'django' in k.lower()
        }

        findings = []
        try:
            with open(settings_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')

            for pattern_name, pattern in settings_patterns.items():
                matches = self._find_pattern_matches(content, lines, pattern, settings_path)
                findings.extend(matches)

        except Exception as e:
            logger.error(f"Error scanning settings: {e}")

        return findings

    def scan_for_secrets(self, project_path: str) -> List[FileFinding]:
        """
        Scan project specifically for hardcoded secrets.

        Args:
            project_path: Path to project root

        Returns:
            List of secret-related findings
        """
        secret_patterns = {
            k: v for k, v in self.patterns.items()
            if any(word in k.lower() for word in ['secret', 'password', 'key', 'token', 'cred'])
        }

        findings = []
        python_files = self._find_python_files(project_path)

        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')

                for pattern_name, pattern in secret_patterns.items():
                    matches = self._find_pattern_matches(content, lines, pattern, file_path)
                    findings.extend(matches)

            except Exception as e:
                logger.error(f"Error scanning {file_path} for secrets: {e}")

        return findings

    def _find_python_files(self, project_path: str) -> List[str]:
        """Find all Python files in project, excluding configured directories."""
        python_files = []

        for root, dirs, files in os.walk(project_path):
            # Remove excluded directories
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]

            for file in files:
                if not file.endswith('.py'):
                    continue

                # Check exclude patterns
                if any(glob.fnmatch.fnmatch(file, pattern) for pattern in self.exclude_files):
                    continue

                file_path = os.path.join(root, file)
                python_files.append(file_path)

        return python_files

    def _scan_file(self, file_path: str, project_root: str) -> List[FileFinding]:
        """Scan a single file for security issues."""
        findings = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            logger.error(f"Could not read {file_path}: {e}")
            return []

        # Check which patterns apply to this file
        rel_path = os.path.relpath(file_path, project_root)

        for pattern_name, pattern in self.patterns.items():
            # Check if file matches pattern's file_pattern
            if not glob.fnmatch.fnmatch(rel_path, pattern.file_pattern.lstrip('**/').lstrip('*')):
                # Also check against just filename
                if not glob.fnmatch.fnmatch(os.path.basename(file_path),
                                            pattern.file_pattern.split('/')[-1]):
                    continue

            matches = self._find_pattern_matches(content, lines, pattern, file_path)
            findings.extend(matches)

        return findings

    def _find_pattern_matches(
        self,
        content: str,
        lines: List[str],
        pattern: FilePattern,
        file_path: str
    ) -> List[FileFinding]:
        """Find all matches of a pattern in file content."""
        findings = []

        # Find all regex matches
        for match in pattern.regex.finditer(content):
            match_text = match.group(0)

            # Find line number
            line_start = content[:match.start()].count('\n')
            line_content = lines[line_start] if line_start < len(lines) else ""

            # Check negative regex (safe pattern that should exclude match)
            if pattern.negative_regex:
                # Check in the surrounding context (5 lines before and after)
                start_line = max(0, line_start - 5)
                end_line = min(len(lines), line_start + 6)
                context = '\n'.join(lines[start_line:end_line])

                if pattern.negative_regex.search(context):
                    continue  # Skip this match - safe pattern found

            # Also skip if the match is in a comment
            stripped_line = line_content.lstrip()
            if stripped_line.startswith('#'):
                continue

            finding = FileFinding(
                pattern_id=pattern.id,
                pattern_name=pattern.name,
                severity=pattern.severity,
                category=pattern.category,
                file_path=file_path,
                line_number=line_start + 1,  # 1-indexed
                line_content=line_content.strip(),
                match_text=match_text,
                description=pattern.description,
                cwe_ids=pattern.cwe_ids or [],
                remediation=pattern.remediation,
            )
            findings.append(finding)

        return findings


def scan_project_for_vulnerabilities(project_path: str) -> ScanResult:
    """
    Convenience function to scan a project for security vulnerabilities.

    Args:
        project_path: Path to project root

    Returns:
        ScanResult with all findings
    """
    scanner = FileSecurityScanner()
    return scanner.scan_project(project_path)


def find_django_settings(project_path: str) -> Optional[str]:
    """
    Find Django settings.py file in project.

    Args:
        project_path: Path to project root

    Returns:
        Path to settings.py or None if not found
    """
    # Common locations for settings
    candidates = [
        os.path.join(project_path, 'settings.py'),
        os.path.join(project_path, 'config', 'settings.py'),
    ]

    # Also search for **/settings.py
    for root, dirs, files in os.walk(project_path):
        # Skip common non-source directories
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'venv', 'env', 'node_modules']]

        for file in files:
            if file == 'settings.py':
                candidates.append(os.path.join(root, file))

    # Return first existing candidate
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate

    return None


__all__ = [
    'FileSecurityScanner',
    'FileFinding',
    'ScanResult',
    'scan_project_for_vulnerabilities',
    'find_django_settings',
]
