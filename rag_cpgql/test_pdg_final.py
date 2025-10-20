"""Final test - use .label and .repr instead of .code"""
from src.execution.joern_client import JoernClient

client = JoernClient('localhost:8080')
client.connect()

# Test 1: Just get label and repr
print("Test 1: Get label and repr from reaching def targets")
result1 = client.execute_query('''
cpg.method.name("heap_fetch").parameter.take(1).flatMap { param =>
    param._reachingDefOut.map { target =>
        Map(
            "param" -> param.name,
            "targetLabel" -> target.label,
            "targetRepr" -> target.toString
        )
    }
}.l
''')
print(result1)
print()

# Test 2: Cast to specific type and get code
print("Test 2: Try asInstanceOf to get code")
result2 = client.execute_query('''
cpg.method.name("heap_fetch").parameter.take(1).flatMap { param =>
    param._reachingDefOut.collect {
        case i: io.shiftleft.codepropertygraph.generated.nodes.Identifier => Map(
            "param" -> param.name,
            "flowsTo" -> i.code,
            "type" -> i.label
        )
    }
}.l
''')
print(result2)
