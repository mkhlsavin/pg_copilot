from __future__ import annotations

import json
from pathlib import Path
from typing import List, Sequence

from feature_mapping.models import CandidateNode, Feature
from feature_mapping.pipeline import FeatureMappingConfig, FeatureMappingPipeline


class StubJoernClient:
    def __init__(self) -> None:
        self.find_calls: list[tuple[str, Sequence[str]]] = []
        self.filter_calls: list[tuple[str, List[int]]] = []
        self.tag_calls: list[tuple[str, List[int]]] = []

    def find_candidates(
        self,
        feature_name: str,
        tokens: Sequence[str],
        *,
        directory_hints: Sequence[str] | None = None,
        max_per_kind: int = 0,
        max_total_results: int = 0,
        include_calls: bool = False,
        include_namespaces: bool = False,
    ) -> List[CandidateNode]:
        self.find_calls.append((feature_name, list(tokens)))
        if feature_name == "Feature Alpha":
            return [
                CandidateNode(
                    node_id=101,
                    kind="file",
                    name="alpha.c",
                    filename="src/alpha.c",
                    line_number=None,
                    score=0.9,
                ),
                CandidateNode(
                    node_id=102,
                    kind="file",
                    name="alpha_extra.c",
                    filename="src/alpha_extra.c",
                    line_number=None,
                    score=0.6,
                ),
            ]
        if feature_name == "Feature Beta":
            return [
                CandidateNode(
                    node_id=201,
                    kind="method",
                    name="beta_method",
                    filename="src/beta.c",
                    line_number=42,
                    score=0.8,
                )
            ]
        return []

    def filter_untagged_nodes(self, feature_name: str, node_ids: Sequence[int]) -> List[int]:
        ids = [int(node_id) for node_id in node_ids]
        self.filter_calls.append((feature_name, ids))
        if feature_name == "Feature Alpha" and ids:
            return ids[:1]  # simulate second node already tagged
        return ids

    def tag_feature(self, feature_name: str, node_ids: Sequence[int], *, batch_size: int = 50) -> None:
        self.tag_calls.append((feature_name, list(node_ids)))


def test_pipeline_creates_summaries_and_tags(tmp_path: Path) -> None:
    stub = StubJoernClient()
    config = FeatureMappingConfig(
        max_nodes_per_feature=3,
        max_candidates_per_kind=5,
        summary_output_dir=tmp_path / "summaries",
        include_calls=True,
        include_namespaces=False,
    )
    pipeline = FeatureMappingPipeline(joern=stub, config=config)
    features = [
        Feature(name="Feature Alpha", category="Performance"),
        Feature(name="Feature Beta", category="Replication"),
    ]

    results = pipeline.run(features)

    assert len(results) == 2
    assert {result.feature.name for result in results} == {"Feature Alpha", "Feature Beta"}
    # Ensure Joern lookups were performed
    assert [name for name, _ in stub.find_calls] == ["Feature Alpha", "Feature Beta"]

    # Validate summaries exist with expected content
    summary_dir = config.summary_output_dir
    assert summary_dir is not None
    summary_files = sorted(summary_dir.glob("*.json"))
    assert {path.stem for path in summary_files} == {"feature-alpha", "feature-beta"}
    alpha_summary = json.loads((summary_dir / "feature-alpha.json").read_text(encoding="utf-8"))
    assert alpha_summary["feature"]["name"] == "Feature Alpha"
    assert len(alpha_summary["candidates"]) == 2

    # Tagging should skip already-tagged nodes for Feature Alpha and tag Feature Beta fully
    assert stub.tag_calls == [
        ("Feature Alpha", [101]),
        ("Feature Beta", [201]),
    ]


def test_pipeline_resumes_from_feature(tmp_path: Path) -> None:
    stub = StubJoernClient()
    config = FeatureMappingConfig(
        max_nodes_per_feature=2,
        summary_output_dir=tmp_path / "summaries",
        resume_from="Feature Beta",
    )
    pipeline = FeatureMappingPipeline(joern=stub, config=config)
    features = [
        Feature(name="Feature Alpha", category="Performance"),
        Feature(name="Feature Beta", category="Replication"),
    ]

    results = pipeline.run(features)

    assert len(results) == 1
    assert results[0].feature.name == "Feature Beta"
    # Only beta should have been processed
    assert len(stub.find_calls) == 1
    assert stub.find_calls[0][0] == "Feature Beta"
    summary_dir = config.summary_output_dir
    assert summary_dir is not None
    assert (summary_dir / "feature-beta.json").exists()
    assert not (summary_dir / "feature-alpha.json").exists()
