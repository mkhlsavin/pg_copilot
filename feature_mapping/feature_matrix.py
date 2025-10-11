from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .models import Feature

FEATURE_MATRIX_URL = "https://www.postgresql.org/about/featurematrix/"
SUPPORTED_CLASSES = {"fm_yes", "fm_obs", "fm_new", "fm_dev"}
FOOTNOTE_RE = re.compile(r"\s*\[\d+]\s*$")
WHITESPACE_RE = re.compile(r"\s+")


class FeatureMatrixError(RuntimeError):
    """Raised when the feature matrix cannot be retrieved or parsed."""


def fetch_feature_matrix(
    url: str = FEATURE_MATRIX_URL,
    *,
    session: Optional[requests.Session] = None,
    timeout: float = 30.0,
) -> List[Feature]:
    """Fetch and parse the PostgreSQL feature matrix for v17."""
    sess = session or requests.Session()
    response = sess.get(url, timeout=timeout)
    if response.status_code != 200:
        raise FeatureMatrixError(f"Failed to fetch feature matrix (status {response.status_code})")
    return parse_feature_matrix(response.text, base_url=url)


def parse_feature_matrix(html: str, *, base_url: str = FEATURE_MATRIX_URL) -> List[Feature]:
    """Parse the feature matrix HTML and return feature entries applicable to v17."""
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.select("table.matrix")
    if not tables:
        raise FeatureMatrixError("Could not locate feature matrix table in HTML.")

    features: List[Feature] = []
    for table in tables:
        version_index = _find_version_index(table, version="17")
        if version_index is None:
            continue
        category = _find_category(table)
        for row in table.select("tbody tr"):
            feature = _parse_row(row, version_index, category, base_url=base_url)
            if feature:
                features.append(feature)
    return features


def _find_version_index(table_tag, *, version: str) -> Optional[int]:
    header_cells = table_tag.select("thead tr th")
    headers = [cell.get_text(strip=True) for cell in header_cells]
    try:
        target_position = headers.index(version)
    except ValueError:
        return None
    # We subtract 1 because the first column (index 0) is the feature name.
    return max(0, target_position - 1)


def _find_category(table_tag) -> Optional[str]:
    previous_heading = table_tag.find_previous(["h2", "h3"])
    if previous_heading:
        return _normalise_text(previous_heading.get_text())
    return None


def _parse_row(row_tag, version_index: int, category: Optional[str], *, base_url: str) -> Optional[Feature]:
    header_cell = row_tag.find("th")
    if not header_cell:
        return None
    feature_name = _clean_feature_name(header_cell.get_text())
    if not feature_name:
        return None
    detail_anchor = header_cell.find("a")
    detail_path = detail_anchor["href"] if detail_anchor and detail_anchor.has_attr("href") else None
    detail_url = urljoin(base_url, detail_path) if detail_path else None
    description = _normalise_text(header_cell.get("title"))

    cells = row_tag.find_all("td")
    if not cells or version_index >= len(cells):
        return None
    cell = cells[version_index]
    classes = set(cell.get("class", []))
    if not (classes & SUPPORTED_CLASSES):
        return None

    return Feature(
        name=feature_name,
        category=category,
        description=description,
        detail_url=detail_url,
    )


def _clean_feature_name(value: str) -> str:
    if not value:
        return ""
    cleaned = FOOTNOTE_RE.sub("", value)
    return _normalise_text(cleaned)


def _normalise_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return WHITESPACE_RE.sub(" ", value).strip()
