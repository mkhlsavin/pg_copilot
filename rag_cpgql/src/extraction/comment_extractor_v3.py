"""
Extract comments and documentation from Joern CPG - Version 3.

Simplified version that parses Scala List output directly, bypassing JoernClient's
incorrect error detection for successful List[String] results.
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

    def extract_method_comments(self, limit: Optional[int] = 100) -> List[Dict[str, Any]]:
        """Extract comments associated with methods.

        Args:
            limit: Limit on number of methods to process

        Returns:
            List of method documentation dicts
        """
        logger.info("Extracting method-level comments from CPG...")

        # Simpler query using direct property access
        query = f"""
        cpg.method
          .filter(m => m._astOut.l.exists(_.label == "COMMENT"))
          .take({limit})
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
        # Match pattern: "string content"
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

        logger.info(f"Extracted {len(methods)} methods with comments")
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

    def extract_all(self, method_limit: int = 1000) -> Dict[str, Any]:
        """Extract all documentation from CPG.

        Args:
            method_limit: Limit on methods processed

        Returns:
            Dict with keys: 'methods', 'stats'
        """
        logger.info("Starting documentation extraction...")

        method_docs = self.extract_method_comments(limit=method_limit)

        stats = {
            'total_method_docs': len(method_docs),
            'total_documentation_entries': len(method_docs)
        }

        logger.info(f"Extraction complete: {stats}")

        return {
            'methods': method_docs,
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

    parser = argparse.ArgumentParser(description='Extract documentation from Joern CPG (v3)')
    parser.add_argument('--output', default='data/cpg_documentation.json',
                       help='Output JSON file path')
    parser.add_argument('--method-limit', type=int, default=1000,
                       help='Limit number of methods to process')
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
    documentation = extractor.extract_all(method_limit=args.method_limit)

    # Save to file
    extractor.save_to_json(args.output, documentation)

    # Print summary
    print("\n" + "="*60)
    print("Documentation Extraction Summary (v3)")
    print("="*60)
    for key, value in documentation['stats'].items():
        print(f"{key}: {value:,}")
    print("="*60)

    # Show sample
    if documentation['methods']:
        print("\nSample extracted method:")
        sample = documentation['methods'][0]
        print(f"  Method: {sample['method_name']}")
        print(f"  File: {sample['file_path']}")
        print(f"  Description: {sample['description'][:100]}...")
    print("="*60)


if __name__ == '__main__':
    main()
