from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

from .grammar_loader import GrammarSpec, GrammarLoadError
from .tokenizer_alignment import TokenizerAlignmentError, tokenizer_info_from_gguf

try:
    from xgrammar.compiler import GrammarCompiler, TokenizerInfo
except Exception:  # pragma: no cover - optional dependency already required transitively
    GrammarCompiler = None  # type: ignore
    TokenizerInfo = None  # type: ignore


@dataclass(slots=True)
class SamplerConfig:
    """Configuration describing how to obtain tokenizer metadata for the sampler."""

    tokenizer_vocab: Optional[Path] = None
    tokenizer_metadata: Optional[Path] = None
    tokenizer_gguf: Optional[Path] = None

    @property
    def enabled(self) -> bool:
        return any(
            (
                self.tokenizer_vocab is not None and self.tokenizer_metadata is not None,
                self.tokenizer_gguf is not None,
            )
        )


def load_tokenizer_info(config: SamplerConfig) -> TokenizerInfo:
    if TokenizerInfo is None:
        raise GrammarLoadError("XGrammar TokenizerInfo is unavailable; update the `xgrammar` package.")
    if config.tokenizer_gguf is not None:
        gguf_path = config.tokenizer_gguf.resolve()
        if not gguf_path.exists():
            raise GrammarLoadError(f"Tokenizer GGUF model not found: {gguf_path}")
        try:
            return tokenizer_info_from_gguf(gguf_path)
        except TokenizerAlignmentError as exc:
            raise GrammarLoadError(f"Failed to parse GGUF tokenizer: {exc}") from exc
    assert config.tokenizer_vocab and config.tokenizer_metadata
    vocab_path = config.tokenizer_vocab.resolve()
    metadata_path = config.tokenizer_metadata.resolve()
    if not vocab_path.exists():
        raise GrammarLoadError(f"Tokenizer vocabulary not found: {vocab_path}")
    if not metadata_path.exists():
        raise GrammarLoadError(f"Tokenizer metadata not found: {metadata_path}")
    encoded_vocab = _load_vocab(vocab_path)
    metadata = metadata_path.read_text(encoding="utf-8")
    return TokenizerInfo.from_vocab_and_metadata(encoded_vocab, metadata)


def build_sampler(spec: GrammarSpec, config: SamplerConfig) -> Optional[Any]:
    """Return a sampler compiled via GrammarCompiler, if metadata is provided."""
    if not config.enabled:
        return None
    if GrammarCompiler is None:
        raise GrammarLoadError("XGrammar GrammarCompiler is unavailable; update the `xgrammar` package.")
    tokenizer_info = load_tokenizer_info(config)
    compiler = GrammarCompiler(tokenizer_info)
    compiled = compiler.compile_grammar(spec.source)
    if hasattr(compiled, "sampler"):
        return compiled.sampler()
    if hasattr(compiled, "create_sampler"):
        return compiled.create_sampler()
    warnings.warn("Compiled grammar does not expose a sampler factory; falling back to engine-only mode.", RuntimeWarning)
    return None


def _load_vocab(path: Path) -> list[str]:
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [str(token) for token in data]
        raise GrammarLoadError("Tokenizer vocabulary JSON must be a list of tokens.")
    # Assume plain text, one token per line.
    return path.read_text(encoding="utf-8").splitlines()
