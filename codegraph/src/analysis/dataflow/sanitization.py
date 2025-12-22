"""Sanitization Detection for Data Flow Analysis.

Sanitization confidence scoring and pattern matching.
"""
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Minimum confidence threshold for considering path "sanitized"
SANITIZATION_CONFIDENCE_THRESHOLD = 0.7

# Generic sanitization confidence patterns
_GENERIC_SANITIZATION_CONFIDENCE = {
    # High confidence (1.0) - Strong, proper sanitization
    'parameterize': 1.0,
    'prepare': 1.0,
    'bind': 1.0,
    'bind_param': 1.0,
    'placeholder': 1.0,

    # High confidence (0.9) - Database-specific escaping
    'pg_escape_string': 0.9,
    'pg_escape_bytea': 0.9,
    'mysqli_real_escape_string': 0.9,
    'mysql_real_escape_string': 0.9,
    'htmlspecialchars': 0.9,
    'htmlentities': 0.9,

    # Medium-high confidence (0.8) - Context-specific validation
    'validate_%': 0.8,
    'verify_%': 0.8,
    'is_valid_%': 0.8,
    'check_type': 0.8,
    'whitelist': 0.8,
    'allowlist': 0.8,

    # Medium confidence (0.7) - Generic escaping/encoding
    'escape_%': 0.7,
    'sanitize_%': 0.7,
    'encode_%': 0.7,
    'urlencode': 0.7,
    'base64_encode': 0.7,
    'json_encode': 0.7,

    # Medium-low confidence (0.6) - Filtering
    'filter_%': 0.6,
    'clean_%': 0.6,
    'strip_tags': 0.6,
    'preg_replace': 0.6,

    # Lower confidence (0.4-0.5) - Type conversion
    'intval': 0.5,
    'floatval': 0.5,
    'int': 0.5,
    'float': 0.5,
    'str.isdigit': 0.4,
    'str.isalpha': 0.4,

    # Low confidence (0.3) - Minimal sanitization
    'trim': 0.3,
    'strip': 0.3,
    'lower': 0.3,
    'upper': 0.3,
    'normalize': 0.3,

    # Very low confidence (0.2) - Often insufficient
    'addslashes': 0.2,
    'stripslashes': 0.2,
    'str_replace': 0.2,

    # Python/Django/SQLAlchemy-specific patterns
    'objects.filter': 1.0,
    'objects.get': 1.0,
    'objects.exclude': 1.0,
    'objects.create': 1.0,
    'objects.update': 1.0,
    'objects.annotate': 1.0,
    'objects.aggregate': 1.0,
    'objects.values': 1.0,
    'objects.values_list': 1.0,

    # SQLAlchemy
    'query.filter': 1.0,
    'query.filter_by': 1.0,
    'session.query': 1.0,
    'session.execute': 0.8,
    'bindparam': 1.0,
    'text': 0.7,

    # Django security utilities
    'escape': 0.9,
    'mark_safe': 0.3,
    'format_html': 0.9,
    'conditional_escape': 0.9,

    # Python type validation
    'isinstance': 0.8,
    'issubclass': 0.8,
    'hasattr': 0.6,
    'getattr': 0.5,

    # Django form validation
    'cleaned_data': 0.8,
    'is_valid': 0.8,
    'clean_%': 0.8,

    # Python stdlib
    'json.loads': 0.6,
    'json.dumps': 0.7,
    're.match': 0.7,
    're.search': 0.7,
    're.sub': 0.6,
    'ast.literal_eval': 0.9,
}

# Module-level cached patterns (lazy-loaded)
_cached_sanitization_patterns: Optional[Dict[str, float]] = None


def _get_sanitization_patterns() -> Dict[str, float]:
    """
    Get merged sanitization patterns: generic + domain-specific.

    Returns:
        Dictionary mapping pattern names to confidence scores (0.0-1.0)
    """
    merged = dict(_GENERIC_SANITIZATION_CONFIDENCE)

    try:
        from src.domains import DomainRegistry
        domain = DomainRegistry.get_active_or_none()
        if domain is not None and hasattr(domain, 'get_sanitization_confidence'):
            domain_patterns = domain.get_sanitization_confidence()
            if domain_patterns:
                merged.update(domain_patterns)
                logger.debug(
                    f"Loaded {len(domain_patterns)} sanitization patterns from "
                    f"{domain.name} plugin (total: {len(merged)})"
                )
    except ImportError:
        logger.debug("Domain registry not available, using generic patterns only")
    except Exception as e:
        logger.debug(f"Could not load domain sanitization patterns: {e}")

    return merged


def get_sanitization_patterns() -> Dict[str, float]:
    """
    Get sanitization patterns with caching.

    Returns merged generic + domain-specific patterns.
    """
    global _cached_sanitization_patterns
    if _cached_sanitization_patterns is None:
        _cached_sanitization_patterns = _get_sanitization_patterns()
    return _cached_sanitization_patterns


class _SanitizationConfidenceProxy:
    """
    Proxy class that mimics dict behavior but lazy-loads sanitization patterns.

    Pattern confidence scores range from 0.0 to 1.0:
    - 1.0: Strong sanitization (parameterized queries, prepared statements)
    - 0.8-0.9: Context-specific validation (input validation, type checking)
    - 0.6-0.7: Generic encoding/escaping (URL encoding, HTML escaping)
    - 0.3-0.5: Weak sanitization (type casting, trimming)
    - 0.2: Often insufficient (addslashes, simple replacement)
    """
    _instance = None
    _patterns = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _ensure_loaded(self):
        if self._patterns is None:
            self._patterns = get_sanitization_patterns()

    def __getitem__(self, key):
        self._ensure_loaded()
        return self._patterns[key]

    def __contains__(self, key):
        self._ensure_loaded()
        return key in self._patterns

    def keys(self):
        self._ensure_loaded()
        return self._patterns.keys()

    def values(self):
        self._ensure_loaded()
        return self._patterns.values()

    def items(self):
        self._ensure_loaded()
        return self._patterns.items()

    def get(self, key, default=None):
        self._ensure_loaded()
        return self._patterns.get(key, default)

    def __len__(self):
        self._ensure_loaded()
        return len(self._patterns)


SANITIZATION_CONFIDENCE = _SanitizationConfidenceProxy()
