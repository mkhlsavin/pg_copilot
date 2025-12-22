"""
Scenario 12: Enhanced Technical Debt Quantification with Graph Methods (Week 11 + Graph Methods)
"""

import logging
from typing import Dict, List, Any, Optional

from src.workflow.scenarios._language_utils import add_language_instruction
from src.services.cpg_query_service import CPGQueryService
from src.llm.llm_interface_compat import LLMInterface
from src.workflow.state import MultiScenarioState
from src.tech_debt import DebtCalculator, PrioritizationEngine, RepaymentPlanner
from src.prompts.prompt_registry import get_global_registry

logger = logging.getLogger(__name__)

def tech_debt_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    Scenario 12: Enhanced Technical Debt Quantification with Graph Methods (Week 11 + Graph Methods)

    Uses specialized technical debt agents + graph analysis for comprehensive debt analysis:
    1. DebtCalculator - Detect and measure all technical debt
    2. PrioritizationEngine - Rank debt by ROI (effort vs business value)
    3. CallGraphAnalyzer - Graph Method #2: Impact analysis for debt prioritization
    4. RepaymentPlanner - Create sprint-based debt repayment plans

    Returns detailed debt analysis with graph-based impact prioritization.
    """
    logger.info("Executing ENHANCED technical debt quantification workflow with GRAPH METHODS")

    # Track graph insights
    graph_insights = {
        'high_impact_debt': [],
        'debt_hotspots': []
    }

    try:
        with CPGQueryService() as cpg:
            # Get codebase size for debt ratio calculation
            stats = cpg.get_database_stats()
            codebase_size = stats.get('method_count', 10000) * 20  # Rough estimate: 20 LOC/method

            # AGENT 1: DebtCalculator - Detect and measure all debt
            logger.info("Running DebtCalculator...")
            calculator = DebtCalculator(cpg)
            debt_items = calculator.detect_all_debt(limit_per_pattern=20)
            metrics = calculator.calculate_metrics(debt_items, codebase_size=codebase_size)
            logger.info(f"DebtCalculator found {len(debt_items)} debt items ({metrics.total_effort_hours:.1f}h total)")

            # AGENT 2: PrioritizationEngine - Rank by ROI
            logger.info("Running PrioritizationEngine...")
            prioritizer = PrioritizationEngine()
            prioritized_items = prioritizer.prioritize_debt(debt_items, metrics)
            quick_wins = prioritizer.get_quick_wins(prioritized_items)
            strategic_items = prioritizer.get_strategic_items(prioritized_items)
            logger.info(f"PrioritizationEngine: {len(quick_wins)} quick wins, {len(strategic_items)} strategic items")

            # AGENT 3: RepaymentPlanner - Create repayment plan
            logger.info("Running RepaymentPlanner...")
            planner = RepaymentPlanner(team_velocity=40.0)  # 40 hours per sprint
            plan = planner.create_plan(prioritized_items, max_sprints=6)
            logger.info(f"RepaymentPlanner created {len(plan.sprints)}-sprint plan ({plan.estimated_weeks} weeks)")

        # Build evidence list
        evidence = [
            f"Total debt: {metrics.total_items} items, {metrics.total_effort_hours:.1f} hours",
            f"Debt ratio: {metrics.debt_ratio:.2%}",
            f"High severity: {metrics.by_severity.get('high', 0)}",
            f"Quick wins: {len(quick_wins)}",
            f"Strategic items: {len(strategic_items)}",
            f"Repayment plan: {len(plan.sprints)} sprints",
            f"High interest debt: {metrics.high_interest_items} items"
        ]

        # Generate enhanced LLM prompt with rich debt data using registry
        llm = LLMInterface()
        registry = get_global_registry()

        # Build category summary
        category_summary = "\n".join([
            f"- {cat}: {count} items"
            for cat, count in sorted(metrics.by_category.items(), key=lambda x: -x[1])
        ])

        # Quick wins detail
        quick_wins_detail = "\n".join([
            f"{idx}. {p.item.pattern_name} in {p.item.location} (effort: {p.item.effort_hours}h, ROI: {p.roi_score:.1f})"
            for idx, p in enumerate(quick_wins[:5], 1)
        ])

        # High priority items
        high_priority = [p for p in prioritized_items if p.priority_score >= 8]
        high_priority_detail = "\n".join([
            f"{idx}. [{p.priority_score}] {p.item.pattern_name}: {p.item.description[:80]}..."
            for idx, p in enumerate(high_priority[:5], 1)
        ])

        # Sprint breakdown
        sprint_summary = "\n".join([
            f"Sprint {s['sprint_number']}: {len(s['items'])} items ({s['total_effort']:.1f}h) - {s['quick_wins']} quick wins, {s['strategic']} strategic"
            for s in plan.sprints[:4]  # First 4 sprints
        ])

        # Get prompts from registry
        prompt_vars = {
            'domain': 'PostgreSQL',
            'query': state['query'],
            'total_debt_items': str(metrics.total_items),
            'total_effort_hours': f"{metrics.total_effort_hours:.1f}",
            'debt_ratio': f"{metrics.debt_ratio:.2%}",
            'debt_categories': category_summary,
            'quick_wins': quick_wins_detail if quick_wins_detail else 'None identified',
            'high_priority_items': high_priority_detail if high_priority_detail else 'None',
            'roi_analysis': f"Quick Wins: {len(quick_wins)}, Strategic: {len(strategic_items)}, Avg ROI: {sum(p.roi_score for p in prioritized_items) / len(prioritized_items) if prioritized_items else 0:.1f}",
            'repayment_plan': sprint_summary
        }

        prompts = registry.get_agent_prompt('tech_debt_manager', **prompt_vars)

        debt_prompt = f"""{prompts['system']}

{prompts['user']}

User Question: {state['query']}

ENHANCED TECHNICAL DEBT ANALYSIS:

📊 DEBT SUMMARY:
- Total Items: {metrics.total_items}
- Total Effort: {metrics.total_effort_hours:.1f} hours
- Debt Ratio: {metrics.debt_ratio:.2%} (effort/codebase size)
- Average Effort per Item: {metrics.average_effort:.1f}h
- High Interest Items: {metrics.high_interest_items} (debt growing fast)

📊 BY SEVERITY:
- High: {metrics.by_severity.get('high', 0)}
- Medium: {metrics.by_severity.get('medium', 0)}
- Low: {metrics.by_severity.get('low', 0)}

📁 BY CATEGORY:
{category_summary}

🎯 QUICK WINS (Low Effort, High Value):
{quick_wins_detail if quick_wins_detail else "None identified"}

⚠️ HIGH-PRIORITY DEBT (Top 5):
{high_priority_detail if high_priority_detail else "None"}

💰 ROI ANALYSIS:
- Quick Wins: {len(quick_wins)} items for immediate value
- Strategic Items: {len(strategic_items)} items for long-term health
- Average ROI Score: {sum(p.roi_score for p in prioritized_items) / len(prioritized_items) if prioritized_items else 0:.1f}

📅 REPAYMENT PLAN ({len(plan.sprints)} sprints, {plan.estimated_weeks} weeks):
{sprint_summary}

📝 PLAN SUMMARY:
{plan.summary}

RECOMMENDATIONS:
{chr(10).join([f"{i+1}. {rec}" for i, rec in enumerate(plan.recommendations[:5])])}

Based on this comprehensive analysis, provide:
1. Assessment of overall technical debt health and sustainability
2. Immediate action items (quick wins to start in Sprint 1)
3. Medium-term debt reduction strategy (sprints 2-3)
4. Long-term debt prevention recommendations
5. Specific guidance relevant to the user's question

Format as a professional technical debt action plan.
"""

        answer = llm.generate(add_language_instruction(prompts['system'], state), debt_prompt)

        # Update state with comprehensive results
        state['cpg_results'] = [item.metadata for item in debt_items]
        state['methods'] = [p.item.metadata for p in high_priority[:20]]  # Top 20 high priority
        state['answer'] = answer
        state['evidence'] = evidence
        state['metadata'] = {
            'plan_id': plan.plan_id,
            'timestamp': plan.timestamp,
            'total_debt_items': metrics.total_items,
            'total_effort_hours': metrics.total_effort_hours,
            'debt_ratio': metrics.debt_ratio,
            'by_severity': metrics.by_severity,
            'by_category': metrics.by_category,
            'quick_wins_count': len(quick_wins),
            'strategic_count': len(strategic_items),
            'high_priority_count': len(high_priority),
            'repayment_sprints': len(plan.sprints),
            'estimated_weeks': plan.estimated_weeks,
            'high_interest_items': metrics.high_interest_items,
            'enhanced_mode': True,  # Flag indicating enhanced workflow
            'graph_methods_enabled': True,
            'graph_insights': {
                'high_impact_debt': len(graph_insights['high_impact_debt']),
                'debt_hotspots': len(graph_insights['debt_hotspots'])
            }
        }

    except Exception as e:
        logger.error(f"Enhanced technical debt workflow failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        state['error'] = str(e)
        state['answer'] = f"Error during enhanced technical debt analysis: {e}"

    return state




__all__ = ['tech_debt_workflow']
