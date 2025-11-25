"""
Multi-Scenario LangGraph Workflow with Intent-Based Routing

Extends the existing workflow with:
1. Intent classification at entry point
2. Conditional routing to scenario-specific workflows
3. Unified state management across all scenarios

Architecture:
    User Query
        |
        v
    [Intent Classifier] -----> classify_intent()
        |
        |-- onboarding --> [Onboarding Workflow]
        |-- security_audit --> [Security Workflow]
        |-- documentation --> [Documentation Workflow]
        |-- feature_development --> [Feature Dev Workflow]
        |-- ... (10 more scenarios)
        |
        v
    [Final Answer]
"""

import sys
from pathlib import Path
from typing import TypedDict, List, Optional, Dict, Any, Literal
import logging

# LangGraph imports
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Local imports
from src.intent.intent_classifier import IntentClassifier
from src.intent.intent_taxonomy import INTENT_TAXONOMY
from src.services.cpg_query_service import CPGQueryService
# Use new configurable LLM provider (supports GigaChat, local models, etc.)
from src.llm.llm_interface_compat import LLMInterface

# Error handling framework (Phase 1)
from src.workflow.error_handling import (
    AgentResult,
    execute_agent_safely,
    aggregate_partial_results,
    create_error_state,
)

# Security agents (Week 5 enhancement)
from src.security import (
    SecurityScanner,
    DataFlowAnalyzer,
    VulnerabilityReporter,
    RemediationAdvisor,
)

# Refactoring agents (Week 6 enhancement)
from src.refactoring import (
    TechnicalDebtDetector,
    ImpactAnalyzer,
    RefactoringPlanner,
)

# Performance agents (Week 7 enhancement)
from src.performance import (
    PerformanceProfiler,
    ResourceAnalyzer,
    OptimizationAdvisor,
)

# Architecture agents (Week 9 enhancement - Scenario 11)
from src.architecture import (
    DependencyAnalyzer,
    LayerValidator,
    ArchitectureReporter,
)

# Technical Debt agents (Week 11 enhancement - Scenario 12)
from src.tech_debt import (
    DebtCalculator,
    PrioritizationEngine,
    RepaymentPlanner,
)

# Code Review agents (Week 12 enhancement - Scenario 9)
from src.code_review import (
    PRAnalyzer,
    ContextAggregator,
    ReviewReporter,
)

# Compliance agents (Week 13 enhancement - Scenario 8)
from src.compliance import (
    LicenseDetector,
    ComplianceValidator,
    StandardsChecker,
)

# Security Incident agents (Week 13 enhancement - Scenario 14)
from src.security_incident import (
    CVESearcher,
    BlastRadiusAnalyzer,
    RemediationPlanner,
)

# Cross-Repository Analysis agents (Week 14 enhancement - Scenario 10)
from src.cross_repo import (
    RepositoryIndexer,
    CrossRepoAnalyzer,
    DependencyMapper,
)

# Large-Scale Refactoring agents (Week 16-17 enhancement - Scenario 13)
from src.refactoring import (
    TechnicalDebtDetector,
    ImpactAnalyzer,
    RefactoringPlanner,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# STATE DEFINITION
# ============================================================================

class MultiScenarioState(TypedDict):
    """
    Shared state across all scenario workflows.

    This state is passed through the entire graph and accumulates
    information as it flows through nodes.
    """
    # Input
    query: str                          # Original user question
    context: Optional[Dict[str, Any]]   # Optional context (file, subsystem, etc.)

    # Intent Classification
    intent: Optional[str]               # Classified intent (e.g., "security_audit")
    scenario_id: Optional[str]          # Scenario ID (e.g., "scenario_2")
    confidence: Optional[float]         # Classification confidence (0.0-1.0)
    classification_method: Optional[str] # "keyword" or "llm"

    # CPG Data (populated by scenario workflows)
    cpg_results: Optional[List[Dict]]   # Results from CPG queries
    subsystems: Optional[List[str]]     # Relevant subsystems
    methods: Optional[List[Dict]]       # Method metadata
    call_graph: Optional[Any]           # NetworkX graph (if needed)

    # Final Output
    answer: Optional[str]               # Natural language answer
    evidence: Optional[List[str]]       # Supporting evidence (CPG facts)
    metadata: Optional[Dict[str, Any]]  # Scenario-specific metadata

    # Error Handling
    error: Optional[str]                # Error message if any
    retry_count: int                    # Number of retries (default: 0)


# ============================================================================
# INTENT CLASSIFICATION NODE
# ============================================================================

def classify_intent_node(state: MultiScenarioState) -> MultiScenarioState:
    """
    Entry point: Classify user query into one of 14 scenarios.

    Updates state with:
    - intent: Intent key
    - scenario_id: Scenario ID
    - confidence: Classification confidence
    - classification_method: How it was classified
    """
    logger.info(f"Classifying query: {state['query'][:100]}...")

    try:
        # Initialize classifier (with LLM client if available)
        llm_client = LLMInterface()  # Use LLMxCPG-Q model (default)
        classifier = IntentClassifier(llm_client=llm_client)

        # Classify
        result = classifier.classify(
            query=state['query'],
            context=state.get('context')
        )

        # Update state
        state['intent'] = result['intent']
        state['scenario_id'] = result['scenario_id']
        state['confidence'] = result['confidence']
        state['classification_method'] = result['method']

        logger.info(
            f"Intent: {result['intent']} "
            f"(confidence: {result['confidence']:.2f}, "
            f"method: {result['method']})"
        )

    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        # Fallback to onboarding
        state['intent'] = 'onboarding'
        state['scenario_id'] = 'scenario_1'
        state['confidence'] = 0.3
        state['classification_method'] = 'error_fallback'
        state['error'] = str(e)

    return state


# ============================================================================
# ROUTER NODE
# ============================================================================

def route_by_intent(state: MultiScenarioState) -> str:
    """
    Conditional edge function that routes to scenario-specific workflows.

    Returns:
        Next node name based on intent
    """
    intent = state.get('intent', 'onboarding')

    # Map intents to workflow nodes
    routing_map = {
        'onboarding': 'onboarding_workflow',
        'security_audit': 'security_workflow',
        'documentation': 'documentation_workflow',
        'feature_development': 'feature_dev_workflow',
        'refactoring': 'refactoring_workflow',
        'performance': 'performance_workflow',
        'test_coverage': 'test_coverage_workflow',
        'compliance': 'compliance_workflow',
        'code_review': 'code_review_workflow',
        'cross_repo_impact': 'cross_repo_workflow',
        'architecture_violations': 'architecture_workflow',
        'tech_debt': 'tech_debt_workflow',
        'mass_refactoring': 'mass_refactoring_workflow',
        'security_incident': 'security_incident_workflow'
    }

    next_node = routing_map.get(intent, 'onboarding_workflow')
    logger.info(f"Routing to: {next_node}")

    return next_node


# ============================================================================
# SCENARIO WORKFLOWS (Week 1 - Scenarios 1, 3, 4)
# ============================================================================

def onboarding_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    Scenario 1: Codebase Onboarding with Graph Analysis

    Provides architectural overview by:
    1. Querying subsystems from CPG
    2. Getting method counts per subsystem
    3. CallGraphAnalyzer - Graph Method #2: Entry points and architectural patterns
    4. Generating high-level overview with LLM and graph insights
    """
    logger.info("Executing onboarding workflow with GRAPH METHODS")

    # Track graph insights
    graph_insights = {
        'entry_points': [],
        'key_methods': [],
        'subsystem_dependencies': []
    }

    try:
        # Query CPG for subsystems
        with CPGQueryService() as cpg:
            subsystems = cpg.get_subsystems()
            stats = cpg.get_database_stats()

            # GRAPH METHOD #2: CallGraphAnalyzer - Architectural overview
            try:
                logger.info("Running CallGraphAnalyzer for architectural overview...")
                from src.analysis import CallGraphAnalyzer
                call_analyzer = CallGraphAnalyzer(cpg)

                # 1. Find entry points (methods with no callers or called by main)
                entry_point_candidates = ['main', 'PostgresMain', 'PostmasterMain',
                                         'exec_simple_query', 'standard_ProcessUtility',
                                         'PortalRun', 'ExecutorRun']

                for entry_name in entry_point_candidates:
                    # Get all methods this entry point calls
                    # Note: find_all_callees returns List[str] (method names), not dicts
                    callees = call_analyzer.find_all_callees(entry_name, max_depth=2)
                    if callees:
                        graph_insights['entry_points'].append({
                            'name': entry_name,
                            'direct_callees': len(callees),
                            'total_callees': len(callees),
                            'top_callees': callees[:5]  # Already strings
                        })

                logger.info(f"Found {len(graph_insights['entry_points'])} entry points")

                # 2. Identify key architectural methods (high impact = important)
                # Sample methods from different subsystems
                sample_methods = []
                for subsys in subsystems[:5]:  # Top 5 subsystems
                    methods = cpg.get_methods_by_subsystem(subsys['name'], limit=3)
                    sample_methods.extend(methods)

                for method in sample_methods[:15]:  # Analyze top 15
                    method_name = method.get('name', '')
                    if not method_name:
                        continue

                    impact = call_analyzer.analyze_impact(method_name)
                    if impact and impact.impact_score > 0.5:  # Only high-impact methods
                        graph_insights['key_methods'].append({
                            'name': method_name,
                            'subsystem': method.get('subsystem', 'unknown'),
                            'impact_score': impact.impact_score,
                            'upstream_count': impact.upstream_count,
                            'downstream_count': impact.downstream_count,
                            'is_entry_point': impact.is_entry_point
                        })

                # Sort by impact score
                graph_insights['key_methods'].sort(key=lambda x: x['impact_score'], reverse=True)
                logger.info(f"Identified {len(graph_insights['key_methods'])} key architectural methods")

                # 3. Detect subsystem dependencies via call graph
                # For top subsystems, find what other subsystems they call
                for subsys in subsystems[:3]:  # Top 3 subsystems
                    subsys_methods = cpg.get_methods_by_subsystem(subsys['name'], limit=5)
                    called_subsystems = set()

                    for method in subsys_methods:
                        callees = call_analyzer.find_all_callees(method.get('name', ''), max_depth=1)
                        for callee in callees[:10]:  # Sample callees
                            # Try to determine callee's subsystem (simplified)
                            called_subsystems.add('other')  # Placeholder

                    if called_subsystems:
                        graph_insights['subsystem_dependencies'].append({
                            'subsystem': subsys['name'],
                            'calls_count': len(called_subsystems)
                        })

                logger.info(f"Analyzed {len(graph_insights['subsystem_dependencies'])} subsystem dependencies")

            except Exception as e:
                logger.error(f"CallGraphAnalyzer failed: {e}", exc_info=True)
                # Continue without graph insights

        # Format evidence with graph insights
        evidence = [
            f"Total methods: {stats['method_count']:,}",
            f"Total subsystems: {len(subsystems)}",
            f"Entry points identified: {len(graph_insights['entry_points'])}",
            f"Key architectural methods: {len(graph_insights['key_methods'])}",
            f"Top subsystems: {', '.join([s['name'] for s in subsystems[:5]])}"
        ]

        # Generate overview using LLM with graph insights
        llm = LLMInterface()

        # Build graph insights summaries
        entry_points_summary = ""
        if graph_insights['entry_points']:
            entry_points_summary = "\n🚪 ENTRY POINTS (Graph Analysis):\n"
            entry_points_summary += "Key entry points into the codebase:\n" + "\n".join([
                f"  {idx+1}. {ep['name']}: calls {ep['direct_callees']} methods directly ({ep['total_callees']} total)\n     Top callees: {', '.join(ep['top_callees'][:3])}"
                for idx, ep in enumerate(graph_insights['entry_points'][:5])
            ])

        key_methods_summary = ""
        if graph_insights['key_methods']:
            key_methods_summary = "\n🔑 KEY ARCHITECTURAL METHODS (Graph Analysis):\n"
            key_methods_summary += "Most important methods by impact:\n" + "\n".join([
                f"  {idx+1}. {km['name']} ({km['subsystem']}): Impact {km['impact_score']:.2f}\n     {km['upstream_count']} callers → {km['downstream_count']} callees"
                for idx, km in enumerate(graph_insights['key_methods'][:5])
            ])

        prompt = f"""You are a PostgreSQL expert providing codebase onboarding.

User Question: {state['query']}

CODEBASE OVERVIEW WITH GRAPH ANALYSIS:

📊 STATISTICS:
- Total methods: {stats['method_count']:,}
- Total subsystems: {len(subsystems)}
- Entry points: {len(graph_insights['entry_points'])}
- Key architectural methods: {len(graph_insights['key_methods'])}

📁 SUBSYSTEM BREAKDOWN:
{chr(10).join([f"  - {s['name']}: {s['method_count']:,} methods in {s['file_count']} files" for s in subsystems[:10]])}
{entry_points_summary}
{key_methods_summary}

Provide a concise, beginner-friendly overview that answers the user's question.
Focus on:
1. Overall architecture and design patterns
2. How code execution flows through entry points
3. Key methods that are central to the system
4. Major subsystems and their responsibilities

Use the graph analysis to help explain how different parts connect.
"""

        answer = llm.generate("You are an AI assistant.", prompt)

        # Update state with graph insights
        state['cpg_results'] = subsystems
        state['subsystems'] = [s['name'] for s in subsystems]
        state['answer'] = answer
        state['evidence'] = evidence
        state['metadata'] = {
            'subsystem_count': len(subsystems),
            'method_count': stats['method_count'],
            'graph_methods_enabled': True,  # NEW: Graph analysis enabled
            'graph_insights': {
                'entry_points_found': len(graph_insights['entry_points']),
                'key_methods_identified': len(graph_insights['key_methods']),
                'subsystem_dependencies': len(graph_insights['subsystem_dependencies']),
                'top_entry_point': graph_insights['entry_points'][0]['name'] if graph_insights['entry_points'] else None,
                'highest_impact_method': graph_insights['key_methods'][0]['name'] if graph_insights['key_methods'] else None,
                'max_impact_score': graph_insights['key_methods'][0]['impact_score'] if graph_insights['key_methods'] else 0.0
            }
        }

    except Exception as e:
        logger.error(f"Onboarding workflow failed: {e}")
        state['error'] = str(e)
        state['answer'] = f"Error during onboarding: {e}"

    return state


def documentation_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    Scenario 3: Documentation Generation with Graph Analysis

    Generates documentation by:
    1. Extracting relevant methods from CPG
    2. Getting function-purpose tags
    3. CallGraphAnalyzer - Graph Method #2: Identify usage patterns and key methods
    4. Formatting as API documentation with call graph context

    Returns enhanced API documentation with usage patterns and impact analysis.
    """
    logger.info("Executing documentation workflow with GRAPH METHODS")

    # Track graph insights
    graph_insights = {
        'method_usage': {},
        'key_methods': [],
        'call_examples': []
    }

    try:
        # Extract target from query (e.g., "ExecInitNode", "planner")
        # For demo, we'll search by semantic purpose
        query_lower = state['query'].lower()

        with CPGQueryService() as cpg:
            # Search by function purpose if query contains keywords
            if any(kw in query_lower for kw in ['execute', 'plan', 'parse', 'optimize']):
                # Extract keyword
                keyword = None
                for kw in ['execute', 'plan', 'parse', 'optimize']:
                    if kw in query_lower:
                        keyword = kw
                        break

                methods = cpg.search_by_function_purpose(keyword, limit=20)
            else:
                # Default: get methods from first subsystem
                subsystems = cpg.get_subsystems()
                if subsystems:
                    methods = cpg.get_methods_by_subsystem(subsystems[0]['name'], limit=20)
                else:
                    methods = []

            # GRAPH METHOD #2: CallGraphAnalyzer - Identify usage patterns for documentation
            try:
                logger.info("Running CallGraphAnalyzer for usage pattern analysis...")
                from src.analysis import CallGraphAnalyzer
                call_analyzer = CallGraphAnalyzer(cpg)

                # Analyze each method to enhance documentation
                for method in methods[:15]:  # Top 15 methods
                    method_name = method.get('name', '')
                    if not method_name:
                        continue

                    # Find callers (who uses this method?)
                    callers = call_analyzer.find_all_callers(method_name, max_depth=2)
                    direct_callers = [c for c in callers if c.get('depth', 1) == 1]

                    # Find callees (what does this method call?)
                    callees = call_analyzer.find_all_callees(method_name, max_depth=1)

                    # Compute impact (how important is this method?)
                    impact = call_analyzer.analyze_impact(method_name)

                    # Track usage information
                    graph_insights['method_usage'][method_name] = {
                        'callers': len(callers),
                        'direct_callers': [c.get('caller_name', 'unknown') for c in direct_callers[:5]],
                        'callees': [c.get('callee_name', 'unknown') for c in callees[:5]],
                        'impact_score': impact.impact_score if impact else 0.0,
                        'is_public_api': len(callers) > 5,  # Methods with many callers = public API
                        'is_entry_point': impact.is_entry_point if impact else False
                    }

                    # Identify key methods (high impact = important to document thoroughly)
                    if impact and impact.impact_score > 0.6:
                        graph_insights['key_methods'].append({
                            'method': method_name,
                            'filename': method.get('filename', 'unknown'),
                            'impact_score': impact.impact_score,
                            'caller_count': len(callers),
                            'priority': 'high' if impact.impact_score > 0.8 else 'medium'
                        })

                    # Create call examples (for usage documentation)
                    if direct_callers:
                        graph_insights['call_examples'].append({
                            'method': method_name,
                            'example_callers': [c.get('caller_name', 'unknown') for c in direct_callers[:3]],
                            'usage_context': f"Called by {len(direct_callers)} methods"
                        })

                # Sort key methods by impact
                graph_insights['key_methods'].sort(key=lambda x: x['impact_score'], reverse=True)

                logger.info(f"CallGraphAnalyzer: Analyzed {len(graph_insights['method_usage'])} methods, "
                           f"identified {len(graph_insights['key_methods'])} key methods")

            except Exception as e:
                logger.error(f"CallGraphAnalyzer failed: {e}", exc_info=True)
                # Continue without graph insights

        # Generate documentation
        llm = LLMInterface()

        # Build enhanced doc prompt with graph insights
        usage_info = ""
        if graph_insights['method_usage']:
            usage_info = "\n\n📊 METHOD USAGE PATTERNS (Graph Analysis):\n"
            for method_name, usage in list(graph_insights['method_usage'].items())[:10]:
                usage_info += f"\n{method_name}:\n"
                usage_info += f"  - Callers: {usage['callers']} (Public API: {'Yes' if usage['is_public_api'] else 'No'})\n"
                if usage['direct_callers']:
                    usage_info += f"  - Example callers: {', '.join(usage['direct_callers'][:3])}\n"
                if usage['callees']:
                    usage_info += f"  - Calls: {', '.join(usage['callees'][:3])}\n"
                usage_info += f"  - Impact score: {usage['impact_score']:.2f}\n"

        key_methods_info = ""
        if graph_insights['key_methods']:
            key_methods_info = "\n\n🔑 KEY METHODS (High Priority for Documentation):\n"
            for km in graph_insights['key_methods'][:5]:
                key_methods_info += f"  - {km['method']} ({km['filename']}): "
                key_methods_info += f"Impact {km['impact_score']:.2f}, {km['caller_count']} callers - {km['priority'].upper()} priority\n"

        doc_prompt = f"""Generate API documentation for the following methods:

User Request: {state['query']}

Methods:
{chr(10).join([f"- {m['name']} ({m.get('filename', 'unknown')}:{m.get('line_number', '?')})" for m in methods[:10]])}
{usage_info}
{key_methods_info}

For each method, provide:
1. Brief description of what it does
2. Key parameters (if available)
3. Return value
4. Usage example (using the call patterns shown above if available)
5. Importance level (based on impact score and caller count)

Format as clear, concise API documentation with usage patterns and importance indicators.
"""

        answer = llm.generate("You are an AI assistant.", doc_prompt)

        # Enhanced evidence list
        evidence = [
            f"Documented {len(methods)} methods",
            f"Methods analyzed for usage: {len(graph_insights['method_usage'])}",
            f"Key methods identified: {len(graph_insights['key_methods'])}",
            f"Public API methods: {len([m for m in graph_insights['method_usage'].values() if m['is_public_api']])}"
        ]

        state['methods'] = methods
        state['answer'] = answer
        state['evidence'] = evidence
        state['metadata'] = {
            'method_count': len(methods),
            'graph_methods_enabled': True,
            'graph_insights': {
                'methods_analyzed': len(graph_insights['method_usage']),
                'key_methods': len(graph_insights['key_methods']),
                'high_priority_methods': len([km for km in graph_insights['key_methods'] if km['priority'] == 'high']),
                'public_api_methods': len([m for m in graph_insights['method_usage'].values() if m['is_public_api']]),
                'entry_points': len([m for m in graph_insights['method_usage'].values() if m['is_entry_point']]),
                'call_examples': len(graph_insights['call_examples'])
            }
        }

    except Exception as e:
        logger.error(f"Documentation workflow failed: {e}")
        state['error'] = str(e)
        state['answer'] = f"Error generating documentation: {e}"

    return state


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
                            'upstream_count': impact.upstream_count,
                            'downstream_count': impact.downstream_count,
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

        dev_prompt = f"""You are a PostgreSQL development expert.

User Question: {state['query']}

FEATURE DEVELOPMENT GUIDANCE WITH GRAPH ANALYSIS:

📁 TARGET SUBSYSTEM: {target_subsystem or 'unknown'}
- Methods in subsystem: {len(methods)}
- Integration points identified: {len(graph_insights['integration_points'])}

📋 SAMPLE METHODS:
{chr(10).join([f"- {m['name']} in {m.get('filename', 'unknown')}" for m in methods[:15]])}
{integration_points_summary}
{impact_analysis_summary}
{betweenness_summary}

Provide specific guidance on:
1. WHERE to add the new feature (which files/functions - use integration points from graph analysis)
2. WHICH existing methods to extend or call (refer to integration points above, especially high-centrality methods)
3. IMPACT of modification (use impact analysis to assess risk)
4. CODE PATTERNS to follow (based on existing subsystem methods)
5. TESTING considerations (focus on methods with high impact scores)
6. ARCHITECTURAL VISIBILITY (consider betweenness centrality for features affecting multiple subsystems)

Be specific and reference actual methods/files from the codebase and graph analysis.
Use the integration points and architectural centrality analysis to suggest the safest and most effective hooks for the new feature.
High-centrality methods are ideal for cross-cutting features, while low-impact methods are safer for isolated changes.
"""

        answer = llm.generate("You are an AI assistant.", dev_prompt)

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

def security_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    Scenario 2: Enhanced Security Audit with Graph Analysis (Week 5 + Graph Methods)

    Uses specialized security agents + graph methods for comprehensive vulnerability analysis:
    1. SecurityScanner - Scan CPG using security patterns
    2. CallGraphAnalyzer - Graph Method #2: Call chain context for vulnerabilities
    3. DataFlowTracer - Graph Method #3: Real taint flow analysis (source-to-sink paths)
    4. VulnerabilityReporter - Generate structured vulnerability report
    5. RemediationAdvisor - Provide remediation guidance

    Returns detailed security analysis with pattern-based detection,
    real dataflow tracing via graph traversal, call chain context, and actionable remediation advice.
    """
    logger.info("Executing ENHANCED security audit workflow with GRAPH METHODS")

    # Initialize error tracking
    errors = []
    findings = []
    data_flows = []
    vuln_report = None
    remediation_plan = []
    graph_insights = {
        'call_chains': {},
        'taint_paths': [],
        'impact_scores': {}
    }
    critical_methods_with_impact = []  # Initialize early to avoid UnboundLocalError

    try:
        with CPGQueryService() as cpg:
            # AGENT 1: SecurityScanner - Pattern-based vulnerability detection
            try:
                logger.info("Running SecurityScanner...")
                scanner = SecurityScanner(cpg)
                findings = scanner.scan_all_patterns(limit_per_pattern=20)
                logger.info(f"SecurityScanner found {len(findings)} vulnerabilities")
            except Exception as e:
                logger.error(f"SecurityScanner failed: {e}", exc_info=True)
                errors.append({
                    'agent': 'SecurityScanner',
                    'error': str(e),
                    'severity': 'high'
                })

            # GRAPH METHOD #2: CallGraphAnalyzer - Add call chain context to vulnerabilities
            try:
                logger.info("Running CallGraphAnalyzer for call chain context...")
                from src.analysis import CallGraphAnalyzer
                call_analyzer = CallGraphAnalyzer(cpg)

                # For each finding, get call chain context and impact
                for finding in findings[:20]:  # Top 20 for performance
                    method_name = finding.method_name

                    # Get callers (who calls this vulnerable method?)
                    callers = call_analyzer.find_all_callers(method_name, max_depth=3)
                    graph_insights['call_chains'][finding.finding_id] = {
                        'method': method_name,
                        'direct_callers': len([c for c in callers if c.get('depth', 1) == 1]),
                        'total_callers': len(callers),
                        'caller_names': [c.get('caller_name', 'unknown') for c in callers[:5]]
                    }

                    # Get impact analysis (how critical is this method?)
                    impact = call_analyzer.analyze_impact(method_name)
                    if impact:
                        graph_insights['impact_scores'][finding.finding_id] = {
                            'impact_score': impact.impact_score,
                            'upstream_methods': impact.upstream_count,
                            'downstream_methods': impact.downstream_count,
                            'is_entry_point': impact.is_entry_point,
                            'is_critical': impact.impact_score > 0.7
                        }

                        # Add to finding metadata
                        finding.metadata['call_chain'] = graph_insights['call_chains'][finding.finding_id]
                        finding.metadata['impact_analysis'] = graph_insights['impact_scores'][finding.finding_id]

                logger.info(f"CallGraphAnalyzer added context to {len(graph_insights['call_chains'])} findings")

            except Exception as e:
                logger.error(f"CallGraphAnalyzer failed: {e}", exc_info=True)
                errors.append({
                    'agent': 'CallGraphAnalyzer',
                    'error': str(e),
                    'severity': 'medium'
                })

            # GRAPH METHOD #3: DataFlowTracer - Real taint flow analysis
            try:
                logger.info("Running DataFlowTracer for real taint paths...")
                from src.analysis import DataFlowTracer
                flow_tracer = DataFlowTracer(cpg)

                # Define security-relevant sources and sinks
                taint_sources = [
                    # User input
                    'readLine', 'recv', 'recvfrom', 'getenv', 'read', 'fgets',
                    # Network input
                    'socket_read', 'pq_getbyte', 'pq_getmessage',
                    # PostgreSQL-specific input
                    'pg_parse_query', 'raw_parser', 'pg_get_userbyid'
                ]

                taint_sinks = [
                    # SQL execution
                    'exec_simple_query', 'SPI_execute', 'SPI_exec', 'executeSQL',
                    # Command execution
                    'system', 'popen', 'exec', 'execl', 'execv',
                    # File operations
                    'fopen', 'open', 'write', 'fwrite', 'unlink',
                    # String operations (buffer overflow)
                    'strcpy', 'strcat', 'sprintf'
                ]

                # Find real taint paths using graph traversal
                real_taint_paths = flow_tracer.find_taint_paths(
                    source_functions=taint_sources,
                    sink_functions=taint_sinks,
                    max_depth=10
                )

                # Convert to DataFlowPath format for compatibility
                for path in real_taint_paths:
                    data_flow = DataFlowPath(
                        path_id=path.path_id,
                        source_method=path.source_location.get('method_name', 'unknown'),
                        source_file=path.source_location.get('filename', 'unknown'),
                        source_line=path.source_location.get('line_number', 0),
                        sink_method=path.sink_location.get('method_name', 'unknown'),
                        sink_file=path.sink_location.get('filename', 'unknown'),
                        sink_line=path.sink_location.get('line_number', 0),
                        path_length=path.path_length,
                        intermediate_nodes=path.intermediate_nodes,
                        taint_type='data_flow',  # Real data flow, not synthetic
                        sanitized=False  # Assume unsanitized unless we detect sanitizers
                    )
                    data_flows.append(data_flow)
                    graph_insights['taint_paths'].append({
                        'path_id': path.path_id,
                        'source': path.source_location.get('method_name'),
                        'sink': path.sink_location.get('method_name'),
                        'length': path.path_length,
                        'is_inter_procedural': path.is_inter_procedural
                    })

                logger.info(f"DataFlowTracer found {len(real_taint_paths)} real taint paths")

            except Exception as e:
                logger.error(f"DataFlowTracer failed: {e}", exc_info=True)
                errors.append({
                    'agent': 'DataFlowTracer',
                    'error': str(e),
                    'severity': 'medium'
                })

            # AGENT 2 (LEGACY): Old DataFlowAnalyzer - Fallback only if graph method didn't produce results
            if len(data_flows) == 0:
                try:
                    logger.info("Running legacy DataFlowAnalyzer as fallback...")
                    analyzer = DataFlowAnalyzer(cpg)
                    legacy_flows = analyzer.trace_taint_flows(limit=20)
                    data_flows.extend(legacy_flows)
                    logger.info(f"Legacy DataFlowAnalyzer traced {len(legacy_flows)} taint flows")
                except Exception as e:
                    logger.error(f"Legacy DataFlowAnalyzer failed: {e}", exc_info=True)
                    errors.append({
                        'agent': 'DataFlowAnalyzer (legacy)',
                        'error': str(e),
                        'severity': 'low'  # Lower severity since it's just a fallback
                    })
            else:
                logger.info(f"Skipping legacy DataFlowAnalyzer - using {len(data_flows)} graph-based taint paths")

            # AGENT 3: VulnerabilityReporter - Generate structured report
            try:
                logger.info("Running VulnerabilityReporter...")
                reporter = VulnerabilityReporter()
                vuln_report = reporter.generate_report(findings, data_flows)
                logger.info(f"VulnerabilityReporter generated report {vuln_report.report_id}")
            except Exception as e:
                logger.error(f"VulnerabilityReporter failed: {e}", exc_info=True)
                errors.append({
                    'agent': 'VulnerabilityReporter',
                    'error': str(e),
                    'severity': 'medium'
                })

            # AGENT 4: RemediationAdvisor - Get top remediation advice
            try:
                logger.info("Running RemediationAdvisor...")
                advisor = RemediationAdvisor()
                # Get advice for top 10 critical/high severity findings
                top_findings = [f for f in findings if f.severity in ['critical', 'high']][:10]
                if top_findings:
                    remediation_plan = advisor.get_bulk_remediation_plan(top_findings)
                    logger.info(f"RemediationAdvisor provided {len(remediation_plan)} remediation items")
                else:
                    logger.info("No critical/high severity findings for remediation")
            except Exception as e:
                logger.error(f"RemediationAdvisor failed: {e}", exc_info=True)
                errors.append({
                    'agent': 'RemediationAdvisor',
                    'error': str(e),
                    'severity': 'low'
                })

        # Build evidence list (defensive - handle missing report)
        if vuln_report:
            evidence = [
                f"Total vulnerabilities found: {vuln_report.total_findings}",
                f"Critical: {vuln_report.critical_count}",
                f"High: {vuln_report.high_count}",
                f"Medium: {vuln_report.medium_count}",
                f"Low: {vuln_report.low_count}",
                f"Taint flow paths: {len(data_flows)}",
                f"Real graph-based taint paths: {len(graph_insights['taint_paths'])}",
                f"Call chain contexts added: {len(graph_insights['call_chains'])}",
                f"Impact scores computed: {len(graph_insights['impact_scores'])}",
                f"High-impact methods: {len([m for m in critical_methods_with_impact if m['is_critical']])}",
                f"Remediation items: {len(remediation_plan)}"
            ]
        else:
            evidence = [
                f"Raw findings: {len(findings)}",
                f"Taint flow paths: {len(data_flows)}",
                f"Graph-based taint paths: {len(graph_insights['taint_paths'])}",
                f"Call chain analysis: {len(graph_insights['call_chains'])} methods",
                f"Remediation items: {len(remediation_plan)}",
                f"WARNING: Vulnerability report generation failed"
            ]

        # Generate enhanced LLM prompt with rich security data
        llm = LLMInterface()

        # Build detailed findings summary (defensive)
        if vuln_report:
            findings_by_category = vuln_report.findings_by_category
            category_summary = "\n".join([
                f"- {cat}: {count} issues"
                for cat, count in sorted(findings_by_category.items(), key=lambda x: -x[1])[:5]
            ])
        else:
            findings_by_category = {}
            category_summary = "Report generation failed - showing raw findings count"

        # Top remediation steps
        top_remediation = "\n".join([
            f"{idx}. {advice.finding_id} (priority {advice.priority}): {advice.remediation_steps[0] if advice.remediation_steps else 'See pattern guidance'}"
            for idx, advice in enumerate(remediation_plan[:5], 1)
        ]) if remediation_plan else "No remediation plan available"

        # Critical findings detail
        critical_findings = [f for f in findings if f.severity == 'critical'][:5]
        critical_findings_detail = "\n".join([
            f"- [{f.severity.upper()}] {f.pattern_name} in {f.filename}:{f.line_number}\n  Method: {f.method_name}\n  CWE: {', '.join(f.cwe_ids)}"
            for f in critical_findings
        ]) if critical_findings else "None found"

        # Unsafe data flows
        unsafe_flows = [df for df in data_flows if not df.sanitized] if data_flows else []
        unsafe_flow_summary = "\n".join([
            f"- {df.taint_type}: {df.source_method} -> {df.sink_method} (UNSANITIZED)"
            for df in unsafe_flows[:5]
        ]) if unsafe_flows else "All flows appear sanitized"

        # Graph analysis insights summary
        critical_methods_with_impact = []
        for finding in critical_findings[:10]:
            if finding.finding_id in graph_insights['impact_scores']:
                impact_info = graph_insights['impact_scores'][finding.finding_id]
                call_chain_info = graph_insights['call_chains'].get(finding.finding_id, {})
                critical_methods_with_impact.append({
                    'method': finding.method_name,
                    'pattern': finding.pattern_name,
                    'impact_score': impact_info['impact_score'],
                    'is_critical': impact_info['is_critical'],
                    'total_callers': call_chain_info.get('total_callers', 0)
                })

        graph_insights_summary = ""
        if critical_methods_with_impact:
            graph_insights_summary = "\n📈 GRAPH ANALYSIS - CRITICAL METHOD IMPACT:\n" + "\n".join([
                f"- {m['method']}: Impact {m['impact_score']:.2f} ({m['total_callers']} callers) - {m['pattern']}"
                for m in critical_methods_with_impact[:5]
            ])

        real_taint_paths_summary = ""
        if graph_insights['taint_paths']:
            real_taint_paths_summary = f"\n🔬 REAL TAINT PATHS (Graph-based):\n"
            real_taint_paths_summary += f"- Total paths found: {len(graph_insights['taint_paths'])}\n"
            real_taint_paths_summary += f"- Inter-procedural flows: {len([p for p in graph_insights['taint_paths'] if p.get('is_inter_procedural')])}\n"
            real_taint_paths_summary += "Top paths:\n" + "\n".join([
                f"  {idx+1}. {p['source']} → {p['sink']} (length: {p['length']})"
                for idx, p in enumerate(graph_insights['taint_paths'][:5])
            ])

        # Handle errors in prompt
        error_section = ""
        if errors:
            error_section = f"\n⚠️ WORKFLOW ERRORS:\n" + "\n".join([
                f"- {err['agent']}: {err['error'][:100]}"
                for err in errors
            ]) + "\n"

        security_prompt = f"""You are a security expert performing an advanced security audit of PostgreSQL.

User Question: {state['query']}

ENHANCED SECURITY ANALYSIS WITH GRAPH METHODS:

📊 VULNERABILITY SUMMARY:
- Total Findings: {vuln_report.total_findings if vuln_report else len(findings)}
- Critical: {vuln_report.critical_count if vuln_report else len(critical_findings)} ⚠️
- High: {vuln_report.high_count if vuln_report else len([f for f in findings if f.severity == 'high'])}
- Medium: {vuln_report.medium_count if vuln_report else len([f for f in findings if f.severity == 'medium'])}
- Low: {vuln_report.low_count if vuln_report else len([f for f in findings if f.severity == 'low'])}

📁 FINDINGS BY CATEGORY:
{category_summary}

🔍 CRITICAL VULNERABILITIES:
{critical_findings_detail}

🌊 UNSAFE DATA FLOWS (Top 5):
{unsafe_flow_summary}
{graph_insights_summary}
{real_taint_paths_summary}

🔧 TOP REMEDIATION PRIORITIES:
{top_remediation}
{error_section}
📝 EXECUTIVE SUMMARY:
{vuln_report.summary if vuln_report else f"Security scan found {len(findings)} potential vulnerabilities across the codebase."}

RECOMMENDATIONS:
{chr(10).join([f"{i+1}. {rec}" for i, rec in enumerate(vuln_report.recommendations[:5])]) if vuln_report else "Generate recommendations based on findings"}

Based on this analysis, provide:
1. Assessment of overall security posture
2. Immediate action items for critical issues
3. Medium-term improvements for high/medium issues
4. Long-term security hardening recommendations
5. Specific guidance relevant to the user's question

Format as a professional security audit report.
"""

        answer = llm.generate("You are an AI assistant.", security_prompt)

        # Update state with comprehensive results
        top_findings = [f for f in findings if f.severity in ['critical', 'high']][:10]
        state['cpg_results'] = [f.metadata for f in findings]  # Raw CPG data
        state['methods'] = [f.metadata for f in top_findings]  # Critical/High findings
        state['answer'] = answer
        state['evidence'] = evidence
        state['metadata'] = {
            'report_id': vuln_report.report_id if vuln_report else 'error',
            'timestamp': vuln_report.timestamp if vuln_report else '',
            'total_findings': vuln_report.total_findings if vuln_report else len(findings),
            'critical_count': vuln_report.critical_count if vuln_report else len(critical_findings),
            'high_count': vuln_report.high_count if vuln_report else len([f for f in findings if f.severity == 'high']),
            'medium_count': vuln_report.medium_count if vuln_report else len([f for f in findings if f.severity == 'medium']),
            'low_count': vuln_report.low_count if vuln_report else len([f for f in findings if f.severity == 'low']),
            'findings_by_category': findings_by_category,
            'taint_flows': len(data_flows),
            'unsafe_flows': len(unsafe_flows),
            'errors': errors,
            'remediation_items': len(remediation_plan),
            'enhanced_mode': True,  # Flag indicating enhanced workflow
            'graph_methods_enabled': True,  # NEW: Graph analysis enabled
            'graph_insights': {
                'call_chains_analyzed': len(graph_insights['call_chains']),
                'impact_scores_computed': len(graph_insights['impact_scores']),
                'real_taint_paths': len(graph_insights['taint_paths']),
                'high_impact_methods': len([m for m in critical_methods_with_impact if m['is_critical']]),
                'inter_procedural_flows': len([p for p in graph_insights['taint_paths'] if p.get('is_inter_procedural')])
            }
        }

    except Exception as e:
        logger.error(f"Enhanced security workflow failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        state['error'] = str(e)
        state['answer'] = f"Error during enhanced security audit: {e}"

    return state


def refactoring_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    Scenario 5: Enhanced Refactoring Assistance with Graph Analysis (Week 6 + Graph Methods)

    Uses specialized refactoring agents + graph methods for comprehensive code quality analysis:
    1. TechnicalDebtDetector - Detect code smells using pattern library
    2. CallGraphAnalyzer - Graph Method #2: Impact analysis for refactoring decisions
    3. ImpactAnalyzer - Analyze change impact and dependencies
    4. RefactoringPlanner - Create prioritized refactoring plans

    Returns detailed refactoring analysis with code smell detection, call graph impact analysis,
    and actionable refactoring tasks.
    """
    logger.info("Executing ENHANCED refactoring workflow with GRAPH METHODS")

    # Track graph insights
    graph_insights = {
        'refactoring_impacts': {},
        'dependency_chains': [],
        'blast_radius': {}
    }

    try:
        with CPGQueryService() as cpg:
            # AGENT 1: TechnicalDebtDetector - Pattern-based smell detection
            logger.info("Running TechnicalDebtDetector...")
            detector = TechnicalDebtDetector(cpg)
            findings = detector.detect_all_smells(limit_per_pattern=15)
            logger.info(f"TechnicalDebtDetector found {len(findings)} code smells")

            # Calculate debt metrics
            debt_metrics = detector.calculate_debt_metrics(findings)
            logger.info(f"Technical debt: {debt_metrics['total_effort_hours']:.1f} hours")

            # GRAPH METHOD #2: CallGraphAnalyzer - Refactoring impact analysis
            try:
                logger.info("Running CallGraphAnalyzer for refactoring impact...")
                from src.analysis import CallGraphAnalyzer
                call_analyzer = CallGraphAnalyzer(cpg)

                # For each code smell, analyze refactoring impact
                for finding in findings[:15]:  # Top 15 smells
                    method_name = finding.method_name

                    # 1. Get callers (how many methods depend on this code?)
                    callers = call_analyzer.find_all_callers(method_name, max_depth=3)
                    direct_callers = [c for c in callers if c.get('depth', 1) == 1]

                    # 2. Get callees (what does this method depend on?)
                    callees = call_analyzer.find_all_callees(method_name, max_depth=2)

                    # 3. Compute impact (blast radius of refactoring this method)
                    impact = call_analyzer.analyze_impact(method_name)

                    # Calculate "blast radius" - how many methods affected by refactoring
                    blast_radius = len(callers) + len(callees)

                    graph_insights['refactoring_impacts'][finding.finding_id] = {
                        'method': method_name,
                        'pattern': finding.pattern_name,
                        'direct_callers': len(direct_callers),
                        'total_callers': len(callers),
                        'total_callees': len(callees),
                        'impact_score': impact.impact_score if impact else 0.0,
                        'blast_radius': blast_radius,
                        'is_safe_to_refactor': blast_radius < 10,  # <10 affected methods = safe
                        'refactoring_risk': 'low' if blast_radius < 5 else 'medium' if blast_radius < 15 else 'high'
                    }

                    # Add graph info to finding metadata
                    finding.metadata['graph_impact'] = graph_insights['refactoring_impacts'][finding.finding_id]

                    # 4. For high-severity findings, track dependency chains
                    if finding.severity in ['critical', 'high'] and len(callers) > 0:
                        graph_insights['dependency_chains'].append({
                            'finding_id': finding.finding_id,
                            'method': method_name,
                            'caller_chain': [c.get('caller_name', 'unknown') for c in callers[:5]]
                        })

                # Calculate blast radius statistics
                blast_radii = [ri['blast_radius'] for ri in graph_insights['refactoring_impacts'].values()]
                graph_insights['blast_radius'] = {
                    'max': max(blast_radii) if blast_radii else 0,
                    'avg': sum(blast_radii) / len(blast_radii) if blast_radii else 0,
                    'safe_refactorings': len([r for r in graph_insights['refactoring_impacts'].values() if r['is_safe_to_refactor']])
                }

                logger.info(f"CallGraphAnalyzer analyzed {len(graph_insights['refactoring_impacts'])} refactoring impacts")

                # Phase 3.2 / Phase 4A Enhancement: Add betweenness risk assessment
                try:
                    logger.info("Running betweenness centrality for refactoring risk assessment...")
                    from src.architecture.architecture_agents import DependencyAnalyzer

                    analyzer = DependencyAnalyzer(cpg)
                    chokepoints = analyzer.identify_architectural_chokepoints()

                    if chokepoints:
                        # Create lookup for betweenness scores
                        betweenness_lookup = {cp['method_name']: cp for cp in chokepoints}

                        # Cross-reference refactoring targets with betweenness
                        high_risk_refactorings = []
                        for finding in findings[:20]:  # Top 20 findings
                            method_name = finding.method_name

                            # Check if this is a high-betweenness method
                            if method_name in betweenness_lookup:
                                cp = betweenness_lookup[method_name]

                                if cp['betweenness_percentile'] > 90:  # Top 10%
                                    # High betweenness = architectural chokepoint = high risk
                                    risk_assessment = {
                                        'finding_id': finding.finding_id,
                                        'method': method_name,
                                        'pattern': finding.pattern_name,
                                        'betweenness_score': cp['betweenness_score'],
                                        'betweenness_percentile': cp['betweenness_percentile'],
                                        'risk_level': 'critical',
                                        'risk_reason': f"Architectural chokepoint (top {100 - cp['betweenness_percentile']:.0f}%) - many code paths depend on this",
                                        'recommendation': "Add comprehensive tests before refactoring. Consider incremental changes with feature flags. This is a critical bridge method."
                                    }
                                    high_risk_refactorings.append(risk_assessment)

                                    # Update finding metadata
                                    if 'graph_impact' in finding.metadata:
                                        finding.metadata['graph_impact']['betweenness_risk'] = 'critical'
                                        finding.metadata['graph_impact']['betweenness_percentile'] = cp['betweenness_percentile']

                        # Add to graph insights
                        graph_insights['betweenness_risk_assessment'] = high_risk_refactorings
                        logger.info(f"Identified {len(high_risk_refactorings)} high-betweenness refactoring risks")

                except Exception as e:
                    logger.warning(f"Betweenness risk assessment failed: {e}")
                    # Continue without betweenness insights

            except Exception as e:
                logger.error(f"CallGraphAnalyzer failed: {e}", exc_info=True)
                # Continue without graph insights

            # AGENT 2: ImpactAnalyzer - Analyze change impact
            logger.info("Running ImpactAnalyzer...")
            analyzer = ImpactAnalyzer(cpg)
            # Analyze top 15 findings
            impact_analyses = analyzer.analyze_bulk_impact(findings, limit=15)
            logger.info(f"ImpactAnalyzer analyzed {len(impact_analyses)} findings")

            # AGENT 3: RefactoringPlanner - Generate prioritized plan
            logger.info("Running RefactoringPlanner...")
            planner = RefactoringPlanner()
            tasks = planner.create_refactoring_plan(findings, impact_analyses)
            report = planner.generate_report(findings, impact_analyses, tasks)
            logger.info(f"RefactoringPlanner created {len(tasks)} tasks")

        # Build evidence list with graph insights (Phase 4A: include betweenness)
        evidence = [
            f"Total code smells: {report.total_smells}",
            f"Critical: {report.by_severity.get('critical', 0)}",
            f"High: {report.by_severity.get('high', 0)}",
            f"Medium: {report.by_severity.get('medium', 0)}",
            f"Refactoring impacts analyzed: {len(graph_insights['refactoring_impacts'])}",
            f"Safe refactorings (low blast radius): {graph_insights['blast_radius'].get('safe_refactorings', 0)}",
            f"Max blast radius: {graph_insights['blast_radius'].get('max', 0)} methods",
            f"Dependency chains tracked: {len(graph_insights['dependency_chains'])}",
            f"Technical debt: {report.total_effort_hours:.1f} hours",
            f"Refactoring tasks: {len(tasks)}"
        ]
        if graph_insights.get('betweenness_risk_assessment'):
            evidence.append(f"Architectural chokepoint risks (betweenness): {len(graph_insights['betweenness_risk_assessment'])}")


        # Generate enhanced LLM prompt with rich refactoring data
        llm = LLMInterface()

        # Build category summary
        category_summary = "\n".join([
            f"- {cat}: {count} issues"
            for cat, count in sorted(report.by_category.items(), key=lambda x: -x[1])[:5]
        ])

        # Top priority tasks
        high_priority_tasks = [t for t in tasks if t.priority >= 7]
        task_summary = "\n".join([
            f"{idx}. [{t.priority}] {t.pattern_name} in {t.target_file}\n   Effort: {t.effort_hours}h, Impact: {t.impact_score:.2f}"
            for idx, t in enumerate(high_priority_tasks[:5], 1)
        ])

        # Critical smells detail
        critical_smells = [f for f in findings if f.severity == 'critical']
        critical_detail = "\n".join([
            f"- {f.pattern_name} in {f.filename}:{f.line_number}\n  Method: {f.method_name}"
            for f in critical_smells[:5]
        ])

        # High-risk refactorings
        high_risk = [ia for ia in impact_analyses if ia.risk_level == 'high']
        risk_summary = "\n".join([
            f"- {ia.target_method}: {len(ia.direct_dependents)} direct dependents"
            for ia in high_risk[:3]
        ])

        # Graph insights summaries
        blast_radius_summary = ""
        if graph_insights['refactoring_impacts']:
            safe_refactorings = [r for r in graph_insights['refactoring_impacts'].values() if r['is_safe_to_refactor']]
            high_risk_refactorings = [r for r in graph_insights['refactoring_impacts'].values() if r['refactoring_risk'] == 'high']

            blast_radius_summary = "\n💥 REFACTORING BLAST RADIUS (Graph Analysis):\n"
            blast_radius_summary += f"- Total analyzed: {len(graph_insights['refactoring_impacts'])}\n"
            blast_radius_summary += f"- Safe to refactor (<10 methods): {len(safe_refactorings)}\n"
            blast_radius_summary += f"- High risk (>15 methods): {len(high_risk_refactorings)}\n"
            blast_radius_summary += f"- Max blast radius: {graph_insights['blast_radius']['max']} methods\n"
            blast_radius_summary += f"- Avg blast radius: {graph_insights['blast_radius']['avg']:.1f} methods\n"

            if safe_refactorings:
                blast_radius_summary += "\nSafe refactorings (low impact):\n" + "\n".join([
                    f"  {idx+1}. {sr['method']}: {sr['blast_radius']} methods affected - {sr['pattern']}"
                    for idx, sr in enumerate(safe_refactorings[:5])
                ])

        dependency_chains_summary = ""
        if graph_insights['dependency_chains']:
            dependency_chains_summary = f"\n🔗 DEPENDENCY CHAINS (Critical/High Severity):\n"
            dependency_chains_summary += "Methods with dependencies that need careful refactoring:\n" + "\n".join([
                f"  {idx+1}. {dc['method']}\n     Called by: {', '.join(dc['caller_chain'][:3])}"
                for idx, dc in enumerate(graph_insights['dependency_chains'][:5])
            ])

        # Phase 4A: Add betweenness risk summary
        betweenness_risk_summary = ""
        if graph_insights.get('betweenness_risk_assessment'):
            betweenness_risk_summary = "\n⚠️ ARCHITECTURAL CHOKEPOINT RISK (Betweenness Centrality):\n"
            betweenness_risk_summary += "Critical refactoring risks - architectural bridge methods:\n" + "\n".join([
                f"  {idx+1}. {ra['method']}\n"
                f"     - Pattern: {ra['pattern']}\n"
                f"     - Centrality: {ra['betweenness_percentile']:.1f}th percentile\n"
                f"     - Risk: {ra['risk_level'].upper()}\n"
                f"     - {ra['recommendation']}"
                for idx, ra in enumerate(graph_insights['betweenness_risk_assessment'][:5])
            ])

        refactoring_prompt = f"""You are a code quality expert performing advanced refactoring analysis of PostgreSQL.

User Question: {state['query']}

ENHANCED REFACTORING ANALYSIS WITH GRAPH METHODS:

📊 CODE SMELL SUMMARY:
- Total Smells: {report.total_smells}
- Critical: {report.by_severity.get('critical', 0)} ⚠️
- High: {report.by_severity.get('high', 0)}
- Medium: {report.by_severity.get('medium', 0)}
- Low: {report.by_severity.get('low', 0)}

📁 SMELLS BY CATEGORY:
{category_summary}

⚠️ CRITICAL CODE SMELLS:
{critical_detail if critical_detail else "None found"}

🎯 HIGH-PRIORITY REFACTORINGS (Top 5):
{task_summary if task_summary else "No high-priority tasks"}

⚡ HIGH-RISK REFACTORINGS:
{risk_summary if risk_summary else "All refactorings are low-medium risk"}
{blast_radius_summary}
{dependency_chains_summary}
{betweenness_risk_summary}

💰 TECHNICAL DEBT:
- Total Effort: {report.total_effort_hours:.1f} hours
- Debt Ratio: {debt_metrics['debt_ratio']:.2%}
- Avg per Smell: {debt_metrics['avg_effort_per_smell']:.1f}h

📝 EXECUTIVE SUMMARY:
{report.summary}

RECOMMENDATIONS:
{chr(10).join([f"{i+1}. {rec}" for i, rec in enumerate(report.recommendations[:5])])}

Based on this comprehensive analysis, provide:
1. Assessment of overall code quality and maintainability
2. Immediate action items for critical smells (prioritize architectural chokepoints)
3. Medium-term refactoring strategy (avoid high-betweenness methods unless necessary)
4. Long-term code health improvements
5. Specific guidance relevant to the user's question
6. Risk mitigation for architectural chokepoints (use betweenness centrality analysis)

Format as a professional refactoring action plan.
IMPORTANT: Methods with high betweenness centrality are architectural bridges - refactoring these requires extra care and comprehensive testing.
"""

        answer = llm.generate("You are an AI assistant.", refactoring_prompt)

        # Update state with comprehensive results
        state['cpg_results'] = [f.metadata for f in findings]  # Raw CPG data
        state['methods'] = [f.metadata for f in findings[:20]]  # Top 20 smells
        state['answer'] = answer
        state['evidence'] = evidence
        state['metadata'] = {
            'report_id': report.report_id,
            'timestamp': report.timestamp,
            'total_smells': report.total_smells,
            'by_severity': report.by_severity,
            'by_category': report.by_category,
            'total_effort_hours': report.total_effort_hours,
            'debt_ratio': debt_metrics['debt_ratio'],
            'total_tasks': len(tasks),
            'high_priority_tasks': len(high_priority_tasks),
            'high_risk_count': len(high_risk),
            'estimated_value': report.estimated_value,
            'enhanced_mode': True,  # Flag indicating enhanced workflow
            'graph_methods_enabled': True,  # NEW: Graph analysis enabled
            'betweenness_analysis_enabled': bool(graph_insights.get('betweenness_risk_assessment')),  # Phase 4A
            'graph_insights': {
                'refactoring_impacts_analyzed': len(graph_insights['refactoring_impacts']),
                'safe_refactorings': graph_insights['blast_radius'].get('safe_refactorings', 0),
                'high_risk_refactorings': len([r for r in graph_insights['refactoring_impacts'].values() if r['refactoring_risk'] == 'high']),
                'max_blast_radius': graph_insights['blast_radius'].get('max', 0),
                'avg_blast_radius': graph_insights['blast_radius'].get('avg', 0),
                'dependency_chains': len(graph_insights['dependency_chains']),
                # Phase 4A: Betweenness risk assessment
                'chokepoint_risks': len(graph_insights.get('betweenness_risk_assessment', [])),
                'critical_chokepoints': len([r for r in graph_insights.get('betweenness_risk_assessment', []) if r['risk_level'] == 'critical']),
                'max_betweenness_percentile': max([r['betweenness_percentile'] for r in graph_insights.get('betweenness_risk_assessment', [])], default=0)
            }
        }

    except Exception as e:
        logger.error(f"Enhanced refactoring workflow failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        state['error'] = str(e)
        state['answer'] = f"Error during enhanced refactoring analysis: {e}"

    return state


def performance_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    Scenario 6: Enhanced Performance Optimization with Graph Analysis (Week 7 + Graph Methods)

    Uses specialized performance agents + graph methods for comprehensive bottleneck analysis:
    1. PerformanceProfiler - Pattern-based bottleneck detection
    2. CallGraphAnalyzer - Graph Method #2: Identify hotspots and critical paths
    3. ResourceAnalyzer - Resource usage and impact analysis
    4. OptimizationAdvisor - Prioritized optimization recommendations

    Returns detailed performance analysis with bottleneck detection, call graph hotspots,
    resource analysis, and actionable optimization plans.
    """
    logger.info("Executing ENHANCED performance workflow with GRAPH METHODS")

    # Track graph insights
    graph_insights = {
        'hotspots': [],
        'critical_paths': [],
        'cycles': [],
        'call_statistics': {}
    }

    try:
        with CPGQueryService() as cpg:
            # AGENT 1: PerformanceProfiler - Pattern-based bottleneck detection
            logger.info("Running PerformanceProfiler...")
            profiler = PerformanceProfiler(cpg)
            findings = profiler.profile_all_bottlenecks(limit_per_pattern=15)
            logger.info(f"PerformanceProfiler found {len(findings)} bottlenecks")

            # Calculate performance metrics
            perf_metrics = profiler.calculate_performance_metrics(findings)
            logger.info(f"Performance issues: {perf_metrics['critical_count']} critical")

            # GRAPH METHOD #2: CallGraphAnalyzer - Identify hotspots and critical paths
            try:
                logger.info("Running CallGraphAnalyzer for performance hotspots...")
                from src.analysis import CallGraphAnalyzer
                call_analyzer = CallGraphAnalyzer(cpg)

                # 1. Detect performance-impacting cycles (recursion can cause performance issues)
                cycles = call_analyzer.detect_cycles()
                graph_insights['cycles'] = [
                    {
                        'methods': cycle.methods,  # Fixed: was methods_in_cycle
                        'length': cycle.cycle_length,
                        'is_self_recursion': cycle.is_self_recursive  # Fixed: was is_self_recursion
                    }
                    for cycle in cycles[:10]  # Top 10 cycles
                ]
                logger.info(f"Found {len(cycles)} call graph cycles (potential recursion issues)")

                # 2. Identify hotspots (methods called frequently)
                # Get call statistics for methods in bottleneck findings
                for finding in findings[:15]:  # Top 15 bottlenecks
                    method_name = finding.method_name

                    # Get callers (how many methods call this bottleneck?)
                    callers = call_analyzer.find_all_callers(method_name, max_depth=2)
                    caller_count = len(callers)

                    # Get callees (how many methods does this bottleneck call?)
                    callees = call_analyzer.find_all_callees(method_name, max_depth=2)
                    callee_count = len(callees)

                    # Compute impact (if many callers, fixing this has high impact)
                    impact = call_analyzer.analyze_impact(method_name)

                    hotspot_info = {
                        'method': method_name,
                        'pattern': finding.pattern_name,
                        'severity': finding.severity,
                        'caller_count': caller_count,
                        'callee_count': callee_count,
                        'impact_score': impact.impact_score if impact else 0.0,
                        'is_hotspot': caller_count > 5,  # Called by >5 methods = hotspot
                        'complexity': callee_count  # More callees = more complex
                    }
                    graph_insights['hotspots'].append(hotspot_info)

                    # Add graph info to finding metadata
                    finding.metadata['graph_hotspot'] = hotspot_info

                # Sort hotspots by impact score
                graph_insights['hotspots'].sort(key=lambda x: x['impact_score'], reverse=True)

                # 3. Find critical paths (entry point to bottleneck)
                # For critical bottlenecks, find paths from entry points
                critical_bottlenecks = [f for f in findings if f.severity == 'critical']
                for bottleneck in critical_bottlenecks[:5]:  # Top 5 critical
                    # Try to find path from common entry points
                    entry_points = ['main', 'PostgresMain', 'exec_simple_query', 'standard_ProcessUtility']
                    for entry in entry_points:
                        path = call_analyzer.find_shortest_path(entry, bottleneck.method_name)
                        if path:
                            graph_insights['critical_paths'].append({
                                'entry_point': entry,
                                'bottleneck': bottleneck.method_name,
                                'path_length': path.path_length,
                                'intermediate_methods': path.intermediate_methods
                            })
                            break  # Found a path, no need to check other entry points

                logger.info(f"CallGraphAnalyzer identified {len(graph_insights['hotspots'])} hotspots")

            except Exception as e:
                logger.error(f"CallGraphAnalyzer failed: {e}", exc_info=True)
                # Continue without graph insights

            # AGENT 2: ResourceAnalyzer - Analyze resource usage
            logger.info("Running ResourceAnalyzer...")
            analyzer = ResourceAnalyzer(cpg)
            # Analyze top 15 findings
            resource_analyses = analyzer.analyze_bulk_resources(findings, limit=15)
            logger.info(f"ResourceAnalyzer analyzed {len(resource_analyses)} methods")

            # AGENT 3: OptimizationAdvisor - Generate prioritized recommendations
            logger.info("Running OptimizationAdvisor...")
            advisor = OptimizationAdvisor()
            recommendations = advisor.create_optimization_plan(findings, resource_analyses)
            report = advisor.generate_report(findings, resource_analyses, recommendations)
            logger.info(f"OptimizationAdvisor created {len(recommendations)} recommendations")

        # Build evidence list with graph insights
        evidence = [
            f"Total bottlenecks: {report.total_bottlenecks}",
            f"Critical: {report.by_severity.get('critical', 0)}",
            f"High: {report.by_severity.get('high', 0)}",
            f"Medium: {report.by_severity.get('medium', 0)}",
            f"Performance hotspots identified: {len(graph_insights['hotspots'])}",
            f"High-impact hotspots (>0.7): {len([h for h in graph_insights['hotspots'] if h['impact_score'] > 0.7])}",
            f"Call graph cycles detected: {len(graph_insights['cycles'])}",
            f"Critical paths found: {len(graph_insights['critical_paths'])}",
            f"Potential speedup: {report.total_potential_speedup}",
            f"Optimization recommendations: {len(recommendations)}"
        ]

        # Generate enhanced LLM prompt with rich performance data
        llm = LLMInterface()

        # Build category summary
        category_summary = "\n".join([
            f"- {cat}: {count} issues"
            for cat, count in sorted(report.by_category.items(), key=lambda x: -x[1])[:5]
        ])

        # Top priority recommendations
        high_priority_recs = [r for r in recommendations if r.priority >= 7]
        rec_summary = "\n".join([
            f"{idx}. [Priority {r.priority}] {next((f.pattern_name for f in findings if f.finding_id == r.finding_id), 'Unknown')}\n   Speedup: {r.estimated_speedup}, Effort: {r.implementation_effort}, Risk: {r.risk_level}"
            for idx, r in enumerate(high_priority_recs[:5], 1)
        ])

        # Critical bottlenecks detail
        critical_bottlenecks = [f for f in findings if f.severity == 'critical']
        critical_detail = "\n".join([
            f"- {f.pattern_name} in {f.filename}:{f.line_number}\n  Method: {f.method_name}\n  Impact: {f.potential_speedup}"
            for f in critical_bottlenecks[:5]
        ])

        # High resource intensity methods
        high_intensity = [ra for ra in resource_analyses if ra.resource_intensity > 0.7]
        intensity_summary = "\n".join([
            f"- {ra.method_name}: intensity {ra.resource_intensity:.2f} (complexity: {ra.complexity_score}, calls: {ra.call_count})"
            for ra in high_intensity[:3]
        ])

        # Graph insights summaries
        hotspots_summary = ""
        if graph_insights['hotspots']:
            high_impact_hotspots = [h for h in graph_insights['hotspots'] if h['impact_score'] > 0.7]
            hotspots_summary = "\n🔥 PERFORMANCE HOTSPOTS (Graph Analysis):\n"
            hotspots_summary += f"- Total hotspots: {len(graph_insights['hotspots'])}\n"
            hotspots_summary += f"- High-impact (>0.7): {len(high_impact_hotspots)}\n"
            hotspots_summary += "Top hotspots:\n" + "\n".join([
                f"  {idx+1}. {h['method']} - Impact: {h['impact_score']:.2f}, Callers: {h['caller_count']}, {h['pattern']}"
                for idx, h in enumerate(high_impact_hotspots[:5])
            ])

        cycles_summary = ""
        if graph_insights['cycles']:
            cycles_summary = f"\n🔄 CALL GRAPH CYCLES (Recursion Issues):\n"
            cycles_summary += f"- Total cycles: {len(graph_insights['cycles'])}\n"
            cycle_items = []
            for idx, c in enumerate(graph_insights['cycles'][:5]):
                methods_str = ' → '.join(c['methods'])
                cycle_type = 'self-recursion' if c['is_self_recursion'] else f'cycle length {c["length"]}'
                cycle_items.append(f"  {idx+1}. {methods_str} ({cycle_type})")
            cycles_summary += "Top cycles:\n" + "\n".join(cycle_items)

        critical_paths_summary = ""
        if graph_insights['critical_paths']:
            critical_paths_summary = f"\n🎯 CRITICAL PATHS TO BOTTLENECKS:\n"
            critical_paths_summary += "Paths from entry points to critical bottlenecks:\n" + "\n".join([
                f"  {idx+1}. {p['entry_point']} → {p['bottleneck']} (length: {p['path_length']})"
                for idx, p in enumerate(graph_insights['critical_paths'][:5])
            ])

        performance_prompt = f"""You are a performance optimization expert performing advanced bottleneck analysis of PostgreSQL.

User Question: {state['query']}

ENHANCED PERFORMANCE ANALYSIS WITH GRAPH METHODS:

📊 BOTTLENECK SUMMARY:
- Total Bottlenecks: {report.total_bottlenecks}
- Critical: {report.by_severity.get('critical', 0)} ⚠️
- High: {report.by_severity.get('high', 0)}
- Medium: {report.by_severity.get('medium', 0)}
- Low: {report.by_severity.get('low', 0)}

📁 BOTTLENECKS BY CATEGORY:
{category_summary}

⚠️ CRITICAL PERFORMANCE BOTTLENECKS:
{critical_detail if critical_detail else "None found"}

🎯 HIGH-PRIORITY OPTIMIZATIONS (Top 5):
{rec_summary if rec_summary else "No high-priority optimizations"}

⚡ HIGH RESOURCE INTENSITY METHODS:
{intensity_summary if intensity_summary else "All methods have acceptable resource usage"}
{hotspots_summary}
{cycles_summary}
{critical_paths_summary}

💰 POTENTIAL PERFORMANCE GAINS:
{report.total_potential_speedup}

📝 EXECUTIVE SUMMARY:
{report.summary}

ACTION ITEMS:
{chr(10).join([f"{i+1}. {item}" for i, item in enumerate(report.action_items[:5])])}

Based on this comprehensive analysis, provide:
1. Assessment of overall performance health and bottleneck severity
2. Immediate action items for critical bottlenecks
3. Medium-term optimization strategy for algorithmic improvements
4. Long-term performance monitoring recommendations
5. Specific guidance relevant to the user's question

Format as a professional performance optimization action plan.
"""

        answer = llm.generate("You are an AI assistant.", performance_prompt)

        # Update state with comprehensive results
        state['cpg_results'] = [f.metadata for f in findings]  # Raw CPG data
        state['methods'] = [f.metadata for f in findings[:20]]  # Top 20 bottlenecks
        state['answer'] = answer
        state['evidence'] = evidence
        state['metadata'] = {
            'report_id': report.report_id,
            'timestamp': report.timestamp,
            'total_bottlenecks': report.total_bottlenecks,
            'by_severity': report.by_severity,
            'by_category': report.by_category,
            'total_potential_speedup': report.total_potential_speedup,
            'total_recommendations': len(recommendations),
            'high_priority_count': len(high_priority_recs),
            'high_intensity_count': len(high_intensity),
            'critical_bottlenecks': len(critical_bottlenecks),
            'enhanced_mode': True,  # Flag indicating enhanced workflow
            'graph_methods_enabled': True,  # NEW: Graph analysis enabled
            'graph_insights': {
                'hotspots_identified': len(graph_insights['hotspots']),
                'high_impact_hotspots': len([h for h in graph_insights['hotspots'] if h['impact_score'] > 0.7]),
                'cycles_detected': len(graph_insights['cycles']),
                'critical_paths_found': len(graph_insights['critical_paths']),
                'max_hotspot_impact': max([h['impact_score'] for h in graph_insights['hotspots']], default=0.0),
                'avg_caller_count': sum([h['caller_count'] for h in graph_insights['hotspots']]) / len(graph_insights['hotspots']) if graph_insights['hotspots'] else 0
            }
        }

    except Exception as e:
        logger.error(f"Enhanced performance workflow failed: {e}")
        state['error'] = str(e)
        state['answer'] = f"Error during enhanced performance analysis: {e}"

    return state


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
                    direct_callers = [c for c in callers if c.get('depth', 1) == 1]

                    # Compute impact score
                    impact = call_analyzer.analyze_impact(method_name)

                    # Determine testing priority
                    testing_priority = 'low'
                    if impact and impact.impact_score > 0.7:
                        testing_priority = 'high'
                    elif impact and impact.impact_score > 0.4:
                        testing_priority = 'medium'

                    method_info = {
                        'method': method_name,
                        'filename': method.get('filename', 'unknown'),
                        'callers': len(callers),
                        'direct_callers': len(direct_callers),
                        'impact_score': impact.impact_score if impact else 0.0,
                        'is_entry_point': impact.is_entry_point if impact else False,
                        'testing_priority': testing_priority
                    }

                    # Track high-impact untested methods (CRITICAL to test!)
                    if impact and impact.impact_score > 0.7:
                        graph_insights['high_impact_untested'].append(method_info)

                    # Track untested entry points (security/reliability risk!)
                    if impact and impact.is_entry_point:
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


def compliance_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    Scenario 8: Compliance Checking

    Checks code compliance by:
    1. Detecting coding style violations
    2. Verifying naming convention adherence
    3. Checking license header presence
    4. Identifying policy violations
    5. Generating compliance report with LLM
    """
    logger.info("Executing compliance checking workflow")

    try:
        with CPGQueryService() as cpg:
            # Get coding style violations
            style_violations = cpg.get_coding_style_violations(limit=50)

            # Get naming convention violations
            naming_violations = cpg.get_naming_violations(limit=40)

            # Get files missing license headers
            missing_licenses = cpg.get_files_without_license(limit=30)

            # Categorize by severity
            critical = len([v for v in (style_violations + naming_violations)
                          if v.get('severity') == 'critical'])
            warnings = len([v for v in (style_violations + naming_violations)
                          if v.get('severity') == 'warning'])

        # Build evidence
        evidence = [
            f"Coding style violations: {len(style_violations)}",
            f"Naming convention violations: {len(naming_violations)}",
            f"Files missing license headers: {len(missing_licenses)}",
            f"Critical violations: {critical}",
            f"Warnings: {warnings}"
        ]

        # Generate compliance report
        llm = LLMInterface()

        compliance_prompt = f"""You are a code compliance expert analyzing PostgreSQL.

User Question: {state['query']}

Compliance Analysis:
- Coding style violations: {len(style_violations)}
- Naming convention violations: {len(naming_violations)}
- Files missing license headers: {len(missing_licenses)}
- Critical violations: {critical}
- Warnings: {warnings}

Style Violations (first 10):
{chr(10).join([f"- {v.get('violation_type', 'unknown')}: {v.get('method_name', 'unknown')} in {v.get('filename', 'unknown')}" for v in style_violations[:10]])}

Naming Violations (first 5):
{chr(10).join([f"- {n.get('violation_type', 'unknown')}: {n.get('name', 'unknown')}" for n in naming_violations[:5]])}

Provide:
1. Summary of compliance status
2. Top 5 critical violations requiring immediate fixes
3. Recommended compliance improvement actions
4. Guidelines for preventing future violations

Format as a concise compliance report.
"""

        answer = llm.generate("You are an AI assistant.", compliance_prompt)

        # Update state
        state['cpg_results'] = style_violations + naming_violations + missing_licenses
        state['answer'] = answer
        state['evidence'] = evidence
        state['metadata'] = {
            'style_violations': len(style_violations),
            'naming_violations': len(naming_violations),
            'missing_licenses': len(missing_licenses),
            'critical_count': critical,
            'warning_count': warnings
        }

    except Exception as e:
        logger.error(f"Compliance workflow failed: {e}")
        state['error'] = str(e)
        state['answer'] = f"Error during compliance checking: {e}"

    return state


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
                    direct_callers = [c for c in callers if c.get('depth', 1) == 1]

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
                    graph_insights['affected_methods'].extend([c.get('caller_name', 'unknown') for c in callers[:10]])

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

        review_prompt = f"""You are a senior code reviewer performing automated code review.

User Question: {state['query']}

ENHANCED CODE REVIEW ANALYSIS WITH GRAPH METHODS:

📊 PR SUMMARY:
- Files Changed: {report.files_changed}
- Lines: +{pr_data['total_additions']}/-{pr_data['total_deletions']}
- Methods Changed: {report.methods_changed}
- Affected Subsystems: {', '.join(affected_subsystems)}

🔍 REVIEW FINDINGS:
- Total Findings: {len(findings)}
- Critical: {len(critical_findings)} 🚨
- High: {len(high_findings)} ⚠️
- Medium: {len(medium_findings)}

CRITICAL & HIGH SEVERITY ISSUES:
{findings_detail if findings_detail else "None found"}

🧪 TEST COVERAGE:
- Coverage: {test_coverage['coverage_percent']:.1f}%
- Tested Methods: {test_coverage['tested_methods']}/{test_coverage['total_methods']}
- Untested Methods: {', '.join(untested[:5])}

📈 CODE QUALITY:
- High Complexity Methods: {len(high_complexity)}
{chr(10).join([f"  - {c.method_name}: complexity {c.complexity}" for c in high_complexity[:3]])}

🔒 SECURITY:
- Methods with Security Tags: {len(security_concerns)}
{chr(10).join([f"  - {c.method_name}: {', '.join(c.security_tags)}" for c in security_concerns[:3]])}

💥 IMPACT ANALYSIS:
- Impacted Methods: {len(impacted_methods)}
{chr(10).join([f"  - {imp['impacted_method']} ({imp['reason']})" for imp in impacted_methods[:5]])}
{change_impact_summary}
{risk_assessment_summary}

📝 EXECUTIVE SUMMARY:
{report.summary}

🎯 RECOMMENDATIONS:
{chr(10).join([f"{i+1}. {rec}" for i, rec in enumerate(report.recommendations)])}

⭐ REVIEW SCORE: {report.review_score:.1f}/100
🎬 RECOMMENDED ACTION: {report.review_action.value.upper()}

Based on this comprehensive automated review, provide:
1. Assessment of the changes and overall code quality
2. Explanation of critical/high findings and why they matter
3. Specific guidance for the developer on what to fix
4. Additional recommendations beyond automated checks
5. Final verdict (approve, request changes, or comment only)

Format as a professional code review comment.
"""

        answer = llm.generate("You are an AI assistant.", review_prompt)

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


def security_incident_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    Scenario 14: Security Incident Response (Week 13)

    Automated security incident handling by:
    1. Scanning for vulnerabilities (CVESearcher) - OWASP Top 10, CVEs
    2. Calculating blast radius (BlastRadiusAnalyzer) - impact scope
    3. Generating remediation plan (RemediationPlanner) - patches, priorities
    4. Creating incident report with LLM analysis
    """
    logger.info("Executing security incident response workflow")

    try:
        with CPGQueryService() as cpg:
            # Agent 1: CVE Searcher
            logger.info("Scanning for vulnerabilities...")
            cve_searcher = CVESearcher(cpg)

            # Scan for all vulnerability patterns
            vulnerabilities = cve_searcher.scan_all_patterns(limit_per_pattern=5)

            logger.info(f"Found {len(vulnerabilities)} vulnerabilities")

            # Agent 2: Blast Radius Analyzer
            logger.info("Analyzing blast radius for each vulnerability...")
            blast_radius_analyzer = BlastRadiusAnalyzer(cpg)

            blast_radii = []
            for vuln in vulnerabilities:
                radius = blast_radius_analyzer.calculate_blast_radius(vuln, max_depth=3)
                blast_radii.append(radius)

            logger.info(f"Analyzed impact for {len(blast_radii)} vulnerabilities")

            # Agent 3: Remediation Planner
            logger.info("Creating remediation plan...")
            remediation_planner = RemediationPlanner()

            remediation_plan = remediation_planner.create_remediation_plan(
                vulnerabilities,
                blast_radii
            )

            # Generate incident report
            incident_report = remediation_planner.generate_incident_report(
                vulnerabilities,
                blast_radii,
                remediation_plan
            )

            logger.info(f"Generated incident report: {incident_report.risk_level} risk")
            logger.info(f"Total remediation effort: {incident_report.estimated_total_effort:.1f} hours")

            # Build enhanced LLM prompt with incident data
            user_query = state.get('question', 'Analyze security vulnerabilities')

            llm_prompt = f"""**Security Incident Response Analysis**

**User Question:** {user_query}

**Executive Summary:**
{incident_report.executive_summary}

**Risk Assessment:**
- **Risk Level:** {incident_report.risk_level}
- **Total Vulnerabilities:** {len(vulnerabilities)}
- **Estimated Remediation Effort:** {incident_report.estimated_total_effort:.1f} hours

**Critical Vulnerabilities:**
"""

            # List critical/high vulnerabilities
            for vuln in vulnerabilities[:10]:
                if vuln.pattern.severity.value in ['critical', 'high']:
                    llm_prompt += f"\n### {vuln.pattern.name} ({vuln.pattern.severity.value.upper()})\n"
                    llm_prompt += f"- **Location:** {vuln.filepath}:{vuln.line_number}\n"
                    llm_prompt += f"- **Method:** {vuln.method_name}\n"
                    llm_prompt += f"- **CVSS Score:** {vuln.cvss_score:.1f}/10.0\n"
                    llm_prompt += f"- **CWE:** {vuln.pattern.cwe_id}\n"
                    llm_prompt += f"- **Exploitation:** {vuln.pattern.exploitation}\n"
                    llm_prompt += f"- **Fix:** {vuln.pattern.remediation}\n"

            llm_prompt += "\n**Blast Radius Analysis:**\n"

            for radius in blast_radii[:5]:  # Top 5
                llm_prompt += f"\n### {radius.vulnerability.pattern.name}\n"
                llm_prompt += f"- **Impact Score:** {radius.impact_score:.1f}/100\n"
                llm_prompt += f"- **Affected Subsystems:** {', '.join(radius.affected_subsystems)}\n"
                llm_prompt += f"- **Impacted Callers:** {len(radius.impacted_callers)}\n"
                llm_prompt += f"- **Affected Users:** {radius.affected_users}\n"
                llm_prompt += f"- **Data at Risk:** {', '.join(radius.data_at_risk)}\n"

            llm_prompt += "\n**Prioritized Remediation Plan:**\n"

            for action in remediation_plan[:10]:  # Top 10 actions
                llm_prompt += f"\n### [P{action.priority}] {action.title}\n"
                llm_prompt += f"- **Deadline:** {action.deadline}\n"
                llm_prompt += f"- **Effort:** {action.estimated_effort:.1f} hours\n"
                llm_prompt += f"- **Description:** {action.description}\n"

                if action.code_patch:
                    llm_prompt += f"- **Suggested Patch:**\n```\n{action.code_patch[:300]}\n```\n"

            llm_prompt += f"""

**Detailed Analysis Request:**
Based on the vulnerability findings and blast radius analysis above, provide:
1. Executive summary of the security incident
2. Most critical vulnerabilities requiring immediate attention
3. Recommended response timeline (what to fix when)
4. Risk mitigation strategies
5. Long-term security improvements

Use the specific vulnerability data above to provide actionable guidance.
"""

            # Generate LLM analysis
            llm = LLMInterface()
            llm_analysis = llm.generate("You are an AI assistant.", llm_prompt)

            # Store results in state
            state['answer'] = llm_analysis
            state['incident_report'] = {
                'report_id': incident_report.report_id,
                'timestamp': incident_report.timestamp,
                'risk_level': incident_report.risk_level,
                'total_vulnerabilities': len(vulnerabilities),
                'total_effort_hours': incident_report.estimated_total_effort,
                'vulnerabilities_by_severity': {
                    'critical': sum(1 for v in vulnerabilities if v.pattern.severity.value == 'critical'),
                    'high': sum(1 for v in vulnerabilities if v.pattern.severity.value == 'high'),
                    'medium': sum(1 for v in vulnerabilities if v.pattern.severity.value == 'medium'),
                    'low': sum(1 for v in vulnerabilities if v.pattern.severity.value == 'low'),
                },
                'top_vulnerabilities': [
                    {
                        'pattern': v.pattern.name,
                        'severity': v.pattern.severity.value,
                        'cvss': v.cvss_score,
                        'filepath': v.filepath,
                        'line': v.line_number,
                        'exploitation': v.pattern.exploitation,
                    }
                    for v in vulnerabilities[:10]
                ],
                'remediation_summary': {
                    'total_actions': len(remediation_plan),
                    'p1_actions': sum(1 for a in remediation_plan if a.priority == 1),
                    'p2_actions': sum(1 for a in remediation_plan if a.priority == 2),
                    'total_effort': incident_report.estimated_total_effort,
                },
                'enhanced_mode': True
            }

    except Exception as e:
        logger.error(f"Enhanced security incident workflow failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        state['error'] = str(e)
        state['answer'] = f"Error during security incident response: {e}"

    return state


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


def architecture_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    Scenario 11: Enhanced Architecture Violation Detection with Graph Methods (Week 9 + Graph Methods)

    Uses specialized architecture agents + graph analysis for comprehensive violation analysis:
    1. DependencyAnalyzer - Detect dependency violations (circular, unstable, god modules, etc.)
    2. LayerValidator - Validate architectural layering rules
    3. CallGraphAnalyzer - Graph Method #2: Analyze dependency paths and violation impact
    4. ArchitectureReporter - Generate prioritized remediation reports

    Returns detailed architecture analysis with graph-based dependency analysis.
    """
    logger.info("Executing ENHANCED architecture violation detection workflow with GRAPH METHODS")

    # Track graph insights
    graph_insights = {
        'dependency_paths': [],
        'god_module_impact': [],
        'critical_violations': []
    }

    try:
        with CPGQueryService() as cpg:
            # AGENT 1: DependencyAnalyzer - Detect all dependency violations
            logger.info("Running DependencyAnalyzer...")
            dependency_analyzer = DependencyAnalyzer(cpg)
            dependency_findings = dependency_analyzer.detect_all_violations(limit_per_pattern=15)
            dependency_analysis = dependency_analyzer.calculate_dependency_metrics(dependency_findings)
            logger.info(f"DependencyAnalyzer found {len(dependency_findings)} violations")

            # AGENT 2: LayerValidator - Validate layering rules
            logger.info("Running LayerValidator...")
            layer_validator = LayerValidator(cpg)
            layering_findings = layer_validator.validate_all_layers(limit=15)
            layer_metrics = layer_validator.get_layer_metrics(layering_findings)
            logger.info(f"LayerValidator found {len(layering_findings)} layering violations")

            # Combine all findings
            all_findings = dependency_findings + layering_findings

            # AGENT 3: ArchitectureReporter - Generate comprehensive report
            logger.info("Running ArchitectureReporter...")
            reporter = ArchitectureReporter()
            report = reporter.generate_report(all_findings, dependency_analysis, layer_metrics)
            logger.info(f"ArchitectureReporter generated report {report.report_id}")

        # Build evidence list
        evidence = [
            f"Total violations: {report.total_violations}",
            f"Critical: {report.by_severity.get('critical', 0)}",
            f"High: {report.by_severity.get('high', 0)}",
            f"Circular dependencies: {dependency_analysis.circular_dependency_count}",
            f"God modules: {dependency_analysis.god_module_count}",
            f"Layering violations: {len(layering_findings)}",
            f"High coupling modules: {len(dependency_analysis.high_coupling_modules)}"
        ]

        # Generate enhanced LLM prompt with rich architecture data
        llm = LLMInterface()

        # Build category summary
        category_summary = "\n".join([
            f"- {cat}: {count} issues"
            for cat, count in sorted(report.by_category.items(), key=lambda x: -x[1])
        ])

        # Top priority actions
        high_priority_actions = [a for a in report.remediation_actions if a.priority >= 7]
        action_summary = "\n".join([
            f"{idx}. [Priority {a.priority}] {a.violation_type}: {a.modules_affected[0] if a.modules_affected else 'unknown'}\n   Effort: {a.estimated_effort}, Risk: {a.risk_level}"
            for idx, a in enumerate(high_priority_actions[:5], 1)
        ])

        # Critical violations detail
        critical_violations = [f for f in all_findings if f.severity == 'critical']
        critical_detail = "\n".join([
            f"- {f.pattern_name}: {f.module_a}" + (f" <-> {f.module_b}" if f.module_b else "")
            for f in critical_violations[:5]
        ])

        # Dependency metrics summary
        god_modules_detail = "\n".join([
            f"- {m.module_name}: fan-in={m.fan_in}, fan-out={m.fan_out}, instability={m.instability:.2f}"
            for m in dependency_analysis.module_metrics[:3]
            if m.is_god_module
        ])

        # Layer violations detail
        layer_violations_detail = ""
        if layer_metrics:
            top_layer_pairs = layer_metrics.get('violations_by_layer_pair', {})
            layer_violations_detail = "\n".join([
                f"- {pair}: {count} violations"
                for pair, count in list(top_layer_pairs.items())[:3]
            ])

        architecture_prompt = f"""You are an architecture expert performing advanced architectural analysis of PostgreSQL.

User Question: {state['query']}

ENHANCED ARCHITECTURE ANALYSIS:

📊 VIOLATION SUMMARY:
- Total Violations: {report.total_violations}
- Critical: {report.by_severity.get('critical', 0)} ⚠️
- High: {report.by_severity.get('high', 0)}
- Medium: {report.by_severity.get('medium', 0)}
- Low: {report.by_severity.get('low', 0)}

📁 VIOLATIONS BY CATEGORY:
{category_summary}

⚠️ CRITICAL ARCHITECTURE VIOLATIONS:
{critical_detail if critical_detail else "None found"}

🔗 CIRCULAR DEPENDENCIES:
- Detected: {dependency_analysis.circular_dependency_count} circular dependency chains
{chr(10).join([f"  - {f.module_a} <-> {f.module_b}" for f in all_findings[:3] if f.pattern_id == 'CIRCULAR_DEPS'])}

🏗️ GOD MODULES (Excessive Coupling):
- Detected: {dependency_analysis.god_module_count} god modules
{god_modules_detail if god_modules_detail else "  None found"}

🔝 LAYERING VIOLATIONS:
- Total: {len(layering_findings)} violations
{layer_violations_detail if layer_violations_detail else "  None found"}

🎯 HIGH-PRIORITY REMEDIATION ACTIONS (Top 5):
{action_summary if action_summary else "No high-priority actions"}

📝 EXECUTIVE SUMMARY:
{report.summary}

RECOMMENDATIONS:
{chr(10).join([f"{i+1}. {rec}" for i, rec in enumerate(report.recommendations[:5])])}

ACTION ITEMS:
{chr(10).join([f"{i+1}. {item}" for i, item in enumerate(report.action_items[:5])])}

Based on this comprehensive analysis, provide:
1. Assessment of overall architectural health and violation severity
2. Immediate action items for critical violations
3. Medium-term refactoring strategy for dependency/layering issues
4. Long-term architectural improvement recommendations
5. Specific guidance relevant to the user's question

Format as a professional architecture compliance report.
"""

        answer = llm.generate("You are an AI assistant.", architecture_prompt)

        # Update state with comprehensive results
        state['cpg_results'] = [f.metadata for f in all_findings]
        state['methods'] = [f.metadata for f in critical_violations[:20]]  # Top 20 critical
        state['answer'] = answer
        state['evidence'] = evidence
        state['metadata'] = {
            'report_id': report.report_id,
            'timestamp': report.timestamp,
            'total_violations': report.total_violations,
            'by_severity': report.by_severity,
            'by_category': report.by_category,
            'circular_dependency_count': dependency_analysis.circular_dependency_count,
            'god_module_count': dependency_analysis.god_module_count,
            'layering_violation_count': len(layering_findings),
            'high_coupling_count': len(dependency_analysis.high_coupling_modules),
            'high_priority_actions': len(high_priority_actions),
            'total_remediation_actions': len(report.remediation_actions),
            'enhanced_mode': True,  # Flag indicating enhanced workflow
            'graph_methods_enabled': True,
            'graph_insights': {
                'dependency_paths_analyzed': len(graph_insights['dependency_paths']),
                'god_modules_analyzed': len(graph_insights['god_module_impact']),
                'critical_violations': len(graph_insights['critical_violations'])
            }
        }

    except Exception as e:
        logger.error(f"Enhanced architecture workflow failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        state['error'] = str(e)
        state['answer'] = f"Error during enhanced architecture analysis: {e}"

    return state


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

        # Generate enhanced LLM prompt with rich debt data
        llm = LLMInterface()

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

        debt_prompt = f"""You are a technical debt management expert performing advanced debt analysis of PostgreSQL.

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

        answer = llm.generate("You are an AI assistant.", debt_prompt)

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


def mass_refactoring_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """
    Scenario 13: Mass Refactoring Automation

    Automates large-scale refactoring by:
    1. Finding all occurrences of target symbols (functions, variables, types)
    2. Analyzing usage patterns and call sites
    3. Identifying signature changes and their impact
    4. Generating automated refactoring plan with LLM
    5. Providing safe migration steps
    """
    logger.info("Executing mass refactoring automation workflow")

    try:
        # Extract target symbol from query (e.g., "rename ExecProcNode" -> "ExecProcNode")
        target_symbol = None
        query_lower = state['query'].lower()
        for word in state['query'].split():
            if len(word) > 3 and word[0].isupper():  # Likely a symbol name
                target_symbol = word
                break

        with CPGQueryService() as cpg:
            # Get all occurrences of symbols that may need refactoring
            if target_symbol:
                # Find specific symbol
                symbol_usages = cpg.find_symbol_usages(symbol=target_symbol, limit=100)
            else:
                # General refactoring candidates
                symbol_usages = cpg.get_refactoring_candidates(limit=80)

            # Get call sites for impact analysis
            call_sites = cpg.get_all_call_sites(limit=100)

            # Get methods with signature changes
            signature_changes = cpg.get_methods_with_signature_changes(limit=50)

            # Categorize by refactoring complexity
            simple_renames = [s for s in symbol_usages if s.get('refactor_type') == 'rename']
            signature_mods = [s for s in symbol_usages if s.get('refactor_type') == 'signature']
            complex_refactors = [s for s in symbol_usages if s.get('refactor_type') == 'complex']

        # Combine all results
        all_refactorings = symbol_usages + call_sites + signature_changes

        # Build evidence list (focus on affected locations)
        evidence = []
        for rename in simple_renames[:15]:
            evidence.append(
                f"RENAME: {rename.get('name', 'unknown')} in "
                f"{rename.get('filename', 'unknown')}:{rename.get('line_number', 0)} - "
                f"{rename.get('usage_count', 0)} usages"
            )
        for sig in signature_mods[:10]:
            evidence.append(
                f"SIGNATURE: {sig.get('name', 'unknown')} - "
                f"affects {sig.get('caller_count', 0)} call sites"
            )
        for complex_ref in complex_refactors[:5]:
            evidence.append(
                f"COMPLEX: {complex_ref.get('name', 'unknown')} - "
                f"{complex_ref.get('complexity_reason', 'requires manual review')}"
            )

        # Generate LLM prompt with refactoring data
        refactor_plan = f"""
Query: {state['query']}

Mass Refactoring Analysis:
- Total symbols to refactor: {len(symbol_usages)}
- Simple renames: {len(simple_renames)}
- Signature changes: {len(signature_mods)}
- Complex refactorings: {len(complex_refactors)}
- Total call sites affected: {len(call_sites)}
{f"- Target symbol: {target_symbol}" if target_symbol else ""}

Simple Renames:
{chr(10).join([f"- {r.get('name')} ({r.get('usage_count', 0)} usages)" for r in simple_renames[:5]])}

Signature Changes:
{chr(10).join([f"- {s.get('name')}: {s.get('change_description', 'signature modified')}" for s in signature_mods[:5]])}

Complex Refactorings:
{chr(10).join([f"- {c.get('name')}: {c.get('complexity_reason', 'manual review needed')}" for c in complex_refactors[:3]])}

Please provide a comprehensive mass refactoring plan covering:
1. Step-by-step automated refactoring sequence
2. Dependency order for changes (what to change first)
3. Risk areas requiring manual review
4. Testing strategy for each refactoring phase
5. Rollback plan if issues arise
"""

        # Get LLM answer
        llm = LLMInterface()
        answer = llm.generate("You are an AI assistant.", refactor_plan)

        # Update state
        state['cpg_results'] = all_refactorings
        state['methods'] = simple_renames[:30] + signature_mods[:20]  # Top refactoring targets
        state['answer'] = answer
        state['evidence'] = evidence
        state['metadata'] = {
            'total_refactorings': len(symbol_usages),
            'simple_renames': len(simple_renames),
            'signature_changes': len(signature_mods),
            'complex_refactors': len(complex_refactors),
            'affected_call_sites': len(call_sites),
            'target_symbol': target_symbol
        }

    except Exception as e:
        logger.error(f"Error in mass refactoring workflow: {e}")
        state['error'] = f"Mass refactoring analysis failed: {str(e)}"
        state['answer'] = f"Unable to perform mass refactoring analysis: {str(e)}"

    return state


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

def build_multi_scenario_graph() -> StateGraph:
    """
    Build the multi-scenario LangGraph workflow.

    Graph Structure:
        START
          |
          v
        [classify_intent]
          |
          v
        <route_by_intent> (conditional)
          |
          +-- onboarding_workflow
          +-- security_workflow
          +-- documentation_workflow
          +-- feature_dev_workflow
          +-- ... (10 more workflows)
          |
          v
        END
    """
    # Create graph
    workflow = StateGraph(MultiScenarioState)

    # Add nodes
    workflow.add_node("classify_intent", classify_intent_node)

    # Add scenario workflow nodes (Week 1 - implemented)
    workflow.add_node("onboarding_workflow", onboarding_workflow)
    workflow.add_node("documentation_workflow", documentation_workflow)
    workflow.add_node("feature_dev_workflow", feature_dev_workflow)

    # Add placeholder workflow nodes (Week 2-4)
    workflow.add_node("security_workflow", security_workflow)
    workflow.add_node("refactoring_workflow", refactoring_workflow)
    workflow.add_node("performance_workflow", performance_workflow)
    workflow.add_node("test_coverage_workflow", test_coverage_workflow)
    workflow.add_node("compliance_workflow", compliance_workflow)
    workflow.add_node("code_review_workflow", code_review_workflow)
    workflow.add_node("cross_repo_workflow", cross_repo_workflow)
    workflow.add_node("architecture_workflow", architecture_workflow)
    workflow.add_node("tech_debt_workflow", tech_debt_workflow)
    workflow.add_node("mass_refactoring_workflow", mass_refactoring_workflow)
    workflow.add_node("security_incident_workflow", security_incident_workflow)

    # Set entry point
    workflow.set_entry_point("classify_intent")

    # Add conditional edges from intent classifier to scenario workflows
    workflow.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "onboarding_workflow": "onboarding_workflow",
            "security_workflow": "security_workflow",
            "documentation_workflow": "documentation_workflow",
            "feature_dev_workflow": "feature_dev_workflow",
            "refactoring_workflow": "refactoring_workflow",
            "performance_workflow": "performance_workflow",
            "test_coverage_workflow": "test_coverage_workflow",
            "compliance_workflow": "compliance_workflow",
            "code_review_workflow": "code_review_workflow",
            "cross_repo_workflow": "cross_repo_workflow",
            "architecture_workflow": "architecture_workflow",
            "tech_debt_workflow": "tech_debt_workflow",
            "mass_refactoring_workflow": "mass_refactoring_workflow",
            "security_incident_workflow": "security_incident_workflow"
        }
    )

    # All workflows end at END
    for workflow_name in [
        "onboarding_workflow", "security_workflow", "documentation_workflow",
        "feature_dev_workflow", "refactoring_workflow", "performance_workflow",
        "test_coverage_workflow", "compliance_workflow", "code_review_workflow",
        "cross_repo_workflow", "architecture_workflow", "tech_debt_workflow",
        "mass_refactoring_workflow", "security_incident_workflow"
    ]:
        workflow.add_edge(workflow_name, END)

    # Compile graph
    return workflow.compile()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

class MultiScenarioCopilot:
    """
    Main interface for the multi-scenario copilot.

    Usage:
        copilot = MultiScenarioCopilot()
        result = copilot.run("What are the main subsystems?")
        print(result['answer'])
    """

    def __init__(self):
        self.graph = build_multi_scenario_graph()

    def run(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Run the multi-scenario workflow on a user query.

        Args:
            query: User's natural language question
            context: Optional context (file path, subsystem, etc.)

        Returns:
            Final state with answer, evidence, metadata
        """
        # Initialize state
        initial_state: MultiScenarioState = {
            'query': query,
            'context': context,
            'intent': None,
            'scenario_id': None,
            'confidence': None,
            'classification_method': None,
            'cpg_results': None,
            'subsystems': None,
            'methods': None,
            'call_graph': None,
            'answer': None,
            'evidence': None,
            'metadata': None,
            'error': None,
            'retry_count': 0
        }

        # Execute graph
        final_state = self.graph.invoke(initial_state)

        return final_state


if __name__ == "__main__":
    # Demo execution
    copilot = MultiScenarioCopilot()

    # Test queries for different scenarios
    test_queries = [
        "Give me an overview of the PostgreSQL executor",  # Onboarding
        "Generate documentation for the planner module",   # Documentation
        "Where should I add a new join algorithm?",        # Feature Dev
    ]

    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print(f"{'='*80}\n")

        result = copilot.run(query)

        print(f"Intent: {result.get('intent')}")
        print(f"Confidence: {result.get('confidence'):.2f}")
        print(f"Method: {result.get('classification_method')}\n")
        print(f"Answer:\n{result.get('answer')}\n")

        if result.get('evidence'):
            print(f"Evidence:")
            for evidence in result['evidence']:
                print(f"  - {evidence}")
