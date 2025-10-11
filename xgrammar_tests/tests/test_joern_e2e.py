from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List

import pytest

from xgrammar_tests import joern_e2e
from xgrammar_tests.joern_e2e import JoernE2ERunner, JoernConnectionConfig, JoernE2EError, GeneratedQuery
from xgrammar_tests.sampler import SamplerConfig


@dataclass
class DummySpec:
    path: Path = Path("dummy")
    source: str = "root ::= 'a'"
    start_symbol: str = "root"
    engine: object | None = object()


class DummyGenerator:
    def __init__(self, queries: List[str]) -> None:
        self._queries = queries

    def generate(self, **kwargs: Any) -> List[str]:
        return list(self._queries)


class DummyClient:
    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint
        self.executed: List[str] = []

    def execute(self, query: str) -> dict[str, Any]:
        self.executed.append(query)
        return {"success": True, "stdout": "ok"}


@pytest.fixture(autouse=True)
def patch_generation(monkeypatch: pytest.MonkeyPatch):
    dummy_generator = DummyGenerator(["cpg.method.limit(1)"])
    monkeypatch.setattr(joern_e2e, "load_grammar", lambda *_, **__: DummySpec())
    monkeypatch.setattr(
        joern_e2e,
        "QueryGenerator",
        SimpleNamespace(
            from_spec=lambda spec: dummy_generator,
            from_sampler=lambda spec, sampler: dummy_generator,
        ),
    )
    monkeypatch.setattr(joern_e2e, "validate_query", lambda query: SimpleNamespace(valid=True, issues=[]))
    monkeypatch.setattr(joern_e2e, "build_sampler", lambda spec, config: object())
    yield


def test_generate_and_execute_without_joern():
    runner = JoernE2ERunner()
    # prevent auto-connect attempts
    runner.close()
    sampler_config = SamplerConfig(tokenizer_vocab=None, tokenizer_metadata=None, tokenizer_gguf=None)

    results = runner.generate_and_execute(sampler_config=sampler_config, count=1, validate=True)

    assert len(results) == 1
    assert isinstance(results[0], GeneratedQuery)
    assert results[0].joern_response is None


def test_generate_and_execute_with_joern(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, Any] = {"client": None}

    def fake_client(endpoint: str):
        captured["client"] = DummyClient(endpoint)
        return captured["client"]

    monkeypatch.setattr(joern_e2e, "CPGQLSClient", fake_client)

    runner = JoernE2ERunner(JoernConnectionConfig(host="localhost", port=8080))
    runner.connect()
    results = runner.generate_and_execute(sampler_config=SamplerConfig(), count=1, validate=False)

    assert captured["client"] is not None
    assert captured["client"].executed == ["cpg.method.limit(1)"]
    assert results[0].joern_response == {"success": True, "stdout": "ok"}


def test_connect_without_dependency(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(joern_e2e, "CPGQLSClient", None)
    runner = JoernE2ERunner()
    with pytest.raises(JoernE2EError):
        runner.connect()
