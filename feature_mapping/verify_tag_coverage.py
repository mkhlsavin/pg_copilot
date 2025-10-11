#!/usr/bin/env python3
"""
Feature Tag Coverage Reporter

Generates a coverage report showing how many CPG nodes are tagged for each PostgreSQL feature.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Iterable, List, Optional

from feature_mapping import config as local_config
from feature_mapping.cli import load_features
from feature_mapping.feature_matrix import FEATURE_MATRIX_URL
from feature_mapping.joern_client import JoernClient
from feature_mapping.models import FeatureCoverage

LOG_FORMAT = "%(levelname)s %(name)s: %(message)s"


def parse_arguments(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report Feature tag coverage for PostgreSQL 17 features.",
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
        "--feature-file",
        type=Path,
        help="Optional path to a newline-delimited list of feature names to include.",
    )
    parser.add_argument(
        "--feature-matrix-url",
        default=FEATURE_MATRIX_URL,
        help="Override the PostgreSQL feature matrix URL (useful for offline copies).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON file to write coverage data.",
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


def collect_feature_names(args: argparse.Namespace) -> List[str]:
    selected: List[str] = []
    if args.feature:
        selected.extend(args.feature)
    if args.feature_file and args.feature_file.exists():
        selected.extend(
            line.strip()
            for line in args.feature_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    return selected


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_arguments(argv)
    setup_logging(args.log_level)

    env_warning = local_config.validate_environment()
    if env_warning:
        logging.warning(env_warning)

    selected = collect_feature_names(args)
    features = load_features(args.feature_matrix_url, selected or None)
    if not features:
        logging.error("No features selected for coverage reporting.")
        return 2

    joern_workdir = local_config.DEFAULT_JOERN_HOME if local_config.DEFAULT_JOERN_HOME.exists() else None
    joern = JoernClient(binary=args.joern_binary, cpg_path=args.cpg, workdir=joern_workdir)

    logging.info("Collecting coverage for %d feature(s)...", len(features))
    counts = joern.feature_tag_counts([feature.name for feature in features])

    coverages = [
        FeatureCoverage(feature=feature, tagged_nodes=counts.get(feature.name, 0))
        for feature in features
    ]

    total_tagged = sum(item.tagged_nodes for item in coverages)
    uncovered = [item for item in coverages if not item.is_tagged]

    logging.info("Total tagged nodes across selection: %d", total_tagged)
    logging.info("Features with at least one tag: %d/%d", len(coverages) - len(uncovered), len(coverages))

    if uncovered:
        logging.warning("Found %d feature(s) with zero tags:", len(uncovered))
        for item in uncovered:
            logging.warning(" - %s (category=%s)", item.feature.name, item.feature.category)
    else:
        logging.info("All selected features have at least one tagged node.")

    if args.output:
        payload = [
            {
                "feature": item.feature.to_dict(),
                "tagged_nodes": item.tagged_nodes,
                "is_tagged": item.is_tagged,
            }
            for item in coverages
        ]
        args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logging.info("Coverage report written to %s", args.output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
