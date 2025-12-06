"""
Accuracy Metrics for RAG-CPGQL Benchmark

Implements answer quality evaluation metrics:
- Semantic Similarity: Embedding-based answer comparison
- Keyword Coverage: Required keyword presence check
- Function Coverage: Expected function mention check
- Factual Accuracy: Composite accuracy score

Author: RAG-CPGQL Test Suite
Date: November 2025
"""

import re
from typing import List, Dict, Any, Set, Optional
from dataclasses import dataclass, field

# Try to import sentence-transformers, fallback to simple similarity
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False


@dataclass
class AccuracyResult:
    """Container for accuracy metrics computation results"""
    semantic_similarity: Optional[float] = None
    keyword_coverage: float = 0.0
    function_coverage: Dict[str, Any] = field(default_factory=dict)
    factual_accuracy: float = 0.0
    pattern_matches: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            'semantic_similarity': self.semantic_similarity,
            'keyword_coverage': self.keyword_coverage,
            'function_coverage': self.function_coverage,
            'factual_accuracy': self.factual_accuracy,
            'pattern_matches': self.pattern_matches,
        }


class AccuracyMetrics:
    """
    Accuracy metrics for evaluating RAG system answer quality.

    Usage:
        metrics = AccuracyMetrics()  # Uses default model

        # Semantic similarity
        sim = metrics.semantic_similarity(generated, reference)

        # Keyword coverage
        cov = metrics.keyword_coverage(generated, ["function", "call"])

        # Full evaluation
        result = metrics.compute_all(generated, ground_truth)
    """

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize accuracy metrics.

        Args:
            model_name: Sentence transformer model for semantic similarity.
                       Defaults to 'all-MiniLM-L6-v2' (fast, good quality)
        """
        self.model_name = model_name
        self._encoder = None

    @property
    def encoder(self):
        """Lazy-load sentence transformer model"""
        if self._encoder is None and HAS_SENTENCE_TRANSFORMERS:
            self._encoder = SentenceTransformer(self.model_name)
        return self._encoder

    def semantic_similarity(
        self,
        generated: str,
        reference: str
    ) -> Optional[float]:
        """
        Compute semantic similarity between generated and reference answer.

        Uses sentence embeddings and cosine similarity.

        Args:
            generated: Generated answer text
            reference: Reference/expected answer text

        Returns:
            Similarity score between 0.0 and 1.0, or None if unavailable
        """
        if not generated or not reference:
            return 0.0

        if not HAS_SENTENCE_TRANSFORMERS or self.encoder is None:
            # Fallback to simple word overlap
            return self._simple_similarity(generated, reference)

        try:
            emb_gen = self.encoder.encode([generated])
            emb_ref = self.encoder.encode([reference])
            similarity = cosine_similarity(emb_gen, emb_ref)[0][0]
            return float(max(0.0, min(1.0, similarity)))
        except Exception:
            return self._simple_similarity(generated, reference)

    def _simple_similarity(self, text1: str, text2: str) -> float:
        """Simple word-overlap based similarity as fallback"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    def keyword_coverage(
        self,
        generated: str,
        required_keywords: List[str],
        case_sensitive: bool = False
    ) -> float:
        """
        Measure what fraction of required keywords appear in output.

        Args:
            generated: Generated answer text
            required_keywords: List of keywords that should appear
            case_sensitive: Whether matching is case-sensitive

        Returns:
            Coverage score between 0.0 and 1.0
        """
        if not required_keywords:
            return 1.0

        if not generated:
            return 0.0

        search_text = generated if case_sensitive else generated.lower()

        found = 0
        for keyword in required_keywords:
            search_keyword = keyword if case_sensitive else keyword.lower()
            if search_keyword in search_text:
                found += 1

        return found / len(required_keywords)

    def function_coverage(
        self,
        retrieved_functions: List[str],
        expected_functions: List[str]
    ) -> Dict[str, Any]:
        """
        Measure overlap between retrieved and expected functions.

        Args:
            retrieved_functions: List of function names found in output
            expected_functions: List of expected function names (ground truth)

        Returns:
            Dictionary with precision, recall, f1, found, missing, extra
        """
        retrieved_set = set(retrieved_functions)
        expected_set = set(expected_functions)

        found = retrieved_set & expected_set
        missing = expected_set - retrieved_set
        extra = retrieved_set - expected_set

        precision = len(found) / len(retrieved_set) if retrieved_set else 0.0
        recall = len(found) / len(expected_set) if expected_set else 1.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        return {
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'found': list(found),
            'missing': list(missing),
            'extra': list(extra),
            'found_count': len(found),
            'expected_count': len(expected_set),
        }

    def pattern_match(
        self,
        generated: str,
        patterns: List[str],
        case_sensitive: bool = False
    ) -> Dict[str, bool]:
        """
        Check which regex patterns match in the generated text.

        Args:
            generated: Generated answer text
            patterns: List of regex patterns to check
            case_sensitive: Whether matching is case-sensitive

        Returns:
            Dictionary mapping pattern -> matched (bool)
        """
        results = {}
        flags = 0 if case_sensitive else re.IGNORECASE

        for pattern in patterns:
            try:
                results[pattern] = bool(re.search(pattern, generated, flags))
            except re.error:
                # Invalid regex, try literal match
                search_text = generated if case_sensitive else generated.lower()
                search_pattern = pattern if case_sensitive else pattern.lower()
                results[pattern] = search_pattern in search_text

        return results

    def factual_accuracy(
        self,
        generated: str,
        ground_truth: Dict[str, Any]
    ) -> float:
        """
        Compute composite factual accuracy score.

        Combines multiple checks:
        - Key patterns matching
        - Expected functions mentioned
        - Required keywords present

        Args:
            generated: Generated answer text
            ground_truth: Dictionary with expected values:
                - key_patterns: List[str] - Regex patterns to match
                - expected_functions: List[str] - Functions to mention
                - required_keywords: List[str] - Keywords to include

        Returns:
            Accuracy score between 0.0 and 1.0
        """
        scores = []

        # Check key patterns
        if 'key_patterns' in ground_truth:
            patterns = ground_truth['key_patterns']
            if patterns:
                matches = self.pattern_match(generated, patterns)
                pattern_score = sum(matches.values()) / len(patterns)
                scores.append(pattern_score)

        # Check expected functions
        if 'expected_functions' in ground_truth:
            functions = ground_truth['expected_functions']
            if functions:
                func_found = sum(
                    1 for func in functions
                    if func.lower() in generated.lower()
                )
                scores.append(func_found / len(functions))

        # Check required keywords
        if 'required_keywords' in ground_truth:
            keywords = ground_truth['required_keywords']
            if keywords:
                kw_score = self.keyword_coverage(generated, keywords)
                scores.append(kw_score)

        # Check min/max expected counts
        if 'min_expected_count' in ground_truth:
            # Count function-like patterns (word followed by parentheses or CamelCase)
            func_pattern = r'\b[A-Z][a-zA-Z0-9_]*(?:\([^)]*\))?'
            matches = re.findall(func_pattern, generated)
            min_count = ground_truth['min_expected_count']
            count_score = min(1.0, len(matches) / min_count) if min_count > 0 else 1.0
            scores.append(count_score)

        return sum(scores) / len(scores) if scores else 0.0

    def extract_functions_from_text(self, text: str) -> List[str]:
        """
        Extract function names from generated text.

        Looks for patterns like:
        - CamelCase words (ExecInitNode)
        - snake_case words followed by () (heap_insert())
        - Function-like mentions

        Args:
            text: Text to extract function names from

        Returns:
            List of extracted function names
        """
        functions = set()

        # CamelCase functions (C-style)
        camel_pattern = r'\b([A-Z][a-zA-Z0-9]*[a-z][a-zA-Z0-9]*)\b'
        functions.update(re.findall(camel_pattern, text))

        # snake_case functions with parentheses
        snake_pattern = r'\b([a-z][a-z0-9_]+)\s*\('
        functions.update(re.findall(snake_pattern, text))

        # PostgreSQL-style prefixes (pg_, Pg, exec_, etc.)
        pg_pattern = r'\b((?:pg_|Pg|exec_|Exec|heap_|index_)[a-zA-Z0-9_]+)\b'
        functions.update(re.findall(pg_pattern, text))

        return list(functions)

    def compute_all(
        self,
        generated: str,
        ground_truth: Dict[str, Any],
        reference_answer: Optional[str] = None
    ) -> AccuracyResult:
        """
        Compute all accuracy metrics at once.

        Args:
            generated: Generated answer text
            ground_truth: Ground truth dictionary with expected values
            reference_answer: Optional reference answer for semantic similarity

        Returns:
            AccuracyResult with all computed metrics
        """
        result = AccuracyResult()

        # Semantic similarity (if reference provided)
        if reference_answer:
            result.semantic_similarity = self.semantic_similarity(
                generated, reference_answer
            )

        # Keyword coverage
        if 'required_keywords' in ground_truth:
            result.keyword_coverage = self.keyword_coverage(
                generated, ground_truth['required_keywords']
            )

        # Function coverage
        if 'expected_functions' in ground_truth:
            extracted = self.extract_functions_from_text(generated)
            result.function_coverage = self.function_coverage(
                extracted, ground_truth['expected_functions']
            )

        # Pattern matches
        if 'key_patterns' in ground_truth:
            result.pattern_matches = self.pattern_match(
                generated, ground_truth['key_patterns']
            )

        # Factual accuracy
        result.factual_accuracy = self.factual_accuracy(generated, ground_truth)

        return result


# Convenience functions
def semantic_similarity(generated: str, reference: str) -> Optional[float]:
    """Compute semantic similarity between two texts"""
    return AccuracyMetrics().semantic_similarity(generated, reference)

def keyword_coverage(generated: str, keywords: List[str]) -> float:
    """Compute keyword coverage"""
    return AccuracyMetrics().keyword_coverage(generated, keywords)

def factual_accuracy(generated: str, ground_truth: Dict[str, Any]) -> float:
    """Compute factual accuracy score"""
    return AccuracyMetrics().factual_accuracy(generated, ground_truth)
