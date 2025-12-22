"""Evaluation Handler for result validation and quality scoring.

Handles:
- Query result validation
- Response quality scoring
- Relevance assessment
- Confidence estimation
"""
import logging
import time
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from .base import BaseHandler, HandlerResult

logger = logging.getLogger(__name__)


@dataclass
class EvaluationScore:
    """Evaluation score with breakdown."""
    overall: float = 0.0
    relevance: float = 0.0
    completeness: float = 0.0
    accuracy: float = 0.0
    confidence: float = 0.0
    factors: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": round(self.overall, 3),
            "relevance": round(self.relevance, 3),
            "completeness": round(self.completeness, 3),
            "accuracy": round(self.accuracy, 3),
            "confidence": round(self.confidence, 3),
            "factors": {k: round(v, 3) for k, v in self.factors.items()}
        }


class EvaluationHandler(BaseHandler):
    """
    Handler for result validation and quality scoring.

    Evaluates query results, responses, and overall
    answer quality based on multiple criteria.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize evaluation handler.

        Args:
            config: Configuration with evaluation thresholds
        """
        super().__init__(config)

        # Configurable thresholds
        self.min_results = config.get('min_results', 1) if config else 1
        self.max_results = config.get('max_results', 1000) if config else 1000
        self.relevance_threshold = config.get('relevance_threshold', 0.5) if config else 0.5

    def handle(
        self,
        evaluation_type: str,
        **kwargs
    ) -> HandlerResult:
        """
        Execute evaluation based on type.

        Args:
            evaluation_type: Type of evaluation to perform
            **kwargs: Evaluation-specific arguments

        Returns:
            HandlerResult with evaluation results
        """
        start_time = time.time()

        try:
            if evaluation_type == "query_results":
                result = self._evaluate_query_results(**kwargs)
            elif evaluation_type == "response":
                result = self._evaluate_response(**kwargs)
            elif evaluation_type == "relevance":
                result = self._evaluate_relevance(**kwargs)
            elif evaluation_type == "query_validity":
                result = self._evaluate_query_validity(**kwargs)
            elif evaluation_type == "confidence":
                result = self._estimate_confidence(**kwargs)
            elif evaluation_type == "full":
                result = self._full_evaluation(**kwargs)
            else:
                raise ValueError(f"Unknown evaluation type: {evaluation_type}")

            duration_ms = (time.time() - start_time) * 1000
            self._track_call(duration_ms, True)

            return HandlerResult(
                success=True,
                data=result,
                duration_ms=duration_ms,
                metadata={"evaluation_type": evaluation_type}
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._track_call(duration_ms, False)
            self.log_error(f"Evaluation failed ({evaluation_type}): {e}")

            return HandlerResult(
                success=False,
                error=str(e),
                duration_ms=duration_ms,
                metadata={"evaluation_type": evaluation_type}
            )

    def evaluate_query_results(
        self,
        results: List[Dict[str, Any]],
        question: str,
        query: str
    ) -> HandlerResult:
        """
        Evaluate query results for quality and relevance.

        Args:
            results: Query results to evaluate
            question: Original question
            query: SQL query that was executed

        Returns:
            HandlerResult with evaluation score
        """
        return self.handle(
            "query_results",
            results=results,
            question=question,
            query=query
        )

    def evaluate_response(
        self,
        response: str,
        question: str,
        results: List[Dict[str, Any]]
    ) -> HandlerResult:
        """
        Evaluate generated response quality.

        Args:
            response: Generated response
            question: Original question
            results: Query results used

        Returns:
            HandlerResult with evaluation score
        """
        return self.handle(
            "response",
            response=response,
            question=question,
            results=results
        )

    def validate_query(self, query: str) -> HandlerResult:
        """
        Validate SQL query syntax and safety.

        Args:
            query: SQL query to validate

        Returns:
            HandlerResult with validation result
        """
        return self.handle("query_validity", query=query)

    def full_evaluation(
        self,
        question: str,
        query: str,
        results: List[Dict[str, Any]],
        response: str
    ) -> HandlerResult:
        """
        Perform full evaluation of question-answer pipeline.

        Args:
            question: Original question
            query: Generated SQL query
            results: Query results
            response: Generated response

        Returns:
            HandlerResult with comprehensive evaluation
        """
        return self.handle(
            "full",
            question=question,
            query=query,
            results=results,
            response=response
        )

    # === Private Evaluation Methods ===

    def _evaluate_query_results(
        self,
        results: List[Dict[str, Any]],
        question: str,
        query: str
    ) -> Dict[str, Any]:
        """Evaluate query results."""
        score = EvaluationScore()

        # Result count factor
        result_count = len(results)
        if result_count == 0:
            score.factors['result_count'] = 0.0
        elif result_count < self.min_results:
            score.factors['result_count'] = 0.3
        elif result_count > self.max_results:
            score.factors['result_count'] = 0.5  # Too many results
        else:
            # Ideal range
            score.factors['result_count'] = 1.0

        # Relevance factor (keyword matching)
        keywords = self._extract_keywords(question)
        relevance_scores = []
        for result in results[:50]:  # Sample first 50
            result_text = ' '.join(str(v) for v in result.values())
            matches = sum(1 for kw in keywords if kw.lower() in result_text.lower())
            relevance_scores.append(matches / max(len(keywords), 1))

        score.factors['keyword_match'] = (
            sum(relevance_scores) / max(len(relevance_scores), 1)
        )

        # Completeness factor (fields present)
        if results:
            expected_fields = {'name', 'filename', 'line_number'}
            present_fields = set(results[0].keys())
            overlap = len(expected_fields & present_fields)
            score.factors['field_completeness'] = overlap / len(expected_fields)
        else:
            score.factors['field_completeness'] = 0.0

        # Calculate overall scores
        score.relevance = score.factors.get('keyword_match', 0.0)
        score.completeness = score.factors.get('field_completeness', 0.0)
        score.accuracy = score.factors.get('result_count', 0.0)

        # Weighted overall
        score.overall = (
            0.4 * score.relevance +
            0.3 * score.completeness +
            0.3 * score.accuracy
        )

        return {
            "score": score.to_dict(),
            "result_count": result_count,
            "is_acceptable": score.overall >= self.relevance_threshold,
            "recommendations": self._generate_recommendations(score, results)
        }

    def _evaluate_response(
        self,
        response: str,
        question: str,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Evaluate response quality."""
        score = EvaluationScore()

        # Length factor
        response_len = len(response)
        if response_len < 50:
            score.factors['length'] = 0.3  # Too short
        elif response_len > 2000:
            score.factors['length'] = 0.7  # Maybe too long
        else:
            score.factors['length'] = 1.0

        # References results
        result_refs = 0
        if results:
            for result in results[:10]:
                name = str(result.get('name', ''))
                if name and name in response:
                    result_refs += 1
            score.factors['references_results'] = min(result_refs / 3, 1.0)
        else:
            score.factors['references_results'] = 0.5  # Neutral if no results

        # Addresses question
        keywords = self._extract_keywords(question)
        addressed = sum(1 for kw in keywords if kw.lower() in response.lower())
        score.factors['addresses_question'] = addressed / max(len(keywords), 1)

        # Structure (has sections or bullet points)
        has_structure = any([
            '\n-' in response,
            '\n*' in response,
            '\n1.' in response,
            ':\n' in response
        ])
        score.factors['structure'] = 1.0 if has_structure else 0.5

        # Calculate overall
        score.relevance = score.factors.get('addresses_question', 0.0)
        score.completeness = score.factors.get('references_results', 0.0)
        score.accuracy = (
            score.factors.get('length', 0.0) +
            score.factors.get('structure', 0.0)
        ) / 2

        score.overall = (
            0.4 * score.relevance +
            0.3 * score.completeness +
            0.3 * score.accuracy
        )

        return {
            "score": score.to_dict(),
            "response_length": response_len,
            "is_acceptable": score.overall >= self.relevance_threshold
        }

    def _evaluate_relevance(
        self,
        content: str,
        question: str
    ) -> Dict[str, Any]:
        """Evaluate content relevance to question."""
        keywords = self._extract_keywords(question)
        content_lower = content.lower()

        matches = {}
        for kw in keywords:
            count = content_lower.count(kw.lower())
            if count > 0:
                matches[kw] = count

        relevance_score = len(matches) / max(len(keywords), 1)

        return {
            "relevance_score": relevance_score,
            "matched_keywords": matches,
            "total_keywords": len(keywords),
            "is_relevant": relevance_score >= self.relevance_threshold
        }

    def _evaluate_query_validity(
        self,
        query: str
    ) -> Dict[str, Any]:
        """Evaluate SQL query validity."""
        issues = []
        warnings = []

        query_upper = query.upper()

        # Check for SELECT
        if 'SELECT' not in query_upper:
            issues.append("Missing SELECT clause")

        # Check for FROM
        if 'FROM' not in query_upper:
            issues.append("Missing FROM clause")

        # Check for dangerous patterns
        dangerous_patterns = [
            (r'\bDROP\b', "DROP statement detected"),
            (r'\bDELETE\b', "DELETE statement detected"),
            (r'\bINSERT\b', "INSERT statement detected"),
            (r'\bUPDATE\b', "UPDATE statement detected"),
            (r'\bTRUNCATE\b', "TRUNCATE statement detected"),
            (r'\bALTER\b', "ALTER statement detected"),
        ]

        for pattern, message in dangerous_patterns:
            if re.search(pattern, query_upper):
                issues.append(message)

        # Check for warnings
        if 'LIMIT' not in query_upper:
            warnings.append("No LIMIT clause - may return many results")

        if query_upper.count('JOIN') > 3:
            warnings.append("Multiple JOINs may be slow")

        # Validate table names
        valid_tables = {
            'nodes_method', 'nodes_call', 'nodes_comment',
            'nodes_identifier', 'nodes_literal', 'nodes_local',
            'nodes_param', 'nodes_return', 'nodes_block',
            'nodes_control_structure', 'nodes_type_decl',
            'edges_ast', 'edges_cfg', 'edges_call', 'edges_ref',
            'edges_reaching_def', 'edges_argument'
        }

        # Extract table names from query
        table_pattern = r'(?:FROM|JOIN)\s+(\w+)'
        found_tables = re.findall(table_pattern, query, re.IGNORECASE)

        for table in found_tables:
            if table.lower() not in valid_tables:
                warnings.append(f"Unknown table: {table}")

        is_valid = len(issues) == 0

        return {
            "is_valid": is_valid,
            "issues": issues,
            "warnings": warnings,
            "query_type": "SELECT" if "SELECT" in query_upper else "UNKNOWN",
            "has_limit": "LIMIT" in query_upper,
            "join_count": query_upper.count('JOIN')
        }

    def _estimate_confidence(
        self,
        results: List[Dict[str, Any]],
        question: str,
        query: str
    ) -> Dict[str, Any]:
        """Estimate confidence in results."""
        factors = {}

        # Result count confidence
        count = len(results)
        if count == 0:
            factors['result_count'] = 0.0
        elif 1 <= count <= 10:
            factors['result_count'] = 0.9  # High confidence
        elif 11 <= count <= 50:
            factors['result_count'] = 0.7
        elif 51 <= count <= 200:
            factors['result_count'] = 0.5
        else:
            factors['result_count'] = 0.3  # Too many

        # Query specificity
        specificity_indicators = [
            ('WHERE', 0.2),
            ('ILIKE', 0.15),
            ('=', 0.1),
            ('AND', 0.1),
            ('JOIN', 0.1),
        ]

        specificity = 0.3  # Base
        query_upper = query.upper()
        for indicator, score in specificity_indicators:
            if indicator in query_upper:
                specificity += score

        factors['query_specificity'] = min(specificity, 1.0)

        # Keyword coverage
        keywords = self._extract_keywords(question)
        if keywords and results:
            sample_text = ' '.join(
                str(v) for r in results[:20] for v in r.values()
            ).lower()
            covered = sum(1 for kw in keywords if kw.lower() in sample_text)
            factors['keyword_coverage'] = covered / len(keywords)
        else:
            factors['keyword_coverage'] = 0.5

        # Overall confidence
        confidence = sum(factors.values()) / len(factors) if factors else 0.5

        return {
            "confidence": round(confidence, 3),
            "factors": {k: round(v, 3) for k, v in factors.items()},
            "level": self._confidence_level(confidence)
        }

    def _full_evaluation(
        self,
        question: str,
        query: str,
        results: List[Dict[str, Any]],
        response: str
    ) -> Dict[str, Any]:
        """Perform comprehensive evaluation."""
        # Query validity
        query_eval = self._evaluate_query_validity(query)

        # Results evaluation
        results_eval = self._evaluate_query_results(results, question, query)

        # Response evaluation
        response_eval = self._evaluate_response(response, question, results)

        # Confidence estimation
        confidence_eval = self._estimate_confidence(results, question, query)

        # Aggregate score
        scores = [
            results_eval['score']['overall'],
            response_eval['score']['overall'],
            confidence_eval['confidence']
        ]

        if query_eval['is_valid']:
            scores.append(1.0)
        else:
            scores.append(0.0)

        overall = sum(scores) / len(scores)

        return {
            "overall_score": round(overall, 3),
            "query_evaluation": query_eval,
            "results_evaluation": results_eval,
            "response_evaluation": response_eval,
            "confidence": confidence_eval,
            "is_acceptable": overall >= self.relevance_threshold,
            "grade": self._score_to_grade(overall)
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text."""
        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'can', 'must',
            'what', 'which', 'who', 'whom', 'this', 'that', 'these',
            'those', 'how', 'where', 'when', 'why', 'all', 'each',
            'every', 'both', 'few', 'more', 'most', 'other', 'some',
            'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
            'than', 'too', 'very', 'just', 'and', 'but', 'or', 'for',
            'with', 'from', 'into', 'to', 'of', 'in', 'on', 'at', 'by',
            'find', 'show', 'get', 'list', 'как', 'что', 'где', 'кто',
            'найди', 'покажи', 'получи'
        }

        # Tokenize and filter
        words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b', text)
        keywords = [w for w in words if w.lower() not in stop_words]

        return keywords[:10]  # Limit to 10 keywords

    def _generate_recommendations(
        self,
        score: EvaluationScore,
        results: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate improvement recommendations."""
        recs = []

        if score.factors.get('result_count', 1) < 0.5:
            if len(results) == 0:
                recs.append("Try broader search patterns (use ILIKE with wildcards)")
            else:
                recs.append("Consider adding LIMIT to reduce result set")

        if score.factors.get('keyword_match', 1) < 0.5:
            recs.append("Results may not be relevant - check query filters")

        if score.factors.get('field_completeness', 1) < 0.7:
            recs.append("Include more fields in SELECT for better context")

        return recs

    def _confidence_level(self, confidence: float) -> str:
        """Convert confidence score to level."""
        if confidence >= 0.8:
            return "high"
        elif confidence >= 0.5:
            return "medium"
        elif confidence >= 0.3:
            return "low"
        else:
            return "very_low"

    def _score_to_grade(self, score: float) -> str:
        """Convert score to letter grade."""
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"
