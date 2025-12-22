"""Tag Filter Generation for Enrichment Agent.

Generates SQL filter suggestions based on enrichment hints.
"""
from typing import Dict, List


def _add_filters_for_category(
    filters: List[Dict],
    hints: Dict,
    hint_key: str,
    tag_name: str
) -> None:
    """Add filters for a specific category."""
    for value in hints.get(hint_key, []):
        filters.append({
            'tag_name': tag_name,
            'tag_value': value,
            'query_fragment': f"name ILIKE '%{value}%'"
        })


def generate_tag_filters(hints: Dict) -> List[Dict]:
    """
    Generate SQL tag filter suggestions.

    Args:
        hints: Dictionary of enrichment hints

    Returns:
        List of tag filters for use in SQL queries like:
        SELECT name FROM nodes_method WHERE name ILIKE '%memory%'
    """
    filters = []

    # Function purpose filters
    _add_filters_for_category(filters, hints, 'function_purposes', 'function-purpose')

    # Data structure filters
    _add_filters_for_category(filters, hints, 'data_structures', 'data-structure')

    # Domain concept filters
    _add_filters_for_category(filters, hints, 'domain_concepts', 'domain-concept')

    # Feature filters
    _add_filters_for_category(filters, hints, 'features', 'Feature')

    # Category 1: Parameter & Return filters
    _add_filters_for_category(filters, hints, 'param_roles', 'param-role')
    _add_filters_for_category(filters, hints, 'return_kinds', 'return-kind')
    _add_filters_for_category(filters, hints, 'return_outcomes', 'return-outcome')

    # Category 2: Variable & Identifier filters
    _add_filters_for_category(filters, hints, 'variable_roles', 'variable-role')
    _add_filters_for_category(filters, hints, 'data_kinds', 'data-kind')
    _add_filters_for_category(filters, hints, 'security_sensitivities', 'security-sensitivity')
    _add_filters_for_category(filters, hints, 'is_locks', 'is-lock')
    _add_filters_for_category(filters, hints, 'is_pointer_to_structs', 'is-pointer-to-struct')

    # Category 3: Type & Member filters
    _add_filters_for_category(filters, hints, 'type_categories', 'type-category')
    _add_filters_for_category(filters, hints, 'type_domain_entities', 'type-domain-entity')
    _add_filters_for_category(filters, hints, 'type_concurrency_primitives', 'type-concurrency-primitive')
    _add_filters_for_category(filters, hints, 'type_ownership_models', 'type-ownership-model')
    _add_filters_for_category(filters, hints, 'member_roles', 'member-role')
    _add_filters_for_category(filters, hints, 'member_pointers', 'member-pointer')
    _add_filters_for_category(filters, hints, 'member_length_fields', 'member-length-field')

    # Category 4: Literal & Constant filters
    _add_filters_for_category(filters, hints, 'literal_kinds', 'literal-kind')
    _add_filters_for_category(filters, hints, 'literal_domains', 'literal-domain')
    _add_filters_for_category(filters, hints, 'literal_severities', 'literal-severity')
    _add_filters_for_category(filters, hints, 'is_null_constants', 'is-null-constant')
    _add_filters_for_category(filters, hints, 'is_bitmasks', 'is-bitmask')
    _add_filters_for_category(filters, hints, 'literal_constants', 'literal-constant')
    _add_filters_for_category(filters, hints, 'is_lock_constants', 'is-lock-constant')

    # Category 5: Control Flow & Jump
    _add_filters_for_category(filters, hints, 'jump_kinds', 'jump-kind')
    _add_filters_for_category(filters, hints, 'jump_domains', 'jump-domain')
    _add_filters_for_category(filters, hints, 'jump_scopes', 'jump-scope')
    _add_filters_for_category(filters, hints, 'modifier_concurrencies', 'modifier-concurrency')
    _add_filters_for_category(filters, hints, 'modifier_attributes', 'modifier-attribute')

    # Category 6: Namespace & Reference
    _add_filters_for_category(filters, hints, 'namespace_layers', 'namespace-layer')
    _add_filters_for_category(filters, hints, 'namespace_domains', 'namespace-domain')
    _add_filters_for_category(filters, hints, 'method_ref_kinds', 'method-ref-kind')
    _add_filters_for_category(filters, hints, 'method_ref_usages', 'method-ref-usage')

    # Category 7: Data Flow & Edge
    _add_filters_for_category(filters, hints, 'data_flow_kinds', 'data-flow-kind')
    _add_filters_for_category(filters, hints, 'child_roles', 'child-role')
    _add_filters_for_category(filters, hints, 'call_actions', 'call-action')
    _add_filters_for_category(filters, hints, 'call_side_effects', 'call-side-effect')
    _add_filters_for_category(filters, hints, 'call_receiver_roles', 'call-receiver-role')
    _add_filters_for_category(filters, hints, 'argument_param_names', 'argument-param-name')
    _add_filters_for_category(filters, hints, 'branch_kinds', 'branch-kind')
    _add_filters_for_category(filters, hints, 'control_reasons', 'control-reason')

    return filters


__all__ = ['generate_tag_filters']
