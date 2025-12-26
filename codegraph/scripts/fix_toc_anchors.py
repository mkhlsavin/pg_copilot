#!/usr/bin/env python3
"""
Fix TOC anchors in Russian documentation files.

This script adds explicit anchor IDs to headings in Russian markdown files
so that TOC links work correctly after HTML generation.

Problem:
- TOC uses English anchors: [Краткий справочник](#quick-reference)
- Heading is Russian: ## Краткий справочник
- Generated HTML id is transliterated: id="kratkiy-spravochnik"
- Result: Broken anchor link

Solution:
Add explicit anchor IDs to headings:
## Краткий справочник {#quick-reference}

Usage:
    python scripts/fix_toc_anchors.py                    # Fix all RU files
    python scripts/fix_toc_anchors.py --dry-run          # Preview changes
    python scripts/fix_toc_anchors.py --check            # Just report issues
"""

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


@dataclass
class TocLink:
    """A link from TOC section."""
    text: str
    anchor: str
    line_num: int


@dataclass
class Heading:
    """A heading in the document."""
    level: int
    text: str
    anchor_id: str  # Existing {#id} if present
    line_num: int
    line_content: str


def extract_toc_links(content: str) -> List[TocLink]:
    """
    Extract all TOC-style links from content.

    Looks for patterns like:
    - [Link text](#anchor-id)
    """
    links = []
    # Match markdown links with anchor references
    pattern = r'\[([^\]]+)\]\(#([a-z0-9-]+)\)'

    for i, line in enumerate(content.split('\n'), 1):
        for match in re.finditer(pattern, line, re.IGNORECASE):
            text = match.group(1)
            anchor = match.group(2)
            links.append(TocLink(text=text, anchor=anchor, line_num=i))

    return links


def extract_headings(content: str) -> List[Heading]:
    """
    Extract all headings from content.

    Handles:
    - ## Heading text
    - ## Heading text {#explicit-id}
    """
    headings = []
    # Match headings with optional {#id}
    pattern = r'^(#{1,6})\s+(.+?)(?:\s+\{#([a-z0-9-]+)\})?\s*$'

    for i, line in enumerate(content.split('\n'), 1):
        match = re.match(pattern, line)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            anchor_id = match.group(3) or ''
            headings.append(Heading(
                level=level,
                text=text,
                anchor_id=anchor_id,
                line_num=i,
                line_content=line
            ))

    return headings


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    # Remove formatting like ** and `
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Normalize whitespace
    text = ' '.join(text.split())
    return text.lower()


def extract_key_terms(text: str) -> Set[str]:
    """Extract key technical terms that should match exactly."""
    terms = set()
    # D3FEND technique IDs
    for match in re.findall(r'd3-[a-z]+', text.lower()):
        terms.add(match)
    # CWE IDs
    for match in re.findall(r'cwe-\d+', text.lower()):
        terms.add(match)
    # Technical terms in parentheses (often English)
    for match in re.findall(r'\(([^)]+)\)', text):
        if re.match(r'^[A-Za-z0-9\s-]+$', match):
            terms.add(match.lower().strip())
    return terms


def word_overlap_score(text1: str, text2: str) -> float:
    """Calculate word overlap (Jaccard-like) between two texts."""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    # Filter out very short words
    words1 = {w for w in words1 if len(w) > 2}
    words2 = {w for w in words2 if len(w) > 2}

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union) if union else 0.0


def find_matching_heading(link: TocLink, headings: List[Heading]) -> Heading | None:
    """
    Find heading that matches a TOC link.

    Matching strategies (in priority order):
    1. Exact text match (normalized) - prefer headings WITHOUT existing anchor
    2. Exact text match (normalized) - headings with existing anchor
    3. Partial match - link text in heading or vice versa
    4. Key term match - D3-xxx, CWE-xxx, technical terms in parentheses
    5. Fuzzy match - high word overlap (>50%)
    """
    link_text = normalize_text(link.text)
    link_terms = extract_key_terms(link.text)

    # Pass 1: Exact match, prefer headings without anchor
    for heading in headings:
        if heading.anchor_id:
            continue  # Skip headings that already have anchor
        heading_text = normalize_text(heading.text)
        if link_text == heading_text:
            return heading

    # Pass 2: Exact match, with anchor (for warnings)
    for heading in headings:
        heading_text = normalize_text(heading.text)
        if link_text == heading_text:
            return heading

    # Pass 3: Partial match, only headings without anchor
    for heading in headings:
        if heading.anchor_id:
            continue
        heading_text = normalize_text(heading.text)
        # Link text in heading
        if link_text in heading_text:
            return heading
        # Heading text in link
        if heading_text in link_text:
            return heading

    # Pass 4: Key term match (D3-xxx, CWE-xxx, etc.)
    if link_terms:
        for heading in headings:
            if heading.anchor_id:
                continue
            heading_terms = extract_key_terms(heading.text)
            if link_terms & heading_terms:  # Any common key terms
                return heading

    # Pass 5: Fuzzy match based on word overlap (>50%)
    best_match = None
    best_score = 0.5  # Minimum threshold

    for heading in headings:
        if heading.anchor_id:
            continue
        heading_text = normalize_text(heading.text)
        score = word_overlap_score(link_text, heading_text)
        if score > best_score:
            best_score = score
            best_match = heading

    return best_match


def fix_file(file_path: Path, dry_run: bool = False, check_only: bool = False) -> Tuple[int, int]:
    """
    Fix TOC anchors in a single file.

    Args:
        file_path: Path to markdown file
        dry_run: If True, only show what would change
        check_only: If True, only report issues without showing fixes

    Returns:
        Tuple of (issues_found, issues_fixed)
    """
    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')

    toc_links = extract_toc_links(content)
    headings = extract_headings(content)

    issues_found = 0
    issues_fixed = 0

    # Build set of anchors that need to be added
    anchors_to_add: Dict[int, str] = {}  # line_num -> anchor

    for link in toc_links:
        # Check if there's already a heading with this exact anchor
        has_anchor = any(h.anchor_id == link.anchor for h in headings)
        if has_anchor:
            continue

        # Find matching heading
        heading = find_matching_heading(link, headings)
        if not heading:
            logger.debug(f"  No matching heading for: [{link.text}](#{link.anchor})")
            continue

        # Check if heading already has a different anchor
        if heading.anchor_id:
            if heading.anchor_id != link.anchor:
                logger.warning(
                    f"  {file_path.name}:{heading.line_num}: "
                    f"Heading has {{{heading.anchor_id}}} but TOC expects #{link.anchor}"
                )
            continue

        # Need to add anchor
        issues_found += 1

        if check_only:
            logger.info(
                f"  {file_path.name}:{heading.line_num}: "
                f"Missing {{#{link.anchor}}} on '{heading.text[:40]}...'"
            )
            continue

        # Record anchor to add
        if heading.line_num not in anchors_to_add:
            anchors_to_add[heading.line_num] = link.anchor
            issues_fixed += 1

    if not anchors_to_add:
        return (issues_found, issues_fixed)

    # Apply fixes
    new_lines = []
    for i, line in enumerate(lines, 1):
        if i in anchors_to_add:
            anchor = anchors_to_add[i]
            # Add {#anchor} before the newline
            if line.rstrip().endswith('}'):
                # Already has an anchor (shouldn't happen, but safety)
                new_lines.append(line)
            else:
                new_line = line.rstrip() + f' {{#{anchor}}}'
                new_lines.append(new_line)
                if not dry_run:
                    logger.info(f"  Fixed: {line.strip()[:50]} -> +{{#{anchor}}}")
                else:
                    logger.info(f"  Would fix: {line.strip()[:50]} -> +{{#{anchor}}}")
        else:
            new_lines.append(line)

    if not dry_run:
        new_content = '\n'.join(new_lines)
        file_path.write_text(new_content, encoding='utf-8')

    return (issues_found, issues_fixed)


def process_directory(dir_path: Path, dry_run: bool = False, check_only: bool = False) -> Tuple[int, int, int]:
    """
    Process all markdown files in a directory.

    Returns:
        Tuple of (files_processed, issues_found, issues_fixed)
    """
    if not dir_path.exists():
        return (0, 0, 0)

    files_processed = 0
    total_issues = 0
    total_fixed = 0

    for md_file in dir_path.glob('*.md'):
        files_processed += 1
        issues, fixed = fix_file(md_file, dry_run, check_only)
        total_issues += issues
        total_fixed += fixed

    # Process subdirectories (like scenarios/)
    for subdir in dir_path.iterdir():
        if subdir.is_dir():
            for md_file in subdir.glob('*.md'):
                files_processed += 1
                issues, fixed = fix_file(md_file, dry_run, check_only)
                total_issues += issues
                total_fixed += fixed

    return (files_processed, total_issues, total_fixed)


def main():
    parser = argparse.ArgumentParser(
        description='Fix TOC anchors in Russian documentation files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/fix_toc_anchors.py                    # Fix all RU files
  python scripts/fix_toc_anchors.py --dry-run          # Preview changes
  python scripts/fix_toc_anchors.py --check            # Just report issues
  python scripts/fix_toc_anchors.py --dir docs/guides/ru  # Fix specific directory
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without writing files'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Only check and report issues'
    )
    parser.add_argument(
        '--dir',
        type=Path,
        help='Process only this directory'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 60)
    logger.info("Fixing TOC anchors in Russian documentation")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("DRY RUN - no files will be modified")
    if args.check:
        logger.info("CHECK MODE - only reporting issues")

    dirs_to_process = [args.dir] if args.dir else RU_DIRS

    total_files = 0
    total_issues = 0
    total_fixed = 0

    for dir_path in dirs_to_process:
        if not dir_path.exists():
            continue

        logger.info(f"\nProcessing: {dir_path.relative_to(PROJECT_ROOT)}")
        files, issues, fixed = process_directory(dir_path, args.dry_run, args.check)
        total_files += files
        total_issues += issues
        total_fixed += fixed

    logger.info("")
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Files processed:  {total_files}")
    logger.info(f"Issues found:     {total_issues}")
    if not args.check:
        logger.info(f"Issues fixed:     {total_fixed}")
    logger.info("=" * 60)

    # Return exit code based on issues
    if args.check and total_issues > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
