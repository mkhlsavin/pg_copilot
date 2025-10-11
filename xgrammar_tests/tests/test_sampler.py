from __future__ import annotations

import json
from pathlib import Path

import pytest

from xgrammar.compiler import TokenizerInfo
from xgrammar.grammar import Grammar

from xgrammar_tests.generator import QueryGenerator
from xgrammar_tests.grammar_loader import GrammarSpec, GrammarLoadError
from xgrammar_tests.sampler import SamplerConfig, build_sampler, load_tokenizer_info


def _write_files(tmp_path: Path, vocab: list[str], metadata: str) -> tuple[Path, Path]:
    vocab_path = tmp_path / "tokenizer.vocab.txt"
    vocab_path.write_text("\n".join(vocab), encoding="utf-8")
    metadata_path = tmp_path / "tokenizer.metadata.json"
    metadata_path.write_text(metadata, encoding="utf-8")
    return vocab_path, metadata_path


def test_sampler_disabled_returns_none():
    grammar = Grammar.from_ebnf('root ::= "a"', root_rule_name="root")
    spec = GrammarSpec(path=Path("dummy"), source='root ::= "a"', engine=grammar)
    config = SamplerConfig()
    sampler = build_sampler(spec, config)
    assert sampler is None


def test_sampler_missing_files_raises(tmp_path: Path):
    grammar = Grammar.from_ebnf('root ::= "a"', root_rule_name="root")
    spec = GrammarSpec(path=Path("dummy"), source='root ::= "a"', engine=grammar)
    config = SamplerConfig(
        tokenizer_vocab=tmp_path / "missing.vocab",
        tokenizer_metadata=tmp_path / "missing.json",
    )
    with pytest.raises(GrammarLoadError):
        build_sampler(spec, config)


def test_sampler_generation_roundtrip(tmp_path: Path):
    grammar_src = 'root ::= "a"'
    grammar = Grammar.from_ebnf(grammar_src, root_rule_name="root")
    spec = GrammarSpec(path=Path("dummy"), source=grammar_src, engine=grammar)

    tokenizer_info = TokenizerInfo(["a", "b", "<pad>"])
    metadata = tokenizer_info.serialize_json()
    vocab_path, metadata_path = _write_files(tmp_path, ["a", "b", "<pad>"], metadata)
    config = SamplerConfig(tokenizer_vocab=vocab_path, tokenizer_metadata=metadata_path)

    sampler = build_sampler(spec, config)
    if sampler is None:
        pytest.skip("Compiled grammar did not expose a sampler in this environment.")

    generator = QueryGenerator.from_sampler(spec, sampler)
    result = generator.generate(count=1, mode="deterministic", max_steps=8)
    assert result
    assert isinstance(result[0], str)


def test_load_tokenizer_info_from_gguf(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    gguf_file = tmp_path / "model.gguf"
    gguf_file.write_bytes(b"gguf")

    dummy = TokenizerInfo(["a", "b", "c"])
    monkeypatch.setattr("xgrammar_tests.sampler.tokenizer_info_from_gguf", lambda path: dummy)

    config = SamplerConfig(tokenizer_gguf=gguf_file)
    info = load_tokenizer_info(config)
    assert info is dummy
