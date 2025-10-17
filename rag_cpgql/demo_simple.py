"""
Simplified demo to avoid encoding issues
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.workflow.langgraph_workflow import run_workflow

# Load 5 sample questions
dataset_path = Path("data/all_qa_merged.jsonl")
questions = []
with open(dataset_path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if i >= 5:  # Just take first 5 questions
            break
        qa = json.loads(line.strip())
        questions.append(qa)

print(f"Processing {len(questions)} questions from dataset...")
print("=" * 80)

results = []
for i, qa in enumerate(questions, 1):
    question = qa['question']

    print(f"\n[{i}/5] Question: {question[:60]}...")

    result = run_workflow(question, verbose=False)
    state = result.get('state', {})

    # Show key results
    domain = state.get('domain', 'N/A')
    intent = state.get('intent', 'N/A')
    query = state.get('cpgql_query', 'N/A')
    valid = result.get('valid', False)

    print(f"  Domain: {domain}")
    print(f"  Intent: {intent}")
    print(f"  Valid: {valid}")
    print(f"  Query: {query[:80]}...")

    results.append({
        'question': question,
        'domain': domain,
        'valid': valid
    })

print("\n" + "=" * 80)
print(f"COMPLETE: Processed {len(results)} questions")
valid_count = sum(1 for r in results if r['valid'])
print(f"Valid queries: {valid_count}/{len(results)}")

# Save results
output_file = Path("results/demo_simple_results.json")
output_file.parent.mkdir(exist_ok=True)
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"Results saved to: {output_file}")
