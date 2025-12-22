"""
Dead Code Patterns - Unnecessary code that should be removed

Comprehensive patterns for detecting various forms of dead code:
- Unused functions and variables
- Deprecated markers
- Disabled code blocks
- Empty stubs
- Unreachable code
- Orphan components
- Dead callbacks
- Test-only functions in production

Sprint 1 + Sprint 2 dead code patterns for Scenario 5.
"""

from typing import Dict
from .._base import (
    RefactoringPattern,
    CodeSmellCategory,
    CodeSmellSeverity,
)


DEAD_CODE_PATTERN = RefactoringPattern(
    id="DEAD_CODE_001",
    name="Dead Code / Unused Functions",
    category=CodeSmellCategory.DISPENSABLES,
    severity=CodeSmellSeverity.MEDIUM,
    description=(
        "Code that is never executed or functions that are never called. Dead code "
        "adds unnecessary complexity, confuses developers, and increases maintenance "
        "burden without providing any value."
    ),
    cpgql_query="""
        -- Find methods that are never called (potential dead code)
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.full_name,
            m.filename,
            m.line_number,
            (m.line_number_end - m.line_number) AS line_count,
            'DEAD_CODE' AS smell_type,
            'MEDIUM' AS severity
        FROM nodes_method m
        LEFT JOIN call_containment c ON c.callee_name = m.name
        WHERE c.callee_name IS NULL  -- Never called
        AND m.name NOT LIKE 'test_%'
        AND m.name NOT LIKE 'main'
        AND m.name NOT LIKE '%_init'
        AND (m.line_number_end - m.line_number) > 5  -- Ignore trivial functions
        AND m.line_number_end > 0
        LIMIT 100;
    """,
    symptoms=[
        "Function never called anywhere in codebase",
        "Commented-out code blocks",
        "Unreachable code after returns",
        "Unused variables or parameters"
    ],
    refactoring_technique=(
        "Delete Unused Code: Remove functions that are never called\n"
        "Remove Dead Branches: Eliminate unreachable code paths\n"
        "Remove Unused Parameters: Clean up function signatures\n"
        "Version Control: Rely on git history instead of commenting out code"
    ),
    example_before="""
        // BEFORE: Dead code cluttering the file

        /* This function is no longer used after refactoring
        static int old_calculate_cost(Item *item) {
            return item->price * item->quantity;
        }
        */

        static int unused_helper(void) {
            // This was meant for a feature that was never implemented
            return 42;
        }

        static void process_item(Item *item) {
            if (item == NULL)
                return;

            // ... processing logic

            return;

            // Unreachable code below
            log_debug("This never executes");
            cleanup_resources();
        }
    """,
    example_after="""
        // AFTER: Clean code without dead weight

        static void process_item(Item *item) {
            if (item == NULL)
                return;

            // ... processing logic
        }
    """,
    effort_estimate=0.5
)


DEPRECATED_MARKER_PATTERN = RefactoringPattern(
    id="DEAD_CODE_002",
    name="Deprecated Marker Detection",
    category=CodeSmellCategory.DISPENSABLES,
    severity=CodeSmellSeverity.MEDIUM,
    description=(
        "Code marked with deprecation indicators (pg_deprecated, DEPRECATED comments) "
        "that should be removed or migrated to modern alternatives."
    ),
    cpgql_query="""
        -- Find methods/code with deprecation markers
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.full_name,
            m.filename,
            m.line_number,
            'DEPRECATED_MARKER' AS smell_type,
            'MEDIUM' AS severity
        FROM nodes_method m
        WHERE (LOWER(m.code) LIKE '%deprecated%'
            OR LOWER(m.code) LIKE '%pg_deprecated%'
            OR LOWER(m.code) LIKE '%obsolete%'
            OR LOWER(m.code) LIKE '%__attribute__((deprecated%')
        AND m.name NOT LIKE 'test_%'
        ORDER BY m.filename, m.line_number
        LIMIT 100;
    """,
    symptoms=[
        "DEPRECATED comment or annotation",
        "__attribute__((deprecated)) usage",
        "pg_deprecated macro usage",
        "Functions marked for removal"
    ],
    refactoring_technique=(
        "Remove Deprecated Code: Delete if no longer needed\n"
        "Migrate to New API: Update callers to use replacement\n"
        "Add Migration Path: Provide deprecation warnings\n"
        "Document Timeline: Set removal deadline"
    ),
    example_before="""
        // BEFORE: Deprecated function still in codebase
        /* DEPRECATED: Use new_format_string() instead */
        static char *old_format_string(const char *fmt) {
            // Old implementation
            return pstrdup(fmt);
        }
    """,
    example_after="""
        // AFTER: Replaced with new implementation
        static char *format_string(const char *fmt) {
            // Modern implementation with proper escaping
            return format_with_escaping(fmt);
        }
    """,
    effort_estimate=1.0
)


DISABLED_CODE_BLOCK_PATTERN = RefactoringPattern(
    id="DEAD_CODE_003",
    name="Disabled Code Block (#if 0)",
    category=CodeSmellCategory.DISPENSABLES,
    severity=CodeSmellSeverity.MEDIUM,
    description=(
        "Code blocks disabled via preprocessor (#if 0, #ifdef NOTUSED) that should "
        "be removed or properly conditionalized."
    ),
    cpgql_query="""
        -- Find methods containing disabled code blocks
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.full_name,
            m.filename,
            m.line_number,
            'DISABLED_CODE_BLOCK' AS smell_type,
            'MEDIUM' AS severity
        FROM nodes_method m
        WHERE (m.code LIKE '%#if 0%'
            OR m.code LIKE '%#ifdef NOTUSED%'
            OR m.code LIKE '%#ifdef NOT_USED%'
            OR m.code LIKE '%#if defined(UNUSED)%'
            OR m.code LIKE '%#ifdef DEBUG_ONLY%')
        AND m.name NOT LIKE 'test_%'
        ORDER BY m.filename, m.line_number
        LIMIT 100;
    """,
    symptoms=[
        "#if 0 / #endif blocks",
        "#ifdef NOTUSED directives",
        "Permanently disabled code",
        "Debug-only code in production"
    ],
    refactoring_technique=(
        "Delete Disabled Code: Remove #if 0 blocks entirely\n"
        "Use Version Control: Rely on git for code history\n"
        "Proper Feature Flags: Use runtime configuration\n"
        "Conditional Compilation: Use meaningful macros"
    ),
    example_before="""
        // BEFORE: Disabled code cluttering source
        static void process_data(Data *d) {
            #if 0
            // Old algorithm - keeping for reference
            for (int i = 0; i < d->count; i++) {
                process_item(&d->items[i]);
            }
            #endif

            // New algorithm
            process_batch(d->items, d->count);
        }
    """,
    example_after="""
        // AFTER: Clean code, history in git
        static void process_data(Data *d) {
            process_batch(d->items, d->count);
        }
    """,
    effort_estimate=0.5
)


UNUSED_VARIABLE_PATTERN = RefactoringPattern(
    id="DEAD_CODE_004",
    name="Unused Variable Declaration",
    category=CodeSmellCategory.DISPENSABLES,
    severity=CodeSmellSeverity.LOW,
    description=(
        "Variables declared but never read or used in the code. Unused variables "
        "clutter the codebase, may indicate incomplete implementations, and can "
        "confuse maintainers."
    ),
    cpgql_query="""
        -- Find local variables with no read references
        WITH declared_locals AS (
            SELECT DISTINCT
                nl.id,
                nl.name,
                COALESCE(nm.filename, 'unknown') AS filename,
                nl.line_number,
                COALESCE(nm.full_name, 'unknown') AS method_full_name
            FROM nodes_local nl
            LEFT JOIN edges_ast ea ON nl.id = ea.dst
            LEFT JOIN nodes_method nm ON ea.src = nm.id
            WHERE nl.name NOT LIKE 'test_%'
              AND nl.name NOT LIKE '__%'
              AND nl.name NOT IN ('_', 'unused', 'dummy')
        ),
        referenced_vars AS (
            SELECT DISTINCT ni.name
            FROM nodes_identifier ni
            WHERE ni.name IS NOT NULL
        )
        SELECT DISTINCT
            dl.id,
            dl.name AS variable_name,
            dl.filename,
            dl.line_number,
            dl.method_full_name,
            'UNUSED_VARIABLE' AS smell_type,
            'LOW' AS severity
        FROM declared_locals dl
        LEFT JOIN referenced_vars rv ON dl.name = rv.name
        WHERE rv.name IS NULL
        ORDER BY dl.filename, dl.line_number
        LIMIT 100;
    """,
    symptoms=[
        "Variable declared but never read",
        "Assignment to unused variable",
        "Parameter never used in function body",
        "Loop counter declared but not used"
    ],
    refactoring_technique=(
        "Remove Unused Variable: Simply delete the declaration\n"
        "Use Variable: Add logic that uses the value\n"
        "Mark Intentional: Use __attribute__((unused)) or (void)var"
    ),
    example_before="""
        // BEFORE: Unused variables
        void process_data(int *data, int count) {
            int unused_counter = 0;  // Never used
            int temp;                // Declared but unused

            for (int i = 0; i < count; i++) {
                process_item(data[i]);
            }
        }
    """,
    example_after="""
        // AFTER: Cleaned up
        void process_data(int *data, int count) {
            for (int i = 0; i < count; i++) {
                process_item(data[i]);
            }
        }
    """,
    effort_estimate=0.25
)


EMPTY_STUB_PATTERN = RefactoringPattern(
    id="DEAD_CODE_005",
    name="Empty Function Stub",
    category=CodeSmellCategory.DISPENSABLES,
    severity=CodeSmellSeverity.LOW,
    description=(
        "Functions with empty bodies or that only return without doing anything. "
        "These may be unimplemented stubs or dead code that should be removed."
    ),
    cpgql_query="""
        -- Find empty or trivial functions
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.full_name,
            m.filename,
            m.line_number,
            (m.line_number_end - m.line_number) AS line_count,
            'EMPTY_STUB' AS smell_type,
            'LOW' AS severity
        FROM nodes_method m
        WHERE (m.line_number_end - m.line_number) <= 3
        AND m.line_number_end > 0
        AND (m.code LIKE '%{}%'
            OR m.code LIKE '%{ }%'
            OR m.code LIKE '%{ return; }%'
            OR m.code LIKE '%{ return NULL; }%')
        AND m.name NOT LIKE 'test_%'
        AND m.name NOT LIKE '%_noop%'
        ORDER BY m.filename, m.line_number
        LIMIT 100;
    """,
    symptoms=[
        "Functions with empty body {}",
        "Functions that only return",
        "Placeholder stubs",
        "Unimplemented interface methods"
    ],
    refactoring_technique=(
        "Remove Empty Stubs: Delete if unused\n"
        "Implement Properly: Add real implementation\n"
        "Document Intent: If intentional, add comments\n"
        "Use Assert/Error: Throw if should not be called"
    ),
    example_before="""
        // BEFORE: Empty stubs
        static void on_startup(void) {
            // TODO: implement startup hook
        }

        static void cleanup(void) {
            return;
        }
    """,
    example_after="""
        // AFTER: Either implemented or removed
        static void on_startup(void) {
            initialize_subsystems();
            register_cleanup_handlers();
        }

        // cleanup() removed - was never needed
    """,
    effort_estimate=0.25
)


ERROR_ONLY_FUNCTION_PATTERN = RefactoringPattern(
    id="DEAD_CODE_006",
    name="Error-Only Function",
    category=CodeSmellCategory.DISPENSABLES,
    severity=CodeSmellSeverity.LOW,
    description=(
        "Functions that only report errors without doing real work. These may indicate "
        "unimplemented features or dead code paths."
    ),
    cpgql_query="""
        -- Find functions that only call error reporting
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.full_name,
            m.filename,
            m.line_number,
            'ERROR_ONLY' AS smell_type,
            'LOW' AS severity
        FROM nodes_method m
        WHERE (m.line_number_end - m.line_number) <= 5
        AND m.line_number_end > 0
        AND (m.code LIKE '%ereport(ERROR%'
            OR m.code LIKE '%elog(ERROR%'
            OR m.code LIKE '%abort()%'
            OR m.code LIKE '%Assert(false)%')
        AND m.code NOT LIKE '%if%'  -- No conditional logic
        AND m.name NOT LIKE 'test_%'
        ORDER BY m.filename, m.line_number
        LIMIT 100;
    """,
    symptoms=[
        "Functions that only call ereport/elog",
        "Functions that always abort",
        "Panic-only handlers",
        "Unimplemented required interfaces"
    ],
    refactoring_technique=(
        "Implement Function: Add real logic\n"
        "Remove If Dead: Delete unreachable error handlers\n"
        "Add Assertions: Document why error is expected\n"
        "Create Issue: Track unimplemented features"
    ),
    example_before="""
        // BEFORE: Function only reports error
        static void handle_special_case(Node *node) {
            ereport(ERROR, (errcode(ERRCODE_FEATURE_NOT_SUPPORTED),
                           errmsg("special case not implemented")));
        }
    """,
    example_after="""
        // AFTER: Properly implemented or documented
        static void handle_special_case(Node *node) {
            /* Special case handling for edge conditions */
            if (node->type == T_Special)
                process_special_node((SpecialNode *)node);
            else
                ereport(ERROR, (errcode(ERRCODE_INTERNAL_ERROR),
                               errmsg("unexpected node type in special case")));
        }
    """,
    effort_estimate=0.5
)


UNREACHABLE_AFTER_RETURN_PATTERN = RefactoringPattern(
    id="DEAD_CODE_007",
    name="Unreachable Code After Return",
    category=CodeSmellCategory.DISPENSABLES,
    severity=CodeSmellSeverity.MEDIUM,
    description=(
        "Code that appears after return, elog(ERROR), or other terminating statements "
        "that will never be executed."
    ),
    cpgql_query="""
        -- Find methods with code patterns indicating unreachable code
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.full_name,
            m.filename,
            m.line_number,
            'UNREACHABLE_CODE' AS smell_type,
            'MEDIUM' AS severity
        FROM nodes_method m
        WHERE (m.code LIKE '%return;%' || chr(10) || '%'  -- Code after return
            OR m.code LIKE '%return %' || chr(10) || '%'
            OR m.code LIKE '%elog(FATAL%' || chr(10) || '%'
            OR m.code LIKE '%exit(%' || chr(10) || '%')
        AND (m.line_number_end - m.line_number) > 5
        AND m.line_number_end > 0
        AND m.name NOT LIKE 'test_%'
        ORDER BY m.filename, m.line_number
        LIMIT 100;
    """,
    symptoms=[
        "Code after return statement",
        "Code after elog(FATAL) or exit()",
        "Code after unconditional throw",
        "Compiler warnings about unreachable code"
    ],
    refactoring_technique=(
        "Delete Unreachable Code: Remove statements after return\n"
        "Fix Logic: Move code before return if needed\n"
        "Restructure Control Flow: Use proper conditionals\n"
        "Enable Compiler Warnings: -Wunreachable-code"
    ),
    example_before="""
        // BEFORE: Unreachable code after return
        static int process_value(int val) {
            if (val < 0)
                return -1;

            return val * 2;

            // Unreachable!
            log_debug("processing complete");
            cleanup_temp_data();
        }
    """,
    example_after="""
        // AFTER: Clean control flow
        static int process_value(int val) {
            if (val < 0)
                return -1;

            int result = val * 2;
            log_debug("processing complete");
            return result;
        }
    """,
    effort_estimate=0.25
)


DEAD_ASSIGNMENT_PATTERN = RefactoringPattern(
    id="DEAD_CODE_008",
    name="Dead Assignment (Value Overwritten Before Use)",
    category=CodeSmellCategory.DISPENSABLES,
    severity=CodeSmellSeverity.MEDIUM,
    description=(
        "Values assigned to variables but overwritten before being read. Dead "
        "assignments waste computation, can indicate logic errors, and may hide bugs."
    ),
    cpgql_query="""
        -- Find potential dead assignments (value overwritten without read)
        -- Simplified heuristic: Look for patterns that suggest overwritten values
        SELECT DISTINCT
            nm.id,
            nm.name AS method_name,
            nm.full_name,
            nm.filename,
            nm.line_number,
            'DEAD_ASSIGNMENT' AS smell_type,
            'MEDIUM' AS severity
        FROM nodes_method nm
        WHERE (nm.code LIKE '%=%=%'  -- Multiple assignments on same line pattern
               OR nm.code LIKE '%=%;%=%')  -- Two assignments nearby
          AND nm.full_name NOT LIKE 'test_%'
          AND nm.line_number_end - nm.line_number > 5  -- Non-trivial methods
        LIMIT 50;
    """,
    symptoms=[
        "Variable assigned, then immediately reassigned",
        "Return value discarded without use",
        "Computation result not used",
        "Default value always overwritten"
    ],
    refactoring_technique=(
        "Remove Dead Assignment: Delete the unused assignment\n"
        "Use Computed Value: Ensure value is read before overwrite\n"
        "Combine Assignments: Merge into single initialization"
    ),
    example_before="""
        // BEFORE: Dead assignment
        int result = compute_default();  // Dead - overwritten
        if (condition) {
            result = compute_special();
        } else {
            result = compute_other();
        }
        return result;
    """,
    example_after="""
        // AFTER: Removed dead assignment
        int result;
        if (condition) {
            result = compute_special();
        } else {
            result = compute_other();
        }
        return result;
    """,
    effort_estimate=0.5
)


INVARIANT_DEAD_CODE_PATTERN = RefactoringPattern(
    id="DEAD_CODE_009",
    name="Unreachable Code Due to Constant/Invariant",
    category=CodeSmellCategory.DISPENSABLES,
    severity=CodeSmellSeverity.MEDIUM,
    description=(
        "Code that can never execute because conditions always evaluate to the same "
        "value (e.g., if(0), if(false)). This dead code bloats binaries and confuses readers."
    ),
    cpgql_query="""
        -- Find always-false conditions
        SELECT DISTINCT
            nm.id,
            nm.name AS method_name,
            nm.full_name,
            nm.filename,
            nm.line_number,
            nm.code,
            'INVARIANT_DEAD_CODE' AS smell_type,
            'MEDIUM' AS severity
        FROM nodes_method nm
        WHERE (nm.code LIKE '%if (0)%'
            OR nm.code LIKE '%if (false)%'
            OR nm.code LIKE '%if (NULL)%'
            OR nm.code LIKE '%if (0 ==%'
            OR nm.code LIKE '%while (0)%'
            OR nm.code LIKE '%while (false)%')
          AND nm.full_name NOT LIKE 'test_%'
          AND nm.code NOT LIKE '%#if 0%'  -- Exclude preprocessor
        ORDER BY nm.filename, nm.line_number
        LIMIT 50;
    """,
    symptoms=[
        "Condition always evaluates to false",
        "Code after assert(false) or abort()",
        "Constant comparison always same result",
        "Loop condition always false"
    ],
    refactoring_technique=(
        "Remove Dead Branch: Delete the unreachable code\n"
        "Fix Logic Error: Correct the condition if it's a bug\n"
        "Use Preprocessor: Use #if 0 if keeping for reference"
    ),
    example_before="""
        // BEFORE: Always-false condition
        void process(int *data) {
            if (0) {
                // This code never runs
                debug_print(data);
            }

            // Or constant comparison
            int version = 2;
            if (version == 1) {
                // Dead code - version is always 2
                legacy_process(data);
            }
        }
    """,
    example_after="""
        // AFTER: Dead code removed
        void process(int *data) {
            // Debug code removed
            // Legacy code removed since version is always 2
        }
    """,
    effort_estimate=0.5
)


DEAD_CALLBACK_PATTERN = RefactoringPattern(
    id="DEAD_CODE_010",
    name="Dead Callback/Hook (Never Registered)",
    category=CodeSmellCategory.DISPENSABLES,
    severity=CodeSmellSeverity.MEDIUM,
    description=(
        "Callback or hook functions that are defined but never registered with "
        "the hook system or assigned to function pointers. These are remnants of "
        "removed features or incomplete implementations."
    ),
    cpgql_query="""
        -- Find callback-style functions not called anywhere
        WITH callback_candidates AS (
            SELECT DISTINCT m.id, m.name, m.full_name, m.filename, m.line_number
            FROM nodes_method m
            WHERE (m.name LIKE '%_hook%'
                OR m.name LIKE '%_callback%'
                OR m.name LIKE '%_handler%'
                OR m.name LIKE '%_notify%'
                OR m.name LIKE '%_event%')
              AND m.name NOT LIKE 'test_%'
              AND m.is_external = false
        ),
        called_methods AS (
            SELECT DISTINCT callee_name
            FROM call_containment
        )
        SELECT DISTINCT
            cc.id,
            cc.name AS method_name,
            cc.full_name,
            cc.filename,
            cc.line_number,
            'DEAD_CALLBACK' AS smell_type,
            'MEDIUM' AS severity
        FROM callback_candidates cc
        LEFT JOIN called_methods cm ON cc.name = cm.callee_name
        WHERE cm.callee_name IS NULL
        LIMIT 50;
    """,
    symptoms=[
        "Callback function never assigned to pointer",
        "Hook not registered with system",
        "Event handler never connected",
        "Unused notification handler"
    ],
    refactoring_technique=(
        "Register Callback: Add to appropriate hook list\n"
        "Remove Dead Callback: Delete if no longer needed\n"
        "Document Intent: Add comment explaining future use"
    ),
    example_before="""
        // BEFORE: Unregistered callback
        static void my_shutdown_hook(int code) {
            cleanup_resources();
            log_shutdown(code);
        }

        // Hook never registered:
        // register_shutdown_hook(my_shutdown_hook);
    """,
    example_after="""
        // AFTER: Either register or remove

        // Option 1: Register the hook
        void init_module(void) {
            register_shutdown_hook(my_shutdown_hook);
        }

        // Option 2: Remove the dead callback entirely
    """,
    effort_estimate=0.5
)


SINGLE_CALLER_FUNCTION_PATTERN = RefactoringPattern(
    id="DEAD_CODE_011",
    name="Single-Caller Function (Inlining Candidate)",
    category=CodeSmellCategory.DISPENSABLES,
    severity=CodeSmellSeverity.LOW,
    description=(
        "Small functions called from exactly one location. These may be candidates "
        "for inlining to reduce function call overhead and simplify code. However, "
        "keep for clarity if the function name documents intent."
    ),
    cpgql_query="""
        -- Find small functions with exactly one caller
        WITH caller_counts AS (
            SELECT
                callee_name,
                COUNT(DISTINCT containing_method_name) AS caller_count,
                MIN(containing_method_name) AS only_caller
            FROM call_containment
            GROUP BY callee_name
            HAVING COUNT(DISTINCT containing_method_name) = 1
        )
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.full_name,
            m.filename,
            m.line_number,
            (m.line_number_end - m.line_number) AS line_count,
            cc.only_caller,
            'SINGLE_CALLER_FUNCTION' AS smell_type,
            'LOW' AS severity
        FROM caller_counts cc
        JOIN nodes_method m ON m.name = cc.callee_name
        WHERE (m.line_number_end - m.line_number) <= 15
          AND m.line_number_end > 0
          AND m.name NOT LIKE 'test_%'
          AND m.name NOT LIKE '%_init%'
          AND m.name NOT LIKE '%_cleanup%'
          AND m.name NOT IN ('main', 'PG_init')
        ORDER BY line_count ASC
        LIMIT 50;
    """,
    symptoms=[
        "Function called from only one place",
        "Very short function (< 15 lines)",
        "Function adds little abstraction value",
        "Overhead of function call significant"
    ],
    refactoring_technique=(
        "Inline Function: Move body to single call site\n"
        "Keep If Clear: Retain if name documents intent well\n"
        "Use inline keyword: Mark for compiler inlining"
    ),
    example_before="""
        // BEFORE: Single-caller helper
        static int get_default_timeout(void) {
            return DEFAULT_TIMEOUT_MS;
        }

        void init_connection(Connection *conn) {
            conn->timeout = get_default_timeout();  // Only call site
            // ...
        }
    """,
    example_after="""
        // AFTER: Inlined for simplicity
        void init_connection(Connection *conn) {
            conn->timeout = DEFAULT_TIMEOUT_MS;  // Inlined
            // ...
        }
    """,
    effort_estimate=0.25
)


TEST_ONLY_FUNCTION_PATTERN = RefactoringPattern(
    id="DEAD_CODE_012",
    name="Test-Only Function in Production Code",
    category=CodeSmellCategory.DISPENSABLES,
    severity=CodeSmellSeverity.MEDIUM,
    description=(
        "Functions in production code that are only called from test files. These "
        "functions may be test helpers that should be moved to test directories, "
        "or they may indicate dead code that can be removed."
    ),
    cpgql_query="""
        -- Find production functions only called from tests
        WITH test_callers AS (
            SELECT DISTINCT callee_name
            FROM call_containment
            WHERE containing_method_name LIKE 'test_%'
               OR filename LIKE '%test%'
               OR filename LIKE '%_test.%'
        ),
        production_callers AS (
            SELECT DISTINCT callee_name
            FROM call_containment
            WHERE containing_method_name NOT LIKE 'test_%'
              AND filename NOT LIKE '%test%'
              AND filename NOT LIKE '%_test.%'
        ),
        test_only AS (
            SELECT tc.callee_name
            FROM test_callers tc
            LEFT JOIN production_callers pc ON tc.callee_name = pc.callee_name
            WHERE pc.callee_name IS NULL
        )
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.full_name,
            m.filename,
            m.line_number,
            (m.line_number_end - m.line_number) AS line_count,
            'TEST_ONLY_FUNCTION' AS smell_type,
            'MEDIUM' AS severity
        FROM test_only tof
        JOIN nodes_method m ON m.name = tof.callee_name
        WHERE m.filename NOT LIKE '%test%'
          AND m.filename NOT LIKE '%_test.%'
          AND m.name NOT LIKE 'test_%'
          AND (m.line_number_end - m.line_number) > 3
          AND m.line_number_end > 0
        ORDER BY m.filename, m.line_number
        LIMIT 50;
    """,
    symptoms=[
        "Function only called from test code",
        "Production code with test helper functions",
        "Internal APIs exposed only for testing",
        "Dead production code kept for tests"
    ],
    refactoring_technique=(
        "Move to Test: Relocate to test directory\n"
        "Remove If Unused: Delete if tests don't need it\n"
        "Mark as Test Helper: Use TEST_ONLY annotation\n"
        "Add Production Usage: Use in production if valuable"
    ),
    example_before="""
        // BEFORE: Production file with test-only function
        // src/parser.c

        // Used in production
        Node *parse_expression(const char *input) { ... }

        // Only called from tests!
        void dump_parse_tree(Node *root) {
            // Debugging helper
            print_node(root, 0);
        }
    """,
    example_after="""
        // AFTER: Moved to test helper file
        // src/parser.c - only production code
        Node *parse_expression(const char *input) { ... }

        // test/test_helpers.c - test utilities
        void dump_parse_tree(Node *root) {
            print_node(root, 0);
        }
    """,
    effort_estimate=1.0
)


ORPHAN_COMPONENT_PATTERN = RefactoringPattern(
    id="DEAD_CODE_013",
    name="Orphan Component (Isolated via WCC)",
    category=CodeSmellCategory.DISPENSABLES,
    severity=CodeSmellSeverity.HIGH,
    description=(
        "Code components isolated in the call graph with no paths from entry points. "
        "Detected via Weakly Connected Components analysis."
    ),
    cpgql_query="""
        -- Find methods in small isolated components (no entry point connections)
        WITH method_calls AS (
            SELECT DISTINCT containing_method_name AS caller_name, callee_name
            FROM call_containment
        ),
        entry_points AS (
            SELECT DISTINCT name FROM nodes_method
            WHERE name IN ('main', 'PG_init', 'InitPostgres', '_PG_init')
               OR name LIKE '%_handler'
               OR name LIKE '%_hook'
        ),
        reachable AS (
            -- Find all methods reachable from entry points (simplified)
            SELECT DISTINCT mc.callee_name AS name
            FROM method_calls mc
            WHERE mc.caller_name IN (SELECT name FROM entry_points)
            UNION
            SELECT DISTINCT mc2.callee_name
            FROM method_calls mc2
            WHERE mc2.caller_name IN (
                SELECT mc.callee_name
                FROM method_calls mc
                WHERE mc.caller_name IN (SELECT name FROM entry_points)
            )
        )
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.full_name,
            m.filename,
            m.line_number,
            'ORPHAN_COMPONENT' AS smell_type,
            'HIGH' AS severity
        FROM nodes_method m
        WHERE m.name NOT IN (SELECT name FROM reachable)
        AND m.name NOT IN (SELECT name FROM entry_points)
        AND m.name NOT LIKE 'test_%'
        AND m.name NOT LIKE '%_init'
        AND (m.line_number_end - m.line_number) > 10
        AND m.line_number_end > 0
        ORDER BY m.filename, m.line_number
        LIMIT 100;
    """,
    symptoms=[
        "No call paths from entry points",
        "Isolated in call graph",
        "Part of removed feature",
        "Leftover from refactoring"
    ],
    refactoring_technique=(
        "Delete Orphan Code: Remove entire isolated component\n"
        "Reconnect If Needed: Add calls from entry points\n"
        "Export As Library: If useful standalone\n"
        "Archive For Reference: Move to separate archive"
    ),
    example_before="""
        // BEFORE: Orphan functions never called
        static void old_feature_init(void) {
            // Part of removed feature
        }

        static void old_feature_process(Data *d) {
            // Never called after refactoring
        }

        static void old_feature_cleanup(void) {
            // Leftover code
        }
    """,
    example_after="""
        // AFTER: Orphan code removed
        // (code deleted, history preserved in git)
    """,
    effort_estimate=1.0
)


# Registry of dead code patterns
DEAD_CODE_PATTERNS: Dict[str, RefactoringPattern] = {
    "DEAD_CODE": DEAD_CODE_PATTERN,
    "DEPRECATED_MARKER": DEPRECATED_MARKER_PATTERN,
    "DISABLED_CODE_BLOCK": DISABLED_CODE_BLOCK_PATTERN,
    "UNUSED_VARIABLE": UNUSED_VARIABLE_PATTERN,
    "EMPTY_STUB": EMPTY_STUB_PATTERN,
    "ERROR_ONLY_FUNCTION": ERROR_ONLY_FUNCTION_PATTERN,
    "UNREACHABLE_AFTER_RETURN": UNREACHABLE_AFTER_RETURN_PATTERN,
    "DEAD_ASSIGNMENT": DEAD_ASSIGNMENT_PATTERN,
    "INVARIANT_DEAD_CODE": INVARIANT_DEAD_CODE_PATTERN,
    "DEAD_CALLBACK": DEAD_CALLBACK_PATTERN,
    "SINGLE_CALLER_FUNCTION": SINGLE_CALLER_FUNCTION_PATTERN,
    "TEST_ONLY_FUNCTION": TEST_ONLY_FUNCTION_PATTERN,
    "ORPHAN_COMPONENT": ORPHAN_COMPONENT_PATTERN,
}
