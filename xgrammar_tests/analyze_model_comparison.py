#!/usr/bin/env python3
"""
Analyze model comparison results and generate report.
"""

import json
import re
from pathlib import Path

def clean_query(query):
    """Clean up generated query."""
    if not query:
        return ""

    # Extract the portion starting from the first 'cpg' occurrence
    lower_query = query.lower()
    if "cpg" in lower_query:
        start_idx = lower_query.index("cpg")
        query = query[start_idx:]

    # Trim at first newline or code fence to isolate the query
    query = query.split("\n")[0]
    query = query.split("```")[0]
    query = query.split("|")[0]
    query = query.strip().strip("`\"'")

    cleaned = re.sub(r'\s*\.\s*', '.', query)
    cleaned = re.sub(r'\s*\(\s*', '(', cleaned)
    cleaned = re.sub(r'\s*\)\s*', ')', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = re.sub(r'"(method|call|parameter|name|code|caller|argument)"', r'\1', cleaned)
    cleaned = re.sub(r'\s*"\s*$', '', cleaned)
    cleaned = re.sub(r'\(\s*"[a-z]?\s*$', '', cleaned)
    cleaned = re.sub(r'\s+l\s+c$', '.l', cleaned)
    cleaned = re.sub(r'\s+l\s*"?$', '.l', cleaned)
    cleaned = re.sub(r'\s+c$', '', cleaned)

    # Remove garbage patterns
    cleaned = re.sub(r'addCriterionHere.*', '', cleaned)
    cleaned = re.sub(r'_HERE_.*', '', cleaned)
    cleaned = re.sub(r'(labele\s*\.\s*)+', '', cleaned)
    cleaned = re.sub(r'=>.*', '', cleaned)

    for suffix in ('.l', '.toList', '.head'):
        idx = cleaned.find(suffix)
        if idx != -1:
            cleaned = cleaned[:idx + len(suffix)]
            break

    if not cleaned.endswith(('.l', '.toList', '.head')):
        if cleaned.count('.') >= 2 and len(cleaned) < 100:
            cleaned += '.l'

    return cleaned.strip()

def validate_query(generated, expected):
    """Validate and score a query."""
    if not generated or len(generated) < 3:
        return {"valid": False, "score": 0, "issues": ["Empty or too short"]}

    cleaned = clean_query(generated)
    expected_literals = re.findall(r'"([^"]+)"', expected)
    issues = []
    score = 0

    # Basic structure (20 points)
    if cleaned.startswith('cpg'):
        score += 10
    else:
        issues.append("Doesn't start with 'cpg'")

    if '.' in cleaned:
        score += 10
    else:
        issues.append("No property chains")

    # Has execution directive (20 points)
    if cleaned.endswith(('.l', '.toList', '.head')):
        score += 20
    else:
        issues.append("Missing execution directive")

    # Similarity to expected (40 points)
    expected_parts = expected.split('.')
    cleaned_parts = cleaned.split('.')

    matching_parts = sum(1 for part in expected_parts if part in cleaned_parts)
    similarity = matching_parts / len(expected_parts) if expected_parts else 0
    score += int(similarity * 40)

    if similarity < 0.5:
        issues.append(f"Low similarity to expected ({similarity*100:.0f}%)")

    # Literal checks (10 points)
    if expected_literals:
        missing_literals = [lit for lit in expected_literals if lit and lit not in cleaned]
        if missing_literals:
            issues.append("Missing literal(s): " + ", ".join(missing_literals))
        else:
            score += 10

    # No garbage (10 points)
    garbage_patterns = ['HERE', 'labele', '=>', 'x"', 'addCriterion']
    has_garbage = any(pattern in generated for pattern in garbage_patterns)

    if not has_garbage and len(cleaned) < 200:
        score += 10
    else:
        if has_garbage:
            issues.append("Contains garbage text")
        if len(cleaned) >= 200:
            issues.append("Query too long (garbage?)")

    is_valid = score >= 60 and not has_garbage

    return {
        "valid": is_valid,
        "score": score,
        "cleaned": cleaned,
        "issues": issues
    }

def analyze_results():
    """Analyze comparison results."""
    input_file = Path("C:/Users/user/pg_copilot/xgrammar_tests/model_comparison_results.json")

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("="*70)
    print("MODEL COMPARISON ANALYSIS")
    print("="*70)
    print()
    grammar_used = data.get("grammar_used", True)
    if grammar_used:
        print(f"Grammar file: {data.get('grammar', 'N/A')}")
    else:
        print("Grammar: disabled (unconstrained generation)")
    print()

    model_scores = []

    for model_result in data['results']:
        if model_result['status'] != 'success':
            print(f"{model_result['model']}: FAILED")
            print()
            continue

        model_name = model_result['model']
        print(f"\n{model_name} ({model_result['size']})")
        print("-" * 70)

        total_score = 0
        valid_count = 0
        query_details = []

        for result in model_result['results']:
            generated = result['generated']
            expected = result['expected']
            task = result['task']

            validation = validate_query(generated, expected)

            total_score += validation['score']
            if validation['valid']:
                valid_count += 1

            query_details.append({
                "task": task,
                "expected": expected,
                "generated": generated,
                "cleaned": validation['cleaned'],
                "valid": validation['valid'],
                "score": validation['score'],
                "issues": validation['issues']
            })

            status = "[OK]" if validation['valid'] else "[FAIL]"
            print(f"{status} Q{result['query_id']}: {task}")
            print(f"  Expected:  {expected}")
            print(f"  Generated: {generated[:70]}{'...' if len(generated) > 70 else ''}")
            print(f"  Cleaned:   {validation['cleaned'][:70]}{'...' if len(validation['cleaned']) > 70 else ''}")
            print(f"  Score: {validation['score']}/100")
            if validation['issues']:
                print(f"  Issues: {', '.join(validation['issues'])}")

        avg_score = total_score / len(model_result['results'])
        success_rate = (valid_count / len(model_result['results'])) * 100

        print(f"\nSummary:")
        print(f"  Valid queries: {valid_count}/{len(model_result['results'])} ({success_rate:.0f}%)")
        print(f"  Average score: {avg_score:.1f}/100")
        print(f"  Load time: {model_result['load_time']:.1f}s")

        model_scores.append({
            "model": model_name,
            "description": model_result['description'],
            "size": model_result['size'],
            "valid_count": valid_count,
            "total_queries": len(model_result['results']),
            "success_rate": success_rate,
            "average_score": avg_score,
            "load_time": model_result['load_time'],
            "queries": query_details
        })

    # Sort by score
    model_scores.sort(key=lambda x: x['average_score'], reverse=True)

    # Print ranking
    print("\n" + "="*70)
    print("RANKING")
    print("="*70)
    print()
    print(f"{'Rank':<6} {'Model':<20} {'Valid':<10} {'Avg Score':<12} {'Load Time':<10}")
    print("-" * 70)

    for i, model in enumerate(model_scores, 1):
        print(f"{i:<6} {model['model']:<20} {model['valid_count']}/{model['total_queries']} ({model['success_rate']:.0f}%){'':<3} {model['average_score']:.1f}/100{'':<5} {model['load_time']:.1f}s")

    # Save detailed analysis
    output_file = Path("C:/Users/user/pg_copilot/xgrammar_tests/model_comparison_analysis.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        total_queries = max(
            (len(model['results']) for model in data['results'] if model.get('status') == 'success'),
            default=0
        )
        json.dump({
            "ranking": model_scores,
            "test_info": {
                "num_models": len(model_scores),
                "num_queries_per_model": total_queries,
                "grammar": data.get("grammar") if data.get("grammar_used", True) else None,
                "grammar_used": data.get("grammar_used", True)
            }
        }, f, indent=2, ensure_ascii=False)

    print(f"\n\nDetailed analysis saved to: {output_file}")

    # Winner
    if model_scores:
        winner = model_scores[0]
        print(f"\n{'='*70}")
        print(f"WINNER: {winner['model']}")
        print(f"{'='*70}")
        print(f"Success Rate: {winner['success_rate']:.0f}%")
        print(f"Average Score: {winner['average_score']:.1f}/100")
        print(f"Valid Queries: {winner['valid_count']}/{winner['total_queries']}")

if __name__ == "__main__":
    analyze_results()
