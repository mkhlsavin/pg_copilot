"""
AST-Based Clone Detector for Code Duplicate Detection.

Phase 4 Improvement for Scenario 07: Advanced clone detection using
AST structure comparison, token similarity, and control flow analysis.

Detects multiple clone types:
- Type-1: Exact clones (identical code)
- Type-2: Renamed clones (identifier changes only)
- Type-3: Structural clones (similar structure with modifications)
- Type-4: Semantic clones (different code, same behavior)
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class CloneResult:
    """Result of clone detection between two methods."""
    method1_id: int
    method1_name: str
    method1_file: str
    method2_id: int
    method2_name: str
    method2_file: str
    similarity: float
    clone_type: str  # 'exact', 'renamed', 'structural', 'semantic'
    shared_patterns: List[str] = field(default_factory=list)
    line_count1: int = 0
    line_count2: int = 0

    def to_dict(self) -> Dict:
        return {
            'method1_id': self.method1_id,
            'method1_name': self.method1_name,
            'method1_file': self.method1_file,
            'method2_id': self.method2_id,
            'method2_name': self.method2_name,
            'method2_file': self.method2_file,
            'similarity': self.similarity,
            'clone_type': self.clone_type,
            'shared_patterns': self.shared_patterns,
            'line_count1': self.line_count1,
            'line_count2': self.line_count2
        }


# Category patterns for filtering clones by domain
CLONE_CATEGORY_PATTERNS = {
    'error_handling': ['ereport', 'elog', 'errcode', 'errmsg', 'errdetail', 'PG_TRY', 'PG_CATCH'],
    'memory_allocation': ['palloc', 'palloc0', 'pfree', 'repalloc', 'MemoryContext', 'AllocSet'],
    'lock_management': ['LWLockAcquire', 'LWLockRelease', 'LockAcquire', 'LockRelease', 'SpinLock'],
    'null_check': ['NULL', 'Assert', 'PointerIsValid', 'AssertArg', 'if (.*== NULL)', 'if (.*!= NULL)'],
    'buffer_operations': ['ReadBuffer', 'ReleaseBuffer', 'MarkBufferDirty', 'BufferGetPage'],
    'tuple_operations': ['heap_', 'HeapTuple', 'slot_', 'TupleTableSlot'],
    'catalog_access': ['SearchSysCache', 'RelationGet', 'systable_', 'heap_open'],
    'string_operations': ['pstrdup', 'strlen', 'strcmp', 'strncpy', 'snprintf', 'appendStringInfo'],
}


class ASTCloneDetector:
    """
    Advanced clone detection using AST structure comparison.

    Implements multi-level similarity:
    1. Token similarity (Type-1 clones - exact)
    2. Normalized token similarity (Type-2 clones - renamed)
    3. AST structure similarity (Type-3 clones - structural)
    4. Control flow similarity (Type-4 clones - semantic)
    """

    def __init__(self, cpg_service):
        """Initialize clone detector with CPG service."""
        self.cpg = cpg_service
        self._method_cache = None

    def detect_clones(
        self,
        min_similarity: float = 0.7,
        category: str = None,
        max_methods: int = 300,
        min_lines: int = 5
    ) -> List[CloneResult]:
        """
        Detect code clones across the codebase.

        Args:
            min_similarity: Minimum similarity threshold (0.0-1.0)
            category: Optional category filter (e.g., 'error_handling', 'memory_allocation')
            max_methods: Maximum methods to analyze
            min_lines: Minimum method line count

        Returns:
            List of CloneResult sorted by similarity descending
        """
        logger.info(f"Detecting clones (min_similarity={min_similarity}, category={category})")

        # Load methods with structure
        methods = self._load_methods_with_structure(max_methods, min_lines, category)
        logger.info(f"Loaded {len(methods)} methods for clone detection")

        if len(methods) < 2:
            logger.warning("Not enough methods for clone detection")
            return []

        clones = []

        # Compare all pairs (O(n^2) but limited by max_methods)
        for i, m1 in enumerate(methods):
            for m2 in methods[i+1:]:
                # Skip methods in same file with overlapping lines (likely same function)
                if m1['filename'] == m2['filename']:
                    if abs(m1.get('line_number', 0) - m2.get('line_number', 0)) < 10:
                        continue

                sim, clone_type = self._compute_ast_similarity(m1, m2)

                if sim >= min_similarity:
                    clones.append(CloneResult(
                        method1_id=m1['id'],
                        method1_name=m1['name'],
                        method1_file=m1.get('filename', ''),
                        method2_id=m2['id'],
                        method2_name=m2['name'],
                        method2_file=m2.get('filename', ''),
                        similarity=sim,
                        clone_type=clone_type,
                        shared_patterns=self._find_shared_patterns(m1, m2),
                        line_count1=m1.get('line_count', 0),
                        line_count2=m2.get('line_count', 0)
                    ))

        # Sort by similarity descending
        clones.sort(key=lambda x: -x.similarity)
        logger.info(f"Found {len(clones)} clone pairs")

        return clones

    def detect_clones_for_category(
        self,
        category: str,
        min_similarity: float = 0.6
    ) -> List[CloneResult]:
        """
        Detect clones within a specific category.

        Args:
            category: Category name (e.g., 'error_handling')
            min_similarity: Minimum similarity threshold

        Returns:
            List of CloneResult filtered by category
        """
        if category not in CLONE_CATEGORY_PATTERNS:
            logger.warning(f"Unknown category: {category}")
            return self.detect_clones(min_similarity=min_similarity)

        # Try category-specific detection first
        clones = self.detect_clones(
            min_similarity=min_similarity,
            category=category,
            max_methods=200
        )

        # If no clones found with category filter, try general detection
        # and filter results by category patterns post-hoc
        if not clones:
            logger.info(f"No category-specific clones found for {category}, trying general detection")
            all_clones = self.detect_clones(min_similarity=min_similarity, max_methods=300)

            # Filter by shared patterns matching the category
            patterns = CLONE_CATEGORY_PATTERNS.get(category, [])
            if patterns:
                clones = [c for c in all_clones if c.shared_patterns and
                         any(p.lower() in str(c.shared_patterns).lower() for p in patterns[:3])]

                if clones:
                    logger.info(f"Found {len(clones)} clones matching {category} patterns")
                else:
                    # Return general clones if no pattern matches
                    clones = all_clones[:20]
                    logger.info(f"Returning {len(clones)} general clones (no {category} matches)")

        return clones

    def _load_methods_with_structure(
        self,
        limit: int = 300,
        min_lines: int = 5,
        category: str = None
    ) -> List[Dict]:
        """
        Load methods with AST structure from CPG.

        Args:
            limit: Maximum methods to load
            min_lines: Minimum method line count
            category: Optional category filter

        Returns:
            List of method dicts with 'ast_structure', 'tokens', 'control_flow'
        """
        # Build category filter if specified
        category_filter = ""
        if category and category in CLONE_CATEGORY_PATTERNS:
            patterns = CLONE_CATEGORY_PATTERNS[category]
            # Match methods containing any of the category patterns
            pattern_conditions = " OR ".join([f"m.code LIKE '%{p}%'" for p in patterns[:3]])
            category_filter = f"AND ({pattern_conditions})"

        query = f"""
            SELECT
                m.id, m.name, m.full_name, m.filename, m.code,
                m.line_number, m.line_number_end,
                COALESCE(m.line_number_end - m.line_number, 0) AS line_count
            FROM nodes_method m
            WHERE COALESCE(m.line_number_end - m.line_number, 0) >= {min_lines}
              AND m.is_external = false
              AND m.name NOT LIKE 'test_%'
              AND m.name NOT LIKE '%_test'
              AND m.name NOT IN ('<global>', '<empty>', '<clinit>')
              {category_filter}
            ORDER BY m.filename, m.line_number
            LIMIT {limit}
        """

        try:
            methods = self.cpg.execute_query(query)
        except Exception as e:
            logger.error(f"Failed to load methods: {e}")
            return []

        # Extract AST structure for each method
        for m in methods:
            code = m.get('code', '') or ''
            m['ast_structure'] = self._extract_ast_structure(code)
            m['tokens'] = self._tokenize(code)
            m['control_flow'] = self._extract_control_flow(code)
            m['normalized_tokens'] = self._normalize_tokens(code)

        return methods

    def _extract_ast_structure(self, code: str) -> List[str]:
        """
        Extract simplified AST structure from code.

        Args:
            code: Source code string

        Returns:
            List of AST node type labels
        """
        if not code:
            return []

        patterns = [
            (r'\bif\s*\(', 'IF'),
            (r'\belse\s*if\s*\(', 'ELIF'),
            (r'\belse\b', 'ELSE'),
            (r'\bfor\s*\(', 'FOR'),
            (r'\bwhile\s*\(', 'WHILE'),
            (r'\bdo\s*\{', 'DO'),
            (r'\bswitch\s*\(', 'SWITCH'),
            (r'\bcase\s+', 'CASE'),
            (r'\bdefault\s*:', 'DEFAULT'),
            (r'\breturn\b', 'RETURN'),
            (r'\bbreak\b', 'BREAK'),
            (r'\bcontinue\b', 'CONTINUE'),
            (r'\bgoto\b', 'GOTO'),
            (r'\b\w+\s*\([^)]*\)\s*;', 'CALL'),
            (r'\b\w+\s*=\s*', 'ASSIGN'),
            (r'malloc|palloc|calloc|realloc', 'ALLOC'),
            (r'free|pfree', 'FREE'),
            (r'ereport|elog', 'ERROR'),
            (r'Assert|Assert[A-Z]\w*', 'ASSERT'),
            (r'PG_TRY|PG_CATCH|PG_FINALLY', 'EXCEPTION'),
        ]

        structure = []
        for pattern, label in patterns:
            matches = re.findall(pattern, code, re.IGNORECASE)
            structure.extend([label] * len(matches))

        return structure

    def _tokenize(self, code: str) -> Set[str]:
        """
        Tokenize code into set of tokens.

        Args:
            code: Source code string

        Returns:
            Set of tokens
        """
        if not code:
            return set()

        # Extract words/identifiers
        tokens = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', code))

        # Remove common C keywords
        keywords = {'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default',
                   'return', 'break', 'continue', 'goto', 'int', 'char', 'void',
                   'bool', 'true', 'false', 'NULL', 'static', 'const', 'struct'}
        tokens -= keywords

        return tokens

    def _normalize_tokens(self, code: str) -> Set[str]:
        """
        Normalize code by replacing identifiers with placeholders.

        Args:
            code: Source code string

        Returns:
            Set of normalized tokens
        """
        if not code:
            return set()

        # Replace identifiers with placeholders
        normalized = re.sub(r'\b[a-z_][a-z0-9_]*\b', 'VAR', code.lower())
        normalized = re.sub(r'\b[A-Z][a-zA-Z0-9_]*\b', 'TYPE', normalized)

        return set(re.findall(r'\w+', normalized))

    def _extract_control_flow(self, code: str) -> List[str]:
        """
        Extract control flow sequence from code.

        Args:
            code: Source code string

        Returns:
            List of control flow elements in order
        """
        if not code:
            return []

        cf_elements = []

        # Find control flow elements in order of appearance
        patterns = [
            (r'\bif\s*\(', 'IF'),
            (r'\belse\b', 'ELSE'),
            (r'\bfor\s*\(', 'FOR'),
            (r'\bwhile\s*\(', 'WHILE'),
            (r'\bswitch\s*\(', 'SWITCH'),
            (r'\breturn\b', 'RETURN'),
            (r'\bbreak\b', 'BREAK'),
        ]

        for pattern, label in patterns:
            for match in re.finditer(pattern, code):
                cf_elements.append((match.start(), label))

        # Sort by position and extract labels
        cf_elements.sort(key=lambda x: x[0])
        return [label for _, label in cf_elements]

    def _compute_ast_similarity(
        self,
        m1: Dict,
        m2: Dict
    ) -> Tuple[float, str]:
        """
        Compute similarity using multiple metrics.

        Args:
            m1: First method dict with structure info
            m2: Second method dict with structure info

        Returns:
            Tuple of (similarity_score, clone_type)
        """
        # Level 1: Token similarity (Type-1 clones - exact)
        token_sim = self._jaccard_similarity(m1['tokens'], m2['tokens'])
        if token_sim > 0.95:
            return token_sim, 'exact'

        # Level 2: Normalized token similarity (Type-2 clones - renamed)
        norm_sim = self._jaccard_similarity(m1['normalized_tokens'], m2['normalized_tokens'])
        if norm_sim > 0.85:
            return norm_sim, 'renamed'

        # Level 3: AST structure similarity (Type-3 clones - structural)
        ast_sim = self._sequence_similarity(m1['ast_structure'], m2['ast_structure'])
        if ast_sim > 0.75:
            return ast_sim, 'structural'

        # Level 4: Control flow similarity (Type-4 clones - semantic)
        cf_sim = self._sequence_similarity(m1['control_flow'], m2['control_flow'])
        if cf_sim > 0.70:
            return cf_sim, 'semantic'

        # Return highest similarity
        max_sim = max(token_sim, norm_sim, ast_sim, cf_sim)
        return max_sim, 'none'

    def _jaccard_similarity(self, set1: Set, set2: Set) -> float:
        """
        Compute Jaccard similarity between two sets.

        Args:
            set1: First set
            set2: Second set

        Returns:
            Jaccard similarity (0.0-1.0)
        """
        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union else 0.0

    def _sequence_similarity(self, seq1: List[str], seq2: List[str]) -> float:
        """
        Compute similarity between two sequences using Counter overlap.

        Args:
            seq1: First sequence
            seq2: Second sequence

        Returns:
            Similarity score (0.0-1.0)
        """
        if not seq1 or not seq2:
            return 0.0

        c1 = Counter(seq1)
        c2 = Counter(seq2)

        intersection = sum((c1 & c2).values())
        union = sum((c1 | c2).values())

        return intersection / union if union else 0.0

    def _find_shared_patterns(self, m1: Dict, m2: Dict) -> List[str]:
        """
        Find shared code patterns between two methods.

        Args:
            m1: First method dict
            m2: Second method dict

        Returns:
            List of shared pattern names
        """
        shared = []

        code1 = (m1.get('code', '') or '').lower()
        code2 = (m2.get('code', '') or '').lower()

        for category, patterns in CLONE_CATEGORY_PATTERNS.items():
            # Check if both methods contain patterns from this category
            matches1 = any(p.lower() in code1 for p in patterns)
            matches2 = any(p.lower() in code2 for p in patterns)

            if matches1 and matches2:
                shared.append(category)

        return shared


def detect_duplicate_category(query: str) -> Tuple[Optional[str], List[str]]:
    """
    Detect duplicate category from query.

    Args:
        query: User query about duplicates

    Returns:
        Tuple of (category_name, pattern_list)
    """
    query_lower = query.lower()

    category_keywords = {
        'error': 'error_handling',
        'ereport': 'error_handling',
        'elog': 'error_handling',
        'memory': 'memory_allocation',
        'alloc': 'memory_allocation',
        'palloc': 'memory_allocation',
        'lock': 'lock_management',
        'lwlock': 'lock_management',
        'null': 'null_check',
        'assert': 'null_check',
        'buffer': 'buffer_operations',
        'tuple': 'tuple_operations',
        'heap': 'tuple_operations',
        'catalog': 'catalog_access',
        'syscache': 'catalog_access',
        'string': 'string_operations',
    }

    for keyword, category in category_keywords.items():
        if keyword in query_lower:
            patterns = CLONE_CATEGORY_PATTERNS.get(category, [])
            return category, patterns

    return None, []


__all__ = [
    'ASTCloneDetector',
    'CloneResult',
    'CLONE_CATEGORY_PATTERNS',
    'detect_duplicate_category',
]
