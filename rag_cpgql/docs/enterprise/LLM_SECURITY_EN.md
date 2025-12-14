# LLM Integration Security

> Data Protection Guide for Working with LLM Providers

---

## Overview

The `SecureLLMProvider` module provides comprehensive protection when working with external LLM providers (GigaChat, OpenAI, etc.). The module implements the "defence in depth" principle — multi-layered data protection.

### Security Guarantees

| Guarantee | Implementation |
|-----------|----------------|
| **No code transmission** | Only NL queries sent to LLM |
| **Pre-request DLP** | Scanning before sending |
| **Post-response DLP** | Masking in responses |
| **Full audit** | Logging every request |
| **SIEM integration** | Real-time events |
| **Secrets in Vault** | API keys in HashiCorp Vault |

---

## Architecture

### Request Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SecureLLMProvider                               │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     1. PRE-REQUEST PHASE                         │   │
│  │                                                                  │   │
│  │  User Query ──► [DLP Scanner] ──┬──► BLOCK ──► DLPBlockedException │
│  │                                 │                                │   │
│  │                                 ├──► MASK ──► Masked Query       │   │
│  │                                 │                                │   │
│  │                                 └──► PASS ──► Original Query     │   │
│  │                                                    │              │   │
│  │                                    ┌───────────────┘              │   │
│  │                                    ▼                              │   │
│  │                             [SIEM Event]                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                       │                                 │
│                                       ▼                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    2. LLM PROVIDER CALL                          │   │
│  │                                                                  │   │
│  │  [VaultClient] ──► API Key ──► [GigaChat/OpenAI] ──► Response   │   │
│  │                                                                  │   │
│  │  • API key from Vault                                           │   │
│  │  • TLS connection                                               │   │
│  │  • Request ID tracking                                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                       │                                 │
│                                       ▼                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   3. POST-RESPONSE PHASE                         │   │
│  │                                                                  │   │
│  │  Response ──► [DLP Scanner] ──► Mask Sensitive Data ──► User    │   │
│  │                     │                                            │   │
│  │                     ▼                                            │   │
│  │              [SIEM Event]                                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                       │                                 │
│                                       ▼                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     4. AUDIT LOGGING                             │   │
│  │                                                                  │   │
│  │  • Request ID                  • Token usage                     │   │
│  │  • User ID                     • Latency                         │   │
│  │  • Session ID                  • DLP matches                     │   │
│  │  • IP address                  • Error details                   │   │
│  │                                                                  │   │
│  │  ──► [PostgreSQL] + [SIEM]                                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Protection Principles

### 1. Source Code Is Never Transmitted

```
┌──────────────────────────────────────────────────────────────────┐
│                      ORGANIZATION PERIMETER                       │
│                                                                  │
│   [Source Code] ──► [CPG Analysis] ──► [DuckDB]                 │
│                                           │                      │
│                                           ▼                      │
│   [User] ──► "Find buffer overflow in function X"               │
│                           │                                      │
│                           ▼                                      │
│                   [RAG Query Engine]                            │
│                           │                                      │
│                           ▼                                      │
│               NL Query (no code snippets)                       │
│                           │                                      │
└───────────────────────────┼──────────────────────────────────────┘
                            │
                            ▼
                     [GigaChat API]
                            │
                            ▼
               NL Response (explanation)
```

**What IS sent to LLM:**
- User text queries
- Metadata (function names, file names)
- Structured data from CPG

**What is NOT sent:**
- Source code
- File contents
- Connection strings
- Secrets and credentials

---

## API Reference

### SecureLLMProvider

```python
from src.security.llm import SecureLLMProvider
from src.security.config import get_security_config
from src.llm.gigachat import GigaChatProvider

# Create secure provider
base_provider = GigaChatProvider(config)
secure_provider = SecureLLMProvider(
    wrapped_provider=base_provider,
    config=get_security_config()
)

# Usage (with security context)
response = secure_provider.generate(
    system_prompt="You are a security analyst.",
    user_prompt="Analyze this function for vulnerabilities.",
    _user_id="analyst@company.com",
    _session_id="sess-12345",
    _ip_address="10.0.0.50"
)
```

### Methods

| Method | Description |
|--------|-------------|
| `generate(system_prompt, user_prompt, **kwargs)` | Generation with full protection |
| `generate_simple(prompt, **kwargs)` | Simplified call |
| `generate_stream(system_prompt, user_prompt, **kwargs)` | Streaming generation |
| `is_available()` | Check provider availability |

### Context Parameters

| Parameter | Description |
|-----------|-------------|
| `_user_id` | User ID for audit |
| `_session_id` | Session ID |
| `_ip_address` | Client IP address |

---

## Configuration

### Full Configuration (config.yaml)

```yaml
security:
  enabled: true

  # LLM interaction logging
  llm_logging:
    enabled: true
    log_prompts: true           # Log prompts
    redact_prompts: true        # Redact sensitive data
    max_prompt_length: 2000     # Max length in log
    log_responses: true         # Log responses
    max_response_length: 5000   # Max response length in log
    log_token_usage: true       # Log token usage
    log_latency: true           # Log latency
    log_to_database: true       # Save to PostgreSQL
    log_to_siem: true           # Send to SIEM

  # DLP configuration
  dlp:
    enabled: true
    pre_request:
      enabled: true
      default_action: WARN
    post_response:
      enabled: true
      default_action: MASK

  # SIEM integration
  siem:
    enabled: true
    syslog:
      enabled: true
      host: "siem.company.com"
      port: 514

  # HashiCorp Vault
  vault:
    enabled: true
    url: "https://vault.company.com:8200"
    auth_method: "approle"
    llm_secrets_path: "rag-cpgql/llm"
```

---

## Error Handling

### DLPBlockedException

```python
from src.security.dlp import DLPBlockedException

try:
    response = secure_provider.generate(
        system_prompt="...",
        user_prompt=user_input
    )
except DLPBlockedException as e:
    # Request blocked by DLP
    logger.warning(f"DLP blocked: {e.message}")

    # Violation information
    for match in e.matches:
        print(f"Category: {match.category}")
        print(f"Pattern: {match.pattern_name}")
        print(f"Severity: {match.severity}")

    # Return error to client
    return {
        "error": "dlp_blocked",
        "message": "Request contains sensitive data",
        "categories": e.to_dict()["categories"]
    }
```

### Error Structure

```json
{
  "error": "dlp_blocked",
  "message": "Request blocked by DLP policy. Detected 2 violation(s) in categories: credentials, pii. Please remove sensitive data before retrying.",
  "categories": ["credentials", "pii"],
  "violation_count": 2
}
```

---

## Secrets Management

### HashiCorp Vault Integration

```python
from src.security.vault import VaultClient
from src.security.config import get_security_config

config = get_security_config()
vault = VaultClient(config.vault)

# Get LLM credentials
credentials = vault.get_llm_credentials()

# Result:
# {
#   "gigachat_credentials": "...",
#   "openai_api_key": "sk-...",
#   "anthropic_api_key": "sk-ant-..."
# }
```

### Environment Variable Fallback

When Vault is unavailable, environment variables are used:

| Variable | Provider |
|----------|----------|
| `GIGACHAT_CREDENTIALS` | GigaChat |
| `OPENAI_API_KEY` | OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI |

---

## Auditing and Logging

### Request Log Structure

```json
{
  "timestamp": "2025-12-14T10:30:00.000Z",
  "request_id": "req-12345",
  "event": "llm_request",
  "provider": "GigaChatProvider",
  "model": "GigaChat-2-Pro",
  "user_id": "analyst@company.com",
  "session_id": "sess-67890",
  "ip_address": "10.0.0.50",
  "latency_ms": 1250.5,
  "tokens": {
    "prompt_tokens": 150,
    "completion_tokens": 450,
    "total_tokens": 600
  },
  "dlp": {
    "pre_request_matches": 0,
    "post_response_matches": 1,
    "action": "MASK"
  }
}
```

### SIEM Events

| Event | When Sent |
|-------|-----------|
| `LLM_REQUEST` | When sending request |
| `LLM_RESPONSE` | When receiving response |
| `LLM_ERROR` | On error |
| `DLP_BLOCK` | When DLP blocks |
| `DLP_MASK` | When masking |

---

## Streaming Generation

### Streaming Mode Specifics

```python
# Streaming generation with protection
for chunk in secure_provider.generate_stream(
    system_prompt="You are a security analyst.",
    user_prompt="Explain this vulnerability.",
    _user_id="analyst@company.com"
):
    # Chunk has already passed pre-request DLP
    print(chunk, end="", flush=True)

# Post-response DLP runs after stream completion
# If sensitive data detected - event to SIEM
```

**Streaming Limitations:**
- Pre-request DLP works fully
- Post-response DLP logs matches but cannot modify already-sent chunks
- Recommended for interactive scenarios with low risk

---

## Metrics and Monitoring

### Prometheus Metrics

```promql
# LLM request count
rate(llm_requests_total[5m])

# DLP block count
rate(dlp_blocks_total{phase="llm_request"}[5m])

# Average LLM latency
histogram_quantile(0.95, rate(llm_latency_seconds_bucket[5m]))

# Token usage
sum(rate(llm_tokens_total[1h])) by (provider, model)

# LLM errors
rate(llm_errors_total[5m])
```

### Grafana Dashboard

```json
{
  "panels": [
    {
      "title": "LLM Requests per Minute",
      "query": "rate(llm_requests_total[1m])"
    },
    {
      "title": "DLP Block Rate",
      "query": "rate(dlp_blocks_total{phase='llm_request'}[5m]) / rate(llm_requests_total[5m])"
    },
    {
      "title": "P95 Latency",
      "query": "histogram_quantile(0.95, rate(llm_latency_seconds_bucket[5m]))"
    },
    {
      "title": "Token Usage by Model",
      "query": "sum(rate(llm_tokens_total[1h])) by (model)"
    }
  ]
}
```

---

## Best Practices

### For Developers

1. **Always pass context** — `_user_id`, `_session_id`, `_ip_address`
2. **Handle DLPBlockedException** — inform the user
3. **Use streaming carefully** — understand post-DLP limitations
4. **Don't log full responses** — use `max_response_length`

### For Operators

1. **Monitor DLP block rate** — high rate may indicate a problem
2. **Set up LLM_ERROR alerts** — provider errors require attention
3. **Rotate API keys** — use Vault with auto-rotation
4. **Audit tokens** — track anomalous consumption

### For Compliance

1. **Document data flow** — what data goes where
2. **Retain logs** — minimum 1 year for compliance
3. **Regular audit** — verify DLP effectiveness
4. **Incident response** — plan for DLP_BLOCK response

---

## Related Documents

- [Enterprise Security Brief](./ENTERPRISE_SECURITY_BRIEF_EN.md) — Security overview
- [DLP Security](./DLP_SECURITY_EN.md) — DLP patterns and configuration
- [SIEM Integration](./SIEM_INTEGRATION_EN.md) — SIEM integration
- [Vault Integration](#) — Secrets management

---

*Version: 1.0 | December 2025*
