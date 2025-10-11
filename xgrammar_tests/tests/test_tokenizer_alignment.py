from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict

import pytest

from xgrammar.tokenizer_info import VocabType
from xgrammar_tests import tokenizer_alignment as alignment


class DummyField:
    def __init__(self, value: Any) -> None:
        self._value = value

    def contents(self, *_, **__) -> Any:
        return self._value


class DummyReader:
    def __init__(self, fields: Dict[str, DummyField]) -> None:
        self._fields = fields

    def get_field(self, key: str) -> DummyField | None:
        return self._fields.get(key)


def _patch_reader(monkeypatch: pytest.MonkeyPatch, fields: Dict[str, DummyField]) -> None:
    monkeypatch.setattr(
        alignment,
        "GGUFReader",
        lambda path: DummyReader(fields),
    )


def test_tokenizer_info_from_gguf_byte_level(monkeypatch: pytest.MonkeyPatch) -> None:
    fields = {
        "tokenizer.ggml.tokens": DummyField(["!", "Ġfoo", "bar"]),
        "tokenizer.ggml.eos_token_id": DummyField(2),
        "tokenizer.ggml.pre": DummyField("qwen2"),
    }
    _patch_reader(monkeypatch, fields)

    info = alignment.tokenizer_info_from_gguf(Path("dummy.gguf"))

    assert info.vocab_size == 3
    assert info.vocab_type is VocabType.BYTE_LEVEL
    assert info.stop_token_ids == [2]
    assert info.add_prefix_space is False


def test_tokenizer_info_from_gguf_byte_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    fields = {
        "tokenizer.ggml.tokens": DummyField(["<0x0A>", "<0x1B>", "token"]),
        "tokenizer.ggml.eos_token_id": DummyField([1, 2]),
        "tokenizer.ggml.pre": DummyField("llama"),
    }
    _patch_reader(monkeypatch, fields)

    info = alignment.tokenizer_info_from_gguf(Path("dummy.gguf"))

    assert info.vocab_type is VocabType.BYTE_FALLBACK
    assert info.stop_token_ids == [1, 2]
    assert info.add_prefix_space is True


def test_tokenizer_info_from_gguf_missing_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_reader(monkeypatch, {})

    with pytest.raises(alignment.TokenizerAlignmentError):
        alignment.tokenizer_info_from_gguf(Path("missing.gguf"))
