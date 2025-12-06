"""
Scenario 7: Test Coverage Analysis with Graph Methods
"""

import logging
from typing import Dict, List, Any, Optional

from src.services.cpg_query_service import CPGQueryService
from src.llm.llm_interface_compat import LLMInterface
from src.workflow.state import MultiScenarioState

logger = logging.getLogger(__name__)

def test_coverage_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    Scenario 7: Test Coverage Analysis with Graph Methods

    Identifies testing gaps by:
    1. Finding methods without test coverage
    2. Analyzing coverage by subsystem
    3. CallGraphAnalyzer - Graph Method #2: Prioritize untested methods by impact
    4. Generating test coverage improvement plan with LLM

    Returns prioritized test coverage gaps with impact-based recommendations.
    """
    logger.info("Executing test coverage workflow with GRAPH METHODS")

    # Track graph insights
    graph_insights = {
        'critical_untested': [],
        'high_impact_untested': [],
        'untested_entry_points': []
    }

    try:
        # Extract target subsystem from query if specified
        query_lower = state['query'].lower()
        target_subsystem = None

        with CPGQueryService() as cpg:
            # Get all subsystems first
            subsystems = cpg.get_subsystems()

            # Try to find target subsystem in query
            for subsys in subsystems:
                if subsys['name'].lower() in query_lower:
                    target_subsystem = subsys['name']
                    break

            # Get methods without tests
            untested_methods = cpg.get_methods_without_tests(
                subsystem=target_subsystem,
                limit=100
            )

            # GRAPH METHOD #2: CallGraphAnalyzer - Prioritize untested methods by impact
            try:
                logger.info("Running CallGraphAnalyzer to prioritize untested methods...")
                from src.analysis import CallGraphAnalyzer
                call_analyzer = CallGraphAnalyzer(cpg)

                # Analyze each untested method to determine testing priority
                for method in untested_methods[:30]:  # Analyze top 30 untested methods
                    method_name = method.get('name', '')
                    if not method_name:
                        continue

                    # Find callers (untested methods with many callers = high priority)
                    callers = call_analyzer.find_all_callers(method_name, max_depth=2)
                    # callers can be list of strings or list of dicts depending on implementation
                    if callers and isinstance(callers[0], dict):
                        direct_callers = [c for c in callers if c.get('depth', 1) == 1]
                    else:
                        # If callers are strings, treat all as direct callers
                        direct_callers = callers if callers else []

                    # Compute impact score
                    impact = call_analyzer.analyze_impact(method_name)

                    # Determine testing priority
                    testing_priority = 'low'
                    if impact and impact.impact_score > 0.7:
                        testing_priority = 'high'
                    elif impact and impact.impact_score > 0.4:
                        testing_priority = 'medium'

                    # Determine if entry point (has many callers but few callees)
                    is_entry_point = (len(callers) >= 3 and
                                      len(impact.direct_callees if impact else []) >= 5) if impact else False

                    method_info = {
                        'method': method_name,
                        'filename': method.get('filename', 'unknown'),
                        'callers': len(callers),
                        'direct_callers': len(direct_callers),
                        'impact_score': impact.impact_score if impact else 0.0,
                        'is_entry_point': is_entry_point,
                        'testing_priority': testing_priority
                    }

                    # Track high-impact untested methods (CRITICAL to test!)
                    if impact and impact.impact_score > 0.7:
                        graph_insights['high_impact_untested'].append(method_info)

                    # Track untested entry points (security/reliability risk!)
                    if is_entry_point:
                        graph_insights['untested_entry_points'].append(method_info)

                    # Track critical untested methods (many callers + high impact)
                    if len(callers) > 5 and impact and impact.impact_score > 0.5:
                        graph_insights['critical_untested'].append(method_info)

                # Sort by impact score
                graph_insights['high_impact_untested'].sort(key=lambda x: x['impact_score'], reverse=True)
                graph_insights['critical_untested'].sort(key=lambda x: x['callers'], reverse=True)

                logger.info(f"CallGraphAnalyzer: {len(graph_insights['high_impact_untested'])} high-impact untested, "
                           f"{len(graph_insights['untested_entry_points'])} untested entry points, "
                           f"{len(graph_insights['critical_untested'])} critical untested")

            except Exception as e:
                logger.error(f"CallGraphAnalyzer failed: {e}", exc_info=True)
                # Continue without graph insights

        # Build enhanced evidence
        evidence = [
            f"Methods without test coverage: {len(untested_methods)}",
            f"Subsystem analyzed: {target_subsystem if target_subsystem else 'All subsystems'}",
            f"High-impact untested methods: {len(graph_insights['high_impact_untested'])}",
            f"Untested entry points: {len(graph_insights['untested_entry_points'])}",
            f"Critical untested methods: {len(graph_insights['critical_untested'])}"
        ]

        # Generate test coverage report
        llm = LLMInterface()

        # Build graph insights for prompt
        priority_summary = ""
        if graph_insights['high_impact_untested']:
            priority_summary = "\n\n⚠️ HIGH-IMPACT UNTESTED METHODS (CRITICAL PRIORITY):\n"
            for um in graph_insights['high_impact_untested'][:5]:
                priority_summary += f"  - {um['method']} ({um['filename']}): "
                priority_summary += f"Impact {um['impact_score']:.2f}, {um['callers']} callers - {um['testing_priority'].upper()} priority\n"

        entry_points_summary = ""
        if graph_insights['untested_entry_points']:
            entry_points_summary = "\n\n🚨 UNTESTED ENTRY POINTS (Security/Reliability Risk):\n"
            for ep in graph_insights['untested_entry_points'][:5]:
                entry_points_summary += f"  - {ep['method']} ({ep['filename']}): "
                entry_points_summary += f"{ep['callers']} callers, Impact {ep['impact_score']:.2f}\n"

        critical_summary = ""
        if graph_insights['critical_untested']:
            critical_summary = "\n\n💥 CRITICAL UNTESTED METHODS (High Caller Count + High Impact):\n"
            for cu in graph_insights['critical_untested'][:5]:
                critical_summary += f"  - {cu['method']}: {cu['callers']} callers, Impact {cu['impact_score']:.2f}\n"

        coverage_prompt = f"""You are a test engineer analyzing test coverage for PostgreSQL.

User Question: {state['query']}

Test Coverage Analysis:
- Methods without test coverage: {len(untested_methods)}
- Subsystem: {target_subsystem if target_subsystem else 'All subsystems'}

Untested Methods (first 20):
{chr(10).join([f"- {m['name']} in {m['filename']}" for m in untested_methods[:20]])}
{priority_summary}
{entry_points_summary}
{critical_summary}

Provide:
1. Summary of test coverage gaps (focus on high-impact and entry point methods)
2. Top 5 critical methods that need tests (use the impact analysis above)
3. Suggested test cases for each critical method
4. Testing strategy recommendations (unit tests, integration tests, etc.)
5. Priority levels for test development (which methods to test first)

Format as a concise test coverage improvement plan with impact-based prioritization.
"""

        answer = llm.generate("You are an AI assistant.", coverage_prompt)

        # Update state
        state['cpg_results'] = untested_methods
        state['methods'] = untested_methods[:50]  # Top 50 untested methods
        state['answer'] = answer
        state['evidence'] = evidence
        state['metadata'] = {
            'untested_count': len(untested_methods),
            'target_subsystem': target_subsystem,
            'graph_methods_enabled': True,
            'graph_insights': {
                'high_impact_untested': len(graph_insights['high_impact_untested']),
                'untested_entry_points': len(graph_insights['untested_entry_points']),
                'critical_untested': len(graph_insights['critical_untested']),
                'max_impact_score': max([um['impact_score'] for um in graph_insights['high_impact_untested']], default=0.0),
                'methods_analyzed': min(30, len(untested_methods))
            }
        }

    except Exception as e:
        logger.error(f"Test coverage workflow failed: {e}")
        state['error'] = str(e)
        state['answer'] = f"Error during test coverage analysis: {e}"

    return state




__all__ = ['test_coverage_workflow']
