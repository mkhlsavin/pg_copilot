#!/usr/bin/env python3
"""
Comparative test of 6 different models for CPGQL generation.
Tests LLMxCPG-Q (fine-tuned) vs 5 general-purpose models.
"""

import json
import time
from pathlib import Path
from llama_cpp import Llama, LlamaGrammar

GRAMMAR_PATH = Path("C:/Users/user/pg_copilot/cpgql_gbnf/cpgql_llama_cpp_v2.gbnf")
USE_GRAMMAR = False

PROMPT_TEMPLATE = """You are a CPGQL assistant.
Respond with a single-line CPGQL query that starts with cpg and ends with .l (or .toList/.head if required).
Use exactly the entities and literals mentioned in the task; do not substitute or invent alternatives.
Return only the query text—no explanations, comments, or code fences.
Examples:
- cpg.method.name.l
- cpg.call.name("strcpy").caller.name.l
- cpg.method.parameter.name.l

Task: {task}
Query:"""

# Model configurations
MODELS = [
    {
        "name": "LLMxCPG-Q",
        "description": "Qwen2.5-Coder 32B (Fine-tuned for CPGQL)",
        "path": "C:/Users/user/.lmstudio/models/llmxcpg/LLMxCPG-Q/qwen2.5-coder-32B-instruct-bnb-q5_k_m.gguf",
        "size": "32B"
    },
    {
        "name": "Qwen3-32B",
        "description": "Qwen3 32B General",
        "path": "C:/Users/user/.lmstudio/models/lmstudio-community/Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf",
        "size": "32B"
    },
    {
        "name": "QwQ-32B",
        "description": "QwQ 32B Reasoning Model",
        "path": "C:/Users/user/.lmstudio/models/lmstudio-community/QwQ-32B-GGUF/QwQ-32B-Q4_K_M.gguf",
        "size": "32B"
    },
    {
        "name": "Qwen3-Coder-30B",
        "description": "Qwen3 Coder 30B",
        "path": "C:/Users/user/.lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",
        "size": "30B"
    },
    {
        "name": "Seed-OSS-36B",
        "description": "Seed OSS 36B Instruct",
        "path": "C:/Users/user/.lmstudio/models/lmstudio-community/Seed-OSS-36B-Instruct-GGUF/Seed-OSS-36B-Instruct-Q4_K_M.gguf",
        "size": "36B"
    },
    {
        "name": "GPT-OSS-20B",
        "description": "GPT OSS 20B",
        "path": "C:/Users/user/.lmstudio/models/lmstudio-community/gpt-oss-20b-GGUF/gpt-oss-20b-MXFP4.gguf",
        "size": "20B"
    }
]

# Standard test queries
TEST_QUERIES = [
    {
        "id": 1,
        "task": "Find all methods",
        "prompt": PROMPT_TEMPLATE.format(task="Find all methods"),
        "expected": "cpg.method.name.l"
    },
    {
        "id": 2,
        "task": "Find calls to strcpy",
        "prompt": PROMPT_TEMPLATE.format(task="Find calls to strcpy"),
        "expected": "cpg.call.name(\"strcpy\").l"
    },
    {
        "id": 3,
        "task": "Find method parameters",
        "prompt": PROMPT_TEMPLATE.format(task="Find method parameters"),
        "expected": "cpg.method.parameter.name.l"
    },
    {
        "id": 4,
        "task": "Find callers of memcpy",
        "prompt": PROMPT_TEMPLATE.format(task="Find callers of memcpy"),
        "expected": "cpg.method.name(\"memcpy\").caller.name.l"
    },
    {
        "id": 5,
        "task": "Find buffer operations",
        "prompt": PROMPT_TEMPLATE.format(task="Find buffer operations"),
        "expected": "cpg.call.name(\"memcpy\").argument.code.l"
    },
    {
        "id": 6,
        "task": "Find method signatures",
        "prompt": PROMPT_TEMPLATE.format(task="Find method signatures"),
        "expected": "cpg.method.signature.l"
    },
    {
        "id": 7,
        "task": "Find call arguments",
        "prompt": PROMPT_TEMPLATE.format(task="Find call arguments"),
        "expected": "cpg.call.argument.code.l"
    },
    {
        "id": 8,
        "task": "Find control flow parents",
        "prompt": PROMPT_TEMPLATE.format(task="Find control flow parents"),
        "expected": "cpg.method.controlledBy.code.l"
    }
]

def load_grammar():
    """Load GBNF grammar."""
    grammar_text = GRAMMAR_PATH.read_text(encoding='utf-8')
    return LlamaGrammar.from_string(grammar_text)

def test_model(model_config, grammar, test_queries):
    """Test a single model on all queries."""
    print(f"\n{'='*70}")
    print(f"Testing: {model_config['name']}")
    print(f"Description: {model_config['description']}")
    print(f"Size: {model_config['size']}")
    print(f"{'='*70}")

    try:
        # Load model
        print(f"Loading model...")
        start_time = time.time()

        llm = Llama(
            model_path=model_config['path'],
            n_ctx=2048,
            n_gpu_layers=-1,
            verbose=False
        )

        load_time = time.time() - start_time
        print(f"Model loaded in {load_time:.1f}s")

        results = []

        # Test each query
        total_queries = len(test_queries)
        for query_config in test_queries:
            print(f"\n  Query {query_config['id']}/{total_queries}: {query_config['task']}")

            start = time.time()
            output = llm(
                query_config['prompt'],
                max_tokens=150,
                grammar=grammar,
                temperature=0.6,
                top_p=0.95,
                repeat_penalty=1.1,
                echo=False,
                stop=[]
            )
            gen_time = time.time() - start

            generated = output['choices'][0]['text'].strip()
            print(f"  Generated: {generated}")
            print(f"  Time: {gen_time:.2f}s")

            results.append({
                "query_id": query_config['id'],
                "task": query_config['task'],
                "expected": query_config['expected'],
                "generated": generated,
                "generation_time": gen_time
            })

        return {
            "model": model_config['name'],
            "description": model_config['description'],
            "size": model_config['size'],
            "load_time": load_time,
            "status": "success",
            "results": results
        }

    except Exception as e:
        print(f"  ERROR: {e}")
        return {
            "model": model_config['name'],
            "description": model_config['description'],
            "size": model_config['size'],
            "status": "failed",
            "error": str(e)
        }

def main():
    print("="*70)
    print("CPGQL Model Comparison Test")
    mode_desc = "grammar-constrained generation" if USE_GRAMMAR else "unconstrained generation"
    print(f"Testing 6 models with {mode_desc}")
    print("="*70)

    # Load grammar once
    if USE_GRAMMAR:
        print("\nLoading grammar...")
        grammar = load_grammar()
        print("Grammar loaded!")
    else:
        print("\nSkipping grammar loading (unconstrained mode).")
        grammar = None

    all_results = []

    # Test each model
    for model_config in MODELS:
        result = test_model(model_config, grammar, TEST_QUERIES)
        all_results.append(result)

        # Small delay between models
        time.sleep(2)

    # Save results
    output_file = Path("C:/Users/user/pg_copilot/xgrammar_tests/model_comparison_results.json")
    print(f"\n{'='*70}")
    print(f"Saving results to {output_file}...")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "test_date": time.strftime("%Y-%m-%d"),
            "grammar": str(GRAMMAR_PATH),
            "num_models": len(MODELS),
            "num_queries": len(TEST_QUERIES),
            "grammar_used": USE_GRAMMAR,
            "results": all_results
        }, f, indent=2, ensure_ascii=False)

    print(f"Results saved!")
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")

    for result in all_results:
        if result['status'] == 'success':
            print(f"\n{result['model']} ({result['size']}):")
            print(f"  Load time: {result['load_time']:.1f}s")
            print(f"  Queries: {len(result['results'])}/{len(TEST_QUERIES)} completed")
        else:
            print(f"\n{result['model']}: FAILED - {result.get('error', 'Unknown error')}")

    print(f"\n[OK] Comparison test completed!")

if __name__ == "__main__":
    exit(main())
