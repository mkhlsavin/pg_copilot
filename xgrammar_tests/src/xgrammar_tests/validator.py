from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(slots=True)
class ValidationResult:
    query: str
    valid: bool
    issues: List[str]

    def raise_for_errors(self) -> None:
        if not self.valid:
            raise ValueError("; ".join(self.issues))


def validate_query(query: str) -> ValidationResult:
    issues: List[str] = []
    stripped = query.strip()

    if not stripped:
        issues.append("Query is empty.")

    if not stripped.startswith("cpg"):
        issues.append("Query must start with the root object `cpg`.")

    if ".." in stripped:
        issues.append("Query contains consecutive dots (`..`).")

    if stripped.count("(") != stripped.count(")"):
        issues.append("Parentheses are unbalanced.")

    if stripped.count("[") != stripped.count("]"):
        issues.append("Square brackets are unbalanced.")

    return ValidationResult(query=query, valid=not issues, issues=issues)
