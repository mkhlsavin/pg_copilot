"""
Extract comments and documentation from Joern CPG - Version 4.

BATCHED VERSION: Queries methods in small batches to avoid output truncation.
The Joern server returns huge List[String] outputs that get truncated, so we
process 100 methods at a time.
"""

import sys
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

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

    def extract_method_comments(self, limit: Optional[int] = 100, offset: int = 0, batch_size: int = 100) -> List[Dict[str, Any]]:
        """Extract comments associated with methods in batches.

        Args:
            limit: Total number of methods to process
            offset: Starting offset in the method list
            batch_size: Number of methods to query in each batch

        Returns:
            List of method documentation dicts
        """
        logger.info(f"Extracting method-level comments from CPG (limit={limit}, offset={offset}, batch_size={batch_size})...")

        # Query using drop() and take() for pagination
        query = f"""
        cpg.method
          .filter(m => m._astOut.l.exists(_.label == "COMMENT"))
          .drop({offset})
          .take({batch_size})
          .map {{ m =>
            val file = m.file.name.headOption.getOrElse("unknown")
            val name = m.name
            val lineNumber = m.lineNumber.getOrElse(0)
            val commentNodes = m._astOut.l.filter(_.label == "COMMENT")
            val commentText = commentNodes.map(_.property("CODE").toString).mkString(" ")

            s"$name|||$file|||$lineNumber|||$commentText"
          }}.l
        """.strip()

        result = self.client.execute_query(query)

        # Parse output regardless of 'success' flag (it's incorrectly set for List results)
        raw_output = result.get('result', '') or result.get('error', '')

        return self._parse_method_results(raw_output)

    def _parse_method_results(self, raw_output: str) -> List[Dict[str, Any]]:
        """Parse Scala List[String] output into Python dicts."""
        methods = []

        # Extract strings from List(...) format
        # Match pattern: """string content"""
        pattern = r'"""((?:[^"]|"")*?)"""'
        matches = re.findall(pattern, raw_output, re.DOTALL)

        for match in matches:
            # Parse our custom format: name|||file|||line|||comment
            parts = match.split('|||')
            if len(parts) >= 4:
                name, file_path, line_num, comment = parts[0], parts[1], parts[2], '|||'.join(parts[3:])

                if comment and len(comment.strip()) > 10:
                    methods.append({
                        'method_name': name.strip(),
                        'file_path': file_path.replace('\\\\', '/').replace('\\', '/'),
                        'line_number': int(line_num) if line_num.isdigit() else 0,
                        'comment': comment.strip(),
                        'description': self._extract_description(comment)
                    })

        logger.info(f"Extracted {len(methods)} methods with comments in this batch")
        return methods

    def _extract_description(self, comment: str) -> str:
        """Extract first sentence/paragraph from comment."""
        # Remove comment markers
        clean = re.sub(r'/\*+|\*+/|//|/\*|\*/|\*', ' ', comment)
        clean = clean.strip()

        # Get first paragraph
        paragraphs = clean.split('\n\n')
        if paragraphs:
            first_para = paragraphs[0].replace('\n', ' ').strip()
            if len(first_para) > 200:
                sentences = first_para.split('. ')
                return sentences[0] + '.' if sentences else first_para[:200] + '...'
            return first_para

        return clean[:200] + '...' if len(clean) > 200 else clean

    def extract_all_batched(self, total_limit: int = 1000, batch_size: int = 100) -> Dict[str, Any]:
        """Extract all documentation from CPG using batched queries.

        Args:
            total_limit: Total number of methods to process
            batch_size: Number of methods per batch query

        Returns:
            Dict with keys: 'methods', 'stats'
        """
        logger.info(f"Starting batched documentation extraction (total={total_limit}, batch_size={batch_size})...")

        all_methods = []
        offset = 0
        empty_batches = 0
        max_empty_batches = 3  # Stop if we get 3 empty batches in a row

        while offset < total_limit:
            remaining = total_limit - offset
            current_batch_size = min(batch_size, remaining)

            logger.info(f"Fetching batch: offset={offset}, size={current_batch_size}")

            batch_methods = self.extract_method_comments(
                limit=current_batch_size,
                offset=offset,
                batch_size=current_batch_size
            )

            if not batch_methods:
                empty_batches += 1
                logger.warning(f"Empty batch at offset {offset} (count: {empty_batches})")
                if empty_batches >= max_empty_batches:
                    logger.info(f"Stopping after {empty_batches} consecutive empty batches")
                    break
            else:
                empty_batches = 0  # Reset counter
                all_methods.extend(batch_methods)

            offset += current_batch_size

        stats = {
            'total_method_docs': len(all_methods),
            'total_documentation_entries': len(all_methods),
            'batches_processed': offset // batch_size,
            'final_offset': offset
        }

        logger.info(f"Extraction complete: {stats}")

        return {
            'methods': all_methods,
            'stats': stats
        }

    def save_to_json(self, output_path: str, data: Dict[str, Any]) -> None:
        """Save extracted documentation to JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved documentation to {output_path}")


def main():
    """Main entry point for comment extraction."""
    import argparse

    parser = argparse.ArgumentParser(description='Extract documentation from Joern CPG (v4 - batched)')
    parser.add_argument('--output', default='data/cpg_documentation.json',
                       help='Output JSON file path')
    parser.add_argument('--total-limit', type=int, default=1000,
                       help='Total number of methods to process')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Number of methods per batch')
    parser.add_argument('--joern-host', default='localhost',
                       help='Joern server host')
    parser.add_argument('--joern-port', type=int, default=8080,
                       help='Joern server port')

    args = parser.parse_args()

    # Initialize Joern client
    server_endpoint = f"{args.joern_host}:{args.joern_port}"
    logger.info(f"Connecting to Joern at {server_endpoint}...")
    client = JoernClient(server_endpoint=server_endpoint)

    # Connect
    if not client.connect():
        logger.error("Failed to connect to Joern server")
        sys.exit(1)

    logger.info("Connected successfully to Joern CPG")

    # Extract documentation
    extractor = CommentExtractor(client)
    documentation = extractor.extract_all_batched(
        total_limit=args.total_limit,
        batch_size=args.batch_size
    )

    # Save to file
    extractor.save_to_json(args.output, documentation)

    # Print summary
    print("\n" + "="*60)
    print("Documentation Extraction Summary (v4 - batched)")
    print("="*60)
    for key, value in documentation['stats'].items():
        print(f"{key}: {value:,}")
    print("="*60)

    # Show sample
    if documentation['methods']:
        print("\nSample extracted methods:")
        for i, sample in enumerate(documentation['methods'][:3], 1):
            print(f"\n{i}. Method: {sample['method_name']}")
            print(f"   File: {sample['file_path']}:{sample['line_number']}")
            print(f"   Description: {sample['description'][:100]}...")
    print("="*60)


if __name__ == '__main__':
    main()
