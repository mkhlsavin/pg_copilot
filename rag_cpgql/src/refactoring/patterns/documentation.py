"""
Documentation Patterns - Code documentation and comment smells

Pattern for detecting TODO/FIXME comments indicating incomplete work.
"""

from typing import Dict
from .._base import (
    RefactoringPattern,
    CodeSmellCategory,
    CodeSmellSeverity,
)


TODO_FIXME_PATTERN = RefactoringPattern(
    id="TODO_FIXME_001",
    name="TODO/FIXME Comments",
    category=CodeSmellCategory.DOCUMENTATION,
    severity=CodeSmellSeverity.LOW,
    description=(
        "TODO and FIXME comments indicate incomplete work or known issues. While "
        "they're useful for tracking work, accumulating TODOs indicate technical "
        "debt and deferred decisions that should be addressed."
    ),
    cpgql_query="""
        -- Find methods with TODO/FIXME comments
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.full_name,
            m.filename,
            m.line_number,
            'TODO_FIXME' AS smell_type,
            'LOW' AS severity
        FROM nodes_method m
        WHERE (m.code LIKE '%TODO%'
           OR m.code LIKE '%FIXME%'
           OR m.code LIKE '%HACK%'
           OR m.code LIKE '%XXX%')
        AND m.name NOT LIKE 'test_%'
        LIMIT 100;
    """,
    symptoms=[
        "TODO comments older than 6 months",
        "FIXME without issue tracker references",
        "Vague TODOs without actionable steps",
        "Many TODOs in same module"
    ],
    refactoring_technique=(
        "Create Issues: Convert TODOs to tracked issues\n"
        "Fix Immediately: Address simple TODOs right away\n"
        "Remove Stale TODOs: Delete outdated or irrelevant comments\n"
        "Add Context: Include issue numbers and deadlines"
    ),
    example_before="""
        // BEFORE: Accumulating TODOs

        static void execute_query(char *sql) {
            // TODO: Add parameter validation
            // FIXME: This doesn't handle Unicode properly
            // XXX: Security issue - no SQL injection protection
            // HACK: Temporary workaround for bug #1234

            exec_simple_query(sql);
        }
    """,
    example_after="""
        // AFTER: TODOs converted to tracked work

        /**
         * Execute SQL query with proper validation.
         *
         * Known issues:
         * - Issue #5678: Add Unicode support (Q2 2025)
         * - Issue #5679: Implement SQL injection protection (Priority: HIGH)
         */
        static void execute_query(const char *sql) {
            if (!validate_sql(sql)) {
                elog(ERROR, "Invalid SQL query");
            }

            char *sanitized = sanitize_sql(sql);  // Addresses #5679
            exec_simple_query(sanitized);
            pfree(sanitized);
        }
    """,
    effort_estimate=1.0
)


# Registry of documentation patterns
DOCUMENTATION_PATTERNS: Dict[str, RefactoringPattern] = {
    "TODO_FIXME": TODO_FIXME_PATTERN,
}
