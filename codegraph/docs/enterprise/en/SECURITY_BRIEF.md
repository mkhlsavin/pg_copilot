# CodeGraph: Enterprise Security Brief

> Document for CISOs, Security Executives, and Security Architects

---

## Table of Contents

- [Executive Summary](#executive-summary)
  - [Key Security Capabilities](#key-security-capabilities)
- [1. Data Residency and Sovereignty](#1-data-residency-and-sovereignty)
  - [Data Processing Principles](#data-processing-principles)
  - [Data Security Guarantees](#data-security-guarantees)
  - [Compliance](#compliance)
- [2. Access Control and Authentication](#2-access-control-and-authentication)
  - [RBAC Role Hierarchy](#rbac-role-hierarchy)
  - [Permission Matrix (21 Permissions)](#permission-matrix-21-permissions)
  - [Authentication Methods](#authentication-methods)
- [3. Data Loss Prevention (DLP)](#3-data-loss-prevention-dlp)
  - [DLP Scanning Architecture](#dlp-scanning-architecture)
  - [Detection Categories (25+ Patterns)](#detection-categories-25-patterns)
  - [DLP Actions](#dlp-actions)
- [4. SIEM Integration](#4-siem-integration)
  - [Supported Formats](#supported-formats)
  - [Security Event Types](#security-event-types)
  - [Delivery Architecture](#delivery-architecture)
- [5. Secrets Management](#5-secrets-management)
  - [HashiCorp Vault Integration](#hashicorp-vault-integration)
  - [Managed Secrets](#managed-secrets)
  - [Security](#security)
- [Competitive Advantages](#competitive-advantages)
- [Contact](#contact)

## Executive Summary

**CodeGraph** is a static code analysis platform powered by Code Property Graph (CPG), designed with enterprise security requirements in mind. The platform provides complete data control, integration with enterprise security infrastructure, and compliance with regulatory requirements.

### Key Security Capabilities

| Capability | Description |
|------------|-------------|
| **On-Premise Deployment** | Code never leaves your infrastructure |
| **GigaChat + Yandex AI Studio** | Russian LLMs (Qwen3-235B, YandexGPT) — only queries transmitted, not code |
| **RBAC** | 4 roles, 21 permissions, granular access control |
| **DLP** | 25+ patterns for sensitive data detection |
| **SIEM** | Integration with Syslog, ArcSight (CEF), QRadar (LEEF) |
| **Vault** | HashiCorp Vault for secrets management |

---

## 1. Data Residency and Sovereignty

### Data Processing Principles

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORGANIZATION PERIMETER                        │
│                                                                 │
│  [Source Code] ──► [CPG Analysis] ──► [DuckDB Storage]         │
│                          │                                      │
│                     Code remains                                │
│                     inside perimeter                            │
│                          │                                      │
│  [User] ──► [RAG Query] ──► [DLP Scanner] ──┐                  │
│                                              │                  │
└──────────────────────────────────────────────│──────────────────┘
                                               │
                          Only NL queries ─────►│
                          (no source code)      │
                                               ▼
                                        [GigaChat / Yandex AI Studio API]
```

### Data Security Guarantees

| Aspect | Implementation |
|--------|----------------|
| **Code Storage** | Local only (DuckDB, file system) |
| **Data Transmission** | Source code is never sent to external systems |
| **LLM Integration** | GigaChat/Yandex AI Studio receives only user text queries |
| **Air-Gapped Mode** | Support for fully isolated environments with local LLMs |

### Compliance

- **152-FZ** — Processing of Russian citizens' personal data within Russia
- **GOST R 57580** — Information protection in financial organizations
- **FSTEC Requirements** — Deployment capability in certified infrastructure
- **GDPR** — Data minimization principles (code not transmitted)
- **SOX** — Complete audit trail for compliance

---

## 2. Access Control and Authentication

### RBAC Role Hierarchy

```
                    ┌─────────────┐
                    │    ADMIN    │ ← Full access (admin:all)
                    │  (Level 4)  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  REVIEWER   │ ← Code review + Analyst capabilities
                    │  (Level 3)  │   (GitHub/GitLab integration)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   ANALYST   │ ← Query execution + sessions
                    │  (Level 2)  │   (API keys, export)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   VIEWER    │ ← Read-only access
                    │  (Level 1)  │   (scenarios, history, stats)
                    └─────────────┘
```

### Permission Matrix (21 Permissions)

| Category | Permissions | VIEWER | ANALYST | REVIEWER | ADMIN |
|----------|-------------|:------:|:-------:|:--------:|:-----:|
| **Scenarios** | scenarios:read | ✓ | ✓ | ✓ | ✓ |
| | scenarios:execute | | ✓ | ✓ | ✓ |
| **Queries** | query:execute | | ✓ | ✓ | ✓ |
| | query:validate | | ✓ | ✓ | ✓ |
| **Review** | review:execute | | | ✓ | ✓ |
| | review:github | | | ✓ | ✓ |
| | review:gitlab | | | ✓ | ✓ |
| **Sessions** | sessions:read | ✓ | ✓ | ✓ | ✓ |
| | sessions:write | | ✓ | ✓ | ✓ |
| | sessions:delete | | ✓ | ✓ | ✓ |
| **History** | history:read | ✓ | ✓ | ✓ | ✓ |
| | history:export | | ✓ | ✓ | ✓ |
| **Users** | users:read | | | | ✓ |
| | users:write | | | | ✓ |
| | users:delete | | | | ✓ |
| **API Keys** | api_keys:read | | ✓ | ✓ | ✓ |
| | api_keys:write | | ✓ | ✓ | ✓ |
| | api_keys:delete | | | | ✓ |
| **Metrics** | stats:read | ✓ | ✓ | ✓ | ✓ |
| | metrics:read | | | | ✓ |
| **Admin** | admin:all | | | | ✓ |

### Authentication Methods

| Method | Description | Status |
|--------|-------------|--------|
| **JWT Bearer** | Access tokens (30 min) + Refresh tokens (7 days) | ✅ Implemented |
| **API Keys** | SHA-256 hashing, expiration, revocation | ✅ Implemented |
| **OAuth2/OIDC** | GitHub, GitLab, Google, Keycloak | ✅ Integration-ready |
| **LDAP/AD** | Group sync, SSO | ✅ Integration-ready |

---

## 3. Data Loss Prevention (DLP)

### DLP Scanning Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      USER REQUEST                            │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  PRE-REQUEST SCANNING                        │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Patterns: API keys, passwords, tokens, PII, paths      │  │
│  └────────────────────────────────────────────────────────┘  │
│                           │                                  │
│            ┌──────────────┼──────────────┐                   │
│            ▼              ▼              ▼                   │
│        [BLOCK]        [MASK]        [WARN/LOG]              │
│      Reject         Mask          Send with                 │
│      request        data          logging                   │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
                  [GigaChat / Yandex AI Studio API]
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                 POST-RESPONSE SCANNING                       │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Mask sensitive data in LLM response before display     │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### Detection Categories (25+ Patterns)

| Category | Severity | Example Patterns |
|----------|----------|------------------|
| **Credentials** | HIGH | AWS keys (`AKIA...`), GitHub tokens (`ghp_...`), passwords, JWT, RSA/EC private keys |
| **Personal Data** | MEDIUM | Email, phone numbers (RU/US), passport numbers, SSN, credit cards |
| **Source Code** | LOW | Database connection strings, internal Unix/Windows paths |

### DLP Actions

| Action | Priority | Description |
|--------|----------|-------------|
| `BLOCK` | 4 (max) | Complete request blocking |
| `MASK` | 3 | Replace sensitive data with `[REDACTED]` |
| `WARN` | 2 | Warning + SIEM event dispatch |
| `LOG_ONLY` | 1 | Audit logging only |

---

## 4. SIEM Integration

### Supported Formats

| Format | Compatible Systems | Description |
|--------|-------------------|-------------|
| **Syslog (RFC 5424)** | Splunk, Graylog, rsyslog | Standard Unix format |
| **CEF** | ArcSight, Splunk | Common Event Format |
| **LEEF** | IBM QRadar | Log Event Extended Format |

### Security Event Types

```
EVENT_TYPE              SEVERITY    DESCRIPTION
────────────────────────────────────────────────────────────
LLM_REQUEST             INFO        Request to LLM provider
LLM_RESPONSE            INFO        Response from LLM
LLM_ERROR               ERROR       LLM interaction error
DLP_BLOCK               CRITICAL    Request blocked by DLP
DLP_MASK                WARNING     Data masked
DLP_WARN                WARNING     DLP warning
AUTH_SUCCESS            INFO        Successful authentication
AUTH_FAILURE            WARNING     Failed login attempt
VAULT_ACCESS            INFO        Vault secrets access
VAULT_ROTATE            INFO        Secrets rotation
RATE_LIMIT              WARNING     Rate limit exceeded
SECURITY_ALERT          CRITICAL    Critical security event
```

### Delivery Architecture

- **Buffering**: Up to 10,000 events in queue
- **Retry**: Exponential backoff on failures
- **Failover**: Continued operation when SIEM is unavailable

---

## 5. Secrets Management

### HashiCorp Vault Integration

| Authentication Method | Use Case |
|----------------------|----------|
| **Token** | Development, testing |
| **AppRole** | CI/CD pipelines, services |
| **Kubernetes** | K8s clusters with ServiceAccount |

### Managed Secrets

- **LLM Providers**: GigaChat, Yandex AI Studio (Qwen3-235B, YandexGPT), OpenAI
- **Database**: PostgreSQL, DuckDB credentials
- **Integrations**: GitHub/GitLab tokens, SIEM credentials

### Security

- KV v2 Secret Engine with versioning
- TTL caching with automatic rotation
- Environment variable fallback when Vault unavailable

---

## Competitive Advantages

| Feature | CodeGraph | GitHub Copilot | Sourcegraph | CodeScene |
|---------|:---------:|:--------------:|:-----------:|:---------:|
| On-Premise Deployment | ✅ | ❌ | ✅ | ✅ |
| Integrated DLP | ✅ | ❌ | ❌ | ❌ |
| Multi-Format SIEM | ✅ | ❌ | ❌ | ❌ |
| Vault Integration | ✅ | ❌ | ❌ | ❌ |
| Russian LLM (GigaChat + Yandex AI Studio) | ✅ | ❌ | ❌ | ❌ |
| CPG-based Analysis | ✅ | ❌ | ✅ | ✅ |
| Taint-Verified Vulnerabilities | ✅ | ❌ | Partial | ❌ |

---

## Contact

**For security and integration inquiries:**

- Email: security@codegraph.ru

---

*Version: 1.0 | December 2025*
