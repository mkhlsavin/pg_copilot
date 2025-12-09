"""
LangGraph Workflow for Automated Patch Review.

Orchestrates the complete patch review pipeline:
1. Parse patch
2. Generate delta CPG
3. Run impact analyzers
4. Generate verdicts
5. Aggregate and output results
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Literal, TypedDict
from datetime import datetime
from enum import Enum

import duckdb

# LangGraph imports (optional - graceful fallback)
try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = "END"

from ..models import (
    PatchContext,
    DeltaCPG,
    ReviewVerdict,
    ReviewSession,
    ReviewStatus,
    ReviewPolicy,
    Recommendation,
    DefinitionOfDone,
    DoDValidationResult,
)
from ..patch_parser import PatchParser
from ..dod import DoDExtractor, DoDGenerator, DoDValidator, DoDConfirmer
from ..delta_cpg_generator import DeltaCPGGenerator
from ..analyzers import (
    PatchCallGraphAnalyzer,
    PatchDataFlowAnalyzer,
    PatchControlFlowAnalyzer,
    PatchDependencyAnalyzer,
    CallGraphAnalysisResult,
    DataFlowAnalysisResult,
    ControlFlowAnalysisResult,
    DependencyAnalysisResult,
)
from ..verdicts import (
    SecurityVerdictGenerator,
    PerformanceVerdictGenerator,
    ErrorVerdictGenerator,
    ArchitectureVerdictGenerator,
)
from ..aggregation import VerdictAggregator, AggregationConfig
from ..formatters import JSONFormatter, MarkdownFormatter, PRCommentFormatter

logger = logging.getLogger(__name__)


class ReviewState(TypedDict, total=False):
    """State for the review workflow."""
    # Input
    patch_source: str  # 'git_diff', 'github_pr', 'gitlab_mr'
    patch_data: Dict[str, Any]
    session_id: str
    policy: Optional[ReviewPolicy]

    # Task description and DoD inputs
    task_description: Optional[str]  # From PR, Jira, or manual input
    pr_body: Optional[str]           # PR/MR description for DoD extraction
    jira_ticket: Optional[str]       # Jira ticket ID
    interactive_mode: bool           # Whether to ask for DoD confirmation

    # Definition of Done
    dod: Optional[DefinitionOfDone]
    dod_confirmed: bool
    dod_validation: Optional[DoDValidationResult]

    # Parsed patch
    patch_context: Optional[PatchContext]
    parse_error: Optional[str]

    # Delta CPG
    delta_cpg: Optional[DeltaCPG]
    delta_error: Optional[str]

    # Analysis results
    call_graph_result: Optional[CallGraphAnalysisResult]
    dataflow_result: Optional[DataFlowAnalysisResult]
    control_flow_result: Optional[ControlFlowAnalysisResult]
    dependency_result: Optional[DependencyAnalysisResult]
    analysis_errors: List[str]

    # Verdicts
    security_verdict: Optional[Any]
    performance_verdict: Optional[Any]
    error_verdict: Optional[Any]
    architecture_verdict: Optional[Any]

    # Final result
    review_verdict: Optional[ReviewVerdict]
    formatted_output: Optional[Dict[str, str]]

    # Metadata
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error: Optional[str]


class ReviewWorkflow:
    """
    LangGraph-based workflow for patch review.

    Provides a structured, observable pipeline for:
    - Parsing patches from multiple sources
    - Generating delta CPG
    - Running impact analysis
    - Generating category verdicts
    - Aggregating final verdict
    - Formatting output
    """

    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        config: Optional[AggregationConfig] = None,
        policy: Optional[ReviewPolicy] = None,
        dod_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the review workflow.

        Args:
            conn: DuckDB connection with CPG loaded
            config: Aggregation configuration
            policy: Review policy
            dod_config: DoD configuration (sources, formats, etc.)
        """
        self.conn = conn
        self.config = config or AggregationConfig()
        self.policy = policy
        self.dod_config = dod_config or {}

        # Initialize components
        self.parser = PatchParser()
        self.delta_generator = DeltaCPGGenerator(conn)
        self.aggregator = VerdictAggregator(conn, config, policy)

        # DoD components
        self.dod_extractor = DoDExtractor(self.dod_config.get('extraction', {}))
        self.dod_generator = DoDGenerator(config=self.dod_config.get('generation', {}))
        self.dod_validator = DoDValidator(self.dod_config.get('validation', {}))
        self.dod_confirmer = DoDConfirmer()

        # Formatters
        self.json_formatter = JSONFormatter()
        self.markdown_formatter = MarkdownFormatter()
        self.pr_formatter = PRCommentFormatter()

        # Build the workflow graph
        self.graph = self._build_graph() if LANGGRAPH_AVAILABLE else None

    def _build_graph(self) -> Optional[StateGraph]:
        """Build the LangGraph workflow."""
        if not LANGGRAPH_AVAILABLE:
            return None

        # Define the graph
        workflow = StateGraph(ReviewState)

        # Add nodes - including DoD stages
        workflow.add_node("parse_patch", self._parse_patch)
        workflow.add_node("extract_dod", self._extract_dod)
        workflow.add_node("generate_dod", self._generate_dod)
        workflow.add_node("confirm_dod", self._confirm_dod)
        workflow.add_node("generate_delta", self._generate_delta)
        workflow.add_node("run_analyzers", self._run_analyzers)
        workflow.add_node("generate_verdicts", self._generate_verdicts)
        workflow.add_node("validate_dod", self._validate_dod)
        workflow.add_node("aggregate_verdict", self._aggregate_verdict)
        workflow.add_node("format_output", self._format_output)
        workflow.add_node("handle_error", self._handle_error)

        # Add edges - new flow with DoD
        workflow.set_entry_point("parse_patch")

        workflow.add_conditional_edges(
            "parse_patch",
            self._check_parse_result,
            {
                "success": "extract_dod",
                "error": "handle_error"
            }
        )

        # After parsing, extract DoD
        workflow.add_conditional_edges(
            "extract_dod",
            self._check_dod_extracted,
            {
                "found": "confirm_dod",
                "not_found": "generate_dod"
            }
        )

        # If DoD not found, generate it then confirm
        workflow.add_edge("generate_dod", "confirm_dod")

        # Confirm DoD (interactive or passthrough)
        workflow.add_conditional_edges(
            "confirm_dod",
            self._check_dod_skipped,
            {
                "continue": "generate_delta",
                "skipped": "generate_delta",  # Still continue but without DoD
            }
        )

        workflow.add_conditional_edges(
            "generate_delta",
            self._check_delta_result,
            {
                "success": "run_analyzers",
                "error": "handle_error"
            }
        )

        workflow.add_edge("run_analyzers", "generate_verdicts")
        workflow.add_edge("generate_verdicts", "aggregate_verdict")
        workflow.add_edge("aggregate_verdict", "validate_dod")
        workflow.add_edge("validate_dod", "format_output")
        workflow.add_edge("format_output", END)
        workflow.add_edge("handle_error", END)

        return workflow.compile()

    def run(
        self,
        patch_source: str,
        patch_data: Dict[str, Any],
        session_id: Optional[str] = None,
        policy: Optional[ReviewPolicy] = None,
        task_description: Optional[str] = None,
        pr_body: Optional[str] = None,
        jira_ticket: Optional[str] = None,
        interactive_mode: bool = False,
    ) -> ReviewVerdict:
        """
        Run the complete review workflow.

        Args:
            patch_source: Source type ('git_diff', 'github_pr', 'gitlab_mr')
            patch_data: Patch data dictionary
            session_id: Optional session ID
            policy: Optional review policy
            task_description: Task description for DoD generation
            pr_body: PR body text for DoD extraction
            jira_ticket: Jira ticket ID for DoD extraction
            interactive_mode: Whether to ask for DoD confirmation

        Returns:
            Complete review verdict
        """
        session_id = session_id or str(uuid.uuid4())

        # Extract PR body from patch_data if not provided
        if pr_body is None and patch_source == 'github_pr':
            pr_body = patch_data.get('body', '')
        elif pr_body is None and patch_source == 'gitlab_mr':
            pr_body = patch_data.get('description', '')

        initial_state: ReviewState = {
            'patch_source': patch_source,
            'patch_data': patch_data,
            'session_id': session_id,
            'policy': policy or self.policy,
            'task_description': task_description,
            'pr_body': pr_body,
            'jira_ticket': jira_ticket,
            'interactive_mode': interactive_mode,
            'dod_confirmed': False,
            'status': 'started',
            'started_at': datetime.now(),
            'analysis_errors': []
        }

        if self.graph:
            # Use LangGraph
            final_state = self.graph.invoke(initial_state)
        else:
            # Fallback to manual execution
            final_state = self._run_manual(initial_state)

        if final_state.get('error'):
            raise RuntimeError(f"Review failed: {final_state['error']}")

        return final_state['review_verdict']

    def _run_manual(self, state: ReviewState) -> ReviewState:
        """Run workflow manually without LangGraph."""
        try:
            # Parse patch
            state = self._parse_patch(state)
            if state.get('parse_error'):
                return self._handle_error(state)

            # Extract DoD
            state = self._extract_dod(state)

            # Generate DoD if not found
            if not state.get('dod'):
                state = self._generate_dod(state)

            # Confirm DoD (interactive or passthrough)
            state = self._confirm_dod(state)
            if state.get('dod_skipped'):
                logger.info("DoD skipped, continuing without DoD validation")

            # Generate delta
            state = self._generate_delta(state)
            if state.get('delta_error'):
                return self._handle_error(state)

            # Run analyzers
            state = self._run_analyzers(state)

            # Generate verdicts
            state = self._generate_verdicts(state)

            # Aggregate
            state = self._aggregate_verdict(state)

            # Validate DoD against findings (after aggregate to use final verdict)
            state = self._validate_dod(state)

            # Format output
            state = self._format_output(state)

            return state

        except Exception as e:
            state['error'] = str(e)
            return self._handle_error(state)

    def _parse_patch(self, state: ReviewState) -> ReviewState:
        """Parse the patch from input."""
        logger.info(f"Parsing patch from {state['patch_source']}")

        try:
            patch_source = state['patch_source']
            patch_data = state['patch_data']

            if patch_source == 'git_diff':
                patch = self.parser.parse_git_diff(patch_data.get('diff', ''))
            elif patch_source == 'github_pr':
                patch = self.parser.parse_github_pr(patch_data)
            elif patch_source == 'gitlab_mr':
                patch = self.parser.parse_gitlab_mr(patch_data)
            else:
                patch = self.parser.parse(patch_data)

            state['patch_context'] = patch
            state['status'] = 'parsed'

        except Exception as e:
            logger.error(f"Parse error: {e}")
            state['parse_error'] = str(e)

        return state

    def _generate_delta(self, state: ReviewState) -> ReviewState:
        """Generate delta CPG from patch."""
        logger.info("Generating delta CPG")

        try:
            patch = state['patch_context']
            session_id = state['session_id']

            # Create review session
            session = ReviewSession(
                session_id=session_id,
                patch_id=patch.patch_id,
                base_commit=patch.base_commit,
                head_commit=patch.head_commit,
                status=ReviewStatus.ANALYZING,
                created_at=datetime.now()
            )

            # Generate delta
            delta = self.delta_generator.generate_delta(patch, session)

            state['delta_cpg'] = delta
            state['status'] = 'delta_generated'

        except Exception as e:
            logger.error(f"Delta generation error: {e}")
            state['delta_error'] = str(e)

        return state

    def _run_analyzers(self, state: ReviewState) -> ReviewState:
        """Run all impact analyzers."""
        logger.info("Running impact analyzers")

        patch = state['patch_context']
        delta = state['delta_cpg']
        errors = []

        # Call graph analysis
        try:
            analyzer = PatchCallGraphAnalyzer(self.conn)
            state['call_graph_result'] = analyzer.analyze_call_graph_impact(patch, delta)
        except Exception as e:
            logger.warning(f"Call graph analysis failed: {e}")
            errors.append(f"call_graph: {e}")

        # Dataflow analysis
        try:
            analyzer = PatchDataFlowAnalyzer(self.conn)
            state['dataflow_result'] = analyzer.analyze_dataflow_changes(patch, delta)
        except Exception as e:
            logger.warning(f"Dataflow analysis failed: {e}")
            errors.append(f"dataflow: {e}")

        # Control flow analysis
        try:
            analyzer = PatchControlFlowAnalyzer(self.conn)
            state['control_flow_result'] = analyzer.analyze_control_flow_changes(patch, delta)
        except Exception as e:
            logger.warning(f"Control flow analysis failed: {e}")
            errors.append(f"control_flow: {e}")

        # Dependency analysis
        try:
            analyzer = PatchDependencyAnalyzer(self.conn)
            state['dependency_result'] = analyzer.analyze_dependency_changes(patch, delta)
        except Exception as e:
            logger.warning(f"Dependency analysis failed: {e}")
            errors.append(f"dependency: {e}")

        state['analysis_errors'] = errors
        state['status'] = 'analyzed'

        return state

    def _generate_verdicts(self, state: ReviewState) -> ReviewState:
        """Generate category-specific verdicts."""
        logger.info("Generating verdicts")

        patch = state['patch_context']
        delta = state['delta_cpg']

        # Security verdict
        try:
            generator = SecurityVerdictGenerator(self.conn)
            state['security_verdict'] = generator.generate_verdict(
                patch, delta, state.get('dataflow_result')
            )
        except Exception as e:
            logger.error(f"Security verdict failed: {e}")

        # Performance verdict
        try:
            generator = PerformanceVerdictGenerator(self.conn)
            state['performance_verdict'] = generator.generate_verdict(
                patch, delta,
                state.get('control_flow_result'),
                state.get('call_graph_result')
            )
        except Exception as e:
            logger.error(f"Performance verdict failed: {e}")

        # Error verdict
        try:
            generator = ErrorVerdictGenerator(self.conn)
            state['error_verdict'] = generator.generate_verdict(
                patch, delta, state.get('control_flow_result')
            )
        except Exception as e:
            logger.error(f"Error verdict failed: {e}")

        # Architecture verdict
        try:
            generator = ArchitectureVerdictGenerator(self.conn)
            state['architecture_verdict'] = generator.generate_verdict(
                patch, delta,
                state.get('call_graph_result'),
                state.get('dependency_result')
            )
        except Exception as e:
            logger.error(f"Architecture verdict failed: {e}")

        state['status'] = 'verdicts_generated'
        return state

    def _aggregate_verdict(self, state: ReviewState) -> ReviewState:
        """Aggregate all verdicts into final review."""
        logger.info("Aggregating final verdict")

        patch = state['patch_context']
        delta = state['delta_cpg']

        # Use the aggregator which will regenerate verdicts
        # In production, we'd pass pre-computed verdicts
        verdict = self.aggregator.generate_review(patch, delta)

        state['review_verdict'] = verdict
        state['status'] = 'aggregated'
        state['completed_at'] = datetime.now()

        return state

    def _format_output(self, state: ReviewState) -> ReviewState:
        """Format the verdict for output."""
        logger.info("Formatting output")

        verdict = state['review_verdict']

        state['formatted_output'] = {
            'json': self.json_formatter.format_full(verdict),
            'json_summary': self.json_formatter.format_summary(verdict),
            'markdown': self.markdown_formatter.format_full_report(verdict),
            'markdown_summary': self.markdown_formatter.format_summary(verdict)
        }

        state['status'] = 'completed'
        return state

    def _handle_error(self, state: ReviewState) -> ReviewState:
        """Handle workflow errors."""
        error = state.get('parse_error') or state.get('delta_error') or state.get('error')
        logger.error(f"Workflow error: {error}")

        state['error'] = error
        state['status'] = 'failed'
        state['completed_at'] = datetime.now()

        return state

    def _check_parse_result(self, state: ReviewState) -> str:
        """Check if parsing succeeded."""
        return "error" if state.get('parse_error') else "success"

    def _check_delta_result(self, state: ReviewState) -> str:
        """Check if delta generation succeeded."""
        return "error" if state.get('delta_error') else "success"

    def _check_dod_extracted(self, state: ReviewState) -> str:
        """Check if DoD was successfully extracted."""
        return "found" if state.get('dod') else "not_found"

    def _check_dod_skipped(self, state: ReviewState) -> str:
        """Check if DoD was skipped by user."""
        return "skipped" if state.get('dod_skipped') else "continue"

    def _confirm_dod(self, state: ReviewState) -> ReviewState:
        """Interactively confirm DoD with user (if interactive mode enabled)."""
        if not state.get('interactive_mode'):
            # Non-interactive mode: mark as confirmed and continue
            if state.get('dod'):
                dod = state['dod']
                state['dod'] = type(dod)(
                    items=dod.items,
                    source=dod.source,
                    format=dod.format,
                    confirmed=True,
                    generated_from=dod.generated_from,
                    raw_text=dod.raw_text,
                )
                state['dod_confirmed'] = True
            state['status'] = 'dod_confirmed'
            return state

        # Interactive mode: prompt user for confirmation
        logger.info("Requesting DoD confirmation from user")

        try:
            dod = state.get('dod')
            source_desc = ""
            if dod:
                source_desc = f"from {dod.source.value}"
                if dod.generated_from:
                    source_desc += f" (generated from {dod.generated_from})"

            confirmed_dod, should_skip = self.dod_confirmer.confirm(
                dod=dod,
                source_description=source_desc,
            )

            if should_skip:
                state['dod'] = None
                state['dod_skipped'] = True
                state['dod_confirmed'] = False
                logger.info("DoD validation skipped by user")
            else:
                state['dod'] = confirmed_dod
                state['dod_confirmed'] = True
                state['dod_skipped'] = False
                logger.info(f"DoD confirmed: {len(confirmed_dod.items) if confirmed_dod else 0} items")

        except KeyboardInterrupt:
            # User cancelled the review
            state['error'] = "Review cancelled by user"
            state['status'] = 'cancelled'
            raise

        except Exception as e:
            logger.warning(f"DoD confirmation failed: {e}")
            # Continue without confirmation
            state['dod_confirmed'] = False

        state['status'] = 'dod_confirmed'
        return state

    def _extract_dod(self, state: ReviewState) -> ReviewState:
        """Extract Definition of Done from available sources."""
        logger.info("Extracting Definition of Done")

        patch = state.get('patch_context')
        if not patch:
            return state

        try:
            dod = self.dod_extractor.extract(
                patch=patch,
                pr_body=state.get('pr_body'),
                jira_ticket=state.get('jira_ticket'),
            )

            if dod:
                state['dod'] = dod
                logger.info(f"DoD extracted from {dod.source.value}: {len(dod.items)} items")
            else:
                logger.info("No DoD found in any source")

        except Exception as e:
            logger.warning(f"DoD extraction failed: {e}")

        state['status'] = 'dod_extracted'
        return state

    def _generate_dod(self, state: ReviewState) -> ReviewState:
        """Generate DoD using LLM if not found."""
        logger.info("Generating Definition of Done")

        # Check if auto-generate is enabled
        if not self.dod_config.get('auto_generate', True):
            logger.info("DoD auto-generation disabled")
            return state

        patch = state.get('patch_context')
        task_description = state.get('task_description')

        # If no task description, try to extract from PR body
        if not task_description:
            task_description = state.get('pr_body', '')

        # If still no description, use patch summary
        if not task_description and patch:
            task_description = f"Changes to {len(patch.files)} files: {', '.join(f.path for f in patch.files[:5])}"

        try:
            dod = self.dod_generator.generate(
                task_description=task_description,
                patch=patch,
            )

            state['dod'] = dod
            logger.info(f"DoD generated: {len(dod.items)} items")

        except Exception as e:
            logger.warning(f"DoD generation failed: {e}")

        state['status'] = 'dod_generated'
        return state

    def _validate_dod(self, state: ReviewState) -> ReviewState:
        """Validate DoD against review findings."""
        logger.info("Validating Definition of Done")

        dod = state.get('dod')
        verdict = state.get('review_verdict')

        if not dod or not verdict:
            return state

        try:
            validation_result = self.dod_validator.validate(dod, verdict)

            state['dod_validation'] = validation_result
            state['dod'] = validation_result.dod  # Update with validated DoD

            # Update verdict with DoD validation
            if verdict:
                verdict.dod_validation = validation_result
                verdict.dod_compliance_score = validation_result.compliance_score

            logger.info(
                f"DoD validation: {validation_result.satisfied_count}/{validation_result.total_items} "
                f"items satisfied ({validation_result.compliance_score:.1f}%)"
            )

        except Exception as e:
            logger.warning(f"DoD validation failed: {e}")

        state['status'] = 'dod_validated'
        return state

    def run_async(
        self,
        patch_source: str,
        patch_data: Dict[str, Any],
        callback_url: Optional[str] = None
    ) -> str:
        """
        Start async review (returns session ID immediately).

        Args:
            patch_source: Source type
            patch_data: Patch data
            callback_url: URL to call when complete

        Returns:
            Session ID for tracking
        """
        session_id = str(uuid.uuid4())

        # In production, this would queue the review
        # For now, we run synchronously
        try:
            self.run(patch_source, patch_data, session_id)
        except Exception as e:
            logger.error(f"Async review failed: {e}")

        return session_id

    def get_review_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get status of an async review.

        Args:
            session_id: Session ID

        Returns:
            Status dictionary
        """
        try:
            result = self.conn.execute("""
                SELECT status, created_at, completed_at, verdict
                FROM review_sessions
                WHERE session_id = ?
            """, [session_id]).fetchone()

            if result:
                return {
                    'session_id': session_id,
                    'status': result[0],
                    'created_at': result[1],
                    'completed_at': result[2],
                    'has_verdict': result[3] is not None
                }
        except Exception:
            pass

        return {'session_id': session_id, 'status': 'not_found'}
