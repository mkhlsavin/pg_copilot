"""
Web Book Scraper

Scrapes online PostgreSQL books (HTML format) like interdb.jp.
Preserves structure (chapters, sections) and converts to the same format as PDF extraction.
"""
import logging
import os
import re
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

import config
from utils import save_json, get_timestamp


logger = logging.getLogger(__name__)


class WebBookScraper:
    """Scrapes structured content from online HTML books."""

    def __init__(self, base_url: str, rate_limit: float = 0.5):
        """
        Initialize scraper.

        Args:
            base_url: Base URL of the book
            rate_limit: Delay between requests (seconds)
        """
        self.base_url = base_url
        self.rate_limit = rate_limit
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.extracted_items = []

    def fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch HTML page.

        Args:
            url: URL to fetch

        Returns:
            HTML content or None on failure
        """
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"HTTP {response.status_code} for {url}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def parse_toc(self, html: str, base_url: str) -> List[Dict]:
        """
        Parse table of contents to extract chapter links.

        Args:
            html: Index page HTML
            base_url: Base URL for resolving relative links

        Returns:
            List of chapter information
        """
        soup = BeautifulSoup(html, 'html.parser')
        chapters = {}

        # For interdb.jp, look for links to pgsqlNN/index.html
        all_links = soup.find_all('a', href=True)

        for link in all_links:
            href = link.get('href')
            text = link.get_text().strip()

            # Look for chapter index pages (pgsqlNN/index.html)
            if href and 'pgsql' in href and '/index.html' in href:
                # Extract chapter number from pgsqlNN
                chapter_match = re.search(r'pgsql(\d+)', href)
                if chapter_match:
                    chapter_num = int(chapter_match.group(1))

                    # Clean up title (remove leading number if present)
                    title = text
                    title_match = re.match(r'^\d+\.\s*(.+)', title)
                    if title_match:
                        title = title_match.group(1)

                    full_url = urljoin(base_url, href)

                    # Only keep first occurrence of each chapter
                    if chapter_num not in chapters:
                        chapters[chapter_num] = {
                            'chapter_num': chapter_num,
                            'title': title,
                            'url': full_url
                        }

        # Convert to sorted list
        chapter_list = [chapters[num] for num in sorted(chapters.keys())]

        logger.info(f"Found {len(chapter_list)} chapters")
        return chapter_list

    def extract_chapter_sections(self, chapter_url: str, chapter_info: Dict) -> List[str]:
        """
        Extract section page URLs from a chapter index page.

        Args:
            chapter_url: Chapter index URL
            chapter_info: Chapter metadata

        Returns:
            List of section page URLs
        """
        html = self.fetch_page(chapter_url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        section_urls = set()

        # Extract chapter directory from URL (e.g., pgsql01, pgsql02)
        chapter_match = re.search(r'(pgsql\d+)', chapter_url)
        if not chapter_match:
            logger.warning(f"Could not extract chapter directory from {chapter_url}")
            return []

        chapter_dir = chapter_match.group(1)

        # Find all links on the chapter index page
        for link in soup.find_all('a', href=True):
            href = link['href']

            # Look for section pages that belong to THIS chapter
            # Match patterns like: ./01.html, ./02.html (relative) or ../pgsqlNN/01.html
            if (href.endswith('.html') and
                not href.endswith('index.html') and
                not href.startswith('http') and
                not href.startswith('#')):

                # Only include if it's a relative link in same directory or explicitly references this chapter
                if (href.startswith('./') or
                    (chapter_dir in href and not 'index.html' in href)):

                    # Resolve relative URL
                    full_url = urljoin(chapter_url, href)

                    # Double-check it's in the correct chapter directory
                    if chapter_dir in full_url:
                        section_urls.add(full_url)

        logger.info(f"Found {len(section_urls)} sections in chapter {chapter_info['chapter_num']}")
        return sorted(list(section_urls))

    def extract_chapter_content(self, url: str, chapter_info: Dict) -> List[Dict]:
        """
        Extract content from a chapter (all its section pages).

        Args:
            url: Chapter index URL
            chapter_info: Chapter metadata

        Returns:
            List of extracted content items
        """
        # First get all section pages for this chapter
        section_urls = self.extract_chapter_sections(url, chapter_info)

        if not section_urls:
            logger.warning(f"No sections found for chapter {chapter_info['chapter_num']}")
            return []

        all_items = []

        # Extract content from each section page
        for section_url in section_urls:
            time.sleep(self.rate_limit)  # Rate limiting
            items = self.extract_section_content(section_url, chapter_info)
            all_items.extend(items)

        logger.info(f"Extracted {len(all_items)} items from chapter {chapter_info['chapter_num']}")
        return all_items

    def extract_section_content(self, url: str, chapter_info: Dict) -> List[Dict]:
        """
        Extract content from a single section page.

        Args:
            url: Section URL
            chapter_info: Chapter metadata

        Returns:
            List of extracted content items
        """
        html = self.fetch_page(url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        items = []

        # Extract main content (adjust selectors based on site structure)
        # Common patterns: <article>, <main>, <div class="content">, etc.

        main_content = None
        for selector in ['article', 'main', 'div.content', 'div#content', 'div.main']:
            main_content = soup.select_one(selector)
            if main_content:
                break

        if not main_content:
            # Fall back to body
            main_content = soup.find('body')

        if not main_content:
            logger.warning(f"No content found for {url}")
            return []

        # Extract sections within the chapter
        current_section = None
        page_counter = 1

        # Look for section headings (h2, h3, etc.)
        for element in main_content.find_all(['h2', 'h3', 'h4', 'p', 'pre', 'table']):
            if element.name in ['h2', 'h3', 'h4']:
                # This is a section heading
                section_text = element.get_text().strip()
                if section_text:
                    current_section = section_text

            elif element.name == 'p':
                # This is a paragraph
                text = element.get_text().strip()

                if len(text) < config.MIN_TEXT_LENGTH:
                    continue

                item = {
                    'source_type': 'web',
                    'source_url': url,
                    'book_name': self._extract_book_name(self.base_url),
                    'page_number': page_counter,
                    'chapter': f"Chapter {chapter_info['chapter_num']}: {chapter_info['title']}",
                    'section': current_section,
                    'text': text,
                    'tables': [],
                    'extracted_at': get_timestamp()
                }
                items.append(item)
                page_counter += 1

            elif element.name == 'pre':
                # This is code block
                code = element.get_text().strip()

                if len(code) < config.MIN_TEXT_LENGTH:
                    continue

                item = {
                    'source_type': 'web',
                    'source_url': url,
                    'book_name': self._extract_book_name(self.base_url),
                    'page_number': page_counter,
                    'chapter': f"Chapter {chapter_info['chapter_num']}: {chapter_info['title']}",
                    'section': current_section,
                    'text': f"[CODE BLOCK]\n{code}",
                    'tables': [],
                    'extracted_at': get_timestamp()
                }
                items.append(item)
                page_counter += 1

            elif element.name == 'table' and config.EXTRACT_TABLES:
                # Extract table
                table_text = self._extract_table(element)
                if table_text:
                    # Add table as a separate item or append to last item
                    if items:
                        items[-1]['tables'].append({
                            'table_index': len(items[-1]['tables']),
                            'content': table_text
                        })

        logger.info(f"Extracted {len(items)} items from {chapter_info['title']}")
        return items

    def _extract_table(self, table_element) -> str:
        """Extract text from HTML table."""
        rows = []
        for tr in table_element.find_all('tr'):
            cells = []
            for td in tr.find_all(['td', 'th']):
                cells.append(td.get_text().strip())
            if cells:
                rows.append(' | '.join(cells))
        return '\n'.join(rows)

    def _extract_book_name(self, url: str) -> str:
        """Extract book name from URL."""
        parsed = urlparse(url)
        domain = parsed.netloc

        # Map known domains to book names
        if 'interdb.jp' in domain:
            return 'The Internals of PostgreSQL'

        return domain

    def scrape_book(self, index_url: str) -> List[Dict]:
        """
        Scrape entire book from index page.

        Args:
            index_url: URL of book's index/TOC page

        Returns:
            List of all extracted content items
        """
        logger.info(f"Scraping book from: {index_url}")

        # Fetch index page
        html = self.fetch_page(index_url)
        if not html:
            logger.error("Failed to fetch index page")
            return []

        # Parse table of contents
        chapters = self.parse_toc(html, index_url)

        if not chapters:
            logger.error("No chapters found")
            return []

        all_items = []

        # Scrape each chapter
        for chapter_info in tqdm(chapters, desc="Scraping chapters"):
            time.sleep(self.rate_limit)

            items = self.extract_chapter_content(chapter_info['url'], chapter_info)
            all_items.extend(items)

        self.extracted_items = all_items

        logger.info(f"Total extracted: {len(all_items)} items from {len(chapters)} chapters")

        return all_items

    def get_statistics(self) -> Dict:
        """Get extraction statistics."""
        if not self.extracted_items:
            return {}

        # Count chapters
        chapters = set()
        sections = set()
        for item in self.extracted_items:
            if item['chapter']:
                chapters.add(item['chapter'])
            if item['section']:
                sections.add(item['section'])

        # Count tables
        total_tables = sum(len(item.get('tables', [])) for item in self.extracted_items)

        return {
            'total_items': len(self.extracted_items),
            'unique_chapters': len(chapters),
            'unique_sections': len(sections),
            'total_tables': total_tables,
            'avg_text_length': sum(len(item['text']) for item in self.extracted_items) / len(self.extracted_items) if self.extracted_items else 0
        }

    def save_to_json(self, output_path: str = None):
        """Save extracted content to JSON."""
        if output_path is None:
            # Create a filename based on book name
            book_name = self._extract_book_name(self.base_url)
            safe_name = re.sub(r'[^\w\s-]', '', book_name).strip().replace(' ', '_').lower()
            output_path = os.path.join(config.DATA_DIR, f"web_{safe_name}.json")

        save_json(self.extracted_items, output_path)
        logger.info(f"Saved {len(self.extracted_items)} items to {output_path}")


def main():
    """Main function for standalone execution."""
    import sys
    from utils import setup_logging, ensure_dir

    setup_logging("INFO")
    ensure_dir(config.DATA_DIR)

    # Scrape interdb.jp
    scraper = WebBookScraper("https://www.interdb.jp/pg/")

    content = scraper.scrape_book("https://www.interdb.jp/pg/index.html")

    # Print statistics
    stats = scraper.get_statistics()
    print("\n" + "=" * 60)
    print("Extraction Statistics:")
    print("=" * 60)
    for key, value in stats.items():
        print(f"{key}: {value}")

    # Save
    scraper.save_to_json()

    print("\n" + "=" * 60)
    print(f"Scraping complete!")
    print(f"Output: {config.DATA_DIR}/web_the_internals_of_postgresql.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
