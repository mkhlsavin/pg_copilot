"""
Scenario 10: Cross-Repository Analysis with Graph Methods (Week 14-15 + Graph Methods)
"""

import logging
from typing import Dict, List, Any, Optional

from src.services.cpg_query_service import CPGQueryService
from src.llm.llm_interface_compat import LLMInterface
from src.workflow.state import MultiScenarioState
from src.prompts.prompt_registry import get_global_registry

logger = logging.getLogger(__name__)

def cross_repo_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    Scenario 10: Cross-Repository Analysis with Graph Methods (Week 14-15 + Graph Methods)

    Automated cross-repository analysis by:
    1. Discovering and indexing repositories (RepositoryIndexer)
    2. Detecting code duplication across repos (CrossRepoAnalyzer)
    3. Mapping inter-repository dependencies (DependencyMapper)
    4. Identifying consolidation opportunities
    5. CallGraphAnalyzer - Graph Method #2: Shared method analysis and consolidation patterns
    6. Generating consolidation report with LLM analysis

    Returns cross-repo analysis with graph-based consolidation recommendations.
    """
    logger.info("Executing cross-repository analysis workflow with GRAPH METHODS")

    # Track graph insights
    graph_insights = {
        'shared_methods': [],
        'consolidation_patterns': [],
        'cross_repo_calls': []
    }

    try:
        with CPGQueryService() as cpg:
            # Agent 1: Repository Indexer
            indexer = RepositoryIndexer(cpg)

            # Check if workspace path provided in context
            workspace_path = state.get('user_context', {}).get('workspace_path', '.')

            # Discover repositories
            repositories = indexer.discover_repositories(workspace_path)

            if not repositories:
                # If no repos found in workspace, create mock repo for current project
                current_repo = indexer._extract_repo_metadata(Path('.'))
                repositories = [current_repo]

            # Index repositories into CPG
            for repo in repositories:
                indexer.index_repository_cpg(repo)

            logger.info(f"Indexed {len(repositories)} repositories")

            # Agent 2: Cross-Repo Analyzer
            analyzer = CrossRepoAnalyzer(cpg)

            # Find code duplications
            duplications = analyzer.find_code_duplications(
                repositories,
                min_similarity=70.0,
                min_lines=10
            )

            # Find similar utility functions
            utility_dups = analyzer.find_similar_utilities(repositories)
            all_duplications = duplications + utility_dups

            # Identify consolidation opportunities
            opportunities = analyzer.identify_consolidation_opportunities(all_duplications)

            logger.info(f"Found {len(all_duplications)} duplications, {len(opportunities)} opportunities")

            # Agent 3: Dependency Mapper
            mapper = DependencyMapper(cpg)

            # Map dependencies
            dependencies = mapper.map_dependencies(repositories)

            # Generate dependency graph
            dep_graph = mapper.generate_dependency_graph(dependencies)

            # Detect circular dependencies
            circular_deps = mapper.detect_circular_dependencies(dep_graph)

            # Generate consolidation report
            report = mapper.generate_dependency_report(
                repositories,
                dependencies,
                all_duplications,
                opportunities
            )

            logger.info(f"Found {len(dependencies)} cross-repo dependencies")

            # GRAPH METHOD #2: CallGraphAnalyzer - Analyze shared methods and consolidation patterns
            try:
                logger.info("Running CallGraphAnalyzer for cross-repo method analysis...")
                from src.analysis import CallGraphAnalyzer
                call_analyzer = CallGraphAnalyzer(cpg)

                # Analyze duplicated methods to find consolidation patterns
                for dup in all_duplications[:10]:  # Top 10 duplications
                    if dup.instances and len(dup.instances) >= 2:
                        # Get method names from first instance
                        first_instance = dup.instances[0]
                        if hasattr(first_instance, 'method_name') and first_instance.method_name:
                            method_name = first_instance.method_name

                            # Analyze the shared method pattern
                            callers = call_analyzer.find_all_callers(method_name, max_depth=2)
                            callees = call_analyzer.find_all_callees(method_name, max_depth=2)
                            impact = call_analyzer.analyze_impact(method_name)

                            # Calculate consolidation benefit
                            consolidation_score = (len(callers) + len(callees)) * len(dup.instances)

                            graph_insights['shared_methods'].append({
                                'pattern_name': dup.pattern_name,
                                'instances': len(dup.instances),
                                'similarity': dup.similarity_score,
                                'callers': len(callers),
                                'callees': len(callees),
                                'impact_score': impact.impact_score if impact else 0.0,
                                'consolidation_score': consolidation_score,
                                'consolidation_benefit': 'high' if consolidation_score > 50 else 'medium' if consolidation_score > 20 else 'low'
                            })

                # Analyze cross-repo dependencies using call graph
                for dep in dependencies[:10]:
                    # Find methods that create this dependency
                    if hasattr(dep, 'source_method') and dep.source_method:
                        source_method = dep.source_method

                        # Find what this method calls (cross-repo calls)
                        callees = call_analyzer.find_all_callees(source_method, max_depth=2)

                        # Check for tight coupling (many cross-repo calls)
                        if len(callees) > 5:
                            graph_insights['cross_repo_calls'].append({
                                'source_repo': dep.source_repo,
                                'target_repo': dep.target_repo,
                                'source_method': source_method,
                                'cross_calls': len(callees),
                                'coupling_score': dep.coupling_score,
                                'decoupling_priority': 'high' if len(callees) > 10 else 'medium'
                            })

                # Identify consolidation patterns based on call graph similarity
                method_groups = {}  # Group methods by call pattern
                for dup in all_duplications[:15]:
                    if dup.instances:
                        for inst in dup.instances:
                            if hasattr(inst, 'method_name') and inst.method_name:
                                method_name = inst.method_name
                                callees = call_analyzer.find_all_callees(method_name, max_depth=1)
                                callee_names = {c.get('callee_name', '') for c in callees}

                                # Create signature from callees
                                signature = tuple(sorted(callee_names))
                                if signature not in method_groups:
                                    method_groups[signature] = []
                                method_groups[signature].append(method_name)

                # Find patterns with multiple instances (consolidation candidates)
                for signature, methods in method_groups.items():
                    if len(methods) >= 2 and signature:  # At least 2 methods with same pattern
                        graph_insights['consolidation_patterns'].append({
                            'pattern_signature': ', '.join(list(signature)[:3]),  # First 3 callees
                            'method_count': len(methods),
                            'consolidation_opportunity': 'Extract to shared library',
                            'priority': 'high' if len(methods) >= 3 else 'medium'
                        })

                logger.info(f"CallGraphAnalyzer: Found {len(graph_insights['shared_methods'])} shared methods, "
                           f"{len(graph_insights['consolidation_patterns'])} consolidation patterns, "
                           f"{len(graph_insights['cross_repo_calls'])} high-coupling dependencies")

            except Exception as e:
                logger.error(f"CallGraphAnalyzer failed: {e}", exc_info=True)
                # Continue without graph insights

        # Build evidence list
        evidence = []

        # Top duplications
        for dup in sorted(all_duplications, key=lambda d: d.similarity_score, reverse=True)[:5]:
            repos = set(inst.repo_id for inst in dup.instances)
            evidence.append(
                f"DUPLICATION [{dup.severity.value.upper()}]: {dup.pattern_name} "
                f"({dup.similarity_score:.1f}% similar) found in {len(repos)} repos - "
                f"could save {dup.potential_savings} LOC"
            )

        # Top opportunities
        for opp in opportunities[:5]:
            evidence.append(
                f"CONSOLIDATION [P{opp.priority}]: {opp.title} - "
                f"save {opp.estimated_savings} LOC, effort {opp.estimated_effort:.1f}h"
            )

        # High-risk dependencies
        high_risk_deps = [d for d in dependencies if d.risk_level.value in ['critical', 'high']]
        for dep in high_risk_deps[:5]:
            evidence.append(
                f"DEPENDENCY [{dep.risk_level.value.upper()}]: {dep.source_repo} → {dep.target_repo} "
                f"({dep.dependency_type.value}, coupling: {dep.coupling_score:.1f})"
            )

        # Circular dependencies
        if circular_deps:
            for cycle in circular_deps[:3]:
                evidence.append(f"CIRCULAR DEPENDENCY: {' → '.join(cycle)}")

        # Generate LLM prompt
        llm_prompt = f"""
Query: {state['query']}

CROSS-REPOSITORY CONSOLIDATION ANALYSIS

REPOSITORY SUMMARY:
- Total Repositories: {report.total_repos}
- Total Methods: {report.total_methods}
- Languages: {', '.join(set(r.language for r in repositories))}

CODE DUPLICATION:
- Total Duplications Found: {len(all_duplications)}
  - Critical: {sum(1 for d in all_duplications if d.severity.value == 'critical')}
  - High: {sum(1 for d in all_duplications if d.severity.value == 'high')}
  - Medium: {sum(1 for d in all_duplications if d.severity.value == 'medium')}
- Estimated Savings: {report.estimated_total_savings} lines of code

TOP 5 DUPLICATIONS:
{chr(10).join([f"{i+1}. {d.pattern_name} ({d.similarity_score:.1f}% similar, {len(d.instances)} instances)" for i, d in enumerate(sorted(all_duplications, key=lambda d: d.similarity_score, reverse=True)[:5])])}

CONSOLIDATION OPPORTUNITIES:
- Total Opportunities: {len(opportunities)}

TOP 5 PRIORITIES:
{chr(10).join([f"{i+1}. [P{o.priority}] {o.title}" for i, o in enumerate(opportunities[:5])])}
{chr(10).join([f"   - Effort: {o.estimated_effort:.1f}h, Savings: {o.estimated_savings} LOC" for o in opportunities[:5]])}

CROSS-REPO DEPENDENCIES:
- Total Dependencies: {len(dependencies)}
- Risk Summary:
  - Critical: {report.risk_summary.get('critical', 0)}
  - High: {report.risk_summary.get('high', 0)}
  - Medium: {report.risk_summary.get('medium', 0)}
  - Low: {report.risk_summary.get('low', 0)}

HIGH-RISK DEPENDENCIES:
{chr(10).join([f"- {d.source_repo} → {d.target_repo} ({d.dependency_type.value}, coupling: {d.coupling_score:.1f})" for d in high_risk_deps[:5]])}

CIRCULAR DEPENDENCIES:
{chr(10).join([f"- {' → '.join(cycle)}" for cycle in circular_deps[:3]]) if circular_deps else "None detected"}

DETAILED EVIDENCE:
{chr(10).join(evidence[:20])}
"""

        # Add graph insights to LLM prompt
        if graph_insights['shared_methods'] or graph_insights['consolidation_patterns']:
            llm_prompt += "\n\n📊 GRAPH ANALYSIS - CONSOLIDATION INSIGHTS:\n"

            # Shared methods analysis
            if graph_insights['shared_methods']:
                llm_prompt += f"\n**Shared Methods Analysis ({len(graph_insights['shared_methods'])} analyzed):**\n"
                high_benefit = [sm for sm in graph_insights['shared_methods'] if sm['consolidation_benefit'] == 'high']
                llm_prompt += f"- High consolidation benefit: {len(high_benefit)} methods\n"
                for sm in sorted(graph_insights['shared_methods'], key=lambda x: x['consolidation_score'], reverse=True)[:5]:
                    llm_prompt += f"  - {sm['pattern_name']}: {sm['instances']} instances, "
                    llm_prompt += f"{sm['similarity']:.1f}% similar, score: {sm['consolidation_score']}, "
                    llm_prompt += f"{sm['consolidation_benefit'].upper()} benefit\n"

            # Consolidation patterns
            if graph_insights['consolidation_patterns']:
                llm_prompt += f"\n**🎯 Consolidation Patterns ({len(graph_insights['consolidation_patterns'])} found):**\n"
                high_priority = [cp for cp in graph_insights['consolidation_patterns'] if cp['priority'] == 'high']
                llm_prompt += f"- High priority patterns: {len(high_priority)}\n"
                for cp in sorted(graph_insights['consolidation_patterns'], key=lambda x: x['method_count'], reverse=True)[:5]:
                    llm_prompt += f"  - Pattern calling [{cp['pattern_signature']}]: "
                    llm_prompt += f"{cp['method_count']} methods - {cp['consolidation_opportunity']} ({cp['priority'].upper()})\n"

            # Cross-repo coupling analysis
            if graph_insights['cross_repo_calls']:
                llm_prompt += f"\n**⚠️ High-Coupling Cross-Repo Dependencies ({len(graph_insights['cross_repo_calls'])} found):**\n"
                high_priority_decoupling = [crc for crc in graph_insights['cross_repo_calls'] if crc['decoupling_priority'] == 'high']
                llm_prompt += f"- High decoupling priority: {len(high_priority_decoupling)}\n"
                for crc in sorted(graph_insights['cross_repo_calls'], key=lambda x: x['cross_calls'], reverse=True)[:5]:
                    llm_prompt += f"  - {crc['source_repo']} → {crc['target_repo']}: "
                    llm_prompt += f"{crc['cross_calls']} cross-calls, coupling: {crc['coupling_score']:.1f}, "
                    llm_prompt += f"priority: {crc['decoupling_priority'].upper()}\n"

        llm_prompt += """

Please provide:
1. Analysis of most critical duplication and consolidation opportunities
2. Risk assessment of high-coupling dependencies
3. Recommended consolidation roadmap (prioritized action plan)
4. Estimated ROI of top 3 consolidation opportunities
5. Strategies to reduce coupling and circular dependencies
"""

        # Get LLM answer
        llm = LLMInterface()
        answer = llm.generate("You are an AI assistant.", llm_prompt)

        # Update state
        state['llm_prompt'] = llm_prompt
        state['answer'] = answer
        state['evidence'] = evidence
        state['cpg_results'] = {
            'repositories': [
                {
                    'id': r.repo_id,
                    'name': r.name,
                    'language': r.language,
                    'methods': r.method_count,
                    'files': r.file_count,
                }
                for r in repositories
            ],
            'duplications': [
                {
                    'pattern_name': d.pattern_name,
                    'similarity': d.similarity_score,
                    'severity': d.severity.value,
                    'instances': len(d.instances),
                    'savings': d.potential_savings,
                }
                for d in all_duplications[:10]
            ],
            'dependencies': [
                {
                    'source': d.source_repo,
                    'target': d.target_repo,
                    'type': d.dependency_type.value,
                    'coupling': d.coupling_score,
                    'risk': d.risk_level.value,
                }
                for d in dependencies[:10]
            ],
        }
        state['metadata'] = {
            'total_repos': report.total_repos,
            'total_methods': report.total_methods,
            'total_duplications': len(all_duplications),
            'total_dependencies': len(dependencies),
            'total_savings_potential': report.estimated_total_savings,
            'consolidation_opportunities': len(opportunities),
            'high_risk_dependencies': len(high_risk_deps),
            'circular_dependencies': len(circular_deps),
            'enhanced_mode': True,
            'graph_methods_enabled': True,
            'graph_insights': {
                'shared_methods_analyzed': len(graph_insights['shared_methods']),
                'high_consolidation_benefit': len([sm for sm in graph_insights['shared_methods'] if sm['consolidation_benefit'] == 'high']),
                'consolidation_patterns': len(graph_insights['consolidation_patterns']),
                'high_priority_patterns': len([cp for cp in graph_insights['consolidation_patterns'] if cp['priority'] == 'high']),
                'high_coupling_dependencies': len(graph_insights['cross_repo_calls']),
                'high_decoupling_priority': len([crc for crc in graph_insights['cross_repo_calls'] if crc['decoupling_priority'] == 'high']),
                'total_consolidation_score': sum([sm['consolidation_score'] for sm in graph_insights['shared_methods']])
            }
        }

    except Exception as e:
        logger.error(f"Enhanced cross-repo analysis workflow failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        state['error'] = str(e)
        state['answer'] = f"Error during cross-repository analysis: {e}"

    return state




__all__ = ['cross_repo_workflow']
