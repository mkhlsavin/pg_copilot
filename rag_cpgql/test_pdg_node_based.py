"""Test node-based DDG traversals instead of edge-based"""
from src.execution.joern_client import JoernClient

client = JoernClient('localhost:8080')
client.connect()

# Test 1: Try node.reachingDef() or similar
print("Test 1: Try identifier.reachingDef()")
result1 = client.execute_query('''
cpg.method.name("heap_fetch").ast.isIdentifier.take(1).map { ident =>
    Map(
        "identifier" -> ident.code,
        "hasReachingDef" -> ident.inE("REACHING_DEF").nonEmpty
    )
}.l
''')
print(result1)
print()

# Test 2: Check what methods are available on edges
print("Test 2: outE REACHING_DEF and check count only")
result2 = client.execute_query('''
cpg.method.name("heap_fetch").parameter.take(1).map { param =>
    Map(
        "param" -> param.name,
        "reachingDefCount" -> param.outE("REACHING_DEF").size
    )
}.l
''')
print(result2)
print()

# Test 3: Try _reachingDefOut or reachingDefOut
print("Test 3: Try _reachingDefOut")
result3 = client.execute_query('''
cpg.method.name("heap_fetch").parameter.take(1).map { param =>
    Map(
        "param" -> param.name,
        "reachingDefOut" -> param._reachingDefOut.size
    )
}.l
''')
print(result3)
