"""
Scenario 13: Mass Refactoring Automation
"""

import logging
from typing import Dict, List, Any, Optional

from src.services.cpg_query_service import CPGQueryService
from src.llm.llm_interface_compat import LLMInterface
from src.workflow.state import MultiScenarioState

logger = logging.getLogger(__name__)

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




__all__ = ['mass_refactoring_workflow']
