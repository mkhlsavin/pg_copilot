"""
Scenario 4: Feature Development Assistance with Graph Analysis
"""

import logging
from typing import Dict, List, Any, Optional

from src.services.cpg_query_service import CPGQueryService
from src.llm.llm_interface_compat import LLMInterface
from src.workflow.state import MultiScenarioState
from src.prompts.prompt_registry import get_global_registry

logger = logging.getLogger(__name__)

def feature_dev_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    Scenario 4: Feature Development Assistance with Graph Analysis

    Helps find integration points by:
    1. Analyzing query for target subsystem/feature
    2. Finding relevant methods and call patterns
    3. CallGraphAnalyzer - Graph Method #2: Identify integration points via call graph
    4. Suggesting where to add code with impact analysis
    """
    logger.info("Executing feature development workflow with GRAPH METHODS")

    # Track graph insights
    graph_insights = {
        'integration_points': [],
        'similar_features': [],
        'impact_analysis': {}
    }

    try:
        # Parse query for target area
        query_lower = state['query'].lower()

        with CPGQueryService() as cpg:
            # Get subsystems
            subsystems = cpg.get_subsystems()

            # Try to find relevant subsystem
            target_subsystem = None
            for subsys in subsystems:
                if subsys['name'].lower() in query_lower:
                    target_subsystem = subsys['name']
                    break

            if not target_subsystem and subsystems:
                # Default to first subsystem
                target_subsystem = subsystems[0]['name']

            # Get methods in target subsystem
            if target_subsystem:
                methods = cpg.get_methods_by_subsystem(target_subsystem, limit=50)
            else:
                methods = []

            # GRAPH METHOD #2: CallGraphAnalyzer - Find integration points
            try:
                logger.info("Running CallGraphAnalyzer for integration point analysis...")
                from src.analysis import CallGraphAnalyzer
                call_analyzer = CallGraphAnalyzer(cpg)

                # 1. Identify potential integration points (methods with many callers)
                for method in methods[:20]:  # Top 20 methods
                    method_name = method.get('name', '')
                    if not method_name:
                        continue

                    # Get callers (indicates this is a popular integration point)
                    callers = call_analyzer.find_all_callers(method_name, max_depth=2)
                    callees = call_analyzer.find_all_callees(method_name, max_depth=2)

                    # Compute impact if we modify this method
                    impact = call_analyzer.analyze_impact(method_name)

                    if len(callers) > 3:  # Popular method = good integration point
                        graph_insights['integration_points'].append({
                            'method': method_name,
                            'filename': method.get('filename', 'unknown'),
                            'callers': len(callers),
                            'callees': len(callees),
                            'impact_score': impact.impact_score if impact else 0.0,
                            'is_entry_point': impact.is_entry_point if impact else False,
                            'reason': 'High caller count - popular integration point'
                        })

                # Sort by caller count (most popular first)
                graph_insights['integration_points'].sort(key=lambda x: x['callers'], reverse=True)

                # 2. For each integration point, analyze modification impact
                for int_point in graph_insights['integration_points'][:5]:
                    method_name = int_point['method']
                    impact = call_analyzer.analyze_impact(method_name)

                    if impact:
                        graph_insights['impact_analysis'][method_name] = {
                            'safe_to_modify': impact.impact_score < 0.5,  # Low impact = safer
                            'impact_score': impact.impact_score,
                            'upstream_count': len(impact.transitive_callers),
                            'downstream_count': len(impact.transitive_callees),
                            'recommendation': 'Safe to extend' if impact.impact_score < 0.5 else 'Modify with caution'
                        }

                logger.info(f"Identified {len(graph_insights['integration_points'])} integration points")

                # Phase 3.2 / Phase 4A Enhancement: Add betweenness centrality analysis
                try:
                    logger.info("Running betweenness centrality analysis for integration points...")
                    from src.architecture.architecture_agents import DependencyAnalyzer

                    analyzer = DependencyAnalyzer(cpg)
                    chokepoints = analyzer.identify_architectural_chokepoints()

                    if chokepoints:
                        # High betweenness = central in architecture = good integration point
                        betweenness_integration_points = []
                        for cp in chokepoints[:15]:  # Top 15 by betweenness
                            if cp['betweenness_percentile'] > 80:  # Top 20%
                                betweenness_integration_points.append({
                                    'method': cp['method_name'],
                                    'betweenness_score': cp['betweenness_score'],
                                    'betweenness_percentile': cp['betweenness_percentile'],
                                    'risk_level': cp['risk_level'],
                                    'reason': 'High architectural centrality - strategic integration point',
                                    'recommendation': 'Central method with high visibility - good for features affecting multiple subsystems'
                                })

                        # Add to graph insights
                        graph_insights['betweenness_integration_points'] = betweenness_integration_points
                        logger.info(f"Identified {len(betweenness_integration_points)} high-centrality integration points")

                except Exception as e:
                    logger.warning(f"Betweenness centrality analysis failed: {e}")
                    # Continue without betweenness insights

            except Exception as e:
                logger.error(f"CallGraphAnalyzer failed: {e}", exc_info=True)
                # Continue without graph insights

        # Generate feature development guidance with graph insights
        llm = LLMInterface()

        # Build graph insights summaries
        integration_points_summary = ""
        if graph_insights['integration_points']:
            integration_points_summary = "\n🔌 INTEGRATION POINTS (Graph Analysis):\n"
            integration_points_summary += "Recommended hooks for new feature:\n" + "\n".join([
                f"  {idx+1}. {ip['method']} ({ip['filename']})\n"
                f"     - {ip['callers']} callers, {ip['callees']} callees\n"
                f"     - Impact: {ip['impact_score']:.2f}, {ip['reason']}"
                for idx, ip in enumerate(graph_insights['integration_points'][:5])
            ])

        impact_analysis_summary = ""
        if graph_insights['impact_analysis']:
            impact_analysis_summary = "\n💥 MODIFICATION IMPACT ANALYSIS:\n"
            for method, analysis in list(graph_insights['impact_analysis'].items())[:5]:
                impact_analysis_summary += f"  - {method}: {analysis['recommendation']}\n"
                impact_analysis_summary += f"    Impact: {analysis['impact_score']:.2f} "
                impact_analysis_summary += f"({analysis['upstream_count']} upstream, {analysis['downstream_count']} downstream)\n"

        # Phase 4A: Add betweenness centrality summary
        betweenness_summary = ""
        if graph_insights.get('betweenness_integration_points'):
            betweenness_summary = "\n🎯 ARCHITECTURAL CENTRALITY (Betweenness Centrality):\n"
            betweenness_summary += "Strategic integration points with high architectural visibility:\n" + "\n".join([
                f"  {idx+1}. {bp['method']}\n"
                f"     - Centrality: {bp['betweenness_percentile']:.1f}th percentile\n"
                f"     - Risk Level: {bp['risk_level']}\n"
                f"     - {bp['recommendation']}"
                for idx, bp in enumerate(graph_insights['betweenness_integration_points'][:5])
            ])

        # Build integration points summary for registry
        integration_points_data = "\n".join([
            f"- {ip['method']} ({ip['filename']}): {ip['callers']} callers, {ip['callees']} callees, Impact: {ip['impact_score']:.2f}"
            for ip in graph_insights['integration_points'][:5]
        ]) if graph_insights['integration_points'] else "No integration points identified"

        # Build related functions summary
        related_funcs = "\n".join([
            f"- {m['name']} in {m.get('filename', 'unknown')}"
            for m in methods[:15]
        ]) if methods else "No methods found"

        # Build dependencies context
        dependencies_ctx = f"""Target Subsystem: {target_subsystem or 'unknown'}
Methods in subsystem: {len(methods)}
Integration points identified: {len(graph_insights['integration_points'])}
{integration_points_summary}
{impact_analysis_summary}
{betweenness_summary}"""

        # Get prompts from registry
        registry = get_global_registry()
        prompts = registry.get_agent_prompt('feature_developer',
            domain='PostgreSQL',
            query=state['query'],
            integration_points=integration_points_data,
            related_functions=related_funcs,
            dependencies=dependencies_ctx
        )

        answer = llm.generate(prompts['system'], prompts['user'])

        state['subsystems'] = [target_subsystem] if target_subsystem else []
        state['methods'] = methods
        state['answer'] = answer
        # Phase 4A: Add betweenness evidence
        evidence_list = [
            f"Analyzed {len(methods)} methods in {target_subsystem or 'codebase'}",
            f"Integration points identified: {len(graph_insights['integration_points'])}",
            f"Impact analysis for {len(graph_insights['impact_analysis'])} key methods",
            f"Safe to extend: {len([m for m, a in graph_insights['impact_analysis'].items() if a['safe_to_modify']])} methods"
        ]
        if graph_insights.get('betweenness_integration_points'):
            evidence_list.append(f"High-centrality integration points (betweenness): {len(graph_insights['betweenness_integration_points'])}")

        state['evidence'] = evidence_list
        state['metadata'] = {
            'target_subsystem': target_subsystem,
            'method_count': len(methods),
            'graph_methods_enabled': True,  # NEW
            'betweenness_analysis_enabled': bool(graph_insights.get('betweenness_integration_points')),  # Phase 4A
            'graph_insights': {
                'integration_points_found': len(graph_insights['integration_points']),
                'safe_to_extend': len([m for m, a in graph_insights['impact_analysis'].items() if a['safe_to_modify']]),
                'high_impact_points': len([ip for ip in graph_insights['integration_points'] if ip['impact_score'] > 0.7]),
                'top_integration_point': graph_insights['integration_points'][0]['method'] if graph_insights['integration_points'] else None,
                # Phase 4A: Betweenness centrality insights
                'high_centrality_points': len(graph_insights.get('betweenness_integration_points', [])),
                'top_centrality_method': graph_insights['betweenness_integration_points'][0]['method'] if graph_insights.get('betweenness_integration_points') else None,
                'max_centrality_percentile': max([bp['betweenness_percentile'] for bp in graph_insights.get('betweenness_integration_points', [])], default=0)
            }
        }

    except Exception as e:
        logger.error(f"Feature development workflow failed: {e}")
        state['error'] = str(e)
        state['answer'] = f"Error in feature development workflow: {e}"

    return state


# ============================================================================
# PLACEHOLDER WORKFLOWS (Week 2-4)
# ============================================================================

# security_workflow moved to src/workflow/scenarios/security.py



__all__ = ['feature_dev_workflow']
