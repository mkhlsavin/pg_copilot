# Technical Debt Report

Generated: 2024-12-09

This document tracks all identified technical debt items in the codebase, organized by priority.

---

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

### Authentication Modules

| Module | Status | Description |
|--------|--------|-------------|
| `src/api/auth/oauth.py` | Infrastructure ready | OAuth2/OIDC providers (GitHub, GitLab, Google) |
| `src/api/auth/ldap_auth.py` | Infrastructure ready | LDAP/Active Directory integration |

### Workflow Handlers

| Module | Status | Description |
|--------|--------|-------------|
| `src/workflow/handlers/` | Stub package | RetrievalHandler, AnalysisHandler, GenerationHandler, EvaluationHandler |

---

## Priority 5: Abstract Methods Without Implementation

### Domain Plugin Base (`src/domains/base.py`)

8 abstract methods requiring implementation in domain plugins:
- `name` property (line 84)
- `display_name` property (line 95)
- `description` property (line 106)
- `_load_subsystems()` (line 128)
- `_load_prompts()` (line 150)
- `_load_intent_patterns()` (line 171)
- `_load_security_patterns()` (line 192)

### Plugin Helpers (`src/workflow/_plugin_helpers.py`)

25+ exception classes with empty implementations (lines 72-533).
These are intentionally empty exception classes for error categorization.

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

---

## Notes

- This document should be updated when implementing any of the above items
- Priority 1 items block full API functionality
- Priority 3 items (large modules) are recommended for splitting before adding new features
- Use `# TODO:` comments in code to mark new technical debt
