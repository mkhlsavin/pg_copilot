from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence


@dataclass(slots=True)
class Feature:
    """Structured representation of a PostgreSQL feature matrix entry."""

    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    detail_url: Optional[str] = None

    def tokens(
        self,
        *,
        extra_stopwords: Optional[Iterable[str]] = None,
        include_description: bool = False,
        description_token_limit: int = 8,
    ) -> List[str]:
        """Tokenize the feature name for downstream heuristics."""
        from .heuristics import tokenize

        tokens = tokenize(
            self.name,
            extra_stopwords=extra_stopwords,
        )
        if include_description and self.description:
            desc_tokens = tokenize(
                self.description,
                extra_stopwords=extra_stopwords,
            )
            appended = 0
            for token in desc_tokens:
                if token not in tokens:
                    tokens.append(token)
                    appended += 1
                    if description_token_limit and appended >= description_token_limit:
                        break
        return tokens

    def to_dict(self) -> dict[str, Optional[str]]:
        """Serialise the feature for JSON/diagnostic outputs."""
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "detail_url": self.detail_url,
        }


@dataclass(slots=True)
class CandidateNode:
    """Single CPG node that might implement a feature."""

    node_id: int
    kind: str
    name: str
    score: float
    filename: Optional[str] = None
    line_number: Optional[int] = None
    additional_terms: Sequence[str] = field(default_factory=tuple)

    def as_tag_assignment(self, feature_name: str) -> dict:
        """Return a JSON-serialisable payload for tagging scripts."""
        return {
            "id": self.node_id,
            "kind": self.kind,
            "feature": feature_name,
            "name": self.name,
            "filename": self.filename,
            "line": self.line_number,
        }


@dataclass(slots=True)
class MappingResult:
    """Representation of the final mapping for a feature."""

    feature: Feature
    nodes: Sequence[CandidateNode]

    def best_nodes(self, limit: int | None = None) -> Sequence[CandidateNode]:
        if limit is None:
            return self.nodes
        return tuple(sorted(self.nodes, key=lambda c: c.score, reverse=True)[:limit])


@dataclass(slots=True)
class FeatureCoverage:
    """Coverage information for a feature's tags within the CPG."""

    feature: Feature
    tagged_nodes: int

    @property
    def is_tagged(self) -> bool:
        return self.tagged_nodes > 0
