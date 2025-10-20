# Phase 3: DDG API Research - Final Findings

## Test Results Summary

**Tests Passed**: 10/12 (83% success rate)

### Working DDG Pattern Types

1. **Parameter to Identifier Flow** ✓
   - Parameters flow to identifiers in method body
   - Can track which lines use parameter values
   - Example: `relation` parameter flows to identifier at line 1571

2. **Parameter to Return Flow** ✓
   - Can track if parameters flow to return statements
   - Currently empty for heap_fetch (no direct param → return)

3. **Local Variable Assignment Chains** ✓
   - Identifier `tuple` traces back to parameter `tuple`
   - Can track definitions of local variables

4. **Variable Reassignment Chains** ✓
   - Identifier-to-identifier data flow working
   - Found flows: tid→tid, buffer→buffer, relation→relation

5. **Call Argument Sources** ✓
   - Can track what values reach call arguments
   - Property access issue with `.property("LINE_NUMBER")` but query runs

6. **Return Value Sources** ✓
   - Can track what values flow to return statements

7. **Control Dependencies (CDG)** ✓
   - `_cdgOut` traversal works
   - Can find nodes dependent on control structures

8. **Field Access Data Flow** ✓
   - Can track data flow for field access operations

9. **DDG Edge Statistics** ✓
   - **CRITICAL**: heap_fetch has 425 REACHING_DEF edges, 185 CDG edges
   - 5 parameters, 61 identifiers, 98 calls, 4 returns

10. **DDG Target Node Types** ✓
    - Parameters flow to:
      - IDENTIFIER: 14 instances
      - METHOD_PARAMETER_OUT: 9 instances
      - CALL: 1 instance
      - METHOD_RETURN: 4 instances

### Failed Pattern Types

1. **Parameter to Call Argument Flow** ✗
   - Error: `Argument` type doesn't exist in Joern
   - Solution: Use `CALL` node type instead

2. **Parameter to Call to Return Chain** ✗
   - Same `Argument` type issue

## Correct API Patterns

### Working Traversals

```scala
// Parameter to identifier flow
param._reachingDefOut.collect {
    case i: io.shiftleft.codepropertygraph.generated.nodes.Identifier =>
        i.code  // Works!
}

// Identifier to definition source
ident._reachingDefIn.collect {
    case call: io.shiftleft.codepropertygraph.generated.nodes.Call =>
        call.name  // Works!
    case param: io.shiftleft.codepropertygraph.generated.nodes.MethodParameterIn =>
        param.name  // Works!
}

// Control dependencies
ctrl._cdgOut.map { dependent =>
    dependent.label  // Works!
}

// Edge counting
m.ast.outE("REACHING_DEF").size  // Returns 425 for heap_fetch
m.ast.outE("CDG").size  // Returns 185 for heap_fetch
```

### Property Access

✓ **WORKS**:
- `.label` - node type
- `.code` - source code (on specific node types after casting)
- `.name` - name property
- `.lineNumber.map(_.toString).getOrElse("unknown")` - line number

✗ **DOESN'T WORK**:
- `.property("LINE_NUMBER")` - returns Null, can't use .map on it

### Node Type Casting

```scala
// Use collect with case patterns for type-specific handling
param._reachingDefOut.collect {
    case i: io.shiftleft.codepropertygraph.generated.nodes.Identifier =>
        Map("type" -> "IDENTIFIER", "code" -> i.code)
    case c: io.shiftleft.codepropertygraph.generated.nodes.Call =>
        Map("type" -> "CALL", "name" -> c.name)
    case r: io.shiftleft.codepropertygraph.generated.nodes.Return =>
        Map("type" -> "RETURN", "code" -> r.code)
}
```

## DDG Pattern Categories for Extraction

Based on successful tests, we can extract:

### 1. Parameter Data Flow Patterns
- **Parameter → Identifier**: Where parameters are used
- **Parameter → Method Return**: What parameters contribute to return values
- **Parameter → Call**: Parameters passed to function calls

### 2. Local Variable Dependencies
- **Identifier → Call**: Variables defined by function calls
- **Identifier → Parameter**: Variables coming from parameters
- **Identifier → Identifier**: Variable reassignments

### 3. Return Value Tracking
- **Call → Return**: Function results flowing to return
- **Parameter → Return**: Parameters directly returned
- **Identifier → Return**: Local variables returned

### 4. Control Dependencies
- **Control Structure → Dependent Nodes**: Nodes affected by if/while/for
- Can identify which code executes conditionally

### 5. Call Argument Tracking
- What values reach function call arguments
- Track data flow into critical functions

## Volume Estimation

Based on heap_fetch analysis:
- **425 REACHING_DEF edges** per method
- **185 CDG edges** per method
- Assuming 1,000 methods in PostgreSQL codebase:
  - **~425,000 DDG edges total**
  - **~185,000 CDG edges total**
  - Target extraction: **50,000-100,000 meaningful patterns**

## Implementation Strategy

1. **Extract 5 core pattern types**:
   - Parameter flow patterns (→ identifiers, → returns, → calls)
   - Local variable chains (assignments, reassignments)
   - Return value sources
   - Call argument sources
   - Control dependencies

2. **Batch processing** (like CFG extractor):
   - Process methods in batches of 100
   - Generate natural language descriptions
   - Include line numbers and method context

3. **Natural language descriptions**:
   - "Parameter 'relation' of type Relation flows to identifier at line 1571"
   - "Variable 'tid' from line 1561 flows to identifier 'tid' at line 1571"
   - "Return statement depends on call to HeapTupleSatisfiesMVCC"

4. **ChromaDB integration**:
   - Same structure as CFG patterns
   - Semantic search for "where does parameter X flow"
   - Enable data flow analysis via RAG

## Next Steps

1. ✓ Research complete - API patterns identified
2. → Implement DDGExtractor with 5 pattern types
3. → Test on sample methods
4. → Run full extraction (target: 50K-100K patterns)
5. → Index into ChromaDB
6. → Integrate with EnrichmentPromptBuilder
7. → Complete Phase 3 documentation
