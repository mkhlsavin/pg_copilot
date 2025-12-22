"""DuckDB CPG Client v2 - Backward Compatibility Facade.

This module provides backward compatibility with the original API.
The implementation has been refactored into the src.cpg_export.client package.

Use the new package directly for better organization:
    from src.cpg_export.client import DuckDBCPGClient, CPGStatistics

Or continue using this module for backward compatibility:
    from src.cpg_export.duckdb_cpg_client_v2 import DuckDBCPGClient, CPGStatistics
"""

# Re-export all public classes from the new package
from src.cpg_export.client import (
    DuckDBCPGClient,
    DuckDBConnectionPool,
    get_global_pool,
    CPGStatistics,
)

__all__ = [
    "DuckDBCPGClient",
    "DuckDBConnectionPool",
    "get_global_pool",
    "CPGStatistics",
]


def main():
    """Example usage and testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Query DuckDB CPG v2")
    parser.add_argument('--db', type=str, default='cpg.duckdb',
                        help='Path to DuckDB database file')
    parser.add_argument('--stats', action='store_true',
                        help='Show CPG statistics')
    parser.add_argument('--method', type=str,
                        help='Find method by name')
    parser.add_argument('--callees', type=str,
                        help='Get callees of method')
    parser.add_argument('--callers', type=str,
                        help='Get callers of method')
    parser.add_argument('--chain', type=str,
                        help='Get call chain from method')
    parser.add_argument('--type', type=str,
                        help='Find type declaration by name')
    parser.add_argument('--identifier', type=str,
                        help='Find identifiers by name')

    args = parser.parse_args()

    with DuckDBCPGClient(db_path=args.db) as client:
        if args.stats:
            stats = client.get_statistics()
            print("\nCPG Statistics (CPG Spec v1.1):")
            print("=" * 80)
            print(f"  Methods: {stats.method_count}")
            print(f"  Call Nodes: {stats.call_node_count}")
            print(f"  Identifiers: {stats.identifier_count}")
            print(f"  Literals: {stats.literal_count}")
            print(f"  Local Variables: {stats.local_count}")
            print(f"  Parameters: {stats.param_count}")
            print(f"  Returns: {stats.return_count}")
            print(f"  Blocks: {stats.block_count}")
            print(f"  Control Structures: {stats.control_structure_count}")
            print(f"  Type Declarations: {stats.type_decl_count}")
            print(f"\n  AST Edges: {stats.ast_edge_count}")
            print(f"  CFG Edges: {stats.cfg_edge_count}")
            print(f"  Call Edges: {stats.call_edge_count}")
            print(f"  Reference Edges: {stats.ref_edge_count}")
            print(f"  Reaching Def Edges: {stats.reaching_def_edge_count}")
            print(f"  Argument Edges: {stats.argument_edge_count}")

        if args.method:
            results = client.find_method_by_name(args.method)
            print(f"\nMethods matching '{args.method}':")
            print("=" * 80)
            for method in results:
                print(f"  {method['name']} ({method['filename']}:{method['line_number']})")
                print(f"    Full name: {method['full_name']}")

        if args.callees:
            results = client.get_direct_callees(args.callees)
            print(f"\nMethods called by '{args.callees}':")
            print("=" * 80)
            for callee in results:
                print(f"  -> {callee['callee_name']} ({callee['callee_filename']}:{callee['callee_line']})")

        if args.callers:
            results = client.get_direct_callers(args.callers)
            print(f"\nMethods calling '{args.callers}':")
            print("=" * 80)
            for caller in results:
                print(f"  <- {caller['caller_name']} ({caller['caller_filename']}:{caller['caller_line']})")

        if args.chain:
            results = client.get_call_chain(args.chain)
            print(f"\nCall chain from '{args.chain}':")
            print("=" * 80)
            current_depth = 0
            for method in results:
                if method['depth'] != current_depth:
                    current_depth = method['depth']
                    print(f"\nDepth {current_depth}:")
                print(f"  -> {method['name']} ({method['filename']}:{method['line_number']})")

        if args.type:
            results = client.find_type_by_name(args.type)
            print(f"\nType declarations matching '{args.type}':")
            print("=" * 80)
            for type_decl in results:
                print(f"  {type_decl['name']} ({type_decl['filename']})")
                print(f"    Full name: {type_decl['full_name']}")
                if type_decl['inherits_from_type_full_name']:
                    print(f"    Inherits: {type_decl['inherits_from_type_full_name']}")

        if args.identifier:
            results = client.find_identifiers_by_name(args.identifier)
            print(f"\nIdentifiers named '{args.identifier}':")
            print("=" * 80)
            for ident in results:
                print(f"  {ident['name']} : {ident['type_full_name']} (line {ident['line_number']})")


if __name__ == "__main__":
    main()
