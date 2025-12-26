"""
Document Translator

Translates Markdown documentation from English to Russian using LLM.
Includes caching to avoid re-translating unchanged content.
"""

import hashlib
import json
import logging
import re
import sys
from pathlib import Path
from typing import Optional

# Add project root to path for importing LLM providers
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from .config import TRANSLATION_CACHE_DIR, MAX_CONTENT_LENGTH

logger = logging.getLogger(__name__)


def _slugify_english(text: str) -> str:
    """Create a slug from English text for anchor IDs."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    return text.strip('-')


def add_heading_anchors(content: str) -> str:
    """
    Add explicit anchor IDs to headings before translation.

    This ensures that anchor links in TOC remain valid after translation,
    because the markdown attr_list extension will use {#id} syntax.

    Example:
        ## Quick Reference  →  ## Quick Reference {#quick-reference}
    """
    def add_anchor(match):
        hashes = match.group(1)
        title = match.group(2).strip()

        # Skip if already has {#...}
        if re.search(r'\{#[\w-]+\}\s*$', title):
            return match.group(0)

        # Create slug from English heading
        slug = _slugify_english(title)
        if not slug:
            return match.group(0)

        return f"{hashes} {title} {{#{slug}}}"

    return re.sub(r'^(#{1,6})\s+(.+)$', add_anchor, content, flags=re.MULTILINE)


# Translation system prompt
TRANSLATION_SYSTEM_PROMPT = """You are a professional technical translator specializing in software documentation.

Your task: Translate the following Markdown documentation from English to Russian.

Translation guidelines:
1. Preserve ALL Markdown formatting exactly (headers, code blocks, links, lists, tables)
2. Keep code examples, variable names, and file paths in English (unchanged)
3. Keep technical terms in English: API, REST, JSON, HTTP, URL, CLI, TUI, SQL, CPG, LLM, etc.
4. Translate comments inside code blocks if they are in English
5. Translate link text but preserve URLs unchanged
6. Maintain the same structure and heading hierarchy
7. Use formal Russian style ("Вы" form, not "ты")
8. For technical concepts, use established Russian IT terminology
9. Keep acronyms and product names (CodeGraph, YandexGPT, GigaChat) unchanged
10. Preserve any HTML tags, badges, or special markdown syntax
11. CRITICAL: Preserve {#anchor-id} syntax at the end of headings EXACTLY as written.
    Example: "## Quick Reference {#quick-reference}" → "## Краткий справочник {#quick-reference}"
    The anchor ID inside {} must NOT be translated or changed.

Do NOT add any explanations, notes, or comments. Output ONLY the translated Markdown content."""


class TranslationCache:
    """Cache for translated content to avoid redundant API calls."""

    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or TRANSLATION_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.cache_dir / "index.json"
        self.index = self._load_index()

    def _load_index(self) -> dict:
        """Load cache index from disk."""
        if self.index_file.exists():
            try:
                return json.loads(self.index_file.read_text(encoding='utf-8'))
            except Exception as e:
                logger.warning(f"Failed to load cache index: {e}")
        return {}

    def _save_index(self):
        """Save cache index to disk."""
        self.index_file.write_text(
            json.dumps(self.index, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

    def _get_hash(self, content: str) -> str:
        """Generate hash for content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    def get(self, content: str) -> Optional[str]:
        """Get cached translation if available."""
        content_hash = self._get_hash(content)
        if content_hash in self.index:
            cache_file = self.cache_dir / f"{content_hash}.md"
            if cache_file.exists():
                logger.debug(f"Cache hit: {content_hash}")
                return cache_file.read_text(encoding='utf-8')
        return None

    def set(self, original: str, translated: str):
        """Cache a translation."""
        content_hash = self._get_hash(original)
        cache_file = self.cache_dir / f"{content_hash}.md"
        cache_file.write_text(translated, encoding='utf-8')
        self.index[content_hash] = {
            'original_length': len(original),
            'translated_length': len(translated),
        }
        self._save_index()
        logger.debug(f"Cached translation: {content_hash}")


class DocumentTranslator:
    """Translates documentation using LLM providers."""

    def __init__(self, provider_name: str = None, use_cache: bool = True):
        """
        Initialize translator with LLM provider.

        Args:
            provider_name: 'yandex', 'gigachat', or 'openai'. Uses config default if None.
            use_cache: Whether to use translation cache.
        """
        self.provider = self._create_provider(provider_name)
        self.cache = TranslationCache() if use_cache else None
        self.stats = {
            'translated': 0,
            'cached': 0,
            'chunks': 0,
            'errors': 0,
        }

    def _create_provider(self, provider_name: str = None):
        """Create LLM provider instance."""
        try:
            from src.llm.factory import create_llm_provider, load_config

            config = load_config()

            if provider_name:
                if 'llm' not in config:
                    config['llm'] = {}
                config['llm']['provider'] = provider_name

            provider = create_llm_provider(config)
            current_provider = config.get('llm', {}).get('provider', 'default')
            logger.info(f"Translator using provider: {provider_name or current_provider}")
            return provider

        except ImportError as e:
            logger.error(f"Failed to import LLM provider: {e}")
            raise RuntimeError(
                "LLM provider not available. "
                "Ensure src/llm/ modules are accessible."
            )

    def translate(self, content: str, force: bool = False) -> str:
        """
        Translate Markdown content from English to Russian.

        Args:
            content: English Markdown content
            force: If True, skip cache and force new translation

        Returns:
            Russian Markdown content
        """
        # Add explicit anchor IDs to headings before translation
        # This ensures TOC links work after translation
        content = add_heading_anchors(content)

        # Check cache first
        if self.cache and not force:
            cached = self.cache.get(content)
            if cached:
                self.stats['cached'] += 1
                return cached

        # Split large content into chunks
        if len(content) > MAX_CONTENT_LENGTH:
            translated = self._translate_in_chunks(content)
        else:
            translated = self._translate_single(content)

        # Cache the result
        if self.cache and translated:
            self.cache.set(content, translated)

        self.stats['translated'] += 1
        return translated

    def _translate_single(self, content: str) -> str:
        """Translate a single piece of content."""
        try:
            response = self.provider.generate(
                system_prompt=TRANSLATION_SYSTEM_PROMPT,
                user_prompt=f"Translate this documentation to Russian:\n\n{content}",
                temperature=0.3,
                max_tokens=4096,
            )
            return response.content.strip()

        except Exception as e:
            logger.error(f"Translation error: {e}")
            self.stats['errors'] += 1
            # Return original content with error marker
            return f"<!-- TRANSLATION ERROR: {e} -->\n\n{content}"

    def _translate_in_chunks(self, content: str) -> str:
        """Split content by H2 headers and translate chunk by chunk."""
        # Split by ## headers while preserving them
        sections = re.split(r'(?=^## )', content, flags=re.MULTILINE)

        translated_sections = []

        for i, section in enumerate(sections):
            if not section.strip():
                continue

            logger.debug(f"Translating chunk {i + 1}/{len(sections)}")
            self.stats['chunks'] += 1

            # Check cache for individual chunks too
            if self.cache:
                cached = self.cache.get(section)
                if cached:
                    translated_sections.append(cached)
                    self.stats['cached'] += 1
                    continue

            translated = self._translate_single(section)
            translated_sections.append(translated)

            # Cache the chunk
            if self.cache:
                self.cache.set(section, translated)

        return '\n\n'.join(translated_sections)

    def get_stats(self) -> dict:
        """Get translation statistics."""
        return self.stats.copy()


class MockTranslator:
    """Mock translator for testing without API calls."""

    def __init__(self):
        self.stats = {'translated': 0, 'cached': 0, 'chunks': 0, 'errors': 0}

    def translate(self, content: str, force: bool = False) -> str:
        """Create a mock translation by prepending Russian marker."""
        self.stats['translated'] += 1

        # Simple mock: prepend comment and translate headers
        lines = content.split('\n')
        result = ["<!-- TODO: Перевести этот документ -->", ""]

        for line in lines:
            # Mock translate headers
            if line.startswith('# '):
                result.append(f"# [RU] {line[2:]}")
            elif line.startswith('## '):
                result.append(f"## [RU] {line[3:]}")
            elif line.startswith('### '):
                result.append(f"### [RU] {line[4:]}")
            else:
                result.append(line)

        return '\n'.join(result)

    def get_stats(self) -> dict:
        return self.stats.copy()


def create_translator(
    provider: str = None,
    use_cache: bool = True,
    mock: bool = False
) -> DocumentTranslator:
    """
    Factory function to create appropriate translator.

    Args:
        provider: LLM provider name
        use_cache: Whether to use cache
        mock: If True, return mock translator for testing

    Returns:
        Translator instance
    """
    if mock:
        return MockTranslator()
    return DocumentTranslator(provider_name=provider, use_cache=use_cache)


if __name__ == "__main__":
    # Test the translator
    logging.basicConfig(level=logging.INFO)

    test_content = """# Getting Started

This guide will help you get started with CodeGraph.

## Installation

Install CodeGraph using pip:

```bash
pip install codegraph
```

## Configuration

Create a `config.yaml` file with the following content:

```yaml
llm:
  provider: yandex
```

For more details, see [Configuration Guide](CONFIGURATION.md).
"""

    # Test mock translator
    print("=== Testing Mock Translator ===")
    mock = create_translator(mock=True)
    result = mock.translate(test_content)
    print(result[:500])
    print(f"\nStats: {mock.get_stats()}")
