# Technical Debt Report

Generated: 2024-12-09

This document tracks all identified technical debt items in the codebase, organized by priority.

---

## Priority 1: Critical API Stubs (29 TODOs)

These API endpoints return placeholder data and need actual implementation.

### Authentication (`src/api/routers/auth.py`)

| Line | Endpoint | Status |
|------|----------|--------|
| 84 | `POST /auth/login` | Stub - returns mock token |
| 107 | `POST /auth/refresh` | Stub - not implemented |
| 129 | `POST /auth/logout` | Stub - not implemented |
| 150 | `POST /auth/api-keys` | Stub - not implemented |
| 169 | `GET /auth/api-keys` | Stub - not implemented |
| 188 | `DELETE /auth/api-keys/{key_id}` | Stub - not implemented |
| 206 | `GET /auth/providers` | Returns hardcoded providers |
| 230 | `GET /auth/oauth/{provider}` | Stub - not implemented |
| 254 | `GET /auth/oauth/{provider}/callback` | Stub - not implemented |
| 278 | `POST /auth/ldap` | Stub - not implemented |

### Sessions (`src/api/routers/sessions.py`)

| Line | Endpoint | Status |
|------|----------|--------|
| 70 | `GET /sessions` | Returns empty list |
| 98 | `POST /sessions` | Returns placeholder session |
| 126 | `GET /sessions/{id}` | Not implemented |
| 146 | `DELETE /sessions/{id}` | Not implemented |
| 170 | `PATCH /sessions/{id}` | Not implemented |

### Statistics (`src/api/routers/stats.py`)

| Line | Endpoint | Status |
|------|----------|--------|
| 32 | `GET /stats/metrics` | Returns zeroed metrics |
| 55 | `GET /stats/scenarios` | Not implemented |
| 75 | `GET /stats/users` | Not implemented |
| 96 | `GET /stats/performance` | Not implemented |

### Query Execution (`src/api/routers/query.py`)

| Line | Endpoint | Status |
|------|----------|--------|
| 60 | `POST /query/execute` | Stub - returns error |
| 84 | `POST /query/validate` | Not implemented |

### Review (`src/api/routers/review.py`)

| Line | Endpoint | Status |
|------|----------|--------|
| 123 | `POST /review/patch` | Stub - under development |
| 154 | `POST /review/github` | Not implemented |
| 180 | `POST /review/gitlab` | Not implemented |

### Chat (`src/api/routers/chat.py`)

| Line | Endpoint | Status |
|------|----------|--------|
| 65 | `POST /chat` | Stub - not implemented |
| 95 | `POST /chat/stream` | Stub - not implemented |

### History (`src/api/routers/history.py`)

| Line | Endpoint | Status |
|------|----------|--------|
| 70 | `GET /history` | Not implemented |
| 96 | `GET /history/export` | Not implemented |
| 116 | `DELETE /history` | Not implemented |

---

## Priority 2: LLM Provider Stubs (3 items)

| File | Line | Issue |
|------|------|-------|
| `src/llm/factory.py` | 324 | OpenAI provider not implemented |
| `src/llm/gigachat_provider.py` | 409 | GigaChat embeddings not implemented |
| `src/llm/base_provider.py` | 175 | Base embeddings raises NotImplementedError |

---

## Priority 3: Large Modules Requiring Refactoring

These modules exceed 1000 lines and should be split for maintainability.

### Critical (>2000 lines)

| File | Lines | Recommendation |
|------|-------|----------------|
| `src/workflow/scenarios/security.py` | 2,324 | Split into security_audit/, entry_points/, incident/ |
| `src/workflow/multi_scenario_workflow.py` | 2,066 | Extract workflow_factories/, scenario_registry/ |
| `src/security/security_patterns.py` | 1,968 | Split by vulnerability category |
| `src/refactoring/refactoring_patterns.py` | 1,734 | Split by code smell category |

### High Priority (1200-1700 lines)

| File | Lines | Methods | Issue |
|------|-------|---------|-------|
| `src/workflow/langgraph_workflow.py` | 1,716 | 25 | Extract nodes into separate modules |
| `src/domains/postgresql/plugin.py` | 1,376 | 40 | God object - needs splitting |
| `src/analysis/call_graph_analyzer.py` | 1,342 | 16 | Multiple algorithms in one class |
| `src/architecture/architecture_agents.py` | 1,335 | 25 | Mixed data and logic classes |
| `src/agents/enrichment_agent.py` | 1,328 | 8 | Extract mappers |
| `src/analysis/dataflow_tracer.py` | 1,320 | 16 | Main class overloaded |

### Medium Priority (1000-1200 lines)

| File | Lines |
|------|-------|
| `src/workflow/scenarios/refactoring.py` | 1,329 |
| `src/performance/performance_agents.py` | 1,238 |
| `src/cpg_export/duckdb_cpg_client_v2.py` | 1,290 |
| `src/cpg_export/joern_to_duckdb_v2.py` | 1,180 |
| `src/agents/generator_agent.py` | 1,079 |
| `src/analysis/concurrency_analyzer.py` | 1,099 |
| `src/ranking/result_ranker.py` | 1,063 |

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

---

## Notes

- This document should be updated when implementing any of the above items
- Priority 1 items block full API functionality
- Priority 3 items (large modules) are recommended for splitting before adding new features
- Use `# TODO:` comments in code to mark new technical debt
