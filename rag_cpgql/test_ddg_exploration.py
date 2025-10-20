"""
Phase 3: DDG (Data Dependency Graph) API Exploration
Explore Joern's data flow analysis capabilities for tracking variable dependencies.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.execution.joern_client import JoernClient


def test_ddg_basic():
    """Test basic DDG node access"""
    query = """
    cpg.method.name(".*").take(1).map { m =>
        Map(
            "methodName" -> m.name,
            "ddgNodeCount" -> m.ddg.size
        )
    }.l
    """
    return query


def test_parameter_to_sink():
    """Test tracking parameter data flow to sinks (return/call)"""
    query = """
    cpg.method.name("heap_fetch").parameter.take(1).map { param =>
        Map(
            "paramName" -> param.name,
            "paramType" -> param.typeFullName,
            "reachableSinks" -> param.reachableBy(cpg.ret).size
        )
    }.l
    """
    return query


def test_local_variable_flow():
    """Test local variable data dependencies"""
    query = """
    cpg.method.name(".*").take(1).local.take(3).map { local =>
        Map(
            "localName" -> local.name,
            "type" -> local.typeFullName,
            "reachableByIdentifier" -> local.reachableBy(cpg.identifier).size
        )
    }.l
    """
    return query


def test_identifier_ddg():
    """Test identifier nodes in DDG"""
    query = """
    cpg.method.name("heap_fetch").ast.isIdentifier.take(5).map { ident =>
        Map(
            "name" -> ident.name,
            "lineNumber" -> ident.lineNumber,
            "ddgIn" -> ident.ddgIn.size,
            "ddgOut" -> ident.ddgOut.size
        )
    }.l
    """
    return query


def test_call_argument_flow():
    """Test data flow from arguments to calls"""
    query = """
    cpg.call.name("elog").argument.take(3).map { arg =>
        Map(
            "argumentCode" -> arg.code,
            "argumentIndex" -> arg.argumentIndex,
            "reachableByParam" -> arg.reachableBy(cpg.parameter).size
        )
    }.l
    """
    return query


def test_reaching_definitions():
    """Test reaching definitions for variables"""
    query = """
    cpg.method.name("heap_fetch").local.name("tuple").map { local =>
        Map(
            "variableName" -> local.name,
            "defSites" -> local.reachableBy(cpg.assignment).code.l,
            "useSites" -> local.reachableBy(cpg.identifier).code.take(5).l
        )
    }.l
    """
    return query


def test_taint_tracking():
    """Test simple taint tracking from source to sink"""
    query = """
    cpg.method.name("heap_fetch").parameter.take(1).map { param =>
        Map(
            "paramName" -> param.name,
            "flowsToReturn" -> param.reachableBy(cpg.ret).size,
            "flowsToCalls" -> param.reachableBy(cpg.call).take(3).name.l
        )
    }.l
    """
    return query


def test_reachable_by_nodes():
    """Test reachableBy for data flow analysis"""
    query = """
    cpg.method.name(".*").take(1).parameter.take(1).map { param =>
        Map(
            "paramName" -> param.name,
            "reachableByCall" -> param.reachableBy(cpg.call).size,
            "reachableByIdentifier" -> param.reachableBy(cpg.identifier).size,
            "reachableByAssignment" -> param.reachableBy(cpg.assignment).size
        )
    }.l
    """
    return query


def run_test(client, test_name, query):
    """Run a single test query"""
    print(f"\n{'='*60}")
    print(f"Test: {test_name}")
    print(f"{'='*60}")
    print(f"Query:\n{query}\n")

    try:
        result = client.execute_query(query)
        print(f"Status: {result['status']}")
        print(f"Result:\n{json.dumps(result['result'], indent=2)}\n")
        return {
            "test": test_name,
            "status": result['status'],
            "result": result['result'],
            "success": result['status'] == 'success'
        }
    except Exception as e:
        print(f"Error: {str(e)}\n")
        return {
            "test": test_name,
            "status": "error",
            "error": str(e),
            "success": False
        }


def main():
    """Run all DDG exploration tests"""
    print("="*60)
    print("Phase 3: DDG API Exploration")
    print("="*60)

    # Connect to Joern
    client = JoernClient('localhost:8080')
    client.connect()

    # Define tests
    tests = [
        ("DDG Basic Access", test_ddg_basic()),
        ("Parameter to Sink Flow", test_parameter_to_sink()),
        ("Local Variable Flow", test_local_variable_flow()),
        ("Identifier DDG Edges", test_identifier_ddg()),
        ("Call Argument Flow", test_call_argument_flow()),
        ("Reaching Definitions", test_reaching_definitions()),
        ("Taint Tracking", test_taint_tracking()),
        ("ReachableBy Analysis", test_reachable_by_nodes()),
    ]

    # Run all tests
    results = []
    for test_name, query in tests:
        result = run_test(client, test_name, query)
        results.append(result)

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    passed = sum(1 for r in results if r['success'])
    total = len(results)

    print(f"\nTests Passed: {passed}/{total}")
    print("\nTest Results:")
    for r in results:
        status = "✅ PASS" if r['success'] else "❌ FAIL"
        print(f"  {status} - {r['test']}")

    # Save results
    output_file = Path("ddg_exploration_results.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to: {output_file}")
    print(f"\n{'='*60}")
    print("DDG Exploration Complete")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
