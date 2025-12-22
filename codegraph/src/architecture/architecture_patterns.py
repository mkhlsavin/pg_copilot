"""
Architecture Violation Pattern Library (Scenario 11)

Defines patterns for detecting architectural violations in code:
1. Circular Dependencies - Modules that depend on each other
2. Layering Violations - Lower layers calling higher layers
3. God Modules - Modules with excessive dependencies
4. Unstable Dependencies - Depending on unstable modules
5. Feature Envy - Methods accessing too much from other modules
6. Inappropriate Intimacy - Modules knowing too much about each other

Each pattern includes:
- Pattern ID and name
- Description and symptoms
- CPGQL/SQL detection query
- Severity level (critical, high, medium, low)
- Remediation guidance
- Impact assessment

Author: Architecture Analysis Team
Date: 2025-11-22
"""

from typing import List, Dict, Any, Optional

# Import base types from split module
from ._base import (
    ViolationSeverity,
    ViolationCategory,
    ArchitecturePattern,
    validate_pattern,
)


# ============================================================================
# PATTERN DEFINITIONS
# ============================================================================

# Pattern 1: Circular Dependencies
CIRCULAR_DEPENDENCIES = ArchitecturePattern(
    pattern_id="CIRCULAR_DEPS",
    name="Circular Dependencies",
    description="Two or more modules depend on each other, creating dependency cycles",
    category=ViolationCategory.DEPENDENCY,
    severity=ViolationSeverity.HIGH,
    symptoms=[
        "Module A imports/calls Module B, and Module B imports/calls Module A",
        "Compilation/build order issues",
        "Tight coupling between modules",
        "Difficulty testing modules in isolation",
        "Cascading changes across modules"
    ],
    remediation="""
    1. Identify the cycle using dependency analysis
    2. Extract common dependencies to a new shared module
    3. Invert dependencies using interfaces/abstractions
    4. Move shared code to a lower-level module
    5. Use dependency injection to break cycles
    """,
    impact="Makes code harder to maintain, test, and understand. Prevents modular reuse.",
    detection_query="""
    -- Find circular dependencies between files
    WITH file_deps AS (
        SELECT DISTINCT
            c1.filename AS from_file,
            m2.filename AS to_file
        FROM call_containment c1
        JOIN nodes_method m2 ON c1.callee_name = m2.name
        WHERE c1.filename != m2.filename
    )
    SELECT DISTINCT
        fd1.from_file AS module_a,
        fd1.to_file AS module_b,
        'CIRCULAR: A calls B and B calls A' AS violation_type
    FROM file_deps fd1
    JOIN file_deps fd2 ON fd1.from_file = fd2.to_file AND fd1.to_file = fd2.from_file
    WHERE fd1.from_file < fd1.to_file
    ORDER BY fd1.from_file
    LIMIT 50;
    """,
    example_before="""
    // Module A
    import ModuleB;
    class A {
        void methodA() {
            ModuleB.methodB();
        }
    }

    // Module B
    import ModuleA;
    class B {
        void methodB() {
            ModuleA.methodA();  // CIRCULAR!
        }
    }
    """,
    example_after="""
    // Shared Module
    interface IShared {
        void doWork();
    }

    // Module A
    class A implements IShared {
        void methodA() {
            // No dependency on B
        }
    }

    // Module B
    class B {
        private IShared shared;
        B(IShared s) { this.shared = s; }
        void methodB() {
            shared.doWork();  // Depends on abstraction
        }
    }
    """
)

# Pattern 2: Layering Violations
LAYERING_VIOLATIONS = ArchitecturePattern(
    pattern_id="LAYER_VIOLATION",
    name="Layering Violations",
    description="Lower architectural layers calling higher layers (violates layered architecture)",
    category=ViolationCategory.LAYERING,
    severity=ViolationSeverity.CRITICAL,
    symptoms=[
        "Data access layer calling presentation layer",
        "Backend calling frontend code",
        "Infrastructure calling business logic",
        "Inverted dependency flow",
        "Violation of separation of concerns"
    ],
    remediation="""
    1. Define clear architectural layers (e.g., Presentation -> Business -> Data)
    2. Enforce dependency rules: higher layers can call lower, not vice versa
    3. Use events/callbacks for upward communication
    4. Implement dependency inversion principle
    5. Refactor code to respect layer boundaries
    """,
    impact="Destroys architectural integrity, makes system fragile and hard to change",
    detection_query="""
    -- Find calls from lower layers to higher layers
    -- Assumes tags: arch-layer (values: presentation, business, data)
    SELECT DISTINCT
        caller_m.name AS caller_method,
        caller_m.filename AS caller_file,
        caller_layer.value AS caller_layer,
        callee_m.name AS callee_method,
        callee_m.filename AS callee_file,
        callee_layer.value AS callee_layer,
        'VIOLATION: ' || caller_layer.value || ' -> ' || callee_layer.value AS violation_type
    FROM edges_call c
    JOIN nodes_method caller_m ON c.src = caller_m.id
    JOIN nodes_method callee_m ON c.dst = callee_m.id
    JOIN edges_tagged_by e1 ON caller_m.id = e1.src
    JOIN nodes_tag caller_layer ON e1.dst = caller_layer.id
    JOIN edges_tagged_by e2 ON callee_m.id = e2.src
    JOIN nodes_tag callee_layer ON e2.dst = callee_layer.id
    WHERE caller_layer.name = 'arch-layer'
      AND callee_layer.name = 'arch-layer'
      AND (
          -- Data layer calling Business or Presentation
          (caller_layer.value = 'data' AND callee_layer.value IN ('business', 'presentation'))
          OR
          -- Business layer calling Presentation
          (caller_layer.value = 'business' AND callee_layer.value = 'presentation')
      )
    ORDER BY caller_layer.value, callee_layer.value
    LIMIT 100;
    """,
    example_before="""
    // Data Layer (LOWEST)
    class DatabaseAccess {
        void saveData() {
            // ...
            UIController.showSuccess();  // VIOLATION: calling presentation!
        }
    }

    // Presentation Layer (HIGHEST)
    class UIController {
        static void showSuccess() {
            // Display UI
        }
    }
    """,
    example_after="""
    // Data Layer
    interface DataCallback {
        void onSuccess();
    }

    class DatabaseAccess {
        void saveData(DataCallback callback) {
            // ...
            callback.onSuccess();  // Abstraction, not direct call
        }
    }

    // Presentation Layer
    class UIController implements DataCallback {
        void onSuccess() {
            // Display UI
        }
    }
    """
)

# Pattern 3: God Modules
GOD_MODULES = ArchitecturePattern(
    pattern_id="GOD_MODULE",
    name="God Modules (Excessive Dependencies)",
    description="Modules with too many outgoing or incoming dependencies",
    category=ViolationCategory.COUPLING,
    severity=ViolationSeverity.HIGH,
    symptoms=[
        "Module imports/uses > 20 other modules",
        "Module is used by > 30 other modules",
        "Central 'hub' module that everything depends on",
        "Changes to module affect many other modules",
        "Module does too many unrelated things"
    ],
    remediation="""
    1. Apply Single Responsibility Principle - split module by concern
    2. Extract related functionality to new cohesive modules
    3. Use facade pattern to simplify external interface
    4. Create smaller, focused modules with clear purposes
    5. Reduce coupling through dependency injection
    """,
    impact="High coupling, low cohesion, difficult to change without breaking other modules",
    detection_query="""
    -- Find modules with excessive dependencies (fan-out > 20 or fan-in > 30)
    WITH outgoing AS (
        SELECT c.filename AS module_file, COUNT(DISTINCT c.callee_name) AS fan_out
        FROM call_containment c
        GROUP BY c.filename
    ),
    incoming AS (
        SELECT m.filename AS module_file, COUNT(DISTINCT c.containing_method_name) AS fan_in
        FROM call_containment c
        JOIN nodes_method m ON c.callee_name = m.name
        GROUP BY m.filename
    ),
    method_counts AS (
        SELECT filename AS module_file, COUNT(*) AS method_count
        FROM nodes_method
        GROUP BY filename
    )
    SELECT
        COALESCE(o.module_file, i.module_file) AS module_file,
        COALESCE(o.fan_out, 0) AS outgoing_dependencies,
        COALESCE(i.fan_in, 0) AS incoming_dependencies,
        COALESCE(mc.method_count, 0) AS method_count,
        CASE
            WHEN COALESCE(o.fan_out, 0) > 20 AND COALESCE(i.fan_in, 0) > 30 THEN 'God Module (Hub)'
            WHEN COALESCE(o.fan_out, 0) > 20 THEN 'God Module (High Fan-Out)'
            WHEN COALESCE(i.fan_in, 0) > 30 THEN 'God Module (High Fan-In)'
        END AS violation_type
    FROM outgoing o
    FULL OUTER JOIN incoming i ON o.module_file = i.module_file
    LEFT JOIN method_counts mc ON COALESCE(o.module_file, i.module_file) = mc.module_file
    WHERE COALESCE(o.fan_out, 0) > 20 OR COALESCE(i.fan_in, 0) > 30
    ORDER BY (COALESCE(o.fan_out, 0) + COALESCE(i.fan_in, 0)) DESC
    LIMIT 50;
    """,
    example_before="""
    // God Module - does EVERYTHING
    class UtilityManager {
        void handleDatabase() { }
        void renderUI() { }
        void processNetwork() { }
        void manageFiles() { }
        void calculateMetrics() { }
        void validateInput() { }
        // ... 50+ unrelated methods
    }
    """,
    example_after="""
    // Split into focused modules
    class DatabaseManager {
        void handleDatabase() { }
    }

    class UIRenderer {
        void renderUI() { }
    }

    class NetworkProcessor {
        void processNetwork() { }
    }

    class FileManager {
        void manageFiles() { }
    }
    """
)

# Pattern 4: Unstable Dependencies
UNSTABLE_DEPENDENCIES = ArchitecturePattern(
    pattern_id="UNSTABLE_DEPS",
    name="Unstable Dependencies",
    description="Stable modules depending on unstable modules (violates Stable Dependencies Principle)",
    category=ViolationCategory.DEPENDENCY,
    severity=ViolationSeverity.MEDIUM,
    symptoms=[
        "Core/stable modules depending on volatile/experimental modules",
        "High churn in dependent modules due to dependency changes",
        "Frequent breaking changes propagating through system",
        "Stable abstractions depending on concrete implementations"
    ],
    remediation="""
    1. Invert dependencies - stable modules should define interfaces
    2. Unstable modules should implement stable interfaces
    3. Use dependency injection to decouple stable from unstable
    4. Move frequently-changing code to plugins/extensions
    5. Apply Dependency Inversion Principle (DIP)
    """,
    impact="Stable code becomes unstable, ripple effects from changes, reduced reliability",
    detection_query="""
    -- Calculate instability metric for each module
    -- Instability = Fan-Out / (Fan-In + Fan-Out)
    -- Stable modules (instability < 0.3) should NOT depend on unstable (instability > 0.7)
    WITH module_metrics AS (
        SELECT
            m.filename AS module_file,
            COUNT(DISTINCT CASE WHEN c.src = m.id THEN c.dst END) AS fan_out,
            COUNT(DISTINCT CASE WHEN c.dst = m.id THEN c.src END) AS fan_in,
            CAST(COUNT(DISTINCT CASE WHEN c.src = m.id THEN c.dst END) AS FLOAT) /
                NULLIF(COUNT(DISTINCT CASE WHEN c.src = m.id THEN c.dst END) +
                       COUNT(DISTINCT CASE WHEN c.dst = m.id THEN c.src END), 0) AS instability
        FROM nodes_method m
        LEFT JOIN edges_call c ON m.id = c.src OR m.id = c.dst
        GROUP BY m.filename
    ),
    unstable_deps AS (
        SELECT DISTINCT
            stable.module_file AS stable_module,
            stable.instability AS stable_instability,
            unstable.module_file AS unstable_module,
            unstable.instability AS unstable_instability
        FROM edges_call c
        JOIN nodes_method m1 ON c.src = m1.id
        JOIN nodes_method m2 ON c.dst = m2.id
        JOIN module_metrics stable ON m1.filename = stable.module_file
        JOIN module_metrics unstable ON m2.filename = unstable.module_file
        WHERE stable.instability < 0.3  -- Stable module
          AND unstable.instability > 0.7  -- Unstable module
          AND stable.module_file != unstable.module_file
    )
    SELECT
        stable_module,
        ROUND(stable_instability, 3) AS stable_instability,
        unstable_module,
        ROUND(unstable_instability, 3) AS unstable_instability,
        'Stable depending on Unstable' AS violation_type
    FROM unstable_deps
    ORDER BY stable_instability, unstable_instability DESC
    LIMIT 50;
    """,
    example_before="""
    // Stable Core Module (rarely changes)
    class CoreEngine {
        private ExperimentalFeature exp = new ExperimentalFeature();

        void process() {
            exp.tryNewAlgorithm();  // VIOLATION: stable depends on unstable
        }
    }

    // Unstable Experimental Module (changes frequently)
    class ExperimentalFeature {
        void tryNewAlgorithm() {
            // Frequent changes here break CoreEngine!
        }
    }
    """,
    example_after="""
    // Stable Core Module defines interface
    interface IProcessingStrategy {
        void execute();
    }

    class CoreEngine {
        private IProcessingStrategy strategy;

        CoreEngine(IProcessingStrategy s) {
            this.strategy = s;
        }

        void process() {
            strategy.execute();  // Depends on stable abstraction
        }
    }

    // Unstable module implements stable interface
    class ExperimentalFeature implements IProcessingStrategy {
        void execute() {
            // Can change frequently without breaking CoreEngine
        }
    }
    """
)

# Pattern 5: Feature Envy
FEATURE_ENVY = ArchitecturePattern(
    pattern_id="FEATURE_ENVY",
    name="Feature Envy",
    description="Methods that access data/methods from other modules more than their own",
    category=ViolationCategory.COHESION,
    severity=ViolationSeverity.MEDIUM,
    symptoms=[
        "Method makes > 5 calls to another module's methods",
        "Method accesses fields/data from other modules heavily",
        "Method seems to belong in the other module",
        "Low cohesion within current module",
        "Method knows too much about other module's internals"
    ],
    remediation="""
    1. Move the method to the module it's most interested in
    2. Extract common behavior to a shared module
    3. Use Tell Don't Ask principle - pass data as parameters
    4. Reduce coupling by using message passing
    5. Apply Extract Method and Move Method refactorings
    """,
    impact="Poor cohesion, tight coupling, code in wrong place, harder to maintain",
    detection_query="""
    -- Find methods that call other modules' methods > 5 times
    SELECT
        c.containing_method_name AS envious_method,
        c.filename AS envious_module,
        m2.filename AS envied_module,
        COUNT(*) AS call_count,
        'Feature Envy: ' || c.containing_method_name || ' -> ' || m2.filename AS violation_type
    FROM call_containment c
    JOIN nodes_method m2 ON c.callee_name = m2.name
    WHERE c.filename != m2.filename
    GROUP BY c.containing_method_name, c.filename, m2.filename
    HAVING COUNT(*) > 5
    ORDER BY call_count DESC
    LIMIT 100;
    """,
    example_before="""
    // Module A
    class ReportGenerator {
        void generateReport(Customer customer) {
            // Feature Envy: too interested in Customer internals
            String name = customer.getName();
            String address = customer.getAddress();
            String phone = customer.getPhone();
            int orderCount = customer.getOrderCount();
            double totalSpent = customer.getTotalSpent();
            // ... uses all Customer data
        }
    }

    // Module B
    class Customer {
        String getName() { }
        String getAddress() { }
        String getPhone() { }
        int getOrderCount() { }
        double getTotalSpent() { }
    }
    """,
    example_after="""
    // Module A
    class ReportGenerator {
        void generateReport(Customer customer) {
            String report = customer.generateSummary();  // Tell, don't ask
        }
    }

    // Module B - method moved to where data lives
    class Customer {
        String generateSummary() {
            // All data access internal to Customer
            return String.format("%s, %s, %s, Orders: %d, Spent: %.2f",
                getName(), getAddress(), getPhone(),
                getOrderCount(), getTotalSpent());
        }
    }
    """
)

# Pattern 6: Inappropriate Intimacy
INAPPROPRIATE_INTIMACY = ArchitecturePattern(
    pattern_id="INAPPROPRIATE_INTIMACY",
    name="Inappropriate Intimacy",
    description="Modules that are too tightly coupled, knowing too much about each other's internals",
    category=ViolationCategory.COUPLING,
    severity=ViolationSeverity.HIGH,
    symptoms=[
        "Modules accessing each other's private/internal data",
        "Bidirectional dependencies between modules",
        "Changes in one module always require changes in the other",
        "Modules cannot be reused independently",
        "High coupling coefficient (> 50% shared dependencies)"
    ],
    remediation="""
    1. Extract common behavior to a separate module
    2. Use interfaces to reduce direct coupling
    3. Apply Law of Demeter - only talk to immediate friends
    4. Merge overly-intimate modules if they truly belong together
    5. Use message passing instead of direct access
    """,
    impact="Tightly coupled modules, difficult to change or reuse independently",
    detection_query="""
    -- Find module pairs with bidirectional calls and high coupling
    WITH module_calls AS (
        SELECT
            c.filename AS from_file,
            m.filename AS to_file,
            COUNT(*) AS call_count
        FROM call_containment c
        JOIN nodes_method m ON c.callee_name = m.name
        WHERE c.filename != m.filename
        GROUP BY c.filename, m.filename
    )
    SELECT
        mc1.from_file AS module_a,
        mc1.to_file AS module_b,
        mc1.call_count AS a_to_b_calls,
        COALESCE(mc2.call_count, 0) AS b_to_a_calls,
        (mc1.call_count + COALESCE(mc2.call_count, 0)) AS total_coupling,
        'Inappropriate Intimacy (bidirectional)' AS violation_type
    FROM module_calls mc1
    LEFT JOIN module_calls mc2 ON mc1.from_file = mc2.to_file AND mc1.to_file = mc2.from_file
    WHERE mc1.from_file < mc1.to_file
      AND COALESCE(mc2.call_count, 0) > 0
      AND (mc1.call_count + COALESCE(mc2.call_count, 0)) > 10
    ORDER BY total_coupling DESC
    LIMIT 50;
    """,
    example_before="""
    // Module A knows too much about Module B
    class OrderProcessor {
        void processOrder(Cart cart) {
            cart.items.clear();  // Accessing internals!
            cart.total = 0;      // Accessing internals!
            cart.status = "processed";  // Accessing internals!
        }
    }

    // Module B knows too much about Module A
    class Cart {
        List items;
        double total;
        String status;

        void validate() {
            OrderProcessor.validateItems(this.items);  // Too intimate!
        }
    }
    """,
    example_after="""
    // Module A uses public interface
    class OrderProcessor {
        void processOrder(Cart cart) {
            cart.clear();  // Public method, not internal access
            cart.markProcessed();  // Public method
        }
    }

    // Module B encapsulates internals
    class Cart {
        private List items;
        private double total;
        private String status;

        public void clear() {
            items.clear();
            total = 0;
        }

        public void markProcessed() {
            status = "processed";
        }

        public boolean isValid() {
            return !items.isEmpty();  // Self-validating
        }
    }
    """
)


# ============================================================================
# INCLUDE-BASED DEPENDENCY PATTERNS (Sprint 3 - Scenario 11 Enhancement)
# ============================================================================

# Pattern 7: File Include Dependencies
FILE_INCLUDE_DEPS = ArchitecturePattern(
    pattern_id="FILE_INCLUDE_DEPS",
    name="File Include Dependencies",
    description="Shows which files include a specific header, supporting module dependency analysis",
    category=ViolationCategory.DEPENDENCY,
    severity=ViolationSeverity.LOW,  # Informational pattern
    symptoms=[
        "Need to understand header file dependencies",
        "Want to find all files including a specific header",
        "Analyzing impact of header file changes",
        "Understanding module coupling through includes"
    ],
    remediation="""
    1. Review header file organization
    2. Minimize include dependencies where possible
    3. Use forward declarations instead of full includes
    4. Split large headers into smaller focused ones
    """,
    impact="Understanding include dependencies helps plan refactoring and assess change impact.",
    detection_query="""
    -- Find all files including a specific header
    -- Use with WHERE clause: WHERE ei.include_path LIKE '%target_header%'
    SELECT DISTINCT
        ei.src_filename AS dependent_file,
        ei.dst_filename AS included_file,
        ei.include_path,
        ei.is_system,
        ei.line_number
    FROM edges_include ei
    WHERE ei.dst_filename IS NOT NULL
    ORDER BY ei.src_filename, ei.line_number
    LIMIT 100;
    """,
    example_before="// Many files with scattered includes",
    example_after="// Organized include structure with forward declarations"
)


# Pattern 8: Circular Include Dependencies
CIRCULAR_INCLUDE_DEPS = ArchitecturePattern(
    pattern_id="CIRCULAR_INCLUDE_DEPS",
    name="Circular Include Dependencies",
    description="Header files that include each other directly or transitively, causing potential compilation issues",
    category=ViolationCategory.DEPENDENCY,
    severity=ViolationSeverity.HIGH,
    symptoms=[
        "File A includes B, and B includes A",
        "Compilation order dependencies",
        "Incomplete type errors during compilation",
        "Header guard ordering issues"
    ],
    remediation="""
    1. Identify the circular dependency chain
    2. Use forward declarations to break the cycle
    3. Extract common types to a separate header
    4. Restructure headers to have clear layering
    5. Use interface headers to decouple implementations
    """,
    impact="Circular includes cause compilation issues and indicate poor module organization.",
    detection_query="""
    -- Find circular include dependencies
    SELECT DISTINCT
        e1.src_filename AS file_a,
        e2.src_filename AS file_b,
        e1.include_path AS a_includes,
        e2.include_path AS b_includes,
        'CIRCULAR INCLUDE: A includes B and B includes A' AS violation_type
    FROM edges_include e1
    JOIN edges_include e2 ON e1.src_filename = e2.dst_filename
                          AND e1.dst_filename = e2.src_filename
    WHERE e1.src_filename < e1.dst_filename
    ORDER BY e1.src_filename
    LIMIT 50;
    """,
    example_before="""
    // a.h
    #include "b.h"
    struct A { struct B* b_ref; };

    // b.h
    #include "a.h"  // Circular!
    struct B { struct A* a_ref; };
    """,
    example_after="""
    // a_fwd.h
    struct A;

    // b_fwd.h
    struct B;

    // a.h
    #include "b_fwd.h"
    struct A { struct B* b_ref; };

    // b.h
    #include "a_fwd.h"
    struct B { struct A* a_ref; };
    """
)


# Pattern 9: Highly Included Headers (Hub Headers)
HUB_HEADERS = ArchitecturePattern(
    pattern_id="HUB_HEADERS",
    name="Hub Headers (Highly Included)",
    description="Headers included by many files, indicating potential architectural chokepoints or core utilities",
    category=ViolationCategory.COUPLING,
    severity=ViolationSeverity.MEDIUM,
    symptoms=[
        "Header included by 50+ files",
        "Changes to header cause widespread recompilation",
        "Header contains mixed concerns",
        "Difficult to modify without breaking many files"
    ],
    remediation="""
    1. Review if header should be split by concern
    2. Use precompiled headers for truly stable headers
    3. Consider forward declarations to reduce includes
    4. Document stable API vs internal implementation
    """,
    impact="Hub headers are change-sensitive and affect build times; requires careful management.",
    detection_query="""
    -- Find hub headers (included by many files)
    SELECT
        ei.dst_filename AS header_file,
        ei.include_path AS include_path,
        COUNT(DISTINCT ei.src_filename) AS includer_count,
        ei.is_system
    FROM edges_include ei
    WHERE ei.dst_filename IS NOT NULL
    GROUP BY ei.dst_filename, ei.include_path, ei.is_system
    HAVING COUNT(DISTINCT ei.src_filename) >= 10
    ORDER BY includer_count DESC
    LIMIT 30;
    """,
    example_before="""
    // mega_header.h - included everywhere
    #include <all_types.h>
    #include <all_utils.h>
    #include <all_interfaces.h>
    // 1000+ lines of declarations
    """,
    example_after="""
    // core_types.h - focused header
    struct CoreType { ... };

    // utils.h - utility functions only
    int utility_func(int);

    // Each file includes only what it needs
    """
)


# Pattern 10: Module Include Isolation
MODULE_INCLUDE_ISOLATION = ArchitecturePattern(
    pattern_id="MODULE_INCLUDE_ISOLATION",
    name="Module Include Isolation Analysis",
    description="Analyzes which modules/directories have includes from other modules, revealing coupling",
    category=ViolationCategory.COUPLING,
    severity=ViolationSeverity.MEDIUM,
    symptoms=[
        "Includes crossing module boundaries",
        "Backend code including frontend headers",
        "Test code dependencies on implementation",
        "Unexpected cross-cutting includes"
    ],
    remediation="""
    1. Define clear module boundaries
    2. Create public interface headers for each module
    3. Internal headers should not be included externally
    4. Use dependency injection for cross-module needs
    """,
    impact="Cross-module includes create tight coupling and hinder independent module development.",
    detection_query="""
    -- Analyze cross-module include dependencies
    -- Extracts directory as 'module' from filename
    WITH module_includes AS (
        SELECT
            REGEXP_EXTRACT(ei.src_filename, '([^/\\\\]+)[/\\\\][^/\\\\]+$', 1) AS src_module,
            REGEXP_EXTRACT(ei.dst_filename, '([^/\\\\]+)[/\\\\][^/\\\\]+$', 1) AS dst_module,
            ei.src_filename,
            ei.dst_filename
        FROM edges_include ei
        WHERE ei.src_filename IS NOT NULL
          AND ei.dst_filename IS NOT NULL
    )
    SELECT
        src_module,
        dst_module,
        COUNT(*) AS include_count,
        COUNT(DISTINCT src_filename) AS source_files
    FROM module_includes
    WHERE src_module != dst_module
      AND src_module IS NOT NULL
      AND dst_module IS NOT NULL
    GROUP BY src_module, dst_module
    ORDER BY include_count DESC
    LIMIT 30;
    """,
    example_before="""
    // frontend/ui.c
    #include "backend/database.h"  // Cross-module!
    #include "backend/auth.h"       // Cross-module!
    """,
    example_after="""
    // frontend/ui.c
    #include "api/database_api.h"  // Public interface only
    #include "api/auth_api.h"       // Public interface only
    """
)


# ============================================================================
# PATTERN REGISTRY
# ============================================================================

# All available architecture patterns
ARCHITECTURE_PATTERNS: List[ArchitecturePattern] = [
    CIRCULAR_DEPENDENCIES,
    LAYERING_VIOLATIONS,
    GOD_MODULES,
    UNSTABLE_DEPENDENCIES,
    FEATURE_ENVY,
    INAPPROPRIATE_INTIMACY,
    # Sprint 3 - Include-based patterns for Scenario 11
    FILE_INCLUDE_DEPS,
    CIRCULAR_INCLUDE_DEPS,
    HUB_HEADERS,
    MODULE_INCLUDE_ISOLATION
]

# Index by pattern ID
PATTERNS_BY_ID: Dict[str, ArchitecturePattern] = {
    pattern.pattern_id: pattern
    for pattern in ARCHITECTURE_PATTERNS
}

# Index by category
PATTERNS_BY_CATEGORY: Dict[str, List[ArchitecturePattern]] = {
    'dependency': [p for p in ARCHITECTURE_PATTERNS if p.category == ViolationCategory.DEPENDENCY],
    'layering': [p for p in ARCHITECTURE_PATTERNS if p.category == ViolationCategory.LAYERING],
    'coupling': [p for p in ARCHITECTURE_PATTERNS if p.category == ViolationCategory.COUPLING],
    'cohesion': [p for p in ARCHITECTURE_PATTERNS if p.category == ViolationCategory.COHESION]
}

# Index by severity
PATTERNS_BY_SEVERITY: Dict[str, List[ArchitecturePattern]] = {
    'critical': [p for p in ARCHITECTURE_PATTERNS if p.severity == ViolationSeverity.CRITICAL],
    'high': [p for p in ARCHITECTURE_PATTERNS if p.severity == ViolationSeverity.HIGH],
    'medium': [p for p in ARCHITECTURE_PATTERNS if p.severity == ViolationSeverity.MEDIUM],
    'low': [p for p in ARCHITECTURE_PATTERNS if p.severity == ViolationSeverity.LOW]
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_pattern(pattern_id: str) -> Optional[ArchitecturePattern]:
    """
    Get a pattern by its ID.

    Args:
        pattern_id: Pattern identifier (e.g., "CIRCULAR_DEPS")

    Returns:
        ArchitecturePattern if found, None otherwise
    """
    return PATTERNS_BY_ID.get(pattern_id)


def get_patterns_by_category(category: str) -> List[ArchitecturePattern]:
    """
    Get all patterns in a category.

    Args:
        category: Category name (dependency, layering, coupling, cohesion)

    Returns:
        List of patterns in that category
    """
    return PATTERNS_BY_CATEGORY.get(category, [])


def get_patterns_by_severity(severity: str) -> List[ArchitecturePattern]:
    """
    Get all patterns with a specific severity.

    Args:
        severity: Severity level (critical, high, medium, low)

    Returns:
        List of patterns with that severity
    """
    return PATTERNS_BY_SEVERITY.get(severity, [])


def get_all_patterns() -> List[ArchitecturePattern]:
    """
    Get all architecture patterns.

    Returns:
        List of all patterns
    """
    return ARCHITECTURE_PATTERNS.copy()


if __name__ == "__main__":
    # Validation
    print("Architecture Violation Pattern Library")
    print("=" * 60)
    print(f"Total patterns: {len(ARCHITECTURE_PATTERNS)}")
    print(f"\nBreakdown by category:")
    for category, patterns in PATTERNS_BY_CATEGORY.items():
        print(f"  {category}: {len(patterns)} patterns")

    print(f"\nBreakdown by severity:")
    for severity, patterns in PATTERNS_BY_SEVERITY.items():
        print(f"  {severity}: {len(patterns)} patterns")

    print(f"\nPattern validation:")
    for pattern in ARCHITECTURE_PATTERNS:
        valid = validate_pattern(pattern)
        status = "[OK]" if valid else "[!]"
        print(f"  {status} {pattern.pattern_id}: {pattern.name}")
