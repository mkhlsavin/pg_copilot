#!/usr/bin/env python3
"""
Extract Russian documentation from HTML files to Markdown.

This script parses HTML documentation files from docs/landing/docs/ru/
and extracts the content back to Markdown format for the bilingual
documentation workflow.

Features:
    - Extracts content from <article class="doc-content">
    - Converts HTML back to Markdown (headings, code blocks, lists, links)
    - Filters out mock translations (files with [RU] prefix in headings)
    - Preserves proper Russian translations

Usage:
    python scripts/extract_ru_from_html.py                    # Extract all
    python scripts/extract_ru_from_html.py --section guides   # Extract specific section
    python scripts/extract_ru_from_html.py --dry-run          # Preview without writing
    python scripts/extract_ru_from_html.py --check-mock       # Show which files are mock
"""

import argparse
import html
import logging
import re
import sys
from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass

try:
    from bs4 import BeautifulSoup, NavigableString, Tag
except ImportError:
    print("Error: beautifulsoup4 is required. Install with: pip install beautifulsoup4")
    sys.exit(1)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_ROOT = PROJECT_ROOT / "docs"
HTML_ROOT = DOCS_ROOT / "landing" / "docs" / "ru"

# Sections to process
SECTIONS = ["getting-started", "guides", "api", "integrations", "reference"]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


@dataclass
class ExtractResult:
    """Result of extracting content from HTML."""
    filename: str
    section: str
    title: str
    content: str
    is_mock: bool
    has_russian_content: bool


def detect_mock_translation(content: str, title: str) -> bool:
    """
    Detect if content is a mock translation (has [RU] prefixes).

    Mock translations have patterns like:
    - [RU] in title
    - <!-- TODO: Перевести этот документ -->
    - Headings with [RU] prefix
    """
    # Check title
    if title and '[RU]' in title:
        return True

    # Check for TODO marker
    if '<!-- TODO: Перевести этот документ -->' in content:
        return True

    # Check for [RU] in headings (more than 2 indicates mock)
    ru_prefix_count = len(re.findall(r'\[RU\]\s+', content))
    if ru_prefix_count > 2:
        return True

    return False


def has_cyrillic_content(text: str) -> bool:
    """Check if text has substantial Cyrillic (Russian) content."""
    # Remove code blocks and technical terms
    clean_text = re.sub(r'```[\s\S]*?```', '', text)
    clean_text = re.sub(r'`[^`]+`', '', clean_text)

    cyrillic_chars = len(re.findall(r'[а-яА-ЯёЁ]', clean_text))
    latin_chars = len(re.findall(r'[a-zA-Z]', clean_text))

    total = cyrillic_chars + latin_chars
    if total == 0:
        return False

    # Consider it Russian if >20% Cyrillic
    return cyrillic_chars / total > 0.2


def html_to_markdown(soup: BeautifulSoup) -> str:
    """
    Convert BeautifulSoup parsed HTML to Markdown.

    Handles:
    - Headings (h1-h6)
    - Code blocks (with syntax highlighting)
    - Lists (ordered and unordered)
    - Links
    - Bold, italic
    - Blockquotes
    - Tables
    """

    def process_element(element) -> str:
        """Recursively process an HTML element to Markdown."""
        if isinstance(element, NavigableString):
            text = str(element)
            # Normalize whitespace but preserve structure
            return text

        if not isinstance(element, Tag):
            return ''

        tag = element.name

        # Skip certain elements
        if tag in ['script', 'style', 'nav', 'aside']:
            return ''

        # Headings
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(tag[1])
            text = element.get_text(strip=True)
            # Remove anchor links
            text = re.sub(r'\s*¶\s*$', '', text)
            return f"\n{'#' * level} {text}\n"

        # Code blocks
        if tag == 'div' and 'highlight' in element.get('class', []):
            pre = element.find('pre')
            if pre:
                code = pre.get_text()
                # Try to detect language from class
                code_elem = pre.find('code')
                lang = ''
                if code_elem:
                    classes = code_elem.get('class', [])
                    for cls in classes:
                        if cls.startswith('language-'):
                            lang = cls.replace('language-', '')
                            break
                # If no language found, try from highlight class
                if not lang:
                    for cls in element.get('class', []):
                        if cls not in ['highlight', 'codehilite']:
                            lang = cls
                            break
                return f"\n```{lang}\n{code.strip()}\n```\n"

        # Pre/code (inline or block)
        if tag == 'pre':
            code_elem = element.find('code')
            if code_elem:
                return f"\n```\n{code_elem.get_text().strip()}\n```\n"
            return f"\n```\n{element.get_text().strip()}\n```\n"

        if tag == 'code':
            text = element.get_text()
            # If it's short and inline, use backticks
            if '\n' not in text and len(text) < 100:
                return f"`{text}`"
            return f"\n```\n{text}\n```\n"

        # Lists
        if tag == 'ul':
            items = []
            for li in element.find_all('li', recursive=False):
                item_text = process_children(li).strip()
                items.append(f"- {item_text}")
            return '\n' + '\n'.join(items) + '\n'

        if tag == 'ol':
            items = []
            for i, li in enumerate(element.find_all('li', recursive=False), 1):
                item_text = process_children(li).strip()
                items.append(f"{i}. {item_text}")
            return '\n' + '\n'.join(items) + '\n'

        # Links
        if tag == 'a':
            href = element.get('href', '')
            text = element.get_text(strip=True)
            if href and text:
                # Convert .html to .md for internal links
                if href.endswith('.html') and not href.startswith(('http://', 'https://')):
                    href = href.replace('.html', '.md')
                return f"[{text}]({href})"
            return text

        # Bold
        if tag in ['strong', 'b']:
            text = process_children(element)
            return f"**{text.strip()}**"

        # Italic
        if tag in ['em', 'i']:
            text = process_children(element)
            return f"*{text.strip()}*"

        # Blockquote
        if tag == 'blockquote':
            text = process_children(element)
            lines = text.strip().split('\n')
            return '\n' + '\n'.join(f"> {line}" for line in lines) + '\n'

        # Paragraphs
        if tag == 'p':
            text = process_children(element)
            return f"\n{text.strip()}\n"

        # Tables
        if tag == 'table':
            return process_table(element)

        # Divs and other containers - process children
        if tag in ['div', 'span', 'article', 'section', 'main']:
            return process_children(element)

        # Line breaks
        if tag == 'br':
            return '\n'

        # Horizontal rule
        if tag == 'hr':
            return '\n---\n'

        # Default: process children
        return process_children(element)

    def process_children(element) -> str:
        """Process all children of an element."""
        result = []
        for child in element.children:
            result.append(process_element(child))
        return ''.join(result)

    def process_table(table) -> str:
        """Convert HTML table to Markdown table."""
        rows = []
        headers = []

        # Process header
        thead = table.find('thead')
        if thead:
            for th in thead.find_all('th'):
                headers.append(th.get_text(strip=True))

        # Process body
        tbody = table.find('tbody') or table
        for tr in tbody.find_all('tr'):
            cells = []
            for td in tr.find_all(['td', 'th']):
                cells.append(td.get_text(strip=True))
            if cells:
                if not headers and tr.find('th'):
                    headers = cells
                else:
                    rows.append(cells)

        if not headers and rows:
            headers = rows.pop(0)

        if not headers:
            return ''

        # Build markdown table
        result = ['', '| ' + ' | '.join(headers) + ' |']
        result.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')
        for row in rows:
            # Pad row if necessary
            while len(row) < len(headers):
                row.append('')
            result.append('| ' + ' | '.join(row) + ' |')
        result.append('')

        return '\n'.join(result)

    return process_element(soup)


def extract_from_html(html_path: Path) -> Optional[ExtractResult]:
    """
    Extract Markdown content from an HTML documentation file.

    Args:
        html_path: Path to HTML file

    Returns:
        ExtractResult or None if extraction failed
    """
    try:
        html_content = html_path.read_text(encoding='utf-8')
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find main content article
        article = soup.find('article', class_='doc-content')
        if not article:
            logger.warning(f"No article.doc-content found in {html_path}")
            return None

        # Extract title from h1 or page title
        title = ''
        h1 = article.find('h1')
        if h1:
            title = h1.get_text(strip=True)
            # Remove anchor
            title = re.sub(r'\s*¶\s*$', '', title)
        else:
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
                # Clean up "- CodeGraph Documentation" suffix
                title = re.sub(r'\s*-\s*CodeGraph.*$', '', title)

        # Convert to Markdown
        markdown = html_to_markdown(article)

        # Clean up markdown
        markdown = clean_markdown(markdown)

        # Detect if this is a mock translation
        is_mock = detect_mock_translation(markdown, title)

        # Check for actual Russian content
        has_russian = has_cyrillic_content(markdown)

        # Determine section from path
        section = html_path.parent.name

        return ExtractResult(
            filename=html_path.stem,
            section=section,
            title=title,
            content=markdown,
            is_mock=is_mock,
            has_russian_content=has_russian,
        )

    except Exception as e:
        logger.error(f"Error extracting {html_path}: {e}")
        return None


def clean_markdown(text: str) -> str:
    """Clean up extracted Markdown."""
    # Remove excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove leading/trailing whitespace from lines (but preserve indentation for code)
    lines = text.split('\n')
    cleaned = []
    in_code_block = False

    for line in lines:
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            cleaned.append(line)
        elif in_code_block:
            cleaned.append(line)  # Preserve as-is in code blocks
        else:
            cleaned.append(line.rstrip())

    text = '\n'.join(cleaned)

    # Ensure file starts with title
    text = text.lstrip('\n')

    # Ensure file ends with single newline
    text = text.rstrip() + '\n'

    return text


def save_markdown(result: ExtractResult, output_dir: Path, dry_run: bool = False):
    """
    Save extracted Markdown to file.

    Args:
        result: Extraction result
        output_dir: Base output directory (docs/)
        dry_run: If True, only print what would be done
    """
    # Determine output path
    section_dir = output_dir / result.section / 'ru'
    output_file = section_dir / f"{result.filename}.md"

    if dry_run:
        logger.info(f"Would write: {output_file}")
        logger.info(f"  Title: {result.title}")
        logger.info(f"  Content length: {len(result.content)} chars")
        logger.info(f"  Is mock: {result.is_mock}")
        return

    # Create directory if needed
    section_dir.mkdir(parents=True, exist_ok=True)

    # Write file
    output_file.write_text(result.content, encoding='utf-8')
    logger.info(f"Wrote: {output_file}")


def process_section(section: str, dry_run: bool = False, check_mock: bool = False) -> Tuple[int, int, int]:
    """
    Process all HTML files in a section.

    Args:
        section: Section name (e.g., 'guides')
        dry_run: If True, only preview
        check_mock: If True, just report mock status

    Returns:
        Tuple of (total, extracted, skipped_mock)
    """
    section_path = HTML_ROOT / section
    if not section_path.exists():
        logger.warning(f"Section not found: {section_path}")
        return (0, 0, 0)

    total = 0
    extracted = 0
    skipped_mock = 0

    for html_file in section_path.glob('*.html'):
        if html_file.name == 'index.html':
            continue  # Skip index files

        total += 1
        result = extract_from_html(html_file)

        if result is None:
            continue

        if check_mock:
            status = "MOCK" if result.is_mock else "REAL"
            ru_status = "RU+" if result.has_russian_content else "RU-"
            logger.info(f"[{status}] [{ru_status}] {section}/{result.filename}: {result.title[:50]}")
            continue

        if result.is_mock:
            logger.info(f"Skipping mock translation: {result.filename}")
            skipped_mock += 1
            continue

        if not result.has_russian_content:
            logger.info(f"Skipping (no Russian content): {result.filename}")
            skipped_mock += 1
            continue

        save_markdown(result, DOCS_ROOT, dry_run)
        extracted += 1

    return (total, extracted, skipped_mock)


def main():
    parser = argparse.ArgumentParser(
        description='Extract Russian documentation from HTML to Markdown',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/extract_ru_from_html.py                    # Extract all sections
  python scripts/extract_ru_from_html.py --section guides   # Extract only guides
  python scripts/extract_ru_from_html.py --dry-run          # Preview without writing
  python scripts/extract_ru_from_html.py --check-mock       # Show mock status
        """
    )

    parser.add_argument(
        '--section',
        choices=SECTIONS + ['enterprise'],
        help='Process only this section'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without writing files'
    )
    parser.add_argument(
        '--check-mock',
        action='store_true',
        help='Only check and report mock translation status'
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
    logger.info("Extracting Russian documentation from HTML")
    logger.info("=" * 60)

    sections_to_process = [args.section] if args.section else SECTIONS

    total_all = 0
    extracted_all = 0
    skipped_all = 0

    for section in sections_to_process:
        logger.info(f"\nProcessing section: {section}")
        total, extracted, skipped = process_section(
            section,
            dry_run=args.dry_run,
            check_mock=args.check_mock
        )
        total_all += total
        extracted_all += extracted
        skipped_all += skipped

    logger.info("")
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total HTML files:     {total_all}")
    logger.info(f"Extracted to MD:      {extracted_all}")
    logger.info(f"Skipped (mock/empty): {skipped_all}")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
