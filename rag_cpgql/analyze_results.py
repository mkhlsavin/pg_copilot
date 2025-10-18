"""Deep analysis of test results."""
import json
from pathlib import Path
import re
import sys

# Load results - use command line arg or default to optimized_persistent_200q.json
results_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('results/optimized_persistent_200q.json')
print(f'Analyzing results from: {results_path}')
print('='*80)

with open(results_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Analyze each question
for i, result in enumerate(data['results'], 1):
    print('='*80)
    print(f'QUESTION {i}/{len(data["results"])}')
    print('='*80)
    print(f'Question: {result["question"][:120]}...')
    print(f'\nGenerated Query: {result["query"]}')
    print(f'\nQuery Valid: {result["valid"]}')

    # Check if tags were used
    uses_tags = '.tag.nameExact(' in result['query']
    print(f'Uses Enrichment Tags: {"YES" if uses_tags else "NO"}')

    # Extract tag info if present
    if uses_tags:
        tag_pattern = r'tag\.nameExact\("([^"]+)"\)\.valueExact\("([^"]+)"\)'
        matches = re.findall(tag_pattern, result['query'])
        if matches:
            print('\nTags Used:')
            for tag_name, tag_value in matches:
                print(f'  - {tag_name}: {tag_value}')

    # Execution results
    exec_success = result.get('execution_success', result.get('success', False))
    print(f'\nExecution Successful: {exec_success}')
    if exec_success:
        # Check state for execution details
        state = result.get('state', {})
        exec_result = state.get('execution_result', {})

        # execution_result is a dict with keys: success, result, error, execution_time, raw_response
        if isinstance(exec_result, dict):
            actual_result = exec_result.get('result', '')
            result_len = len(actual_result)
        else:
            # Fallback for old format (shouldn't happen)
            result_len = len(str(exec_result))

        print(f'Result Size: {result_len:,} chars')

        # Check if fallback was used
        used_fallback = state.get('used_fallback_query', False)
        print(f'Used Fallback: {"YES" if used_fallback else "NO"}')

        if used_fallback:
            print(f'Fallback Query: {state.get("fallback_query", "N/A")}')
    else:
        error = result.get('execution_error', result.get('error', 'N/A'))
        print(f'Execution Error: {error}')

    # Answer quality
    answer = result.get('answer', '')
    print(f'\nAnswer Length: {len(answer)} chars')
    print(f'Answer Preview: {answer[:200]}...')

    # RAGAS metrics
    if 'ragas_metrics' in result and result['ragas_metrics']:
        print('\nRAGAS Metrics:')
        metrics = result['ragas_metrics']
        for metric_name, value in metrics.items():
            if value is not None and str(value) != 'nan':
                print(f'  - {metric_name}: {value:.3f}')

    # Timing
    elapsed = result.get("elapsed", result.get("total_time", 0))
    print(f'\nExecution Time: {elapsed:.2f}s')
    print()

# Summary statistics
print('='*80)
print('SUMMARY STATISTICS')
print('='*80)

total = len(data['results'])
tag_usage = sum(1 for r in data['results'] if '.tag.nameExact(' in r['query'])
successful = sum(1 for r in data['results'] if r.get('execution_success', r.get('success', False)))
no_fallback = sum(1 for r in data['results'] if not r.get('state', {}).get('used_fallback_query', False) and r.get('execution_success', r.get('success', False)))

# Count multi-tag queries (queries with 2+ tag filters)
multi_tag_queries = sum(1 for r in data['results'] if r['query'].count('.where(_.tag.nameExact(') >= 2)
single_tag_queries = tag_usage - multi_tag_queries

# Calculate average result size for successful executions
result_sizes = []
for r in data['results']:
    if r.get('execution_success', r.get('success', False)):
        state = r.get('state', {})
        exec_result = state.get('execution_result', '')
        if exec_result:
            result_sizes.append(len(exec_result))

avg_result_size = sum(result_sizes) / len(result_sizes) if result_sizes else 0

print(f'Total Questions: {total}')
print(f'Tag Usage: {tag_usage}/{total} ({tag_usage/total*100:.1f}%)')
print(f'  - Single-tag queries: {single_tag_queries}/{total} ({single_tag_queries/total*100:.1f}%)')
print(f'  - Multi-tag queries (2+): {multi_tag_queries}/{total} ({multi_tag_queries/total*100:.1f}%)')
print(f'Execution Success: {successful}/{total} ({successful/total*100:.1f}%)')
print(f'No Fallback Needed: {no_fallback}/{total} ({no_fallback/total*100:.1f}%)')
print(f'Average Result Size: {avg_result_size:,.0f} chars ({len(result_sizes)} successful queries)')

avg_time = sum(r.get('elapsed', r.get('total_time', 0)) for r in data['results']) / total
print(f'Average Execution Time: {avg_time:.2f}s')
