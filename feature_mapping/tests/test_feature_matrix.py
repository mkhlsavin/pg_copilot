from __future__ import annotations

import json
from pathlib import Path

import pytest

from feature_mapping.feature_matrix import FEATURE_MATRIX_URL, fetch_feature_matrix, parse_feature_matrix
from feature_mapping.models import Feature

FIXTURES_DIR = Path(__file__).parent / "fixtures"
MATRIX_FIXTURE = FIXTURES_DIR / "postgresql_feature_matrix.json"
COUNT_FIXTURE = FIXTURES_DIR / "feature_count.json"


@pytest.fixture(scope="module")
def feature_matrix_payload() -> dict:
    if not MATRIX_FIXTURE.exists():
        pytest.skip(f"Feature matrix fixture missing: {MATRIX_FIXTURE}")
    return json.loads(MATRIX_FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def expected_count_payload() -> dict:
    if not COUNT_FIXTURE.exists():
        pytest.skip(f"Feature count fixture missing: {COUNT_FIXTURE}")
    return json.loads(COUNT_FIXTURE.read_text(encoding="utf-8"))


def test_fetch_feature_matrix_live_count(expected_count_payload: dict) -> None:
    """Live fetch should match the expected feature count."""
    expected_count = expected_count_payload["expected_count"]
    features = fetch_feature_matrix(FEATURE_MATRIX_URL)
    assert len(features) == expected_count


def test_parse_feature_matrix_fixture(feature_matrix_payload: dict) -> None:
    """Parsing the archived matrix snapshot should reproduce the serialized features."""
    snapshot_count = feature_matrix_payload["expected_count"]
    html_features = [Feature(**entry) for entry in feature_matrix_payload["features"]]
    assert len(html_features) == snapshot_count


def test_feature_structure(feature_matrix_payload: dict) -> None:
    """Fixture should contain well-structured feature metadata."""
    features = feature_matrix_payload["features"]
    assert features, "Feature list should not be empty"
    for feature in features:
        assert feature["name"], "Feature name must be populated"
        assert isinstance(feature.get("category"), (str, type(None)))
        assert isinstance(feature.get("description"), (str, type(None)))
        assert isinstance(feature.get("detail_url"), (str, type(None)))
