# Joern Integration Guide (ARCHIVED)

> **ARCHIVED DOCUMENTATION**
>
> This document describes legacy Joern integration that is no longer required.
> CodeGraph now uses DuckDB with pre-exported CPG data directly.
>
> This guide is preserved for users who need direct Joern access for advanced use cases
> such as creating new CPG exports or running custom CPGQL queries.
>
> For current documentation, see:
> - [Installation Guide](../getting-started/INSTALLATION.md)
> - [CPG Export Guide](../guides/CPG_EXPORT.md)
> - [SQL Query Cookbook](../reference/SQL_QUERY_COOKBOOK.md)

---

## Overview

Joern was previously used to:
- Parse source code into Code Property Graphs (CPG)
- Execute CPGQL queries
- Export CPG to DuckDB format

**Current Status**: Joern is now optional. CPG data is pre-exported to DuckDB format and queries are executed directly in SQL.

## Installation (Optional)

### Windows

```powershell
# Download Joern
Invoke-WebRequest -Uri "https://github.com/joernio/joern/releases/latest/download/joern-cli.zip" -OutFile "joern-cli.zip"

# Extract
Expand-Archive joern-cli.zip -DestinationPath C:\Users\user\joern

# Add to PATH
$env:PATH += ";C:\Users\user\joern\joern-cli\bin"
```

### Linux/Mac

```bash
# Download and install
curl -L "https://github.com/joernio/joern/releases/latest/download/joern-install.sh" | bash

# Add to PATH
export PATH=$PATH:~/bin/joern/joern-cli/bin
```

## Starting Joern Server

### Automated (Recommended)

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File scripts/bootstrap_joern.ps1
```

### Manual

```bash
# Start server with workspace
joern --server --server-host localhost --server-port 8080

# Or with specific CPG
joern --server --server-host localhost --server-port 8080 \
      --workspace /path/to/workspace
```

### Verify Server

```bash
# Check port
netstat -ano | findstr :8080

# Test connection
curl http://localhost:8080/status
```

## Creating CPG

### From Source Code

```bash
# Create CPG from PostgreSQL source
joern-parse /path/to/postgresql/src -o pg17.cpg

# With specific language
joern-parse --language c /path/to/source -o project.cpg
```

### Loading CPG

```scala
// In Joern console
importCpg("/path/to/pg17.cpg")
```

## CPGQL Queries (Legacy)

> **Note**: These queries are provided for reference. Use SQL queries for production.

### Basic Queries

```scala
// Find all methods
cpg.method.name.l

// Find specific method
cpg.method.name("CommitTransaction").l

// Find callers
cpg.method.name("CommitTransaction").caller.name.l

// Find callees
cpg.method.name("CommitTransaction").callee.name.l
```

### Complex Queries

```scala
// Call chain
cpg.method.name("executor_start")
   .repeat(_.callee)(_.until(_.name("heap_insert")))
   .path.l

// Data flow
cpg.method.name("ProcessQuery")
   .parameter
   .reachableByFlows(cpg.call.name("SPI_execute").argument)
   .l
```

## Export to DuckDB

### Using Export Script

```bash
python src/cpg_export/joern_to_duckdb_v2.py \
    --cpg /path/to/pg17.cpg \
    --output cpg.duckdb
```

### Programmatic Export

```python
from src.cpg_export.joern_to_duckdb_v2 import CPGExporter

exporter = CPGExporter(
    cpg_path="/path/to/pg17.cpg",
    output_path="cpg.duckdb"
)

exporter.export()
print(f"Exported {exporter.stats['methods']} methods")
```

## Configuration

### config.yaml

```yaml
joern:
  host: localhost
  port: 8080
  workspace: /path/to/workspace
  timeout: 60
  max_retries: 3

cpg:
  type: postgresql
  path: pg17.cpg
```

### Environment Variables

```bash
export JOERN_HOST=localhost
export JOERN_PORT=8080
export JOERN_WORKSPACE=/path/to/workspace
```

## Troubleshooting

### Server Won't Start

```bash
# Check Java version
java -version
# Requires Java 11+

# Check memory
joern --server -J-Xmx8G  # Allocate 8GB
```

### Connection Refused

```bash
# Check if process is running
ps aux | grep joern

# Check port binding
netstat -tlnp | grep 8080
```

### Query Timeout

```yaml
# Increase timeout in config.yaml
joern:
  timeout: 120  # seconds
```

### Out of Memory

```bash
# Increase JVM heap
joern --server -J-Xmx16G -J-XX:+UseG1GC
```

## Best Practices

1. **Use SQL when possible** - Faster for most queries
2. **Reserve CPGQL for** - Complex traversals, data flow analysis
3. **Pre-export to DuckDB** - Avoid Joern dependency in production
4. **Cache results** - Expensive queries should be cached
