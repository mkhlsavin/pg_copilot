from feature_mapping.joern_client import _parse_coverage_output


def test_parse_coverage_output_handles_valid_lines() -> None:
    stdout = "\n".join(
        [
            "__COVERAGE__|MERGE|5",
            "__COVERAGE__|JSONB data type|12",
            "noise line",
        ]
    )
    coverage = _parse_coverage_output(stdout)
    assert coverage == {
        "MERGE": 5,
        "JSONB data type": 12,
    }


def test_parse_coverage_output_ignores_bad_counts() -> None:
    stdout = "__COVERAGE__|MERGE|not-a-number\n__COVERAGE__|WAL improvements|40"
    coverage = _parse_coverage_output(stdout)
    assert "MERGE" not in coverage
    assert coverage["WAL improvements"] == 40
