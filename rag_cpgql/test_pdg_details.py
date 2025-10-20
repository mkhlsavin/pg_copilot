"""Test getting details from REACHING_DEF traversals"""
from src.execution.joern_client import JoernClient

client = JoernClient('localhost:8080')
client.connect()

# Test 1: Get target nodes from parameter via _reachingDefOut
print("Test 1: Parameter -> _reachingDefOut -> target nodes")
result1 = client.execute_query('''
cpg.method.name("heap_fetch").parameter.take(1).flatMap { param =>
    param._reachingDefOut.map { target =>
        Map(
            "param" -> param.name,
            "flowsTo" -> target.code,
            "targetType" -> target.label,
            "targetLine" -> target.lineNumber
        )
    }
}.l
''')
print(result1)
print()

# Test 2: Get source nodes for identifier via _reachingDefIn
print("Test 2: Identifier -> _reachingDefIn -> source nodes")
result2 = client.execute_query('''
cpg.method.name("heap_fetch").ast.isIdentifier.name("tuple").take(1).flatMap { ident =>
    ident._reachingDefIn.map { source =>
        Map(
            "identifier" -> ident.code,
            "definedBy" -> source.code,
            "sourceType" -> source.label,
            "sourceLine" -> source.lineNumber
        )
    }
}.l
''')
print(result2)
print()

# Test 3: Check CDG edges via _cdgOut
print("Test 3: Control structure -> _cdgOut -> dependent nodes")
result3 = client.execute_query('''
cpg.method.name("heap_fetch").ast.isControlStructure.take(1).flatMap { ctrl =>
    ctrl._cdgOut.take(3).map { dependent =>
        Map(
            "controlNode" -> ctrl.code,
            "dependentNode" -> dependent.code,
            "dependentType" -> dependent.label
        )
    }
}.l
''')
print(result3)
