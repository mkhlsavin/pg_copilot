"""
Adaptive Query Refiner

Learns from query execution outcomes to suggest better query patterns.
Tracks which query patterns work for different question types and provides
intelligent refinement suggestions.
"""

import re
import time
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class QueryPattern:
    """Represents a learned query pattern."""

    def __init__(
        self,
        pattern: str,
        question_type: str,
        success_count: int = 0,
        failure_count: int = 0,
        avg_result_count: float = 0.0,
        last_used: Optional[float] = None
    ):
        self.pattern = pattern
        self.question_type = question_type
        self.success_count = success_count
        self.failure_count = failure_count
        self.avg_result_count = avg_result_count
        self.last_used = last_used or time.time()

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.success_count / total

    @property
    def confidence(self) -> float:
        """Calculate confidence score based on usage and success."""
        # Confidence increases with more usage and higher success rate
        usage_factor = min(1.0, (self.success_count + self.failure_count) / 10)
        return self.success_rate * usage_factor

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'pattern': self.pattern,
            'question_type': self.question_type,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'avg_result_count': self.avg_result_count,
            'last_used': self.last_used,
            'success_rate': self.success_rate,
            'confidence': self.confidence
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueryPattern':
        """Deserialize from dictionary."""
        return cls(
            pattern=data['pattern'],
            question_type=data['question_type'],
            success_count=data['success_count'],
            failure_count=data['failure_count'],
            avg_result_count=data['avg_result_count'],
            last_used=data.get('last_used')
        )


class AdaptiveQueryRefiner:
    """
    Learn which query patterns work for different question types.

    Tracks successful and failed query patterns, and suggests refinements
    based on learned knowledge.
    """

    def __init__(self, persistence_path: Optional[str] = None):
        """
        Initialize the adaptive refiner.

        Args:
            persistence_path: Path to save/load learned patterns
        """
        self.success_patterns: Dict[str, List[QueryPattern]] = defaultdict(list)
        self.failure_patterns: Dict[str, List[Dict]] = defaultdict(list)

        # Persistence
        self.persistence_path = Path(persistence_path) if persistence_path else \
                                Path("data/adaptive_query_patterns.json")

        # Configuration
        self.min_results_threshold = 5
        self.max_patterns_per_type = 50
        self.pattern_expiry_days = 30

        # Load existing patterns
        self.load_patterns()

        logger.info(f"AdaptiveQueryRefiner initialized with {self._count_patterns()} learned patterns")

    def record_query_outcome(
        self,
        question: str,
        question_type: str,
        query: str,
        success: bool,
        result_count: int,
        execution_time: float = 0.0,
        metadata: Optional[Dict] = None
    ):
        """
        Record query success/failure for learning.

        Args:
            question: Original question
            question_type: Type of question (e.g., "data_flow", "control_flow", "find_methods")
            query: CPGQL query that was executed
            success: Whether query executed successfully
            result_count: Number of results returned
            execution_time: Query execution time in seconds
            metadata: Additional context (specificity level, tags used, etc.)
        """
        pattern = self._extract_query_pattern(query)

        if success and result_count >= self.min_results_threshold:
            # Record successful pattern
            self._record_success(
                question_type=question_type,
                pattern=pattern,
                result_count=result_count,
                execution_time=execution_time,
                metadata=metadata
            )
            logger.info(f"[OK] Recorded success pattern for '{question_type}': {result_count} results")
        else:
            # Record failed pattern
            self._record_failure(
                question_type=question_type,
                pattern=pattern,
                query=query,
                result_count=result_count,
                reason="empty_results" if result_count == 0 else "insufficient_results",
                metadata=metadata
            )
            logger.info(f"[FAIL] Recorded failure pattern for '{question_type}': {result_count} results")

        # Periodically clean up old patterns
        if self._should_cleanup():
            self._cleanup_old_patterns()

    def suggest_refinements(
        self,
        question: str,
        question_type: str,
        failed_query: str,
        max_suggestions: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Suggest query refinements based on learned patterns.

        Args:
            question: Original question
            question_type: Type of question
            failed_query: Query that failed or returned insufficient results
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of refinement suggestions with strategy descriptions
        """
        logger.info(f"Generating refinements for question type: {question_type}")

        refinements = []

        # Strategy 1: Use patterns from successful similar queries
        if self.success_patterns.get(question_type):
            successful_refinement = self._suggest_from_success_patterns(
                question_type, failed_query
            )
            if successful_refinement:
                refinements.append(successful_refinement)

        # Strategy 2: Remove most restrictive filter
        removal_refinement = self._suggest_filter_removal(failed_query)
        if removal_refinement:
            refinements.append(removal_refinement)

        # Strategy 3: Broaden name matching pattern
        broadening_refinement = self._suggest_name_broadening(failed_query)
        if broadening_refinement:
            refinements.append(broadening_refinement)

        # Strategy 4: Switch from exact to pattern matching
        pattern_refinement = self._suggest_pattern_matching(failed_query)
        if pattern_refinement:
            refinements.append(pattern_refinement)

        # Strategy 5: Add graph traversal (if not present)
        traversal_refinement = self._suggest_graph_traversal(failed_query, question_type)
        if traversal_refinement:
            refinements.append(traversal_refinement)

        # Sort by confidence and return top suggestions
        refinements.sort(key=lambda x: x.get('confidence', 0.0), reverse=True)

        logger.info(f"Generated {len(refinements)} refinement suggestions")
        return refinements[:max_suggestions]

    def get_best_pattern_for_type(self, question_type: str) -> Optional[QueryPattern]:
        """Get the most successful pattern for a question type."""
        patterns = self.success_patterns.get(question_type, [])
        if not patterns:
            return None

        # Sort by confidence (combination of success rate and usage)
        patterns.sort(key=lambda p: p.confidence, reverse=True)
        return patterns[0]

    def get_statistics(self) -> Dict[str, Any]:
        """Get learning statistics."""
        total_successes = sum(
            sum(p.success_count for p in patterns)
            for patterns in self.success_patterns.values()
        )
        total_failures = sum(
            len(failures)
            for failures in self.failure_patterns.values()
        )

        return {
            'total_patterns_learned': self._count_patterns(),
            'question_types_covered': len(self.success_patterns),
            'total_successful_queries': total_successes,
            'total_failed_queries': total_failures,
            'success_rate': total_successes / (total_successes + total_failures) if (total_successes + total_failures) > 0 else 0.0,
            'question_types': {
                qtype: {
                    'patterns': len(patterns),
                    'total_successes': sum(p.success_count for p in patterns),
                    'avg_confidence': sum(p.confidence for p in patterns) / len(patterns) if patterns else 0.0
                }
                for qtype, patterns in self.success_patterns.items()
            }
        }

    def save_patterns(self):
        """Save learned patterns to disk."""
        data = {
            'version': '1.0',
            'timestamp': time.time(),
            'success_patterns': {
                qtype: [p.to_dict() for p in patterns]
                for qtype, patterns in self.success_patterns.items()
            },
            'failure_patterns': dict(self.failure_patterns),
            'statistics': self.get_statistics()
        }

        self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.persistence_path, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {self._count_patterns()} patterns to {self.persistence_path}")

    def load_patterns(self):
        """Load learned patterns from disk."""
        if not self.persistence_path.exists():
            logger.info("No existing patterns file found, starting fresh")
            return

        try:
            with open(self.persistence_path, 'r') as f:
                data = json.load(f)

            # Load success patterns
            for qtype, patterns_data in data.get('success_patterns', {}).items():
                self.success_patterns[qtype] = [
                    QueryPattern.from_dict(p) for p in patterns_data
                ]

            # Load failure patterns
            for qtype, failures in data.get('failure_patterns', {}).items():
                self.failure_patterns[qtype] = failures

            logger.info(f"Loaded {self._count_patterns()} patterns from {self.persistence_path}")
        except Exception as e:
            logger.error(f"Error loading patterns: {e}")

    # Private methods

    def _extract_query_pattern(self, query: str) -> str:
        """
        Extract a generalized pattern from a query.

        Examples:
            cpg.method.name("heap_insert").tag.name("mvcc").l
            → "cpg.method.name(PATTERN).tag.name(TAG).l"

            cpg.method.where(_.tag.nameExact("domain-concept").valueExact("wal")).l
            → "cpg.method.where(TAG_FILTER).l"
        """
        pattern = query

        # Replace specific strings with placeholders
        pattern = re.sub(r'\.name\(".*?"\)', '.name(PATTERN)', pattern)
        pattern = re.sub(r'\.nameExact\(".*?"\)', '.nameExact(EXACT)', pattern)
        pattern = re.sub(r'\.valueExact\(".*?"\)', '.valueExact(VALUE)', pattern)
        pattern = re.sub(r'\.value\(".*?"\)', '.value(VALUE)', pattern)
        pattern = re.sub(r'\.lineNumber\s*[><=]+\s*\d+', '.lineNumber(NUM)', pattern)

        return pattern

    def _record_success(
        self,
        question_type: str,
        pattern: str,
        result_count: int,
        execution_time: float,
        metadata: Optional[Dict]
    ):
        """Record a successful query pattern."""
        # Find existing pattern or create new
        existing = None
        for p in self.success_patterns[question_type]:
            if p.pattern == pattern:
                existing = p
                break

        if existing:
            # Update existing pattern
            existing.success_count += 1
            # Update rolling average of result count
            total_attempts = existing.success_count + existing.failure_count
            existing.avg_result_count = (
                (existing.avg_result_count * (total_attempts - 1) + result_count) / total_attempts
            )
            existing.last_used = time.time()
        else:
            # Create new pattern
            new_pattern = QueryPattern(
                pattern=pattern,
                question_type=question_type,
                success_count=1,
                avg_result_count=result_count
            )
            self.success_patterns[question_type].append(new_pattern)

        # Limit number of patterns per type
        if len(self.success_patterns[question_type]) > self.max_patterns_per_type:
            # Keep only the most successful patterns
            self.success_patterns[question_type].sort(key=lambda p: p.confidence, reverse=True)
            self.success_patterns[question_type] = self.success_patterns[question_type][:self.max_patterns_per_type]

    def _record_failure(
        self,
        question_type: str,
        pattern: str,
        query: str,
        result_count: int,
        reason: str,
        metadata: Optional[Dict]
    ):
        """Record a failed query pattern."""
        # Update failure count in success patterns (if exists)
        for p in self.success_patterns[question_type]:
            if p.pattern == pattern:
                p.failure_count += 1
                p.last_used = time.time()
                break

        # Record failure details
        self.failure_patterns[question_type].append({
            'pattern': pattern,
            'query': query,
            'result_count': result_count,
            'reason': reason,
            'timestamp': time.time(),
            'metadata': metadata
        })

        # Keep only recent failures (last 100 per type)
        if len(self.failure_patterns[question_type]) > 100:
            self.failure_patterns[question_type] = self.failure_patterns[question_type][-100:]

    def _suggest_from_success_patterns(
        self,
        question_type: str,
        failed_query: str
    ) -> Optional[Dict[str, Any]]:
        """Suggest refinement based on successful patterns for this question type."""
        best_pattern = self.get_best_pattern_for_type(question_type)
        if not best_pattern:
            return None

        # Try to apply the successful pattern structure to the failed query
        refined_query = self._apply_pattern_structure(failed_query, best_pattern.pattern)

        if refined_query and refined_query != failed_query:
            return {
                'query': refined_query,
                'strategy': f"Apply successful pattern (success rate: {best_pattern.success_rate:.1%})",
                'confidence': best_pattern.confidence,
                'pattern_used': best_pattern.pattern,
                'avg_results': best_pattern.avg_result_count
            }

        return None

    def _apply_pattern_structure(self, query: str, pattern: str) -> str:
        """Apply a successful pattern structure to a query."""
        # This is a simplified implementation
        # In production, would use more sophisticated pattern matching

        # If pattern uses graph traversal and query doesn't, add it
        if '.reachableBy(' in pattern and '.reachableBy(' not in query:
            # Add reachableBy traversal
            if query.endswith('.l'):
                query = query[:-2] + '.parameter.reachableBy(cpg.identifier).code.l'

        # If pattern uses .ast and query doesn't, add it
        if '.ast' in pattern and '.ast' not in query:
            if query.endswith('.l'):
                query = query[:-2] + '.ast.isControlStructure.code.l'

        return query

    def _suggest_filter_removal(self, query: str) -> Optional[Dict[str, Any]]:
        """Suggest removing one filter to broaden the query."""
        # Count filters
        where_clauses = re.findall(r'\.where\([^)]+\)', query)
        tag_filters = re.findall(r'\.tag\.(?:nameExact|valueExact)\([^)]+\)', query)

        if where_clauses:
            # Remove last where clause
            refined = re.sub(r'\.where\([^)]+\)(?!.*\.where)', '', query)
            return {
                'query': refined,
                'strategy': 'Remove most restrictive filter (.where clause)',
                'confidence': 0.7,
                'change': 'Removed one .where() filter'
            }
        elif len(tag_filters) > 1:
            # Remove one tag filter
            refined = re.sub(r'\.tag\.(?:nameExact|valueExact)\([^)]+\)', '', query, count=1)
            return {
                'query': refined,
                'strategy': 'Remove one tag filter to broaden search',
                'confidence': 0.7,
                'change': 'Removed one tag filter'
            }

        return None

    def _suggest_name_broadening(self, query: str) -> Optional[Dict[str, Any]]:
        """Suggest broadening name matching patterns."""
        # Look for exact name matches
        exact_names = re.findall(r'\.name\("([^"]+)"\)', query)

        if exact_names:
            name = exact_names[0]
            # Broaden to pattern matching
            if '_' in name:
                # Use first part of underscore-separated name
                broad_pattern = f".*{name.split('_')[0]}.*"
            else:
                # Use partial match
                broad_pattern = f".*{name[:len(name)//2]}.*"

            refined = query.replace(f'.name("{name}")', f'.name("{broad_pattern}")')

            return {
                'query': refined,
                'strategy': 'Broaden name pattern matching',
                'confidence': 0.8,
                'change': f'Changed .name("{name}") to .name("{broad_pattern}")'
            }

        return None

    def _suggest_pattern_matching(self, query: str) -> Optional[Dict[str, Any]]:
        """Suggest switching from exact to pattern matching."""
        # Look for nameExact/valueExact
        has_exact = 'nameExact' in query or 'valueExact' in query

        if has_exact:
            refined = query.replace('nameExact', 'name').replace('valueExact', 'value')
            return {
                'query': refined,
                'strategy': 'Switch from exact to pattern matching',
                'confidence': 0.75,
                'change': 'Changed *Exact() to pattern matching'
            }

        return None

    def _suggest_graph_traversal(
        self,
        query: str,
        question_type: str
    ) -> Optional[Dict[str, Any]]:
        """Suggest adding graph traversal for richer context."""
        # Don't add if already has traversal
        if any(t in query for t in ['.reachableBy(', '.ast.', '.caller', '.callee']):
            return None

        # Add based on question type
        if 'data_flow' in question_type.lower():
            # Add data flow traversal
            if query.endswith('.l'):
                refined = query[:-2] + '.parameter.reachableBy(cpg.identifier).code.take(20).l'
                return {
                    'query': refined,
                    'strategy': 'Add data flow traversal (.reachableBy)',
                    'confidence': 0.65,
                    'change': 'Added .parameter.reachableBy() for data flow context'
                }

        elif 'control_flow' in question_type.lower() or 'how' in question_type.lower():
            # Add control flow traversal
            if query.endswith('.l'):
                refined = query[:-2] + '.ast.isControlStructure.code.take(20).l'
                return {
                    'query': refined,
                    'strategy': 'Add control flow traversal (.ast)',
                    'confidence': 0.65,
                    'change': 'Added .ast for control flow context'
                }

        return None

    def _should_cleanup(self) -> bool:
        """Determine if it's time to clean up old patterns."""
        # Cleanup every 100 recordings or every hour
        total_patterns = self._count_patterns()
        return total_patterns > 0 and total_patterns % 100 == 0

    def _cleanup_old_patterns(self):
        """Remove patterns that haven't been used recently."""
        cutoff_time = time.time() - (self.pattern_expiry_days * 24 * 3600)
        removed_count = 0

        for qtype in list(self.success_patterns.keys()):
            before = len(self.success_patterns[qtype])
            self.success_patterns[qtype] = [
                p for p in self.success_patterns[qtype]
                if p.last_used > cutoff_time
            ]
            after = len(self.success_patterns[qtype])
            removed_count += (before - after)

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old patterns (>{self.pattern_expiry_days} days)")

    def _count_patterns(self) -> int:
        """Count total learned patterns."""
        return sum(len(patterns) for patterns in self.success_patterns.values())


# Utility functions

def classify_question_type(question: str, analysis: Optional[Dict] = None) -> str:
    """
    Classify question into type for pattern matching.

    Types:
    - data_flow: Questions about data dependencies
    - control_flow: Questions about execution flow
    - find_methods: Questions looking for specific methods
    - architecture: Questions about system structure
    - general: Catch-all
    """
    question_lower = question.lower()

    # Check analysis if available
    if analysis:
        intent = analysis.get('intent', '').lower()
        if 'flow' in intent or 'track' in intent:
            if 'data' in intent:
                return 'data_flow'
            if 'control' in intent or 'execution' in intent:
                return 'control_flow'

    # Keyword-based classification
    if any(kw in question_lower for kw in ['track', 'flow', 'propagate', 'source', 'reach']):
        if any(kw in question_lower for kw in ['data', 'value', 'variable', 'parameter']):
            return 'data_flow'
        return 'control_flow'

    if any(kw in question_lower for kw in ['find', 'search', 'which', 'what', 'list']):
        if any(kw in question_lower for kw in ['method', 'function', 'procedure']):
            return 'find_methods'

    if any(kw in question_lower for kw in ['architecture', 'structure', 'module', 'subsystem', 'layer']):
        return 'architecture'

    return 'general'
