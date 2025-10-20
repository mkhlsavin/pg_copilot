"""
CFG Pattern Retriever

High-level API for retrieving relevant CFG patterns for query enrichment.
Integrates with AnalyzerAgent to provide execution flow context.

Based on: PHASE2_CFG_PATTERN_DESIGN.md
"""

import logging
from typing import Dict, List, Optional

from src.retrieval.cfg_vector_store import CFGVectorStore

logger = logging.getLogger(__name__)


class CFGRetriever:
    """Retrieve relevant CFG patterns for query enrichment."""

    def __init__(self, persist_directory: str = "chromadb_storage"):
        """Initialize CFG retriever."""
        self.vector_store = CFGVectorStore(persist_directory=persist_directory)
        self.vector_store.initialize(collection_name="cfg_patterns")
        self.logger = logging.getLogger(__name__)

    def retrieve_relevant_patterns(self, question: str, analysis: Dict,
                                   top_k: int = 5) -> Dict:
        """
        Retrieve CFG patterns relevant to the question.

        Args:
            question: User's question
            analysis: AnalyzerAgent analysis with domain, keywords, intent
            top_k: Number of patterns to retrieve

        Returns:
            Dict with patterns, statistics, and formatted summary
        """
        try:
            # Build enhanced query from question + analysis
            query = self._build_search_query(question, analysis)

            # Search for patterns
            results = self.vector_store.search_patterns(
                query=query,
                n_results=top_k
            )

            # Calculate relevance scores (convert distance to similarity)
            patterns_with_scores = []
            for pattern in results['patterns']:
                # ChromaDB uses L2 distance, convert to similarity score
                distance = pattern.get('distance', 1.0)
                # Lower distance = higher relevance
                # Use exponential decay: relevance = e^(-distance)
                import math
                relevance = math.exp(-distance) if distance else 1.0

                pattern_info = {
                    'pattern_type': pattern['metadata']['pattern_type'],
                    'method_name': pattern['metadata']['method_name'],
                    'file_path': pattern['metadata']['file_path'],
                    'line_number': int(pattern['metadata']['line_number']),
                    'description': self._extract_description(pattern['text']),
                    'condition': self._extract_condition(pattern['text']),
                    'relevance': relevance,
                    'distance': distance
                }
                patterns_with_scores.append(pattern_info)

            # Sort by relevance (highest first)
            patterns_with_scores.sort(key=lambda x: x['relevance'], reverse=True)

            # Calculate statistics
            avg_relevance = sum(p['relevance'] for p in patterns_with_scores) / len(patterns_with_scores) if patterns_with_scores else 0.0
            top_relevance = patterns_with_scores[0]['relevance'] if patterns_with_scores else 0.0

            # Format summary for prompt
            summary = self._format_pattern_summary(patterns_with_scores)

            return {
                'patterns': patterns_with_scores,
                'stats': {
                    'count': len(patterns_with_scores),
                    'avg_relevance': avg_relevance,
                    'top_relevance': top_relevance,
                    'query': query
                },
                'summary': summary
            }

        except Exception as e:
            self.logger.error(f"Error retrieving CFG patterns: {e}", exc_info=True)
            return {
                'patterns': [],
                'stats': {'count': 0, 'avg_relevance': 0.0, 'top_relevance': 0.0, 'error': str(e)},
                'summary': ''
            }

    def _build_search_query(self, question: str, analysis: Dict) -> str:
        """Build enhanced search query from question and analysis."""
        # Extract key information from analysis
        domain = analysis.get('domain', '')
        keywords = analysis.get('keywords', [])
        intent = analysis.get('intent', '')

        # Build query parts
        query_parts = [question]

        # Add domain context
        if domain:
            query_parts.append(f"domain: {domain}")

        # Add important keywords
        if keywords:
            key_keywords = keywords[:5]  # Top 5 keywords
            query_parts.append(f"keywords: {' '.join(key_keywords)}")

        # Add intent hint
        if intent:
            if 'how' in intent or 'explain' in intent:
                query_parts.append("execution flow control flow")
            elif 'error' in intent or 'check' in intent:
                query_parts.append("error handling validation")
            elif 'lock' in intent or 'concurrency' in intent:
                query_parts.append("lock synchronization")
            elif 'transaction' in intent:
                query_parts.append("transaction boundary commit abort")

        return " ".join(query_parts)

    def _extract_description(self, text: str) -> str:
        """Extract description from pattern text."""
        # Description is typically the last line
        lines = text.strip().split('\n')
        for line in reversed(lines):
            if line.startswith('Description:'):
                return line.replace('Description:', '').strip()

        # If no description found, return first meaningful line
        return lines[0] if lines else ""

    def _extract_condition(self, text: str) -> Optional[str]:
        """Extract condition from pattern text if present."""
        for line in text.split('\n'):
            if line.startswith('Condition:') or line.startswith('Validates:'):
                return line.split(':', 1)[1].strip() if ':' in line else None
        return None

    def _format_pattern_summary(self, patterns: List[Dict]) -> str:
        """Format CFG patterns into summary text for prompt enrichment."""
        if not patterns:
            return ""

        summary_parts = ["## Execution Flow Patterns\n"]

        for i, pattern in enumerate(patterns, 1):
            ptype = pattern['pattern_type'].replace('_', ' ').title()
            method = pattern['method_name']
            description = pattern['description']

            summary_parts.append(f"**{i}. {ptype}** in `{method}`:")
            summary_parts.append(f"   - {description}")

            # Add condition if available
            if pattern.get('condition'):
                condition = pattern['condition']
                summary_parts.append(f"   - Condition: `{condition}`")

            # Add location
            file_path = pattern['file_path']
            line_num = pattern['line_number']
            summary_parts.append(f"   - Location: {file_path}:{line_num}")

            # Add relevance indicator
            relevance_pct = pattern['relevance'] * 100
            if relevance_pct >= 30:
                summary_parts.append(f"   - Relevance: {relevance_pct:.1f}% (HIGH)")
            elif relevance_pct >= 20:
                summary_parts.append(f"   - Relevance: {relevance_pct:.1f}% (MEDIUM)")

            summary_parts.append("")  # Blank line

        return "\n".join(summary_parts)

    def search_by_pattern_type(self, question: str, pattern_type: str,
                               top_k: int = 3) -> Dict:
        """
        Search for specific pattern type.

        Args:
            question: User's question
            pattern_type: Pattern type to filter (control_structure, error_handling, etc.)
            top_k: Number of results

        Returns:
            Dict with filtered patterns
        """
        results = self.vector_store.search_patterns(
            query=question,
            n_results=top_k,
            pattern_type_filter=pattern_type
        )

        # Format results
        patterns = []
        for pattern in results['patterns']:
            patterns.append({
                'pattern_type': pattern['metadata']['pattern_type'],
                'method_name': pattern['metadata']['method_name'],
                'file_path': pattern['metadata']['file_path'],
                'line_number': int(pattern['metadata']['line_number']),
                'text': pattern['text']
            })

        return {
            'patterns': patterns,
            'pattern_type': pattern_type,
            'count': len(patterns)
        }


def main():
    """CLI interface for CFG retriever."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="CFG Pattern Retriever")
    parser.add_argument('--question', required=True, help='Question to search for')
    parser.add_argument('--top-k', type=int, default=5, help='Number of results')
    parser.add_argument('--pattern-type', help='Filter by pattern type')

    args = parser.parse_args()

    # Initialize retriever
    retriever = CFGRetriever()

    # Mock analysis (in production, this comes from AnalyzerAgent)
    analysis = {
        'domain': 'storage',
        'keywords': ['heap', 'tuple', 'visibility'],
        'intent': 'explain-mechanism'
    }

    # Retrieve patterns
    if args.pattern_type:
        results = retriever.search_by_pattern_type(
            question=args.question,
            pattern_type=args.pattern_type,
            top_k=args.top_k
        )
    else:
        results = retriever.retrieve_relevant_patterns(
            question=args.question,
            analysis=analysis,
            top_k=args.top_k
        )

    # Display results
    print(f"\nQuestion: {args.question}\n")

    if 'summary' in results:
        print(results['summary'])
        print("\nStatistics:")
        print(f"  Patterns found: {results['stats']['count']}")
        print(f"  Avg relevance: {results['stats']['avg_relevance']:.3f}")
        print(f"  Top relevance: {results['stats']['top_relevance']:.3f}")
    else:
        print(f"Found {results['count']} patterns:\n")
        for pattern in results['patterns']:
            print(f"- {pattern['pattern_type']} in {pattern['method_name']}")
            print(f"  {pattern['file_path']}:{pattern['line_number']}")
            print()

    return 0


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
