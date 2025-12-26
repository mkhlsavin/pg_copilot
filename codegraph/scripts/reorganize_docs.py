#!/usr/bin/env python3
"""
Reorganize documentation folder structure for bilingual support.

This script creates en/ and ru/ subdirectories in each documentation section
and moves English markdown files to the en/ subdirectory.

Before:
    docs/guides/
    ├── TUI_USER_GUIDE.md
    ├── CLI_GUIDE.md
    └── scenarios/
        └── 01-onboarding.md

After:
    docs/guides/
    ├── en/
    │   ├── TUI_USER_GUIDE.md
    │   ├── CLI_GUIDE.md
    │   └── scenarios/
    │       └── 01-onboarding.md
    └── ru/
        └── (empty, to be populated)

Usage:
    python scripts/reorganize_docs.py                    # Reorganize all sections
    python scripts/reorganize_docs.py --section guides   # Reorganize specific section
    python scripts/reorganize_docs.py --dry-run          # Preview without changes
    python scripts/reorganize_docs.py --revert           # Revert changes
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path
from typing import List, Tuple

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_ROOT = PROJECT_ROOT / "docs"

# Sections to reorganize (enterprise and sber500 already have en/ru structure)
SECTIONS_TO_REORGANIZE = [
    "getting-started",
    "guides",
    "api",
    "integrations",
    "reference",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def get_md_files(section_path: Path) -> List[Path]:
    """Get all markdown files in a section (excluding en/ru subdirs)."""
    md_files = []

    for item in section_path.iterdir():
        # Skip en/ru directories if they exist
        if item.is_dir() and item.name in ['en', 'ru']:
            continue

        if item.is_file() and item.suffix == '.md':
            md_files.append(item)
        elif item.is_dir():
            # Handle subdirectories like scenarios/
            for md_file in item.rglob('*.md'):
                md_files.append(md_file)

    return md_files


def check_section_status(section_path: Path) -> Tuple[bool, bool, int]:
    """
    Check the current status of a section.

    Returns:
        Tuple of (has_en_dir, has_ru_dir, md_files_in_root)
    """
    en_dir = section_path / 'en'
    ru_dir = section_path / 'ru'

    has_en = en_dir.exists() and en_dir.is_dir()
    has_ru = ru_dir.exists() and ru_dir.is_dir()

    # Count MD files not in en/ru
    md_count = 0
    for item in section_path.iterdir():
        if item.is_dir() and item.name in ['en', 'ru']:
            continue
        if item.is_file() and item.suffix == '.md':
            md_count += 1
        elif item.is_dir():
            md_count += len(list(item.rglob('*.md')))

    return (has_en, has_ru, md_count)


def reorganize_section(section_name: str, dry_run: bool = False) -> bool:
    """
    Reorganize a documentation section to have en/ru structure.

    Args:
        section_name: Name of the section (e.g., 'guides')
        dry_run: If True, only preview changes

    Returns:
        True if successful
    """
    section_path = DOCS_ROOT / section_name

    if not section_path.exists():
        logger.warning(f"Section not found: {section_path}")
        return False

    has_en, has_ru, md_in_root = check_section_status(section_path)

    logger.info(f"Section: {section_name}")
    logger.info(f"  Has en/: {has_en}")
    logger.info(f"  Has ru/: {has_ru}")
    logger.info(f"  MD files in root: {md_in_root}")

    # If already has en/ and no MD in root, skip
    if has_en and md_in_root == 0:
        logger.info(f"  Already reorganized, skipping")
        return True

    # Create en/ and ru/ directories
    en_dir = section_path / 'en'
    ru_dir = section_path / 'ru'

    if dry_run:
        logger.info(f"  Would create: {en_dir}")
        logger.info(f"  Would create: {ru_dir}")
    else:
        en_dir.mkdir(exist_ok=True)
        ru_dir.mkdir(exist_ok=True)
        logger.info(f"  Created: {en_dir}")
        logger.info(f"  Created: {ru_dir}")

    # Get files to move
    md_files = get_md_files(section_path)

    for md_file in md_files:
        # Calculate relative path from section
        rel_path = md_file.relative_to(section_path)

        # New path under en/
        new_path = en_dir / rel_path

        if dry_run:
            logger.info(f"  Would move: {rel_path} -> en/{rel_path}")
        else:
            # Create parent directories if needed
            new_path.parent.mkdir(parents=True, exist_ok=True)

            # Move file
            shutil.move(str(md_file), str(new_path))
            logger.info(f"  Moved: {rel_path} -> en/{rel_path}")

    # Clean up empty directories in root (not en/ru)
    if not dry_run:
        for item in section_path.iterdir():
            if item.is_dir() and item.name not in ['en', 'ru']:
                # Check if empty
                if not any(item.iterdir()):
                    item.rmdir()
                    logger.info(f"  Removed empty dir: {item.name}")
                else:
                    # Move entire directory to en/
                    new_path = en_dir / item.name
                    if not new_path.exists():
                        shutil.move(str(item), str(new_path))
                        logger.info(f"  Moved dir: {item.name} -> en/{item.name}")

    return True


def revert_section(section_name: str, dry_run: bool = False) -> bool:
    """
    Revert a section from en/ru structure back to flat.

    Args:
        section_name: Name of the section
        dry_run: If True, only preview changes

    Returns:
        True if successful
    """
    section_path = DOCS_ROOT / section_name
    en_dir = section_path / 'en'

    if not en_dir.exists():
        logger.info(f"No en/ directory in {section_name}, nothing to revert")
        return True

    # Move all files from en/ back to root
    for item in en_dir.iterdir():
        if item.is_file():
            dest = section_path / item.name
            if dry_run:
                logger.info(f"  Would move: en/{item.name} -> {item.name}")
            else:
                shutil.move(str(item), str(dest))
                logger.info(f"  Moved: en/{item.name} -> {item.name}")
        elif item.is_dir():
            dest = section_path / item.name
            if dry_run:
                logger.info(f"  Would move dir: en/{item.name} -> {item.name}")
            else:
                shutil.move(str(item), str(dest))
                logger.info(f"  Moved dir: en/{item.name} -> {item.name}")

    # Remove en/ and ru/ directories if empty
    if not dry_run:
        ru_dir = section_path / 'ru'
        if en_dir.exists() and not any(en_dir.iterdir()):
            en_dir.rmdir()
            logger.info(f"  Removed: en/")
        if ru_dir.exists() and not any(ru_dir.iterdir()):
            ru_dir.rmdir()
            logger.info(f"  Removed: ru/")

    return True


def show_status():
    """Show current status of all sections."""
    logger.info("=" * 60)
    logger.info("Documentation Structure Status")
    logger.info("=" * 60)

    for section in SECTIONS_TO_REORGANIZE + ['enterprise', 'sber500']:
        section_path = DOCS_ROOT / section
        if not section_path.exists():
            logger.info(f"{section}: NOT FOUND")
            continue

        has_en, has_ru, md_in_root = check_section_status(section_path)

        if has_en and has_ru and md_in_root == 0:
            status = "READY (has en/ and ru/)"
        elif has_en and md_in_root > 0:
            status = f"PARTIAL ({md_in_root} MD files still in root)"
        else:
            status = f"NEEDS REORGANIZATION ({md_in_root} MD files in root)"

        logger.info(f"{section}: {status}")

    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Reorganize docs folders for bilingual structure',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/reorganize_docs.py                    # Reorganize all
  python scripts/reorganize_docs.py --section guides   # Reorganize guides only
  python scripts/reorganize_docs.py --dry-run          # Preview changes
  python scripts/reorganize_docs.py --status           # Show current status
  python scripts/reorganize_docs.py --revert           # Undo reorganization
        """
    )

    parser.add_argument(
        '--section',
        choices=SECTIONS_TO_REORGANIZE,
        help='Process only this section'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying files'
    )
    parser.add_argument(
        '--revert',
        action='store_true',
        help='Revert changes (move files from en/ back to root)'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show current reorganization status'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.status:
        show_status()
        return

    sections = [args.section] if args.section else SECTIONS_TO_REORGANIZE

    logger.info("=" * 60)
    if args.revert:
        logger.info("Reverting documentation reorganization")
    else:
        logger.info("Reorganizing documentation for bilingual structure")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("DRY RUN - No files will be modified")
        logger.info("")

    success_count = 0
    for section in sections:
        logger.info("")
        if args.revert:
            if revert_section(section, dry_run=args.dry_run):
                success_count += 1
        else:
            if reorganize_section(section, dry_run=args.dry_run):
                success_count += 1

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Processed {success_count}/{len(sections)} sections")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
