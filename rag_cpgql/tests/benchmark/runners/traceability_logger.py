"""
Traceability Logger for RAG-CPGQL Benchmark

Provides comprehensive logging for debugging benchmark runs:
- Intent classification details
- Workflow execution traces
- SQL queries and results
- Evaluation metrics
- Error tracking

Author: RAG-CPGQL Test Suite
Date: November 2025
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class IntentTrace:
    """Trace data for intent classification"""
    method: str = ""  # "keyword" or "llm"
    confidence: float = 0.0
    classified_intent: str = ""
    alternative_intents: List[Dict[str, float]] = field(default_factory=list)
    classification_time_ms: float = 0.0


@dataclass
class QueryTrace:
    """Trace data for a single database query"""
    query: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    rows_returned: int = 0
    error: Optional[str] = None


@dataclass
class WorkflowTrace:
    """Trace data for workflow execution"""
    workflow_name: str = ""
    nodes_executed: List[str] = field(default_factory=list)
    sql_queries: List[QueryTrace] = field(default_factory=list)
    graph_methods_called: List[str] = field(default_factory=list)
    llm_calls: List[Dict[str, Any]] = field(default_factory=list)
    total_duration_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class EvaluationTrace:
    """Trace data for evaluation results"""
    precision_at_k: Dict[int, float] = field(default_factory=dict)
    recall_at_k: Dict[int, float] = field(default_factory=dict)
    f1_at_k: Dict[int, float] = field(default_factory=dict)
    mrr: float = 0.0
    ndcg_at_k: Dict[int, float] = field(default_factory=dict)
    semantic_similarity: Optional[float] = None
    keyword_coverage: float = 0.0
    factual_accuracy: float = 0.0
    passed: bool = False
    failure_reason: Optional[str] = None


@dataclass
class QuestionTrace:
    """Complete trace for a single question"""
    trace_id: str = ""
    question_id: str = ""
    scenario_id: str = ""
    question_text: str = ""
    language: str = "en"
    difficulty: str = "medium"

    # Execution traces
    intent_classification: IntentTrace = field(default_factory=IntentTrace)
    workflow_execution: WorkflowTrace = field(default_factory=WorkflowTrace)

    # Results
    generated_answer: str = ""
    retrieved_items: List[str] = field(default_factory=list)
    retrieved_count: int = 0

    # Evaluation
    evaluation: EvaluationTrace = field(default_factory=EvaluationTrace)

    # Timing
    start_time: str = ""
    end_time: str = ""
    total_duration_ms: float = 0.0

    # Error tracking
    error: Optional[str] = None
    error_traceback: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'trace_id': self.trace_id,
            'question_id': self.question_id,
            'scenario_id': self.scenario_id,
            'question_text': self.question_text,
            'language': self.language,
            'difficulty': self.difficulty,
            'intent_classification': asdict(self.intent_classification),
            'workflow_execution': {
                'workflow_name': self.workflow_execution.workflow_name,
                'nodes_executed': self.workflow_execution.nodes_executed,
                'sql_queries': [asdict(q) for q in self.workflow_execution.sql_queries],
                'graph_methods_called': self.workflow_execution.graph_methods_called,
                'llm_calls': self.workflow_execution.llm_calls,
                'total_duration_ms': self.workflow_execution.total_duration_ms,
                'error': self.workflow_execution.error,
            },
            'generated_answer': self.generated_answer,
            'retrieved_items': self.retrieved_items,
            'retrieved_count': self.retrieved_count,
            'evaluation': asdict(self.evaluation),
            'start_time': self.start_time,
            'end_time': self.end_time,
            'total_duration_ms': self.total_duration_ms,
            'error': self.error,
            'error_traceback': self.error_traceback,
        }


class TraceabilityLogger:
    """
    Comprehensive traceability logger for benchmark debugging.

    Usage:
        logger = TraceabilityLogger(output_dir="results/traces")

        # Start tracing a question
        trace = logger.start_question("CG_EN_001", "scenario_02", "What functions...")

        # Log intent classification
        logger.log_intent(trace, method="keyword", intent="security_audit", confidence=0.95)

        # Log workflow execution
        logger.log_workflow_start(trace, "security_workflow")
        logger.log_sql_query(trace, "SELECT * FROM...", duration_ms=12, rows=47)
        logger.log_workflow_end(trace)

        # Log evaluation
        logger.log_evaluation(trace, precision=0.8, recall=0.72, mrr=1.0)

        # Finish and save
        logger.finish_question(trace)
    """

    def __init__(
        self,
        output_dir: str = "results/traces",
        log_level: int = logging.INFO,
        write_individual_traces: bool = True
    ):
        """
        Initialize traceability logger.

        Args:
            output_dir: Directory to write trace files
            log_level: Python logging level
            write_individual_traces: Whether to write individual JSON files per question
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.write_individual_traces = write_individual_traces
        self.traces: List[QuestionTrace] = []
        self.current_run_id: Optional[str] = None

        # Setup Python logger
        self.logger = logging.getLogger("benchmark.traceability")
        self.logger.setLevel(log_level)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(handler)

    def start_run(self, run_id: Optional[str] = None) -> str:
        """
        Start a new benchmark run.

        Args:
            run_id: Optional run identifier. If None, generates timestamp-based ID.

        Returns:
            The run ID
        """
        self.current_run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.traces = []

        # Create run directory
        run_dir = self.output_dir / self.current_run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Started benchmark run: {self.current_run_id}")
        return self.current_run_id

    def start_question(
        self,
        question_id: str,
        scenario_id: str,
        question_text: str,
        language: str = "en",
        difficulty: str = "medium"
    ) -> QuestionTrace:
        """
        Start tracing a new question.

        Args:
            question_id: Unique question identifier
            scenario_id: Scenario this question belongs to
            question_text: The actual question text
            language: Question language (en/ru)
            difficulty: Question difficulty (easy/medium/hard)

        Returns:
            QuestionTrace object to accumulate trace data
        """
        trace_id = f"TRACE_{self.current_run_id or 'DEFAULT'}_{question_id}"

        trace = QuestionTrace(
            trace_id=trace_id,
            question_id=question_id,
            scenario_id=scenario_id,
            question_text=question_text,
            language=language,
            difficulty=difficulty,
            start_time=datetime.now().isoformat(),
        )

        self.logger.debug(f"Started tracing: {question_id}")
        return trace

    def log_intent(
        self,
        trace: QuestionTrace,
        method: str,
        intent: str,
        confidence: float,
        alternatives: Optional[List[Dict[str, float]]] = None,
        duration_ms: float = 0.0
    ):
        """Log intent classification results"""
        trace.intent_classification = IntentTrace(
            method=method,
            confidence=confidence,
            classified_intent=intent,
            alternative_intents=alternatives or [],
            classification_time_ms=duration_ms,
        )

        self.logger.debug(
            f"[{trace.question_id}] Intent: {intent} ({method}, conf={confidence:.2f})"
        )

    def log_workflow_start(self, trace: QuestionTrace, workflow_name: str):
        """Log workflow execution start"""
        trace.workflow_execution.workflow_name = workflow_name
        self.logger.debug(f"[{trace.question_id}] Workflow started: {workflow_name}")

    def log_workflow_node(self, trace: QuestionTrace, node_name: str):
        """Log a workflow node execution"""
        trace.workflow_execution.nodes_executed.append(node_name)
        self.logger.debug(f"[{trace.question_id}] Node executed: {node_name}")

    def log_sql_query(
        self,
        trace: QuestionTrace,
        query: str,
        duration_ms: float = 0.0,
        rows: int = 0,
        params: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """Log a SQL query execution"""
        query_trace = QueryTrace(
            query=query[:500],  # Truncate long queries
            params=params or {},
            duration_ms=duration_ms,
            rows_returned=rows,
            error=error,
        )
        trace.workflow_execution.sql_queries.append(query_trace)

        status = "OK" if not error else f"ERROR: {error}"
        self.logger.debug(
            f"[{trace.question_id}] SQL: {query[:50]}... ({duration_ms:.1f}ms, {rows} rows) [{status}]"
        )

    def log_graph_method(self, trace: QuestionTrace, method_name: str):
        """Log a graph method call"""
        trace.workflow_execution.graph_methods_called.append(method_name)
        self.logger.debug(f"[{trace.question_id}] Graph method: {method_name}")

    def log_llm_call(
        self,
        trace: QuestionTrace,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        duration_ms: float = 0.0,
        error: Optional[str] = None
    ):
        """Log an LLM API call"""
        llm_trace = {
            'model': model,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'duration_ms': duration_ms,
            'error': error,
        }
        trace.workflow_execution.llm_calls.append(llm_trace)

        self.logger.debug(
            f"[{trace.question_id}] LLM: {model} ({prompt_tokens}+{completion_tokens} tokens, {duration_ms:.1f}ms)"
        )

    def log_workflow_end(
        self,
        trace: QuestionTrace,
        duration_ms: float = 0.0,
        error: Optional[str] = None
    ):
        """Log workflow execution end"""
        trace.workflow_execution.total_duration_ms = duration_ms
        trace.workflow_execution.error = error

        status = "OK" if not error else f"ERROR: {error}"
        self.logger.debug(
            f"[{trace.question_id}] Workflow completed: {duration_ms:.1f}ms [{status}]"
        )

    def log_retrieval(
        self,
        trace: QuestionTrace,
        retrieved_items: List[str],
        answer: str
    ):
        """Log retrieval results"""
        trace.retrieved_items = retrieved_items
        trace.retrieved_count = len(retrieved_items)
        trace.generated_answer = answer

        self.logger.debug(
            f"[{trace.question_id}] Retrieved {len(retrieved_items)} items, answer length: {len(answer)}"
        )

    def log_evaluation(
        self,
        trace: QuestionTrace,
        precision_at_k: Optional[Dict[int, float]] = None,
        recall_at_k: Optional[Dict[int, float]] = None,
        f1_at_k: Optional[Dict[int, float]] = None,
        mrr: float = 0.0,
        ndcg_at_k: Optional[Dict[int, float]] = None,
        semantic_similarity: Optional[float] = None,
        keyword_coverage: float = 0.0,
        factual_accuracy: float = 0.0,
        passed: bool = False,
        failure_reason: Optional[str] = None
    ):
        """Log evaluation metrics"""
        trace.evaluation = EvaluationTrace(
            precision_at_k=precision_at_k or {},
            recall_at_k=recall_at_k or {},
            f1_at_k=f1_at_k or {},
            mrr=mrr,
            ndcg_at_k=ndcg_at_k or {},
            semantic_similarity=semantic_similarity,
            keyword_coverage=keyword_coverage,
            factual_accuracy=factual_accuracy,
            passed=passed,
            failure_reason=failure_reason,
        )

        status = "PASS" if passed else f"FAIL: {failure_reason or 'unknown'}"
        self.logger.info(
            f"[{trace.question_id}] Evaluation: P@10={precision_at_k.get(10, 0):.2f}, "
            f"R@10={recall_at_k.get(10, 0):.2f}, MRR={mrr:.2f} [{status}]"
        )

    def log_error(
        self,
        trace: QuestionTrace,
        error: str,
        traceback: Optional[str] = None
    ):
        """Log an error"""
        trace.error = error
        trace.error_traceback = traceback
        self.logger.error(f"[{trace.question_id}] Error: {error}")

    def finish_question(self, trace: QuestionTrace) -> Dict[str, Any]:
        """
        Finish tracing a question and save trace data.

        Args:
            trace: The QuestionTrace to finish

        Returns:
            Dictionary representation of the trace
        """
        trace.end_time = datetime.now().isoformat()

        # Calculate total duration
        start = datetime.fromisoformat(trace.start_time)
        end = datetime.fromisoformat(trace.end_time)
        trace.total_duration_ms = (end - start).total_seconds() * 1000

        # Add to traces list
        self.traces.append(trace)

        # Write individual trace file if enabled
        if self.write_individual_traces and self.current_run_id:
            trace_file = self.output_dir / self.current_run_id / f"{trace.question_id}.json"
            with open(trace_file, 'w', encoding='utf-8') as f:
                json.dump(trace.to_dict(), f, indent=2, ensure_ascii=False)

        self.logger.debug(f"Finished tracing: {trace.question_id} ({trace.total_duration_ms:.1f}ms)")
        return trace.to_dict()

    def finish_run(self) -> Dict[str, Any]:
        """
        Finish the benchmark run and save aggregate results.

        Returns:
            Summary dictionary with run statistics
        """
        if not self.current_run_id:
            self.logger.warning("No active run to finish")
            return {}

        # Calculate summary statistics
        total = len(self.traces)
        passed = sum(1 for t in self.traces if t.evaluation.passed)
        failed = total - passed

        by_scenario = {}
        by_difficulty = {'easy': [], 'medium': [], 'hard': []}

        for trace in self.traces:
            # By scenario
            if trace.scenario_id not in by_scenario:
                by_scenario[trace.scenario_id] = {'total': 0, 'passed': 0, 'traces': []}
            by_scenario[trace.scenario_id]['total'] += 1
            if trace.evaluation.passed:
                by_scenario[trace.scenario_id]['passed'] += 1
            by_scenario[trace.scenario_id]['traces'].append(trace.question_id)

            # By difficulty
            if trace.difficulty in by_difficulty:
                by_difficulty[trace.difficulty].append(trace.evaluation.passed)

        # Calculate averages
        avg_metrics = {
            'avg_precision_at_10': 0.0,
            'avg_recall_at_10': 0.0,
            'avg_mrr': 0.0,
            'avg_semantic_similarity': 0.0,
            'avg_keyword_coverage': 0.0,
            'avg_duration_ms': 0.0,
        }

        if self.traces:
            avg_metrics['avg_precision_at_10'] = sum(
                t.evaluation.precision_at_k.get(10, 0) for t in self.traces
            ) / total
            avg_metrics['avg_recall_at_10'] = sum(
                t.evaluation.recall_at_k.get(10, 0) for t in self.traces
            ) / total
            avg_metrics['avg_mrr'] = sum(t.evaluation.mrr for t in self.traces) / total

            sem_sims = [t.evaluation.semantic_similarity for t in self.traces
                       if t.evaluation.semantic_similarity is not None]
            if sem_sims:
                avg_metrics['avg_semantic_similarity'] = sum(sem_sims) / len(sem_sims)

            avg_metrics['avg_keyword_coverage'] = sum(
                t.evaluation.keyword_coverage for t in self.traces
            ) / total
            avg_metrics['avg_duration_ms'] = sum(t.total_duration_ms for t in self.traces) / total

        summary = {
            'run_id': self.current_run_id,
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_questions': total,
                'passed': passed,
                'failed': failed,
                'pass_rate': passed / total if total > 0 else 0.0,
            },
            'by_scenario': {
                sid: {
                    'total': data['total'],
                    'passed': data['passed'],
                    'pass_rate': data['passed'] / data['total'] if data['total'] > 0 else 0.0,
                }
                for sid, data in by_scenario.items()
            },
            'by_difficulty': {
                diff: {
                    'total': len(results),
                    'passed': sum(results),
                    'pass_rate': sum(results) / len(results) if results else 0.0,
                }
                for diff, results in by_difficulty.items()
            },
            'average_metrics': avg_metrics,
        }

        # Save summary
        summary_file = self.output_dir / self.current_run_id / "run_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        # Save all traces
        all_traces_file = self.output_dir / self.current_run_id / "all_traces.json"
        with open(all_traces_file, 'w', encoding='utf-8') as f:
            json.dump([t.to_dict() for t in self.traces], f, indent=2, ensure_ascii=False)

        self.logger.info(
            f"Run {self.current_run_id} completed: {passed}/{total} passed ({100*passed/total:.1f}%)"
        )

        return summary

    def get_failed_traces(self) -> List[QuestionTrace]:
        """Get all traces that failed evaluation"""
        return [t for t in self.traces if not t.evaluation.passed]

    def get_traces_by_scenario(self, scenario_id: str) -> List[QuestionTrace]:
        """Get all traces for a specific scenario"""
        return [t for t in self.traces if t.scenario_id == scenario_id]

    def get_slow_traces(self, threshold_ms: float = 5000) -> List[QuestionTrace]:
        """Get traces that took longer than threshold"""
        return [t for t in self.traces if t.total_duration_ms > threshold_ms]
