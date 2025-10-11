from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Iterable, List, Optional

from . import config as local_config
from .feature_matrix import FEATURE_MATRIX_URL, fetch_feature_matrix
from .joern_client import JoernClient
from .models import Feature, MappingResult
from .pipeline import FeatureMappingConfig, FeatureMappingPipeline

LOG_FORMAT = "%(levelname)s %(name)s: %(message)s"


def parse_arguments(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Map PostgreSQL 17 feature matrix entries to Joern CPG nodes.",
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
    parser.add_argument("--feature", action="append", help="Limit execution to specific feature names.")
    parser.add_argument(
        "--feature-file",
        type=Path,
        help="Optional path to a newline-delimited list of feature names to include.",
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
        "--dry-run",
        action="store_true",
        help="Discover candidate nodes but do not persist tags.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON file to write the resulting mapping.",
    )
    parser.add_argument(
        "--matrix-output",
        type=Path,
        help="Optional JSON file to capture the fetched feature matrix snapshot.",
    )
    parser.add_argument(
        "--feature-matrix-url",
        default=FEATURE_MATRIX_URL,
        help="Override the PostgreSQL feature matrix URL (useful for offline copies).",
    )
    parser.add_argument(
        "--include-calls",
        action="store_true",
        help="Include call sites when generating candidates.",
    )
    parser.add_argument(
        "--include-namespaces",
        action="store_true",
        help="Include namespace blocks when generating candidates.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of features to process per batch when invoking Joern.",
    )
    parser.add_argument(
        "--skip-tagging",
        action="store_true",
        help="Skip writing Feature tags to the CPG (useful for review-only runs).",
    )
    parser.add_argument(
        "--resume-from",
        help="Resume processing starting from the feature with the given name.",
    )
    parser.add_argument(
        "--summary-dir",
        type=Path,
        help="Write per-feature candidate summaries (JSON) to this directory.",
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


def load_features(url: str, include_names: Optional[List[str]] = None) -> List[Feature]:
    features = fetch_feature_matrix(url)
    if include_names:
        lowered = {name.lower() for name in include_names}
        features = [feature for feature in features if feature.name.lower() in lowered]
    return features


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_arguments(argv)
    setup_logging(args.log_level)

    env_warning = local_config.validate_environment()
    if env_warning:
        logging.warning(env_warning)

    include_features: List[str] = []
    if args.feature:
        include_features.extend(args.feature)
    if args.feature_file and args.feature_file.exists():
        include_features.extend(
            line.strip()
            for line in args.feature_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )

    features = load_features(args.feature_matrix_url, include_features or None)
    if not features:
        logging.error("No features selected for mapping.")
        return 2

    if args.matrix_output:
        matrix_payload = [feature.to_dict() for feature in features]
        args.matrix_output.write_text(json.dumps(matrix_payload, indent=2), encoding="utf-8")
        logging.info("Feature matrix snapshot written to %s", args.matrix_output)

    joern_workdir = local_config.DEFAULT_JOERN_HOME if local_config.DEFAULT_JOERN_HOME.exists() else None
    joern = JoernClient(binary=args.joern_binary, cpg_path=args.cpg, workdir=joern_workdir)
    pipeline = FeatureMappingPipeline(
        joern=joern,
        config=FeatureMappingConfig(
            max_nodes_per_feature=args.max_nodes,
            max_candidates_per_kind=args.max_per_kind,
            max_candidates_total=args.max_candidates_total,
            score_threshold=args.score_threshold,
            dry_run=args.dry_run,
            feature_matrix_url=args.feature_matrix_url,
            include_calls=args.include_calls,
            include_namespaces=args.include_namespaces,
            batch_size=args.batch_size,
            skip_tagging=args.skip_tagging,
            summary_output_dir=args.summary_dir,
            resume_from=args.resume_from,
        ),
    )

    logging.info("Processing %d feature(s). Dry-run=%s", len(features), args.dry_run)
    results = pipeline.run(features)
    logging.info("Mapped %d feature(s).", len(results))

    if args.output:
        serialised = [
            {
                "feature": {
                    "name": result.feature.name,
                    "category": result.feature.category,
                    "description": result.feature.description,
                    "detail_url": result.feature.detail_url,
                },
                "nodes": [
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
            for result in results
        ]
        args.output.write_text(json.dumps(serialised, indent=2), encoding="utf-8")
        logging.info("Mapping written to %s", args.output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
