"""
Tests for Statistics Repository.

Tests for StatsRepository with mocked database sessions.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


class MockResult:
    """Mock database result."""

    def __init__(self, value=None, rows=None):
        self._value = value
        self._rows = rows or []

    def scalar(self):
        return self._value

    def all(self):
        return self._rows


class MockRow:
    """Mock database row."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockJobStatus:
    """Mock JobStatus enum."""

    PENDING = MagicMock(value="pending")
    RUNNING = MagicMock(value="running")
    COMPLETED = MagicMock(value="completed")
    FAILED = MagicMock(value="failed")


class TestStatsRepositoryInit:
    """Tests for StatsRepository initialization."""

    def test_init_with_session(self):
        """Test initialization with session."""
        from src.api.database.repositories.stats_repo import StatsRepository

        mock_session = MagicMock()
        repo = StatsRepository(mock_session)

        assert repo.db is mock_session


class TestUserStatistics:
    """Tests for user statistics methods."""

    @pytest.fixture
    def repo(self):
        """Create StatsRepository with mock session."""
        from src.api.database.repositories.stats_repo import StatsRepository

        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        return StatsRepository(mock_session)

    @pytest.mark.asyncio
    async def test_count_users(self, repo):
        """Test counting total users."""
        repo.db.execute.return_value = MockResult(value=42)

        count = await repo.count_users()

        assert count == 42
        repo.db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_users_active_only(self, repo):
        """Test counting only active users."""
        repo.db.execute.return_value = MockResult(value=30)

        count = await repo.count_users(active_only=True)

        assert count == 30

    @pytest.mark.asyncio
    async def test_count_users_all(self, repo):
        """Test counting all users including inactive."""
        repo.db.execute.return_value = MockResult(value=50)

        count = await repo.count_users(active_only=False)

        assert count == 50

    @pytest.mark.asyncio
    async def test_count_users_none_result(self, repo):
        """Test count_users with None result."""
        repo.db.execute.return_value = MockResult(value=None)

        count = await repo.count_users()

        assert count == 0

    @pytest.mark.asyncio
    async def test_count_active_users(self, repo):
        """Test counting active users in time window."""
        repo.db.execute.return_value = MockResult(value=15)

        count = await repo.count_active_users(hours=24)

        assert count == 15

    @pytest.mark.asyncio
    async def test_count_active_users_custom_hours(self, repo):
        """Test counting with custom hours parameter."""
        repo.db.execute.return_value = MockResult(value=5)

        count = await repo.count_active_users(hours=1)

        assert count == 5

    @pytest.mark.asyncio
    async def test_count_new_users(self, repo):
        """Test counting new users."""
        repo.db.execute.return_value = MockResult(value=8)

        count = await repo.count_new_users(days=7)

        assert count == 8

    @pytest.mark.asyncio
    async def test_count_new_users_custom_days(self, repo):
        """Test counting new users with custom days."""
        repo.db.execute.return_value = MockResult(value=3)

        count = await repo.count_new_users(days=30)

        assert count == 3


class TestSessionStatistics:
    """Tests for session statistics methods."""

    @pytest.fixture
    def repo(self):
        """Create StatsRepository with mock session."""
        from src.api.database.repositories.stats_repo import StatsRepository

        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        return StatsRepository(mock_session)

    @pytest.mark.asyncio
    async def test_count_sessions(self, repo):
        """Test counting total sessions."""
        repo.db.execute.return_value = MockResult(value=100)

        count = await repo.count_sessions()

        assert count == 100

    @pytest.mark.asyncio
    async def test_count_sessions_none_result(self, repo):
        """Test count_sessions with None result."""
        repo.db.execute.return_value = MockResult(value=None)

        count = await repo.count_sessions()

        assert count == 0

    @pytest.mark.asyncio
    async def test_count_active_sessions(self, repo):
        """Test counting active sessions."""
        repo.db.execute.return_value = MockResult(value=25)

        count = await repo.count_active_sessions(hours=1)

        assert count == 25

    @pytest.mark.asyncio
    async def test_count_active_sessions_custom_hours(self, repo):
        """Test counting with custom hours."""
        repo.db.execute.return_value = MockResult(value=10)

        count = await repo.count_active_sessions(hours=6)

        assert count == 10


class TestJobStatistics:
    """Tests for job statistics methods."""

    @pytest.fixture
    def repo(self):
        """Create StatsRepository with mock session."""
        from src.api.database.repositories.stats_repo import StatsRepository

        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        return StatsRepository(mock_session)

    @pytest.mark.asyncio
    async def test_count_jobs_by_status(self, repo):
        """Test counting jobs grouped by status."""
        rows = [
            MockRow(status=MockJobStatus.PENDING, count=5),
            MockRow(status=MockJobStatus.RUNNING, count=3),
            MockRow(status=MockJobStatus.COMPLETED, count=42),
        ]
        repo.db.execute.return_value = MockResult(rows=rows)

        result = await repo.count_jobs_by_status()

        assert result["pending"] == 5
        assert result["running"] == 3
        assert result["completed"] == 42

    @pytest.mark.asyncio
    async def test_count_jobs_by_status_empty(self, repo):
        """Test counting jobs when none exist."""
        repo.db.execute.return_value = MockResult(rows=[])

        result = await repo.count_jobs_by_status()

        assert result == {}

    @pytest.mark.asyncio
    async def test_count_active_jobs(self, repo):
        """Test counting active (pending/running) jobs."""
        repo.db.execute.return_value = MockResult(value=8)

        count = await repo.count_active_jobs()

        assert count == 8

    @pytest.mark.asyncio
    async def test_count_active_jobs_none(self, repo):
        """Test count_active_jobs with None result."""
        repo.db.execute.return_value = MockResult(value=None)

        count = await repo.count_active_jobs()

        assert count == 0


class TestScenarioStatistics:
    """Tests for scenario statistics methods."""

    @pytest.fixture
    def repo(self):
        """Create StatsRepository with mock session."""
        from src.api.database.repositories.stats_repo import StatsRepository

        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        return StatsRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_scenario_usage(self, repo):
        """Test getting scenario usage counts."""
        rows = [
            MockRow(scenario_id="security", count=100),
            MockRow(scenario_id="performance", count=50),
            MockRow(scenario_id="debugging", count=30),
        ]
        repo.db.execute.return_value = MockResult(rows=rows)

        result = await repo.get_scenario_usage()

        assert result["security"] == 100
        assert result["performance"] == 50
        assert result["debugging"] == 30

    @pytest.mark.asyncio
    async def test_get_scenario_usage_empty(self, repo):
        """Test scenario usage with no data."""
        repo.db.execute.return_value = MockResult(rows=[])

        result = await repo.get_scenario_usage()

        assert result == {}

    @pytest.mark.asyncio
    async def test_get_scenario_usage_period(self, repo):
        """Test getting scenario usage for period."""
        rows = [
            MockRow(scenario_id="refactoring", count=20),
        ]
        repo.db.execute.return_value = MockResult(rows=rows)

        result = await repo.get_scenario_usage_period(days=30)

        assert result["refactoring"] == 20

    @pytest.mark.asyncio
    async def test_get_scenario_usage_period_custom_days(self, repo):
        """Test period with custom days."""
        rows = [
            MockRow(scenario_id="architecture", count=5),
        ]
        repo.db.execute.return_value = MockResult(rows=rows)

        result = await repo.get_scenario_usage_period(days=7)

        assert result["architecture"] == 5


class TestDialogueStatistics:
    """Tests for dialogue statistics methods."""

    @pytest.fixture
    def repo(self):
        """Create StatsRepository with mock session."""
        from src.api.database.repositories.stats_repo import StatsRepository

        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        return StatsRepository(mock_session)

    @pytest.mark.asyncio
    async def test_count_total_turns(self, repo):
        """Test counting total dialogue turns."""
        repo.db.execute.return_value = MockResult(value=1000)

        count = await repo.count_total_turns()

        assert count == 1000

    @pytest.mark.asyncio
    async def test_count_total_turns_none(self, repo):
        """Test count_total_turns with None result."""
        repo.db.execute.return_value = MockResult(value=None)

        count = await repo.count_total_turns()

        assert count == 0

    @pytest.mark.asyncio
    async def test_count_turns_period(self, repo):
        """Test counting turns in period."""
        repo.db.execute.return_value = MockResult(value=150)

        count = await repo.count_turns_period(days=1)

        assert count == 150

    @pytest.mark.asyncio
    async def test_count_turns_period_custom_days(self, repo):
        """Test period with custom days."""
        repo.db.execute.return_value = MockResult(value=500)

        count = await repo.count_turns_period(days=7)

        assert count == 500


class TestCombinedMetrics:
    """Tests for combined metrics methods."""

    @pytest.fixture
    def repo(self):
        """Create StatsRepository with mock session."""
        from src.api.database.repositories.stats_repo import StatsRepository

        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        return StatsRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_system_metrics(self, repo):
        """Test getting system metrics."""
        # Mock the individual methods
        repo.db.execute.side_effect = [
            MockResult(value=1000),  # count_total_turns
            MockResult(value=25),  # count_active_sessions
            MockResult(value=5),  # count_active_jobs
            MockResult(rows=[MockRow(scenario_id="security", count=100)]),  # get_scenario_usage
        ]

        metrics = await repo.get_system_metrics()

        assert metrics["total_requests"] == 1000
        assert metrics["active_sessions"] == 25
        assert metrics["active_jobs"] == 5
        assert "scenarios_usage" in metrics
        assert metrics["cache_hit_rate"] == 0.0  # Not instrumented
        assert metrics["avg_response_time_ms"] == 0.0  # Not instrumented

    @pytest.mark.asyncio
    async def test_get_user_statistics(self, repo):
        """Test getting user statistics."""
        repo.db.execute.side_effect = [
            MockResult(value=100),  # count_users (total)
            MockResult(value=50),  # count_active_users (24h)
            MockResult(value=80),  # count_active_users (7d)
            MockResult(value=10),  # count_new_users
        ]

        stats = await repo.get_user_statistics()

        assert stats["total_users"] == 100
        assert stats["active_users_24h"] == 50
        assert stats["active_users_7d"] == 80
        assert stats["new_users_7d"] == 10

    @pytest.mark.asyncio
    async def test_get_scenario_statistics(self, repo):
        """Test getting scenario statistics."""
        rows_all = [MockRow(scenario_id="security", count=200)]
        rows_30d = [MockRow(scenario_id="security", count=100)]
        rows_7d = [MockRow(scenario_id="security", count=30)]

        repo.db.execute.side_effect = [
            MockResult(rows=rows_all),  # get_scenario_usage (all time)
            MockResult(rows=rows_30d),  # get_scenario_usage_period (30d)
            MockResult(rows=rows_7d),  # get_scenario_usage_period (7d)
            MockResult(value=500),  # count_total_turns
        ]

        stats = await repo.get_scenario_statistics()

        assert "scenarios" in stats
        assert stats["scenarios"]["all_time"]["security"] == 200
        assert stats["scenarios"]["last_30_days"]["security"] == 100
        assert stats["scenarios"]["last_7_days"]["security"] == 30
        assert stats["total_queries"] == 500


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def repo(self):
        """Create StatsRepository with mock session."""
        from src.api.database.repositories.stats_repo import StatsRepository

        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        return StatsRepository(mock_session)

    @pytest.mark.asyncio
    async def test_all_counts_return_zero_on_none(self, repo):
        """Test that all count methods return 0 for None."""
        repo.db.execute.return_value = MockResult(value=None)

        assert await repo.count_users() == 0
        assert await repo.count_active_users() == 0
        assert await repo.count_new_users() == 0
        assert await repo.count_sessions() == 0
        assert await repo.count_active_sessions() == 0
        assert await repo.count_active_jobs() == 0
        assert await repo.count_total_turns() == 0
        assert await repo.count_turns_period() == 0

    @pytest.mark.asyncio
    async def test_empty_usage_returns_empty_dict(self, repo):
        """Test that usage methods return empty dict for no data."""
        repo.db.execute.return_value = MockResult(rows=[])

        assert await repo.get_scenario_usage() == {}
        assert await repo.count_jobs_by_status() == {}
        assert await repo.get_scenario_usage_period() == {}


class TestTimeWindowCalculations:
    """Tests for time window calculations."""

    @pytest.fixture
    def repo(self):
        """Create StatsRepository with mock session."""
        from src.api.database.repositories.stats_repo import StatsRepository

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=MockResult(value=0))
        return StatsRepository(mock_session)

    @pytest.mark.asyncio
    async def test_active_users_uses_hours(self, repo):
        """Test that active users uses hours for cutoff."""
        await repo.count_active_users(hours=48)

        # Just verify it was called (time calculation is internal)
        repo.db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_new_users_uses_days(self, repo):
        """Test that new users uses days for cutoff."""
        await repo.count_new_users(days=14)

        repo.db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_turns_period_uses_days(self, repo):
        """Test that turns period uses days for cutoff."""
        await repo.count_turns_period(days=90)

        repo.db.execute.assert_called_once()
