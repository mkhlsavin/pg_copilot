"""Run RAG-CPGQL tests on expanded question set"""
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, 'src')

from execution.joern_client import JoernClient
from generation.prompts import CPGQL_SYSTEM_PROMPT

# Simple query generation (for testing, we'll manually create queries)
# In production, this would use LLM

# Connect to Joern
joern = JoernClient(cpg_project_name="pg17_full.cpg", port=8080)
if not joern.connect():
    print("Failed to connect to Joern server")
    sys.exit(1)

print("=" * 80)
print("RAG-CPGQL Expanded Test Suite")
print("=" * 80)

# Load test questions
test_file = Path("test_questions_expanded.jsonl")
questions = []
with open(test_file) as f:
    for line in f:
        questions.append(json.loads(line))

print(f"Loaded {len(questions)} test questions")
print()

# Results storage
results = []
success_count = 0
error_count = 0

# Test each question
for i, q in enumerate(questions, 1):
    print(f"\n[{i}/{len(questions)}] Testing: {q['question']}")
    print(f"  Category: {q['category']}")
    print(f"  Layer: {q['enrichment_layer']}")
    print(f"  Expected: {q['expected_tag']}")

    # Generate query based on expected tag
    query = None
    tag_parts = q['expected_tag'].split(':')

    if len(tag_parts) == 2:
        tag_name, tag_value = tag_parts
        if q['category'] == 'feature':
            query = f'cpg.file.where(_.tag.nameExact("Feature").valueExact("{tag_value}")).name.l.take(10)'
        elif q['category'] == 'semantic':
            query = f'cpg.method.where(_.tag.nameExact("{tag_name}").valueExact("{tag_value}")).name.l.take(10)'
        elif q['category'] == 'architecture':
            query = f'cpg.file.where(_.tag.nameExact("{tag_name}").valueExact("{tag_value}")).name.l.take(10)'
        elif q['category'] == 'security':
            if tag_value == 'sql-injection' or tag_value == 'buffer-overflow':
                query = f'cpg.call.where(_.tag.nameExact("security-risk").valueExact("{tag_value}")).map(c => (c.name, c.file.name, c.lineNumber.getOrElse(0))).l.take(10)'
            else:
                query = f'cpg.call.where(_.tag.nameExact("security-risk")).map(c => (c.name, c.file.name, c.lineNumber.getOrElse(0))).l.take(10)'
        elif q['category'] == 'metrics':
            if 'complexity' in tag_name:
                query = f'cpg.method.where(_.tag.nameExact("{tag_name}").value.toInt > 15).name.l.take(10)'
            elif 'refactor-priority' in tag_name:
                query = f'cpg.method.where(_.tag.nameExact("refactor-priority").valueExact("{tag_value}")).name.l.take(10)'
        elif q['category'] == 'extension':
            query = f'cpg.method.where(_.tag.nameExact("extension-point").valueExact("true")).name.l.take(10)'
        elif q['category'] == 'testing':
            query = f'cpg.method.where(_.tag.nameExact("test-coverage").valueExact("untested")).name.l.take(10)'
        elif q['category'] == 'performance':
            query = f'cpg.method.where(_.tag.nameExact("perf-hotspot").valueExact("hot")).name.l.take(10)'
        elif q['category'] == 'subsystem':
            query = f'cpg.file.where(_.tag.nameExact("subsystem-name").valueExact("{tag_value}")).name.l.take(10)'
        elif q['category'] == 'api':
            query = f'cpg.method.where(_.tag.nameExact("api-caller-count").value.toInt > 50).sortBy(_.tag.nameExact("api-caller-count").value.toInt).name.l.take(10)'
    elif len(tag_parts) == 1:
        tag_name = tag_parts[0]
        if tag_name == 'security-risk':
            query = f'cpg.call.where(_.tag.nameExact("security-risk")).map(c => (c.name, c.file.name)).l.take(10)'
        elif tag_name == 'api-caller-count':
            query = f'cpg.method.where(_.tag.nameExact("api-caller-count").value.toInt > 100).sortBy(_.tag.nameExact("api-caller-count").value.toInt).name.l.take(10)'
        elif tag_name == 'cyclomatic-complexity':
            query = f'cpg.method.where(_.tag.nameExact("cyclomatic-complexity").value.toInt > 15).name.l.take(10)'

    if not query:
        print(f"  [SKIP] Could not generate query")
        continue

    print(f"  Query: {query[:100]}...")

    # Execute query
    try:
        result = joern.execute_query(query)

        if result['success']:
            stdout = result['results'].get('stdout', '')
            # Count results (simple heuristic)
            if 'List(' in stdout or 'res' in stdout:
                success_count += 1
                print(f"  [OK] Query executed successfully")
                print(f"       Results: {stdout[:200]}...")
            else:
                error_count += 1
                print(f"  [WARN] Query executed but no clear results")
        else:
            error_count += 1
            print(f"  [ERROR] Query failed: {result.get('error', 'Unknown error')}")

        results.append({
            'id': q['id'],
            'question': q['question'],
            'category': q['category'],
            'query': query,
            'success': result['success'],
            'output': stdout[:500] if result['success'] else result.get('error', '')
        })

    except Exception as e:
        error_count += 1
        print(f"  [ERROR] Exception: {e}")
        results.append({
            'id': q['id'],
            'question': q['question'],
            'category': q['category'],
            'query': query,
            'success': False,
            'output': str(e)
        })

    # Rate limiting
    time.sleep(0.5)

# Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print(f"Total questions: {len(questions)}")
print(f"Successful: {success_count}")
print(f"Errors: {error_count}")
print(f"Success rate: {success_count/len(questions)*100:.1f}%")

# Save results
results_file = Path("results/expanded_test_results.json")
results_file.parent.mkdir(exist_ok=True)
with open(results_file, 'w') as f:
    json.dump(results, f, indent=2)
print(f"\nResults saved to: {results_file}")

# Category breakdown
print("\n" + "=" * 80)
print("BREAKDOWN BY CATEGORY")
print("=" * 80)
category_stats = {}
for r in results:
    cat = r['category']
    if cat not in category_stats:
        category_stats[cat] = {'total': 0, 'success': 0}
    category_stats[cat]['total'] += 1
    if r['success']:
        category_stats[cat]['success'] += 1

for cat, stats in sorted(category_stats.items()):
    success_rate = stats['success'] / stats['total'] * 100
    print(f"{cat:20s}: {stats['success']}/{stats['total']} ({success_rate:.1f}%)")

joern.close()
print("\nDone!")
