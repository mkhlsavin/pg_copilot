#!/usr/bin/env python3
"""
Bilingual Documentation Builder for CodeGraph

Converts Markdown documentation to styled HTML with automatic translation
from English to Russian using LLM providers (YandexGPT, GigaChat, OpenAI).

Features:
    - Markdown → HTML conversion with syntax highlighting
    - Automatic EN → RU translation via LLM
    - Translation caching for faster rebuilds
    - Internal link validation
    - Responsive design with dark/light theme support
    - Sidebar navigation generation

Input:
    docs/
    ├── getting-started/    → Installation, configuration
    ├── guides/             → User guides and scenarios
    ├── api/                → REST API, WebSocket documentation
    ├── integrations/       → GigaChat, YandexGPT integration
    ├── reference/          → Technical reference
    └── enterprise/         → Enterprise features (already bilingual)

Output:
    docs/landing/docs/
    ├── en/                 → English HTML documentation
    │   ├── index.html
    │   ├── getting-started/
    │   ├── guides/
    │   └── ...
    └── ru/                 → Russian HTML documentation
        └── (mirror structure)

Usage:
    python scripts/build_docs.py                    # Full build with translation
    python scripts/build_docs.py --no-translate    # Build EN only (no translation)
    python scripts/build_docs.py --provider yandex # Use YandexGPT for translation
    python scripts/build_docs.py --mock            # Use mock translator (testing)
    python scripts/build_docs.py --validate        # Validate links only
    python scripts/build_docs.py -v                # Verbose output

Environment Variables (for translation):
    YANDEX_API_KEY      - YandexGPT API key
    YANDEX_FOLDER_ID    - YandexGPT folder ID
    GIGACHAT_CREDENTIALS - GigaChat credentials

See Also:
    scripts/docs_builder/README.md - Detailed documentation
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path
from typing import Dict, List

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.docs_builder.config import (
    SOURCE_FOLDERS,
    OUTPUT_EN,
    OUTPUT_RU,
    BILINGUAL_FOLDERS,
    DOC_SECTIONS,
    DOCS_ROOT,
    PROJECT_ROOT as CONFIG_PROJECT_ROOT,
)
from scripts.docs_builder.discovery import (
    discover_docs,
    DocFile,
    find_missing_translations,
    check_translation_status,
    print_translation_summary,
    extract_title,
)
from scripts.docs_builder.translator import create_translator
from scripts.docs_builder.converter import (
    convert_markdown_to_html,
    transform_links,
    strip_frontmatter,
    add_custom_styles,
)
from scripts.docs_builder.template import HTMLGenerator, generate_sidebar
from scripts.docs_builder.navigation import (
    generate_sidebar_html,
    generate_index_page,
    generate_section_index,
)
from scripts.docs_builder.linker import LinkValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class DocBuilder:
    """Main documentation builder orchestrator."""

    def __init__(
        self,
        translate: bool = True,
        provider: str = None,
        mock: bool = False,
        validate_only: bool = False,
        verbose: bool = False,
        force_translate: bool = False,
    ):
        """
        Initialize the documentation builder.

        Args:
            translate: Whether to translate EN docs to RU
            provider: LLM provider name (yandex, gigachat, openai)
            mock: Use mock translator for testing
            validate_only: Only validate existing output
            verbose: Enable verbose logging
            force_translate: If True, ignore existing RU files and always translate
        """
        self.translate = translate
        self.validate_only = validate_only
        self.force_translate = force_translate
        self.docs_root = DOCS_ROOT
        self.output_base = CONFIG_PROJECT_ROOT / "docs" / "landing" / "docs"
        self.output_en = self.output_base / "en"
        self.output_ru = self.output_base / "ru"

        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        # Initialize translator
        if translate and not validate_only:
            self.translator = create_translator(
                provider=provider,
                use_cache=True,
                mock=mock
            )
        else:
            self.translator = None

        # HTML generators
        self.html_gen_en = HTMLGenerator('en')
        self.html_gen_ru = HTMLGenerator('ru')

        # Track files for navigation
        self.files_by_section: Dict[str, List[Dict]] = {}

        # Statistics
        self.stats = {
            'files_discovered': 0,
            'files_processed': 0,
            'files_translated': 0,
            'translation_cached': 0,
            'used_existing_ru': 0,  # Files where existing RU was used instead of translation
            'errors': 0,
        }

    def build(self) -> bool:
        """
        Execute the full build process.

        Returns:
            True if build succeeded, False otherwise
        """
        try:
            if self.validate_only:
                return self._validate_only()

            logger.info("=" * 60)
            logger.info("Starting documentation build")
            logger.info("=" * 60)

            # 1. Setup output directories
            self._setup_output_dirs()

            # 2. Discover documentation files
            all_docs = discover_docs(self.docs_root, SOURCE_FOLDERS)
            self.stats['files_discovered'] = sum(len(f) for f in all_docs.values())
            logger.info(f"Discovered {self.stats['files_discovered']} documentation files")

            # 3. Find files needing translation
            if self.translate:
                missing = find_missing_translations(all_docs)
                logger.info(f"Files needing Russian translation: {len(missing)}")

            # 4. Process each section
            for folder, doc_files in all_docs.items():
                self._process_section(folder, doc_files)

            # 5. Generate index pages
            self._generate_index_pages()

            # 6. Copy static assets (CSS, JS reference - they exist in landing/)
            # Assets are referenced relatively, no copy needed

            # 7. Validate links
            validation_result = self._validate_links()

            # 8. Print summary
            self._print_summary(validation_result)

            return len(validation_result.broken_links) == 0

        except Exception as e:
            logger.error(f"Build failed: {e}", exc_info=True)
            return False

    def _setup_output_dirs(self):
        """Create output directory structure."""
        logger.info("Setting up output directories...")

        # Create base directories
        self.output_en.mkdir(parents=True, exist_ok=True)
        self.output_ru.mkdir(parents=True, exist_ok=True)

        # Create section subdirectories
        for section in DOC_SECTIONS:
            (self.output_en / section['id']).mkdir(exist_ok=True)
            (self.output_ru / section['id']).mkdir(exist_ok=True)

        logger.info(f"Output directories ready: {self.output_base}")

    def _process_section(self, folder: str, doc_files: List[DocFile]):
        """
        Process all files in a documentation section using two-pass approach.

        Pass 1: Collect all files and extract titles (EN + RU)
        Pass 2: Generate all HTML files with complete navigation info
        """
        logger.info(f"Processing section: {folder} ({len(doc_files)} files)")

        # Initialize section in files tracker
        if folder not in self.files_by_section:
            self.files_by_section[folder] = []

        # First pass: collect all files and extract titles
        pending_files = []  # List of (content, doc, folder, slug, lang) tuples

        for doc in doc_files:
            try:
                content = transform_links(doc.content)
                content = strip_frontmatter(content)
                slug = doc.filename.replace('.md', '')

                if doc.language == 'en':
                    # Track file for navigation
                    file_info = {
                        'slug': slug,
                        'title': doc.title or slug.replace('_', ' ').replace('-', ' ').title(),
                        'path': doc.relative_path,
                    }
                    self.files_by_section[folder].append(file_info)
                    pending_files.append((content, doc, folder, slug, 'en'))

                    # Also prepare Russian version
                    if self.translate:
                        ru_content, ru_title = self._prepare_russian_version(content, doc, folder, slug)
                        if ru_content:
                            pending_files.append((ru_content, doc, folder, slug, 'ru'))
                            if ru_title:
                                file_info['title_ru'] = ru_title

                elif doc.language == 'ru':
                    # Extract Russian title and update corresponding EN entry
                    ru_title = extract_title(doc.content)
                    if ru_title:
                        for fi in self.files_by_section[folder]:
                            if fi['slug'] == slug:
                                fi['title_ru'] = ru_title
                                break
                    pending_files.append((content, doc, folder, slug, 'ru'))

            except Exception as e:
                logger.error(f"Error collecting {doc.relative_path}: {e}")
                self.stats['errors'] += 1

        # Second pass: generate all HTML files (now all title_ru are populated)
        for content, doc, folder, slug, lang in pending_files:
            try:
                self._generate_html_file(content, doc, folder, slug, lang)
                self.stats['files_processed'] += 1
            except Exception as e:
                logger.error(f"Error generating HTML for {doc.relative_path}: {e}")
                self.stats['errors'] += 1

    def _prepare_russian_version(
        self,
        en_content: str,
        doc: DocFile,
        folder: str,
        slug: str
    ) -> tuple:
        """
        Prepare Russian version content without generating HTML.

        Returns:
            Tuple of (ru_content, ru_title) or (None, None) if not available
        """
        status = check_translation_status(self.docs_root, folder, doc.filename)

        if status.use_existing_ru and not self.force_translate:
            # Use existing Russian file (it's newer than English)
            ru_path = self.docs_root / folder / 'ru' / doc.filename
            ru_content = ru_path.read_text(encoding='utf-8')
            ru_content = transform_links(ru_content)
            ru_content = strip_frontmatter(ru_content)
            ru_title = extract_title(ru_content)
            self.stats['used_existing_ru'] += 1
            logger.debug(f"Using existing RU file: {doc.filename}")
            return ru_content, ru_title

        elif status.ru_exists and not self.force_translate:
            # Russian file exists but is older than English - still use it
            ru_path = self.docs_root / folder / 'ru' / doc.filename
            ru_content = ru_path.read_text(encoding='utf-8')
            ru_content = transform_links(ru_content)
            ru_content = strip_frontmatter(ru_content)
            ru_title = extract_title(ru_content)
            self.stats['used_existing_ru'] += 1
            logger.debug(f"Using existing RU file (may be outdated): {doc.filename}")
            return ru_content, ru_title

        elif self.translator:
            # No Russian file or force_translate - translate from English
            try:
                ru_content = self.translator.translate(en_content)
                ru_title = extract_title(ru_content)
                self.stats['files_translated'] += 1
                return ru_content, ru_title
            except Exception as e:
                logger.warning(f"Translation failed for {doc.filename}: {e}")
                fallback = f"<!-- TODO: Translate this document -->\n\n{en_content}"
                return fallback, None

        return None, None

    def _generate_html_file(
        self,
        content: str,
        doc: DocFile,
        folder: str,
        slug: str,
        lang: str
    ):
        """Generate an HTML file from Markdown content."""
        # Convert markdown to HTML
        result = convert_markdown_to_html(content)
        html_content = add_custom_styles(result.html)

        # Generate sidebar
        sidebar = generate_sidebar_html(
            DOC_SECTIONS,
            self.files_by_section,
            f"{folder}/{slug}.html",
            lang
        )

        # Get appropriate HTML generator
        gen = self.html_gen_en if lang == 'en' else self.html_gen_ru

        # Get prev/next navigation
        prev_page, next_page = self._get_prev_next_page(folder, slug, lang)

        # Generate full page
        full_html = gen.generate(
            title=result.title or doc.title or slug,
            content=html_content,
            relative_path=f"{folder}/{slug}",
            section_id=folder,
            headings=result.headings,
            sidebar_html=sidebar,
            prev_page=prev_page,
            next_page=next_page,
        )

        # Write output file
        output_dir = self.output_en if lang == 'en' else self.output_ru
        output_file = output_dir / folder / f"{slug}.html"
        output_file.write_text(full_html, encoding='utf-8')
        logger.debug(f"Generated: {output_file}")

    def _get_section_index(self, section_id: str) -> int:
        """Get index of section in DOC_SECTIONS."""
        for i, section in enumerate(DOC_SECTIONS):
            if section['id'] == section_id:
                return i
        return -1

    def _get_prev_section(self, section_id: str, lang: str) -> dict:
        """Get previous section info for navigation."""
        idx = self._get_section_index(section_id)
        if idx > 0:
            prev = DOC_SECTIONS[idx - 1]
            title_key = f"title_{lang}"
            return {
                'id': prev['id'],
                'title': prev.get(title_key, prev['id'].title())
            }
        return None

    def _get_next_section(self, section_id: str, lang: str) -> dict:
        """Get next section info for navigation."""
        idx = self._get_section_index(section_id)
        if idx >= 0 and idx < len(DOC_SECTIONS) - 1:
            next_sec = DOC_SECTIONS[idx + 1]
            title_key = f"title_{lang}"
            return {
                'id': next_sec['id'],
                'title': next_sec.get(title_key, next_sec['id'].title())
            }
        return None

    def _get_prev_next_page(
        self,
        section_id: str,
        slug: str,
        lang: str
    ) -> tuple:
        """
        Get previous and next page info for navigation.

        Returns:
            Tuple of (prev_page, next_page) dicts with 'url' and 'title' keys
        """
        from scripts.docs_builder.navigation import sort_files_by_order

        # Get sorted files for this section
        files = sort_files_by_order(
            self.files_by_section.get(section_id, []),
            section_id
        )

        # Filter out index/readme
        files = [f for f in files if f['slug'].lower() not in ('index', 'readme')]

        # Build all pages list: index first, then files
        overview_title = "Overview" if lang == 'en' else "Обзор"
        all_pages = [{'slug': 'index', 'title': overview_title}] + files

        # Find current position
        current_idx = None
        for i, f in enumerate(all_pages):
            if f['slug'] == slug:
                current_idx = i
                break

        if current_idx is None:
            return None, None

        prev_page = None
        next_page = None

        # Get title based on language
        def get_title(f, lang):
            if lang == 'ru' and 'title_ru' in f:
                return f['title_ru']
            return f.get('title', f['slug'])

        # Previous page
        if current_idx > 0:
            p = all_pages[current_idx - 1]
            prev_page = {
                'url': f"{p['slug']}.html",
                'title': get_title(p, lang)
            }
        else:
            # Go to previous section's last page
            prev_section = self._get_prev_section(section_id, lang)
            if prev_section:
                prev_page = {
                    'url': f"../{prev_section['id']}/index.html",
                    'title': prev_section['title']
                }

        # Next page
        if current_idx < len(all_pages) - 1:
            n = all_pages[current_idx + 1]
            next_page = {
                'url': f"{n['slug']}.html",
                'title': get_title(n, lang)
            }
        else:
            # Go to next section
            next_section = self._get_next_section(section_id, lang)
            if next_section:
                next_page = {
                    'url': f"../{next_section['id']}/index.html",
                    'title': next_section['title']
                }

        return prev_page, next_page

    def _generate_index_pages(self):
        """Generate documentation index pages."""
        logger.info("Generating index pages...")

        for lang in ['en', 'ru']:
            # Main index
            index_html = generate_index_page(lang, DOC_SECTIONS, self.files_by_section)
            output_dir = self.output_en if lang == 'en' else self.output_ru
            (output_dir / 'index.html').write_text(index_html, encoding='utf-8')

            # Section indices
            for section in DOC_SECTIONS:
                section_id = section['id']
                title_key = f"title_{lang}"
                title = section.get(title_key, section_id.title())

                files = self.files_by_section.get(section_id, [])
                sidebar = generate_sidebar_html(
                    DOC_SECTIONS,
                    self.files_by_section,
                    f"{section_id}/index.html",
                    lang
                )

                section_html = generate_section_index(
                    section_id, title, files, lang, sidebar,
                    prev_section=self._get_prev_section(section_id, lang),
                    next_section=self._get_next_section(section_id, lang),
                )

                (output_dir / section_id / 'index.html').write_text(
                    section_html, encoding='utf-8'
                )

        logger.info("Index pages generated")

    def _validate_links(self):
        """Validate all links in generated documentation."""
        logger.info("Validating links...")

        validator = LinkValidator(self.output_base)
        result = validator.validate_all()

        if result.broken_links:
            logger.warning(f"Found {len(result.broken_links)} broken links")
            for link in result.broken_links[:10]:  # Show first 10
                logger.warning(f"  {link.source_file}:{link.line_number} - {link.error}")

        return result

    def _validate_only(self) -> bool:
        """Run link validation only."""
        logger.info("Running link validation only...")

        if not self.output_base.exists():
            logger.error(f"Output directory not found: {self.output_base}")
            return False

        validator = LinkValidator(self.output_base)
        print(validator.get_report())

        result = validator.validate_all()
        return len(result.broken_links) == 0

    def _print_summary(self, validation_result):
        """Print build summary."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("BUILD SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Files discovered:    {self.stats['files_discovered']}")
        logger.info(f"Files processed:     {self.stats['files_processed']}")

        if self.translate:
            logger.info(f"Used existing RU:    {self.stats['used_existing_ru']}")
            if self.translator:
                translator_stats = self.translator.get_stats()
                logger.info(f"Files translated:    {translator_stats.get('translated', 0)}")
                logger.info(f"From cache:          {translator_stats.get('cached', 0)}")

        logger.info(f"Errors:              {self.stats['errors']}")
        logger.info(f"Broken links:        {len(validation_result.broken_links)}")
        logger.info("")
        logger.info(f"Output directory:    {self.output_base}")
        logger.info("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Build bilingual HTML documentation from Markdown',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/build_docs.py                    # Full build with translation
  python scripts/build_docs.py --no-translate    # Build EN only
  python scripts/build_docs.py --mock            # Test with mock translator
  python scripts/build_docs.py --validate        # Validate links only
  python scripts/build_docs.py --check-status    # Show translation status summary
  python scripts/build_docs.py --force-translate # Re-translate all, ignore existing RU
        """
    )

    parser.add_argument(
        '--translate',
        action='store_true',
        default=True,
        help='Enable LLM translation (default: True)'
    )
    parser.add_argument(
        '--no-translate',
        action='store_true',
        help='Disable translation, build English only'
    )
    parser.add_argument(
        '--provider',
        choices=['yandex', 'gigachat', 'openai'],
        help='LLM provider for translation'
    )
    parser.add_argument(
        '--mock',
        action='store_true',
        help='Use mock translator (for testing)'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate links in existing output only'
    )
    parser.add_argument(
        '--check-status',
        action='store_true',
        help='Show translation status summary and exit'
    )
    parser.add_argument(
        '--force-translate',
        action='store_true',
        help='Force re-translation even if RU files exist'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    # Handle --check-status option
    if args.check_status:
        print_translation_summary()
        sys.exit(0)

    # Determine translation setting
    translate = not args.no_translate

    builder = DocBuilder(
        translate=translate,
        provider=args.provider,
        mock=args.mock,
        validate_only=args.validate,
        verbose=args.verbose,
        force_translate=args.force_translate,
    )

    success = builder.build()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
