#!/usr/bin/env python3
"""
Security Audit CLI

Command-line interface for running comprehensive security audits
on multi-language projects.

Supported languages:
- C/C++ (buffer overflows, format strings, command injection)
- Python/Django (SQL injection, XSS, CSRF, deserialization)
- JavaScript/TypeScript (XSS, prototype pollution, eval injection)
- Go (race conditions, SQL injection, command injection)
- Ruby/Rails (eval injection, YAML deserialization, mass assignment)
- C#/.NET (SQL injection, XSS, insecure deserialization)
- Kotlin/Android (WebView XSS, intent redirection, insecure storage)
- Swift/iOS (keychain misuse, URL scheme hijacking, TLS bypass)
- Java (SQL injection, deserialization, XXE)
- PHP (SQL injection, XSS, command injection)

Usage:
    python -m src.cli.security_audit full --path /path/to/project
    python -m src.cli.security_audit full --path /path/to/project --output ./reports
    python -m src.cli.security_audit full --path /path/to/project --language python
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.table import Table
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from src.security.file_scanner import (
    FileSecurityScanner,
    ScanResult,
    find_django_settings,
)
from src.security.report_generator import (
    SecurityAuditReport,
    ReportGenerator,
)

logger = logging.getLogger(__name__)

if RICH_AVAILABLE:
    console = Console()
else:
    console = None


SUPPORTED_LANGUAGES = [
    "auto", "c", "cpp", "python", "javascript", "typescript",
    "go", "ruby", "csharp", "kotlin", "swift", "java", "php"
]


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for security audit CLI."""
    parser = argparse.ArgumentParser(
        prog="security-audit",
        description="Multi-language security audit tool supporting C/C++, Python, JavaScript, Go, Ruby, C#, Kotlin, Swift, Java, PHP",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Full audit command
    full_parser = subparsers.add_parser("full", help="Run full security audit")
    full_parser.add_argument(
        "--path", "-p",
        required=True,
        help="Path to project to audit"
    )
    full_parser.add_argument(
        "--output", "-o",
        help="Output directory for reports (default: ./security_reports)"
    )
    full_parser.add_argument(
        "--format", "-f",
        nargs="+",
        default=["json", "markdown", "sarif"],
        choices=["json", "markdown", "md", "sarif", "all"],
        help="Output format(s)"
    )
    full_parser.add_argument(
        "--exclude-dirs",
        nargs="+",
        default=[],
        help="Additional directories to exclude"
    )
    full_parser.add_argument(
        "--no-cpg",
        action="store_true",
        help="Skip CPG-based analysis (faster, file-based only)"
    )
    full_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    full_parser.add_argument(
        "--language", "-l",
        choices=SUPPORTED_LANGUAGES,
        default="auto",
        help="Target language for security patterns (default: auto-detect)"
    )

    # Quick scan command
    quick_parser = subparsers.add_parser("quick", help="Quick file-based scan only")
    quick_parser.add_argument("--path", "-p", required=True, help="Path to project")
    quick_parser.add_argument("--output", "-o", help="Output file for report")

    # Settings scan command
    settings_parser = subparsers.add_parser("settings", help="Scan Django settings only")
    settings_parser.add_argument("--path", "-p", required=True, help="Path to settings.py")

    # Secrets scan command
    secrets_parser = subparsers.add_parser("secrets", help="Scan for hardcoded secrets")
    secrets_parser.add_argument("--path", "-p", required=True, help="Path to project")

    return parser


def run_full_audit(args) -> int:
    """Run full security audit."""
    project_path = os.path.abspath(args.path)

    if not os.path.isdir(project_path):
        print(f"Error: Project path does not exist: {project_path}")
        return 1

    project_name = os.path.basename(project_path)
    output_dir = args.output or os.path.join(os.getcwd(), "security_reports")
    formats = args.format if 'all' not in args.format else ["json", "markdown", "sarif"]

    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold]Security Audit[/bold]\n"
            f"Project: {project_name}\n"
            f"Path: {project_path}\n"
            f"Output: {output_dir}",
            title="CodeGraph Security Scanner"
        ))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Starting security audit...", total=100)

            # Stage 1: File-based scanning
            progress.update(task, completed=10, description="Scanning files for vulnerabilities...")

            scanner = FileSecurityScanner(
                exclude_dirs=scanner_exclude_dirs(args.exclude_dirs)
            )
            scan_result = scanner.scan_project(project_path)

            progress.update(task, completed=50, description="Analyzing findings...")

            # Create report
            generator = ReportGenerator()
            report = generator.create_report(
                project_name=project_name,
                project_path=project_path,
                scan_result=scan_result,
            )

            progress.update(task, completed=80, description="Generating reports...")

            # Save reports
            output_files = generator.save_report(
                output_dir=output_dir,
                formats=formats,
                base_filename=f"security_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

            progress.update(task, completed=100, description="Completed!")

        # Display summary
        display_summary(report, output_files)

    else:
        # Non-rich fallback
        print(f"Security Audit: {project_name}")
        print(f"Path: {project_path}")
        print("-" * 60)

        print("Scanning files...")
        scanner = FileSecurityScanner(
            exclude_dirs=scanner_exclude_dirs(args.exclude_dirs)
        )
        scan_result = scanner.scan_project(project_path)

        print(f"Found {len(scan_result.findings)} potential issues")

        # Create and save report
        generator = ReportGenerator()
        report = generator.create_report(
            project_name=project_name,
            project_path=project_path,
            scan_result=scan_result,
        )

        output_files = generator.save_report(
            output_dir=output_dir,
            formats=formats,
            base_filename=f"security_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        print("\nSummary:")
        for severity, count in report.severity_counts.items():
            if count > 0:
                print(f"  {severity.upper()}: {count}")

        print(f"\nReports saved to: {output_dir}")

    return 0


def run_quick_scan(args) -> int:
    """Run quick file-based scan."""
    project_path = os.path.abspath(args.path)

    if not os.path.isdir(project_path):
        print(f"Error: Project path does not exist: {project_path}")
        return 1

    print(f"Quick scan: {project_path}")

    scanner = FileSecurityScanner()
    scan_result = scanner.scan_project(project_path)

    print(f"\nFiles scanned: {scan_result.files_scanned}")
    print(f"Findings: {len(scan_result.findings)}")
    print(f"Duration: {scan_result.duration_seconds:.2f}s")

    if scan_result.findings:
        print("\nFindings:")
        for finding in scan_result.findings[:20]:  # Show first 20
            severity_icon = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢',
            }.get(finding.severity.value, '⚪')

            print(f"  {severity_icon} [{finding.severity.value.upper()}] {finding.pattern_name}")
            print(f"      File: {finding.file_path}:{finding.line_number}")

        if len(scan_result.findings) > 20:
            print(f"  ... and {len(scan_result.findings) - 20} more")

    # Save report if output specified
    if args.output:
        from src.security.report_generator import generate_quick_report
        generate_quick_report(scan_result, args.output)
        print(f"\nReport saved to: {args.output}")

    return 0


def run_settings_scan(args) -> int:
    """Scan Django settings file."""
    settings_path = args.path

    if not os.path.isfile(settings_path):
        # Try to find settings.py
        if os.path.isdir(settings_path):
            found = find_django_settings(settings_path)
            if found:
                settings_path = found
                print(f"Found settings at: {settings_path}")
            else:
                print(f"Error: Could not find settings.py in {settings_path}")
                return 1
        else:
            print(f"Error: Path does not exist: {settings_path}")
            return 1

    print(f"Scanning Django settings: {settings_path}")

    scanner = FileSecurityScanner()
    findings = scanner.scan_django_settings(settings_path)

    print(f"\nFindings: {len(findings)}")

    for finding in findings:
        severity_icon = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢',
        }.get(finding.severity.value, '⚪')

        print(f"\n{severity_icon} [{finding.severity.value.upper()}] {finding.pattern_name}")
        print(f"   Line {finding.line_number}: {finding.line_content[:80]}")
        print(f"   CWE: {', '.join(finding.cwe_ids)}")
        print(f"   Fix: {finding.remediation[:100]}...")

    return 0


def run_secrets_scan(args) -> int:
    """Scan for hardcoded secrets."""
    project_path = os.path.abspath(args.path)

    if not os.path.isdir(project_path):
        print(f"Error: Project path does not exist: {project_path}")
        return 1

    print(f"Scanning for secrets: {project_path}")

    scanner = FileSecurityScanner()
    findings = scanner.scan_for_secrets(project_path)

    print(f"\nSecrets found: {len(findings)}")

    for finding in findings:
        print(f"\n🔐 {finding.pattern_name}")
        print(f"   File: {finding.file_path}:{finding.line_number}")
        print(f"   Match: {finding.match_text[:50]}...")

    if not findings:
        print("No hardcoded secrets detected! ✅")

    return 0


def scanner_exclude_dirs(extra_dirs: List[str]) -> List[str]:
    """Get list of directories to exclude."""
    default_exclude = [
        '__pycache__', '.git', '.venv', 'venv', 'env',
        'node_modules', '.tox', '.pytest_cache', '.mypy_cache',
        'migrations', 'static', 'media', 'dist', 'build',
    ]
    return default_exclude + extra_dirs


def display_summary(report: SecurityAuditReport, output_files: dict) -> None:
    """Display audit summary using Rich."""
    if not RICH_AVAILABLE:
        return

    # Summary table
    table = Table(title="Security Audit Summary")
    table.add_column("Severity", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("Status")

    # Windows-safe ASCII icons instead of emojis
    severity_styles = {
        'critical': ('red', '[X]'),
        'high': ('orange1', '[!]'),
        'medium': ('yellow', '[~]'),
        'low': ('green', '[o]'),
        'info': ('blue', '[i]'),
    }

    for severity, count in report.severity_counts.items():
        style, icon = severity_styles.get(severity, ('white', '[-]'))
        status = "FAIL" if count > 0 and severity in ['critical', 'high'] else "PASS" if count == 0 else "WARN"
        table.add_row(
            f"{icon} {severity.upper()}",
            str(count),
            status,
            style=style if count > 0 else None
        )

    table.add_row("", "", "", style="dim")
    table.add_row("[bold]TOTAL[/bold]", f"[bold]{report.total_findings}[/bold]", "")

    console.print(table)

    # Risk assessment
    if report.critical_count > 0:
        console.print(Panel(
            "[bold red]CRITICAL RISK[/bold red]\n\n"
            f"Found {report.critical_count} critical vulnerabilities!\n"
            "These must be addressed before deployment.",
            title="[!] Security Alert",
            border_style="red"
        ))
    elif report.high_count > 0:
        console.print(Panel(
            "[bold orange1]HIGH RISK[/bold orange1]\n\n"
            f"Found {report.high_count} high severity issues.\n"
            "Address these vulnerabilities soon.",
            title="[!] Security Warning",
            border_style="orange1"
        ))
    else:
        console.print(Panel(
            "[bold green]LOW RISK[/bold green]\n\n"
            "No critical or high severity issues found.",
            title="[OK] Security Status",
            border_style="green"
        ))

    # Output files
    console.print("\n[bold]Generated Reports:[/bold]")
    for format_name, file_path in output_files.items():
        console.print(f"  * {format_name}: [cyan]{file_path}[/cyan]")

    # Top findings preview
    if report.file_findings:
        console.print("\n[bold]Top Findings:[/bold]")
        for finding in report.file_findings[:5]:
            severity_icon = severity_styles.get(finding.severity.value, ('white', '[-]'))[1]
            console.print(f"  {severity_icon} {finding.pattern_name}")
            console.print(f"      [dim]{finding.file_path}:{finding.line_number}[/dim]")


def main() -> int:
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "full":
        return run_full_audit(args)
    elif args.command == "quick":
        return run_quick_scan(args)
    elif args.command == "settings":
        return run_settings_scan(args)
    elif args.command == "secrets":
        return run_secrets_scan(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
