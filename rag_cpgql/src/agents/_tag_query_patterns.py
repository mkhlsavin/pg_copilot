"""
Tag Query Patterns for Enrichment-Aware Prompt Builder.

Contains comprehensive tag query patterns extracted from export_tags.sc.
Extracted from enrichment_prompt_builder.py for maintainability.
"""

from typing import Dict, List


# Comprehensive tag query patterns extracted from export_tags.sc
TAG_QUERY_PATTERNS: Dict[str, List[str]] = {
    # ==================================================================
    # CATEGORY 1: PARAMETER & RETURN SEMANTIC PATTERNS
    # ==================================================================
    'param-role': [
        # Find methods with parameters of specific role
        'cpg.method.parameter.where(_.tag.nameExact("param-role").valueExact("{value}")).method.name.dedup.l',
        # Find all parameter roles in a method
        'cpg.method.name("{method_name}").parameter.tag.nameExact("param-role").value.l',
        # Find parameters by role across all methods
        'cpg.parameter.where(_.tag.nameExact("param-role").valueExact("{value}")).name.dedup.l',
        # Combine param role with function purpose
        'cpg.method.where(_.parameter.tag.nameExact("param-role").valueExact("{value}")).where(_.tag.nameExact("function-purpose")).name.l',
    ],

    'return-kind': [
        # Find methods returning specific type
        'cpg.method.where(_.tag.nameExact("return-kind").valueExact("{value}")).name.l',
        # Find error-returning methods
        'cpg.method.where(_.tag.nameExact("return-kind").valueExact("error-code")).name.l',
        # Find boolean-returning methods (predicates)
        'cpg.method.where(_.tag.nameExact("return-kind").valueExact("boolean")).name.l',
        # Combine return-kind with domain
        'cpg.method.where(_.tag.nameExact("return-kind").valueExact("{value}")).where(_.tag.nameExact("domain-concept")).name.l',
    ],

    'return-outcome': [
        # Find methods that can fail
        'cpg.method.methodReturn.where(_.tag.nameExact("return-outcome").valueExact("failure")).method.name.dedup.l',
        # Find methods with retry logic
        'cpg.method.methodReturn.where(_.tag.nameExact("return-outcome").valueExact("retry")).method.name.dedup.l',
        # Find successful completion paths
        'cpg.method.methodReturn.where(_.tag.nameExact("return-outcome").valueExact("success")).method.name.dedup.l',
        # Error handlers (failure + error-code)
        'cpg.method.where(_.tag.nameExact("return-kind").valueExact("error-code")).methodReturn.where(_.tag.nameExact("return-outcome").valueExact("failure")).method.name.dedup.l',
    ],

    'validation-required': [
        # Find parameters requiring null checks
        'cpg.parameter.where(_.tag.nameExact("validation-required").valueExact("null-check")).name.l',
        # Find security-sensitive parameters
        'cpg.parameter.where(_.tag.nameExact("validation-required").valueExact("security-check")).method.name.dedup.l',
        # Find sanitization points
        'cpg.parameter.where(_.tag.nameExact("validation-required").valueExact("sanitise")).method.name.dedup.l',
        # Combine validation with param role
        'cpg.parameter.where(_.tag.nameExact("validation-required")).where(_.tag.nameExact("param-role").valueExact("{value}")).method.name.dedup.l',
    ],

    # ==================================================================
    # CATEGORY 2: VARIABLE & IDENTIFIER SEMANTIC PATTERNS
    # ==================================================================
    'variable-role': [
        # Find variables by semantic role
        'cpg.local.where(_.tag.nameExact("variable-role").valueExact("{value}")).name.l',
        # Find methods using specific variable roles
        'cpg.method.where(_.local.tag.nameExact("variable-role").valueExact("{value}")).name.dedup.l',
        # Find iterators in methods
        'cpg.local.where(_.tag.nameExact("variable-role").valueExact("iterator")).method.name.dedup.l',
        # Combine variable role with data kind
        'cpg.local.where(_.tag.nameExact("variable-role").valueExact("{value}")).where(_.tag.nameExact("data-kind")).name.l',
    ],

    'data-kind': [
        # Find variables of specific data kind
        'cpg.identifier.where(_.tag.nameExact("data-kind").valueExact("{value}")).name.dedup.l',
        # Find methods manipulating specific data kinds
        'cpg.method.where(_.identifier.tag.nameExact("data-kind").valueExact("{value}")).name.dedup.l',
        # Find transaction-related variables
        'cpg.identifier.where(_.tag.nameExact("data-kind").valueExact("transaction-id")).method.name.dedup.l',
        # Combine data kind with variable role
        'cpg.local.where(_.tag.nameExact("data-kind").valueExact("{value}")).tag.nameExact("variable-role").value.dedup.l',
    ],

    'security-sensitivity': [
        # Find security-sensitive variables
        'cpg.identifier.where(_.tag.nameExact("security-sensitivity").valueExact("{value}")).name.dedup.l',
        # Find methods handling credentials
        'cpg.method.where(_.identifier.tag.nameExact("security-sensitivity").valueExact("credential")).name.dedup.l',
        # Find secret variables
        'cpg.local.where(_.tag.nameExact("security-sensitivity").valueExact("secret")).name.l',
        # Security-sensitive data flow
        'cpg.identifier.where(_.tag.nameExact("security-sensitivity")).method.name.dedup.l',
    ],

    'lifetime': [
        # Find static variables
        'cpg.local.where(_.tag.nameExact("lifetime").valueExact("static")).name.l',
        # Find auto (local) variables
        'cpg.local.where(_.tag.nameExact("lifetime").valueExact("auto")).method.name.dedup.l',
        # Combine lifetime with mutability
        'cpg.local.where(_.tag.nameExact("lifetime").valueExact("{value}")).tag.nameExact("mutability").value.dedup.l',
    ],

    'mutability': [
        # Find immutable variables
        'cpg.local.where(_.tag.nameExact("mutability").valueExact("immutable")).name.l',
        # Find mutable variables
        'cpg.local.where(_.tag.nameExact("mutability").valueExact("mutable")).method.name.dedup.l',
        # Combine mutability with data kind
        'cpg.local.where(_.tag.nameExact("mutability").valueExact("{value}")).tag.nameExact("data-kind").value.dedup.l',
    ],

    'is-lock': [
        # Find lock-related identifiers
        'cpg.identifier.where(_.tag.nameExact("is-lock").valueExact("{value}")).name.dedup.l',
        # Find methods manipulating locks
        'cpg.method.where(_.identifier.tag.nameExact("is-lock").valueExact("{value}")).name.dedup.l',
        # Combine lock indicators with concurrency primitives
        'cpg.identifier.where(_.tag.nameExact("is-lock").valueExact("{value}")).where(_.tag.nameExact("type-concurrency-primitive")).method.name.dedup.l',
    ],

    'is-pointer-to-struct': [
        # Find pointer variables referencing structs
        'cpg.identifier.where(_.tag.nameExact("is-pointer-to-struct").valueExact("{value}")).name.dedup.l',
        # Find methods using struct pointers
        'cpg.method.where(_.identifier.tag.nameExact("is-pointer-to-struct").valueExact("{value}")).name.dedup.l',
        # Combine with member roles to inspect struct access
        'cpg.identifier.where(_.tag.nameExact("is-pointer-to-struct").valueExact("{value}")).where(_.tag.nameExact("member-role")).method.name.dedup.l',
    ],

    # ==================================================================
    # CATEGORY 3: TYPE & MEMBER SEMANTIC PATTERNS
    # ==================================================================
    'type-category': [
        # Find type declarations by category
        'cpg.typeDecl.where(_.tag.nameExact("type-category").valueExact("{value}")).name.l',
        # Find members for a specific type category
        'cpg.typeDecl.where(_.tag.nameExact("type-category").valueExact("{value}")).member.name.dedup.l',
        # Combine type category with member roles
        'cpg.typeDecl.where(_.tag.nameExact("type-category").valueExact("{value}")).member.tag.nameExact("member-role").value.l',
    ],

    'type-domain-entity': [
        # Find types representing domain entities
        'cpg.typeDecl.where(_.tag.nameExact("type-domain-entity").valueExact("{value}")).name.l',
        # Find methods manipulating the domain entity
        'cpg.method.where(_.identifier.tag.nameExact("type-domain-entity").valueExact("{value}")).name.dedup.l',
        # Combine domain entities with type categories
        'cpg.typeDecl.where(_.tag.nameExact("type-domain-entity").valueExact("{value}")).where(_.tag.nameExact("type-category")).member.name.dedup.l',
    ],

    'type-concurrency-primitive': [
        # Find concurrency primitive type declarations
        'cpg.typeDecl.where(_.tag.nameExact("type-concurrency-primitive").valueExact("{value}")).name.l',
        # Find methods using concurrency primitives
        'cpg.method.where(_.identifier.tag.nameExact("type-concurrency-primitive").valueExact("{value}")).name.dedup.l',
        # Combine concurrency primitive with member roles
        'cpg.typeDecl.where(_.tag.nameExact("type-concurrency-primitive").valueExact("{value}")).member.tag.nameExact("member-role").value.l',
    ],

    'type-ownership-model': [
        # Find types defining ownership policies
        'cpg.typeDecl.where(_.tag.nameExact("type-ownership-model").valueExact("{value}")).name.l',
        # Find methods allocating ownership-managed types
        'cpg.method.where(_.identifier.tag.nameExact("type-ownership-model").valueExact("{value}")).name.dedup.l',
        # Combine ownership models with mutability
        'cpg.typeDecl.where(_.tag.nameExact("type-ownership-model").valueExact("{value}")).member.tag.nameExact("member-role").value.l',
    ],

    'member-role': [
        # Find members by semantic role
        'cpg.member.where(_.tag.nameExact("member-role").valueExact("{value}")).name.l',
        # Find types containing members with the role
        'cpg.typeDecl.where(_.member.tag.nameExact("member-role").valueExact("{value}")).name.dedup.l',
        # Combine member roles with ownership models
        'cpg.typeDecl.where(_.member.tag.nameExact("member-role").valueExact("{value}")).where(_.tag.nameExact("type-ownership-model")).name.l',
    ],

    'member-pointer': [
        # Find pointer members
        'cpg.member.where(_.tag.nameExact("member-pointer").valueExact("{value}")).name.l',
        # Find types with pointer members
        'cpg.typeDecl.where(_.member.tag.nameExact("member-pointer").valueExact("{value}")).name.dedup.l',
        # Combine pointer members with struct categories
        'cpg.typeDecl.where(_.member.tag.nameExact("member-pointer").valueExact("{value}")).where(_.tag.nameExact("type-category")).name.l',
    ],

    'member-length-field': [
        # Find length/size fields
        'cpg.member.where(_.tag.nameExact("member-length-field").valueExact("{value}")).name.l',
        # Find types containing length fields
        'cpg.typeDecl.where(_.member.tag.nameExact("member-length-field").valueExact("{value}")).name.dedup.l',
        # Combine length fields with member roles
        'cpg.member.where(_.tag.nameExact("member-length-field").valueExact("{value}")).tag.nameExact("member-role").value.dedup.l',
    ],

    # ==================================================================
    # CATEGORY 4: LITERAL & CONSTANT SEMANTIC PATTERNS
    # ==================================================================
    'literal-kind': [
        # Find literals by semantic kind
        'cpg.literal.where(_.tag.nameExact("literal-kind").valueExact("{value}")).code.l',
        # Find methods containing specific literal kinds
        'cpg.method.where(_.literal.tag.nameExact("literal-kind").valueExact("{value}")).name.dedup.l',
        # Combine literal kinds with domains
        'cpg.literal.where(_.tag.nameExact("literal-kind").valueExact("{value}")).where(_.tag.nameExact("literal-domain")).code.l',
    ],

    'literal-domain': [
        # Find literals tagged with domain
        'cpg.literal.where(_.tag.nameExact("literal-domain").valueExact("{value}")).code.l',
        # Find methods using literals from domain
        'cpg.method.where(_.literal.tag.nameExact("literal-domain").valueExact("{value}")).name.dedup.l',
    ],

    'literal-severity': [
        # Find literals by severity
        'cpg.literal.where(_.tag.nameExact("literal-severity").valueExact("{value}")).code.l',
        # Find logging calls with specific severity
        'cpg.call.where(_.argument.tag.nameExact("literal-severity").valueExact("{value}")).method.name.dedup.l',
    ],

    'literal-constant': [
        # Find literal constants by symbol
        'cpg.literal.where(_.tag.nameExact("literal-constant").valueExact("{value}")).code.l',
        # Map literal constants to methods
        'cpg.method.where(_.literal.tag.nameExact("literal-constant").valueExact("{value}")).name.dedup.l',
        # Combine literal constants with literal kind
        'cpg.literal.where(_.tag.nameExact("literal-constant").valueExact("{value}")).where(_.tag.nameExact("literal-kind")).code.l',
    ],

    'is-null-constant': [
        # Find null constants
        'cpg.literal.where(_.tag.nameExact("is-null-constant").valueExact("{value}")).code.l',
        # Find null constant usage per method
        'cpg.method.where(_.literal.tag.nameExact("is-null-constant").valueExact("{value}")).name.dedup.l',
    ],

    'is-bitmask': [
        # Find bitmask literals
        'cpg.literal.where(_.tag.nameExact("is-bitmask").valueExact("{value}")).code.l',
        # Find methods using bitmask literals
        'cpg.method.where(_.literal.tag.nameExact("is-bitmask").valueExact("{value}")).name.dedup.l',
        # Combine bitmask literals with literal-kind
        'cpg.literal.where(_.tag.nameExact("is-bitmask").valueExact("{value}")).where(_.tag.nameExact("literal-kind")).code.l',
    ],

    'is-lock-constant': [
        # Find lock-related literal constants
        'cpg.literal.where(_.tag.nameExact("is-lock-constant").valueExact("{value}")).code.l',
        # Find methods using lock constants
        'cpg.method.where(_.literal.tag.nameExact("is-lock-constant").valueExact("{value}")).name.dedup.l',
        # Tie lock constants to lock domain literals
        'cpg.literal.where(_.tag.nameExact("is-lock-constant").valueExact("{value}")).where(_.tag.nameExact("literal-domain").valueExact("lock")).code.l',
    ],

    # ==================================================================
    # CATEGORY 6: NAMESPACE & REFERENCE SEMANTICS
    # ==================================================================
    'namespace-layer': [
        # Find namespaces by architectural layer
        'cpg.namespace.where(_.tag.nameExact("namespace-layer").valueExact("{value}")).name.dedup.l',
        # Find files containing namespace layer
        'cpg.file.where(_.namespace.tag.nameExact("namespace-layer").valueExact("{value}")).name.dedup.l',
        # Find methods in namespace layer
        'cpg.method.where(_.namespace.tag.nameExact("namespace-layer").valueExact("{value}")).name.dedup.l',
    ],

    'namespace-domain': [
        # Find namespaces by domain classification
        'cpg.namespace.where(_.tag.nameExact("namespace-domain").valueExact("{value}")).name.dedup.l',
        # Find methods under namespace domain
        'cpg.method.where(_.namespace.tag.nameExact("namespace-domain").valueExact("{value}")).name.dedup.l',
    ],

    'method-ref-kind': [
        # Find method references by kind
        'cpg.methodRef.where(_.tag.nameExact("method-ref-kind").valueExact("{value}")).name.dedup.l',
        # Find methods defining references of specific kind
        'cpg.method.where(_.methodRef.tag.nameExact("method-ref-kind").valueExact("{value}")).name.dedup.l',
    ],

    'method-ref-usage': [
        # Find method references by usage role
        'cpg.methodRef.where(_.tag.nameExact("method-ref-usage").valueExact("{value}")).name.dedup.l',
        # Find methods that use references with a specific usage
        'cpg.method.where(_.methodRef.tag.nameExact("method-ref-usage").valueExact("{value}")).name.dedup.l',
    ],

    # ==================================================================
    # CATEGORY 7: DATA FLOW & EDGE SEMANTIC ENRICHMENT
    # ==================================================================
    'data-flow-kind': [
        # Find edges by data flow kind
        'cpg.call.where(_.argument.tag.nameExact("data-flow-kind").valueExact("{value}")).name.dedup.l',
        # Find methods producing the flow
        'cpg.method.where(_.call.argument.tag.nameExact("data-flow-kind").valueExact("{value}")).name.dedup.l',
    ],

    'child-role': [
        # Find AST nodes by child role
        'cpg.ast.where(_.tag.nameExact("child-role").valueExact("{value}")).code.l',
        # Map child roles to methods
        'cpg.method.where(_.ast.tag.nameExact("child-role").valueExact("{value}")).name.dedup.l',
    ],

    'call-action': [
        # Find call actions
        'cpg.call.where(_.tag.nameExact("call-action").valueExact("{value}")).name.dedup.l',
        # Link call actions to methods
        'cpg.method.where(_.call.tag.nameExact("call-action").valueExact("{value}")).name.dedup.l',
    ],

    'call-side-effect': [
        # Find calls by side-effect
        'cpg.call.where(_.tag.nameExact("call-side-effect").valueExact("{value}")).name.dedup.l',
        # Find methods with specific side-effects
        'cpg.method.where(_.call.tag.nameExact("call-side-effect").valueExact("{value}")).name.dedup.l',
    ],

    'call-receiver-role': [
        # Find call receivers by role
        'cpg.call.where(_.tag.nameExact("call-receiver-role").valueExact("{value}")).name.dedup.l',
        # Map call receiver roles to methods
        'cpg.method.where(_.call.tag.nameExact("call-receiver-role").valueExact("{value}")).name.dedup.l',
    ],

    'argument-param-name': [
        # Find argument to parameter mappings
        'cpg.call.where(_.argument.tag.nameExact("argument-param-name").valueExact("{value}")).name.dedup.l',
        # Find methods referencing specific arguments
        'cpg.method.where(_.call.argument.tag.nameExact("argument-param-name").valueExact("{value}")).name.dedup.l',
    ],

    'branch-kind': [
        # Find branches by kind
        'cpg.controlStructure.where(_.tag.nameExact("branch-kind").valueExact("{value}")).code.l',
        # Map branch kind to methods
        'cpg.method.where(_.controlStructure.tag.nameExact("branch-kind").valueExact("{value}")).name.dedup.l',
    ],

    'control-reason': [
        # Find control decisions by reason
        'cpg.controlStructure.where(_.tag.nameExact("control-reason").valueExact("{value}")).code.l',
        # Map control reasons back to methods
        'cpg.method.where(_.controlStructure.tag.nameExact("control-reason").valueExact("{value}")).name.dedup.l',
    ],

    # ==================================================================
    # CATEGORY 5: CONTROL FLOW & JUMP SEMANTICS
    # ==================================================================
    'jump-kind': [
        # Find jumps by kind
        'cpg.jump.where(_.tag.nameExact("jump-kind").valueExact("{value}")).code.l',
        # Map jump kind to methods
        'cpg.method.where(_.jump.tag.nameExact("jump-kind").valueExact("{value}")).name.dedup.l',
        # Combine jump kind with domains
        'cpg.jump.where(_.tag.nameExact("jump-kind").valueExact("{value}")).where(_.tag.nameExact("jump-domain")).code.l',
    ],

    'jump-domain': [
        # Find jumps by domain
        'cpg.jump.where(_.tag.nameExact("jump-domain").valueExact("{value}")).code.l',
        # Find methods containing domain-specific jumps
        'cpg.method.where(_.jump.tag.nameExact("jump-domain").valueExact("{value}")).name.dedup.l',
    ],

    'jump-scope': [
        # Find jump scopes
        'cpg.jump.where(_.tag.nameExact("jump-scope").valueExact("{value}")).code.l',
        # Determine methods with specific jump scope
        'cpg.method.where(_.jump.tag.nameExact("jump-scope").valueExact("{value}")).name.dedup.l',
    ],

    'modifier-concurrency': [
        # Find concurrency modifiers
        'cpg.modifier.where(_.tag.nameExact("modifier-concurrency").valueExact("{value}")).code.l',
        # Find methods with concurrency modifiers
        'cpg.method.where(_.modifier.tag.nameExact("modifier-concurrency").valueExact("{value}")).name.dedup.l',
        # Combine concurrency modifiers with variable roles
        'cpg.modifier.where(_.tag.nameExact("modifier-concurrency").valueExact("{value}")).where(_.tag.nameExact("variable-role")).code.l',
    ],

    'modifier-attribute': [
        # Find attribute modifiers
        'cpg.modifier.where(_.tag.nameExact("modifier-attribute").valueExact("{value}")).code.l',
        # Find methods using attribute modifiers
        'cpg.method.where(_.modifier.tag.nameExact("modifier-attribute").valueExact("{value}")).name.dedup.l',
        # Combine attributes with literal severities (e.g., inline logging)
        'cpg.modifier.where(_.tag.nameExact("modifier-attribute").valueExact("{value}")).where(_.method.literal).method.name.dedup.l',
    ],

    # ==================================================================
    # EXISTING PATTERNS
    # ==================================================================
    'function-purpose': [
        # Find all methods with specific purpose
        'cpg.method.where(_.tag.nameExact("function-purpose").valueExact("{value}")).name.l',
        # Find callers of methods with specific purpose
        'cpg.method.where(_.tag.nameExact("function-purpose").valueExact("{value}")).callIn.name.dedup.l',
        # Find files containing methods with specific purpose
        'cpg.file.where(_.method.tag.nameExact("function-purpose").valueExact("{value}")).name.l',
        # Find methods with specific purpose in specific subsystem
        'cpg.method.where(_.tag.nameExact("function-purpose").valueExact("{value}")).where(_.tag.nameExact("subsystem-name")).name.l',
    ],

    'data-structure': [
        # Find methods operating on specific data structure
        'cpg.method.where(_.tag.nameExact("data-structure").valueExact("{value}")).name.l',
        # Find type definitions for data structure
        'cpg.typeDecl.name(".*{value}.*").l',
        # Find methods accessing specific data structure via tags
        'cpg.method.where(_.tag.nameExact("data-structure").valueExact("{value}")).file.name.dedup.l',
    ],

    'domain-concept': [
        # Find methods related to domain concept
        'cpg.method.where(_.tag.nameExact("domain-concept").valueExact("{value}")).name.l',
        # Find calls involving domain concept
        'cpg.call.where(_.method.tag.nameExact("domain-concept").valueExact("{value}")).name.dedup.l',
        # Combine name search with domain-concept tag
        'cpg.method.name(".*{value}.*").where(_.tag.nameExact("domain-concept").valueExact("{value}")).l',
    ],

    'algorithm-class': [
        # Find methods implementing specific algorithm
        'cpg.method.where(_.tag.nameExact("algorithm-class").valueExact("{value}")).name.l',
        # Find complex algorithm implementations
        'cpg.method.where(_.tag.nameExact("algorithm-class").valueExact("{value}")).where(_.tag.nameExact("cyclomatic-complexity")).name.l',
    ],

    'subsystem-name': [
        # Find all methods in subsystem
        'cpg.method.where(_.tag.nameExact("subsystem-name").valueExact("{value}")).name.l',
        # Find subsystem entry points (public APIs)
        'cpg.method.where(_.tag.nameExact("subsystem-name").valueExact("{value}")).where(_.tag.nameExact("api-public").valueExact("true")).name.l',
        # Find files in subsystem
        'cpg.file.where(_.method.tag.nameExact("subsystem-name").valueExact("{value}")).name.dedup.l',
    ],

    'Feature': [
        # Find files implementing feature
        'cpg.file.where(_.tag.nameExact("Feature").valueExact("{value}")).name.l',
        # Find methods implementing feature
        'cpg.method.where(_.file.tag.nameExact("Feature").valueExact("{value}")).name.l',
        # Find feature entry points
        'cpg.method.where(_.file.tag.nameExact("Feature").valueExact("{value}")).where(_.tag.nameExact("api-public")).name.l',
    ],

    'security-risk': [
        # Find high-risk functions
        'cpg.method.where(_.tag.nameExact("security-risk").valueExact("high")).name.l',
        # Find security-sensitive calls
        'cpg.call.where(_.method.tag.nameExact("security-risk")).name.dedup.l',
        # Combine security risk with domain
        'cpg.method.where(_.tag.nameExact("security-risk").valueExact("{value}")).where(_.tag.nameExact("domain-concept")).name.l',
    ],

    'api-category': [
        # Find methods by API category
        'cpg.method.where(_.tag.nameExact("api-category").valueExact("{value}")).name.l',
        # Find public APIs in category
        'cpg.method.where(_.tag.nameExact("api-category").valueExact("{value}")).where(_.tag.nameExact("api-public").valueExact("true")).name.l',
        # Find typical usage patterns
        'cpg.method.where(_.tag.nameExact("api-category").valueExact("{value}")).where(_.tag.nameExact("api-typical-usage")).name.l',
    ],

    'architectural-role': [
        # Find components by architectural role
        'cpg.method.where(_.tag.nameExact("architectural-role").valueExact("{value}")).name.l',
        # Find role interactions
        'cpg.method.where(_.tag.nameExact("architectural-role").valueExact("{value}")).callIn.method.tag.nameExact("architectural-role").value.dedup.l',
    ],

    # New categories for Phase 3 expansion

    'cyclomatic-complexity': [
        # Find simple functions (low complexity)
        'cpg.method.where(_.tag.nameExact("cyclomatic-complexity").value.toInt <= 5).name.l',
        # Find complex functions requiring refactoring
        'cpg.method.where(_.tag.nameExact("cyclomatic-complexity").value.toInt > 15).name.l',
        # Find functions with specific complexity
        'cpg.method.where(_.tag.nameExact("cyclomatic-complexity").valueExact("{value}")).name.l',
    ],

    'test-coverage': [
        # Find untested functions
        'cpg.method.where(_.tag.nameExact("test-coverage").valueExact("untested")).name.l',
        # Find well-tested functions
        'cpg.method.where(_.tag.nameExact("test-coverage").valueExact("full")).name.l',
        # Combine untested with high complexity (high risk!)
        'cpg.method.where(_.tag.nameExact("test-coverage").valueExact("untested")).where(_.tag.nameExact("cyclomatic-complexity").value.toInt > 10).name.l',
    ],

    'refactor-priority': [
        # Find high-priority refactor candidates
        'cpg.method.where(_.tag.nameExact("refactor-priority").valueExact("high")).name.l',
        # Find code needing attention
        'cpg.method.where(_.tag.nameExact("refactor-priority").valueExact("medium")).name.l',
        # Combine refactor priority with test coverage
        'cpg.method.where(_.tag.nameExact("refactor-priority").valueExact("high")).where(_.tag.nameExact("test-coverage")).name.l',
    ],

    'lines-of-code': [
        # Find very small functions
        'cpg.method.where(_.tag.nameExact("lines-of-code").value.toInt <= 5).name.l',
        # Find large functions
        'cpg.method.where(_.tag.nameExact("lines-of-code").value.toInt > 100).name.l',
        # Find single-line functions
        'cpg.method.where(_.tag.nameExact("lines-of-code").valueExact("1")).name.l',
    ],

    'api-public': [
        # Find all public APIs
        'cpg.method.where(_.tag.nameExact("api-public").valueExact("true")).name.l',
        # Find public APIs in specific file
        'cpg.method.where(_.tag.nameExact("api-public").valueExact("true")).file.name.dedup.l',
        # Combine public APIs with typical usage
        'cpg.method.where(_.tag.nameExact("api-public").valueExact("true")).where(_.tag.nameExact("api-typical-usage")).name.l',
    ],

    'api-typical-usage': [
        # Find functions with usage patterns
        'cpg.method.where(_.tag.nameExact("api-typical-usage").valueExact("{value}")).name.l',
        # Find frequently called APIs
        'cpg.method.where(_.tag.nameExact("api-typical-usage")).where(_.tag.nameExact("api-caller-count")).name.l',
    ],

    'loop-depth': [
        # Find nested loop structures
        'cpg.method.where(_.tag.nameExact("loop-depth").value.toInt > 2).name.l',
        # Find simple single-loop functions
        'cpg.method.where(_.tag.nameExact("loop-depth").valueExact("1")).name.l',
        # Combine loop depth with complexity
        'cpg.method.where(_.tag.nameExact("loop-depth").value.toInt > 2).where(_.tag.nameExact("cyclomatic-complexity")).name.l',
    ],

    # Hybrid patterns combining multiple tags
    'hybrid': [
        # Combine purpose + data-structure
        'cpg.method.where(_.tag.nameExact("function-purpose").valueExact("{purpose}")).where(_.tag.nameExact("data-structure").valueExact("{structure}")).name.l',
        # Combine domain + complexity filter
        'cpg.method.where(_.tag.nameExact("domain-concept").valueExact("{domain}")).where(_.tag.nameExact("cyclomatic-complexity").value.toInt < 10).name.l',
        # Combine feature + security
        'cpg.method.where(_.file.tag.nameExact("Feature").valueExact("{feature}")).where(_.tag.nameExact("security-risk")).name.l',
        # Combine subsystem + test coverage (high-value pattern!)
        'cpg.method.where(_.tag.nameExact("subsystem-name").valueExact("{subsystem}")).where(_.tag.nameExact("test-coverage").valueExact("untested")).name.l',
        # Find complex, untested, high-refactor-priority code (technical debt!)
        'cpg.method.where(_.tag.nameExact("cyclomatic-complexity").value.toInt > 15).where(_.tag.nameExact("test-coverage").valueExact("untested")).where(_.tag.nameExact("refactor-priority").valueExact("high")).name.l',
        # Find public APIs with no usage documentation
        'cpg.method.where(_.tag.nameExact("api-public").valueExact("true")).whereNot(_.tag.nameExact("api-typical-usage")).name.l',
    ],
}


# Complexity-aware pattern selection (Phase 3)
COMPLEXITY_PATTERNS: Dict[str, List[str]] = {
    'simple': [
        # Simple patterns for straightforward queries
        'cpg.method.where(_.tag.nameExact("{tag_name}").valueExact("{value}")).name.l',
        'cpg.file.where(_.tag.nameExact("{tag_name}").valueExact("{value}")).name.l',
        'cpg.call.where(_.method.tag.nameExact("{tag_name}").valueExact("{value}")).name.dedup.l',
    ],
    'moderate': [
        # Moderate patterns with some filtering
        'cpg.method.where(_.tag.nameExact("{tag_name}").valueExact("{value}")).callIn.name.dedup.l',
        'cpg.method.where(_.tag.nameExact("{tag_name}").valueExact("{value}")).file.name.dedup.l',
        'cpg.method.where(_.tag.nameExact("{tag_name1}").valueExact("{value1}")).where(_.tag.nameExact("{tag_name2}")).name.l',
    ],
    'complex': [
        # Complex patterns with multiple filters and traversals
        'cpg.method.where(_.tag.nameExact("{tag_name}").valueExact("{value}")).where(_.tag.nameExact("cyclomatic-complexity").value.toInt < 10).callIn.method.name.dedup.l',
        'cpg.file.where(_.method.tag.nameExact("{tag_name}").valueExact("{value}")).method.where(_.tag.nameExact("api-public").valueExact("true")).name.l',
        'cpg.method.where(_.tag.nameExact("{tag_name}").valueExact("{value}")).where(_.tag.nameExact("test-coverage").valueExact("untested")).file.name.dedup.l',
    ]
}


# Intent-specific tag priority mappings
INTENT_TAG_PRIORITY: Dict[str, List[str]] = {
    'find-function': [
        'function-purpose', 'param-role', 'return-kind', 'subsystem-name', 'api-category',
        'domain-concept', 'type-category', 'member-pointer', 'member-pointers',
        'literal-constant', 'literal-constants', 'namespace-layers',
        'data-flow-kind', 'data-flow-kinds', 'child-role', 'child-roles',
        'call-action', 'call-actions', 'call-side-effect', 'call-side-effects',
        'argument-param-name', 'argument-param-names', 'branch-kind', 'branch-kinds'
    ],
    'explain-concept': [
        'domain-concept', 'function-purpose', 'algorithm-class', 'data-structure',
        'type-category', 'type-domain-entity', 'literal-kind', 'literal-kinds',
        'literal-domain', 'literal-domains', 'namespace-domains', 'method-ref-kinds',
        'method-ref-usages', 'data-flow-kind', 'data-flow-kinds', 'child-role', 'child-roles',
        'call-action', 'call-actions', 'call-side-effect', 'call-side-effects',
        'branch-kind', 'branch-kinds'
    ],
    'trace-flow': [
        'data-flow-kind', 'data-flow-kinds', 'child-role', 'child-roles',
        'call-action', 'call-actions', 'call-side-effect', 'call-side-effects',
        'call-receiver-role', 'call-receiver-roles', 'argument-param-name', 'argument-param-names',
        'branch-kind', 'branch-kinds', 'control-reason', 'control-reasons',
        'function-purpose', 'param-role', 'return-kind',
        'subsystem-name', 'architectural-role', 'api-category', 'type-domain-entity',
        'is-lock', 'is-locks', 'is-pointer-to-struct', 'is-pointer-to-structs',
        'member-length-field', 'member-length-fields', 'literal-domain', 'literal-domains',
        'jump-kinds', 'jump-domains', 'jump-scopes', 'modifier-concurrencies', 'namespace-layers'
    ],
    'security-check': [
        'validation-required', 'security-risk', 'param-role', 'function-purpose',
        'api-category', 'domain-concept', 'literal-severity', 'literal-severities',
        'literal-kind', 'literal-kinds', 'modifier-concurrencies', 'method-ref-usages',
        'call-side-effect', 'call-side-effects', 'branch-kind', 'branch-kinds',
        'control-reason', 'control-reasons',
        'data-flow-kind', 'data-flow-kinds'
    ],
    'find-bug': [
        'test-coverage', 'cyclomatic-complexity', 'return-outcome', 'security-risk',
        'refactor-priority', 'is-pointer-to-struct', 'is-pointer-to-structs',
        'literal-kind', 'literal-kinds', 'literal-severity', 'literal-severities',
        'literal-constant', 'literal-constants', 'jump-kinds', 'namespace-domains',
        'branch-kind', 'branch-kinds', 'control-reason', 'control-reasons',
        'call-side-effect', 'call-side-effects',
        'call-action', 'call-actions', 'data-flow-kind', 'data-flow-kinds'
    ],
    'analyze-component': [
        'subsystem-name', 'Feature', 'architectural-role', 'domain-concept', 'type-category',
        'type-ownership-model', 'member-pointer', 'member-pointers', 'member-length-field',
        'member-length-fields', 'literal-domain', 'literal-domains', 'modifier-attributes',
        'namespace-layers', 'method-ref-kinds', 'method-ref-usages', 'data-flow-kind',
        'data-flow-kinds', 'call-action', 'call-actions', 'call-side-effect',
        'call-side-effects', 'call-receiver-role', 'call-receiver-roles', 'argument-param-name',
        'argument-param-names', 'child-role', 'child-roles', 'branch-kind', 'branch-kinds',
        'control-reason', 'control-reasons'
    ],
    'api-usage': [
        'param-role', 'return-kind', 'api-category', 'api-public', 'api-typical-usage',
        'function-purpose', 'type-category', 'literal-domain', 'literal-domains',
        'literal-kind', 'literal-kinds', 'method-ref-kinds', 'method-ref-usages',
        'argument-param-name', 'argument-param-names', 'call-action', 'call-actions',
        'call-side-effect', 'call-side-effects', 'call-receiver-role', 'call-receiver-roles',
        'data-flow-kind', 'data-flow-kinds', 'control-reason', 'control-reasons'
    ],
}


__all__ = [
    'TAG_QUERY_PATTERNS',
    'COMPLEXITY_PATTERNS',
    'INTENT_TAG_PRIORITY',
]
