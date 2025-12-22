"""
Taint-Verified Security Scanner.

Verifies potential SQL injection and other vulnerabilities through data-flow analysis.
Uses the DataFlowTracer to check if user input actually reaches dangerous sinks.

This reduces false positives by only reporting vulnerabilities that have
confirmed taint paths from untrusted sources to dangerous sinks.
"""

import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field

from src.analysis.dataflow_tracer import (
    DataFlowTracer,
    DataFlowPath,
    SANITIZATION_CONFIDENCE_THRESHOLD,
)

logger = logging.getLogger(__name__)


# Python/Django taint sources (user input)
PYTHON_TAINT_SOURCES = [
    # Django request data
    'request.GET',
    'request.POST',
    'request.data',
    'request.body',
    'request.FILES',
    'request.META',
    'request.COOKIES',
    'request.headers',
    # Flask request data
    'request.args',
    'request.form',
    'request.json',
    'request.values',
    # Generic input
    'input',
    'raw_input',
    'sys.stdin',
    # Environment (can be attacker-controlled)
    'os.getenv',
    'os.environ',
    'getenv',
    # File input
    'open',
    'read',
    'readline',
    'readlines',
    # Network input
    'recv',
    'recvfrom',
    'urlopen',
]

# Python/Django SQL sinks (dangerous functions)
PYTHON_SQL_SINKS = [
    # Raw SQL execution
    'execute',
    'executemany',
    'raw',
    'extra',
    'cursor.execute',
    # Django raw queries
    'RawSQL',
    'connection.cursor',
    # SQLAlchemy raw
    'engine.execute',
    'text',
]

# General dangerous sinks for Python
PYTHON_DANGEROUS_SINKS = {
    'sql_injection': PYTHON_SQL_SINKS,
    'command_injection': [
        'os.system',
        'os.popen',
        'subprocess.call',
        'subprocess.run',
        'subprocess.Popen',
        'commands.getoutput',
        'eval',
        'exec',
        'compile',
    ],
    'path_traversal': [
        'open',
        'os.path.join',
        'send_file',
        'FileResponse',
    ],
    'xss': [
        'mark_safe',
        'render_to_string',
        'HttpResponse',
    ],
    'deserialization': [
        'pickle.loads',
        'pickle.load',
        'yaml.load',
        'yaml.unsafe_load',
        'marshal.loads',
    ],
}


@dataclass
class VerifiedFinding:
    """A security finding verified through taint analysis."""
    original_finding: Dict[str, Any]
    is_verified: bool
    taint_path: Optional[DataFlowPath] = None
    sanitization_confidence: float = 0.0
    verification_notes: List[str] = field(default_factory=list)

    @property
    def severity(self) -> str:
        """Get severity, potentially adjusted based on verification."""
        original_severity = self.original_finding.get('severity', 'info')
        if not self.is_verified:
            # Downgrade unverified findings
            if original_severity in ('critical', 'high'):
                return 'medium'
            elif original_severity == 'medium':
                return 'low'
            else:
                return 'info'
        return original_severity

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for report generation."""
        result = self.original_finding.copy()
        result['is_taint_verified'] = self.is_verified
        result['sanitization_confidence'] = self.sanitization_confidence
        result['verification_notes'] = self.verification_notes

        # Adjust severity if not verified
        if not self.is_verified:
            result['original_severity'] = self.original_finding.get('severity')
            result['severity'] = self.severity

        # Add taint path info
        if self.taint_path:
            result['taint_path'] = {
                'source': self.taint_path.source_location,
                'sink': self.taint_path.sink_location,
                'path_length': self.taint_path.path_length,
                'is_inter_procedural': self.taint_path.is_inter_procedural,
                'sanitization_points': [
                    {'function': s.get('function'), 'confidence': s.get('confidence', 0)}
                    for s in self.taint_path.sanitization_points
                ]
            }

        return result


class TaintVerifiedScanner:
    """
    Verifies SQL injection and other vulnerabilities through data-flow analysis.

    Uses DataFlowTracer.find_taint_paths() to check if user input actually
    reaches dangerous sinks. This reduces false positives significantly.
    """

    def __init__(self, cpg_service):
        """
        Initialize scanner with CPG service.

        Args:
            cpg_service: CPGQueryService instance with database connection
        """
        self.cpg = cpg_service
        self.tracer = DataFlowTracer(cpg_service)
        logger.info("TaintVerifiedScanner initialized")

    def verify_sql_injection(
        self,
        findings: List[Dict[str, Any]],
        source_functions: Optional[List[str]] = None,
        sink_functions: Optional[List[str]] = None,
        max_depth: int = 10
    ) -> List[VerifiedFinding]:
        """
        Verify SQL injection findings through taint analysis.

        Args:
            findings: List of potential SQL injection findings
            source_functions: Taint sources (defaults to PYTHON_TAINT_SOURCES)
            sink_functions: SQL sinks (defaults to PYTHON_SQL_SINKS)
            max_depth: Maximum taint flow depth

        Returns:
            List of VerifiedFinding objects with taint analysis results
        """
        if source_functions is None:
            source_functions = PYTHON_TAINT_SOURCES
        if sink_functions is None:
            sink_functions = PYTHON_SQL_SINKS

        logger.info(f"Verifying {len(findings)} SQL injection findings via taint analysis")

        # Get all taint paths from sources to SQL sinks
        taint_paths = self.tracer.find_taint_paths(
            source_functions=source_functions,
            sink_functions=sink_functions,
            max_depth=max_depth,
            check_sanitization=True  # Filter sanitized paths
        )

        # Build lookup by sink location (file:line or call_id)
        taint_by_sink: Dict[str, DataFlowPath] = {}
        for path in taint_paths:
            sink_loc = path.sink_location
            # Key by file:line
            if sink_loc.get('file') and sink_loc.get('line'):
                key = f"{sink_loc['file']}:{sink_loc['line']}"
                taint_by_sink[key] = path
            # Also key by call_id
            if sink_loc.get('call_id'):
                taint_by_sink[str(sink_loc['call_id'])] = path

        verified_findings = []
        verified_count = 0
        unverified_count = 0

        for finding in findings:
            # Build keys to lookup taint path
            file_path = finding.get('file_path', '')
            line_number = finding.get('line_number', 0)
            call_id = finding.get('call_id') or finding.get('node_id')

            lookup_keys = []
            if file_path and line_number:
                lookup_keys.append(f"{file_path}:{line_number}")
            if call_id:
                lookup_keys.append(str(call_id))

            # Try to find matching taint path
            taint_path = None
            for key in lookup_keys:
                if key in taint_by_sink:
                    taint_path = taint_by_sink[key]
                    break

            # Create verified finding
            if taint_path:
                # Calculate max sanitization confidence on path
                max_confidence = max(
                    (s.get('confidence', 0) for s in taint_path.sanitization_points),
                    default=0.0
                )

                verified = VerifiedFinding(
                    original_finding=finding,
                    is_verified=True,
                    taint_path=taint_path,
                    sanitization_confidence=max_confidence,
                    verification_notes=[
                        f"Taint path confirmed from {taint_path.source_location.get('function', 'source')} "
                        f"to {taint_path.sink_location.get('function', 'sink')}",
                        f"Path length: {taint_path.path_length} hops",
                    ]
                )
                verified_count += 1
            else:
                verified = VerifiedFinding(
                    original_finding=finding,
                    is_verified=False,
                    sanitization_confidence=1.0,  # Assume sanitized if no path
                    verification_notes=[
                        "No taint path found from user input sources",
                        "This may be a false positive or internal-only code path",
                    ]
                )
                unverified_count += 1

            verified_findings.append(verified)

        logger.info(
            f"SQL injection verification complete: {verified_count} verified, "
            f"{unverified_count} unverified (potential false positives)"
        )

        return verified_findings

    def scan_sql_injection_verified(
        self,
        limit: int = 50
    ) -> List[VerifiedFinding]:
        """
        Scan for SQL injection vulnerabilities with taint verification.

        Unlike pattern-based scanning, this only reports findings where
        user input demonstrably reaches SQL execution.

        Args:
            limit: Maximum number of results

        Returns:
            List of verified SQL injection findings
        """
        logger.info("Starting taint-verified SQL injection scan")

        # Get taint paths directly
        taint_paths = self.tracer.find_taint_paths(
            source_functions=PYTHON_TAINT_SOURCES,
            sink_functions=PYTHON_SQL_SINKS,
            max_depth=15,
            check_sanitization=True
        )

        verified_findings = []
        for idx, path in enumerate(taint_paths[:limit]):
            # Create finding from taint path
            finding = {
                'pattern_id': 'TAINT_SQL_INJECTION',
                'pattern_name': 'Taint-Verified SQL Injection',
                'severity': 'high' if path.path_length <= 3 else 'medium',
                'description': (
                    f"User input from {path.source_location.get('function', 'source')} "
                    f"reaches SQL execution at {path.sink_location.get('function', 'sink')} "
                    f"without adequate sanitization"
                ),
                'file_path': path.sink_location.get('file', 'unknown'),
                'line_number': path.sink_location.get('line', 0),
                'containing_method': path.sink_location.get('method', 'unknown'),
                'cwe_ids': ['CWE-89'],
            }

            max_confidence = max(
                (s.get('confidence', 0) for s in path.sanitization_points),
                default=0.0
            )

            verified_findings.append(VerifiedFinding(
                original_finding=finding,
                is_verified=True,
                taint_path=path,
                sanitization_confidence=max_confidence,
                verification_notes=[
                    f"Direct taint path confirmed ({path.path_length} hops)",
                    "Sanitization confidence below threshold",
                ]
            ))

        logger.info(f"Found {len(verified_findings)} taint-verified SQL injection vulnerabilities")
        return verified_findings


class SecurityRelevantCallsFilter:
    """
    Filters security-relevant function calls based on taint analysis.

    Only shows calls where there's a real taint path from user input,
    eliminating noise from internal-only code paths.
    """

    def __init__(self, cpg_service):
        """
        Initialize filter with CPG service.

        Args:
            cpg_service: CPGQueryService instance
        """
        self.cpg = cpg_service
        self.tracer = DataFlowTracer(cpg_service)
        logger.info("SecurityRelevantCallsFilter initialized")

    def filter_by_taint(
        self,
        findings: List[Dict[str, Any]],
        category: str = 'sql_injection'
    ) -> List[Dict[str, Any]]:
        """
        Filter findings to only include those with real taint paths.

        Args:
            findings: List of findings to filter
            category: Vulnerability category for sink selection

        Returns:
            Filtered list with only taint-reachable findings
        """
        # Get sinks for this category
        sinks = PYTHON_DANGEROUS_SINKS.get(category, PYTHON_SQL_SINKS)

        # Get all taint paths
        taint_paths = self.tracer.find_taint_paths(
            source_functions=PYTHON_TAINT_SOURCES,
            sink_functions=sinks,
            max_depth=15,
            check_sanitization=False  # Include all paths for filtering
        )

        # Build set of tainted locations
        tainted_locations: Set[str] = set()
        for path in taint_paths:
            sink = path.sink_location
            if sink.get('file') and sink.get('line'):
                tainted_locations.add(f"{sink['file']}:{sink['line']}")
            if sink.get('call_id'):
                tainted_locations.add(f"call:{sink['call_id']}")

        # Filter findings
        filtered = []
        for finding in findings:
            file_path = finding.get('file_path', '')
            line_number = finding.get('line_number', 0)
            call_id = finding.get('call_id') or finding.get('node_id')

            # Check if this location is tainted
            is_tainted = False
            if file_path and line_number:
                is_tainted = f"{file_path}:{line_number}" in tainted_locations
            if not is_tainted and call_id:
                is_tainted = f"call:{call_id}" in tainted_locations

            if is_tainted:
                finding['taint_verified'] = True
                filtered.append(finding)
            else:
                # Optionally downgrade to info
                if finding.get('severity') == 'info':
                    # Skip info-level findings without taint
                    continue
                else:
                    # Keep but mark as unverified and downgrade
                    finding['taint_verified'] = False
                    finding['original_severity'] = finding.get('severity')
                    finding['severity'] = 'info'
                    finding['verification_note'] = 'No taint path found - potential false positive'
                    filtered.append(finding)

        logger.info(
            f"Filtered {len(findings)} findings to {len(filtered)} "
            f"({len(findings) - len(filtered)} removed as likely false positives)"
        )
        return filtered

    def filter_security_relevant_calls(
        self,
        findings: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filter INFO-level security-relevant call findings.

        These are often noisy and only useful if there's actual taint flow.

        Args:
            findings: List of findings, potentially including INFO-level calls

        Returns:
            Filtered findings with meaningful INFO calls only
        """
        info_findings = [f for f in findings if f.get('severity') == 'info']
        other_findings = [f for f in findings if f.get('severity') != 'info']

        if not info_findings:
            return findings

        # Filter info findings by taint
        filtered_info = self.filter_by_taint(info_findings, 'sql_injection')

        # Only keep info findings that are taint-verified
        verified_info = [f for f in filtered_info if f.get('taint_verified', False)]

        logger.info(
            f"Security-relevant calls filter: "
            f"kept {len(verified_info)}/{len(info_findings)} INFO findings"
        )

        return other_findings + verified_info


def integrate_with_report_generator(
    cpg_service,
    findings: List[Dict[str, Any]],
    verify_sql: bool = True,
    filter_info: bool = True
) -> List[Dict[str, Any]]:
    """
    Integration function for report generator.

    Applies taint verification and filtering to findings before report generation.

    Args:
        cpg_service: CPGQueryService instance
        findings: Raw findings from pattern-based scanning
        verify_sql: Whether to verify SQL injection findings
        filter_info: Whether to filter INFO-level findings

    Returns:
        Processed findings with taint verification applied
    """
    processed = findings.copy()

    try:
        if verify_sql:
            # Separate SQL injection findings
            sql_findings = [
                f for f in processed
                if 'sql' in f.get('pattern_id', '').lower()
                or 'execute' in f.get('pattern_name', '').lower()
            ]
            other_findings = [
                f for f in processed
                if f not in sql_findings
            ]

            if sql_findings:
                scanner = TaintVerifiedScanner(cpg_service)
                verified = scanner.verify_sql_injection(sql_findings)

                # Convert back to dicts
                sql_processed = [v.to_dict() for v in verified]
                processed = other_findings + sql_processed

                logger.info(f"SQL injection verification applied to {len(sql_findings)} findings")

        if filter_info:
            filter_obj = SecurityRelevantCallsFilter(cpg_service)
            processed = filter_obj.filter_security_relevant_calls(processed)
            logger.info("Security-relevant calls filtering applied")

    except Exception as e:
        logger.error(f"Error in taint verification: {e}", exc_info=True)
        # Return original findings on error
        return findings

    return processed


__all__ = [
    'TaintVerifiedScanner',
    'SecurityRelevantCallsFilter',
    'VerifiedFinding',
    'PYTHON_TAINT_SOURCES',
    'PYTHON_SQL_SINKS',
    'PYTHON_DANGEROUS_SINKS',
    'integrate_with_report_generator',
]
