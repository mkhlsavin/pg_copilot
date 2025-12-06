"""
Scenario 14: Security Incident Response with Graph Analysis
"""

import logging
from typing import Dict, List, Any, Optional

from src.services.cpg_query_service import CPGQueryService
from src.llm.llm_interface_compat import LLMInterface
from src.workflow.state import MultiScenarioState

logger = logging.getLogger(__name__)

def security_incident_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    Scenario 14: Security Incident Response with Graph Analysis

    Handles emergency security incidents by:
    1. Finding all uses of vulnerable functions/patterns
    2. CallGraphAnalyzer - Graph Method #2: Trace call paths to vulnerable code
    3. DataFlowTracer - Graph Method #3: Real taint flow analysis for root cause
    4. Identifying attack surface and exploitable paths via graph
    5. Generating emergency hotfix recommendations with LLM
    6. Prioritizing fixes by severity, exposure, and call path depth
    """
    logger.info("Executing security incident response workflow with GRAPH METHODS")

    # Track graph insights for incident analysis
    graph_insights = {
        'call_paths_to_vulns': [],
        'attack_vectors': [],
        'incident_taint_paths': [],
        'blast_radius': {}
    }

    try:
        # Extract vulnerable function/CVE from query
        vulnerable_function = None
        query_words = state['query'].split()
        for i, word in enumerate(query_words):
            if word.lower() in ['strcpy', 'sprintf', 'gets', 'scanf', 'memcpy'] or 'CVE' in word.upper():
                vulnerable_function = word
                break

        with CPGQueryService() as cpg:
            # Get all security vulnerabilities (high priority)
            critical_vulns = cpg.get_critical_vulnerabilities(limit=50)

            # Find specific vulnerable function usages if specified
            if vulnerable_function:
                vuln_usages = cpg.find_vulnerable_function_usages(function=vulnerable_function, limit=100)
            else:
                vuln_usages = []

            # GRAPH METHOD #2: CallGraphAnalyzer - Trace attack vectors to vulnerabilities
            try:
                logger.info("Running CallGraphAnalyzer for incident call path tracing...")
                from src.analysis import CallGraphAnalyzer
                call_analyzer = CallGraphAnalyzer(cpg)

                # 1. For each critical vulnerability, find how it can be reached
                for vuln in critical_vulns[:10]:  # Top 10 critical
                    vuln_method = vuln.get('name', '')
                    if not vuln_method:
                        continue

                    # Find all entry points that can reach this vulnerability
                    entry_points = ['main', 'PostgresMain', 'exec_simple_query',
                                   'ProcessUtility', 'PortalRun']

                    for entry in entry_points:
                        path = call_analyzer.find_shortest_path(entry, vuln_method)
                        if path:
                            graph_insights['call_paths_to_vulns'].append({
                                'entry_point': entry,
                                'vulnerable_method': vuln_method,
                                'path_length': path.path_length,
                                'intermediate_methods': path.intermediate_methods,
                                'severity': vuln.get('severity', 'unknown'),
                                'vuln_type': vuln.get('vulnerability_type', 'unknown')
                            })
                            # Found a path, track it as an attack vector
                            graph_insights['attack_vectors'].append({
                                'vector': f"{entry} → {vuln_method}",
                                'hops': path.path_length,
                                'severity': vuln.get('severity')
                            })
                            break  # One path per vulnerability is enough for incident response

                # 2. For vulnerable function (if specified), trace who calls it
                if vulnerable_function and vuln_usages:
                    for usage in vuln_usages[:10]:
                        caller_name = usage.get('caller_name', '')
                        if caller_name:
                            # Find callers of the caller (2 levels up)
                            callers = call_analyzer.find_all_callers(caller_name, max_depth=2)
                            if callers:
                                graph_insights['call_paths_to_vulns'].append({
                                    'entry_point': 'external',
                                    'vulnerable_method': vulnerable_function,
                                    'caller_method': caller_name,
                                    'upstream_callers': len(callers),
                                    'caller_chain': [c.get('caller_name', 'unknown') for c in callers[:3]]
                                })

                # 3. Calculate blast radius for emergency fix
                # How many methods would be affected by patching each critical vuln?
                for vuln in critical_vulns[:5]:
                    vuln_method = vuln.get('name', '')
                    if not vuln_method:
                        continue

                    callers = call_analyzer.find_all_callers(vuln_method, max_depth=3)
                    callees = call_analyzer.find_all_callees(vuln_method, max_depth=2)
                    blast_radius = len(callers) + len(callees)

                    graph_insights['blast_radius'][vuln_method] = {
                        'total_affected': blast_radius,
                        'callers': len(callers),
                        'callees': len(callees),
                        'risk': 'high' if blast_radius > 20 else 'medium' if blast_radius > 10 else 'low'
                    }

                logger.info(f"Found {len(graph_insights['call_paths_to_vulns'])} call paths to vulnerabilities")
                logger.info(f"Identified {len(graph_insights['attack_vectors'])} attack vectors")

            except Exception as e:
                logger.error(f"CallGraphAnalyzer failed: {e}", exc_info=True)
                # Continue without graph insights

            # GRAPH METHOD #3: DataFlowTracer - Real taint flow analysis for incident
            taint_flows = []
            try:
                logger.info("Running DataFlowTracer for incident taint analysis...")
                from src.analysis import DataFlowTracer
                flow_tracer = DataFlowTracer(cpg)

                # Find real taint paths related to the incident
                incident_sources = ['recv', 'readLine', 'getenv', 'read', 'fgets',
                                   'pq_getbyte', 'pq_getmessage', 'socket_read']
                incident_sinks = ['exec_simple_query', 'SPI_execute', 'system',
                                 'popen', 'strcpy', 'sprintf', 'memcpy']

                # If vulnerable function specified, add it as a sink
                if vulnerable_function:
                    incident_sinks.append(vulnerable_function)

                real_taint_paths = flow_tracer.find_taint_paths(
                    source_functions=incident_sources,
                    sink_functions=incident_sinks,
                    max_depth=8  # Shorter for incident response
                )

                # Convert to taint_flows format for compatibility
                for path in real_taint_paths:
                    taint_flow = {
                        'source': path.source_location.get('method_name', 'unknown'),
                        'sink': path.sink_location.get('method_name', 'unknown'),
                        'path_length': path.path_length,
                        'is_inter_procedural': path.is_inter_procedural
                    }
                    taint_flows.append(taint_flow)
                    graph_insights['incident_taint_paths'].append({
                        'path_id': path.path_id,
                        'source': taint_flow['source'],
                        'sink': taint_flow['sink'],
                        'hops': path.path_length,
                        'critical': taint_flow['sink'] in [v.get('name', '') for v in critical_vulns[:10]]
                    })

                logger.info(f"DataFlowTracer found {len(real_taint_paths)} real taint paths for incident")

            except Exception as e:
                logger.error(f"DataFlowTracer failed: {e}", exc_info=True)
                # Fallback to legacy method
                try:
                    taint_flows_raw = cpg.get_taint_flow_paths(limit=40)
                    taint_flows = taint_flows_raw if taint_flows_raw else []
                except:
                    taint_flows = []

            # Get exposed attack surface (kept for compatibility)
            attack_surface = cpg.get_attack_surface_methods(limit=30)

            # Categorize by severity
            critical = [v for v in critical_vulns if v.get('severity') == 'critical']
            high = [v for v in critical_vulns if v.get('severity') == 'high']
            medium = [v for v in critical_vulns if v.get('severity') == 'medium']

        # Combine all security findings
        all_findings = critical_vulns + vuln_usages + taint_flows + attack_surface

        # Build evidence list with graph insights (prioritize critical and high severity)
        evidence = []
        for vuln in critical[:10]:
            evidence.append(
                f"CRITICAL: {vuln.get('vulnerability_type', 'unknown')} in "
                f"{vuln.get('name', 'unknown')} at "
                f"{vuln.get('filename', 'unknown')}:{vuln.get('line_number', 0)}"
            )
        for vuln in high[:10]:
            evidence.append(
                f"HIGH: {vuln.get('vulnerability_type', 'unknown')} in "
                f"{vuln.get('name', 'unknown')} - "
                f"exploitability: {vuln.get('exploitability', 'unknown')}"
            )
        if vulnerable_function and vuln_usages:
            for usage in vuln_usages[:10]:
                evidence.append(
                    f"USAGE: {vulnerable_function} called in "
                    f"{usage.get('caller_name', 'unknown')} at "
                    f"{usage.get('filename', 'unknown')}:{usage.get('line_number', 0)}"
                )

        # Add graph-based evidence
        evidence.append(f"Attack vectors identified: {len(graph_insights['attack_vectors'])}")
        evidence.append(f"Call paths to vulnerabilities: {len(graph_insights['call_paths_to_vulns'])}")
        evidence.append(f"Real taint paths found: {len(graph_insights['incident_taint_paths'])}")
        evidence.append(f"Blast radius analyzed: {len(graph_insights['blast_radius'])} critical vulns")

        for flow in taint_flows[:5]:
            evidence.append(
                f"TAINT FLOW: {flow.get('source', 'unknown')} -> "
                f"{flow.get('sink', 'unknown')} ({flow.get('path_length', 0)} hops)"
            )

        # Build graph insights summaries for LLM
        attack_vectors_summary = ""
        if graph_insights['attack_vectors']:
            attack_vectors_summary = "\n🎯 ATTACK VECTORS (Graph Analysis):\n"
            attack_vectors_summary += "Entry points that can reach vulnerabilities:\n" + "\n".join([
                f"  {idx+1}. {av['vector']} ({av['hops']} hops) - {av['severity'].upper()}"
                for idx, av in enumerate(graph_insights['attack_vectors'][:5])
            ])

        blast_radius_summary = ""
        if graph_insights['blast_radius']:
            blast_radius_summary = "\n💥 BLAST RADIUS FOR EMERGENCY PATCHES:\n"
            for method, radius in list(graph_insights['blast_radius'].items())[:5]:
                blast_radius_summary += f"  - {method}: {radius['total_affected']} methods affected "
                blast_radius_summary += f"({radius['callers']} callers, {radius['callees']} callees) - {radius['risk'].upper()} RISK\n"

        critical_taint_paths_summary = ""
        if graph_insights['incident_taint_paths']:
            critical_paths = [p for p in graph_insights['incident_taint_paths'] if p.get('critical')]
            if critical_paths:
                critical_taint_paths_summary = f"\n🔬 CRITICAL TAINT PATHS (Graph-based):\n"
                critical_taint_paths_summary += "Real dataflows to critical vulnerabilities:\n" + "\n".join([
                    f"  {idx+1}. {p['source']} → {p['sink']} ({p['hops']} hops) ⚠️ CRITICAL"
                    for idx, p in enumerate(critical_paths[:5])
                ])

        # Generate LLM prompt with incident data and graph analysis
        incident_response = f"""
Query: {state['query']}

🚨 SECURITY INCIDENT RESPONSE - URGENT (WITH GRAPH ANALYSIS) 🚨

📊 VULNERABILITY SUMMARY:
- Critical vulnerabilities: {len(critical)}
- High severity: {len(high)}
- Medium severity: {len(medium)}
- Total attack surface methods: {len(attack_surface)}
- Real taint flow paths found: {len(taint_flows)}
- Attack vectors identified: {len(graph_insights['attack_vectors'])}
- Call paths to vulnerabilities: {len(graph_insights['call_paths_to_vulns'])}
{f"- Vulnerable function analyzed: {vulnerable_function} ({len(vuln_usages)} usages)" if vulnerable_function else ""}

⚠️ CRITICAL VULNERABILITIES (IMMEDIATE ACTION REQUIRED):
{chr(10).join([f"- {v.get('vulnerability_type')}: {v.get('name')} in {v.get('filename')}:{v.get('line_number')}" for v in critical[:5]])}

🔴 HIGH SEVERITY ISSUES:
{chr(10).join([f"- {v.get('vulnerability_type')}: {v.get('name')} (exploitability: {v.get('exploitability')})" for v in high[:5]])}
{attack_vectors_summary}
{critical_taint_paths_summary}

🌊 TAINT FLOW ANALYSIS:
{chr(10).join([f"- {t.get('source')} -> {t.get('sink')} (path length: {t.get('path_length')})" for t in taint_flows[:3]])}

{f"🔧 VULNERABLE FUNCTION USAGES ({vulnerable_function}):" if vulnerable_function and vuln_usages else ""}
{chr(10).join([f"- {u.get('filename')}:{u.get('line_number')} in {u.get('caller_name')}" for u in vuln_usages[:5]]) if vulnerable_function and vuln_usages else ""}
{blast_radius_summary}

📋 EMERGENCY RESPONSE PLAN REQUIRED:
Provide a comprehensive incident response covering:
1. IMMEDIATE hotfix actions (priority order based on attack vectors)
2. Exploit mitigation strategies (address taint paths)
3. Patch deployment sequence (consider blast radius)
4. Testing approach for security fixes
5. Communication plan for stakeholders
6. Long-term remediation recommendations

Use the graph analysis to prioritize fixes based on:
- Attack vector accessibility (fewer hops = higher priority)
- Blast radius (lower impact = safer to patch quickly)
- Critical taint paths (actual exploitable data flows)
"""

        # Get LLM answer
        llm = LLMInterface()
        answer = llm.generate("You are an AI assistant.", incident_response)

        # Update state with graph insights
        state['cpg_results'] = all_findings
        state['methods'] = critical + high[:20]  # Critical and high severity only
        state['answer'] = answer
        state['evidence'] = evidence
        state['metadata'] = {
            'critical_count': len(critical),
            'high_severity_count': len(high),
            'medium_severity_count': len(medium),
            'attack_surface_methods': len(attack_surface),
            'taint_flow_paths': len(taint_flows),
            'vulnerable_function': vulnerable_function,
            'vulnerable_function_usages': len(vuln_usages) if vuln_usages else 0,
            'graph_methods_enabled': True,  # NEW: Graph analysis enabled
            'graph_insights': {
                'attack_vectors_identified': len(graph_insights['attack_vectors']),
                'call_paths_to_vulns': len(graph_insights['call_paths_to_vulns']),
                'incident_taint_paths': len(graph_insights['incident_taint_paths']),
                'critical_taint_paths': len([p for p in graph_insights['incident_taint_paths'] if p.get('critical')]),
                'blast_radius_analyzed': len(graph_insights['blast_radius']),
                'shortest_attack_path': min([av['hops'] for av in graph_insights['attack_vectors']], default=999),
                'max_blast_radius': max([r['total_affected'] for r in graph_insights['blast_radius'].values()], default=0) if graph_insights['blast_radius'] else 0
            }
        }

    except Exception as e:
        logger.error(f"Error in security incident workflow: {e}")
        state['error'] = f"Security incident response failed: {str(e)}"
        state['answer'] = f"Unable to perform security incident analysis: {str(e)}"

    return state


# ============================================================================
# GRAPH BUILDER
# ============================================================================



__all__ = ['security_incident_workflow']
