# Domains Module

Pluggable domain system providing specialized analysis capabilities for different codebases including PostgreSQL, Linux Kernel, LLVM, and generic C/C++.

## Overview

```
src/domains/
├── base.py              # Abstract base domain class
├── registry.py          # Domain registration and lookup
├── postgresql/          # PostgreSQL domain plugin
│   ├── __init__.py
│   ├── config.py        # Domain-specific configuration
│   ├── patterns.py      # Code patterns and concepts
│   ├── memory.py        # Memory management functions
│   ├── concurrency.py   # Lock and synchronization primitives
│   └── vulnerabilities.py # Vulnerability patterns
├── linux/               # Linux Kernel domain
│   ├── __init__.py
│   ├── config.py
│   ├── patterns.py
│   └── syscalls.py
├── llvm/                # LLVM/Compiler domain
│   ├── __init__.py
│   └── patterns.py
├── python_django/       # Python Django domain
│   └── __init__.py
└── generic_cpp/         # Generic C/C++ domain
    └── __init__.py
```

## Supported Domains

| Domain | Description | Concepts |
|--------|-------------|----------|
| `postgresql` | PostgreSQL database server | 51 domain concepts |
| `linux` | Linux Kernel | Kernel patterns, syscalls |
| `llvm` | LLVM compiler infrastructure | IR, passes, optimization |
| `python_django` | Django web framework | Views, models, ORM |
| `generic_cpp` | Generic C/C++ code | Standard patterns |

## Usage

### Domain Registry

```python
from src.domains.registry import get_domain, list_domains

# Get specific domain
pg_domain = get_domain('postgresql')

# List available domains
domains = list_domains()
# ['postgresql', 'linux', 'llvm', 'python_django', 'generic_cpp']
```

### Domain Capabilities

```python
from src.domains.postgresql import PostgreSQLDomain

domain = PostgreSQLDomain()

# Get memory functions
memory_funcs = domain.get_memory_functions()
# ['palloc', 'pfree', 'repalloc', 'MemoryContextAlloc', ...]

# Get concurrency primitives
locks = domain.get_concurrency_primitives()
# ['LWLockAcquire', 'LWLockRelease', 'SpinLockAcquire', ...]

# Get vulnerability patterns
vulns = domain.get_vulnerability_patterns()
# [{'name': 'buffer_overflow', 'pattern': '...'}, ...]

# Get domain concepts
concepts = domain.get_concepts()
# ['MVCC', 'WAL', 'vacuum', 'indexing', ...]
```

## Domain Interface

```python
class BaseDomain(ABC):
    """Abstract base class for domain plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Domain name."""
        pass

    @abstractmethod
    def get_memory_functions(self) -> List[str]:
        """Get memory management functions."""
        pass

    @abstractmethod
    def get_concurrency_primitives(self) -> List[str]:
        """Get locking/synchronization primitives."""
        pass

    @abstractmethod
    def get_vulnerability_patterns(self) -> List[Dict]:
        """Get domain-specific vulnerability patterns."""
        pass

    @abstractmethod
    def get_concepts(self) -> List[str]:
        """Get domain-specific concepts for tagging."""
        pass

    @abstractmethod
    def get_query_templates(self) -> Dict[str, str]:
        """Get SQL query templates for common CPG analyses."""
        pass
```

## PostgreSQL Domain

### Concepts (51 total)

| Category | Concepts |
|----------|----------|
| Transaction | MVCC, WAL, checkpoint, vacuum, xact |
| Storage | heap, index, btree, toast, buffer |
| Concurrency | lock, lwlock, spinlock, latch |
| Replication | streaming, logical, slot, walsender |
| Planning | planner, optimizer, path, cost |

### Memory Functions

```python
POSTGRESQL_MEMORY_FUNCTIONS = [
    'palloc', 'palloc0', 'repalloc', 'pfree',
    'MemoryContextAlloc', 'MemoryContextAllocZero',
    'MemoryContextCreate', 'MemoryContextDelete',
    'AllocSetContextCreate', 'CurrentMemoryContext',
]
```

### Vulnerability Patterns

```python
POSTGRESQL_VULNERABILITY_PATTERNS = [
    {
        'name': 'buffer_overflow',
        'pattern': r'memcpy|strcpy|sprintf',
        'severity': 'high'
    },
    {
        'name': 'sql_injection',
        'pattern': r'simple_string_to_string.*user_input',
        'severity': 'critical'
    },
]
```

## Linux Kernel Domain

### Concepts

- Memory: kmalloc, vmalloc, slab
- Concurrency: spinlock, mutex, rcu
- Networking: sk_buff, netfilter
- Filesystem: inode, dentry, vfs

## Adding a New Domain

```python
# src/domains/my_domain/__init__.py
from src.domains.base import BaseDomain

class MyDomain(BaseDomain):
    @property
    def name(self) -> str:
        return "my_domain"

    def get_memory_functions(self) -> List[str]:
        return ['malloc', 'free', 'custom_alloc']

    def get_concurrency_primitives(self) -> List[str]:
        return ['my_lock', 'my_unlock']

    # ... implement other methods

# Register in registry.py
DOMAINS['my_domain'] = MyDomain()
```

## Configuration

```yaml
domains:
  default: postgresql

  postgresql:
    enabled: true
    concept_count: 51

  linux:
    enabled: true
    include_syscalls: true

  llvm:
    enabled: false
```

## See Also

- `/src/extraction/domain_concept_tagger.py` - Concept tagging
- `/src/agents/analyzer_agent.py` - Domain detection
- `/data/` - Domain-specific extracted patterns
