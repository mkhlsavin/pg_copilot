# RAG-CPGQL Quick Reference

> One-page cheatsheet for daily use

---

## Essential Commands

| Command | Example | Description |
|---------|---------|-------------|
| `/help` | `/help review` | Show help |
| `/scenarios` | `/scenarios security` | List scenarios |
| `/select` | `/select 02` | Switch scenario |
| `/stat` | `/stat` | Show DB stats |
| `/query` | `/query SELECT * FROM nodes_method LIMIT 5` | Run SQL |
| `/review` | `/review git` | Code review |
| `/config` | `/config llm temperature 0.5` | Edit config |
| `/exit` | `/exit` | Save and quit |

---

## Scenarios by Role

### Developer
```
/select 01  → Onboarding      "Where is function X?"
/select 04  → Feature Dev     "Where to add hook?"
/select 05  → Refactoring     "Find dead code"
/select 15  → Debugging       "Trace execution path"
```

### QA/Tester
```
/select 07  → Test Coverage   "What's untested?"
/select 09  → Code Review     "Review this patch"
/select 12  → Tech Debt       "Quantify debt"
```

### Security
```
/select 02  → Security Audit  "Find SQL injection"
/select 08  → Compliance      "Check OWASP Top 10"
/select 14  → Incident        "Trace attack vector"
/select 16  → Entry Points    "List API endpoints"
```

### Technical Writer
```
/select 03  → Documentation   "Document function X"
/select 11  → Architecture    "Explain module structure"
```

---

## Common Queries

### Find Functions
```
> Where is palloc defined?
> Show callers of heap_insert
> What does ExecProcNode call?
```

### Security Analysis
```
> Find SQL injection vulnerabilities
> Trace data flow from user input to query
> Show functions without input validation
```

### Code Understanding
```
> Explain the executor subsystem
> How does memory allocation work?
> Show dependencies of module X
```

---

## Code Review

```bash
/review git              # Local changes
/review github 123       # GitHub PR
/review gitlab 456       # GitLab MR
/review file patch.diff  # Patch file

# With options
/review git --format json --inline
```

---

## SQL Queries

```sql
-- Count functions
/query SELECT COUNT(*) FROM nodes_method

-- Find functions by name
/query SELECT name, filename FROM nodes_method
       WHERE name LIKE 'heap%' LIMIT 10

-- Find callers
/query SELECT caller.name FROM edges_call e
       JOIN nodes_method caller ON e.src = caller.id
       WHERE e.dst = (SELECT id FROM nodes_method WHERE name='palloc')
       LIMIT 5
```

---

## Configuration

```bash
# View all
/config

# Edit LLM settings
/config llm provider gigachat
/config llm temperature 0.7

# Environment variables
export GIGACHAT_AUTH_KEY="..."
export OPENAI_API_KEY="..."
```

---

## Quick Workflows

### Morning Security Check
```
/select 02
> Find vulnerabilities in recent commits
/review git
```

### New Developer Start
```
/select 01
> What is the main architecture?
> Where should I start reading?
```

### Pre-Release Audit
```
/select 08
> Generate OWASP compliance report
/review git --format json > audit.json
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No results" | Check `/stat`, verify CPG loaded |
| Slow response | Reduce `n_ctx` in config |
| Connection refused | Restart Joern server |
| API timeout | Increase `timeout` in config |

---

*Full documentation: [USER_GUIDE.md](USER_GUIDE.md)*
