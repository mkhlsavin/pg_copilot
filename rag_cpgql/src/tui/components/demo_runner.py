"""Demo runner component for quick benchmark testing."""

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..utils.themes import Theme, DEFAULT_THEME

logger = logging.getLogger(__name__)

# Ground truth base directory
GROUND_TRUTH_DIR = Path(__file__).parents[3] / "tests" / "benchmark" / "ground_truth"

# Scenario mapping (scenario_id -> folder_name)
SCENARIO_FOLDERS = {
    "01": "scenario_01_onboarding",
    "02": "scenario_02_security_audit",
    "03": "scenario_03_documentation",
    "04": "scenario_04_feature_dev",
    "05": "scenario_05_refactoring",
    "06": "scenario_06_performance",
    "07": "scenario_07_test_coverage",
    "08": "scenario_08_compliance",
    "09": "scenario_09_code_review",
    "10": "scenario_10_cross_repo",
    "11": "scenario_11_architecture",
    "12": "scenario_12_tech_debt",
    "13": "scenario_13_mass_refactoring",
    "14": "scenario_14_security_incident",
    "15": "scenario_15_debugging",
    "16": "scenario_16_entry_points",
}

# Scenario display names
SCENARIO_NAMES = {
    "01": "Onboarding",
    "02": "Security Audit",
    "03": "Documentation",
    "04": "Feature Dev",
    "05": "Refactoring",
    "06": "Performance",
    "07": "Test Coverage",
    "08": "Compliance",
    "09": "Code Review",
    "10": "Cross-Repo",
    "11": "Architecture",
    "12": "Tech Debt",
    "13": "Mass Refactoring",
    "14": "Security Incident",
    "15": "Debugging",
    "16": "Entry Points",
}


@dataclass
class DemoResult:
    """Result of a single demo question execution."""

    scenario_id: str
    scenario_name: str
    question: str
    answer: str
    duration: float
    success: bool
    error: Optional[str] = None


class DemoRunner:
    """
    Demo runner for quick benchmark testing.

    Executes one question per scenario and displays results.
    """

    def __init__(
        self,
        console: Console,
        copilot: Any,
        theme: Theme = DEFAULT_THEME,
        timeout: float = 30.0,
    ):
        """
        Initialize demo runner.

        Args:
            console: Rich Console for output
            copilot: Copilot instance (MultiScenarioCopilot or SimpleCopilotWrapper)
            theme: Color theme
            timeout: Timeout per question in seconds
        """
        self.console = console
        self.copilot = copilot
        self.theme = theme
        self.timeout = timeout

    def load_demo_questions(self, language: str = "en") -> Dict[str, dict]:
        """
        Load one demo question per scenario.

        Args:
            language: Language code (en or ru)

        Returns:
            Dict mapping scenario_id to question data
        """
        questions = {}

        for scenario_id, folder_name in SCENARIO_FOLDERS.items():
            folder_path = GROUND_TRUTH_DIR / folder_name
            questions_file = folder_path / f"questions_{language}.yaml"

            if not questions_file.exists():
                # Try alternative language
                alt_lang = "ru" if language == "en" else "en"
                questions_file = folder_path / f"questions_{alt_lang}.yaml"

            if not questions_file.exists():
                logger.warning(f"No questions file for scenario {scenario_id}")
                continue

            try:
                with open(questions_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                if not data or "questions" not in data:
                    continue

                # Get first easy question, or first question if no easy ones
                question_list = data["questions"]
                selected = None

                # Prefer easy difficulty
                for q in question_list:
                    if q.get("difficulty") == "easy":
                        selected = q
                        break

                # Fallback to first question
                if not selected and question_list:
                    selected = question_list[0]

                if selected:
                    questions[scenario_id] = {
                        "id": selected.get("id", f"Q_{scenario_id}"),
                        "question": selected["question"],
                        "category": selected.get("category", "general"),
                        "difficulty": selected.get("difficulty", "unknown"),
                        "scenario_name": SCENARIO_NAMES.get(scenario_id, f"Scenario {scenario_id}"),
                    }

            except Exception as e:
                logger.error(f"Failed to load questions for scenario {scenario_id}: {e}")

        return questions

    def run_single(self, scenario_id: str, q_data: dict) -> DemoResult:
        """
        Run a single demo question.

        Args:
            scenario_id: Scenario identifier
            q_data: Question data dict

        Returns:
            DemoResult with execution outcome
        """
        question = q_data["question"]
        scenario_name = q_data.get("scenario_name", f"Scenario {scenario_id}")

        start_time = time.time()

        try:
            # Run through copilot
            if hasattr(self.copilot, "run"):
                result = self.copilot.run(question, context={})
            elif hasattr(self.copilot, "invoke"):
                result = self.copilot.invoke({"question": question})
            else:
                raise ValueError("Copilot has no run or invoke method")

            duration = time.time() - start_time

            # Extract answer
            if isinstance(result, dict):
                answer = result.get("answer", str(result))
            else:
                answer = str(result)

            # Truncate answer for display
            if len(answer) > 100:
                answer = answer[:97] + "..."

            return DemoResult(
                scenario_id=scenario_id,
                scenario_name=scenario_name,
                question=question,
                answer=answer,
                duration=duration,
                success=True,
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Demo question failed for scenario {scenario_id}: {e}")

            return DemoResult(
                scenario_id=scenario_id,
                scenario_name=scenario_name,
                question=question,
                answer="",
                duration=duration,
                success=False,
                error=str(e)[:50],
            )

    def run_demo(
        self,
        scenarios: Optional[List[str]] = None,
        language: str = "en",
    ) -> List[DemoResult]:
        """
        Run demo for all or selected scenarios.

        Args:
            scenarios: List of scenario IDs to run (None for all)
            language: Language for questions

        Returns:
            List of DemoResult
        """
        # Load questions
        all_questions = self.load_demo_questions(language)

        # Filter if specific scenarios requested
        if scenarios:
            questions = {
                k: v for k, v in all_questions.items()
                if k in scenarios
            }
        else:
            questions = all_questions

        results = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        ) as progress:
            task = progress.add_task("Running demo...", total=len(questions))

            for scenario_id in sorted(questions.keys()):
                q_data = questions[scenario_id]
                progress.update(
                    task,
                    description=f"[cyan]Scenario {scenario_id}[/cyan]: {q_data['scenario_name']}...",
                )

                result = self.run_single(scenario_id, q_data)
                results.append(result)

                progress.advance(task)

        return results

    def render_results(self, results: List[DemoResult]) -> Panel:
        """
        Render demo results as a Rich table.

        Args:
            results: List of DemoResult

        Returns:
            Rich Panel with results table
        """
        table = Table(
            show_header=True,
            header_style="bold",
            border_style=self.theme.border,
            expand=True,
        )

        table.add_column("Scenario", style="cyan", width=18)
        table.add_column("Question", width=25)
        table.add_column("Status", justify="center", width=8)
        table.add_column("Time", justify="right", width=7)
        table.add_column("Answer", width=30)

        passed = 0
        total_time = 0.0

        for r in results:
            # Truncate question
            q_display = r.question[:22] + "..." if len(r.question) > 25 else r.question

            if r.success:
                status = "[green]OK[/green]"
                answer_display = r.answer[:27] + "..." if len(r.answer) > 30 else r.answer
                passed += 1
            else:
                status = "[red]FAIL[/red]"
                answer_display = f"[red]{r.error or 'Error'}[/red]"

            total_time += r.duration

            table.add_row(
                f"{r.scenario_id} {r.scenario_name}",
                q_display,
                status,
                f"{r.duration:.1f}s",
                answer_display,
            )

        # Summary row
        table.add_section()
        pct = (passed / len(results) * 100) if results else 0
        summary_status = f"[green]{passed}/{len(results)}[/green]" if pct >= 50 else f"[yellow]{passed}/{len(results)}[/yellow]"

        table.add_row(
            "[bold]TOTAL[/bold]",
            "",
            summary_status,
            f"[bold]{total_time:.1f}s[/bold]",
            f"[bold]{pct:.1f}% passed[/bold]",
        )

        return Panel(
            table,
            title="[bold]Demo Results[/bold]",
            subtitle=f"{passed}/{len(results)} passed ({pct:.1f}%)",
            border_style=self.theme.border,
        )
