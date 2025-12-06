"""
Scenario 8: Regulatory Compliance Checking with Graph Analysis (Week 13 + Graph Methods)
"""

import logging
from typing import Dict, List, Any, Optional

from src.services.cpg_query_service import CPGQueryService
from src.llm.llm_interface_compat import LLMInterface
from src.workflow.state import MultiScenarioState

logger = logging.getLogger(__name__)

def compliance_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    Scenario 8: Regulatory Compliance Checking with Graph Analysis (Week 13 + Graph Methods)

    Automated compliance validation by:
    1. Scanning for license compliance issues (LicenseDetector)
    2. Checking GDPR/HIPAA privacy compliance (ComplianceValidator)
    3. Validating security compliance (OWASP, CWE)
    4. Enforcing coding standards (StandardsChecker)
    5. CallGraphAnalyzer - Graph Method #2: Impact analysis for compliance violations
    6. Generating comprehensive compliance report with LLM

    Returns compliance report with violation impact analysis and remediation priorities.
    """
    logger.info("Executing regulatory compliance checking workflow with GRAPH METHODS")

    # Track graph insights
    graph_insights = {
        'violation_impact': {},
        'high_impact_violations': [],
        'critical_methods': []
    }

    try:
        with CPGQueryService() as cpg:
            all_violations = []

            # Agent 1: License Detector
            logger.info("Running license compliance checks...")
            license_detector = LicenseDetector()

            # Get source files from query or scan all
            source_files_query = """
            SELECT DISTINCT filename
            FROM nodes_file
            WHERE filename LIKE '%.py' OR filename LIKE '%.c' OR filename LIKE '%.java'
            LIMIT 50
            """
            file_results = cpg.execute_custom_sql(source_files_query)
            source_files = [row.get('filename', '') for row in file_results if row.get('filename')]

            # Scan for license violations
            license_violations = license_detector.scan_file_licenses(source_files)
            all_violations.extend(license_violations)

            # Check for license conflicts (if licenses detected)
            detected_licenses = []
            for filepath in source_files[:10]:  # Sample
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        header = ''.join(f.readlines()[:50])
                    license_type = license_detector.extract_license_from_text(header)
                    if license_type:
                        detected_licenses.append(license_type)
                except:
                    continue

            if detected_licenses:
                conflict_violations = license_detector.detect_license_conflicts(detected_licenses)
                all_violations.extend(conflict_violations)

            # Agent 2: Compliance Validator
            logger.info("Running privacy and security compliance checks...")
            compliance_validator = ComplianceValidator(cpg)

            # Check privacy compliance (GDPR/HIPAA)
            privacy_violations = compliance_validator.check_privacy_compliance()
            all_violations.extend(privacy_violations)

            # Check security compliance (OWASP, CWE)
            security_violations = compliance_validator.check_security_compliance()
            all_violations.extend(security_violations)

            # Check hardcoded secrets in sample files
            for filepath in source_files[:20]:
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    secret_violations = compliance_validator.check_hardcoded_secrets(content, filepath)
                    all_violations.extend(secret_violations)
                except:
                    continue

            # Agent 3: Standards Checker
            logger.info("Running coding standards checks...")
            standards_checker = StandardsChecker(cpg)

            # Check documentation
            doc_violations = standards_checker.check_documentation()
            all_violations.extend(doc_violations)

            # Check complexity
            complexity_violations = standards_checker.check_complexity()
            all_violations.extend(complexity_violations)

            # Generate compliance report
            compliance_report = standards_checker.generate_compliance_report(all_violations)

            logger.info(f"Found {len(all_violations)} compliance violations")
            logger.info(f"Compliance score: {compliance_report.compliance_score:.1f}/100")
            logger.info(f"Critical: {compliance_report.critical_count}, High: {compliance_report.high_count}")

            # GRAPH METHOD #2: CallGraphAnalyzer - Analyze impact of compliance violations
            try:
                logger.info("Running CallGraphAnalyzer for compliance violation impact...")
                from src.analysis import CallGraphAnalyzer
                call_analyzer = CallGraphAnalyzer(cpg)

                # Analyze impact for critical/high severity violations with method context
                critical_high_violations = [
                    v for v in all_violations
                    if v.rule.severity.value in ['critical', 'high'] and hasattr(v, 'method_name') and v.method_name
                ]

                for violation in critical_high_violations[:15]:  # Top 15 critical/high violations
                    method_name = violation.method_name

                    # Find who calls this non-compliant method
                    callers = call_analyzer.find_all_callers(method_name, max_depth=3)
                    direct_callers = [c for c in callers if c.get('depth', 1) == 1]

                    # Find what this method calls
                    callees = call_analyzer.find_all_callees(method_name, max_depth=2)

                    # Compute impact score
                    impact = call_analyzer.analyze_impact(method_name)

                    # Calculate compliance fix impact
                    blast_radius = len(callers) + len(callees)
                    fix_risk = 'high' if blast_radius > 20 else 'medium' if blast_radius > 10 else 'low'

                    graph_insights['violation_impact'][method_name] = {
                        'violation_type': violation.rule.category.value,
                        'severity': violation.rule.severity.value,
                        'callers': len(callers),
                        'direct_callers': len(direct_callers),
                        'callees': len(callees),
                        'impact_score': impact.impact_score if impact else 0.0,
                        'blast_radius': blast_radius,
                        'fix_risk': fix_risk,
                        'is_critical_method': impact.is_entry_point if impact else False
                    }

                    # Track high-impact violations
                    if impact and impact.impact_score > 0.7:
                        graph_insights['high_impact_violations'].append({
                            'method': method_name,
                            'violation': violation.rule.name,
                            'severity': violation.rule.severity.value,
                            'impact_score': impact.impact_score,
                            'blast_radius': blast_radius
                        })

                    # Track critical methods (entry points with violations)
                    if impact and impact.is_entry_point:
                        graph_insights['critical_methods'].append({
                            'method': method_name,
                            'violation': violation.rule.name,
                            'reason': 'Entry point with compliance violation'
                        })

                logger.info(f"CallGraphAnalyzer: Analyzed {len(graph_insights['violation_impact'])} violations, "
                           f"found {len(graph_insights['high_impact_violations'])} high-impact violations")

            except Exception as e:
                logger.error(f"CallGraphAnalyzer failed: {e}", exc_info=True)
                # Continue without graph insights

            # Build enhanced LLM prompt with compliance data
            user_query = state.get('question', 'Perform compliance analysis')

            llm_prompt = f"""**Regulatory Compliance Analysis**

**User Question:** {user_query}

**Compliance Report:**
- **Compliance Score:** {compliance_report.compliance_score:.1f}/100
- **Status:** {"✅ PASSED" if compliance_report.passed else "❌ FAILED"}
- **Total Violations:** {len(all_violations)}
- **Critical Violations:** {compliance_report.critical_count}
- **High Severity Violations:** {compliance_report.high_count}

**Violations by Category:**
"""

            for category, violations in compliance_report.violations_by_category.items():
                llm_prompt += f"\n### {category.upper()} ({len(violations)} violations)\n"
                for violation in violations[:5]:  # Top 5 per category
                    llm_prompt += f"- **[{violation.rule.severity.value.upper()}]** {violation.description}\n"
                    llm_prompt += f"  - File: {violation.filepath}:{violation.line_number}\n"
                    llm_prompt += f"  - Fix: {violation.remediation_steps}\n"

            llm_prompt += f"""

**Compliance Recommendations:**
"""
            for rec in compliance_report.recommendations:
                llm_prompt += f"- {rec}\n"

            # Add graph insights to LLM prompt
            if graph_insights['violation_impact']:
                llm_prompt += f"\n\n💥 VIOLATION IMPACT ANALYSIS (Graph Analysis):\n"
                llm_prompt += f"- Total violations analyzed: {len(graph_insights['violation_impact'])}\n"
                llm_prompt += f"- High-impact violations (>0.7): {len(graph_insights['high_impact_violations'])}\n"
                llm_prompt += f"- Critical methods with violations: {len(graph_insights['critical_methods'])}\n\n"

                # High-impact violations
                if graph_insights['high_impact_violations']:
                    llm_prompt += "**High-Impact Violations (Prioritize These):**\n"
                    for hiv in graph_insights['high_impact_violations'][:5]:
                        llm_prompt += f"  - {hiv['method']}: {hiv['violation']} ({hiv['severity'].upper()})\n"
                        llm_prompt += f"    Impact: {hiv['impact_score']:.2f}, Blast radius: {hiv['blast_radius']} methods\n"

                # Critical methods (entry points with violations)
                if graph_insights['critical_methods']:
                    llm_prompt += "\n**⚠️ CRITICAL: Entry Points with Compliance Violations:**\n"
                    for cm in graph_insights['critical_methods'][:5]:
                        llm_prompt += f"  - {cm['method']}: {cm['violation']} - {cm['reason']}\n"

                # Remediation impact
                llm_prompt += "\n**Remediation Impact Analysis:**\n"
                for method, impact in list(graph_insights['violation_impact'].items())[:5]:
                    llm_prompt += f"  - {method}: {impact['blast_radius']} methods affected "
                    llm_prompt += f"({impact['callers']} callers, {impact['callees']} callees) - {impact['fix_risk'].upper()} risk\n"

            llm_prompt += f"""

**Detailed Analysis:**
Based on the compliance violations found, provide:
1. A summary of the most critical compliance issues
2. Regulatory implications (GDPR, HIPAA, OWASP, licensing risks)
3. Prioritized remediation plan
4. Best practices to prevent future violations

Use the violation data above to provide specific, actionable guidance.
"""

            # Generate LLM analysis
            llm = LLMInterface()
            llm_analysis = llm.generate("You are an AI assistant.", llm_prompt)

            # Store results in state
            state['answer'] = llm_analysis
            state['compliance_report'] = {
                'report_id': compliance_report.report_id,
                'timestamp': compliance_report.timestamp,
                'compliance_score': compliance_report.compliance_score,
                'passed': compliance_report.passed,
                'total_violations': len(all_violations),
                'critical_count': compliance_report.critical_count,
                'high_count': compliance_report.high_count,
                'violations_by_category': {
                    cat: len(viols) for cat, viols in compliance_report.violations_by_category.items()
                },
                'recommendations': compliance_report.recommendations,
                'top_violations': [
                    {
                        'rule': v.rule.name,
                        'severity': v.rule.severity.value,
                        'category': v.rule.category.value,
                        'filepath': v.filepath,
                        'line': v.line_number,
                        'description': v.description,
                    }
                    for v in all_violations[:20]
                ],
                'enhanced_mode': True,
                'graph_methods_enabled': True,
                'graph_insights': {
                    'violations_analyzed': len(graph_insights['violation_impact']),
                    'high_impact_violations': len(graph_insights['high_impact_violations']),
                    'critical_methods': len(graph_insights['critical_methods']),
                    'total_blast_radius': sum([v['blast_radius'] for v in graph_insights['violation_impact'].values()]),
                    'avg_blast_radius': round(
                        sum([v['blast_radius'] for v in graph_insights['violation_impact'].values()]) / len(graph_insights['violation_impact'])
                        if graph_insights['violation_impact'] else 0, 1
                    ),
                    'high_risk_fixes': len([v for v in graph_insights['violation_impact'].values() if v['fix_risk'] == 'high'])
                }
            }

    except Exception as e:
        logger.error(f"Enhanced compliance workflow failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        state['error'] = str(e)
        state['answer'] = f"Error during compliance checking: {e}"

    return state




__all__ = ['compliance_workflow']
