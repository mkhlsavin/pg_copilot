"""Validation of CPG export completeness.

This module provides tools to validate that all data from Joern
has been successfully exported to DuckDB.
"""
import logging
import re
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating a single entity type"""
    entity: str
    joern_count: int
    duckdb_count: int
    is_valid: bool
    missing: int

    @property
    def percentage(self) -> float:
        """Percentage of data exported"""
        if self.joern_count == 0:
            return 100.0
        return (self.duckdb_count / self.joern_count) * 100


# Mapping from DuckDB table names to Joern query types
NODE_TYPE_MAPPING = {
    'nodes_method': 'method',
    'nodes_call': 'call',
    'nodes_identifier': 'identifier',
    'nodes_literal': 'literal',
    'nodes_local': 'local',
    'nodes_param': 'parameter',
    'nodes_return': 'ret',
    'nodes_block': 'block',
    'nodes_control_structure': 'controlStructure',
    'nodes_type_decl': 'typeDecl',
    'nodes_comment': 'comment',
    'nodes_file': 'file',
    'nodes_namespace': 'namespace',
    'nodes_namespace_block': 'namespaceBlock',
    'nodes_member': 'member',
    'nodes_type': 'typ',
    'nodes_method_parameter_out': 'methodParameterOut',
    'nodes_method_return': 'methodReturn',
    'nodes_field_identifier': 'fieldAccess',
    'nodes_type_argument': 'typeArgument',
    'nodes_type_parameter': 'typeParameter',
    'nodes_jump_label': 'jumpLabel',
    'nodes_jump_target': 'jumpTarget',
    'nodes_method_ref': 'methodRef',
    'nodes_modifier': 'modifier',
    'nodes_type_ref': 'typeRef',
    'nodes_unknown': 'unknown',
    'nodes_binding': 'binding',
    'nodes_annotation': 'annotation',
}


class ExportValidator:
    """Validates that CPG export is complete by comparing Joern and DuckDB counts."""

    def __init__(self, joern_client, conn):
        """
        Args:
            joern_client: JoernClient instance for querying Joern
            conn: DuckDB connection
        """
        self.joern_client = joern_client
        self.conn = conn

    def validate_all(self, node_types: Optional[list] = None) -> Dict[str, ValidationResult]:
        """Validate all exported node types.

        Args:
            node_types: Optional list of node types to validate. If None, validate all.

        Returns:
            Dict mapping table names to ValidationResult
        """
        results = {}

        types_to_validate = node_types or list(NODE_TYPE_MAPPING.keys())

        for table_name in types_to_validate:
            if table_name in NODE_TYPE_MAPPING:
                result = self._validate_node_type(table_name)
                results[table_name] = result

        return results

    def _validate_node_type(self, table_name: str) -> ValidationResult:
        """Validate a single node type.

        Args:
            table_name: DuckDB table name (e.g., 'nodes_method')

        Returns:
            ValidationResult with comparison data
        """
        joern_type = NODE_TYPE_MAPPING.get(table_name)
        if not joern_type:
            return ValidationResult(
                entity=table_name,
                joern_count=0,
                duckdb_count=0,
                is_valid=True,
                missing=0
            )

        # Get Joern count
        joern_count = self._get_joern_count(joern_type)

        # Get DuckDB count
        duckdb_count = self._get_duckdb_count(table_name)

        is_valid = (joern_count == duckdb_count)
        missing = max(0, joern_count - duckdb_count)

        return ValidationResult(
            entity=table_name,
            joern_count=joern_count,
            duckdb_count=duckdb_count,
            is_valid=is_valid,
            missing=missing
        )

    def _get_joern_count(self, joern_type: str) -> int:
        """Get count of nodes from Joern.

        Args:
            joern_type: Joern type name (e.g., 'method', 'call')

        Returns:
            Count of nodes in Joern
        """
        try:
            query = f"cpg.{joern_type}.size"
            result = self.joern_client.execute_query(query)

            if result and result.get('success'):
                count_str = result.get('result', '0')
                # Parse "val res: Int = 12345" format
                match = re.search(r'=\s*(\d+)', count_str)
                if match:
                    return int(match.group(1))
                # Try direct int parse
                try:
                    return int(count_str.strip())
                except ValueError:
                    pass
            return 0
        except Exception as e:
            logger.warning(f"Could not get Joern count for {joern_type}: {e}")
            return 0

    def _get_duckdb_count(self, table_name: str) -> int:
        """Get count of nodes from DuckDB.

        Args:
            table_name: DuckDB table name

        Returns:
            Count of rows in table
        """
        try:
            result = self.conn.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.warning(f"Could not get DuckDB count for {table_name}: {e}")
            return 0

    def print_report(self, results: Dict[str, ValidationResult]):
        """Print a formatted validation report.

        Args:
            results: Dict of validation results from validate_all()
        """
        print("\n" + "=" * 70)
        print("CPG EXPORT VALIDATION REPORT")
        print("=" * 70)

        all_valid = True
        total_joern = 0
        total_duckdb = 0

        # Sort by entity name
        sorted_results = sorted(results.items())

        for entity, result in sorted_results:
            status = "[OK]" if result.is_valid else "[MISSING]"
            pct = result.percentage

            print(f"{status:10} {entity:35} {result.duckdb_count:>10} / {result.joern_count:>10} ({pct:5.1f}%)")

            if not result.is_valid:
                all_valid = False

            total_joern += result.joern_count
            total_duckdb += result.duckdb_count

        print("-" * 70)

        total_pct = (total_duckdb / total_joern * 100) if total_joern > 0 else 100
        print(f"{'TOTAL':10} {'':35} {total_duckdb:>10} / {total_joern:>10} ({total_pct:5.1f}%)")

        print("=" * 70)

        if all_valid:
            print("[SUCCESS] ALL DATA EXPORTED SUCCESSFULLY")
        else:
            missing_count = sum(r.missing for r in results.values())
            print(f"[WARNING] {missing_count} RECORDS MISSING - CHECK LOGS")

        print("=" * 70 + "\n")

        return all_valid

    def get_summary(self, results: Dict[str, ValidationResult]) -> dict:
        """Get summary statistics from validation results.

        Args:
            results: Dict of validation results

        Returns:
            Dict with summary statistics
        """
        total_joern = sum(r.joern_count for r in results.values())
        total_duckdb = sum(r.duckdb_count for r in results.values())
        total_missing = sum(r.missing for r in results.values())
        all_valid = all(r.is_valid for r in results.values())
        valid_count = sum(1 for r in results.values() if r.is_valid)

        return {
            'total_joern': total_joern,
            'total_duckdb': total_duckdb,
            'total_missing': total_missing,
            'all_valid': all_valid,
            'valid_entities': valid_count,
            'total_entities': len(results),
            'percentage': (total_duckdb / total_joern * 100) if total_joern > 0 else 100
        }


def validate_export(joern_client, conn, print_report: bool = True) -> Dict[str, ValidationResult]:
    """Convenience function to validate export and optionally print report.

    Args:
        joern_client: JoernClient instance
        conn: DuckDB connection
        print_report: Whether to print the report

    Returns:
        Dict of validation results
    """
    validator = ExportValidator(joern_client, conn)
    results = validator.validate_all()

    if print_report:
        validator.print_report(results)

    return results
