"""Simple test for REACHING_DEF edges"""
from src.execution.joern_client import JoernClient

client = JoernClient('localhost:8080')
client.connect()

# Test 1: Check if REACHING_DEF edges exist
print("Test 1: Count REACHING_DEF edges")
result1 = client.execute_query('cpg.graph.E("REACHING_DEF").size')
print(result1)
print()

# Test 2: Try alternative: check via method
print("Test 2: REACHING_DEF count via method")
result2 = client.execute_query('cpg.method.name("heap_fetch").take(1).map(m => m.ast.outE("REACHING_DEF").size).l')
print(result2)
print()

# Test 3: See if edges support ._source and ._target
print("Test 3: First REACHING_DEF edge with ._source")
result3 = client.execute_query('cpg.graph.E("REACHING_DEF").take(1).map(e => e._source.code).l')
print(result3)
