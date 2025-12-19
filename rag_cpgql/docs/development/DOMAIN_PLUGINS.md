# Domain Plugin Development Guide

This guide explains how to create custom domain plugins to adapt the CodeGraph system to new codebases.

## Overview

Domain plugins encapsulate codebase-specific knowledge:
- Function names and patterns
- Security-sensitive operations
- Memory management APIs
- Synchronization primitives
- Error handling conventions

This separation allows the core analysis logic to remain generic while providing precise, domain-aware analysis.

## Architecture

```
src/domains/
├── __init__.py           # Auto-registration
├── base.py               # DomainPlugin abstract base class
├── registry.py           # DomainRegistry singleton
├── generic_cpp/          # Generic C/C++ plugin
│   ├── plugin.py
│   └── data/
│       ├── subsystems.yaml
│       ├── security_patterns.yaml
│       └── prompts.yaml
└── postgresql/           # PostgreSQL-specific plugin
    ├── plugin.py
    └── data/
        ├── subsystems.yaml
        ├── security_patterns.yaml
        └── prompts.yaml
```

## Creating a New Domain Plugin

### Step 1: Create Plugin Directory

```bash
mkdir -p src/domains/my_domain/data
```

### Step 2: Implement Plugin Class

Create `src/domains/my_domain/plugin.py`:

```python
"""
Domain plugin for MyDomain codebase.
"""
from typing import Dict, List, Any
from src.domains.base import DomainPlugin


class MyDomainPlugin(DomainPlugin):
    """Plugin for analyzing MyDomain codebase."""

    @property
    def name(self) -> str:
        return "my_domain"

    @property
    def display_name(self) -> str:
        return "My Domain"

    @property
    def description(self) -> str:
        return "Analysis plugin for MyDomain codebase"

    # === Required Methods ===

    def get_memory_functions(self) -> Dict[str, List[str]]:
        """Memory management functions by category."""
        return {
            'allocation': ['my_alloc', 'my_malloc', 'my_calloc'],
            'deallocation': ['my_free', 'my_release'],
            'reallocation': ['my_realloc', 'my_resize'],
        }

    def get_lock_functions(self) -> List[str]:
        """Synchronization primitives."""
        return [
            'my_lock_acquire', 'my_lock_release',
            'my_mutex_lock', 'my_mutex_unlock',
        ]

    def get_security_patterns(self) -> List[Dict]:
        """Security vulnerability patterns."""
        return [
            {
                'name': 'command_injection',
                'pattern': r'system\s*\(',
                'severity': 'critical',
                'cwe': 'CWE-78',
            },
            # ... more patterns
        ]

    # === Optional Methods (with defaults in base class) ===

    def get_vulnerability_function_mappings(self) -> Dict[str, List[str]]:
        """Map vulnerability types to relevant functions."""
        return {
            'sql_injection': ['execute_query', 'run_sql'],
            'buffer_overflow': ['strcpy', 'sprintf', 'gets'],
            'null_pointer': ['malloc', 'calloc', 'my_alloc'],
            # ... more mappings
        }

    def get_duplicate_pattern_functions(self) -> Dict[str, List[str]]:
        """Map code duplication patterns to expected functions."""
        return {
            'error_handling': ['log_error', 'report_error', 'throw_exception'],
            'resource_cleanup': ['cleanup', 'release', 'destroy'],
            # ... more patterns
        }

    def get_taint_sources(self) -> List[str]:
        """Functions that introduce untrusted data."""
        return [
            'read_input', 'recv', 'getenv', 'fgets',
            'parse_request', 'get_user_data',
        ]

    def get_taint_sinks(self) -> List[str]:
        """Dangerous functions that should not receive tainted data."""
        return [
            'execute_command', 'system', 'eval',
            'write_file', 'send_response',
        ]

    def get_concurrency_functions(self) -> Dict[str, List[str]]:
        """Concurrency primitives by category."""
        return {
            'mutex': ['mutex_lock', 'mutex_unlock', 'mutex_trylock'],
            'spinlock': ['spin_lock', 'spin_unlock'],
            'atomic': ['atomic_read', 'atomic_write', 'atomic_cas'],
            'condition': ['cond_wait', 'cond_signal', 'cond_broadcast'],
        }


# Auto-register when module is imported
my_domain_plugin = MyDomainPlugin()
```

### Step 3: Create Configuration Files

#### `data/subsystems.yaml`

```yaml
subsystems:
  core:
    description: "Core system functionality"
    key_functions:
      - main
      - init_system
      - shutdown_system
    patterns:
      - "core_*"
      - "*_init"

  network:
    description: "Network communication"
    key_functions:
      - send_packet
      - receive_packet
      - open_connection
    patterns:
      - "net_*"
      - "*_socket"

  storage:
    description: "Data storage layer"
    key_functions:
      - read_data
      - write_data
      - flush_cache
    patterns:
      - "storage_*"
      - "*_file"
```

#### `data/security_patterns.yaml`

```yaml
patterns:
  - name: buffer_overflow
    description: "Potential buffer overflow"
    pattern: "(strcpy|strcat|sprintf|gets)\\s*\\("
    severity: high
    cwe: CWE-120
    remediation: "Use bounded string functions (strncpy, snprintf)"

  - name: sql_injection
    description: "Potential SQL injection"
    pattern: "execute.*\\+.*input"
    severity: critical
    cwe: CWE-89
    remediation: "Use parameterized queries"

  - name: command_injection
    description: "Command injection risk"
    pattern: "(system|popen|exec)\\s*\\("
    severity: critical
    cwe: CWE-78
    remediation: "Avoid shell commands or use allowlists"
```

### Step 4: Register the Plugin

Add to `src/domains/__init__.py`:

```python
# Import to trigger auto-registration
from .my_domain.plugin import my_domain_plugin
```

### Step 5: Configure Domain

In `config.yaml`:

```yaml
domain: my_domain
```

## Plugin Methods Reference

### Required Methods

| Method | Return Type | Description |
|--------|-------------|-------------|
| `name` | `str` | Plugin identifier (lowercase, no spaces) |
| `display_name` | `str` | Human-readable name |
| `description` | `str` | Plugin description |

### Memory & Resource Management

| Method | Return Type | Description |
|--------|-------------|-------------|
| `get_memory_functions()` | `Dict[str, List[str]]` | Memory ops by category |
| `get_lock_functions()` | `List[str]` | Lock/synchronization functions |

### Security Analysis

| Method | Return Type | Description |
|--------|-------------|-------------|
| `get_security_patterns()` | `List[Dict]` | Vulnerability patterns with regex |
| `get_vulnerability_function_mappings()` | `Dict[str, List[str]]` | Vuln type → functions |
| `get_taint_sources()` | `List[str]` | Input/untrusted data sources |
| `get_taint_sinks()` | `List[str]` | Dangerous operations |
| `get_sanitization_patterns()` | `List[Dict]` | Input validation patterns |

### Code Pattern Detection

| Method | Return Type | Description |
|--------|-------------|-------------|
| `get_duplicate_pattern_functions()` | `Dict[str, List[str]]` | Clone detection patterns |
| `get_concurrency_functions()` | `Dict[str, List[str]]` | Sync primitives by type |

### Subsystem Information

| Method | Return Type | Description |
|--------|-------------|-------------|
| `get_subsystem_functions(name)` | `List[str]` | Functions in subsystem |
| `find_subsystem_for_function(func)` | `Optional[str]` | Subsystem containing function |
| `get_all_key_functions()` | `List[str]` | All important functions |

## Best Practices

### 1. Be Comprehensive

Include all major function categories:

```python
def get_memory_functions(self) -> Dict[str, List[str]]:
    return {
        'allocation': [...],      # malloc, calloc equivalents
        'deallocation': [...],    # free equivalents
        'reallocation': [...],    # realloc equivalents
        'context': [...],         # memory pool/arena management
    }
```

### 2. Use Specific Patterns

More specific patterns reduce false positives:

```python
# Good - specific to your codebase
'my_execute_sql'

# Less good - too generic
'execute'
```

### 3. Map Vulnerability Types Completely

Cover all relevant CWE categories:

```python
def get_vulnerability_function_mappings(self) -> Dict[str, List[str]]:
    return {
        'sql_injection': [...],        # CWE-89
        'buffer_overflow': [...],      # CWE-120
        'command_injection': [...],    # CWE-78
        'path_traversal': [...],       # CWE-22
        'null_pointer': [...],         # CWE-476
        'use_after_free': [...],       # CWE-416
        'race_condition': [...],       # CWE-362
        # ... etc
    }
```

### 4. Include Taint Flow

Define complete source-to-sink paths:

```python
# Sources: where untrusted data enters
def get_taint_sources(self) -> List[str]:
    return [
        'recv', 'read', 'getenv',           # System input
        'parse_request', 'get_param',        # Application input
        'database_fetch', 'file_read',       # External data
    ]

# Sinks: dangerous operations
def get_taint_sinks(self) -> List[str]:
    return [
        'system', 'exec', 'popen',           # Command execution
        'sql_execute', 'query',              # Database
        'fopen', 'unlink',                   # File operations
    ]
```

## Testing Your Plugin

### Unit Tests

```python
# tests/unit/test_my_domain_plugin.py
import pytest
from src.domains.my_domain.plugin import MyDomainPlugin


class TestMyDomainPlugin:
    def setup_method(self):
        self.plugin = MyDomainPlugin()

    def test_plugin_name(self):
        assert self.plugin.name == "my_domain"

    def test_memory_functions_complete(self):
        mem = self.plugin.get_memory_functions()
        assert 'allocation' in mem
        assert 'deallocation' in mem
        assert len(mem['allocation']) > 0

    def test_vulnerability_mappings(self):
        vuln = self.plugin.get_vulnerability_function_mappings()
        assert 'sql_injection' in vuln
        assert 'buffer_overflow' in vuln

    def test_taint_sources_not_empty(self):
        sources = self.plugin.get_taint_sources()
        assert len(sources) > 0

    def test_taint_sinks_not_empty(self):
        sinks = self.plugin.get_taint_sinks()
        assert len(sinks) > 0
```

### Integration Tests

```python
# tests/integration/test_my_domain_workflow.py
def test_security_workflow_uses_plugin():
    from src.domains import DomainRegistry
    from src.workflow.scenarios.security import security_workflow

    # Activate plugin
    DomainRegistry.activate("my_domain")

    # Run workflow
    state = create_initial_state("Find SQL injection vulnerabilities")
    result = security_workflow(state)

    # Verify plugin functions are used
    assert 'execute_query' in str(result.get('retrieved_functions', []))
```

## Example: Linux Kernel Plugin

```python
class LinuxKernelPlugin(DomainPlugin):
    @property
    def name(self) -> str:
        return "linux_kernel"

    def get_memory_functions(self) -> Dict[str, List[str]]:
        return {
            'allocation': ['kmalloc', 'kzalloc', 'vmalloc', 'alloc_pages'],
            'deallocation': ['kfree', 'vfree', 'free_pages'],
            'slab': ['kmem_cache_alloc', 'kmem_cache_free'],
        }

    def get_lock_functions(self) -> List[str]:
        return [
            'spin_lock', 'spin_unlock', 'spin_lock_irqsave',
            'mutex_lock', 'mutex_unlock',
            'rcu_read_lock', 'rcu_read_unlock',
        ]

    def get_concurrency_functions(self) -> Dict[str, List[str]]:
        return {
            'spinlock': ['spin_lock', 'spin_unlock', 'spin_trylock'],
            'mutex': ['mutex_lock', 'mutex_unlock', 'mutex_trylock'],
            'rwlock': ['read_lock', 'write_lock', 'read_unlock', 'write_unlock'],
            'rcu': ['rcu_read_lock', 'rcu_read_unlock', 'synchronize_rcu'],
            'atomic': ['atomic_read', 'atomic_set', 'atomic_add', 'atomic_inc'],
        }

    def get_taint_sources(self) -> List[str]:
        return [
            'copy_from_user', 'get_user', '__get_user',
            'strncpy_from_user', 'strnlen_user',
        ]

    def get_taint_sinks(self) -> List[str]:
        return [
            'copy_to_user', 'put_user',
            'call_usermodehelper', 'kernel_execve',
        ]
```

## Troubleshooting

### Plugin Not Loading

1. Check import in `src/domains/__init__.py`
2. Verify no syntax errors in plugin file
3. Check logs for registration messages

### Functions Not Being Used

1. Verify domain is activated: `DomainRegistry.get_active()`
2. Check helper functions are called in workflows
3. Enable debug logging

### Pattern Matching Issues

1. Test regex patterns separately
2. Use raw strings for regex: `r"pattern"`
3. Escape special characters properly

## See Also

- [Architecture Guide](ARCHITECTURE.md) - System design
- [Contributing Guide](CONTRIBUTING.md) - Code standards
- [Patterns Guide](PATTERNS.md) - Code patterns
