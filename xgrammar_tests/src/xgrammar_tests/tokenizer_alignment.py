from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from gguf import GGUFReader

from xgrammar.tokenizer_info import TokenizerInfo, VocabType


class TokenizerAlignmentError(RuntimeError):
    """Raised when tokenizer metadata cannot be extracted."""


@dataclass(slots=True)
class GGUFMetadata:
    tokens: List[str]
    stop_token_ids: List[int]
    vocab_type: VocabType
    add_prefix_space: bool


def tokenizer_info_from_gguf(path: Path | str) -> TokenizerInfo:
    """
    Construct a TokenizerInfo object from a GGUF model file.

    Parameters
    ----------
    path : Path | str
        Path to the GGUF model containing tokenizer metadata.
    """
    reader = GGUFReader(Path(path))
    metadata = _extract_metadata(reader)
    return TokenizerInfo(
        metadata.tokens,
        vocab_type=metadata.vocab_type,
        vocab_size=len(metadata.tokens),
        stop_token_ids=metadata.stop_token_ids or None,
        add_prefix_space=metadata.add_prefix_space,
    )


def _extract_metadata(reader: GGUFReader) -> GGUFMetadata:
    token_field = reader.get_field("tokenizer.ggml.tokens")
    if token_field is None:
        raise TokenizerAlignmentError("GGUF file does not contain `tokenizer.ggml.tokens` field.")
    tokens_raw = token_field.contents()
    if not isinstance(tokens_raw, list) or not tokens_raw:
        raise TokenizerAlignmentError("Tokenizer tokens field is empty or malformed.")
    tokens = [_ensure_str(token) for token in tokens_raw]

    stop_ids = _collect_stop_token_ids(reader)
    vocab_type = _infer_vocab_type(tokens)
    add_prefix_space = _infer_prefix_space(reader, tokens)

    return GGUFMetadata(
        tokens=tokens,
        stop_token_ids=stop_ids,
        vocab_type=vocab_type,
        add_prefix_space=add_prefix_space,
    )


def _ensure_str(token: object) -> str:
    if isinstance(token, str):
        return token
    if isinstance(token, bytes):
        return token.decode("utf-8", "ignore")
    raise TokenizerAlignmentError(f"Unsupported token type: {type(token)!r}")


_STOP_TOKEN_KEYS: Sequence[str] = (
    "tokenizer.ggml.eos_token_id",
    "tokenizer.ggml.eot_token_id",
    "tokenizer.ggml.eom_token_id",
    "tokenizer.ggml.middle_token_id",
    "tokenizer.ggml.stop_token_id",
)


def _collect_stop_token_ids(reader: GGUFReader) -> List[int]:
    stop_ids: List[int] = []
    for key in _STOP_TOKEN_KEYS:
        field = reader.get_field(key)
        if field is None:
            continue
        value = field.contents()
        if isinstance(value, list):
            stop_ids.extend(int(v) for v in value if isinstance(v, (int, float)))
        elif isinstance(value, (int, float)):
            stop_ids.append(int(value))
    deduped: List[int] = []
    for value in stop_ids:
        if value not in deduped:
            deduped.append(value)
    return deduped


def _infer_vocab_type(tokens: Sequence[str]) -> VocabType:
    window = tokens[: min(len(tokens), 1024)]
    if any(token.startswith("<0x") and token.endswith(">") for token in window):
        return VocabType.BYTE_FALLBACK
    if any(token.startswith("Ġ") for token in window):
        return VocabType.BYTE_LEVEL
    return VocabType.RAW


def _infer_prefix_space(reader: GGUFReader, tokens: Sequence[str]) -> bool:
    # Heuristic: SentencePiece based vocabularies encode spaces as '▁', which
    # does not require prefix spaces. Byte fallback tokenizers typically need
    # the leading space to be preserved.
    pre_field = reader.get_field("tokenizer.ggml.pre")
    if pre_field is not None:
        value = str(pre_field.contents()).lower()
        if "llama" in value or "baichuan" in value:
            return True
    sample = tokens[: min(len(tokens), 1024)]
    if any(token.startswith("▁") for token in sample):
        return False
    vocab_type = _infer_vocab_type(sample)
    return vocab_type is VocabType.BYTE_FALLBACK

