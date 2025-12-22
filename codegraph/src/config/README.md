# Config Module

Unified configuration management system providing centralized access to all application settings with environment variable support and YAML configuration files.

## Overview

```
src/config/
├── unified_config.py    # Main unified configuration class
├── joern_config.py      # Joern server configuration
├── cpg_config.py        # CPG database configuration
├── llm_config.py        # LLM provider configuration
└── __init__.py          # Module exports
```

## UnifiedConfig

The `UnifiedConfig` class provides centralized access to all configuration:

```python
from src.config.unified_config import get_unified_config

config = get_unified_config()

# Access settings
print(config.llm.provider)      # 'gigachat'
print(config.joern.endpoint)    # 'localhost:8080'
print(config.database.url)      # PostgreSQL URL
```

## Configuration Sources

1. **YAML File** (`config.yaml`) - Primary configuration
2. **Environment Variables** - Override YAML settings
3. **Defaults** - Fallback values

### Priority Order

```
Environment Variables > config.yaml > Defaults
```

## Configuration Sections

### LLM Configuration

```yaml
llm:
  provider: gigachat  # gigachat, local, openai

  gigachat:
    credentials: ${GIGACHAT_CREDENTIALS}
    model: GigaChat-Pro
    temperature: 0.1

  local:
    model_path: /models/qwen3-coder-30b.gguf
    n_ctx: 8192
    n_gpu_layers: -1
```

### Joern Configuration

```yaml
joern:
  endpoint: localhost:8080
  workspace: /tmp/joern_workspace
  timeout: 300
  bootstrap_on_start: true
```

### Database Configuration

```yaml
database:
  url: postgresql+asyncpg://user:pass@localhost/ragcpgql
  pool_size: 5
  max_overflow: 10
  echo: false
```

### Retrieval Configuration

```yaml
retrieval:
  chroma_path: ./chromadb_storage
  top_k_qa: 5
  top_k_graph: 10

  ddg:
    enabled: true
    top_k: 20

  cfg:
    enabled: true
    top_k: 20
```

### API Configuration

```yaml
api:
  host: 0.0.0.0
  port: 8000
  debug: false

  jwt:
    secret: ${JWT_SECRET}
    algorithm: HS256
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GIGACHAT_CREDENTIALS` | GigaChat API credentials | - |
| `JWT_SECRET` | JWT signing secret | - |
| `DATABASE_URL` | PostgreSQL connection URL | - |
| `JOERN_ENDPOINT` | Joern server endpoint (optional, for CPG export) | localhost:8080 |
| `CHROMA_PATH` | ChromaDB storage path | ./chromadb_storage |

## Usage

### Get Configuration

```python
from src.config.unified_config import get_unified_config

# Singleton instance
config = get_unified_config()
```

### Reload Configuration

```python
from src.config.unified_config import reload_config

# Reload from files
reload_config()
```

### Override Settings

```python
import os

# Set environment variable
os.environ['LLM_PROVIDER'] = 'local'

# Configuration will use environment value
config = get_unified_config()
assert config.llm.provider == 'local'
```

## Validation

Configuration is validated on load:

```python
from pydantic import ValidationError

try:
    config = get_unified_config()
except ValidationError as e:
    print(f"Invalid configuration: {e}")
```

## See Also

- `/config.yaml` - Main configuration file
- `/src/api/config.py` - API-specific settings
- `/docs/guides/CONFIGURATION.md` - Configuration guide
