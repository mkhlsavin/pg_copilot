# Contributing Guide

How to contribute to CodeGraph.

## Development Setup

### Prerequisites

- Python 3.10+
- Git
- Conda/Miniconda
- NVIDIA GPU with CUDA (for testing)

### Setup

```bash
# Clone repository
git clone <repository-url>
cd codegraph

# Create development environment
conda create -n codegraph-dev python=3.11
conda activate codegraph-dev

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Project Structure

```
codegraph/
├── src/                    # Source code
│   ├── agents/            # Agent implementations
│   ├── retrieval/         # Retrieval components
│   ├── generation/        # Query generation
│   ├── workflow/          # Workflow orchestration
│   ├── domains/           # Domain plugins
│   ├── services/          # Core services
│   └── config/            # Configuration
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── benchmark/         # Benchmark tests
├── docs/                   # Documentation
├── examples/               # Example code
├── scripts/                # Utility scripts
└── config/                 # Configuration files
```

## Code Style

### Python Style

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use docstrings for public methods

```python
def find_methods(
    name: str,
    file_pattern: Optional[str] = None,
    max_results: int = 100
) -> List[Dict[str, Any]]:
    """
    Find methods by name.

    Args:
        name: Method name to search for
        file_pattern: Optional file pattern to filter
        max_results: Maximum number of results

    Returns:
        List of method dictionaries with name, file, line
    """
    pass
```

### Imports

Order imports as:
1. Standard library
2. Third-party packages
3. Local imports

```python
import os
from typing import Dict, List, Optional

import duckdb
from langchain_core.messages import HumanMessage

from src.config import CPGConfig
from src.services.cpg_query_service import CPGQueryService
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_hybrid_retriever.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Writing Tests

```python
import pytest
from src.agents.analyzer_agent import AnalyzerAgent

class TestAnalyzerAgent:
    """Tests for AnalyzerAgent."""

    @pytest.fixture
    def agent(self):
        """Create agent fixture."""
        return AnalyzerAgent()

    def test_analyze_simple_question(self, agent):
        """Test analysis of simple question."""
        result = agent.analyze("Find method CommitTransaction")

        assert result['intent'] == 'find_method'
        assert 'CommitTransaction' in result['keywords']

    def test_analyze_with_domain(self, agent):
        """Test domain extraction."""
        result = agent.analyze("How does transaction commit work?")

        assert result['domain'] == 'transaction-manager'
```

### Test Fixtures

Common fixtures in `tests/conftest.py`:

```python
@pytest.fixture
def mock_cpg_service():
    """Mock CPG service."""
    service = MagicMock()
    service.find_method.return_value = [
        {'name': 'CommitTransaction', 'file': 'xact.c'}
    ]
    return service

@pytest.fixture
def sample_state():
    """Sample workflow state."""
    return WorkflowState(
        question="Find callers of CommitTransaction",
        analysis={'intent': 'find_callers'}
    )
```

## Adding New Features

### Adding a New Agent

1. Create agent file in `src/agents/`:

```python
# src/agents/custom_agent.py

from typing import Dict, Optional
from src.config import CPGConfig, get_global_cpg_config

class CustomAgent:
    """Custom agent for specific analysis."""

    def __init__(self, cpg_config: Optional[CPGConfig] = None):
        self.cpg_config = cpg_config or get_global_cpg_config()

    def process(self, question: str, context: Dict) -> Dict:
        """Process question with custom logic."""
        # Implementation here
        return {'result': ...}
```

2. Add tests in `tests/unit/`:

```python
# tests/unit/test_custom_agent.py

class TestCustomAgent:
    def test_process_basic(self):
        agent = CustomAgent()
        result = agent.process("test", {})
        assert 'result' in result
```

3. Register in workflow if needed.

### Adding a New Scenario

1. Create scenario in `src/workflow/scenarios/`:

```python
# src/workflow/scenarios/custom_scenario.py

from src.workflow.scenarios import BaseScenario

class CustomScenario(BaseScenario):
    """Custom analysis scenario."""

    name = "custom"

    def run(self, question: str) -> Dict:
        state = self.create_initial_state(question)

        state = self.analyze(state)
        state = self.custom_process(state)
        state = self.interpret(state)

        return self.format_result(state)
```

2. Register in `src/workflow/scenarios/__init__.py`.

### Adding a New Domain Plugin

1. Create plugin directory:

```bash
mkdir -p src/domains/linux_kernel
```

2. Implement plugin:

```python
# src/domains/linux_kernel/plugin.py

from src.domains.base import DomainPlugin

class LinuxKernelDomainPlugin(DomainPlugin):
    @property
    def name(self) -> str:
        return "linux_kernel"

    @property
    def display_name(self) -> str:
        return "Linux Kernel 6.x"

    def get_memory_functions(self) -> Dict[str, List[str]]:
        return {
            'allocate': ['kmalloc', 'kzalloc', 'vmalloc'],
            'free': ['kfree', 'vfree']
        }

    def get_lock_functions(self) -> List[str]:
        return ['spin_lock', 'mutex_lock', 'rw_lock']
```

3. Register in `src/domains/__init__.py`.

## Documentation

### Docstrings

Use Google style docstrings:

```python
def function(arg1: str, arg2: int) -> Dict:
    """Short description.

    Longer description if needed.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Description of return value

    Raises:
        ValueError: If arg2 is negative

    Example:
        >>> result = function("test", 5)
        >>> print(result)
    """
```

### Updating Documentation

1. Update relevant docs in `docs/`
2. Add examples if applicable
3. Update README.md if public API changes

## Pull Request Process

1. **Create branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes** with tests

3. **Run checks**
   ```bash
   # Run tests
   pytest tests/ -v

   # Check formatting
   black --check src/ tests/

   # Check types
   mypy src/
   ```

4. **Commit**
   ```bash
   git add .
   git commit -m "feat: add my feature"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/my-feature
   ```

### Commit Messages

Follow conventional commits:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `test:` - Tests
- `refactor:` - Refactoring
- `chore:` - Maintenance

Examples:
```
feat: add hybrid retrieval to RetrieverAgent
fix: handle empty results in InterpreterAgent
docs: update API reference for new methods
test: add tests for domain plugin loading
```

## Code Review

### What We Look For

- Tests for new functionality
- Documentation for public APIs
- No breaking changes (or migration path)
- Performance considerations
- Error handling

### Review Checklist

- [ ] Tests pass
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Code follows style guide
- [ ] Commit messages are clear

## Release Process

1. Update version in `setup.py`
2. Update CHANGELOG.md
3. Create release branch
4. Run full test suite
5. Create GitHub release
6. Publish to PyPI (if applicable)

## Getting Help

- Open an issue for bugs
- Start a discussion for questions
- Join development chat (if available)

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
