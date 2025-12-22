"""Fallback Enrichment for General Domain.

Contains aggressive keyword matching for when the domain is general.
"""
from typing import Dict, List


# Purpose mapping for keyword -> function purpose
PURPOSE_MAPPING = {
    'manage': 'utilities',
    'allocate': 'memory-management',
    'store': 'storage-access',
    'retrieve': 'storage-access',
    'process': 'utilities',
    'execute': 'query-execution',
    'optimize': 'query-planning',
    'maintain': 'utilities',
    'track': 'utilities',
    'monitor': 'utilities',
    'create': 'utilities',
    'delete': 'storage-access',
    'update': 'storage-access',
    'check': 'utilities',
    'validate': 'utilities',
    'convert': 'utilities',
    'format': 'utilities',
    'parse': 'parsing',
    'handle': 'error-handling',
    'error': 'error-handling',
    'exception': 'error-handling',
    'lock': 'concurrency-control',
    'transaction': 'transaction-control',
    'query': 'query-execution',
    'plan': 'query-planning',
    'network': 'networking',
    'connect': 'networking',
    'catalog': 'catalog-access',
    'wal': 'wal-logging',
    'log': 'wal-logging'
}

# Generic domain concepts
CONCEPT_KEYWORDS = {
    'transaction': 'mvcc',
    'buffer': 'mvcc',
    'cache': 'mvcc',
    'vacuum': 'vacuum',
    'parallel': 'parallelism',
    'replication': 'replication',
    'partition': 'partitioning',
    'extension': 'extension',
    'jit': 'jit'
}

# Generic data structures
STRUCTURE_KEYWORDS = {
    'buffer': 'buffer',
    'list': 'linked-list',
    'array': 'array',
    'hash': 'hash-table',
    'tree': 'binary-tree',
    'queue': 'queue',
    'relation': 'relation',
    'bitmap': 'bitmap'
}

# Generic param roles
PARAM_ROLE_KEYWORDS = {
    'buffer': 'buffer',
    'pointer': 'state-pointer',
    'context': 'transaction-context',
    'memory': 'memory-context',
    'size': 'size'
}

# Generic return kinds
RETURN_KIND_KEYWORDS = {
    'bool': 'boolean',
    'status': 'status-code',
    'error': 'error-code',
    'pointer': 'pointer'
}

# Generic variable roles
VAR_ROLE_KEYWORDS = {
    'buffer': 'buffer-manager',
    'state': 'state',
    'counter': 'counter',
    'iterator': 'iterator',
    'temporary': 'temporary'
}

# Generic data kinds
DATA_KIND_KEYWORDS = {
    'buffer': 'buffer',
    'relation': 'relation',
    'tuple': 'tuple',
    'transaction': 'transaction-id',
    'pointer': 'wal-pointer'
}


def _match_keywords_to_list(keyword_lower: List[str], mapping: Dict[str, str], target_list: List[str]) -> None:
    """Match keywords against a mapping and add to target list."""
    for keyword in keyword_lower:
        for key, value in mapping.items():
            if key in keyword:
                if value not in target_list:
                    target_list.append(value)


def general_domain_fallback(hints: Dict, keywords: List[str]) -> Dict:
    """
    Fallback enrichment for general domain using aggressive keyword matching.

    Args:
        hints: Current hints dictionary
        keywords: List of keywords from query analysis

    Returns:
        Enhanced hints dictionary with fallback values
    """
    keyword_lower = [k.lower() for k in keywords]

    # Add function purposes based on keywords
    _match_keywords_to_list(keyword_lower, PURPOSE_MAPPING, hints['function_purposes'])

    # If still no function purposes, add generic utilities
    if not hints['function_purposes']:
        hints['function_purposes'] = ['utilities', 'general']

    # Generic domain concepts
    for keyword, concept in CONCEPT_KEYWORDS.items():
        if any(keyword in kw for kw in keyword_lower):
            if concept not in hints['domain_concepts']:
                hints['domain_concepts'].append(concept)

    # Add generic MVCC if no domain concepts
    if not hints['domain_concepts']:
        hints['domain_concepts'] = ['mvcc', 'extension']

    # Add generic data structures
    for keyword, structure in STRUCTURE_KEYWORDS.items():
        if any(keyword in kw for kw in keyword_lower):
            if structure not in hints['data_structures']:
                hints['data_structures'].append(structure)

    # Add generic data structures if none found
    if not hints['data_structures']:
        hints['data_structures'] = ['array', 'hash-table', 'buffer']

    # Add generic param roles for better coverage
    for keyword, role in PARAM_ROLE_KEYWORDS.items():
        if any(keyword in kw for kw in keyword_lower):
            if role not in hints['param_roles']:
                hints['param_roles'].append(role)

    # Add generic return kinds
    for keyword, kind in RETURN_KIND_KEYWORDS.items():
        if any(keyword in kw for kw in keyword_lower):
            if kind not in hints['return_kinds']:
                hints['return_kinds'].append(kind)

    # Add generic variable roles
    for keyword, role in VAR_ROLE_KEYWORDS.items():
        if any(keyword in kw for kw in keyword_lower):
            if role not in hints['variable_roles']:
                hints['variable_roles'].append(role)

    # Add generic data kinds
    for keyword, kind in DATA_KIND_KEYWORDS.items():
        if any(keyword in kw for kw in keyword_lower):
            if kind not in hints['data_kinds']:
                hints['data_kinds'].append(kind)

    return hints


__all__ = ['general_domain_fallback']
