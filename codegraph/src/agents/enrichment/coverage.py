"""Coverage Calculation for Enrichment Agent.

Calculates how well the hints cover different enrichment layers.
"""
from typing import Dict


# List of all hint keys that count toward coverage
COVERAGE_KEYS = [
    # Base categories (5)
    'function_purposes',
    'data_structures',
    'algorithms',
    'domain_concepts',
    'features',
    # Category 1: Parameter & Return (4)
    'param_roles',
    'return_kinds',
    'return_outcomes',
    'validation_required',
    # Category 2: Variable & Identifier (7)
    'variable_roles',
    'data_kinds',
    'security_sensitivities',
    'lifetimes',
    'mutabilities',
    'is_locks',
    'is_pointer_to_structs',
    # Category 3: Type & Member (7)
    'type_categories',
    'type_domain_entities',
    'type_concurrency_primitives',
    'type_ownership_models',
    'member_roles',
    'member_pointers',
    'member_length_fields',
    # Category 4: Literal & Constant (7)
    'literal_kinds',
    'literal_domains',
    'literal_severities',
    'is_null_constants',
    'is_bitmasks',
    'literal_constants',
    'is_lock_constants',
    # Category 5: Control Flow & Jump (5)
    'jump_kinds',
    'jump_domains',
    'jump_scopes',
    'modifier_concurrencies',
    'modifier_attributes',
    # Category 6: Namespace & Reference (4)
    'namespace_layers',
    'namespace_domains',
    'method_ref_kinds',
    'method_ref_usages',
    # Category 7: Data Flow & Edge (8)
    'data_flow_kinds',
    'child_roles',
    'call_actions',
    'call_side_effects',
    'call_receiver_roles',
    'argument_param_names',
    'branch_kinds',
    'control_reasons',
]


def calculate_coverage(hints: Dict) -> float:
    """
    Calculate how well the hints cover different enrichment layers.

    Args:
        hints: Dictionary of enrichment hints

    Returns:
        Score 0-1 based on VALID CPG tag categories only.
    """
    layers_with_hints = 0
    total_layers = len(COVERAGE_KEYS)  # 47 layers

    for key in COVERAGE_KEYS:
        if hints.get(key):
            layers_with_hints += 1

    return layers_with_hints / total_layers


__all__ = ['calculate_coverage', 'COVERAGE_KEYS']
