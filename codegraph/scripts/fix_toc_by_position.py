#!/usr/bin/env python3
"""
Fix TOC anchors by position-based matching.

This script matches TOC entries to headings based on document order,
not text matching. This handles cases where TOC text and heading text
are different translations.

Usage:
    python scripts/fix_toc_by_position.py                    # Fix all RU files
    python scripts/fix_toc_by_position.py --dry-run          # Preview changes
    python scripts/fix_toc_by_position.py --file FILE        # Fix specific file
"""

import argparse
import logging
import re
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Optional

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_ROOT = PROJECT_ROOT / "docs"

# Directories with RU files
RU_DIRS = [
    DOCS_ROOT / "guides" / "ru",
    DOCS_ROOT / "getting-started" / "ru",
    DOCS_ROOT / "enterprise" / "ru",
    DOCS_ROOT / "api" / "ru",
    DOCS_ROOT / "reference" / "ru",
    DOCS_ROOT / "integrations" / "ru",
    DOCS_ROOT / "sber500" / "ru",
]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


@dataclass
class TocEntry:
    """A TOC link with its position."""
    text: str
    anchor: str
    line_num: int
    level: int  # Inferred from indentation


@dataclass
class Heading:
    """A heading in the document."""
    level: int
    text: str
    anchor_id: Optional[str]
    line_num: int


def extract_toc_section(lines: List[str]) -> Tuple[int, int, List[TocEntry]]:
    """
    Extract TOC section from document.

    Returns: (start_line, end_line, entries)
    """
    entries = []
    start_line = -1
    end_line = -1

    # Find TOC start (## Содержание or ## Contents)
    toc_pattern = re.compile(r'^##\s+(Содержание|Contents|Table of Contents)', re.IGNORECASE)

    for i, line in enumerate(lines):
        if toc_pattern.match(line):
            start_line = i
            break

    if start_line < 0:
        return (-1, -1, [])

    # Find TOC entries
    link_pattern = re.compile(r'^(\s*)- \[([^\]]+)\]\(#([a-z0-9-]+)\)')

    for i in range(start_line + 1, len(lines)):
        line = lines[i]

        # Stop at next heading or empty line after entries
        if line.startswith('#') and not entries:
            break
        if line.startswith('#') or (not line.strip() and entries):
            # Check if next non-empty line is a heading
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip():
                    if lines[j].startswith('#'):
                        end_line = i
                        break
                    break
            if end_line > 0:
                break

        match = link_pattern.match(line)
        if match:
            indent = len(match.group(1))
            level = indent // 2 + 1  # 0 spaces = level 1, 2 spaces = level 2, etc.
            entries.append(TocEntry(
                text=match.group(2),
                anchor=match.group(3),
                line_num=i,
                level=level
            ))

    if end_line < 0:
        end_line = start_line + len(entries) + 2

    return (start_line, end_line, entries)


def extract_headings(lines: List[str], after_line: int = 0) -> List[Heading]:
    """Extract all headings after a given line."""
    headings = []
    pattern = re.compile(r'^(#{1,6})\s+(.+?)(?:\s+\{#([a-z0-9-]+)\})?\s*$')

    for i, line in enumerate(lines):
        if i <= after_line:
            continue

        match = pattern.match(line)
        if match:
            headings.append(Heading(
                level=len(match.group(1)),
                text=match.group(2).strip(),
                anchor_id=match.group(3),
                line_num=i
            ))

    return headings


def match_toc_to_headings(toc_entries: List[TocEntry], headings: List[Heading]) -> List[Tuple[TocEntry, Heading]]:
    """
    Match TOC entries to headings by position.

    Strategy:
    1. For each TOC entry, find the next unmatched heading
    2. Prefer headings without existing anchors
    3. Skip headings that already have the correct anchor
    """
    matches = []
    used_headings = set()

    for toc in toc_entries:
        # Check if any heading already has this anchor
        already_has = any(h.anchor_id == toc.anchor for h in headings)
        if already_has:
            continue

        # Find best matching heading
        best = None
        for h in headings:
            if h.line_num in used_headings:
                continue
            if h.anchor_id:  # Skip if already has anchor
                continue

            # Simple heuristic: take the next unmatched heading
            if best is None or h.line_num < best.line_num:
                best = h

        if best:
            matches.append((toc, best))
            used_headings.add(best.line_num)

    return matches


def fix_file(file_path: Path, dry_run: bool = False) -> int:
    """Fix TOC anchors in a single file."""
    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')

    # Extract TOC
    toc_start, toc_end, toc_entries = extract_toc_section(lines)
    if not toc_entries:
        logger.debug(f"  No TOC found in {file_path.name}")
        return 0

    logger.debug(f"  Found {len(toc_entries)} TOC entries")

    # Extract headings after TOC
    headings = extract_headings(lines, toc_end)
    logger.debug(f"  Found {len(headings)} headings")

    # Match TOC to headings
    matches = match_toc_to_headings(toc_entries, headings)

    if not matches:
        logger.debug(f"  No matches needed")
        return 0

    # Apply fixes
    fixes = 0
    for toc, heading in matches:
        # Add anchor to heading
        old_line = lines[heading.line_num]
        new_line = old_line.rstrip() + f' {{#{toc.anchor}}}'

        if dry_run:
            logger.info(f"  Would fix line {heading.line_num + 1}: {old_line[:50]}... -> +{{#{toc.anchor}}}")
        else:
            logger.info(f"  Fixed line {heading.line_num + 1}: {old_line[:50]}... -> +{{#{toc.anchor}}}")
            lines[heading.line_num] = new_line

        fixes += 1

    if not dry_run and fixes > 0:
        new_content = '\n'.join(lines)
        file_path.write_text(new_content, encoding='utf-8')

    return fixes


def main():
    parser = argparse.ArgumentParser(description='Fix TOC anchors by position-based matching')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without writing files')
    parser.add_argument('--file', type=Path, help='Process only this file')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 60)
    logger.info("Fixing TOC anchors by position-based matching")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("DRY RUN - no files will be modified")

    total_fixes = 0
    total_files = 0

    if args.file:
        files = [args.file]
    else:
        files = []
        for dir_path in RU_DIRS:
            if dir_path.exists():
                files.extend(dir_path.glob('*.md'))

    for file_path in files:
        if not file_path.exists():
            continue

        total_files += 1
        logger.info(f"\nProcessing: {file_path.name}")
        fixes = fix_file(file_path, args.dry_run)
        total_fixes += fixes

    logger.info("")
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Files processed: {total_files}")
    logger.info(f"Fixes applied:   {total_fixes}")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
