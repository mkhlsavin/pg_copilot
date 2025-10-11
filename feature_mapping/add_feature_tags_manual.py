#!/usr/bin/env python3
"""
Feature Tagging Bootstrapper

Runs the automated FeatureMappingPipeline for a curated set of high-impact PostgreSQL
features. This replaces the legacy manual tagging script and delegates all discovery
and tagging to the shared pipeline logic.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Iterable, List, Optional

from feature_mapping import config as local_config
from feature_mapping.cli import load_features
from feature_mapping.feature_matrix import FEATURE_MATRIX_URL
from feature_mapping.joern_client import JoernClient
from feature_mapping.pipeline import FeatureMappingConfig, FeatureMappingPipeline

# Curated feature names previously handled manually.
FEATURE_NAMES = [
    "MERGE",
    "Logical replication",
    "JSONB data type",
    "Parallel query",
    "Partitioning",
    "WAL improvements",
    "SCRAM-SHA-256",
    "JIT compilation",
    "BRIN indexes",
    "TOAST",
]

LOG_FORMAT = "%(levelname)s %(name)s: %(message)s"


def parse_arguments(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run FeatureMappingPipeline for a curated subset of PostgreSQL features.",
    )
    parser.add_argument(
        "--joern-binary",
        default=str(local_config.DEFAULT_JOERN_BINARY),
        help="Path to the Joern executable.",
    )
    parser.add_argument(
        "--cpg",
        type=Path,
        default=local_config.DEFAULT_CPG_PATH,
        help="Path to the PostgreSQL 17 CPG binary.",
    )
    parser.add_argument(
        "--feature",
        action="append",
        help="Optional feature name to include (can be provided multiple times).",
    )
    parser.add_argument(
        "--feature-matrix-url",
        default=FEATURE_MATRIX_URL,
        help="Override the PostgreSQL feature matrix URL (useful for offline copies).",
    )
    parser.add_argument(
        "--max-nodes",
        type=int,
        default=15,
        help="Maximum number of nodes to tag per feature.",
    )
    parser.add_argument(
        "--max-per-kind",
        type=int,
        default=60,
        help="Maximum number of candidate nodes to inspect per CPG node kind.",
    )
    parser.add_argument(
        "--max-candidates-total",
        type=int,
        default=0,
        help="Optional cap on the total candidate nodes retrieved per feature (0 = unlimited).",
    )
    parser.add_argument(
        "--score-threshold",
        type=float,
        default=0.15,
        help="Minimum heuristic score required for a node to be tagged.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Number of features to process per batch when invoking Joern.",
    )
    parser.add_argument(
        "--summary-dir",
        type=Path,
        help="Write per-feature candidate summaries (JSON) to this directory.",
    )
    parser.add_argument(
        "--skip-tagging",
        action="store_true",
        help="Skip writing Feature tags to the CPG (review-only run).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover candidate nodes but do not persist tags.",
    )
    parser.add_argument(
        "--resume-from",
        help="Resume processing starting from the feature with the given name.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set the logging verbosity.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def setup_logging(level: str) -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format=LOG_FORMAT)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_arguments(argv)
    setup_logging(args.log_level)

    env_warning = local_config.validate_environment()
    if env_warning:
        logging.warning(env_warning)

    selected_features: List[str] = FEATURE_NAMES.copy()
    if args.feature:
        selected_features.extend(args.feature)

    features = load_features(args.feature_matrix_url, selected_features)
    if not features:
        logging.error("No matching features found in the matrix for selection: %s", selected_features)
        return 2

    joern_workdir = local_config.DEFAULT_JOERN_HOME if local_config.DEFAULT_JOERN_HOME.exists() else None
    joern = JoernClient(binary=args.joern_binary, cpg_path=args.cpg, workdir=joern_workdir)

    config = FeatureMappingConfig(
        max_nodes_per_feature=args.max_nodes,
        max_candidates_per_kind=args.max_per_kind,
        max_candidates_total=args.max_candidates_total,
        score_threshold=args.score_threshold,
        dry_run=args.dry_run,
        feature_matrix_url=args.feature_matrix_url,
        include_calls=True,
        include_namespaces=False,
        batch_size=args.batch_size,
        skip_tagging=args.skip_tagging,
        summary_output_dir=args.summary_dir,
        resume_from=args.resume_from,
    )

    pipeline = FeatureMappingPipeline(joern=joern, config=config)

    logging.info(
        "Processing %d curated feature(s). Dry-run=%s Skip-tagging=%s",
        len(features),
        args.dry_run,
        args.skip_tagging,
    )
    results = pipeline.run(features)
    logging.info("Completed mapping for %d feature(s).", len(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
