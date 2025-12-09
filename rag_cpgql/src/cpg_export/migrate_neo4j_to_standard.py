"""
Migrate Neo4j CSV format DuckDB to standard CPG schema.

Converts column names from Neo4j export format (:ID, NAME:string, etc.)
to standard CPG schema format (id, name, etc.).
"""

import duckdb
import logging
from pathlib import Path
from typing import Dict, List, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Column mapping from Neo4j format to standard format
NODE_COLUMN_MAPPINGS = {
    ":ID": "id",
    ":LABEL": None,  # Skip this column
    "NAME:string": "name",
    "FULL_NAME:string": "full_name",
    "SIGNATURE:string": "signature",
    "FILENAME:string": "filename",
    "LINE_NUMBER:int": "line_number",
    "LINE_NUMBER_END:int": "line_number_end",
    "COLUMN_NUMBER:int": "column_number",
    "COLUMN_NUMBER_END:int": "column_number_end",
    "CODE:string": "code",
    "IS_EXTERNAL:boolean": "is_external",
    "AST_PARENT_TYPE:string": "ast_parent_type",
    "AST_PARENT_FULL_NAME:string": "ast_parent_full_name",
    "ORDER:int": "order_index",
    "HASH": "hash",
    "METHOD_FULL_NAME:string": "method_full_name",
    "ARGUMENT_INDEX:int": "argument_index",
    "TYPE_FULL_NAME:string": "type_full_name",
    "DISPATCH_TYPE:string": "dispatch_type",
    "DYNAMIC_TYPE_HINT_FULL_NAME:string[]": "dynamic_type_hint_full_name",
    "CONTROL_STRUCTURE_TYPE:string": "control_structure_type",
    "PARSER_TYPE_NAME:string": "parser_type_name",
    "EVALUATION_STRATEGY:string": "evaluation_strategy",
    "INDEX:int": "index",
    "OFFSET:int": "offset",
    "OFFSET_END:int": "offset_end",
    "GENERIC_SIGNATURE:string": "generic_signature",
    "VALUE:string": "value",
    "INHERITS_FROM_TYPE_FULL_NAME:string[]": "inherits_from_type_full_name",
    "ALIAS_TYPE_FULL_NAME:string": "alias_type_full_name",
    "MODIFIER_TYPE:string": "modifier_type",
}

EDGE_COLUMN_MAPPINGS = {
    ":START_ID": "src_id",
    ":END_ID": "dst_id",
    ":TYPE": "edge_type",
}


def get_table_columns(conn: duckdb.DuckDBPyConnection, table_name: str) -> List[str]:
    """Get column names for a table."""
    result = conn.execute(f"DESCRIBE {table_name}").fetchall()
    return [row[0] for row in result]


def create_column_mapping(columns: List[str], is_edge: bool = False) -> Dict[str, str]:
    """Create mapping from old column names to new names."""
    mappings = EDGE_COLUMN_MAPPINGS if is_edge else NODE_COLUMN_MAPPINGS
    result = {}

    for col in columns:
        if col in mappings:
            new_name = mappings[col]
            if new_name:  # Skip None mappings
                result[col] = new_name
        else:
            # Keep column as lowercase and clean up
            new_name = col.lower()
            # Remove type suffixes
            new_name = new_name.replace(":string[]", "").replace(":string", "")
            new_name = new_name.replace(":int", "").replace(":boolean", "")
            new_name = new_name.replace(":", "_")
            # Clean up brackets and special chars
            new_name = new_name.replace("[]", "_list").replace("[", "_").replace("]", "_")
            new_name = new_name.strip("_").replace("__", "_")
            if new_name:
                result[col] = new_name

    return result


def migrate_table(
    src_conn: duckdb.DuckDBPyConnection,
    dst_conn: duckdb.DuckDBPyConnection,
    table_name: str,
    is_edge: bool = False
) -> int:
    """Migrate a single table to standard schema."""
    columns = get_table_columns(src_conn, table_name)
    mapping = create_column_mapping(columns, is_edge)

    if not mapping:
        logger.warning(f"No columns to migrate for {table_name}")
        return 0

    # Build SELECT clause with column renaming
    select_parts = []
    for old_col, new_col in mapping.items():
        select_parts.append(f'"{old_col}" AS {new_col}')

    select_clause = ", ".join(select_parts)

    # Create new table with migrated data
    create_query = f"""
        CREATE TABLE {table_name} AS
        SELECT {select_clause}
        FROM src_db.{table_name}
    """

    try:
        dst_conn.execute(create_query)
        count = dst_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        logger.info(f"  {table_name}: {count:,} rows ({len(mapping)} columns)")
        return count
    except Exception as e:
        logger.error(f"  {table_name}: ERROR - {e}")
        return 0


def migrate_database(src_path: str, dst_path: str) -> Dict[str, int]:
    """
    Migrate a Neo4j format DuckDB to standard schema.

    Args:
        src_path: Path to source (Neo4j format) DuckDB
        dst_path: Path to destination (standard format) DuckDB

    Returns:
        Dictionary with table names and row counts
    """
    logger.info(f"Migrating {src_path} -> {dst_path}")

    # Remove destination if exists
    dst_file = Path(dst_path)
    if dst_file.exists():
        dst_file.unlink()
        logger.info(f"Removed existing {dst_path}")

    # Connect to both databases
    src_conn = duckdb.connect(src_path, read_only=True)
    dst_conn = duckdb.connect(dst_path)

    # Attach source database
    dst_conn.execute(f"ATTACH '{src_path}' AS src_db (READ_ONLY)")

    stats = {}

    try:
        # Get all tables from source
        tables = src_conn.execute("SHOW TABLES").fetchall()

        logger.info(f"Found {len(tables)} tables to migrate")

        # Migrate node tables
        logger.info("Migrating node tables...")
        for (table_name,) in tables:
            if table_name.startswith("nodes_"):
                count = migrate_table(src_conn, dst_conn, table_name, is_edge=False)
                stats[table_name] = count

        # Migrate edge tables
        logger.info("Migrating edge tables...")
        for (table_name,) in tables:
            if table_name.startswith("edges_"):
                count = migrate_table(src_conn, dst_conn, table_name, is_edge=True)
                stats[table_name] = count

        # Create indexes
        logger.info("Creating indexes...")

        # Get list of actually created tables
        created_tables = [t[0] for t in dst_conn.execute("SHOW TABLES").fetchall()]

        # Node indexes
        for table_name in created_tables:
            if table_name.startswith("nodes_"):
                try:
                    dst_conn.execute(f"CREATE INDEX idx_{table_name}_id ON {table_name}(id)")
                except:
                    pass
                try:
                    columns = [c[0] for c in dst_conn.execute(f"DESCRIBE {table_name}").fetchall()]
                    if "name" in columns:
                        dst_conn.execute(f"CREATE INDEX idx_{table_name}_name ON {table_name}(name)")
                except:
                    pass

        # Edge indexes
        for table_name in created_tables:
            if table_name.startswith("edges_"):
                try:
                    dst_conn.execute(f"CREATE INDEX idx_{table_name}_src ON {table_name}(src_id)")
                    dst_conn.execute(f"CREATE INDEX idx_{table_name}_dst ON {table_name}(dst_id)")
                except:
                    pass

        logger.info("Migration completed!")

    finally:
        src_conn.close()
        dst_conn.close()

    return stats


def print_stats(stats: Dict[str, int]):
    """Print migration statistics."""
    print("\n=== Migration Statistics ===")

    node_total = sum(v for k, v in stats.items() if k.startswith("nodes_"))
    edge_total = sum(v for k, v in stats.items() if k.startswith("edges_"))

    print(f"\nNode tables: {sum(1 for k in stats if k.startswith('nodes_'))}")
    for name, count in sorted(stats.items()):
        if name.startswith("nodes_"):
            print(f"  {name:30} {count:>10,}")
    print(f"  {'TOTAL':30} {node_total:>10,}")

    print(f"\nEdge tables: {sum(1 for k in stats if k.startswith('edges_'))}")
    for name, count in sorted(stats.items()):
        if name.startswith("edges_"):
            print(f"  {name:30} {count:>10,}")
    print(f"  {'TOTAL':30} {edge_total:>10,}")

    print(f"\nGrand Total: {node_total + edge_total:,} records")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python migrate_neo4j_to_standard.py <source.duckdb> <destination.duckdb>")
        sys.exit(1)

    src_path = sys.argv[1]
    dst_path = sys.argv[2]

    stats = migrate_database(src_path, dst_path)
    print_stats(stats)
