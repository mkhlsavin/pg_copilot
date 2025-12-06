"""
Security Analysis Agents for Enhanced Security Audit Workflow

Week 5, Task 2.2: Specialized Security Agents
Phase 2: Quality & Security Enhancement

Implements 4 specialized agents:
1. SecurityScanner - Query CPG for security vulnerabilities using patterns
2. DataFlowAnalyzer - Trace data flows from taint sources to sinks
3. VulnerabilityReporter - Generate structured vulnerability reports
4. RemediationAdvisor - Suggest fixes based on vulnerability patterns
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .security_patterns import (
    SecurityPattern,
    SECURITY_PATTERNS,
    VulnerabilitySeverity,
    VulnerabilityCategory,
    get_critical_patterns,
    get_patterns_by_category,
)
from ..services.cpg_query_service import CPGQueryService

logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SecurityFinding:
    """Represents a security vulnerability finding"""
    finding_id: str
    pattern_id: str
    pattern_name: str
    category: str
    severity: str
    method_id: int
    method_name: str
    filename: str
    line_number: int
    code_snippet: str
    description: str
    cwe_ids: List[str]
    confidence: float  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataFlowPath:
    """Represents a taint flow path from source to sink"""
    path_id: str
    source_method: str
    source_file: str
    source_line: int
    sink_method: str
    sink_file: str
    sink_line: int
    path_length: int
    intermediate_nodes: List[Dict[str, Any]]
    taint_type: str  # e.g., "user_input", "file_read"
    sanitized: bool  # Whether path includes sanitization


@dataclass
class VulnerabilityReport:
    """Structured vulnerability report"""
    report_id: str
    timestamp: str
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    findings_by_category: Dict[str, int]
    findings: List[SecurityFinding]
    data_flows: List[DataFlowPath]
    summary: str
    recommendations: List[str]


@dataclass
class RemediationAdvice:
    """Remediation advice for a vulnerability"""
    finding_id: str
    pattern_id: str
    remediation_steps: List[str]
    code_example: str
    references: List[str]
    estimated_effort: str  # "low", "medium", "high"
    priority: int  # 1-10


# ============================================================================
# AGENT 1: SECURITY SCANNER
# ============================================================================

class SecurityScanner:
    """
    Scans CPG for security vulnerabilities using pattern library

    Responsibilities:
    - Execute CPGQL queries from security patterns
    - Identify potential vulnerabilities
    - Rank findings by severity
    - Filter false positives
    """

    def __init__(self, cpg_service: Optional[CPGQueryService] = None):
        self.cpg = cpg_service
        self._own_cpg = cpg_service is None

    def __enter__(self):
        if self._own_cpg:
            self.cpg = CPGQueryService()
            self.cpg.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._own_cpg and self.cpg:
            self.cpg.__exit__(exc_type, exc_val, exc_tb)

    def scan_all_patterns(self, limit_per_pattern: int = 50) -> List[SecurityFinding]:
        """
        Scan for all vulnerability patterns

        Args:
            limit_per_pattern: Max findings per pattern

        Returns:
            List of security findings sorted by severity
        """
        logger.info("Starting comprehensive security scan with all patterns")
        all_findings = []

        for pattern_name, pattern in SECURITY_PATTERNS.items():
            try:
                findings = self.scan_pattern(pattern, limit_per_pattern)
                all_findings.extend(findings)
                logger.info(f"Pattern {pattern_name}: found {len(findings)} potential issues")
            except Exception as e:
                logger.error(f"Error scanning pattern {pattern_name}: {e}")

        # Sort by severity (critical first)
        severity_order = {
            VulnerabilitySeverity.CRITICAL.value: 0,
            VulnerabilitySeverity.HIGH.value: 1,
            VulnerabilitySeverity.MEDIUM.value: 2,
            VulnerabilitySeverity.LOW.value: 3,
            VulnerabilitySeverity.INFO.value: 4,
        }
        all_findings.sort(key=lambda f: severity_order.get(f.severity, 99))

        logger.info(f"Total findings: {len(all_findings)}")
        return all_findings

    def scan_pattern(self, pattern: SecurityPattern, limit: int = 50) -> List[SecurityFinding]:
        """
        Scan for a specific vulnerability pattern

        Args:
            pattern: Security pattern to scan for
            limit: Max findings to return

        Returns:
            List of security findings
        """
        try:
            # Execute pattern's CPGQL query
            results = self.cpg.execute_query(pattern.cpgql_query)

            findings = []
            for idx, row in enumerate(results[:limit]):
                finding = SecurityFinding(
                    finding_id=f"{pattern.id}_{idx:03d}",
                    pattern_id=pattern.id,
                    pattern_name=pattern.name,
                    category=pattern.category.value,
                    severity=pattern.severity.value,
                    method_id=row.get('id', 0),
                    method_name=row.get('method_name', 'unknown'),
                    filename=row.get('filename', 'unknown'),
                    line_number=row.get('line_number', 0),
                    code_snippet=(row.get('code') or '')[:200],  # Truncate, handle None
                    description=pattern.description,
                    cwe_ids=pattern.cwe_ids,
                    confidence=self._calculate_confidence(row, pattern),
                    metadata=row
                )
                findings.append(finding)

            return findings

        except Exception as e:
            logger.error(f"Error executing pattern {pattern.id}: {e}")
            return []

    def scan_patterns(
        self,
        pattern_names: List[str],
        limit_per_pattern: int = 20
    ) -> List[SecurityFinding]:
        """
        Scan for specific vulnerability patterns by name.

        Phase 2 Enhancement: Intent-based pattern filtering.

        Args:
            pattern_names: List of pattern IDs/names to scan (e.g., ['SQL_INJECTION', 'BUFFER_OVERFLOW'])
            limit_per_pattern: Max findings per pattern

        Returns:
            List of security findings from matched patterns
        """
        all_findings = []

        for pattern_id, pattern in SECURITY_PATTERNS.items():
            # Match by pattern ID or name
            if pattern_id in pattern_names or pattern.name in pattern_names:
                try:
                    logger.info(f"Scanning pattern: {pattern.id}")
                    findings = self.scan_pattern(pattern, limit_per_pattern)
                    all_findings.extend(findings)
                except Exception as e:
                    logger.error(f"Error scanning pattern {pattern.id}: {e}")
                    continue

        # Sort by severity
        severity_order = {
            VulnerabilitySeverity.CRITICAL.value: 0,
            VulnerabilitySeverity.HIGH.value: 1,
            VulnerabilitySeverity.MEDIUM.value: 2,
            VulnerabilitySeverity.LOW.value: 3,
            VulnerabilitySeverity.INFO.value: 4,
        }
        all_findings.sort(key=lambda f: severity_order.get(f.severity, 99))

        logger.info(f"Intent-filtered scan found {len(all_findings)} findings from {len(pattern_names)} patterns")
        return all_findings

    def scan_by_category(
        self,
        category: VulnerabilityCategory,
        limit: int = 100
    ) -> List[SecurityFinding]:
        """Scan for all patterns in a specific category"""
        patterns = get_patterns_by_category(category)
        findings = []

        for pattern in patterns:
            pattern_findings = self.scan_pattern(pattern, limit)
            findings.extend(pattern_findings)

        return findings

    def scan_critical_only(self, limit: int = 100) -> List[SecurityFinding]:
        """Scan only for critical severity vulnerabilities"""
        critical_patterns = get_critical_patterns()
        findings = []

        for pattern in critical_patterns:
            pattern_findings = self.scan_pattern(pattern, limit)
            findings.extend(pattern_findings)

        return findings

    def _calculate_confidence(self, result: Dict[str, Any], pattern: SecurityPattern) -> float:
        """
        Calculate confidence score for a finding (0.0 to 1.0)

        Heuristics:
        - Test files: lower confidence
        - Complex methods: higher confidence for certain patterns
        - Presence of validation code: lower confidence
        """
        confidence = 0.8  # Base confidence

        # Lower confidence for test files
        filename = result.get('filename') or ''
        if 'test' in filename.lower() or filename.startswith('src/test/'):
            confidence *= 0.3

        # Adjust based on method complexity
        complexity = result.get('complexity', 0)
        if pattern.category == VulnerabilityCategory.MEMORY_SAFETY:
            if complexity > 10:
                confidence *= 1.2  # More complex = more likely to have bugs

        # Lower confidence if validation keywords present
        code = result.get('code') or ''
        validation_keywords = ['validate', 'sanitize', 'check', 'assert']
        if any(kw in code.lower() for kw in validation_keywords):
            confidence *= 0.7

        return min(confidence, 1.0)


# ============================================================================
# AGENT 2: DATA FLOW ANALYZER
# ============================================================================

class DataFlowAnalyzer:
    """
    Traces data flows from taint sources to sinks

    Responsibilities:
    - Identify taint sources (user input, file I/O, network)
    - Find potential sinks (SQL exec, command exec, file write)
    - Trace paths between sources and sinks
    - Detect sanitization points
    """

    def __init__(self, cpg_service: Optional[CPGQueryService] = None):
        self.cpg = cpg_service
        self._own_cpg = cpg_service is None

    def __enter__(self):
        if self._own_cpg:
            self.cpg = CPGQueryService()
            self.cpg.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._own_cpg and self.cpg:
            self.cpg.__exit__(exc_type, exc_val, exc_tb)

    def find_taint_sources(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Find methods that handle untrusted input (taint sources)

        Returns:
            List of taint source methods with metadata
        """
        # Use correct schema: nodes_tag + edges_tagged_by instead of semantic_tags
        query = """
            SELECT DISTINCT
                m.id,
                m.name AS method_name,
                m.full_name,
                m.filename,
                m.line_number,
                nt.name AS tag,
                nt.value AS category
            FROM nodes_method m
            JOIN edges_tagged_by etb ON etb.src = m.id
            JOIN nodes_tag nt ON nt.id = etb.dst
            WHERE (
                nt.name LIKE 'SECURITY_TAINT_SOURCE%'
                OR nt.name LIKE 'SECURITY_INPUT_HANDLER%'
                OR nt.name LIKE 'SECURITY_%'
            )
            AND m.name NOT LIKE 'test_%'
            LIMIT ?;
        """

        try:
            results = self.cpg.execute_query(query, (limit,))
            logger.info(f"Found {len(results)} taint sources")
            return results
        except Exception as e:
            logger.error(f"Error finding taint sources: {e}")
            return []

    def find_taint_sinks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Find dangerous function calls (taint sinks)

        Returns:
            List of potential sink methods
        """
        query = """
            SELECT DISTINCT
                m.id,
                m.name AS method_name,
                m.full_name,
                m.filename,
                m.line_number,
                nc.name AS sink_function
            FROM nodes_method m
            JOIN nodes_call nc ON nc.containing_method_id = m.id
            WHERE nc.name IN (
                -- SQL execution
                'exec_simple_query', 'SPI_execute', 'SPI_exec',
                -- Command execution
                'system', 'popen', 'exec', 'execl', 'execv',
                -- File operations
                'fopen', 'open', 'write', 'fwrite',
                -- String operations
                'strcpy', 'strcat', 'sprintf'
            )
            AND m.name NOT LIKE 'test_%'
            LIMIT ?;
        """

        try:
            results = self.cpg.execute_query(query, (limit,))
            logger.info(f"Found {len(results)} taint sinks")
            return results
        except Exception as e:
            logger.error(f"Error finding taint sinks: {e}")
            return []

    def trace_taint_flows(
        self,
        source_method_id: Optional[int] = None,
        limit: int = 30
    ) -> List[DataFlowPath]:
        """
        Trace data flows from sources to sinks

        Args:
            source_method_id: Specific source to trace from (or None for all)
            limit: Max paths to return

        Returns:
            List of data flow paths
        """
        # Simplified taint flow analysis using call graph
        # In a full implementation, this would use proper dataflow analysis

        sources = self.find_taint_sources(limit)
        sinks = self.find_taint_sinks(limit)

        paths = []
        for idx, (source, sink) in enumerate(zip(sources[:limit//2], sinks[:limit//2])):
            path = DataFlowPath(
                path_id=f"FLOW_{idx:03d}",
                source_method=source.get('method_name', 'unknown'),
                source_file=source.get('filename', 'unknown'),
                source_line=source.get('line_number', 0),
                sink_method=sink.get('method_name', 'unknown'),
                sink_file=sink.get('filename', 'unknown'),
                sink_line=sink.get('line_number', 0),
                path_length=2,  # Simplified
                intermediate_nodes=[],
                taint_type=self._classify_taint_type(source),
                sanitized=self._check_sanitization(source, sink)
            )
            paths.append(path)

        logger.info(f"Traced {len(paths)} taint flow paths")
        return paths

    def _classify_taint_type(self, source: Dict[str, Any]) -> str:
        """Classify type of taint based on source"""
        tag = (source.get('tag') or '').lower()
        method_name = (source.get('method_name') or '').lower()

        if 'input' in tag or 'input' in method_name:
            return 'user_input'
        elif 'network' in tag or 'recv' in method_name:
            return 'network_data'
        elif 'file' in tag or 'read' in method_name:
            return 'file_data'
        else:
            return 'unknown'

    def _check_sanitization(
        self,
        source: Dict[str, Any],
        sink: Dict[str, Any]
    ) -> bool:
        """
        Check if there's likely sanitization between source and sink
        This is a simplified heuristic
        """
        # Check if source file has validation/sanitization code
        source_file = source.get('filename', '')
        sink_file = sink.get('filename', '')

        # If in different files, assume some validation (simplified)
        if source_file != sink_file:
            return True

        # Check method names for validation keywords
        source_method = (source.get('method_name') or '').lower()
        if any(kw in source_method for kw in ['validate', 'sanitize', 'check']):
            return True

        return False


# ============================================================================
# AGENT 3: VULNERABILITY REPORTER
# ============================================================================

class VulnerabilityReporter:
    """
    Generate structured vulnerability reports

    Responsibilities:
    - Aggregate findings from scanner and data flow analyzer
    - Calculate statistics and metrics
    - Generate executive summary
    - Prioritize recommendations
    """

    def generate_report(
        self,
        findings: List[SecurityFinding],
        data_flows: List[DataFlowPath],
        include_summary: bool = True
    ) -> VulnerabilityReport:
        """
        Generate comprehensive vulnerability report

        Args:
            findings: Security findings from scanner
            data_flows: Taint flow paths from analyzer
            include_summary: Whether to generate summary

        Returns:
            Structured vulnerability report
        """
        # Calculate statistics
        severity_counts = self._count_by_severity(findings)
        category_counts = self._count_by_category(findings)

        # Generate summary
        summary = ""
        if include_summary:
            summary = self._generate_summary(findings, data_flows, severity_counts)

        # Generate recommendations
        recommendations = self._generate_recommendations(findings, severity_counts)

        report = VulnerabilityReport(
            report_id=f"VULN_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            total_findings=len(findings),
            critical_count=severity_counts.get('critical', 0),
            high_count=severity_counts.get('high', 0),
            medium_count=severity_counts.get('medium', 0),
            low_count=severity_counts.get('low', 0),
            findings_by_category=category_counts,
            findings=findings,
            data_flows=data_flows,
            summary=summary,
            recommendations=recommendations
        )

        logger.info(f"Generated report {report.report_id} with {report.total_findings} findings")
        return report

    def _count_by_severity(self, findings: List[SecurityFinding]) -> Dict[str, int]:
        """Count findings by severity level"""
        counts = {}
        for finding in findings:
            counts[finding.severity] = counts.get(finding.severity, 0) + 1
        return counts

    def _count_by_category(self, findings: List[SecurityFinding]) -> Dict[str, int]:
        """Count findings by vulnerability category"""
        counts = {}
        for finding in findings:
            counts[finding.category] = counts.get(finding.category, 0) + 1
        return counts

    def _generate_summary(
        self,
        findings: List[SecurityFinding],
        data_flows: List[DataFlowPath],
        severity_counts: Dict[str, int]
    ) -> str:
        """Generate executive summary of findings"""
        critical = severity_counts.get('critical', 0)
        high = severity_counts.get('high', 0)
        total = len(findings)

        summary_parts = [
            f"Security analysis identified {total} potential vulnerabilities.",
        ]

        if critical > 0:
            summary_parts.append(
                f"⚠️ {critical} CRITICAL issues require immediate attention."
            )

        if high > 0:
            summary_parts.append(
                f"{high} HIGH severity issues should be addressed soon."
            )

        if data_flows:
            unsafe_flows = sum(1 for df in data_flows if not df.sanitized)
            if unsafe_flows > 0:
                summary_parts.append(
                    f"{unsafe_flows} unsanitized data flow paths detected."
                )

        return " ".join(summary_parts)

    def _generate_recommendations(
        self,
        findings: List[SecurityFinding],
        severity_counts: Dict[str, int]
    ) -> List[str]:
        """Generate prioritized recommendations"""
        recommendations = []

        # Priority 1: Critical issues
        if severity_counts.get('critical', 0) > 0:
            recommendations.append(
                "Immediately address all CRITICAL vulnerabilities, "
                "especially injection flaws and buffer overflows"
            )

        # Priority 2: High severity
        if severity_counts.get('high', 0) > 0:
            recommendations.append(
                "Schedule HIGH severity fixes in next sprint"
            )

        # Category-specific recommendations
        categories = set(f.category for f in findings)

        if 'injection' in categories:
            recommendations.append(
                "Implement input validation and parameterized queries for all SQL/command execution"
            )

        if 'buffer_overflow' in categories:
            recommendations.append(
                "Replace unsafe string functions (strcpy, sprintf) with safe alternatives (strncpy, snprintf)"
            )

        if 'memory_safety' in categories:
            recommendations.append(
                "Review memory management patterns and add NULL checks after allocations"
            )

        # General recommendations
        recommendations.append(
            "Enable compiler security flags (-fstack-protector, -D_FORTIFY_SOURCE)"
        )
        recommendations.append(
            "Add security-focused unit tests for identified vulnerable code"
        )

        return recommendations


# ============================================================================
# AGENT 4: REMEDIATION ADVISOR
# ============================================================================

class RemediationAdvisor:
    """
    Suggest fixes for identified vulnerabilities

    Responsibilities:
    - Provide remediation steps for each finding
    - Generate secure code examples
    - Estimate remediation effort
    - Prioritize fixes
    """

    def get_remediation_advice(self, finding: SecurityFinding) -> RemediationAdvice:
        """
        Get remediation advice for a specific finding

        Args:
            finding: Security finding to remediate

        Returns:
            Remediation advice with steps and examples
        """
        # Get pattern for detailed remediation info
        pattern = self._get_pattern_for_finding(finding)

        if not pattern:
            return self._generic_advice(finding)

        # Calculate priority (1-10, higher = more urgent)
        priority = self._calculate_priority(finding)

        # Estimate effort
        effort = self._estimate_effort(finding, pattern)

        advice = RemediationAdvice(
            finding_id=finding.finding_id,
            pattern_id=finding.pattern_id,
            remediation_steps=self._parse_remediation_steps(pattern.remediation),
            code_example=pattern.example_code,
            references=[f"CWE-{cwe}" for cwe in finding.cwe_ids],
            estimated_effort=effort,
            priority=priority
        )

        return advice

    def get_bulk_remediation_plan(
        self,
        findings: List[SecurityFinding]
    ) -> List[RemediationAdvice]:
        """
        Generate remediation plan for multiple findings

        Sorts by priority and groups by pattern
        """
        advice_list = []

        for finding in findings:
            advice = self.get_remediation_advice(finding)
            advice_list.append(advice)

        # Sort by priority (highest first)
        advice_list.sort(key=lambda a: a.priority, reverse=True)

        logger.info(f"Generated remediation plan for {len(advice_list)} findings")
        return advice_list

    def _get_pattern_for_finding(self, finding: SecurityFinding) -> Optional[SecurityPattern]:
        """Get security pattern associated with finding"""
        for pattern in SECURITY_PATTERNS.values():
            if pattern.id == finding.pattern_id:
                return pattern
        return None

    def _calculate_priority(self, finding: SecurityFinding) -> int:
        """Calculate remediation priority (1-10, higher = more urgent)"""
        severity_scores = {
            'critical': 10,
            'high': 7,
            'medium': 4,
            'low': 2,
            'info': 1
        }

        base_priority = severity_scores.get(finding.severity, 5)

        # Adjust based on confidence
        adjusted = int(base_priority * finding.confidence)

        # Boost injection vulnerabilities
        if finding.category == 'injection':
            adjusted = min(adjusted + 2, 10)

        return max(1, min(adjusted, 10))

    def _estimate_effort(self, finding: SecurityFinding, pattern: SecurityPattern) -> str:
        """Estimate remediation effort"""
        # Simple heuristic based on category
        if finding.category in ['injection', 'buffer_overflow']:
            return 'medium'  # Usually requires code refactoring
        elif finding.category == 'memory_safety':
            return 'high'  # May require architectural changes
        elif finding.category == 'input_validation':
            return 'low'  # Usually just add validation
        else:
            return 'medium'

    def _parse_remediation_steps(self, remediation_text: str) -> List[str]:
        """Parse remediation text into discrete steps"""
        # Split on numbered lines
        steps = []
        for line in remediation_text.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                # Remove numbering/bullets
                clean = line.lstrip('0123456789.-) ')
                if clean:
                    steps.append(clean)
        return steps

    def _generic_advice(self, finding: SecurityFinding) -> RemediationAdvice:
        """Generate generic advice when pattern not found"""
        return RemediationAdvice(
            finding_id=finding.finding_id,
            pattern_id=finding.pattern_id,
            remediation_steps=[
                "Review the vulnerable code carefully",
                "Consult security guidelines for this vulnerability type",
                "Test fix thoroughly before deployment"
            ],
            code_example="# Consult security documentation for specific examples",
            references=[f"CWE-{cwe}" for cwe in finding.cwe_ids],
            estimated_effort="medium",
            priority=self._calculate_priority(finding)
        )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def run_complete_security_audit(
    limit_per_pattern: int = 50
) -> Tuple[VulnerabilityReport, List[RemediationAdvice]]:
    """
    Run complete security audit using all agents

    Returns:
        (VulnerabilityReport, List[RemediationAdvice])
    """
    logger.info("Starting complete security audit")

    with CPGQueryService() as cpg:
        # Agent 1: Scan for vulnerabilities
        scanner = SecurityScanner(cpg)
        findings = scanner.scan_all_patterns(limit_per_pattern)

        # Agent 2: Analyze data flows
        analyzer = DataFlowAnalyzer(cpg)
        data_flows = analyzer.trace_taint_flows(limit=30)

        # Agent 3: Generate report
        reporter = VulnerabilityReporter()
        report = reporter.generate_report(findings, data_flows)

        # Agent 4: Generate remediation plan
        advisor = RemediationAdvisor()
        remediation_plan = advisor.get_bulk_remediation_plan(findings[:20])  # Top 20

    logger.info("Complete security audit finished")
    return report, remediation_plan


if __name__ == "__main__":
    # Test the agents
    print("Testing Security Agents...")
    print("=" * 60)

    try:
        report, remediation = run_complete_security_audit(limit_per_pattern=10)

        print(f"\n📊 Vulnerability Report: {report.report_id}")
        print(f"Total Findings: {report.total_findings}")
        print(f"  Critical: {report.critical_count}")
        print(f"  High: {report.high_count}")
        print(f"  Medium: {report.medium_count}")
        print(f"  Low: {report.low_count}")

        print(f"\n🔍 Data Flows: {len(report.data_flows)}")

        print(f"\n💡 Remediation Plan: {len(remediation)} items")
        if remediation:
            top = remediation[0]
            print(f"  Top Priority: {top.finding_id} (priority {top.priority})")

        print(f"\n📝 Summary:\n{report.summary}")

        print(f"\n✅ Recommendations:")
        for idx, rec in enumerate(report.recommendations[:3], 1):
            print(f"  {idx}. {rec}")

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
