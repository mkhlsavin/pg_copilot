from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from xgrammar_tests import cli
from xgrammar_tests.grammar_loader import GrammarLoadError


def test_build_parser_defaults():
    parser = cli.build_parser()
    args = parser.parse_args([])
    assert args.count == 1
    assert args.mode == "random"
    assert args.max_steps == 128


def test_main_invalid_path(tmp_path: Path):
    bogus = tmp_path / "missing.gbnf"
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--grammar", str(bogus)])
    assert excinfo.value.code != 0


def test_export_gbnf(tmp_path: Path):
    export_path = tmp_path / "out.gbnf"
    exit_code = cli.main(["--export-gbnf", str(export_path)])
    assert exit_code == 0
    content = export_path.read_text(encoding="utf-8")
    assert content.startswith("root")
