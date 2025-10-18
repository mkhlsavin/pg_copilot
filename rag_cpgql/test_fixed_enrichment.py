"""Test fixed enrichment with real CPG tags."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.enrichment_agent import EnrichmentAgent
from src.agents.analyzer_agent import AnalyzerAgent

def test_mvcc_question():
    """Test MVCC question with fixed enrichment."""
    question = "How does PostgreSQL handle visibility checks for BRIN index entries to ensure consistency with MVCC semantics?"

    # Analyze question
    analyzer = AnalyzerAgent()
    analysis = analyzer.analyze(question)

    print(f"Question: {question[:80]}...")
    print(f"\nAnalysis:")
    print(f"  Domain: {analysis['domain']}")
    print(f"  Intent: {analysis['intent']}")
    print(f"  Keywords: {analysis['keywords']}")

    # Get enrichment hints
    enrichment = EnrichmentAgent()
    hints = enrichment.get_enrichment_hints(question, analysis)

    print(f"\nEnrichment Hints:")
    print(f"  Function purposes: {hints['function_purposes']}")
    print(f"  Data structures: {hints['data_structures']}")
    print(f"  Domain concepts: {hints['domain_concepts']}")
    print(f"  Features: {hints['features']}")
    print(f"  Coverage: {hints['coverage_score']:.2f}")

    print(f"\nGenerated Tag Filters:")
    for i, tag in enumerate(hints['tags'][:5], 1):
        print(f"  {i}. {tag['tag_name']}:{tag['tag_value']}")
        print(f"     Query: cpg.method.where({tag['query_fragment']}).name.l")

    # Test queries with Joern
    print(f"\n{'='*80}")
    print("Testing queries with Joern...")
    print(f"{'='*80}\n")

    from src.execution.joern_client import JoernClient

    client = JoernClient()
    client.connect()

    for i, tag in enumerate(hints['tags'][:3], 1):
        query = f"cpg.method.where({tag['query_fragment']}).name.l.take(5)"
        print(f"Query {i}: {query}")

        result = client.execute_query(query)
        if result['success']:
            lines = result['result'].split('\n')
            # Show first few lines
            for line in lines[:10]:
                print(f"  {line}")
        else:
            print(f"  ERROR: {result.get('error', 'Unknown error')}")
        print()

    client.disconnect()

    print(f"\n{'='*80}")
    print("✅ Test completed successfully!")
    print(f"{'='*80}")

if __name__ == "__main__":
    test_mvcc_question()
