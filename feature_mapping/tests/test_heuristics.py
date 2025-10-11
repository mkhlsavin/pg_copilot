from __future__ import annotations

import math

import pytest

from feature_mapping.heuristics import (
    CATEGORY_HINT_TOKENS,
    SYNONYM_MAP,
    combine_scores,
    expand_tokens,
    feature_override_for,
    normalise,
    score_path,
    score_text,
    tokenize,
)
from feature_mapping.models import Feature


def test_tokenize_filters_stopwords_and_numbers() -> None:
    text = "New WAL feature for 64-bit recovery"
    tokens = tokenize(text)
    assert "new" not in tokens  # stopword removed
    assert "for" not in tokens
    assert "64" not in tokens  # numeric stripped
    assert "wal" in tokens
    assert "recovery" in tokens


def test_feature_tokens_include_description_limit() -> None:
    feature = Feature(
        name="Logical replication",
        description="Improved WAL sender processes for logical replication slots.",
    )
    tokens = feature.tokens(include_description=True, description_token_limit=3)
    assert "logical" in tokens
    # Description contributes terms, respecting the limit
    assert "improved" not in tokens  # filtered as stopword
    assert "wal" in tokens
    assert tokens.count("logical") == 1


def test_expand_tokens_adds_synonyms_and_category_hints() -> None:
    base_tokens = ["wal"]
    expanded = expand_tokens(base_tokens, category="Replication")
    assert "wal" in expanded
    assert SYNONYM_MAP["wal"].issubset(set(expanded))
    replication_hints = CATEGORY_HINT_TOKENS["replication"]
    assert replication_hints.intersection(expanded)


@pytest.mark.parametrize(
    ("text", "tokens", "expected"),
    [
        ("Parallel worker launch", ["parallel", "worker"], 1.0),
        ("Parallelism executor", ["parallel", "worker"], 0.25),
        ("No match", ["jsonb"], 0.0),
    ],
)
def test_score_text(text: str, tokens: list[str], expected: float) -> None:
    score = score_text(text, tokens)
    assert math.isclose(score, expected, abs_tol=1e-6)


def test_score_path_partial_matches() -> None:
    path = "src/backend/access/brin/brin.c"
    tokens = ["brin", "access"]
    score = score_path(path, tokens)
    # Both tokens should register as direct matches
    assert math.isclose(score, 1.0, abs_tol=1e-6)


def test_combine_scores_handles_empty_inputs() -> None:
    assert combine_scores() == 0.0
    assert combine_scores(0.2, 0.0, 0.4) == pytest.approx(0.3)


def test_feature_override_for_known_feature() -> None:
    override = feature_override_for("psql \\bind")
    assert override.tokens == ("psql", "bind")
    assert override.directory_hints == ("psql",)
    assert override.extra_stopwords == ()


def test_normalise_handles_accents() -> None:
    assert normalise("Café WAL") == "cafe wal"
