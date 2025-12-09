"""
Scenario 9: Enhanced Code Review Automation with Graph Analysis (Week 12 + Graph Methods)
"""

import logging
from typing import Dict, List, Any, Optional

from src.workflow.scenarios._language_utils import add_language_instruction
from src.services.cpg_query_service import CPGQueryService
from src.llm.llm_interface_compat import LLMInterface
from src.workflow.state import MultiScenarioState

from src.prompts.prompt_registry import get_global_registry
from src.code_review.review_agents import PRAnalyzer, ContextAggregator, ReviewReporter

logger = logging.getLogger(__name__)

def code_review_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    Scenario 9: Enhanced Code Review Automation with Graph Analysis (Week 12 + Graph Methods)

    Uses specialized code review agents + graph methods for comprehensive PR analysis:
    1. PRAnalyzer - Parse PR diffs and extract changes
    2. ContextAggregator - Gather CPG context for changes
    3. CallGraphAnalyzer - Graph Method #2: Impact analysis for code changes
    4. ReviewReporter - Generate review comments and recommendations

    Integrates with:
    - Security analysis (Scenario 5)
    - Performance analysis (Scenario 6)
    - Architecture violations (Scenario 11)
    - Technical debt (Scenario 12)

    Returns detailed code review with findings, score, impact analysis, and recommended action.
    """
    logger.info("Executing ENHANCED code review automation workflow with GRAPH METHODS")

    # Track graph insights
    graph_insights = {
        'change_impact': {},
        'affected_methods': [],
        'risk_assessment': {}
    }

    try:
        # Extract PR diff from query (if provided)
        # For demo, we'll simulate with recent changes from CPG
        diff_text = state.get('pr_diff', '')
        pr_metadata = state.get('pr_metadata', {
            'title': 'Code changes for review',
            'author': 'developer',
            'number': 123
        })

        with CPGQueryService() as cpg:
            # AGENT 1: PRAnalyzer - Parse diff and extract changes
            logger.info("Running PRAnalyzer...")
            pr_analyzer = PRAnalyzer()

            # If no diff provided, simulate from recent changes
            if not diff_text:
                # Get recent changes as proxy for PR
                recent_changes = cpg.execute_custom_sql("""
                    SELECT
                        m.name,
                        m.filename,
                        m.line_number,
                        m.line_number_end
                    FROM nodes_method m
                    ORDER BY m.id DESC
                    LIMIT 20
                """)

                # Create simple simulated diff
                diff_text = self._simulate_diff_from_changes(recent_changes)

            pr_data = pr_analyzer.parse_pr_diff(diff_text, pr_metadata)
            changed_methods = pr_analyzer.extract_changed_methods(pr_data)
            affected_subsystems = pr_analyzer.identify_affected_subsystems(pr_data['changed_files'])
            logger.info(f"PRAnalyzer: {pr_data['files_changed']} files, {len(changed_methods)} methods changed")

            # Link changed methods to CPG (find method IDs)
            for method in changed_methods:
                result = cpg.execute_custom_sql(f"""
                    SELECT id FROM nodes_method
                    WHERE name = '{method.method_name}'
                      AND filename LIKE '%{method.filepath.split('/')[-1]}'
                    LIMIT 1
                """)
                if result:
                    method.method_id = result[0]['id']

            # AGENT 2: ContextAggregator - Gather CPG context
            logger.info("Running ContextAggregator...")
            aggregator = ContextAggregator(cpg)

            method_contexts = []
            for method in changed_methods:
                if method.method_id:
                    context = aggregator.gather_method_context(method.method_id)
                    if context:
                        method_contexts.append(context)

            test_coverage = aggregator.check_test_coverage(changed_methods)
            impacted_methods = aggregator.find_impacted_methods(changed_methods)
            logger.info(f"ContextAggregator: {len(method_contexts)} contexts, {test_coverage['coverage_percent']:.1f}% coverage")

            # GRAPH METHOD #2: CallGraphAnalyzer - Impact analysis for PR changes
            try:
                logger.info("Running CallGraphAnalyzer for PR change impact...")
                from src.analysis import CallGraphAnalyzer
                call_analyzer = CallGraphAnalyzer(cpg)

                # For each changed method, analyze impact
                for method in changed_methods:
                    method_name = method.method_name
                    if not method_name:
                        continue

                    # Get callers (who will be affected by this change?)
                    callers = call_analyzer.find_all_callers(method_name, max_depth=3)
                    # Handle mixed return types: callers can be list of dicts or list of strings
                    if callers and isinstance(callers[0], dict):
                        direct_callers = [c for c in callers if c.get('depth', 1) == 1]
                    else:
                        # If callers are strings, treat all as direct callers
                        direct_callers = callers if callers else []

                    # Get callees (what does this changed method depend on?)
                    callees = call_analyzer.find_all_callees(method_name, max_depth=2)

                    # Compute impact score
                    impact = call_analyzer.analyze_impact(method_name)

                    # Calculate change risk
                    blast_radius = len(callers) + len(callees)
                    change_risk = 'high' if blast_radius > 20 else 'medium' if blast_radius > 10 else 'low'

                    graph_insights['change_impact'][method_name] = {
                        'callers': len(callers),
                        'direct_callers': len(direct_callers),
                        'callees': len(callees),
                        'impact_score': impact.impact_score if impact else 0.0,
                        'blast_radius': blast_radius,
                        'change_risk': change_risk,
                        'is_entry_point': impact.is_entry_point if impact else False
                    }

                    # Track affected methods for review
                    # Handle mixed types: callers can be dicts or strings
                    for c in callers[:10]:
                        if isinstance(c, dict):
                            graph_insights['affected_methods'].append(c.get('caller_name', 'unknown'))
                        else:
                            graph_insights['affected_methods'].append(str(c))

                # Calculate overall PR risk
                total_blast_radius = sum([ci['blast_radius'] for ci in graph_insights['change_impact'].values()])
                high_risk_changes = len([ci for ci in graph_insights['change_impact'].values() if ci['change_risk'] == 'high'])

                graph_insights['risk_assessment'] = {
                    'total_blast_radius': total_blast_radius,
                    'avg_blast_radius': total_blast_radius / len(graph_insights['change_impact']) if graph_insights['change_impact'] else 0,
                    'high_risk_changes': high_risk_changes,
                    'overall_risk': 'high' if high_risk_changes > 2 else 'medium' if high_risk_changes > 0 else 'low'
                }

                logger.info(f"CallGraphAnalyzer: Total blast radius {total_blast_radius}, {high_risk_changes} high-risk changes")

            except Exception as e:
                logger.error(f"CallGraphAnalyzer failed: {e}", exc_info=True)
                # Continue without graph insights

            # AGENT 3: ReviewReporter - Generate review
            logger.info("Running ReviewReporter...")
            reporter = ReviewReporter()

            findings = reporter.analyze_changes(pr_data, method_contexts, test_coverage)
            report = reporter.generate_review_report(pr_data, findings, method_contexts)
            logger.info(f"ReviewReporter: {len(findings)} findings, score: {report.review_score:.1f}, action: {report.review_action.value}")

        # Build evidence list with graph insights
        evidence = [
            f"Files changed: {report.files_changed}",
            f"Methods changed: {report.methods_changed}",
            f"Findings: {len(report.findings)}",
            f"Review score: {report.review_score:.1f}/100",
            f"Test coverage: {test_coverage['coverage_percent']:.1f}%",
            f"Affected subsystems: {', '.join(affected_subsystems)}",
            f"Impacted methods: {len(impacted_methods)}",
            f"Total blast radius: {graph_insights['risk_assessment'].get('total_blast_radius', 0)}",
            f"High-risk changes: {graph_insights['risk_assessment'].get('high_risk_changes', 0)}",
            f"Overall risk: {graph_insights['risk_assessment'].get('overall_risk', 'unknown')}"
        ]

        # Generate enhanced LLM prompt
        llm = LLMInterface()

        # Build findings summary
        critical_findings = [f for f in findings if f.severity.value == 'critical']
        high_findings = [f for f in findings if f.severity.value == 'high']
        medium_findings = [f for f in findings if f.severity.value == 'medium']

        findings_detail = "\n".join([
            f"- [{f.severity.value.upper()}] {f.title}: {f.description}"
            for f in (critical_findings + high_findings)[:10]
        ])

        # Build context summary
        high_complexity = [c for c in method_contexts if c.complexity > 15]
        untested = test_coverage['untested_methods']
        security_concerns = [c for c in method_contexts if c.security_tags]

        # Build graph insights summaries
        change_impact_summary = ""
        if graph_insights['change_impact']:
            change_impact_summary = "\n💥 CHANGE IMPACT (Graph Analysis):\n"
            for method, impact in list(graph_insights['change_impact'].items())[:5]:
                change_impact_summary += f"  - {method}: {impact['blast_radius']} methods affected "
                change_impact_summary += f"({impact['callers']} callers, {impact['callees']} callees) - {impact['change_risk'].upper()} RISK\n"

        risk_assessment_summary = ""
        if graph_insights['risk_assessment']:
            risk_assessment_summary = f"\n⚠️ OVERALL PR RISK ASSESSMENT:\n"
            risk_assessment_summary += f"  - Total blast radius: {graph_insights['risk_assessment']['total_blast_radius']} methods\n"
            risk_assessment_summary += f"  - Avg per change: {graph_insights['risk_assessment']['avg_blast_radius']:.1f} methods\n"
            risk_assessment_summary += f"  - High-risk changes: {graph_insights['risk_assessment']['high_risk_changes']}\n"
            risk_assessment_summary += f"  - Overall risk: {graph_insights['risk_assessment']['overall_risk'].upper()}\n"

        # Get agent prompt from registry
        registry = get_global_registry()
        
        # Prepare variables for prompt template
        prompt_vars = {
            'domain': 'PostgreSQL',  # Can be made configurable
            'query': state['query'],
            'files_changed': report.files_changed,
            'additions': pr_data['total_additions'],
            'deletions': pr_data['total_deletions'],
            'methods_changed': report.methods_changed,
            'file_list': ', '.join(affected_subsystems),
            'code_context': f"""
PR SUMMARY:
- Files Changed: {report.files_changed}
- Lines: +{pr_data['total_additions']}/-{pr_data['total_deletions']}
- Methods Changed: {report.methods_changed}
- Affected Subsystems: {', '.join(affected_subsystems)}

REVIEW FINDINGS:
- Total Findings: {len(findings)}
- Critical: {len(critical_findings)}
- High: {len(high_findings)}
- Medium: {len(medium_findings)}

CRITICAL & HIGH SEVERITY ISSUES:
{findings_detail if findings_detail else 'None found'}

TEST COVERAGE:
- Coverage: {test_coverage['coverage_percent']:.1f}%
- Tested Methods: {test_coverage['tested_methods']}/{test_coverage['total_methods']}
- Untested Methods: {', '.join(untested[:5])}

CODE QUALITY:
- High Complexity Methods: {len(high_complexity)}
{chr(10).join([f'  - {c.method_name}: complexity {c.complexity}' for c in high_complexity[:3]])}

SECURITY:
- Methods with Security Tags: {len(security_concerns)}
{chr(10).join([f'  - {c.method_name}: {chr(44).join(c.security_tags)}' for c in security_concerns[:3]])}

IMPACT ANALYSIS:
- Impacted Methods: {len(impacted_methods)}
{chr(10).join([f'  - {imp["impacted_method"]} ({imp["reason"]})' for imp in impacted_methods[:5]])}
{change_impact_summary}
{risk_assessment_summary}

EXECUTIVE SUMMARY:
{report.summary}

RECOMMENDATIONS:
{chr(10).join([f'{i+1}. {rec}' for i, rec in enumerate(report.recommendations)])}

REVIEW SCORE: {report.review_score:.1f}/100
RECOMMENDED ACTION: {report.review_action.value.upper()}
""",
            'call_graph_impact': change_impact_summary + risk_assessment_summary,
            'security_findings': chr(10).join([f'  - {c.method_name}: {chr(44).join(c.security_tags)}' for c in security_concerns[:3]]) if security_concerns else 'None',
            'complexity_metrics': chr(10).join([f'  - {c.method_name}: complexity {c.complexity}' for c in high_complexity[:3]]) if high_complexity else 'None'
        }
        
        # Get prompts from registry with variable substitution
        prompts = registry.get_agent_prompt('code_reviewer', **prompt_vars)
        
        # Build final review prompt combining system context and user request
        review_prompt = f"""{prompts['system']}

{prompts['user']}

Based on this comprehensive automated review, provide:
1. Assessment of the changes and overall code quality
2. Explanation of critical/high findings and why they matter
3. Specific guidance for the developer on what to fix
4. Additional recommendations beyond automated checks
5. Final verdict (approve, request changes, or comment only)

Format as a professional code review comment.
"""

        answer = llm.generate(add_language_instruction(prompts['system'], state), review_prompt)

        # Update state
        state['cpg_results'] = [f.__dict__ for f in findings]
        state['methods'] = [c.__dict__ for c in method_contexts[:20]]
        state['answer'] = answer
        state['evidence'] = evidence
        state['metadata'] = {
            'report_id': report.report_id,
            'pr_info': pr_metadata,
            'files_changed': report.files_changed,
            'methods_changed': report.methods_changed,
            'findings_count': len(findings),
            'critical_count': len(critical_findings),
            'high_count': len(high_findings),
            'medium_count': len(medium_findings),
            'review_score': report.review_score,
            'review_action': report.review_action.value,
            'test_coverage_percent': test_coverage['coverage_percent'],
            'untested_methods': untested[:10],
            'impacted_methods_count': len(impacted_methods),
            'affected_subsystems': affected_subsystems,
            'enhanced_mode': True,
            'graph_methods_enabled': True,
            'graph_insights': {
                'changes_analyzed': len(graph_insights['change_impact']),
                'total_blast_radius': graph_insights['risk_assessment'].get('total_blast_radius', 0),
                'avg_blast_radius': round(graph_insights['risk_assessment'].get('avg_blast_radius', 0), 1),
                'high_risk_changes': graph_insights['risk_assessment'].get('high_risk_changes', 0),
                'overall_risk': graph_insights['risk_assessment'].get('overall_risk', 'unknown'),
                'affected_methods_count': len(set(graph_insights['affected_methods']))
            }
        }

    except Exception as e:
        logger.error(f"Enhanced code review workflow failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        state['error'] = str(e)
        state['answer'] = f"Error during enhanced code review: {e}"

    return state




__all__ = ['code_review_workflow']
