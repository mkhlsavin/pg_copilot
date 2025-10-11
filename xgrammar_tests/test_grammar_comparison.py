#!/usr/bin/env python3
"""
Compare CPGQL grammar versions (v1 vs v2) for generation quality.
"""

import json
from pathlib import Path
from llama_cpp import Llama, LlamaGrammar

# Paths
MODEL_PATH = Path("C:/Users/user/.lmstudio/models/llmxcpg/LLMxCPG-Q/qwen2.5-coder-32B-instruct-bnb-q5_k_m.gguf")
GRAMMAR_V1 = Path("C:/Users/user/pg_copilot/cpgql_gbnf/cpgql_llama_cpp_clean.gbnf")
GRAMMAR_V2 = Path("C:/Users/user/pg_copilot/cpgql_gbnf/cpgql_llama_cpp_v2.gbnf")

def load_model():
    """Load model once for both tests."""
    print("Loading model...")
    llm = Llama(
        model_path=str(MODEL_PATH),
        n_ctx=2048,
        n_gpu_layers=-1,
        verbose=False
    )
    print("Model loaded!\n")
    return llm

def test_grammar(llm, grammar_path, version_name):
    """Test a grammar version."""
    print(f"="*70)
    print(f"Testing {version_name}: {grammar_path.name}")
    print(f"="*70)

    # Load grammar
    grammar_text = grammar_path.read_text(encoding='utf-8')
    print(f"Grammar size: {len(grammar_text)} chars")

    try:
        grammar = LlamaGrammar.from_string(grammar_text)
        print("[OK] Grammar compiled successfully!")
    except Exception as e:
        print(f"[ERROR] Grammar compilation failed: {e}")
        return None

    # Test prompts with strong examples
    test_cases = [
        {
            "task": "Find all methods",
            "prompt": "CPGQL query to list all methods:\ncpg.method.name.l"
        },
        {
            "task": "Find vulnerable strcpy calls",
            "prompt": "CPGQL query to find strcpy callers:\ncpg.method.name(\"strcpy\").caller.name.l"
        },
        {
            "task": "Find buffer overflow risks",
            "prompt": "CPGQL query for memcpy arguments:\ncpg.call.name(\"memcpy\").argument.code.l"
        },
    ]

    results = []
    print(f"\nGenerating {len(test_cases)} queries...\n")

    for i, test in enumerate(test_cases, 1):
        print(f"[{i}/{len(test_cases)}] {test['task']}")

        try:
            output = llm(
                test['prompt'],
                max_tokens=80,
                grammar=grammar,
                temperature=0.7,
                top_p=0.9,
                repeat_penalty=1.1,
                echo=False,
                stop=["\n", "cpg"]
            )

            query = output['choices'][0]['text'].strip()
            # Clean up result
            if query.startswith("cpg"):
                query = query.split('\n')[0]

            print(f"  Generated: {query}")

            results.append({
                "task": test['task'],
                "prompt": test['prompt'],
                "generated": query
            })
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({
                "task": test['task'],
                "prompt": test['prompt'],
                "generated": f"ERROR: {e}"
            })

    print()
    return results

def main():
    """Main comparison test."""
    print("="*70)
    print("CPGQL Grammar Comparison Test (v1 vs v2)")
    print("="*70)
    print()

    # Load model once
    llm = load_model()

    # Test both versions
    v1_results = test_grammar(llm, GRAMMAR_V1, "Version 1 (Original)")
    print()
    v2_results = test_grammar(llm, GRAMMAR_V2, "Version 2 (Improved)")

    # Save comparison results
    output = {
        "model": str(MODEL_PATH.name),
        "v1_grammar": str(GRAMMAR_V1.name),
        "v2_grammar": str(GRAMMAR_V2.name),
        "v1_results": v1_results,
        "v2_results": v2_results
    }

    output_file = Path("C:/Users/user/pg_copilot/xgrammar_tests/grammar_comparison_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print()
    print("="*70)
    print("Comparison Summary")
    print("="*70)

    if v1_results and v2_results:
        print(f"\nVersion 1 Results:")
        for r in v1_results:
            print(f"  - {r['task']}: {r['generated'][:60]}")

        print(f"\nVersion 2 Results:")
        for r in v2_results:
            print(f"  - {r['task']}: {r['generated'][:60]}")

    print(f"\n[OK] Results saved to: {output_file}")
    return 0

if __name__ == "__main__":
    exit(main())
