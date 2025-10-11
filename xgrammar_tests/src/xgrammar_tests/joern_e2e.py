from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence

from .generator import GenerationError, QueryGenerator
from .grammar_loader import GrammarLoadError, GrammarSpec, load_grammar
from .sampler import SamplerConfig, build_sampler
from .validator import validate_query

try:
    from cpgqls_client import CPGQLSClient  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    CPGQLSClient = None  # type: ignore[assignment]


class JoernE2EError(RuntimeError):
    """Raised when Joern end-to-end execution fails."""


@dataclass(slots=True)
class JoernConnectionConfig:
    host: str = "localhost"
    port: int = 8080
    project: str = "pg17_full.cpg"
    load_cpg: bool = False


@dataclass(slots=True)
class GeneratedQuery:
    query: str
    validation_issues: Optional[List[str]]
    joern_response: Optional[dict[str, Any]]


class JoernE2ERunner:
    """Coordinate sampler-backed generation with Joern execution."""

    def __init__(self, connection: Optional[JoernConnectionConfig] = None) -> None:
        self._connection = connection or JoernConnectionConfig()
        self._client: Optional[CPGQLSClient] = None

    def connect(self) -> None:
        if CPGQLSClient is None:
            raise JoernE2EError(
                "cpgqls-client is not installed. Install it with `pip install cpgqls-client`."
            )
        endpoint = f"{self._connection.host}:{self._connection.port}"
        self._client = CPGQLSClient(endpoint)
        if self._connection.load_cpg:
            self._ensure_project_loaded()

    def close(self) -> None:
        self._client = None

    def _ensure_project_loaded(self) -> None:
        assert self._client is not None
        check = self._client.execute("cpg.method.limit(1)")
        stdout = check.get("stdout", "")
        if "Not found: cpg" not in stdout:
            return
        project_name = self._connection.project
        cpg_bin = Path.home() / "joern" / "workspace" / project_name / "cpg.bin"
        if not cpg_bin.exists():
            raise JoernE2EError(f"CPG binary not found at {cpg_bin}")
        load_cmd = (
            f'val cpg = io.shiftleft.codepropertygraph.cpgloading.CpgLoader.load("{cpg_bin}")'
        )
        self._client.execute(load_cmd)
        self._client.execute("import io.shiftleft.semanticcpg.language._")

    def generate_and_execute(
        self,
        *,
        grammar_path: Optional[Path] = None,
        sampler_config: Optional[SamplerConfig] = None,
        count: int = 1,
        mode: str = "random",
        seed: Optional[int] = None,
        max_steps: int = 128,
        validate: bool = True,
    ) -> List[GeneratedQuery]:
        sampler_config = sampler_config or SamplerConfig()
        try:
            spec: GrammarSpec = load_grammar(grammar_path, start_symbol="root")
        except GrammarLoadError as exc:
            raise JoernE2EError(str(exc)) from exc

        sampler = None
        if sampler_config.enabled:
            try:
                sampler = build_sampler(spec, sampler_config)
            except GrammarLoadError as exc:
                raise JoernE2EError(str(exc)) from exc

        generator = (
            QueryGenerator.from_sampler(spec, sampler)
            if sampler is not None
            else QueryGenerator.from_spec(spec)
        )
        try:
            queries = generator.generate(count=count, mode=mode, seed=seed, max_steps=max_steps)
        except GenerationError as exc:
            raise JoernE2EError(str(exc)) from exc

        if self._client is None and sampler_config.enabled:
            # Allow generation-only usage without active server.
            try:
                self.connect()
            except JoernE2EError:
                pass

        results: List[GeneratedQuery] = []
        for query in queries:
            validation_issues: Optional[List[str]] = None
            if validate:
                validation = validate_query(query)
                if not validation.valid:
                    validation_issues = validation.issues

            joern_response: Optional[dict[str, Any]] = None
            if self._client is not None:
                try:
                    joern_response = self._client.execute(query)
                except Exception as exc:  # pragma: no cover - network failures
                    joern_response = {
                        "success": False,
                        "error": str(exc),
                    }

            results.append(
                GeneratedQuery(
                    query=query,
                    validation_issues=validation_issues,
                    joern_response=joern_response,
                )
            )
        return results

    def __enter__(self) -> "JoernE2ERunner":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb) -> None:
        self.close()
