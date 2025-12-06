"""
Security Verdict Generator for Patch Review System.

Analyzes patch changes for security vulnerabilities and generates
a comprehensive security verdict with CWE mappings.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum

import duckdb

from ..models import (
    PatchContext,
    DeltaCPG,
    Finding,
    Severity,
    SecurityVerdict,
    FindingCategory,
)
from ..analyzers import PatchDataFlowAnalyzer, DataFlowAnalysisResult

logger = logging.getLogger(__name__)


class VulnerabilityType(Enum):
    """Types of security vulnerabilities."""
    INJECTION = "injection"
    XSS = "xss"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    CRYPTOGRAPHY = "cryptography"
    SENSITIVE_DATA = "sensitive_data"
    CONFIGURATION = "configuration"
    INPUT_VALIDATION = "input_validation"
    RESOURCE_MANAGEMENT = "resource_management"


@dataclass
class SecurityPattern:
    """A security pattern to check for."""
    name: str
    description: str
    cwe_id: str
    severity: Severity
    vuln_type: VulnerabilityType
    pattern: str  # Regex pattern
    recommendation: str
    confidence: float = 0.8


@dataclass
class SecurityCheckResult:
    """Result of a single security check."""
    pattern: SecurityPattern
    matched: bool
    location: str
    code_snippet: str
    context: Dict[str, any] = field(default_factory=dict)


class SecurityVerdictGenerator:
    """
    Generates security verdicts for patch changes.

    Performs comprehensive security analysis including:
    - Pattern-based vulnerability detection
    - Taint analysis for injection vulnerabilities
    - Sanitization bypass detection
    - Sensitive data exposure checks
    - Configuration security issues
    """

    # Security patterns to check
    SECURITY_PATTERNS: List[SecurityPattern] = [
        # SQL Injection
        SecurityPattern(
            name="SQL Injection",
            description="Potential SQL injection via string concatenation",
            cwe_id="CWE-89",
            severity=Severity.CRITICAL,
            vuln_type=VulnerabilityType.INJECTION,
            pattern=r'(?:execute|query|cursor\.execute)\s*\(\s*["\'].*?%s|(?:\+|\.format|\$\{)',
            recommendation="Use parameterized queries or prepared statements",
            confidence=0.85
        ),
        SecurityPattern(
            name="SQL Injection (f-string)",
            description="Potential SQL injection via f-string interpolation",
            cwe_id="CWE-89",
            severity=Severity.CRITICAL,
            vuln_type=VulnerabilityType.INJECTION,
            pattern=r'(?:execute|query)\s*\(\s*f["\'].*?\{',
            recommendation="Use parameterized queries instead of f-strings",
            confidence=0.90
        ),

        # Command Injection
        SecurityPattern(
            name="Command Injection",
            description="Potential command injection via shell execution",
            cwe_id="CWE-78",
            severity=Severity.CRITICAL,
            vuln_type=VulnerabilityType.INJECTION,
            pattern=r'(?:os\.system|subprocess\.(?:call|run|Popen)|exec|eval)\s*\([^)]*(?:\+|%|\.format|f["\'])',
            recommendation="Use subprocess with shell=False and list arguments",
            confidence=0.85
        ),
        SecurityPattern(
            name="Unsafe Shell Execution",
            description="Shell execution with shell=True",
            cwe_id="CWE-78",
            severity=Severity.HIGH,
            vuln_type=VulnerabilityType.INJECTION,
            pattern=r'subprocess\.(?:call|run|Popen)\s*\([^)]*shell\s*=\s*True',
            recommendation="Avoid shell=True; use list arguments instead",
            confidence=0.80
        ),

        # XSS
        SecurityPattern(
            name="Reflected XSS",
            description="Potential XSS via unescaped user input in HTML",
            cwe_id="CWE-79",
            severity=Severity.HIGH,
            vuln_type=VulnerabilityType.XSS,
            pattern=r'(?:innerHTML|outerHTML|document\.write)\s*=\s*[^;]*(?:request|params|query|input)',
            recommendation="Use proper HTML encoding or a template engine with auto-escaping",
            confidence=0.75
        ),
        SecurityPattern(
            name="DOM XSS",
            description="Potential DOM-based XSS via unsafe sink",
            cwe_id="CWE-79",
            severity=Severity.HIGH,
            vuln_type=VulnerabilityType.XSS,
            pattern=r'(?:eval|setTimeout|setInterval|Function)\s*\([^)]*(?:location|document\.URL|window\.name)',
            recommendation="Avoid using eval/setTimeout with user-controlled data",
            confidence=0.80
        ),

        # Authentication Issues
        SecurityPattern(
            name="Hardcoded Credentials",
            description="Hardcoded password or API key detected",
            cwe_id="CWE-798",
            severity=Severity.CRITICAL,
            vuln_type=VulnerabilityType.AUTHENTICATION,
            pattern=r'(?:password|passwd|pwd|secret|api_key|apikey|auth_token)\s*=\s*["\'][^"\']{4,}["\']',
            recommendation="Use environment variables or a secrets manager",
            confidence=0.70
        ),
        SecurityPattern(
            name="Weak Password Check",
            description="Potentially weak password comparison",
            cwe_id="CWE-287",
            severity=Severity.HIGH,
            vuln_type=VulnerabilityType.AUTHENTICATION,
            pattern=r'password\s*==\s*["\']|if\s+password\s*==',
            recommendation="Use constant-time comparison for passwords (e.g., hmac.compare_digest)",
            confidence=0.65
        ),

        # Cryptography
        SecurityPattern(
            name="Weak Cryptography (MD5)",
            description="Use of weak hashing algorithm MD5",
            cwe_id="CWE-328",
            severity=Severity.MEDIUM,
            vuln_type=VulnerabilityType.CRYPTOGRAPHY,
            pattern=r'(?:md5|MD5)\s*\(|hashlib\.md5',
            recommendation="Use SHA-256 or stronger hashing algorithms",
            confidence=0.90
        ),
        SecurityPattern(
            name="Weak Cryptography (SHA1)",
            description="Use of weak hashing algorithm SHA1",
            cwe_id="CWE-328",
            severity=Severity.MEDIUM,
            vuln_type=VulnerabilityType.CRYPTOGRAPHY,
            pattern=r'(?:sha1|SHA1)\s*\(|hashlib\.sha1',
            recommendation="Use SHA-256 or stronger hashing algorithms",
            confidence=0.90
        ),
        SecurityPattern(
            name="Insecure Random",
            description="Use of non-cryptographic random for security purposes",
            cwe_id="CWE-338",
            severity=Severity.HIGH,
            vuln_type=VulnerabilityType.CRYPTOGRAPHY,
            pattern=r'random\.(?:random|randint|choice|shuffle)',
            recommendation="Use secrets module for cryptographic randomness",
            confidence=0.60
        ),

        # Sensitive Data
        SecurityPattern(
            name="Debug Mode Enabled",
            description="Debug mode enabled in production configuration",
            cwe_id="CWE-489",
            severity=Severity.MEDIUM,
            vuln_type=VulnerabilityType.CONFIGURATION,
            pattern=r'DEBUG\s*=\s*True|debug\s*:\s*true|\.debug\s*=\s*true',
            recommendation="Disable debug mode in production environments",
            confidence=0.70
        ),
        SecurityPattern(
            name="Sensitive Data Logging",
            description="Potential logging of sensitive information",
            cwe_id="CWE-532",
            severity=Severity.MEDIUM,
            vuln_type=VulnerabilityType.SENSITIVE_DATA,
            pattern=r'(?:log|print|console\.log)\s*\([^)]*(?:password|secret|token|key|credential)',
            recommendation="Avoid logging sensitive data; mask or redact if necessary",
            confidence=0.65
        ),

        # Path Traversal
        SecurityPattern(
            name="Path Traversal",
            description="Potential path traversal via user input in file operations",
            cwe_id="CWE-22",
            severity=Severity.HIGH,
            vuln_type=VulnerabilityType.INPUT_VALIDATION,
            pattern=r'(?:open|read|write|os\.path\.join)\s*\([^)]*(?:request|params|input|user)',
            recommendation="Validate and sanitize file paths; use os.path.realpath to resolve paths",
            confidence=0.70
        ),

        # Deserialization
        SecurityPattern(
            name="Unsafe Deserialization",
            description="Unsafe deserialization of untrusted data",
            cwe_id="CWE-502",
            severity=Severity.CRITICAL,
            vuln_type=VulnerabilityType.INPUT_VALIDATION,
            pattern=r'(?:pickle\.loads?|yaml\.(?:load|unsafe_load)|marshal\.loads?)\s*\(',
            recommendation="Use safe alternatives like json or yaml.safe_load",
            confidence=0.85
        ),

        # SSRF
        SecurityPattern(
            name="Server-Side Request Forgery",
            description="Potential SSRF via user-controlled URL",
            cwe_id="CWE-918",
            severity=Severity.HIGH,
            vuln_type=VulnerabilityType.INPUT_VALIDATION,
            pattern=r'(?:requests\.get|urllib\.request\.urlopen|fetch)\s*\([^)]*(?:request|params|input|url)',
            recommendation="Validate and whitelist allowed URLs; block internal network access",
            confidence=0.70
        ),

        # XXE
        SecurityPattern(
            name="XML External Entity",
            description="Potential XXE vulnerability in XML parsing",
            cwe_id="CWE-611",
            severity=Severity.HIGH,
            vuln_type=VulnerabilityType.INPUT_VALIDATION,
            pattern=r'(?:etree\.parse|minidom\.parse|xml\.sax\.parse)\s*\(',
            recommendation="Disable external entity processing in XML parsers",
            confidence=0.60
        ),
    ]

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        """
        Initialize the security verdict generator.

        Args:
            conn: DuckDB connection with CPG loaded
        """
        self.conn = conn
        self.dataflow_analyzer = PatchDataFlowAnalyzer(conn)

    def generate_verdict(
        self,
        patch: PatchContext,
        delta_cpg: DeltaCPG,
        dataflow_result: Optional[DataFlowAnalysisResult] = None
    ) -> SecurityVerdict:
        """
        Generate comprehensive security verdict for the patch.

        Args:
            patch: The patch context
            delta_cpg: Delta CPG with changes
            dataflow_result: Optional pre-computed dataflow analysis

        Returns:
            Complete security verdict
        """
        logger.info(f"Generating security verdict for patch {patch.patch_id}")

        findings: List[Finding] = []

        # 1. Pattern-based vulnerability detection
        pattern_findings = self._check_security_patterns(patch, delta_cpg)
        findings.extend(pattern_findings)

        # 2. Taint analysis
        if dataflow_result is None:
            dataflow_result = self.dataflow_analyzer.analyze_dataflow_changes(
                patch, delta_cpg
            )

        # Add taint path findings
        for taint_path in dataflow_result.new_taint_paths:
            findings.append(Finding(
                category=FindingCategory.SECURITY,
                severity=taint_path.severity,
                title=f"New Taint Path: {taint_path.source_type} → {taint_path.sink_type}",
                description=taint_path.description,
                location=f"{taint_path.source_file}:{taint_path.source_line}",
                code_snippet=taint_path.source_code,
                recommendation=taint_path.recommendation,
                confidence=taint_path.confidence,
                cwe_id=taint_path.cwe_id
            ))

        # Add sanitization bypass findings
        for bypass in dataflow_result.sanitization_bypasses:
            findings.append(Finding(
                category=FindingCategory.SECURITY,
                severity=Severity.CRITICAL,
                title=f"Sanitization Bypass: {bypass.bypass_type}",
                description=bypass.description,
                location=bypass.location,
                recommendation=bypass.recommendation,
                confidence=bypass.confidence
            ))

        # Add sensitive data exposure findings
        for exposure in dataflow_result.sensitive_data_findings:
            findings.append(Finding(
                category=FindingCategory.SECURITY,
                severity=exposure.severity,
                title=f"Sensitive Data Exposure: {exposure.data_type}",
                description=exposure.description,
                location=exposure.location,
                recommendation=exposure.recommendation,
                confidence=exposure.confidence
            ))

        # 3. Check for removed security controls
        removed_controls = self._check_removed_security_controls(delta_cpg)
        findings.extend(removed_controls)

        # 4. Check for new attack surface
        attack_surface_findings = self._analyze_attack_surface(patch, delta_cpg)
        findings.extend(attack_surface_findings)

        # Calculate security score
        score = self._calculate_security_score(findings)

        # Get vulnerability counts by type
        vuln_counts = self._count_vulnerabilities_by_type(findings)

        # Get CWE summary
        cwe_summary = self._get_cwe_summary(findings)

        verdict = SecurityVerdict(
            findings=findings,
            score=score,
            taint_paths=dataflow_result.new_taint_paths if dataflow_result else [],
            sanitization_bypasses=dataflow_result.sanitization_bypasses if dataflow_result else [],
            cwe_ids=list(cwe_summary.keys())
        )

        logger.info(
            f"Security verdict: score={score:.2f}, "
            f"critical={verdict.critical_count}, high={verdict.high_count}"
        )

        return verdict

    def _check_security_patterns(
        self,
        patch: PatchContext,
        delta_cpg: DeltaCPG
    ) -> List[Finding]:
        """Check for security patterns in added/modified code."""
        findings: List[Finding] = []

        # Get all added code from delta
        added_code_blocks: List[Tuple[str, int, str]] = []  # (file, line, code)

        for node in delta_cpg.nodes:
            if node.change_type.value == 'added' and node.code:
                added_code_blocks.append((
                    node.filename or 'unknown',
                    node.line_number or 0,
                    node.code
                ))

        # Also check hunks directly
        for file_diff in patch.files:
            for hunk in file_diff.hunks:
                # Iterate over added lines with line numbers
                for i, line in enumerate(hunk.added_lines):
                    if line.strip():  # Skip empty lines
                        line_num = hunk.new_start + i
                        added_code_blocks.append((
                            file_diff.path,
                            line_num,
                            line
                        ))

        # Check each pattern against added code
        for pattern in self.SECURITY_PATTERNS:
            compiled = re.compile(pattern.pattern, re.IGNORECASE)

            for filepath, line_num, code in added_code_blocks:
                if compiled.search(code):
                    findings.append(Finding(
                        category=FindingCategory.SECURITY,
                        severity=pattern.severity,
                        title=pattern.name,
                        description=pattern.description,
                        location=f"{filepath}:{line_num}",
                        code_snippet=code[:200],
                        recommendation=pattern.recommendation,
                        confidence=pattern.confidence,
                        cwe_id=pattern.cwe_id,
                        is_new=True
                    ))

        return findings

    def _check_removed_security_controls(
        self,
        delta_cpg: DeltaCPG
    ) -> List[Finding]:
        """Check for removed security controls (sanitization, validation)."""
        findings: List[Finding] = []

        security_control_patterns = [
            (r'sanitize|escape|encode|validate|verify|check', 'Security control'),
            (r'authenticate|authorize|permission|role', 'Authentication/Authorization'),
            (r'encrypt|decrypt|hash|sign', 'Cryptographic control'),
            (r'csrf|xsrf|token', 'CSRF protection'),
            (r'rate_limit|throttle', 'Rate limiting'),
        ]

        for node in delta_cpg.nodes:
            if node.change_type.value == 'deleted':
                code = node.code or node.name or ''
                for pattern, control_type in security_control_patterns:
                    if re.search(pattern, code, re.IGNORECASE):
                        findings.append(Finding(
                            category=FindingCategory.SECURITY,
                            severity=Severity.HIGH,
                            title=f"Removed {control_type}",
                            description=f"A {control_type.lower()} was removed from the codebase",
                            location=f"{node.filename}:{node.line_number}",
                            code_snippet=code[:200],
                            recommendation=f"Verify the {control_type.lower()} is no longer needed or moved elsewhere",
                            confidence=0.70,
                            is_new=True
                        ))
                        break  # Only one finding per removed node

        return findings

    def _analyze_attack_surface(
        self,
        patch: PatchContext,
        delta_cpg: DeltaCPG
    ) -> List[Finding]:
        """Analyze changes to the application's attack surface."""
        findings: List[Finding] = []

        # Patterns for attack surface expansion
        attack_surface_patterns = [
            (r'@app\.route|@router\.(?:get|post|put|delete)|@api_view', 'New API endpoint'),
            (r'def\s+(?:get|post|put|delete|patch|handle)', 'New HTTP handler'),
            (r'socket\.(?:listen|accept|bind)|websocket', 'New network listener'),
            (r'input\s*\(|raw_input|stdin', 'New user input'),
            (r'upload|file.*upload|multipart', 'New file upload'),
            (r'deserialize|fromjson|parse.*body', 'New deserialization point'),
        ]

        for node in delta_cpg.nodes:
            if node.change_type.value == 'added':
                code = node.code or ''
                for pattern, surface_type in attack_surface_patterns:
                    if re.search(pattern, code, re.IGNORECASE):
                        findings.append(Finding(
                            category=FindingCategory.SECURITY,
                            severity=Severity.LOW,
                            title=f"Attack Surface Expansion: {surface_type}",
                            description=f"The patch adds a {surface_type.lower()}, increasing attack surface",
                            location=f"{node.filename}:{node.line_number}",
                            code_snippet=code[:200],
                            recommendation="Ensure proper input validation and authentication for new entry points",
                            confidence=0.60,
                            is_new=True
                        ))
                        break

        return findings

    def _calculate_security_score(self, findings: List[Finding]) -> float:
        """
        Calculate security score (0-100).

        Higher is better (fewer vulnerabilities).
        """
        if not findings:
            return 100.0

        # Weights for different severities
        severity_weights = {
            Severity.CRITICAL: 25,
            Severity.HIGH: 15,
            Severity.MEDIUM: 8,
            Severity.LOW: 3,
            Severity.INFO: 1,
        }

        total_penalty = 0
        for finding in findings:
            weight = severity_weights.get(finding.severity, 1)
            total_penalty += weight * finding.confidence

        # Cap the penalty at 100
        score = max(0, 100 - total_penalty)
        return round(score, 2)

    def _count_vulnerabilities_by_type(
        self,
        findings: List[Finding]
    ) -> Dict[str, int]:
        """Count vulnerabilities by type."""
        counts: Dict[str, int] = {}

        for finding in findings:
            vuln_type = self._infer_vulnerability_type(finding)
            counts[vuln_type] = counts.get(vuln_type, 0) + 1

        return counts

    def _infer_vulnerability_type(self, finding: Finding) -> str:
        """Infer vulnerability type from finding."""
        title_lower = finding.title.lower()

        if 'injection' in title_lower or 'sql' in title_lower:
            return 'injection'
        elif 'xss' in title_lower or 'cross-site' in title_lower:
            return 'xss'
        elif 'auth' in title_lower or 'credential' in title_lower:
            return 'authentication'
        elif 'crypto' in title_lower or 'hash' in title_lower or 'random' in title_lower:
            return 'cryptography'
        elif 'sensitive' in title_lower or 'exposure' in title_lower:
            return 'sensitive_data'
        elif 'config' in title_lower or 'debug' in title_lower:
            return 'configuration'
        elif 'taint' in title_lower or 'sanitiz' in title_lower:
            return 'input_validation'
        else:
            return 'other'

    def _get_cwe_summary(self, findings: List[Finding]) -> Dict[str, int]:
        """Get summary of CWE IDs found."""
        summary: Dict[str, int] = {}

        for finding in findings:
            if finding.cwe_id:
                summary[finding.cwe_id] = summary.get(finding.cwe_id, 0) + 1

        return summary

    def _get_recommendation(
        self,
        score: float,
        findings: List[Finding]
    ) -> str:
        """Get overall recommendation based on score and findings."""
        critical_count = sum(1 for f in findings if f.severity == Severity.CRITICAL)
        high_count = sum(1 for f in findings if f.severity == Severity.HIGH)

        if critical_count > 0:
            return "BLOCK - Critical security vulnerabilities detected. Must be fixed before merge."
        elif high_count >= 3:
            return "BLOCK - Multiple high-severity security issues. Significant rework required."
        elif score < 50:
            return "REQUEST_CHANGES - Security score below threshold. Address findings before merge."
        elif score < 75:
            return "COMMENT - Some security concerns to address. Consider fixing before merge."
        else:
            return "APPROVE - No significant security issues detected."
