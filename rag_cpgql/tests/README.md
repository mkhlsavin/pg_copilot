# CodeGraph Test Suite

Comprehensive test suite for the CodeGraph code analysis system.

## Test Statistics

- **Total Test Files:** ~78
- **Total Test Functions:** ~2,000+
- **Test Classes:** ~600+
- **Async Tests:** 350+

## Directory Structure

```
tests/
├── api/                    # FastAPI endpoint tests
│   ├── conftest.py         # API test fixtures (auth, db, clients)
│   ├── test_auth.py        # Authentication endpoints
│   ├── test_chat.py        # Chat message endpoints
│   ├── test_demo.py        # Demo endpoints
│   ├── test_health.py      # Health check endpoints
│   ├── test_history.py     # Chat history endpoints
│   ├── test_import.py      # Project import endpoints
│   ├── test_projects.py    # Project management endpoints
│   ├── test_query.py       # Query execution endpoints
│   ├── test_review.py      # Code review endpoints
│   ├── test_scenarios.py   # Scenario management endpoints
│   ├── test_sessions.py    # Session management endpoints
│   ├── test_stats.py       # Statistics endpoints
│   └── test_websocket.py   # WebSocket endpoints
│
├── database/               # Database repository tests
│   ├── conftest.py         # Database test fixtures
│   ├── test_api_key_repo.py
│   ├── test_session_repo.py
│   ├── test_stats_repo.py
│   └── test_user_repo.py
│
├── integration/            # Integration workflow tests
│   ├── test_all_scenarios_real_cpg.py
│   ├── test_phase2_enhancements.py
│   ├── test_phase3_deep_integration.py
│   ├── test_phase4a_workflow_integration.py
│   └── test_phase4c_sanitization_detection.py
│
├── llm/                    # LLM provider tests
│   ├── test_factory.py
│   ├── test_gigachat_provider.py
│   └── test_openai_provider.py
│
├── security/               # Security component tests
│   ├── test_dlp_scanner.py
│   ├── test_secure_llm.py
│   ├── test_siem_integration.py
│   └── test_taint_scanner.py
│
├── services/               # Service layer tests
│   ├── test_chat_service.py
│   ├── test_cpg_query_service.py
│   └── test_review_service.py
│
├── tui/                    # Terminal UI tests
│   ├── test_config_editor.py
│   ├── test_help_panel.py
│   ├── test_query_executor.py
│   ├── test_repl.py
│   └── test_stats_display.py
│
├── unit/                   # Unit tests for core components
│   ├── test_benchmark_metrics.py
│   ├── test_domain_plugins.py
│   ├── test_duckdb_client.py
│   ├── test_feedback_loop.py
│   ├── test_gigachat_provider.py
│   ├── test_hybrid_retriever.py
│   ├── test_incremental_exporter.py
│   ├── test_llm_reranking.py
│   ├── test_local_provider.py
│   ├── test_monitoring.py
│   ├── test_phase4c_unit.py
│   ├── test_query_cache.py
│   ├── test_query_handlers.py
│   ├── test_result_ranker_cross_source.py
│   ├── test_security_agents.py
│   ├── test_vector_embeddings.py
│   └── test_workflow_state.py
│
├── workflow/               # Workflow and scenario tests
│   └── scenarios/
│       ├── test_architecture_workflow.py
│       ├── test_code_review_workflow.py
│       ├── test_compliance_workflow.py
│       ├── test_concurrency_workflow.py
│       ├── test_cross_repo_workflow.py
│       ├── test_debugging_workflow.py
│       ├── test_documentation_workflow.py
│       ├── test_feature_dev_workflow.py
│       ├── test_onboarding_workflow.py
│       ├── test_performance_workflow.py
│       ├── test_refactoring_workflow.py
│       ├── test_security_workflow.py
│       ├── test_tech_debt_workflow.py
│       └── test_test_coverage_workflow.py
│
├── benchmark/              # Benchmark evaluation utilities
│
└── Root test files:        # Specialized integration tests
    ├── test_call_graph_analyzer.py     # Call graph analysis
    ├── test_dataflow_tracer.py         # Data flow tracing
    ├── test_intent_classifier.py       # Intent classification
    ├── test_multi_scenario_integration.py  # Multi-scenario tests
    ├── test_p0_fixes.py                # Critical P0 fixes
    ├── test_patch_review_system.py     # Patch review system
    ├── test_phase2_integration.py      # Phase 2 integration
    ├── test_prompt_registry.py         # Prompt management
    └── test_ragas_integration.py       # RAGAS evaluation
```

## Running Tests

### Run All Tests

```bash
# Run all tests with verbose output
pytest tests/ -v

# Run with short traceback
pytest tests/ -v --tb=short

# Run with coverage
pytest tests/ -v --cov=src --cov-report=html
```

### Run Specific Test Categories

```bash
# API endpoint tests
pytest tests/api/ -v

# Database repository tests
pytest tests/database/ -v

# Unit tests
pytest tests/unit/ -v

# Workflow scenario tests
pytest tests/workflow/ -v

# Security tests
pytest tests/security/ -v

# Integration tests
pytest tests/integration/ -v

# LLM provider tests
pytest tests/llm/ -v

# TUI tests
pytest tests/tui/ -v

# Service layer tests
pytest tests/services/ -v
```

### Run Specific Test Files

```bash
# Run a specific test file
pytest tests/api/test_auth.py -v

# Run a specific test class
pytest tests/api/test_auth.py::TestLoginEndpoint -v

# Run a specific test function
pytest tests/api/test_auth.py::TestLoginEndpoint::test_login_success -v
```

### Run Tests by Marker

```bash
# Run async tests only
pytest tests/ -v -m asyncio

# Run slow tests
pytest tests/ -v -m slow

# Skip slow tests
pytest tests/ -v -m "not slow"
```

## Test Fixtures

### API Test Fixtures (`tests/api/conftest.py`)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `test_engine` | session | SQLAlchemy async test engine |
| `test_session` | function | Database session for tests |
| `test_db` | function | Dependency-injected DB session |
| `app` | function | Test FastAPI application |
| `client` | function | Synchronous TestClient |
| `async_client` | function | AsyncClient for async tests |
| `test_user` | function | Regular user fixture |
| `admin_user` | function | Admin user fixture |
| `auth_headers` | function | JWT auth headers for test_user |
| `admin_auth_headers` | function | JWT auth headers for admin |
| `api_prefix` | session | API version prefix constant |

### Database Test Fixtures (`tests/database/conftest.py`)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `db_session` | function | Database session |
| `test_user` | function | Test user for DB tests |

## Testing Patterns

### Async Testing

Most tests use `pytest-asyncio` for async test support:

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result == expected
```

### Mocking

Tests use `unittest.mock` for mocking dependencies:

```python
from unittest.mock import Mock, patch, AsyncMock

@patch('src.module.dependency')
def test_with_mock(mock_dep):
    mock_dep.return_value = expected_value
    # Test code here
```

### Database Testing

Tests use in-memory SQLite for fast database testing:

```python
# Connection string for tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
```

### API Testing

Tests use FastAPI's TestClient:

```python
def test_endpoint(client, auth_headers):
    response = client.get("/api/v1/endpoint", headers=auth_headers)
    assert response.status_code == 200
```

## Test Categories

### 1. Unit Tests (`tests/unit/`)
Test individual components in isolation with mocked dependencies.

### 2. API Tests (`tests/api/`)
Test FastAPI endpoints with request/response validation.

### 3. Service Tests (`tests/services/`)
Test business logic in service layer.

### 4. Integration Tests (`tests/integration/`)
Test multi-component workflows and features.

### 5. Workflow Tests (`tests/workflow/scenarios/`)
Test complete analysis scenarios (security, performance, etc.).

### 6. Database Tests (`tests/database/`)
Test repository layer and database operations.

### 7. Security Tests (`tests/security/`)
Test security components (DLP, taint analysis, SIEM).

### 8. LLM Tests (`tests/llm/`)
Test LLM provider integrations.

### 9. TUI Tests (`tests/tui/`)
Test terminal user interface components.

## Naming Conventions

- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test functions: `test_<description>`
- Fixtures: `<resource>_fixture` or descriptive name

## Writing New Tests

### 1. Choose the right directory

- Unit tests: `tests/unit/`
- API endpoint tests: `tests/api/`
- Service tests: `tests/services/`
- Integration tests: `tests/integration/`
- Workflow scenarios: `tests/workflow/scenarios/`

### 2. Use appropriate fixtures

Import fixtures from conftest.py files.

### 3. Follow existing patterns

Look at similar test files for patterns.

### 4. Test edge cases

Include tests for:
- Success cases
- Error cases
- Edge cases
- Invalid input
- Authentication/authorization

## Troubleshooting

### Database Connection Errors

Ensure DATABASE_URL is set for tests that need real database:

```bash
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/test_db"
```

### Import Errors

Run tests from project root:

```bash
cd codegraph
pytest tests/ -v
```

### Async Test Issues

Ensure `pytest-asyncio` is installed:

```bash
pip install pytest-asyncio
```

## Coverage

Generate coverage report:

```bash
# HTML report
pytest tests/ --cov=src --cov-report=html

# Terminal report
pytest tests/ --cov=src --cov-report=term-missing

# XML report (for CI)
pytest tests/ --cov=src --cov-report=xml
```

Coverage report will be generated in `htmlcov/` directory.

## CI/CD Integration

Tests are designed to run in CI pipelines:

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run tests with JUnit XML output
pytest tests/ --junitxml=test-results.xml -v

# Run with coverage for SonarQube
pytest tests/ --cov=src --cov-report=xml
```

## Maintenance

### Last Updated
December 2025

### Test Suite Health
- All imports verified
- No broken dependencies
- Duplicate tests removed
- Documentation up to date
