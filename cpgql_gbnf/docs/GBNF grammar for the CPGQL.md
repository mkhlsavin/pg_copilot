# Grammar for the CPGQL Query Language (GBNF Notation)

## Overview of GBNF Notation and CPGQL Structure

**GBNF (Grammar BNF)** is an EBNF-style format used for specifying grammars, as supported by tools like XGrammar[\[1\]](https://xgrammar.mlc.ai/docs/tutorials/ebnf_guided_generation.html#:~:text=Then%20specify%20an%20EBNF%20grammar,with%20the%20specification%20here). We will use GBNF to formally describe **CPGQL**, the Code Property Graph Query Language used in Joern. A CPGQL query is essentially a *graph traversal* composed of a root followed by a chain of steps. According to Joern’s documentation, a query consists of:

1. A **root object** (the code property graph, cpg)

2. Zero or more **Node-Type Steps** (traverse to nodes of a given type)

3. Zero or more **Filter Steps**, **Map Steps**, or **Repeat Steps** (refine or transform the traversal)

4. Zero or more **Property Directives** (access node properties)

5. Zero or more **Execution Directives** (execute the traversal to yield results)

6. Zero or more **Augmentation Directives** (modify/extend the graph)[\[2\]](https://docs.joern.io/traversal-basics/#:~:text=A%20query%20consists%20of%20the,following%20components)

For example, the query cpg.method.name.toList breaks down as: cpg (root object), .method (node-type step selecting all METHOD nodes), .name (property directive for the NAME property), and .toList (execution directive returning the results in a list)[\[3\]](https://docs.joern.io/traversal-basics/#:~:text=cpg). Queries are typically written as a fluent chain separated by .. They can include inline lambda expressions for filtering and mapping, using Scala-like syntax (e.g. filter(\_.condition) or map(x \=\> ... )). Below, we present the full grammar of CPGQL in GBNF form, covering all these components.

## GBNF Grammar for CPGQL

Below is the **Extended Backus–Naur Form (EBNF)** grammar for CPGQL, using GBNF notation. This grammar captures the core syntax of CPGQL queries as described in Joern’s reference documentation:

root            ::= "cpg" ( "." step )\* \[ executionDirective \]  
step            ::= nodeTypeStep   
                 | propertyStep   
                 | filterStep   
                 | mapStep   
                 | repeatStep   
                 | coreStep   
                 | complexStep   
                 | augmentationDirective   
                 | helpDirective 

; Node-Type Steps – select nodes by type (all, method, call, etc.)  
nodeTypeStep    ::= "all"  
                 | "block" | "call" | "comment" | "controlStructure"   
                 | "file" | "identifier" | "literal" | "local"   
                 | "member" | "metaData" | "method" | "methodRef"   
                 | "methodReturn" | "modifier" | "namespace"   
                 | "namespaceBlock" | "parameter" | "returns"   
                 | "tag" | "typeDecl" | "typ"   
                 | "break" | "continue" | "ifBlock"  (\* specific control structures \*)  
                 | "elseBlock" | "switch" | "case"   (\* additional control structures \*)

; Property Steps – access or filter by node properties (e.g. name, code, id)  
propertyStep    ::= propertyName \[ propertyModifier \] \[ "(" literalOrPattern ")" \]  
propertyName    ::= "code" | "name" | "fullName" | "signature"   
                 | "label" | "id" | "lineNumber" | "lineNumberEnd"   
                 | "order" | "argumentIndex" | "parserTypeName"   
                 | "evaluationStrategy" | "typeFullName" | "value"   
                 | "hash" | "version" | "language"   
propertyModifier::= "Exact" | "Not" | "ExactNot"  
literalOrPattern::= stringLiteral | numericLiteral 

; Filter Steps – filter current nodes by a predicate (Scala lambda returning boolean or traversal)  
filterStep      ::= "filter"    "(" lambdaExpr ")"   
                 | "filterNot" "(" lambdaExpr ")"   
                 | "where"     "(" lambdaExpr ")"   
                 | "whereNot"  "(" lambdaExpr ")"   
                 | "and"       "(" lambdaExpr ( "," lambdaExpr )+ ")"   
                 | "or"        "(" lambdaExpr ( "," lambdaExpr )+ ")" 

; Map and Side-Effect Steps – transform or perform actions on nodes  
mapStep         ::= "map"       "(" lambdaExpr ")"   
                 | "sideEffect" "(" lambdaExpr ")" 

; Repeat Steps – repeated traversal with optional emit/until modifiers (curried parameters)  
repeatStep      ::= "repeat" "(" lambdaTraversal ")" "(" repeatModifiers ")"   
repeatModifiers ::= \[ "emit" "(" lambdaExpr ")" \]   
                    \[ "until" "(" lambdaExpr ")" \]   
                    \[ ( "maxDepth" | "times" ) "(" numericLiteral ")" \]

; Core Steps – miscellaneous traversal operations  
coreStep        ::= "clone" | "dedup"   
                 | "start"          (\* start a new traversal from current node \*)   
                 | "internal" | "external"  (\* filter methods: internal vs external \*)  
                 | "push" | "pop"   (\* (if defined; placeholder for stack ops) \*)

; Complex Steps – higher-level traversals (calls, graph relations, dataflow, etc.)  
complexStep     ::= "callee" | "caller"   
                 | "callOut" | "callIn"   
                 | "argument" | "ast" | "astParent" | "astChildren"   
                 | "isCall" | "isLiteral" | "isIdentifier" | "isControlStructure" | "isReturn"  
                 | "controls" | "controlledBy"   
                 | "dominates" | "dominatedBy"   
                 | "postDominates" | "postDominatedBy"   
                 | "reachableBy"     "(" traversalArg ")"   
                 | "reachableByFlows" "(" traversalArg ")"   
                 | "source" | "sink"   
                 | "tagList"   
                 | "location"   
                 | "isPublic" | "isPrivate" | "isProtected" | "isStatic" | "isVirtual"   
                 | "notControlledBy" \[ "(" stringLiteral ")" \]  (\* optional condition pattern \*)

; Augmentation Directives – mutate/extend the graph  
augmentationDirective ::= "newTagNode"     "(" stringLiteral ")"   
                         | "newTagNodePair" "(" stringLiteral "," stringLiteral ")"   
                         | "store" 

; Execution Directives – execute traversal and format output  
executionDirective ::= "toList" | "l"   
                     | "toJson" | "toJsonPretty"   
                     | "p" | "browse"   
                     | "head" | "size" 

; Help Directive – context-sensitive help  
helpDirective    ::= "help" 

; Lambda expression for filters/maps – shorthand \_ or explicit param \-\> expression  
lambdaExpr      ::= identifier "=\>" expr   
                 | "\_" expr   
lambdaTraversal ::= identifier "=\>" traversalExpr   
                 | "\_" traversalExpr 

; Expressions used in lambdas (for booleans, etc.)  
expr            ::= orExpr   
orExpr          ::= andExpr ( "||" andExpr )\*   
andExpr         ::= comparisonExpr ( "&&" comparisonExpr )\*   
comparisonExpr  ::= valueExpr \[ ( "==" | "\!=" | "\<" | "\>" | "\<=" | "\>=" ) valueExpr \] 

; A chain of property accesses, method calls, or traversals yielding a value  
valueExpr       ::= valueChain \[ "." methodCall \]\*   
valueChain      ::= ( identifier | "\_" ) ( "." chainStep )\*   
chainStep       ::= nodeTypeStep           (\* traverse to sub-nodes by type \*)   
                 | propertyStep           (\* access or filter by property \*)   
                 | complexStep            (\* graph relation step \*)   
                 | coreStep               (\* core traversal operations \*)   
                 | executionDirective     (\* execute traversal (returns value) \*)   
methodCall      ::= identifier "(" \[ argList \] ")"   
                 | identifier             (\* method with no args \*)  
argList         ::= expr ( "," expr )\* 

; A full traversal expression (for arguments to steps like reachableBy)  
traversalExpr   ::= "cpg" ( "." step )\* 

; Terminals: string and numeric literals (follow typical regex for strings/numbers)  
stringLiteral   ::= '\\"' ( \[^"\\n\] | '\\"\\"' )\* '\\"'    (\* double-quoted string, with escapes if needed \*)  
numericLiteral  ::= \[0-9\]+  
identifier      ::= \[A-Za-z\_\]\[A-Za-z0-9\_\]\* 

*(Comments in parentheses (\* ... \*) are explanatory and not part of the grammar.)*

## Explanation of the Grammar

* **Root and Traversal Chain:** A query must start with the literal "cpg" (the root CPG object)[\[3\]](https://docs.joern.io/traversal-basics/#:~:text=cpg). This is followed by zero or more steps, each preceded by a dot. The grammar uses root ::= "cpg" ( "." step )\* to express this fluent chain. An optional executionDirective may terminate the query to produce results[\[4\]](https://docs.joern.io/traversal-basics/#:~:text=queried%202,results%20in%20a%20specific%20format) (e.g. .l, .toList, etc.).

* **Node-Type Steps:** These are simple keywords that select all nodes of a certain type[\[5\]](https://docs.joern.io/cpgql/reference-card/#:~:text=Step%20Description%20,All%20source%20files)[\[6\]](https://docs.joern.io/cpgql/reference-card/#:~:text=,All%20tags). For example, .method selects all METHOD nodes, .file selects all FILE nodes, etc. We include all node-type steps listed in the documentation (method, call, literal, etc.) and a few specific control structure variants like ifBlock, break, continue as mentioned[\[7\]](https://docs.joern.io/cpgql/reference-card/#:~:text=,All%20source%20files)[\[8\]](https://docs.joern.io/cpgql/node-type-steps/#:~:text=Step%20Description%20all%20Visits%20all,based%20Code). Node-type steps take no arguments.

* **Property Steps:** After selecting nodes, one can access their properties. For example, .name or .code will retrieve that property for each node[\[9\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=Property%20Filter%20Steps%20are%20Filter,value%20for%20their%20CODE%20property). In the grammar, propertyStep covers both **property directives** (no argument, returns the property value) and **property filter steps** (with an argument to filter nodes by property)[\[10\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=Property%20Filter%20Steps%20are%20Filter,value%20for%20their%20CODE%20property). If a property step has an argument (in parentheses), it filters the nodes by matching the property against a string or numeric literal. We allow optional modifiers like Exact or Not in the property name to handle variations such as .nameExact("foo") (exact match) or .nameNot("foo") (regex non-match)[\[11\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=joern%3E%20cpg.call.name%28,exit%2842)[\[12\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=their%20negated%20version%20available%3A). For instance, cpg.call.name("exit") keeps call nodes whose NAME matches the regex "exit"[\[11\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=joern%3E%20cpg.call.name%28,exit%2842), while cpg.call.nameExact("exit") would match exactly "exit". Numeric properties (like lineNumber) can be filtered by numeric literals (e.g. .lineNumber(42)). If no argument is given, the property step acts as a projection returning the property values[\[3\]](https://docs.joern.io/traversal-basics/#:~:text=cpg).

* **Filter Steps:** These steps filter the current set of nodes using a boolean predicate[\[13\]](https://docs.joern.io/cpgql/reference-card/#:~:text=Step%20Description%20,predicate). The grammar includes:

* **filter(expr) / filterNot(expr):** Keep nodes for which the lambda expression returns true (or false for filterNot)[\[14\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=filter%20)[\[15\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=,together).

* **where(expr) / whereNot(expr):** Similar to filter, but the expression returns a *traversal* which is checked for non-empty results (for where) or empty (for whereNot)[\[16\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=where%20)[\[17\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=joern%3E%20cpg.call.whereNot%28_.name%28,It%20depends%21%5C%5Cn). For example, cpg.call.where(\_.receivers.size \> 0\) would keep calls that have any receiver.

* **and(pred1, pred2, ...) / or(pred1, pred2, ...):** Higher-order filters that combine multiple predicates with logical AND/OR[\[18\]](https://docs.joern.io/cpgql/reference-card/#:~:text=,multiple%20or%20related%20filter%20traversals). These correspond to Gremlin’s and()/or() steps, requiring all or any of the given traversals to succeed.

The filter lambdas use Scala-like syntax. We allow both the shorthand underscore form and explicit parameters. For instance, cpg.call.filter(\_.name \== "exit") is equivalent to cpg.call.filter(node \=\> node.name \== "exit")[\[19\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=One%20helpful%20trick%20is%20to,it%2C%20that%20is%2C%20the%20node). Inside these lambdas, one can call node properties (node.name), use boolean operators (&&, ||), comparisons (\==, \!=, \<, \>, etc.), and even perform sub-traversals.

* **Map and Side-Effect Steps:** The **map(step)** step transforms each node in the traversal by applying a function[\[20\]](https://docs.joern.io/cpgql/reference-card/#:~:text=Step%20Description%20,step%20by%20applying%20a%20function). For example, one can map a node to a tuple or to one of its properties (e.g., cpg.method.map(m \=\> m.fullName)). The **sideEffect(step)** is similar but is used for executing some side effect (like logging or collecting metrics) without altering the traversed elements[\[20\]](https://docs.joern.io/cpgql/reference-card/#:~:text=Step%20Description%20,step%20by%20applying%20a%20function). Both take a lambda expression. In the grammar, we treat them similarly: mapStep ::= "map"(lambdaExpr) and sideEffect(lambdaExpr). The lambda for map can return any value (including complex tuples as in map(c \=\> (c.name, c.location))[\[21\]](https://docs.joern.io/cpgql/calls/#:~:text=joern%3E%20cpg.call.name%28,l)), while sideEffect’s lambda typically returns Unit (no effect on the traversal output).

* **Repeat Steps:** CPGQL supports advanced *recursive* traversals via the repeat step, often combined with until, emit, and a depth limiter[\[22\]](https://docs.joern.io/cpgql/reference-card/#:~:text=,iteration%20of%20the%20repeat%20loop)[\[23\]](https://docs.joern.io/cpgql/repeat-steps/#:~:text=Repeat%20Steps%20are%20CPGQL%20Steps,repeat%20another%20traversal%20multiple%20times). In Joern’s Scala-based syntax, repeat uses two parameter lists: the first is the traversal to repeat, and the second contains modifiers like until and emit[\[24\]](https://docs.joern.io/cpgql/repeat-steps/#:~:text=repeat..maxDepth%20)[\[25\]](https://docs.joern.io/cpgql/repeat-steps/#:~:text=repeat..until%20). For example:

* cpg.method.repeat(\_.astChildren)(\_.until(\_.isCall))

* repeats going down AST children until a call node is encountered[\[25\]](https://docs.joern.io/cpgql/repeat-steps/#:~:text=repeat..until%20). Our grammar represents this as repeatStep ::= "repeat"("(" lambdaTraversal ")" "(" repeatModifiers ")". The repeatModifiers can include:

* **emit(cond)** – emit interim nodes that satisfy the condition at each iteration[\[26\]](https://docs.joern.io/cpgql/repeat-steps/#:~:text=repeat..emit..maxDepth%20).

* **until(cond)** – stop when the condition becomes true[\[25\]](https://docs.joern.io/cpgql/repeat-steps/#:~:text=repeat..until%20).

* **maxDepth(n)** or **times(n)** – limit the number of repetitions (max depth)[\[27\]](https://docs.joern.io/cpgql/repeat-steps/#:~:text=repeat..maxDepth%20). (Joern uses maxDepth, analogous to Gremlin’s times).

These can be combined. For instance, repeat(\_.astChildren)(\_.emit(\_.isControlStructure).until(\_.isCall)) will traverse down AST children, emit any control structure nodes along the way, and stop when a CALL is reached[\[28\]](https://docs.joern.io/cpgql/repeat-steps/#:~:text=repeat..emit..until%20). The grammar allows any combination of emit, until, and a depth limiter, consistent with the documented patterns[\[26\]](https://docs.joern.io/cpgql/repeat-steps/#:~:text=repeat..emit..maxDepth%20)[\[28\]](https://docs.joern.io/cpgql/repeat-steps/#:~:text=repeat..emit..until%20).

* **Core Steps:** We include common traversal utility steps:

* **clone** – produces a duplicate of the current traversal (useful for branching).

* **dedup** – removes duplicate nodes in the traversal[\[20\]](https://docs.joern.io/cpgql/reference-card/#:~:text=Step%20Description%20,step%20by%20applying%20a%20function).

* **start** – explicitly start a new traversal from the current element (often used within lambdas). For example, x.start.ast treats x as a new starting point for an AST traversal.

* **internal / external** – filter methods by whether they are defined in the project or are external library methods. In queries, cpg.method.internal yields methods with isExternal=false, and cpg.method.external yields those with isExternal=true[\[29\]](https://queries.joern.io/#:~:text=).

* (Other core-like operations can be added as needed; we included push/pop as placeholders).

* **Complex Steps:** These are higher-level steps that encapsulate common multi-hop traversals or queries:

* **Call graph steps:** .callOut and .callIn to go from methods to their outgoing calls or incoming calls[\[30\]](https://docs.joern.io/cpgql/calls/#:~:text=Traversals%20Description%20Example%20,callIn.code.l); .callee and .caller to traverse the call graph (similar concept).

* **Arguments:** .argument traverses from a call to its argument nodes (actual parameters)[\[31\]](https://docs.joern.io/cpgql/calls/#:~:text=Code%20string%20,argument.code.l). Similarly, one can traverse .parameter from a method to its parameters (though .parameter can be node-type or context-dependent).

* **AST steps:** .ast gives all AST descendants, .astChildren gives direct children in the AST, and .astParent goes to the parent in the AST (upwards traversal)[\[32\]](https://docs.joern.io/cpgql/calls/#:~:text=,block). These are useful for syntax-tree queries.

* **Type filters (isX):** We include filters like .isCall, .isLiteral, .isIdentifier, .isReturn, .isControlStructure which restrict the traversal to nodes of that type (these steps return a traversal of the same nodes if they match the type, effectively acting as type checks)[\[33\]](https://docs.joern.io/cpgql/control-flow-steps/#:~:text=controls%20)[\[34\]](https://docs.joern.io/cpgql/control-flow-steps/#:~:text=controlledBy%20). For example, \_.isCall in a predicate returns true if the node is a CALL node.

* **Control-flow graph steps:** .controls (find nodes controlled by this node)[\[33\]](https://docs.joern.io/cpgql/control-flow-steps/#:~:text=controls%20), .controlledBy (nodes that control this one)[\[34\]](https://docs.joern.io/cpgql/control-flow-steps/#:~:text=controlledBy%20), .dominates, .dominatedBy, .postDominates, .postDominatedBy – these traverse the control-flow dominator relationships[\[35\]](https://docs.joern.io/cpgql/control-flow-steps/#:~:text=dominates%20)[\[36\]](https://docs.joern.io/cpgql/control-flow-steps/#:~:text=dominatedBy%20).

* **Data-flow steps:** .reachableBy(traversal) finds if the current node (often a *sink*) is reachable by data flow from the given *source*[\[37\]](https://docs.joern.io/cpgql/data-flow-steps/#:~:text=reachableBy%20). .reachableByFlows(traversal) returns the actual flow paths[\[38\]](https://docs.joern.io/cpgql/data-flow-steps/#:~:text=reachableByFlows%20). In the grammar, we allow a full traversalExpr inside these, e.g. cpg.call.reachableBy(cpg.method.name("main").parameter). In practice, the argument is often a defined value or a simple traversal as shown in the docs[\[39\]](https://docs.joern.io/cpgql/data-flow-steps/#:~:text=joern%3E%20def%20source%20%3D%20cpg.method.name%28,15L%2C%20closureBindingId%20%3D%20None).

* **Source/Sink tags:** .source and .sink yield known attacker-controlled source nodes or sensitive sink nodes related to the current element (as defined by data-flow tags)[\[40\]](https://docs.joern.io/cpgql/reference-card/#:~:text=,a%20sink%20via%20a%20dataflow).

* **Tag navigation:** .tagList returns any tag nodes attached to the current nodes[\[41\]](https://docs.joern.io/cpgql/reference-card/#:~:text=methods%2C%20literals%2C%20types%20etc,to%20each%20of%20the%20nodes).

* **Location:** .location retrieves location information (typically a special Location node or a tuple of file/line) for each node[\[42\]](https://docs.joern.io/cpgql/calls/#:~:text=%3E%20Use%20%60cpg.call.,more%20available%20options).

* **Modifier checks:** .isPublic, .isPrivate, .isProtected, .isStatic, .isVirtual filter methods by their modifiers[\[43\]](https://docs.joern.io/cpgql/node-type-steps/#:~:text=Complex%20Step%20Description%20isPrivate%20Filter,modifierType%20property%20set%20to%20STATIC). For example, cpg.method.isPublic keeps only methods with a PUBLIC modifier[\[44\]](https://docs.joern.io/cpgql/node-type-steps/#:~:text=Complex%20Step%20Description%20isPrivate%20Filter,connected%20to%20MODIFIER%20nodes%20with).

* **notControlledBy(pattern)**: This step (somewhat specialized) filters flows to those *not* inside a condition matching the given pattern (e.g., not controlled by an if with a certain condition). It can take a string regex as an argument to specify the undesired condition[\[45\]](https://docs.joern.io/cpgql/reference-card/#:~:text=traversed%20nodes%20,a%20sink%20via%20a%20dataflow). If no argument, it simply filters out any control dependence.

*(The list above is not exhaustive but covers the major steps documented in Joern[\[46\]](https://docs.joern.io/cpgql/reference-card/#:~:text=Step%20Description%20,callees%20of%20the%20traversed%20nodes)[\[47\]](https://docs.joern.io/cpgql/reference-card/#:~:text=highlighting%20,a%20sink%20via%20a%20dataflow).)*

* **Augmentation Directives:** These steps modify the graph by adding new nodes/tags. In Joern, newTagNode("KEY") creates a new tag node for each current node, with the given key[\[48\]](https://docs.joern.io/cpgql/augmentation-directives/#:~:text=newTagNode%20)[\[49\]](https://docs.joern.io/cpgql/augmentation-directives/#:~:text=And%20say%20that%20you%E2%80%99d%20like,tags%20you%20want%20to%20create), and newTagNodePair("KEY","VALUE") creates tag nodes with a key and value[\[50\]](https://docs.joern.io/cpgql/augmentation-directives/#:~:text=newTagNodePair%20). After calling these, one typically uses .store to save the changes in a diff graph[\[51\]](https://docs.joern.io/cpgql/augmentation-directives/#:~:text=,nodes%20in%20the%20active%20Code)[\[49\]](https://docs.joern.io/cpgql/augmentation-directives/#:~:text=And%20say%20that%20you%E2%80%99d%20like,tags%20you%20want%20to%20create). The grammar reflects this: e.g., cpg.call.name("err").newTagNode("ERROR").store would tag all calls named "err" and stage the change for commit.

* **Execution Directives:** These steps **terminate** the traversal and produce a result in a certain format[\[52\]](https://docs.joern.io/cpgql/execution-directives/#:~:text=Execution%20Directives%20are%20CPGQL%20Directives,the%20results%20in%20a%20list). In the grammar, we allow at most one execution directive at the end of the query (since executing consumes the traversal). Key directives (from Joern’s reference[\[53\]](https://docs.joern.io/cpgql/reference-card/#:~:text=Execution%20Directives%20)) include:

* .toList (and its shorthand .l) – execute the traversal and collect results into a list[\[54\]](https://docs.joern.io/cpgql/execution-directives/#:~:text=l%20).

* .p – pretty-print the results (good for quick inspection)[\[55\]](https://docs.joern.io/cpgql/execution-directives/#:~:text=p%20).

* .toJson / .toJsonPretty – output the results as JSON.

* .head – get the first result only[\[56\]](https://docs.joern.io/cpgql/execution-directives/#:~:text=head%20).

* .size – get the count of results (an integer)[\[57\]](https://docs.joern.io/cpgql/execution-directives/#:~:text=size%20).

* .browse – open the results in a pager (interactive viewer)[\[58\]](https://docs.joern.io/cpgql/reference-card/#:~:text=,the%20result%20to%20prettified%20JSON).

* **Help Directive:** .help can be appended to any traversal to get interactive help about what methods/steps are available at that point[\[59\]](https://docs.joern.io/cpgql/reference-card/#:~:text=Help%20Directive%20). We include helpDirective ::= "help". (In practice this prints context-sensitive documentation in the Joern REPL.)

* **Lambdas and Expressions:** The grammar defines lambdaExpr to capture the Scala-like lambdas used in filter, where, map, etc. Both forms are supported: the shorthand using \_ and the longhand with an explicit parameter name and \=\>. Inside a lambda, expr can be a boolean or other expression, built from comparisons and logical operators. We allow a fairly general expression grammar:

* The lambda body can call methods or properties on the parameter. For example, \_.name \== "foo" compares a node’s name property[\[60\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=One%20helpful%20trick%20is%20to,it%2C%20that%20is%2C%20the%20node), and \_.code.contains("42") calls the standard string method contains on the code property[\[61\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=And%20their%20expression%20can%20contain,any%20combination%20of%20boolean%20statements).

* We support chaining traversal steps inside lambdas. For instance, \_.ast.isReturn.l.size \> 1 (used to find methods with multiple returns) is parsed as: take the current node, go to its AST children that are returns, collect them to a list, get the size, and compare to 1[\[62\]](https://queries.joern.io/#:~:text=CPGQL%20Query%3A)[\[63\]](https://queries.joern.io/#:~:text=%28%7Bcpg.method.internal.filter%28_.ast.isReturn.l.size%20%3E%201%29.nameNot%28). Our valueChain nonterminal covers such sub-traversals. Similarly, one can do \_.start to get back a Traversal from a node inside a lambda (enabling use of traversal steps like .argument as in c.start.argument.code)[\[21\]](https://docs.joern.io/cpgql/calls/#:~:text=joern%3E%20cpg.call.name%28,l).

* Common Scala/Java methods like toString(), get (for Options), or string checks (endsWith, startsWith, etc.) are allowed in expressions. The grammar’s methodCall rule is generic, allowing any identifier with optional arguments. For example, \_.location.lineNumber.get would be parsed as a chain where location is a step yielding an object (perhaps an Option), then .get as a method call retrieving the value[\[64\]](https://queries.joern.io/#:~:text=author%3A%20%40fabsx00).

* Arithmetic or other operations can appear as part of expressions (the grammar currently focuses on comparisons and boolean ops, but can be extended similarly).

**Note:** The grammar above is comprehensive with respect to Joern’s documented query language features as of 2025\. It is based on the Joern documentation[\[2\]](https://docs.joern.io/traversal-basics/#:~:text=A%20query%20consists%20of%20the,following%20components)[\[53\]](https://docs.joern.io/cpgql/reference-card/#:~:text=Execution%20Directives%20) and examples of valid CPGQL queries[\[62\]](https://queries.joern.io/#:~:text=CPGQL%20Query%3A)[\[11\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=joern%3E%20cpg.call.name%28,exit%2842). If certain method names or steps are not used in a given context, they will simply have no effect or cause a runtime error, but syntactically the grammar permits them. This grammar should enable guided generation or parsing of CPGQL queries, ensuring that generated queries follow the correct structure (root object, then a sequence of valid steps, optional execution at end, etc.) as per Joern’s query language specification.

---

[\[1\]](https://xgrammar.mlc.ai/docs/tutorials/ebnf_guided_generation.html#:~:text=Then%20specify%20an%20EBNF%20grammar,with%20the%20specification%20here) EBNF-Guided Generation — XGrammar 0.1.25 documentation

[https://xgrammar.mlc.ai/docs/tutorials/ebnf\_guided\_generation.html](https://xgrammar.mlc.ai/docs/tutorials/ebnf_guided_generation.html)

[\[2\]](https://docs.joern.io/traversal-basics/#:~:text=A%20query%20consists%20of%20the,following%20components) [\[3\]](https://docs.joern.io/traversal-basics/#:~:text=cpg) [\[4\]](https://docs.joern.io/traversal-basics/#:~:text=queried%202,results%20in%20a%20specific%20format) Traversal Basics | Joern Documentation

[https://docs.joern.io/traversal-basics/](https://docs.joern.io/traversal-basics/)

[\[5\]](https://docs.joern.io/cpgql/reference-card/#:~:text=Step%20Description%20,All%20source%20files) [\[6\]](https://docs.joern.io/cpgql/reference-card/#:~:text=,All%20tags) [\[7\]](https://docs.joern.io/cpgql/reference-card/#:~:text=,All%20source%20files) [\[13\]](https://docs.joern.io/cpgql/reference-card/#:~:text=Step%20Description%20,predicate) [\[18\]](https://docs.joern.io/cpgql/reference-card/#:~:text=,multiple%20or%20related%20filter%20traversals) [\[20\]](https://docs.joern.io/cpgql/reference-card/#:~:text=Step%20Description%20,step%20by%20applying%20a%20function) [\[22\]](https://docs.joern.io/cpgql/reference-card/#:~:text=,iteration%20of%20the%20repeat%20loop) [\[40\]](https://docs.joern.io/cpgql/reference-card/#:~:text=,a%20sink%20via%20a%20dataflow) [\[41\]](https://docs.joern.io/cpgql/reference-card/#:~:text=methods%2C%20literals%2C%20types%20etc,to%20each%20of%20the%20nodes) [\[45\]](https://docs.joern.io/cpgql/reference-card/#:~:text=traversed%20nodes%20,a%20sink%20via%20a%20dataflow) [\[46\]](https://docs.joern.io/cpgql/reference-card/#:~:text=Step%20Description%20,callees%20of%20the%20traversed%20nodes) [\[47\]](https://docs.joern.io/cpgql/reference-card/#:~:text=highlighting%20,a%20sink%20via%20a%20dataflow) [\[53\]](https://docs.joern.io/cpgql/reference-card/#:~:text=Execution%20Directives%20) [\[58\]](https://docs.joern.io/cpgql/reference-card/#:~:text=,the%20result%20to%20prettified%20JSON) [\[59\]](https://docs.joern.io/cpgql/reference-card/#:~:text=Help%20Directive%20) Reference Card | Joern Documentation

[https://docs.joern.io/cpgql/reference-card/](https://docs.joern.io/cpgql/reference-card/)

[\[8\]](https://docs.joern.io/cpgql/node-type-steps/#:~:text=Step%20Description%20all%20Visits%20all,based%20Code) [\[43\]](https://docs.joern.io/cpgql/node-type-steps/#:~:text=Complex%20Step%20Description%20isPrivate%20Filter,modifierType%20property%20set%20to%20STATIC) [\[44\]](https://docs.joern.io/cpgql/node-type-steps/#:~:text=Complex%20Step%20Description%20isPrivate%20Filter,connected%20to%20MODIFIER%20nodes%20with) Node-Type Steps | Joern Documentation

[https://docs.joern.io/cpgql/node-type-steps/](https://docs.joern.io/cpgql/node-type-steps/)

[\[9\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=Property%20Filter%20Steps%20are%20Filter,value%20for%20their%20CODE%20property) [\[10\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=Property%20Filter%20Steps%20are%20Filter,value%20for%20their%20CODE%20property) [\[11\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=joern%3E%20cpg.call.name%28,exit%2842) [\[12\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=their%20negated%20version%20available%3A) [\[14\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=filter%20) [\[15\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=,together) [\[16\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=where%20) [\[17\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=joern%3E%20cpg.call.whereNot%28_.name%28,It%20depends%21%5C%5Cn) [\[19\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=One%20helpful%20trick%20is%20to,it%2C%20that%20is%2C%20the%20node) [\[60\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=One%20helpful%20trick%20is%20to,it%2C%20that%20is%2C%20the%20node) [\[61\]](https://docs.joern.io/cpgql/filter-steps/#:~:text=And%20their%20expression%20can%20contain,any%20combination%20of%20boolean%20statements) Filter Steps | Joern Documentation

[https://docs.joern.io/cpgql/filter-steps/](https://docs.joern.io/cpgql/filter-steps/)

[\[21\]](https://docs.joern.io/cpgql/calls/#:~:text=joern%3E%20cpg.call.name%28,l) [\[30\]](https://docs.joern.io/cpgql/calls/#:~:text=Traversals%20Description%20Example%20,callIn.code.l) [\[31\]](https://docs.joern.io/cpgql/calls/#:~:text=Code%20string%20,argument.code.l) [\[32\]](https://docs.joern.io/cpgql/calls/#:~:text=,block) [\[42\]](https://docs.joern.io/cpgql/calls/#:~:text=%3E%20Use%20%60cpg.call.,more%20available%20options) Calls | Joern Documentation

[https://docs.joern.io/cpgql/calls/](https://docs.joern.io/cpgql/calls/)

[\[23\]](https://docs.joern.io/cpgql/repeat-steps/#:~:text=Repeat%20Steps%20are%20CPGQL%20Steps,repeat%20another%20traversal%20multiple%20times) [\[24\]](https://docs.joern.io/cpgql/repeat-steps/#:~:text=repeat..maxDepth%20) [\[25\]](https://docs.joern.io/cpgql/repeat-steps/#:~:text=repeat..until%20) [\[26\]](https://docs.joern.io/cpgql/repeat-steps/#:~:text=repeat..emit..maxDepth%20) [\[27\]](https://docs.joern.io/cpgql/repeat-steps/#:~:text=repeat..maxDepth%20) [\[28\]](https://docs.joern.io/cpgql/repeat-steps/#:~:text=repeat..emit..until%20) Repeat Steps | Joern Documentation

[https://docs.joern.io/cpgql/repeat-steps/](https://docs.joern.io/cpgql/repeat-steps/)

[\[29\]](https://queries.joern.io/#:~:text=) [\[62\]](https://queries.joern.io/#:~:text=CPGQL%20Query%3A) [\[63\]](https://queries.joern.io/#:~:text=%28%7Bcpg.method.internal.filter%28_.ast.isReturn.l.size%20%3E%201%29.nameNot%28) [\[64\]](https://queries.joern.io/#:~:text=author%3A%20%40fabsx00) Joern Query Database | Joern Query Database

[https://queries.joern.io/](https://queries.joern.io/)

[\[33\]](https://docs.joern.io/cpgql/control-flow-steps/#:~:text=controls%20) [\[34\]](https://docs.joern.io/cpgql/control-flow-steps/#:~:text=controlledBy%20) [\[35\]](https://docs.joern.io/cpgql/control-flow-steps/#:~:text=dominates%20) [\[36\]](https://docs.joern.io/cpgql/control-flow-steps/#:~:text=dominatedBy%20) Control-Flow Steps | Joern Documentation

[https://docs.joern.io/cpgql/control-flow-steps/](https://docs.joern.io/cpgql/control-flow-steps/)

[\[37\]](https://docs.joern.io/cpgql/data-flow-steps/#:~:text=reachableBy%20) [\[38\]](https://docs.joern.io/cpgql/data-flow-steps/#:~:text=reachableByFlows%20) [\[39\]](https://docs.joern.io/cpgql/data-flow-steps/#:~:text=joern%3E%20def%20source%20%3D%20cpg.method.name%28,15L%2C%20closureBindingId%20%3D%20None) Data-Flow Steps | Joern Documentation

[https://docs.joern.io/cpgql/data-flow-steps/](https://docs.joern.io/cpgql/data-flow-steps/)

[\[48\]](https://docs.joern.io/cpgql/augmentation-directives/#:~:text=newTagNode%20) [\[49\]](https://docs.joern.io/cpgql/augmentation-directives/#:~:text=And%20say%20that%20you%E2%80%99d%20like,tags%20you%20want%20to%20create) [\[50\]](https://docs.joern.io/cpgql/augmentation-directives/#:~:text=newTagNodePair%20) [\[51\]](https://docs.joern.io/cpgql/augmentation-directives/#:~:text=,nodes%20in%20the%20active%20Code) Augmentation Directives | Joern Documentation

[https://docs.joern.io/cpgql/augmentation-directives/](https://docs.joern.io/cpgql/augmentation-directives/)

[\[52\]](https://docs.joern.io/cpgql/execution-directives/#:~:text=Execution%20Directives%20are%20CPGQL%20Directives,the%20results%20in%20a%20list) [\[54\]](https://docs.joern.io/cpgql/execution-directives/#:~:text=l%20) [\[55\]](https://docs.joern.io/cpgql/execution-directives/#:~:text=p%20) [\[56\]](https://docs.joern.io/cpgql/execution-directives/#:~:text=head%20) [\[57\]](https://docs.joern.io/cpgql/execution-directives/#:~:text=size%20) Execution Directives | Joern Documentation

[https://docs.joern.io/cpgql/execution-directives/](https://docs.joern.io/cpgql/execution-directives/)