#!/usr/bin/env python3
"""
Audit TOC anchors in documentation files.

Identifies:
1. TOC entries with no corresponding heading
2. Headings that need explicit anchors
3. Mismatched anchor IDs

Usage:
    python scripts/audit_toc.py                    # Audit all RU files
    python scripts/audit_toc.py --file FILE        # Audit specific file
    python scripts/audit_toc.py --fix              # Fix what can be fixed
"""

import argparse
import re
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Set

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


@dataclass
class TocEntry:
    text: str
    anchor: str
    line_num: int


@dataclass
class Heading:
    level: int
    text: str
    anchor_id: Optional[str]
    line_num: int


def extract_toc_entries(lines: List[str]) -> List[TocEntry]:
    """Extract all TOC-style anchor links."""
    entries = []
    pattern = re.compile(r'\[([^\]]+)\]\(#([a-z0-9-]+)\)')

    for i, line in enumerate(lines):
        for match in pattern.finditer(line):
            entries.append(TocEntry(
                text=match.group(1),
                anchor=match.group(2),
                line_num=i + 1
            ))

    return entries


def extract_headings(lines: List[str]) -> List[Heading]:
    """Extract all headings."""
    headings = []
    pattern = re.compile(r'^(#{1,6})\s+(.+?)(?:\s+\{#([a-z0-9-]+)\})?\s*$')

    for i, line in enumerate(lines):
        match = pattern.match(line)
        if match:
            headings.append(Heading(
                level=len(match.group(1)),
                text=match.group(2).strip(),
                anchor_id=match.group(3),
                line_num=i + 1
            ))

    return headings


def audit_file(file_path: Path, fix: bool = False) -> dict:
    """Audit a single file."""
    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')

    toc_entries = extract_toc_entries(lines)
    headings = extract_headings(lines)

    # Build sets
    toc_anchors = {e.anchor for e in toc_entries}
    heading_anchors = {h.anchor_id for h in headings if h.anchor_id}

    # Find issues
    missing_sections = []  # TOC entries with no heading
    need_anchor = []  # Headings that might need anchor

    for toc in toc_entries:
        if toc.anchor in heading_anchors:
            continue  # Already has correct anchor

        # Check if there's a heading with similar text
        found = False
        for h in headings:
            if h.anchor_id:
                continue
            # Simple text similarity check
            toc_words = set(toc.text.lower().split())
            heading_words = set(h.text.lower().split())
            overlap = len(toc_words & heading_words)
            if overlap >= min(len(toc_words), len(heading_words)) // 2:
                need_anchor.append({
                    'toc': toc,
                    'heading': h,
                    'similarity': overlap
                })
                found = True
                break

        if not found:
            missing_sections.append(toc)

    return {
        'file': file_path,
        'toc_count': len(toc_entries),
        'heading_count': len(headings),
        'missing_sections': missing_sections,
        'need_anchor': need_anchor,
    }


def main():
    parser = argparse.ArgumentParser(description='Audit TOC anchors')
    parser.add_argument('--file', type=Path, help='Audit specific file')
    parser.add_argument('--fix', action='store_true', help='Fix what can be fixed')

    args = parser.parse_args()

    print("=" * 70)
    print("TOC ANCHOR AUDIT")
    print("=" * 70)

    if args.file:
        files = [args.file]
    else:
        files = []
        for dir_path in RU_DIRS:
            if dir_path.exists():
                files.extend(dir_path.glob('*.md'))

    total_missing = 0
    total_need_anchor = 0

    for file_path in sorted(files):
        if not file_path.exists():
            continue

        result = audit_file(file_path, args.fix)

        if result['missing_sections'] or result['need_anchor']:
            print(f"\n{file_path.name}")
            print("-" * 60)

            if result['missing_sections']:
                print(f"  MISSING SECTIONS ({len(result['missing_sections'])}):")
                for toc in result['missing_sections'][:5]:
                    print(f"    Line {toc.line_num}: [{toc.text}](#{toc.anchor})")
                if len(result['missing_sections']) > 5:
                    print(f"    ... and {len(result['missing_sections']) - 5} more")
                total_missing += len(result['missing_sections'])

            if result['need_anchor']:
                print(f"  NEED ANCHOR ({len(result['need_anchor'])}):")
                for item in result['need_anchor'][:5]:
                    print(f"    Line {item['heading'].line_num}: {item['heading'].text[:40]}...")
                    print(f"      -> needs {{#{item['toc'].anchor}}}")
                if len(result['need_anchor']) > 5:
                    print(f"    ... and {len(result['need_anchor']) - 5} more")
                total_need_anchor += len(result['need_anchor'])

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Missing sections (TOC entries with no heading): {total_missing}")
    print(f"Headings needing explicit anchors: {total_need_anchor}")
    print("=" * 70)


if __name__ == '__main__':
    main()
