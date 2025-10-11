"""Test single question quickly"""
import sys
sys.path.insert(0, 'src')

from execution.joern_client import JoernClient

# Connect to Joern
joern = JoernClient(cpg_project_name="pg17_full.cpg", port=8080)
if not joern.connect():
    print("Failed to connect")
    sys.exit(1)

# Test Q3 with corrected query
print("\n=== Testing Q3 (Security) ===")
q3_query = 'cpg.call.where(_.tag.nameExact("security-risk")).map(c => (c.name, c.file.name, c.lineNumber.getOrElse(0))).l.take(10)'
print(f"Query: {q3_query}")

result = joern.execute_query(q3_query)
print(f"\nSuccess: {result['success']}")
if result['success']:
    stdout = result['results'].get('stdout', '')
    print(f"Output: {stdout[:500]}")
else:
    print(f"Error: {result['error']}")

joern.close()
