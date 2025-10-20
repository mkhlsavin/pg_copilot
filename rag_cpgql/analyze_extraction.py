import json
from collections import Counter
from pathlib import Path

data = json.load(open('data/cpg_documentation_complete.json'))
methods = data['methods']

print(f'=== Extraction Statistics ===')
print(f'Total methods with documentation: {len(methods)}')
print(f'Average comment length: {sum(len(m["comment"]) for m in methods) / len(methods):.0f} chars')

print(f'\n=== File Distribution (top 10) ===')
file_counts = Counter(m['file_path'] for m in methods)
for file, count in file_counts.most_common(10):
    print(f'{count:4d} methods: {file}')

print(f'\n=== Sample Documentation ===')
sample = methods[50]
print(f'Method: {sample["method_name"]}')
print(f'File: {sample["file_path"]}:{sample["line_number"]}')
print(f'Description: {sample["description"]}')
print(f'\nFull comment (first 300 chars):')
print(sample['comment'][:300])
