#!/usr/bin/env python
"""Generate CPGQL queries and optionally execute them against a Joern server."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from xgrammar_tests.joern_e2e import (
    GeneratedQuery,
    JoernConnectionConfig,
    JoernE2EError,
    JoernE2ERunner,
)
from xgrammar_tests.sampler import SamplerConfig


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grammar", type=Path, help="Optional path to a cpgql.gbnf file.")
    parser.add_argument("--count", type=int, default=3, help="Number of queries to generate.")
    parser.add_argument(
        "--mode",
        choices=("random", "deterministic"),
        default="random",
        help="Sampler mode to use.",
    )
    parser.add_argument("--seed", type=int, help="Optional RNG seed.")
    parser.add_argument("--max-steps", type=int, default=128, help="Maximum traversal length.")
    parser.add_argument(
        "--no-validate",
        dest="validate",
        action="store_false",
        help="Disable post-generation validation.",
    )

    sampler = parser.add_argument_group("Sampler")
    sampler.add_argument("--tokenizer-vocab", type=Path, help="Path to tokenizer vocabulary.")
    sampler.add_argument(
        "--tokenizer-metadata",
        type=Path,
        help="Path to tokenizer metadata JSON.",
    )
    sampler.add_argument(
        "--tokenizer-gguf",
        type=Path,
        help="Path to a GGUF model used to derive tokenizer metadata.",
    )

    joern = parser.add_argument_group("Joern")
    joern.add_argument("--joern-host", default="localhost", help="Joern server host.")
    joern.add_argument("--joern-port", type=int, default=8080, help="Joern server port.")
    joern.add_argument(
        "--joern-project",
        default="pg17_full.cpg",
        help="Workspace project name used when loading CPGs.",
    )
    joern.add_argument(
        "--joern-load",
        action="store_true",
        help="Attempt to load the CPG automatically if not already loaded.",
    )
    joern.add_argument(
        "--connect",
        action="store_true",
        help="Attempt to connect to Joern before generating queries.",
    )

    parser.set_defaults(validate=True)
    return parser


def _build_sampler_config(args: argparse.Namespace) -> SamplerConfig:
    return SamplerConfig(
        tokenizer_vocab=args.tokenizer_vocab,
        tokenizer_metadata=args.tokenizer_metadata,
        tokenizer_gguf=args.tokenizer_gguf,
    )


def _emit_result(idx: int, result: GeneratedQuery) -> None:
    print(f"# Query {idx}")
    print(result.query)
    if result.validation_issues:
        print(f"# validation issues: {result.validation_issues}", file=sys.stderr)
    if result.joern_response is not None:
        print(json.dumps(result.joern_response, indent=2))
    print()


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    sampler_config = _build_sampler_config(args)
    if sampler_config.tokenizer_gguf and (
        sampler_config.tokenizer_vocab or sampler_config.tokenizer_metadata
    ):
        parser.error("Specify either --tokenizer-gguf or the vocab/metadata pair, not both.")

    runner = JoernE2ERunner(
        JoernConnectionConfig(
            host=args.joern_host,
            port=args.joern_port,
            project=args.joern_project,
            load_cpg=args.joern_load,
        )
    )

    if args.connect:
        try:
            runner.connect()
        except JoernE2EError as exc:
            parser.error(str(exc))

    try:
        results = runner.generate_and_execute(
            grammar_path=args.grammar,
            sampler_config=sampler_config,
            count=args.count,
            mode=args.mode,
            seed=args.seed,
            max_steps=args.max_steps,
            validate=args.validate,
        )
    except JoernE2EError as exc:
        parser.error(str(exc))
        return 2  # pragma: no cover (argparse exits)

    for idx, result in enumerate(results, start=1):
        _emit_result(idx, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

