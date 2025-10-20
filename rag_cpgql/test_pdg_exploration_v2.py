"""
Phase 3: PDG (Program Dependence Graph) API Exploration - CORRECTED VERSION
Uses REACHING_DEF edges for DDG and CDG edges for control dependencies.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.execution.joern_client import JoernClient


def test_reaching_def_basic():
    """Test basic REACHING_DEF edges (DDG)"""
    query = """
    cpg.method.name("heap_fetch").take(1).map { m =>
        Map(
            "methodName" -> m.name,
            "reachingDefCount" -> m.ast.outE("REACHING_DEF").size
        )
    }.l
    """
    return query


def test_reaching_def_details():
    """Test REACHING_DEF edge details"""
    query = """
    cpg.method.name("heap_fetch").ast.outE("REACHING_DEF").take(10).map { edge =>
        Map(
            "sourceNode" -> edge.inNode.code,
            "targetNode" -> edge.outNode.code,
            "variable" -> edge.property("VARIABLE"),
            "sourceType" -> edge.inNode.label,
            "targetType" -> edge.outNode.label
        )
    }.l
    """
    return query


def test_parameter_reaching_defs():
    """Test reaching definitions from parameters"""
    query = """
    cpg.method.name("heap_fetch").parameter.take(1).flatMap { param =>
        param.outE("REACHING_DEF").map { edge =>
            Map(
                "parameter" -> param.name,
                "reachesTo" -> edge.outNode.code,
                "variable" -> edge.property("VARIABLE"),
                "lineNumber" -> edge.outNode.lineNumber
            )
        }
    }.l
    """
    return query


def test_identifier_reaching_defs():
    """Test reaching definitions for identifiers"""
    query = """
    cpg.method.name("heap_fetch").ast.isIdentifier.take(5).flatMap { ident =>
        ident.inE("REACHING_DEF").map { edge =>
            Map(
                "identifier" -> ident.code,
                "definedBy" -> edge.inNode.code,
                "variable" -> edge.property("VARIABLE"),
                "line" -> ident.lineNumber
            )
        }
    }.take(10).l
    """
    return query


def test_cdg_basic():
    """Test basic CDG (Control Dependency Graph) edges"""
    query = """
    cpg.method.name("heap_fetch").take(1).map { m =>
        Map(
            "methodName" -> m.name,
            "cdgEdgeCount" -> m.ast.outE("CDG").size
        )
    }.l
    """
    return query


def test_cdg_details():
    """Test CDG edge details"""
    query = """
    cpg.method.name("heap_fetch").ast.outE("CDG").take(10).map { edge =>
        Map(
            "controlNode" -> edge.inNode.code,
            "dependentNode" -> edge.outNode.code,
            "controlType" -> edge.inNode.label,
            "dependentType" -> edge.outNode.label
        )
    }.l
    """
    return query


def test_call_reaching_defs():
    """Test reaching definitions for function calls"""
    query = """
    cpg.call.name("HeapTupleSatisfiesMVCC").take(1).flatMap { call =>
        call.argument.flatMap { arg =>
            arg.inE("REACHING_DEF").map { edge =>
                Map(
                    "callName" -> call.name,
                    "argCode" -> arg.code,
                    "argIndex" -> arg.argumentIndex,
                    "definedBy" -> edge.inNode.code,
                    "variable" -> edge.property("VARIABLE")
                )
            }
        }
    }.take(10).l
    """
    return query


def test_return_reaching_defs():
    """Test reaching definitions for return statements"""
    query = """
    cpg.method.name("heap_fetch").ast.isReturn.take(1).flatMap { ret =>
        ret.inE("REACHING_DEF").map { edge =>
            Map(
                "returnCode" -> ret.code,
                "definedBy" -> edge.inNode.code,
                "variable" -> edge.property("VARIABLE"),
                "defType" -> edge.inNode.label
            )
        }
    }.take(10).l
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
    """Run all PDG exploration tests"""
    print("="*60)
    print("Phase 3: PDG API Exploration (CORRECTED)")
    print("Using REACHING_DEF and CDG edges")
    print("="*60)

    # Connect to Joern
    client = JoernClient('localhost:8080')
    client.connect()

    # Define tests
    tests = [
        ("REACHING_DEF Basic Count", test_reaching_def_basic()),
        ("REACHING_DEF Edge Details", test_reaching_def_details()),
        ("Parameter REACHING_DEF", test_parameter_reaching_defs()),
        ("Identifier REACHING_DEF", test_identifier_reaching_defs()),
        ("CDG Basic Count", test_cdg_basic()),
        ("CDG Edge Details", test_cdg_details()),
        ("Call Argument REACHING_DEF", test_call_reaching_defs()),
        ("Return REACHING_DEF", test_return_reaching_defs()),
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
    output_file = Path("pdg_exploration_results_v2.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to: {output_file}")
    print(f"\n{'='*60}")
    print("PDG Exploration Complete")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
