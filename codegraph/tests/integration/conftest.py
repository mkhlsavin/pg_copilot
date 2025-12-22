"""
Integration Tests Configuration.

Provides skipif markers and fixtures for integration tests
that require external services and environment variables.
"""

import os
import pytest
from pathlib import Path


# =============================================================================
# Environment Variable Checks
# =============================================================================

def _has_llm_credentials() -> bool:
    """Check if any LLM credentials are available."""
    return any([
        os.getenv('GIGACHAT_AUTH_KEY'),
        os.getenv('GIGACHAT_CREDENTIALS'),
        os.getenv('YANDEX_API_KEY'),
    ])


def _has_cpg_database() -> bool:
    """Check if CPG database file exists."""
    project_root = Path(__file__).parent.parent.parent
    cpg_paths = [
        project_root / 'cpg.duckdb',
        project_root / 'data' / 'cpg.duckdb',
        Path(os.getenv('CPG_DATABASE_PATH', '')),
    ]
    return any(p.exists() for p in cpg_paths if p)


# =============================================================================
# Skip Conditions
# =============================================================================

requires_llm = pytest.mark.skipif(
    not _has_llm_credentials(),
    reason="LLM credentials not configured (GIGACHAT_AUTH_KEY, GIGACHAT_CREDENTIALS, or YANDEX_API_KEY required)"
)

requires_cpg = pytest.mark.skipif(
    not _has_cpg_database(),
    reason="CPG database not available (cpg.duckdb required)"
)

requires_integration = pytest.mark.skipif(
    not (_has_llm_credentials() and _has_cpg_database()),
    reason="Full integration environment not available (requires LLM credentials and CPG database)"
)


# =============================================================================
# Auto-Skip Mechanism (Module-Level)
# =============================================================================

def pytest_collection_modifyitems(config, items):
    """
    Automatically mark integration tests with skipif conditions.

    Tests in the integration folder that import MultiScenarioCopilot
    or other integration components will be skipped if the environment
    is not properly configured.
    """
    integration_dir = Path(__file__).parent

    for item in items:
        # Only process tests in the integration directory
        item_path = Path(item.fspath)
        if integration_dir not in item_path.parents and item_path.parent != integration_dir:
            continue

        # Skip tests that require full integration environment
        # unless the marker is already applied
        if not any(mark.name in ('skipif', 'skip') for mark in item.iter_markers()):
            if not _has_llm_credentials():
                item.add_marker(pytest.mark.skip(
                    reason="Skipping integration test: LLM credentials not configured"
                ))
            elif not _has_cpg_database():
                item.add_marker(pytest.mark.skip(
                    reason="Skipping integration test: CPG database not available"
                ))
