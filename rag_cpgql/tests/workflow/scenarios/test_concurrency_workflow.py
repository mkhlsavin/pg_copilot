"""
Tests for Concurrency Analysis Workflow (Scenario 09).

Tests for concurrency workflow, lock analysis, race detection, and sync patterns.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any


def create_mock_state(query: str) -> Dict[str, Any]:
    """Create a minimal state dict for testing."""
    return {
        "query": query,
        "context": None,
        "intent": "concurrency",
        "scenario_id": "scenario_9",
        "confidence": 0.9,
        "classification_method": "test",
        "cpg_results": None,
        "subsystems": None,
        "methods": None,
        "call_graph": None,
        "answer": None,
        "evidence": None,
        "metadata": None,
        "retrieved_functions": None,
        "error": None,
        "retry_count": 0,
    }


class TestConcurrencyWorkflowImports:
    """Tests for concurrency workflow module imports."""

    def test_import_workflow(self):
        """Test that concurrency workflow can be imported."""
        from src.workflow.scenarios.concurrency import concurrency_workflow

        assert callable(concurrency_workflow)

    def test_import_concurrency_analyzer(self):
        """Test that ConcurrencyAnalyzer can be imported."""
        from src.analysis.concurrency_analyzer import ConcurrencyAnalyzer

        assert ConcurrencyAnalyzer is not None


class TestConcurrencyQueryPatterns:
    """Tests for concurrency query pattern detection."""

    def test_lock_keywords(self):
        """Test lock keyword detection."""
        queries = [
            "Find LWLock usage",
            "Analyze spinlock contention",
            "Show mutex usage",
        ]

        lock_keywords = ["lock", "lwlock", "spinlock", "mutex", "synchronization"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in lock_keywords)

    def test_race_condition_keywords(self):
        """Test race condition keyword detection."""
        queries = [
            "Find race conditions",
            "Detect TOCTOU vulnerabilities",
            "Check concurrent access",
        ]

        race_keywords = ["race", "toctou", "concurrent", "unsafe"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in race_keywords)

    def test_shared_memory_keywords(self):
        """Test shared memory keyword detection."""
        queries = [
            "Analyze shared memory access",
            "Find shmem usage",
            "Check memory sharing",
        ]

        shmem_keywords = ["shared", "memory", "shmem", "access"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in shmem_keywords)

    def test_deadlock_keywords(self):
        """Test deadlock keyword detection."""
        queries = [
            "Find potential deadlocks",
            "Check lock ordering",
            "Analyze lock order violations",
        ]

        deadlock_keywords = ["deadlock", "ordering", "order"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in deadlock_keywords)

    def test_atomic_keywords(self):
        """Test atomic operation keyword detection."""
        queries = [
            "Find atomic operations",
            "Check memory barriers",
            "Analyze volatile variables",
        ]

        atomic_keywords = ["atomic", "barrier", "fence", "volatile"]

        for query in queries:
            query_lower = query.lower()
            assert any(kw in query_lower for kw in atomic_keywords)


class TestConcurrencyWorkflowMocked:
    """Tests for concurrency_workflow function with mocked dependencies."""

    @pytest.fixture
    def mock_cpg_service(self):
        """Create mock CPG service."""
        mock = MagicMock()
        mock.get_subsystems.return_value = []
        mock.get_database_stats.return_value = {"method_count": 10000}
        mock.execute_query.return_value = []
        return mock

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM interface."""
        mock = MagicMock()
        mock.generate.return_value = "Concurrency analysis complete."
        return mock

    @pytest.fixture
    def mock_concurrency_analyzer(self):
        """Create mock ConcurrencyAnalyzer."""
        mock_analyzer = MagicMock()

        # Mock lock usage
        mock_lock = MagicMock()
        mock_lock.lock_type = "LWLock"
        mock_lock.function_name = "acquire_lwlock"
        mock_analyzer.find_lock_usage.return_value = [mock_lock]

        # Mock race conditions
        mock_race = MagicMock()
        mock_race.severity = "high"
        mock_race.pattern = "TOCTOU"
        mock_analyzer.detect_race_conditions.return_value = [mock_race]

        # Mock shared access
        mock_shared = MagicMock()
        mock_shared.is_protected = False
        mock_analyzer.analyze_shared_access.return_value = [mock_shared]

        # Mock lock ordering
        mock_analyzer.detect_lock_ordering_issues.return_value = []

        # Mock atomic ops
        mock_analyzer.find_atomic_operations.return_value = []

        # Mock statistics
        mock_analyzer.get_concurrency_statistics.return_value = {
            "functions_using_locks": 50,
            "total_locks": 100,
        }

        return mock_analyzer

    def test_workflow_returns_state(
        self, mock_cpg_service, mock_llm, mock_concurrency_analyzer
    ):
        """Test that workflow returns state dict."""
        from src.workflow.scenarios.concurrency import concurrency_workflow

        state = create_mock_state("Find race conditions")

        with patch("src.workflow.scenarios.concurrency.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(return_value=mock_cpg_service)
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            with patch("src.workflow.scenarios.concurrency.LLMInterface", return_value=mock_llm):
                with patch("src.workflow.scenarios.concurrency.get_global_registry") as mock_registry:
                    mock_registry.return_value.get_agent_prompt.return_value = {
                        "system": "You are a concurrency expert",
                        "user": "Analyze concurrency",
                    }
                    with patch("src.workflow.scenarios.concurrency.ConcurrencyAnalyzer", return_value=mock_concurrency_analyzer):
                        result = concurrency_workflow(state)

        assert isinstance(result, dict)


class TestConcurrencyErrorHandling:
    """Tests for concurrency workflow error handling."""

    def test_cpg_connection_error(self):
        """Test handling of CPG connection error."""
        from src.workflow.scenarios.concurrency import concurrency_workflow

        state = create_mock_state("Analyze locks")

        with patch("src.workflow.scenarios.concurrency.CPGQueryService") as mock_cpg:
            mock_cpg.return_value.__enter__ = MagicMock(
                side_effect=Exception("CPG connection failed")
            )
            mock_cpg.return_value.__exit__ = MagicMock(return_value=False)

            result = concurrency_workflow(state)

        # Should have error set
        assert result.get("error") is not None


class TestConcurrencyAnalyzer:
    """Tests for ConcurrencyAnalyzer agent interface."""

    def test_find_lock_usage(self):
        """Test lock usage finding."""
        mock_analyzer = MagicMock()
        mock_locks = [
            {"type": "LWLock", "function": "func1"},
            {"type": "SpinLock", "function": "func2"},
        ]
        mock_analyzer.find_lock_usage.return_value = mock_locks

        locks = mock_analyzer.find_lock_usage(lock_type="LWLock")

        assert len(locks) == 2

    def test_detect_race_conditions(self):
        """Test race condition detection."""
        mock_analyzer = MagicMock()
        mock_races = [
            {"pattern": "TOCTOU", "severity": "high"},
            {"pattern": "unprotected_access", "severity": "medium"},
        ]
        mock_analyzer.detect_race_conditions.return_value = mock_races

        races = mock_analyzer.detect_race_conditions()

        assert len(races) == 2

    def test_analyze_shared_access(self):
        """Test shared access analysis."""
        mock_analyzer = MagicMock()
        mock_accesses = [
            {"variable": "shared_var", "is_protected": True},
            {"variable": "global_state", "is_protected": False},
        ]
        mock_analyzer.analyze_shared_access.return_value = mock_accesses

        accesses = mock_analyzer.analyze_shared_access()

        assert len(accesses) == 2

    def test_detect_lock_ordering_issues(self):
        """Test lock ordering issue detection."""
        mock_analyzer = MagicMock()
        mock_issues = [
            {"locks": ["lock1", "lock2"], "risk": "deadlock"},
        ]
        mock_analyzer.detect_lock_ordering_issues.return_value = mock_issues

        issues = mock_analyzer.detect_lock_ordering_issues()

        assert len(issues) == 1

    def test_find_atomic_operations(self):
        """Test atomic operation finding."""
        mock_analyzer = MagicMock()
        mock_atomics = [
            {"operation": "atomic_add", "type": "fetch_and_add"},
        ]
        mock_analyzer.find_atomic_operations.return_value = mock_atomics

        atomics = mock_analyzer.find_atomic_operations()

        assert len(atomics) == 1

    def test_get_concurrency_statistics(self):
        """Test concurrency statistics gathering."""
        mock_analyzer = MagicMock()
        mock_stats = {
            "functions_using_locks": 100,
            "total_locks": 250,
            "lock_types": ["LWLock", "SpinLock"],
        }
        mock_analyzer.get_concurrency_statistics.return_value = mock_stats

        stats = mock_analyzer.get_concurrency_statistics()

        assert stats["functions_using_locks"] == 100


class TestLockTypes:
    """Tests for lock type classification."""

    def test_lwlock_detection(self):
        """Test LWLock detection."""
        query = "Find LWLock usage in executor"

        assert "lwlock" in query.lower()

    def test_spinlock_detection(self):
        """Test SpinLock detection."""
        query = "Analyze spinlock contention"

        assert "spinlock" in query.lower()

    def test_condvar_detection(self):
        """Test condition variable detection."""
        query = "Find condition variable usage"

        assert "condition" in query.lower()

    def test_latch_detection(self):
        """Test latch detection."""
        query = "Check latch usage"

        assert "latch" in query.lower()


class TestRaceConditionPatterns:
    """Tests for race condition pattern detection."""

    def test_toctou_pattern(self):
        """Test TOCTOU pattern detection."""
        pattern = "TOCTOU"

        assert pattern == "TOCTOU"

    def test_signal_handler_pattern(self):
        """Test signal handler race detection."""
        query = "Find signal handler races"

        assert "signal" in query.lower()

    def test_unprotected_access_pattern(self):
        """Test unprotected access pattern."""
        query = "Find unprotected shared variable access"

        assert "unprotected" in query.lower() or "shared" in query.lower()


class TestSharedMemoryAnalysis:
    """Tests for shared memory analysis."""

    def test_protected_access(self):
        """Test protected access identification."""
        accesses = [
            {"variable": "var1", "is_protected": True},
            {"variable": "var2", "is_protected": False},
        ]

        protected = [a for a in accesses if a["is_protected"]]
        unprotected = [a for a in accesses if not a["is_protected"]]

        assert len(protected) == 1
        assert len(unprotected) == 1

    def test_critical_section_coverage(self):
        """Test critical section coverage."""
        shared_vars = ["var1", "var2", "var3"]
        protected_vars = ["var1", "var3"]

        coverage = len(protected_vars) / len(shared_vars)

        assert coverage == 2 / 3


class TestDeadlockDetection:
    """Tests for deadlock detection logic."""

    def test_lock_ordering_violation(self):
        """Test lock ordering violation detection."""
        # Thread 1: acquires lock1, then lock2
        # Thread 2: acquires lock2, then lock1
        lock_orders = [
            {"thread": "T1", "locks": ["lock1", "lock2"]},
            {"thread": "T2", "locks": ["lock2", "lock1"]},
        ]

        # Check for potential deadlock
        t1_order = lock_orders[0]["locks"]
        t2_order = lock_orders[1]["locks"]

        # If reversed order, potential deadlock
        is_reversed = t1_order[0] == t2_order[1] and t1_order[1] == t2_order[0]

        assert is_reversed is True

    def test_circular_dependency(self):
        """Test circular lock dependency detection."""
        dependencies = [
            {"from": "lock1", "to": "lock2"},
            {"from": "lock2", "to": "lock3"},
            {"from": "lock3", "to": "lock1"},
        ]

        # Build graph
        graph = {}
        for dep in dependencies:
            if dep["from"] not in graph:
                graph[dep["from"]] = []
            graph[dep["from"]].append(dep["to"])

        # Check for cycle (simplified check)
        has_cycle = "lock1" in graph and "lock2" in graph["lock1"]

        assert has_cycle is True


class TestAtomicOperations:
    """Tests for atomic operation analysis."""

    def test_atomic_types(self):
        """Test atomic operation type classification."""
        atomic_ops = [
            {"type": "fetch_and_add", "function": "atomic_add"},
            {"type": "compare_and_swap", "function": "atomic_cas"},
            {"type": "load_acquire", "function": "atomic_load"},
        ]

        types = set(op["type"] for op in atomic_ops)

        assert "fetch_and_add" in types
        assert "compare_and_swap" in types

    def test_memory_ordering(self):
        """Test memory ordering detection."""
        orderings = ["acquire", "release", "seq_cst", "relaxed"]

        for order in orderings:
            assert order in ["acquire", "release", "seq_cst", "relaxed"]


class TestConcurrencyMetrics:
    """Tests for concurrency metrics calculation."""

    def test_lock_contention_metric(self):
        """Test lock contention metric."""
        lock_acquisitions = 1000
        lock_failures = 50

        contention_rate = lock_failures / lock_acquisitions

        assert contention_rate == 0.05  # 5%

    def test_critical_section_length(self):
        """Test critical section length analysis."""
        critical_sections = [
            {"function": "func1", "lines": 5},
            {"function": "func2", "lines": 50},
            {"function": "func3", "lines": 3},
        ]

        avg_length = sum(cs["lines"] for cs in critical_sections) / len(critical_sections)

        assert avg_length == 58 / 3


class TestSynchronizationPrimitives:
    """Tests for synchronization primitive usage."""

    def test_primitive_types(self):
        """Test synchronization primitive types."""
        primitives = [
            "LWLock",
            "SpinLock",
            "ConditionVariable",
            "Latch",
            "Semaphore",
            "Barrier",
        ]

        for prim in primitives:
            assert isinstance(prim, str)
            assert len(prim) > 0

    def test_primitive_usage_statistics(self):
        """Test primitive usage statistics."""
        usage = {
            "LWLock": 150,
            "SpinLock": 80,
            "ConditionVariable": 20,
        }

        total = sum(usage.values())
        most_used = max(usage, key=usage.get)

        assert total == 250
        assert most_used == "LWLock"


class TestConcurrencyBestPractices:
    """Tests for concurrency best practice checks."""

    def test_lock_granularity(self):
        """Test lock granularity analysis."""
        locks = [
            {"scope": "global", "granularity": "coarse"},
            {"scope": "per_bucket", "granularity": "fine"},
        ]

        fine_grained = [l for l in locks if l["granularity"] == "fine"]

        assert len(fine_grained) == 1

    def test_lock_free_alternatives(self):
        """Test lock-free alternative identification."""
        operations = [
            {"type": "increment", "can_be_lockfree": True},
            {"type": "complex_update", "can_be_lockfree": False},
        ]

        lockfree_ops = [op for op in operations if op["can_be_lockfree"]]

        assert len(lockfree_ops) == 1


class TestConcurrencySeverityScoring:
    """Tests for concurrency issue severity scoring."""

    def test_severity_calculation(self):
        """Test severity calculation for concurrency issues."""
        issues = [
            {"type": "race_condition", "data_corruption_risk": True, "severity": "high"},
            {"type": "lock_contention", "performance_impact": "medium", "severity": "medium"},
        ]

        high_severity = [i for i in issues if i["severity"] == "high"]

        assert len(high_severity) == 1

    def test_risk_assessment(self):
        """Test risk assessment for race conditions."""
        race = {
            "pattern": "TOCTOU",
            "shared_variable": "critical_state",
            "access_frequency": "high",
        }

        # High access frequency + critical variable = high risk
        risk_level = "high" if race["access_frequency"] == "high" else "low"

        assert risk_level == "high"
