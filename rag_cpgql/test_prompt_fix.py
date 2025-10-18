"""Test that fixed prompt generates tag-based queries."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.analyzer_agent import AnalyzerAgent
from src.agents.enrichment_agent import EnrichmentAgent
from src.generation.cpgql_generator import CPGQLGenerator
from src.generation.llm_interface import LLMInterface

def test_prompt_generates_tags():
    """Test that LLM generates tag-based queries with new prompt."""

    # Simple MVCC question
    question = "How does PostgreSQL handle visibility checks for BRIN index entries?"

    # Analyze
    analyzer = AnalyzerAgent()
    analysis = analyzer.analyze(question)
    print(f"Question: {question}")
    print(f"Domain: {analysis['domain']}")
    print(f"Intent: {analysis['intent']}")

    # Get enrichment
    enrichment = EnrichmentAgent()
    hints = enrichment.get_enrichment_hints(question, analysis)
    print(f"\nEnrichment coverage: {hints['coverage_score']:.2f}")
    print(f"Tags generated: {len(hints['tags'])}")

    # Format hints for generator
    formatted_hints = f"function-purpose: {', '.join(hints['function_purposes'][:3])}"
    if hints['domain_concepts']:
        formatted_hints += f"\ndomain-concept: {', '.join(hints['domain_concepts'][:3])}"

    print(f"\nFormatted hints:\n{formatted_hints}")

    # Initialize LLM and generator (use default Qwen3-Coder model)
    print("\nInitializing LLM...")
    llm = LLMInterface(
        use_llmxcpg=False,  # Use Qwen3-Coder
        verbose=False
    )

    generator = CPGQLGenerator(llm, use_grammar=True)

    # Generate query
    print("\nGenerating query with fixed prompt...")
    query = generator.generate_query(
        question=question,
        enrichment_hints=formatted_hints,
        max_tokens=200,
        temperature=0.3
    )

    print(f"\nGenerated query:\n{query}")

    # Check if query uses tags
    uses_tags = '.tag.nameExact(' in query
    print(f"\n{'✅ SUCCESS' if uses_tags else '❌ FAILED'}: Query {'uses' if uses_tags else 'does NOT use'} tags!")

    if uses_tags:
        print("\nThe prompt fix works! LLM is now generating tag-based queries.")
    else:
        print("\nProblem: LLM still generating name-only queries despite prompt fix.")
        print("This may require stronger prompt engineering or more tag examples.")

    return uses_tags

if __name__ == "__main__":
    success = test_prompt_generates_tags()
    sys.exit(0 if success else 1)
