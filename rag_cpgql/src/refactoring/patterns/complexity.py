"""
Complexity Patterns - Code that is difficult to understand

Patterns for detecting High Cyclomatic Complexity and Deep Nesting smells.
These patterns indicate code that is hard to test, maintain, and prone to bugs.
"""

from typing import Dict
from .._base import (
    RefactoringPattern,
    CodeSmellCategory,
    CodeSmellSeverity,
)


HIGH_COMPLEXITY_PATTERN = RefactoringPattern(
    id="HIGH_COMPLEXITY_001",
    name="High Cyclomatic Complexity",
    category=CodeSmellCategory.COMPLEXITY,
    severity=CodeSmellSeverity.HIGH,
    description=(
        "Methods with high cyclomatic complexity (typically >10) have many decision "
        "points and code paths. They are difficult to understand, test, and maintain, "
        "and are more likely to contain bugs."
    ),
    cpgql_query="""
        -- Find methods with high estimated complexity (via control structure count)
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.full_name,
            m.filename,
            m.line_number,
            (m.line_number_end - m.line_number) AS line_count,
            'HIGH_COMPLEXITY' AS smell_type,
            CASE
                WHEN (m.line_number_end - m.line_number) > 150 THEN 'CRITICAL'
                WHEN (m.line_number_end - m.line_number) > 100 THEN 'HIGH'
                ELSE 'MEDIUM'
            END AS severity
        FROM nodes_method m
        WHERE (m.line_number_end - m.line_number) > 50
        AND m.line_number_end > 0
        AND m.name NOT LIKE 'test_%'
        ORDER BY line_count DESC
        LIMIT 50;
    """,
    symptoms=[
        "Cyclomatic complexity > 10",
        "Many nested if/else statements",
        "Long switch/case statements",
        "Difficult to write unit tests",
        "High bug density"
    ],
    refactoring_technique=(
        "Extract Method: Break complex logic into smaller methods\n"
        "Decompose Conditional: Simplify complex conditions\n"
        "Replace Nested Conditional with Guard Clauses\n"
        "Replace Type Code with Polymorphism\n"
        "Simplify Boolean Expressions"
    ),
    example_before="""
        // BEFORE: Complexity of 25+
        static int process_node(Node *node, Context *ctx) {
            if (node == NULL) {
                if (ctx->strict_mode) {
                    if (ctx->error_count > MAX_ERRORS) {
                        return ERROR_TOO_MANY;
                    } else {
                        log_warning("NULL node");
                        return ERROR_NULL_NODE;
                    }
                } else {
                    return SUCCESS;
                }
            } else {
                switch (node->type) {
                    case T_Var:
                        if (node->varno < 0) {
                            return ERROR_INVALID_VAR;
                        }
                        // ... 10 more cases
                }
            }
        }
    """,
    example_after="""
        // AFTER: Complexity reduced to ~5
        static int process_node(Node *node, Context *ctx) {
            // Guard clauses reduce nesting
            if (node == NULL)
                return handle_null_node(ctx);

            return process_node_by_type(node, ctx);
        }

        static int handle_null_node(Context *ctx) {
            if (!ctx->strict_mode)
                return SUCCESS;

            if (ctx->error_count > MAX_ERRORS)
                return ERROR_TOO_MANY;

            log_warning("NULL node");
            return ERROR_NULL_NODE;
        }

        static int process_node_by_type(Node *node, Context *ctx) {
            switch (node->type) {
                case T_Var:
                    return process_var_node((Var *)node, ctx);
                case T_Const:
                    return process_const_node((Const *)node, ctx);
                // Each case delegates to focused function
            }
        }
    """,
    effort_estimate=3.0
)


DEEP_NESTING_PATTERN = RefactoringPattern(
    id="DEEP_NESTING_001",
    name="Deep Nesting",
    category=CodeSmellCategory.COMPLEXITY,
    severity=CodeSmellSeverity.MEDIUM,
    description=(
        "Code with excessive nesting levels (typically >3-4 levels) is hard to "
        "follow and understand. Deep nesting often indicates complex logic that "
        "should be broken down or simplified."
    ),
    cpgql_query="""
        -- Find methods with deep nesting (heuristic based on line count and brace patterns)
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.full_name,
            m.filename,
            m.line_number,
            (m.line_number_end - m.line_number) AS line_count,
            'DEEP_NESTING' AS smell_type,
            'MEDIUM' AS severity
        FROM nodes_method m
        WHERE (m.line_number_end - m.line_number) > 40
        AND m.line_number_end > 0
        AND m.code LIKE '%{%{%{%{%'  -- At least 4 levels of braces
        AND m.name NOT LIKE 'test_%'
        ORDER BY line_count DESC
        LIMIT 50;
    """,
    symptoms=[
        "More than 3-4 nesting levels",
        "Rightward drift of code",
        "Difficulty tracking scope",
        "Complex conditional logic"
    ],
    refactoring_technique=(
        "Replace Nested Conditional with Guard Clauses\n"
        "Extract Method: Move nested logic to separate method\n"
        "Consolidate Conditional Expression\n"
        "Invert Conditions: Use early returns"
    ),
    example_before="""
        // BEFORE: 5 levels of nesting
        static void validate_and_process(Data *data) {
            if (data != NULL) {
                if (data->is_valid) {
                    if (data->type == TYPE_A) {
                        if (data->status == STATUS_READY) {
                            if (can_process(data)) {
                                process_data(data);
                            }
                        }
                    }
                }
            }
        }
    """,
    example_after="""
        // AFTER: Flattened with guard clauses
        static void validate_and_process(Data *data) {
            // Guard clauses eliminate nesting
            if (data == NULL)
                return;
            if (!data->is_valid)
                return;
            if (data->type != TYPE_A)
                return;
            if (data->status != STATUS_READY)
                return;
            if (!can_process(data))
                return;

            process_data(data);
        }
    """,
    effort_estimate=1.0
)


# Registry of complexity patterns
COMPLEXITY_PATTERNS: Dict[str, RefactoringPattern] = {
    "HIGH_COMPLEXITY": HIGH_COMPLEXITY_PATTERN,
    "DEEP_NESTING": DEEP_NESTING_PATTERN,
}
