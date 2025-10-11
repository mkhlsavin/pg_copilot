from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .generator import QueryGenerator, GenerationError
from .grammar_loader import GrammarLoadError, GrammarSpec, load_grammar
from .sampler import SamplerConfig, build_sampler, GrammarLoadError as SamplerError
from .validator import validate_query


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate CPGQL queries using the XGrammar engine.",
    )
    parser.add_argument(
        "--grammar",
        type=Path,
        help="Override path to cpgql.gbnf (defaults to repo copy).",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of queries to generate (default: 1).",
    )
    parser.add_argument(
        "--mode",
        choices=("random", "deterministic"),
        default="random",
        help="Sampling mode (default: random).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Optional RNG seed for reproducible generation.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=128,
        help="Maximum traversal length allowed by the sampler.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run lightweight validation on generated queries.",
    )
    parser.add_argument(
        "--export-gbnf",
        type=Path,
        help="Write the sanitised grammar to the given path and exit.",
    )
    parser.add_argument(
        "--tokenizer-vocab",
        type=Path,
        help="Path to tokenizer vocabulary (JSON array or newline-delimited tokens) for sampler compilation.",
    )
    parser.add_argument(
        "--tokenizer-metadata",
        type=Path,
        help="Path to tokenizer metadata JSON (produced via TokenizerInfo.serialize_json).",
    )
    parser.add_argument(
        "--tokenizer-gguf",
        type=Path,
        help="Path to a GGUF model whose tokenizer should be used for sampler compilation.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        grammar: GrammarSpec = load_grammar(args.grammar, start_symbol="root")
        if args.export_gbnf:
            args.export_gbnf.write_text(grammar.source, encoding="utf-8")
            print(f"Sanitised grammar written to {args.export_gbnf}")
            return 0
        sampler_config = SamplerConfig(
            tokenizer_vocab=args.tokenizer_vocab,
            tokenizer_metadata=args.tokenizer_metadata,
            tokenizer_gguf=args.tokenizer_gguf,
        )
        if sampler_config.tokenizer_gguf and (
            sampler_config.tokenizer_vocab or sampler_config.tokenizer_metadata
        ):
            parser.error("Specify either --tokenizer-gguf or (--tokenizer-vocab + --tokenizer-metadata), not both.")
        sampler = None
        if sampler_config.enabled:
            try:
                sampler = build_sampler(grammar, sampler_config)
            except (GrammarLoadError, SamplerError) as exc:
                parser.error(str(exc))
        if sampler is not None:
            generator = QueryGenerator.from_sampler(grammar, sampler)
        else:
            generator = QueryGenerator.from_spec(grammar)
        queries = generator.generate(
            count=args.count,
            mode=args.mode,
            seed=args.seed,
            max_steps=args.max_steps,
        )
    except (GrammarLoadError, GenerationError) as exc:
        parser.error(str(exc))
        return 2  # pragma: no cover (argparse exits)

    for query in queries:
        if args.validate:
            validation = validate_query(query)
            if not validation.valid:
                print(f"# INVALID: {validation.issues}", file=sys.stderr)
        print(query)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
