"""
Error Handling Framework for Workflow Agents

Provides decorators and utilities for robust error handling in agent-based workflows.
Ensures graceful degradation when individual agents fail.

Key Features:
- @safe_agent_execution decorator for wrapping agent calls
- Structured error responses with agent name and error details
- Partial result aggregation for multi-agent workflows
- Logging integration for debugging

Author: Production Fixes - Phase 1
Date: November 25, 2025
"""

from typing import Any, Dict, Optional, Callable, List, TypeVar, Union
from functools import wraps
from dataclasses import dataclass, field
from datetime import datetime
import logging
import traceback

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class AgentResult:
    """
    Structured result from agent execution.

    Attributes:
        success: Whether the agent completed successfully
        result: The actual result (or fallback value on failure)
        agent: Name of the agent
        error: Error details if failed (None if success)
        duration_ms: Execution time in milliseconds
        timestamp: When the execution completed
    """
    success: bool
    result: Any
    agent: str
    error: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'success': self.success,
            'result': self.result,
            'agent': self.agent,
            'error': self.error,
            'duration_ms': self.duration_ms,
            'timestamp': self.timestamp.isoformat(),
        }


class AgentExecutionError(Exception):
    """
    Exception for agent execution failures.

    Attributes:
        agent_name: Name of the failed agent
        original_error: The underlying exception
        context: Additional context about the failure
    """
    def __init__(
        self,
        agent_name: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ):
        self.agent_name = agent_name
        self.original_error = error
        self.context = context or {}
        super().__init__(f"Agent '{agent_name}' failed: {error}")


def safe_agent_execution(
    agent_name: str,
    fallback_result: Any = None,
    log_errors: bool = True,
    include_traceback: bool = False
) -> Callable:
    """
    Decorator for safe agent execution with error handling.

    Wraps agent functions to catch exceptions and return structured results.
    On failure, returns the fallback_result instead of crashing.

    Args:
        agent_name: Identifier for the agent (used in logs and results)
        fallback_result: Value to return on failure
        log_errors: Whether to log errors (default: True)
        include_traceback: Include traceback in error dict (default: False)

    Returns:
        Decorator function

    Example:
        @safe_agent_execution('analyzer', fallback_result={'analysis': 'failed'})
        def analyze_code(code: str) -> Dict:
            return analyzer.analyze(code)

        result = analyze_code("def foo(): pass")
        if result.success:
            print(result.result)
        else:
            print(f"Agent failed: {result.error}")
    """
    def decorator(func: Callable[..., T]) -> Callable[..., AgentResult]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> AgentResult:
            import time
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                return AgentResult(
                    success=True,
                    result=result,
                    agent=agent_name,
                    error=None,
                    duration_ms=duration_ms,
                )

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000

                # Build error details
                error_details = {
                    'type': type(e).__name__,
                    'message': str(e),
                }

                if include_traceback:
                    error_details['traceback'] = traceback.format_exc()

                # Log if enabled
                if log_errors:
                    logger.error(
                        f"Agent '{agent_name}' failed after {duration_ms:.1f}ms: "
                        f"{type(e).__name__}: {e}",
                        exc_info=True,
                        extra={
                            'agent': agent_name,
                            'args_preview': str(args)[:200] if args else None,
                        }
                    )

                return AgentResult(
                    success=False,
                    result=fallback_result,
                    agent=agent_name,
                    error=error_details,
                    duration_ms=duration_ms,
                )

        return wrapper
    return decorator


def execute_agent_safely(
    func: Callable,
    agent_name: str,
    fallback_result: Any = None,
    *args,
    **kwargs
) -> AgentResult:
    """
    Execute a function with safe error handling (non-decorator version).

    Useful when you can't use decorators or need dynamic agent names.

    Args:
        func: Function to execute
        agent_name: Name for logging and results
        fallback_result: Value to return on failure
        *args: Arguments to pass to func
        **kwargs: Keyword arguments to pass to func

    Returns:
        AgentResult with success status and result/error

    Example:
        result = execute_agent_safely(
            analyzer.analyze,
            'analyzer',
            fallback_result={},
            code="def foo(): pass"
        )
    """
    import time
    start_time = time.time()

    try:
        result = func(*args, **kwargs)
        duration_ms = (time.time() - start_time) * 1000

        return AgentResult(
            success=True,
            result=result,
            agent=agent_name,
            duration_ms=duration_ms,
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000

        logger.error(
            f"Agent '{agent_name}' failed: {type(e).__name__}: {e}",
            exc_info=True
        )

        return AgentResult(
            success=False,
            result=fallback_result,
            agent=agent_name,
            error={
                'type': type(e).__name__,
                'message': str(e),
            },
            duration_ms=duration_ms,
        )


@dataclass
class AggregatedResults:
    """
    Aggregated results from multiple agent executions.

    Attributes:
        success_rate: Fraction of agents that succeeded (0.0-1.0)
        successful_agents: List of agent names that succeeded
        failed_agents: List of agent names that failed
        results: List of successful results
        errors: List of error dicts from failed agents
        degraded: True if any agent failed (partial success)
        total_duration_ms: Sum of all agent durations
    """
    success_rate: float
    successful_agents: List[str]
    failed_agents: List[str]
    results: List[Any]
    errors: List[Dict[str, Any]]
    degraded: bool
    total_duration_ms: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'success_rate': self.success_rate,
            'successful_agents': self.successful_agents,
            'failed_agents': self.failed_agents,
            'results': self.results,
            'errors': self.errors,
            'degraded': self.degraded,
            'total_duration_ms': self.total_duration_ms,
        }


def aggregate_partial_results(
    results: List[Union[AgentResult, Dict[str, Any]]]
) -> AggregatedResults:
    """
    Aggregate results from multiple agents into a summary.

    Handles cases where some agents succeeded and others failed,
    enabling graceful degradation with partial results.

    Args:
        results: List of AgentResult or dict with 'success' key

    Returns:
        AggregatedResults with summary statistics

    Example:
        results = [
            AgentResult(success=True, result={'data': 1}, agent='agent1'),
            AgentResult(success=False, result=None, agent='agent2', error={'message': 'failed'}),
            AgentResult(success=True, result={'data': 2}, agent='agent3'),
        ]

        summary = aggregate_partial_results(results)
        print(f"Success rate: {summary.success_rate}")  # 0.667
        print(f"Degraded: {summary.degraded}")  # True
    """
    if not results:
        return AggregatedResults(
            success_rate=1.0,
            successful_agents=[],
            failed_agents=[],
            results=[],
            errors=[],
            degraded=False,
            total_duration_ms=0.0,
        )

    # Normalize to AgentResult-like dicts
    normalized = []
    for r in results:
        if isinstance(r, AgentResult):
            normalized.append({
                'success': r.success,
                'result': r.result,
                'agent': r.agent,
                'error': r.error,
                'duration_ms': r.duration_ms or 0,
            })
        elif isinstance(r, dict):
            normalized.append({
                'success': r.get('success', False),
                'result': r.get('result'),
                'agent': r.get('agent', 'unknown'),
                'error': r.get('error'),
                'duration_ms': r.get('duration_ms', 0),
            })
        else:
            # Treat unknown types as failed
            normalized.append({
                'success': False,
                'result': None,
                'agent': 'unknown',
                'error': {'message': f'Invalid result type: {type(r)}'},
                'duration_ms': 0,
            })

    # Aggregate
    successful = [r for r in normalized if r['success']]
    failed = [r for r in normalized if not r['success']]

    success_rate = len(successful) / len(normalized) if normalized else 0.0
    total_duration = sum(r.get('duration_ms', 0) or 0 for r in normalized)

    return AggregatedResults(
        success_rate=success_rate,
        successful_agents=[r['agent'] for r in successful],
        failed_agents=[r['agent'] for r in failed],
        results=[r['result'] for r in successful],
        errors=[r['error'] for r in failed if r['error']],
        degraded=len(failed) > 0,
        total_duration_ms=total_duration,
    )


def create_error_state(
    error_message: str,
    agent_name: Optional[str] = None,
    original_error: Optional[Exception] = None
) -> Dict[str, Any]:
    """
    Create a standardized error state for workflow nodes.

    Args:
        error_message: Human-readable error message
        agent_name: Name of the agent that failed
        original_error: The original exception

    Returns:
        Dict with error information for state update

    Example:
        try:
            result = risky_operation()
        except Exception as e:
            return create_error_state(
                "Failed to process query",
                agent_name="analyzer",
                original_error=e
            )
    """
    error_state = {
        'error': error_message,
        'success': False,
        'answer': f"Error: {error_message}",
        'metadata': {
            'error_type': type(original_error).__name__ if original_error else 'Unknown',
            'error_agent': agent_name,
            'timestamp': datetime.now().isoformat(),
        }
    }

    return error_state


class WorkflowErrorHandler:
    """
    Context manager for handling errors in workflow execution.

    Provides a clean way to wrap workflow steps with error handling
    and automatic state updates on failure.

    Example:
        with WorkflowErrorHandler(state, 'analyzer') as handler:
            result = analyzer.analyze(query)
            handler.set_result(result)

        if handler.failed:
            return state  # State already updated with error
    """

    def __init__(
        self,
        state: Dict[str, Any],
        agent_name: str,
        fallback_message: str = "An error occurred"
    ):
        self.state = state
        self.agent_name = agent_name
        self.fallback_message = fallback_message
        self.result = None
        self.failed = False
        self.error = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.failed = True
            self.error = exc_val

            # Update state with error
            error_info = create_error_state(
                self.fallback_message,
                agent_name=self.agent_name,
                original_error=exc_val
            )

            self.state.update(error_info)

            logger.error(
                f"WorkflowErrorHandler caught error in '{self.agent_name}': "
                f"{exc_type.__name__}: {exc_val}"
            )

            # Suppress the exception (we've handled it)
            return True

        return False

    def set_result(self, result: Any):
        """Store the successful result."""
        self.result = result
