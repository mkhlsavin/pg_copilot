"""
Duplicate Patterns - Repeated code that violates DRY principle

Pattern for detecting duplicate or similar code blocks.
"""

from typing import Dict
from .._base import (
    RefactoringPattern,
    CodeSmellCategory,
    CodeSmellSeverity,
)


DUPLICATE_CODE_PATTERN = RefactoringPattern(
    id="DUPLICATE_CODE_001",
    name="Duplicate Code",
    category=CodeSmellCategory.DISPENSABLES,
    severity=CodeSmellSeverity.MEDIUM,
    description=(
        "Similar or identical code appearing in multiple places. Duplicate code "
        "increases maintenance burden, makes bug fixes harder, and violates DRY "
        "(Don't Repeat Yourself) principle."
    ),
    cpgql_query="""
        -- Find methods with similar names (potential duplicates)
        -- Note: True clone detection requires more sophisticated analysis
        SELECT DISTINCT
            m1.id AS method1_id,
            m1.name AS method1_name,
            m1.filename AS file1,
            m2.id AS method2_id,
            m2.name AS method2_name,
            m2.filename AS file2,
            'DUPLICATE_CODE' AS smell_type,
            'MEDIUM' AS severity
        FROM nodes_method m1
        JOIN nodes_method m2 ON m1.name LIKE m2.name || '%'
                        OR m2.name LIKE m1.name || '%'
        WHERE m1.id < m2.id
        AND m1.filename != m2.filename
        AND (m1.line_number_end - m1.line_number) > 10
        AND m1.line_number_end > 0
        AND m1.name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    symptoms=[
        "Copy-pasted code with minor variations",
        "Similar methods in different files",
        "Repeated logic patterns",
        "Bug fixes needed in multiple places"
    ],
    refactoring_technique=(
        "Extract Method: Pull duplicate code into shared function\n"
        "Pull Up Method: Move to common base\n"
        "Form Template Method: Create template with variations\n"
        "Replace Algorithm: Use a more general algorithm"
    ),
    example_before="""
        // BEFORE: Duplicated validation in multiple files

        // file1.c
        static bool validate_user(User *user) {
            if (user == NULL) return false;
            if (user->name == NULL) return false;
            if (strlen(user->name) == 0) return false;
            if (strlen(user->name) > MAX_NAME) return false;
            return true;
        }

        // file2.c
        static bool validate_admin(Admin *admin) {
            if (admin == NULL) return false;
            if (admin->name == NULL) return false;
            if (strlen(admin->name) == 0) return false;
            if (strlen(admin->name) > MAX_NAME) return false;
            return true;
        }
    """,
    example_after="""
        // AFTER: Extracted common validation

        // validation.c
        bool validate_name(const char *name) {
            if (name == NULL) return false;
            size_t len = strlen(name);
            return len > 0 && len <= MAX_NAME;
        }

        // file1.c
        static bool validate_user(User *user) {
            return user != NULL && validate_name(user->name);
        }

        // file2.c
        static bool validate_admin(Admin *admin) {
            return admin != NULL && validate_name(admin->name);
        }
    """,
    effort_estimate=2.0
)


# Registry of duplicate patterns
DUPLICATE_PATTERNS: Dict[str, RefactoringPattern] = {
    "DUPLICATE_CODE": DUPLICATE_CODE_PATTERN,
}
