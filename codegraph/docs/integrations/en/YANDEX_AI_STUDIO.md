# Yandex AI Studio Integration Guide

Integration guide for Yandex Cloud AI Studio with CodeGraph using OpenAI-compatible API.

## Table of Contents

- [Overview](#overview)
- [Quick Setup (3 Steps)](#quick-setup-3-steps)
  - [Step 1: Create API Key](#step-1-create-api-key)
  - [Step 2: Set Environment Variables](#step-2-set-environment-variables)
  - [Step 3: Configure config.yaml](#step-3-configure-configyaml)
- [Available Models](#available-models)
  - [Text Generation Models](#text-generation-models)
  - [Embedding Models](#embedding-models)
- [Model URI Format](#model-uri-format)
- [Usage in Code](#usage-in-code)
  - [Basic Usage](#basic-usage)
  - [Streaming](#streaming)
  - [Embeddings](#embeddings)
  - [With CodeGraph Workflow](#with-codegraph-workflow)
- [Configuration Reference](#configuration-reference)
  - [Full config.yaml Example](#full-configyaml-example)
  - [Environment Variables](#environment-variables)
  - [Provider Parameters](#provider-parameters)
- [Privacy and Compliance](#privacy-and-compliance)
- [Error Handling](#error-handling)
  - [Authentication Error (401)](#authentication-error-401)
  - [Rate Limit Exceeded (429)](#rate-limit-exceeded-429)
  - [Connection Timeout](#connection-timeout)
  - [Folder ID Error](#folder-id-error)
- [Retry Logic](#retry-logic)
- [Best Practices](#best-practices)
- [Comparison with Other Providers](#comparison-with-other-providers)
- [Resources](#resources)
- [Next Steps](#next-steps)

## Overview

Yandex Cloud AI Studio is a comprehensive AI platform providing access to:
- **YandexGPT** family of models (YandexGPT, YandexGPT-Lite, YandexGPT-32k)
- **Open-source models** (Qwen3, DeepSeek, OpenAI OSS)
- **Embedding models** for semantic search

CodeGraph integrates with Yandex AI Studio using the OpenAI-compatible API, which allows using the standard `openai` Python library.

**Key Features:**
- OpenAI API compatibility (use familiar `openai` library)
- Privacy-focused: logging disabled by default via `x-data-logging-enabled: false`
- Multiple model options from 20B to 235B parameters
- Built-in retry with exponential backoff

## Quick Setup (3 Steps)

### Step 1: Create API Key

1. Go to [Yandex Cloud Console](https://console.yandex.cloud/)
2. Navigate to **AI Studio** in the left menu
3. Click **Create new key** in the top panel
4. Select **Create API key**
5. In the **Scope** field, select `yc.ai.languageModels.execute`
6. Click **Create** and save both the ID and secret key
7. Note your **Folder ID** from the folder selector in the top panel

### Step 2: Set Environment Variables

```powershell
# Windows PowerShell
$env:YANDEX_API_KEY = "AQVNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
$env:YANDEX_FOLDER_ID = "b1gxxxxxxxxxxxxxxxxx"

# Permanent (survives restart)
[System.Environment]::SetEnvironmentVariable('YANDEX_API_KEY', 'AQVNxxx...', 'User')
[System.Environment]::SetEnvironmentVariable('YANDEX_FOLDER_ID', 'b1gxxx...', 'User')
```

```bash
# Linux/Mac
export YANDEX_API_KEY="AQVNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export YANDEX_FOLDER_ID="b1gxxxxxxxxxxxxxxxxx"

# Add to ~/.bashrc for permanent
echo 'export YANDEX_API_KEY="your_key"' >> ~/.bashrc
echo 'export YANDEX_FOLDER_ID="your_folder"' >> ~/.bashrc
```

### Step 3: Configure config.yaml

```yaml
llm:
  provider: yandex

  yandex:
    api_key: ${YANDEX_API_KEY}
    folder_id: ${YANDEX_FOLDER_ID}
    model: "qwen3-235b-a22b-fp8/latest"
    temperature: 0.7
    max_tokens: 2000
    timeout: 180
```

Verify configuration:
```bash
python -c "
from src.llm.yandex_provider import YandexProvider
from src.llm.base_provider import LLMConfig

config = LLMConfig(provider_type='yandex')
provider = YandexProvider(config)
print(f'Provider: {provider}')
print('Connection successful!')
"
```

## Available Models

### Text Generation Models

| Model | URI | Context | Best For |
|-------|-----|---------|----------|
| **Qwen3 235B** | `qwen3-235b-a22b-fp8/latest` | 262K | Complex code analysis, security review (default) |
| **gpt-oss-120b** | `gpt-oss-120b/latest` | 131K | OpenAI OSS reasoning model, complex tasks |
| **gpt-oss-20b** | `gpt-oss-20b/latest` | 131K | OpenAI OSS model, balanced performance |
| **Gemma 3 27B** | `gemma-3-27b-it/latest` | 131K | Google's open model, instruction-tuned |
| **YandexGPT Pro 5** | `yandexgpt/latest` | 32K | General purpose, excellent Russian support |
| **YandexGPT Pro 5.1** | `yandexgpt/rc` | 32K | Latest features, improved reasoning |
| **YandexGPT Lite 5** | `yandexgpt-lite` | 32K | Fast responses, simple queries |
| **Alice AI LLM** | `aliceai-llm` | 32K | Conversational AI, dialogue systems |
| **Fine-tuned YandexGPT Lite** | `yandexgpt-lite/latest@<suffix>` | 32K | Custom fine-tuned models |

**Recommendations:**
- **Code Analysis**: Use `qwen3-235b-a22b-fp8/latest` (262K context, best quality)
- **Security Review**: Use `gpt-oss-120b/latest` (reasoning capabilities)
- **Fast Queries**: Use `yandexgpt-lite` for speed
- **Russian Text**: Use `yandexgpt/latest` for native Russian support
- **Large Files**: Use models with 131K+ context (Qwen3, gpt-oss, Gemma)

### Embedding Models

| Model | Dimensions | Use Case |
|-------|------------|----------|
| `text-search-doc/latest` | 256 | Document embeddings (default) |
| `text-search-query/latest` | 256 | Query embeddings |

## Model URI Format

Yandex requires a specific model URI format:

```
gpt://<folder_id>/<model_name>
emb://<folder_id>/<embedding_model>
```

Examples:
```
gpt://b1g123456789/qwen3-235b-a22b-fp8/latest
gpt://b1g123456789/yandexgpt/latest
emb://b1g123456789/text-search-doc/latest
```

The CodeGraph provider constructs this automatically from your `folder_id` and `model` settings.

## Usage in Code

### Basic Usage

```python
import os
from openai import OpenAI

# Initialize client with Yandex endpoint
client = OpenAI(
    api_key=os.getenv("YANDEX_API_KEY"),
    base_url="https://llm.api.cloud.yandex.net/v1",
    default_headers={
        "x-data-logging-enabled": "false",  # Privacy
        "x-folder-id": os.getenv("YANDEX_FOLDER_ID"),
    },
)

# Construct model URI
folder_id = os.getenv("YANDEX_FOLDER_ID")
model_uri = f"gpt://{folder_id}/qwen3-235b-a22b-fp8/latest"

# Make request
response = client.chat.completions.create(
    model=model_uri,
    messages=[
        {"role": "system", "content": "You are a code analysis expert."},
        {"role": "user", "content": "Explain MVCC in PostgreSQL."},
    ],
    temperature=0.7,
    max_tokens=2000,
)

print(response.choices[0].message.content)
```

### Streaming

```python
# Stream response
stream = client.chat.completions.create(
    model=model_uri,
    messages=[
        {"role": "user", "content": "List security best practices for C code."},
    ],
    stream=True,
)

for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

### Embeddings

```python
# Get embeddings
embedding_uri = f"emb://{folder_id}/text-search-doc/latest"

response = client.embeddings.create(
    model=embedding_uri,
    input="Find buffer overflow vulnerabilities",
    encoding_format="float",
)

embedding = response.data[0].embedding
print(f"Embedding dimension: {len(embedding)}")  # 256
```

### With CodeGraph Workflow

```python
from src.llm.yandex_provider import YandexProvider
from src.llm.base_provider import LLMConfig

# Initialize provider (reads from config.yaml)
config = LLMConfig(
    provider_type='yandex',
    temperature=0.7,
    max_tokens=2000,
    extra_params={
        'api_key': os.getenv('YANDEX_API_KEY'),
        'folder_id': os.getenv('YANDEX_FOLDER_ID'),
        'model': 'qwen3-235b-a22b-fp8/latest',
    }
)
provider = YandexProvider(config)

# Generate response
response = provider.generate(
    system_prompt="You are a PostgreSQL security expert.",
    user_prompt="Find SQL injection vulnerabilities in the executor module."
)

print(response.content)
print(f"Tokens used: {response.metadata['tokens_used']}")
print(f"Latency: {response.metadata['latency_ms']:.0f}ms")
```

Using with workflow:
```python
from src.workflow.orchestration.copilot import Copilot

# Copilot automatically uses configured provider
copilot = Copilot()
result = copilot.answer("Find memory allocation functions in PostgreSQL")
print(result['answer'])
```

## Configuration Reference

### Full config.yaml Example

```yaml
llm:
  # Set Yandex as the active provider
  provider: yandex

  yandex:
    # Required: Authentication
    api_key: ${YANDEX_API_KEY}      # Service account API key
    folder_id: ${YANDEX_FOLDER_ID}  # Yandex Cloud folder ID

    # Model selection
    model: "qwen3-235b-a22b-fp8/latest"  # Best for code analysis

    # API endpoint (default, usually not changed)
    base_url: "https://llm.api.cloud.yandex.net/v1"

    # Timeouts
    timeout: 180  # seconds (increased for large prompts)

    # Generation parameters
    temperature: 0.7       # Creativity (0.0-1.0)
    max_tokens: 2000       # Max response length
    top_p: null            # Use Yandex default

    # Embedding model
    embedding_model: "text-search-doc/latest"
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `YANDEX_API_KEY` | Yes | API key from Yandex Cloud Console |
| `YANDEX_FOLDER_ID` | Yes | Folder ID where AI Studio is enabled |

### Provider Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | string | - | Yandex Cloud API key (required) |
| `folder_id` | string | - | Yandex Cloud folder ID (required) |
| `model` | string | `qwen3-235b-a22b-fp8/latest` | Text generation model |
| `base_url` | string | `https://llm.api.cloud.yandex.net/v1` | API endpoint |
| `timeout` | int | 60 | Request timeout in seconds |
| `temperature` | float | 0.7 | Response randomness (0.0-1.0) |
| `max_tokens` | int | 2000 | Maximum response tokens |
| `top_p` | float | null | Nucleus sampling parameter |
| `embedding_model` | string | `text-search-doc/latest` | Embedding model |

## Privacy and Compliance

CodeGraph automatically disables Yandex-side logging for privacy/GDPR compliance:

```python
default_headers={
    "x-data-logging-enabled": "false",  # Disables logging on Yandex side
    "x-folder-id": folder_id,
}
```

This ensures:
- Your prompts are not logged by Yandex
- Response data is not stored
- Compliant with data protection regulations

## Error Handling

### Authentication Error (401)

```
Error: 401 Unauthorized
```

**Solutions:**
```bash
# Check if variables are set
echo $YANDEX_API_KEY
echo $YANDEX_FOLDER_ID

# Verify API key format (should start with AQVNw, AQVN_, or similar)
python -c "import os; key = os.getenv('YANDEX_API_KEY', ''); print(f'Key prefix: {key[:5]}...' if key else 'NOT SET')"

# Verify API key scope includes yc.ai.languageModels.execute
```

### Rate Limit Exceeded (429)

```
Error: 429 Too Many Requests
```

**Solutions:**
```yaml
# Built-in retry handles this automatically
# But you can increase timeout for complex requests
yandex:
  timeout: 300  # 5 minutes
```

Or implement custom retry:
```python
import time

for attempt in range(3):
    try:
        response = provider.generate(system_prompt, user_prompt)
        break
    except YandexRateLimitError:
        time.sleep(2 ** attempt)  # Exponential backoff
```

### Connection Timeout

```
Error: Request timeout
```

**Solutions:**
```yaml
# Increase timeout for large prompts/responses
yandex:
  timeout: 300  # seconds
```

### Folder ID Error

```
Error: Folder not found or access denied
```

**Solutions:**
1. Verify folder ID in Yandex Cloud Console (top panel dropdown)
2. Ensure AI Studio is enabled in the folder
3. Check that API key has access to the folder

## Retry Logic

The Yandex provider includes built-in retry with exponential backoff:

```python
# Automatic retry for:
# - APITimeoutError (timeout)
# - APIConnectionError (connection issues)

# Retry parameters:
# - max_retries: 3
# - initial_delay: 2.0 seconds
# - max_delay: 30.0 seconds
# - backoff_factor: 2.0
```

Example retry sequence:
1. First attempt fails -> wait 2s
2. Second attempt fails -> wait 4s
3. Third attempt fails -> raise exception

## Best Practices

1. **Use Qwen3-235B for code analysis** - Best quality for complex queries
2. **Use YandexGPT-Lite for simple queries** - Faster response times
3. **Set appropriate timeout** - 180s for security analysis, 60s for simple queries
4. **Monitor token usage** - Response metadata includes token counts
5. **Use streaming for long responses** - Better UX for interactive applications
6. **Store credentials in environment** - Never commit API keys to git

## Comparison with Other Providers

| Feature | Yandex AI Studio | GigaChat | OpenAI |
|---------|------------------|----------|--------|
| API Compatibility | OpenAI-compatible | Custom SDK | Native |
| Best Model | Qwen3 235B | GigaChat-2-Pro | GPT-4 |
| Privacy Header | Yes (x-data-logging-enabled) | No | No |
| Russian Support | Excellent | Excellent | Good |
| Pricing | Pay-per-token | Pay-per-token | Pay-per-token |
| Max Context | 262K (Qwen3) | 32K | 128K (GPT-4) |
| Open Models | Qwen3, Gemma, gpt-oss | No | No |

## Resources

- [Yandex AI Studio Overview](https://yandex.cloud/en/services/ai-studio)
- [OpenAI Compatibility Documentation](https://yandex.cloud/en/docs/ai-studio/concepts/openai-compatibility)
- [Available Models](https://yandex.cloud/en/docs/ai-studio/concepts/generation/)
- [Yandex Cloud ML SDK](https://github.com/yandex-cloud/yandex-cloud-ml-sdk)
- [VS Code Integration Tutorial](https://yandex.cloud/en/docs/ai-studio/tutorials/qwen-vsc-integration)

## Next Steps

- [Installation](../getting-started/INSTALLATION.md) - Full setup guide
- [Configuration](../getting-started/CONFIGURATION.md) - All settings
- [TUI User Guide](../guides/TUI_USER_GUIDE.md) - Using the system
- [GigaChat Integration](./GIGACHAT.md) - Alternative LLM provider
