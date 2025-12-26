"""
Markdown to HTML Converter

Converts Markdown documentation to styled HTML using the Python markdown library.
"""

import re
import logging
from typing import Tuple
from dataclasses import dataclass

try:
    import markdown
    from markdown.extensions.toc import TocExtension
    from markdown.extensions.codehilite import CodeHiliteExtension
    from markdown.extensions.tables import TableExtension
    from markdown.extensions.fenced_code import FencedCodeExtension
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    """Result of Markdown to HTML conversion."""
    html: str
    toc: str
    title: str
    headings: list


def create_markdown_converter():
    """
    Create a Markdown converter with all necessary extensions.

    Extensions:
    - tables: GitHub-style tables
    - fenced_code: Code blocks with language hints
    - codehilite: Syntax highlighting
    - toc: Table of contents generation
    - sane_lists: Better list handling
    - attr_list: Custom attributes on elements
    - md_in_html: Markdown inside HTML blocks
    """
    if not MARKDOWN_AVAILABLE:
        raise RuntimeError(
            "markdown library not installed. "
            "Install with: pip install markdown pygments"
        )

    return markdown.Markdown(
        extensions=[
            'tables',
            'fenced_code',
            'codehilite',
            'toc',
            'sane_lists',
            'attr_list',
            'md_in_html',
            'smarty',
        ],
        extension_configs={
            'codehilite': {
                'css_class': 'highlight',
                'guess_lang': True,
                'linenums': False,
            },
            'toc': {
                'permalink': True,
                'permalink_class': 'heading-anchor',
                'permalink_title': 'Link to this section',
                'toc_depth': 3,
                'slugify': _slugify,
            },
        }
    )


def _slugify(value: str, separator: str = '-') -> str:
    """
    Create a slug from a heading text.

    Handles both English and Russian text.
    """
    # Transliterate Russian characters
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    }

    value = value.lower()

    # Transliterate
    result = []
    for char in value:
        if char in translit_map:
            result.append(translit_map[char])
        elif char.isalnum():
            result.append(char)
        elif char in ' _-':
            result.append(separator)
        # Skip other characters

    # Clean up
    slug = ''.join(result)
    slug = re.sub(f'{separator}+', separator, slug)  # Remove duplicate separators
    slug = slug.strip(separator)

    return slug


def convert_markdown_to_html(md_content: str) -> ConversionResult:
    """
    Convert Markdown content to HTML.

    Args:
        md_content: Markdown string

    Returns:
        ConversionResult with HTML, TOC, title, and headings
    """
    md = create_markdown_converter()

    # Convert
    html = md.convert(md_content)
    toc = md.toc

    # Extract title from first H1
    title = ""
    title_match = re.search(r'^#\s+(.+?)(?:\s*\{.*\})?$', md_content, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()

    # Extract headings for navigation
    headings = []
    for match in re.finditer(r'^(#{1,6})\s+(.+?)(?:\s*\{.*\})?$', md_content, re.MULTILINE):
        level = len(match.group(1))
        text = match.group(2).strip()
        slug = _slugify(text)
        headings.append({
            'level': level,
            'text': text,
            'slug': slug,
        })

    # Reset converter for next use
    md.reset()

    return ConversionResult(
        html=html,
        toc=toc,
        title=title,
        headings=headings,
    )


def transform_links(content: str, from_ext: str = '.md', to_ext: str = '.html') -> str:
    """
    Transform file extensions in Markdown links.

    Converts [text](file.md) to [text](file.html)
    """
    def replace_link(match):
        text = match.group(1)
        url = match.group(2)

        # Don't transform external URLs
        if url.startswith(('http://', 'https://', 'mailto:', '#')):
            return match.group(0)

        # Transform .md to .html
        if url.endswith(from_ext):
            url = url[:-len(from_ext)] + to_ext

        return f'[{text}]({url})'

    # Match markdown links: [text](url)
    pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    return re.sub(pattern, replace_link, content)


def add_custom_styles(html: str) -> str:
    """
    Add custom CSS classes to HTML elements for styling.

    Wraps certain elements with div containers for better styling.
    """
    # Wrap tables in scrollable container
    html = re.sub(
        r'<table>',
        '<div class="table-wrapper"><table>',
        html
    )
    html = re.sub(
        r'</table>',
        '</table></div>',
        html
    )

    # Add classes to code blocks
    html = re.sub(
        r'<pre><code',
        '<pre class="code-block"><code',
        html
    )

    # Wrap blockquotes with custom class
    html = re.sub(
        r'<blockquote>',
        '<blockquote class="callout">',
        html
    )

    return html


def extract_metadata(content: str) -> dict:
    """
    Extract YAML frontmatter metadata if present.

    Returns empty dict if no frontmatter.
    """
    if not content.startswith('---'):
        return {}

    # Find closing ---
    end_match = re.search(r'\n---\n', content[3:])
    if not end_match:
        return {}

    frontmatter = content[3:end_match.start() + 3]

    # Parse simple key: value pairs
    metadata = {}
    for line in frontmatter.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            metadata[key.strip()] = value.strip().strip('"\'')

    return metadata


def strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter from content."""
    if not content.startswith('---'):
        return content

    end_match = re.search(r'\n---\n', content[3:])
    if not end_match:
        return content

    return content[end_match.end() + 3:].lstrip()


if __name__ == "__main__":
    # Test the converter
    test_md = """---
title: Test Document
author: CodeGraph Team
---

# Getting Started

This is an introduction to **CodeGraph**.

## Installation

Install using pip:

```python
pip install codegraph
```

## Configuration

| Option | Type | Description |
|--------|------|-------------|
| `api_key` | string | Your API key |
| `timeout` | int | Request timeout |

> **Note**: Make sure to configure your API key before use.

For details, see [Configuration Guide](CONFIGURATION.md).

### Subsection

This links to [another page](../guides/USAGE.md#section).
"""

    print("=== Testing Markdown Converter ===\n")

    # Extract metadata
    meta = extract_metadata(test_md)
    print(f"Metadata: {meta}\n")

    # Strip frontmatter
    clean_md = strip_frontmatter(test_md)

    # Transform links
    transformed = transform_links(clean_md)
    print("=== Links Transformed ===")
    print(transformed[:200])

    # Convert to HTML
    if MARKDOWN_AVAILABLE:
        result = convert_markdown_to_html(transformed)
        print("\n=== Conversion Result ===")
        print(f"Title: {result.title}")
        print(f"Headings: {result.headings}")
        print(f"\nTOC:\n{result.toc}")
        print(f"\nHTML (first 500 chars):\n{result.html[:500]}")
    else:
        print("\nmarkdown library not installed")
