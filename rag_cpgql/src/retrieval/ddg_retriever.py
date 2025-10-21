"""
DDG Pattern Retriever

High-level API for retrieving relevant DDG (Data Dependency Graph) patterns for query enrichment.
Integrates with AnalyzerAgent to provide data flow context.

Based on: PHASE3_DDG_API_FINDINGS.md, PHASE3_SUMMARY.md
"""

import logging
from typing import Dict, List, Optional

from src.retrieval.ddg_vector_store import DDGVectorStore

logger = logging.getLogger(__name__)


class DDGRetriever:
    """Retrieve relevant DDG patterns for query enrichment."""

    def __init__(self, persist_directory: str = "chromadb_storage"):
        """Initialize DDG retriever."""
        self.vector_store = DDGVectorStore(persist_directory=persist_directory)
        self.vector_store.initialize(collection_name="ddg_patterns")
        self.logger = logging.getLogger(__name__)

    def retrieve_relevant_patterns(self, question: str, analysis: Dict,
                                   top_k: int = 5) -> Dict:
        """
        Retrieve DDG patterns relevant to the question.

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
                    'flow_info': self._extract_flow_info(pattern['text']),
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
            self.logger.error(f"Error retrieving DDG patterns: {e}", exc_info=True)
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

        # Add intent hint for data flow queries
        if intent:
            if 'where' in intent or 'flow' in intent:
                query_parts.append("parameter flow data flow variable tracking")
            elif 'trace' in intent or 'track' in intent:
                query_parts.append("data dependency variable chain")
            elif 'return' in intent or 'value' in intent:
                query_parts.append("return source value flow")
            elif 'argument' in intent or 'call' in intent:
                query_parts.append("call argument source data reaching")
            elif 'control' in intent or 'depend' in intent:
                query_parts.append("control dependency conditional")

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

    def _extract_flow_info(self, text: str) -> Optional[Dict]:
        """Extract data flow information from pattern text."""
        flow_info = {}

        for line in text.split('\n'):
            if line.startswith('Parameter:'):
                flow_info['parameter'] = line.split(':', 1)[1].strip() if ':' in line else None
            elif line.startswith('Flows to:'):
                flow_info['flows_to'] = line.split(':', 1)[1].strip() if ':' in line else None
            elif line.startswith('Variable flow:'):
                flow_info['variable_flow'] = line.split(':', 1)[1].strip() if ':' in line else None
            elif line.startswith('Source:'):
                flow_info['source'] = line.split(':', 1)[1].strip() if ':' in line else None
            elif line.startswith('Call:'):
                flow_info['call'] = line.split(':', 1)[1].strip() if ':' in line else None

        return flow_info if flow_info else None

    def _format_pattern_summary(self, patterns: List[Dict]) -> str:
        """Format DDG patterns into summary text for prompt enrichment."""
        if not patterns:
            return ""

        summary_parts = ["## Data Flow Patterns\n"]

        for i, pattern in enumerate(patterns, 1):
            ptype = pattern['pattern_type'].replace('_', ' ').title()
            method = pattern['method_name']
            description = pattern['description']

            summary_parts.append(f"**{i}. {ptype}** in `{method}`:")
            summary_parts.append(f"   - {description}")

            # Add flow information if available
            if pattern.get('flow_info'):
                flow = pattern['flow_info']
                if flow.get('parameter'):
                    summary_parts.append(f"   - Parameter: `{flow['parameter']}`")
                if flow.get('flows_to'):
                    summary_parts.append(f"   - Flows to: {flow['flows_to']}")
                if flow.get('variable_flow'):
                    summary_parts.append(f"   - Variable flow: {flow['variable_flow']}")
                if flow.get('source'):
                    summary_parts.append(f"   - Source: {flow['source']}")
                if flow.get('call'):
                    summary_parts.append(f"   - Call: `{flow['call']}`")

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
            pattern_type: Pattern type to filter (parameter_flow, variable_chain, etc.)
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
    """CLI interface for DDG retriever."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="DDG Pattern Retriever")
    parser.add_argument('--question', required=True, help='Question to search for')
    parser.add_argument('--top-k', type=int, default=5, help='Number of results')
    parser.add_argument('--pattern-type', help='Filter by pattern type')

    args = parser.parse_args()

    # Initialize retriever
    retriever = DDGRetriever()

    # Mock analysis (in production, this comes from AnalyzerAgent)
    analysis = {
        'domain': 'storage',
        'keywords': ['relation', 'parameter', 'tuple', 'data'],
        'intent': 'trace-data-flow'
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
