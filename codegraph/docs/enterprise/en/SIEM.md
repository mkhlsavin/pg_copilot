# SIEM Integration

> Integration Guide for SOC and Monitoring Teams

---

## Table of Contents

- [Overview](#overview)
  - [Key Capabilities](#key-capabilities)
- [Architecture](#architecture)
  - [System Components](#system-components)
- [Event Types](#event-types)
  - [SecurityEventType](#securityeventtype)
  - [Severity Levels (RFC 5424)](#severity-levels-rfc-5424)
- [Syslog Format (RFC 5424)](#syslog-format-rfc-5424)
  - [Message Structure](#message-structure)
  - [Example Message](#example-message)
  - [Configuration](#configuration)
  - [Splunk Integration](#splunk-integration)
- [CEF Format (ArcSight)](#cef-format-arcsight)
  - [Message Structure](#message-structure)
  - [Signature ID Mapping](#signature-id-mapping)
  - [Example Message](#example-message)
  - [Extension Fields](#extension-fields)
  - [CEF Configuration](#cef-configuration)
  - [ArcSight FlexConnector](#arcsight-flexconnector)
- [LEEF Format (QRadar)](#leef-format-qradar)
  - [Message Structure](#message-structure)
  - [Example Message](#example-message)
  - [LEEF Configuration](#leef-configuration)
  - [QRadar Log Source](#qradar-log-source)
- [Buffering and Reliability](#buffering-and-reliability)
  - [Buffer Configuration](#buffer-configuration)
  - [Failure Behavior](#failure-behavior)
  - [Buffer Statistics](#buffer-statistics)
- [API Reference](#api-reference)
  - [Creating Events](#creating-events)
  - [SIEMDispatcher API](#siemdispatcher-api)
- [Event Examples](#event-examples)
  - [DLP Block Event](#dlp-block-event)
  - [LLM Request Event](#llm-request-event)
  - [Auth Failure Event](#auth-failure-event)
- [Monitoring and Alerts](#monitoring-and-alerts)
  - [Grafana Dashboard](#grafana-dashboard)
  - [Prometheus Alerts](#prometheus-alerts)
- [Troubleshooting](#troubleshooting)
  - [Connection Testing](#connection-testing)
  - [Diagnostics](#diagnostics)
  - [Logging](#logging)
- [Related Documents](#related-documents)

## Overview

CodeGraph supports real-time security event dispatch to SIEM systems. Three formats are supported: Syslog (RFC 5424), CEF (ArcSight), and LEEF (QRadar).

### Key Capabilities

- **3 output formats**: Syslog RFC 5424, CEF, LEEF
- **13 event types**: LLM, DLP, Auth, Vault, Rate Limiting
- **3 transport protocols**: UDP, TCP, TLS
- **Buffering**: up to 10,000 events in queue
- **Retry with backoff**: automatic retry on failures
- **Graceful degradation**: continued operation when SIEM unavailable

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                         APPLICATION                                  │
│                                                                     │
│  [LLM Provider] ──┐                                                 │
│                   │                                                 │
│  [DLP Scanner] ───┼──► [SecurityEvent] ──► [SIEMDispatcher]        │
│                   │                              │                  │
│  [Auth Module] ───┘                              │                  │
│                                                  │                  │
│                                           ┌──────▼──────┐           │
│                                           │ SIEMBuffer  │           │
│                                           │ (10K queue) │           │
│                                           └──────┬──────┘           │
│                                                  │                  │
│                    ┌─────────────────────────────┼─────────────────┐│
│                    │                             │                 ││
│                    ▼                             ▼                 ▼│
│           ┌──────────────┐            ┌──────────────┐    ┌──────────────┐│
│           │SysLogHandler │            │  CEFHandler  │    │ LEEFHandler  ││
│           │  (RFC 5424)  │            │  (ArcSight)  │    │  (QRadar)    ││
│           └──────┬───────┘            └──────┬───────┘    └──────┬───────┘│
└──────────────────┼───────────────────────────┼───────────────────┼────────┘
                   │                           │                   │
                   ▼                           ▼                   ▼
            ┌────────────┐              ┌────────────┐      ┌────────────┐
            │  Splunk    │              │  ArcSight  │      │  QRadar    │
            │  Graylog   │              │  Splunk    │      │            │
            │  rsyslog   │              │            │      │            │
            └────────────┘              └────────────┘      └────────────┘
```

---

## Event Types

### SecurityEventType

| Event Type | Description | Severity |
|------------|-------------|----------|
| `LLM_REQUEST` | Request to LLM provider | INFO (6) |
| `LLM_RESPONSE` | Response from LLM | INFO (6) |
| `LLM_ERROR` | LLM interaction error | ERROR (3) |
| `DLP_BLOCK` | Request blocked by DLP | CRITICAL (2) |
| `DLP_MASK` | Data masked | WARNING (4) |
| `DLP_WARN` | DLP warning | WARNING (4) |
| `DLP_LOG` | DLP logging | INFO (6) |
| `AUTH_SUCCESS` | Successful authentication | INFO (6) |
| `AUTH_FAILURE` | Failed authentication | WARNING (4) |
| `VAULT_ACCESS` | Vault secrets access | INFO (6) |
| `VAULT_ROTATE` | Secrets rotation | NOTICE (5) |
| `RATE_LIMIT` | Rate limit exceeded | WARNING (4) |
| `SECURITY_ALERT` | Critical security event | ALERT (1) |

### Severity Levels (RFC 5424)

| Code | Level | Description |
|:----:|-------|-------------|
| 0 | EMERGENCY | System unusable |
| 1 | ALERT | Immediate action required |
| 2 | CRITICAL | Critical condition |
| 3 | ERROR | Error condition |
| 4 | WARNING | Warning condition |
| 5 | NOTICE | Normal but significant |
| 6 | INFO | Informational message |
| 7 | DEBUG | Debug message |

---

## Syslog Format (RFC 5424)

### Message Structure

```
<PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID [STRUCTURED-DATA] MSG
```

### Example Message

```
<134>1 2025-12-14T10:30:00.000Z codegraph-server codegraph 12345 DLP001
[dlp@12345 category="credentials" pattern="aws_access_key" action="BLOCK"]
DLP blocked request: AWS access key detected in user prompt
```

### Configuration

```yaml
security:
  siem:
    enabled: true
    syslog:
      enabled: true
      protocol: udp      # udp, tcp, tls
      host: "siem.company.com"
      port: 514
      facility: 16       # LOCAL0 (16-23)
      app_name: "codegraph"
      hostname: null     # Auto-detect
      tls:               # Only for protocol: tls
        ca_cert: "/path/to/ca.crt"
        client_cert: "/path/to/client.crt"
        client_key: "/path/to/client.key"
        verify: true
```

### Splunk Integration

```conf
# inputs.conf
[udp://514]
sourcetype = syslog
index = security

# props.conf
[syslog]
TIME_FORMAT = %Y-%m-%dT%H:%M:%S.%3N%Z
SHOULD_LINEMERGE = false
```

---

## CEF Format (ArcSight)

### Message Structure

```
CEF:Version|Device Vendor|Device Product|Device Version|Signature ID|Name|Severity|Extension
```

### Signature ID Mapping

| Event Type | Signature ID | Name |
|------------|--------------|------|
| `llm.request` | LLM001 | LLM Request |
| `llm.response` | LLM002 | LLM Response |
| `llm.error` | LLM003 | LLM Error |
| `dlp.block` | DLP001 | DLP Block |
| `dlp.mask` | DLP002 | DLP Mask |
| `dlp.warn` | DLP003 | DLP Warning |
| `auth.success` | AUTH01 | Auth Success |
| `auth.failure` | AUTH02 | Auth Failure |
| `vault.access` | VLT001 | Vault Access |
| `security.alert` | SEC001 | Security Alert |

### Example Message

```
CEF:0|CodeGraph|CodeAnalysis|1.0|DLP001|DLP Block|8|
src=10.0.0.50 suser=analyst@company.com externalId=req-12345
msg=AWS access key detected rt=2025-12-14T10:30:00.000Z
cs1=GigaChat cs1Label=LLM Provider
cs4=credentials cs4Label=DLP Category
cs5=aws_access_key cs5Label=DLP Pattern
cn2=125 cn2Label=Latency MS
```

### Extension Fields

| Field | CEF Key | Description |
|-------|---------|-------------|
| IP Address | `src` | Source IP |
| User ID | `suser` | User identifier |
| Request ID | `externalId` | Request ID |
| Message | `msg` | Message text |
| Timestamp | `rt` | Event time |
| LLM Provider | `cs1` | LLM provider |
| LLM Model | `cs2` | LLM model |
| Action | `cs3` | Action taken |
| DLP Category | `cs4` | DLP category |
| DLP Pattern | `cs5` | DLP pattern |
| Tokens Used | `cn1` | Tokens used |
| Latency MS | `cn2` | Latency in ms |

### CEF Configuration

```yaml
security:
  siem:
    cef:
      enabled: true
      host: "arcsight.company.com"
      port: 514
      protocol: tcp
      device_vendor: "CodeGraph"
      device_product: "CodeAnalysis"
      device_version: "1.0"
```

### ArcSight FlexConnector

```xml
<!-- connector.parser.xml -->
<parser>
  <name>CodeGraph CEF Parser</name>
  <pattern>CEF:0|CodeGraph|CodeAnalysis|.*</pattern>
</parser>
```

---

## LEEF Format (QRadar)

### Message Structure

```
LEEF:Version|Vendor|Product|Version|EventID|Extension
```

### Example Message

```
LEEF:2.0|CodeGraph|CodeAnalysis|1.0|DLP001|
cat=DLP	sev=8	src=10.0.0.50	usrName=analyst
msg=AWS access key detected	devTime=2025-12-14T10:30:00.000Z
```

### LEEF Configuration

```yaml
security:
  siem:
    leef:
      enabled: true
      host: "qradar.company.com"
      port: 514
      protocol: udp
      product_vendor: "CodeGraph"
      product_name: "CodeAnalysis"
      product_version: "1.0"
```

### QRadar Log Source

1. Admin → Log Sources → Add
2. Vendor: `CodeGraph`
3. Log Source Type: `Universal LEEF`
4. Protocol: Syslog
5. Port: 514

---

## Buffering and Reliability

### Buffer Configuration

```yaml
security:
  siem:
    buffer:
      max_size: 10000           # Maximum events in queue
      flush_interval_seconds: 5  # Flush interval
      retry_attempts: 3          # Retry count
      retry_backoff_seconds: 2.0 # Delay between retries
```

### Failure Behavior

1. **First attempt** — immediate send
2. **Failure** — event queued, retry in 2 sec
3. **Second failure** — retry in 4 sec (backoff × 2)
4. **Third failure** — retry in 8 sec
5. **After 3 failures** — event to fallback log

### Buffer Statistics

```python
dispatcher = get_siem_dispatcher()
stats = dispatcher.stats

print(f"Events in queue: {stats['queue_size']}")
print(f"Sent: {stats['sent_count']}")
print(f"Failed: {stats['failed_count']}")
print(f"Retry pending: {stats['retry_pending']}")
```

---

## API Reference

### Creating Events

```python
from src.security.siem.base_handler import SecurityEvent, SecurityEventType
from src.security.siem.dispatcher import dispatch_security_event

# Create event
event = SecurityEvent.create(
    event_type=SecurityEventType.DLP_BLOCK,
    message="AWS access key detected in user prompt",
    request_id="req-12345",
    severity=2,  # CRITICAL
    user_id="user_123",
    ip_address="10.0.0.50",
    dlp_category="credentials",
    dlp_pattern="aws_access_key",
    action="BLOCK"
)

# Send to SIEM
success = dispatch_security_event(event)
```

### SIEMDispatcher API

```python
from src.security.siem.dispatcher import SIEMDispatcher, init_siem_dispatcher
from src.security.config import get_security_config

# Initialize
config = get_security_config()
dispatcher = init_siem_dispatcher(config.siem)

# Async dispatch (via buffer)
dispatcher.dispatch(event)

# Sync dispatch (bypass buffer, for critical events)
dispatcher.dispatch_sync(event)

# Flush buffer
sent_count = dispatcher.flush()

# Statistics
print(dispatcher.stats)
print(f"Handlers: {dispatcher.handler_count}")
print(f"Enabled: {dispatcher.is_enabled}")

# Close
dispatcher.close()
```

---

## Event Examples

### DLP Block Event

```json
{
  "event_type": "dlp.block",
  "timestamp": "2025-12-14T10:30:00.000Z",
  "request_id": "req-12345",
  "severity": 2,
  "message": "DLP blocked request: AWS access key detected",
  "user_id": "analyst@company.com",
  "ip_address": "10.0.0.50",
  "dlp_category": "credentials",
  "dlp_pattern": "aws_access_key",
  "action": "BLOCK"
}
```

### LLM Request Event

```json
{
  "event_type": "llm.request",
  "timestamp": "2025-12-14T10:30:00.000Z",
  "request_id": "req-67890",
  "severity": 6,
  "message": "LLM request to GigaChat",
  "user_id": "analyst@company.com",
  "provider": "GigaChat",
  "model": "GigaChat-2-Pro",
  "tokens_used": 150,
  "latency_ms": 1250.5
}
```

### Auth Failure Event

```json
{
  "event_type": "auth.failure",
  "timestamp": "2025-12-14T10:30:00.000Z",
  "request_id": "req-11111",
  "severity": 4,
  "message": "Authentication failed: invalid credentials",
  "user_id": "unknown",
  "ip_address": "10.0.0.99",
  "details": {
    "reason": "invalid_password",
    "attempts": 3
  }
}
```

---

## Monitoring and Alerts

### Grafana Dashboard

```json
{
  "panels": [
    {
      "title": "SIEM Events per Minute",
      "query": "rate(siem_events_sent_total[1m])"
    },
    {
      "title": "SIEM Queue Size",
      "query": "siem_buffer_queue_size"
    },
    {
      "title": "SIEM Failures",
      "query": "rate(siem_events_failed_total[5m])"
    }
  ]
}
```

### Prometheus Alerts

```yaml
groups:
  - name: siem
    rules:
      - alert: SIEMQueueBacklog
        expr: siem_buffer_queue_size > 5000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "SIEM queue backlog detected"

      - alert: SIEMConnectionFailed
        expr: rate(siem_events_failed_total[5m]) > 10
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "SIEM connection failures detected"
```

---

## Troubleshooting

### Connection Testing

```bash
# Test UDP
echo "<134>1 test message" | nc -u siem.company.com 514

# Test TCP
echo "<134>1 test message" | nc siem.company.com 514

# Test TLS
openssl s_client -connect siem.company.com:6514
```

### Diagnostics

```python
# Check dispatcher status
from src.security.siem.dispatcher import get_siem_dispatcher

dispatcher = get_siem_dispatcher()
if dispatcher:
    print(f"Enabled: {dispatcher.is_enabled}")
    print(f"Handlers: {dispatcher.handler_count}")
    print(f"Stats: {dispatcher.stats}")
else:
    print("SIEM dispatcher not initialized")
```

### Logging

```yaml
# logging.yaml
loggers:
  src.security.siem:
    level: DEBUG
    handlers: [console, file]
```

---

## Related Documents

- [Enterprise Security Brief](./SECURITY_BRIEF.md) — Security overview
- [DLP Security](./DLP_SECURITY.md) — DLP integration
- [LLM Security](./LLM_SECURITY.md) — LLM security

---

*Version: 1.0 | December 2025*
