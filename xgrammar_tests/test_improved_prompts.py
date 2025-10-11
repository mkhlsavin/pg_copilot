#!/usr/bin/env python3
"""
Test with improved prompts to fix string literal generation.
"""

import json
from pathlib import Path
from llama_cpp import Llama, LlamaGrammar

MODEL_PATH = Path("C:/Users/user/.lmstudio/models/llmxcpg/LLMxCPG-Q/qwen2.5-coder-32B-instruct-bnb-q5_k_m.gguf")
GRAMMAR_PATH = Path("C:/Users/user/pg_copilot/cpgql_gbnf/cpgql_llama_cpp_v2.gbnf")

def load_grammar():
    """Load GBNF grammar from file."""
    print(f"[1/4] Loading grammar...")
    grammar_text = GRAMMAR_PATH.read_text(encoding='utf-8')
    return LlamaGrammar.from_string(grammar_text)

def load_model():
    """Load GGUF model."""
    print(f"[2/4] Loading model...")
    llm = Llama(
        model_path=str(MODEL_PATH),
        n_ctx=4096,
        n_gpu_layers=-1,
        verbose=False
    )
    print(f"      Model loaded!")
    return llm

def generate_queries(llm, grammar):
    """Generate CPGQL queries with improved prompts."""
    print(f"[3/4] Generating queries with improved prompts...")

    # IMPROVED PROMPTS - Multi-shot examples with complete strings
    prompts = [
        # Simple
        {
            "task": "find all methods",
            "prompt": """Generate a complete CPGQL query. Examples:
cpg.method.name.l
cpg.call.name.l
cpg.method.parameter.name.l

Task: Find all methods
Query:"""
        },
        # With string parameter
        {
            "task": "find method named main",
            "prompt": """Generate a complete CPGQL query. Examples:
cpg.method.name("main").l
cpg.method.name("execute").l
cpg.call.name("strcpy").l

Task: Find method named main
Query:"""
        },
        # Complex with caller
        {
            "task": "find callers of strcpy",
            "prompt": """Generate a complete CPGQL query. Examples:
cpg.method.name("strcpy").caller.name.l
cpg.method.name("memcpy").caller.name.l
cpg.call.name("malloc").caller.name.l

Task: Find callers of strcpy
Query:"""
        },
        # With argument
        {
            "task": "find memcpy arguments",
            "prompt": """Generate a complete CPGQL query. Examples:
cpg.call.name("memcpy").argument.code.l
cpg.call.name("strcpy").argument.code.l
cpg.call.name("sprintf").argument.code.l

Task: Find memcpy arguments
Query:"""
        },
        # Parameters
        {
            "task": "find method parameters",
            "prompt": """Generate a complete CPGQL query. Examples:
cpg.method.parameter.name.l
cpg.method.parameter.typeFullName.l
cpg.method.filter(_.isPublic).parameter.name.l

Task: Find method parameters
Query:"""
        },
    ]

    queries = []

    for i, item in enumerate(prompts, 1):
        task = item["task"]
        prompt = item["prompt"]

        print(f"\n   Query {i}/5: {task}")

        output = llm(
            prompt,
            max_tokens=300,  # INCREASED from 200
            grammar=grammar,
            temperature=0.3,  # LOWERED from 0.6 for consistency
            top_p=0.95,
            min_p=0.05,
            repeat_penalty=1.2,  # INCREASED to avoid repetition
            echo=False,
            stop=[]
        )

        query = output['choices'][0]['text'].strip()
        print(f"   Generated: {query}")

        queries.append({
            "id": i,
            "task": task,
            "prompt": prompt,
            "query": query
        })

    return queries

def save_results(queries):
    """Save results."""
    output_file = Path("C:/Users/user/pg_copilot/xgrammar_tests/improved_prompts_results.json")
    print(f"\n[4/4] Saving results...")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(queries, f, indent=2, ensure_ascii=False)

    print(f"      Saved to: {output_file}")

def main():
    print("="*70)
    print("CPGQL Generation - Improved Prompts Test")
    print("="*70)
    print()

    try:
        grammar = load_grammar()
        llm = load_model()
        queries = generate_queries(llm, grammar)
        save_results(queries)

        print(f"\n[OK] Test completed!")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
