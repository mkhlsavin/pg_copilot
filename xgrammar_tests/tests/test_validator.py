from __future__ import annotations

from xgrammar_tests.validator import validate_query


def test_validator_happy_path():
    result = validate_query("cpg.method.name.l")
    assert result.valid
    assert result.issues == []


def test_validator_detects_multiple_issues():
    result = validate_query(" method..name(")
    assert not result.valid
    assert "Query must start with the root object `cpg`." in result.issues
    assert "Query contains consecutive dots (`..`)." in result.issues
    assert "Parentheses are unbalanced." in result.issues
