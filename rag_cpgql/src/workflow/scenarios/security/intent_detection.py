"""
Security Intent Detection Module.

Provides functions for detecting security-related intent from user queries.
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


# ===== PHASE 2 IMPROVEMENT: Intent-Based Security Pattern Filtering =====
# Maps query keywords to relevant security patterns for targeted scanning

SECURITY_INTENT_MAP = {
    # Injection vulnerabilities
    'sql injection': ['SQL_INJECTION', 'TAINTED_INPUT'],
    'sql': ['SQL_INJECTION', 'TAINTED_INPUT'],
    'command injection': ['COMMAND_INJECTION', 'EXEC_PATH_INJECTION'],
    'command': ['COMMAND_INJECTION', 'EXEC_PATH_INJECTION'],
    'injection': ['SQL_INJECTION', 'COMMAND_INJECTION', 'LOG_INJECTION', 'TAINTED_INPUT'],
    'log injection': ['LOG_INJECTION'],

    # Memory vulnerabilities
    'buffer overflow': ['BUFFER_OVERFLOW_STRCPY', 'BUFFER_OVERFLOW_SPRINTF', 'ARRAY_BOUNDS'],
    'buffer': ['BUFFER_OVERFLOW_STRCPY', 'BUFFER_OVERFLOW_SPRINTF', 'ARRAY_BOUNDS'],
    'memory': ['USE_AFTER_FREE', 'DOUBLE_FREE', 'MEMORY_LEAK', 'NULL_POINTER_DEREFERENCE'],
    'use after free': ['USE_AFTER_FREE'],
    'use-after-free': ['USE_AFTER_FREE'],
    'double free': ['DOUBLE_FREE'],
    'memory leak': ['MEMORY_LEAK', 'RESOURCE_LEAK'],
    'null': ['NULL_POINTER_DEREFERENCE'],
    'dereference': ['NULL_POINTER_DEREFERENCE'],
    'null pointer': ['NULL_POINTER_DEREFERENCE'],

    # S15 New Vulnerability Types
    'integer overflow': ['INTEGER_OVERFLOW'],
    'overflow': ['INTEGER_OVERFLOW', 'BUFFER_OVERFLOW_STRCPY', 'BUFFER_OVERFLOW_SPRINTF'],
    'format string': ['FORMAT_STRING'],
    'array bounds': ['ARRAY_BOUNDS'],
    'array index': ['ARRAY_BOUNDS'],
    'type confusion': ['TYPE_CONFUSION'],
    'uninitialized': ['UNINITIALIZED_VAR'],
    'timing': ['RACE_CONDITION', 'FILE_RACE'],
    'side channel': ['RACE_CONDITION'],
    'side-channel': ['RACE_CONDITION'],
    'privilege escalation': ['PRIV_ESCALATION', 'MISSING_AUTH'],
    'symlink': ['FILE_RACE', 'RACE_CONDITION'],
    'signal': ['RACE_CONDITION'],
    'deserialization': ['INSECURE_DESERIALIZATION'],
    'denial of service': ['RESOURCE_LEAK', 'INTEGER_OVERFLOW'],
    'dos': ['RESOURCE_LEAK', 'INTEGER_OVERFLOW'],
    'information disclosure': ['CLEARTEXT_STORAGE', 'HARDCODED_SECRETS'],
    'xxe': ['XXE'],
    'xml': ['XXE'],
    'logic': ['MISSING_AUTH', 'PRIV_ESCALATION'],
    'memory corruption': ['USE_AFTER_FREE', 'BUFFER_OVERFLOW_STRCPY', 'DOUBLE_FREE'],
    'container escape': ['PATH_TRAVERSAL', 'EXEC_PATH_INJECTION'],
    'api misuse': ['TAINTED_INPUT', 'MISSING_AUTH'],
    'supply chain': ['EXEC_PATH_INJECTION', 'COMMAND_INJECTION'],
    'zero day': ['BUFFER_OVERFLOW_STRCPY', 'USE_AFTER_FREE', 'INTEGER_OVERFLOW'],
    'zero-day': ['BUFFER_OVERFLOW_STRCPY', 'USE_AFTER_FREE', 'INTEGER_OVERFLOW'],
    'cve': ['SQL_INJECTION', 'BUFFER_OVERFLOW_STRCPY', 'USE_AFTER_FREE'],

    # Authentication/Authorization
    'authentication': ['MISSING_AUTH', 'HARDCODED_SECRETS'],
    'auth': ['MISSING_AUTH', 'HARDCODED_SECRETS'],
    'hardcoded': ['HARDCODED_SECRETS'],
    'secret': ['HARDCODED_SECRETS', 'INSUFFICIENT_ENTROPY'],
    'password': ['HARDCODED_SECRETS', 'CLEARTEXT_STORAGE'],
    'credential': ['HARDCODED_SECRETS', 'CLEARTEXT_STORAGE'],

    # Cryptography
    'crypto': ['WEAK_CRYPTO', 'INSUFFICIENT_ENTROPY'],
    'cryptography': ['WEAK_CRYPTO', 'INSUFFICIENT_ENTROPY'],
    'encryption': ['WEAK_CRYPTO', 'CLEARTEXT_STORAGE'],
    'hash': ['WEAK_CRYPTO'],
    'random': ['INSUFFICIENT_ENTROPY'],
    'entropy': ['INSUFFICIENT_ENTROPY'],

    # Path/File vulnerabilities
    'path traversal': ['PATH_TRAVERSAL'],
    'path': ['PATH_TRAVERSAL', 'EXEC_PATH_INJECTION'],
    'file': ['PATH_TRAVERSAL', 'FILE_RACE'],
    'directory': ['PATH_TRAVERSAL'],

    # Race conditions
    'race condition': ['RACE_CONDITION', 'FILE_RACE'],
    'race': ['RACE_CONDITION', 'FILE_RACE'],
    'toctou': ['FILE_RACE', 'RACE_CONDITION'],
    'time of check': ['FILE_RACE', 'RACE_CONDITION'],

    # Information disclosure
    'sensitive': ['CLEARTEXT_STORAGE', 'HARDCODED_SECRETS'],
    'disclosure': ['CLEARTEXT_STORAGE', 'HARDCODED_SECRETS'],

    # Input validation
    'input validation': ['TAINTED_INPUT'],
    'validation': ['TAINTED_INPUT'],
    'input': ['TAINTED_INPUT', 'SQL_INJECTION'],

    # Generic/Broad queries
    'vulnerability': None,  # Fall back to all patterns
    'vulnerabilities': None,
    'security': None,
    'audit': None,

    # D3FEND Source Code Hardening queries
    'hardening': None,  # Triggers HardeningScanner
    'd3fend': None,  # Triggers HardeningScanner
    'initialization': ['UNINITIALIZED_VAR'],  # D3-VI
    'credential scrubbing': ['HARDCODED_SECRETS', 'CLEARTEXT_STORAGE'],  # D3-CS
    'null check': ['NULL_POINTER_DEREFERENCE'],  # D3-NPC
    'unsafe function': ['BUFFER_OVERFLOW_STRCPY', 'BUFFER_OVERFLOW_SPRINTF'],  # D3-TL
    'trusted library': ['BUFFER_OVERFLOW_STRCPY', 'BUFFER_OVERFLOW_SPRINTF'],  # D3-TL
    'pointer validation': ['NULL_POINTER_DEREFERENCE'],  # D3-PV
    'reference nullification': ['USE_AFTER_FREE', 'DOUBLE_FREE'],  # D3-RN
    'integer range': ['INTEGER_OVERFLOW'],  # D3-IRV
    'memory safety': ['USE_AFTER_FREE', 'DOUBLE_FREE', 'BUFFER_OVERFLOW_STRCPY'],  # D3-MBSV
    'compliance': None,  # Triggers HardeningScanner for compliance score
}


def detect_security_intent(query: str) -> Optional[List[str]]:
    """
    Detect security intent from query and return relevant patterns.

    Args:
        query: User's security query

    Returns:
        List of relevant pattern names, or None to run all patterns
    """
    query_lower = query.lower()
    matched_patterns = set()
    has_broad_term = False

    # Check each intent keyword (sorted by length desc for longest match first)
    # This ensures "sql injection" matches before just "sql"
    sorted_intents = sorted(SECURITY_INTENT_MAP.keys(), key=len, reverse=True)

    for intent in sorted_intents:
        patterns = SECURITY_INTENT_MAP[intent]
        # Check if intent is in query (handles multi-word intents)
        if intent in query_lower:
            if patterns is None:
                # Mark that we found a broad term, but continue checking for specific patterns
                has_broad_term = True
            else:
                matched_patterns.update(patterns)

    # If we found specific patterns, return them (even if broad term was also present)
    if matched_patterns:
        return list(matched_patterns)

    # If only broad terms found, return None to run all patterns
    if has_broad_term:
        return None

    # Default to None (all patterns) if no specific intent detected
    return None


def detect_hardening_intent(query: str) -> bool:
    """
    Detect if the query is about D3FEND hardening or compliance.

    Args:
        query: User's security query

    Returns:
        True if the query is about hardening/D3FEND compliance
    """
    query_lower = query.lower()
    hardening_keywords = [
        'hardening', 'd3fend', 'compliance', 'defensive',
        'initialization check', 'null check', 'credential scrub',
        'trusted library', 'reference nullification', 'pointer validation',
        'integer range validation', 'memory block validation',
        'variable type validation', 'domain logic validation',
        'operational logic validation', 'cwe-457', 'cwe-798', 'cwe-190',
        'cwe-416', 'cwe-676', 'cwe-476'
    ]
    return any(keyword in query_lower for keyword in hardening_keywords)
