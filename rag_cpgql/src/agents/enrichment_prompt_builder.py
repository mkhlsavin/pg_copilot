"""Enrichment-Aware Prompt Builder for CPGQL Generation.

This module builds prompts that emphasize the use of CPG enrichment tags
to improve query accuracy and coverage.
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from src.agents.tag_effectiveness_tracker import get_global_tracker
from src.validation.tag_validator import get_validator

logger = logging.getLogger(__name__)


# Comprehensive tag query patterns extracted from export_tags.sc
TAG_QUERY_PATTERNS = {
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
COMPLEXITY_PATTERNS = {
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
INTENT_TAG_PRIORITY = {
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


@dataclass
class TagRelevance:
    """Scored tag with relevance information."""
    category: str
    value: str
    score: float
    reason: str  # Why this tag is relevant


class TagRelevanceScorer:
    """Scores enrichment tags by relevance to question and analysis."""

    def __init__(self, use_effectiveness: bool = True):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.use_effectiveness = use_effectiveness
        self.tracker = get_global_tracker() if use_effectiveness else None

    def score_tags(
        self,
        hints: Dict[str, List[str]],
        question: str,
        analysis: Dict
    ) -> List[TagRelevance]:
        """
        Score all enrichment tags by relevance.

        Args:
            hints: Enrichment hints from EnrichmentAgent
            question: User question
            analysis: AnalyzerAgent output

        Returns:
            List of TagRelevance objects sorted by score (descending)
        """
        scored_tags = []

        intent = analysis.get('intent', 'explain-concept')
        domain = analysis.get('domain', 'general')
        keywords = analysis.get('keywords', [])

        # Get intent-based priority tags
        priority_categories = INTENT_TAG_PRIORITY.get(intent, [])

        # Score each tag category
        for category, values in hints.items():
            if not values or category in ['tags', 'coverage_score']:
                # Skip tags (already processed) and coverage_score
                continue

            if not isinstance(values, list):
                # Skip non-list values
                continue

            # Base score from intent alignment
            base_score = 0.5
            if category.replace('_', '-') in priority_categories:
                base_score = 0.8
                reason = f"High-priority for {intent} intent"
            else:
                reason = f"Available tag"

            # Boost for keyword overlap
            for value in values[:5]:  # Limit to top 5 per category
                # Skip non-string values
                if not isinstance(value, str):
                    continue

                keyword_boost = 0.0
                for keyword in keywords:
                    if keyword.lower() in value.lower() or value.lower() in keyword.lower():
                        keyword_boost = 0.2
                        reason = f"Matches keyword '{keyword}'"
                        break

                # Domain alignment boost
                domain_boost = 0.0
                if domain != 'general' and domain.lower() in value.lower():
                    domain_boost = 0.1
                    reason = f"Matches domain '{domain}'"

                # Historical effectiveness boost (Phase 2 enhancement)
                effectiveness_boost = 0.0
                if self.use_effectiveness and self.tracker:
                    # Map category to tag name format
                    tag_name = category.replace('_', '-')
                    if tag_name.endswith('s'):  # Remove plural
                        tag_name = tag_name[:-1]

                    effectiveness = self.tracker.get_tag_effectiveness(tag_name, value)

                    # If effectiveness is significantly different from neutral (0.5):
                    # Boost for high-performing tags (>0.6)
                    # Penalize for low-performing tags (<0.4)
                    if effectiveness > 0.6:
                        effectiveness_boost = 0.15 * (effectiveness - 0.5)
                        reason = f"High-performing tag (score={effectiveness:.2f})"
                    elif effectiveness < 0.4:
                        effectiveness_boost = -0.1 * (0.5 - effectiveness)
                        # Keep original reason but note low performance

                final_score = min(1.0, max(0.0, base_score + keyword_boost + domain_boost + effectiveness_boost))

                scored_tags.append(TagRelevance(
                    category=category,
                    value=value,
                    score=final_score,
                    reason=reason
                ))

        # Sort by score
        scored_tags.sort(key=lambda t: t.score, reverse=True)

        return scored_tags


class EnrichmentPromptBuilder:
    """Builds enrichment-focused prompts for CPGQL generation."""

    def __init__(self, enable_documentation: bool = True, enable_cfg: bool = True, enable_ddg: bool = True):
        self.scorer = TagRelevanceScorer()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.enable_documentation = enable_documentation
        self.enable_cfg = enable_cfg
        self.enable_ddg = enable_ddg

        # Initialize tag validator
        try:
            self.validator = get_validator()
            self.logger.info("Tag validator initialized successfully")
        except Exception as e:
            self.logger.warning(f"Could not initialize tag validator: {e}")
            self.validator = None

        # Initialize documentation retriever if enabled
        self.doc_retriever = None
        if enable_documentation:
            try:
                from src.retrieval.documentation_retriever import DocumentationRetriever
                self.doc_retriever = DocumentationRetriever()
                self.logger.info("Documentation retriever initialized successfully")
            except Exception as e:
                self.logger.warning(f"Could not initialize documentation retriever: {e}")
                self.enable_documentation = False

        # Initialize CFG pattern retriever if enabled
        self.cfg_retriever = None
        if enable_cfg:
            try:
                from src.retrieval.cfg_retriever import CFGRetriever
                self.cfg_retriever = CFGRetriever()
                self.logger.info("CFG pattern retriever initialized successfully")
            except Exception as e:
                self.logger.warning(f"Could not initialize CFG retriever: {e}")
                self.enable_cfg = False

        # Initialize DDG pattern retriever if enabled
        self.ddg_retriever = None
        if enable_ddg:
            try:
                from src.retrieval.ddg_retriever import DDGRetriever
                self.ddg_retriever = DDGRetriever()
                self.logger.info("DDG pattern retriever initialized successfully")
            except Exception as e:
                self.logger.warning(f"Could not initialize DDG retriever: {e}")
                self.enable_ddg = False

    def _validate_and_filter_hints(self, hints: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Validate and filter enrichment hints to keep only valid CPG tags.

        Args:
            hints: Raw enrichment hints with potentially invalid tag values

        Returns:
            Filtered hints containing only valid tag values
        """
        if not self.validator or not hints:
            return hints

        filtered_hints = {}
        invalid_count = 0
        corrected_count = 0

        for category, values in hints.items():
            # Skip non-tag fields
            if category in ['tags', 'coverage_score', 'fallback_applied', 'coverage_improvement', 'hybrid_patterns']:
                filtered_hints[category] = values
                continue

            if not isinstance(values, list):
                filtered_hints[category] = values
                continue

            # Map category names to tag names (e.g., "function_purposes" -> "function-purpose")
            tag_name = category.replace('_', '-')
            if tag_name.endswith('ies'):
                tag_name = tag_name[:-3] + 'y'
            elif tag_name.endswith('s'):
                tag_name = tag_name[:-1]

            # Validate each value
            valid_values = []
            for value in values:
                if not isinstance(value, str):
                    valid_values.append(value)
                    continue

                is_valid, corrected = self.validator.validate_and_correct(tag_name, value)

                if is_valid:
                    if corrected:
                        # Use corrected value
                        valid_values.append(corrected)
                        corrected_count += 1
                        self.logger.info(f"Corrected tag: {category}='{value}' -> '{corrected}'")
                    else:
                        # Original value is valid
                        valid_values.append(value)
                else:
                    # Invalid and no correction available
                    invalid_count += 1
                    self.logger.warning(f"Filtered invalid tag: {category}='{value}' (not in CPG)")

                    # Try to suggest valid alternatives
                    valid_alternatives = self.validator.get_valid_values(tag_name)
                    if valid_alternatives:
                        self.logger.debug(f"  Valid {tag_name} values: {', '.join(valid_alternatives[:5])}")

            if valid_values:
                filtered_hints[category] = valid_values

        if invalid_count > 0 or corrected_count > 0:
            self.logger.info(f"Tag validation: {corrected_count} corrected, {invalid_count} removed")

        return filtered_hints

    def build_enrichment_context(
        self,
        hints: Dict[str, List[str]],
        question: str,
        analysis: Dict,
        max_tags: int = 7,
        max_patterns: int = 5
    ) -> str:
        """
        Build enrichment context section for CPGQL generation prompt.

        Args:
            hints: Enrichment hints from EnrichmentAgent
            question: User question
            analysis: AnalyzerAgent output
            max_tags: Maximum number of tags to show
            max_patterns: Maximum number of query patterns to show

        Returns:
            Formatted enrichment context string
        """
        if not hints or all(not v for v in hints.values()):
            return ""

        # Validate and filter hints to keep only valid CPG tags
        hints = self._validate_and_filter_hints(hints)

        if not hints or all(not v for v in hints.values()):
            self.logger.warning("No valid tags remaining after validation")
            return ""

        # Score and select top tags
        scored_tags = self.scorer.score_tags(hints, question, analysis)
        top_tags = scored_tags[:max_tags]

        # Ensure control reasons surface when available (Category 7 linkage)
        control_values = hints.get('control_reasons', [])
        if control_values:
            control_index = next((idx for idx, tag in enumerate(top_tags) if tag.category == 'control_reasons'), None)
            if control_index is None:
                control_tag = TagRelevance(
                    category='control_reasons',
                    value=control_values[0],
                    score=1.0,
                    reason='Critical control rationale for flow analysis'
                )
            else:
                control_tag = top_tags.pop(control_index)
                control_tag.score = max(control_tag.score, 0.95)
            # Prepend control reason and trim to maintain max_tags limit
            top_tags = [control_tag] + top_tags[:max_tags - 1]

        if not top_tags:
            return ""

        intent = analysis.get('intent', 'explain-concept')

        # Determine query complexity (Phase 3 enhancement)
        complexity = self._determine_query_complexity(question, analysis, len(top_tags))

        # Build context
        lines = []
        lines.append("🏷️  **ENRICHMENT TAGS** (Use these in your CPGQL query!):")
        lines.append("")

        # Group tags by category
        by_category = {}
        for tag in top_tags:
            if tag.category not in by_category:
                by_category[tag.category] = []
            by_category[tag.category].append(tag)

        # Show tags by category
        for category, tags in list(by_category.items())[:5]:  # Max 5 categories
            category_name = category.replace('_', '-')
            tag_values = [f'"{t.value}"' for t in tags[:3]]  # Max 3 values per category

            lines.append(f"• {category_name}: {', '.join(tag_values)}")

        lines.append("")
        lines.append(f"**Tag Query Patterns** ({complexity} complexity):")

        # Generate specific patterns for top tags
        patterns_shown = 0
        for tag in top_tags[:3]:  # Use top 3 tags for patterns
            category_key = tag.category.replace('_', '-')

            # Map plural forms to singular forms for TAG_QUERY_PATTERNS lookup
            category_mapping = {
                'function-purposes': 'function-purpose',
                'domain-concepts': 'domain-concept',
                'data-structures': 'data-structure',
                'subsystems': 'subsystem-name',
                'features': 'Feature',
                'api-categories': 'api-category',
                'architectural-roles': 'architectural-role',
                'algorithms': 'algorithm-class',
                # Category 1: Parameter & Return
                'param-roles': 'param-role',
                'return-kinds': 'return-kind',
                'return-outcomes': 'return-outcome',
                'validation-required': 'validation-required',
                # Category 2: Variable & Identifier
                'variable-roles': 'variable-role',
                'data-kinds': 'data-kind',
                'security-sensitivities': 'security-sensitivity',
                'lifetimes': 'lifetime',
                'mutabilities': 'mutability',
                'is-locks': 'is-lock',
                'is-pointer-to-structs': 'is-pointer-to-struct',
                # Category 3: Type & Member
                'type-categories': 'type-category',
                'type-domain-entities': 'type-domain-entity',
                'type-concurrency-primitives': 'type-concurrency-primitive',
                'type-ownership-models': 'type-ownership-model',
                'member-roles': 'member-role',
                'member-pointers': 'member-pointer',
                'member-length-fields': 'member-length-field',
                # Category 4: Literal & Constant
                'literal-kinds': 'literal-kind',
                'literal-domains': 'literal-domain',
                'literal-severities': 'literal-severity',
                'is-null-constants': 'is-null-constant',
                'is-bitmasks': 'is-bitmask',
                'literal-constants': 'literal-constant',
                'is-lock-constants': 'is-lock-constant',
                # Category 5: Control Flow & Jump
                'jump-kinds': 'jump-kind',
                'jump-domains': 'jump-domain',
                'jump-scopes': 'jump-scope',
                'modifier-concurrencies': 'modifier-concurrency',
                'modifier-attributes': 'modifier-attribute',
                # Category 6: Namespace & Reference
                'namespace-layers': 'namespace-layer',
                'namespace-domains': 'namespace-domain',
                'method-ref-kinds': 'method-ref-kind',
                'method-ref-usages': 'method-ref-usage',
                # Category 7: Data Flow & Edge
                'data-flow-kinds': 'data-flow-kind',
                'child-roles': 'child-role',
                'call-actions': 'call-action',
                'call-side-effects': 'call-side-effect',
                'call-receiver-roles': 'call-receiver-role',
                'argument-param-names': 'argument-param-name',
                'branch-kinds': 'branch-kind',
                'control-reasons': 'control-reason',
            }

            lookup_key = category_mapping.get(category_key, category_key)

            if lookup_key in TAG_QUERY_PATTERNS:
                templates = TAG_QUERY_PATTERNS[lookup_key]

                # Pick best template for intent and complexity (Phase 3)
                template = self._select_template_for_intent(templates, intent, complexity)
                pattern = template.replace('{value}', tag.value)

                lines.append(f"• {pattern}")
                patterns_shown += 1

                if patterns_shown >= max_patterns:
                    break

        # Add complexity-appropriate fallback patterns if needed
        if patterns_shown < max_patterns and complexity in COMPLEXITY_PATTERNS:
            lines.append("")
            lines.append(f"**General {complexity} patterns:**")

            fallback_patterns = COMPLEXITY_PATTERNS[complexity][:max_patterns - patterns_shown]
            for pattern in fallback_patterns:
                lines.append(f"• {pattern}")

        # Phase 4: Show hybrid patterns from fallback strategies if available
        if hints.get('hybrid_patterns'):
            lines.append("")
            lines.append("**Hybrid Patterns** (name + tag matching):")
            for pattern in hints['hybrid_patterns'][:3]:  # Show top 3
                lines.append(f"• {pattern}")

        # Add hybrid pattern hint if multiple tags available
        if len(top_tags) >= 2:
            lines.append("")
            lines.append("**Combine tags for precise queries:**")
            lines.append("• Use .where() multiple times to combine tag filters")
            lines.append(f'  Example: cpg.method.where(_.tag.nameExact(...)).where(_.tag.nameExact(...)).name.l')

        # Phase 4: Show fallback status if applied
        if hints.get('fallback_applied'):
            lines.append("")
            improvement = hints.get('coverage_improvement', 0.0)
            lines.append(f"📈 Fallback strategies applied (+{improvement:.3f} coverage boost)")

        return '\n'.join(lines)

    def _determine_query_complexity(self, question: str, analysis: Dict, num_tags: int) -> str:
        """
        Determine appropriate query complexity level based on question characteristics.

        Returns: 'simple', 'moderate', or 'complex'
        """
        intent = analysis.get('intent', 'explain-concept')
        keywords = analysis.get('keywords', [])

        # Simple queries: single keyword, find-function intent
        if intent == 'find-function' and len(keywords) <= 2 and num_tags <= 2:
            return 'simple'

        # Complex queries: multiple tags, trace-flow, security-check
        if intent in ['trace-flow', 'security-check', 'find-bug']:
            return 'complex'

        # Complex queries: many keywords or tags
        if len(keywords) >= 4 or num_tags >= 4:
            return 'complex'

        # Long questions tend to be more complex
        if len(question) > 100:
            return 'moderate'

        # Default: moderate complexity
        return 'moderate'

    def _select_template_for_intent(self, templates: List[str], intent: str, complexity: str = 'moderate') -> str:
        """
        Select most appropriate template for given intent and complexity.

        Args:
            templates: Available template patterns
            intent: Query intent (find-function, trace-flow, etc.)
            complexity: Query complexity level (simple, moderate, complex)

        Returns:
            Selected template string
        """
        # First, filter by complexity if we have enough templates
        complexity_filtered = []

        if complexity == 'simple':
            # Simple queries: prefer single-filter patterns
            complexity_filtered = [t for t in templates if t.count('.where(') <= 1 and 'callIn' not in t]
        elif complexity == 'complex':
            # Complex queries: prefer multi-filter or traversal patterns
            complexity_filtered = [t for t in templates if t.count('.where(') >= 2 or 'callIn' in t or 'callOut' in t]

        # If complexity filtering yielded results, use those; otherwise use all
        search_pool = complexity_filtered if complexity_filtered else templates

        # Intent-based template selection heuristics
        if intent == 'find-function':
            # Prefer patterns that return method names
            for t in search_pool:
                if '.method.' in t and '.name.l' in t and 'callIn' not in t:
                    return t

        elif intent == 'trace-flow':
            # Prefer patterns with callIn/callOut
            for t in search_pool:
                if 'callIn' in t or 'callOut' in t:
                    return t

        elif intent == 'security-check':
            # Prefer patterns with security context
            for t in search_pool:
                if 'security' in t or 'risk' in t:
                    return t

        elif intent == 'explain-concept':
            # Prefer patterns that show relationships
            for t in search_pool:
                if 'file' in t or 'callIn' in t:
                    return t

        elif intent == 'find-bug':
            # Prefer patterns with quality metrics
            for t in search_pool:
                if 'test-coverage' in t or 'cyclomatic-complexity' in t:
                    return t

        elif intent == 'api-usage':
            # Prefer patterns with API tags
            for t in search_pool:
                if 'api-public' in t or 'api-category' in t:
                    return t

        # Fallback: return first from search pool or first from templates
        return search_pool[0] if search_pool else templates[0]

    def get_tag_usage_guidance(self, intent: str) -> str:
        """Get intent-specific guidance for using tags."""
        guidance = {
            'find-function': (
                "Focus on function-purpose and subsystem-name tags. "
                "Use .where(_.tag.nameExact(...)) to filter by semantic purpose."
            ),
            'explain-concept': (
                "Use domain-concept and function-purpose tags. "
                "Combine tags with .callIn to show how concept is used."
            ),
            'trace-flow': (
                "Use function-purpose and architectural-role tags. "
                "Chain .callIn and .callOut to trace execution paths."
            ),
            'security-check': (
                "Prioritize security-risk tags. "
                "Filter by risk level: .where(_.tag.nameExact('security-risk').valueExact('high'))"
            ),
            'find-bug': (
                "Use test-coverage and cyclomatic-complexity tags. "
                "Find untested complex code: .where(_.tag.nameExact('test-coverage').valueExact('untested'))"
            ),
            'analyze-component': (
                "Use subsystem-name and Feature tags. "
                "Find component boundaries with .file.where(_.tag.nameExact('Feature'))"
            ),
            'api-usage': (
                "Use api-category and api-public tags. "
                "Find public APIs: .where(_.tag.nameExact('api-public').valueExact('true'))"
            ),
        }

        return guidance.get(intent, "Use enrichment tags with .where(_.tag.nameExact(...).valueExact(...)) to filter results.")

    def build_documentation_context(
        self,
        question: str,
        analysis: Dict,
        top_k: int = 3
    ) -> str:
        """
        Build documentation context from code comments.

        Args:
            question: User question
            analysis: Analysis from AnalyzerAgent
            top_k: Number of documentation entries to retrieve

        Returns:
            Formatted documentation context string
        """
        if not self.enable_documentation or not self.doc_retriever:
            return ""

        try:
            # Retrieve relevant documentation
            result = self.doc_retriever.retrieve_relevant_documentation(
                question=question,
                analysis=analysis,
                top_k=top_k
            )

            # Check if we have relevant documentation
            # Lowered threshold from 0.25 to 0.10 to allow more documentation context
            if not result['documentation'] or result['stats']['avg_relevance'] < 0.10:
                return ""

            # Use the pre-formatted summary
            return result['summary']

        except Exception as e:
            self.logger.warning(f"Error retrieving documentation: {e}")
            return ""

    def build_cfg_context(
        self,
        question: str,
        analysis: Dict,
        top_k: int = 3
    ) -> str:
        """
        Build CFG pattern context for execution flow understanding.

        Args:
            question: User question
            analysis: Analysis from AnalyzerAgent
            top_k: Number of CFG patterns to retrieve

        Returns:
            Formatted CFG pattern context string
        """
        if not self.enable_cfg or not self.cfg_retriever:
            return ""

        try:
            # Retrieve relevant CFG patterns
            result = self.cfg_retriever.retrieve_relevant_patterns(
                question=question,
                analysis=analysis,
                top_k=top_k
            )

            # Check if we have relevant patterns
            # Lowered threshold from 0.25 to 0.10 to allow more CFG patterns
            if not result['patterns'] or result['stats']['avg_relevance'] < 0.10:
                return ""

            # Use the pre-formatted summary
            return result['summary']

        except Exception as e:
            self.logger.warning(f"Error retrieving CFG patterns: {e}")
            return ""

    def build_ddg_context(
        self,
        question: str,
        analysis: Dict,
        top_k: int = 3
    ) -> str:
        """
        Build DDG pattern context for data flow understanding.

        Args:
            question: User question
            analysis: Analysis from AnalyzerAgent
            top_k: Number of DDG patterns to retrieve

        Returns:
            Formatted DDG pattern context string
        """
        if not self.enable_ddg or not self.ddg_retriever:
            return ""

        try:
            # Retrieve relevant DDG patterns
            result = self.ddg_retriever.retrieve_relevant_patterns(
                question=question,
                analysis=analysis,
                top_k=top_k
            )

            # Check if we have relevant patterns
            # Lowered threshold from 0.25 to 0.10 to allow more DDG patterns
            if not result['patterns'] or result['stats']['avg_relevance'] < 0.10:
                return ""

            # Use the pre-formatted summary
            return result['summary']

        except Exception as e:
            self.logger.warning(f"Error retrieving DDG patterns: {e}")
            return ""

    def build_full_enrichment_prompt(
        self,
        hints: Dict[str, List[str]],
        question: str,
        analysis: Dict,
        max_tags: int = 7,
        max_patterns: int = 5,
        include_documentation: bool = True,
        include_cfg: bool = True,
        include_ddg: bool = True
    ) -> str:
        """
        Build complete enrichment prompt including tags, documentation, CFG patterns, and DDG patterns.

        Args:
            hints: Enrichment hints from EnrichmentAgent
            question: User question
            analysis: AnalyzerAgent output
            max_tags: Maximum number of tags to show
            max_patterns: Maximum number of query patterns to show
            include_documentation: Whether to include code documentation
            include_cfg: Whether to include CFG execution flow patterns
            include_ddg: Whether to include DDG data flow patterns

        Returns:
            Complete formatted enrichment prompt
        """
        sections = []

        # 1. Documentation context (WHAT functions do)
        if include_documentation:
            doc_context = self.build_documentation_context(question, analysis, top_k=3)
            if doc_context:
                sections.append(doc_context)

        # 2. CFG pattern context (HOW functions execute)
        if include_cfg:
            cfg_context = self.build_cfg_context(question, analysis, top_k=3)
            if cfg_context:
                sections.append(cfg_context)

        # 3. DDG pattern context (WHERE data flows) - Phase 3
        if include_ddg:
            ddg_context = self.build_ddg_context(question, analysis, top_k=3)
            if ddg_context:
                sections.append(ddg_context)

        # 4. Enrichment tags context (semantic search)
        tag_context = self.build_enrichment_context(
            hints, question, analysis, max_tags, max_patterns
        )
        if tag_context:
            sections.append(tag_context)

        # 5. Intent-specific guidance
        intent = analysis.get('intent', 'explain-concept')
        guidance = self.get_tag_usage_guidance(intent)
        if guidance:
            sections.append("")
            sections.append(f"**Guidance**: {guidance}")

        return '\n\n'.join(sections)
