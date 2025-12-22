"""Keyword Matching for Enrichment Agent.

Contains keyword dictionaries and matching logic for enhancing
enrichment hints based on query keywords.
"""
from typing import Dict, List

# Known structures for data structure matching
KNOWN_STRUCTURES = ['btree', 'hash', 'list', 'array', 'tree', 'queue']

# Known PostgreSQL features
KNOWN_FEATURES = ['mvcc', 'wal', 'vacuum', 'toast', 'jsonb', 'parallel', 'partition']

# Type classification keywords
TYPE_KEYWORDS = {
    'struct': 'struct',
    'enum': 'enum',
    'typedef': 'typedef',
    'union': 'union'
}

# Type domain entities
ENTITY_KEYWORDS = {
    'relation': 'relation',
    'tuple': 'heap-tuple',
    'heap': 'heap-tuple',
    'buffer': 'buffer-desc',
    'wal': 'wal-record',
    'catalog': 'catalog-entry',
    'executor': 'executor-state',
    'index': 'index'
}

# Concurrency primitive keywords
PRIMITIVE_KEYWORDS = {
    'lock': 'lwlock',
    'spinlock': 'spinlock',
    'mutex': 'mutex',
    'semaphore': 'semaphore',
    'condition': 'condition-variable'
}

# Ownership keywords
OWNERSHIP_KEYWORDS = {
    'reference': 'reference-counted',
    'arena': 'arena-managed',
    'pinned': 'pinned-buffer',
    'copy-on-write': 'copy-on-write'
}

# Member role keywords
MEMBER_KEYWORDS = {
    'metadata': 'metadata',
    'counter': 'count',
    'flag': 'flag',
    'state': 'state',
    'reference': 'reference'
}

# Lock indicator keywords
LOCK_KEYWORDS = ['lock', 'mutex', 'spinlock', 'semaphore', 'lwlock']

# Pointer indicator keywords
POINTER_KEYWORDS = ['pointer', 'ptr', 'struct pointer', 'struct*']

# Length indicator keywords
LENGTH_KEYWORDS = ['length', 'size', 'count', 'capacity']

# Literal kind keywords
LITERAL_KIND_KEYWORDS = {
    'error': 'error-code',
    'mask': 'bit-mask',
    'flag': 'boolean-flag',
    'timeout': 'timeout',
    'magic': 'magic-number',
    'null': 'null-constant',
    'size': 'size-constant'
}

# Literal domain keywords
LITERAL_DOMAIN_KEYWORDS = {
    'transaction': 'transaction',
    'visibility': 'visibility',
    'buffer': 'buffer',
    'lock': 'lock',
    'wal': 'wal',
    'catalog': 'catalog',
    'error': 'error'
}

# Severity keywords
SEVERITY_KEYWORDS = ['warning', 'error', 'notice']

# Constant keywords
CONSTANT_KEYWORDS = {
    'errcode': 'ERRCODE_SYNTAX_ERROR',
    'invalidblocknumber': 'InvalidBlockNumber',
    'locktag': 'LOCKTAG_RELATION'
}

# Jump kind keywords
JUMP_KIND_KEYWORDS = {
    'retry': 'retry',
    'cleanup': 'cleanup',
    'dispatch': 'dispatch',
    'error handler': 'error-handler',
    'break': 'loop-break',
    'continue': 'loop-continue'
}

# Jump domain keywords
JUMP_DOMAIN_KEYWORDS = {
    'executor': 'executor',
    'storage': 'storage',
    'transaction': 'transaction',
    'planner': 'planner',
    'buffer': 'buffer'
}

# Modifier concurrency keywords
MODIFIER_CONCURRENCY_KEYWORDS = {
    'atomic': 'atomic-access',
    'volatile': 'volatile-access',
    'synchronized': 'synchronized',
    'thread local': 'thread-local'
}

# Modifier attribute keywords
MODIFIER_ATTRIBUTE_KEYWORDS = {
    'inline': 'inline',
    'noinline': 'noinline',
    'constexpr': 'constexpr',
    'readonly': 'readonly',
    'const ': 'const'
}

# Namespace layer keywords
NAMESPACE_LAYER_KEYWORDS = {
    'executor': 'executor',
    'planner': 'planner',
    'storage': 'storage',
    'catalog': 'catalog',
    'buffer': 'buffer',
}

# Namespace domain keywords
NAMESPACE_DOMAIN_KEYWORDS = {
    'extension': 'extension',
    'client': 'client',
    'server': 'server',
    'tools': 'tools',
    'config': 'configuration',
}

# Method ref kind keywords
METHOD_REF_KIND_KEYWORDS = {
    'callback': 'callback',
    'function pointer': 'function-pointer',
    'virtual': 'virtual-dispatch',
}

# Method ref usage keywords
METHOD_REF_USAGE_KEYWORDS = {
    'initializer': 'initializer',
    'cleanup': 'cleanup',
    'predicate': 'predicate',
    'comparator': 'comparator',
    'allocator': 'allocator',
}

# Data flow keywords
DATA_FLOW_KEYWORDS = {
    'lock': 'lock-propagation',
    'buffer': 'buffer-flow',
    'result': 'result-flow',
    'transaction': 'transaction-flow',
    'cost': 'cost-flow'
}

# Child role keywords
CHILD_ROLE_KEYWORDS = {
    'condition': 'condition',
    'body': 'body',
    'return': 'return'
}

# Call action keywords
CALL_ACTION_KEYWORDS = {
    'dispatch': 'dispatch',
    'initialize': 'initialize',
    'read': 'read',
    'write': 'write'
}

# Call side effect keywords
CALL_SIDE_EFFECT_KEYWORDS = {
    'state': 'state-change',
    'lock': 'lock-state',
    'io': 'io'
}

# Call receiver keywords
CALL_RECEIVER_KEYWORDS = {
    'handler': 'handler',
    'strategy': 'strategy',
    'manager': 'buffer-manager'
}

# Argument keywords
ARGUMENT_KEYWORDS = {
    'callback': 'callback',
    'state': 'state',
    'context': 'context',
    'buffer': 'buffer',
    'block': 'blockNumber'
}

# Branch keywords
BRANCH_KEYWORDS = {
    'retry': 'retry',
    'cleanup': 'cleanup',
    'error': 'error'
}

# Control reason keywords
CONTROL_REASON_KEYWORDS = {
    'deadlock': 'deadlock-avoidance',
    'validation': 'result-validation',
    'consistency': 'consistency-check'
}


def _match_keywords(keyword_lower: List[str], mapping: Dict[str, str], hints_list: List[str]) -> None:
    """Match keywords against a mapping and add to hints list."""
    for key, value in mapping.items():
        if any(key in kw for kw in keyword_lower):
            if value not in hints_list:
                hints_list.append(value)


def _match_any_keywords(keyword_lower: List[str], keywords: List[str]) -> bool:
    """Check if any of the keywords match any of the query keywords."""
    return any(any(kw_check in kw for kw_check in keywords) for kw in keyword_lower)


def enhance_with_keywords(hints: Dict, keywords: List[str]) -> Dict:
    """
    Enhance hints with keyword-based matching.

    Args:
        hints: Current hints dictionary
        keywords: List of keywords from query analysis

    Returns:
        Enhanced hints dictionary
    """
    keyword_lower = [k.lower() for k in keywords]

    # Check for specific data structures
    for structure in KNOWN_STRUCTURES:
        if any(structure in kw for kw in keyword_lower):
            if structure not in hints['data_structures']:
                hints['data_structures'].append(structure)

    # Check for specific features
    for feature in KNOWN_FEATURES:
        if any(feature in kw for kw in keyword_lower):
            if feature.upper() not in hints['features']:
                hints['features'].append(feature.upper())

    # Type classification
    _match_keywords(keyword_lower, TYPE_KEYWORDS, hints['type_categories'])

    # Type domain entities
    _match_keywords(keyword_lower, ENTITY_KEYWORDS, hints['type_domain_entities'])

    # Concurrency primitives
    _match_keywords(keyword_lower, PRIMITIVE_KEYWORDS, hints['type_concurrency_primitives'])

    # Ownership keywords
    _match_keywords(keyword_lower, OWNERSHIP_KEYWORDS, hints['type_ownership_models'])

    # Member roles
    _match_keywords(keyword_lower, MEMBER_KEYWORDS, hints['member_roles'])

    # Lock indicators
    if _match_any_keywords(keyword_lower, LOCK_KEYWORDS):
        if 'true' not in hints['is_locks']:
            hints['is_locks'].append('true')

    # Pointer indicators
    if _match_any_keywords(keyword_lower, POINTER_KEYWORDS):
        if 'true' not in hints['is_pointer_to_structs']:
            hints['is_pointer_to_structs'].append('true')
        if 'true' not in hints['member_pointers']:
            hints['member_pointers'].append('true')

    # Length indicators
    if _match_any_keywords(keyword_lower, LENGTH_KEYWORDS):
        if 'true' not in hints['member_length_fields']:
            hints['member_length_fields'].append('true')

    # Literal patterns
    _match_keywords(keyword_lower, LITERAL_KIND_KEYWORDS, hints['literal_kinds'])
    _match_keywords(keyword_lower, LITERAL_DOMAIN_KEYWORDS, hints['literal_domains'])

    # Severities
    for sev in SEVERITY_KEYWORDS:
        if any(sev in kw for kw in keyword_lower):
            if sev not in hints['literal_severities']:
                hints['literal_severities'].append(sev)

    # Null constants
    if any('null' in kw for kw in keyword_lower):
        if 'true' not in hints['is_null_constants']:
            hints['is_null_constants'].append('true')

    # Bitmasks
    if any('mask' in kw for kw in keyword_lower):
        if 'true' not in hints['is_bitmasks']:
            hints['is_bitmasks'].append('true')

    # Constants
    _match_keywords(keyword_lower, CONSTANT_KEYWORDS, hints['literal_constants'])

    # Lock constants
    if any('lock constant' in kw or 'locktag' in kw for kw in keyword_lower):
        if 'true' not in hints['is_lock_constants']:
            hints['is_lock_constants'].append('true')

    # Jump-related
    _match_keywords(keyword_lower, JUMP_KIND_KEYWORDS, hints['jump_kinds'])
    _match_keywords(keyword_lower, JUMP_DOMAIN_KEYWORDS, hints['jump_domains'])

    if any('loop' in kw for kw in keyword_lower):
        if 'loop' not in hints['jump_scopes']:
            hints['jump_scopes'].append('loop')

    # Modifier concurrency
    _match_keywords(keyword_lower, MODIFIER_CONCURRENCY_KEYWORDS, hints['modifier_concurrencies'])
    _match_keywords(keyword_lower, MODIFIER_ATTRIBUTE_KEYWORDS, hints['modifier_attributes'])

    # Namespace & reference
    _match_keywords(keyword_lower, NAMESPACE_LAYER_KEYWORDS, hints['namespace_layers'])
    _match_keywords(keyword_lower, NAMESPACE_DOMAIN_KEYWORDS, hints['namespace_domains'])
    _match_keywords(keyword_lower, METHOD_REF_KIND_KEYWORDS, hints['method_ref_kinds'])
    _match_keywords(keyword_lower, METHOD_REF_USAGE_KEYWORDS, hints['method_ref_usages'])

    # Data flow & edge
    _match_keywords(keyword_lower, DATA_FLOW_KEYWORDS, hints['data_flow_kinds'])
    _match_keywords(keyword_lower, CHILD_ROLE_KEYWORDS, hints['child_roles'])
    _match_keywords(keyword_lower, CALL_ACTION_KEYWORDS, hints['call_actions'])
    _match_keywords(keyword_lower, CALL_SIDE_EFFECT_KEYWORDS, hints['call_side_effects'])
    _match_keywords(keyword_lower, CALL_RECEIVER_KEYWORDS, hints['call_receiver_roles'])
    _match_keywords(keyword_lower, ARGUMENT_KEYWORDS, hints['argument_param_names'])
    _match_keywords(keyword_lower, BRANCH_KEYWORDS, hints['branch_kinds'])
    _match_keywords(keyword_lower, CONTROL_REASON_KEYWORDS, hints['control_reasons'])

    return hints


__all__ = ['enhance_with_keywords']
