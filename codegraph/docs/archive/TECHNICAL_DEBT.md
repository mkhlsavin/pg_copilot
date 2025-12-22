# Technical Debt Report

Generated: 2024-12-09
Updated: 2024-12-21

This document tracks all identified technical debt items in the codebase, organized by priority.

---

## Table of Contents

- [Priority 1: Critical API Stubs (29 TODOs)](#priority-1-critical-api-stubs-29-todos)
  - [Authentication (`src/api/routers/auth.py`)](#authentication-srcapiroutersauthpy)
  - [Sessions (`src/api/routers/sessions.py`)](#sessions-srcapirouterssessionspy)
  - [Statistics (`src/api/routers/stats.py`)](#statistics-srcapiroutersstatspy)
  - [Query Execution (`src/api/routers/query.py`)](#query-execution-srcapiroutersquerypy)
  - [Review (`src/api/routers/review.py`)](#review-srcapiroutersreviewpy)
  - [Chat (`src/api/routers/chat.py`)](#chat-srcapirouterschatpy)
  - [History (`src/api/routers/history.py`)](#history-srcapiroutershistorypy)
- [Priority 2: LLM Provider Stubs (3 items)](#priority-2-llm-provider-stubs-3-items)
- [Priority 3: Large Modules (Documented, Not Refactored)](#priority-3-large-modules-documented-not-refactored)
  - [Critical (>2000 lines)](#critical-2000-lines)
  - [High Priority (1200-1700 lines)](#high-priority-1200-1700-lines)
  - [Medium Priority (1000-1200 lines)](#medium-priority-1000-1200-lines)
  - [Refactoring Guidelines (Future)](#refactoring-guidelines-future)
- [Priority 4: Future Implementation (Planned Features)](#priority-4-future-implementation-planned-features)
  - [Authentication Modules](#authentication-modules)
  - [Workflow Handlers](#workflow-handlers)
- [Priority 5: Abstract Methods (By Design)](#priority-5-abstract-methods-by-design)
  - [Domain Plugin Base (`src/domains/base.py`)](#domain-plugin-base-srcdomainsbasepy)
  - [Plugin Helpers (`src/workflow/_plugin_helpers.py`)](#plugin-helpers-srcworkflow_plugin_helperspy)
- [Resolved Items](#resolved-items)
- [Notes](#notes)

## Priority 1: Critical API Stubs (29 TODOs)

These API endpoints return placeholder data and need actual implementation.

### Authentication (`src/api/routers/auth.py`)

| Line | Endpoint | Status |
|------|----------|--------|
| 113 | `POST /auth/token` | **IMPLEMENTED** - JWT login with password verification |
| 177 | `POST /auth/refresh` | **IMPLEMENTED** - Token refresh with blacklisting |
| 235 | `DELETE /auth/logout` | **IMPLEMENTED** - Token blacklisting |
| 266 | `POST /auth/api-keys` | **IMPLEMENTED** - Create API key |
| 317 | `GET /auth/api-keys` | **IMPLEMENTED** - List user's API keys |
| 352 | `DELETE /auth/api-keys/{key_id}` | **IMPLEMENTED** - Revoke API key |
| 406 | `GET /auth/oauth/providers` | Returns available providers (infrastructure ready) |
| 428 | `GET /auth/oauth/{provider}` | OAuth infrastructure ready, external integration pending |
| 451 | `GET /auth/oauth/{provider}/callback` | OAuth infrastructure ready, external integration pending |
| 479 | `POST /auth/ldap` | LDAP infrastructure ready, external integration pending |

### Sessions (`src/api/routers/sessions.py`)

| Line | Endpoint | Status |
|------|----------|--------|
| 79 | `GET /sessions` | **IMPLEMENTED** - Paginated list with turn counts |
| 138 | `POST /sessions` | **IMPLEMENTED** - Create with metadata |
| 179 | `GET /sessions/{id}` | **IMPLEMENTED** - Get with dialogue history |
| 248 | `DELETE /sessions/{id}` | **IMPLEMENTED** - Delete with ownership check |
| 296 | `PATCH /sessions/{id}` | **IMPLEMENTED** - Update metadata/scenario |

### Statistics (`src/api/routers/stats.py`)

| Line | Endpoint | Status |
|------|----------|--------|
| 61 | `GET /stats` | **IMPLEMENTED** - System metrics from database |
| 92 | `GET /stats/scenarios` | **IMPLEMENTED** - Scenario usage by period |
| 120 | `GET /stats/users` | **IMPLEMENTED** - User activity (admin only) |
| 158 | `GET /stats/performance` | **IMPLEMENTED** - Performance metrics (basic) |

### Query Execution (`src/api/routers/query.py`)

| Line | Endpoint | Status |
|------|----------|--------|
| 120 | `POST /query/execute` | **IMPLEMENTED** - SQL query with CPGQueryService |
| 215 | `POST /query/validate` | **IMPLEMENTED** - Syntax validation with warnings |

### Review (`src/api/routers/review.py`)

| Line | Endpoint | Status |
|------|----------|--------|
| 145 | `POST /review/patch` | **IMPLEMENTED** - ReviewService integration |
| 232 | `POST /review/pr` | **IMPLEMENTED** - GitHub PR via httpx |
| 327 | `POST /review/mr` | **IMPLEMENTED** - GitLab MR via httpx |

### Chat (`src/api/routers/chat.py`)

| Line | Endpoint | Status |
|------|----------|--------|
| 66 | `POST /chat` | **IMPLEMENTED** - ChatService integration with session management |
| 195 | `POST /chat/stream` | **IMPLEMENTED** - SSE streaming with dialogue persistence |
| 311 | `GET /chat/scenarios` | **IMPLEMENTED** - List available scenarios |
| 329 | `GET /chat/scenarios/{id}` | **IMPLEMENTED** - Get scenario details |

### History (`src/api/routers/history.py`)

| Line | Endpoint | Status |
|------|----------|--------|
| 63 | `GET /history/{session_id}` | **IMPLEMENTED** - Paginated dialogue history with ownership check |
| 153 | `POST /history/{session_id}/export` | **IMPLEMENTED** - Export as JSON or Markdown |
| 273 | `DELETE /history/{session_id}/clear` | **IMPLEMENTED** - Clear turns, keep session |

---

## Priority 2: LLM Provider Stubs (3 items)

| File | Line | Issue |
|------|------|-------|
| `src/llm/factory.py` | 324 | **IMPLEMENTED** - OpenAI provider with Azure support |
| `src/llm/gigachat_provider.py` | 409 | **IMPLEMENTED** - GigaChat embeddings via GigaChatEmbeddings |
| `src/llm/base_provider.py` | 175 | Base embeddings raises NotImplementedError (intentional - abstract method) |

---

## Priority 3: Large Modules (Documented, Not Refactored)

These modules exceed 1000 lines. Per project decision, they are **documented** rather than split,
as refactoring would require extensive testing and could introduce regressions.

**Status:** DOCUMENTED - Future refactoring deferred until comprehensive test coverage is in place.

### Critical (>2000 lines)

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `src/workflow/scenarios/security.py` | 2,324 | Security analysis scenarios (audit, entry points, incidents) | Documented |
| `src/workflow/multi_scenario_workflow.py` | 2,066 | Main workflow orchestration with 16 scenarios | Documented |
| `src/security/security_patterns.py` | 1,968 | Vulnerability patterns and detection rules | Documented |
| `src/refactoring/refactoring_patterns.py` | 1,734 | Code smell patterns and refactoring suggestions | Documented |

### High Priority (1200-1700 lines)

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `src/workflow/langgraph_workflow.py` | 1,716 | LangGraph-based workflow nodes and edges | Documented |
| `src/domains/postgresql/plugin.py` | 1,376 | PostgreSQL domain plugin with 40+ methods | Documented |
| `src/analysis/call_graph_analyzer.py` | 1,342 | Call graph analysis algorithms | Documented |
| `src/architecture/architecture_agents.py` | 1,335 | Architecture analysis agents | Documented |
| `src/agents/enrichment_agent.py` | 1,328 | Data enrichment and mapping | Documented |
| `src/analysis/dataflow_tracer.py` | 1,320 | Dataflow tracing and taint analysis | Documented |

### Medium Priority (1000-1200 lines)

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `src/workflow/scenarios/refactoring.py` | 1,329 | Refactoring scenario analysis | Documented |
| `src/performance/performance_agents.py` | 1,238 | Performance analysis agents | Documented |
| `src/cpg_export/duckdb_cpg_client_v2.py` | 1,290 | DuckDB CPG client v2 | Documented |
| `src/cpg_export/joern_to_duckdb_v2.py` | 1,180 | Joern to DuckDB converter v2 | Documented |
| `src/agents/generator_agent.py` | 1,079 | Response generation agent | Documented |
| `src/analysis/concurrency_analyzer.py` | 1,099 | Concurrency issue detection | Documented |
| `src/ranking/result_ranker.py` | 1,063 | Result ranking and scoring | Documented |

### Refactoring Guidelines (Future)

When test coverage reaches 80%+, consider:
1. **security.py**: Split into `security/audit.py`, `security/entry_points.py`, `security/incident.py`
2. **multi_scenario_workflow.py**: Extract `workflow/factories/`, `workflow/registry/`
3. **postgresql/plugin.py**: Extract `plugin/queries.py`, `plugin/formatters.py`, `plugin/validators.py`

---

## Priority 4: Future Implementation (Planned Features)

These modules have complete infrastructure code but require external integration (credentials, servers).
**Status:** DEFERRED - Will be activated when external services are configured.

### Authentication Modules

| Module | Lines | Status | Description |
|--------|-------|--------|-------------|
| `src/api/auth/oauth.py` | 446 | Infrastructure complete | OAuth2/OIDC: GitHub, GitLab, Google, Keycloak providers |
| `src/api/auth/ldap_auth.py` | 398 | Infrastructure complete | LDAP/AD authentication with group sync |

**OAuth Features Ready:**
- OAuthProvider base class with token exchange
- GitHubOAuth, GitLabOAuth, GoogleOAuth, KeycloakOAuth implementations
- OAuthManager for multi-provider support
- User info parsing per provider

**LDAP Features Ready:**
- LDAPAuthenticator with AD/OpenLDAP support
- User DN search and bind authentication
- Group membership extraction
- Role mapping from LDAP groups

### Workflow Handlers

| Module | Status | Description |
|--------|--------|-------------|
| `src/workflow/handlers/` | Stub docstring | Placeholder for future handler extraction from large workflow modules |

**Planned Handlers (when extracted from large modules):**
- RetrievalHandler: CPG query operations
- AnalysisHandler: Code analysis operations
- GenerationHandler: LLM response generation
- EvaluationHandler: Result validation

---

## Priority 5: Abstract Methods (By Design)

These are intentional abstract/base implementations following established design patterns.
**Status:** BY DESIGN - No action required.

### Domain Plugin Base (`src/domains/base.py`)

7 abstract methods that domain plugins must implement:
| Method | Purpose | Implementations |
|--------|---------|-----------------|
| `name` | Domain identifier | PostgreSQL, Generic C++, Python Django |
| `display_name` | Human-readable name | All 3 plugins |
| `description` | Domain description | All 3 plugins |
| `_load_subsystems()` | Subsystem definitions | All 3 plugins |
| `_load_prompts()` | LLM prompt templates | All 3 plugins |
| `_load_intent_patterns()` | Intent classification | All 3 plugins |
| `_load_security_patterns()` | Security vulnerability patterns | All 3 plugins |

**Existing Implementations:**
- `src/domains/postgresql/plugin.py` (1,376 lines) - PostgreSQL domain
- `src/domains/generic_cpp/plugin.py` - Generic C/C++ domain
- `src/domains/python_django/plugin.py` - Python/Django domain

### Plugin Helpers (`src/workflow/_plugin_helpers.py`)

Helper functions with domain-aware defaults:
- `get_memory_functions_from_plugin()` - Memory allocation/free functions
- `get_lock_functions_from_plugin()` - Lock acquisition/release functions
- `get_debug_functions_from_plugin()` - Debugging/logging functions
- `get_entry_points_from_plugin()` - Application entry points
- `get_subsystem_functions_from_plugin()` - Subsystem-organized functions
- `get_dml_functions_from_plugin()` - DML operation functions

These functions provide PostgreSQL defaults but delegate to active domain plugin when available.

---

## Resolved Items

- [x] Duplicate `ApiKeyRepository` class removed from `src/api/auth/api_keys.py`
- [x] Commented imports removed from `src/workflow/handlers/__init__.py`
- [x] OAuth/LDAP modules marked as NOT_YET_IMPLEMENTED
- [x] Auth endpoints implemented: login, refresh, logout, API keys (6/10 endpoints)
- [x] `validate_api_key` function added to `src/api/auth/api_keys.py`
- [x] Sessions endpoints implemented: list, create, get, delete, update (5/5 endpoints)
- [x] Stats endpoints implemented: metrics, scenarios, users, performance (4/4 endpoints)
- [x] Created StatsRepository for metrics collection
- [x] Query endpoints implemented: execute, validate (2/2 endpoints) with SQL injection prevention
- [x] Review endpoints implemented: patch, pr, mr (3/3 endpoints) with ReviewService
- [x] Chat endpoints implemented: chat, stream, scenarios (4/4 endpoints) with ChatService
- [x] History endpoints implemented: get, export, clear (3/3 endpoints) with SessionRepository
- [x] OpenAI provider implemented with Azure support (`src/llm/openai_provider.py`)
- [x] GigaChat embeddings implemented via GigaChatEmbeddings
- [x] Priority 3 large modules documented with purpose and future refactoring guidelines
- [x] Priority 4 future implementation modules documented (OAuth 446 lines, LDAP 398 lines)
- [x] Priority 5 abstract methods documented as "by design" with 3 existing implementations
- [x] Project structure reorganized (2024-12-12):
  - Documentation moved from root to `docs/development/` (AUTHENTICATION_UPDATE.md, DEPLOYMENT_READINESS_PLAN.md, UX_IMPROVEMENTS_PLAN.md)
  - BENCHMARK_GUIDE.md moved to `docs/guides/`
  - Demo scripts moved to `examples/` (demo_benchmark.py, demo_patch_review.py, demo_review_output.*)
  - benchmark_hybrid_retrieval.py moved to `scripts/`
  - config.gigachat.yaml.example moved to `config/`
  - test_gigachat.py moved to `tests/llm/`
  - Tests from `tests/` root organized into subdirectories:
    - Unit tests moved to `tests/unit/` (test_call_graph_analyzer.py, test_dataflow_tracer.py, test_intent_classifier.py, test_patch_review_system.py, test_prompt_registry.py)
    - Integration tests moved to `tests/integration/` (test_multi_scenario_integration.py, test_phase2_integration.py, test_ragas_integration.py, test_p0_fixes.py)
  - benchmark_results moved to `data/`
  - Empty security_reports directory removed
- [x] D3FEND security checks fixed (2024-12-21):
  - Fixed 6 SQL queries in `src/security/hardening/d3fend_checks.py` (lines 246, 315, 381, 618, 691, 768)
  - Changed broken `JOIN nodes_method nm ON nc.method_id = nm.id` to proper `JOIN edges_contains ec ON ec.dst = nc.id JOIN nodes_method nm ON ec.src = nm.id`
  - Affected checks: D3-IRV (Integer Range Validation), D3-RN (Reference Nullification), D3-TL (Trusted Library), D3-NPC (Null Pointer Checking), D3-DLV (Domain Logic Validation), D3-OLV (Operational Logic Validation)
- [x] Benchmark Yandex API support added (2024-12-21):
  - Added `--provider` CLI argument to `tests/benchmark/run_benchmark.py`
  - Supports `gigachat`, `yandex`, `openai`, `local` providers
  - Yandex uses Qwen3 model (`qwen3-235b-a22b-fp8/latest`)
- [x] CFGAnalyzer module created (2024-12-21):
  - New file: `src/analysis/cfg_analyzer.py` (~400 lines)
  - Proper cyclomatic complexity calculation: M = E - N + 2
  - CFG structure extraction, path enumeration, dominator analysis
  - Uses `edges_contains` and `edges_cfg` tables correctly
- [x] FieldSensitiveTracer module created (2024-12-21):
  - New file: `src/analysis/field_sensitive_tracer.py` (~450 lines)
  - Tracks field access paths like `obj.field1.field2`
  - Field-sensitive taint analysis for security scanning
  - Uses `nodes_field_identifier` and `nodes_member` tables
- [x] DataFlowTracer field-sensitive integration (2024-12-21):
  - Added `find_taint_paths_field_sensitive()` method
  - Added `find_sensitive_data_flows()` for sensitive field tracking
  - Integrated FieldSensitiveTracer with existing taint analysis
- [x] ControlFlowAnalyzer updated to use CFGAnalyzer (2024-12-21):
  - Replaced broken complexity query with CFGAnalyzer
  - Removed fallback heuristics for complexity estimation

---

## Notes

- This document should be updated when implementing any of the above items
- Priority 1 items block full API functionality
- Priority 3 items (large modules) are recommended for splitting before adding new features
- Use `# TODO:` comments in code to mark new technical debt
