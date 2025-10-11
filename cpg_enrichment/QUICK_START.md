# CPG Enrichment – Quick Start Guide

## Windows PowerShell

Before you run the wrappers:

- Open PowerShell directly inside `pg_copilot\cpg_enrichment`.
- Ensure Joern is available. If it lives elsewhere, set the path once: `$env:JOERN_PATH="C:\tools\joern\joern.bat"` (the scripts also probe `joern` on `PATH` and in nearby folders).

```powershell
# 1. Configure JVM memory
$env:JAVA_OPTS="-Xmx16G -Xms4G"

# 2. Launch the enrichment workflow
# Option A: you have a .bin/.zip archive of the CPG workspace
dot\enrich_cpg.ps1 standard import/postgres-REL_17_6/pg17_full.cpg.bin

# Option B: you already have an extracted Joern workspace
dot\enrich_cpg.ps1 standard workspace/pg17_full.cpg
```

## Linux / macOS / Git Bash

Before you run the wrappers:

- Open a terminal inside `pg_copilot/cpg_enrichment`.
- If Joern is not on your `PATH`, export it explicitly: `export JOERN_PATH=/opt/joern/joern` (the script also checks for `joern` in PATH and sibling folders).

```bash
# 1. Configure JVM memory
export JAVA_OPTS="-Xmx16G -Xms4G"

# 2. Make the wrapper executable
chmod +x enrich_cpg.sh

# Option A: you have a .bin/.zip archive of the CPG workspace
./enrich_cpg.sh standard import/postgres-REL_17_6/pg17_full.cpg.bin

# Option B: you already have an extracted Joern workspace
./enrich_cpg.sh standard workspace/pg17_full.cpg
```

**Note:** The wrappers automatically detect whether the input path is a workspace directory or an archive. You only need to intervene when:

- The workspace has not been created yet.
- You provide a `.bin`/`.bin.zip` archive in a different location and the script cannot infer the output directory.
- You call `enrich_all.sc` manually from somewhere else—in that case pass `-Denrich.root=/full/path/to/pg_copilot/cpg_enrichment` or export `ENRICH_ROOT` beforehand.

## Manual Mode (when automation is unavailable)

### Step 1: Import the CPG (if no workspace exists)

```bash
# Configure JVM memory
export JAVA_OPTS="-Xmx16G -Xms4G"  # Windows PowerShell equivalent: $env:JAVA_OPTS="-Xmx16G -Xms4G"

# Start Joern
joern
```

```scala
// Import the archive when starting from a .bin/.zip bundle
importCpg("import/postgres-REL_17_6/pg17_full.cpg.bin", "pg17_full.cpg")

// Or open an existing workspace
open("pg17_full.cpg")
```

### Step 2: Validate the CPG is loaded

```scala
cpg.file.size  // should be > 0
```

### Step 3: Execute enrichment scripts from the Joern REPL

```scala
// Minimal profile (~10 minutes)
import $file.`ast_comments.sc`
import $file.`subsystem_readme.sc`

// Standard profile (~50 minutes total)
import $file.`api_usage_examples.sc`
import $file.`security_patterns.sc`
import $file.`code_metrics.sc`
import $file.`extension_points.sc`
import $file.`dependency_graph.sc`

// Full profile (~90 minutes total)
import $file.`test_coverage.sc`
import $file.`performance_hotspots.sc`

// Finish (closes the workspace cleanly)
close
```

## Verifying Results

```bash
# Start Joern
joern
```

```scala
// Open the workspace
open("pg17_full.cpg")

// Check that enrichment data is present
cpg.comment.size  // should be > 0
cpg.tag.size      // should be > 0

// Inspect sample tags
cpg.file.tag.name("subsystem-name").value.dedup.sorted.l.take(10)
cpg.method.tag.name("api-caller-count").value.l.map(_.toInt).sorted.reverse.take(10)
```

## Common Issues

### Error: "Access is denied" while importing a workspace

**Cause:** The current user cannot create the workspace directory when importing from an archive.

**Fix:**

```bash
# Option 1 (command line import)
joern --import import/postgres-REL_17_6

# Option 2 (import inside the Joern shell)
joern
open("pg17_full.cpg")

# Option 3 (manual archive import)
joern
importCpg("import/postgres-REL_17_6/pg17_full.cpg.bin", "pg17_full.cpg")
```

### Error: "invalid escape character" (Windows)

**Cause:** Backslashes in Windows paths conflict with Scala escape sequences.

**Fix:** Use Unix-style forward slashes in strings. If you encounter this error:

```scala
// Problematic
importCpg("import\postgres-REL_17_6\pg17_full.cpg.bin", "pg17_full.cpg")

// Correct
importCpg("import/postgres-REL_17_6/pg17_full.cpg.bin", "pg17_full.cpg")
```

### Error: "Not found: $file" in batch mode

**Cause:** `import $file` works only in the interactive REPL; batch scripts must use `:load` with local files.

**Fix:** The automation wrappers (`enrich_cpg.ps1`, `enrich_cpg.sh`) already handle this. If you are experimenting manually in the REPL:

```scala
// From the interactive REPL
import $file.`ast_comments.sc`

// From a batch script (preferred)
:load ast_comments.sc
import $file.`ast_comments.sc`
```

### Out of Memory (OOM)

**Fix:** Increase the JVM heap:

```bash
# Bash
export JAVA_OPTS="-Xmx32G -Xms8G"

# PowerShell
$env:JAVA_OPTS="-Xmx32G -Xms8G"
```

### Error: Script not found

**Fix:** Verify that the Scala scripts are present in the current directory:

```bash
ls *.sc
# Expected output: ast_comments.sc, subsystem_readme.sc, api_usage_examples.sc, ...
```

## Enrichment Profiles

| Profile | Duration | Includes | Notes |
|---------|----------|----------|-------|
| **minimal** | ~10 min | comments, subsystem tags | Baseline metadata |
| **standard** | ~60 min | minimal + api, security, metrics, extension, dependency | Production default |
| **full** | ~90 min | standard + test, performance | Full analysis coverage |

## Useful Environment Variables

```bash
# JVM sizing
export JAVA_OPTS="-Xmx16G -Xms4G"

# Joern path (when not on PATH)
export JOERN_PATH="/path/to/joern"

# PostgreSQL source root (used by subsystem_readme.sc)
export subsystem.srcroot="C:\Users\user\postgres-REL_17_6\src"
```

## Additional References

- Detailed walkthrough: [ENRICHMENT_README.md](ENRICHMENT_README.md)
- RAG pipeline plan: [C:\Users\user\pg_copilot\rag_cpgql\IMPLEMENTATION_PLAN.md](C:\Users\user\pg_copilot\rag_cpgql\IMPLEMENTATION_PLAN.md)
