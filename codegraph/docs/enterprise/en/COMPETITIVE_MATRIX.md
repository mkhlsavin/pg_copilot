# CodeGraph Competitive Matrix

> Comparative Analysis for RFP and Decision Making

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [Comparison Summary Table](#comparison-summary-table)
- [CodeGraph Unique Advantages](#codegraph-unique-advantages)
  - [1. Only Platform with Integrated DLP](#1-only-platform-with-integrated-dlp)
  - [2. Only Platform with SIEM in Three Formats](#2-only-platform-with-siem-in-three-formats)
  - [3. Only Platform with Vault Integration](#3-only-platform-with-vault-integration)
  - [4. Taint-Verified Vulnerabilities](#4-taint-verified-vulnerabilities)
  - [5. Multi-Criteria Hypothesis Validation](#5-multi-criteria-hypothesis-validation)
- [Use Case Comparison](#use-case-comparison)
  - [Use Case 1: Enterprise Security Audit](#use-case-1-enterprise-security-audit)
  - [Use Case 2: AI-Assisted Code Review](#use-case-2-ai-assisted-code-review)
  - [Use Case 3: Compliance (152-FZ, GDPR)](#use-case-3-compliance-152-fz-gdpr)
- [Pricing Comparison (Approximate)](#pricing-comparison-approximate)
- [Requirements Compliance Matrix](#requirements-compliance-matrix)
  - [For Financial Organizations (GOST R 57580)](#for-financial-organizations-gost-r-57580)
  - [For Government Organizations](#for-government-organizations)
- [Conclusion](#conclusion)
- [Related Documents](#related-documents)

## Executive Summary

CodeGraph is the **only solution** combining:

- **CPG-based analysis** with taint-verified vulnerability detection
- **Integrated DLP protection** for LLM interactions
- **SIEM integration** in three formats (Syslog, CEF, LEEF)
- **Russian LLMs** (GigaChat, Yandex AI Studio) for 152-FZ compliance
- **Multi-criteria hypothesis validation** to reduce false positives

---

## Comparison Summary Table

| Feature | CodeGraph | GitHub Copilot | Sourcegraph | CodeScene | SonarQube |
|---------|:---------:|:--------------:|:-----------:|:---------:|:---------:|
| **Deployment** |
| On-Premise | ✅ | ❌ | ✅ | ✅ | ✅ |
| Air-Gapped | ✅ | ❌ | ⚠️ Partial | ⚠️ Partial | ✅ |
| Kubernetes | ✅ | ❌ | ✅ | ✅ | ✅ |
| Docker | ✅ | ❌ | ✅ | ✅ | ✅ |
| **Data Residency** |
| Code stays on-prem | ✅ | ❌ | ✅ | ✅ | ✅ |
| Russian LLM | ✅ GigaChat + Yandex AI Studio | ❌ | ❌ | ❌ | ❌ |
| 152-FZ compliance | ✅ | ❌ | ❌ | ❌ | ⚠️ |
| **Security** |
| RBAC | ✅ 4 roles, 21 perms | ⚠️ GitHub roles | ✅ | ✅ | ✅ |
| **Integrated DLP** | ✅ 25+ patterns | ❌ | ❌ | ❌ | ❌ |
| **SIEM Integration** | ✅ Syslog/CEF/LEEF | ❌ | ❌ | ❌ | ⚠️ Webhook |
| **HashiCorp Vault** | ✅ | ❌ | ❌ | ❌ | ❌ |
| JWT + API Keys | ✅ | ✅ GitHub tokens | ✅ | ✅ | ✅ |
| OAuth2/OIDC | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Code Analysis** |
| Code Property Graph | ✅ DuckDB CPG | ❌ | ✅ Custom | ⚠️ Behavioral | ❌ AST |
| Taint Analysis | ✅ | ❌ | ✅ | ❌ | ⚠️ Limited |
| **Taint-Verified Vulns** | ✅ | ❌ | ⚠️ Partial | ❌ | ❌ |
| Data Flow | ✅ | ❌ | ✅ | ❌ | ⚠️ |
| Control Flow | ✅ | ❌ | ✅ | ⚠️ | ⚠️ |
| **Vulnerability Detection** |
| SAST | ✅ | ❌ | ✅ | ✅ | ✅ |
| **Multi-Criteria Scoring** | ✅ | ❌ | ❌ | ❌ | ❌ |
| CWE/CAPEC mapping | ✅ | ❌ | ⚠️ | ⚠️ | ✅ |
| Hypothesis Validation | ✅ | ❌ | ❌ | ❌ | ❌ |
| **LLM Integration** |
| AI Copilot | ✅ | ✅ | ✅ Cody | ❌ | ❌ |
| LLM Security Layer | ✅ DLP + Audit | ❌ | ❌ | ❌ | ❌ |
| Prompt Protection | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Languages (13)** |
| C/C++ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Java | ✅ | ✅ | ✅ | ✅ | ✅ |
| Python | ✅ | ✅ | ✅ | ✅ | ✅ |
| JavaScript/TypeScript | ✅ | ✅ | ✅ | ✅ | ✅ |
| Go | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| C# | ✅ | ✅ | ✅ | ✅ | ✅ |
| Kotlin | ✅ | ✅ | ✅ | ⚠️ | ⚠️ |
| PHP | ✅ | ⚠️ | ✅ | ⚠️ | ✅ |
| Ruby | ✅ | ⚠️ | ✅ | ⚠️ | ✅ |
| Swift | ✅ | ✅ | ⚠️ | ❌ | ⚠️ |
| Ghidra (binary) | ✅ | ❌ | ❌ | ❌ | ❌ |
| LLVM IR | ✅ | ❌ | ❌ | ❌ | ❌ |

**Legend:** ✅ Full Support | ⚠️ Partial Support | ❌ Not Supported

---

## CodeGraph Unique Advantages

### 1. Only Platform with Integrated DLP

```
                    CodeGraph                    Competitors
                    ─────────                    ───────────
User Query ──► [DLP Scanner] ──► LLM       User Query ──► LLM
                    │                                │
                    ▼                                ▼
              Block/Mask/Log                   No protection
```

**Why This Matters:**
- Prevents secret leakage through LLM prompts
- Masks PII in LLM responses
- GDPR and data protection compliance

### 2. Only Platform with SIEM in Three Formats

| CodeGraph | GitHub Copilot | Sourcegraph | CodeScene |
|:---------:|:--------------:|:-----------:|:---------:|
| Syslog RFC 5424 | ❌ | ❌ | ❌ |
| CEF (ArcSight) | ❌ | ❌ | ❌ |
| LEEF (QRadar) | ❌ | ❌ | ❌ |

**Why This Matters:**
- Integration with existing SOC
- Centralized security monitoring
- Compliance audit trail

### 3. Only Platform with Vault Integration

```yaml
# CodeGraph
vault:
  enabled: true
  auth_method: approle
  auto_rotation: true

# Competitors: env vars or plaintext configs only
```

**Why This Matters:**
- Centralized secrets management
- Automatic API key rotation
- Kubernetes-native authorization

### 4. Taint-Verified Vulnerabilities

```
CodeGraph:
Source ──[data flow]──► Sink = CONFIRMED vulnerability

Traditional SAST:
Pattern match = POSSIBLE vulnerability (high false positive rate)
```

**Results:**
- 100% CVE detection rate (3/3 target CVEs)
- 60%+ false positive reduction
- Prioritization by actual risk

### 5. Multi-Criteria Hypothesis Validation

```
Priority Score = (CWE Frequency × 0.40)
               + (Attack Similarity × 0.30)
               + (Codebase Exposure × 0.30)
```

**Competitors:** Static severity without codebase context

---

## Use Case Comparison

### Use Case 1: Enterprise Security Audit

| Requirement | CodeGraph | GitHub Copilot | Sourcegraph |
|-------------|:---------:|:--------------:|:-----------:|
| Buffer overflow detection | ✅ CPG + Taint | ❌ | ✅ |
| Data flow verification | ✅ | ❌ | ✅ |
| Risk prioritization | ✅ Multi-criteria | ❌ | ⚠️ Severity only |
| LLM interaction audit | ✅ | ❌ | ❌ |
| SIEM reporting | ✅ | ❌ | ❌ |

### Use Case 2: AI-Assisted Code Review

| Requirement | CodeGraph | GitHub Copilot | Sourcegraph Cody |
|-------------|:---------:|:--------------:|:----------------:|
| AI-assisted review | ✅ | ✅ | ✅ |
| CPG-based analysis | ✅ | ❌ | ⚠️ |
| DLP protection | ✅ | ❌ | ❌ |
| On-premise LLM | ✅ | ❌ Cloud only | ⚠️ Limited |
| Audit trail | ✅ | ❌ | ⚠️ |

### Use Case 3: Compliance (152-FZ, GDPR)

| Requirement | CodeGraph | GitHub Copilot | Sourcegraph |
|-------------|:---------:|:--------------:|:-----------:|
| Data in Russia | ✅ On-prem | ❌ US cloud | ⚠️ On-prem |
| Russian LLM | ✅ GigaChat + Yandex AI Studio | ❌ | ❌ |
| DLP for PII | ✅ | ❌ | ❌ |
| Audit logging | ✅ | ⚠️ | ⚠️ |
| SIEM integration | ✅ | ❌ | ❌ |

---

## Pricing Comparison (Approximate)

| Solution | Model | Approximate Cost |
|----------|-------|------------------|
| **CodeGraph** | Per-developer | $40-50/dev/month |
| GitHub Copilot Business | Per-developer | $19/dev/month |
| GitHub Copilot Enterprise | Per-developer | $39/dev/month |
| Sourcegraph Enterprise | Per-developer | $49+/dev/month |
| CodeScene | Per-developer | Custom pricing |
| SonarQube Enterprise | Per-instance | $20K+/year |

**Note:** CodeGraph includes all enterprise features (DLP, SIEM, Vault) at no additional cost.

---

## Requirements Compliance Matrix

### For Financial Organizations (GOST R 57580)

| Requirement | CodeGraph | Alternatives |
|-------------|:---------:|:------------:|
| On-premise deployment | ✅ | ⚠️ |
| Full operation audit | ✅ | ⚠️ |
| Granular RBAC | ✅ | ⚠️ |
| SIEM integration | ✅ | ❌ |
| Encryption at-rest | ✅ | ✅ |
| Secrets management | ✅ Vault | ⚠️ |

### For Government Organizations

| Requirement | CodeGraph | Alternatives |
|-------------|:---------:|:------------:|
| 152-FZ compliance | ✅ | ❌ |
| Russian LLM | ✅ | ❌ |
| FSTEC certification (roadmap) | ⚠️ Planned | ❌ |
| Air-gapped deployment | ✅ | ⚠️ |

---

## Conclusion

CodeGraph is the **only solution** on the market combining:

1. **CPG-based analysis** with taint-verified vulnerabilities
2. **Integrated DLP** for LLM interaction protection
3. **SIEM integration** in three enterprise formats
4. **HashiCorp Vault** for secrets management
5. **Russian LLMs** (GigaChat + Yandex AI Studio) for 152-FZ compliance
6. **Multi-criteria validation** to reduce false positives

No competitor offers all these capabilities in a single solution.

---

## Related Documents

- [Enterprise Security Brief](./SECURITY_BRIEF.md) — Security overview
- [Hypothesis Validation Whitepaper](./HYPOTHESIS_WHITEPAPER.md) — Technical description
- [Business Case](../sber500/en/BUSINESS_CASE.md) — Business case

---

*Version: 1.0 | December 2025*
