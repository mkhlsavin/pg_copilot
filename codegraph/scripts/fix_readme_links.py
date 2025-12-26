#!/usr/bin/env python3
"""
Fix links in section README files.

Issues:
1. ./en/ and ./ru/ links don't work in generated HTML (duplicate language switcher)
2. ./en/FILE.md links should be en/FILE.md
3. ../section/en/FILE.md should be ../section/FILE.md (for cross-section links)

This script removes the Languages section and fixes relative links.
"""

import re
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DOCS_ROOT = PROJECT_ROOT / "docs"

# README files to fix
README_FILES = [
    DOCS_ROOT / "api" / "README.md",
    DOCS_ROOT / "guides" / "README.md",
    DOCS_ROOT / "getting-started" / "README.md",
    DOCS_ROOT / "enterprise" / "README.md",
    DOCS_ROOT / "integrations" / "README.md",
    DOCS_ROOT / "reference" / "README.md",
    # RU README files
    DOCS_ROOT / "api" / "ru" / "README.md",
    DOCS_ROOT / "guides" / "ru" / "README.md",
    DOCS_ROOT / "getting-started" / "ru" / "README.md",
    DOCS_ROOT / "enterprise" / "ru" / "README.md",
    DOCS_ROOT / "integrations" / "ru" / "README.md",
    DOCS_ROOT / "reference" / "ru" / "README.md",
]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def fix_readme(file_path: Path) -> int:
    """
    Fix links in a README file.

    Returns number of fixes applied.
    """
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return 0

    content = file_path.read_text(encoding='utf-8')
    original = content
    fixes = 0

    # 1. Remove Languages section (matches English and Russian versions)
    languages_patterns = [
        r'\n## Languages\n\n(?:- \[[^\]]+\]\([^\)]+\)[^\n]*\n)+',
        r'\n## Языки\n\n(?:- \[[^\]]+\]\([^\)]+\)[^\n]*\n)+',
    ]
    for lang_pattern in languages_patterns:
        if re.search(lang_pattern, content):
            content = re.sub(lang_pattern, '\n', content)
            fixes += 1
            logger.info(f"  Removed Languages/Языки section")

    # 2. Fix ./en/FILE.md -> en/FILE.md
    pattern1 = r'\]\(\./en/([^)]+)\)'
    matches1 = re.findall(pattern1, content)
    if matches1:
        content = re.sub(pattern1, r'](en/\1)', content)
        fixes += len(matches1)
        logger.info(f"  Fixed {len(matches1)} ./en/ links")

    # 3. Fix ./ru/FILE.md -> ru/FILE.md
    pattern2 = r'\]\(\./ru/([^)]+)\)'
    matches2 = re.findall(pattern2, content)
    if matches2:
        content = re.sub(pattern2, r'](ru/\1)', content)
        fixes += len(matches2)
        logger.info(f"  Fixed {len(matches2)} ./ru/ links")

    # 4. Fix cross-section links: ../section/en/FILE.md -> ../section/en/FILE.md
    # These are actually correct for the source structure, but cause issues
    # because the README is copied to both en/ and ru/ in output
    # For now, leave these as-is - they need special handling in build_docs.py

    if content != original:
        file_path.write_text(content, encoding='utf-8')
        logger.info(f"Fixed: {file_path.name}")
    else:
        logger.info(f"No changes: {file_path.name}")

    return fixes


def main():
    logger.info("=" * 60)
    logger.info("Fixing README links")
    logger.info("=" * 60)

    total_fixes = 0

    for readme in README_FILES:
        fixes = fix_readme(readme)
        total_fixes += fixes

    logger.info("")
    logger.info(f"Total fixes applied: {total_fixes}")


if __name__ == '__main__':
    main()
