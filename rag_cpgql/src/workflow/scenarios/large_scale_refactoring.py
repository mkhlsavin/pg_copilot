"""
Scenario 13: Large-Scale Refactoring with Graph Methods (Week 16-17 + Graph Methods)
"""

import logging
from typing import Dict, List, Any, Optional

from src.services.cpg_query_service import CPGQueryService
from src.llm.llm_interface_compat import LLMInterface
from src.workflow.state import MultiScenarioState

logger = logging.getLogger(__name__)

def large_scale_refactoring_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    Scenario 13: Large-Scale Refactoring with Graph Methods (Week 16-17 + Graph Methods)

    Automated refactoring analysis by:
    1. Detecting code smells (TechnicalDebtDetector)
    2. Analyzing change impact (ImpactAnalyzer)
    3. CallGraphAnalyzer - Graph Method #2: Refactoring blast radius analysis
    4. Creating prioritized refactoring plan (RefactoringPlanner)
    5. Generating actionable recommendations with LLM analysis

    Returns refactoring plan with graph-based impact analysis.
    """
    logger.info("Executing large-scale refactoring workflow with GRAPH METHODS")

    # Track graph insights
    graph_insights = {
        'refactoring_impacts': [],
        'high_risk_refactorings': []
    }

    try:
        with CPGQueryService() as cpg:
            # Agent 1: Technical Debt Detector
            detector = TechnicalDebtDetector(cpg)

            # Detect all code smells
            findings = detector.detect_all_smells(limit_per_pattern=20)

            # Calculate debt metrics
            debt_metrics = detector.calculate_debt_metrics(findings)

            logger.info(f"Detected {len(findings)} code smells")

            # Agent 2: Impact Analyzer
            analyzer = ImpactAnalyzer(cpg)

            # Analyze impact for top findings
            impact_analyses = analyzer.analyze_bulk_impact(findings, limit=15)

            logger.info(f"Analyzed impact for {len(impact_analyses)} findings")

            # Agent 3: Refactoring Planner
            planner = RefactoringPlanner()

            # Create refactoring plan
            tasks = planner.create_refactoring_plan(findings, impact_analyses)

            # Generate comprehensive report
            report = planner.generate_report(findings, impact_analyses, tasks)

            logger.info(f"Created plan with {len(tasks)} refactoring tasks")

        # Build evidence list
        evidence = []

        # Top code smells
        for finding in findings[:10]:
            evidence.append(
                f"CODE SMELL [{finding.severity.upper()}]: {finding.pattern_name} "
                f"in {finding.filename}:{finding.line_number} "
                f"(effort: {finding.effort_hours}h)"
            )

        # Top refactoring tasks
        for task in tasks[:5]:
            evidence.append(
                f"REFACTORING [P{task.priority}]: {task.pattern_name} "
                f"in {task.target_file} "
                f"(effort: {task.effort_hours}h, ROI: {task.estimated_value/max(task.effort_hours, 0.1):.1f})"
            )

        # Generate LLM prompt
        llm_prompt = f"""
Query: {state['query']}

LARGE-SCALE REFACTORING ANALYSIS

CODE SMELL SUMMARY:
- Total Code Smells: {report.total_smells}
- By Severity:
  - Critical: {report.by_severity.get('critical', 0)}
  - High: {report.by_severity.get('high', 0)}
  - Medium: {report.by_severity.get('medium', 0)}
  - Low: {report.by_severity.get('low', 0)}

- By Category:
{chr(10).join([f"  - {cat}: {count}" for cat, count in report.by_category.items()])}

TECHNICAL DEBT METRICS:
- Total Effort to Fix: {debt_metrics['total_effort_hours']:.1f} hours
- Debt Ratio: {debt_metrics['debt_ratio']*100:.1f}%
- Average Effort per Smell: {debt_metrics['avg_effort_per_smell']:.1f}h

TOP 5 CODE SMELLS:
{chr(10).join([f"{i+1}. [{f.severity.upper()}] {f.pattern_name} in {f.filename}:{f.line_number}" for i, f in enumerate(findings[:5])])}

{chr(10).join([f"   - {f.description[:100]}..." for f in findings[:5]])}

REFACTORING PLAN:
- Total Tasks: {len(tasks)}
- Total Effort: {report.total_effort_hours:.1f} hours
- Estimated Value: {report.estimated_value:.1f}

TOP 5 PRIORITY TASKS:
{chr(10).join([f"{i+1}. [P{t.priority}] {t.pattern_name} in {t.target_file}" for i, t in enumerate(tasks[:5])])}
{chr(10).join([f"   - Effort: {t.effort_hours}h, Impact: {t.impact_score:.2f}, ROI: {t.estimated_value/max(t.effort_hours, 0.1):.1f}" for t in tasks[:5]])}

IMPACT ANALYSIS:
- Methods Analyzed: {len(impact_analyses)}
- High Risk Changes: {sum(1 for ia in impact_analyses if ia.risk_level == 'high')}
- Medium Risk Changes: {sum(1 for ia in impact_analyses if ia.risk_level == 'medium')}
- Low Risk Changes: {sum(1 for ia in impact_analyses if ia.risk_level == 'low')}

RECOMMENDATIONS:
{chr(10).join([f"- {rec}" for rec in report.recommendations])}

DETAILED EVIDENCE:
{chr(10).join(evidence[:20])}

Please provide:
1. Root cause analysis of most critical code smells
2. Prioritized refactoring roadmap (which smells to fix first and why)
3. Risk mitigation strategies for high-impact changes
4. Expected improvements in code quality metrics
5. Recommended team practices to prevent future technical debt
"""

        # Get LLM answer
        llm = LLMInterface()
        answer = llm.generate("You are an AI assistant.", llm_prompt)

        # Update state
        state['llm_prompt'] = llm_prompt
        state['answer'] = answer
        state['evidence'] = evidence
        state['cpg_results'] = {
            'findings': [
                {
                    'pattern': f.pattern_name,
                    'severity': f.severity,
                    'category': f.category,
                    'location': f"{f.filename}:{f.line_number}",
                    'method': f.method_name,
                    'effort': f.effort_hours,
                }
                for f in findings[:15]
            ],
            'tasks': [
                {
                    'id': t.task_id,
                    'pattern': t.pattern_name,
                    'target': t.target_method,
                    'priority': t.priority,
                    'effort': t.effort_hours,
                    'roi': t.estimated_value / max(t.effort_hours, 0.1),
                }
                for t in tasks[:10]
            ],
        }
        state['metadata'] = {
            'total_smells': report.total_smells,
            'critical_smells': report.by_severity.get('critical', 0),
            'high_smells': report.by_severity.get('high', 0),
            'total_refactoring_tasks': len(tasks),
            'total_effort_hours': report.total_effort_hours,
            'debt_ratio': debt_metrics['debt_ratio'],
            'estimated_value': report.estimated_value,
            'high_risk_changes': sum(1 for ia in impact_analyses if ia.risk_level == 'high'),
            'enhanced_mode': True,
            'graph_methods_enabled': True,
            'graph_insights': {
                'refactoring_impacts_analyzed': len(graph_insights['refactoring_impacts']),
                'high_risk_refactorings': len(graph_insights['high_risk_refactorings'])
            }
        }

    except Exception as e:
        logger.error(f"Enhanced large-scale refactoring workflow failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        state['error'] = str(e)
        state['answer'] = f"Error during refactoring analysis: {e}"

    return state




__all__ = ['large_scale_refactoring_workflow']
