# Automated Patch-Based Code Review System

## Overview

The automated code review system analyzes patches (git diffs, GitHub PRs, GitLab MRs) using Code Property Graph (CPG) analysis to provide comprehensive review feedback including:

- Security vulnerability detection
- Performance impact analysis
- Error risk assessment
- Architecture impact analysis
- Definition of Done (DoD) validation

## Quick Start

### Basic Usage

```bash
# Run demo with default settings
python demo_patch_review.py

# With custom database
python demo_patch_review.py --db /path/to/cpg.duckdb

# Without DoD functionality
python demo_patch_review.py --no-dod

# Auto-generate DoD instead of extracting from PR
python demo_patch_review.py --auto-dod
```

### Programmatic Usage

```python
import duckdb
from src.patch_review import ReviewWorkflow

# Connect to CPG database
conn = duckdb.connect('cpg.duckdb')

# Configure DoD settings
dod_config = {
    'auto_generate': True,
    'extraction': {
        'sources': ['pr_body', 'jira', 'commit_message'],
        'formats': ['checklist', 'yaml', 'markdown'],
    },
}

# Create workflow
workflow = ReviewWorkflow(conn, dod_config=dod_config)

# Run review
verdict = workflow.run(
    patch_source='git_diff',
    patch_data={'diff': diff_content},
    pr_body=pr_description,  # For DoD extraction
    task_description=task_desc,  # For DoD generation
)

# Access results
print(f"Score: {verdict.overall_score}/100")
print(f"Recommendation: {verdict.recommendation.value}")

# DoD validation results
if verdict.dod_validation:
    print(f"DoD Compliance: {verdict.dod_validation.compliance_score}%")
```

## Architecture

### Workflow Pipeline

```
parse_patch → extract_dod → [generate_dod] → generate_delta_cpg
    ↓
run_analyzers → generate_verdicts → validate_dod → aggregate → format_output
```

### Components

| Component | Description |
|-----------|-------------|
| `PatchParser` | Parses git diffs, GitHub PRs, GitLab MRs |
| `DoDExtractor` | Extracts DoD from PR body, Jira, commit message |
| `DoDGenerator` | Generates DoD using LLM when not found |
| `DeltaCPGGenerator` | Creates delta CPG overlay for changes |
| `Analyzers` | Call graph, dataflow, control flow, dependency |
| `VerdictGenerators` | Security, performance, error, architecture |
| `DoDValidator` | Validates DoD against review findings |
| `VerdictAggregator` | Combines verdicts into final review |

## Definition of Done (DoD)

### DoD Sources

The system can extract DoD from multiple sources (configurable priority):

1. **PR Body** - Markdown checklist in PR/MR description
2. **Jira** - Custom field or description from linked ticket
3. **Commit Message** - DoD section in first commit
4. **Manual Input** - CLI or API input
5. **Auto-Generated** - LLM generates from task description

### DoD Formats

Supported formats for DoD extraction:

#### Markdown Checklist
```markdown
## Definition of Done

- [ ] Feature works as expected
- [ ] No security vulnerabilities introduced
- [ ] Unit tests added
- [ ] Documentation updated
```

#### YAML Block
```yaml
```yaml
dod:
  - description: Feature works as expected
    type: functional
  - description: Unit tests pass
    type: test
```
```

#### JSON Block
```json
```json
{
  "dod": [
    {"description": "Feature works", "type": "functional"},
    {"description": "Tests pass", "type": "test"}
  ]
}
```
```

### Criterion Types

| Type | Description | Validation |
|------|-------------|------------|
| `functional` | Feature requirements | Manual review (cannot auto-validate) |
| `security` | No vulnerabilities | Security verdict score |
| `test` | Tests added/passing | Error verdict suggestions |
| `documentation` | Docs updated | Manual review |
| `performance` | No regressions | Performance verdict score |
| `code_quality` | Style compliance | Architecture verdict score |

### DoD Validation

Each DoD item is validated against review findings:

- **Security** items: Validated against security verdict (critical/high findings fail)
- **Test** items: Validated against test suggestions count
- **Performance** items: Validated against performance score
- **Code Quality** items: Validated against architecture score
- **Functional/Documentation**: Cannot be auto-validated (pending for manual review)

## Configuration

### config/code_review.yaml

```yaml
# Definition of Done Configuration
dod:
  sources:
    - pr_body
    - jira
    - commit_message
    - manual
  source_priority:
    - pr_body
    - jira
    - commit_message
  formats:
    - checklist
    - yaml
    - markdown
    - json
  auto_generate: true
  interactive_confirm: false

  # Jira integration
  jira:
    url: ${JIRA_URL}
    api_key: ${JIRA_API_KEY}
    dod_field: "customfield_10001"

  # Validation settings
  validation:
    strict_mode: false
    blocking_severities:
      - critical
      - high

# Review Policy
policy:
  block_on_critical_security: true
  min_score_to_approve: 70.0
  require_dod_compliance: false
  min_dod_compliance_score: 60.0

# Verdict Weights
verdicts:
  weights:
    security: 0.35
    performance: 0.20
    error: 0.25
    architecture: 0.20
  dod_compliance_weight: 0.10
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `JIRA_URL` | Jira server URL for DoD extraction |
| `JIRA_API_KEY` | Jira API authentication key |
| `GITHUB_TOKEN` | GitHub API token for PR access |
| `GITLAB_TOKEN` | GitLab API token for MR access |

## API Reference

### ReviewWorkflow

```python
workflow = ReviewWorkflow(
    conn: duckdb.DuckDBPyConnection,
    config: Optional[AggregationConfig] = None,
    policy: Optional[ReviewPolicy] = None,
    dod_config: Optional[Dict[str, Any]] = None,
)

verdict = workflow.run(
    patch_source: str,  # 'git_diff', 'github_pr', 'gitlab_mr'
    patch_data: Dict[str, Any],
    session_id: Optional[str] = None,
    policy: Optional[ReviewPolicy] = None,
    task_description: Optional[str] = None,
    pr_body: Optional[str] = None,
    jira_ticket: Optional[str] = None,
    interactive_mode: bool = False,
)
```

### ReviewVerdict

```python
class ReviewVerdict:
    patch_id: str
    overall_score: float  # 0-100
    recommendation: Recommendation  # APPROVE, REQUEST_CHANGES, BLOCK, COMMENT

    # Sub-verdicts
    security: SecurityVerdict
    performance: PerformanceVerdict
    error: ErrorVerdict
    architecture: ArchitectureVerdict

    # Findings
    all_findings: List[Finding]
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int

    # DoD
    dod_validation: Optional[DoDValidationResult]
    dod_compliance_score: float  # 0-100
```

### DoDValidationResult

```python
class DoDValidationResult:
    dod: DefinitionOfDone
    total_items: int
    satisfied_count: int
    failed_count: int
    pending_count: int
    compliance_score: float  # 0-100
    blocking_failures: List[DoDItem]
    is_compliant: bool  # True if all items satisfied
```

## Output Formats

### JSON Output

```json
{
  "patch_id": "PATCH_abc123",
  "overall_score": 45.5,
  "recommendation": "REQUEST_CHANGES",
  "dod_compliance_score": 60.0,
  "findings": [...],
  "dod_validation": {
    "compliance_score": 60.0,
    "items": [
      {"description": "...", "satisfied": true, "evidence": "..."},
      {"description": "...", "satisfied": false, "evidence": "..."}
    ]
  }
}
```

### Markdown Output

```markdown
## Patch Review Summary

**Overall Score:** 45/100
**Recommendation:** REQUEST_CHANGES

### Definition of Done

**Compliance Score:** 60%

- ✅ Feature works as expected
- ❌ No security vulnerabilities introduced
  - Evidence: Security issues found: SQL Injection
- ⏳ Unit tests added (pending manual review)

### Security Findings

1. [HIGH] SQL Injection vulnerability
   - Location: src/auth/login.py:14
   - CWE-89
```

## Troubleshooting

### "DoD not found"

If DoD is not being extracted:

1. Check that PR body contains DoD section with correct format
2. Verify `dod.sources` includes your source type
3. Check `dod.formats` includes your DoD format
4. Enable `auto_generate: true` to generate when not found

### "DoD validation skipped"

DoD validation requires:
- DoD successfully extracted or generated
- Review verdict generated
- No workflow errors

### "Jira extraction failed"

1. Verify JIRA_URL and JIRA_API_KEY environment variables
2. Check Jira API permissions
3. Verify `dod_field` points to correct custom field

## Examples

### GitHub PR Integration

```python
# Parse GitHub PR event
pr_data = {
    'number': 123,
    'title': 'Add authentication',
    'body': pr_body_with_dod,
    'diff_url': 'https://api.github.com/repos/...',
}

verdict = workflow.run(
    patch_source='github_pr',
    patch_data=pr_data,
    pr_body=pr_data['body'],
)
```

### GitLab MR Integration

```python
mr_data = {
    'iid': 456,
    'title': 'Add authentication',
    'description': mr_description_with_dod,
}

verdict = workflow.run(
    patch_source='gitlab_mr',
    patch_data=mr_data,
    pr_body=mr_data['description'],
)
```

### Manual DoD Creation

```python
from src.patch_review.dod import DoDExtractor

extractor = DoDExtractor()
dod = extractor.create_manual_dod(
    items=[
        "Feature works as expected",
        "No security vulnerabilities",
        "Unit tests added",
    ],
    types=["functional", "security", "test"],
)
```
