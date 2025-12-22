#!/usr/bin/env python3
"""
PostgreSQL Security Validation Runner.

Validates hypothesis generation against PostgreSQL 17.5/17.6 CPG databases
to detect CVE-2025-8713, CVE-2025-8714, and CVE-2025-8715.

Usage:
    python run_validation.py --db path/to/postgresql.duckdb
    python run_validation.py --compare 17.5.duckdb 17.6.duckdb
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.security.hypothesis.validator import (
    HypothesisValidator,
    validate_postgresql_security,
    generate_validation_report,
)
from src.security.hypothesis.models import (
    ValidationResults,
    ValidationStatus,
    SecurityHypothesis,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Target CVEs for PostgreSQL 17.5/17.6
TARGET_CVES = ["CVE-2025-8713", "CVE-2025-8714", "CVE-2025-8715"]

# Success criteria from the plan
SUCCESS_CRITERIA = {
    "detection_rate": 0.67,  # >= 67% (2 of 3 CVEs)
    "precision": 0.70,       # >= 70%
    "hypothesis_quality": 0.50,  # >= 50% confirmation rate
    "max_time_sec": 60,      # < 60s for 100 hypotheses
}


def validate_single_database(
    db_path: str,
    output_dir: Optional[str] = None,
) -> ValidationResults:
    """Run validation on a single PostgreSQL CPG database.

    Args:
        db_path: Path to DuckDB database
        output_dir: Optional output directory for reports

    Returns:
        ValidationResults
    """
    logger.info(f"Starting validation for: {db_path}")

    results = validate_postgresql_security(db_path, include_known_cves=True)

    # Log summary
    logger.info(f"Validation complete:")
    logger.info(f"  - Total hypotheses: {results.total_hypotheses}")
    logger.info(f"  - Confirmed: {results.confirmed_hypotheses}")
    logger.info(f"  - Rejected: {results.rejected_hypotheses}")
    logger.info(f"  - CVEs found: {results.cves_found}")
    logger.info(f"  - CVEs missed: {results.cves_missed}")
    logger.info(f"  - Detection rate: {results.detection_rate:.1%}")
    logger.info(f"  - Precision: {results.precision:.1%}")

    # Check against success criteria
    check_success_criteria(results)

    # Save results if output dir specified
    if output_dir:
        save_results(results, db_path, output_dir)

    return results


def compare_databases(
    vulnerable_db: str,
    fixed_db: str,
    output_dir: Optional[str] = None,
) -> Dict:
    """Compare validation results between vulnerable and fixed versions.

    Args:
        vulnerable_db: Path to vulnerable version (e.g., 17.5)
        fixed_db: Path to fixed version (e.g., 17.6)
        output_dir: Optional output directory

    Returns:
        Comparison results dictionary
    """
    logger.info(f"Comparing {vulnerable_db} vs {fixed_db}")

    # Validate both
    vuln_results = validate_single_database(vulnerable_db)
    fixed_results = validate_single_database(fixed_db)

    comparison = {
        "vulnerable_version": {
            "path": vulnerable_db,
            "total_hypotheses": vuln_results.total_hypotheses,
            "confirmed": vuln_results.confirmed_hypotheses,
            "cves_found": vuln_results.cves_found,
            "detection_rate": vuln_results.detection_rate,
        },
        "fixed_version": {
            "path": fixed_db,
            "total_hypotheses": fixed_results.total_hypotheses,
            "confirmed": fixed_results.confirmed_hypotheses,
            "cves_found": fixed_results.cves_found,
            "detection_rate": fixed_results.detection_rate,
        },
        "delta": {
            "confirmed_diff": vuln_results.confirmed_hypotheses - fixed_results.confirmed_hypotheses,
            "cves_fixed": [cve for cve in vuln_results.cves_found if cve not in fixed_results.cves_found],
        },
    }

    # Expected: vulnerable should have more findings than fixed
    if comparison["delta"]["confirmed_diff"] > 0:
        logger.info(f"SUCCESS: Vulnerable version has {comparison['delta']['confirmed_diff']} more findings")
        logger.info(f"CVEs fixed in new version: {comparison['delta']['cves_fixed']}")
    else:
        logger.warning("UNEXPECTED: Fixed version has same or more findings than vulnerable")

    if output_dir:
        comparison_path = Path(output_dir) / "comparison_results.json"
        with open(comparison_path, 'w') as f:
            json.dump(comparison, f, indent=2)
        logger.info(f"Saved comparison to {comparison_path}")

    return comparison


def check_success_criteria(results: ValidationResults) -> bool:
    """Check if validation meets success criteria.

    Args:
        results: Validation results

    Returns:
        True if all criteria met
    """
    passed = True

    # Detection rate
    if results.detection_rate >= SUCCESS_CRITERIA["detection_rate"]:
        logger.info(f"✓ Detection rate: {results.detection_rate:.1%} >= {SUCCESS_CRITERIA['detection_rate']:.0%}")
    else:
        logger.warning(f"✗ Detection rate: {results.detection_rate:.1%} < {SUCCESS_CRITERIA['detection_rate']:.0%}")
        passed = False

    # Precision
    if results.precision >= SUCCESS_CRITERIA["precision"]:
        logger.info(f"✓ Precision: {results.precision:.1%} >= {SUCCESS_CRITERIA['precision']:.0%}")
    else:
        logger.warning(f"✗ Precision: {results.precision:.1%} < {SUCCESS_CRITERIA['precision']:.0%}")
        passed = False

    # Hypothesis quality (confirmation rate)
    if results.total_hypotheses > 0:
        quality = results.confirmed_hypotheses / results.total_hypotheses
        if quality >= SUCCESS_CRITERIA["hypothesis_quality"]:
            logger.info(f"✓ Hypothesis quality: {quality:.1%} >= {SUCCESS_CRITERIA['hypothesis_quality']:.0%}")
        else:
            logger.warning(f"✗ Hypothesis quality: {quality:.1%} < {SUCCESS_CRITERIA['hypothesis_quality']:.0%}")
            passed = False

    # Performance
    total_time = results.total_time_sec
    if total_time <= SUCCESS_CRITERIA["max_time_sec"]:
        logger.info(f"✓ Performance: {total_time:.1f}s <= {SUCCESS_CRITERIA['max_time_sec']}s")
    else:
        logger.warning(f"✗ Performance: {total_time:.1f}s > {SUCCESS_CRITERIA['max_time_sec']}s")
        passed = False

    return passed


def save_results(
    results: ValidationResults,
    db_path: str,
    output_dir: str,
) -> None:
    """Save validation results to files.

    Args:
        results: Validation results
        db_path: Path to database (for naming)
        output_dir: Output directory
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    db_name = Path(db_path).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save JSON results
    json_path = output_path / f"{db_name}_{timestamp}_results.json"
    with open(json_path, 'w') as f:
        json.dump({
            "batch_id": results.batch_id,
            "total_hypotheses": results.total_hypotheses,
            "confirmed": results.confirmed_hypotheses,
            "rejected": results.rejected_hypotheses,
            "inconclusive": results.inconclusive_hypotheses,
            "cves_found": results.cves_found,
            "cves_missed": results.cves_missed,
            "detection_rate": results.detection_rate,
            "precision": results.precision,
            "recall": results.recall,
            "f1_score": results.f1_score,
            "generation_time_sec": results.generation_time_sec,
            "execution_time_sec": results.execution_time_sec,
            "total_time_sec": results.total_time_sec,
        }, f, indent=2)

    logger.info(f"Saved JSON results to {json_path}")


def main():
    parser = argparse.ArgumentParser(
        description="PostgreSQL Security Validation Runner"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Single database validation
    validate_parser = subparsers.add_parser("validate", help="Validate a single database")
    validate_parser.add_argument(
        "--db", "-d",
        required=True,
        help="Path to DuckDB CPG database"
    )
    validate_parser.add_argument(
        "--output", "-o",
        help="Output directory for reports"
    )

    # Compare two databases
    compare_parser = subparsers.add_parser("compare", help="Compare vulnerable vs fixed versions")
    compare_parser.add_argument(
        "--vulnerable", "-v",
        required=True,
        help="Path to vulnerable version database (e.g., 17.5)"
    )
    compare_parser.add_argument(
        "--fixed", "-f",
        required=True,
        help="Path to fixed version database (e.g., 17.6)"
    )
    compare_parser.add_argument(
        "--output", "-o",
        help="Output directory for reports"
    )

    args = parser.parse_args()

    if args.command == "validate":
        validate_single_database(args.db, args.output)
    elif args.command == "compare":
        compare_databases(args.vulnerable, args.fixed, args.output)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
