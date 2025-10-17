"""Tag Effectiveness Tracker for Learning Tag Utility

Tracks which enrichment tags lead to successful CPGQL queries
and uses this feedback to improve tag selection over time.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


@dataclass
class TagUsageRecord:
    """Record of a tag being used in a query."""
    tag_name: str
    tag_value: str
    question_domain: str
    question_intent: str
    query_valid: bool
    query_executed: bool
    execution_successful: bool
    timestamp: str
    coverage_score: float


class TagEffectivenessTracker:
    """
    Tracks tag effectiveness over time to learn which tags
    produce successful queries.

    Uses a simple running average of success rates per tag.
    """

    def __init__(
        self,
        persistence_path: Optional[Path] = None,
        min_samples: int = 3
    ):
        """
        Initialize tracker.

        Args:
            persistence_path: Path to save/load tracking data
            min_samples: Minimum samples before using effectiveness scores
        """
        self.min_samples = min_samples
        self.persistence_path = persistence_path or Path("data/tag_effectiveness.json")

        # Thread-safe access
        self._lock = threading.RLock()

        # Tag effectiveness data: tag_key -> stats
        self._effectiveness: Dict[str, Dict] = defaultdict(lambda: {
            'total_uses': 0,
            'valid_queries': 0,
            'successful_executions': 0,
            'avg_coverage': 0.0,
            'success_rate': 0.0,
            'effectiveness_score': 0.5  # Default neutral score
        })

        # Load existing data
        self._load()

    def record_tag_usage(
        self,
        tag_name: str,
        tag_value: str,
        domain: str,
        intent: str,
        query_valid: bool,
        query_executed: bool = False,
        execution_successful: bool = False,
        coverage_score: float = 0.0
    ):
        """
        Record usage of a tag in query generation.

        Args:
            tag_name: Name of the tag (e.g., "function-purpose")
            tag_value: Value of the tag (e.g., "memory-management")
            domain: Question domain
            intent: Question intent
            query_valid: Whether generated query was valid
            query_executed: Whether query was executed
            execution_successful: Whether execution succeeded
            coverage_score: Enrichment coverage score for this query
        """
        with self._lock:
            tag_key = f"{tag_name}:{tag_value}"

            stats = self._effectiveness[tag_key]

            # Update counters
            stats['total_uses'] += 1

            if query_valid:
                stats['valid_queries'] += 1

            if execution_successful:
                stats['successful_executions'] += 1

            # Update running average of coverage
            n = stats['total_uses']
            old_avg = stats['avg_coverage']
            stats['avg_coverage'] = old_avg + (coverage_score - old_avg) / n

            # Calculate success rate (valid queries / total uses)
            stats['success_rate'] = stats['valid_queries'] / stats['total_uses']

            # Calculate effectiveness score (0-1):
            # Weighted combination of:
            # - Success rate (50%)
            # - Execution success rate (30%)
            # - Average coverage (20%)
            exec_rate = (stats['successful_executions'] / stats['total_uses']
                        if stats['total_uses'] > 0 else 0)

            stats['effectiveness_score'] = (
                0.5 * stats['success_rate'] +
                0.3 * exec_rate +
                0.2 * stats['avg_coverage']
            )

            logger.debug(
                f"Updated tag {tag_key}: uses={stats['total_uses']}, "
                f"effectiveness={stats['effectiveness_score']:.3f}"
            )

    def get_tag_effectiveness(
        self,
        tag_name: str,
        tag_value: str
    ) -> float:
        """
        Get effectiveness score for a tag.

        Returns:
            Effectiveness score 0-1, or 0.5 (neutral) if insufficient data
        """
        with self._lock:
            tag_key = f"{tag_name}:{tag_value}"

            if tag_key not in self._effectiveness:
                return 0.5  # Neutral default

            stats = self._effectiveness[tag_key]

            # Need minimum samples before trusting the score
            if stats['total_uses'] < self.min_samples:
                return 0.5  # Not enough data

            return stats['effectiveness_score']

    def get_tag_stats(
        self,
        tag_name: str,
        tag_value: str
    ) -> Optional[Dict]:
        """Get detailed statistics for a tag."""
        with self._lock:
            tag_key = f"{tag_name}:{tag_value}"

            if tag_key not in self._effectiveness:
                return None

            return dict(self._effectiveness[tag_key])

    def get_top_tags(
        self,
        domain: Optional[str] = None,
        limit: int = 10
    ) -> List[Tuple[str, str, float]]:
        """
        Get top-performing tags.

        Args:
            domain: Optional domain filter
            limit: Maximum tags to return

        Returns:
            List of (tag_name, tag_value, effectiveness_score) tuples
        """
        with self._lock:
            # Filter tags with sufficient samples
            valid_tags = [
                (key, stats)
                for key, stats in self._effectiveness.items()
                if stats['total_uses'] >= self.min_samples
            ]

            # Sort by effectiveness
            valid_tags.sort(key=lambda x: x[1]['effectiveness_score'], reverse=True)

            # Extract top tags
            results = []
            for tag_key, stats in valid_tags[:limit]:
                tag_name, tag_value = tag_key.split(':', 1)
                results.append((tag_name, tag_value, stats['effectiveness_score']))

            return results

    def get_summary_stats(self) -> Dict:
        """Get summary statistics across all tags."""
        with self._lock:
            if not self._effectiveness:
                return {
                    'total_tags': 0,
                    'total_uses': 0,
                    'avg_effectiveness': 0.0,
                    'tags_with_sufficient_data': 0
                }

            total_tags = len(self._effectiveness)
            total_uses = sum(s['total_uses'] for s in self._effectiveness.values())

            tags_with_data = [
                s for s in self._effectiveness.values()
                if s['total_uses'] >= self.min_samples
            ]

            avg_effectiveness = (
                sum(s['effectiveness_score'] for s in tags_with_data) / len(tags_with_data)
                if tags_with_data else 0.0
            )

            return {
                'total_tags': total_tags,
                'total_uses': total_uses,
                'avg_effectiveness': avg_effectiveness,
                'tags_with_sufficient_data': len(tags_with_data),
                'min_samples_threshold': self.min_samples
            }

    def _save(self):
        """Save tracking data to disk."""
        try:
            self.persistence_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert defaultdict to regular dict for JSON
            data = {
                'version': '1.0',
                'last_updated': datetime.now().isoformat(),
                'effectiveness': dict(self._effectiveness)
            }

            with open(self.persistence_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved tag effectiveness data to {self.persistence_path}")

        except Exception as e:
            logger.error(f"Failed to save tag effectiveness data: {e}")

    def _load(self):
        """Load tracking data from disk."""
        try:
            if not self.persistence_path.exists():
                logger.info("No existing tag effectiveness data found")
                return

            with open(self.persistence_path, 'r') as f:
                data = json.load(f)

            # Load effectiveness data
            if 'effectiveness' in data:
                for tag_key, stats in data['effectiveness'].items():
                    self._effectiveness[tag_key] = stats

            logger.info(
                f"Loaded tag effectiveness data: {len(self._effectiveness)} tags tracked"
            )

        except Exception as e:
            logger.error(f"Failed to load tag effectiveness data: {e}")

    def persist(self):
        """Explicitly persist current state to disk."""
        with self._lock:
            self._save()

    def reset(self):
        """Reset all tracking data (use with caution)."""
        with self._lock:
            self._effectiveness.clear()
            self._save()
            logger.warning("Tag effectiveness data has been reset")


# Global singleton instance
_global_tracker: Optional[TagEffectivenessTracker] = None


def get_global_tracker() -> TagEffectivenessTracker:
    """Get or create global tag effectiveness tracker."""
    global _global_tracker

    if _global_tracker is None:
        _global_tracker = TagEffectivenessTracker()

    return _global_tracker
