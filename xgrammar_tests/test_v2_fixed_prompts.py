#!/usr/bin/env python3
"""
Test CPGQL grammar-constrained generation using llama-cpp-python.

This script generates CPGQL queries using the v2 grammar with improved prompts.
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
    print(f"[2/4] Loading model from {MODEL_PATH}...")
    print(f"      This may take a few minutes...")
    llm = Llama(
        model_path=str(MODEL_PATH),
        n_ctx=2048,
        n_gpu_layers=-1,  # Use GPU if available
        verbose=False
    )
    print(f"      Model loaded successfully!")
    return llm

def generate_queries(llm, grammar, count=5):
    """Generate CPGQL queries using grammar constraints."""
    print(f"[3/4] Generating {count} CPGQL queries with grammar constraints...")

    # Fixed single-line prompts without \n
    prompts = [
        "Generate CPGQL query to find all methods. Example: cpg.method.name.l | Query:",
        "Generate CPGQL query to find vulnerable functions. Example: cpg.method.name(\"strcpy\").caller.name.l | Query:",
        "Generate CPGQL query to find buffer overflow risks. Example: cpg.call.name(\"memcpy\").argument.code.l | Query:",
        "Generate CPGQL query for control flow analysis. Example: cpg.method.controlledBy.code.l | Query:",
        "Generate CPGQL query to find all function calls. Example: cpg.call.name.l | Query:",
    ]

    queries = []
    for i, prompt in enumerate(prompts[:count], 1):
        task = prompt.split('. Example:')[0].replace('Generate CPGQL query ', '')
        print(f"\n   Query {i}/{count}: {task}")

        output = llm(
            prompt,
            max_tokens=150,  # Increased from 100
            grammar=grammar,
            temperature=0.6,  # Decreased for more focused output
            top_p=0.9,
            min_p=0.05,
            repeat_penalty=1.1,
            echo=False,
            stop=[]  # Removed stop tokens
        )

        query = output['choices'][0]['text'].strip()
        print(f"   Generated: {query}")

        queries.append({
            "id": i,
            "prompt": task,
            "query": query
        })

    return queries

def save_results(queries):
    """Save generated queries to file."""
    output_file = Path("C:/Users/user/pg_copilot/xgrammar_tests/grammar_generated_queries_v2.json")
    print(f"\n[4/4] Saving results to {output_file}...")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(queries, f, indent=2, ensure_ascii=False)

    print(f"      Saved {len(queries)} queries")
    print(f"\n[OK] SUCCESS! Grammar-constrained generation completed!")
    print(f"\nResults saved to: {output_file}")

def main():
    """Main entry point."""
    print("="*70)
    print("CPGQL Grammar-Constrained Generation Test (v2)")
    print("Using llama-cpp-python with improved GBNF grammar and prompts")
    print("="*70)
    print()

    try:
        # Load grammar
        grammar = load_grammar()

        # Load model
        llm = load_model()

        # Generate queries
        queries = generate_queries(llm, grammar, count=5)

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
