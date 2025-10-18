"""Debug script to see actual prompt sent to LLM."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.analyzer_agent import AnalyzerAgent
from src.agents.enrichment_agent import EnrichmentAgent
from src.generation.cpgql_generator import CPGQLGenerator
from src.generation.llm_interface import LLMInterface

def debug_prompt():
    """Show the actual prompt sent to LLM."""

    question = "How does PostgreSQL handle visibility checks for BRIN index entries?"

    # Analyze
    analyzer = AnalyzerAgent()
    analysis = analyzer.analyze(question)

    # Get enrichment
    enrichment = EnrichmentAgent()
    hints = enrichment.get_enrichment_hints(question, analysis)

    # Format hints for generator (this is what's passed to CPGQLGenerator)
    formatted_hints = f"Purposes: {', '.join(hints['function_purposes'][:3])}"
    if hints['domain_concepts']:
        formatted_hints += f" | Top tag: _.tag.nameExact(\"domain-concept\").valueExact(\"{hints['domain_concepts'][0]}\")"

    print("="*80)
    print("FORMATTED HINTS PASSED TO GENERATOR:")
    print("="*80)
    print(formatted_hints)
    print()

    # Initialize generator (but don't load LLM - just get the prompt)
    from src.generation.cpgql_generator import CPGQLGenerator

    # Create a mock generator just to build the prompt
    class MockLLM:
        pass

    mock_gen = CPGQLGenerator(MockLLM(), use_grammar=False)

    # Build the prompt that would be sent to LLM
    prompt = mock_gen._build_prompt(question, formatted_hints)

    print("="*80)
    print("ACTUAL PROMPT SENT TO LLM:")
    print("="*80)
    print(prompt)
    print()
    print("="*80)
    print("ANALYSIS:")
    print("="*80)
    print(f"Prompt length: {len(prompt)} chars")
    print(f"Contains 'IMPORTANT': {'Yes' if 'IMPORTANT' in prompt else 'No'}")
    print(f"Contains tag examples: {'Yes' if 'tag.nameExact' in prompt else 'No'}")
    print(f"Number of tag examples: {prompt.count('tag.nameExact')}")
    print(f"Contains enrichment hints: {'Yes' if formatted_hints and formatted_hints in prompt else 'No'}")

if __name__ == "__main__":
    debug_prompt()
