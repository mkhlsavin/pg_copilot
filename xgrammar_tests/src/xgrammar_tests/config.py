from __future__ import annotations

from pathlib import Path
from typing import Iterable

def _candidate_paths() -> Iterable[Path]:
    here = Path(__file__).resolve()
    for parent in here.parents:
        for relative in (
            Path("cpgql_gbnf") / "cpgql.gbnf",
            Path("cpgql_clean.gbnf"),
            Path("cpgql.gbnf"),
        ):
            candidate = parent / relative
            if candidate.exists():
                yield candidate
    for relative in (
        Path("cpgql_gbnf") / "cpgql.gbnf",
        Path("cpgql_clean.gbnf"),
        Path("cpgql.gbnf"),
    ):
        cwd_candidate = Path.cwd() / relative
        if cwd_candidate.exists():
            yield cwd_candidate


def default_grammar_path() -> Path:
    for candidate in _candidate_paths():
        return candidate.resolve()
    raise FileNotFoundError(
        "Unable to locate cpgql.gbnf. Set the path explicitly via --grammar or environment."
    )
