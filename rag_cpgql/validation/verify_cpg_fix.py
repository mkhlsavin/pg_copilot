#!/usr/bin/env python3
"""
Verify CPG Database Fix - Check that filename field is properly populated.

This script verifies that the v5.1.0 fix for nodes_call.filename was
successfully applied and the CPG database contains complete data.

Checks:
1. nodes_call.filename is NOT NULL for >= 95% of records
2. backend/commands directory has coverage (> 0 calls)
3. bin/pg_dump directory has coverage (> 0 calls)
4. Critical CVE target files are present
"""

import argparse
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple

try:
    import duckdb
except ImportError:
    print("ERROR: duckdb not installed. Run: pip install duckdb")
    sys.exit(1)


@dataclass
class VerificationResult:
    """Result of a single verification check."""
    name: str
    passed: bool
    expected: str
    actual: str
    details: str = ""


def verify_filename_not_null(conn: duckdb.DuckDBPyConnection) -> VerificationResult:
    """Check that filename field is populated for most records."""
    query = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN filename IS NULL OR filename = '' THEN 1 ELSE 0 END) as null_count,
            SUM(CASE WHEN filename IS NOT NULL AND filename != '' THEN 1 ELSE 0 END) as populated_count
        FROM nodes_call
    """
    result = conn.execute(query).fetchone()
    total, null_count, populated_count = result

    if total == 0:
        return VerificationResult(
            name="filename_not_null",
            passed=False,
            expected="nodes_call should have records",
            actual="0 records found",
            details="The nodes_call table is empty"
        )

    null_pct = (null_count / total) * 100
    populated_pct = (populated_count / total) * 100
    passed = null_pct < 5  # Less than 5% NULL is acceptable

    return VerificationResult(
        name="filename_not_null",
        passed=passed,
        expected="NULL < 5%",
        actual=f"NULL = {null_pct:.2f}% ({null_count:,} of {total:,})",
        details=f"Populated: {populated_pct:.2f}% ({populated_count:,} records)"
    )


def verify_directory_coverage(conn: duckdb.DuckDBPyConnection) -> List[VerificationResult]:
    """Check coverage for critical directories."""
    query = """
        SELECT
            CASE
                WHEN filename LIKE 'backend/access%' OR filename LIKE '%/backend/access%' THEN 'backend/access'
                WHEN filename LIKE 'backend/catalog%' OR filename LIKE '%/backend/catalog%' THEN 'backend/catalog'
                WHEN filename LIKE 'backend/commands%' OR filename LIKE '%/backend/commands%' THEN 'backend/commands'
                WHEN filename LIKE 'backend/optimizer%' OR filename LIKE '%/backend/optimizer%' THEN 'backend/optimizer'
                WHEN filename LIKE 'backend/parser%' OR filename LIKE '%/backend/parser%' THEN 'backend/parser'
                WHEN filename LIKE 'backend/utils%' OR filename LIKE '%/backend/utils%' THEN 'backend/utils'
                WHEN filename LIKE 'bin/pg_dump%' OR filename LIKE '%/bin/pg_dump%' THEN 'bin/pg_dump'
                WHEN filename LIKE 'src/bin/pg_dump%' OR filename LIKE '%/src/bin/pg_dump%' THEN 'bin/pg_dump'
                ELSE 'other'
            END as directory,
            COUNT(*) as count
        FROM nodes_call
        WHERE filename IS NOT NULL AND filename != ''
        GROUP BY directory
        ORDER BY count DESC
    """
    results = conn.execute(query).fetchall()
    dir_counts = {row[0]: row[1] for row in results}

    # Critical directories that must have coverage
    critical_dirs = {
        "backend/commands": 5000,  # Expected minimum
        "bin/pg_dump": 2000,       # Expected minimum
    }

    verification_results = []

    for dir_name, min_expected in critical_dirs.items():
        count = dir_counts.get(dir_name, 0)
        passed = count > 0

        verification_results.append(VerificationResult(
            name=f"directory_{dir_name.replace('/', '_')}",
            passed=passed,
            expected=f"> 0 (target: {min_expected:,})",
            actual=f"{count:,} calls",
            details="CRITICAL for CVE detection" if not passed else "OK"
        ))

    # Add summary of all directories
    summary_lines = [f"  {d}: {c:,}" for d, c in sorted(dir_counts.items(), key=lambda x: -x[1]) if c > 0]
    summary = "\n".join(summary_lines[:10])  # Top 10

    verification_results.append(VerificationResult(
        name="directory_summary",
        passed=True,
        expected="N/A",
        actual=f"{len(dir_counts)} directories",
        details=f"Top directories:\n{summary}"
    ))

    return verification_results


def verify_cve_target_files(conn: duckdb.DuckDBPyConnection) -> List[VerificationResult]:
    """Check that CVE target files are present."""
    target_files = [
        ("analyze.c", "CVE-2025-8713"),
        ("pg_dump.c", "CVE-2025-8714"),
        ("pg_backup_archiver.c", "CVE-2025-8715"),
        ("selfuncs.c", "CVE-2025-8713"),
        ("plancat.c", "CVE-2025-8713"),
    ]

    results = []
    for filename, cve in target_files:
        query = f"""
            SELECT filename, COUNT(*) as count
            FROM nodes_call
            WHERE filename LIKE '%{filename}'
            GROUP BY filename
        """
        rows = conn.execute(query).fetchall()
        total_count = sum(row[1] for row in rows)
        files_found = [row[0] for row in rows]

        passed = total_count > 0
        results.append(VerificationResult(
            name=f"file_{filename}",
            passed=passed,
            expected=f"> 0 calls ({cve})",
            actual=f"{total_count:,} calls",
            details=f"Files: {', '.join(files_found[:3])}" if files_found else "NOT FOUND"
        ))

    return results


def verify_table_stats(conn: duckdb.DuckDBPyConnection) -> VerificationResult:
    """Get overall table statistics."""
    stats = {}
    tables = ["nodes_method", "nodes_call", "call_graph", "call_containment", "edges_reaching_def"]

    for table in tables:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            stats[table] = count
        except:
            stats[table] = 0

    summary_lines = [f"  {t}: {c:,}" for t, c in stats.items()]
    summary = "\n".join(summary_lines)

    all_populated = all(c > 0 for t, c in stats.items() if t in ["nodes_method", "nodes_call"])

    return VerificationResult(
        name="table_statistics",
        passed=all_populated,
        expected="Core tables populated",
        actual=f"{len([c for c in stats.values() if c > 0])}/{len(stats)} tables",
        details=f"Table counts:\n{summary}"
    )


def run_verification(db_path: str) -> Tuple[List[VerificationResult], bool]:
    """Run all verification checks."""
    print(f"\n{'='*60}")
    print(f"CPG Database Verification")
    print(f"Database: {db_path}")
    print(f"{'='*60}\n")

    if not Path(db_path).exists():
        print(f"ERROR: Database not found: {db_path}")
        return [], False

    conn = duckdb.connect(db_path, read_only=True)

    all_results = []

    # 1. Table statistics
    print("Checking table statistics...")
    all_results.append(verify_table_stats(conn))

    # 2. Filename not null
    print("Checking filename field...")
    all_results.append(verify_filename_not_null(conn))

    # 3. Directory coverage
    print("Checking directory coverage...")
    all_results.extend(verify_directory_coverage(conn))

    # 4. CVE target files
    print("Checking CVE target files...")
    all_results.extend(verify_cve_target_files(conn))

    conn.close()

    # Print results
    print(f"\n{'='*60}")
    print("VERIFICATION RESULTS")
    print(f"{'='*60}\n")

    passed_count = 0
    failed_count = 0

    for result in all_results:
        status = "PASS" if result.passed else "FAIL"
        emoji = "[+]" if result.passed else "[X]"

        print(f"{emoji} {result.name}")
        print(f"    Expected: {result.expected}")
        print(f"    Actual:   {result.actual}")
        if result.details and not result.details.startswith("OK"):
            for line in result.details.split("\n"):
                print(f"    {line}")
        print()

        if result.passed:
            passed_count += 1
        else:
            failed_count += 1

    # Summary
    print(f"{'='*60}")
    all_passed = failed_count == 0
    status = "ALL CHECKS PASSED" if all_passed else "SOME CHECKS FAILED"
    print(f"Summary: {passed_count} passed, {failed_count} failed - {status}")
    print(f"{'='*60}\n")

    if not all_passed:
        print("RECOMMENDATION:")
        print("  The CPG database may still have incomplete data.")
        print("  Consider re-exporting from Joern with full coverage.")
        print("  Check that joern_to_duckdb_v2.py has the filename fix applied.")

    return all_results, all_passed


def main():
    parser = argparse.ArgumentParser(description="Verify CPG database fix for filename field")
    parser.add_argument(
        "--db", "-d",
        type=str,
        default="cpg.duckdb",
        help="Path to DuckDB CPG database (default: cpg.duckdb)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    # Try to find database
    db_path = args.db
    if not Path(db_path).exists():
        # Try common locations
        candidates = [
            Path.cwd() / db_path,
            Path.cwd().parent / db_path,
            Path(__file__).parent.parent / db_path,
        ]
        for candidate in candidates:
            if candidate.exists():
                db_path = str(candidate)
                break

    results, all_passed = run_verification(db_path)

    if args.json:
        import json
        json_results = [
            {
                "name": r.name,
                "passed": r.passed,
                "expected": r.expected,
                "actual": r.actual,
                "details": r.details
            }
            for r in results
        ]
        print(json.dumps({"results": json_results, "all_passed": all_passed}, indent=2))

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
