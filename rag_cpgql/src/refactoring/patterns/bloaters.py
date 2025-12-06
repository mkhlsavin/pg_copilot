"""
Bloater Patterns - Methods and classes that have grown too large

Patterns for detecting God Class, Long Method, and Long Parameter List smells.
These code smells indicate excessive size and complexity that hinder maintainability.
"""

from typing import Dict
from .._base import (
    RefactoringPattern,
    CodeSmellCategory,
    CodeSmellSeverity,
)


GOD_CLASS_PATTERN = RefactoringPattern(
    id="GOD_CLASS_001",
    name="God Class / Large Class",
    category=CodeSmellCategory.BLOATERS,
    severity=CodeSmellSeverity.HIGH,
    description=(
        "A class that knows too much or does too much. God classes have hundreds "
        "of lines of code, many methods, and high coupling. They violate Single "
        "Responsibility Principle and are difficult to understand and maintain."
    ),
    cpgql_query="""
        -- Find files with excessive method count (potential God classes)
        SELECT DISTINCT
            m.filename,
            COUNT(DISTINCT m.id) AS method_count,
            MAX(m.line_number_end - m.line_number) AS max_method_lines,
            AVG(m.line_number_end - m.line_number) AS avg_method_lines,
            SUM(m.line_number_end - m.line_number) AS total_lines,
            'GOD_CLASS' AS smell_type,
            'HIGH' AS severity
        FROM nodes_method m
        WHERE m.name NOT LIKE 'test_%'
          AND m.line_number_end > 0
        GROUP BY m.filename
        HAVING COUNT(DISTINCT m.id) > 30  -- More than 30 methods
           OR SUM(m.line_number_end - m.line_number) > 1000
        ORDER BY total_lines DESC
        LIMIT 50;
    """,
    symptoms=[
        "File has more than 30 methods",
        "File exceeds 1000 lines of code",
        "Class has many instance variables",
        "Difficult to understand class purpose",
        "Multiple unrelated responsibilities"
    ],
    refactoring_technique=(
        "Extract Class: Break the class into smaller, focused classes\n"
        "Extract Subclass: Create subclasses for specialized behavior\n"
        "Extract Interface: Define clear interfaces for responsibilities\n"
        "Move Method: Relocate methods to more appropriate classes"
    ),
    example_before="""
        // BEFORE: God class doing everything
        typedef struct ConnectionManager {
            // Connection state
            int socket_fd;
            char *host;
            int port;

            // Authentication
            char *username;
            char *password;

            // Query execution
            char *current_query;
            int query_timeout;

            // Result handling
            void *result_buffer;
            size_t buffer_size;

            // Logging
            FILE *log_file;
            int log_level;

            // Statistics
            int queries_executed;
            long bytes_transferred;
        } ConnectionManager;

        // 50+ methods managing all these concerns...
    """,
    example_after="""
        // AFTER: Separate concerns into focused classes
        typedef struct Connection {
            int socket_fd;
            char *host;
            int port;
        } Connection;

        typedef struct Authenticator {
            char *username;
            char *password;
        } Authenticator;

        typedef struct QueryExecutor {
            Connection *conn;
            char *current_query;
            int query_timeout;
        } QueryExecutor;

        typedef struct ResultHandler {
            void *result_buffer;
            size_t buffer_size;
        } ResultHandler;

        typedef struct ConnectionStats {
            int queries_executed;
            long bytes_transferred;
        } ConnectionStats;
    """,
    effort_estimate=8.0
)


LONG_METHOD_PATTERN = RefactoringPattern(
    id="LONG_METHOD_001",
    name="Long Method",
    category=CodeSmellCategory.BLOATERS,
    severity=CodeSmellSeverity.MEDIUM,
    description=(
        "A method that has grown too long, typically more than 50-100 lines. "
        "Long methods are difficult to understand, test, and maintain. They often "
        "do multiple things and violate the Single Responsibility Principle."
    ),
    cpgql_query="""
        -- Find excessively long methods
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.full_name,
            m.filename,
            m.line_number,
            (m.line_number_end - m.line_number) AS line_count,
            'LONG_METHOD' AS smell_type,
            CASE
                WHEN (m.line_number_end - m.line_number) > 200 THEN 'CRITICAL'
                WHEN (m.line_number_end - m.line_number) > 100 THEN 'HIGH'
                ELSE 'MEDIUM'
            END AS severity
        FROM nodes_method m
        WHERE (m.line_number_end - m.line_number) > 50  -- More than 50 lines
        AND m.line_number_end > 0
        AND m.name NOT LIKE 'test_%'
        ORDER BY line_count DESC
        LIMIT 100;
    """,
    symptoms=[
        "Method exceeds 50-100 lines",
        "Difficult to understand method purpose",
        "Multiple levels of nested control structures",
        "Long scrolling to see entire method",
        "Many local variables"
    ],
    refactoring_technique=(
        "Extract Method: Break into smaller, focused methods\n"
        "Replace Temp with Query: Eliminate temporary variables\n"
        "Decompose Conditional: Extract complex conditions\n"
        "Introduce Parameter Object: Group related parameters"
    ),
    example_before="""
        // BEFORE: 150-line method doing everything
        static void process_transaction(Transaction *txn) {
            // 20 lines: validate transaction
            if (txn == NULL) return;
            if (txn->amount <= 0) return;
            // ... more validation

            // 30 lines: acquire locks
            lock_table(txn->table_id);
            // ... complex locking logic

            // 40 lines: execute transaction
            begin_transaction();
            // ... transaction execution

            // 30 lines: handle errors
            if (error) {
                rollback();
                // ... error handling
            }

            // 30 lines: cleanup
            release_locks();
            free_resources();
            // ... cleanup logic
        }
    """,
    example_after="""
        // AFTER: Broken into focused methods
        static void process_transaction(Transaction *txn) {
            if (!validate_transaction(txn))
                return;

            acquire_transaction_locks(txn);

            if (execute_transaction_steps(txn)) {
                commit_transaction(txn);
            } else {
                handle_transaction_error(txn);
            }

            cleanup_transaction(txn);
        }

        static bool validate_transaction(Transaction *txn) { /* 10 lines */ }
        static void acquire_transaction_locks(Transaction *txn) { /* 15 lines */ }
        static bool execute_transaction_steps(Transaction *txn) { /* 20 lines */ }
        static void handle_transaction_error(Transaction *txn) { /* 15 lines */ }
        static void cleanup_transaction(Transaction *txn) { /* 10 lines */ }
    """,
    effort_estimate=2.0
)


LONG_PARAMETER_LIST_PATTERN = RefactoringPattern(
    id="LONG_PARAM_LIST_001",
    name="Long Parameter List",
    category=CodeSmellCategory.BLOATERS,
    severity=CodeSmellSeverity.MEDIUM,
    description=(
        "A method with too many parameters (typically more than 3-4). Long parameter "
        "lists are hard to understand, difficult to use correctly, and make the code "
        "brittle when requirements change."
    ),
    cpgql_query="""
        -- Find methods with many parameters (estimated from signature)
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.full_name,
            m.filename,
            m.line_number,
            LENGTH(m.signature) - LENGTH(REPLACE(m.signature, ',', '')) + 1 AS param_estimate,
            'LONG_PARAMETER_LIST' AS smell_type,
            'MEDIUM' AS severity
        FROM nodes_method m
        WHERE LENGTH(m.signature) - LENGTH(REPLACE(m.signature, ',', '')) >= 4
        AND m.name NOT LIKE 'test_%'
        AND m.signature IS NOT NULL
        ORDER BY param_estimate DESC
        LIMIT 50;
    """,
    symptoms=[
        "Method has more than 4 parameters",
        "Difficult to remember parameter order",
        "Many null or default arguments",
        "Parameters often changed together"
    ],
    refactoring_technique=(
        "Introduce Parameter Object: Group related parameters into a struct\n"
        "Preserve Whole Object: Pass entire object instead of parts\n"
        "Replace Parameter with Method Call: Calculate values inside method\n"
        "Remove Flag Arguments: Create separate methods for different behaviors"
    ),
    example_before="""
        // BEFORE: Too many parameters
        static void create_index(
            Relation rel,
            char *index_name,
            Oid access_method,
            int n_key_columns,
            AttrNumber *key_columns,
            Oid *key_opclasses,
            bool unique,
            bool primary,
            bool isconstraint,
            bool deferrable,
            bool initdeferred
        ) {
            // ...
        }
    """,
    example_after="""
        // AFTER: Use parameter object
        typedef struct IndexParams {
            Relation rel;
            char *index_name;
            Oid access_method;
            int n_key_columns;
            AttrNumber *key_columns;
            Oid *key_opclasses;
            IndexOptions options;  // Grouped boolean flags
        } IndexParams;

        typedef struct IndexOptions {
            bool unique;
            bool primary;
            bool isconstraint;
            bool deferrable;
            bool initdeferred;
        } IndexOptions;

        static void create_index(IndexParams *params) {
            // Much cleaner!
        }
    """,
    effort_estimate=1.5
)


# Registry of bloater patterns
BLOATER_PATTERNS: Dict[str, RefactoringPattern] = {
    "GOD_CLASS": GOD_CLASS_PATTERN,
    "LONG_METHOD": LONG_METHOD_PATTERN,
    "LONG_PARAMETER_LIST": LONG_PARAMETER_LIST_PATTERN,
}
