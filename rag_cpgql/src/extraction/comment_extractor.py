"""
Extract comments and documentation from Joern CPG.

This module queries the CPG to extract:
- Method-level comments (docstrings, header comments)
- Inline comments associated with code blocks
- File-level documentation
- Function signature documentation

The extracted documentation is stored in a structured format for ChromaDB indexing.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import re

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.execution.joern_client import JoernClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CommentExtractor:
    """Extract and structure documentation from Joern CPG."""

    def __init__(self, joern_client: JoernClient):
        """Initialize with Joern client.

        Args:
            joern_client: Initialized Joern client connected to CPG
        """
        self.client = joern_client

    def extract_method_comments(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Extract comments associated with methods.

        Args:
            limit: Optional limit on number of methods to process

        Returns:
            List of dicts with structure:
            {
                'method_name': str,
                'file_path': str,
                'signature': str,
                'comment': str,
                'line_number': int,
                'code_snippet': str
            }
        """
        logger.info("Extracting method-level comments from CPG...")

        # Query to get methods with their associated comments
        # Comments are linked via AST edges and accessed through _astOut
        query = """
        cpg.method
          .filter(m => m._astOut.l.exists(_.label == "COMMENT"))
          .map { m =>
            val file = m.file.name.headOption.getOrElse("unknown")
            val signature = m.signature
            val name = m.name
            val lineNumber = m.lineNumber.getOrElse(0)
            val code = m.code.take(500)
            val commentNodes = m._astOut.l.filter(_.label == "COMMENT")
            val commentTexts = commentNodes.flatMap { c =>
              Try(c.property("CODE").toString).toOption
            }.mkString("|||")

            s"METHOD_DOC###$name###$file###$signature###$lineNumber###$commentTexts###$code"
          }
        """.strip()

        if limit:
            query += f".take({limit})"

        query += ".l"

        result = self.client.execute_query(query)

        if not result['success']:
            logger.error(f"Failed to extract method comments: {result.get('error')}")
            return []

        # Parse results
        methods_with_comments = []
        raw_results = result.get('result', '').strip().split('\n')

        for line in raw_results:
            if not line or 'res' in line[:10] or not 'METHOD_DOC###' in line:
                continue

            parts = line.split('###')
            if len(parts) < 7:
                continue

            # Extract components
            try:
                idx = parts.index('METHOD_DOC') if 'METHOD_DOC' in parts else 0
                if idx + 6 < len(parts):
                    name = parts[idx + 1]
                    file_path = parts[idx + 2]
                    signature = parts[idx + 3]
                    line_num = parts[idx + 4]
                    comment = parts[idx + 5]
                    code = parts[idx + 6] if idx + 6 < len(parts) else ""

                    # Only include methods with actual comments
                    if comment and comment.strip() and len(comment.strip()) > 5:
                        methods_with_comments.append({
                            'method_name': name,
                            'file_path': file_path.replace('\\\\', '/'),
                            'signature': signature,
                            'comment': comment.replace('|||', '\n').strip(),
                            'line_number': int(line_num) if line_num.isdigit() else 0,
                            'code_snippet': code[:500]
                        })
            except (ValueError, IndexError) as e:
                logger.debug(f"Skipping malformed line: {e}")
                continue

        logger.info(f"Extracted {len(methods_with_comments)} methods with comments")
        return methods_with_comments

    def extract_file_comments(self) -> List[Dict[str, Any]]:
        """Extract file-level documentation (header comments).

        Returns:
            List of dicts with structure:
            {
                'file_path': str,
                'header_comment': str,
                'description': str
            }
        """
        logger.info("Extracting file-level comments from CPG...")

        # Query for file-level comments via AST edges
        query = """
        cpg.file
          .filter(f => f._astOut.l.exists(_.label == "COMMENT"))
          .map { f =>
            val filePath = f.name
            val commentNodes = f._astOut.l.filter(_.label == "COMMENT")
            val commentTexts = commentNodes.flatMap { c =>
              Try(c.property("CODE").toString).toOption
            }.mkString("|||")

            s"FILE_DOC###$filePath###$commentTexts"
          }
          .l
        """.strip()

        result = self.client.execute_query(query)

        if not result['success']:
            logger.error(f"Failed to extract file comments: {result.get('error')}")
            return []

        # Parse results
        files_with_comments = []
        raw_results = result.get('result', '').strip().split('\n')

        for line in raw_results:
            if not line or 'res' in line[:10] or not 'FILE_DOC###' in line:
                continue

            parts = line.split('###')
            if len(parts) < 3:
                continue

            try:
                idx = parts.index('FILE_DOC') if 'FILE_DOC' in parts else 0
                if idx + 2 < len(parts):
                    file_path = parts[idx + 1]
                    comment = parts[idx + 2]

                    if comment and comment.strip() and len(comment.strip()) > 10:
                        # Extract description from comment (first paragraph typically)
                        full_comment = comment.replace('|||', '\n')
                        description = self._extract_description(full_comment)

                        files_with_comments.append({
                            'file_path': file_path.replace('\\\\', '/'),
                            'header_comment': full_comment.strip(),
                            'description': description
                        })
            except (ValueError, IndexError) as e:
                logger.debug(f"Skipping malformed file comment line: {e}")
                continue

        logger.info(f"Extracted {len(files_with_comments)} files with header comments")
        return files_with_comments

    def extract_inline_comments(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Extract inline comments from code blocks.

        Args:
            limit: Optional limit on number of comments to extract

        Returns:
            List of dicts with structure:
            {
                'file_path': str,
                'line_number': int,
                'comment': str,
                'context_code': str,
                'parent_method': str
            }
        """
        logger.info("Extracting inline comments from CPG...")

        # Query for all comment nodes with their context
        query = """
        cpg.comment
          .map { c =>
            val file = c.file.name.headOption.getOrElse("unknown")
            val lineNum = c.lineNumber.getOrElse(0)
            val text = c.code
            val parentMethod = c.method.name.headOption.getOrElse("global")
            val context = c.astParent.code.headOption.getOrElse("")

            s"INLINE_COMMENT||$file||$lineNum||$text||$parentMethod||$context"
          }
        """.strip()

        if limit:
            query += f".take({limit})"

        query += ".l"

        result = self.client.execute_query(query)

        if not result['success']:
            logger.error(f"Failed to extract inline comments: {result.get('error')}")
            return []

        # Parse results
        inline_comments = []
        raw_results = result.get('result', '').strip().split('\n')

        for line in raw_results:
            if not line or line == 'res' or not line.startswith('INLINE_COMMENT'):
                continue

            parts = line.split('||', 5)
            if len(parts) < 6:
                continue

            _, file_path, line_num, comment, parent_method, context = parts

            if comment and comment.strip():
                inline_comments.append({
                    'file_path': file_path,
                    'line_number': int(line_num) if line_num.isdigit() else 0,
                    'comment': comment.strip(),
                    'context_code': context[:200],  # First 200 chars of context
                    'parent_method': parent_method
                })

        logger.info(f"Extracted {len(inline_comments)} inline comments")
        return inline_comments

    def _extract_description(self, comment: str) -> str:
        """Extract a concise description from a comment block.

        Args:
            comment: Full comment text

        Returns:
            First meaningful sentence or paragraph
        """
        # Remove comment markers
        clean = re.sub(r'/\*+|\*+/|//|/\*|\*/|\*', ' ', comment)
        clean = clean.strip()

        # Get first paragraph (up to double newline or first 200 chars)
        paragraphs = clean.split('\n\n')
        if paragraphs:
            first_para = paragraphs[0].replace('\n', ' ').strip()
            if len(first_para) > 200:
                # Truncate at sentence boundary
                sentences = first_para.split('. ')
                return sentences[0] + '.' if sentences else first_para[:200] + '...'
            return first_para

        return clean[:200] + '...' if len(clean) > 200 else clean

    def extract_all(self, method_limit: Optional[int] = None) -> Dict[str, Any]:
        """Extract all documentation from CPG.

        Args:
            method_limit: Optional limit on methods processed

        Returns:
            Dict with keys: 'methods', 'files', 'inline_comments', 'stats'
        """
        logger.info("Starting full documentation extraction...")

        method_docs = self.extract_method_comments(limit=method_limit)
        file_docs = self.extract_file_comments()
        inline_comments = self.extract_inline_comments(limit=method_limit)

        stats = {
            'total_method_docs': len(method_docs),
            'total_file_docs': len(file_docs),
            'total_inline_comments': len(inline_comments),
            'total_documentation_entries': len(method_docs) + len(file_docs) + len(inline_comments)
        }

        logger.info(f"Extraction complete: {stats}")

        return {
            'methods': method_docs,
            'files': file_docs,
            'inline_comments': inline_comments,
            'stats': stats
        }

    def save_to_json(self, output_path: str, data: Dict[str, Any]) -> None:
        """Save extracted documentation to JSON file.

        Args:
            output_path: Path to output JSON file
            data: Documentation data from extract_all()
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved documentation to {output_path}")


def main():
    """Main entry point for comment extraction."""
    import argparse

    parser = argparse.ArgumentParser(description='Extract documentation from Joern CPG')
    parser.add_argument('--output', default='data/cpg_documentation.json',
                       help='Output JSON file path')
    parser.add_argument('--method-limit', type=int, default=None,
                       help='Limit number of methods to process (for testing)')
    parser.add_argument('--joern-host', default='localhost',
                       help='Joern server host')
    parser.add_argument('--joern-port', type=int, default=8080,
                       help='Joern server port')

    args = parser.parse_args()

    # Initialize Joern client
    server_endpoint = f"{args.joern_host}:{args.joern_port}"
    logger.info(f"Connecting to Joern at {server_endpoint}...")
    client = JoernClient(server_endpoint=server_endpoint)

    # Connect and test
    if not client.connect():
        logger.error("Failed to connect to Joern server")
        sys.exit(1)

    test_result = client.execute_query("cpg.method.name.take(1).l")
    if not test_result['success']:
        logger.error(f"Connection test failed: {test_result.get('error')}")
        sys.exit(1)

    logger.info("Connected successfully to Joern CPG")

    # Extract documentation
    extractor = CommentExtractor(client)
    documentation = extractor.extract_all(method_limit=args.method_limit)

    # Save to file
    extractor.save_to_json(args.output, documentation)

    # Print summary
    print("\n" + "="*60)
    print("Documentation Extraction Summary")
    print("="*60)
    for key, value in documentation['stats'].items():
        print(f"{key}: {value:,}")
    print("="*60)


if __name__ == '__main__':
    main()
