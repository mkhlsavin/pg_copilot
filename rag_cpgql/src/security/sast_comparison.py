"""
SAST Comparison Module.

Compares RAG-CPGQL security findings with external SAST tools (Bandit, Semgrep)
to calculate precision, recall, and F1 score.

This helps validate the quality of our analysis and identify gaps.
"""

import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SASTFinding:
    """Normalized finding from any SAST tool."""
    tool: str
    rule_id: str
    severity: str
    file_path: str
    line_number: int
    message: str
    cwe_ids: List[str] = field(default_factory=list)

    @property
    def location_key(self) -> str:
        """Key for matching findings by location."""
        # Normalize path separators
        normalized_path = self.file_path.replace('\\', '/')
        # Get just the filename for matching (paths may differ)
        filename = os.path.basename(normalized_path)
        return f"{filename}:{self.line_number}"

    @property
    def category(self) -> str:
        """Categorize finding by type."""
        rule_lower = self.rule_id.lower()
        msg_lower = self.message.lower()

        if 'sql' in rule_lower or 'sql' in msg_lower:
            return 'sql_injection'
        elif 'xss' in rule_lower or 'cross-site' in msg_lower:
            return 'xss'
        elif 'command' in rule_lower or 'shell' in msg_lower or 'os.system' in msg_lower:
            return 'command_injection'
        elif 'pickle' in rule_lower or 'deserial' in msg_lower or 'yaml.load' in msg_lower:
            return 'deserialization'
        elif 'path' in rule_lower or 'traversal' in msg_lower:
            return 'path_traversal'
        elif 'credential' in rule_lower or 'password' in msg_lower or 'secret' in msg_lower:
            return 'hardcoded_credentials'
        elif 'debug' in rule_lower:
            return 'debug_enabled'
        else:
            return 'other'


@dataclass
class ComparisonResult:
    """Result of comparing two sets of findings."""
    our_findings: List[SASTFinding]
    tool_findings: List[SASTFinding]
    matched: List[Tuple[SASTFinding, SASTFinding]]
    only_ours: List[SASTFinding]
    only_theirs: List[SASTFinding]

    @property
    def precision(self) -> float:
        """Precision: What fraction of our findings are confirmed by tool."""
        if not self.our_findings:
            return 0.0
        return len(self.matched) / len(self.our_findings)

    @property
    def recall(self) -> float:
        """Recall: What fraction of tool findings we detected."""
        if not self.tool_findings:
            return 0.0
        return len(self.matched) / len(self.tool_findings)

    @property
    def f1_score(self) -> float:
        """F1 Score: Harmonic mean of precision and recall."""
        p, r = self.precision, self.recall
        if p + r == 0:
            return 0.0
        return 2 * p * r / (p + r)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            'our_count': len(self.our_findings),
            'tool_count': len(self.tool_findings),
            'matched_count': len(self.matched),
            'only_ours_count': len(self.only_ours),
            'only_theirs_count': len(self.only_theirs),
            'precision': round(self.precision, 3),
            'recall': round(self.recall, 3),
            'f1_score': round(self.f1_score, 3),
        }


# Rule mapping: RAG-CPGQL pattern -> (Bandit rules, Semgrep rules)
RULE_MAPPING = {
    'DJANGO_SQL_INJECTION': (['B608'], ['python.django.security.injection.sql']),
    'PYTHON_SQL_001': (['B608'], ['python.django.security.injection.sql']),
    'PYTHON_SQL_002': (['B608'], ['python.lang.security.audit.sqli']),
    'DJANGO_DEBUG_001': (['B201'], ['python.django.security.audit.debug-enabled']),
    'PYTHON_PICKLE_001': (['B301', 'B302'], ['python.lang.security.deserialization']),
    'PYTHON_YAML_001': (['B506'], ['python.lang.security.audit.yaml-load']),
    'PYTHON_EVAL_EXEC': (['B307', 'B102'], ['python.lang.security.audit.exec-detected']),
    'PYTHON_SHELL_001': (['B602', 'B603', 'B604'], ['python.lang.security.audit.subprocess-shell']),
    'PYTHON_HARDCODED_001': (['B105', 'B106', 'B107'], ['python.lang.security.audit.hardcoded-password']),
    'DJANGO_XSS_001': (['B703'], ['python.django.security.audit.xss']),
}


class SASTComparator:
    """
    Compares RAG-CPGQL findings with Bandit and Semgrep.

    Calculates precision, recall, and F1 score for quality assessment.
    """

    def __init__(self, project_path: str):
        """
        Initialize comparator.

        Args:
            project_path: Path to the project being analyzed
        """
        self.project_path = Path(project_path)
        self._bandit_available = None
        self._semgrep_available = None

    def _find_executable(self, name: str) -> Optional[str]:
        """Find executable, checking common Windows paths."""
        import shutil

        # Try standard PATH first
        exe = shutil.which(name)
        if exe:
            return exe

        # Windows user Scripts directory
        user_scripts = Path.home() / "AppData" / "Roaming" / "Python" / "Python313" / "Scripts"
        for ext in ['', '.exe']:
            path = user_scripts / f"{name}{ext}"
            if path.exists():
                return str(path)

        # Also try pysemgrep for semgrep
        if name == 'semgrep':
            pysemgrep = self._find_executable('pysemgrep')
            if pysemgrep:
                return pysemgrep

        return None

    def _check_bandit(self) -> bool:
        """Check if Bandit is available."""
        if self._bandit_available is not None:
            return self._bandit_available
        try:
            exe = self._find_executable('bandit')
            if not exe:
                self._bandit_available = False
                return False

            result = subprocess.run(
                [exe, '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            self._bandit_available = result.returncode == 0
            self._bandit_exe = exe if self._bandit_available else None
        except (subprocess.SubprocessError, FileNotFoundError):
            self._bandit_available = False
        return self._bandit_available

    def _check_semgrep(self) -> bool:
        """Check if Semgrep is available."""
        if self._semgrep_available is not None:
            return self._semgrep_available
        try:
            exe = self._find_executable('pysemgrep')  # Use pysemgrep directly
            if not exe:
                exe = self._find_executable('semgrep')
            if not exe:
                self._semgrep_available = False
                return False

            result = subprocess.run(
                [exe, '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            self._semgrep_available = result.returncode == 0
            self._semgrep_exe = exe if self._semgrep_available else None
        except (subprocess.SubprocessError, FileNotFoundError):
            self._semgrep_available = False
        return self._semgrep_available

    def run_bandit(self, exclude_dirs: Optional[List[str]] = None) -> List[SASTFinding]:
        """
        Run Bandit on the project and parse results.

        Args:
            exclude_dirs: Directories to exclude from scanning

        Returns:
            List of findings from Bandit
        """
        if not self._check_bandit():
            logger.warning("Bandit not available")
            return []

        exclude_dirs = exclude_dirs or ['venv', '.venv', 'node_modules', '__pycache__']
        exclude_arg = ','.join(exclude_dirs)

        cmd = [
            self._bandit_exe or 'bandit',
            '-r', str(self.project_path),
            '-f', 'json',
            '--exclude', exclude_arg,
            '-ll',  # Only medium and higher
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes
                cwd=str(self.project_path)
            )

            # Bandit returns non-zero if findings exist
            if result.stdout:
                # Strip progress line if present (e.g., "Working... --- 100%")
                output = result.stdout
                if output.startswith('Working'):
                    # Find the start of JSON
                    json_start = output.find('{')
                    if json_start != -1:
                        output = output[json_start:]
                data = json.loads(output)
                return self._parse_bandit_results(data)
            else:
                logger.info("Bandit found no issues")
                return []

        except subprocess.TimeoutExpired:
            logger.error("Bandit timed out")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Bandit output: {e}")
            return []
        except Exception as e:
            logger.error(f"Error running Bandit: {e}")
            return []

    def _parse_bandit_results(self, data: Dict[str, Any]) -> List[SASTFinding]:
        """Parse Bandit JSON output into SASTFinding objects."""
        findings = []

        for result in data.get('results', []):
            severity = result.get('issue_severity', 'LOW').lower()
            # Map Bandit severity
            if severity == 'high':
                severity = 'high'
            elif severity == 'medium':
                severity = 'medium'
            else:
                severity = 'low'

            # Extract CWE if available
            cwe_ids = []
            cwe = result.get('issue_cwe', {})
            if isinstance(cwe, dict) and cwe.get('id'):
                cwe_ids.append(f"CWE-{cwe['id']}")

            findings.append(SASTFinding(
                tool='bandit',
                rule_id=result.get('test_id', 'B000'),
                severity=severity,
                file_path=result.get('filename', ''),
                line_number=result.get('line_number', 0),
                message=result.get('issue_text', ''),
                cwe_ids=cwe_ids,
            ))

        logger.info(f"Bandit found {len(findings)} issues")
        return findings

    def run_semgrep(
        self,
        config: str = 'p/security-audit',
        exclude_dirs: Optional[List[str]] = None
    ) -> List[SASTFinding]:
        """
        Run Semgrep on the project and parse results.

        Args:
            config: Semgrep config/ruleset to use
            exclude_dirs: Directories to exclude

        Returns:
            List of findings from Semgrep
        """
        if not self._check_semgrep():
            logger.warning("Semgrep not available")
            return []

        exclude_dirs = exclude_dirs or ['venv', '.venv', 'node_modules', '__pycache__']

        cmd = [
            self._semgrep_exe or 'semgrep',
            '--config', config,
            '--json',
            '--no-git-ignore',
            str(self.project_path),
        ]

        # Add exclude patterns
        for d in exclude_dirs:
            cmd.extend(['--exclude', d])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes
            )

            if result.stdout:
                data = json.loads(result.stdout)
                return self._parse_semgrep_results(data)
            else:
                logger.info("Semgrep found no issues")
                return []

        except subprocess.TimeoutExpired:
            logger.error("Semgrep timed out")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Semgrep output: {e}")
            return []
        except Exception as e:
            logger.error(f"Error running Semgrep: {e}")
            return []

    def _parse_semgrep_results(self, data: Dict[str, Any]) -> List[SASTFinding]:
        """Parse Semgrep JSON output into SASTFinding objects."""
        findings = []

        for result in data.get('results', []):
            # Map Semgrep severity
            severity_map = {
                'ERROR': 'high',
                'WARNING': 'medium',
                'INFO': 'low',
            }
            severity = severity_map.get(
                result.get('extra', {}).get('severity', 'INFO'),
                'low'
            )

            # Extract CWE
            cwe_ids = []
            metadata = result.get('extra', {}).get('metadata', {})
            if 'cwe' in metadata:
                cwe = metadata['cwe']
                if isinstance(cwe, list):
                    cwe_ids.extend([c if c.startswith('CWE') else f"CWE-{c}" for c in cwe])
                elif isinstance(cwe, str):
                    cwe_ids.append(cwe if cwe.startswith('CWE') else f"CWE-{cwe}")

            findings.append(SASTFinding(
                tool='semgrep',
                rule_id=result.get('check_id', ''),
                severity=severity,
                file_path=result.get('path', ''),
                line_number=result.get('start', {}).get('line', 0),
                message=result.get('extra', {}).get('message', ''),
                cwe_ids=cwe_ids,
            ))

        logger.info(f"Semgrep found {len(findings)} issues")
        return findings

    def convert_our_findings(
        self,
        findings: List[Dict[str, Any]]
    ) -> List[SASTFinding]:
        """
        Convert RAG-CPGQL findings to SASTFinding format.

        Args:
            findings: Our findings in dict format

        Returns:
            List of SASTFinding objects
        """
        converted = []

        for f in findings:
            converted.append(SASTFinding(
                tool='rag-cpgql',
                rule_id=f.get('pattern_id', 'UNKNOWN'),
                severity=f.get('severity', 'info'),
                file_path=f.get('file_path', ''),
                line_number=f.get('line_number', 0),
                message=f.get('description', ''),
                cwe_ids=f.get('cwe_ids', []),
            ))

        return converted

    def compare_findings(
        self,
        our_findings: List[SASTFinding],
        tool_findings: List[SASTFinding],
        match_by_location: bool = True,
        match_by_category: bool = True
    ) -> ComparisonResult:
        """
        Compare two sets of findings.

        Args:
            our_findings: Our findings
            tool_findings: External tool findings
            match_by_location: Match by file:line
            match_by_category: Also require category match

        Returns:
            ComparisonResult with metrics
        """
        matched = []
        only_ours = []
        matched_tool_indices: Set[int] = set()

        for our in our_findings:
            found_match = False

            for idx, theirs in enumerate(tool_findings):
                if idx in matched_tool_indices:
                    continue

                # Check location match
                location_match = (
                    our.location_key == theirs.location_key
                    if match_by_location else True
                )

                # Check category match
                category_match = (
                    our.category == theirs.category
                    if match_by_category else True
                )

                # Allow some line number flexibility (within 5 lines)
                if not location_match and match_by_location:
                    our_file = os.path.basename(our.file_path)
                    their_file = os.path.basename(theirs.file_path)
                    if our_file == their_file:
                        line_diff = abs(our.line_number - theirs.line_number)
                        if line_diff <= 5:
                            location_match = True

                if location_match and category_match:
                    matched.append((our, theirs))
                    matched_tool_indices.add(idx)
                    found_match = True
                    break

            if not found_match:
                only_ours.append(our)

        only_theirs = [
            f for idx, f in enumerate(tool_findings)
            if idx not in matched_tool_indices
        ]

        return ComparisonResult(
            our_findings=our_findings,
            tool_findings=tool_findings,
            matched=matched,
            only_ours=only_ours,
            only_theirs=only_theirs,
        )

    def generate_comparison_report(
        self,
        our_findings: List[Dict[str, Any]],
        run_bandit: bool = True,
        run_semgrep: bool = True
    ) -> Dict[str, Any]:
        """
        Generate comprehensive comparison report.

        Args:
            our_findings: Our findings in dict format
            run_bandit: Whether to run Bandit comparison
            run_semgrep: Whether to run Semgrep comparison

        Returns:
            Report dictionary with metrics and analysis
        """
        report = {
            'project_path': str(self.project_path),
            'our_findings_count': len(our_findings),
            'comparisons': {},
            'summary': {},
        }

        our_sast = self.convert_our_findings(our_findings)

        if run_bandit:
            bandit_findings = self.run_bandit()
            if bandit_findings:
                comparison = self.compare_findings(our_sast, bandit_findings)
                report['comparisons']['bandit'] = {
                    'tool_name': 'Bandit',
                    'tool_findings': len(bandit_findings),
                    **comparison.to_dict(),
                    'only_ours_details': [
                        {'rule': f.rule_id, 'file': f.file_path, 'line': f.line_number}
                        for f in comparison.only_ours[:10]  # Limit details
                    ],
                    'only_theirs_details': [
                        {'rule': f.rule_id, 'file': f.file_path, 'line': f.line_number}
                        for f in comparison.only_theirs[:10]
                    ],
                }

        if run_semgrep:
            semgrep_findings = self.run_semgrep()
            if semgrep_findings:
                comparison = self.compare_findings(our_sast, semgrep_findings)
                report['comparisons']['semgrep'] = {
                    'tool_name': 'Semgrep',
                    'tool_findings': len(semgrep_findings),
                    **comparison.to_dict(),
                    'only_ours_details': [
                        {'rule': f.rule_id, 'file': f.file_path, 'line': f.line_number}
                        for f in comparison.only_ours[:10]
                    ],
                    'only_theirs_details': [
                        {'rule': f.rule_id, 'file': f.file_path, 'line': f.line_number}
                        for f in comparison.only_theirs[:10]
                    ],
                }

        # Calculate summary
        if report['comparisons']:
            f1_scores = [
                c['f1_score']
                for c in report['comparisons'].values()
            ]
            precisions = [
                c['precision']
                for c in report['comparisons'].values()
            ]
            recalls = [
                c['recall']
                for c in report['comparisons'].values()
            ]

            report['summary'] = {
                'average_f1': round(sum(f1_scores) / len(f1_scores), 3) if f1_scores else 0,
                'average_precision': round(sum(precisions) / len(precisions), 3) if precisions else 0,
                'average_recall': round(sum(recalls) / len(recalls), 3) if recalls else 0,
                'tools_compared': list(report['comparisons'].keys()),
            }

        return report

    def generate_markdown_report(
        self,
        our_findings: List[Dict[str, Any]],
        run_bandit: bool = True,
        run_semgrep: bool = True,
        language: str = 'en'
    ) -> str:
        """
        Generate comparison report in Markdown format.

        Args:
            our_findings: Our findings
            run_bandit: Run Bandit comparison
            run_semgrep: Run Semgrep comparison
            language: Report language ('en' or 'ru')

        Returns:
            Markdown formatted report
        """
        report_data = self.generate_comparison_report(
            our_findings, run_bandit, run_semgrep
        )

        # Headers based on language
        if language == 'ru':
            title = "## Сравнение с внешними SAST-инструментами"
            summary_header = "### Сводка"
            our_findings_label = "Наши находки"
            tool_findings_label = "Находки инструмента"
            matched_label = "Совпадения"
            only_ours_label = "Только у нас"
            only_theirs_label = "Только у инструмента"
            avg_f1_label = "Средний F1"
            strengths_label = "Наши преимущества"
            gaps_label = "Области для улучшения"
        else:
            title = "## SAST Comparison Report"
            summary_header = "### Summary"
            our_findings_label = "Our findings"
            tool_findings_label = "Tool findings"
            matched_label = "Matched"
            only_ours_label = "Only ours"
            only_theirs_label = "Only theirs"
            avg_f1_label = "Average F1"
            strengths_label = "Our strengths"
            gaps_label = "Areas for improvement"

        lines = [title, ""]

        for tool_name, data in report_data.get('comparisons', {}).items():
            lines.append(f"### {data.get('tool_name', tool_name)}")
            lines.append("")
            lines.append(f"| Metric | Value |")
            lines.append("|--------|-------|")
            lines.append(f"| {our_findings_label} | {data.get('our_count', 0)} |")
            lines.append(f"| {tool_findings_label} | {data.get('tool_count', 0)} |")
            lines.append(f"| {matched_label} | {data.get('matched_count', 0)} |")
            lines.append(f"| {only_ours_label} | {data.get('only_ours_count', 0)} |")
            lines.append(f"| {only_theirs_label} | {data.get('only_theirs_count', 0)} |")
            lines.append(f"| Precision | {data.get('precision', 0):.1%} |")
            lines.append(f"| Recall | {data.get('recall', 0):.1%} |")
            lines.append(f"| **F1 Score** | **{data.get('f1_score', 0):.1%}** |")
            lines.append("")

        summary = report_data.get('summary', {})
        if summary:
            lines.append(summary_header)
            lines.append("")
            lines.append(f"- **{avg_f1_label}:** {summary.get('average_f1', 0):.1%}")
            lines.append(f"- **Precision:** {summary.get('average_precision', 0):.1%}")
            lines.append(f"- **Recall:** {summary.get('average_recall', 0):.1%}")
            lines.append("")

            # Analysis
            if summary.get('average_precision', 0) > summary.get('average_recall', 0):
                lines.append(f"**{strengths_label}:** High precision - fewer false positives due to taint analysis")
            else:
                lines.append(f"**{gaps_label}:** Consider expanding pattern coverage")

        return '\n'.join(lines)


def install_sast_tools() -> Dict[str, bool]:
    """
    Install Bandit and Semgrep if not available.

    Returns:
        Dict with installation status for each tool
    """
    status = {}

    # Try to install Bandit
    try:
        result = subprocess.run(
            ['pip', 'install', 'bandit'],
            capture_output=True,
            text=True,
            timeout=120
        )
        status['bandit'] = result.returncode == 0
        if status['bandit']:
            logger.info("Bandit installed successfully")
        else:
            logger.warning(f"Bandit installation failed: {result.stderr}")
    except Exception as e:
        logger.error(f"Failed to install Bandit: {e}")
        status['bandit'] = False

    # Try to install Semgrep
    try:
        result = subprocess.run(
            ['pip', 'install', 'semgrep'],
            capture_output=True,
            text=True,
            timeout=300
        )
        status['semgrep'] = result.returncode == 0
        if status['semgrep']:
            logger.info("Semgrep installed successfully")
        else:
            logger.warning(f"Semgrep installation failed: {result.stderr}")
    except Exception as e:
        logger.error(f"Failed to install Semgrep: {e}")
        status['semgrep'] = False

    return status


__all__ = [
    'SASTComparator',
    'SASTFinding',
    'ComparisonResult',
    'RULE_MAPPING',
    'install_sast_tools',
]
