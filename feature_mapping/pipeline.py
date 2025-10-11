from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from .feature_matrix import FEATURE_MATRIX_URL, fetch_feature_matrix
from .heuristics import expand_tokens, feature_override_for, normalise, tokenize
from .joern_client import JoernClient
from .models import CandidateNode, Feature, MappingResult

logger = logging.getLogger(__name__)


TOKEN_DIRECTORY_HINTS = {
    "json": {"json", "jsonb"},
    "wal": {"wal", "xlog"},
    "scram": {"auth", "libpq"},
    "logical": {"replication", "logical"},
    "btree": {"btree"},
    "brin": {"brin"},
    "gin": {"gin"},
    "gist": {"gist"},
    "tsvector": {"tsearch"},
    "partition": {"partition"},
    "merge": {"commands"},
}

CATEGORY_DIRECTORY_HINTS = {
    "performance": {"optimizer", "executor"},
    "security": {"libpq", "auth"},
    "replication": {"replication", "wal"},
    "json": {"json"},
    "index": {"btree", "index", "brin", "gin", "gist"},
    "sql": {"parser"},
    "ddl": {"parser", "commands"},
}


@dataclass(slots=True)
class FeatureMappingConfig:
    """Configuration knobs for the mapping pipeline."""

    max_nodes_per_feature: int = 15
    max_candidates_per_kind: int = 60
    max_candidates_total: int = 0  # 0 disables total cap
    score_threshold: float = 0.15
    dry_run: bool = False
    feature_matrix_url: str = FEATURE_MATRIX_URL
    include_calls: bool = False
    include_namespaces: bool = False
    batch_size: int = 10
    skip_tagging: bool = False
    summary_output_dir: Optional[Path] = None
    resume_from: Optional[str] = None


@dataclass
class FeatureMappingPipeline:
    """High-level orchestrator for the feature-to-code mapping workflow."""

    joern: JoernClient
    config: FeatureMappingConfig = field(default_factory=FeatureMappingConfig)

    def fetch_features(self) -> List[Feature]:
        """Retrieve feature definitions from the official PostgreSQL matrix."""
        logger.info("Fetching feature matrix from %s", self.config.feature_matrix_url)
        return fetch_feature_matrix(self.config.feature_matrix_url)

    def run(
        self,
        features: Optional[Sequence[Feature]] = None,
    ) -> List[MappingResult]:
        """Execute the end-to-end mapping pipeline."""
        features = list(features) if features is not None else self.fetch_features()
        if self.config.resume_from:
            resume_key = normalise(self.config.resume_from)
            start_index = next(
                (idx for idx, feature in enumerate(features) if normalise(feature.name) == resume_key),
                None,
            )
            if start_index is None:
                logger.warning(
                    "Resume marker '%s' not found in feature list; processing all %d features.",
                    self.config.resume_from,
                    len(features),
                )
            else:
                features = features[start_index:]
                logger.info(
                    "Resuming from feature '%s' at position %d (remaining %d features).",
                    features[0].name,
                    start_index + 1,
                    len(features),
                )
        total = len(features)
        logger.info("Mapping %d features onto the PostgreSQL CPG", total)
        results: List[MappingResult] = []
        batch_size = max(1, self.config.batch_size)
        for batch_start in range(0, total, batch_size):
            batch = features[batch_start : batch_start + batch_size]
            batch_end = batch_start + len(batch)
            logger.info(
                "Processing feature batch %d-%d/%d",
                batch_start + 1,
                batch_end,
                total,
            )
            for feature in batch:
                try:
                    result = self.map_feature(feature)
                except Exception as exc:  # noqa: BLE001 - propagate gracefully
                    logger.error("Failed to map feature %s: %s", feature.name, exc, exc_info=True)
                    continue
                results.append(result)
                self._write_summary(result)
                if (
                    not self.config.dry_run
                    and not self.config.skip_tagging
                    and result.nodes
                ):
                    try:
                        self.apply_tags(result)
                    except Exception as exc:  # noqa: BLE001
                        logger.error(
                            "Failed to tag nodes for feature %s: %s", feature.name, exc, exc_info=True
                        )
        return results

    def map_feature(self, feature: Feature) -> MappingResult:
        """Map an individual feature to candidate code nodes."""
        override = feature_override_for(feature.name)
        name_tokens = feature.tokens(
            extra_stopwords=override.extra_stopwords or None,
            include_description=False,
        )
        description_tokens: List[str] = []
        if feature.description:
            description_tokens = tokenize(
                feature.description,
                extra_stopwords=override.extra_stopwords or None,
            )[:4]
        base_tokens = list(dict.fromkeys(name_tokens))
        if override.tokens:
            for token in override.tokens:
                if token not in base_tokens:
                    base_tokens.append(token)
        if not base_tokens:
            for token in description_tokens:
                if token not in base_tokens:
                    base_tokens.append(token)
                if len(base_tokens) >= 3:
                    break
        expanded_tokens = expand_tokens(
            list(dict.fromkeys(base_tokens + description_tokens)),
            category=feature.category,
        )
        if not expanded_tokens:
            expanded_tokens = base_tokens
        matching_tokens = base_tokens if base_tokens else (description_tokens or expanded_tokens)
        directory_hints = self._directory_hints(
            feature,
            expanded_tokens,
            extra_hints=override.directory_hints,
        )

        logger.debug(
            "Feature '%s' match_tokens=%s expanded_tokens=%s hints=%s",
            feature.name,
            matching_tokens,
            expanded_tokens,
            directory_hints,
        )

        search_start = time.perf_counter()
        candidates = self.joern.find_candidates(
            feature.name,
            matching_tokens,
            directory_hints=directory_hints,
            max_per_kind=self.config.max_candidates_per_kind,
            max_total_results=self.config.max_candidates_total,
            include_calls=self.config.include_calls,
            include_namespaces=self.config.include_namespaces,
        )
        if not candidates and directory_hints:
            candidates = self.joern.find_candidates(
                feature.name,
                matching_tokens,
                directory_hints=(),
                max_per_kind=self.config.max_candidates_per_kind,
                max_total_results=self.config.max_candidates_total,
                include_calls=self.config.include_calls,
                include_namespaces=self.config.include_namespaces,
            )
        elapsed = time.perf_counter() - search_start

        filtered = self._filter_candidates(candidates)
        logger.debug(
            "Feature '%s' Joern search yielded %d candidates in %.2fs; %d retained (threshold %.2f)",
            feature.name,
            len(candidates),
            elapsed,
            len(filtered),
            self.config.score_threshold,
        )
        if not filtered and candidates:
            logger.debug(
                "Feature '%s' filtered out all %d candidates; consider lowering score threshold",
                feature.name,
                len(candidates),
            )

        logger.info(
            "Feature '%s' => %d candidate nodes (filtered from %d)",
            feature.name,
            len(filtered),
            len(candidates),
        )
        return MappingResult(feature=feature, nodes=filtered)

    def apply_tags(self, result: MappingResult) -> None:
        """Persist feature tags to the CPG."""
        if self.config.skip_tagging:
            logger.debug(
                "Skipping tag persistence for feature '%s' (skip-tagging enabled).",
                result.feature.name,
            )
            return
        node_ids = [node.node_id for node in result.best_nodes(self.config.max_nodes_per_feature)]
        if not node_ids:
            logger.warning("No candidate nodes to tag for feature '%s'", result.feature.name)
            return
        pending_node_ids = self.joern.filter_untagged_nodes(result.feature.name, node_ids)
        if not pending_node_ids:
            logger.info(
                "All %d candidate nodes already tagged for feature '%s'; no updates required.",
                len(node_ids),
                result.feature.name,
            )
            return
        logger.debug(
            "Tagging %d/%d nodes for feature '%s' (skipped %d already-tagged nodes).",
            len(pending_node_ids),
            len(node_ids),
            result.feature.name,
            len(node_ids) - len(pending_node_ids),
        )
        self.joern.tag_feature(result.feature.name, pending_node_ids)

    def _filter_candidates(self, candidates: Sequence[CandidateNode]) -> List[CandidateNode]:
        threshold = self.config.score_threshold
        filtered = [cand for cand in candidates if cand.score >= threshold]
        if not filtered:
            filtered = candidates[: self.config.max_nodes_per_feature]
        else:
            filtered = filtered[: self.config.max_nodes_per_feature]
        return filtered

    def _directory_hints(
        self,
        feature: Feature,
        tokens: Sequence[str],
        *,
        extra_hints: Sequence[str] = (),
    ) -> List[str]:
        hints: set[str] = set(extra_hints)
        for token in tokens:
            hints.update(TOKEN_DIRECTORY_HINTS.get(token, set()))
        if feature.category:
            category_key = normalise(feature.category)
            for key, values in CATEGORY_DIRECTORY_HINTS.items():
                if key in category_key:
                    hints.update(values)
        return sorted(hints)

    def _write_summary(self, result: MappingResult) -> None:
        output_dir = self.config.summary_output_dir
        if not output_dir:
            return
        try:
            path = Path(output_dir)
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.error("Failed to prepare summary directory %s: %s", output_dir, exc)
            return
        slug = re.sub(r"[^a-z0-9]+", "-", normalise(result.feature.name)).strip("-") or "feature"
        timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        payload = {
            "feature": result.feature.to_dict(),
            "generated_at": timestamp,
            "node_limit": self.config.max_nodes_per_feature,
            "candidates": [
                {
                    "id": node.node_id,
                    "kind": node.kind,
                    "name": node.name,
                    "filename": node.filename,
                    "line": node.line_number,
                    "score": node.score,
                }
                for node in result.nodes
            ],
        }
        output_path = path / f"{slug}.json"
        try:
            output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.error(
                "Failed to write summary for feature '%s' to %s: %s",
                result.feature.name,
                output_path,
                exc,
            )
