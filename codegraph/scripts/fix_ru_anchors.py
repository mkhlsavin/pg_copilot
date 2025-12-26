#!/usr/bin/env python3
"""
Fix Russian documentation anchors.

This script:
1. Transliterates Cyrillic anchors in TOC to match _slugify() from converter.py
2. Replaces "Table of Contents" with "Содержание" in Russian docs
"""

import re
import sys
from pathlib import Path

# Same transliteration map as in converter.py
TRANSLIT_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
}


def slugify(value: str, separator: str = '-') -> str:
    """
    Create a slug from a heading text (same as converter.py).
    """
    value = value.lower()

    result = []
    for char in value:
        if char in TRANSLIT_MAP:
            result.append(TRANSLIT_MAP[char])
        elif char.isalnum():
            result.append(char)
        elif char in ' _-':
            result.append(separator)

    slug = ''.join(result)
    slug = re.sub(f'{separator}+', separator, slug)
    slug = slug.strip(separator)

    return slug


def has_cyrillic(text: str) -> bool:
    """Check if text contains Cyrillic characters."""
    return bool(re.search('[а-яё]', text, re.IGNORECASE))


def fix_anchor(match: re.Match) -> str:
    """Fix a single anchor by transliterating it."""
    prefix = match.group(1)  # ](#
    anchor = match.group(2)  # the anchor text
    suffix = match.group(3)  # )

    if has_cyrillic(anchor):
        new_anchor = slugify(anchor)
        return f'{prefix}{new_anchor}{suffix}'
    return match.group(0)


def fix_file(filepath: Path, dry_run: bool = False) -> tuple[int, int]:
    """
    Fix anchors in a single file.

    Returns:
        Tuple of (anchors_fixed, toc_fixed)
    """
    content = filepath.read_text(encoding='utf-8')
    original = content

    # Fix anchors: [text](#cyrillic-anchor) -> [text](#transliterated-anchor)
    # Pattern matches: ](#anchor) where anchor may contain Cyrillic
    pattern = r'(\]\(#)([^)]+)(\))'
    content, anchors_fixed = re.subn(pattern, fix_anchor, content)

    # Fix "Table of Contents" -> "Содержание"
    toc_fixed = 0
    if '## Table of Contents' in content:
        content = content.replace('## Table of Contents', '## Содержание')
        toc_fixed = 1

    if content != original and not dry_run:
        filepath.write_text(content, encoding='utf-8')

    return anchors_fixed, toc_fixed


def main():
    dry_run = '--dry-run' in sys.argv

    # Files to process
    files = [
        # enterprise/ru/
        "docs/enterprise/ru/COMPETITIVE_MATRIX.md",
        "docs/enterprise/ru/DEPLOYMENT_GUIDE.md",
        "docs/enterprise/ru/DLP_SECURITY.md",
        "docs/enterprise/ru/HYPOTHESIS_WHITEPAPER.md",
        "docs/enterprise/ru/LLM_SECURITY.md",
        "docs/enterprise/ru/RBAC.md",
        "docs/enterprise/ru/SECURITY_BRIEF.md",
        "docs/enterprise/ru/SIEM.md",
        # getting-started/ru/
        "docs/getting-started/ru/CONFIGURATION.md",
        "docs/getting-started/ru/INSTALLATION.md",
        "docs/getting-started/ru/README.md",
        # guides/ru/
        "docs/guides/ru/BENCHMARK_GUIDE.md",
        "docs/guides/ru/CODE_REVIEW.md",
        "docs/guides/ru/CPG_EXPORT.md",
        "docs/guides/ru/PROGRAMMATIC_GUIDE.md",
        "docs/guides/ru/PROJECT_IMPORT.md",
        "docs/guides/ru/REFACTORING.md",
        "docs/guides/ru/SCENARIOS.md",
        "docs/guides/ru/TROUBLESHOOTING.md",
        "docs/guides/ru/TUI_USER_GUIDE.md",
        # sber500/ru/
        "docs/sber500/ru/BUSINESS_CASE.md",
        "docs/sber500/ru/DEMO_SCRIPT.md",
        "docs/sber500/ru/PITCH_DECK.md",
        "docs/sber500/ru/TECHNICAL_INTEGRATION.md",
    ]

    project_root = Path(__file__).parent.parent

    total_anchors = 0
    total_toc = 0

    print(f"{'[DRY RUN] ' if dry_run else ''}Fixing Russian documentation anchors...")
    print("-" * 60)

    for rel_path in files:
        filepath = project_root / rel_path
        if not filepath.exists():
            print(f"  SKIP: {rel_path} (not found)")
            continue

        anchors, toc = fix_file(filepath, dry_run)
        total_anchors += anchors
        total_toc += toc

        if anchors > 0 or toc > 0:
            print(f"  FIXED: {rel_path}")
            if anchors > 0:
                print(f"         - {anchors} anchor(s) transliterated")
            if toc > 0:
                print(f"         - TOC header renamed to 'Содержание'")
        else:
            print(f"  OK: {rel_path} (no changes needed)")

    print("-" * 60)
    print(f"Total: {total_anchors} anchors fixed, {total_toc} TOC headers renamed")

    if dry_run:
        print("\n[DRY RUN] No files were modified. Run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
