# PostgreSQL Security Validation

This directory contains tools for validating the hypothesis generation module against PostgreSQL 17.5/17.6 source code to detect CVE-2025-8713, CVE-2025-8714, and CVE-2025-8715.

## Directory Structure

```
validation/
├── postgresql/
│   ├── 17.5/           # PostgreSQL 17.5 source (vulnerable)
│   └── 17.6/           # PostgreSQL 17.6 source (fixed)
├── cpg/
│   ├── postgresql-17.5.duckdb  # CPG database for 17.5
│   └── postgresql-17.6.duckdb  # CPG database for 17.6
├── run_validation.py   # Validation runner script
└── README.md           # This file
```

## Setup

### 1. Download PostgreSQL Sources

```bash
# Download PostgreSQL 17.5 (vulnerable version)
wget https://ftp.postgresql.org/pub/source/v17.5/postgresql-17.5.tar.gz
tar -xzf postgresql-17.5.tar.gz -C postgresql/17.5

# Download PostgreSQL 17.6 (fixed version)
wget https://ftp.postgresql.org/pub/source/v17.6/postgresql-17.6.tar.gz
tar -xzf postgresql-17.6.tar.gz -C postgresql/17.6
```

### 2. Generate CPG Databases

Use Joern to generate CPG databases from the source code:

```bash
# Generate CPG for 17.5
joern-export --format=duckdb postgresql/17.5/postgresql-17.5/ -o cpg/postgresql-17.5.duckdb

# Generate CPG for 17.6
joern-export --format=duckdb postgresql/17.6/postgresql-17.6/ -o cpg/postgresql-17.6.duckdb
```

Focus on critical directories:
- `src/bin/pg_dump/` (CVE-2025-8714, CVE-2025-8715)
- `src/backend/commands/analyze.c` (CVE-2025-8713)
- `src/backend/optimizer/`

## Running Validation

### Validate Single Database

```bash
python run_validation.py validate --db cpg/postgresql-17.5.duckdb --output results/
```

### Compare Vulnerable vs Fixed

```bash
python run_validation.py compare \
    --vulnerable cpg/postgresql-17.5.duckdb \
    --fixed cpg/postgresql-17.6.duckdb \
    --output results/
```

## Target CVEs

| CVE | Type | Affected Files | Description |
|-----|------|----------------|-------------|
| CVE-2025-8713 | Information Disclosure | analyze.c, plancat.c | Statistics data leakage via optimizer |
| CVE-2025-8714 | RCE | pg_dump.c, pg_backup_archiver.c | pg_dump injection via object names |
| CVE-2025-8715 | Code Injection | pg_dump.c, pg_backup_*.c | Newline injection in psql commands |

## Success Criteria

| Metric | Threshold | Description |
|--------|-----------|-------------|
| Detection Rate | >= 67% | Detect at least 2 of 3 CVEs |
| Precision | >= 70% | Max 30% false positives |
| Hypothesis Quality | >= 50% | Confirmation rate |
| Performance | < 60s | 100 hypotheses generation |

## Expected Results

For PostgreSQL 17.5 (vulnerable):
- Should detect vulnerabilities related to CVE-2025-8713/8714/8715
- Higher number of confirmed hypotheses

For PostgreSQL 17.6 (fixed):
- Should detect fewer vulnerabilities
- CVE patterns should be fixed

The comparison report shows which vulnerabilities were fixed between versions.
