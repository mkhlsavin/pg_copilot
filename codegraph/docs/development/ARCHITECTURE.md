# CodeGraph Architecture

This document describes the modular architecture of the CodeGraph Copilot system.

## Overview

The system is organized into several key modules:

```
src/
├── domains/           # Domain Plugin System
│   ├── base.py        # Abstract base class for domain plugins
│   ├── registry.py    # Domain registration and activation
│   ├── generic_cpp.py # Generic C/C++ domain plugin
│   └── postgresql/    # PostgreSQL-specific plugin
├── workflow/          # LangGraph Workflow System
│   ├── multi_scenario_workflow.py  # Main workflow orchestrator
│   ├── state.py                    # State definitions (TypedDicts)
│   ├── query_handlers.py           # Query detection and handling
│   └── scenarios/                  # Individual scenario workflows
└── ...
```

## Domain Plugin System

The domain plugin system allows the copilot to support multiple codebases (PostgreSQL, Linux Kernel, generic C/C++, etc.) through a unified interface.

### Key Components

#### DomainPlugin (Abstract Base Class)
- Location: `src/domains/base.py`
- Defines the interface all domain plugins must implement:
  - `name`: Unique identifier (e.g., "generic_cpp")
  - `display_name`: Human-readable name (e.g., "C/C++")
  - `subsystems`: Code subsystem definitions
  - `get_security_patterns()`: Vulnerability patterns
  - `get_intent_patterns()`: Query intent patterns
  - `get_prompts()`: LLM prompt templates

#### DomainRegistry
- Location: `src/domains/registry.py`
- Singleton registry for managing domain plugins
- Key methods:
  - `register(plugin)`: Register a new plugin
  - `activate(name)`: Set the active domain
  - `get_active()`: Get the currently active domain

#### Available Plugins

1. **GenericCppDomainPlugin** (`src/domains/generic_cpp.py`)
   - Subsystems: memory_management, file_io, string_handling, data_structures, concurrency, network, error_handling, system_calls
   - Security Patterns: buffer_overflow, use_after_free, format_string, etc.
   - 10 security vulnerability patterns with CWE IDs

2. **PostgreSQLDomainPlugin** (`src/domains/postgresql/plugin.py`)
   - PostgreSQL-specific subsystems (executor, planner, storage, etc.)
   - Database-specific security patterns

### Usage

```python
from src.domains import DomainRegistry, get_active_domain

# Activate a domain
DomainRegistry.activate('generic_cpp')

# Get subsystems
domain = get_active_domain()
for name, info in domain.subsystems.items():
    print(f"{name}: {info.description}")

# Get security patterns
patterns = domain.get_security_patterns()
for p in patterns:
    print(f"{p.id} ({p.severity}): {p.description}")
```

## Workflow System

The workflow system uses LangGraph to orchestrate multi-step analysis workflows.

### State Management

#### MultiScenarioState
- Location: `src/workflow/state.py`
- TypedDict defining the shape of data flowing through workflows:
  - Input: `query`, `context`
  - Classification: `intent`, `scenario_id`, `confidence`
  - CPG Data: `cpg_results`, `subsystems`, `methods`
  - Output: `answer`, `evidence`, `metadata`
  - Error handling: `error`, `retry_count`

#### Helper Function
```python
from src.workflow.state import create_initial_state

state = create_initial_state("Find SQL injection vulnerabilities")
```

### Query Handlers

- Location: `src/workflow/query_handlers.py`
- Functions for detecting and handling specific query types:
  - `detect_onboarding_query_type(query)`: Classifies queries as definition, call_graph, dataflow, or general
  - `handle_definition_query(state, cpg)`: Handles "where is X defined" queries
  - `handle_call_graph_query(state, cpg)`: Handles "who calls X" queries
  - `handle_dataflow_query(state, cpg)`: Handles data flow tracing queries

### Scenario Workflows

Each scenario has its own workflow module in `src/workflow/scenarios/`:

| Scenario | File | Description |
|----------|------|-------------|
| Security | security.py | Vulnerability analysis |
| Performance | performance.py | Performance and complexity analysis |
| Refactoring | refactoring.py | Code smell detection |
| Onboarding | onboarding.py | Codebase navigation |
| Documentation | documentation.py | Doc generation |
| Feature Dev | feature_dev.py | Feature development assistance |
| Test Coverage | test_coverage.py | Test analysis |
| Code Review | code_review.py | Review assistance |
| Compliance | compliance.py | Standards checking |
| Security Incident | security_incident.py | Incident response |
| Cross Repo | cross_repo.py | Cross-repository analysis |
| Large Scale Refactoring | large_scale_refactoring.py | Automated refactoring |
| Architecture | architecture.py | Architecture analysis |
| Tech Debt | tech_debt.py | Technical debt quantification |
| Mass Refactoring | mass_refactoring.py | Bulk refactoring |

### Main Orchestrator

- Location: `src/workflow/multi_scenario_workflow.py`
- `MultiScenarioCopilot`: Main class for running queries
- `build_multi_scenario_graph()`: Builds the LangGraph workflow

```python
from src.workflow.multi_scenario_workflow import MultiScenarioCopilot

copilot = MultiScenarioCopilot()
result = copilot.run("Find SQL injection vulnerabilities")
print(result['answer'])
```

## Testing

Unit tests are organized in `tests/unit/`:

| Test File | Coverage |
|-----------|----------|
| test_domain_plugins.py | Domain plugin system (35 tests) |
| test_query_handlers.py | Query detection (31 tests) |
| test_workflow_state.py | State definitions (20 tests) |

Run tests:
```bash
pytest tests/unit/test_domain_plugins.py tests/unit/test_query_handlers.py tests/unit/test_workflow_state.py -v
```

## Adding a New Domain

1. Create a new plugin class inheriting from `DomainPlugin`:

```python
from src.domains.base import DomainPlugin, SubsystemInfo, SecurityPattern

class MyDomainPlugin(DomainPlugin):
    @property
    def name(self) -> str:
        return "my_domain"

    @property
    def display_name(self) -> str:
        return "My Domain"

    def _load_subsystems(self):
        return {
            "core": SubsystemInfo(
                name="Core",
                description="Core functionality",
                key_functions=["main", "init"],
            ),
        }

    # Implement other abstract methods...
```

2. Register the plugin in `src/domains/__init__.py`:

```python
from .my_domain import MyDomainPlugin, my_domain_plugin
DomainRegistry.register(my_domain_plugin)
```

3. Add tests in `tests/unit/test_domain_plugins.py`

## File Size Summary

After modularization:

| File | Lines | Description |
|------|-------|-------------|
| multi_scenario_workflow.py | ~793 | Main orchestrator (reduced from 5,558) |
| query_handlers.py | ~500 | Query detection and handling |
| state.py | 147 | State definitions |
| scenarios/*.py | 15 files | Individual workflow implementations |
| domains/generic_cpp.py | 295 | C/C++ domain plugin |
