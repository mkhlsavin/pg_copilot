#!/usr/bin/env python3
"""
Extended test of LLMxCPG-Q model with v2 grammar.
Tests more complex CPGQL queries and different parameters.
"""

import json
from pathlib import Path
from llama_cpp import Llama, LlamaGrammar

# Paths
MODEL_PATH = Path("C:/Users/user/.lmstudio/models/llmxcpg/LLMxCPG-Q/qwen2.5-coder-32B-instruct-bnb-q5_k_m.gguf")
GRAMMAR_PATH = Path("C:/Users/user/pg_copilot/cpgql_gbnf/cpgql_llama_cpp_v2.gbnf")

def load_grammar():
    """Load GBNF grammar from file."""
    print(f"[1/4] Loading grammar from {GRAMMAR_PATH}...")
    grammar_text = GRAMMAR_PATH.read_text(encoding='utf-8')
    print(f"      Grammar loaded: {len(grammar_text)} characters")
    return LlamaGrammar.from_string(grammar_text)

def load_model():
    """Load GGUF model."""
    print(f"[2/4] Loading LLMxCPG-Q model...")
    print(f"      Model: qwen2.5-coder-32B-instruct (fine-tuned for CPGQL)")
    llm = Llama(
        model_path=str(MODEL_PATH),
        n_ctx=4096,  # Increased context
        n_gpu_layers=-1,
        verbose=False
    )
    print(f"      Model loaded successfully!")
    return llm

def generate_queries(llm, grammar, count=10):
    """Generate CPGQL queries with extended test cases."""
    print(f"[3/4] Generating {count} CPGQL queries...")

    # Extended test prompts with various complexity levels
    prompts = [
        # Simple queries
        "Generate CPGQL query to find all methods. Example: cpg.method.name.l | Query:",
        "Generate CPGQL query to list all function calls. Example: cpg.call.name.l | Query:",

        # Queries with filters
        "Generate CPGQL query to find methods named 'main'. Example: cpg.method.name(\"main\").l | Query:",
        "Generate CPGQL query to find calls to strcpy. Example: cpg.call.name(\"strcpy\").l | Query:",

        # Complex queries with chaining
        "Generate CPGQL query to find callers of memcpy. Example: cpg.method.name(\"memcpy\").caller.name.l | Query:",
        "Generate CPGQL query to find method signatures. Example: cpg.method.signature.l | Query:",

        # Security-focused queries
        "Generate CPGQL query to find vulnerable buffer operations. Example: cpg.call.name(\"memcpy\").argument.code.l | Query:",
        "Generate CPGQL query for control flow analysis. Example: cpg.method.controlledBy.code.l | Query:",

        # Advanced queries
        "Generate CPGQL query to find method parameters. Example: cpg.method.parameter.name.l | Query:",
        "Generate CPGQL query to analyze data flow. Example: cpg.method.name.toList | Query:",
    ]

    queries = []

    # Test with different parameter sets
    param_configs = [
        {"name": "low_temp", "temperature": 0.3, "max_tokens": 200},
        {"name": "medium_temp", "temperature": 0.6, "max_tokens": 200},
        {"name": "high_temp", "temperature": 0.9, "max_tokens": 200},
    ]

    config = param_configs[1]  # Use medium temperature

    for i, prompt in enumerate(prompts[:count], 1):
        task = prompt.split('. Example:')[0].replace('Generate CPGQL query ', '')
        print(f"\n   Query {i}/{count}: {task}")

        output = llm(
            prompt,
            max_tokens=config["max_tokens"],
            grammar=grammar,
            temperature=config["temperature"],
            top_p=0.95,
            min_p=0.05,
            repeat_penalty=1.15,
            echo=False,
            stop=[]
        )

        query = output['choices'][0]['text'].strip()
        print(f"   Generated: {query}")

        # Extract example from prompt for comparison
        example = prompt.split('Example: ')[1].split(' |')[0]

        queries.append({
            "id": i,
            "prompt": task,
            "example": example,
            "query": query,
            "config": config["name"]
        })

    return queries

def save_results(queries):
    """Save generated queries to file."""
    output_file = Path("C:/Users/user/pg_copilot/xgrammar_tests/llmxcpg_extended_results.json")
    print(f"\n[4/4] Saving results to {output_file}...")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(queries, f, indent=2, ensure_ascii=False)

    print(f"      Saved {len(queries)} queries")
    print(f"\n[OK] SUCCESS! Extended LLMxCPG-Q test completed!")
    print(f"\nResults saved to: {output_file}")

def main():
    """Main entry point."""
    print("="*70)
    print("LLMxCPG-Q Extended Test")
    print("Fine-tuned model for Joern/CPGQL with v2 grammar")
    print("="*70)
    print()

    try:
        # Load grammar
        grammar = load_grammar()

        # Load model
        llm = load_model()

        # Generate queries
        queries = generate_queries(llm, grammar, count=10)

        # Save results
        save_results(queries)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
