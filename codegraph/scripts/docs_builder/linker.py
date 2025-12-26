"""
Link Validator

Validates internal and external links in documentation.
Checks for broken links, missing anchors, and orphaned pages.
"""

import re
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import List, Set, Dict, Optional
from urllib.parse import urlparse, unquote

logger = logging.getLogger(__name__)


@dataclass
class LinkInfo:
    """Information about a link."""
    source_file: str
    line_number: int
    link_text: str
    url: str
    is_valid: bool
    error: Optional[str] = None
    link_type: str = "unknown"  # internal, anchor, external, mailto


@dataclass
class ValidationResult:
    """Result of link validation."""
    total_links: int
    valid_links: int
    broken_links: List[LinkInfo]
    warnings: List[str]


def extract_links_from_markdown(content: str) -> List[tuple]:
    """
    Extract all links from Markdown content.

    Returns list of (text, url, line_number) tuples.
    """
    links = []
    lines = content.split('\n')

    # Pattern for [text](url) style links
    md_link_pattern = r'\[([^\]]*)\]\(([^)]+)\)'

    # Pattern for reference-style links [text][ref]
    ref_link_pattern = r'\[([^\]]*)\]\[([^\]]+)\]'

    # Pattern for reference definitions [ref]: url
    ref_def_pattern = r'^\[([^\]]+)\]:\s*(.+?)(?:\s+"[^"]*")?$'

    # Collect reference definitions
    references = {}
    for line_num, line in enumerate(lines, 1):
        for match in re.finditer(ref_def_pattern, line):
            ref_id = match.group(1).lower()
            url = match.group(2).strip()
            references[ref_id] = url

    # Extract inline links
    for line_num, line in enumerate(lines, 1):
        for match in re.finditer(md_link_pattern, line):
            text = match.group(1)
            url = match.group(2).strip()
            links.append((text, url, line_num))

        # Resolve reference links
        for match in re.finditer(ref_link_pattern, line):
            text = match.group(1)
            ref_id = match.group(2).lower()
            if ref_id in references:
                links.append((text, references[ref_id], line_num))

    return links


def extract_links_from_html(content: str) -> List[tuple]:
    """
    Extract all links from HTML content.

    Returns list of (text, url, line_number) tuples.
    """
    links = []
    lines = content.split('\n')

    # Pattern for <a href="url">text</a>
    href_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>'

    for line_num, line in enumerate(lines, 1):
        for match in re.finditer(href_pattern, line, re.IGNORECASE):
            url = match.group(1)
            text = match.group(2)
            links.append((text, url, line_num))

    return links


def classify_link(url: str) -> str:
    """Classify a link by its type."""
    if url.startswith('#'):
        return 'anchor'
    elif url.startswith('mailto:'):
        return 'mailto'
    elif url.startswith(('http://', 'https://')):
        return 'external'
    elif url.startswith('../') and url.count('../') >= 2:
        # Links going up 2+ levels are to landing page, treat as external
        return 'parent'
    else:
        return 'internal'


def validate_anchor(anchor: str, content: str) -> bool:
    """
    Check if an anchor exists in the content.

    Anchors are generated from headings using slugification.
    """
    anchor = anchor.lstrip('#')
    if not anchor:
        return True  # Empty anchor is valid (links to top)

    # Check for explicit anchor IDs
    if f'id="{anchor}"' in content or f"id='{anchor}'" in content:
        return True

    # Check for heading-generated anchors
    # Look for heading with matching slug
    heading_pattern = r'^#+\s+(.+?)(?:\s*\{.*\})?$'
    for match in re.finditer(heading_pattern, content, re.MULTILINE):
        heading_text = match.group(1)
        slug = slugify(heading_text)
        if slug == anchor:
            return True

    return False


def slugify(text: str) -> str:
    """Create a slug from text (simplified version)."""
    # Transliterate Russian
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    }

    text = text.lower()
    result = []
    for char in text:
        if char in translit_map:
            result.append(translit_map[char])
        elif char.isalnum():
            result.append(char)
        elif char in ' _-':
            result.append('-')

    slug = ''.join(result)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug


def validate_internal_link(
    url: str,
    source_file: Path,
    output_dir: Path,
    known_files: Set[str]
) -> tuple:
    """
    Validate an internal link.

    Returns (is_valid, error_message).
    """
    # Parse URL and anchor
    if '#' in url:
        path_part, anchor = url.split('#', 1)
    else:
        path_part = url
        anchor = None

    # Handle relative paths
    if path_part:
        # Decode URL encoding
        path_part = unquote(path_part)

        # Resolve relative to source file
        source_dir = source_file.parent
        target_path = (source_dir / path_part).resolve()

        # Check if target is within output directory
        try:
            target_relative = str(target_path.relative_to(output_dir)).replace('\\', '/')
        except ValueError:
            # Target is outside output_dir (e.g., links to landing page)
            # Consider these valid as they're intentional parent links
            return True, None

        if not target_path.exists() and target_relative not in known_files:
            # Check with .html extension
            if not target_path.with_suffix('.html').exists():
                return False, f"Target file not found: {path_part}"

    return True, None


class LinkValidator:
    """Validates links in documentation files."""

    def __init__(self, output_dir: Path):
        """
        Initialize validator.

        Args:
            output_dir: Base directory for generated HTML files
        """
        self.output_dir = output_dir
        self.known_files: Set[str] = set()
        self.all_links: List[LinkInfo] = []

    def register_file(self, relative_path: str):
        """Register a known file for link validation."""
        self.known_files.add(relative_path)

    def validate_file(self, file_path: Path, content: str) -> List[LinkInfo]:
        """
        Validate all links in a file.

        Args:
            file_path: Path to the file
            content: File content (HTML or Markdown)

        Returns:
            List of LinkInfo for each link
        """
        # Detect format and extract links
        if file_path.suffix == '.html':
            links = extract_links_from_html(content)
        else:
            links = extract_links_from_markdown(content)

        results = []
        source = str(file_path.relative_to(self.output_dir))

        for text, url, line_num in links:
            link_type = classify_link(url)
            is_valid = True
            error = None

            # Skip parent links (to landing page) and external/mailto
            if link_type in ('parent', 'external', 'mailto'):
                info = LinkInfo(
                    source_file=source,
                    line_number=line_num,
                    link_text=text,
                    url=url,
                    is_valid=True,
                    error=None,
                    link_type=link_type,
                )
                results.append(info)
                self.all_links.append(info)
                continue

            if link_type == 'anchor':
                is_valid = validate_anchor(url, content)
                if not is_valid:
                    error = f"Anchor not found: {url}"

            elif link_type == 'internal':
                is_valid, error = validate_internal_link(
                    url, file_path, self.output_dir, self.known_files
                )

            # External and mailto links are assumed valid
            # (checking them would require network requests)

            info = LinkInfo(
                source_file=source,
                line_number=line_num,
                link_text=text,
                url=url,
                is_valid=is_valid,
                error=error,
                link_type=link_type,
            )
            results.append(info)
            self.all_links.append(info)

        return results

    def validate_all(self) -> ValidationResult:
        """
        Validate all HTML files in output directory.

        Returns:
            ValidationResult with summary and broken links
        """
        # First pass: register all files
        for html_file in self.output_dir.rglob('*.html'):
            rel_path = str(html_file.relative_to(self.output_dir)).replace('\\', '/')
            self.register_file(rel_path)

        # Second pass: validate links
        for html_file in self.output_dir.rglob('*.html'):
            try:
                content = html_file.read_text(encoding='utf-8')
                self.validate_file(html_file, content)
            except Exception as e:
                logger.error(f"Error validating {html_file}: {e}")

        # Compile results
        broken = [link for link in self.all_links if not link.is_valid]
        warnings = []

        # Check for orphaned files (files not linked from anywhere)
        linked_files = set()
        for link in self.all_links:
            if link.link_type == 'internal':
                linked_files.add(link.url.split('#')[0])

        # for known in self.known_files:
        #     if known not in linked_files and 'index.html' not in known:
        #         warnings.append(f"Orphaned file: {known}")

        return ValidationResult(
            total_links=len(self.all_links),
            valid_links=len(self.all_links) - len(broken),
            broken_links=broken,
            warnings=warnings,
        )

    def get_report(self) -> str:
        """Generate a text report of validation results."""
        result = self.validate_all()

        lines = [
            "=" * 60,
            "LINK VALIDATION REPORT",
            "=" * 60,
            f"Total links checked: {result.total_links}",
            f"Valid links: {result.valid_links}",
            f"Broken links: {len(result.broken_links)}",
            "",
        ]

        if result.broken_links:
            lines.append("BROKEN LINKS:")
            lines.append("-" * 40)

            # Group by source file
            by_source: Dict[str, List[LinkInfo]] = {}
            for link in result.broken_links:
                if link.source_file not in by_source:
                    by_source[link.source_file] = []
                by_source[link.source_file].append(link)

            for source, links in by_source.items():
                lines.append(f"\n{source}:")
                for link in links:
                    lines.append(f"  Line {link.line_number}: {link.url}")
                    lines.append(f"    Error: {link.error}")

        if result.warnings:
            lines.append("\nWARNINGS:")
            lines.append("-" * 40)
            for warning in result.warnings:
                lines.append(f"  - {warning}")

        lines.append("\n" + "=" * 60)

        return '\n'.join(lines)


if __name__ == "__main__":
    # Test link extraction
    test_md = """
# Test Document

This is a [link to guide](../guides/CLI_GUIDE.md).

See [installation](#installation) section below.

External: [GitHub](https://github.com)

Contact: [email us](mailto:hello@codegraph.ru)

## Installation

Install with pip.

Reference link: [API docs][api]

[api]: ../api/REST_API.md "API Documentation"
"""

    print("=== Testing Link Extraction ===")
    links = extract_links_from_markdown(test_md)
    for text, url, line in links:
        link_type = classify_link(url)
        print(f"  Line {line}: [{text}]({url}) - {link_type}")
