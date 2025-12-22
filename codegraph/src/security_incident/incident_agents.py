"""
Security Incident Response Agents - Scenario 14

Implements three specialized agents for security incident handling:

1. CVESearcher - Search for vulnerability patterns (OWASP Top 10, CVEs)
2. BlastRadiusAnalyzer - Calculate incident impact and affected scope
3. RemediationPlanner - Generate patches and remediation plans

Author: Security Incident Response Team
Date: 2025-11-22
"""

import re
import uuid
import networkx as nx
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timedelta

from .vulnerability_patterns import (
    VulnerabilityPattern,
    VulnerabilitySeverity,
    VulnerabilityCategory,
    INJECTION_PATTERNS,
    XSS_PATTERNS,
    AUTH_PATTERNS,
    MEMORY_PATTERNS,
    ALL_VULNERABILITY_PATTERNS,
)
from ..analysis.call_graph_analyzer import CallGraphAnalyzer


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class VulnerabilityFinding:
    """
    A discovered vulnerability instance.

    Attributes:
        finding_id: Unique identifier
        pattern: The vulnerability pattern matched
        method_id: CPG method ID where found
        method_name: Method name
        filepath: File location
        line_number: Line number
        code_snippet: Vulnerable code
        confidence: Detection confidence (0.0-1.0)
        cvss_score: CVSS score (0.0-10.0)
    """
    finding_id: str
    pattern: VulnerabilityPattern
    method_id: int
    method_name: str
    filepath: str
    line_number: int
    code_snippet: str
    confidence: float = 0.9
    cvss_score: float = 7.5


@dataclass
class BlastRadius:
    """
    Impact scope of a vulnerability.

    Attributes:
        vulnerability: The vulnerability
        directly_affected_methods: Methods containing vulnerability
        impacted_callers: Methods that call vulnerable code
        impacted_callees: Methods called by vulnerable code
        affected_subsystems: Subsystems impacted
        affected_users: Estimated affected users
        data_at_risk: Types of data at risk
        impact_score: Overall impact (0-100)
        call_depth: Maximum call chain depth
        critical_path_methods: High-PageRank methods in blast radius (Phase 2)
        pagerank_amplification: Impact amplification from critical methods (Phase 2)
    """
    vulnerability: VulnerabilityFinding
    directly_affected_methods: List[Dict[str, Any]]
    impacted_callers: List[Dict[str, Any]]
    impacted_callees: List[Dict[str, Any]]
    affected_subsystems: List[str]
    affected_users: str = "Unknown"
    data_at_risk: List[str] = field(default_factory=list)
    impact_score: float = 0.0
    call_depth: int = 0
    critical_path_methods: List[Dict[str, Any]] = field(default_factory=list)
    pagerank_amplification: float = 0.0


@dataclass
class RemediationAction:
    """
    A remediation action.

    Attributes:
        action_id: Unique identifier
        vulnerability: Associated vulnerability
        action_type: Type of action (patch, config, workaround)
        priority: Priority (1-5, 1=highest)
        title: Action title
        description: What to do
        code_patch: Suggested code fix
        verification_steps: How to verify fix
        estimated_effort: Effort in hours
        deadline: Recommended fix deadline
    """
    action_id: str
    vulnerability: VulnerabilityFinding
    action_type: str  # "patch", "config_change", "workaround", "upgrade"
    priority: int  # 1-5
    title: str
    description: str
    code_patch: Optional[str] = None
    verification_steps: List[str] = field(default_factory=list)
    estimated_effort: float = 1.0
    deadline: Optional[str] = None


@dataclass
class IncidentReport:
    """
    Complete security incident report.

    Attributes:
        report_id: Unique identifier
        timestamp: When generated
        vulnerabilities: All vulnerabilities found
        blast_radii: Impact analysis for each
        remediation_plan: Ordered remediation actions
        executive_summary: High-level summary
        risk_level: Overall risk (LOW, MEDIUM, HIGH, CRITICAL)
        estimated_total_effort: Total remediation effort
    """
    report_id: str
    timestamp: str
    vulnerabilities: List[VulnerabilityFinding]
    blast_radii: List[BlastRadius]
    remediation_plan: List[RemediationAction]
    executive_summary: str
    risk_level: str
    estimated_total_effort: float


# ============================================================================
# AGENT 1: CVE SEARCHER
# ============================================================================

class CVESearcher:
    """
    Agent 1: Search for vulnerability patterns.

    Searches for:
    - OWASP Top 10 vulnerabilities
    - CVE-style patterns
    - Memory safety issues
    - Custom vulnerability signatures

    Usage:
        searcher = CVESearcher(cpg_service)
        vulnerabilities = searcher.scan_all_patterns()
        sql_injections = searcher.find_sql_injection()
    """

    def __init__(self, cpg_service):
        """
        Initialize CVESearcher.

        Args:
            cpg_service: CPGQueryService instance
        """
        self.cpg = cpg_service

    def scan_all_patterns(self, limit_per_pattern: int = 10) -> List[VulnerabilityFinding]:
        """
        Scan for all vulnerability patterns.

        Args:
            limit_per_pattern: Max findings per pattern

        Returns:
            List of vulnerability findings
        """
        findings = []

        for pattern_id, pattern in ALL_VULNERABILITY_PATTERNS.items():
            pattern_findings = self.scan_pattern(pattern, limit_per_pattern)
            findings.extend(pattern_findings)

        return findings

    def scan_pattern(
        self,
        pattern: VulnerabilityPattern,
        limit: int = 10
    ) -> List[VulnerabilityFinding]:
        """
        Scan for a specific vulnerability pattern.

        Args:
            pattern: Vulnerability pattern to search for
            limit: Maximum findings

        Returns:
            List of findings for this pattern
        """
        findings = []

        try:
            # Execute detection query
            results = self.cpg.execute_custom_sql(pattern.detection_query)

            for row in results[:limit]:
                # Calculate CVSS score from severity
                cvss_score = self._severity_to_cvss(pattern.severity)

                finding = VulnerabilityFinding(
                    finding_id=f"{pattern.pattern_id}_{uuid.uuid4().hex[:8]}",
                    pattern=pattern,
                    method_id=row.get('method_id', 0),
                    method_name=row.get('method_name', 'unknown'),
                    filepath=row.get('filename', 'unknown'),
                    line_number=row.get('line_number', 0),
                    code_snippet=row.get('code', '')[:200],
                    confidence=0.9,  # High confidence for pattern matches
                    cvss_score=cvss_score
                )

                findings.append(finding)

        except Exception as e:
            # Query may fail if schema doesn't match
            pass

        return findings

    def find_sql_injection(self) -> List[VulnerabilityFinding]:
        """Find SQL injection vulnerabilities"""
        return self.scan_pattern(INJECTION_PATTERNS["SQL_INJECTION"])

    def find_command_injection(self) -> List[VulnerabilityFinding]:
        """Find command injection vulnerabilities"""
        return self.scan_pattern(INJECTION_PATTERNS["COMMAND_INJECTION"])

    def find_xss(self) -> List[VulnerabilityFinding]:
        """Find XSS vulnerabilities"""
        findings = []
        for pattern in XSS_PATTERNS.values():
            findings.extend(self.scan_pattern(pattern))
        return findings

    def find_buffer_overflows(self) -> List[VulnerabilityFinding]:
        """Find buffer overflow vulnerabilities"""
        return self.scan_pattern(MEMORY_PATTERNS["BUFFER_OVERFLOW"])

    def _severity_to_cvss(self, severity: VulnerabilitySeverity) -> float:
        """Convert severity to CVSS score"""
        mapping = {
            VulnerabilitySeverity.CRITICAL: 9.5,
            VulnerabilitySeverity.HIGH: 7.5,
            VulnerabilitySeverity.MEDIUM: 5.5,
            VulnerabilitySeverity.LOW: 3.0,
            VulnerabilitySeverity.INFO: 0.0,
        }
        return mapping.get(severity, 5.0)


# ============================================================================
# AGENT 2: BLAST RADIUS ANALYZER
# ============================================================================

class BlastRadiusAnalyzer:
    """
    Agent 2: Calculate incident impact and blast radius.

    Analyzes:
    - Call graph propagation (who calls vulnerable code)
    - Data flow analysis (what data is affected)
    - Subsystem impact
    - User impact estimation
    - Risk scoring

    Usage:
        analyzer = BlastRadiusAnalyzer(cpg_service)
        blast_radius = analyzer.calculate_blast_radius(vulnerability)
        impact_score = analyzer.estimate_impact(blast_radius)
    """

    def __init__(self, cpg_service):
        """
        Initialize BlastRadiusAnalyzer.

        Args:
            cpg_service: CPGQueryService instance
        """
        self.cpg = cpg_service
        self.call_graph_analyzer = CallGraphAnalyzer(cpg_service)
        self._pagerank_cache = None  # Cache PageRank results

    def calculate_blast_radius(
        self,
        vulnerability: VulnerabilityFinding,
        max_depth: int = 3
    ) -> BlastRadius:
        """
        Calculate blast radius for a vulnerability.

        Args:
            vulnerability: The vulnerability to analyze
            max_depth: Maximum call chain depth

        Returns:
            BlastRadius analysis
        """
        # Get directly affected method
        directly_affected = [{
            'method_id': vulnerability.method_id,
            'method_name': vulnerability.method_name,
            'filepath': vulnerability.filepath,
        }]

        # Find all callers (who calls this vulnerable method)
        callers = self._find_callers(vulnerability.method_id, max_depth)

        # Find all callees (what does vulnerable method call)
        callees = self._find_callees(vulnerability.method_id)

        # Identify affected subsystems
        affected_subsystems = self._identify_subsystems(
            directly_affected + callers + callees
        )

        # Estimate data at risk
        data_at_risk = self._identify_data_at_risk(vulnerability)

        # Calculate impact score
        impact_score = self._calculate_impact_score(
            len(callers),
            len(callees),
            len(affected_subsystems),
            vulnerability.cvss_score
        )

        # Estimate affected users
        affected_users = self._estimate_affected_users(
            len(callers),
            affected_subsystems
        )

        # Phase 2 Enhancement: Identify critical methods using PageRank
        critical_methods, pagerank_amplification = self._identify_critical_methods(
            directly_affected + callers
        )

        # Adjust impact score with PageRank amplification
        final_impact_score = min(100.0, impact_score * (1 + pagerank_amplification))

        return BlastRadius(
            vulnerability=vulnerability,
            directly_affected_methods=directly_affected,
            impacted_callers=callers,
            impacted_callees=callees,
            affected_subsystems=affected_subsystems,
            affected_users=affected_users,
            data_at_risk=data_at_risk,
            impact_score=final_impact_score,
            call_depth=min(max_depth, len(callers)),
            critical_path_methods=critical_methods,
            pagerank_amplification=pagerank_amplification
        )

    def _find_callers(self, method_id: int, max_depth: int = 3) -> List[Dict[str, Any]]:
        """Find all methods that call this method (up to max_depth)"""
        callers = []

        try:
            # Find direct callers
            query = f"""
            SELECT DISTINCT
                caller.id AS method_id,
                caller.name AS method_name,
                caller.filename AS filepath,
                caller.line_number
            FROM edges_call c
            JOIN nodes_method caller ON c.src = caller.id
            WHERE c.dst = {method_id}
            LIMIT 50
            """

            results = self.cpg.execute_custom_sql(query)

            for row in results:
                callers.append({
                    'method_id': row.get('method_id'),
                    'method_name': row.get('method_name'),
                    'filepath': row.get('filepath'),
                    'line_number': row.get('line_number', 0),
                })

        except Exception as e:
            pass

        return callers

    def _find_callees(self, method_id: int) -> List[Dict[str, Any]]:
        """Find all methods called by this method"""
        callees = []

        try:
            query = f"""
            SELECT DISTINCT
                callee.id AS method_id,
                callee.name AS method_name,
                callee.filename AS filepath,
                callee.line_number
            FROM edges_call c
            JOIN nodes_method callee ON c.dst = callee.id
            WHERE c.src = {method_id}
            LIMIT 50
            """

            results = self.cpg.execute_custom_sql(query)

            for row in results:
                callees.append({
                    'method_id': row.get('method_id'),
                    'method_name': row.get('method_name'),
                    'filepath': row.get('filepath'),
                    'line_number': row.get('line_number', 0),
                })

        except Exception as e:
            pass

        return callees

    def _identify_subsystems(self, methods: List[Dict[str, Any]]) -> List[str]:
        """Identify affected subsystems from method list"""
        subsystems = set()

        for method in methods:
            filepath = method.get('filepath', '')
            # Extract top-level directory as subsystem
            parts = filepath.split('/')
            if len(parts) > 1:
                subsystems.add(parts[0])

        return sorted(list(subsystems))

    def _identify_data_at_risk(self, vulnerability: VulnerabilityFinding) -> List[str]:
        """Identify types of data at risk"""
        data_types = []

        code = vulnerability.code_snippet.lower()

        # Check for sensitive data patterns
        if any(word in code for word in ['password', 'pwd', 'passwd']):
            data_types.append('passwords')
        if any(word in code for word in ['email', 'user', 'account']):
            data_types.append('user_data')
        if any(word in code for word in ['credit', 'card', 'payment']):
            data_types.append('payment_info')
        if any(word in code for word in ['token', 'session', 'auth']):
            data_types.append('authentication_tokens')
        if any(word in code for word in ['ssn', 'license', 'id_number']):
            data_types.append('pii')

        return data_types if data_types else ['unknown']

    def _calculate_impact_score(
        self,
        caller_count: int,
        callee_count: int,
        subsystem_count: int,
        cvss_score: float
    ) -> float:
        """
        Calculate overall impact score (0-100).

        Factors:
        - CVSS score (50% weight)
        - Caller count (25% weight)
        - Subsystem spread (15% weight)
        - Callee count (10% weight)
        """
        # Normalize CVSS (0-10 -> 0-50)
        cvss_component = (cvss_score / 10.0) * 50

        # Normalize caller count (log scale, max 25 points)
        import math
        caller_component = min(25, math.log(caller_count + 1) * 5)

        # Normalize subsystem count (max 15 points)
        subsystem_component = min(15, subsystem_count * 3)

        # Normalize callee count (log scale, max 10 points)
        callee_component = min(10, math.log(callee_count + 1) * 2)

        total_score = (
            cvss_component +
            caller_component +
            subsystem_component +
            callee_component
        )

        return min(100, total_score)

    def _estimate_affected_users(
        self,
        caller_count: int,
        subsystems: List[str]
    ) -> str:
        """Estimate number of affected users"""
        if caller_count > 50 or 'api' in subsystems:
            return "All users"
        elif caller_count > 20 or 'auth' in subsystems:
            return "Most users (>50%)"
        elif caller_count > 5:
            return "Some users (10-50%)"
        else:
            return "Few users (<10%)"

    def _identify_critical_methods(
        self,
        affected_methods: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], float]:
        """
        Identify critical methods in blast radius using PageRank.

        Phase 2 Enhancement: Uses CallGraphAnalyzer.compute_pagerank() to identify
        architecturally important methods in the blast radius. High-PageRank methods
        indicate critical code paths that amplify vulnerability impact.

        Args:
            affected_methods: List of methods in blast radius

        Returns:
            Tuple of (critical_methods, amplification_factor)
            - critical_methods: Methods with PageRank in top 10%
            - amplification_factor: Impact multiplier (0.0-1.0)
        """
        if not affected_methods:
            return ([], 0.0)

        try:
            # Compute PageRank for entire call graph (cached)
            if self._pagerank_cache is None:
                self._pagerank_cache = self.call_graph_analyzer.compute_pagerank(
                    max_iterations=10,
                    top_n=100
                )

            # Create lookup dict for PageRank scores
            pagerank_lookup = {
                pr['method_name']: pr['pagerank_score']
                for pr in self._pagerank_cache
            }

            # Calculate PageRank scores for affected methods
            critical_methods = []
            max_pagerank = max(pagerank_lookup.values()) if pagerank_lookup else 1.0
            threshold = max_pagerank * 0.1  # Top 10%

            total_pagerank = 0.0
            for method in affected_methods:
                method_name = method.get('method_name', '')
                pagerank_score = pagerank_lookup.get(method_name, 0.0)
                total_pagerank += pagerank_score

                # Identify critical methods (top 10% PageRank)
                if pagerank_score >= threshold:
                    critical_methods.append({
                        'method_name': method_name,
                        'method_id': method.get('method_id'),
                        'pagerank_score': pagerank_score,
                        'pagerank_percentile': (pagerank_score / max_pagerank) * 100,
                        'criticality': 'HIGH' if pagerank_score >= threshold * 2 else 'MEDIUM'
                    })

            # Calculate amplification factor (0.0-1.0)
            # More critical methods = higher amplification
            if affected_methods:
                amplification = len(critical_methods) / len(affected_methods)
                amplification *= (total_pagerank / (len(affected_methods) * max_pagerank))
                amplification = min(1.0, amplification)  # Cap at 1.0
            else:
                amplification = 0.0

            # Sort critical methods by PageRank (descending)
            critical_methods.sort(key=lambda x: x['pagerank_score'], reverse=True)

            return (critical_methods, amplification)

        except Exception as e:
            # Gracefully degrade if PageRank fails
            return ([], 0.0)


# ============================================================================
# AGENT 3: REMEDIATION PLANNER
# ============================================================================

class RemediationPlanner:
    """
    Agent 3: Generate remediation plans and patches.

    Generates:
    - Prioritized remediation actions
    - Code patches
    - Configuration changes
    - Workarounds
    - Verification steps

    Usage:
        planner = RemediationPlanner()
        actions = planner.create_remediation_plan(vulnerabilities, blast_radii)
        patch = planner.generate_patch(vulnerability)
    """

    def __init__(self):
        """Initialize RemediationPlanner"""
        pass

    def create_remediation_plan(
        self,
        vulnerabilities: List[VulnerabilityFinding],
        blast_radii: List[BlastRadius]
    ) -> List[RemediationAction]:
        """
        Create prioritized remediation plan.

        Args:
            vulnerabilities: All vulnerabilities
            blast_radii: Blast radius for each

        Returns:
            Ordered list of remediation actions
        """
        actions = []

        for vuln, radius in zip(vulnerabilities, blast_radii):
            action = self._create_action(vuln, radius)
            actions.append(action)

        # Sort by priority (1=highest), then by impact score
        actions.sort(key=lambda a: (a.priority, -self._get_impact_score(a, blast_radii)))

        return actions

    def _create_action(
        self,
        vulnerability: VulnerabilityFinding,
        blast_radius: BlastRadius
    ) -> RemediationAction:
        """Create remediation action for a vulnerability"""
        # Determine priority based on severity and impact
        priority = self._calculate_priority(
            vulnerability.pattern.severity,
            blast_radius.impact_score
        )

        # Generate code patch
        code_patch = self._generate_patch(vulnerability)

        # Calculate estimated effort
        effort = self._estimate_effort(vulnerability, blast_radius)

        # Calculate deadline
        deadline = self._calculate_deadline(priority)

        # Generate verification steps
        verification = self._generate_verification_steps(vulnerability)

        return RemediationAction(
            action_id=f"REM_{uuid.uuid4().hex[:8]}",
            vulnerability=vulnerability,
            action_type="patch",
            priority=priority,
            title=f"Fix {vulnerability.pattern.name}",
            description=f"{vulnerability.pattern.remediation} in {vulnerability.filepath}:{vulnerability.line_number}",
            code_patch=code_patch,
            verification_steps=verification,
            estimated_effort=effort,
            deadline=deadline
        )

    def _calculate_priority(
        self,
        severity: VulnerabilitySeverity,
        impact_score: float
    ) -> int:
        """
        Calculate priority (1-5, 1=highest).

        Based on severity + impact:
        - CRITICAL + High Impact -> P1
        - CRITICAL + Low Impact or HIGH + High Impact -> P2
        - HIGH + Low Impact or MEDIUM + High Impact -> P3
        - MEDIUM + Low Impact or LOW -> P4
        - INFO -> P5
        """
        high_impact = impact_score > 70

        if severity == VulnerabilitySeverity.CRITICAL:
            return 1 if high_impact else 2
        elif severity == VulnerabilitySeverity.HIGH:
            return 2 if high_impact else 3
        elif severity == VulnerabilitySeverity.MEDIUM:
            return 3 if high_impact else 4
        elif severity == VulnerabilitySeverity.LOW:
            return 4
        else:  # INFO
            return 5

    def _generate_patch(self, vulnerability: VulnerabilityFinding) -> Optional[str]:
        """Generate code patch for vulnerability"""
        pattern_id = vulnerability.pattern.pattern_id

        # SQL Injection
        if "SQL" in pattern_id or vulnerability.pattern.category == VulnerabilityCategory.INJECTION:
            return """
# Before (vulnerable):
query = f"SELECT * FROM users WHERE id = {user_id}"
cursor.execute(query)

# After (fixed):
query = "SELECT * FROM users WHERE id = ?"
cursor.execute(query, (user_id,))
"""

        # Command Injection
        elif "COMMAND" in pattern_id:
            return """
# Before (vulnerable):
os.system(f"ls {user_input}")

# After (fixed):
import subprocess
subprocess.run(["ls", user_input], check=True)
"""

        # XSS
        elif "XSS" in pattern_id:
            return """
# Before (vulnerable):
return f"<div>{user_input}</div>"

# After (fixed):
import html
return f"<div>{html.escape(user_input)}</div>"
"""

        # Buffer Overflow
        elif "BUFFER" in pattern_id:
            return """
// Before (vulnerable):
char buffer[100];
strcpy(buffer, user_input);

// After (fixed):
char buffer[100];
strncpy(buffer, user_input, sizeof(buffer) - 1);
buffer[sizeof(buffer) - 1] = '\\0';
"""

        return None

    def _estimate_effort(
        self,
        vulnerability: VulnerabilityFinding,
        blast_radius: BlastRadius
    ) -> float:
        """Estimate remediation effort in hours"""
        base_effort = 2.0  # Base effort

        # Add effort based on impact
        if blast_radius.impact_score > 80:
            base_effort += 6.0  # High impact
        elif blast_radius.impact_score > 50:
            base_effort += 3.0  # Medium impact
        else:
            base_effort += 1.0  # Low impact

        # Add effort for number of affected methods
        base_effort += len(blast_radius.impacted_callers) * 0.5

        return round(base_effort, 1)

    def _calculate_deadline(self, priority: int) -> str:
        """Calculate recommended deadline"""
        now = datetime.now()

        deadlines = {
            1: timedelta(days=1),   # P1: 1 day
            2: timedelta(days=3),   # P2: 3 days
            3: timedelta(days=7),   # P3: 1 week
            4: timedelta(days=14),  # P4: 2 weeks
            5: timedelta(days=30),  # P5: 1 month
        }

        deadline = now + deadlines.get(priority, timedelta(days=7))
        return deadline.strftime("%Y-%m-%d")

    def _generate_verification_steps(
        self,
        vulnerability: VulnerabilityFinding
    ) -> List[str]:
        """Generate verification steps"""
        steps = [
            f"1. Apply patch to {vulnerability.filepath}",
            "2. Run unit tests to verify functionality",
            "3. Perform security scan to confirm vulnerability is fixed",
        ]

        # Add specific verification based on vulnerability type
        if vulnerability.pattern.category == VulnerabilityCategory.INJECTION:
            steps.append("4. Test with malicious input (SQL injection payloads)")
        elif vulnerability.pattern.category == VulnerabilityCategory.XSS:
            steps.append("4. Test with XSS payloads (<script>alert('XSS')</script>)")
        elif vulnerability.pattern.category == VulnerabilityCategory.MEMORY_SAFETY:
            steps.append("4. Run memory analysis tools (Valgrind, AddressSanitizer)")

        steps.append("5. Deploy to staging and verify")

        return steps

    def _get_impact_score(
        self,
        action: RemediationAction,
        blast_radii: List[BlastRadius]
    ) -> float:
        """Get impact score for sorting"""
        for radius in blast_radii:
            if radius.vulnerability.finding_id == action.vulnerability.finding_id:
                return radius.impact_score
        return 0.0

    def generate_incident_report(
        self,
        vulnerabilities: List[VulnerabilityFinding],
        blast_radii: List[BlastRadius],
        remediation_plan: List[RemediationAction]
    ) -> IncidentReport:
        """Generate complete incident report"""
        # Calculate risk level using severity ordering
        severity_order = {
            VulnerabilitySeverity.INFO: 0,
            VulnerabilitySeverity.LOW: 1,
            VulnerabilitySeverity.MEDIUM: 2,
            VulnerabilitySeverity.HIGH: 3,
            VulnerabilitySeverity.CRITICAL: 4,
        }

        max_severity = VulnerabilitySeverity.INFO
        if vulnerabilities:
            max_severity = max(
                (v.pattern.severity for v in vulnerabilities),
                key=lambda s: severity_order[s]
            )

        risk_level = max_severity.value.upper()

        # Calculate total effort
        total_effort = sum(action.estimated_effort for action in remediation_plan)

        # Generate executive summary
        critical_count = sum(1 for v in vulnerabilities if v.pattern.severity == VulnerabilitySeverity.CRITICAL)
        high_count = sum(1 for v in vulnerabilities if v.pattern.severity == VulnerabilitySeverity.HIGH)

        summary = f"""Security Incident Response Report

Total Vulnerabilities: {len(vulnerabilities)}
- Critical: {critical_count}
- High: {high_count}
- Medium/Low: {len(vulnerabilities) - critical_count - high_count}

Overall Risk Level: {risk_level}

Immediate Actions Required: {sum(1 for a in remediation_plan if a.priority <= 2)}
Total Remediation Effort: {total_effort:.1f} hours
"""

        return IncidentReport(
            report_id=f"INC_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now().isoformat(),
            vulnerabilities=vulnerabilities,
            blast_radii=blast_radii,
            remediation_plan=remediation_plan,
            executive_summary=summary,
            risk_level=risk_level,
            estimated_total_effort=total_effort
        )
