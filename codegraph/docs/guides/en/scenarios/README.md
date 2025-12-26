# Workflow Scenarios Guide

> Detailed guides for each of the 16 CodeGraph analysis scenarios.

## Scenario Overview

CodeGraph provides 16 specialized analysis scenarios organized by user role:

### Developer Scenarios

| # | Scenario | Description | Guide |
|---|----------|-------------|-------|
| 01 | [Onboarding](./01-onboarding.md) | New developer codebase exploration | [Guide](./01-onboarding.md) |
| 04 | [Feature Development](./04-feature-development.md) | Adding new features | [Guide](./04-feature-development.md) |
| 05 | [Refactoring](./05-refactoring.md) | Code cleanup and refactoring | [Guide](./05-refactoring.md) |
| 15 | [Debugging](./15-debugging.md) | Debugging assistance | [Guide](./15-debugging.md) |

### Security Scenarios

| # | Scenario | Description | Guide |
|---|----------|-------------|-------|
| 02 | [Security Audit](./02-security-audit.md) | Vulnerability scanning | [Guide](./02-security-audit.md) |
| 08 | [Compliance](./08-compliance.md) | Regulatory compliance checks | [Guide](./08-compliance.md) |
| 14 | [Incident Response](./14-incident-response.md) | Security incident investigation | [Guide](./14-incident-response.md) |
| 16 | [Entry Points](./16-entry-points.md) | API surface mapping | [Guide](./16-entry-points.md) |

### QA/Tester Scenarios

| # | Scenario | Description | Guide |
|---|----------|-------------|-------|
| 07 | [Test Coverage](./07-test-coverage.md) | Coverage gap analysis | [Guide](./07-test-coverage.md) |
| 09 | [Code Review](./09-code-review.md) | Automated code review | [Guide](./09-code-review.md) |

### Technical Writer Scenarios

| # | Scenario | Description | Guide |
|---|----------|-------------|-------|
| 03 | [Documentation](./03-documentation.md) | API documentation generation | [Guide](./03-documentation.md) |
| 11 | [Architecture](./11-architecture.md) | Architecture documentation | [Guide](./11-architecture.md) |

### Advanced Scenarios

| # | Scenario | Description | Guide |
|---|----------|-------------|-------|
| 06 | [Performance](./06-performance.md) | Performance analysis | [Guide](./06-performance.md) |
| 10 | [Cross-Repo](./10-cross-repo.md) | Cross-repository analysis | [Guide](./10-cross-repo.md) |
| 12 | [Tech Debt](./12-tech-debt.md) | Technical debt assessment | [Guide](./12-tech-debt.md) |
| 13 | [Mass Refactoring](./13-mass-refactoring.md) | Large-scale refactoring | [Guide](./13-mass-refactoring.md) |

## Quick Selection

```bash
# Select scenario by number in TUI
/select 01   # Onboarding
/select 02   # Security Audit
/select 03   # Documentation
...
/select 16   # Entry Points
```

## Related Documentation

- [TUI User Guide](../TUI_USER_GUIDE.md) - Complete TUI usage guide
- [Scenarios Overview](../SCENARIOS.md) - API and programmatic usage
- [CLI Guide](../CLI_GUIDE.md) - Command-line interface
