#!/usr/bin/env python
"""Export TokenizerInfo metadata and vocabulary from a Hugging Face tokenizer."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from transformers import AutoTokenizer

from xgrammar.compiler import TokenizerInfo
from xgrammar_tests.tokenizer_alignment import (
    TokenizerAlignmentError,
    tokenizer_info_from_gguf,
)


def export_tokenizer(model_path: str, vocab_path: Path, metadata_path: Path) -> None:
    path = Path(model_path)
    if path.suffix.lower() == ".gguf" and path.exists():
        tokenizer_info = tokenizer_info_from_gguf(path)
    else:
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        tokenizer_info = TokenizerInfo.from_huggingface(tokenizer)
    metadata_path.write_text(tokenizer_info.serialize_json(), encoding="utf-8")
    decoded = [token.decode("utf-8", "ignore") if isinstance(token, bytes) else str(token)
               for token in tokenizer_info.decoded_vocab]
    if vocab_path.suffix == ".json":
        vocab_path.write_text(json.dumps(decoded, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        vocab_path.write_text("\n".join(decoded), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", help="Hugging Face model or local tokenizer path")
    parser.add_argument("--vocab", type=Path, default=Path("tokenizer.vocab.txt"), help="Output vocab file (txt or json)")
    parser.add_argument("--metadata", type=Path, default=Path("tokenizer.metadata.json"), help="Output metadata JSON file")
    args = parser.parse_args()
    try:
        export_tokenizer(args.model, args.vocab, args.metadata)
    except TokenizerAlignmentError as exc:
        parser.error(str(exc))
    print(f"Wrote vocab to {args.vocab}")
    print(f"Wrote metadata to {args.metadata}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
