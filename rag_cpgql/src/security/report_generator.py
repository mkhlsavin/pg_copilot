"""
Security Audit Report Generator

Generates comprehensive security audit reports in multiple formats:
- JSON (for CI/CD integration)
- Markdown (for documentation)
- SARIF (for GitHub Security Alerts)

Supports multiple languages (en, ru) via ReportLocalizer.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from src.security._base import VulnerabilitySeverity, VulnerabilityCategory
from src.security.file_scanner import FileFinding, ScanResult
from src.security.report_localizer import ReportLocalizer, get_localizer


@dataclass
class SecurityAuditReport:
    """
    Consolidated security audit report.

    Aggregates findings from multiple sources:
    - File-based scanning
    - CPG-based SAST
    - DLP scanning
    - D3FEND hardening checks
    """
    project_name: str
    project_path: str
    audit_time: datetime
    duration_seconds: float

    # Findings from different sources
    file_findings: List[FileFinding] = field(default_factory=list)
    cpg_findings: List[Dict[str, Any]] = field(default_factory=list)
    dlp_findings: List[Dict[str, Any]] = field(default_factory=list)
    hardening_findings: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    files_scanned: int = 0
    patterns_checked: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def all_findings(self) -> List[Dict[str, Any]]:
        """Get all findings as dictionaries (excluding D3FEND hardening findings)."""
        findings = []

        # Add file findings
        for f in self.file_findings:
            findings.append(f.to_dict())

        # Add other findings (already dicts)
        findings.extend(self.cpg_findings)
        findings.extend(self.dlp_findings)
        # Note: hardening_findings are NOT included here - they're rendered separately
        # in D3FEND compliance section

        return findings

    @property
    def all_findings_including_hardening(self) -> List[Dict[str, Any]]:
        """Get all findings including D3FEND hardening (for JSON/SARIF export)."""
        findings = self.all_findings.copy()
        findings.extend(self.hardening_findings)
        return findings

    @property
    def severity_counts(self) -> Dict[str, int]:
        """Count all findings by severity."""
        counts = {s.value: 0 for s in VulnerabilitySeverity}

        for finding in self.all_findings:
            severity = finding.get('severity', 'info')
            if severity in counts:
                counts[severity] += 1

        return counts

    @property
    def critical_count(self) -> int:
        return self.severity_counts.get('critical', 0)

    @property
    def high_count(self) -> int:
        return self.severity_counts.get('high', 0)

    @property
    def medium_count(self) -> int:
        return self.severity_counts.get('medium', 0)

    @property
    def total_findings(self) -> int:
        return len(self.all_findings)

    def to_json(self, indent: int = 2) -> str:
        """Generate JSON report."""
        report = {
            "report_metadata": {
                "project_name": self.project_name,
                "project_path": self.project_path,
                "audit_time": self.audit_time.isoformat(),
                "duration_seconds": self.duration_seconds,
                "files_scanned": self.files_scanned,
                "patterns_checked": self.patterns_checked,
                "report_version": "1.0",
            },
            "summary": {
                "total_findings": self.total_findings,
                "severity_counts": self.severity_counts,
                "critical_issues": self.critical_count,
                "high_issues": self.high_count,
            },
            "findings": self.all_findings,
            "hardening_findings": self.hardening_findings,
            "errors": self.errors,
        }
        return json.dumps(report, indent=indent, default=str)

    def to_markdown(self, language: str = 'en') -> str:
        """
        Generate Markdown report with localization.

        Args:
            language: Language code ('en' or 'ru')

        Returns:
            Markdown formatted report string
        """
        loc = get_localizer(language)
        lines = []

        # Header
        lines.append(f"# {loc.t('security_audit_report')}: {self.project_name}")
        lines.append("")
        lines.append(f"**{loc.t('project_path')}:** `{self.project_path}`")
        lines.append(f"**{loc.t('audit_time')}:** {self.audit_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**{loc.t('duration')}:** {self.duration_seconds:.2f} {loc.t('duration_seconds')}")
        lines.append(f"**{loc.t('files_scanned')}:** {self.files_scanned}")
        lines.append("")

        # Executive Summary
        lines.append(f"## {loc.t('executive_summary')}")
        lines.append("")
        lines.append(f"| {loc.t('severity')} | {loc.t('count')} |")
        lines.append("|----------|-------|")
        for severity, count in self.severity_counts.items():
            emoji = loc.severity_emoji(severity)
            label = loc.severity_label(severity)
            lines.append(f"| {emoji} {label} | {count} |")
        lines.append(f"| **{loc.t('total')}** | **{self.total_findings}** |")
        lines.append("")

        # Risk Assessment
        if self.critical_count > 0:
            lines.append(f"> **{loc.t('critical_risk')}**")
            lines.append("")
        elif self.high_count > 0:
            lines.append(f"> **{loc.t('high_risk')}**")
            lines.append("")

        # D3FEND Hardening Section (if available)
        d3fend_lines = self._render_d3fend_section(loc)
        if d3fend_lines:
            lines.extend(d3fend_lines)
            lines.append("")

        # Findings by Severity
        for severity in ['critical', 'high', 'medium', 'low', 'info']:
            severity_findings = [f for f in self.all_findings if f.get('severity') == severity]
            if severity_findings:
                emoji = loc.severity_emoji(severity)
                label = loc.severity_label(severity)
                lines.append(f"## {emoji} {label} {loc.t('severity_findings')} ({len(severity_findings)})")
                lines.append("")

                for i, finding in enumerate(severity_findings, 1):
                    lines.append(f"### {i}. {finding.get('pattern_name', 'Unknown Pattern')}")
                    lines.append("")
                    lines.append(f"**{loc.t('pattern_id')}:** `{finding.get('pattern_id', 'N/A')}`")

                    # File and method with proper context
                    file_path = finding.get('file_path', 'N/A')
                    containing_method = finding.get('containing_method', '')
                    line_number = finding.get('line_number', 'N/A')

                    if containing_method and containing_method != 'unknown':
                        lines.append(f"**{loc.t('file')}:** `{file_path}`")
                        lines.append(f"**{loc.t('method')}:** `{containing_method}`")
                        lines.append(f"**{loc.t('line')}:** {line_number}")
                    else:
                        lines.append(f"**{loc.t('file')}:** `{file_path}:{line_number}`")

                    cwe_ids = finding.get('cwe_ids', [])
                    if cwe_ids:
                        cwe_links = [f"[{cwe}](https://cwe.mitre.org/data/definitions/{cwe.replace('CWE-', '')}.html)"
                                    for cwe in cwe_ids]
                        lines.append(f"**{loc.t('cwe')}:** {', '.join(cwe_links)}")

                    lines.append("")
                    # Use localized description if available
                    description = loc.localize_description(finding)
                    lines.append(f"**{loc.t('description')}:** {description}")
                    lines.append("")

                    line_content = finding.get('line_content', '') or finding.get('code', '')
                    if line_content:
                        lines.append(f"**{loc.t('vulnerable_code')}:**")
                        lines.append("```python")
                        lines.append(line_content[:200] + ('...' if len(line_content) > 200 else ''))
                        lines.append("```")
                        lines.append("")

                    # Use localized remediation if available
                    remediation = loc.localize_remediation(finding)
                    if remediation:
                        lines.append(f"**{loc.t('remediation')}:**")
                        lines.append(remediation)
                        lines.append("")

                    lines.append("---")
                    lines.append("")

        # Recommendations Section
        recs_lines = self._render_recommendations_section(loc)
        if recs_lines:
            lines.extend(recs_lines)
            lines.append("")

        # Errors
        if self.errors:
            lines.append(f"## {loc.t('errors_during_scan')}")
            lines.append("")
            for error in self.errors:
                lines.append(f"- {error}")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append(f"*{loc.t('generated_by')}*")

        return '\n'.join(lines)

    def _render_d3fend_section(self, loc: ReportLocalizer, detected_language: str = 'python') -> List[str]:
        """Render D3FEND compliance section with N/A marking for inapplicable techniques."""
        # Always show D3FEND section, even without findings (to show N/A status)
        lines = []
        lines.append(f"## {loc.t('d3fend_compliance')}")
        lines.append("")

        # C/C++ only techniques (not applicable for Python)
        C_ONLY_TECHNIQUES = {'D3-VI', 'D3-RN', 'D3-PV', 'D3-IRV', 'D3-TL', 'D3-VTV', 'D3-MBSV', 'D3-NPC'}
        # Techniques applicable to all languages including Python
        PYTHON_APPLICABLE = {'D3-CS', 'D3-DLV', 'D3-OLV'}

        # Header with applicability column
        lines.append(f"| {loc.t('technique')} | {loc.t('technique_name')} | {loc.t('found')} | {loc.t('status')} | {loc.t('applicability')} |")
        lines.append("|---------|----------|---------|--------|---------------|")

        # Group by D3FEND technique
        by_technique: Dict[str, List[Dict]] = {}
        for f in self.hardening_findings:
            tech = f.get('d3fend_id', 'UNKNOWN')
            if tech not in by_technique:
                by_technique[tech] = []
            by_technique[tech].append(f)

        total_applicable = 0
        passing_applicable = 0

        # Standard D3FEND techniques to check
        all_techniques = [
            'D3-VI', 'D3-CS', 'D3-IRV', 'D3-PV', 'D3-RN',
            'D3-TL', 'D3-VTV', 'D3-MBSV', 'D3-NPC', 'D3-DLV', 'D3-OLV'
        ]

        for tech in all_techniques:
            findings = by_technique.get(tech, [])
            count = len(findings)
            tech_name = loc.d3fend_technique_name(tech)

            # Determine applicability for Python
            if detected_language == 'python' and tech in C_ONLY_TECHNIQUES:
                status = "N/A"
                applicability = loc.t('c_cpp_only')
                count_str = "-"
            else:
                total_applicable += 1
                if count > 0:
                    status = "⚠️"
                    count_str = str(count)
                else:
                    status = "✅"
                    passing_applicable += 1
                    count_str = "0"
                applicability = loc.t('python_applicable') if detected_language == 'python' else loc.t('applicable')

            lines.append(f"| {tech} | {tech_name} | {count_str} | {status} | {applicability} |")

        # Compliance score (only for applicable techniques)
        if total_applicable > 0:
            score = (passing_applicable / total_applicable) * 100
            lines.append("")
            lines.append(f"**{loc.t('compliance_score')}:** {score:.0f}% ({passing_applicable}/{total_applicable} {loc.t('applicable_techniques')})")

        # Add detailed findings for D3-CS (Credential Scrubbing) if any
        d3cs_lines = self._render_d3fend_findings_detail(loc, by_technique)
        if d3cs_lines:
            lines.append("")
            lines.extend(d3cs_lines)

        return lines

    def _render_d3fend_findings_detail(self, loc: ReportLocalizer, by_technique: Dict[str, List[Dict]]) -> List[str]:
        """Render detailed D3FEND findings, especially for credentials (D3-CS)."""
        lines = []

        # Render D3-CS (Credential Scrubbing) findings - these are critical
        if 'D3-CS' in by_technique and by_technique['D3-CS']:
            lines.append(f"### {loc.t('credential_findings_detail')}")
            lines.append("")
            for i, finding in enumerate(by_technique['D3-CS'], 1):
                filename = finding.get('filename', finding.get('file_path', 'unknown'))
                line_num = finding.get('line_number', 0)
                method = finding.get('method_name', finding.get('containing_method', 'unknown'))
                code = finding.get('code_snippet', finding.get('code', ''))
                # Use localized remediation
                remediation = loc.localize_remediation(finding) or loc.t('use_env_variables')

                lines.append(f"**{i}. {filename}:{line_num}**")
                if method and method != 'unknown':
                    lines.append(f"   {loc.t('method')}: `{method}`")
                if code:
                    lines.append(f"   ```python")
                    lines.append(f"   {code[:150]}{'...' if len(code) > 150 else ''}")
                    lines.append(f"   ```")
                lines.append(f"   {loc.t('remediation')}: {remediation}")
                lines.append("")

        return lines

    def _render_recommendations_section(self, loc: ReportLocalizer) -> List[str]:
        """Render recommendations section based on actual findings."""
        if not self.all_findings:
            return []

        lines = []
        lines.append(f"## {loc.t('recommendations')}")
        lines.append("")

        # Group findings by category/type for targeted recommendations
        recommendations = []

        # Check for SQL injection
        sql_findings = [f for f in self.all_findings
                       if 'sql' in f.get('pattern_id', '').lower()
                       or 'execute' in f.get('pattern_name', '').lower()]
        if sql_findings:
            recommendations.append({
                'title': loc.t('sql_injection'),
                'problem': loc.t('sql_injection_desc'),
                'solution': loc.t('use_parameterized_queries'),
                'count': len(sql_findings),
                'priority': loc.t('priority_high'),
                'effort': loc.t('effort_low'),
                'example': '''# Было:
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# Стало:
cursor.execute("SELECT * FROM users WHERE id = %s", [user_id])''' if loc.language == 'ru' else '''# Before:
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# After:
cursor.execute("SELECT * FROM users WHERE id = %s", [user_id])'''
            })

        # Check for XSS
        xss_findings = [f for f in self.all_findings
                       if 'xss' in f.get('pattern_id', '').lower()
                       or 'mark_safe' in str(f.get('line_content', '')).lower()]
        if xss_findings:
            recommendations.append({
                'title': loc.t('xss'),
                'problem': loc.t('xss_desc'),
                'solution': loc.t('escape_output'),
                'count': len(xss_findings),
                'priority': loc.t('priority_high'),
                'effort': loc.t('effort_low'),
            })

        # Check for hardcoded credentials
        cred_findings = [f for f in self.all_findings
                        if 'credential' in f.get('pattern_id', '').lower()
                        or 'password' in str(f.get('line_content', '')).lower()]
        if cred_findings:
            recommendations.append({
                'title': loc.t('hardcoded_credentials'),
                'problem': loc.t('hardcoded_credentials_desc'),
                'solution': loc.t('use_env_variables'),
                'count': len(cred_findings),
                'priority': loc.t('priority_high'),
                'effort': loc.t('effort_medium'),
            })

        # Check for auth bypass
        auth_findings = [f for f in self.all_findings
                        if 'auth' in f.get('pattern_id', '').lower()
                        or 'csrf' in f.get('pattern_id', '').lower()]
        if auth_findings:
            recommendations.append({
                'title': loc.t('auth_bypass'),
                'problem': loc.t('auth_bypass_desc'),
                'solution': loc.t('add_auth_decorator'),
                'count': len(auth_findings),
                'priority': loc.t('priority_medium'),
                'effort': loc.t('effort_low'),
            })

        # Render recommendations
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"### {i}. {rec['title']} ({rec['count']} {loc.t('findings').lower()})")
            lines.append("")
            lines.append(f"**{loc.t('problem')}:** {rec['problem']}")
            lines.append(f"**{loc.t('solution')}:** {rec['solution']}")
            lines.append(f"**{loc.t('priority')}:** {rec['priority']}")
            lines.append(f"**{loc.t('effort')}:** {rec['effort']}")

            if 'example' in rec:
                lines.append("")
                lines.append(f"**{loc.t('example')}:**")
                lines.append("```python")
                lines.append(rec['example'])
                lines.append("```")

            lines.append("")

        return lines

    def to_sarif(self) -> Dict[str, Any]:
        """
        Generate SARIF (Static Analysis Results Interchange Format) report.

        SARIF is the standard format for static analysis results, supported by
        GitHub Security Alerts, Azure DevOps, and many other tools.
        """
        # Build rules from unique patterns
        rules = {}
        results = []

        for finding in self.all_findings:
            pattern_id = finding.get('pattern_id', 'UNKNOWN')
            severity = finding.get('severity', 'info')

            # Create rule if not exists
            if pattern_id not in rules:
                rules[pattern_id] = {
                    "id": pattern_id,
                    "name": finding.get('pattern_name', pattern_id),
                    "shortDescription": {
                        "text": finding.get('pattern_name', pattern_id)
                    },
                    "fullDescription": {
                        "text": finding.get('description', '')
                    },
                    "help": {
                        "text": finding.get('remediation', ''),
                        "markdown": finding.get('remediation', '')
                    },
                    "defaultConfiguration": {
                        "level": self._sarif_level(severity)
                    },
                    "properties": {
                        "tags": finding.get('cwe_ids', []),
                        "security-severity": self._sarif_security_severity(severity),
                    }
                }

            # Create result
            file_path = finding.get('file_path', '')
            line_number = finding.get('line_number', 1)

            result = {
                "ruleId": pattern_id,
                "level": self._sarif_level(severity),
                "message": {
                    "text": finding.get('description', '')
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": file_path.replace('\\', '/'),
                            },
                            "region": {
                                "startLine": line_number,
                                "startColumn": 1,
                            }
                        }
                    }
                ],
            }

            # Add code snippet if available
            line_content = finding.get('line_content', '')
            if line_content:
                result["locations"][0]["physicalLocation"]["region"]["snippet"] = {
                    "text": line_content
                }

            results.append(result)

        # Build SARIF document
        sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "RAG-CPGQL Security Scanner",
                            "version": "1.0.0",
                            "informationUri": "https://github.com/rag-cpgql",
                            "rules": list(rules.values()),
                        }
                    },
                    "results": results,
                    "invocations": [
                        {
                            "executionSuccessful": len(self.errors) == 0,
                            "startTimeUtc": self.audit_time.isoformat() + "Z",
                        }
                    ],
                }
            ]
        }

        return sarif

    def _severity_emoji(self, severity: str) -> str:
        """Get emoji for severity level."""
        return {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢',
            'info': '🔵',
        }.get(severity, '⚪')

    def _sarif_level(self, severity: str) -> str:
        """Convert severity to SARIF level."""
        return {
            'critical': 'error',
            'high': 'error',
            'medium': 'warning',
            'low': 'note',
            'info': 'note',
        }.get(severity, 'note')

    def _sarif_security_severity(self, severity: str) -> str:
        """Convert severity to SARIF security-severity score."""
        return {
            'critical': '9.0',
            'high': '7.0',
            'medium': '5.0',
            'low': '3.0',
            'info': '1.0',
        }.get(severity, '1.0')


class ReportGenerator:
    """
    Report generator for security audit results.

    Supports multiple output formats and can combine results from
    different scanning sources.
    """

    def __init__(self):
        self.report: Optional[SecurityAuditReport] = None

    def create_report(
        self,
        project_name: str,
        project_path: str,
        scan_result: Optional[ScanResult] = None,
    ) -> SecurityAuditReport:
        """
        Create a new security audit report.

        Args:
            project_name: Name of the project
            project_path: Path to project root
            scan_result: Result from file-based scanning

        Returns:
            SecurityAuditReport instance
        """
        self.report = SecurityAuditReport(
            project_name=project_name,
            project_path=project_path,
            audit_time=datetime.now(),
            duration_seconds=0,
        )

        if scan_result:
            self.report.file_findings = scan_result.findings
            self.report.files_scanned = scan_result.files_scanned
            self.report.duration_seconds = scan_result.duration_seconds
            self.report.errors = scan_result.errors

        return self.report

    def add_cpg_findings(self, findings: List[Dict[str, Any]]) -> None:
        """Add findings from CPG-based analysis."""
        if self.report:
            self.report.cpg_findings.extend(findings)

    def add_dlp_findings(self, findings: List[Dict[str, Any]]) -> None:
        """Add findings from DLP scanning."""
        if self.report:
            self.report.dlp_findings.extend(findings)

    def add_hardening_findings(self, findings: List[Dict[str, Any]]) -> None:
        """Add findings from D3FEND hardening checks."""
        if self.report:
            self.report.hardening_findings.extend(findings)

    def save_report(
        self,
        output_dir: str,
        formats: List[str] = None,
        base_filename: str = "security_audit",
        language: str = 'en'
    ) -> Dict[str, str]:
        """
        Save report in specified formats.

        Args:
            output_dir: Directory to save reports
            formats: List of formats ['json', 'markdown', 'sarif']
            base_filename: Base name for output files
            language: Language code for markdown report ('en' or 'ru')

        Returns:
            Dict mapping format to output file path
        """
        if not self.report:
            raise ValueError("No report created. Call create_report first.")

        formats = formats or ['json', 'markdown', 'sarif']
        os.makedirs(output_dir, exist_ok=True)

        output_files = {}

        if 'json' in formats:
            json_path = os.path.join(output_dir, f"{base_filename}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                f.write(self.report.to_json())
            output_files['json'] = json_path

        if 'markdown' in formats or 'md' in formats:
            md_path = os.path.join(output_dir, f"{base_filename}.md")
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(self.report.to_markdown(language=language))
            output_files['markdown'] = md_path

        if 'sarif' in formats:
            sarif_path = os.path.join(output_dir, f"{base_filename}.sarif")
            with open(sarif_path, 'w', encoding='utf-8') as f:
                json.dump(self.report.to_sarif(), f, indent=2)
            output_files['sarif'] = sarif_path

        return output_files


def generate_quick_report(scan_result: ScanResult, output_path: str) -> str:
    """
    Generate a quick Markdown report from scan results.

    Args:
        scan_result: Result from file-based scanning
        output_path: Path to save the report

    Returns:
        Path to generated report
    """
    project_name = os.path.basename(scan_result.project_path)

    generator = ReportGenerator()
    report = generator.create_report(
        project_name=project_name,
        project_path=scan_result.project_path,
        scan_result=scan_result,
    )

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report.to_markdown())

    return output_path


__all__ = [
    'SecurityAuditReport',
    'ReportGenerator',
    'generate_quick_report',
]
