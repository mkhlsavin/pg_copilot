"""Test Feature tag queries"""
import sys
sys.path.insert(0, 'src')

from execution.joern_client import JoernClient

# Connect to Joern
joern = JoernClient(cpg_project_name="pg17_full.cpg", port=8080)
if not joern.connect():
    print("Failed to connect")
    sys.exit(1)

print("=" * 80)
print("Testing PostgreSQL Feature Tags")
print("=" * 80)

# Test queries for each feature
test_queries = [
    {
        "name": "Q1: Find MERGE files",
        "query": 'cpg.file.where(_.tag.nameExact("Feature").valueExact("MERGE")).name.l'
    },
    {
        "name": "Q2: Find JSONB functions",
        "query": 'cpg.method.where(_.file.tag.nameExact("Feature").valueExact("JSONB data type")).name.l.take(10)'
    },
    {
        "name": "Q3: Find JIT compilation code",
        "query": 'cpg.file.where(_.tag.nameExact("Feature").valueExact("JIT compilation")).name.l'
    },
    {
        "name": "Q4: Find WAL improvement files",
        "query": 'cpg.file.where(_.tag.nameExact("Feature").valueExact("WAL improvements")).name.l.take(20)'
    },
    {
        "name": "Q5: Find Partitioning methods",
        "query": 'cpg.method.where(_.file.tag.nameExact("Feature").valueExact("Partitioning")).name.l.take(15)'
    },
    {
        "name": "Q6: Count all Feature tags",
        "query": 'cpg.tag.nameExact("Feature").value.l.groupBy(identity).view.mapValues(_.size).toList.sortBy(-_._2)'
    }
]

for test in test_queries:
    print(f"\n{test['name']}")
    print(f"Query: {test['query']}")
    print("-" * 80)

    result = joern.execute_query(test['query'])
    if result['success']:
        stdout = result['results'].get('stdout', '')
        # Print first 800 chars
        print(f"Result: {stdout[:800]}")
        if len(stdout) > 800:
            print("... (truncated)")
    else:
        print(f"ERROR: {result['error']}")

print("\n" + "=" * 80)
print("Feature Tag Testing Complete")
print("=" * 80)

joern.close()
