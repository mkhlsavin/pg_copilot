"""
RAGAS Feedback Loop for Continuous Quality Monitoring

Provides:
- Automatic RAGAS evaluation after each query
- Metrics storage in SQLite database
- Quality degradation detection
- Historical trend analysis
- Alert generation

Author: Production Essentials - Phase 2
Date: November 25, 2025
"""

import sqlite3
import time
import json
import logging
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class EvaluationResult:
    """Single evaluation result."""
    timestamp: datetime
    scenario: str
    question: str
    answer: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    overall_score: float
    latency_ms: float
    contexts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'scenario': self.scenario,
            'question': self.question,
            'answer': self.answer[:500] if self.answer else '',  # Truncate
            'faithfulness': self.faithfulness,
            'answer_relevancy': self.answer_relevancy,
            'context_precision': self.context_precision,
            'context_recall': self.context_recall,
            'overall_score': self.overall_score,
            'latency_ms': self.latency_ms,
            'contexts_count': len(self.contexts),
            'metadata': self.metadata,
        }


@dataclass
class DegradationAlert:
    """Quality degradation alert."""
    timestamp: datetime
    severity: AlertSeverity
    metric: str
    current_value: float
    baseline_value: float
    threshold: float
    message: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity.value,
            'metric': self.metric,
            'current_value': self.current_value,
            'baseline_value': self.baseline_value,
            'threshold': self.threshold,
            'message': self.message,
        }


@dataclass
class MetricsTrend:
    """Metrics trend over time."""
    dates: List[str]
    faithfulness: List[float]
    answer_relevancy: List[float]
    context_precision: List[float]
    context_recall: List[float]
    overall: List[float]
    sample_counts: List[int]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'dates': self.dates,
            'faithfulness': self.faithfulness,
            'answer_relevancy': self.answer_relevancy,
            'context_precision': self.context_precision,
            'context_recall': self.context_recall,
            'overall': self.overall,
            'sample_counts': self.sample_counts,
        }


# ============================================================================
# RAGAS FEEDBACK LOOP
# ============================================================================

class RAGASFeedbackLoop:
    """
    Continuous quality monitoring using RAGAS metrics.

    Features:
    - Automatic evaluation after each query
    - SQLite storage for historical data
    - Degradation detection with configurable thresholds
    - Trend analysis and visualization helpers
    - Alert generation for quality issues

    Usage:
        feedback = RAGASFeedbackLoop()

        # Evaluate a response
        result = feedback.evaluate_response(
            question="How does exec_simple_query work?",
            answer="The exec_simple_query function...",
            contexts=["Context 1", "Context 2"],
            scenario="onboarding"
        )

        # Check for degradation
        alerts = feedback.detect_degradation()

        # Get trend data
        trend = feedback.get_metrics_over_time(days=7)
    """

    def __init__(
        self,
        db_path: str = "ragas_metrics.db",
        degradation_threshold: float = 0.05,
        alert_window: int = 10,
        auto_cleanup_days: int = 90
    ):
        """
        Initialize RAGAS feedback loop.

        Args:
            db_path: Path to SQLite database
            degradation_threshold: Threshold for quality degradation (5% default)
            alert_window: Number of recent evaluations for degradation detection
            auto_cleanup_days: Days to keep historical data
        """
        self.db_path = db_path
        self.degradation_threshold = degradation_threshold
        self.alert_window = alert_window
        self.auto_cleanup_days = auto_cleanup_days

        self._lock = threading.Lock()
        self._init_database()

        # Try to initialize RAGAS evaluator
        try:
            from src.evaluation.ragas_evaluator import RAGASEvaluator
            self._ragas = RAGASEvaluator()
            self._ragas_available = self._ragas.llm_available
        except Exception as e:
            logger.warning(f"RAGAS evaluator not available: {e}")
            self._ragas = None
            self._ragas_available = False

        logger.info(
            f"RAGASFeedbackLoop initialized: db={db_path}, "
            f"threshold={degradation_threshold}, ragas_available={self._ragas_available}"
        )

    def _init_database(self):
        """Initialize SQLite database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main evaluations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                scenario TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT,
                faithfulness REAL,
                answer_relevancy REAL,
                context_precision REAL,
                context_recall REAL,
                overall_score REAL,
                latency_ms REAL,
                contexts_count INTEGER,
                metadata TEXT
            )
        ''')

        # Alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                severity TEXT NOT NULL,
                metric TEXT NOT NULL,
                current_value REAL,
                baseline_value REAL,
                threshold REAL,
                message TEXT,
                acknowledged INTEGER DEFAULT 0
            )
        ''')

        # Daily aggregates for fast trend queries
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_aggregates (
                date DATE PRIMARY KEY,
                sample_count INTEGER,
                avg_faithfulness REAL,
                avg_answer_relevancy REAL,
                avg_context_precision REAL,
                avg_context_recall REAL,
                avg_overall_score REAL,
                avg_latency_ms REAL
            )
        ''')

        # Create indexes for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_evaluations_timestamp
            ON evaluations(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_evaluations_scenario
            ON evaluations(scenario)
        ''')

        conn.commit()
        conn.close()

        logger.debug("Database schema initialized")

    def evaluate_response(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        scenario: str = "unknown",
        ground_truths: Optional[List[str]] = None,
        latency_ms: float = 0.0,
        metadata: Optional[Dict] = None,
        use_ragas: bool = True
    ) -> EvaluationResult:
        """
        Evaluate a single response using RAGAS metrics.

        Args:
            question: User question
            answer: Generated answer
            contexts: Retrieved contexts
            scenario: Scenario name
            ground_truths: Reference answers (optional)
            latency_ms: Response latency
            metadata: Additional metadata
            use_ragas: Use RAGAS LLM-based evaluation

        Returns:
            EvaluationResult with RAGAS metrics
        """
        timestamp = datetime.now()

        # Compute metrics
        if use_ragas and self._ragas_available:
            scores = self._evaluate_with_ragas(question, answer, contexts, ground_truths)
        else:
            scores = self._evaluate_custom(question, answer, contexts)

        # Create result
        result = EvaluationResult(
            timestamp=timestamp,
            scenario=scenario,
            question=question,
            answer=answer,
            faithfulness=scores.get('faithfulness', 0.0),
            answer_relevancy=scores.get('answer_relevancy', 0.0),
            context_precision=scores.get('context_precision', 0.0),
            context_recall=scores.get('context_recall', 0.0),
            overall_score=scores.get('overall_score', 0.0),
            latency_ms=latency_ms,
            contexts=contexts,
            metadata=metadata or {}
        )

        # Store in database
        self._store_evaluation(result)

        # Update daily aggregate
        self._update_daily_aggregate(result)

        logger.debug(f"Evaluation stored: scenario={scenario}, overall={result.overall_score:.3f}")

        return result

    def _evaluate_with_ragas(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truths: Optional[List[str]]
    ) -> Dict[str, float]:
        """Evaluate using RAGAS library."""
        try:
            from datasets import Dataset
            from ragas import evaluate
            from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall

            # Prepare dataset
            data = {
                'question': [question],
                'answer': [answer],
                'contexts': [contexts],
                'ground_truth': ground_truths if ground_truths else [[]]
            }
            dataset = Dataset.from_dict(data)

            # Evaluate
            result = evaluate(
                dataset,
                metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
                llm=self._ragas.llm
            )

            # Extract scores
            scores = {}
            for metric in ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']:
                if metric in result:
                    scores[metric] = float(result[metric])
                else:
                    scores[metric] = 0.0

            scores['overall_score'] = sum(scores.values()) / len(scores) if scores else 0.0

            return scores

        except Exception as e:
            logger.warning(f"RAGAS evaluation failed: {e}, using custom metrics")
            return self._evaluate_custom(question, answer, contexts)

    def _evaluate_custom(
        self,
        question: str,
        answer: str,
        contexts: List[str]
    ) -> Dict[str, float]:
        """
        Custom evaluation metrics when RAGAS is not available.

        Uses simple heuristics:
        - Answer length and content presence
        - Context overlap with answer
        - Question keyword coverage
        """
        scores = {}

        # Faithfulness: Does answer use context?
        if contexts and answer:
            context_text = ' '.join(contexts).lower()
            answer_words = set(answer.lower().split())
            context_words = set(context_text.split())
            overlap = len(answer_words & context_words)
            scores['faithfulness'] = min(1.0, overlap / max(len(answer_words), 1))
        else:
            scores['faithfulness'] = 0.0

        # Answer relevancy: Does answer address the question?
        if question and answer:
            question_words = set(question.lower().split())
            answer_text = answer.lower()
            covered = sum(1 for w in question_words if w in answer_text)
            scores['answer_relevancy'] = min(1.0, covered / max(len(question_words), 1))
        else:
            scores['answer_relevancy'] = 0.0

        # Context precision: Are contexts relevant?
        if contexts and question:
            question_lower = question.lower()
            relevant_contexts = sum(1 for c in contexts if any(w in c.lower() for w in question_lower.split()))
            scores['context_precision'] = relevant_contexts / max(len(contexts), 1)
        else:
            scores['context_precision'] = 0.0

        # Context recall: Estimate based on context count
        scores['context_recall'] = min(1.0, len(contexts) / 5)  # Assume 5 contexts is ideal

        # Overall
        scores['overall_score'] = sum(scores.values()) / len(scores) if scores else 0.0

        return scores

    def _store_evaluation(self, result: EvaluationResult):
        """Store evaluation result in database."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO evaluations (
                    timestamp, scenario, question, answer,
                    faithfulness, answer_relevancy, context_precision, context_recall,
                    overall_score, latency_ms, contexts_count, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.timestamp.isoformat(),
                result.scenario,
                result.question,
                result.answer[:5000] if result.answer else '',  # Limit size
                result.faithfulness,
                result.answer_relevancy,
                result.context_precision,
                result.context_recall,
                result.overall_score,
                result.latency_ms,
                len(result.contexts),
                json.dumps(result.metadata) if result.metadata else None
            ))

            conn.commit()
            conn.close()

    def _update_daily_aggregate(self, result: EvaluationResult):
        """Update daily aggregate table."""
        date_str = result.timestamp.strftime('%Y-%m-%d')

        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get current aggregate
            cursor.execute('''
                SELECT sample_count, avg_faithfulness, avg_answer_relevancy,
                       avg_context_precision, avg_context_recall, avg_overall_score, avg_latency_ms
                FROM daily_aggregates WHERE date = ?
            ''', (date_str,))

            row = cursor.fetchone()

            if row:
                # Update existing aggregate
                n = row[0]
                new_n = n + 1
                cursor.execute('''
                    UPDATE daily_aggregates SET
                        sample_count = ?,
                        avg_faithfulness = (? * ? + ?) / ?,
                        avg_answer_relevancy = (? * ? + ?) / ?,
                        avg_context_precision = (? * ? + ?) / ?,
                        avg_context_recall = (? * ? + ?) / ?,
                        avg_overall_score = (? * ? + ?) / ?,
                        avg_latency_ms = (? * ? + ?) / ?
                    WHERE date = ?
                ''', (
                    new_n,
                    row[1], n, result.faithfulness, new_n,
                    row[2], n, result.answer_relevancy, new_n,
                    row[3], n, result.context_precision, new_n,
                    row[4], n, result.context_recall, new_n,
                    row[5], n, result.overall_score, new_n,
                    row[6], n, result.latency_ms, new_n,
                    date_str
                ))
            else:
                # Insert new aggregate
                cursor.execute('''
                    INSERT INTO daily_aggregates (
                        date, sample_count, avg_faithfulness, avg_answer_relevancy,
                        avg_context_precision, avg_context_recall, avg_overall_score, avg_latency_ms
                    ) VALUES (?, 1, ?, ?, ?, ?, ?, ?)
                ''', (
                    date_str,
                    result.faithfulness,
                    result.answer_relevancy,
                    result.context_precision,
                    result.context_recall,
                    result.overall_score,
                    result.latency_ms
                ))

            conn.commit()
            conn.close()

    def get_metrics_over_time(
        self,
        scenario: Optional[str] = None,
        days: int = 7
    ) -> MetricsTrend:
        """
        Get metrics trend over time.

        Args:
            scenario: Filter by scenario (optional)
            days: Number of days to include

        Returns:
            MetricsTrend with daily metrics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if scenario:
            # Query raw evaluations for specific scenario
            cursor.execute('''
                SELECT
                    DATE(timestamp) as date,
                    COUNT(*) as sample_count,
                    AVG(faithfulness) as avg_faithfulness,
                    AVG(answer_relevancy) as avg_relevancy,
                    AVG(context_precision) as avg_precision,
                    AVG(context_recall) as avg_recall,
                    AVG(overall_score) as avg_overall
                FROM evaluations
                WHERE timestamp >= datetime('now', ? || ' days')
                AND scenario = ?
                GROUP BY DATE(timestamp)
                ORDER BY date
            ''', (f'-{days}', scenario))
        else:
            # Use pre-aggregated data
            cursor.execute('''
                SELECT
                    date,
                    sample_count,
                    avg_faithfulness,
                    avg_answer_relevancy,
                    avg_context_precision,
                    avg_context_recall,
                    avg_overall_score
                FROM daily_aggregates
                WHERE date >= date('now', ? || ' days')
                ORDER BY date
            ''', (f'-{days}',))

        rows = cursor.fetchall()
        conn.close()

        return MetricsTrend(
            dates=[r[0] for r in rows],
            sample_counts=[r[1] for r in rows],
            faithfulness=[r[2] or 0.0 for r in rows],
            answer_relevancy=[r[3] or 0.0 for r in rows],
            context_precision=[r[4] or 0.0 for r in rows],
            context_recall=[r[5] or 0.0 for r in rows],
            overall=[r[6] or 0.0 for r in rows],
        )

    def detect_degradation(
        self,
        threshold: Optional[float] = None,
        window: Optional[int] = None
    ) -> List[DegradationAlert]:
        """
        Detect quality degradation.

        Compares recent evaluations to previous window.

        Args:
            threshold: Degradation threshold (default from init)
            window: Number of evaluations to compare

        Returns:
            List of degradation alerts
        """
        threshold = threshold or self.degradation_threshold
        window = window or self.alert_window

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get recent scores
        cursor.execute('''
            SELECT faithfulness, answer_relevancy, context_precision,
                   context_recall, overall_score
            FROM evaluations
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (window * 2,))

        rows = cursor.fetchall()
        conn.close()

        if len(rows) < window * 2:
            return []  # Not enough data

        # Split into recent and previous
        recent = rows[:window]
        previous = rows[window:window*2]

        alerts = []
        metrics = ['faithfulness', 'answer_relevancy', 'context_precision',
                   'context_recall', 'overall_score']

        for i, metric in enumerate(metrics):
            recent_avg = sum(r[i] or 0 for r in recent) / window
            previous_avg = sum(r[i] or 0 for r in previous) / window

            degradation = previous_avg - recent_avg

            if degradation > threshold:
                severity = AlertSeverity.CRITICAL if degradation > threshold * 2 else AlertSeverity.WARNING

                alert = DegradationAlert(
                    timestamp=datetime.now(),
                    severity=severity,
                    metric=metric,
                    current_value=recent_avg,
                    baseline_value=previous_avg,
                    threshold=threshold,
                    message=f"{metric} degraded by {degradation:.1%}: {previous_avg:.3f} -> {recent_avg:.3f}"
                )

                alerts.append(alert)
                self._store_alert(alert)

                logger.warning(f"Degradation detected: {alert.message}")

        return alerts

    def _store_alert(self, alert: DegradationAlert):
        """Store alert in database."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO alerts (
                    timestamp, severity, metric, current_value,
                    baseline_value, threshold, message
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.timestamp.isoformat(),
                alert.severity.value,
                alert.metric,
                alert.current_value,
                alert.baseline_value,
                alert.threshold,
                alert.message
            ))

            conn.commit()
            conn.close()

    def get_recent_alerts(self, limit: int = 10) -> List[DegradationAlert]:
        """Get recent alerts."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT timestamp, severity, metric, current_value,
                   baseline_value, threshold, message
            FROM alerts
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))

        alerts = []
        for row in cursor.fetchall():
            alerts.append(DegradationAlert(
                timestamp=datetime.fromisoformat(row[0]),
                severity=AlertSeverity(row[1]),
                metric=row[2],
                current_value=row[3],
                baseline_value=row[4],
                threshold=row[5],
                message=row[6]
            ))

        conn.close()
        return alerts

    def get_summary_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get summary statistics for the period.

        Args:
            days: Number of days to include

        Returns:
            Summary statistics dictionary
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                COUNT(*) as total_evaluations,
                AVG(faithfulness) as avg_faithfulness,
                AVG(answer_relevancy) as avg_relevancy,
                AVG(context_precision) as avg_precision,
                AVG(context_recall) as avg_recall,
                AVG(overall_score) as avg_overall,
                AVG(latency_ms) as avg_latency,
                MIN(overall_score) as min_overall,
                MAX(overall_score) as max_overall
            FROM evaluations
            WHERE timestamp >= datetime('now', ? || ' days')
        ''', (f'-{days}',))

        row = cursor.fetchone()

        # Get scenario breakdown
        cursor.execute('''
            SELECT scenario, COUNT(*), AVG(overall_score)
            FROM evaluations
            WHERE timestamp >= datetime('now', ? || ' days')
            GROUP BY scenario
        ''', (f'-{days}',))

        scenarios = {r[0]: {'count': r[1], 'avg_score': r[2]} for r in cursor.fetchall()}

        conn.close()

        return {
            'period_days': days,
            'total_evaluations': row[0] or 0,
            'avg_faithfulness': row[1] or 0.0,
            'avg_answer_relevancy': row[2] or 0.0,
            'avg_context_precision': row[3] or 0.0,
            'avg_context_recall': row[4] or 0.0,
            'avg_overall_score': row[5] or 0.0,
            'avg_latency_ms': row[6] or 0.0,
            'min_overall_score': row[7] or 0.0,
            'max_overall_score': row[8] or 0.0,
            'scenarios': scenarios
        }

    def cleanup_old_data(self, days: Optional[int] = None):
        """
        Remove old evaluation data.

        Args:
            days: Days to keep (default from init)
        """
        days = days or self.auto_cleanup_days

        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                DELETE FROM evaluations
                WHERE timestamp < datetime('now', ? || ' days')
            ''', (f'-{days}',))

            deleted = cursor.rowcount

            cursor.execute('''
                DELETE FROM daily_aggregates
                WHERE date < date('now', ? || ' days')
            ''', (f'-{days}',))

            conn.commit()
            conn.close()

            logger.info(f"Cleaned up {deleted} old evaluations")

    def is_healthy(self, min_score: float = 0.6) -> Tuple[bool, str]:
        """
        Check if system is healthy based on recent evaluations.

        Args:
            min_score: Minimum acceptable average score

        Returns:
            Tuple of (is_healthy, message)
        """
        stats = self.get_summary_stats(days=1)

        if stats['total_evaluations'] == 0:
            return True, "No recent evaluations"

        avg_score = stats['avg_overall_score']

        if avg_score < min_score:
            return False, f"Average score {avg_score:.3f} below threshold {min_score}"

        return True, f"Healthy: avg_score={avg_score:.3f}"


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Global singleton instance
_feedback_loop: Optional[RAGASFeedbackLoop] = None


def get_feedback_loop(db_path: str = "ragas_metrics.db") -> RAGASFeedbackLoop:
    """Get or create the global feedback loop instance."""
    global _feedback_loop
    if _feedback_loop is None:
        _feedback_loop = RAGASFeedbackLoop(db_path=db_path)
    return _feedback_loop


def evaluate_and_store(
    question: str,
    answer: str,
    contexts: List[str],
    scenario: str = "unknown",
    latency_ms: float = 0.0
) -> EvaluationResult:
    """
    Convenience function to evaluate and store a response.

    Args:
        question: User question
        answer: Generated answer
        contexts: Retrieved contexts
        scenario: Scenario name
        latency_ms: Response latency

    Returns:
        EvaluationResult
    """
    feedback = get_feedback_loop()
    return feedback.evaluate_response(
        question=question,
        answer=answer,
        contexts=contexts,
        scenario=scenario,
        latency_ms=latency_ms
    )


def check_quality_health() -> Tuple[bool, str]:
    """Check if system quality is healthy."""
    feedback = get_feedback_loop()
    return feedback.is_healthy()
