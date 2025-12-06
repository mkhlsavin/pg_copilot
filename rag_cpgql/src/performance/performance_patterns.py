"""
Performance Bottleneck Pattern Library

Week 7, Task 1: Performance Patterns
Phase 2: Quality & Security Enhancement

Defines performance bottleneck patterns with CPG queries for detection.
Based on common performance anti-patterns and optimization opportunities.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any


# ============================================================================
# ENUMS
# ============================================================================

class BottleneckSeverity(Enum):
    """Severity levels for performance bottlenecks"""
    CRITICAL = "critical"  # Severe performance impact (>10x slowdown)
    HIGH = "high"          # Significant impact (5-10x slowdown)
    MEDIUM = "medium"      # Moderate impact (2-5x slowdown)
    LOW = "low"            # Minor impact (<2x slowdown)
    INFO = "info"          # Potential optimization opportunity


class BottleneckCategory(Enum):
    """Categories of performance bottlenecks"""
    ALGORITHMIC = "algorithmic"        # Algorithm complexity issues
    MEMORY = "memory"                  # Memory usage and allocation
    IO = "io"                          # I/O operations
    CONCURRENCY = "concurrency"        # Threading/locking issues
    DATABASE = "database"              # Database query issues
    NETWORK = "network"                # Network operations
    RESOURCE_LEAK = "resource_leak"    # Resource management


# ============================================================================
# PERFORMANCE PATTERN DEFINITION
# ============================================================================

@dataclass
class PerformancePattern:
    """Defines a performance bottleneck pattern"""
    id: str
    name: str
    category: BottleneckCategory
    severity: BottleneckSeverity
    description: str
    cpgql_query: str
    symptoms: List[str]
    optimization_technique: str
    example_before: str
    example_after: str
    potential_speedup: str  # e.g., "5-10x", "O(n^2) to O(n)"


# ============================================================================
# PATTERN DEFINITIONS
# ============================================================================

# Pattern 1: Nested Loops with High Complexity
NESTED_LOOPS_PATTERN = PerformancePattern(
    id="NESTED_LOOPS_001",
    name="Nested Loops / N² Complexity",
    category=BottleneckCategory.ALGORITHMIC,
    severity=BottleneckSeverity.HIGH,
    description=(
        "Methods with deeply nested loops can cause O(n²) or worse complexity. "
        "Each additional loop level multiplies execution time. Common in sorting, "
        "searching, and matrix operations that haven't been optimized."
    ),
    cpgql_query="""
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.filename,
            m.line_number,
            m.line_number,
            (m.line_number_end - m.line_number),
            'NESTED_LOOPS' AS bottleneck_type,
            'HIGH' AS severity
        FROM nodes_method m
        WHERE m.line_number > 20
          AND (m.line_number_end - m.line_number) > 30
          AND m.name NOT LIKE 'test_%'
        ORDER BY m.line_number DESC
        LIMIT 50;
    """,
    symptoms=[
        "High cyclomatic complexity (>20)",
        "Execution time grows quadratically with input size",
        "CPU usage spikes with larger datasets"
    ],
    optimization_technique=(
        "1. Use hash tables for O(1) lookups instead of nested searches\n"
        "2. Sort data once and use binary search (O(n log n) vs O(n²))\n"
        "3. Cache intermediate results to avoid recomputation\n"
        "4. Consider vectorization or parallel processing\n"
        "5. Use more efficient algorithms (e.g., merge sort vs bubble sort)"
    ),
    example_before="""
// O(n²) complexity
for (int i = 0; i < n; i++) {
    for (int j = 0; j < n; j++) {
        if (array1[i] == array2[j]) {
            count++;
        }
    }
}""",
    example_after="""
// O(n) complexity using hash set
HashSet<int> set = new HashSet<int>(array2);
for (int i = 0; i < n; i++) {
    if (set.contains(array1[i])) {
        count++;
    }
}""",
    potential_speedup="O(n²) to O(n) - up to 100x for large datasets"
)

# Pattern 2: Expensive Operations in Loops
EXPENSIVE_LOOP_OPERATIONS_PATTERN = PerformancePattern(
    id="EXPENSIVE_LOOP_OPS_001",
    name="Expensive Operations in Loops",
    category=BottleneckCategory.ALGORITHMIC,
    severity=BottleneckSeverity.CRITICAL,
    description=(
        "Performing expensive operations (I/O, database queries, network calls) "
        "inside loops multiplies their cost by the loop iteration count. Common "
        "in N+1 query problems and inefficient data fetching."
    ),
    cpgql_query="""
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.filename,
            m.line_number,
            COUNT(DISTINCT nc.name) AS call_count,
            'EXPENSIVE_LOOP_OPS' AS bottleneck_type,
            'CRITICAL' AS severity
        FROM nodes_method m
        JOIN edges_call ec ON ec.src = m.id
        JOIN nodes_call nc ON ec.dst = nc.id
        WHERE (nc.name LIKE '%query%'
            OR nc.name LIKE '%execute%'
            OR nc.name LIKE '%fetch%'
            OR nc.name LIKE '%read%'
            OR nc.name LIKE '%write%')
          AND m.line_number > 5
          AND m.name NOT LIKE 'test_%'
        GROUP BY m.id, m.name, m.filename, m.line_number
        HAVING COUNT(DISTINCT nc.name) > 3
        ORDER BY call_count DESC
        LIMIT 50;
    """,
    symptoms=[
        "Linear increase in I/O operations with data size (N+1 problem)",
        "Database connection pool exhaustion",
        "Slow response times that scale with input size"
    ],
    optimization_technique=(
        "1. Batch operations - fetch/update all at once\n"
        "2. Use bulk queries instead of individual queries\n"
        "3. Implement caching for repeated reads\n"
        "4. Move I/O outside loop when possible\n"
        "5. Use async/parallel operations for independent calls"
    ),
    example_before="""
// N+1 query problem
for (User user : users) {
    Profile profile = db.query("SELECT * FROM profiles WHERE user_id = ?", user.id);
    processProfile(profile);
}""",
    example_after="""
// Single batch query
List<Integer> userIds = users.stream().map(u -> u.id).collect(Collectors.toList());
Map<Integer, Profile> profiles = db.batchQuery("SELECT * FROM profiles WHERE user_id IN (?)", userIds);
for (User user : users) {
    processProfile(profiles.get(user.id));
}""",
    potential_speedup="N queries to 1 query - up to 100x for large N"
)

# Pattern 3: Excessive Memory Allocation
EXCESSIVE_ALLOCATION_PATTERN = PerformancePattern(
    id="EXCESSIVE_ALLOC_001",
    name="Excessive Memory Allocation",
    category=BottleneckCategory.MEMORY,
    severity=BottleneckSeverity.HIGH,
    description=(
        "Creating many temporary objects in tight loops causes garbage collection "
        "pressure and memory fragmentation. Common with string concatenation, "
        "repeated list creation, and unnecessary object instantiation."
    ),
    cpgql_query="""
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.filename,
            m.line_number,
            m.line_number,
            'EXCESSIVE_ALLOC' AS bottleneck_type,
            'HIGH' AS severity
        FROM nodes_method m
        WHERE (m.name LIKE '%string%'
            OR m.name LIKE '%concat%'
            OR m.name LIKE '%append%'
            OR m.name LIKE '%build%')
          AND m.line_number > 8
          AND (m.line_number_end - m.line_number) > 20
          AND m.name NOT LIKE 'test_%'
        ORDER BY m.line_number DESC
        LIMIT 50;
    """,
    symptoms=[
        "High GC frequency and pause times",
        "Memory usage spikes during execution",
        "String concatenation in loops"
    ],
    optimization_technique=(
        "1. Use StringBuilder for string concatenation in loops\n"
        "2. Reuse objects and buffers when possible\n"
        "3. Use object pools for frequently created objects\n"
        "4. Pre-allocate collections with expected capacity\n"
        "5. Use primitive types instead of boxed types"
    ),
    example_before="""
// Creates N temporary String objects
String result = "";
for (String item : items) {
    result = result + item + ",";  // New String each iteration
}""",
    example_after="""
// Single StringBuilder, minimal allocations
StringBuilder sb = new StringBuilder(items.size() * 10);
for (String item : items) {
    sb.append(item).append(",");
}
String result = sb.toString();""",
    potential_speedup="O(n²) string operations to O(n) - up to 50x"
)

# Pattern 4: Large Result Sets
LARGE_RESULT_SET_PATTERN = PerformancePattern(
    id="LARGE_RESULT_SET_001",
    name="Large Result Set Loading",
    category=BottleneckCategory.DATABASE,
    severity=BottleneckSeverity.HIGH,
    description=(
        "Loading large result sets into memory at once causes memory pressure "
        "and slow response times. Common when fetching all rows without pagination "
        "or streaming."
    ),
    cpgql_query="""
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.filename,
            m.line_number,
            'LARGE_RESULT_SET' AS bottleneck_type,
            'HIGH' AS severity
        FROM nodes_method m
        JOIN edges_call ec ON ec.src = m.id
        JOIN nodes_call nc ON ec.dst = nc.id
        WHERE nc.name LIKE '%fetch%all%'
           OR nc.name LIKE '%get%all%'
           OR nc.name LIKE '%load%all%'
           OR nc.name LIKE '%select%'
          AND m.name NOT LIKE 'test_%'
        ORDER BY (m.line_number_end - m.line_number) DESC
        LIMIT 50;
    """,
    symptoms=[
        "Memory usage proportional to dataset size",
        "Long response times for first result",
        "Out of memory errors with large datasets"
    ],
    optimization_technique=(
        "1. Implement pagination (LIMIT/OFFSET)\n"
        "2. Use streaming/cursor-based iteration\n"
        "3. Fetch only required columns (not SELECT *)\n"
        "4. Add indexes for filtered columns\n"
        "5. Consider result set size limits"
    ),
    example_before="""
// Loads all rows into memory
List<Row> rows = db.query("SELECT * FROM large_table");
for (Row row : rows) {
    process(row);
}""",
    example_after="""
// Streams rows one at a time
try (ResultCursor cursor = db.queryCursor("SELECT * FROM large_table")) {
    while (cursor.hasNext()) {
        Row row = cursor.next();
        process(row);
    }
}""",
    potential_speedup="Constant memory vs O(n) - handles datasets 100x larger"
)

# Pattern 5: Deep Recursion
DEEP_RECURSION_PATTERN = PerformancePattern(
    id="DEEP_RECURSION_001",
    name="Deep Recursion / Stack Overflow Risk",
    category=BottleneckCategory.ALGORITHMIC,
    severity=BottleneckSeverity.MEDIUM,
    description=(
        "Deep or unbounded recursion can cause stack overflow and poor performance "
        "due to function call overhead. Common in tree traversal, graph algorithms, "
        "and recursive parsing without tail call optimization."
    ),
    cpgql_query="""
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.filename,
            m.line_number,
            COUNT(*) AS recursive_call_count,
            'DEEP_RECURSION' AS bottleneck_type,
            'MEDIUM' AS severity
        FROM nodes_method m
        JOIN edges_call ec ON ec.src = m.id
        JOIN nodes_method m_callee ON ec.dst = m_callee.id
        WHERE m_callee.name = m.name  -- Recursive call
          AND m.name NOT LIKE 'test_%'
        GROUP BY m.id, m.name, m.filename, m.line_number
        HAVING COUNT(*) > 0
        ORDER BY recursive_call_count DESC
        LIMIT 50;
    """,
    symptoms=[
        "Stack overflow errors with large inputs",
        "Function call overhead visible in profiling",
        "Exponential time complexity without memoization"
    ],
    optimization_technique=(
        "1. Convert to iterative approach with explicit stack\n"
        "2. Add memoization/caching for repeated subproblems\n"
        "3. Use tail recursion if language supports optimization\n"
        "4. Implement depth limits to prevent overflow\n"
        "5. Consider dynamic programming for overlapping subproblems"
    ),
    example_before="""
// Exponential time O(2^n) without memoization
int fibonacci(int n) {
    if (n <= 1) return n;
    return fibonacci(n-1) + fibonacci(n-2);
}""",
    example_after="""
// Linear time O(n) with memoization
Map<Integer, Integer> memo = new HashMap<>();
int fibonacci(int n) {
    if (n <= 1) return n;
    if (memo.containsKey(n)) return memo.get(n);
    int result = fibonacci(n-1) + fibonacci(n-2);
    memo.put(n, result);
    return result;
}""",
    potential_speedup="O(2^n) to O(n) - exponential improvement"
)

# Pattern 6: Inefficient Data Structures
INEFFICIENT_DATA_STRUCTURE_PATTERN = PerformancePattern(
    id="INEFFICIENT_DS_001",
    name="Inefficient Data Structure Usage",
    category=BottleneckCategory.ALGORITHMIC,
    severity=BottleneckSeverity.MEDIUM,
    description=(
        "Using inappropriate data structures leads to poor algorithmic complexity. "
        "Common examples: linear search in lists instead of hash lookups, "
        "ArrayList for frequent insertions/deletions, or no indexing in databases."
    ),
    cpgql_query="""
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.filename,
            m.line_number,
            m.line_number,
            'INEFFICIENT_DS' AS bottleneck_type,
            'MEDIUM' AS severity
        FROM nodes_method m
        JOIN edges_call ec ON ec.src = m.id
        JOIN nodes_call nc ON ec.dst = nc.id
        WHERE (nc.name LIKE '%contains%'
            OR nc.name LIKE '%find%'
            OR nc.name LIKE '%search%'
            OR nc.name LIKE '%index_of%')
          AND m.line_number > 5
          AND m.name NOT LIKE 'test_%'
        GROUP BY m.id, m.name, m.filename, m.line_number
        HAVING COUNT(*) > 3
        ORDER BY m.line_number DESC
        LIMIT 50;
    """,
    symptoms=[
        "Linear search operations (O(n) lookups)",
        "Frequent insertions/deletions in arrays",
        "Missing database indexes"
    ],
    optimization_technique=(
        "1. Use HashMap/HashSet for O(1) lookups instead of List\n"
        "2. Use LinkedList for frequent insertions/deletions\n"
        "3. Use TreeMap/TreeSet for sorted data\n"
        "4. Add database indexes for frequently queried columns\n"
        "5. Use specialized structures (Trie, Bloom filter) when appropriate"
    ),
    example_before="""
// O(n) lookup in list
List<User> users = getAllUsers();
for (Request req : requests) {
    User user = users.stream()
        .filter(u -> u.id == req.userId)
        .findFirst().orElse(null);
}""",
    example_after="""
// O(1) lookup in map
Map<Integer, User> userMap = getAllUsers().stream()
    .collect(Collectors.toMap(u -> u.id, u -> u));
for (Request req : requests) {
    User user = userMap.get(req.userId);
}""",
    potential_speedup="O(n) to O(1) lookups - up to 100x for large datasets"
)

# Pattern 7: N+1 Query Problem (Phase 5 Enhancement)
N_PLUS_ONE_QUERY_PATTERN = PerformancePattern(
    id="N_PLUS_ONE_001",
    name="N+1 Query Problem",
    category=BottleneckCategory.DATABASE,
    severity=BottleneckSeverity.CRITICAL,
    description=(
        "The N+1 query problem occurs when code executes 1 query to fetch N items, "
        "then N additional queries to fetch related data for each item. This multiplies "
        "database round trips and severely impacts performance. Common in ORM usage "
        "without proper eager loading or query optimization."
    ),
    cpgql_query="""
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.filename,
            m.line_number,
            COUNT(DISTINCT nc.name) AS db_call_count,
            'N_PLUS_ONE' AS bottleneck_type,
            'CRITICAL' AS severity
        FROM nodes_method m
        JOIN edges_call ec ON ec.src = m.id
        JOIN nodes_call nc ON ec.dst = nc.id
        WHERE (nc.name LIKE '%query%'
            OR nc.name LIKE '%select%'
            OR nc.name LIKE '%fetch%'
            OR nc.name LIKE '%find%'
            OR nc.name LIKE '%get%')
          AND m.line_number > 3
          AND m.code LIKE '%for%'
          AND m.name NOT LIKE 'test_%'
        GROUP BY m.id, m.name, m.filename, m.line_number
        HAVING COUNT(DISTINCT nc.name) >= 2
        ORDER BY db_call_count DESC
        LIMIT 50;
    """,
    symptoms=[
        "Number of queries grows linearly with dataset size",
        "Database connection pool exhaustion under load",
        "Response time proportional to number of items processed",
        "High database server CPU from query parsing overhead"
    ],
    optimization_technique=(
        "1. Use eager loading (JOIN FETCH in ORM, includes in ActiveRecord)\n"
        "2. Implement batch loading with single IN query\n"
        "3. Use DataLoader pattern for GraphQL\n"
        "4. Add query result caching for repeated accesses\n"
        "5. Profile queries with query logging to identify patterns"
    ),
    example_before="""
// N+1: 1 query + N queries
orders = db.query("SELECT * FROM orders WHERE user_id = ?", userId);
for (Order order : orders) {
    // Executes query for EACH order
    items = db.query("SELECT * FROM items WHERE order_id = ?", order.id);
    order.setItems(items);
}""",
    example_after="""
// 2 queries total: much more efficient
orders = db.query("SELECT * FROM orders WHERE user_id = ?", userId);
orderIds = orders.stream().map(o -> o.id).collect(toList());
// Single batch query
allItems = db.query("SELECT * FROM items WHERE order_id IN (?)", orderIds);
Map<Integer, List<Item>> itemsByOrder = allItems.stream()
    .collect(groupingBy(i -> i.orderId));
for (Order order : orders) {
    order.setItems(itemsByOrder.get(order.id));
}""",
    potential_speedup="N+1 queries to 2 queries - up to 50x reduction in DB round trips"
)

# Pattern 8: Missing Database Indexes (Phase 5 Enhancement)
MISSING_INDEX_PATTERN = PerformancePattern(
    id="MISSING_INDEX_001",
    name="Missing Database Indexes",
    category=BottleneckCategory.DATABASE,
    severity=BottleneckSeverity.HIGH,
    description=(
        "Queries without proper indexes perform full table scans, causing linear "
        "performance degradation as tables grow. Common in WHERE clauses, JOIN "
        "conditions, and ORDER BY clauses on unindexed columns."
    ),
    cpgql_query="""
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.filename,
            m.line_number,
            COUNT(*) AS query_count,
            'MISSING_INDEX' AS bottleneck_type,
            'HIGH' AS severity
        FROM nodes_method m
        JOIN edges_call ec ON ec.src = m.id
        JOIN nodes_call nc ON ec.dst = nc.id
        WHERE (nc.name LIKE '%query%'
            OR nc.name LIKE '%execute%'
            OR nc.name LIKE '%select%')
          AND (m.code LIKE '%WHERE%'
            OR m.code LIKE '%JOIN%'
            OR m.code LIKE '%ORDER BY%')
          AND m.name NOT LIKE 'test_%'
        GROUP BY m.id, m.name, m.filename, m.line_number
        HAVING COUNT(*) > 0
        ORDER BY query_count DESC
        LIMIT 50;
    """,
    symptoms=[
        "Slow query performance on large tables",
        "Query time increases linearly with table size",
        "High disk I/O from full table scans",
        "EXPLAIN shows 'table scan' instead of 'index scan'"
    ],
    optimization_technique=(
        "1. Add indexes on WHERE clause columns\n"
        "2. Create composite indexes for multi-column queries\n"
        "3. Index foreign keys for JOIN operations\n"
        "4. Add covering indexes to avoid table lookups\n"
        "5. Use EXPLAIN ANALYZE to identify missing indexes"
    ),
    example_before="""
// Slow: full table scan on users table
SELECT * FROM users WHERE email = 'user@example.com';
// Table scan gets slower as users table grows

// Slow: no index on join column
SELECT o.* FROM orders o
JOIN users u ON o.user_id = u.id
WHERE u.email = 'user@example.com';""",
    example_after="""
// Fast: uses index on email column
CREATE INDEX idx_users_email ON users(email);
SELECT * FROM users WHERE email = 'user@example.com';
// O(log n) lookup instead of O(n) scan

// Fast: indexes on both join columns
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_users_email ON users(email);
SELECT o.* FROM orders o
JOIN users u ON o.user_id = u.id
WHERE u.email = 'user@example.com';""",
    potential_speedup="O(n) to O(log n) - up to 1000x for large tables"
)

# Pattern 9: Synchronous I/O in Loops (Phase 5 Enhancement)
SYNC_IO_IN_LOOPS_PATTERN = PerformancePattern(
    id="SYNC_IO_LOOP_001",
    name="Synchronous I/O in Loops",
    category=BottleneckCategory.IO,
    severity=BottleneckSeverity.CRITICAL,
    description=(
        "Performing blocking I/O operations (file reads, network calls, database queries) "
        "sequentially in loops wastes time waiting for each operation to complete. Total "
        "time equals sum of all I/O latencies. Async or parallel I/O can reduce this to "
        "the maximum latency instead of the sum."
    ),
    cpgql_query="""
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.filename,
            m.line_number,
            COUNT(DISTINCT nc.name) AS io_call_count,
            'SYNC_IO_LOOP' AS bottleneck_type,
            'CRITICAL' AS severity
        FROM nodes_method m
        JOIN edges_call ec ON ec.src = m.id
        JOIN nodes_call nc ON ec.dst = nc.id
        WHERE (nc.name LIKE '%read%'
            OR nc.name LIKE '%write%'
            OR nc.name LIKE '%fetch%'
            OR nc.name LIKE '%request%'
            OR nc.name LIKE '%download%'
            OR nc.name LIKE '%upload%')
          AND m.code LIKE '%for%'
          AND m.code NOT LIKE '%async%'
          AND m.code NOT LIKE '%await%'
          AND m.name NOT LIKE 'test_%'
        GROUP BY m.id, m.name, m.filename, m.line_number
        HAVING COUNT(DISTINCT nc.name) >= 2
        ORDER BY io_call_count DESC
        LIMIT 50;
    """,
    symptoms=[
        "Response time equals sum of all I/O latencies",
        "Low CPU usage while waiting for I/O",
        "Thread blocking visible in profiling",
        "Poor scalability with number of items"
    ],
    optimization_technique=(
        "1. Use async/await for concurrent I/O operations\n"
        "2. Implement parallel processing with thread pools\n"
        "3. Batch API requests when possible\n"
        "4. Use streaming for large files instead of full read/write\n"
        "5. Implement connection pooling to reuse connections"
    ),
    example_before="""
// Sequential: total time = sum of all request times
List<User> users = new ArrayList<>();
for (String userId : userIds) {
    // Blocks for ~100ms per request
    User user = httpClient.get("/api/users/" + userId);
    users.add(user);
}
// Total time for 10 users: ~1000ms""",
    example_after="""
// Parallel: total time = max request time
List<CompletableFuture<User>> futures = new ArrayList<>();
for (String userId : userIds) {
    futures.add(CompletableFuture.supplyAsync(() ->
        httpClient.get("/api/users/" + userId)
    ));
}
List<User> users = futures.stream()
    .map(CompletableFuture::join)
    .collect(toList());
// Total time for 10 users: ~100ms (10x faster)""",
    potential_speedup="Sequential to parallel - up to Nx speedup (N = number of items)"
)

# Pattern 10: String Concatenation in Loops (Phase 5 Enhancement)
STRING_CONCAT_IN_LOOPS_PATTERN = PerformancePattern(
    id="STRING_CONCAT_LOOP_001",
    name="String Concatenation in Loops",
    category=BottleneckCategory.MEMORY,
    severity=BottleneckSeverity.HIGH,
    description=(
        "String concatenation using + operator in loops creates O(n²) complexity because "
        "strings are immutable. Each concatenation allocates a new string and copies all "
        "previous characters. With N iterations, this results in N*(N+1)/2 character copies."
    ),
    cpgql_query="""
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.filename,
            m.line_number,
            (m.line_number_end - m.line_number),
            'STRING_CONCAT_LOOP' AS bottleneck_type,
            'HIGH' AS severity
        FROM nodes_method m
        WHERE (m.code LIKE '%+%'
            OR m.code LIKE '%concat%'
            OR m.code LIKE '%append%')
          AND m.code LIKE '%for%'
          AND m.code LIKE '%String%'
          AND m.line_number > 2
          AND m.name NOT LIKE 'test_%'
        ORDER BY (m.line_number_end - m.line_number) DESC
        LIMIT 50;
    """,
    symptoms=[
        "Quadratic performance degradation with string length",
        "High memory allocation rate",
        "Frequent garbage collection",
        "Profiler shows time in string allocation"
    ],
    optimization_technique=(
        "1. Use StringBuilder (Java) or StringBuffer (thread-safe)\n"
        "2. Use string.join() for simple concatenations\n"
        "3. Pre-allocate buffer with estimated capacity\n"
        "4. Use StringWriter for text generation\n"
        "5. Consider streaming output instead of building large strings"
    ),
    example_before="""
// O(n²) complexity: creates n temporary strings
String result = "";
for (int i = 0; i < items.size(); i++) {
    result = result + items.get(i) + ",";  // New string allocation
}
// For 1000 items: ~500,000 character copies""",
    example_after="""
// O(n) complexity: single buffer
StringBuilder sb = new StringBuilder(items.size() * 20);
for (int i = 0; i < items.size(); i++) {
    sb.append(items.get(i)).append(",");
}
String result = sb.toString();
// For 1000 items: ~20,000 character copies (25x fewer)""",
    potential_speedup="O(n²) to O(n) - up to 100x for large strings"
)

# Pattern 11: Unbounded Queries (Phase 5 Enhancement)
UNBOUNDED_QUERY_PATTERN = PerformancePattern(
    id="UNBOUNDED_QUERY_001",
    name="Unbounded Database Queries",
    category=BottleneckCategory.DATABASE,
    severity=BottleneckSeverity.HIGH,
    description=(
        "Queries without LIMIT clauses can return millions of rows, causing memory "
        "exhaustion, slow response times, and database overload. Common in reporting "
        "queries, admin panels, and data exports without pagination."
    ),
    cpgql_query="""
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.filename,
            m.line_number,
            'UNBOUNDED_QUERY' AS bottleneck_type,
            'HIGH' AS severity
        FROM nodes_method m
        WHERE (m.code LIKE '%SELECT%'
            OR m.code LIKE '%query%'
            OR m.code LIKE '%fetch%all%')
          AND m.code NOT LIKE '%LIMIT%'
          AND m.code NOT LIKE '%limit%'
          AND m.code NOT LIKE '%take%'
          AND m.code NOT LIKE '%first%'
          AND m.name NOT LIKE 'test_%'
        ORDER BY (m.line_number_end - m.line_number) DESC
        LIMIT 50;
    """,
    symptoms=[
        "Memory usage proportional to table size",
        "Unpredictable response times",
        "OutOfMemory errors on large datasets",
        "Database server memory pressure"
    ],
    optimization_technique=(
        "1. Add LIMIT clause with reasonable default (e.g., 100, 1000)\n"
        "2. Implement pagination (OFFSET/LIMIT or cursor-based)\n"
        "3. Use streaming for large result sets\n"
        "4. Add explicit row count limits at application level\n"
        "5. Monitor query result set sizes in production"
    ),
    example_before="""
// Dangerous: could return millions of rows
List<Order> orders = db.query(
    "SELECT * FROM orders WHERE status = 'pending'"
);
// Memory usage: unbounded, could cause OOM

// Could overwhelm client and database
for (Order order : orders) {
    processOrder(order);
}""",
    example_after="""
// Safe: bounded result set with pagination
int pageSize = 100;
int offset = 0;
List<Order> batch;
do {
    batch = db.query(
        "SELECT * FROM orders WHERE status = 'pending' " +
        "LIMIT ? OFFSET ?",
        pageSize, offset
    );
    for (Order order : batch) {
        processOrder(order);
    }
    offset += pageSize;
} while (batch.size() == pageSize);
// Memory usage: O(pageSize) instead of O(total rows)""",
    potential_speedup="Unbounded to bounded memory - enables processing datasets 1000x larger"
)

# Pattern 12: Lock Contention (Phase 5 Enhancement)
LOCK_CONTENTION_PATTERN = PerformancePattern(
    id="LOCK_CONTENTION_001",
    name="Lock Contention / Synchronization Bottleneck",
    category=BottleneckCategory.CONCURRENCY,
    severity=BottleneckSeverity.CRITICAL,
    description=(
        "Excessive synchronization or lock contention causes threads to wait, reducing "
        "parallelism and throughput. Common with coarse-grained locks, synchronized "
        "methods on shared objects, or database row-level locks under high concurrency."
    ),
    cpgql_query="""
        SELECT DISTINCT
            m.id,
            m.name AS method_name,
            m.filename,
            m.line_number,
            'LOCK_CONTENTION' AS bottleneck_type,
            'CRITICAL' AS severity
        FROM nodes_method m
        WHERE (m.code LIKE '%synchronized%'
            OR m.code LIKE '%lock%'
            OR m.code LIKE '%Lock%'
            OR m.code LIKE '%mutex%'
            OR m.code LIKE '%Semaphore%')
          AND (m.line_number_end - m.line_number) > 20
          AND m.name NOT LIKE 'test_%'
        ORDER BY (m.line_number_end - m.line_number) DESC
        LIMIT 50;
    """,
    symptoms=[
        "Low CPU utilization despite many threads",
        "Thread dumps show many BLOCKED threads",
        "Throughput doesn't scale with thread count",
        "Profiler shows time spent waiting for locks"
    ],
    optimization_technique=(
        "1. Use fine-grained locks instead of coarse-grained\n"
        "2. Replace locks with lock-free data structures (ConcurrentHashMap)\n"
        "3. Use read-write locks when appropriate\n"
        "4. Minimize critical section size (hold locks for less time)\n"
        "5. Use thread-local storage or immutable objects to avoid locking"
    ),
    example_before="""
// Coarse-grained lock: serializes all operations
public class Cache {
    private synchronized Object get(String key) {
        return map.get(key);  // Blocks all other threads
    }

    private synchronized void put(String key, Object value) {
        map.put(key, value);  // Blocks all other threads
    }
}
// Throughput: limited to single-threaded performance""",
    example_after="""
// Lock-free concurrent data structure
public class Cache {
    private final ConcurrentHashMap<String, Object> map = new ConcurrentHashMap<>();

    public Object get(String key) {
        return map.get(key);  // No lock contention
    }

    public void put(String key, Object value) {
        map.put(key, value);  // Lock-free for most operations
    }
}
// Throughput: scales with CPU cores""",
    potential_speedup="Single-threaded to multi-threaded - up to Nx speedup (N = CPU cores)"
)

# ============================================================================
# PATTERN COLLECTION
# ============================================================================

PERFORMANCE_PATTERNS: Dict[str, PerformancePattern] = {
    # Original 6 patterns (Phase 2)
    "NESTED_LOOPS": NESTED_LOOPS_PATTERN,
    "EXPENSIVE_LOOP_OPS": EXPENSIVE_LOOP_OPERATIONS_PATTERN,
    "EXCESSIVE_ALLOC": EXCESSIVE_ALLOCATION_PATTERN,
    "LARGE_RESULT_SET": LARGE_RESULT_SET_PATTERN,
    "DEEP_RECURSION": DEEP_RECURSION_PATTERN,
    "INEFFICIENT_DS": INEFFICIENT_DATA_STRUCTURE_PATTERN,
    # New 6 patterns (Phase 5 Enhancement)
    "N_PLUS_ONE": N_PLUS_ONE_QUERY_PATTERN,
    "MISSING_INDEX": MISSING_INDEX_PATTERN,
    "SYNC_IO_LOOP": SYNC_IO_IN_LOOPS_PATTERN,
    "STRING_CONCAT_LOOP": STRING_CONCAT_IN_LOOPS_PATTERN,
    "UNBOUNDED_QUERY": UNBOUNDED_QUERY_PATTERN,
    "LOCK_CONTENTION": LOCK_CONTENTION_PATTERN,
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_pattern_by_id(pattern_id: str) -> PerformancePattern:
    """Get pattern by ID"""
    for pattern in PERFORMANCE_PATTERNS.values():
        if pattern.id == pattern_id:
            return pattern
    raise ValueError(f"Pattern not found: {pattern_id}")


def get_patterns_by_category(category: BottleneckCategory) -> List[PerformancePattern]:
    """Get all patterns in a category"""
    return [p for p in PERFORMANCE_PATTERNS.values() if p.category == category]


def get_patterns_by_severity(severity: BottleneckSeverity) -> List[PerformancePattern]:
    """Get all patterns with given severity"""
    return [p for p in PERFORMANCE_PATTERNS.values() if p.severity == severity]


def get_critical_patterns() -> List[PerformancePattern]:
    """Get all critical performance patterns"""
    return get_patterns_by_severity(BottleneckSeverity.CRITICAL)


def get_all_cpgql_queries() -> Dict[str, str]:
    """Get all CPGQL queries for batch execution"""
    return {name: pattern.cpgql_query for name, pattern in PERFORMANCE_PATTERNS.items()}


def get_pattern_summary() -> str:
    """Get summary of all patterns"""
    lines = ["Performance Bottleneck Patterns:\n"]
    for name, pattern in PERFORMANCE_PATTERNS.items():
        lines.append(
            f"- {pattern.name} ({pattern.severity.value.upper()}, "
            f"{pattern.category.value}): {pattern.potential_speedup}"
        )
    return "\n".join(lines)


def validate_pattern(pattern: PerformancePattern) -> List[str]:
    """Validate a pattern has all required fields"""
    errors = []
    if not pattern.id:
        errors.append("Missing pattern ID")
    if not pattern.cpgql_query:
        errors.append("Missing CPGQL query")
    if not pattern.optimization_technique:
        errors.append("Missing optimization technique")
    return errors


def validate_all_patterns() -> Dict[str, List[str]]:
    """Validate all patterns"""
    validation_results = {}
    for name, pattern in PERFORMANCE_PATTERNS.items():
        errors = validate_pattern(pattern)
        if errors:
            validation_results[name] = errors
    return validation_results
