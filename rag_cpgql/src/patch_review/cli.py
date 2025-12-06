"""
Command-Line Interface for Patch Review System.

Provides CLI commands for:
- Reviewing patches from files or stdin
- Reviewing GitHub PRs
- Reviewing GitLab MRs
- Standalone security and dead code analysis
- Outputting in various formats
"""

import argparse
import sys
import os
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

import duckdb

from .workflow import ReviewWorkflow
from .aggregation import AggregationConfig
from .models import ReviewPolicy, Recommendation
from .formatters import JSONFormatter, MarkdownFormatter

# Import security and refactoring agents for analyze command
try:
    from ..security.security_agents import SecurityScanner
    from ..security.security_patterns import SECURITY_PATTERNS, VulnerabilitySeverity
    from ..refactoring.refactoring_agents import DeadCodeDetector
    from ..refactoring.refactoring_patterns import REFACTORING_PATTERNS
    from ..services.cpg_query_service import CPGQueryService
    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog='patch-review',
        description='Automated Code Review for Patches using CPG Analysis'
    )

    parser.add_argument(
        '--db', '-d',
        default='cpg.duckdb',
        help='Path to DuckDB CPG database (default: cpg.duckdb)'
    )

    parser.add_argument(
        '--output', '-o',
        choices=['json', 'markdown', 'summary', 'score'],
        default='markdown',
        help='Output format (default: markdown)'
    )

    parser.add_argument(
        '--output-file', '-f',
        help='Write output to file instead of stdout'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Only output the result, no status messages'
    )

    # Thresholds
    parser.add_argument(
        '--security-threshold',
        type=float,
        default=60.0,
        help='Minimum security score to pass (default: 60)'
    )

    parser.add_argument(
        '--block-on-critical',
        action='store_true',
        default=True,
        help='Block if any critical findings (default: true)'
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Review diff file
    diff_parser = subparsers.add_parser('diff', help='Review a diff file')
    diff_parser.add_argument(
        'file',
        nargs='?',
        help='Diff file to review (or - for stdin)'
    )

    # Review GitHub PR
    github_parser = subparsers.add_parser('github', help='Review a GitHub PR')
    github_parser.add_argument('pr_number', type=int, help='PR number')
    github_parser.add_argument('--owner', help='Repository owner')
    github_parser.add_argument('--repo', help='Repository name')
    github_parser.add_argument('--token', help='GitHub token (or use GITHUB_TOKEN env)')
    github_parser.add_argument(
        '--post-review',
        action='store_true',
        help='Post review comments to the PR'
    )

    # Review GitLab MR
    gitlab_parser = subparsers.add_parser('gitlab', help='Review a GitLab MR')
    gitlab_parser.add_argument('mr_iid', type=int, help='MR internal ID')
    gitlab_parser.add_argument('--project', help='Project ID or path')
    gitlab_parser.add_argument('--token', help='GitLab token (or use GITLAB_TOKEN env)')
    gitlab_parser.add_argument(
        '--post-review',
        action='store_true',
        help='Post review comments to the MR'
    )

    # Init database
    init_parser = subparsers.add_parser('init', help='Initialize delta tables in database')

    # Analyze command - standalone security and dead code analysis
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Run standalone security and dead code analysis'
    )
    analyze_parser.add_argument(
        '--type', '-t',
        choices=['security', 'dead-code', 'all'],
        default='all',
        help='Type of analysis to run (default: all)'
    )
    analyze_parser.add_argument(
        '--severity', '-s',
        choices=['critical', 'high', 'medium', 'low', 'all'],
        default='all',
        help='Minimum severity to report (default: all)'
    )
    analyze_parser.add_argument(
        '--patterns', '-p',
        help='Comma-separated list of specific pattern IDs to check'
    )
    analyze_parser.add_argument(
        '--limit', '-l',
        type=int,
        default=50,
        help='Maximum findings per pattern (default: 50)'
    )

    # Add common flags to diff, github, gitlab for enhanced analysis
    for cmd_parser in [diff_parser, github_parser, gitlab_parser]:
        cmd_parser.add_argument(
            '--dead-code',
            action='store_true',
            help='Include dead code analysis in review'
        )
        cmd_parser.add_argument(
            '--security-only',
            action='store_true',
            help='Only run security analysis (skip other verdicts)'
        )

    return parser


def review_diff(args, conn: duckdb.DuckDBPyConnection) -> int:
    """Review a diff file."""
    # Read diff
    if args.file == '-' or args.file is None:
        if not args.quiet:
            logger.info("Reading diff from stdin...")
        diff_text = sys.stdin.read()
    else:
        if not args.quiet:
            logger.info(f"Reading diff from {args.file}...")
        with open(args.file, 'r') as f:
            diff_text = f.read()

    if not diff_text.strip():
        logger.error("Empty diff provided")
        return 1

    # Create workflow
    config = AggregationConfig()
    policy = ReviewPolicy(
        security_threshold=args.security_threshold,
        block_on_critical=args.block_on_critical
    )

    workflow = ReviewWorkflow(conn, config, policy)

    # Run review
    if not args.quiet:
        logger.info("Running review...")

    try:
        verdict = workflow.run('git_diff', {'diff': diff_text})
    except Exception as e:
        logger.error(f"Review failed: {e}")
        return 1

    # Output result
    output = format_output(verdict, args.output)
    write_output(output, args.output_file)

    # Return exit code based on recommendation
    if verdict.recommendation == Recommendation.BLOCK:
        return 2
    elif verdict.recommendation == Recommendation.REQUEST_CHANGES:
        return 1
    return 0


def review_github(args, conn: duckdb.DuckDBPyConnection) -> int:
    """Review a GitHub PR."""
    from .integrations import GitHubIntegration, GitHubConfig

    # Get config
    token = args.token or os.environ.get('GITHUB_TOKEN')
    owner = args.owner or os.environ.get('GITHUB_OWNER')
    repo = args.repo or os.environ.get('GITHUB_REPO')

    if not all([token, owner, repo]):
        logger.error("Missing GitHub configuration. Provide --owner, --repo, --token or set environment variables.")
        return 1

    config = GitHubConfig(token=token, owner=owner, repo=repo)
    github = GitHubIntegration(config)

    if not args.quiet:
        logger.info(f"Fetching PR #{args.pr_number} from {owner}/{repo}...")

    try:
        # Fetch PR data
        patch = github.create_patch_context(args.pr_number)

        # Create workflow
        workflow = ReviewWorkflow(conn)
        verdict = workflow.run('github_pr', {
            'patch_context': patch,
            'pr_number': args.pr_number
        })

        # Post review if requested
        if args.post_review:
            if not args.quiet:
                logger.info("Posting review to GitHub...")
            github.submit_review(args.pr_number, verdict)

        # Output result
        output = format_output(verdict, args.output)
        write_output(output, args.output_file)

        if verdict.recommendation == Recommendation.BLOCK:
            return 2
        elif verdict.recommendation == Recommendation.REQUEST_CHANGES:
            return 1
        return 0

    except Exception as e:
        logger.error(f"GitHub review failed: {e}")
        return 1


def review_gitlab(args, conn: duckdb.DuckDBPyConnection) -> int:
    """Review a GitLab MR."""
    from .integrations import GitLabIntegration, GitLabConfig

    # Get config
    token = args.token or os.environ.get('GITLAB_TOKEN')
    project = args.project or os.environ.get('GITLAB_PROJECT_ID')

    if not all([token, project]):
        logger.error("Missing GitLab configuration. Provide --project, --token or set environment variables.")
        return 1

    config = GitLabConfig(token=token, project_id=project)
    gitlab = GitLabIntegration(config)

    if not args.quiet:
        logger.info(f"Fetching MR !{args.mr_iid} from {project}...")

    try:
        # Fetch MR data
        patch = gitlab.create_patch_context(args.mr_iid)

        # Create workflow
        workflow = ReviewWorkflow(conn)
        verdict = workflow.run('gitlab_mr', {
            'patch_context': patch,
            'mr_iid': args.mr_iid
        })

        # Post review if requested
        if args.post_review:
            if not args.quiet:
                logger.info("Posting review to GitLab...")
            gitlab.submit_review(args.mr_iid, verdict)

        # Output result
        output = format_output(verdict, args.output)
        write_output(output, args.output_file)

        if verdict.recommendation == Recommendation.BLOCK:
            return 2
        elif verdict.recommendation == Recommendation.REQUEST_CHANGES:
            return 1
        return 0

    except Exception as e:
        logger.error(f"GitLab review failed: {e}")
        return 1


def init_database(args, conn: duckdb.DuckDBPyConnection) -> int:
    """Initialize delta tables in database."""
    logger.info("Initializing delta tables...")

    # Read and execute migration SQL
    migration_path = Path(__file__).parent.parent / 'cpg_export' / 'migrations' / 'add_delta_tables.sql'

    if not migration_path.exists():
        logger.error(f"Migration file not found: {migration_path}")
        return 1

    try:
        with open(migration_path, 'r') as f:
            sql = f.read()

        # Execute each statement
        for statement in sql.split(';'):
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                conn.execute(statement)

        logger.info("Delta tables initialized successfully")
        return 0

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return 1


def analyze_codebase(args) -> int:
    """Run standalone security and dead code analysis."""
    if not AGENTS_AVAILABLE:
        logger.error("Analysis agents not available. Install security and refactoring modules.")
        return 1

    if not args.quiet:
        logger.info(f"Running {args.type} analysis...")

    results = {
        'analysis_type': args.type,
        'severity_filter': args.severity,
        'pattern_filter': args.patterns,
        'security_findings': [],
        'dead_code_findings': [],
        'summary': {}
    }

    # Parse specific patterns if provided
    specific_patterns = None
    if args.patterns:
        specific_patterns = [p.strip().upper() for p in args.patterns.split(',')]

    # Create CPG service (pass db_path, not connection)
    try:
        cpg_service = CPGQueryService(args.db)
    except Exception as e:
        logger.error(f"Failed to create CPG service: {e}")
        return 1

    # Run security analysis
    if args.type in ['security', 'all']:
        if not args.quiet:
            logger.info("Running security pattern analysis...")
        try:
            scanner = SecurityScanner(cpg_service)
            security_findings = scanner.scan_all_patterns(limit_per_pattern=args.limit)

            # Filter by severity
            if args.severity != 'all':
                severity_map = {
                    'critical': VulnerabilitySeverity.CRITICAL,
                    'high': VulnerabilitySeverity.HIGH,
                    'medium': VulnerabilitySeverity.MEDIUM,
                    'low': VulnerabilitySeverity.LOW,
                }
                min_severity = severity_map.get(args.severity)
                if min_severity:
                    severity_order = ['critical', 'high', 'medium', 'low']
                    min_idx = severity_order.index(args.severity)
                    allowed_severities = severity_order[:min_idx + 1]
                    security_findings = [
                        f for f in security_findings
                        if f.severity.lower() in allowed_severities
                    ]

            # Filter by specific patterns
            if specific_patterns:
                security_findings = [
                    f for f in security_findings
                    if f.pattern_id in specific_patterns or f.pattern_name.upper() in specific_patterns
                ]

            results['security_findings'] = [
                {
                    'finding_id': f.finding_id,
                    'pattern_id': f.pattern_id,
                    'pattern_name': f.pattern_name,
                    'category': f.category,
                    'severity': f.severity,
                    'method_name': f.method_name,
                    'filename': f.filename,
                    'line_number': f.line_number,
                    'cwe_ids': f.cwe_ids,
                    'confidence': f.confidence,
                }
                for f in security_findings
            ]
            logger.info(f"Found {len(security_findings)} security findings")
        except Exception as e:
            logger.error(f"Security analysis failed: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()

    # Run dead code analysis
    if args.type in ['dead-code', 'all']:
        if not args.quiet:
            logger.info("Running dead code analysis...")
        try:
            detector = DeadCodeDetector(cpg_service)
            dead_code_findings = detector.detect_all(limit_per_pattern=args.limit)

            # Filter by severity
            if args.severity != 'all':
                severity_order = ['critical', 'high', 'medium', 'low']
                min_idx = severity_order.index(args.severity)
                allowed_severities = severity_order[:min_idx + 1]
                dead_code_findings = [
                    f for f in dead_code_findings
                    if f.get('severity', 'medium').lower() in allowed_severities
                ]

            # Filter by specific patterns
            if specific_patterns:
                dead_code_findings = [
                    f for f in dead_code_findings
                    if f.get('pattern_id', '').upper() in specific_patterns
                    or f.get('detection_type', '').upper() in specific_patterns
                ]

            # Convert DeadCodeFinding objects to dicts for JSON serialization
            results['dead_code_findings'] = [
                {
                    'finding_id': f.finding_id,
                    'pattern_id': f.pattern_id,
                    'pattern_name': f.pattern_name,
                    'detection_type': f.detection_type,
                    'severity': f.severity,
                    'method_id': f.method_id,
                    'method_name': f.method_name,
                    'filename': f.filename,
                    'line_number': f.line_number,
                    'confidence': f.confidence,
                }
                for f in dead_code_findings
            ]
            logger.info(f"Found {len(dead_code_findings)} dead code findings")
        except Exception as e:
            logger.error(f"Dead code analysis failed: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()

    # Calculate summary
    results['summary'] = {
        'total_security_findings': len(results['security_findings']),
        'total_dead_code_findings': len(results['dead_code_findings']),
        'security_by_severity': _count_by_severity(results['security_findings']),
        'dead_code_by_type': _count_by_type(results['dead_code_findings']),
    }

    # Output result
    output = format_analysis_output(results, args.output)
    write_output(output, args.output_file)

    # Return exit code based on findings
    critical_count = results['summary']['security_by_severity'].get('critical', 0)
    high_count = results['summary']['security_by_severity'].get('high', 0)

    if critical_count > 0:
        return 2  # Critical findings
    elif high_count > 0:
        return 1  # High severity findings
    return 0


def _count_by_severity(findings: List[Any]) -> Dict[str, int]:
    """Count findings by severity."""
    counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    for f in findings:
        # Handle both dict and dataclass objects
        if hasattr(f, 'severity'):
            sev = f.severity.lower() if isinstance(f.severity, str) else str(f.severity).lower()
        else:
            sev = f.get('severity', 'medium').lower()
        if sev in counts:
            counts[sev] += 1
    return counts


def _count_by_type(findings: List[Any]) -> Dict[str, int]:
    """Count dead code findings by type."""
    counts = {}
    for f in findings:
        # Handle both dict and dataclass objects
        if hasattr(f, 'detection_type'):
            detection_type = f.detection_type
        else:
            detection_type = f.get('detection_type', 'unknown')
        counts[detection_type] = counts.get(detection_type, 0) + 1
    return counts


def format_analysis_output(results: Dict[str, Any], output_format: str) -> str:
    """Format analysis results for output."""
    if output_format == 'json':
        return json.dumps(results, indent=2, default=str)
    elif output_format == 'summary':
        return json.dumps(results['summary'], indent=2)
    elif output_format == 'score':
        return json.dumps({
            'security_count': results['summary']['total_security_findings'],
            'dead_code_count': results['summary']['total_dead_code_findings'],
            'critical': results['summary']['security_by_severity'].get('critical', 0),
            'high': results['summary']['security_by_severity'].get('high', 0),
        })
    else:  # markdown
        return _format_analysis_markdown(results)


def _format_analysis_markdown(results: Dict[str, Any]) -> str:
    """Format analysis results as Markdown."""
    lines = [
        "# Code Analysis Report",
        "",
        f"**Analysis Type:** {results['analysis_type']}",
        f"**Severity Filter:** {results['severity_filter']}",
        "",
        "## Summary",
        "",
        f"- **Security Findings:** {results['summary']['total_security_findings']}",
        f"- **Dead Code Findings:** {results['summary']['total_dead_code_findings']}",
        "",
    ]

    # Security severity breakdown
    if results['summary']['security_by_severity']:
        lines.append("### Security Findings by Severity")
        lines.append("")
        for sev, count in results['summary']['security_by_severity'].items():
            if count > 0:
                lines.append(f"- **{sev.upper()}:** {count}")
        lines.append("")

    # Dead code type breakdown
    if results['summary']['dead_code_by_type']:
        lines.append("### Dead Code by Type")
        lines.append("")
        for dtype, count in results['summary']['dead_code_by_type'].items():
            if count > 0:
                lines.append(f"- **{dtype}:** {count}")
        lines.append("")

    # Security findings details
    if results['security_findings']:
        lines.append("## Security Findings")
        lines.append("")
        lines.append("| Severity | Pattern | File | Line | CWE |")
        lines.append("|----------|---------|------|------|-----|")
        for f in results['security_findings'][:50]:  # Limit table size
            cwe = ', '.join(f.get('cwe_ids', []))
            filename = Path(f.get('filename', '')).name
            lines.append(
                f"| {f.get('severity', 'N/A')} | {f.get('pattern_name', 'N/A')} | "
                f"{filename} | {f.get('line_number', 'N/A')} | {cwe} |"
            )
        lines.append("")

    # Dead code findings details
    if results['dead_code_findings']:
        lines.append("## Dead Code Findings")
        lines.append("")
        lines.append("| Type | Method | File | Line | Confidence |")
        lines.append("|------|--------|------|------|------------|")
        for f in results['dead_code_findings'][:50]:  # Limit table size
            filename = Path(f.get('filename', '')).name
            confidence = f.get('confidence', 0)
            if isinstance(confidence, float):
                confidence = f"{confidence:.2f}"
            lines.append(
                f"| {f.get('detection_type', 'N/A')} | {f.get('method_name', 'N/A')} | "
                f"{filename} | {f.get('line_number', 'N/A')} | {confidence} |"
            )
        lines.append("")

    return '\n'.join(lines)


def format_output(verdict, output_format: str) -> str:
    """Format verdict for output."""
    if output_format == 'json':
        formatter = JSONFormatter()
        return formatter.format_full(verdict)
    elif output_format == 'summary':
        formatter = JSONFormatter()
        return formatter.format_summary(verdict)
    elif output_format == 'score':
        return json.dumps({
            'score': verdict.overall_score,
            'recommendation': verdict.recommendation.value,
            'critical': verdict.critical_count,
            'high': verdict.high_count
        })
    else:  # markdown
        formatter = MarkdownFormatter()
        return formatter.format_full_report(verdict)


def write_output(output: str, output_file: Optional[str]) -> None:
    """Write output to file or stdout."""
    if output_file:
        with open(output_file, 'w') as f:
            f.write(output)
    else:
        print(output)


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.quiet:
        logging.getLogger().setLevel(logging.ERROR)

    if not args.command:
        parser.print_help()
        return 0

    # For analyze command, don't open connection here - CPGQueryService will do it
    if args.command == 'analyze':
        return analyze_codebase(args)

    # Connect to database for other commands
    try:
        conn = duckdb.connect(args.db)
    except Exception as e:
        logger.error(f"Failed to connect to database {args.db}: {e}")
        return 1

    try:
        if args.command == 'diff':
            return review_diff(args, conn)
        elif args.command == 'github':
            return review_github(args, conn)
        elif args.command == 'gitlab':
            return review_gitlab(args, conn)
        elif args.command == 'init':
            return init_database(args, conn)
        else:
            parser.print_help()
            return 0
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
