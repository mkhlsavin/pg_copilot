"""Comprehensive DDG Pattern Exploration - All Pattern Types"""
from src.execution.joern_client import JoernClient
import json
from typing import Dict, Any, List
import time

client = JoernClient('localhost:8080')
client.connect()

def run_test(name: str, query: str) -> Dict[str, Any]:
    """Run a test query and return results"""
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    print(f"{'='*60}")
    print(f"Query:\n{query}\n")

    start_time = time.time()
    result = client.execute_query(query)
    execution_time = time.time() - start_time

    if result['success']:
        print(f"[SUCCESS] ({execution_time:.2f}s)")
        print(f"Result: {result['result'][:500]}...")  # First 500 chars
        return {
            'name': name,
            'status': 'success',
            'result': result['result'],
            'execution_time': execution_time
        }
    else:
        print(f"[FAILED] ({execution_time:.2f}s)")
        print(f"Error: {result.get('error', 'Unknown error')}")
        return {
            'name': name,
            'status': 'failed',
            'error': result.get('error', 'Unknown error'),
            'execution_time': execution_time
        }

# Store all results
results = []

print("\n" + "="*60)
print("DDG Pattern Exploration - Comprehensive Test Suite")
print("="*60)

# ============================================================
# 1. PARAMETER DATA FLOW
# ============================================================

print("\n" + "="*60)
print("CATEGORY 1: Parameter Data Flow Patterns")
print("="*60)

# Test 1.1: Parameter to identifier flow
results.append(run_test(
    "Parameter to Identifier Flow",
    """
    cpg.method.name("heap_fetch").parameter.take(3).flatMap { param =>
        param._reachingDefOut.collect {
            case i: io.shiftleft.codepropertygraph.generated.nodes.Identifier =>
                Map(
                    "methodName" -> param.method.name,
                    "parameter" -> param.name,
                    "paramType" -> param.typeFullName,
                    "flowsToIdentifier" -> i.code,
                    "atLine" -> i.lineNumber.map(_.toString).getOrElse("unknown"),
                    "inMethod" -> i.method.name
                )
        }
    }.l
    """
))

# Test 1.2: Parameter to call argument flow
results.append(run_test(
    "Parameter to Call Argument Flow",
    """
    cpg.method.name("heap_fetch").parameter.take(3).flatMap { param =>
        param._reachingDefOut.collect {
            case arg: io.shiftleft.codepropertygraph.generated.nodes.Argument =>
                Map(
                    "parameter" -> param.name,
                    "flowsToCall" -> arg.call.name,
                    "argumentIndex" -> arg.argumentIndex.toString,
                    "argumentCode" -> arg.code,
                    "atLine" -> arg.lineNumber.map(_.toString).getOrElse("unknown")
                )
        }
    }.take(10).l
    """
))

# Test 1.3: Parameter to return flow
results.append(run_test(
    "Parameter to Return Flow",
    """
    cpg.method.name("heap_fetch").parameter.flatMap { param =>
        param._reachingDefOut.collect {
            case ret: io.shiftleft.codepropertygraph.generated.nodes.Return =>
                Map(
                    "methodName" -> param.method.name,
                    "parameter" -> param.name,
                    "returnCode" -> ret.code,
                    "atLine" -> ret.lineNumber.map(_.toString).getOrElse("unknown")
                )
        }
    }.take(10).l
    """
))

# ============================================================
# 2. LOCAL VARIABLE DEPENDENCIES
# ============================================================

print("\n" + "="*60)
print("CATEGORY 2: Local Variable Dependencies")
print("="*60)

# Test 2.1: Assignment chains
results.append(run_test(
    "Local Variable Assignment Chains",
    """
    cpg.method.name("heap_fetch").ast.isIdentifier.name("tuple").take(1).flatMap { ident =>
        ident._reachingDefIn.collect {
            case call: io.shiftleft.codepropertygraph.generated.nodes.Call =>
                Map(
                    "identifier" -> ident.code,
                    "definedByCall" -> call.name,
                    "callCode" -> call.code,
                    "atLine" -> call.lineNumber.map(_.toString).getOrElse("unknown")
                )
            case param: io.shiftleft.codepropertygraph.generated.nodes.MethodParameterIn =>
                Map(
                    "identifier" -> ident.code,
                    "definedByParam" -> param.name,
                    "paramType" -> param.typeFullName,
                    "atLine" -> param.lineNumber.map(_.toString).getOrElse("unknown")
                )
        }
    }.take(10).l
    """
))

# Test 2.2: Identifier to identifier flow (variable reassignments)
results.append(run_test(
    "Variable Reassignment Chains",
    """
    cpg.method.name("heap_fetch").ast.isIdentifier.take(5).flatMap { ident =>
        ident._reachingDefOut.collect {
            case targetIdent: io.shiftleft.codepropertygraph.generated.nodes.Identifier =>
                Map(
                    "sourceVar" -> ident.code,
                    "sourceLine" -> ident.lineNumber.map(_.toString).getOrElse("unknown"),
                    "targetVar" -> targetIdent.code,
                    "targetLine" -> targetIdent.lineNumber.map(_.toString).getOrElse("unknown")
                )
        }
    }.take(10).l
    """
))

# ============================================================
# 3. CALL ARGUMENT TRACKING
# ============================================================

print("\n" + "="*60)
print("CATEGORY 3: Call Argument Data Flow")
print("="*60)

# Test 3.1: What reaches call arguments
results.append(run_test(
    "Call Argument Sources",
    """
    cpg.call.name("HeapTupleSatisfiesMVCC").take(1).flatMap { call =>
        call.argument.flatMap { arg =>
            arg._reachingDefIn.take(5).map { source =>
                Map(
                    "callName" -> call.name,
                    "argumentIndex" -> arg.argumentIndex.toString,
                    "argumentCode" -> arg.code,
                    "sourceLabel" -> source.label,
                    "sourceLine" -> source.property("LINE_NUMBER").map(_.toString).getOrElse("unknown")
                )
            }
        }
    }.take(10).l
    """
))

# ============================================================
# 4. RETURN VALUE TRACKING
# ============================================================

print("\n" + "="*60)
print("CATEGORY 4: Return Value Data Sources")
print("="*60)

# Test 4.1: What flows to return statements
results.append(run_test(
    "Return Value Sources",
    """
    cpg.method.name("heap_fetch").ast.isReturn.flatMap { ret =>
        ret._reachingDefIn.take(5).map { source =>
            Map(
                "methodName" -> ret.method.name,
                "returnCode" -> ret.code,
                "returnLine" -> ret.lineNumber.map(_.toString).getOrElse("unknown"),
                "sourceLabel" -> source.label,
                "sourceLine" -> source.property("LINE_NUMBER").map(_.toString).getOrElse("unknown")
            )
        }
    }.take(10).l
    """
))

# ============================================================
# 5. CONTROL DEPENDENCY (CDG)
# ============================================================

print("\n" + "="*60)
print("CATEGORY 5: Control Dependencies")
print("="*60)

# Test 5.1: Control structure dependencies
results.append(run_test(
    "Control Structure Dependencies",
    """
    cpg.method.name("heap_fetch").ast.isControlStructure.take(3).flatMap { ctrl =>
        ctrl._cdgOut.take(5).map { dependent =>
            Map(
                "controlType" -> ctrl.controlStructureType,
                "controlCode" -> ctrl.code,
                "controlLine" -> ctrl.lineNumber.map(_.toString).getOrElse("unknown"),
                "dependentLabel" -> dependent.label,
                "dependentLine" -> dependent.property("LINE_NUMBER").map(_.toString).getOrElse("unknown")
            )
        }
    }.take(15).l
    """
))

# ============================================================
# 6. FIELD/MEMBER ACCESS FLOW
# ============================================================

print("\n" + "="*60)
print("CATEGORY 6: Field/Member Access Patterns")
print("="*60)

# Test 6.1: Field access data flow
results.append(run_test(
    "Field Access Data Flow",
    """
    cpg.call.name("<operator>.fieldAccess").take(5).flatMap { fa =>
        fa._reachingDefIn.take(3).map { source =>
            Map(
                "fieldAccessCode" -> fa.code,
                "fieldAccessLine" -> fa.lineNumber.map(_.toString).getOrElse("unknown"),
                "sourceLabel" -> source.label,
                "sourceLine" -> source.property("LINE_NUMBER").map(_.toString).getOrElse("unknown")
            )
        }
    }.take(10).l
    """
))

# ============================================================
# 7. COMPLEX FLOW PATTERNS
# ============================================================

print("\n" + "="*60)
print("CATEGORY 7: Complex Multi-Step Flows")
print("="*60)

# Test 7.1: Parameter to Call to Return chain
results.append(run_test(
    "Parameter to Call to Return Chain",
    """
    cpg.method.name("heap_fetch").parameter.name("relation").flatMap { param =>
        param._reachingDefOut.collect {
            case arg: io.shiftleft.codepropertygraph.generated.nodes.Argument =>
                val call = arg.call
                Map(
                    "parameter" -> param.name,
                    "flowsToCall" -> call.name,
                    "argumentIndex" -> arg.argumentIndex.toString,
                    "callLine" -> call.lineNumber.map(_.toString).getOrElse("unknown")
                )
        }
    }.take(10).l
    """
))

# ============================================================
# STATISTICS
# ============================================================

print("\n" + "="*60)
print("CATEGORY 8: DDG Statistics")
print("="*60)

# Test 8.1: Overall DDG edge counts
results.append(run_test(
    "DDG Edge Statistics",
    """
    cpg.method.name("heap_fetch").take(1).map { m =>
        Map(
            "methodName" -> m.name,
            "totalReachingDefEdges" -> m.ast.outE("REACHING_DEF").size.toString,
            "totalCdgEdges" -> m.ast.outE("CDG").size.toString,
            "parameters" -> m.parameter.size.toString,
            "identifiers" -> m.ast.isIdentifier.size.toString,
            "calls" -> m.ast.isCall.size.toString,
            "returns" -> m.ast.isReturn.size.toString
        )
    }.l
    """
))

# Test 8.2: Node type distribution in DDG
results.append(run_test(
    "DDG Target Node Types",
    """
    cpg.method.name("heap_fetch").parameter.flatMap { param =>
        param._reachingDefOut.map(_.label)
    }.groupBy(identity).map { case (label, nodes) =>
        Map("nodeType" -> label, "count" -> nodes.size.toString)
    }.l
    """
))

# ============================================================
# SUMMARY
# ============================================================

print("\n" + "="*60)
print("EXPLORATION SUMMARY")
print("="*60)

passed = [r for r in results if r['status'] == 'success']
failed = [r for r in results if r['status'] == 'failed']

print(f"\nTests Passed: {len(passed)}/{len(results)}")
print(f"\nTest Results:")
for r in results:
    status = "[PASS]" if r['status'] == 'success' else "[FAIL]"
    print(f"  {status} - {r['name']}")

# Save results
output_file = "ddg_exploration_results.json"
with open(output_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n[OK] Results saved to: {output_file}")

print("\n" + "="*60)
print("DDG Pattern Types Identified:")
print("="*60)
print("1. Parameter to Identifier Flow")
print("2. Parameter to Call Argument Flow")
print("3. Parameter to Return Flow")
print("4. Local Variable Assignment Chains")
print("5. Variable Reassignment Chains")
print("6. Call Argument Sources")
print("7. Return Value Sources")
print("8. Control Dependencies (CDG)")
print("9. Field Access Data Flow")
print("10. Complex Multi-Step Flows")

print("\n" + "="*60)
print("DDG Exploration Complete")
print("="*60)
