# GigaChat Integration Guide

Integration guide for GigaChat API (Sber Russian LLM) with CodeGraph.

## Table of Contents

- [Overview](#overview)
- [Quick Setup (3 Steps)](#quick-setup-3-steps)
  - [Step 1: Set Authorization Key](#step-1-set-authorization-key)
  - [Step 2: Configure config.yaml](#step-2-configure-configyaml)
  - [Step 3: Verify](#step-3-verify)
- [Pre-configured Parameters](#pre-configured-parameters)
- [Available Models](#available-models)
- [Automated Setup](#automated-setup)
  - [PowerShell Script](#powershell-script)
  - [Using Template](#using-template)
- [Usage in Code](#usage-in-code)
  - [Basic Usage](#basic-usage)
  - [With CodeGraph](#with-codegraph)
- [Configuration Reference](#configuration-reference)
  - [Full config.yaml Example](#full-configyaml-example)
  - [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)
  - [Authentication Failed (401)](#authentication-failed-401)
  - [Connection Timeout](#connection-timeout)
  - [SSL Certificate Error](#ssl-certificate-error)
  - [Rate Limiting](#rate-limiting)
- [Best Practices](#best-practices)
- [Security Considerations](#security-considerations)
- [Resources](#resources)
- [Next Steps](#next-steps)

## Overview

GigaChat is a Russian LLM provider from Sberbank. CodeGraph supports GigaChat as an alternative to OpenAI, Yandex AI Studio, or local models.

> **Tip:** For larger context windows (up to 262K tokens), consider using [Yandex AI Studio](./YANDEX_AI_STUDIO.md) which offers Qwen3-235B and other models.

## Quick Setup (3 Steps)

### Step 1: Set Authorization Key

```powershell
# Windows PowerShell
$env:GIGACHAT_AUTH_KEY = "your_authorization_key"

# Permanent (survives restart)
[System.Environment]::SetEnvironmentVariable('GIGACHAT_AUTH_KEY', 'your_key', 'User')
```

```bash
# Linux/Mac
export GIGACHAT_AUTH_KEY="your_authorization_key"

# Add to ~/.bashrc for permanent
echo 'export GIGACHAT_AUTH_KEY="your_key"' >> ~/.bashrc
```

### Step 2: Configure config.yaml

```yaml
llm:
  provider: gigachat

  gigachat:
    client_id: "019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6"
    scope: "GIGACHAT_API_PERS"
    model: "GigaChat-2-Pro"
    temperature: 0.7
    max_tokens: 2000
    timeout: 60
```

### Step 3: Verify

```bash
python test_gigachat.py
```

Expected output:
```
GigaChat connection successful
Model: GigaChat-2-Pro
Status: Ready
```

## Pre-configured Parameters

| Parameter | Value |
|-----------|-------|
| Client ID | `019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6` |
| Scope | `GIGACHAT_API_PERS` |
| Model | `GigaChat-2-Pro` |
| Auth Key | Set via environment variable |

## Available Models

| Model | Description | Best For |
|-------|-------------|----------|
| GigaChat-2-Pro | Most capable | Complex analysis |
| GigaChat-2 | Standard | General use |
| GigaChat-Lite | Fastest | Simple queries |

## Automated Setup

### PowerShell Script

```powershell
# Run automated setup
.\setup_gigachat.ps1
```

The script will:
1. Prompt for Authorization Key
2. Create config.yaml from template
3. Install GigaChat SDK
4. Verify configuration

### Using Template

```bash
# Copy template
cp config.gigachat.yaml.example config.yaml

# Edit with your settings
notepad config.yaml
```

## Usage in Code

### Basic Usage

```python
import os
from langchain_gigachat import GigaChat

# Get auth key from environment
auth_key = os.getenv("GIGACHAT_AUTH_KEY")

# Initialize client
llm = GigaChat(
    credentials=auth_key,
    scope="GIGACHAT_API_PERS",
    model="GigaChat-2-Pro",
    verify_ssl_certs=False
)

# Make request
response = llm.invoke("What is PostgreSQL?")
print(response.content)
```

### With CodeGraph

```python
from src.llm.gigachat_provider import GigaChatProvider

# Initialize provider
provider = GigaChatProvider()

# Use with workflow
from src.workflow.langgraph_workflow_simple import run_workflow

result = run_workflow("Find transaction handling methods")
print(result['answer'])
```

## Configuration Reference

### Full config.yaml Example

```yaml
llm:
  provider: gigachat

  gigachat:
    # Required
    client_id: "019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6"
    scope: "GIGACHAT_API_PERS"
    model: "GigaChat-2-Pro"

    # Optional
    temperature: 0.7          # Creativity (0.0-1.0)
    max_tokens: 2000          # Max response length
    timeout: 60               # Request timeout (seconds)
    verify_ssl_certs: false   # SSL verification
    profanity_check: false    # Content filter

    # Rate limiting
    max_retries: 3
    retry_delay: 1.0
```

### Environment Variables

```bash
# Required
GIGACHAT_AUTH_KEY=your_authorization_key

# Optional
GIGACHAT_CLIENT_ID=019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6
GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_MODEL=GigaChat-2-Pro
```

## Troubleshooting

### Authentication Failed (401)

```
Error: 401 Unauthorized
```

**Solution:**
```bash
# Check if key is set
echo $GIGACHAT_AUTH_KEY

# Verify key format (should be base64)
python -c "import base64; base64.b64decode('$GIGACHAT_AUTH_KEY')"
```

### Connection Timeout

```
Error: Connection timed out
```

**Solution:**
```yaml
# Increase timeout in config.yaml
gigachat:
  timeout: 120  # seconds
```

### SSL Certificate Error

```
Error: SSL: CERTIFICATE_VERIFY_FAILED
```

**Solution:**
```yaml
# Disable SSL verification (not recommended for production)
gigachat:
  verify_ssl_certs: false
```

### Rate Limiting

```
Error: 429 Too Many Requests
```

**Solution:**
```yaml
gigachat:
  max_retries: 5
  retry_delay: 2.0  # seconds
```

## Best Practices

1. **Never commit auth keys** - Use environment variables
2. **Use GigaChat-2-Pro** - Best quality for code analysis
3. **Set appropriate timeout** - 60s for normal, 120s for complex
4. **Enable retries** - Handle transient failures

## Security Considerations

- Store auth keys in environment variables
- Add `.env` to `.gitignore`
- Use secure connection (HTTPS)
- Consider SSL verification in production

## Resources

- [GigaChat API Documentation](https://developers.sber.ru/docs/ru/gigachat)
- [LangChain GigaChat](https://python.langchain.com/docs/integrations/chat/gigachat)

## Next Steps

- [Installation](../getting-started/INSTALLATION.md) - Full setup
- [Configuration](../getting-started/CONFIGURATION.md) - All settings
- [TUI User Guide](../guides/TUI_USER_GUIDE.md) - Using the system
- [Yandex AI Studio Integration](./YANDEX_AI_STUDIO.md) - Alternative LLM provider (larger context)
