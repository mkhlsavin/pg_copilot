"""
PostgreSQL Source Code Extractor
Extracts README files and multi-line comments from PostgreSQL source code.
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class PgSourceCodeExtractor:
    """Extract documentation from PostgreSQL source code."""

    def __init__(self, source_root: str):
        """
        Initialize extractor.

        Args:
            source_root: Path to PostgreSQL source root (e.g., C:/Users/user/postgres-REL_17_6/src)
        """
        self.source_root = Path(source_root)
        if not self.source_root.exists():
            raise ValueError(f"Source root does not exist: {source_root}")

        logger.info(f"Initialized PgSourceCodeExtractor for: {source_root}")

    def extract_readme_files(self) -> List[Dict]:
        """
        Recursively find and extract all README files.

        Returns:
            List of dictionaries with 'content', 'file_path', 'relative_path', 'directory'
        """
        readme_files = []

        # Find all README files (case-insensitive)
        for readme_path in self.source_root.rglob('README*'):
            if readme_path.is_file():
                try:
                    # Read content
                    with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().strip()

                    if content:
                        relative_path = readme_path.relative_to(self.source_root)

                        readme_files.append({
                            'content': content,
                            'file_path': str(readme_path),
                            'relative_path': str(relative_path),
                            'directory': str(readme_path.parent.relative_to(self.source_root)),
                            'type': 'README'
                        })

                        logger.debug(f"Extracted README: {relative_path}")

                except Exception as e:
                    logger.warning(f"Failed to read {readme_path}: {e}")

        logger.info(f"Extracted {len(readme_files)} README files")
        return readme_files

    def extract_c_comments(self, max_files: int = None) -> List[Dict]:
        """
        Extract multi-line comments from C source files.

        Args:
            max_files: Maximum number of .c files to process (None = all)

        Returns:
            List of dictionaries with 'content', 'file_path', 'relative_path', 'line_start'
        """
        comments = []

        # Pattern for multi-line comments: /* ... */ or /** ... */
        # Use DOTALL to match across newlines
        comment_pattern = re.compile(r'/\*\*?(.*?)\*/', re.DOTALL)

        # Find all .c files
        c_files = list(self.source_root.rglob('*.c'))

        if max_files:
            c_files = c_files[:max_files]

        logger.info(f"Processing {len(c_files)} C source files...")

        for c_file in c_files:
            try:
                # Read file content
                with open(c_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                relative_path = c_file.relative_to(self.source_root)

                # Find all multi-line comments
                for match in comment_pattern.finditer(content):
                    comment_text = match.group(1).strip()

                    # Filter out very short comments (likely not documentation)
                    if len(comment_text) < 50:
                        continue

                    # Clean up comment text
                    # Remove leading * from each line (common in C comments)
                    lines = comment_text.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        # Remove leading whitespace and asterisks
                        cleaned_line = re.sub(r'^\s*\*\s?', '', line)
                        cleaned_lines.append(cleaned_line)

                    cleaned_text = '\n'.join(cleaned_lines).strip()

                    # Skip if still too short after cleaning
                    if len(cleaned_text) < 50:
                        continue

                    # Calculate line number
                    line_start = content[:match.start()].count('\n') + 1

                    comments.append({
                        'content': cleaned_text,
                        'file_path': str(c_file),
                        'relative_path': str(relative_path),
                        'line_start': line_start,
                        'type': 'C_COMMENT'
                    })

                if len(comments) % 100 == 0 and len(comments) > 0:
                    logger.info(f"Extracted {len(comments)} comments so far...")

            except Exception as e:
                logger.warning(f"Failed to process {c_file}: {e}")

        logger.info(f"Extracted {len(comments)} multi-line comments from {len(c_files)} files")
        return comments

    def extract_all(self, max_c_files: int = None, output_file: str = None) -> Dict:
        """
        Extract both README files and C comments.

        Args:
            max_c_files: Maximum number of .c files to process (None = all)
            output_file: Optional path to save extracted content as JSON

        Returns:
            Dictionary with 'readme_files' and 'c_comments' lists
        """
        logger.info("Starting extraction of PostgreSQL source code documentation...")

        # Extract READMEs
        readme_files = self.extract_readme_files()

        # Extract C comments
        c_comments = self.extract_c_comments(max_files=max_c_files)

        result = {
            'source_root': str(self.source_root),
            'readme_files': readme_files,
            'c_comments': c_comments,
            'stats': {
                'total_readme_files': len(readme_files),
                'total_c_comments': len(c_comments),
                'total_items': len(readme_files) + len(c_comments)
            }
        }

        # Save to file if requested
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved extracted content to: {output_file}")

        logger.info(f"Extraction complete: {result['stats']['total_items']} items")
        return result

    def convert_to_content_items(self, extraction_result: Dict) -> List[Dict]:
        """
        Convert extracted content to format compatible with content_chunker.py.

        Args:
            extraction_result: Result from extract_all()

        Returns:
            List of content items in format expected by ContentChunker
        """
        content_items = []

        # Convert README files
        for readme in extraction_result['readme_files']:
            content_items.append({
                'title': f"README: {readme['directory']}",
                'url': readme['relative_path'],
                'content': readme['content'],
                'source_type': 'README',
                'metadata': {
                    'file_path': readme['file_path'],
                    'directory': readme['directory']
                }
            })

        # Convert C comments
        for comment in extraction_result['c_comments']:
            # Create a meaningful title
            file_name = Path(comment['relative_path']).name
            title = f"Comment from {file_name}:{comment['line_start']}"

            content_items.append({
                'title': title,
                'url': f"{comment['relative_path']}:{comment['line_start']}",
                'content': comment['content'],
                'source_type': 'C_COMMENT',
                'metadata': {
                    'file_path': comment['file_path'],
                    'relative_path': comment['relative_path'],
                    'line_start': comment['line_start']
                }
            })

        logger.info(f"Converted {len(content_items)} items to content format")
        return content_items


def main():
    """Command-line interface for source code extraction."""
    import argparse

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(
        description='Extract documentation from PostgreSQL source code'
    )
    parser.add_argument(
        '--source-root',
        default=r'C:\Users\user\postgres-REL_17_6\src',
        help='Path to PostgreSQL source root directory'
    )
    parser.add_argument(
        '--max-c-files',
        type=int,
        default=None,
        help='Maximum number of C files to process (default: all)'
    )
    parser.add_argument(
        '--output',
        default='data/pg_source_extracted.json',
        help='Output file for extracted content'
    )
    parser.add_argument(
        '--output-content',
        default='data/pg_source_content.json',
        help='Output file for content items (compatible with chunker)'
    )

    args = parser.parse_args()

    # Create extractor
    extractor = PgSourceCodeExtractor(args.source_root)

    # Extract all content
    result = extractor.extract_all(
        max_c_files=args.max_c_files,
        output_file=args.output
    )

    # Convert to content items format
    content_items = extractor.convert_to_content_items(result)

    # Save content items
    with open(args.output_content, 'w', encoding='utf-8') as f:
        json.dump(content_items, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(content_items)} content items to: {args.output_content}")

    # Print statistics
    print("\n" + "="*60)
    print("EXTRACTION STATISTICS")
    print("="*60)
    print(f"Source root:        {args.source_root}")
    print(f"README files:       {result['stats']['total_readme_files']}")
    print(f"C comments:         {result['stats']['total_c_comments']}")
    print(f"Total items:        {result['stats']['total_items']}")
    print(f"\nOutput files:")
    print(f"  Raw extraction:   {args.output}")
    print(f"  Content items:    {args.output_content}")
    print("="*60)

    # Show sample README paths
    if result['readme_files']:
        print("\nSample README files:")
        for readme in result['readme_files'][:5]:
            print(f"  - {readme['relative_path']}")
        if len(result['readme_files']) > 5:
            print(f"  ... and {len(result['readme_files']) - 5} more")

    # Show sample comment locations
    if result['c_comments']:
        print("\nSample C comment locations:")
        for comment in result['c_comments'][:5]:
            print(f"  - {comment['relative_path']}:{comment['line_start']}")
        if len(result['c_comments']) > 5:
            print(f"  ... and {len(result['c_comments']) - 5} more")

    print("\nNext steps:")
    print(f"  1. Chunk content:        python content_chunker.py --input {args.output_content}")
    print(f"  2. Generate Q&A pairs:   python generate_qa_from_chunks.py --qa-per-chunk 2")


if __name__ == '__main__':
    main()
