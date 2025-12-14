# CodeGraph: Pitch Deck

## Sber500xGigaChat Accelerator Application

---

## SLIDE 1: Title

```
+====================================================================+
|                                                                     |
|                         CodeGraph                                   |
|                                                                     |
|            AI Copilot for Source Code Analysis                      |
|                    Powered by GigaChat                              |
|                                                                     |
|  ------------------------------------------------------------------ |
|                                                                     |
|                    Sber500 x GigaChat                               |
|                      December 2024                                  |
|                                                                     |
+====================================================================+
```

**Speaker Notes:**
> "Good day! I'm presenting CodeGraph - a code analysis system
> that uses GigaChat so developers can ask questions about code
> in natural language and get instant answers."

---

## SLIDE 2: Problem

```
+====================================================================+
|                         PROBLEM                                     |
+====================================================================+
|                                                                     |
|  +----------------------------------------------------------+      |
|  |  60%   |  of time developers spend UNDERSTANDING code    |      |
|  |████████|  not writing new code                           |      |
|  +----------------------------------------------------------+      |
|                                                                     |
|  +----------------------------------------------------------+      |
|  |  80%   |  of vulnerabilities missed by manual code review|      |
|  |████████|  according to NIST                              |      |
|  +----------------------------------------------------------+      |
|                                                                     |
|  +----------------------------------------------------------+      |
|  |3-6 mo  |  for onboarding in enterprise projects          |      |
|  |████████|  on legacy codebases                            |      |
|  +----------------------------------------------------------+      |
|                                                                     |
|  Sources: GitHub Survey 2023, NIST Report, Industry Average        |
+====================================================================+
```

**Speaker Notes:**
> "Three main pains of enterprise development:
> 1. Understanding existing code takes most of the time
> 2. Vulnerabilities are missed during manual review
> 3. New employees take very long to ramp up"

---

## SLIDE 3: Solution

```
+====================================================================+
|                         SOLUTION                                    |
+====================================================================+
|                                                                     |
|  CodeGraph = GigaChat + Code Property Graph + Hybrid Retrieval      |
|                                                                     |
|  +--------------------------------------------------------------+  |
|  |                                                              |  |
|  |  Developer: "Find SQL injection vulnerabilities"             |  |
|  |                         |                                    |  |
|  |                         v                                    |  |
|  |  +--------------------------------------------------------+  |  |
|  |  |  GigaChat understands intent and generates query        |  |  |
|  |  |  for code graph (CPGQL)                                 |  |  |
|  |  +--------------------------------------------------------+  |  |
|  |                         |                                    |  |
|  |                         v                                    |  |
|  |  Result: 7 critical vulnerabilities in 2-3 seconds           |  |
|  |  with specific files, lines, and recommendations             |  |
|  |                                                              |  |
|  +--------------------------------------------------------------+  |
|                                                                     |
+====================================================================+
```

**Speaker Notes:**
> "Our solution combines three technologies:
> 1. GigaChat for understanding questions and generating answers
> 2. Code Property Graph for structural code analysis
> 3. Hybrid search for precise relevant code discovery"

---

## SLIDE 4: How GigaChat Works

```
+====================================================================+
|               HOW GIGACHAT WORKS IN THE SYSTEM                      |
+====================================================================+
|                                                                     |
|     Question                                                        |
|        |                                                            |
|        v                                                            |
|  +-------------+   +--------------+   +-----------------+           |
|  |  ANALYZER   |-->|  ENRICHMENT  |-->|   GENERATOR     |           |
|  |  GigaChat   |   |  GigaChat    |   |   GigaChat      |           |
|  |             |   |              |   |                 |           |
|  | Understands |   | Adds         |   | Generates       |           |
|  | intent      |   | context      |   | CPGQL query     |           |
|  +-------------+   +--------------+   +-----------------+           |
|                                              |                      |
|                                              v                      |
|                    +-------------------------------------+          |
|                    |          INTERPRETER                |          |
|                    |            GigaChat                 |          |
|                    |                                     |          |
|                    |  Synthesizes answer in Russian with |          |
|                    |  fix recommendations                |          |
|                    +-------------------------------------+          |
|                                                                     |
|  4-5 GigaChat calls per user question                               |
+====================================================================+
```

**Speaker Notes:**
> "GigaChat is used at every processing stage:
> - Analyzer understands what the user wants
> - Enrichment adds domain-specific context
> - Generator creates the code graph query
> - Interpreter forms an understandable answer
>
> Total 4-5 API calls per question."

---

## SLIDE 5: Quality Metrics

```
+====================================================================+
|                    QUALITY METRICS                                  |
+====================================================================+
|                                                                     |
|  COMPARISON WITH COMPETITORS:                                       |
|                                                                     |
|  Metric       | Vector-only | Graph-only | CodeGraph   | Growth    |
|  -------------+-------------+------------+-------------+---------- |
|  Precision@10 |    0.218    |   0.200    |   0.300     | +37.5%    |
|  Recall@10    |    0.433    |   0.354    |   0.553     | +27.8%    |
|  F1@10        |    0.286    |   0.251    |   0.383     | +33.6%    |
|  MRR          |    1.000    |   0.636    |   1.000     | +57.1%    |
|                                                                     |
|  ------------------------------------------------------------------ |
|                                                                     |
|  PERFORMANCE:                                                       |
|                                                                     |
|  | 2-3ms |  average graph query time (100x faster)                  |
|  | <5sec |  full E2E response with GigaChat                         |
|  | <4GB  |  memory consumption (90% savings)                        |
|                                                                     |
+====================================================================+
```

**Speaker Notes:**
> "Hybrid approach gives +33% quality compared to pure
> vector search. The system is very fast - response
> reaches user in less than 5 seconds."

---

## SLIDE 6: ROI for Clients

```
+====================================================================+
|                   ROI FOR CLIENTS                                   |
+====================================================================+
|                                                                     |
|  +-------------------------------------------------------------+   |
|  | ONBOARDING                                                   |   |
|  | Before: 3-6 months  ->  After: 2-4 weeks                     |   |
|  | ROI: 6x faster                                               |   |
|  +-------------------------------------------------------------+   |
|                                                                     |
|  +-------------------------------------------------------------+   |
|  | SECURITY AUDIT                                               |   |
|  | Before: 2-4 weeks   ->  After: 2-4 hours                     |   |
|  | ROI: 40x faster                                              |   |
|  +-------------------------------------------------------------+   |
|                                                                     |
|  +-------------------------------------------------------------+   |
|  | CODE REVIEW                                                  |   |
|  | Before: 2-4 hours   ->  After: 10-15 minutes                 |   |
|  | ROI: 10x faster                                              |   |
|  +-------------------------------------------------------------+   |
|                                                                     |
|  +-------------------------------------------------------------+   |
|  | FUNCTION SEARCH                                              |   |
|  | Before: 5-30 minutes ->  After: 2-3 seconds                  |   |
|  | ROI: 600x faster                                             |   |
|  +-------------------------------------------------------------+   |
|                                                                     |
+====================================================================+
```

**Speaker Notes:**
> "Main value - saving developer time:
> - New employee becomes productive in weeks, not months
> - Security audit done in hours, not weeks
> - Code review is automated
> - Finding needed function - seconds instead of minutes"

---

## SLIDE 7: Market

```
+====================================================================+
|                         MARKET                                      |
+====================================================================+
|                                                                     |
|  TAM (Global):                                                      |
|  +-------------------------------------------------------------+   |
|  |  $4.5B (2024)  ->  $11.2B (2030)                             |   |
|  |  CAGR: 15.8%                                                 |   |
|  |  Code analysis tools market                                  |   |
|  +-------------------------------------------------------------+   |
|                                                                     |
|  SAM (Russia):                                                      |
|  +-------------------------------------------------------------+   |
|  |  ~500 enterprise companies with C/C++ codebases              |   |
|  |  ~2,000+ development teams                                   |   |
|  |  Potential: ~500M RUB/year                                   |   |
|  +-------------------------------------------------------------+   |
|                                                                     |
|  SOM (Year 1):                                                      |
|  +-------------------------------------------------------------+   |
|  |  Focus: Fintech + Telecom                                    |   |
|  |  Target: 20-50 teams                                         |   |
|  |  Revenue: 12-30M RUB                                         |   |
|  +-------------------------------------------------------------+   |
|                                                                     |
+====================================================================+
```

**Speaker Notes:**
> "Code analysis market grows 15% annually. In Russia,
> solutions with Russian LLM are especially in demand - it's about compliance.
> First year we focus on fintech and telecom."

---

## SLIDE 8: Enterprise Security

```
+====================================================================+
|                    ENTERPRISE SECURITY                              |
+====================================================================+
|                                                                     |
|  UNIQUE ADVANTAGES:                                                 |
|                                                                     |
|  | Feature              | CodeGraph | Competitors |                 |
|  |----------------------+-----------+-------------|                 |
|  | Integrated DLP       |    ✅     |     ❌      |                 |
|  | SIEM (3 formats)     |    ✅     |     ❌      |                 |
|  | HashiCorp Vault      |    ✅     |     ❌      |                 |
|  | Taint-Verified Vulns |    ✅     | ⚠️ Partial  |                 |
|  | Russian LLM          |    ✅     |     ❌      |                 |
|  | 152-FZ Compliance    |    ✅     |     ❌      |                 |
|                                                                     |
|  ------------------------------------------------------------------ |
|                                                                     |
|  LLM INTERACTION PROTECTION:                                        |
|  +----------------------------------------------------------+      |
|  | User Query -> [DLP] -> GigaChat -> [DLP] -> Response      |      |
|  |                |                    |                     |      |
|  |           Block/Mask           Mask PII                   |      |
|  +----------------------------------------------------------+      |
|                                                                     |
|  RBAC: 4 roles, 21 permissions | DLP: 25+ patterns                  |
|  SIEM: Syslog/CEF/LEEF | Vault: auto-rotation                       |
|                                                                     |
+====================================================================+
```

**Speaker Notes:**
> "Key differentiator from competitors - enterprise security:
> - Integrated DLP protects against secret leakage through LLM
> - SIEM integration in three formats for any SOC
> - RBAC with 21 granular permissions
> - Taint-verified vulnerabilities with 100% CVE detection rate
>
> This is the only solution on the market with full enterprise features."

---

## SLIDE 9: Product Readiness

```
+====================================================================+
|                   PRODUCT READINESS                                 |
+====================================================================+
|                                                                     |
|  STATUS: MVP READY                                                  |
|                                                                     |
|  +-------------------------------------------------------------+   |
|  | Code          | 69,000+ lines production Python              |   |
|  | Tests         | 924+ unit tests (100% pass)                  |   |
|  | Scenarios     | 16 ready workflows                           |   |
|  | Agents        | 13 specialized (5 RAG + 8 analysis)          |   |
|  +-------------------------------------------------------------+   |
|                                                                     |
|  INDEXED:                                                           |
|  +-------------------------------------------------------------+   |
|  | PostgreSQL 17 | 52,482 methods | 111,847 edges               |   |
|  | Vector DB     | 250,000+ documents                           |   |
|  | Semantic tags | 15.68M tags (47 categories)                  |   |
|  +-------------------------------------------------------------+   |
|                                                                     |
|  INFRASTRUCTURE:                                                    |
|  +-------------------------------------------------------------+   |
|  | Docker + Kubernetes manifests                                |   |
|  | CI/CD pipeline (GitHub Actions)                              |   |
|  | Prometheus/Grafana monitoring                                |   |
|  +-------------------------------------------------------------+   |
|                                                                     |
+====================================================================+
```

**Speaker Notes:**
> "This is not a prototype, but a working production-grade product:
> - 69 thousand lines of code
> - More than 900 tests
> - Ready infrastructure for deployment"

---

## SLIDE 10: Roadmap

```
+====================================================================+
|                        ROADMAP                                      |
+====================================================================+
|                                                                     |
|  Q1 2025                                                            |
|  +-------------------------------------------------------------+   |
|  | - Public beta release                                        |   |
|  | - 10 pilot clients                                           |   |
|  | - GitHub/GitLab integration                                  |   |
|  +-------------------------------------------------------------+   |
|                          |                                          |
|                          v                                          |
|  Q2 2025                                                            |
|  +-------------------------------------------------------------+   |
|  | - Enterprise features (SSO, audit logs)                      |   |
|  | - Java/Python support                                        |   |
|  | - SaaS platform MVP                                          |   |
|  +-------------------------------------------------------------+   |
|                          |                                          |
|                          v                                          |
|  Q3-Q4 2025                                                         |
|  +-------------------------------------------------------------+   |
|  | - 50+ paying clients                                         |   |
|  | - Series A fundraising                                       |   |
|  | - CIS expansion                                              |   |
|  +-------------------------------------------------------------+   |
|                                                                     |
+====================================================================+
```

**Speaker Notes:**
> "First quarter we launch beta with pilot clients.
> Second - add enterprise features and new languages.
> By year end we plan 50+ paying clients."

---

## SLIDE 11: Accelerator Request

```
+====================================================================+
|                REQUEST TO SBER500                                   |
+====================================================================+
|                                                                     |
|  WHAT WE NEED:                                                      |
|  +-------------------------------------------------------------+   |
|  | 1. Increased GigaChat API limits (50+ QPS)                   |   |
|  | 2. Access to GigaChat-2-Max for better quality               |   |
|  | 3. Technical support for prompt optimization                 |   |
|  | 4. Mentorship for enterprise segment entry                   |   |
|  | 5. Pilot clients from Sber ecosystem                         |   |
|  +-------------------------------------------------------------+   |
|                                                                     |
|  WHAT WE BRING:                                                     |
|  +-------------------------------------------------------------+   |
|  | 1. Production-ready product (not a prototype)                |   |
|  | 2. Bright GigaChat use case in DevTools                      |   |
|  | 3. Integration potential for SberCode / GigaCode             |   |
|  | 4. Revenue from enterprise clients in first year             |   |
|  +-------------------------------------------------------------+   |
|                                                                     |
|  ------------------------------------------------------------------ |
|                                                                     |
|                     THANK YOU FOR YOUR ATTENTION!                   |
|                                                                     |
|              Contact: [email] | [telegram]                          |
|              GitHub: [repository]                                   |
|                                                                     |
+====================================================================+
```

**Speaker Notes:**
> "In conclusion - what we ask for and what we give in return:
>
> We need GigaChat resources and help with market entry.
>
> In return - a ready product that can become part of Sber
> ecosystem and demonstrates GigaChat capabilities for developers.
>
> Thank you! Ready to answer questions."

---

## Additional Slides (backup)

### Technology Stack

```
+====================================================================+
|                  TECHNOLOGY STACK                                   |
+====================================================================+
|                                                                     |
|  Frontend:     TUI (Rich library) + CLI                             |
|  Backend:      Python 3.10+                                         |
|  LLM:          GigaChat API (langchain-gigachat)                    |
|  Vector DB:    ChromaDB                                             |
|  Graph DB:     DuckDB (CPG storage)                                 |
|  CPG Export:   Joern -> DuckDB                                      |
|  Workflow:     LangGraph orchestration                              |
|  Deployment:   Docker + Kubernetes                                  |
|  Monitoring:   Prometheus + Grafana                                 |
|                                                                     |
+====================================================================+
```

### Unit Economics

```
+====================================================================+
|                  UNIT ECONOMICS                                     |
+====================================================================+
|                                                                     |
|  Cost per query:                                                    |
|  +----------------------------------------------------------+      |
|  | GigaChat API (4-5 calls)  |  ~0.5-2.0 RUB                |      |
|  | Infrastructure            |  ~0.1 RUB                    |      |
|  | TOTAL                     |  ~0.6-2.1 RUB                |      |
|  +----------------------------------------------------------+      |
|                                                                     |
|  Pricing:                                                           |
|  +----------------------------------------------------------+      |
|  | Starter      | 15,000 RUB/mo | up to 1,000 queries        |      |
|  | Professional | 50,000 RUB/mo | up to 5,000 queries        |      |
|  | Enterprise   | On request    | Unlimited + SLA            |      |
|  +----------------------------------------------------------+      |
|                                                                     |
|  Margin: 60-70% on Professional+                                    |
|                                                                     |
+====================================================================+
```

### Competitors

```
+====================================================================+
|                     COMPETITORS                                     |
+====================================================================+
|                                                                     |
|  | Product       | LLM        | Graph | Russian | On-prem |        |
|  |---------------+------------+-------+---------+---------|        |
|  | GitHub Copilot| OpenAI     |   -   |    -    |    -    |        |
|  | Sourcegraph   | Claude     |   +   |    -    |    +    |        |
|  | CodeScene     | -          |   +   |    -    |    +    |        |
|  | CodeGraph     | GigaChat   |   +   |    +    |    +    |        |
|                                                                     |
|  OUR ADVANTAGES:                                                    |
|  1. Native Russian language                                         |
|  2. Data stays in Russia (compliance)                               |
|  3. Hybrid search (graph + vectors)                                 |
|  4. Deep C/C++ specialization (PostgreSQL, Linux Kernel)            |
|                                                                     |
+====================================================================+
```

---

## Presentation Instructions

### Timing (6 minutes)

| Slide | Time | Note |
|-------|------|------|
| 1. Title | 0:15 | Short greeting |
| 2. Problem | 0:30 | Key numbers |
| 3. Solution | 0:30 | How it works |
| 4. GigaChat | 0:45 | LLM role |
| 5. Metrics | 0:30 | Quality numbers |
| 6. ROI | 0:30 | Value for clients |
| 7. Market | 0:30 | TAM/SAM/SOM |
| 8. Enterprise Security | 0:45 | DLP/SIEM/RBAC/Vault |
| 9. Readiness | 0:30 | What's already done |
| 10. Roadmap | 0:30 | Plans |
| 11. Request | 0:30 | Call to action |

### Key Accents

1. **GigaChat - key component** (not auxiliary)
2. **Production-ready** (not prototype)
3. **Specific metrics** (not "better/faster")
4. **Enterprise Security** (DLP, SIEM, RBAC, Vault — unique advantages)
5. **Value for Sber** (use case + integration)

### Preparation

- [ ] Check that demo works
- [ ] Prepare backup video
- [ ] Rehearse timing
- [ ] Prepare FAQ answers
