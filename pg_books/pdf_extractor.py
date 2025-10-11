"""
PDF Extractor

Extracts text content from PostgreSQL technical books (PDF format).
Preserves structure (chapters, sections) and metadata (page numbers).
"""
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import pdfplumber
import PyPDF2

import config
from utils import save_json, get_timestamp


logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extracts structured content from PDF books."""

    def __init__(self):
        """Initialize extractor."""
        self.pdf_count = 0
        self.extracted_items = []

    def extract_pdf(self, pdf_path: str) -> List[Dict]:
        """
        Extract content from a single PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of extracted content items
        """
        logger.info(f"Extracting PDF: {pdf_path}")

        items = []
        pdf_name = Path(pdf_path).name

        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                logger.info(f"Processing {total_pages} pages from {pdf_name}")

                current_chapter = None
                current_section = None

                for page_num, page in enumerate(pdf.pages, start=1):
                    # Extract text from page
                    text = page.extract_text()

                    if not text or len(text) < config.MIN_TEXT_LENGTH:
                        continue

                    # Try to detect chapter/section headings
                    chapter, section = self._detect_structure(text, page_num)

                    if chapter:
                        current_chapter = chapter
                    if section:
                        current_section = section

                    # Extract tables if configured
                    tables = []
                    if config.EXTRACT_TABLES:
                        page_tables = page.extract_tables()
                        if page_tables:
                            tables = self._format_tables(page_tables)

                    # Create content item
                    item = {
                        'pdf_file': pdf_name,
                        'page_number': page_num,
                        'chapter': current_chapter,
                        'section': current_section,
                        'text': text,
                        'tables': tables,
                        'extracted_at': get_timestamp()
                    }

                    items.append(item)

                    if page_num % 50 == 0:
                        logger.info(f"Processed {page_num}/{total_pages} pages")

            logger.info(f"Extracted {len(items)} items from {pdf_name}")
            return items

        except Exception as e:
            logger.error(f"Error extracting PDF {pdf_name}: {e}")
            return []

    def _detect_structure(self, text: str, page_num: int) -> tuple[Optional[str], Optional[str]]:
        """
        Detect chapter and section headings from page text.

        Args:
            text: Page text
            page_num: Page number

        Returns:
            Tuple of (chapter, section) or (None, None)
        """
        lines = text.split('\n')
        chapter = None
        section = None

        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            line = line.strip()

            # Detect chapter (e.g., "Chapter 5: MVCC", "5. MVCC", "Part II: Storage")
            chapter_patterns = [
                r'^Chapter\s+(\d+)[:\.\s]+(.+)$',
                r'^Part\s+([IVX]+)[:\.\s]+(.+)$',
                r'^(\d+)\.\s+([A-Z][^\.]+)$',
            ]

            for pattern in chapter_patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    chapter_num = match.group(1)
                    chapter_title = match.group(2).strip()
                    chapter = f"Chapter {chapter_num}: {chapter_title}"
                    break

            # Detect section (e.g., "5.1 Visibility Rules", "5.1. Visibility Rules")
            section_patterns = [
                r'^(\d+\.\d+)[:\.\s]+(.+)$',
                r'^([IVX]+\.[IVX]+)[:\.\s]+(.+)$',
            ]

            for pattern in section_patterns:
                match = re.match(pattern, line)
                if match:
                    section_num = match.group(1)
                    section_title = match.group(2).strip()
                    section = f"{section_num} {section_title}"
                    break

            if chapter and section:
                break

        return chapter, section

    def _format_tables(self, tables: List) -> List[Dict]:
        """
        Format extracted tables.

        Args:
            tables: List of raw tables from pdfplumber

        Returns:
            List of formatted table dicts
        """
        formatted = []

        for i, table in enumerate(tables):
            if not table:
                continue

            # Convert table to string representation
            table_text = ""
            for row in table:
                if row:
                    table_text += " | ".join([str(cell or "") for cell in row]) + "\n"

            formatted.append({
                'table_index': i,
                'rows': len(table),
                'cols': len(table[0]) if table else 0,
                'content': table_text.strip()
            })

        return formatted

    def extract_all_pdfs(self, pdf_dir: str = config.PDF_DIR) -> List[Dict]:
        """
        Extract content from all PDFs in directory.

        Args:
            pdf_dir: Directory containing PDF files

        Returns:
            List of all extracted content items
        """
        logger.info(f"Scanning for PDFs in: {pdf_dir}")

        # Find all PDF files
        pdf_files = list(Path(pdf_dir).glob("*.pdf"))

        if not pdf_files:
            logger.warning(f"No PDF files found in {pdf_dir}")
            return []

        logger.info(f"Found {len(pdf_files)} PDF file(s)")

        all_items = []

        for pdf_path in pdf_files:
            items = self.extract_pdf(str(pdf_path))
            all_items.extend(items)
            self.pdf_count += 1

        self.extracted_items = all_items

        logger.info(f"Total extracted: {len(all_items)} items from {self.pdf_count} PDF(s)")

        return all_items

    def get_statistics(self) -> Dict:
        """Get extraction statistics."""
        if not self.extracted_items:
            return {}

        # Count pages per PDF
        pdfs = {}
        for item in self.extracted_items:
            pdf = item['pdf_file']
            pdfs[pdf] = pdfs.get(pdf, 0) + 1

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
            'total_pdfs': self.pdf_count,
            'total_pages': len(self.extracted_items),
            'pages_per_pdf': pdfs,
            'unique_chapters': len(chapters),
            'unique_sections': len(sections),
            'total_tables': total_tables,
            'avg_text_length': sum(len(item['text']) for item in self.extracted_items) / len(self.extracted_items)
        }

    def save_to_json(self, output_path: str = config.EXTRACTED_CONTENT_FILE):
        """Save extracted content to JSON."""
        save_json(self.extracted_items, output_path)
        logger.info(f"Saved {len(self.extracted_items)} items to {output_path}")


def main():
    """Main function for standalone execution."""
    import sys
    from utils import setup_logging

    setup_logging("INFO")

    extractor = PDFExtractor()

    # Extract all PDFs
    content = extractor.extract_all_pdfs()

    # Print statistics
    stats = extractor.get_statistics()
    print("\n" + "=" * 60)
    print("Extraction Statistics:")
    print("=" * 60)
    for key, value in stats.items():
        print(f"{key}: {value}")

    # Save
    extractor.save_to_json()

    print("\n" + "=" * 60)
    print(f"Extraction complete!")
    print(f"Output: {config.EXTRACTED_CONTENT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
