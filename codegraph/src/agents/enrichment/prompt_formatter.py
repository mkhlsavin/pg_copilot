"""Prompt Formatting for Enrichment Agent.

Contains functions for formatting enrichment hints for LLM prompts.
"""
from typing import Dict, List


def format_for_prompt(hints: Dict) -> str:
    """
    Format enrichment hints for inclusion in LLM prompt.

    Args:
        hints: Dictionary of enrichment hints

    Returns:
        Formatted string for prompt context (ONLY valid CPG tag categories).
    """
    sections = []

    if hints.get('features'):
        sections.append(f"PostgreSQL Features: {', '.join(hints['features'])}")

    if hints.get('function_purposes'):
        sections.append(f"Function Purposes: {', '.join(hints['function_purposes'])}")

    if hints.get('data_structures'):
        sections.append(f"Data Structures: {', '.join(hints['data_structures'])}")

    if hints.get('domain_concepts'):
        sections.append(f"Domain Concepts: {', '.join(hints['domain_concepts'])}")

    if hints.get('member_pointers'):
        sections.append(f"Member Pointers: {', '.join(hints['member_pointers'])}")

    if hints.get('member_length_fields'):
        sections.append(f"Member Length Fields: {', '.join(hints['member_length_fields'])}")

    if hints.get('literal_kinds'):
        sections.append(f"Literal Kinds: {', '.join(hints['literal_kinds'])}")

    if hints.get('literal_domains'):
        sections.append(f"Literal Domains: {', '.join(hints['literal_domains'])}")

    if hints.get('literal_severities'):
        sections.append(f"Literal Severities: {', '.join(hints['literal_severities'])}")

    if hints.get('literal_constants'):
        sections.append(f"Literal Constants: {', '.join(hints['literal_constants'])}")

    if hints.get('is_lock_constants'):
        sections.append(f"Lock Constants: {', '.join(hints['is_lock_constants'])}")

    if hints.get('data_flow_kinds'):
        sections.append(f"Data Flow: {', '.join(hints['data_flow_kinds'])}")

    if hints.get('child_roles'):
        sections.append(f"Child Roles: {', '.join(hints['child_roles'])}")

    if hints.get('call_actions'):
        sections.append(f"Call Actions: {', '.join(hints['call_actions'])}")

    if hints.get('call_side_effects'):
        sections.append(f"Call Side Effects: {', '.join(hints['call_side_effects'])}")

    if hints.get('call_receiver_roles'):
        sections.append(f"Call Receiver Roles: {', '.join(hints['call_receiver_roles'])}")

    if hints.get('argument_param_names'):
        sections.append(f"Argument to Param: {', '.join(hints['argument_param_names'])}")

    if hints.get('branch_kinds'):
        sections.append(f"Branch Kinds: {', '.join(hints['branch_kinds'])}")

    if hints.get('control_reasons'):
        sections.append(f"Control Reasons: {', '.join(hints['control_reasons'])}")

    if hints.get('jump_kinds'):
        sections.append(f"Jump Kinds: {', '.join(hints['jump_kinds'])}")

    if hints.get('jump_domains'):
        sections.append(f"Jump Domains: {', '.join(hints['jump_domains'])}")

    if hints.get('jump_scopes'):
        sections.append(f"Jump Scopes: {', '.join(hints['jump_scopes'])}")

    if hints.get('modifier_concurrencies'):
        sections.append(f"Concurrency Modifiers: {', '.join(hints['modifier_concurrencies'])}")

    if hints.get('modifier_attributes'):
        sections.append(f"Attributes: {', '.join(hints['modifier_attributes'])}")

    if hints.get('namespace_layers'):
        sections.append(f"Namespace Layers: {', '.join(hints['namespace_layers'])}")

    if hints.get('namespace_domains'):
        sections.append(f"Namespace Domains: {', '.join(hints['namespace_domains'])}")

    if hints.get('method_ref_kinds'):
        sections.append(f"Method Ref Kinds: {', '.join(hints['method_ref_kinds'])}")

    if hints.get('method_ref_usages'):
        sections.append(f"Method Ref Usage: {', '.join(hints['method_ref_usages'])}")

    # Add example tag usage
    if hints.get('tags'):
        sections.append("\nExample tag-based SQL queries:")
        for i, tag in enumerate(hints['tags'][:3], 1):  # Show top 3
            tag_value = tag.get('tag_value', '')
            example = f"SELECT name FROM nodes_method WHERE name ILIKE '%{tag_value}%'"
            sections.append(f"  {i}. {example}")

    return '\n'.join(sections)


def get_example_queries(hints: Dict, limit: int = 5) -> List[str]:
    """
    Generate example SQL queries using enrichment tags.

    Args:
        hints: Enrichment hints
        limit: Maximum number of examples

    Returns:
        List of example SQL queries
    """
    examples = []

    # Generate queries for each tag type
    for tag in hints.get('tags', [])[:limit]:
        tag_name = tag.get('tag_name', '')
        tag_value = tag.get('tag_value', '')

        # Different query patterns based on tag type
        if tag_name == 'function-purpose':
            query = f"SELECT name, file_name FROM nodes_method WHERE name ILIKE '%{tag_value}%' LIMIT 10"
        elif tag_name == 'data-structure':
            query = f"SELECT name, file_name FROM nodes_method WHERE name ILIKE '%{tag_value}%' LIMIT 10"
        elif tag_name == 'Feature':
            query = f"SELECT DISTINCT file_name FROM nodes_method WHERE file_name ILIKE '%{tag_value}%' LIMIT 10"
        else:
            query = f"SELECT name, file_name, line_number FROM nodes_method WHERE name ILIKE '%{tag_value}%' LIMIT 10"

        examples.append(query)

    return examples


__all__ = ['format_for_prompt', 'get_example_queries']
