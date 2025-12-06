"""
Technical Debt Pattern Library (Scenario 12)

Defines patterns for detecting and quantifying technical debt:
1. TODO/FIXME Comments - Unfinished work markers
2. Deprecated API Usage - Using outdated functions
3. Code Duplication - Duplicated code blocks
4. Long Methods - Methods exceeding length thresholds
5. Complex Methods - High cyclomatic complexity
6. Dead Code - Unused methods and variables

Each pattern includes:
- Pattern ID and name
- Description and detection criteria
- CPGQL/SQL detection query
- Severity level (critical, high, medium, low)
- Effort estimation (hours to fix)
- Business value/impact
- Remediation guidance

Author: Technical Debt Team
Date: 2025-11-22
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class DebtSeverity(Enum):
    """Severity levels for technical debt"""
    CRITICAL = "critical"  # Urgent, blocks progress
    HIGH = "high"          # Significant debt, high interest
    MEDIUM = "medium"      # Moderate debt, manageable
    LOW = "low"            # Minor debt, can defer


class DebtCategory(Enum):
    """Categories of technical debt"""
    CODE_QUALITY = "code_quality"           # Code smells, duplication
    MAINTENANCE = "maintenance"             # TODOs, FIXMEs, deprecated usage
    COMPLEXITY = "complexity"               # Complex/long methods
    UNUSED_CODE = "unused_code"             # Dead code


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class DebtPattern:
    """
    Definition of a technical debt pattern.

    Attributes:
        pattern_id: Unique identifier (e.g., "TODO_COMMENTS")
        name: Human-readable name
        description: What this debt represents
        category: DebtCategory enum
        severity: DebtSeverity enum
        symptoms: Observable signs of this debt
        remediation: How to fix this debt
        impact: Business/technical impact
        effort_hours: Base effort to fix (hours)
        interest_rate: How much harder it gets over time (multiplier)
        detection_query: SQL/CPGQL query to find instances
        example: Code example showing the debt
    """
    pattern_id: str
    name: str
    description: str
    category: DebtCategory
    severity: DebtSeverity
    symptoms: List[str]
    remediation: str
    impact: str
    effort_hours: float  # Base effort to fix one instance
    interest_rate: float  # How debt grows over time (1.0 = no growth)
    detection_query: str
    example: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'pattern_id': self.pattern_id,
            'name': self.name,
            'description': self.description,
            'category': self.category.value,
            'severity': self.severity.value,
            'symptoms': self.symptoms,
            'remediation': self.remediation,
            'impact': self.impact,
            'effort_hours': self.effort_hours,
            'interest_rate': self.interest_rate,
            'detection_query': self.detection_query,
            'example': self.example
        }


# ============================================================================
# PATTERN DEFINITIONS
# ============================================================================

# Pattern 1: TODO/FIXME Comments
TODO_FIXME_COMMENTS = DebtPattern(
    pattern_id="TODO_COMMENTS",
    name="TODO/FIXME Comments",
    description="Unfinished work marked with TODO, FIXME, or HACK comments in code",
    category=DebtCategory.MAINTENANCE,
    severity=DebtSeverity.MEDIUM,
    symptoms=[
        "Comments containing TODO, FIXME, HACK, XXX",
        "Incomplete implementations",
        "Deferred work that was never completed",
        "Temporary workarounds marked for future fixing"
    ],
    remediation="""
    1. Review each TODO/FIXME comment for current relevance
    2. Complete the deferred work or create proper ticket
    3. Remove obsolete TODOs that are no longer relevant
    4. Convert remaining TODOs to tracked work items
    5. Set deadlines for addressing each item
    """,
    impact="Accumulates over time, forgotten work, quality degradation, technical surprises",
    effort_hours=2.0,  # Average 2 hours per TODO
    interest_rate=1.1,  # 10% harder over time as context is lost
    detection_query="""
    -- Find methods with TODO/FIXME/HACK comments
    SELECT DISTINCT
        m.id AS method_id,
        m.name AS method_name,
        m.filename,
        m.line_number,
        m.line_number_end,
        (m.line_number_end - m.line_number + 1) AS method_length,
        'TODO/FIXME comment in method' AS debt_type
    FROM nodes_method m
    WHERE m.code LIKE '%TODO%'
       OR m.code LIKE '%FIXME%'
       OR m.code LIKE '%HACK%'
       OR m.code LIKE '%XXX%'
       OR m.code LIKE '%BUG%'
    ORDER BY m.filename, m.line_number
    LIMIT 100;
    """,
    example="""
    // TODO: This needs proper error handling
    void processData(Data* data) {
        // FIXME: Memory leak here
        char* buffer = malloc(1024);
        // HACK: Temporary workaround for bug #1234
        if (data == NULL) return;
    }
    """
)

# Pattern 2: Deprecated API Usage
DEPRECATED_API_USAGE = DebtPattern(
    pattern_id="DEPRECATED_API",
    name="Deprecated API Usage",
    description="Usage of deprecated or obsolete APIs that should be replaced",
    category=DebtCategory.MAINTENANCE,
    severity=DebtSeverity.HIGH,
    symptoms=[
        "Calls to functions marked as deprecated",
        "Use of obsolete APIs",
        "Warnings about deprecated usage during compilation",
        "APIs scheduled for removal in future versions"
    ],
    remediation="""
    1. Identify replacement API for deprecated function
    2. Update all call sites to use new API
    3. Test changes thoroughly
    4. Remove imports/includes of deprecated modules
    5. Update documentation
    """,
    impact="Risk of breaking when deprecated API is removed, security vulnerabilities, performance issues",
    effort_hours=4.0,  # Average 4 hours per deprecated API migration
    interest_rate=1.3,  # 30% harder as API gets closer to removal
    detection_query="""
    -- Find methods calling deprecated functions
    -- Assumes deprecated functions are tagged with 'deprecated' tag
    SELECT DISTINCT
        caller_m.name AS caller_method,
        caller_m.filename AS caller_file,
        caller_m.line_number,
        callee_m.name AS deprecated_api,
        callee_m.filename AS deprecated_api_file,
        'Calls deprecated API' AS debt_type
    FROM edges_call c
    JOIN nodes_method caller_m ON c.src = caller_m.id
    JOIN nodes_method callee_m ON c.dst = callee_m.id
    JOIN edges_tagged_by etb ON callee_m.id = etb.src
    JOIN nodes_tag tag ON etb.dst = tag.id
    WHERE tag.name = 'deprecated'
       OR callee_m.name LIKE '%_deprecated%'
       OR callee_m.name LIKE '%_obsolete%'
    ORDER BY caller_m.filename, caller_m.line_number
    LIMIT 100;
    """,
    example="""
    // Using deprecated API
    void processRequest() {
        // DEPRECATED: Use newProcessData() instead
        oldProcessData();  // This API will be removed in v3.0
    }
    """
)

# Pattern 3: Code Duplication
CODE_DUPLICATION = DebtPattern(
    pattern_id="CODE_DUPLICATION",
    name="Code Duplication",
    description="Duplicated code blocks that should be refactored into reusable functions",
    category=DebtCategory.CODE_QUALITY,
    severity=DebtSeverity.MEDIUM,
    symptoms=[
        "Similar or identical code blocks in multiple places",
        "Copy-paste programming patterns",
        "Repeated logic across methods",
        "Changes need to be applied in multiple locations"
    ],
    remediation="""
    1. Identify duplicated code blocks
    2. Extract common code to a shared function
    3. Replace all duplicates with calls to shared function
    4. Add appropriate parameters for variations
    5. Write tests for extracted function
    """,
    impact="Inconsistent bug fixes, maintenance burden, harder to change, increased codebase size",
    effort_hours=3.0,  # Average 3 hours to refactor duplication
    interest_rate=1.15,  # 15% harder as duplication spreads
    detection_query="""
    -- Find methods with similar names (potential duplication)
    -- Simple heuristic: methods with same prefix and similar length
    WITH method_stats AS (
        SELECT
            m.id,
            m.name,
            m.filename,
            m.line_number,
            (m.line_number_end - m.line_number + 1) AS method_length,
            SUBSTR(m.name, 1, INSTR(m.name || '_', '_') - 1) AS name_prefix
        FROM nodes_method m
        WHERE m.name IS NOT NULL
    )
    SELECT
        m1.name AS method_1,
        m1.filename AS file_1,
        m1.line_number AS line_1,
        m2.name AS method_2,
        m2.filename AS file_2,
        m2.line_number AS line_2,
        ABS(m1.method_length - m2.method_length) AS length_diff,
        'Potential code duplication' AS debt_type
    FROM method_stats m1
    JOIN method_stats m2 ON m1.name_prefix = m2.name_prefix
    WHERE m1.id < m2.id  -- Avoid duplicates
      AND m1.name != m2.name
      AND m1.name_prefix != ''
      AND LENGTH(m1.name_prefix) > 4  -- Meaningful prefix
      AND ABS(m1.method_length - m2.method_length) < 10  -- Similar size
    ORDER BY m1.name_prefix, length_diff
    LIMIT 100;
    """,
    example="""
    // Duplicated code - should be extracted
    void processUserData() {
        User* user = getUser();
        if (user == NULL) return;
        validateUser(user);
        saveToDatabase(user);
        logAction("user processed");
    }

    void processAdminData() {
        Admin* admin = getAdmin();
        if (admin == NULL) return;
        validateAdmin(admin);
        saveToDatabase(admin);
        logAction("admin processed");
    }
    """
)

# Pattern 4: Long Methods (God Methods)
LONG_METHODS = DebtPattern(
    pattern_id="LONG_METHODS",
    name="Long Methods (God Methods)",
    description="Methods that are too long and should be broken down into smaller functions",
    category=DebtCategory.COMPLEXITY,
    severity=DebtSeverity.MEDIUM,
    symptoms=[
        "Methods exceeding 50-100 lines",
        "Difficult to understand and test",
        "Multiple responsibilities in one method",
        "Excessive scrolling to read entire method",
        "Hard to name clearly"
    ],
    remediation="""
    1. Identify logical sections within the long method
    2. Extract each section to its own well-named function
    3. Ensure extracted functions have single responsibility
    4. Update tests to cover extracted functions
    5. Keep main method as orchestrator
    """,
    impact="Hard to understand, test, and maintain; high bug risk; poor reusability",
    effort_hours=5.0,  # Average 5 hours to refactor long method
    interest_rate=1.2,  # 20% harder as method grows longer
    detection_query="""
    -- Find methods exceeding 50 lines
    SELECT
        m.name AS method_name,
        m.filename,
        m.line_number,
        m.line_number_end,
        (m.line_number_end - m.line_number + 1) AS method_length,
        CASE
            WHEN (m.line_number_end - m.line_number + 1) > 200 THEN 'critical'
            WHEN (m.line_number_end - m.line_number + 1) > 100 THEN 'high'
            ELSE 'medium'
        END AS severity,
        'Long method' AS debt_type
    FROM nodes_method m
    WHERE (m.line_number_end - m.line_number + 1) > 50
    ORDER BY (m.line_number_end - m.line_number + 1) DESC
    LIMIT 100;
    """,
    example="""
    // Long method - should be broken down
    void processOrder(Order* order) {
        // 200+ lines of code doing everything:
        // - Validate order
        // - Check inventory
        // - Calculate pricing
        // - Apply discounts
        // - Process payment
        // - Update inventory
        // - Send notifications
        // - Log everything
        // ... many more lines ...
    }
    """
)

# Pattern 5: Complex Methods (High Cyclomatic Complexity)
COMPLEX_METHODS = DebtPattern(
    pattern_id="COMPLEX_METHODS",
    name="Complex Methods (High Cyclomatic Complexity)",
    description="Methods with high cyclomatic complexity (many branches/paths)",
    category=DebtCategory.COMPLEXITY,
    severity=DebtSeverity.HIGH,
    symptoms=[
        "Many if/else or switch statements",
        "Deeply nested conditionals",
        "Complex boolean expressions",
        "Difficult to test all paths",
        "High number of execution paths"
    ],
    remediation="""
    1. Measure cyclomatic complexity (target < 10)
    2. Extract complex conditionals to well-named functions
    3. Use polymorphism instead of switch/if-else chains
    4. Apply strategy or state pattern for complex logic
    5. Write comprehensive tests for all paths
    """,
    impact="High bug risk, hard to test thoroughly, difficult to understand, error-prone changes",
    effort_hours=6.0,  # Average 6 hours to simplify complex method
    interest_rate=1.25,  # 25% harder as complexity increases
    detection_query="""
    -- Estimate complexity by counting control flow nodes
    -- This is a proxy for cyclomatic complexity
    SELECT
        m.name AS method_name,
        m.filename,
        m.line_number,
        (m.line_number_end - m.line_number + 1) AS method_length,
        (
            (LENGTH(m.code) - LENGTH(REPLACE(m.code, 'if', ''))) / 2 +
            (LENGTH(m.code) - LENGTH(REPLACE(m.code, 'for', ''))) / 3 +
            (LENGTH(m.code) - LENGTH(REPLACE(m.code, 'while', ''))) / 5 +
            (LENGTH(m.code) - LENGTH(REPLACE(m.code, 'case', ''))) / 4 +
            (LENGTH(m.code) - LENGTH(REPLACE(m.code, '&&', ''))) / 2 +
            (LENGTH(m.code) - LENGTH(REPLACE(m.code, '||', ''))) / 2
        ) AS estimated_complexity,
        CASE
            WHEN (
                (LENGTH(m.code) - LENGTH(REPLACE(m.code, 'if', ''))) / 2 +
                (LENGTH(m.code) - LENGTH(REPLACE(m.code, 'for', ''))) / 3
            ) > 20 THEN 'critical'
            WHEN (
                (LENGTH(m.code) - LENGTH(REPLACE(m.code, 'if', ''))) / 2 +
                (LENGTH(m.code) - LENGTH(REPLACE(m.code, 'for', ''))) / 3
            ) > 10 THEN 'high'
            ELSE 'medium'
        END AS severity,
        'High complexity' AS debt_type
    FROM nodes_method m
    WHERE m.code IS NOT NULL
      AND (
          (LENGTH(m.code) - LENGTH(REPLACE(m.code, 'if', ''))) / 2 +
          (LENGTH(m.code) - LENGTH(REPLACE(m.code, 'for', ''))) / 3
      ) > 10
    ORDER BY estimated_complexity DESC
    LIMIT 100;
    """,
    example="""
    // Complex method with high cyclomatic complexity
    int calculateDiscount(Order* order) {
        if (order->total > 1000) {
            if (order->customer->isPremium) {
                if (order->items > 10) {
                    return 25;
                } else if (order->items > 5) {
                    return 15;
                } else {
                    return 10;
                }
            } else if (order->customer->isReturning) {
                if (order->items > 10) {
                    return 20;
                } else {
                    return 10;
                }
            } else {
                return 5;
            }
        } else if (order->total > 500) {
            // ... more nested conditions ...
        }
        return 0;
    }
    """
)

# Pattern 6: Dead Code
DEAD_CODE = DebtPattern(
    pattern_id="DEAD_CODE",
    name="Dead Code (Unused Code)",
    description="Unused methods, variables, or code blocks that should be removed",
    category=DebtCategory.UNUSED_CODE,
    severity=DebtSeverity.LOW,
    symptoms=[
        "Methods never called",
        "Variables never read",
        "Commented-out code",
        "Unreachable code after return/break",
        "Orphaned files"
    ],
    remediation="""
    1. Verify code is truly unused (check all call sites)
    2. Remove unused methods and variables
    3. Delete commented-out code (use version control instead)
    4. Remove unreachable code blocks
    5. Delete orphaned files
    """,
    impact="Codebase bloat, confusion about what's active, maintenance burden, slower builds",
    effort_hours=1.0,  # Average 1 hour to remove dead code
    interest_rate=1.05,  # 5% harder as codebase grows
    detection_query="""
    -- Find methods that are never called
    -- (Methods with no incoming edges in call graph)
    SELECT DISTINCT
        m.name AS method_name,
        m.filename,
        m.line_number,
        (m.line_number_end - m.line_number + 1) AS method_length,
        'Unused method (no callers)' AS debt_type
    FROM nodes_method m
    WHERE m.id NOT IN (
        SELECT DISTINCT dst FROM edges_call
    )
    AND m.name NOT LIKE 'main%'  -- Exclude entry points
    AND m.name NOT LIKE 'test%'  -- Exclude test methods
    AND m.name NOT LIKE 'benchmark%'  -- Exclude benchmarks
    ORDER BY method_length DESC
    LIMIT 100;
    """,
    example="""
    // Dead code - never called
    void oldProcessingLogic() {
        // This was replaced by newProcessingLogic()
        // but never removed
        // ...
    }

    /*
    // Commented-out code that should be deleted
    void anotherOldFunction() {
        // Use version control to keep history!
    }
    */
    """
)


# ============================================================================
# PATTERN REGISTRY
# ============================================================================

# All available debt patterns
DEBT_PATTERNS: List[DebtPattern] = [
    TODO_FIXME_COMMENTS,
    DEPRECATED_API_USAGE,
    CODE_DUPLICATION,
    LONG_METHODS,
    COMPLEX_METHODS,
    DEAD_CODE
]

# Index by pattern ID
PATTERNS_BY_ID: Dict[str, DebtPattern] = {
    pattern.pattern_id: pattern
    for pattern in DEBT_PATTERNS
}

# Index by category
PATTERNS_BY_CATEGORY: Dict[str, List[DebtPattern]] = {
    'code_quality': [p for p in DEBT_PATTERNS if p.category == DebtCategory.CODE_QUALITY],
    'maintenance': [p for p in DEBT_PATTERNS if p.category == DebtCategory.MAINTENANCE],
    'complexity': [p for p in DEBT_PATTERNS if p.category == DebtCategory.COMPLEXITY],
    'unused_code': [p for p in DEBT_PATTERNS if p.category == DebtCategory.UNUSED_CODE]
}

# Index by severity
PATTERNS_BY_SEVERITY: Dict[str, List[DebtPattern]] = {
    'critical': [p for p in DEBT_PATTERNS if p.severity == DebtSeverity.CRITICAL],
    'high': [p for p in DEBT_PATTERNS if p.severity == DebtSeverity.HIGH],
    'medium': [p for p in DEBT_PATTERNS if p.severity == DebtSeverity.MEDIUM],
    'low': [p for p in DEBT_PATTERNS if p.severity == DebtSeverity.LOW]
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_pattern(pattern_id: str) -> Optional[DebtPattern]:
    """Get a pattern by its ID"""
    return PATTERNS_BY_ID.get(pattern_id)


def get_patterns_by_category(category: str) -> List[DebtPattern]:
    """Get all patterns in a category"""
    return PATTERNS_BY_CATEGORY.get(category, [])


def get_patterns_by_severity(severity: str) -> List[DebtPattern]:
    """Get all patterns with a specific severity"""
    return PATTERNS_BY_SEVERITY.get(severity, [])


def get_all_patterns() -> List[DebtPattern]:
    """Get all debt patterns"""
    return DEBT_PATTERNS.copy()


def calculate_total_effort(findings_count: Dict[str, int]) -> float:
    """
    Calculate total effort hours for all findings.

    Args:
        findings_count: Dict mapping pattern_id to count

    Returns:
        Total effort hours
    """
    total = 0.0
    for pattern_id, count in findings_count.items():
        pattern = get_pattern(pattern_id)
        if pattern:
            total += pattern.effort_hours * count
    return total


def calculate_debt_ratio(total_effort_hours: float, total_code_size: int) -> float:
    """
    Calculate debt ratio: effort / codebase size.

    Args:
        total_effort_hours: Total effort to fix all debt
        total_code_size: Total lines of code

    Returns:
        Debt ratio (0.0-1.0+)
    """
    if total_code_size == 0:
        return 0.0
    # Normalize: assume 1 hour per 100 lines is 100% debt
    return (total_effort_hours / (total_code_size / 100.0))


if __name__ == "__main__":
    print("Technical Debt Pattern Library")
    print("=" * 60)
    print(f"Total patterns: {len(DEBT_PATTERNS)}")
    print(f"\nBreakdown by category:")
    for category, patterns in PATTERNS_BY_CATEGORY.items():
        print(f"  {category}: {len(patterns)} patterns")

    print(f"\nBreakdown by severity:")
    for severity, patterns in PATTERNS_BY_SEVERITY.items():
        print(f"  {severity}: {len(patterns)} patterns")

    print(f"\nTotal base effort across all patterns:")
    total_effort = sum(p.effort_hours for p in DEBT_PATTERNS)
    print(f"  {total_effort:.1f} hours (per instance)")

    print(f"\nPattern validation:")
    for pattern in DEBT_PATTERNS:
        print(f"  - {pattern.pattern_id}: {pattern.name}")
