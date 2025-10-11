from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Sequence

DEFAULT_STOPWORDS = {
    "the",
    "for",
    "and",
    "of",
    "to",
    "a",
    "an",
    "in",
    "with",
    "on",
    "by",
    "via",
    "from",
    "using",
    "support",
    "enable",
    "adds",
    "add",
    "new",
    "allows",
    "allow",
    "provides",
    "providing",
    "improved",
    "improvement",
    "including",
    "through",
    "are",
    "is",
    "was",
    "were",
    "can",
    "cannot",
    "be",
    "being",
    "been",
    "now",
    "also",
    "into",
    "than",
    "then",
    "up",
    "down",
    "across",
    "before",
    "after",
    "it",
    "its",
    "their",
    "there",
    "within",
    "without",
    "over",
    "where",
    "command",
    "feature",
    "postgresql",
    "database",
    "data",
    "type",
    "types",
    "function",
    "functions",
    "operator",
    "operators",
    "option",
    "options",
}

TOKEN_SPLIT_RE = re.compile(r"[^\w]+", re.UNICODE)

SYNONYM_MAP = {
    "json": {"jsonb"},
    "fts": {"tsearch", "textsearch"},
    "fts2": {"tsvector", "tsquery"},
    "scram": {"auth", "authentication"},
    "parallel": {"worker", "parallelism"},
    "merge": {"mergejoin"},
    "logical": {"wal_sender", "logicalreplication"},
    "hash": {"hashjoin", "hashagg"},
    "wal": {"writeaheadlog", "xlog"},
    "backup": {"basebackup", "pg_basebackup"},
    "replication": {"logicalreplication", "physical"},
    "uuid": {"guid"},
    "encryption": {"ssl", "tls"},
    "vacuum": {"maintenance"},
    "fdw": {"foreign", "data", "wrapper"},
    "monitoring": {"stat", "metrics"},
    "visibility": {"mvcc"},
    "analytics": {"analysis"},
    "planner": {"optimizer"},
}

CATEGORY_HINT_TOKENS = {
    "performance": {"optimizer", "executor"},
    "security": {"auth", "authentication"},
    "replication": {"wal", "logical", "physical"},
    "json": {"json", "jsonb"},
    "index": {"index", "btree", "gist", "gin"},
    "backup": {"backup", "basebackup", "pg_basebackup", "restore"},
    "data integrity": {"checksum", "replica"},
    "client applications": {"client", "bin", "psql"},
    "configuration": {"guc", "config"},
    "custom": {"pl", "trigger"},
    "data definition": {"ddl", "parser", "commands"},
    "data import": {"copy", "fdw", "import"},
    "data types": {"datatype", "types"},
    "extensions": {"extension", "contrib"},
    "foreign data wrappers": {"fdw", "foreign", "wrapper"},
    "internationalisation": {"locale", "encoding", "i18n"},
    "network": {"libpq", "protocol"},
    "partition": {"partition"},
    "platform": {"port", "msvc"},
    "procedural": {"plpgsql", "plpython", "plperl"},
    "sql": {"parser", "commands"},
    "transactions": {"transam", "xlog"},
    "vacuum": {"vacuum"},
    "views": {"view", "rule"},
}

_OVERRIDE_PATH = Path(__file__).with_name("feature_overrides.json")


@dataclass(frozen=True)
class FeatureOverride:
    tokens: tuple[str, ...] = ()
    extra_stopwords: tuple[str, ...] = ()
    directory_hints: tuple[str, ...] = ()


@lru_cache(maxsize=1)
def _load_feature_overrides() -> dict[str, FeatureOverride]:
    if not _OVERRIDE_PATH.exists():
        return {}
    try:
        raw_payload = json.loads(_OVERRIDE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    overrides: dict[str, FeatureOverride] = {}
    for raw_name, config in raw_payload.items():
        if not isinstance(config, dict):
            continue
        tokens = tuple(
            normalise(token)
            for token in config.get("tokens", [])
            if isinstance(token, str) and normalise(token)
        )
        extra_stopwords = tuple(
            normalise(token)
            for token in config.get("extra_stopwords", [])
            if isinstance(token, str) and normalise(token)
        )
        directory_hints = tuple(
            normalise(token)
            for token in config.get("directory_hints", [])
            if isinstance(token, str) and normalise(token)
        )
        overrides[normalise(raw_name)] = FeatureOverride(
            tokens=tokens,
            extra_stopwords=extra_stopwords,
            directory_hints=directory_hints,
        )
    return overrides


EMPTY_OVERRIDE = FeatureOverride()


def normalise(text: str) -> str:
    """Return a lowercase, ASCII-only variant of the input."""
    nfkd = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return without_accents.lower()


def tokenize(text: str, *, extra_stopwords: Iterable[str] | None = None) -> List[str]:
    """Split a string into significant tokens."""
    stopwords = set(DEFAULT_STOPWORDS)
    if extra_stopwords:
        stopwords.update(normalise(sw) for sw in extra_stopwords)
    normalised = normalise(text)
    tokens = [tok for tok in TOKEN_SPLIT_RE.split(normalised) if tok and tok not in stopwords]
    # Remove purely numeric tokens unless they are version numbers like "64-bit"
    clean_tokens = []
    for tok in tokens:
        if tok.isdigit():
            continue
        clean_tokens.append(tok)
    return clean_tokens


def expand_tokens(tokens: Sequence[str], *, category: str | None = None) -> List[str]:
    """Augment tokens with synonyms and category-driven hints."""
    expanded = list(dict.fromkeys(tokens))  # Preserve order while deduplicating
    for token in tokens:
        hints = SYNONYM_MAP.get(token)
        if hints:
            for hint in hints:
                if hint not in expanded:
                    expanded.append(hint)
    if category:
        lowercase_category = normalise(category)
        for key, hints in CATEGORY_HINT_TOKENS.items():
            if key in lowercase_category:
                for hint in hints:
                    if hint not in expanded:
                        expanded.append(hint)
    return expanded


def conjunctive_regex(tokens: Sequence[str]) -> str:
    """Build a regex that requires all tokens to be present (order-insensitive)."""
    escaped = [re.escape(tok) for tok in tokens if tok]
    if not escaped:
        return ".*"
    lookaheads = "".join(f"(?=.*{tok})" for tok in escaped)
    return f"(?i){lookaheads}.*"


@lru_cache(maxsize=1024)
def _token_cache(text: str) -> List[str]:
    return tokenize(text)


def score_text(text: str, tokens: Sequence[str]) -> float:
    """Score how well a piece of text matches the desired tokens."""
    if not tokens:
        return 0.0
    local_tokens = _token_cache(text)
    score = 0.0
    for token in tokens:
        if token in local_tokens:
            score += 1.0
        elif any(token in lt for lt in local_tokens):
            score += 0.5
    return score / len(tokens)


def score_path(path: str, tokens: Sequence[str], *, partial_weight: float = 0.35) -> float:
    """Score how well a filesystem path aligns with tokens via directory segments."""
    if not path or not tokens:
        return 0.0
    normalised_path = normalise(path)
    segments = [seg for seg in re.split(r"[\\/]+", normalised_path) if seg]
    if not segments:
        segments = [normalised_path]
    score = 0.0
    for token in tokens:
        if any(token == segment for segment in segments):
            score += 1.0
        elif any(token in segment for segment in segments):
            score += partial_weight
    return score / len(tokens)


def combine_scores(*scores: float) -> float:
    """Combine multiple partial scores into a single heuristic value."""
    if not scores:
        return 0.0
    weighted = [s for s in scores if s]
    if not weighted:
        return 0.0
    return sum(weighted) / len(weighted)


def feature_override_for(feature_name: str) -> FeatureOverride:
    """Return optional overrides for a feature."""
    if not feature_name:
        return EMPTY_OVERRIDE
    overrides = _load_feature_overrides()
    return overrides.get(normalise(feature_name), EMPTY_OVERRIDE)
