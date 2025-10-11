from __future__ import annotations

import re
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .config import default_grammar_path

try:
    import xgrammar  # type: ignore
except Exception:  # pragma: no cover
    xgrammar = None  # type: ignore[assignment]

COMMENT_PATTERN = re.compile(r"\(\\\*.*?\\\*\)", re.DOTALL)
ESCAPE_PATTERN = re.compile(r"\\([\[\]\(\)\*\+\?\|\'\"_=<>!])")


class GrammarLoadError(RuntimeError):
    """Raised when the grammar cannot be parsed or compiled."""


@dataclass(slots=True)
class GrammarSpec:
    path: Path
    source: str
    start_symbol: str = "root"
    engine: Optional[Any] = None

    def ensure_engine(self) -> Any:
        if self.engine is None:
            raise GrammarLoadError(
                "XGrammar engine is unavailable. Install the `xgrammar` package "
                "or ensure the grammar compiles successfully."
            )
        return self.engine


def _sanitize_gbnf(source: str) -> str:
    cleaned = COMMENT_PATTERN.sub("", source)
    cleaned = ESCAPE_PATTERN.sub(r"\1", cleaned)
    cleaned = cleaned.replace("'", '"')
    cleaned_lines = [line for line in cleaned.splitlines() if not line.strip().startswith(";")]
    if not any(line.strip().startswith("traversalArg") for line in cleaned_lines):
        cleaned_lines.append("traversalArg   ::= traversalExpr")
    return "\n".join(cleaned_lines)


def load_grammar(path: Optional[Path | str] = None, *, start_symbol: str = "root") -> GrammarSpec:
    try:
        resolved_path = Path(path) if path is not None else default_grammar_path()
    except FileNotFoundError as exc:
        raise GrammarLoadError(str(exc)) from exc

    resolved_path = resolved_path.resolve()
    if not resolved_path.exists():
        raise GrammarLoadError(f"Grammar file not found: {resolved_path}")

    raw_source = resolved_path.read_text(encoding="utf-8")
    source = _sanitize_gbnf(raw_source)
    spec = GrammarSpec(path=resolved_path, source=source, start_symbol=start_symbol)

    if xgrammar is None:
        warnings.warn(
            "The `xgrammar` package is not installed; query generation is disabled.",
            ImportWarning,
            stacklevel=2,
        )
        return spec

    try:
        spec.engine = _compile_with_xgrammar(spec)
    except Exception as exc:  # pragma: no cover
        warnings.warn(
            f"Failed to compile grammar via XGrammar ({exc}). Continuing without engine.",
            RuntimeWarning,
            stacklevel=2,
        )
        spec.engine = None

    return spec


def _compile_with_xgrammar(spec: GrammarSpec) -> Any:
    if hasattr(xgrammar, "grammar") and hasattr(xgrammar.grammar, "Grammar"):
        cls = xgrammar.grammar.Grammar
        if hasattr(cls, "from_ebnf"):
            return cls.from_ebnf(spec.source, root_rule_name=spec.start_symbol)

    if hasattr(xgrammar, "Grammar") and hasattr(xgrammar.Grammar, "from_ebnf"):
        return xgrammar.Grammar.from_ebnf(spec.source, root_rule_name=spec.start_symbol)

    raise GrammarLoadError(
        "Unsupported XGrammar API version. Expected Grammar.from_ebnf capability."
    )
