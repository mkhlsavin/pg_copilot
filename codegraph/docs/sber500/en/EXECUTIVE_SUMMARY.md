# CodeGraph: Executive Summary

## Table of Contents

- [AI-Powered Code Analysis Copilot](#ai-powered-code-analysis-copilot)
- [Overview](#overview)
- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [GigaChat Integration](#gigachat-integration)
  - [Role in the System](#role-in-the-system)
  - [Technical Configuration](#technical-configuration)
  - [API Usage](#api-usage)
- [Key Metrics](#key-metrics)
  - [Performance](#performance)
  - [Quality (Benchmark Results)](#quality-benchmark-results)
  - [Business Impact](#business-impact)
- [Technology Stack](#technology-stack)
  - [Production Readiness](#production-readiness)
- [Market Opportunity](#market-opportunity)
  - [TAM (Total Addressable Market)](#tam-total-addressable-market)
  - [SAM (Serviceable Available Market)](#sam-serviceable-available-market)
  - [SOM (Serviceable Obtainable Market)](#som-serviceable-obtainable-market)
- [Competitive Advantage](#competitive-advantage)
  - [Key Differentiators](#key-differentiators)
- [Roadmap](#roadmap)
  - [Q1 2025](#q1-2025)
  - [Q2 2025](#q2-2025)
  - [Q3-Q4 2025](#q3-q4-2025)
- [Unit Economics](#unit-economics)
  - [Cost per Query](#cost-per-query)
  - [Pricing (Subscription Model)](#pricing-subscription-model)
- [Request from Sber500](#request-from-sber500)
  - [What We Need](#what-we-need)
  - [What We Bring](#what-we-bring)
- [Demo Materials](#demo-materials)
- [Contact](#contact)

## AI-Powered Code Analysis Copilot

---

## Overview

**CodeGraph** is an AI-powered code analysis system that enables developers to ask natural language questions about large codebases and receive instant, accurate answers. Built on top of Sber's GigaChat LLM, it combines semantic understanding with structural code analysis through Code Property Graphs (CPG).

---

## The Problem

| Pain Point | Impact | Source |
|------------|--------|--------|
| Developers spend **60% of time** understanding existing code | Lost productivity | GitHub Survey 2023 |
| Manual code review misses **up to 80%** of vulnerabilities | Security risk | NIST Report |
| Onboarding new developers takes **3-6 months** | High costs | Industry Average |
| Documentation becomes outdated within **2-4 weeks** | Technical debt | Developer Survey |

---

## The Solution

CodeGraph provides:

1. **Interactive AI Assistant** — Answers questions about code in 2-3 seconds
2. **Automated Vulnerability Detection** — 12+ vulnerability types (CWE-classified)
3. **16 Ready-to-Use Scenarios** — From onboarding to security incident response
4. **Auto-Generated Documentation** — API docs, architecture diagrams
5. **Code Review Automation** — PR/MR analysis with actionable recommendations

---

## GigaChat Integration

### Role in the System

GigaChat is the **core intelligence** of CodeGraph, used across 4 specialized agents:

```
User Question
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  ANALYZER AGENT (GigaChat)                                  │
│  - Semantic understanding of user intent                    │
│  - Intent classification (security, architecture, debug)    │
│  - Scenario selection from 16 available workflows           │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  HYBRID RETRIEVAL                                           │
│  - Vector Search (ChromaDB): 250K+ documents                │
│  - Graph Search (DuckDB CPG): 52K methods, 111K edges       │
│  - RRF fusion for optimal results                           │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  ENRICHMENT AGENT (GigaChat)                                │
│  - Domain-specific context enrichment                       │
│  - 47 semantic tag categories                               │
│  - 15.68M tags for precise analysis                         │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  GENERATOR AGENT (GigaChat)                                 │
│  - SQL query generation for Code Property Graph             │
│  - Grammar-constrained generation                           │
│  - Query execution on DuckDB CPG                            │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  INTERPRETER AGENT (GigaChat)                               │
│  - Natural language synthesis of results                    │
│  - Severity grouping (Critical/High/Medium/Low)             │
│  - Actionable fix recommendations                           │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
Answer with specific file locations, line numbers, and recommendations
```

### Technical Configuration

```yaml
llm:
  provider: "gigachat"
  gigachat:
    model: "GigaChat-2-Pro"
    scope: "GIGACHAT_API_PERS"
    timeout: 60
    temperature: 0.7
    max_tokens: 2000
```

### API Usage

| Agent | Calls per Query | Purpose |
|-------|-----------------|---------|
| Analyzer | 1 | Intent classification |
| Enrichment | 1-2 | Context enrichment |
| Generator | 1 | Query generation |
| Interpreter | 1 | Response synthesis |
| **Total** | **4-5** | Per user question |

---

## Key Metrics

### Performance

| Metric | Value | Notes |
|--------|-------|-------|
| Query Latency | **2-3 ms** | 100x faster than traditional approaches |
| E2E Response | **< 5 sec** | Including all GigaChat calls |
| Throughput | **50+ QPS** | Supports 100+ concurrent users |
| Memory | **< 4 GB** | 90% savings vs vector-only |

### Quality (Benchmark Results)

| Metric | Vector-only | Graph-only | Hybrid (Ours) | Improvement |
|--------|-------------|------------|---------------|-------------|
| Precision@10 | 0.218 | 0.200 | **0.300** | +37.5% |
| Recall@10 | 0.433 | 0.354 | **0.553** | +27.8% |
| F1@10 | 0.286 | 0.251 | **0.383** | **+33.6%** |
| MRR | 1.000 | 0.636 | **1.000** | +57.1% |

### Business Impact

| Use Case | Before | After | ROI |
|----------|--------|-------|-----|
| Developer onboarding | 3-6 months | **2-4 weeks** | **6x faster** |
| Security audit | 2-4 weeks | **2-4 hours** | **40x faster** |
| Code review | 2-4 hours/PR | **10-15 min** | **10x faster** |
| Function search | 5-30 minutes | **2-3 seconds** | **600x faster** |

---

## Technology Stack

```
Frontend:     TUI (Rich library) + CLI
Backend:      Python 3.10+
LLM:          GigaChat API (langchain-gigachat)
Vector DB:    ChromaDB (250K+ documents)
Graph DB:     DuckDB (CPG: 52K methods, 111K edges)
CPG Storage:  DuckDB (exported from Joern)
Workflow:     LangGraph orchestration
Deployment:   Docker + Kubernetes
Monitoring:   Prometheus + Grafana
```

### Production Readiness

- 69,000+ lines of production Python code
- 924+ unit tests (100% pass rate)
- 16 specialized workflows
- 13 agents (5 RAG + 8 analytical)
- Docker + Kubernetes ready
- CI/CD pipeline (GitHub Actions)
- Prometheus/Grafana monitoring

---

## Market Opportunity

### TAM (Total Addressable Market)

- Global code analysis tools market: **$4.5B** (2024)
- CAGR: **15.8%** through 2030
- Expected size 2030: **$11.2B**

### SAM (Serviceable Available Market)

- Russian enterprise companies with C/C++ codebases: ~500 companies
- Potential: 2,000+ development teams
- Market size: ~**500M RUB/year**

### SOM (Serviceable Obtainable Market)

- Primary focus: FinTech + Telecom
- Year 1 target: **20-50 teams**
- Year 1 revenue: **12-30M RUB**

---

## Competitive Advantage

| Feature | GitHub Copilot | Sourcegraph | CodeScene | **CodeGraph** |
|---------|----------------|-------------|-----------|-----------------|
| LLM | OpenAI | Claude | - | **GigaChat** |
| Code Graph | - | + | + | **+** |
| Russian Language | - | - | - | **Native** |
| Data Sovereignty | - | - | + | **+ (Russia)** |
| On-Premise | - | + | + | **+** |

### Key Differentiators

1. **Native Russian language support** — Critical for Russian enterprise
2. **Data stays in Russia** — Compliance with local regulations
3. **Hybrid retrieval** — Best of vector + graph search
4. **Deep C/C++ specialization** — PostgreSQL, Linux Kernel expertise

---

## Roadmap

### Q1 2025
- Public beta release
- 10 pilot customers
- GitHub/GitLab integration

### Q2 2025
- Enterprise features (SSO, audit logs)
- Java/Python codebase support
- SaaS platform MVP

### Q3-Q4 2025
- 50+ paying customers
- Series A fundraising
- CIS market expansion

---

## Unit Economics

### Cost per Query

| Component | Cost |
|-----------|------|
| GigaChat API (4-5 calls) | ~0.5-2.0 RUB |
| Infrastructure | ~0.1 RUB |
| **Total** | **~0.6-2.1 RUB** |

### Pricing (Subscription Model)

| Tier | Price/month | Queries | Cost/query | Margin |
|------|-------------|---------|------------|--------|
| Starter | 15,000 RUB | 1,000 | 15 RUB | 85%+ |
| Professional | 50,000 RUB | 5,000 | 10 RUB | 80%+ |
| Enterprise | Custom | Unlimited | SLA-based | 70%+ |

---

## Request from Sber500

### What We Need

1. **Increased GigaChat API limits** — 50+ QPS for production workloads
2. **Access to GigaChat-2-Max** — For 15-20% quality improvement
3. **Technical support** — Prompt optimization for code analysis
4. **GTM mentorship** — Enterprise sales strategy
5. **Pilot customers** — 3-5 companies from Sber ecosystem

### What We Bring

1. **Production-ready product** — Not a prototype, a working system
2. **Strong GigaChat use case** — Showcase for DevTools vertical
3. **Integration potential** — SberCode, GigaCode ecosystem fit
4. **Revenue** — Paying enterprise customers in Year 1

---

## Demo Materials

| Material | Description | Status |
|----------|-------------|--------|
| Live Demo | TUI application on PostgreSQL 17 CPG | Ready |
| Video Demo | 5-minute walkthrough with voiceover | In progress |
| Jupyter Notebook | Interactive examples | Ready |
| Documentation | User guide + technical docs | Ready |

---

## Contact

**Product:** CodeGraph
**Application:** Sber500 x GigaChat Accelerator
**Date:** December 2024

---

*This document provides a high-level overview. Detailed technical documentation, benchmark results, and demo materials are available upon request.*
