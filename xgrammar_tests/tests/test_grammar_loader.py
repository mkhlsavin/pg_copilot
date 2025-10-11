from __future__ import annotations

import pytest

from xgrammar_tests.config import default_grammar_path
from xgrammar_tests.generator import QueryGenerator
from xgrammar_tests.grammar_loader import GrammarLoadError, load_grammar


def test_loads_default_grammar_text():
    spec = load_grammar(default_grammar_path())
    assert spec.source.startswith("root")
    assert spec.path == default_grammar_path().resolve()


def test_query_generator_requires_engine():
    spec = load_grammar(default_grammar_path())
    if spec.engine is not None:
        pytest.skip("xgrammar is installed; engine is available.")
    with pytest.raises(GrammarLoadError):
        spec.ensure_engine()
    with pytest.raises(GrammarLoadError):
        QueryGenerator.from_spec(spec)
