# CodeGraph Documentation

> Comprehensive documentation for the CodeGraph code analysis system.

## Documentation Structure

```
docs/
├── getting-started/     # Installation, configuration, quick start
├── guides/              # User guides and how-to documentation
├── api/                 # REST API and WebSocket documentation
├── reference/           # Technical reference documentation
├── development/         # Architecture and contribution guides
├── enterprise/          # Enterprise security and deployment (en/ru)
├── sber500/             # Business documentation (en/ru)
├── integrations/        # Third-party integrations
├── archive/             # Legacy documentation
└── landing/             # Landing page assets
```

## Quick Navigation

### Getting Started
- [Quick Start](./getting-started/README.md) - 10-minute setup guide
- [Installation](./getting-started/INSTALLATION.md) - Detailed installation
- [Configuration](./getting-started/CONFIGURATION.md) - Environment setup

### User Documentation
- [TUI User Guide](./guides/TUI_USER_GUIDE.md) - Complete TUI guide with 16 scenarios
- [Programmatic Guide](./guides/PROGRAMMATIC_GUIDE.md) - Python API usage
- [Scenarios](./guides/SCENARIOS.md) - All analysis scenarios
- [CLI Guide](./guides/CLI_GUIDE.md) - Complete CLI reference and usage
- [Quick Reference](./guides/QUICK_REFERENCE.md) - Cheat sheet
- [Code Review](./guides/CODE_REVIEW.md) - Automated review system
- [Project Import](./guides/PROJECT_IMPORT.md) - Import projects
- [Troubleshooting](./guides/TROUBLESHOOTING.md) - Common issues

### API Documentation
- [REST API](./api/REST_API.md) - HTTP API reference
- [WebSocket API](./api/WEBSOCKET_API.md) - Real-time streaming

### Reference
- [Agents](./reference/AGENTS.md) - Agent system
- [Workflows](./reference/WORKFLOWS.md) - Workflow definitions
- [Schema](./reference/SCHEMA.md) - Database schema
- [SQL Query Cookbook](./reference/SQL_QUERY_COOKBOOK.md) - SQL examples
- [Security](./reference/SECURITY.md) - Security features (DLP, SIEM, Vault)
- [Analysis Modules](./reference/ANALYSIS_MODULES.md) - CFG, dataflow, field-sensitive analysis

### Development
- [Architecture](./development/ARCHITECTURE.md) - System architecture
- [Contributing](./development/CONTRIBUTING.md) - How to contribute
- [Patterns](./development/PATTERNS.md) - Coding standards
- [Domain Plugins](./development/DOMAIN_PLUGINS.md) - Creating domain plugins

### Enterprise (Bilingual: en/ru)
- [Enterprise Docs](./enterprise/README.md) - Security, RBAC, SIEM, DLP

### Business Documentation (Bilingual: en/ru)
- [Sber500 Docs](./sber500/README.md) - Business case, pitch, demos

### Other
- [Integrations](./integrations/README.md) - Third-party integrations
- [Archive](./archive/README.md) - Legacy documentation

---

## Documentation Rules

1. **File Organization**: One topic per file, max 500 lines
2. **Content Quality**: No duplicates, test all examples
3. **Cross-References**: Use relative paths, bidirectional links
4. **Bilingual Content**: Use en/ru subfolders
5. **Maintenance**: Review quarterly, maintain changelog

---

*Last updated: December 2025*
