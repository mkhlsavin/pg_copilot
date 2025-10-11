from __future__ import annotations

import inspect
import random
from dataclasses import dataclass
from typing import Any, Iterable, List, Literal, Optional

from .grammar_loader import GrammarSpec, GrammarLoadError


class GenerationError(RuntimeError):
    """Raised when query generation fails."""


SamplerMode = Literal["random", "deterministic"]


@dataclass(slots=True)
class QueryGenerator:
    """Facade around the XGrammar sampler."""

    grammar: GrammarSpec
    sampler: Any

    @classmethod
    def from_spec(cls, spec: GrammarSpec) -> "QueryGenerator":
        engine = spec.ensure_engine()
        try:
            sampler = _create_sampler(engine)
        except GrammarLoadError as exc:
            raise GenerationError(str(exc)) from exc
        return cls(grammar=spec, sampler=sampler)

    @classmethod
    def from_sampler(cls, spec: GrammarSpec, sampler: Any) -> "QueryGenerator":
        return cls(grammar=spec, sampler=sampler)

    def generate(
        self,
        *,
        count: int = 1,
        mode: SamplerMode = "random",
        seed: Optional[int] = None,
        max_steps: int = 128,
    ) -> List[str]:
        if count <= 0:
            return []

        results: List[str] = []
        base_rng = random.Random(seed)

        for idx in range(count):
            effective_seed = None if seed is None else base_rng.randint(0, 2**31 - 1)
            try:
                sample = _sample_once(
                    sampler=self.sampler,
                    random_mode=(mode == "random"),
                    seed=effective_seed,
                    max_steps=max_steps,
                )
                results.append(str(sample))
            except Exception as exc:  # pragma: no cover - depends on external library
                raise GenerationError(f"Failed to generate query #{idx + 1}: {exc}") from exc
        return results


def _create_sampler(engine: Any) -> Any:
    """Return a callable sampler from the compiled grammar engine."""
    # Prefer dedicated sampler factory if present.
    if hasattr(engine, "sampler"):
        sampler = engine.sampler()
        return sampler

    if hasattr(engine, "create_sampler"):
        return engine.create_sampler()

    raise GrammarLoadError(
        "The compiled grammar engine does not expose a recognised sampler API "
        "(expected `sampler()` or `create_sampler()`)."
    )


def _sample_once(
    *,
    sampler: Any,
    random_mode: bool,
    seed: Optional[int],
    max_steps: int,
) -> str:
    """Invoke the sampler using a broad compatibility strategy."""
    kwargs: dict[str, Any] = {}
    if seed is not None:
        kwargs["seed"] = seed
    if max_steps:
        kwargs["max_steps"] = max_steps
        kwargs["max_length"] = max_steps  # support alternate parameter names
    kwargs["random"] = random_mode
    kwargs["stochastic"] = random_mode

    if hasattr(sampler, "sample"):
        return _invoke_with_filtered_kwargs(sampler.sample, kwargs)
    if callable(sampler):
        return _invoke_with_filtered_kwargs(sampler, kwargs)

    raise GenerationError("Sampler object is neither callable nor exposes a `sample` method.")


def _invoke_with_filtered_kwargs(func: Any, kwargs: dict[str, Any]) -> Any:
    """Call a sampler while discarding unsupported keyword arguments."""
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):  # pragma: no cover - depends on external callable
        try:
            return func(**kwargs)
        except TypeError:
            return func()

    accepted: dict[str, Any] = {}
    for name, value in kwargs.items():
        if name in sig.parameters:
            accepted[name] = value
    try:
        return func(**accepted)
    except TypeError as exc:  # pragma: no cover - defensive
        if accepted and accepted != kwargs:
            raise GenerationError(f"Sampler rejected keyword arguments after filtering: {exc}") from exc
        return func()
