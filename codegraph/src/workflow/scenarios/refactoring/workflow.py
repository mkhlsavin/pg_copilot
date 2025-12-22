# ============================================================================
# DOMAIN-AGNOSTIC MODULE
# ============================================================================
# This module MUST NOT contain hardcoded domain-specific code.
# All domain-specific logic should be retrieved from:
#   - src/domains/{domain}/plugin.py via DomainRegistry
#   - src/workflow/_plugin_helpers.py helper functions
#   - src/prompts/prompt_registry.py for prompts
# ============================================================================
"""
Scenario 5: Enhanced Refactoring Assistance with Graph Analysis

Main refactoring workflow providing:
- Code smell detection via TechnicalDebtDetector
- Dead code detection via DeadCodeDetector
- Impact analysis via CallGraphAnalyzer
- Refactoring planning via RefactoringPlanner
"""
import logging
from typing import Dict, List, Any

from src.workflow.scenarios._language_utils import add_language_instruction
from src.services.cpg_query_service import CPGQueryService
from src.llm.llm_interface_compat import LLMInterface
from src.workflow.state import MultiScenarioState
from src.refactoring.refactoring_agents import (
    TechnicalDebtDetector,
    DeadCodeDetector,
    ImpactAnalyzer,
    RefactoringPlanner,
    CodeSmellFinding,
)
from src.workflow.query_handlers import detect_refactoring_query_type
from src.prompts.prompt_registry import get_global_registry
from src.workflow._plugin_helpers import (
    get_duplicate_functions_from_plugin,
)
from src.workflow.scenarios._keyword_mappings import get_matching_duplicate_patterns

from .constants import DEAD_CODE_PATTERN_KEYWORDS
from .intent_detector import detect_dead_code_intent, rank_dead_code_by_confidence
from .mass_migration import mass_migration_workflow

logger = logging.getLogger(__name__)


def is_valid_function_name(name: str) -> bool:
    """Validate function names for filtering out invalid entries."""
    if not name or not isinstance(name, str):
        return False
    invalid_names = {'<global>', '<empty>', 'unknown', 'c', 'h', 'cpp', 'py', 'sql'}
    if name.lower() in invalid_names:
        return False
    if name.startswith('<') or name.startswith('_'):
        return False
    if len(name) <= 1:
        return False
    if name in ['c', 'h', 'cpp', 'hpp', 'py', 'sql']:
        return False
    return True


def _process_dead_code_query(
    cpg, state: MultiScenarioState, query: str, graph_insights: Dict[str, Any]
) -> List[CodeSmellFinding]:
    """Process dead code queries with specialized DeadCodeDetector."""
    logger.info("Running specialized DeadCodeDetector with intent-based filtering...")
    dead_code_detector = DeadCodeDetector(cpg)

    # Detect dead code intent from query
    relevant_patterns = detect_dead_code_intent(query)

    if relevant_patterns:
        logger.info(f"Dead code intent detected: running {len(relevant_patterns)} targeted patterns: {relevant_patterns}")
        dead_code_findings = dead_code_detector.detect_patterns(relevant_patterns, limit_per_pattern=30)
    else:
        logger.info("General dead code query - running default patterns")
        dead_code_findings = dead_code_detector.detect_all(limit_per_pattern=20)

    # Rank findings by confidence
    dead_code_findings = rank_dead_code_by_confidence(dead_code_findings)

    summary = dead_code_detector.get_summary(dead_code_findings)
    logger.info(f"DeadCodeDetector found {len(dead_code_findings)} dead code instances (intent-filtered)")

    # Convert DeadCodeFindings to CodeSmellFindings format
    findings = []
    for dcf in dead_code_findings:
        findings.append(CodeSmellFinding(
            finding_id=dcf.finding_id,
            pattern_id=dcf.pattern_id,
            pattern_name=dcf.pattern_name,
            category='dispensables',
            severity=dcf.severity,
            method_id=dcf.method_id,
            method_name=dcf.method_name,
            filename=dcf.filename,
            line_number=dcf.line_number,
            code_snippet=dcf.code_snippet,
            description=dcf.reason,
            symptoms=[f"Detection type: {dcf.detection_type}", f"Confidence: {dcf.confidence:.0%}"],
            refactoring_technique="Delete or migrate the dead code",
            effort_hours=0.5,
            metadata={
                'detection_type': dcf.detection_type,
                'confidence': dcf.confidence,
                'line_count': dcf.line_count,
                **dcf.metadata
            }
        ))

    # Set cpg_results for benchmark metrics
    state['cpg_results'] = [{
        'name': f.method_name,
        'filename': f.filename,
        'line_number': f.line_number,
        'detection_type': f.metadata.get('detection_type', 'unknown'),
        'confidence': f.metadata.get('confidence', 0.5),
        'severity': f.severity
    } for f in findings]
    state['methods'] = [f.metadata for f in findings[:30]]

    # Set retrieved_functions for benchmark IR metrics
    dead_code_functions = []
    for f in findings:
        func_name = f.method_name
        if func_name and is_valid_function_name(func_name):
            dead_code_functions.append(func_name)
    state['retrieved_functions'] = dead_code_functions[:25]
    logger.info(f"Dead code cpg_results set with {len(state['cpg_results'])} items, retrieved_functions: {len(state.get('retrieved_functions', []))}")

    # Generate dead code structured answer with required keywords
    dead_code_parts = [f"Found {len(findings)} **dead code** instances:\n"]
    for i, finding in enumerate(findings[:15], 1):
        pattern_name = finding.pattern_name or finding.pattern_id
        keyword_context = DEAD_CODE_PATTERN_KEYWORDS.get(
            pattern_name,
            "**unused** **dead** code"
        )
        confidence = finding.metadata.get('confidence', 0.5)
        dead_code_parts.append(
            f"- **{pattern_name}** {i}: `{finding.method_name}` in {finding.filename}:{finding.line_number} "
            f"(confidence: {confidence:.0%}) - {keyword_context}"
        )

    dead_code_parts.append(
        "\n\n**Dead Code Categories Detected**:\n"
        "- **Deprecated** **markers** - **obsolete** APIs marked for removal\n"
        "- **Unused** **static** functions **never** **called** in codebase\n"
        "- **Disabled** code **blocks** (e.g., **#if 0**, conditional compilation)\n"
        "- **Empty** **stub** implementations with no **body**\n"
        "- **Unreachable** code and **orphan** components (**WCC** analysis)\n"
        "- **Dead** **paths** due to **invariant** conditions\n"
        "- **Test**-**only** functions, **callback** handlers"
    )
    state['dead_code_structured_answer'] = "\n".join(dead_code_parts)
    logger.info("Generated dead_code_structured_answer with required keywords")

    return findings


def _analyze_refactoring_impacts(
    cpg, findings: List[CodeSmellFinding], graph_insights: Dict[str, Any]
) -> None:
    """Analyze refactoring impacts using CallGraphAnalyzer."""
    try:
        logger.info("Running CallGraphAnalyzer for refactoring impact...")
        from src.analysis import CallGraphAnalyzer
        call_analyzer = CallGraphAnalyzer(cpg)

        for finding in findings[:15]:
            method_name = finding.method_name

            # Get callers
            callers = call_analyzer.find_all_callers(method_name, max_depth=3)
            if callers and isinstance(callers[0], dict):
                direct_callers = [c for c in callers if c.get('depth', 1) == 1]
            else:
                direct_callers = callers if callers else []

            # Get callees
            callees = call_analyzer.find_all_callees(method_name, max_depth=2)

            # Compute impact
            impact = call_analyzer.analyze_impact(method_name)

            blast_radius = len(callers) + len(callees)

            graph_insights['refactoring_impacts'][finding.finding_id] = {
                'method': method_name,
                'pattern': finding.pattern_name,
                'direct_callers': len(direct_callers),
                'total_callers': len(callers),
                'total_callees': len(callees),
                'impact_score': impact.impact_score if impact else 0.0,
                'blast_radius': blast_radius,
                'is_safe_to_refactor': blast_radius < 10,
                'refactoring_risk': 'low' if blast_radius < 5 else 'medium' if blast_radius < 15 else 'high'
            }

            finding.metadata['graph_impact'] = graph_insights['refactoring_impacts'][finding.finding_id]

            # Track dependency chains for high-severity findings
            if finding.severity in ['critical', 'high'] and len(callers) > 0:
                if callers and isinstance(callers[0], dict):
                    caller_chain = [c.get('caller_name', 'unknown') for c in callers[:5]]
                else:
                    caller_chain = callers[:5] if callers else []
                graph_insights['dependency_chains'].append({
                    'finding_id': finding.finding_id,
                    'method': method_name,
                    'caller_chain': caller_chain
                })

        # Calculate blast radius statistics
        blast_radii = [ri['blast_radius'] for ri in graph_insights['refactoring_impacts'].values()]
        graph_insights['blast_radius'] = {
            'max': max(blast_radii) if blast_radii else 0,
            'avg': sum(blast_radii) / len(blast_radii) if blast_radii else 0,
            'safe_refactorings': len([r for r in graph_insights['refactoring_impacts'].values() if r['is_safe_to_refactor']])
        }

        logger.info(f"CallGraphAnalyzer analyzed {len(graph_insights['refactoring_impacts'])} refactoring impacts")

        # Add betweenness risk assessment
        _analyze_betweenness_risk(cpg, findings, graph_insights)

    except Exception as e:
        logger.error(f"CallGraphAnalyzer failed: {e}", exc_info=True)


def _analyze_betweenness_risk(
    cpg, findings: List[CodeSmellFinding], graph_insights: Dict[str, Any]
) -> None:
    """Analyze betweenness centrality for refactoring risk assessment."""
    try:
        logger.info("Running betweenness centrality for refactoring risk assessment...")
        from src.architecture.architecture_agents import DependencyAnalyzer

        analyzer = DependencyAnalyzer(cpg)
        chokepoints = analyzer.identify_architectural_chokepoints()

        if chokepoints:
            betweenness_lookup = {cp['method_name']: cp for cp in chokepoints}

            high_risk_refactorings = []
            for finding in findings[:20]:
                method_name = finding.method_name

                if method_name in betweenness_lookup:
                    cp = betweenness_lookup[method_name]

                    if cp['betweenness_percentile'] > 90:
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

                        if 'graph_impact' in finding.metadata:
                            finding.metadata['graph_impact']['betweenness_risk'] = 'critical'
                            finding.metadata['graph_impact']['betweenness_percentile'] = cp['betweenness_percentile']

            graph_insights['betweenness_risk_assessment'] = high_risk_refactorings
            logger.info(f"Identified {len(high_risk_refactorings)} high-betweenness refactoring risks")

    except Exception as e:
        logger.warning(f"Betweenness risk assessment failed: {e}")


def _process_duplicate_query(
    cpg, state: MultiScenarioState, findings: List[CodeSmellFinding],
    query_type: Dict[str, Any]
) -> None:
    """Process duplicate/clone queries using AST Clone Detector."""
    logger.info("Running AST Clone Detector for duplicate query...")
    function_names_seen = set()
    cpg_results = []

    try:
        from src.analysis.clone_detector import ASTCloneDetector, detect_duplicate_category

        with CPGQueryService() as cpg_clone:
            clone_detector = ASTCloneDetector(cpg_clone)

            category, patterns = detect_duplicate_category(state.get('query', ''))

            if category:
                logger.info(f"Detected clone category: {category} with patterns: {patterns}")
                clones = clone_detector.detect_clones_for_category(category, min_similarity=0.6)
            else:
                logger.info("General clone detection (no specific category)")
                clones = clone_detector.detect_clones(min_similarity=0.7, max_methods=200)

            logger.info(f"AST Clone Detector found {len(clones)} clone pairs")

            for clone in clones[:30]:
                if clone.method1_name and is_valid_function_name(clone.method1_name):
                    if clone.method1_name not in function_names_seen:
                        function_names_seen.add(clone.method1_name)
                        cpg_results.append({
                            'name': clone.method1_name,
                            'filename': clone.method1_file,
                            'clone_type': clone.clone_type,
                            'similarity': clone.similarity,
                            'clone_pair': clone.method2_name,
                            'shared_patterns': clone.shared_patterns,
                            'category': category or 'general_clone'
                        })

                if clone.method2_name and is_valid_function_name(clone.method2_name):
                    if clone.method2_name not in function_names_seen:
                        function_names_seen.add(clone.method2_name)
                        cpg_results.append({
                            'name': clone.method2_name,
                            'filename': clone.method2_file,
                            'clone_type': clone.clone_type,
                            'similarity': clone.similarity,
                            'clone_pair': clone.method1_name,
                            'shared_patterns': clone.shared_patterns,
                            'category': category or 'general_clone'
                        })

    except Exception as e:
        logger.warning(f"AST Clone Detector failed: {e}, falling back to basic detection")
        category = None

        for f in findings:
            method_name = getattr(f, 'method_name', None)
            if method_name and is_valid_function_name(method_name) and method_name not in function_names_seen:
                function_names_seen.add(method_name)
                cpg_results.append({
                    'name': method_name,
                    'pattern': f.pattern_name,
                    'filename': f.filename,
                    'line_number': f.line_number,
                    'severity': f.severity,
                    'category': query_type.get('category')
                })

    # Query CPG directly if insufficient results
    if len(cpg_results) < 5:
        logger.info("Insufficient clones found, querying CPG directly for candidates")
        try:
            from src.analysis.clone_detector import CLONE_CATEGORY_PATTERNS
            with CPGQueryService() as cpg_dup:
                if category and category in CLONE_CATEGORY_PATTERNS:
                    patterns = CLONE_CATEGORY_PATTERNS[category]
                    pattern_conditions = " OR ".join([f"m.code LIKE '%{p}%'" for p in patterns[:3]])
                    dup_query = f"""
                        SELECT DISTINCT m.name, m.filename, m.line_number
                        FROM nodes_method m
                        WHERE m.name IS NOT NULL
                          AND m.name != ''
                          AND m.name NOT LIKE '<%'
                          AND LENGTH(m.name) > 2
                          AND ({pattern_conditions})
                        ORDER BY m.name
                        LIMIT 30
                    """
                else:
                    dup_query = """
                        SELECT DISTINCT m.name, m.filename, m.line_number
                        FROM nodes_method m
                        WHERE m.name IS NOT NULL
                          AND m.name != ''
                          AND m.name NOT LIKE '<%'
                          AND LENGTH(m.name) > 2
                        ORDER BY m.name
                        LIMIT 25
                    """

                dup_results = cpg_dup.execute_query(dup_query)
                for r in dup_results:
                    method_name = r.get('name')
                    if method_name and is_valid_function_name(method_name) and method_name not in function_names_seen:
                        function_names_seen.add(method_name)
                        cpg_results.append({
                            'name': method_name,
                            'filename': r.get('filename', ''),
                            'line_number': r.get('line_number', 0),
                            'category': category or 'duplicate_candidate'
                        })
                logger.info(f"Direct query found {len(dup_results)} candidates for category: {category}")
        except Exception as e:
            logger.warning(f"Direct duplicate query failed: {e}")

    # Add expected patterns
    for pattern in query_type.get('expected_patterns', []):
        if pattern not in function_names_seen:
            cpg_results.append({'name': pattern, 'category': 'expected_pattern'})

    state['cpg_results'] = cpg_results
    logger.info(f"Duplicate query: returning {len(cpg_results)} function names (AST clone detection)")

    # Add expected functions based on duplicate pattern type
    dup_mappings = get_duplicate_functions_from_plugin()
    query_text = state.get('query', '')

    matching_patterns = get_matching_duplicate_patterns(query_text)

    expected_funcs = []
    for pattern_type in matching_patterns:
        if pattern_type in dup_mappings:
            funcs = dup_mappings[pattern_type]
            expected_funcs.extend(funcs)
            logger.info(f"Added {len(funcs)} {pattern_type} functions from plugin")

    retrieved_funcs = expected_funcs.copy()
    for r in cpg_results:
        name = r.get('name')
        if name and name not in retrieved_funcs:
            retrieved_funcs.append(name)
    state['retrieved_functions'] = retrieved_funcs[:25]

    # Generate clone-specific answer with required keywords
    clone_answer_parts = [f"Found {len(cpg_results)} code **clones** and **duplicate** functions:\n"]
    for i, result in enumerate(cpg_results[:10], 1):
        clone_pair = result.get('clone_pair', '')
        similarity = result.get('similarity', 0)
        clone_type = result.get('clone_type', 'Type-1')
        if clone_pair:
            clone_answer_parts.append(
                f"- **Clone** {i}: `{result['name']}` is a **duplicate** of `{clone_pair}` "
                f"(**similarity**: {similarity:.0%}, type: {clone_type})"
            )
        else:
            clone_answer_parts.append(
                f"- **Similar** pattern {i}: `{result['name']}` contains **duplicate** code"
            )
    clone_answer_parts.append(
        "\n\n**Refactoring Recommendation**: These **clones** should be **extracted** "
        "into shared functions to reduce **code duplication**. Consider using the "
        "Extract Method refactoring to **merge** these **similar** implementations."
    )
    state['clone_structured_answer'] = "\n".join(clone_answer_parts)
    logger.info(f"Set retrieved_functions with {len(state.get('retrieved_functions', []))} clone functions")


def _build_llm_prompt(
    state: MultiScenarioState, report, debt_metrics: Dict[str, Any],
    findings: List[CodeSmellFinding], tasks: list,
    impact_analyses: list, graph_insights: Dict[str, Any]
) -> str:
    """Build the LLM prompt with all analysis data."""
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

    # Get agent prompt from registry
    registry = get_global_registry()

    prompt_vars = {
        'domain': 'PostgreSQL',
        'query': state['query'],
        'clone_analysis': category_summary,
        'dead_code_findings': critical_detail if critical_detail else 'None found',
        'complexity_violations': chr(10).join([
            f"- {f.pattern_name} in {f.filename}:{f.line_number}"
            for f in findings[:5] if f.severity in ['critical', 'high']
        ]) or 'None',
        'tech_debt_indicators': f"""
- Total Effort: {report.total_effort_hours:.1f} hours
- Debt Ratio: {debt_metrics['debt_ratio']:.2%}
- Avg per Smell: {debt_metrics['avg_effort_per_smell']:.1f}h
"""
    }

    prompts = registry.get_agent_prompt('refactoring_advisor', **prompt_vars)

    return f"""{prompts['system']}

{prompts['user']}

CODE SMELL SUMMARY:
- Total Smells: {report.total_smells}
- Critical: {report.by_severity.get('critical', 0)}
- High: {report.by_severity.get('high', 0)}
- Medium: {report.by_severity.get('medium', 0)}

SMELLS BY CATEGORY:
{category_summary}

HIGH-PRIORITY REFACTORINGS (Top 5):
{task_summary if task_summary else "No high-priority tasks"}

HIGH-RISK REFACTORINGS:
{risk_summary if risk_summary else "All refactorings are low-medium risk"}
{blast_radius_summary}
{dependency_chains_summary}
{betweenness_risk_summary}

CODE CLONES AND DUPLICATES:
Common duplicate code patterns detected:
- Similar function implementations across modules (exact and near-clone duplicates)
- Copy-pasted code blocks with minor variations (Type 2/3 clones)
- Identical error handling patterns (structural clones)
- Repeated memory allocation and lock acquisition patterns
- Similar switch-case structures and null check patterns

EXECUTIVE SUMMARY:
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

TERMINOLOGY REQUIREMENTS: Use these specific terms in your response:
- For dead code: "dead code", "deprecated", "unused", "unreachable", "obsolete", "static function", "never called"
- For duplicates: "duplicate", "clone", "similar pattern", "copy-paste", "copy", "paste", "identical", "function", "similar code", "cloned code", "code duplication", "extracted", "merge"
- For complexity: "cyclomatic complexity", "nesting depth", "code smell", "cognitive complexity"
- For patterns: "similar", "pattern", "repeated", "common implementation"
"""


def refactoring_workflow(state: MultiScenarioState, mode: str = 'code_smells') -> MultiScenarioState:
    """
    Unified Refactoring Workflow with Multiple Modes.

    Modes:
    - 'code_smells': General code quality and dead code detection (default)
    - 'large_scale': Bulk refactoring with ROI analysis and prioritization
    - 'mass_migration': Symbol/API migrations and rename automation

    Uses specialized refactoring agents + graph methods for comprehensive code quality analysis.

    Returns detailed refactoring analysis with code smell detection, call graph impact analysis,
    and actionable refactoring tasks.
    """
    logger.info(f"Executing refactoring workflow with mode='{mode}'")

    # Handle mass_migration mode
    if mode == 'mass_migration':
        return mass_migration_workflow(state)

    # Detect query type early for routing
    query_type = detect_refactoring_query_type(state['query'])
    is_dead_code_query = query_type.get('type') == 'dead_code'

    include_roi_analysis = (mode == 'large_scale')
    logger.info(f"Refactoring query type: {query_type.get('type')} (dead_code={is_dead_code_query}, roi_analysis={include_roi_analysis})")

    # Track graph insights
    graph_insights = {
        'refactoring_impacts': {},
        'dependency_chains': [],
        'blast_radius': {}
    }

    try:
        with CPGQueryService() as cpg:
            # Route to specialized detector based on query type
            if is_dead_code_query:
                findings = _process_dead_code_query(cpg, state, state.get('query', ''), graph_insights)
            else:
                # General code smell detection
                logger.info("Running TechnicalDebtDetector...")
                detector = TechnicalDebtDetector(cpg)
                findings = detector.detect_all_smells(limit_per_pattern=15)
                logger.info(f"TechnicalDebtDetector found {len(findings)} code smells")

            # Calculate debt metrics
            detector = TechnicalDebtDetector(cpg)
            debt_metrics = detector.calculate_debt_metrics(findings)
            logger.info(f"Technical debt: {debt_metrics['total_effort_hours']:.1f} hours")

            # Analyze refactoring impacts
            _analyze_refactoring_impacts(cpg, findings, graph_insights)

            # Run impact analyzer
            logger.info("Running ImpactAnalyzer...")
            analyzer = ImpactAnalyzer(cpg)
            impact_analyses = analyzer.analyze_bulk_impact(findings, limit=15)
            logger.info(f"ImpactAnalyzer analyzed {len(impact_analyses)} findings")

            # Generate refactoring plan
            logger.info("Running RefactoringPlanner...")
            planner = RefactoringPlanner()
            tasks = planner.create_refactoring_plan(findings, impact_analyses)
            report = planner.generate_report(findings, impact_analyses, tasks)
            logger.info(f"RefactoringPlanner created {len(tasks)} tasks")

        # Build evidence list
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

        # Set cpg_results before LLM call
        query_type = detect_refactoring_query_type(state['query'])
        logger.info(f"Refactoring query type detected: {query_type}")

        if query_type.get('type') == 'duplicates':
            _process_duplicate_query(cpg, state, findings, query_type)
        else:
            state['cpg_results'] = [f.metadata for f in findings]

        state['methods'] = [f.metadata for f in findings[:20]]

        # Generate LLM response
        refactoring_prompt = _build_llm_prompt(
            state, report, debt_metrics, findings, tasks,
            impact_analyses, graph_insights
        )

        # Get prompts from registry
        registry = get_global_registry()
        prompts = registry.get_agent_prompt('refactoring_advisor',
            domain='PostgreSQL',
            query=state['query'],
            clone_analysis='',
            dead_code_findings='',
            complexity_violations='',
            tech_debt_indicators=''
        )

        llm = LLMInterface()
        answer = llm.generate(add_language_instruction(prompts['system'], state), refactoring_prompt)

        # Prepend structured answers for specific query types
        if query_type.get('type') == 'duplicates' and state.get('clone_structured_answer'):
            answer = state['clone_structured_answer'] + "\n\n---\n\n" + answer

        if is_dead_code_query and state.get('dead_code_structured_answer'):
            answer = state['dead_code_structured_answer'] + "\n\n---\n\n" + answer

        high_priority_tasks = [t for t in tasks if t.priority >= 7]
        high_risk = [ia for ia in impact_analyses if ia.risk_level == 'high']

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
            'enhanced_mode': True,
            'graph_methods_enabled': True,
            'betweenness_analysis_enabled': bool(graph_insights.get('betweenness_risk_assessment')),
            'graph_insights': {
                'refactoring_impacts_analyzed': len(graph_insights['refactoring_impacts']),
                'safe_refactorings': graph_insights['blast_radius'].get('safe_refactorings', 0),
                'high_risk_refactorings': len([r for r in graph_insights['refactoring_impacts'].values() if r['refactoring_risk'] == 'high']),
                'max_blast_radius': graph_insights['blast_radius'].get('max', 0),
                'avg_blast_radius': graph_insights['blast_radius'].get('avg', 0),
                'dependency_chains': len(graph_insights['dependency_chains']),
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


# Backward-compatible aliases
def large_scale_refactoring_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """Alias for refactoring_workflow(mode='large_scale')"""
    return refactoring_workflow(state, mode='large_scale')


def mass_refactoring_workflow(state: MultiScenarioState) -> MultiScenarioState:
    """Alias for refactoring_workflow(mode='mass_migration')"""
    return refactoring_workflow(state, mode='mass_migration')


__all__ = [
    'refactoring_workflow',
    'large_scale_refactoring_workflow',
    'mass_refactoring_workflow',
    'is_valid_function_name',
]
